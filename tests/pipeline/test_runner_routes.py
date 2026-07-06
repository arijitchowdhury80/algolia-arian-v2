"""Tests for the staged prism-runner.py v2 route logic, job-state transitions,
phase/skill threading, and kill+timeout — with a FAKE subprocess (no real
`claude -p`, no real VPS, no DB). See:
  docs/workspace/cassandra-tooling/staged/prism-runner.py
  docs/plans/2026-07-02-cassandra-airtight-pipeline-goal.md §1.1-1.2

All DB writes in these tests point at an unreachable DSN by default (the
runner's DB path is fail-soft by design — see test_runner_dbwrite.py for the
DB-specific coverage) so these tests stay fast and dependency-free.
"""

from __future__ import annotations

import importlib.util
import json
import os
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
STAGED_RUNNER = REPO_ROOT / "docs/workspace/cassandra-tooling/staged/prism-runner.py"


def _load_runner(tmp_path):
    """Fresh module per test, isolated to tmp_path (JOBS_DIR/AUDITS_DIR/
    STORE_DIR all live under tmp_path — never touches the real filesystem),
    with DATABASE_URL pointed at a guaranteed-unreachable address so every
    test here exercises fail-soft DB behaviour rather than needing a real DB."""
    os.environ["PRISM_EXEC_DIR"] = str(tmp_path / "exec")
    os.environ["PRISM_STORE_DIR"] = str(tmp_path / "store")
    spec = importlib.util.spec_from_file_location(
        f"staged_prism_runner_routes_{uuid.uuid4().hex[:8]}", STAGED_RUNNER
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.DATABASE_URL = "postgresql://prism:localdev@127.0.0.1:1/prism"
    os.makedirs(mod.JOBS_DIR, exist_ok=True)
    os.makedirs(mod.AUDITS_DIR, exist_ok=True)
    os.makedirs(mod.STORE_DIR, exist_ok=True)
    return mod


@pytest.fixture()
def runner(tmp_path):
    return _load_runner(tmp_path)


def _write_audit_data(runner, slug, **overrides):
    d = os.path.join(runner.AUDITS_DIR, slug)
    os.makedirs(d, exist_ok=True)
    data = {
        "meta": {"company": slug.title(), "domain": f"{slug}.com"},
        "score": {"overall": 6.0, "verdict": "OK"},
        "_pad": "x" * 600,
    }
    data.update(overrides)
    with open(os.path.join(d, f"{slug}-audit-data.json"), "w") as f:
        json.dump(data, f)


class FakeProc:
    """Fake Popen: `poll_sequence` is consumed one value per poll() call (last
    value repeats once exhausted), so tests can script a "still running for N
    polls then done" subprocess without a real one."""

    def __init__(self, poll_sequence=(0,), pid=1234):
        self.pid = pid
        self._seq = list(poll_sequence)
        self._i = 0
        self.terminated = False
        self.killed = False

    def poll(self):
        val = self._seq[min(self._i, len(self._seq) - 1)]
        self._i += 1
        self.returncode = val
        return val

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


# ---------------------------------------------------------------- slugify / job I/O (v1 unchanged)

@pytest.mark.parametrize(
    "domain,expected",
    [
        ("dell.com", "dell"),
        ("https://www.dell.com/", "dell"),
        ("www.foot-locker.com", "foot-locker"),
        ("Home Depot Mexico", "home-depot-mexico"),
    ],
)
def test_slugify_matches_v1_behaviour(runner, domain, expected):
    assert runner.slugify(domain) == expected


def test_write_and_read_job_roundtrip(runner):
    job = {"job_id": "x-1", "domain": "x.com", "slug": "x", "status": "queued"}
    runner.write_job(job)
    assert runner.read_job("x-1") == job
    assert runner.read_job("does-not-exist") is None


# ---------------------------------------------------------- POST /run — v1 compat + new fields

def test_handle_run_domain_only_matches_v1_shape(runner):
    code, body = runner.handle_run({"domain": "dell.com"})
    assert code == 202
    assert body["slug"] == "dell"
    assert "job_id" in body and "note" in body
    job = runner.read_job(body["job_id"])
    assert job["domain"] == "dell.com"
    assert "phase" not in job and "skill" not in job  # v1 body never gets these keys


def test_handle_run_requires_domain(runner):
    code, body = runner.handle_run({})
    assert code == 400
    assert "domain" in body["error"]


def test_handle_run_threads_phase_into_job(runner):
    code, body = runner.handle_run({"domain": "dell.com", "phase": "traffic"})
    assert code == 202
    job = runner.read_job(body["job_id"])
    assert job["phase"] == "traffic"


def test_handle_run_threads_skill_and_skip_into_job(runner):
    _code, body = runner.handle_run(
        {"domain": "dell.com", "skill": "algolia-intel-traffic", "skip": "similarweb-login"}
    )
    job = runner.read_job(body["job_id"])
    assert job["skill"] == "algolia-intel-traffic"
    assert job["skip"] == "similarweb-login"


def test_build_audit_cmd_domain_only_is_v1_identical_argv(runner):
    job = {"domain": "dell.com"}
    cmd = runner.build_audit_cmd(job)
    assert cmd == ["sudo", "-u", runner.AUDIT_USER, "bash", runner.RUN_AUDIT, "dell.com"]


def test_build_audit_cmd_threads_phase_skill_skip_as_flags(runner):
    job = {"domain": "dell.com", "phase": "traffic", "skip": "similarweb-login"}
    cmd = runner.build_audit_cmd(job)
    assert "--phase" in cmd and "traffic" in cmd
    assert "--skip" in cmd and "similarweb-login" in cmd
    assert "--skill" not in cmd  # not requested, not added


# ---------------------------------------------------------------- POST /rerun

def test_handle_rerun_requires_slug(runner):
    code, _body = runner.handle_rerun({"phase": "traffic"})
    assert code == 400


def test_handle_rerun_requires_exactly_one_of_phase_or_skill(runner):
    code, _ = runner.handle_rerun({"slug": "dell"})
    assert code == 400
    code, _ = runner.handle_rerun({"slug": "dell", "phase": "traffic", "skill": "x"})
    assert code == 400


def test_handle_rerun_404s_when_no_prior_job_for_slug(runner):
    code, body = runner.handle_rerun({"slug": "never-run-before", "phase": "traffic"})
    assert code == 404
    assert "never-run-before" in body["error"]


def test_handle_rerun_finds_domain_from_job_history_and_starts_scoped_job(runner):
    runner.handle_run({"domain": "dell.com"})  # establishes job history for slug 'dell'
    code, body = runner.handle_rerun({"slug": "dell", "skill": "algolia-intel-traffic"})
    assert code == 202
    job = runner.read_job(body["job_id"])
    assert job["domain"] == "dell.com"
    assert job["skill"] == "algolia-intel-traffic"
    assert job["rerun_of"]


def test_handle_rerun_uses_most_recent_job_for_slug(runner):
    runner.write_job({"job_id": "dell-1", "slug": "dell", "domain": "old-dell.com",
                       "created": "2026-01-01T00:00:00Z"})
    runner.write_job({"job_id": "dell-2", "slug": "dell", "domain": "dell.com",
                       "created": "2026-07-01T00:00:00Z"})
    prior = runner.find_latest_job_for_slug("dell")
    assert prior["job_id"] == "dell-2"


# ---------------------------------------------------- run_job — phase/skill DI, fake subprocess

def test_run_job_dry_run_completes_without_subprocess(runner):
    job = {"job_id": "dry-1", "domain": "dell.com", "slug": "dell", "dry": True}
    runner.run_job(job, sleep_fn=lambda s: None, clock_fn=lambda: 0.0)
    saved = runner.read_job("dry-1")
    assert saved["status"] == "done"
    assert saved["publish"] == "dry"


def test_run_job_success_publishes_and_marks_done(runner):
    _write_audit_data(runner, "dell")
    job = {"job_id": "dell-ok", "domain": "dell.com", "slug": "dell"}
    runner.run_job(job, popen_fn=lambda *a, **k: FakeProc(poll_sequence=(0,)),
                    sleep_fn=lambda s: None, clock_fn=lambda: 0.0)
    saved = runner.read_job("dell-ok")
    assert saved["status"] == "done"
    assert saved["rc"] == 0
    assert os.path.exists(os.path.join(runner.STORE_DIR, "dell", "audit-data.json"))


def test_run_job_nonzero_exit_marks_failed(runner):
    job = {"job_id": "dell-fail", "domain": "dell.com", "slug": "dell"}
    runner.run_job(job, popen_fn=lambda *a, **k: FakeProc(poll_sequence=(1,)),
                    sleep_fn=lambda s: None, clock_fn=lambda: 0.0)
    saved = runner.read_job("dell-fail")
    assert saved["status"] == "failed"
    assert saved["rc"] == 1


def test_run_job_missing_audit_data_marks_published_failed(runner):
    # rc==0 but no *-audit-data.json ever written -> publish_to_store fails.
    job = {"job_id": "dell-nopub", "domain": "dell.com", "slug": "dell"}
    runner.run_job(job, popen_fn=lambda *a, **k: FakeProc(poll_sequence=(0,)),
                    sleep_fn=lambda s: None, clock_fn=lambda: 0.0)
    saved = runner.read_job("dell-nopub")
    assert saved["status"] == "published_failed"


def test_run_job_records_skill_states_from_log_markers(runner):
    def fake_popen(cmd, stdout, stderr, cwd):
        stdout.write(
            ">>> SKILL START: algolia-intel-company\n"
            ">>> SKILL DONE: algolia-intel-company\n"
            ">>> SKILL START: algolia-intel-traffic\n"
        )
        stdout.flush()
        return FakeProc(poll_sequence=(0,))

    _write_audit_data(runner, "dell")
    job = {"job_id": "dell-skills", "domain": "dell.com", "slug": "dell"}
    runner.run_job(job, popen_fn=fake_popen, sleep_fn=lambda s: None, clock_fn=lambda: 0.0)
    saved = runner.read_job("dell-skills")
    assert saved["skills"]["algolia-intel-company"] == "done"
    assert saved["skills"]["algolia-intel-traffic"] == "running"
    assert saved["skills"]["algolia-intel-hiring"] == "pending"


def test_run_job_detects_needs_human_marker_and_continues(runner):
    """The SimilarWeb HITL mark-and-continue contract (plan §3.2): a
    NEEDS_HUMAN marker in the log does NOT fail the job — rc==0 still
    publishes, with the blocked module recorded in needs_human."""
    def fake_popen(cmd, stdout, stderr, cwd):
        stdout.write("NEEDS_HUMAN:similarweb:login required for traffic data\n")
        stdout.flush()
        return FakeProc(poll_sequence=(0,))

    _write_audit_data(runner, "dell")
    job = {"job_id": "dell-hitl", "domain": "dell.com", "slug": "dell"}
    runner.run_job(job, popen_fn=fake_popen, sleep_fn=lambda s: None, clock_fn=lambda: 0.0)
    saved = runner.read_job("dell-hitl")
    assert saved["status"] == "done"  # the run CONTINUES, not fails
    assert saved["needs_human"]["algolia-intel-traffic"] == "login required for traffic data"


# ---------------------------------------------------------------- GET /status/<job_id>

def test_handle_status_404_for_unknown_job(runner):
    code, _body = runner.handle_status("no-such-job")
    assert code == 404


def test_handle_status_includes_skills_and_needs_human_and_log_tail(runner):
    def fake_popen(cmd, stdout, stderr, cwd):
        stdout.write(">>> SKILL START: algolia-intel-company\nsome progress line\n")
        stdout.flush()
        return FakeProc(poll_sequence=(0,))

    _write_audit_data(runner, "dell")
    job = {"job_id": "dell-status", "domain": "dell.com", "slug": "dell"}
    runner.run_job(job, popen_fn=fake_popen, sleep_fn=lambda s: None, clock_fn=lambda: 0.0)
    code, body = runner.handle_status("dell-status")
    assert code == 200
    assert "skills" in body and "needs_human" in body
    assert "some progress line" in body["log_tail"]


# ---------------------------------------------------------------- per-job wall-clock timeout

def test_run_job_wall_clock_timeout_kills_and_marks_needs_human(runner):
    """A job whose subprocess never finishes must not hang the slot forever —
    it gets killed and marked needs_human with a timeout reason once the
    fake clock crosses timeout_s."""
    proc = FakeProc(poll_sequence=(None, None, None, None))  # "never finishes"
    clock = iter([0.0, 0.0, 5.0, 15.0, 25.0, 35.0])  # crosses a 20s cap on the 4th read

    def fake_popen(cmd, stdout, stderr, cwd):
        return proc

    job = {"job_id": "dell-hang", "domain": "dell.com", "slug": "dell"}
    runner.run_job(job, popen_fn=fake_popen, sleep_fn=lambda s: None,
                    clock_fn=lambda: next(clock), poll_interval_s=0, timeout_s=20)
    saved = runner.read_job("dell-hang")
    assert saved["status"] == "needs_human"
    assert proc.terminated is True
    assert any("timeout" in str(v) for v in saved["needs_human"].values())


# ---------------------------------------------------------------- notify on completion

def test_notify_job_finished_noop_when_unconfigured(runner, monkeypatch):
    monkeypatch.delenv("PRISM_NOTIFY_BOT_TOKEN", raising=False)
    monkeypatch.delenv("PRISM_NOTIFY_CHAT_ID", raising=False)
    sent = []
    result = runner.notify_job_finished(
        {"status": "done", "slug": "dell"}, send_fn=lambda *a: sent.append(a) or True
    )
    assert result is False
    assert sent == []


def test_notify_job_finished_sends_on_done(runner, monkeypatch):
    monkeypatch.setenv("PRISM_NOTIFY_BOT_TOKEN", "tok")
    monkeypatch.setenv("PRISM_NOTIFY_CHAT_ID", "123")
    sent = []

    def fake_send(token, chat_id, text):
        sent.append((token, chat_id, text))
        return True

    result = runner.notify_job_finished(
        {"status": "done", "slug": "dell", "publish": "published dell (score=6.0)"},
        send_fn=fake_send,
    )
    assert result is True
    assert sent == [("tok", "123", "PRISM: dell audit done — published dell (score=6.0)")]


def test_notify_job_finished_sends_on_failure_with_reason(runner, monkeypatch):
    monkeypatch.setenv("PRISM_NOTIFY_BOT_TOKEN", "tok")
    monkeypatch.setenv("PRISM_NOTIFY_CHAT_ID", "123")
    sent = []
    result = runner.notify_job_finished(
        {"status": "failed", "slug": "dell", "error": "boom"},
        send_fn=lambda t, c, x: sent.append(x) or True,
    )
    assert result is True
    assert "dell" in sent[0] and "boom" in sent[0] and "FAILED" in sent[0]


def test_notify_job_finished_ignores_non_terminal_status(runner, monkeypatch):
    monkeypatch.setenv("PRISM_NOTIFY_BOT_TOKEN", "tok")
    monkeypatch.setenv("PRISM_NOTIFY_CHAT_ID", "123")
    sent = []
    result = runner.notify_job_finished(
        {"status": "running", "slug": "dell"}, send_fn=lambda *a: sent.append(a) or True
    )
    assert result is False
    assert sent == []


def test_notify_job_finished_swallows_send_exception(runner, monkeypatch):
    """A Telegram outage must never propagate into the audit run itself."""
    monkeypatch.setenv("PRISM_NOTIFY_BOT_TOKEN", "tok")
    monkeypatch.setenv("PRISM_NOTIFY_CHAT_ID", "123")

    def boom(*a):
        raise RuntimeError("network down")

    result = runner.notify_job_finished({"status": "done", "slug": "dell"}, send_fn=boom)
    assert result is False


def test_run_job_success_triggers_notify(runner, monkeypatch):
    """Integration: run_job's real completion path actually calls notify."""
    calls = []
    monkeypatch.setattr(runner, "notify_job_finished", lambda job: calls.append(job["status"]))
    _write_audit_data(runner, "dell")
    job = {"job_id": "dell-notify", "domain": "dell.com", "slug": "dell"}
    runner.run_job(job, popen_fn=lambda *a, **k: FakeProc(poll_sequence=(0,)),
                    sleep_fn=lambda s: None, clock_fn=lambda: 0.0)
    assert calls == ["done"]


def test_run_job_timeout_triggers_notify(runner, monkeypatch):
    calls = []
    monkeypatch.setattr(runner, "notify_job_finished", lambda job: calls.append(job["status"]))
    proc = FakeProc(poll_sequence=(None, None, None, None))
    clock = iter([0.0, 0.0, 5.0, 15.0, 25.0, 35.0])
    job = {"job_id": "dell-hang-notify", "domain": "dell.com", "slug": "dell"}
    runner.run_job(job, popen_fn=lambda *a, **k: proc, sleep_fn=lambda s: None,
                    clock_fn=lambda: next(clock), poll_interval_s=0, timeout_s=20)
    assert calls == ["needs_human"]


def test_terminate_escalates_to_sigkill_if_still_alive_after_grace(runner):
    proc = FakeProc(poll_sequence=(None, None, None))  # poll() always "still running"
    runner._terminate(proc, sleep_fn=lambda s: None, grace_s=0.1)
    assert proc.terminated is True
    assert proc.killed is True  # never died on its own -> escalated


def test_terminate_does_not_sigkill_if_process_exits_during_grace(runner):
    proc = FakeProc(poll_sequence=(None, 0))  # dies on the 2nd poll (within grace)
    runner._terminate(proc, sleep_fn=lambda s: None, grace_s=5.0)
    assert proc.terminated is True
    assert proc.killed is False


# ---------------------------------------------------------------- POST /kill

def test_handle_kill_requires_job_id(runner):
    code, _body = runner.handle_kill({})
    assert code == 400


def test_handle_kill_404_for_unknown_job(runner):
    code, _body = runner.handle_kill({"job_id": "nope"})
    assert code == 404


def test_handle_kill_409_for_a_job_not_running(runner):
    runner.write_job({"job_id": "done-1", "slug": "dell", "domain": "dell.com", "status": "done"})
    code, _body = runner.handle_kill({"job_id": "done-1"})
    assert code == 409


def test_handle_kill_marks_job_killed(runner, monkeypatch):
    """kill_job signals via os.kill — patch it out so the test never sends a
    real signal to a real pid; assert only the job bookkeeping."""
    runner.write_job({"job_id": "run-1", "slug": "dell", "domain": "dell.com",
                       "status": "running", "pid": 99999999})
    calls = []

    def fake_kill(pid, sig):
        calls.append((pid, sig))
        if sig == 0:
            raise ProcessLookupError()  # "probe" says it's already dead -> no SIGKILL step

    monkeypatch.setattr(runner.os, "kill", fake_kill)
    code, _body = runner.handle_kill({"job_id": "run-1"}, sleep_fn=lambda s: None)
    assert code == 200
    saved = runner.read_job("run-1")
    assert saved["status"] == "killed"
    assert (99999999, runner.signal.SIGTERM) in calls


# ---------------------------------------------------------------- GET /needs_human

def test_handle_needs_human_lists_only_jobs_with_blockers(runner):
    runner.write_job({"job_id": "clean-1", "slug": "clean", "domain": "clean.com",
                       "status": "done", "needs_human": {}})
    runner.write_job({"job_id": "blocked-1", "slug": "belk", "domain": "belk.com", "status": "done",
                       "needs_human": {"algolia-intel-traffic": "login required"}})
    code, body = runner.handle_needs_human()
    assert code == 200
    slugs = [w["slug"] for w in body["waiting"]]
    assert slugs == ["belk"]


def test_handle_needs_human_empty_when_nothing_blocked(runner):
    runner.write_job({"job_id": "clean-1", "slug": "clean", "domain": "clean.com",
                       "status": "done"})
    _code, body = runner.handle_needs_human()
    assert body["waiting"] == []


# ---------------------------------------------------------------- GET /jobs (unchanged v1 route)

def test_handle_jobs_returns_recent_jobs(runner):
    runner.write_job({"job_id": "a", "slug": "a", "domain": "a.com", "status": "done",
                       "created": "2026-01-01T00:00:00Z"})
    runner.write_job({"job_id": "b", "slug": "b", "domain": "b.com", "status": "done",
                       "created": "2026-01-02T00:00:00Z"})
    code, body = runner.handle_jobs()
    assert code == 200
    assert {j["job_id"] for j in body["jobs"]} == {"a", "b"}
