"""Tests for Task 5's chat router -- authorization logic + endpoint wiring.

Patch #6 honesty note: this repo has no live Postgres and no live Clerk
session in this sandbox, so nothing here proves a real Clerk-authenticated
request end-to-end. What IS proven:
  - `check_slug_authorization`'s pure decision logic (fail-open with no
    header, 403 on a header that excludes the domain, pass on a header that
    includes it) -- no I/O, no DB, no auth provider needed.
  - `authorize_audit_access`'s DB-fetch + 404/403 wiring, against a fake
    AsyncSession (no live Postgres).
  - The full FastAPI route (`POST /{audit_id}/chat`) responds correctly when
    `run_chat_agent` and the DB session are both faked/overridden.

See docs/workspace/phase2-executioner/task-5-report.md for the concrete,
ready-to-run Clerk integration test spec this stands in for.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from prism_platform.api.routers.chat import authorize_audit_access, check_slug_authorization
from prism_platform.db.models import Account, Audit
from prism_platform.main import app
from prism_platform.pipeline.chat_agent import ChatAgentResult

# ---------------------------------------------------------------------------
# Pure authorization decision logic
# ---------------------------------------------------------------------------


def test_check_slug_authorization_no_header_fails_open() -> None:
    # Matches the real, unenforced state of the stack today -- not a
    # regression introduced by this task. See patch #6 note in chat.py.
    check_slug_authorization("belk.com", None)  # must not raise


def test_check_slug_authorization_header_includes_domain_passes() -> None:
    check_slug_authorization("belk.com", "dell.com, belk.com")  # must not raise


def test_check_slug_authorization_header_excludes_domain_raises_403() -> None:
    with pytest.raises(HTTPException) as exc_info:
        check_slug_authorization("belk.com", "dell.com,lululemon.com")
    assert exc_info.value.status_code == 403


def test_check_slug_authorization_is_case_insensitive() -> None:
    check_slug_authorization("Belk.com", "belk.com")  # must not raise


# ---------------------------------------------------------------------------
# authorize_audit_access -- DB-fetch + authorization, fake AsyncSession
# ---------------------------------------------------------------------------


class _FakeScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _FakeSession:
    """Returns queued results in call order -- mirrors the two sequential
    lookups authorize_audit_access performs (audit, then account)."""

    def __init__(self, results: list[object]) -> None:
        self._results = list(results)

    async def execute(self, stmt: object) -> _FakeScalarResult:
        return _FakeScalarResult(self._results.pop(0))


@pytest.mark.asyncio
async def test_authorize_audit_access_404_when_audit_missing() -> None:
    session = _FakeSession(results=[None])
    with pytest.raises(HTTPException) as exc_info:
        await authorize_audit_access(uuid.uuid4(), session, None)  # type: ignore[arg-type]
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_authorize_audit_access_returns_audit_when_authorized() -> None:
    audit_id = uuid.uuid4()
    account_id = uuid.uuid4()
    audit = Audit(id=audit_id, account_id=account_id)
    account = Account(id=account_id, company_name="Belk", domain="belk.com")
    session = _FakeSession(results=[audit, account])

    result = await authorize_audit_access(audit_id, session, "belk.com")  # type: ignore[arg-type]
    assert result is audit


@pytest.mark.asyncio
async def test_authorize_audit_access_403_when_domain_not_in_header() -> None:
    audit_id = uuid.uuid4()
    account_id = uuid.uuid4()
    audit = Audit(id=audit_id, account_id=account_id)
    account = Account(id=account_id, company_name="Belk", domain="belk.com")
    session = _FakeSession(results=[audit, account])

    with pytest.raises(HTTPException) as exc_info:
        await authorize_audit_access(audit_id, session, "dell.com")  # type: ignore[arg-type]
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Full endpoint -- FastAPI TestClient, DB session + chat agent both faked
# ---------------------------------------------------------------------------


@pytest.fixture
def client_with_fake_audit():
    audit_id = uuid.uuid4()
    account_id = uuid.uuid4()
    audit = Audit(id=audit_id, account_id=account_id)
    account = Account(id=account_id, company_name="Belk", domain="belk.com")

    async def fake_db_session():
        yield _FakeSession(results=[audit, account])

    from prism_platform.api.deps import db_session

    app.dependency_overrides[db_session] = fake_db_session
    try:
        yield TestClient(app), audit_id
    finally:
        app.dependency_overrides.pop(db_session, None)


def test_chat_endpoint_returns_grounded_answer(client_with_fake_audit) -> None:
    client, audit_id = client_with_fake_audit
    fake_result = ChatAgentResult(
        answer="Belk uses Constructor.io (Source: tech_stack).",
        cited_sections={"tech_stack"},
        retrieved_sections=("tech_stack",),
    )
    with patch(
        "prism_platform.api.routers.chat.run_chat_agent", AsyncMock(return_value=fake_result)
    ):
        resp = client.post(f"/api/v1/audits/{audit_id}/chat", json={"question": "what vendor?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "Belk uses Constructor.io (Source: tech_stack)."
    assert body["cited_sections"] == ["tech_stack"]
    assert body["retrieved_sections"] == ["tech_stack"]


def test_chat_endpoint_rejects_unauthorized_slug(client_with_fake_audit) -> None:
    client, audit_id = client_with_fake_audit
    resp = client.post(
        f"/api/v1/audits/{audit_id}/chat",
        json={"question": "what vendor?"},
        headers={"X-Prism-Authorized-Slugs": "dell.com"},
    )
    assert resp.status_code == 403
