"""Tests for core.auth.deps -- the trust-signal channel and the
`require_audit_access` dependency (04-spec.md §4).

Unit tests (signature/exp/jti/fail-closed) need no DB. The user-upsert
proof (@pytest.mark.db) needs a real Postgres -- see tests/auth/conftest.py.
NOT executed in this sandbox (no docker daemon here) -- see
.development-loop/run-2026-07-14-001/07-build-log.md.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid

import pytest
import structlog
from fastapi import HTTPException

from core.auth.deps import require_audit_access, resolve_user_id
from core.config import settings
from core.db.models import Audit
from tests.auth.conftest import skip_if_no_docker

TEST_SECRET = "test-secret-do-not-use-in-prod"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _mint(
    *,
    user_id: str = "user_a",
    email: str = "a@example.com",
    jti: str | None = None,
    exp: float | None = None,
    secret: str = TEST_SECRET,
) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "jti": jti or uuid.uuid4().hex,
        "exp": exp if exp is not None else time.time() + 300,
    }
    payload_bytes = json.dumps(payload).encode()
    sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).digest()
    return f"{_b64url(payload_bytes)}.{_b64url(sig)}"


class _FakeScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _QueueSession:
    """Returns queued results in call order for tests that don't need a
    real Postgres (e.g. require_audit_access's Audit fetch + the
    can_user_see audit_shares lookup it triggers)."""

    def __init__(self, results: list[object]) -> None:
        self._results = list(results)

    async def execute(self, stmt: object) -> _FakeScalarResult:
        return _FakeScalarResult(self._results.pop(0))


@pytest.fixture(autouse=True)
def _set_trust_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "prism_trust_secret", TEST_SECRET)
    monkeypatch.setattr(settings, "acl_enforcement_enabled", False)
    yield


# ---------------------------------------------------------------------------
# resolve_user_id -- fail-closed on anything invalid/missing (no DB needed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_header_returns_none() -> None:
    result = await resolve_user_id(session=object(), x_prism_user_assertion=None)  # type: ignore[arg-type]
    assert result is None


@pytest.mark.asyncio
async def test_invalid_assertion_denies_not_raises() -> None:
    """Malformed input -> None, never an exception (04-spec.md §4)."""
    result = await resolve_user_id(session=object(), x_prism_user_assertion="not-a-valid-assertion")  # type: ignore[arg-type]
    assert result is None


@pytest.mark.asyncio
async def test_tampered_signature_returns_none() -> None:
    good = _mint()
    payload_b64, _sig_b64 = good.split(".", 1)
    tampered = f"{payload_b64}.{_b64url(b'not-the-real-signature-bytes!!!!')}"
    result = await resolve_user_id(session=object(), x_prism_user_assertion=tampered)  # type: ignore[arg-type]
    assert result is None


@pytest.mark.asyncio
async def test_wrong_secret_returns_none() -> None:
    assertion = _mint(secret="a-different-secret")
    result = await resolve_user_id(session=object(), x_prism_user_assertion=assertion)  # type: ignore[arg-type]
    assert result is None


@pytest.mark.asyncio
async def test_expired_assertion_returns_none() -> None:
    assertion = _mint(exp=time.time() - 10)
    result = await resolve_user_id(session=object(), x_prism_user_assertion=assertion)  # type: ignore[arg-type]
    assert result is None


@pytest.mark.asyncio
async def test_missing_secret_configured_denies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "prism_trust_secret", "")
    assertion = _mint()
    result = await resolve_user_id(session=object(), x_prism_user_assertion=assertion)  # type: ignore[arg-type]
    assert result is None


# ---------------------------------------------------------------------------
# jti replay defense + user upsert -- @pytest.mark.db (real Postgres)
# ---------------------------------------------------------------------------


@skip_if_no_docker
@pytest.mark.asyncio
@pytest.mark.db
async def test_jti_replay_rejected(async_session) -> None:
    """First use of a jti succeeds; second use of the SAME jti is
    rejected even with a valid, unexpired signature (Arch Review I-5)."""
    jti = uuid.uuid4().hex
    assertion = _mint(user_id="user_replay", jti=jti)

    first = await resolve_user_id(session=async_session, x_prism_user_assertion=assertion)
    assert first == "user_replay"

    second = await resolve_user_id(session=async_session, x_prism_user_assertion=assertion)
    assert second is None


@skip_if_no_docker
@pytest.mark.asyncio
@pytest.mark.db
async def test_verified_assertion_upserts_user_row(async_session) -> None:
    """A verified assertion with email upserts a `users` row BEFORE
    resolve_user_id returns -- proven by then successfully inserting a
    dependent audit_shares row with that user_id (Arch Review C-3)."""
    from sqlalchemy import text

    assertion = _mint(user_id="user_provisioned", email="provisioned@example.com")
    resolved = await resolve_user_id(session=async_session, x_prism_user_assertion=assertion)
    assert resolved == "user_provisioned"

    row = (
        await async_session.execute(text("SELECT email FROM users WHERE id = 'user_provisioned'"))
    ).one_or_none()
    assert row is not None
    assert row[0] == "provisioned@example.com"

    # FK-dependent insert (audit_shares.created_by references users.id)
    # must now succeed -- this is the exact failure mode C-3 named.
    account_id = uuid.uuid4()
    audit_id = uuid.uuid4()
    await async_session.execute(
        text("INSERT INTO accounts (id, company_name, domain) VALUES (:id, 'Belk', 'belk.com')"),
        {"id": account_id},
    )
    await async_session.execute(
        text(
            "INSERT INTO audits (id, account_id, user_id, status) "
            "VALUES (:id, :account_id, 'user_provisioned', 'completed')"
        ),
        {"id": audit_id, "account_id": account_id},
    )
    await async_session.execute(
        text(
            "INSERT INTO audit_shares (audit_id, shared_with_user_id, permission, created_by) "
            "VALUES (:audit_id, 'user_provisioned', 'view', 'user_provisioned')"
        ),
        {"audit_id": audit_id},
    )
    await async_session.commit()


# ---------------------------------------------------------------------------
# require_audit_access -- 404 for missing OR denied; flag semantics (§10)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_audit_access_404_when_audit_missing() -> None:
    session = _QueueSession(results=[None])
    with pytest.raises(HTTPException) as exc_info:
        await require_audit_access(uuid.uuid4(), session, "user_a")  # type: ignore[arg-type]
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_require_audit_access_flag_off_logs_deny_but_returns_audit() -> None:
    audit = Audit(id=uuid.uuid4(), account_id=uuid.uuid4(), user_id="user_owner")
    session = _QueueSession(results=[audit, None])  # audit fetch, then audit_shares lookup
    with structlog.testing.capture_logs() as cap_logs:
        result = await require_audit_access(audit.id, session, "user_stranger")  # type: ignore[arg-type]
    assert result is audit  # flag off -- request still succeeds despite deny
    deny_logs = [e for e in cap_logs if e.get("decision") == "deny"]
    assert len(deny_logs) >= 1


@pytest.mark.asyncio
async def test_require_audit_access_flag_on_denies_with_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "acl_enforcement_enabled", True)
    audit = Audit(id=uuid.uuid4(), account_id=uuid.uuid4(), user_id="user_owner")
    session = _QueueSession(results=[audit, None])
    with pytest.raises(HTTPException) as exc_info:
        await require_audit_access(audit.id, session, "user_stranger")  # type: ignore[arg-type]
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_require_audit_access_flag_on_allows_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "acl_enforcement_enabled", True)
    audit = Audit(id=uuid.uuid4(), account_id=uuid.uuid4(), user_id="user_owner")
    session = _QueueSession(results=[audit])
    result = await require_audit_access(audit.id, session, "user_owner")  # type: ignore[arg-type]
    assert result is audit
