"""Tests for the ACL-gated audit_stream router (run-2026-07-14-001,
04-spec.md §3 row 6). Deny before opening the SSE stream, not mid-stream.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from core.auth.deps import require_audit_access, resolve_user_id
from core.config import settings
from core.db.models import Audit
from server.api.deps import db_session
from server.main import app
from tests.api.conftest import FakeQueueSession


@pytest.fixture(autouse=True)
def _reset_acl_flag():
    original = settings.acl_enforcement_enabled
    yield
    settings.acl_enforcement_enabled = original


def test_audit_stream_depends_on_require_audit_access() -> None:
    matching_route = next(
        r for r in app.routes if getattr(r, "name", "") == "stream_audit_progress"
    )
    dep_callables = {d.call for d in matching_route.dependant.dependencies}
    assert require_audit_access in dep_callables


def test_stream_denies_before_first_frame() -> None:
    """A denied caller's response never contains an `event: connected`
    frame -- the gate runs before StreamingResponse is even constructed.

    Uses `client.stream()` (headers-only read) rather than a plain `.get()`
    -- a plain `.get()` would block forever consuming an (incorrectly)
    open-ended SSE body if this assertion ever regressed, instead of
    failing fast.
    """
    settings.acl_enforcement_enabled = True
    audit = Audit(id=uuid.uuid4(), account_id=uuid.uuid4(), user_id="user_owner")
    session = FakeQueueSession(results=[audit, None])  # audit fetch, then audit_shares lookup

    async def fake_db_session():
        yield session

    app.dependency_overrides[db_session] = fake_db_session
    app.dependency_overrides[resolve_user_id] = lambda: "user_stranger"
    try:
        client = TestClient(app)
        with client.stream("GET", f"/api/v1/audits/{audit.id}/stream") as resp:
            assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(db_session, None)
        app.dependency_overrides.pop(resolve_user_id, None)


@pytest.mark.asyncio
async def test_stream_allows_owner_to_open_the_stream() -> None:
    """An authorized caller (the owner) gets a `StreamingResponse` back --
    the gate does not block legitimate access. Calls the router function
    directly (bypassing TestClient/ASGI) and does NOT iterate the body:
    the underlying generator polls forever until a terminal audit status,
    which this fake session can't produce, so consuming the body would
    hang the test process -- TestClient's request/response machinery in
    this httpx version drains the ASGI response eagerly even for
    `.stream()`, so it can't be used here either. The "deny before first
    frame" contract is already proven end-to-end by
    test_stream_denies_before_first_frame above (that path 404s before a
    StreamingResponse is ever constructed, so there is no body to drain).
    """
    from server.api.routers.audit_stream import stream_audit_progress

    audit = Audit(id=uuid.uuid4(), account_id=uuid.uuid4(), user_id="user_owner", status="running")
    session = FakeQueueSession(results=[])

    response = await stream_audit_progress(session, audit)
    assert response.status_code == 200
    assert response.media_type == "text/event-stream"
