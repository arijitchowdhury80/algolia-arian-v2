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
facts intact>"}}

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
         - each normalized company word with len>=5 not in _STOPWORDS
           (>=5 avoids false positives from generic 4-letter words like "home")
       Any token with len>=4 found as a substring in the normalized message → match.
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

        # Company words: require >=5 chars to avoid short generic words ("home", "shop")
        for word in company.split():
            word_alnum = "".join(ch for ch in word if ch.isalnum())
            if len(word_alnum) >= 5 and word_alnum not in _STOPWORDS:
                alias_tokens.add(word_alnum)

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

    # 3. Resolve bound slug (unchanged logic from production)
    slug = _BINDINGS.get(session_id)
    if not slug:
        slug = _slug_from_session_key(kwargs)        # deterministic, key-driven (preferred)
    if not slug:
        slug = _match_slug(user_message)
        if not slug and conversation_history:
            for m in reversed(conversation_history):
                if isinstance(m, dict) and m.get("role") == "user":
                    slug = _match_slug(m.get("content"))
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
        # Suggested follow-ups (Telegram can't render tappable buttons from this hook; text prompts).
        if cited or len(t) > 180:
            t = t.rstrip() + ("\n\nTry asking: What are the biggest gaps? · What's the ROI opportunity? · "
                              "Who are their competitors? · How should I open the call?")
    return t


def grounding_gate(response_text=None, session_id=None, **kwargs):
    if not response_text:
        return None
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
        "Kick off a NEW Algolia search audit for a prospect domain on the VPS executor. Use when the "
        "user asks to run / generate / create / start an audit for a company or domain (e.g. 'run an "
        "audit on dell.com', 'audit footlocker.com', 'can you audit Torrid?'). Returns immediately with "
        "a job id; the audit itself takes ~10-20 minutes (research, live search testing, scoring, "
        "factcheck, publish). Do NOT use to answer questions about an existing report."),
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {"type": "string",
                       "description": "Prospect domain or company website, e.g. 'dell.com'."},
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
    try:
        resp = _runner_call("POST", "/run", {"domain": domain})
    except Exception as e:
        return (f"I couldn't reach the audit runner ({type(e).__name__}). The executor service may be "
                "down; that needs a look before I can start a run.")
    slug = resp.get("slug", "")
    return (
        f"Started the audit for {domain} (job {resp.get('job_id')}). It runs end to end on the box: "
        "research, live search testing, scoring, then a factcheck gate, then publish. Give it about 10 "
        f"to 20 minutes. Ask me whether the {slug} audit is ready and I'll check. The moment it passes "
        "factcheck it lands in the report store and I can walk you through the findings.")


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
