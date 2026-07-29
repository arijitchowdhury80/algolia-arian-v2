"""PRISM report-QA — ground every answer in ONE bound audit report.

Two hooks, one plugin (shared binding state):
  L1 pre_llm_call      -> inject the bound company's audit-data.json each turn,
                          plus general Algolia knowledge from the prism_platform KB.
  L4 transform_llm_output -> a Gemini grounding judge verifies FACTUAL claims in the
                            drafted answer against BOTH the report AND the KB, and
                            REWRITES unsupported ones before the message is sent.

Decided scope:
  - FACTS about the prospect must be report-supported (SOURCE_REPORT).
  - GENERAL Algolia facts (products, competitor comparisons, case-study results from
    other companies like "Lacoste +37%", benchmarks) may come from the KB (SOURCE_KNOWLEDGE).
  - COACHING (hypotheses, F1-F6/M1-M10 moves, objection handling, call plans) is allowed
    and is NOT policed by the gate.
Report binding is detected from the conversation and held per session_id.
"""

import json
import os
import re
import unicodedata

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None

REPORTS_DIR = os.environ.get("PRISM_REPORTS_DIR", "/opt/data/reports")
ENV_FILE = os.environ.get("PRISM_ENV_FILE", "/opt/data/.env")
JUDGE_MODEL = os.environ.get("PRISM_JUDGE_MODEL", "gemini-2.5-flash")
PLATFORM_URL = os.environ.get("PRISM_PLATFORM_URL", "http://127.0.0.1:8000")

_BINDINGS: dict = {}                       # session_id -> slug
_INDEX_CACHE = {"mtime": 0.0, "rows": []}
_KNOWLEDGE_CACHE: dict = {}               # session_id -> formatted knowledge text

# Company-name words that are too generic to use as match tokens
_STOPWORDS = {"the", "inc", "llc", "co", "company", "corp", "group", "ltd", "sa", "de", "cv"}

GROUNDING_PREAMBLE = """\
[Facts source for this turn — {company} ({domain})]
The JSON below is the complete audit for {company}; it is the ONLY source for FACTS about this
prospect (numbers, scores, search vendor, findings, financials, competitors). Don't use outside
knowledge for those facts. If something isn't in it, say so plainly and don't guess. You may coach
freely as long as each point ties to a fact from the report. Never invent a number, source, or
finding. (This constrains facts only — your voice and style are entirely your own.)

AUDIT REPORT JSON:
{report_json}
[end audit report]"""

JUDGE_PROMPT = """You are a STRICT grounding verifier for a sales-intelligence assistant.

SOURCE_REPORT = the complete audit report (JSON) for a specific prospect; the ONLY allowed source
for FACTS about THIS specific prospect (numbers, scores, search vendor, named findings, financial
figures, dates, people/competitor names, percentages specific to this company).

SOURCE_KNOWLEDGE = a general Algolia knowledge base (products, features, competitor comparisons,
case-study results from OTHER companies like "Lacoste +37%", industry benchmarks); allowed source
for general Algolia facts only, NOT for facts about the specific prospect.

ANSWER = a drafted reply.

Find every FACTUAL claim in ANSWER. For each:
- Claims about THIS prospect: must be supported by SOURCE_REPORT.
- General Algolia facts (products, competitors, case-study results from other companies,
  benchmarks): must be supported by SOURCE_KNOWLEDGE.
- A factual claim is "unsupported" ONLY if it is absent from or contradicts BOTH sources.
- IGNORE coaching/advice/hypotheses/sales-methodology/opening-moves/objection-handling — those
  are NOT factual claims; never flag them.

Return ONLY minified JSON, no prose:
{{"verdict":"PASS" or "FAIL","unsupported":["<short claim>",...],"corrected":"<ANSWER rewritten so \
each unsupported factual claim is removed or replaced with the correct value from SOURCE_REPORT or \
SOURCE_KNOWLEDGE (or with '(not in the audit report)'); keep ALL coaching and ALL supported \
facts intact. CRITICAL: you are a fact-checker, not a ghostwriter — preserve the original's voice, \
tone, humor, and personality EXACTLY as written. Only the unsupported words change; every other word, \
including phrasing and wit, must read exactly as she wrote it. Never produce a flat, generic, \
corporate-sounding rewrite>"}}

SOURCE_REPORT:
{source_report}

SOURCE_KNOWLEDGE:
{source_knowledge}

ANSWER:
{answer}"""


# ---------------------------------------------------------------- helpers

def _norm(s):
    """NFKD-decompose, drop combining marks (accents→ASCII), lowercase, strip."""
    nfkd = unicodedata.normalize("NFKD", s)
    without_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return without_accents.lower().strip()


def _load_index():
    path = os.path.join(REPORTS_DIR, "index.json")
    try:
        mtime = os.path.getmtime(path)
        if mtime != _INDEX_CACHE["mtime"]:
            with open(path) as f:
                _INDEX_CACHE["rows"] = json.load(f).get("reports", [])
            _INDEX_CACHE["mtime"] = mtime
    except Exception:
        return []
    return _INDEX_CACHE["rows"]


def _match_slug(text):
    """Return the slug for the first report matching `text`, or None.

    Strategy (conservative — prefer precision over recall):
    1. Exact normalized substring: full slug, domain, full company name.
    2. Alias-token matching:
         - slug-without-hyphens  (e.g. "homedepotmexico")
         - domain root (text before first '.')  (e.g. "homedepot")
       Any token with len>=4 found as a substring in the normalized message → match.

    Deliberately does NOT tokenize individual words out of the company name (e.g.
    "Running" out of "Brooks Running") -- a multi-word company name can contain an
    ordinary English word that appears constantly in unrelated text ("is the audit
    still running?", cron's own "you are running as a scheduled job" boilerplate),
    which caused every such message to falsely bind to that company (found live
    2026-07-03). The exact-full-name check above already catches a real mention of
    the whole company name; only the risky single-word fallback is removed.
    """
    if not text:
        return None
    msg = _norm(text)

    for r in _load_index():
        slug = _norm(r.get("slug") or "")
        domain = _norm(r.get("domain") or "")
        company = _norm(r.get("company") or "")

        # 1. Exact normalized substring checks (fast path)
        if slug and slug in msg:
            return r["slug"]
        if domain and domain in msg:
            return r["slug"]
        if company and company in msg:
            return r["slug"]

        # 2. Alias-token matching
        alias_tokens: set = set()

        # Slug without hyphens/underscores
        if slug:
            alias_tokens.add(slug.replace("-", "").replace("_", ""))

        # Domain root: text before first '.'
        if domain:
            domain_root = domain.split(".")[0]
            if domain_root and len(domain_root) >= 4:
                alias_tokens.add(domain_root)

        for token in alias_tokens:
            if len(token) >= 4 and token in msg:
                return r["slug"]

    return None


def _slug_from_session_key(kwargs):
    """Deterministic bind from a Hermes session-key carrying `…:acct:<domain>`.

    The SPA proxy sets X-Hermes-Session-Key = agent:main:prism:rep:<rep>:acct:<domain>,
    which Hermes threads into the hook ctx. Resolving the report by that domain removes
    the reliance on the user's message naming the company. No-op (returns None) if no
    such key is present in ctx — so existing message-match behaviour is unchanged.
    """
    candidates = [v for v in kwargs.values() if isinstance(v, str) and ":acct:" in v]
    for name in ("gateway_session_key", "session_key", "x_hermes_session_key"):
        v = kwargs.get(name)
        if isinstance(v, str) and ":acct:" in v and v not in candidates:
            candidates.append(v)
    for key in candidates:
        domain = key.split(":acct:", 1)[1].strip().lower().split(":")[0]
        if not domain:
            continue
        rows = _load_index()
        for r in rows:                                   # exact domain match
            if (r.get("domain") or "").lower() == domain:
                return r["slug"]
        root = domain.split(".")[0]                       # petsmart.com -> petsmart
        for r in rows:                                    # root match on slug/company
            comp = "".join(ch for ch in (r.get("company") or "").lower() if ch.isalnum())
            if root and (root in (r.get("slug") or "").lower() or (comp and root in comp)):
                return r["slug"]
    return None


def _load_report(slug):
    with open(os.path.join(REPORTS_DIR, slug, "audit-data.json")) as f:
        return f.read()


def _available_list():
    rows = _load_index()
    if not rows:
        return "(no reports available in the store)"
    return "\n".join(f"- {r.get('company')} (say \"{r.get('slug')}\")" for r in rows)


def _gemini_key():
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    try:
        with open(ENV_FILE) as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None


def _retrieve_knowledge(user_message):
    """POST /api/v1/knowledge/retrieve to prism_platform. Fail-open: returns [] on any error."""
    if not httpx or not user_message:
        return []
    try:
        r = httpx.post(
            f"{PLATFORM_URL}/api/v1/knowledge/retrieve",
            json={"query": user_message, "k": 8},
            timeout=5.0,
        )
        if r.status_code != 200:
            return []
        return r.json().get("results", [])
    except Exception:
        return []


def _format_knowledge(results):
    """Format retrieve results into an injectable text block. Returns '' if empty."""
    if not results:
        return ""
    lines = [
        "[Algolia knowledge base — general Algolia facts, products, competitors, case studies, "
        "proof points. These are GENERAL Algolia facts, NOT facts about this specific prospect.]"
    ]
    for item in results:
        text = item.get("text", "")
        sources = item.get("sources", [])
        src_str = " " + " ".join(sources) if sources else ""
        lines.append(f"- {text}{src_str}")
    lines.append("[end Algolia knowledge]")
    return "\n".join(lines)


# ---------------------------------------------------------------- L1: inject report

def inject_report(session_id=None, user_message=None, conversation_history=None, **kwargs):
    # 1. Retrieve Algolia knowledge (best-effort; never breaks chat on failure)
    knowledge_results = _retrieve_knowledge(user_message)
    knowledge_block = _format_knowledge(knowledge_results)

    # Cache the block for the grounding gate this turn; clear if nothing came back
    if knowledge_block:
        _KNOWLEDGE_CACHE[session_id] = knowledge_block
    else:
        _KNOWLEDGE_CACHE.pop(session_id, None)

    # 2. Gap logging: record KB misses so the deferred learner can fill them
    if not knowledge_results and user_message:
        try:
            if httpx:
                httpx.post(
                    f"{PLATFORM_URL}/api/v1/knowledge/gaps",
                    json={
                        "question": user_message,
                        "topic": None,
                        "conversation_id": session_id or "",
                        "why": "kb_miss",
                    },
                    timeout=3.0,
                )
        except Exception:
            pass  # fail-open; gap logging is non-critical

    # 3. Resolve bound slug — ALWAYS check the CURRENT message first so an
    # explicit company mention wins over a stale binding. Sticky-binding bug
    # (2026-07-03): once _BINDINGS[session_id] was set, this block never
    # re-checked the new message, so a session welded to one company (e.g.
    # Brooks Running) stayed welded to it for its entire lifetime — asking
    # about a different company (Belk) kept answering from the old one.
    slug = _match_slug(user_message)
    if not slug:
        slug = _BINDINGS.get(session_id)
    if not slug:
        slug = _slug_from_session_key(kwargs)        # deterministic, key-driven (preferred)
    if not slug and conversation_history:
        # Only the last 5 USER turns — scanning the entire history re-surfaces
        # companies mentioned long ago. This is why a container restart alone
        # didn't fix the stuck-on-Brooks-Running bug: _BINDINGS was empty but
        # conversation_history (persisted in state.db) was not, so the very
        # first post-restart message fell through to an old mention.
        recent_user_msgs = [m.get("content") for m in conversation_history
                             if isinstance(m, dict) and m.get("role") == "user"][-5:]
        for content in reversed(recent_user_msgs):
            slug = _match_slug(content)
            if slug:
                break
    if slug and session_id:
        _BINDINGS[session_id] = slug

    def _with_knowledge(ctx):
        """Prepend the knowledge block to any context string."""
        if knowledge_block:
            return knowledge_block + "\n\n" + ctx
        return ctx

    if not slug:
        return {"context": _with_knowledge(
            "[No audit is bound to this conversation yet. You can't state facts about a specific "
            "prospect until one is loaded, so when it's time, find out which company they want. "
            "Audits available: " + _available_list() + ". How you talk is entirely your own.]")}
    try:
        report_json = _load_report(slug)
    except Exception:
        return {"context": _with_knowledge(
            f"=== PRISM GROUNDING ===\nThe report for '{slug}' could not be loaded. "
            "Tell the user it's unavailable; do not answer from outside knowledge.\n=== END ===")}
    meta = {r["slug"]: r for r in _load_index()}.get(slug, {})
    return {"context": _with_knowledge(GROUNDING_PREAMBLE.format(
        company=meta.get("company", slug),
        domain=meta.get("domain", ""),
        report_json=report_json,
    ))}


# ---------------------------------------------------------------- L4: grounding gate

def _gemini_judge(source_report, source_knowledge, answer):
    if httpx is None:
        raise RuntimeError("httpx unavailable")
    key = _gemini_key()
    if not key:
        raise RuntimeError("no gemini key")
    prompt = JUDGE_PROMPT.format(
        source_report=source_report,
        source_knowledge=source_knowledge or "(no general Algolia knowledge available)",
        answer=answer,
    )
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{JUDGE_MODEL}"
           f":generateContent?key={key}")
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "response_mime_type": "application/json"}}
    r = httpx.post(url, json=body, timeout=45)
    r.raise_for_status()
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


# The final message reaches Telegram (and any non-streaming client), whose Markdown parser mangles
# rich Markdown — backticks become huge monospace blocks, ** shows literally. The SPA does NOT use
# this output (it renders the pre-transform stream itself), so we make the final message clean PLAIN
# text here: remove internal markers AND neutralize Markdown so it reads cleanly on every channel.
_ACCT_RE = re.compile(r"\[Account:[^\]]*\]\s*", re.IGNORECASE)
_CONT_RE = re.compile(r"[ \t]*\[CONTINUATION\b[^\]]*\]", re.IGNORECASE)
_CITE_RE = re.compile(r"[ \t]*\[(?:FACT|ESTIMATE)\b([^\]]*)\]", re.IGNORECASE)
_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
REPORT_BASE = os.environ.get("PRISM_REPORT_BASE", "https://prism.chowmes.com")

# Citation text (source name or JSON path) -> the report section that holds its evidence.
_CITE_MAP = [
    ("section-traffic", re.compile(r"similarweb|traffic|visit|bounce|engagement|session", re.I)),
    ("section-financials", re.compile(r"financ|revenue|ebitda|margin|conversion|aov|gmv", re.I)),
    ("section-techstack", re.compile(r"tech.?stack|search vendor|neuralsearch|search platform|\bibm\b|\bwcs\b|app.?id|constructor|coveo", re.I)),
    ("section-competitive", re.compile(r"competitor|competitive|chewy|amazon|leroy|adeo", re.I)),
    ("section-hiring", re.compile(r"hiring|\bjob\b|\brole\b|headcount|recruit", re.I)),
    ("section-roi", re.compile(r"\broi\b|business case|uplift|payback|opportunity", re.I)),
    ("section-quotes", re.compile(r"quote|earnings", re.I)),
    ("section-signals", re.compile(r"signal|strategic_angle|intelligence_signal|news|leadership|\bcto\b|\bcio\b|\bceo\b|president|hot sale|priorit|mandate", re.I)),
]
_SECTION_LABEL = {
    "section-traffic": "Traffic", "section-financials": "Financials", "section-techstack": "Tech Stack",
    "section-competitive": "Competitors", "section-hiring": "Hiring", "section-roi": "Business Case",
    "section-quotes": "Exec Quotes", "section-signals": "Signals",
}


def _cite_section(body):
    for sid, rx in _CITE_MAP:
        if rx.search(body):
            return sid
    return None


def _clean_for_send(text, slug=None):
    """Flatten Markdown to Telegram-safe text; turn citations into a clickable Evidence footer."""
    if not isinstance(text, str):
        return text
    t = _CONT_RE.sub("", text)
    t = _ACCT_RE.sub("", t)
    t = _CITE_RE.sub("", t)            # drop any inline [FACT]/[ESTIMATE] tags she did emit
    t = re.sub(r"[ \t]{2,}", " ", t)   # tidy double spaces left where a tag was removed
    # code fences + inline code -> keep inner text
    t = re.sub(r"```[a-zA-Z0-9]*\n", "", t)
    t = re.sub(r"```([\s\S]*?)```", r"\1", t)
    t = t.replace("```", "")
    t = re.sub(r"`([^`]*)`", r"\1", t).replace("`", "")
    # links [text](url) -> text (url)
    t = _LINK_RE.sub(r"\1 (\2)", t)
    # bold / italic markers -> plain
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"__([^_]+)__", r"\1", t)
    t = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", t)
    # headings -> plain
    t = re.sub(r"(?m)^[ \t]{0,3}#{1,6}[ \t]*", "", t)
    t = t.replace("**", "")
    # Clickable Evidence footer: the report sections this answer actually discusses (topic match, not
    # dependent on her emitting [FACT]). Bare URLs — Telegram autolinks them. Capped to keep it tight.
    if slug:
        cited = []
        for sid, rx in _CITE_MAP:
            if sid not in cited and rx.search(t):
                cited.append(sid)
        cited = cited[:4]
        if cited:
            links = "\n".join(f"↗ {_SECTION_LABEL.get(sid, sid)}: {REPORT_BASE}/{slug}/#{sid}" for sid in cited)
            t = t.rstrip() + "\n\nEvidence in the report:\n" + links
        # Canned "Try asking..." footer REMOVED (2026-07-03) — it appended the identical four
        # questions to every message regardless of context, reading as a broken record. SOUL.md
        # already instructs her to coach and engage naturally; let her own drafted voice decide
        # what's worth suggesting, in her own words, instead of a bolted-on generic template.
    return t


_RAW_HTML_RE = re.compile(
    r"<!doctype html|<html[\s>]|<title>Sign in|clerk\.accounts\.dev|mountSignIn",
    re.IGNORECASE,
)


def grounding_gate(response_text=None, session_id=None, **kwargs):
    if not response_text:
        return None
    # Hard guard (2026-07-03): a fetch tool call can hit the public Clerk-gated
    # report URL instead of internal data and get a login-page back; nothing
    # downstream validated that before forwarding it verbatim as a chat answer
    # (reproduced live on JBL; same failure class as the lululemon incident in
    # the airtight-pipeline plan, §2.7). Refuse to send anything that looks
    # like raw HTML/a login page, full stop.
    if _RAW_HTML_RE.search(response_text):
        return (
            "Something I tried to pull up came back as a raw web page instead of real "
            "data — I'm not going to forward that. Ask me again and I'll answer from the "
            "audit report directly."
        )
    slug = _BINDINGS.get(session_id)
    if not slug:
        # not report-QA mode; no report to cite, just neutralize any markers/markdown
        cleaned = _clean_for_send(response_text)
        return cleaned if cleaned != response_text else None
    try:
        source_report = _load_report(slug)
    except Exception:
        cleaned = _clean_for_send(response_text, slug)
        return cleaned if cleaned != response_text else None
    source_knowledge = _KNOWLEDGE_CACHE.get(session_id, "")
    try:
        verdict = _gemini_judge(source_report, source_knowledge, response_text)
    except Exception:
        # fail-closed: never silently pass unverified facts
        return (_clean_for_send(response_text, slug) +
                "\n\n_(⚠ Could not verify these details against the audit report — "
                "treat factual specifics with caution.)_")
    if not isinstance(verdict, dict) or verdict.get("verdict") == "PASS":
        cleaned = _clean_for_send(response_text, slug)   # supported -> citations become evidence links
        return cleaned if cleaned != response_text else None
    corrected = verdict.get("corrected")
    if isinstance(corrected, str) and corrected.strip():
        return _clean_for_send(corrected, slug)
    return ("Some details in my draft weren't supported by the audit report, so I held them back. "
            "Ask about specific fields in the report and I'll answer only from it.")


# ---------------------------------------------------------------- L2: executor arm
# Cassandra as executioner. Her container has no claude-cli/skills, so she cannot run
# the audit herself. She calls the host-side prism-runner (loopback, reachable because
# hermes-prism is network_mode:host) which runs run-audit.sh and publishes the result
# into this same report store — so a finished audit auto-appears via _load_index()'s
# mtime cache and she can chat it immediately.
import urllib.request as _urlreq

RUNNER_URL = os.environ.get("PRISM_RUNNER_URL", "http://127.0.0.1:8770")


def _runner_token():
    tok = os.environ.get("PRISM_RUNNER_TOKEN")
    if tok:
        return tok.strip()
    for p in ("/opt/data/.runner-token", "/opt/prism-executor/.runner-token"):
        try:
            with open(p) as f:
                return f.read().strip()
        except Exception:
            pass
    return ""


def _runner_call(method, path, payload=None, timeout=15):
    req = _urlreq.Request(RUNNER_URL + path,
                          data=json.dumps(payload).encode() if payload is not None else None,
                          method=method)
    req.add_header("Content-Type", "application/json")
    tok = _runner_token()
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    with _urlreq.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


RUN_AUDIT_SCHEMA = {
    "name": "run_audit",
    "description": (
        "Kick off an Algolia search audit for a prospect domain on the VPS executor. Use when "
        "the user asks to run / generate / create / start an audit for a company or domain "
        "(e.g. 'run an audit on dell.com', 'audit footlocker.com'). Pass phase or skill (not "
        "both) to run only part of the pipeline instead of the full audit — e.g. 'just re-check "
        "traffic for dell' -> skill='algolia-intel-traffic'. Returns immediately with a job id; "
        "a full audit takes ~10-20 minutes, a single phase/skill is faster. Do NOT use to answer "
        "questions about an existing report, and do NOT use to re-run part of an ALREADY-FINISHED "
        "audit — use rerun for that (this tool starts a fresh workspace scaffold on a full run)."),
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {"type": "string",
                       "description": "Prospect domain or company website, e.g. 'dell.com'."},
            "phase": {"type": "string",
                      "description": "Optional: run only this phase (research|browser|report|"
                                     "factcheck) instead of the full pipeline. Mutually exclusive "
                                     "with skill."},
            "skill": {"type": "string",
                      "description": "Optional: run only this named skill (e.g. "
                                     "'algolia-intel-traffic') instead of the full pipeline. "
                                     "Mutually exclusive with phase."},
        },
        "required": ["domain"],
    },
}

AUDIT_STATUS_SCHEMA = {
    "name": "audit_status",
    "description": (
        "Check the progress of an audit started with run_audit. Pass the job_id you were given, or omit "
        "it to see the most recent job. Use when the user asks 'is the audit done/ready?' or 'how's the "
        "<company> audit going?'."),
    "parameters": {
        "type": "object",
        "properties": {
            "job_id": {"type": "string",
                       "description": "The job id returned by run_audit. Optional; omit for the latest."},
        },
    },
}


def _handle_run_audit(args: dict, **kw) -> str:
    domain = str(args.get("domain") or "").strip()
    if not domain:
        return "I need a domain to audit (for example dell.com)."
    phase = str(args.get("phase") or "").strip()
    skill = str(args.get("skill") or "").strip()
    if phase and skill:
        return "Give me either a phase or a skill to target, not both."
    payload = {"domain": domain}
    if phase:
        payload["phase"] = phase
    if skill:
        payload["skill"] = skill
    try:
        resp = _runner_call("POST", "/run", payload)
    except Exception as e:
        return (f"I couldn't reach the audit runner ({type(e).__name__}). "
                "The executor service may be down; that needs a look before I can start a run.")
    slug = resp.get("slug", "")
    target = ("phase " + phase) if phase else ("skill " + skill)
    scope = f" (scoped to {target})" if (phase or skill) else ""
    return (
        f"Started the audit for {domain}{scope} (job {resp.get('job_id')}). "
        f"Give it a few minutes. Ask me whether the {slug} audit is ready and I'll check.")


# ---------------------------------------------------------------- rerun

RERUN_SCHEMA = {
    "name": "rerun",
    "description": (
        "Re-run ONE phase or skill of an ALREADY-EXISTING audit, without redoing the whole "
        "thing. Use when the user says 're-run just X for Y', 'redo traffic for dell', "
        "'the tech-stack section looks stale, refresh it', or after validate_audit / "
        "list_needs_human surfaces a specific gap that needs fixing. Requires the slug of an "
        "existing audit and exactly one of phase or skill."),
    "parameters": {
        "type": "object",
        "properties": {
            "slug": {"type": "string",
                      "description": "The audit's slug, e.g. 'dell' or 'petsmart'."},
            "phase": {"type": "string",
                      "description": "The phase to re-run (research|browser|report|factcheck). "
                                     "Mutually exclusive with skill."},
            "skill": {"type": "string",
                      "description": "The specific skill to re-run, e.g. "
                                     "'algolia-intel-traffic'. Mutually exclusive with phase."},
        },
        "required": ["slug"],
    },
}


def _handle_rerun(args: dict, **kw) -> str:
    slug = str(args.get("slug") or "").strip()
    if not slug:
        return "Which audit's slug should I re-run part of?"
    phase = str(args.get("phase") or "").strip()
    skill = str(args.get("skill") or "").strip()
    if bool(phase) == bool(skill):
        return "Tell me exactly one of a phase or a skill to re-run, not zero or both."
    payload = {"slug": slug}
    if phase:
        payload["phase"] = phase
    if skill:
        payload["skill"] = skill
    try:
        resp = _runner_call("POST", "/rerun", payload)
    except Exception as e:
        return f"I couldn't reach the audit runner ({type(e).__name__})."
    if "error" in resp:
        return f"Couldn't re-run that: {resp['error']}"
    what = f"phase '{phase}'" if phase else f"skill '{skill}'"
    return (f"Re-running {what} for {slug} (job {resp.get('job_id')}). "
            f"I'll pull the rest of the report from what's already there — only that part updates.")


# ---------------------------------------------------------------- live_status

LIVE_STATUS_SCHEMA = {
    "name": "live_status",
    "description": (
        "Get a GRANULAR status report for an audit — including one that's STILL RUNNING right "
        "now: which phases/skills are done, which is running this moment, what's next, what's "
        "pending, and any module waiting on a human (needs_human). Use whenever the user asks "
        "'status?', 'how's the X audit going?', 'what's happening with Y right now?', or wants "
        "detail beyond a one-line done/not-done answer. Accepts either a job id OR a slug (if a "
        "slug is given, the most recent job for that slug is used)."),
    "parameters": {
        "type": "object",
        "properties": {
            "slug_or_job": {"type": "string",
                             "description": "An audit slug (e.g. 'dell') or a job id "
                                            "(e.g. 'dell-20260702-181234'). If omitted, the "
                                            "most recent job overall is used."},
        },
    },
}


def _resolve_job_id(slug_or_job: str) -> str:
    """A job id always contains a timestamp suffix like -YYYYMMDD-HHMMSS(-rerun-...);
    a bare slug won't. If it looks like a slug, look up its most recent job via /jobs
    (the runner has no separate slug->job index exposed over HTTP, so we scan)."""
    import re as _re
    if _re.search(r"-\d{8}-\d{6}", slug_or_job or ""):
        return slug_or_job
    jobs = _runner_call("GET", "/jobs").get("jobs", [])
    matches = [j for j in jobs if j.get("slug") == slug_or_job]
    if not matches:
        return ""
    matches.sort(key=lambda j: j.get("created", ""))
    return matches[-1].get("job_id", "")


def _handle_live_status(args: dict, **kw) -> str:
    slug_or_job = str(args.get("slug_or_job") or "").strip()
    try:
        if slug_or_job:
            job_id = _resolve_job_id(slug_or_job)
            if not job_id:
                return f"I don't have any job on record for '{slug_or_job}'."
        else:
            jobs = _runner_call("GET", "/jobs").get("jobs", [])
            if not jobs:
                return "No audit jobs have run yet."
            job_id = jobs[-1].get("job_id", "")
        j = _runner_call("GET", "/status/" + job_id)
    except Exception as e:
        return f"I couldn't reach the audit runner ({type(e).__name__})."

    slug = j.get("slug", "?")
    status = j.get("status", "unknown")
    skills = j.get("skills") or {}
    needs_human = j.get("needs_human") or {}
    done = [k for k, v in skills.items() if v == "done"]
    running = [k for k, v in skills.items() if v == "running"]
    pending = [k for k, v in skills.items() if v == "pending"]

    lines = [f"{slug} — status: {status} (phase: {j.get('phase', 'starting')})"]
    if done:
        lines.append(f"Done: {', '.join(done)}")
    if running:
        lines.append(f"Running now: {', '.join(running)}")
    if pending:
        lines.append(f"Pending: {', '.join(pending)}")
    if needs_human:
        blocked = "; ".join(f"{mod} ({why})" for mod, why in needs_human.items())
        lines.append(f"Waiting on a human: {blocked}")
    if status in ("failed", "published_failed"):
        reason = (j.get("publish") or j.get("error") or "").strip()
        if reason:
            lines.append(f"Failure reason: {reason}")
    return "\n".join(lines)


# ---------------------------------------------------------------- validate_audit
#
# NOTE on scope: the airtight plan's runner-side POST /validate {slug} (running
# factcheck_mechanical.py against a finished audit) is Phase-1 scope and was
# NOT part of this build task (which built /run, /rerun, /status, /kill,
# /needs_human, and the DB write path only — see prism-runner.py's docstring).
# This tool is written against that future route so the plugin side is ready
# the moment /validate ships; until then it will 404 and the handler reports
# that honestly rather than pretending success.

VALIDATE_AUDIT_SCHEMA = {
    "name": "validate_audit",
    "description": (
        "Run the mechanical completeness/factcheck gate against a finished audit and report "
        "structured gaps (missing sections, broken sources, render issues). Use when the user "
        "asks to validate, double-check, or spot-check whether an audit's data is solid before "
        "it goes to a prospect."),
    "parameters": {
        "type": "object",
        "properties": {
            "slug": {"type": "string", "description": "The audit's slug, e.g. 'dell'."},
        },
        "required": ["slug"],
    },
}


def _handle_validate_audit(args: dict, **kw) -> str:
    slug = str(args.get("slug") or "").strip()
    if not slug:
        return "Which audit's slug should I validate?"
    try:
        resp = _runner_call("POST", "/validate", {"slug": slug})
    except Exception as e:
        if "404" in str(e) or "HTTPError" in type(e).__name__:
            return ("The runner doesn't have a /validate endpoint deployed yet — that ships in "
                    "a later pipeline upgrade. I can't run the mechanical gate myself.")
        return f"I couldn't reach the audit runner ({type(e).__name__})."
    verdict = resp.get("verdict", "unknown")
    findings = resp.get("findings") or []
    if verdict == "CLEAN" or (verdict == "unknown" and not findings):
        return f"{slug} passes the mechanical gate clean — no completeness or sourcing gaps found."
    lines = [f"{slug} — validation verdict: {verdict}"]
    lines += [f"- {f}" for f in findings[:12]]
    if len(findings) > 12:
        lines.append(f"...and {len(findings) - 12} more.")
    return "\n".join(lines)


# ---------------------------------------------------------------- list_needs_human

LIST_NEEDS_HUMAN_SCHEMA = {
    "name": "list_needs_human",
    "description": (
        "List every audit/section currently waiting on Arijit — e.g. a SimilarWeb login the "
        "traffic module needs, or a job that timed out. Use when asked 'what's waiting on me?', "
        "'anything need my login?', or before starting new work, to surface open blockers."),
    "parameters": {"type": "object", "properties": {}},
}


def _handle_list_needs_human(args: dict, **kw) -> str:
    try:
        resp = _runner_call("GET", "/needs_human")
    except Exception as e:
        return f"I couldn't reach the audit runner ({type(e).__name__})."
    waiting = resp.get("waiting") or []
    if not waiting:
        return ("Nothing's waiting on you right now — every module either finished clean "
                "or hasn't hit a blocker.")
    lines = ["Waiting on you:"]
    for w in waiting:
        blocked = "; ".join(f"{mod} ({why})" for mod, why in (w.get("needs_human") or {}).items())
        lines.append(f"- {w.get('slug')} ({w.get('domain')}): {blocked}")
    return "\n".join(lines)


def _handle_audit_status(args: dict, **kw) -> str:
    job_id = str(args.get("job_id") or "").strip()
    try:
        if not job_id:
            jobs = _runner_call("GET", "/jobs").get("jobs", [])
            if not jobs:
                return "No audit jobs have run yet."
            job_id = jobs[-1].get("job_id", "")
        j = _runner_call("GET", "/status/" + job_id) if job_id else {}
    except Exception as e:
        return f"I couldn't reach the audit runner ({type(e).__name__})."
    st, slug, phase = j.get("status"), j.get("slug"), j.get("phase")
    if st == "done":
        return (f"The {slug} audit is done and published to the report store. Ask me anything about it, "
                f"or say 'tell me about the {slug} audit' and I'll dig in.")
    if st in ("failed", "published_failed"):
        # Surface the runner's own diagnosis (publish/error reason + tail of the run log)
        # instead of a bare status string — this is what lets the LLM actually answer
        # "which skill/layer failed" instead of only "it broke down somewhere."
        reason = (j.get("publish") or j.get("error") or "").strip()
        log_tail = (j.get("log_tail") or "").strip()
        log_snippet = "\n".join(log_tail.splitlines()[-8:]) if log_tail else ""
        msg = f"The {slug} audit did not finish cleanly (status: {st})."
        if reason:
            msg += f" Runner's reason: {reason}."
        if log_snippet:
            msg += f"\n\nLast lines of the run log:\n{log_snippet}"
        msg += "\n\nWant me to retry it?"
        return msg
    return (f"The {slug} audit is still running (phase: {phase or 'starting'}). "
            "Check back in a few minutes.")


_EXEC_TOOLS = (
    ("run_audit", RUN_AUDIT_SCHEMA, _handle_run_audit, "🛰️"),
    ("audit_status", AUDIT_STATUS_SCHEMA, _handle_audit_status, "⏱️"),
    ("rerun", RERUN_SCHEMA, _handle_rerun, "🔁"),
    ("live_status", LIVE_STATUS_SCHEMA, _handle_live_status, "📡"),
    ("validate_audit", VALIDATE_AUDIT_SCHEMA, _handle_validate_audit, "✅"),
    ("list_needs_human", LIST_NEEDS_HUMAN_SCHEMA, _handle_list_needs_human, "🙋"),
)


def register(ctx):
    ctx.register_hook("pre_llm_call", inject_report)
    ctx.register_hook("transform_llm_output", grounding_gate)
    for _name, _schema, _handler, _emoji in _EXEC_TOOLS:
        try:
            ctx.register_tool(name=_name, toolset="prism_audit", schema=_schema,
                              handler=_handler, emoji=_emoji)
        except Exception:
            pass
