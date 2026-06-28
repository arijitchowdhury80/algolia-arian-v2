"""PRISM report-QA — ground every answer in ONE bound audit report.

Two hooks, one plugin (shared binding state):
  L1 pre_llm_call      -> inject the bound company's audit-data.json each turn.
  L4 transform_llm_output -> a Gemini grounding judge verifies FACTUAL claims in the
                            drafted answer against the report and REWRITES unsupported
                            ones before the message is sent (the hard gate).

Decided scope: FACTS about the prospect must be report-supported; COACHING (hypotheses,
F1-F6/M1-M10 moves, objection handling, call plans) is allowed and is NOT policed.
Report binding is detected from the conversation and held per session_id.
"""

import json
import os

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None

REPORTS_DIR = os.environ.get("PRISM_REPORTS_DIR", "/opt/data/reports")
ENV_FILE = os.environ.get("PRISM_ENV_FILE", "/opt/data/.env")
JUDGE_MODEL = os.environ.get("PRISM_JUDGE_MODEL", "gemini-2.5-flash")

_BINDINGS: dict = {}                       # session_id -> slug
_INDEX_CACHE = {"mtime": 0.0, "rows": []}

GROUNDING_PREAMBLE = """\
=== PRISM AUDIT REPORT — SOLE SOURCE OF FACTS ===
You are answering about {company} ({domain}). The JSON below is the COMPLETE audit
report and your ONLY source of FACTS about this prospect.

RULES:
- FACTUAL claims (numbers, scores, search vendor, findings, financials, competitors)
  MUST come from this report. Never use outside/general knowledge for facts.
- If a fact is not in the report, reply exactly: "That's not in the audit report."
- You MAY coach (calibrated hypotheses, F1-F6 / M1-M10 moves, objection handling, call
  plans) — but every coaching point must anchor to a fact cited from this report.
- Never invent a number, a source, or a finding.

AUDIT REPORT JSON:
{report_json}
=== END AUDIT REPORT ==="""

JUDGE_PROMPT = """You are a STRICT grounding verifier for a sales-intelligence assistant.

SOURCE = the complete audit report (JSON) for a prospect; the ONLY allowed source of FACTS.
ANSWER = a drafted reply.

Find every FACTUAL claim about the prospect in ANSWER (specific numbers, percentages, scores,
the search vendor, named findings, financial figures, dates, people/competitor names). For each,
decide if it is DIRECTLY supported by SOURCE.
- IGNORE coaching/advice/hypotheses/sales-methodology/opening-moves/objection-handling — those are
  NOT factual claims; never flag them.
- A factual claim is "unsupported" if its value/wording is absent from or contradicts SOURCE.

Return ONLY minified JSON, no prose:
{{"verdict":"PASS" or "FAIL","unsupported":["<short claim>",...],"corrected":"<ANSWER rewritten so each
unsupported factual claim is removed or replaced with the correct value from SOURCE (or with '(not in
the audit report)'); keep ALL coaching and ALL supported facts intact>"}}

SOURCE:
{source}

ANSWER:
{answer}"""


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
    if not text:
        return None
    t = text.lower()
    t_compact = "".join(ch for ch in t if ch.isalnum())
    for r in _load_index():
        slug = (r.get("slug") or "").lower()
        domain = (r.get("domain") or "").lower()
        company = (r.get("company") or "").lower()
        if slug and slug in t:
            return r["slug"]
        if domain and domain in t:
            return r["slug"]
        if company and company in t:
            return r["slug"]
        comp_compact = "".join(ch for ch in company if ch.isalnum())
        if comp_compact and len(comp_compact) >= 4 and comp_compact in t_compact:
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


# ---------------------------------------------------------------- L1: inject report
def inject_report(session_id=None, user_message=None, conversation_history=None, **kwargs):
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

    if not slug:
        return {"context": (
            "=== PRISM GROUNDING ===\n"
            "No audit report is bound to this conversation. You can ONLY answer from a bound audit "
            "report — do not use outside knowledge. Ask which company, then answer only from that "
            "report. Available reports:\n" + _available_list() + "\n=== END ===")}
    try:
        report_json = _load_report(slug)
    except Exception:
        return {"context": (f"=== PRISM GROUNDING ===\nThe report for '{slug}' could not be loaded. "
                            "Tell the user it's unavailable; do not answer from outside knowledge.\n=== END ===")}
    meta = {r["slug"]: r for r in _load_index()}.get(slug, {})
    return {"context": GROUNDING_PREAMBLE.format(
        company=meta.get("company", slug), domain=meta.get("domain", ""), report_json=report_json)}


# ---------------------------------------------------------------- L4: grounding gate
def _gemini_judge(source_json, answer):
    if httpx is None:
        raise RuntimeError("httpx unavailable")
    key = _gemini_key()
    if not key:
        raise RuntimeError("no gemini key")
    prompt = JUDGE_PROMPT.format(source=source_json, answer=answer)
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{JUDGE_MODEL}"
           f":generateContent?key={key}")
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "response_mime_type": "application/json"}}
    r = httpx.post(url, json=body, timeout=45)
    r.raise_for_status()
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def grounding_gate(response_text=None, session_id=None, **kwargs):
    if not response_text:
        return None
    slug = _BINDINGS.get(session_id)
    if not slug:
        return None                          # not report-QA mode; leave unchanged
    try:
        source = _load_report(slug)
    except Exception:
        return None
    try:
        verdict = _gemini_judge(source, response_text)
    except Exception:
        # fail-closed: never silently pass unverified facts
        return (response_text +
                "\n\n_(⚠ Could not verify these details against the audit report — "
                "treat factual specifics with caution.)_")
    if not isinstance(verdict, dict) or verdict.get("verdict") == "PASS":
        return None                          # supported -> unchanged
    corrected = verdict.get("corrected")
    if isinstance(corrected, str) and corrected.strip():
        return corrected
    return ("Some details in my draft weren't supported by the audit report, so I held them back. "
            "Ask about specific fields in the report and I'll answer only from it.")


def register(ctx):
    ctx.register_hook("pre_llm_call", inject_report)
    ctx.register_hook("transform_llm_output", grounding_gate)
