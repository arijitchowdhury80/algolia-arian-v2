"""PRISM report-QA plugin — v2 tool ADDITIONS (staged, not deployed).

This is NOT a full rewrite of prism-report-qa/__init__.py (588 lines). It is
the set of new tools + helpers to ADD to that file, following its existing
patterns exactly. Deploy plan: docs/workspace/cassandra-tooling/DEPLOY-PLAN.md
(§ "plugin merge" — paste these blocks in, don't replace the file).

READ RECEIPT (protocol-read-receipt.md) — the exact live code these new tools
conform to:

  live-sources/prism-report-qa__init__.py:478-487, `_runner_call`:
    ```
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
    ```
    -> every new tool below calls the runner through this exact helper,
       unchanged. It already handles auth + JSON encode/decode; nothing new
       needed there.

  live-sources/prism-report-qa__init__.py:580-588, `register()`:
    ```
    def register(ctx):
        ctx.register_hook("pre_llm_call", inject_report)
        ctx.register_hook("transform_llm_output", grounding_gate)
        for _name, _schema, _handler, _emoji in _EXEC_TOOLS:
            try:
                ctx.register_tool(name=_name, toolset="prism_audit", schema=_schema,
                                  handler=_handler, emoji=_emoji)
            except Exception:
                pass
    ```
    -> new tools register the same way: (name, schema, handler, emoji) tuples
       appended to `_EXEC_TOOLS` (or a new `_EXEC_TOOLS_V2` tuple merged into
       it — see "MERGE INSTRUCTIONS" at the bottom), same toolset
       "prism_audit", same try/except-per-tool registration loop.

  live-sources/prism-report-qa__init__.py:490-521, `RUN_AUDIT_SCHEMA` /
  `AUDIT_STATUS_SCHEMA` shape:
    -> new schemas below follow the identical
       {"name", "description", "parameters": {"type": "object", "properties": {...}}}
       shape, same style of "use when the user says X" description text.

  live-sources/prism-report-qa__init__.py:524-538, `_handle_run_audit`:
    -> new handlers follow the identical shape: `def _handle_X(args: dict, **kw) -> str`,
       try/except around every `_runner_call`, plain-English return strings
       (never raw JSON) matching Cassandra's voice-preserving contract
       (grounding_gate cleans/voices whatever these return).

New tools added here (map to the staged runner's new routes — see
docs/workspace/cassandra-tooling/staged/prism-runner.py):
  run_audit(domain, phase?, skill?)   -> POST /run  {domain, phase?, skill?}
  rerun(slug, phase|skill)            -> POST /rerun {slug, phase|skill}
  live_status(slug_or_job)            -> GET  /status/<job_id> (resolves slug->job first)
  validate_audit(slug)                -> POST /validate {slug}  [runner-side gate; see note below]
  list_needs_human()                  -> GET  /needs_human
"""


import contextlib

# The following names are assumed already defined in prism-report-qa/__init__.py
# (imported here only so this file type-checks standalone; DELETE this block
# when pasting into the real file — they already exist there).
with contextlib.suppress(Exception):
    from __init__ import _runner_call


# ---------------------------------------------------------------- run_audit v2
# REPLACES the existing RUN_AUDIT_SCHEMA / _handle_run_audit (live-sources
# lines 490-506, 524-538) — same tool name, same toolset, now accepts optional
# phase/skill. A domain-only call behaves EXACTLY as before (full audit).

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


# ---------------------------------------------------------------- MERGE INSTRUCTIONS
#
# In prism-report-qa/__init__.py:
#   1. Replace RUN_AUDIT_SCHEMA and _handle_run_audit (lines 490-506, 524-538)
#      with the versions above (same tool name "run_audit" — this is an
#      upgrade in place, not a new tool, so no toolset/registration change
#      needed for it).
#   2. Add RERUN_SCHEMA/_handle_rerun, LIVE_STATUS_SCHEMA/_handle_live_status,
#      VALIDATE_AUDIT_SCHEMA/_handle_validate_audit,
#      LIST_NEEDS_HUMAN_SCHEMA/_handle_list_needs_human as new top-level
#      definitions (anywhere after _runner_call is defined).
#   3. Extend _EXEC_TOOLS (line 574-577) from:
#        _EXEC_TOOLS = (
#            ("run_audit", RUN_AUDIT_SCHEMA, _handle_run_audit, "🛰️"),
#            ("audit_status", AUDIT_STATUS_SCHEMA, _handle_audit_status, "⏱️"),
#        )
#      to:
#        _EXEC_TOOLS = (
#            ("run_audit", RUN_AUDIT_SCHEMA, _handle_run_audit, "🛰️"),
#            ("audit_status", AUDIT_STATUS_SCHEMA, _handle_audit_status, "⏱️"),
#            ("rerun", RERUN_SCHEMA, _handle_rerun, "🔁"),
#            ("live_status", LIVE_STATUS_SCHEMA, _handle_live_status, "📡"),
#            ("validate_audit", VALIDATE_AUDIT_SCHEMA, _handle_validate_audit, "✅"),
#            ("list_needs_human", LIST_NEEDS_HUMAN_SCHEMA, _handle_list_needs_human, "🙋"),
#        )
#      `register()` (lines 580-588) needs NO changes — it already iterates
#      _EXEC_TOOLS generically.
