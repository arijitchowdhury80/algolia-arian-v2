"""Tests for the staged prism-runner.py v2 DB write path (Postgres as source
of truth, fail-soft additive write). See:
  docs/workspace/cassandra-tooling/staged/prism-runner.py
  docs/plans/2026-07-02-cassandra-airtight-pipeline-goal.md §1.4

Spins an EPHEMERAL postgres:16 container on 127.0.0.1:55440 for the module
(the shared local dev DB on 55432 was not up when this was written — see
memory `project-prism-airtight-pipeline-plan`). Runs the REAL alembic
migrations (001-009) against it so the raw-SQL writes in prism-runner.py are
tested against the exact production schema (server_side column defaults and
all) rather than a hand-rolled approximation. Requires docker.

The staged runner lives outside the `prism_platform` package (it's a
standalone host script, hyphenated filename) so it's loaded via
importlib.util rather than a normal import.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psycopg2
import pytest

# Two roots since the 2026-07-28 restructure: docs/ is at the repo root, while
# alembic.ini and the importable package live inside backend/.
REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]
STAGED_RUNNER = REPO_ROOT / "docs/workspace/cassandra-tooling/staged/prism-runner.py"

CONTAINER_NAME = "prism-test-pg-dbwrite"
TEST_PORT = 55440
TEST_DSN_SYNC = f"postgresql://prism:localdev@127.0.0.1:{TEST_PORT}/prism"
TEST_DSN_ASYNC = f"postgresql+asyncpg://prism:localdev@127.0.0.1:{TEST_PORT}/prism"

pytestmark = pytest.mark.skipif(
    subprocess.run(["docker", "info"], capture_output=True).returncode != 0,
    reason="docker not available — required for the ephemeral test Postgres",
)


def _load_runner(tmp_path=None):
    """Load the staged runner as a fresh module. If tmp_path is given, point
    PRISM_EXEC_DIR/PRISM_STORE_DIR at writable scratch dirs before import so
    the module-level `os.makedirs(JOBS_DIR)` never touches the real /opt or
    /root paths (this test box has no permission there, and even on a real
    dev box we don't want tests writing into it)."""
    import os as _os

    if tmp_path is not None:
        _os.environ["PRISM_EXEC_DIR"] = str(tmp_path / "exec")
        _os.environ["PRISM_STORE_DIR"] = str(tmp_path / "store")
    spec = importlib.util.spec_from_file_location(
        f"staged_prism_runner_dbwrite_{uuid.uuid4().hex[:8]}", STAGED_RUNNER
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _wait_for_pg(dsn: str, timeout: float = 40.0) -> None:
    deadline = time.monotonic() + timeout
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            conn = psycopg2.connect(dsn)
            conn.close()
            return
        except Exception as e:
            last_exc = e
            time.sleep(0.5)
    raise RuntimeError(f"ephemeral postgres never became ready: {last_exc!r}")


def _run_real_migrations(dsn_async: str) -> None:
    """Run the actual alembic 001-009 migrations against the test DB so the
    schema (including every server_side column default) matches production
    exactly — not a hand-approximated CREATE TABLE."""
    sys.path.insert(0, str(BACKEND_ROOT))
    from alembic.config import Config

    from alembic import command

    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", dsn_async)
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="module")
def pg_dsn():
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)
    result = subprocess.run(
        [
            "docker", "run", "-d", "--name", CONTAINER_NAME,
            "-e", "POSTGRES_USER=prism", "-e", "POSTGRES_PASSWORD=localdev",
            "-e", "POSTGRES_DB=prism", "-p", f"{TEST_PORT}:5432", "postgres:16",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"docker run failed: {result.stderr}"
    try:
        _wait_for_pg(TEST_DSN_SYNC)
        _run_real_migrations(TEST_DSN_ASYNC)
        yield TEST_DSN_SYNC
    finally:
        subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)


@pytest.fixture()
def runner(pg_dsn, tmp_path):
    mod = _load_runner(tmp_path)
    mod.DATABASE_URL = pg_dsn
    return mod


@pytest.fixture()
def db_conn(pg_dsn):
    conn = psycopg2.connect(pg_dsn)
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def _clean_tables(pg_dsn):
    conn = psycopg2.connect(pg_dsn)
    with conn, conn.cursor() as cur:
        cur.execute("TRUNCATE module_executions, audits, accounts CASCADE")
    conn.close()
    yield


def _job(domain="dell.com", slug="dell", **extra):
    job = {"job_id": f"{slug}-20260702-120000", "domain": domain, "slug": slug}
    job.update(extra)
    return job


def _audit_data(company="Dell", domain="dell.com", score=6.5, **sections):
    data = {
        "meta": {"company": company, "domain": domain, "audit_date": "2026-07-02"},
        "score": {"overall": score, "verdict": "Solid"},
        "company_snapshot": {"name": company},
        "tech_stack": {"vendor": "Constructor.io"},
        "traffic": {"monthly_visits": 12_000_000},
    }
    data.update(sections)
    return data


# ---------------------------------------------------------------- audit_start

def test_db_write_audit_start_creates_running_audit_row(runner, db_conn):
    job = _job()
    audit_id = runner.db_write_audit_start(job)
    assert audit_id is not None
    with db_conn.cursor() as cur:
        cur.execute("SELECT status, user_id FROM audits WHERE id = %s", (audit_id,))
        row = cur.fetchone()
    assert row == ("running", "cassandra")


def test_db_write_audit_start_creates_account_if_missing(runner, db_conn):
    job = _job(domain="never-seen-before.example", slug="never-seen-before")
    runner.db_write_audit_start(job)
    with db_conn.cursor() as cur:
        cur.execute("SELECT company_name FROM accounts WHERE domain = %s",
                    ("never-seen-before.example",))
        row = cur.fetchone()
    assert row is not None


def test_db_write_audit_start_reuses_existing_account_for_domain(runner, db_conn):
    job1 = _job(domain="dell.com", slug="dell", job_id="dell-20260701-000000")
    job2 = _job(domain="dell.com", slug="dell", job_id="dell-20260702-000000")
    runner.db_write_audit_start(job1)
    runner.db_write_audit_start(job2)
    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM accounts WHERE domain = %s", ("dell.com",))
        (count,) = cur.fetchone()
    assert count == 1


def test_db_write_audit_start_records_phase_and_skill_in_config(runner, db_conn):
    job = _job(phase="research")
    audit_id = runner.db_write_audit_start(job)
    with db_conn.cursor() as cur:
        cur.execute("SELECT config FROM audits WHERE id = %s", (audit_id,))
        (config,) = cur.fetchone()
    assert config["phase"] == "research"
    assert config["job_id"] == job["job_id"]


def test_db_write_audit_start_fails_soft_on_unreachable_db(runner):
    runner.DATABASE_URL = "postgresql://prism:localdev@127.0.0.1:1/prism"  # nothing listens on :1
    audit_id = runner.db_write_audit_start(_job())
    assert audit_id is None  # never raises, just returns None


# ---------------------------------------------------------------- audit_publish

def test_db_write_audit_publish_creates_completed_audit_with_score(runner, db_conn):
    job = _job()
    result = runner.db_write_audit_publish(job, "dell", _audit_data(score=7.25))
    assert result["ok"] is True
    with db_conn.cursor() as cur:
        cur.execute("SELECT status, score FROM audits WHERE id = %s", (result["audit_id"],))
        status, score = cur.fetchone()
    assert status == "completed"
    assert float(score) == 7.25


def test_db_write_audit_publish_stores_full_audit_data_jsonb(runner, db_conn):
    job = _job()
    data = _audit_data()
    result = runner.db_write_audit_publish(job, "dell", data)
    with db_conn.cursor() as cur:
        cur.execute("SELECT audit_data FROM audits WHERE id = %s", (result["audit_id"],))
        (stored,) = cur.fetchone()
    assert stored["meta"]["company"] == "Dell"
    assert stored["tech_stack"]["vendor"] == "Constructor.io"


def test_db_write_audit_publish_updates_prior_running_row_not_a_new_one(runner, db_conn):
    job = _job()
    started_id = runner.db_write_audit_start(job)
    job["_db_audit_id"] = started_id
    result = runner.db_write_audit_publish(job, "dell", _audit_data())
    assert result["audit_id"] == started_id
    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM audits WHERE account_id = "
                    "(SELECT id FROM accounts WHERE domain='dell.com')")
        (count,) = cur.fetchone()
    assert count == 1  # updated in place, not duplicated


def test_db_write_audit_publish_writes_one_module_execution_per_known_module(runner, db_conn):
    job = _job()
    result = runner.db_write_audit_publish(job, "dell", _audit_data())
    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM module_executions WHERE audit_id = %s",
                    (result["audit_id"],))
        (count,) = cur.fetchone()
    assert count == len(runner.MODULE_SECTION_MAP)


def test_db_write_audit_publish_stores_section_output_on_its_module_row(runner, db_conn):
    job = _job()
    result = runner.db_write_audit_publish(job, "dell", _audit_data())
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT output_json, status FROM module_executions "
            "WHERE audit_id = %s AND module_name = 'algolia-intel-techstack'",
            (result["audit_id"],),
        )
        output, status = cur.fetchone()
    assert output["vendor"] == "Constructor.io"
    assert status == "completed"


def test_db_write_audit_publish_marks_needs_human_module(runner, db_conn):
    job = _job()
    result = runner.db_write_audit_publish(
        job, "dell", _audit_data(),
        needs_human={"algolia-intel-traffic": "login required for traffic data"},
    )
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT status, error_message FROM module_executions "
            "WHERE audit_id = %s AND module_name = 'algolia-intel-traffic'",
            (result["audit_id"],),
        )
        status, reason = cur.fetchone()
    assert status == "needs_human"
    assert reason == "login required for traffic data"


def test_db_write_audit_publish_rerun_upserts_same_module_row_not_duplicate(runner, db_conn):
    job = _job()
    result = runner.db_write_audit_publish(job, "dell", _audit_data())
    audit_id = result["audit_id"]
    job["_db_audit_id"] = audit_id
    # Simulate a targeted re-run of just the traffic skill landing new data.
    runner.db_write_audit_publish(job, "dell", _audit_data(traffic={"monthly_visits": 99}))
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT count(*), max((output_json->>'monthly_visits')::int) FROM module_executions "
            "WHERE audit_id = %s AND module_name = 'algolia-intel-traffic'",
            (audit_id,),
        )
        count, latest_visits = cur.fetchone()
    assert count == 1  # ON CONFLICT updated, didn't insert a second row
    assert latest_visits == 99


def test_db_write_audit_publish_modules_without_a_section_key_get_null_output(runner, db_conn):
    job = _job()
    result = runner.db_write_audit_publish(job, "dell", _audit_data())
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT output_json FROM module_executions "
            "WHERE audit_id = %s AND module_name = 'algolia-intel-queries'",
            (result["audit_id"],),
        )
        (output,) = cur.fetchone()
    assert output is None  # MODULE_SECTION_MAP["algolia-intel-queries"] is None by design


def test_db_write_audit_publish_fails_soft_on_unreachable_db(runner):
    runner.DATABASE_URL = "postgresql://prism:localdev@127.0.0.1:1/prism"
    result = runner.db_write_audit_publish(_job(), "dell", _audit_data())
    assert result["ok"] is False
    assert "reason" in result  # never raises


def test_db_write_audit_publish_fails_soft_on_malformed_dsn(runner):
    runner.DATABASE_URL = "not-a-valid-dsn-at-all"
    result = runner.db_write_audit_publish(_job(), "dell", _audit_data())
    assert result["ok"] is False


# ---------------------------------------------------------------- integration: file path unaffected

def test_run_job_publishes_file_store_even_when_db_is_unreachable(runner, tmp_path):
    """The file-publish path (publish_to_store) must succeed regardless of DB
    health — this is the 'additive until cutover, fail-soft' contract from
    plan §1.4. Point the runner at directories under tmp_path, fake a
    successful subprocess (a real claude -p run is out of scope for this
    test — the route/DI tests cover the subprocess loop itself), and set a
    dead DATABASE_URL to prove the DB failure never reaches the job's final
    status."""
    import json as _json
    import os

    runner.DATABASE_URL = "postgresql://prism:localdev@127.0.0.1:1/prism"
    runner.JOBS_DIR = str(tmp_path / "jobs")
    runner.AUDITS_DIR = str(tmp_path / "audits")
    runner.STORE_DIR = str(tmp_path / "store")
    runner.INDEX_JSON = os.path.join(runner.STORE_DIR, "index.json")
    os.makedirs(runner.JOBS_DIR, exist_ok=True)
    audit_dir = os.path.join(runner.AUDITS_DIR, "dell")
    os.makedirs(audit_dir, exist_ok=True)
    fake_data = _audit_data()
    fake_data["_pad"] = "x" * 600  # publish_to_store requires >500 bytes on disk
    with open(os.path.join(audit_dir, "dell-audit-data.json"), "w") as f:
        _json.dump(fake_data, f)

    class _FakeProc:
        pid = 4242
        returncode = 0

        def poll(self):
            return 0  # "already finished" — the poll loop never executes

    job = _job(job_id="dell-fake-1", dry=False)
    runner.run_job(job, popen_fn=lambda *a, **k: _FakeProc(),
                    sleep_fn=lambda s: None, clock_fn=lambda: 0.0)

    saved = runner.read_job("dell-fake-1")
    assert saved["status"] == "done"  # file path succeeded despite dead DB
    assert saved["publish"].startswith("published dell")
    assert saved["db_publish"]["ok"] is False  # DB failure recorded, not silently lost
    assert os.path.exists(os.path.join(runner.STORE_DIR, "dell", "audit-data.json"))
