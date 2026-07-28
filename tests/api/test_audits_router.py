"""Tests for the ACL-gated audits router (run-2026-07-14-001, 04-spec.md
§3 [C-2], [C-4], [M-1]; §6). This router had zero prior test coverage --
a pre-existing gap this plan closes as a side effect, not a new
requirement invented here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from prism_platform.api.deps import db_session
from prism_platform.auth.deps import resolve_user_id
from prism_platform.config import settings
from prism_platform.db.models import Account, Audit
from prism_platform.main import app
from tests.api.conftest import FakeQueueSession

# ---------------------------------------------------------------------------
# get_audit -- 404 identical for missing vs denied (Arch Review C-2)
# ---------------------------------------------------------------------------


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


def test_get_audit_404_identical_for_missing_and_denied() -> None:
    missing_id = uuid.uuid4()
    session_missing = FakeQueueSession(results=[None])
    client = _client_with_session(session_missing, user_id="user_a")
    try:
        resp_missing = client.get(f"/api/v1/audits/{missing_id}")
    finally:
        _clear_overrides()
    assert resp_missing.status_code == 404

    settings.acl_enforcement_enabled = True
    denied_audit = Audit(id=uuid.uuid4(), account_id=uuid.uuid4(), user_id="user_owner")
    session_denied = FakeQueueSession(results=[denied_audit, None])
    client = _client_with_session(session_denied, user_id="user_stranger")
    try:
        resp_denied = client.get(f"/api/v1/audits/{denied_audit.id}")
    finally:
        _clear_overrides()
    assert resp_denied.status_code == 404
    # One status code, identical body shape -- denial can't be
    # distinguished from non-existence by content either.
    assert resp_missing.json() == resp_denied.json()


def test_get_audit_returns_data_for_owner() -> None:
    audit = Audit(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        user_id="user_owner",
        status="completed",
        created_at=datetime.now(UTC),
    )
    account = Account(id=audit.account_id, company_name="Belk", domain="belk.com")
    session = FakeQueueSession(results=[audit, account])
    client = _client_with_session(session, user_id="user_owner")
    try:
        resp = client.get(f"/api/v1/audits/{audit.id}")
    finally:
        _clear_overrides()
    assert resp.status_code == 200
    assert resp.json()["domain"] == "belk.com"


# ---------------------------------------------------------------------------
# create_audit -- stamps real user_id, falls back to "system" (Arch Review C-4)
# ---------------------------------------------------------------------------


def test_create_audit_stamps_real_user_id() -> None:
    session = FakeQueueSession(results=[None])  # no existing account
    client = _client_with_session(session, user_id="user_creator")
    try:
        resp = client.post("/api/v1/audits/", json={"domain": "belk.com", "company_name": "Belk"})
    finally:
        _clear_overrides()
    assert resp.status_code == 201
    created_audits = [obj for obj in session.flushed if isinstance(obj, Audit)]
    assert len(created_audits) == 1
    assert created_audits[0].user_id == "user_creator"


def test_create_audit_without_assertion_stamps_system() -> None:
    session = FakeQueueSession(results=[None])
    client = _client_with_session(session, user_id=None)
    try:
        resp = client.post("/api/v1/audits/", json={"domain": "dell.com", "company_name": "Dell"})
    finally:
        _clear_overrides()
    assert resp.status_code == 201
    created_audits = [obj for obj in session.flushed if isinstance(obj, Audit)]
    assert len(created_audits) == 1
    assert created_audits[0].user_id == "system"  # back-compat, not a regression


# ---------------------------------------------------------------------------
# get_audit_data_by_slug -- dual-mode resolution (M-1, I-2)
# ---------------------------------------------------------------------------


def test_get_audit_data_by_slug_flag_off_matches_legacy_behavior() -> None:
    """ACL_ENFORCEMENT_ENABLED=false (default): unchanged from pre-ACL
    behavior -- resolves the unscoped pick regardless of visibility."""
    audit = Audit(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        user_id="user_owner",
        status="completed",
        audit_data={"meta": {"slug": "belk"}},
    )
    # unscoped slug lookup finds it; can_user_see then denies (no match) --
    # but the flag is off, so it's returned anyway.
    session = FakeQueueSession(results=[audit, None])
    client = _client_with_session(session, user_id="user_stranger")
    try:
        resp = client.get("/api/v1/audits/by-slug/belk/data")
    finally:
        _clear_overrides()
    assert resp.status_code == 200
    assert resp.json()["audit_data"] == {"meta": {"slug": "belk"}}


def test_get_audit_data_by_slug_scopes_to_visible_set_when_enforced() -> None:
    """ACL_ENFORCEMENT_ENABLED=true: unscoped pick isn't visible to this
    caller -> re-resolves from the caller's visible set (I-2)."""
    settings.acl_enforcement_enabled = True
    newer_foreign_audit = Audit(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        user_id="user_b",
        status="completed",
        audit_data={"meta": {"slug": "belk"}, "owner": "b"},
    )
    older_visible_audit = Audit(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        user_id="user_a",
        status="completed",
        audit_data={"meta": {"slug": "belk"}, "owner": "a"},
    )
    # 1: unscoped slug lookup -> newer_foreign_audit
    # 2: can_user_see's audit_shares lookup for user_a on newer_foreign_audit -> None (no share)
    # 3: visible-scoped slug lookup -> older_visible_audit
    session = FakeQueueSession(results=[newer_foreign_audit, None, [older_visible_audit]])
    client = _client_with_session(session, user_id="user_a")
    try:
        resp = client.get("/api/v1/audits/by-slug/belk/data")
    finally:
        _clear_overrides()
    assert resp.status_code == 200
    assert resp.json()["audit_data"]["owner"] == "a"


def test_get_audit_data_by_slug_404_when_no_completed_audit_at_all() -> None:
    session = FakeQueueSession(results=[None, None])
    client = _client_with_session(session, user_id="user_a")
    try:
        resp = client.get("/api/v1/audits/by-slug/nope/data")
    finally:
        _clear_overrides()
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# share_audit -- owner-only, no `permission` field accepted (§6)
# ---------------------------------------------------------------------------


def test_shares_endpoint_owner_only() -> None:
    audit = Audit(id=uuid.uuid4(), account_id=uuid.uuid4(), user_id="user_owner")
    # require_audit_access fetches the audit; can_user_see then denies for
    # the non-owner caller (flag off, so require_audit_access itself
    # doesn't 404 -- but share_audit's OWN is_owner() check does).
    session = FakeQueueSession(results=[audit, None])
    client = _client_with_session(session, user_id="user_stranger")
    try:
        resp = client.post(
            f"/api/v1/audits/{audit.id}/shares", json={"shared_with_user_id": "user_b"}
        )
    finally:
        _clear_overrides()
    assert resp.status_code == 403


def test_shares_endpoint_succeeds_for_owner() -> None:
    audit = Audit(id=uuid.uuid4(), account_id=uuid.uuid4(), user_id="user_owner")
    session = FakeQueueSession(results=[audit])
    client = _client_with_session(session, user_id="user_owner")
    try:
        resp = client.post(
            f"/api/v1/audits/{audit.id}/shares", json={"shared_with_user_id": "user_b"}
        )
    finally:
        _clear_overrides()
    assert resp.status_code == 201
    assert resp.json()["permission"] == "view"


def test_shares_endpoint_rejects_permission_field() -> None:
    audit = Audit(id=uuid.uuid4(), account_id=uuid.uuid4(), user_id="user_owner")
    session = FakeQueueSession(results=[audit])
    client = _client_with_session(session, user_id="user_owner")
    try:
        resp = client.post(
            f"/api/v1/audits/{audit.id}/shares",
            json={"shared_with_user_id": "user_b", "permission": "edit"},
        )
    finally:
        _clear_overrides()
    assert resp.status_code == 422  # extra="forbid" -- no permission field accepted


def test_shares_endpoint_calls_is_owner_not_inline_check() -> None:
    """Contract: audits.py does not reimplement the ownership comparison
    as a second inline `.user_id ==` outside acl.py (Arch Review I-4)."""
    from pathlib import Path

    import prism_platform.api.routers.audits as audits_module

    source = Path(audits_module.__file__).read_text()
    assert "is_owner(user_id, audit)" in source
    assert ".user_id ==" not in source


# ---------------------------------------------------------------------------
# run_audit / run_audit_local -- explicit non-scope comment present (row 14)
# ---------------------------------------------------------------------------


def test_residual_risk_comment_present_above_run_audit_functions() -> None:
    from pathlib import Path

    import prism_platform.api.routers.audits as audits_module

    source = Path(audits_module.__file__).read_text()
    assert source.count("ACL slice (run-2026-07-14-001): NOT gated") == 2
