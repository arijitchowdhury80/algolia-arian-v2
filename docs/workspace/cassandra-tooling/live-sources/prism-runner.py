#!/usr/bin/env python3
"""PRISM audit runner — host-side muscle that lets Cassandra be the executioner.

Cassandra (hermes-prism container) cannot run the audit engine herself: her image
has no claude-cli and no skills. This service runs on the HOST (where run-audit.sh +
claude-cli + the 22 skills + live auth are), on loopback. Cass reaches it via
network_mode:host and triggers a run with a single tool call.

Endpoints (loopback only, bearer-gated):
  GET  /health                 -> {"ok": true}
  POST /run     {domain}       -> starts run-audit.sh in the background, returns job_id
  GET  /status/<job_id>        -> job state + phase + log tail
  GET  /jobs                   -> recent jobs

On a successful run it publishes into Cass's report store so she can chat it
immediately:  reports/<slug>/audit-data.json  + an index.json entry.

Runs as root (systemd). The audit itself is dropped to chowmesadmin (skills+auth env);
the publish step writes the root-owned store.
"""
import json
import os
import re
import subprocess
import threading
import time
import glob
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EXEC_DIR = "/opt/prism-executor"
RUN_AUDIT = os.path.join(EXEC_DIR, "run-audit.sh")
AUDITS_DIR = os.path.join(EXEC_DIR, "audits")
JOBS_DIR = os.path.join(EXEC_DIR, "jobs")
STORE_DIR = "/root/.hermes-prism/reports"
INDEX_JSON = os.path.join(STORE_DIR, "index.json")
AUDIT_USER = "chowmesadmin"
PORT = int(os.environ.get("PRISM_RUNNER_PORT", "8770"))
TOKEN = os.environ.get("PRISM_RUNNER_TOKEN", "")

os.makedirs(JOBS_DIR, exist_ok=True)

_lock = threading.Lock()


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


# --- phase detection from run.log (best-effort progress) ---
PHASE_MARKERS = [
    ("wave1", re.compile(r"01-company-context|Wave 1|intel-company", re.I)),
    ("browser", re.compile(r"browser|screenshot|test-quer", re.I)),
    ("report", re.compile(r"audit-data\.json|render-audit|Layer 3", re.I)),
    ("factcheck", re.compile(r"FACTCHECK_GATE|factcheck", re.I)),
    ("done", re.compile(r"DONE ->", re.I)),
]


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


def publish_to_store(slug):
    """Copy the produced audit-data.json into Cass's store + upsert index.json.
    Returns (ok, detail)."""
    # find the produced audit-data.json under the audit workspace
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

    # upsert index.json entry — mirror the store's flat schema exactly.
    # Real audit-data.json shape: meta.{company,domain,audit_date,audit_status},
    # score.{overall,verdict}. (Verified against the live store, not guessed.)
    meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
    score_obj = data.get("score", {}) if isinstance(data.get("score"), dict) else {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
        # backup then upsert
        try:
            os.replace(INDEX_JSON, INDEX_JSON + ".bak-" +
                       datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
        except FileNotFoundError:
            pass
        idx["reports"] = [r for r in idx.get("reports", []) if r.get("slug") != slug]
        idx["reports"].append(entry)
        tmp = INDEX_JSON + ".tmp"
        with open(tmp, "w") as f:
            json.dump(idx, f, indent=1)
        os.replace(tmp, INDEX_JSON)
    return True, f"published {slug} (score={entry['score']})"


def run_job(job):
    job["status"] = "running"
    job["phase"] = "starting"
    write_job(job)
    logfile = os.path.join(JOBS_DIR, f"{job['job_id']}.log")
    job["logfile"] = logfile
    write_job(job)
    dry = job.get("dry")
    try:
        if dry:
            with open(logfile, "w") as lf:
                lf.write("DRY RUN — skipping real audit\nDONE ->\n")
            rc = 0
        else:
            with open(logfile, "w") as lf:
                proc = subprocess.Popen(
                    ["sudo", "-u", AUDIT_USER, "bash", RUN_AUDIT, job["domain"]],
                    stdout=lf, stderr=subprocess.STDOUT, cwd=EXEC_DIR,
                )
                job["pid"] = proc.pid
                write_job(job)
                # poll for phase while running
                while proc.poll() is None:
                    time.sleep(15)
                    job["phase"] = detect_phase(logfile)
                    write_job(job)
                rc = proc.returncode
        job["rc"] = rc
        if rc == 0:
            ok, detail = (True, "dry") if dry else publish_to_store(job["slug"])
            job["status"] = "done" if ok else "published_failed"
            job["publish"] = detail
            job["phase"] = "done"
        else:
            job["status"] = "failed"
        job["finished"] = _now()
    except Exception as e:
        job["status"] = "failed"
        job["error"] = repr(e)
        job["finished"] = _now()
    write_job(job)


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

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"ok": True, "service": "prism-runner", "port": PORT})
        if not self._auth_ok():
            return self._send(401, {"error": "unauthorized"})
        if self.path == "/jobs":
            jobs = []
            for p in sorted(glob.glob(os.path.join(JOBS_DIR, "*.json")))[-20:]:
                try:
                    jobs.append(json.load(open(p)))
                except Exception:
                    pass
            return self._send(200, {"jobs": jobs})
        if self.path.startswith("/status/"):
            job = read_job(self.path.split("/status/", 1)[1])
            if not job:
                return self._send(404, {"error": "no such job"})
            lf = job.get("logfile")
            if lf and os.path.exists(lf):
                with open(lf, errors="replace") as f:
                    job = dict(job, log_tail="".join(f.readlines()[-15:]))
            return self._send(200, job)
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._auth_ok():
            return self._send(401, {"error": "unauthorized"})
        if self.path != "/run":
            return self._send(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, {"error": "bad json"})
        domain = (body.get("domain") or "").strip()
        if not domain:
            return self._send(400, {"error": "domain required"})
        slug = slugify(domain)
        job_id = f"{slug}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        job = {"job_id": job_id, "domain": domain, "slug": slug,
               "status": "queued", "created": _now(), "dry": bool(body.get("dry"))}
        write_job(job)
        threading.Thread(target=run_job, args=(job,), daemon=True).start()
        return self._send(202, {"job_id": job_id, "slug": slug, "status": "started",
                                "note": "audit runs ~10-20 min; poll /status/<job_id>"})


if __name__ == "__main__":
    print(f"prism-runner listening on 127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
