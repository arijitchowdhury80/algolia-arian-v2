"""Tests for the ACL-gated accounts router (run-2026-07-14-001, 04-spec.md
§3 rows 4-5). This router had zero prior test coverage -- a pre-existing
gap this plan closes as a side effect, not a new requirement invented
here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from core.auth.deps import resolve_user_id
from core.config import settings
from core.db.models import Account, Audit
from server.api.deps import db_session
from server.main import app
from tests.api.conftest import FakeQueueSession


@pytest.fixture(autouse=True)
def _reset_acl_flag():
    original = settings.acl_enforcement_enabled
    yield
    settings.acl_enforcement_enabled = original


def _client_with_session(session, *, user_id: str | None) -> TestClient:
    async def fake_db_session():
        yield session

    app.dependency_overrides[db_session] = fake_db_session
    app.dependency_overrides[resolve_user_id] = lambda: user_id
    return TestClient(app)


def _clear_overrides() -> None:
    app.dependency_overrides.pop(db_session, None)
    app.dependency_overrides.pop(resolve_user_id, None)


def test_list_accounts_flag_off_matches_legacy_behavior() -> None:
    """ACL_ENFORCEMENT_ENABLED=false (default): unchanged from pre-ACL
    behavior -- returns the most-recent audit overall, no visibility
    filter, no latest_visible_audit_per_account call."""
    account = Account(id=uuid.uuid4(), company_name="Belk", domain="belk.com")
    audit = Audit(
        id=uuid.uuid4(),
        account_id=account.id,
        user_id="user_owner",
        status="completed",
        created_at=datetime.now(UTC),
    )
    # 1: select(Account) list, 2: per-account latest-audit lookup (flag off)
    session = FakeQueueSession(results=[[account], audit])
    client = _client_with_session(session, user_id="user_stranger")
    try:
        resp = client.get("/api/v1/accounts/")
    finally:
        _clear_overrides()
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["status"] == "completed"  # visible to everyone while unenforced


def test_list_accounts_flag_on_shows_none_status_for_invisible_audit() -> None:
    """ACL_ENFORCEMENT_ENABLED=true: an account whose only audit is NOT
    visible to the caller still lists (status "none"), not omitted (Arch
    Review I-1/I-2, 04-spec.md §3 row 4)."""
    settings.acl_enforcement_enabled = True
    account = Account(id=uuid.uuid4(), company_name="Belk", domain="belk.com")
    # 1: select(Account) list, 2: latest_visible_audit_per_account's single
    # windowed query -- empty for this caller (no visible audits at all).
    session = FakeQueueSession(results=[[account], []])
    client = _client_with_session(session, user_id="user_stranger")
    try:
        resp = client.get("/api/v1/accounts/")
    finally:
        _clear_overrides()
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["status"] == "none"
    assert body[0]["domain"] == "belk.com"  # existence-vs-no-access isn't distinguishable


def test_get_account_results_flag_on_scopes_latest_audit_to_visible_set() -> None:
    settings.acl_enforcement_enabled = True
    account = Account(id=uuid.uuid4(), company_name="Belk", domain="belk.com")
    # 1: select(Account) all, 2: visible-scoped latest-audit lookup -> []
    # (no ModuleExecution rows follow since we short-circuit before that
    # query in this fake -- module results query still runs but returns
    # nothing relevant to this assertion)
    session = FakeQueueSession(results=[[account], [], []])
    client = _client_with_session(session, user_id="user_stranger")
    try:
        resp = client.get("/api/v1/accounts/belk.com/results")
    finally:
        _clear_overrides()
    assert resp.status_code == 200
    body = resp.json()
    assert body["audit_status"] is None  # no visible audit for this caller
