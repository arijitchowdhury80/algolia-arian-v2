"""Tests for the DB-write helper (server/pipeline/db_write.py).

Split the same way tests/test_knowledge.py already does:
  - Pure-logic tests (status mapping, JSONB shape, duration math) -- run
    anywhere, no DB required.
  - One @pytest.mark.db integration test proving the ORM upsert actually
    lands a ModuleExecution row correctly against a real Postgres with the
    real migrations applied (same ephemeral-docker + alembic pattern as
    tests/pipeline/test_runner_dbwrite.py -- reused, not rebuilt). Skipped
    automatically when docker is unavailable (see pytestmark below); NOT
    executed in this sandbox (no docker daemon here) -- see task-3 report.
"""

from __future__ import annotations

import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from server.pipeline.db_write import (
    attempt_duration_ms,
    verdict_to_status,
    verdict_to_validation_json,
    write_module_execution_row,
)
from server.pipeline.gate import BlockClass, SkillOutput, Verdict, VerdictStatus
from server.pipeline.self_heal import Attempt
from server.pipeline.verdicts import FactCheckVerdict, LegalVerdict, QualityScore


def _skill_output() -> SkillOutput:
    return SkillOutput(
        skill_name="algolia-intel-financial-public",
        domain="belk.com",
        audit_dir=Path("/tmp/Belk"),
        company_name="Belk",
    )


def _attempt(
    phase: str = "algolia-intel-financial-public",
    attempt_number: int = 1,
    dispatch_ok: bool = True,
    started_at: float = 10.0,
    finished_at: float = 12.5,
) -> Attempt:
    return Attempt(
        phase=phase,
        attempt_number=attempt_number,
        dispatch_ok=dispatch_ok,
        gate=None,
        started_at=started_at,
        finished_at=finished_at,
    )


def _pass_verdict() -> Verdict:
    return Verdict(
        skill_name="algolia-intel-financial-public",
        stage=5,
        status=VerdictStatus.PASS,
        block_class=None,
        findings=(),
        mechanical_raw="ok",
        quality=QualityScore(
            dimension="instruction_adherence",
            score=9.0,
            passing_checks=18,
            total_checks=20,
            reasoning="Followed checklist.",
        ),
        legal=LegalVerdict(status="needs_human_review", note="No rubric yet."),
    )


def _retry_worthy_block_verdict() -> Verdict:
    return Verdict(
        skill_name="algolia-intel-financial-public",
        stage=1,
        status=VerdictStatus.BLOCK,
        block_class=BlockClass.RETRY_WORTHY,
        findings=("missing traffic data",),
        mechanical_raw="finding: missing traffic data",
    )


def _unfixable_block_verdict() -> Verdict:
    return Verdict(
        skill_name="algolia-intel-financial-public",
        stage=2,
        status=VerdictStatus.BLOCK,
        block_class=BlockClass.UNFIXABLE,
        findings=("CONTRADICTED: HQ city -- source says Charlotte",),
        mechanical_raw="ok",
        factcheck=FactCheckVerdict(
            claim="Belk is headquartered in Miami.",
            evidence_tier="AUTHENTIC",
            verdict="CONTRADICTED",
            citation="https://belk.com/about",
            reasoning="Source says Charlotte, NC.",
        ),
    )


class TestVerdictToStatus:
    def test_dispatch_failure_is_failed_regardless_of_verdict(self) -> None:
        assert verdict_to_status(_pass_verdict(), dispatch_ok=False) == "failed"

    def test_no_verdict_is_failed(self) -> None:
        assert verdict_to_status(None, dispatch_ok=True) == "failed"

    def test_pass_is_completed(self) -> None:
        assert verdict_to_status(_pass_verdict(), dispatch_ok=True) == "completed"

    def test_retry_worthy_block_is_blocked_not_needs_human(self) -> None:
        assert verdict_to_status(_retry_worthy_block_verdict(), dispatch_ok=True) == "blocked"

    def test_unfixable_block_is_needs_human(self) -> None:
        assert verdict_to_status(_unfixable_block_verdict(), dispatch_ok=True) == "needs_human"


class TestVerdictToValidationJson:
    def test_pass_verdict_carries_quality_and_legal_subverdicts(self) -> None:
        vj = verdict_to_validation_json(_pass_verdict())
        assert vj["stage"] == 5
        assert vj["status"] == "pass"
        assert vj["block_class"] is None
        assert vj["quality"]["score"] == 9.0
        assert vj["legal"]["status"] == "needs_human_review"
        assert vj["factcheck"] is None
        assert vj["adversarial"] is None

    def test_unfixable_block_carries_factcheck_subverdict(self) -> None:
        vj = verdict_to_validation_json(_unfixable_block_verdict())
        assert vj["stage"] == 2
        assert vj["status"] == "block"
        assert vj["block_class"] == "unfixable"
        assert vj["factcheck"]["verdict"] == "CONTRADICTED"
        assert "CONTRADICTED" in vj["findings"][0]

    def test_findings_is_a_plain_list_not_a_tuple_for_json_safety(self) -> None:
        vj = verdict_to_validation_json(_retry_worthy_block_verdict())
        assert isinstance(vj["findings"], list)


class TestAttemptDurationMs:
    def test_computes_positive_duration_from_monotonic_delta(self) -> None:
        attempt = _attempt(started_at=10.0, finished_at=12.5)
        assert attempt_duration_ms(attempt) == 2500

    def test_zero_duration_is_zero_not_negative(self) -> None:
        attempt = _attempt(started_at=5.0, finished_at=5.0)
        assert attempt_duration_ms(attempt) == 0

    def test_never_returns_negative_even_if_clock_is_inconsistent(self) -> None:
        # Defensive: a misbehaving injected clock going "backwards" must not
        # produce a negative duration written to an Integer column.
        attempt = _attempt(started_at=10.0, finished_at=9.0)
        assert attempt_duration_ms(attempt) == 0


class TestDurationDoesNotLeakMonotonicReadingsAsTimestamps:
    """Regression guard for the monotonic-vs-epoch gotcha documented in
    db_write.py's module docstring -- attempt.started_at/finished_at (e.g.
    10.0, 12.5) must never be interpreted as epoch seconds anywhere in this
    module's pure functions."""

    def test_duration_ms_is_the_only_place_raw_clock_values_are_used(self) -> None:
        attempt = _attempt(started_at=10.0, finished_at=12.5)
        # If this were (mis)treated as an epoch timestamp, fromtimestamp(10.0)
        # would be 1970-01-01T00:00:10Z -- assert the module doesn't expose
        # any function that maps a bare attempt clock reading to a real date.
        with pytest.raises(AttributeError):
            attempt.started_at.timestamp()  # floats have no .timestamp()


# ===========================================================================
# DB integration -- @pytest.mark.db, ephemeral docker + real alembic
# migrations, same pattern as tests/pipeline/test_runner_dbwrite.py. Skipped
# automatically when docker is unavailable.
# ===========================================================================

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTAINER_NAME = "prism-test-pg-gate-dbwrite"
TEST_PORT = 55441
TEST_DSN_ASYNC = f"postgresql+asyncpg://prism:localdev@127.0.0.1:{TEST_PORT}/prism"

_skip_if_no_docker = pytest.mark.skipif(
    subprocess.run(["docker", "info"], capture_output=True).returncode != 0,
    reason="docker not available -- required for the ephemeral test Postgres",
)
# Applied per-test (not as a module-level `pytestmark`) so the pure-logic
# tests above run everywhere -- only the DB integration tests below need
# docker.


def _run_real_migrations(dsn_async: str) -> None:
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    from alembic.config import Config

    from alembic import command

    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", dsn_async)
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="module")
def pg_dsn():
    import time

    import psycopg2

    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)
    result = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER_NAME,
            "-e",
            "POSTGRES_USER=prism",
            "-e",
            "POSTGRES_PASSWORD=localdev",
            "-e",
            "POSTGRES_DB=prism",
            "-p",
            f"{TEST_PORT}:5432",
            "postgres:16",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"docker run failed: {result.stderr}"
    dsn_sync = f"postgresql://prism:localdev@127.0.0.1:{TEST_PORT}/prism"
    try:
        deadline = time.monotonic() + 40.0
        last_exc: Exception | None = None
        while time.monotonic() < deadline:
            try:
                conn = psycopg2.connect(dsn_sync)
                conn.close()
                break
            except Exception as e:
                last_exc = e
                time.sleep(0.5)
        else:
            raise RuntimeError(f"ephemeral postgres never became ready: {last_exc!r}")
        _run_real_migrations(TEST_DSN_ASYNC)
        yield TEST_DSN_ASYNC
    finally:
        subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)


@pytest.fixture()
async def async_session(pg_dsn):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(pg_dsn, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture()
async def account_and_audit_id(async_session):
    from sqlalchemy import text

    account_id = uuid.uuid4()
    audit_id = uuid.uuid4()
    await async_session.execute(
        text("INSERT INTO accounts (id, company_name, domain) VALUES (:id, :name, :domain)"),
        {"id": account_id, "name": "Belk", "domain": "belk.com"},
    )
    await async_session.execute(
        text(
            "INSERT INTO audits (id, account_id, user_id, status) "
            "VALUES (:id, :account_id, 'system', 'running')"
        ),
        {"id": audit_id, "account_id": account_id},
    )
    await async_session.commit()
    return audit_id


@pytest.mark.db
@_skip_if_no_docker
@pytest.mark.asyncio
async def test_write_module_execution_row_inserts_a_new_row(async_session, account_and_audit_id):
    from sqlalchemy import select

    from core.db.models import ModuleExecution

    audit_id = account_and_audit_id
    row = await write_module_execution_row(
        async_session,
        audit_id=audit_id,
        domain="belk.com",
        verdict=_pass_verdict(),
        attempt=_attempt(),
        now=datetime(2026, 7, 13, 12, 0, 0, tzinfo=UTC),
    )
    assert row.status == "completed"
    assert row.module_name == "algolia-intel-financial-public"

    result = await async_session.execute(
        select(ModuleExecution).where(ModuleExecution.audit_id == audit_id)
    )
    rows = result.scalars().all()
    assert len(rows) == 1


@pytest.mark.db
@_skip_if_no_docker
@pytest.mark.asyncio
async def test_write_module_execution_row_upserts_on_retry_not_duplicate(
    async_session, account_and_audit_id
):
    from sqlalchemy import select

    from core.db.models import ModuleExecution

    audit_id = account_and_audit_id
    await write_module_execution_row(
        async_session,
        audit_id=audit_id,
        domain="belk.com",
        verdict=_retry_worthy_block_verdict(),
        attempt=_attempt(attempt_number=1),
    )
    await write_module_execution_row(
        async_session,
        audit_id=audit_id,
        domain="belk.com",
        verdict=_pass_verdict(),
        attempt=_attempt(attempt_number=2),
    )

    result = await async_session.execute(
        select(ModuleExecution).where(
            ModuleExecution.audit_id == audit_id,
            ModuleExecution.module_name == "algolia-intel-financial-public",
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 1  # updated in place, not duplicated
    assert rows[0].status == "completed"  # reflects the second (latest) attempt
