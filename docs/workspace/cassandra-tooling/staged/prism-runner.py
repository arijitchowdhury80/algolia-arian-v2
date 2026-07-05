#!/usr/bin/env python3
"""PRISM audit runner v2 — host-side muscle that lets Cassandra be the executioner.

STAGED, NOT DEPLOYED. This is the v2 upgrade of the live
/opt/prism-executor/prism-runner.py (see docs/workspace/cassandra-tooling/live-sources/
prism-runner.py for the exact code this conforms to / extends). Deploy plan:
docs/workspace/cassandra-tooling/DEPLOY-PLAN.md.

Cassandra (hermes-prism container) cannot run the audit engine herself: her image
has no claude-cli and no skills. This service runs on the HOST (where run-audit.sh +
claude-cli + the skills + live auth are), on loopback. Cass reaches it via
network_mode:host and triggers a run with a single tool call.

READ RECEIPT (protocol-read-receipt.md) — this file conforms to the live runner's
wire format, extending it in a backward-compatible way:
  - live prism-runner.py:46-56 `_now()` / `slugify()` — reused verbatim.
  - live prism-runner.py:78-98 `PHASE_MARKERS` / `detect_phase()` — kept as the
    coarse fallback; a new fine-grained `SKILL_MARKERS` / `detect_skill_states()`
    is layered on top (§ "per-skill status" below), never replacing the fallback.
  - live prism-runner.py:101-157 `publish_to_store()` — kept byte-for-byte as the
    file-publish path; the new `db_write_audit_publish()` is called AFTER it,
    wrapped in try/except so a DB error never breaks the file path (plan §1.4).
  - live prism-runner.py:203-264 `Handler` do_GET/do_POST — same bearer-auth
    (`Authorization: Bearer <TOKEN>`), same `_send()` JSON envelope, same
    202-on-start / 404-on-unknown-route conventions. New routes follow the exact
    same pattern.

Endpoints (loopback only, bearer-gated except /health):
  GET  /health                       -> {"ok": true}
  POST /run     {domain, phase?, skill?, skip?}
                                      -> starts run-audit.sh in the background,
                                         returns job_id. `domain`-only body is
                                         UNCHANGED from v1 (full-run default).
  POST /rerun   {slug, phase|skill}  -> re-run one phase/skill of an existing
                                         audit (looked up by slug from job history).
  GET  /status/<job_id>              -> job state + phase + PER-SKILL map +
                                         needs_human map + log tail.
  GET  /jobs                         -> recent jobs (unchanged).
  POST /kill    {job_id}             -> terminate a running job (SIGTERM then
                                         SIGKILL after a grace period).
  GET  /needs_human                  -> audits/sections currently waiting on a
                                         human (e.g. SimilarWeb login).

DB WRITE PATH (plan §1.4, additive until cutover): on run start + on publish,
this writes to Postgres (`audits` + `module_executions`, schema:
prism_platform/db/models.py) IN ADDITION to the existing file store. Postgres
is meant to become the source of truth; today it is best-effort and FAILS SOFT
— any DB error is logged and swallowed, never raised, never blocks the
file-publish path. Uses plain psycopg2 (not SQLAlchemy) — this script runs
standalone on the host with no app install, matching the rest of this file's
stdlib-only style.

On a successful run it still publishes into Cass's report store so she can chat
it immediately: reports/<slug>/audit-data.json + an index.json entry (unchanged
from v1).

Runs as root (systemd). The audit itself is dropped to chowmesadmin (skills+auth env);
the publish step writes the root-owned store.
"""
import contextlib
import glob
import json
import logging
import os
import re
import signal
import subprocess
import threading
import time
import uuid as _uuid
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    import psycopg2
except Exception:  # pragma: no cover — DB is optional/fail-soft by design
    psycopg2 = None

# Overridable via env for tests/dev sandboxes where /opt and /root aren't
# writable; production leaves these unset and gets the exact live paths.
EXEC_DIR = os.environ.get("PRISM_EXEC_DIR", "/opt/prism-executor")
RUN_AUDIT = os.path.join(EXEC_DIR, "run-audit.sh")
AUDITS_DIR = os.path.join(EXEC_DIR, "audits")
JOBS_DIR = os.path.join(EXEC_DIR, "jobs")
STORE_DIR = os.environ.get("PRISM_STORE_DIR", "/root/.hermes-prism/reports")
INDEX_JSON = os.path.join(STORE_DIR, "index.json")
AUDIT_USER = "chowmesadmin"
PORT = int(os.environ.get("PRISM_RUNNER_PORT", "8770"))
TOKEN = os.environ.get("PRISM_RUNNER_TOKEN", "")

# Local dev default per the Cassandra-tooling build task; production sets
# DATABASE_URL via systemd env (see DEPLOY-PLAN.md).
DEFAULT_DATABASE_URL = "postgresql://prism:localdev@127.0.0.1:55432/prism"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

# Per-job wall-clock timeout — the missing hard-timeout the live runner lacks.
# A job stuck past this is killed and marked NEEDS_HUMAN rather than hanging
# the job slot forever. Overridable via env for tests / tuning.
JOB_TIMEOUT_S = int(os.environ.get("PRISM_JOB_TIMEOUT_S", str(60 * 60)))  # 60 min default
KILL_GRACE_S = float(os.environ.get("PRISM_KILL_GRACE_S", "10"))
POLL_INTERVAL_S = float(os.environ.get("PRISM_POLL_INTERVAL_S", "15"))

with contextlib.suppress(OSError):
    os.makedirs(JOBS_DIR, exist_ok=True)  # non-fatal at import — tests point JOBS_DIR elsewhere

_lock = threading.Lock()
_log = logging.getLogger("prism-runner")


def _now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(domain: str) -> str:
    s = re.sub(r"^https?://", "", domain.strip())
    s = re.sub(r"^www\.", "", s)
    s = s.split("/")[0]
    s = re.sub(r"\.[a-z.]+$", "", s)
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).lower().strip("-")
    return s


def job_path(job_id):
    return os.path.join(JOBS_DIR, f"{job_id}.json")


def write_job(job):
    tmp = job_path(job["job_id"]) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(job, f, indent=1)
    os.replace(tmp, job_path(job["job_id"]))


def read_job(job_id):
    try:
        with open(job_path(job_id)) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def find_latest_job_for_slug(slug):
    """Scan JOBS_DIR for the most recent job matching `slug` (by created ts). Used by
    /rerun and /needs_human to recover a domain / prior state for a slug without a
    separate slug->domain index (the runner has no such index today)."""
    best = None
    for p in sorted(glob.glob(os.path.join(JOBS_DIR, "*.json"))):
        try:
            with open(p) as f:
                job = json.load(f)
        except Exception:
            continue
        is_newer = best is None or job.get("created", "") >= best.get("created", "")
        if job.get("slug") == slug and is_newer:
            best = job
    return best


# --- phase detection from run.log (best-effort progress, coarse fallback) ---
# Unchanged from live prism-runner.py:79-98 — kept as the fallback when a log
# has none of the new fine-grained SKILL_MARKERS (old-format logs, or a run
# that predates this v2).
PHASE_MARKERS = [
    ("wave1", re.compile(r"01-company-context|Wave 1|intel-company", re.I)),
    ("browser", re.compile(r"browser|screenshot|test-quer", re.I)),
    ("report", re.compile(r"audit-data\.json|render-audit|Layer 3", re.I)),
    ("factcheck", re.compile(r"FACTCHECK_GATE|factcheck", re.I)),
    ("done", re.compile(r"DONE ->", re.I)),
]

# --- fine-grained per-skill status (new in v2) ---
# Convention introduced by this v2 (documented in run-audit.sh's prompt): each
# skill invocation logs a `>>> SKILL START: <name>` / `>>> SKILL DONE: <name>`
# marker. This is a NEW logging convention — old logs won't have it, which is
# why detect_phase() above stays as the fallback. Skill names match the
# algolia-intel-* / algolia-audit-* skill catalog.
SKILL_NAMES = (
    "algolia-intel-company", "algolia-intel-techstack", "algolia-intel-traffic",
    "algolia-intel-competitors", "algolia-intel-financial-public",
    "algolia-intel-financial-private", "algolia-intel-investor",
    "algolia-intel-social", "algolia-intel-news", "algolia-intel-hiring",
    "algolia-intel-partner", "algolia-intel-industry", "algolia-intel-queries",
    "algolia-audit-browser", "algolia-audit-report", "algolia-audit-factcheck",
)
_SKILL_START_RE = re.compile(r">>>\s*SKILL START:\s*([a-z0-9-]+)", re.I)
_SKILL_DONE_RE = re.compile(r">>>\s*SKILL DONE:\s*([a-z0-9-]+)", re.I)
_NEEDS_HUMAN_RE = re.compile(r"NEEDS_HUMAN:([a-z0-9_-]+)(?::(.*))?", re.I)

# Maps a NEEDS_HUMAN:<token> marker (what the skill/prompt actually emits) to the
# module name it blocks. "similarweb" is the concrete, locked case (plan §3.2);
# other tokens pass through unchanged so a not-yet-enumerated block still surfaces.
_NEEDS_HUMAN_MODULE_ALIASES = {
    "similarweb": "algolia-intel-traffic",
}


def detect_phase(logfile):
    phase = "starting"
    try:
        with open(logfile, errors="replace") as f:
            tail = f.read()[-8000:]
        for name, rx in PHASE_MARKERS:
            if rx.search(tail):
                phase = name
    except Exception:
        pass
    return phase


def detect_skill_states(logfile):
    """Return {skill_name: 'pending'|'running'|'done'} from START/DONE markers.

    Best-effort log tail-scan (same class of heuristic as detect_phase, just
    finer-grained) — not a structured event stream. A skill with no START
    marker at all is 'pending'; START without DONE is 'running'; both is
    'done'. NEEDS_HUMAN skills are reported separately by detect_needs_human()
    and overridden onto this map by the caller (a needs_human module is not
    truly 'done').
    """
    states = {name: "pending" for name in SKILL_NAMES}
    try:
        with open(logfile, errors="replace") as f:
            text = f.read()
    except Exception:
        return states
    started = {m.group(1).lower() for m in _SKILL_START_RE.finditer(text)}
    done = {m.group(1).lower() for m in _SKILL_DONE_RE.finditer(text)}
    for name in SKILL_NAMES:
        if name in done:
            states[name] = "done"
        elif name in started:
            states[name] = "running"
    return states


def detect_needs_human(logfile):
    """Return {module_name: reason} for every NEEDS_HUMAN:<token>[:<reason>] marker
    seen in the log. This is the SimilarWeb HITL mark-and-continue detector (plan
    §3.2): the run-audit.sh prompt instructs the skill to emit this marker and
    CONTINUE with the rest of the pipeline instead of aborting, so a blocked
    traffic step doesn't kill the whole audit."""
    found = {}
    try:
        with open(logfile, errors="replace") as f:
            text = f.read()
    except Exception:
        return found
    for m in _NEEDS_HUMAN_RE.finditer(text):
        token = m.group(1).lower()
        reason = (m.group(2) or token).strip() or token
        module = _NEEDS_HUMAN_MODULE_ALIASES.get(token, token)
        found[module] = reason
    return found


def publish_to_store(slug):
    """Copy the produced audit-data.json into Cass's store + upsert index.json.
    Returns (ok, detail). UNCHANGED from live prism-runner.py:101-157 — this is
    the file-publish path and stays authoritative regardless of DB outcome."""
    candidates = (
        glob.glob(f"{AUDITS_DIR}/{slug}/**/*audit-data.json", recursive=True)
        + glob.glob(f"{AUDITS_DIR}/{slug}/*audit-data.json")
    )
    candidates = [c for c in candidates if os.path.getsize(c) > 500]
    if not candidates:
        return False, "no audit-data.json produced"
    src = max(candidates, key=os.path.getsize)
    with open(src) as f:
        data = json.load(f)
    dest_dir = os.path.join(STORE_DIR, slug)
    os.makedirs(dest_dir, exist_ok=True)
    with open(os.path.join(dest_dir, "audit-data.json"), "w") as f:
        json.dump(data, f)

    meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
    score_obj = data.get("score", {}) if isinstance(data.get("score"), dict) else {}
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    entry = {
        "slug": slug,
        "company": meta.get("company") or slug,
        "domain": meta.get("domain") or "",
        "audit_date": meta.get("audit_date") or today,
        "status": meta.get("audit_status") or "",
        "score": score_obj.get("overall"),
        "verdict": score_obj.get("verdict") or "",
        "corpus": f"{slug}/audit-data.json",
        "source": "prism-runner (VPS executor)",
        "imported_at": today,
    }
    with _lock:
        try:
            with open(INDEX_JSON) as f:
                idx = json.load(f)
        except FileNotFoundError:
            idx = {"schema": "chowmes-prism report store v1",
                   "store_root": STORE_DIR, "reports": []}
        with contextlib.suppress(FileNotFoundError):
            os.replace(INDEX_JSON, INDEX_JSON + ".bak-" +
                       datetime.now(UTC).strftime("%Y%m%d-%H%M%S"))
        idx["reports"] = [r for r in idx.get("reports", []) if r.get("slug") != slug]
        idx["reports"].append(entry)
        tmp = INDEX_JSON + ".tmp"
        with open(tmp, "w") as f:
            json.dump(idx, f, indent=1)
        os.replace(tmp, INDEX_JSON)
    return True, f"published {slug} (score={entry['score']})", data


# ==========================================================================
# DB WRITE PATH — Postgres as (eventual) source of truth, fail-soft (§1.4)
# ==========================================================================

# audit-data.json top-level key -> the algolia-intel-* / algolia-audit-*
# module that produces it. Verified against a real published audit-data.json
# (top-level keys read 2026-07-02: meta, cover, score, company_snapshot,
# executives, intelligence_signals, competitors, findings, gap_pairs,
# financials, traffic, tech_stack, ..., hiring, ..., industry_context,
# partner_intel, ...). Not every module maps 1:1 to a section (e.g. queries/
# browser/factcheck don't own a top-level data section) — those are recorded
# with output_json=None, status derived from needs_human/skill-state only.
MODULE_SECTION_MAP = {
    "algolia-intel-company": "company_snapshot",
    "algolia-intel-techstack": "tech_stack",
    "algolia-intel-traffic": "traffic",
    "algolia-intel-competitors": "competitors",
    "algolia-intel-financial-public": "financials",
    "algolia-intel-financial-private": "financials",
    "algolia-intel-investor": "intelligence_signals",
    "algolia-intel-social": "intelligence_signals",
    "algolia-intel-news": "intelligence_signals",
    "algolia-intel-hiring": "hiring",
    "algolia-intel-partner": "partner_intel",
    "algolia-intel-industry": "industry_context",
    "algolia-intel-queries": None,
    "algolia-audit-browser": "findings",
    "algolia-audit-report": None,
    "algolia-audit-factcheck": None,
}


def _log_db_error(where, exc):
    _log.warning("DB write failed (fail-soft, file path unaffected) at %s: %r", where, exc)


def db_connect(dsn=None):
    if psycopg2 is None:
        raise RuntimeError("psycopg2 not installed")
    return psycopg2.connect(dsn or DATABASE_URL)


def db_get_or_create_account(conn, domain, company_name):
    domain = (domain or "").strip().lower()
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM accounts WHERE domain = %s", (domain,))
        row = cur.fetchone()
        if row:
            return row[0]
        acct_id = str(_uuid.uuid4())
        cur.execute(
            "INSERT INTO accounts (id, company_name, domain) VALUES (%s, %s, %s)",
            (acct_id, company_name or domain, domain),
        )
        return acct_id


def db_write_audit_start(job):
    """Fail-soft: insert an audits row (status='running') when a job starts.
    Returns the new audit_id (str) on success, or None on ANY failure — never
    raises. Callers must not depend on this succeeding."""
    conn = None
    try:
        conn = db_connect()
        with conn:
            account_id = db_get_or_create_account(conn, job.get("domain", ""), job.get("slug", ""))
            audit_id = str(_uuid.uuid4())
            config = {
                "job_id": job["job_id"],
                "phase": job.get("phase"),
                "skill": job.get("skill"),
                "skip": job.get("skip"),
                "rerun_of": job.get("rerun_of"),
            }
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO audits (id, account_id, user_id, status, config, started_at) "
                    "VALUES (%s, %s, %s, %s, %s, now())",
                    (audit_id, account_id, "cassandra", "running", json.dumps(config)),
                )
        return audit_id
    except Exception as exc:
        _log_db_error("db_write_audit_start", exc)
        return None
    finally:
        if conn is not None:
            with __import__("contextlib").suppress(Exception):
                conn.close()


def db_write_audit_publish(job, slug, audit_data, needs_human=None):
    """Fail-soft: upsert the audits row to status='completed' with the full
    audit_data JSONB blob + score, and upsert one module_executions row per
    known module (needs_human status for any module flagged blocked). Returns
    a dict {"ok": bool, ...} — NEVER raises. This is additive: a DB error here
    must not affect the file-publish path, which the caller already
    completed before calling this."""
    conn = None
    try:
        conn = db_connect()
        meta = audit_data.get("meta") or {}
        domain = (meta.get("domain") or job.get("domain") or "").strip().lower()
        company = meta.get("company") or slug
        score = (audit_data.get("score") or {}).get("overall")
        needs_human = needs_human or {}

        with conn:
            account_id = db_get_or_create_account(conn, domain, company)
            audit_id = job.get("_db_audit_id")
            with conn.cursor() as cur:
                if audit_id:
                    cur.execute(
                        "UPDATE audits SET status=%s, score=%s, audit_data=%s, "
                        "completed_at=now() WHERE id=%s",
                        ("completed", score, json.dumps(audit_data), audit_id),
                    )
                    if cur.rowcount == 0:
                        audit_id = None
                if not audit_id:
                    audit_id = str(_uuid.uuid4())
                    cur.execute(
                        "INSERT INTO audits (id, account_id, user_id, status, score, "
                        "audit_data, started_at, completed_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s, now(), now())",
                        (audit_id, account_id, "cassandra", "completed", score,
                         json.dumps(audit_data)),
                    )
                for module_name, section_key in MODULE_SECTION_MAP.items():
                    reason = needs_human.get(module_name)
                    status = "needs_human" if reason else "completed"
                    output = audit_data.get(section_key) if section_key else None
                    cur.execute(
                        "INSERT INTO module_executions "
                        "(id, audit_id, domain, module_name, module_version, status, "
                        "output_json, error_message, completed_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now()) "
                        "ON CONFLICT (audit_id, module_name) DO UPDATE SET "
                        "status=EXCLUDED.status, output_json=EXCLUDED.output_json, "
                        "error_message=EXCLUDED.error_message, completed_at=now()",
                        (str(_uuid.uuid4()), audit_id, domain, module_name, "v1", status,
                         json.dumps(output) if output is not None else None, reason),
                    )
        return {"ok": True, "audit_id": audit_id}
    except Exception as exc:
        _log_db_error("db_write_audit_publish", exc)
        return {"ok": False, "reason": repr(exc)}
    finally:
        if conn is not None:
            with __import__("contextlib").suppress(Exception):
                conn.close()


# ==========================================================================
# Job execution
# ==========================================================================

def build_audit_cmd(job):
    """Build the run-audit.sh argv for this job. `domain`-only jobs (v1
    behaviour) get exactly the v1 argv (positional domain, nothing else) so
    v1 callers are unaffected. phase/skill/skip thread through as flags that
    staged/run-audit.sh v2 parses; a legacy (v1) run-audit.sh on disk simply
    ignores trailing args it doesn't recognise... which is NOT safe to assume,
    so this runner only adds the flags when they're actually requested."""
    cmd = ["sudo", "-u", AUDIT_USER, "bash", RUN_AUDIT, job["domain"]]
    if job.get("phase"):
        cmd += ["--phase", job["phase"]]
    if job.get("skill"):
        cmd += ["--skill", job["skill"]]
    if job.get("skip"):
        cmd += ["--skip", job["skip"]]
    return cmd


def run_job(job, popen_fn=subprocess.Popen, sleep_fn=time.sleep, clock_fn=time.monotonic,
            poll_interval_s=POLL_INTERVAL_S, timeout_s=JOB_TIMEOUT_S):
    """Run one audit job to completion (or timeout/kill). Dependency-injected
    (popen_fn/sleep_fn/clock_fn) so tests never spawn a real subprocess or
    sleep real wall-clock time — same DI shape as prism_platform/pipeline/self_heal.py
    in this repo."""
    # Build the command line from the REQUESTED phase/skill/skip BEFORE anything
    # below overwrites job["phase"] for progress-tracking. job["phase"] is reused
    # as both "the phase the caller asked to run" (input) and "which phase the
    # job is currently at" (runtime status, written by detect_phase() polling) —
    # building the cmd late read the clobbered status value instead of the
    # request, so every real (non-dry) audit sent literally "--phase starting"
    # to run-audit.sh and was rejected by its own arg validation. Found live via
    # the Belk acceptance test, 2026-07-03 — the dry-run path never exercises
    # this line, which is why testing this deploy with dry:true never caught it.
    cmd = build_audit_cmd(job)

    job["status"] = "running"
    job["phase"] = "starting"
    write_job(job)
    logfile = os.path.join(JOBS_DIR, f"{job['job_id']}.log")
    job["logfile"] = logfile
    write_job(job)

    if not job.get("dry"):
        job["_db_audit_id"] = db_write_audit_start(job)
        write_job(job)

    dry = job.get("dry")
    deadline = clock_fn() + timeout_s if timeout_s else None
    try:
        if dry:
            with open(logfile, "w") as lf:
                lf.write("DRY RUN — skipping real audit\nDONE ->\n")
            rc = 0
        else:
            with open(logfile, "w") as lf:
                proc = popen_fn(cmd, stdout=lf, stderr=subprocess.STDOUT,
                                 cwd=EXEC_DIR)
                job["pid"] = proc.pid
                write_job(job)
                killed_for_timeout = False
                while proc.poll() is None:
                    sleep_fn(poll_interval_s)
                    job["phase"] = detect_phase(logfile)
                    job["skills"] = detect_skill_states(logfile)
                    job["needs_human"] = detect_needs_human(logfile)
                    write_job(job)
                    if deadline is not None and clock_fn() >= deadline:
                        killed_for_timeout = True
                        _terminate(proc, sleep_fn)
                        break
                rc = proc.returncode if proc.returncode is not None else -9
                if killed_for_timeout:
                    job["status"] = "needs_human"
                    job["needs_human"] = dict(job.get("needs_human") or {},
                                               _job=f"wall-clock timeout after {timeout_s}s")
                    job["rc"] = rc
                    job["finished"] = _now()
                    write_job(job)
                    return
        job["rc"] = rc
        if rc == 0:
            job["skills"] = detect_skill_states(logfile)
            job["needs_human"] = detect_needs_human(logfile)
            if dry:
                ok, detail, data = True, "dry", {}
            else:
                published = publish_to_store(job["slug"])
                ok, detail = published[0], published[1]
                data = published[2] if ok and len(published) > 2 else {}
            job["status"] = "done" if ok else "published_failed"
            job["publish"] = detail
            job["phase"] = "done"
            if ok and not dry:
                db_result = db_write_audit_publish(job, job["slug"], data,
                                                    needs_human=job.get("needs_human"))
                job["db_publish"] = db_result
        else:
            job["status"] = "failed"
        job["finished"] = _now()
    except Exception as e:
        job["status"] = "failed"
        job["error"] = repr(e)
        job["finished"] = _now()
    write_job(job)


def _terminate(proc, sleep_fn=time.sleep, grace_s=KILL_GRACE_S):
    """SIGTERM, wait a grace period, then SIGKILL if still alive. Same
    escalation used by POST /kill (kill_job below) — factored out so both
    paths (operator-requested kill, timeout-triggered kill) behave
    identically."""
    with contextlib.suppress(Exception):
        proc.terminate()
    waited = 0.0
    step = min(1.0, grace_s) or 1.0
    while proc.poll() is None and waited < grace_s:
        sleep_fn(step)
        waited += step
    if proc.poll() is None:
        with contextlib.suppress(Exception):
            proc.kill()


def kill_job(job_id, sleep_fn=time.sleep):
    """POST /kill handler logic. Returns (code, obj). Sends SIGTERM to the
    job's recorded pid, escalates to SIGKILL after KILL_GRACE_S if it's still
    alive, and marks the job 'killed'. A job with no live pid (already
    finished, or pid unknown) is a no-op 409, not an error — killing a
    finished job is a caller mistake, not a runner fault."""
    job = read_job(job_id)
    if not job:
        return 404, {"error": "no such job"}
    pid = job.get("pid")
    if not pid or job.get("status") not in ("running", "queued"):
        return 409, {"error": "job not running", "status": job.get("status")}
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except Exception as e:
        return 500, {"error": f"kill failed: {e!r}"}
    waited = 0.0
    step = min(1.0, KILL_GRACE_S) or 1.0
    while waited < KILL_GRACE_S:
        try:
            os.kill(pid, 0)  # probe: raises ProcessLookupError once dead
        except ProcessLookupError:
            break
        except Exception:
            break
        sleep_fn(step)
        waited += step
    else:
        with __import__("contextlib").suppress(Exception):
            os.kill(pid, signal.SIGKILL)
    job["status"] = "killed"
    job["finished"] = _now()
    write_job(job)
    return 200, {"job_id": job_id, "status": "killed"}


# ==========================================================================
# Route logic (pure functions — the HTTP Handler below is a thin adapter over
# these, matching the live Handler's do_GET/do_POST shape but decomposed for
# testability without spinning a real server).
# ==========================================================================

def handle_run(body):
    """POST /run. `{domain}`-only body is byte-identical in behaviour to v1.
    `phase`/`skill`/`skip` are new, optional, and threaded into the job +
    the run-audit.sh argv (build_audit_cmd)."""
    domain = (body.get("domain") or "").strip()
    if not domain:
        return 400, {"error": "domain required"}
    slug = slugify(domain)
    job_id = f"{slug}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    job = {
        "job_id": job_id, "domain": domain, "slug": slug,
        "status": "queued", "created": _now(), "dry": bool(body.get("dry")),
    }
    for k in ("phase", "skill", "skip"):
        v = body.get(k)
        if v:
            job[k] = str(v).strip()
    write_job(job)
    threading.Thread(target=run_job, args=(job,), daemon=True).start()
    return 202, {"job_id": job_id, "slug": slug, "status": "started",
                 "note": "audit runs ~10-20 min; poll /status/<job_id>"}


def handle_rerun(body):
    """POST /rerun {slug, phase|skill}. Looks up the domain for `slug` from
    job history (find_latest_job_for_slug — the runner has no separate
    slug->domain index) and re-dispatches scoped to just that phase/skill.
    Requires exactly one of phase/skill (a rerun with neither is just a full
    /run and should use that route instead; a rerun with both is ambiguous)."""
    slug = (body.get("slug") or "").strip()
    phase = (body.get("phase") or "").strip()
    skill = (body.get("skill") or "").strip()
    if not slug:
        return 400, {"error": "slug required"}
    if bool(phase) == bool(skill):
        return 400, {"error": "exactly one of phase or skill required"}
    prior = find_latest_job_for_slug(slug)
    if not prior or not prior.get("domain"):
        return 404, {"error": f"no prior job found for slug '{slug}' (unknown domain)"}
    domain = prior["domain"]
    job_id = f"{slug}-rerun-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    job = {
        "job_id": job_id, "domain": domain, "slug": slug,
        "status": "queued", "created": _now(), "dry": bool(body.get("dry")),
        "rerun_of": prior.get("job_id"),
    }
    if phase:
        job["phase"] = phase
    if skill:
        job["skill"] = skill
    write_job(job)
    threading.Thread(target=run_job, args=(job,), daemon=True).start()
    return 202, {"job_id": job_id, "slug": slug, "status": "started",
                 "rerun_of": prior.get("job_id"),
                 "note": f"re-running {'phase ' + phase if phase else 'skill ' + skill} for {slug}"}


def handle_status(job_id):
    """GET /status/<job_id>. Extends v1 with `skills` (per-skill map) and
    `needs_human` (module -> reason), both re-derived from the live logfile
    on every call so a still-running job's status reflects real-time progress
    (Arijit's "look into the pipeline and report" ask)."""
    job = read_job(job_id)
    if not job:
        return 404, {"error": "no such job"}
    lf = job.get("logfile")
    out = dict(job)
    if lf and os.path.exists(lf):
        with open(lf, errors="replace") as f:
            out["log_tail"] = "".join(f.readlines()[-15:])
        # re-derive live state on every status call, not just what run_job last wrote —
        # a concurrent GET while the job thread is mid-poll-sleep still sees fresh state.
        out["skills"] = detect_skill_states(lf)
        out["needs_human"] = detect_needs_human(lf)
    return 200, out


def handle_kill(body, sleep_fn=time.sleep):
    job_id = (body.get("job_id") or "").strip()
    if not job_id:
        return 400, {"error": "job_id required"}
    return kill_job(job_id, sleep_fn=sleep_fn)


def handle_needs_human():
    """GET /needs_human — every job currently carrying a needs_human module,
    across all recent jobs (not just the latest), so Arijit/Cassandra can see
    everything waiting on him at a glance."""
    out = []
    for p in sorted(glob.glob(os.path.join(JOBS_DIR, "*.json"))):
        try:
            with open(p) as f:
                job = json.load(f)
        except Exception:
            continue
        nh = job.get("needs_human") or {}
        if nh:
            out.append({"job_id": job.get("job_id"), "slug": job.get("slug"),
                        "domain": job.get("domain"), "status": job.get("status"),
                        "needs_human": nh})
    return 200, {"waiting": out}


def handle_jobs():
    jobs = []
    for p in sorted(glob.glob(os.path.join(JOBS_DIR, "*.json")))[-20:]:
        with contextlib.suppress(Exception), open(p) as f:
            jobs.append(json.load(f))
    return 200, {"jobs": jobs}


# ==========================================================================
# HTTP adapter (thin — delegates to the route functions above)
# ==========================================================================

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _auth_ok(self):
        if not TOKEN:
            return True
        return self.headers.get("Authorization", "") == f"Bearer {TOKEN}"

    def log_message(self, *a):
        pass

    def _read_body(self):
        n = int(self.headers.get("Content-Length", "0"))
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return None

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"ok": True, "service": "prism-runner", "port": PORT})
        if not self._auth_ok():
            return self._send(401, {"error": "unauthorized"})
        if self.path == "/jobs":
            return self._send(*handle_jobs())
        if self.path == "/needs_human":
            return self._send(*handle_needs_human())
        if self.path.startswith("/status/"):
            return self._send(*handle_status(self.path.split("/status/", 1)[1]))
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._auth_ok():
            return self._send(401, {"error": "unauthorized"})
        body = self._read_body()
        if body is None:
            return self._send(400, {"error": "bad json"})
        if self.path == "/run":
            return self._send(*handle_run(body))
        if self.path == "/rerun":
            return self._send(*handle_rerun(body))
        if self.path == "/kill":
            return self._send(*handle_kill(body))
        return self._send(404, {"error": "not found"})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"prism-runner listening on 127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
