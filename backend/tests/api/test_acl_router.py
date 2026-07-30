"""Tests for GET /api/v1/acl/visible (run-2026-07-14-001, 04-spec.md §5)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from core.auth.deps import resolve_user_id
from server.api.deps import db_session
from server.main import app
from tests.api.conftest import FakeQueueSession


def _client_with_session(session, *, user_id: str | None) -> TestClient:
    async def fake_db_session():
        yield session

    app.dependency_overrides[db_session] = fake_db_session
    app.dependency_overrides[resolve_user_id] = lambda: user_id
    return TestClient(app)


def _clear_overrides() -> None:
    app.dependency_overrides.pop(db_session, None)
    app.dependency_overrides.pop(resolve_user_id, None)


def test_visible_rejects_user_id_mismatch() -> None:
    """Caller's assertion user_id must equal the user_id query param
    exactly -- a mismatch is 403, not a substitution opportunity."""
    session = FakeQueueSession(results=[])
    client = _client_with_session(session, user_id="user_a")
    try:
        resp = client.get("/api/v1/acl/visible", params={"user_id": "user_b"})
    finally:
        _clear_overrides()
    assert resp.status_code == 403


def test_visible_rejects_unauthenticated_caller() -> None:
    """No assertion at all (user_id=None) -> 403, never a substitution."""
    session = FakeQueueSession(results=[])
    client = _client_with_session(session, user_id=None)
    try:
        resp = client.get("/api/v1/acl/visible", params={"user_id": "user_a"})
    finally:
        _clear_overrides()
    assert resp.status_code == 403


def test_visible_response_shape() -> None:
    audit_id_1 = uuid.uuid4()
    audit_id_2 = uuid.uuid4()
    session = FakeQueueSession(results=[[audit_id_1, audit_id_2]])
    client = _client_with_session(session, user_id="user_a")
    try:
        resp = client.get("/api/v1/acl/visible", params={"user_id": "user_a"})
    finally:
        _clear_overrides()
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"visible_audit_ids"}
    assert set(body["visible_audit_ids"]) == {str(audit_id_1), str(audit_id_2)}
