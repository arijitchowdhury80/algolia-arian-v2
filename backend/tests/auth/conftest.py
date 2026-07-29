"""Shared @pytest.mark.db fixtures for tests/auth/* -- ephemeral docker
Postgres + real alembic migrations, same pattern as
tests/pipeline/test_db_write.py's DB integration section. Skipped
automatically when docker is unavailable; NOT executed in this sandbox (no
docker daemon here) -- see
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
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTAINER_NAME = "prism-test-pg-auth"
TEST_PORT = 55443
TEST_DSN_SYNC = f"postgresql://prism:localdev@127.0.0.1:{TEST_PORT}/prism"
TEST_DSN_ASYNC = f"postgresql+asyncpg://prism:localdev@127.0.0.1:{TEST_PORT}/prism"

skip_if_no_docker = pytest.mark.skipif(
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


@pytest.fixture()
def seed_user(async_session):
    """Factory fixture: insert a users row, return its id."""

    async def _seed(user_id: str, email: str = "test@example.com") -> str:
        await async_session.execute(
            text("INSERT INTO users (id, email) VALUES (:id, :email) ON CONFLICT DO NOTHING"),
            {"id": user_id, "email": email},
        )
        await async_session.commit()
        return user_id

    return _seed


@pytest.fixture()
def seed_account_and_audit(async_session):
    """Factory fixture: insert an account + audit owned by `owner_id`,
    return (account_id, audit_id)."""

    async def _seed(owner_id: str, domain: str = "belk.com", company_name: str = "Belk"):
        account_id = uuid.uuid4()
        audit_id = uuid.uuid4()
        await async_session.execute(
            text("INSERT INTO accounts (id, company_name, domain) VALUES (:id, :name, :domain)"),
            {"id": account_id, "name": company_name, "domain": domain},
        )
        await async_session.execute(
            text(
                "INSERT INTO audits (id, account_id, user_id, status) "
                "VALUES (:id, :account_id, :owner_id, 'completed')"
            ),
            {"id": audit_id, "account_id": account_id, "owner_id": owner_id},
        )
        await async_session.commit()
        return account_id, audit_id

    return _seed
