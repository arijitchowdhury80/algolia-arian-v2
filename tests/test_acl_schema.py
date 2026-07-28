"""Schema tests for the ACL slice (run-2026-07-14-001) -- `users`,
`audit_shares`, `seen_assertions` tables + indexes. See
.development-loop/run-2026-07-14-001/04-spec.md §1 and 06-plan.md Wave 1
(B1).

@pytest.mark.db -- ephemeral docker Postgres + real alembic migrations,
same pattern as tests/pipeline/test_db_write.py's DB integration section.
Skipped automatically when docker is unavailable; NOT executed in this
sandbox (no docker daemon here) -- see
.development-loop/run-2026-07-14-001/07-build-log.md.
"""

from __future__ import annotations

import subprocess
import sys
import time
import uuid
from pathlib import Path

import psycopg2
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTAINER_NAME = "prism-test-pg-acl-schema"
TEST_PORT = 55442
TEST_DSN_SYNC = f"postgresql://prism:localdev@127.0.0.1:{TEST_PORT}/prism"
TEST_DSN_ASYNC = f"postgresql+asyncpg://prism:localdev@127.0.0.1:{TEST_PORT}/prism"

pytestmark = pytest.mark.db

_skip_if_no_docker = pytest.mark.skipif(
    subprocess.run(["docker", "info"], capture_output=True).returncode != 0,
    reason="docker not available -- required for the ephemeral test Postgres",
)


def _run_real_migrations(dsn_async: str) -> None:
    sys.path.insert(0, str(REPO_ROOT))
    from alembic.config import Config

    from alembic import command

    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", dsn_async)
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="module")
def pg_dsn():
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
    try:
        deadline = time.monotonic() + 40.0
        last_exc: Exception | None = None
        while time.monotonic() < deadline:
            try:
                conn = psycopg2.connect(TEST_DSN_SYNC)
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
    engine = create_async_engine(pg_dsn, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@_skip_if_no_docker
@pytest.mark.asyncio
async def test_users_and_audit_shares_tables_exist_with_constraints(async_session) -> None:
    result = await async_session.execute(
        text(
            "SELECT to_regclass('public.users'), to_regclass('public.audit_shares'), "
            "to_regclass('public.seen_assertions')"
        )
    )
    users_tbl, shares_tbl, seen_tbl = result.one()
    assert users_tbl is not None
    assert shares_tbl is not None
    assert seen_tbl is not None


@_skip_if_no_docker
@pytest.mark.asyncio
async def test_expected_indexes_exist(async_session) -> None:
    result = await async_session.execute(
        text(
            "SELECT indexname FROM pg_indexes WHERE tablename IN "
            "('audit_shares', 'audits', 'seen_assertions') "
            "AND indexname IN ('idx_audit_shares_shared_with', 'idx_audits_user')"
        )
    )
    names = {row[0] for row in result.all()}
    assert names == {"idx_audit_shares_shared_with", "idx_audits_user"}


@_skip_if_no_docker
@pytest.mark.asyncio
async def test_permission_check_rejects_non_view_value(async_session) -> None:
    account_id = uuid.uuid4()
    audit_id = uuid.uuid4()
    await async_session.execute(
        text("INSERT INTO accounts (id, company_name, domain) VALUES (:id, 'Belk', 'belk.com')"),
        {"id": account_id},
    )
    await async_session.execute(
        text(
            "INSERT INTO audits (id, account_id, user_id, status) "
            "VALUES (:id, :account_id, 'system', 'running')"
        ),
        {"id": audit_id, "account_id": account_id},
    )
    await async_session.execute(
        text("INSERT INTO users (id, email) VALUES ('user_a', 'a@example.com')")
    )
    await async_session.commit()

    with pytest.raises(IntegrityError):
        await async_session.execute(
            text(
                "INSERT INTO audit_shares (audit_id, shared_with_user_id, permission, created_by) "
                "VALUES (:audit_id, 'user_a', 'edit', 'user_a')"
            ),
            {"audit_id": audit_id},
        )
        await async_session.commit()


@_skip_if_no_docker
@pytest.mark.asyncio
async def test_audit_shares_rejects_duplicate_composite_pk(async_session) -> None:
    account_id = uuid.uuid4()
    audit_id = uuid.uuid4()
    await async_session.execute(
        text("INSERT INTO accounts (id, company_name, domain) VALUES (:id, 'Belk', 'belk.com')"),
        {"id": account_id},
    )
    await async_session.execute(
        text(
            "INSERT INTO audits (id, account_id, user_id, status) "
            "VALUES (:id, :account_id, 'system', 'running')"
        ),
        {"id": audit_id, "account_id": account_id},
    )
    await async_session.execute(
        text("INSERT INTO users (id, email) VALUES ('user_b', 'b@example.com')")
    )
    await async_session.execute(
        text(
            "INSERT INTO audit_shares (audit_id, shared_with_user_id, permission, created_by) "
            "VALUES (:audit_id, 'user_b', 'view', 'user_b')"
        ),
        {"audit_id": audit_id},
    )
    await async_session.commit()

    with pytest.raises(IntegrityError):
        await async_session.execute(
            text(
                "INSERT INTO audit_shares (audit_id, shared_with_user_id, permission, created_by) "
                "VALUES (:audit_id, 'user_b', 'view', 'user_b')"
            ),
            {"audit_id": audit_id},
        )
        await async_session.commit()


@_skip_if_no_docker
@pytest.mark.asyncio
async def test_downgrade_cleanly_drops_new_tables_and_index(pg_dsn) -> None:
    """`alembic downgrade -1` cleanly drops all three new tables and the
    new index with no error (06-plan.md B1 acceptance criteria)."""
    sys.path.insert(0, str(REPO_ROOT))
    from alembic.config import Config

    from alembic import command

    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", pg_dsn)
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    command.downgrade(cfg, "-1")

    engine = create_async_engine(pg_dsn, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT to_regclass('public.users'), to_regclass('public.audit_shares'), "
                    "to_regclass('public.seen_assertions')"
                )
            )
            users_tbl, shares_tbl, seen_tbl = result.one()
            assert users_tbl is None
            assert shares_tbl is None
            assert seen_tbl is None
    finally:
        await engine.dispose()
        # Restore head so subsequent tests in this module (if any run after)
        # see the full schema again.
        command.upgrade(cfg, "head")
