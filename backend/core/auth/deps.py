"""Trust-signal channel: verifies the signed X-Prism-User-Assertion header
minted by the prism-hub proxy (04-spec.md §4) and exposes the single
`require_audit_access` dependency every ACL-gated endpoint depends on
(§3) -- no second wrapper.

Format: ``base64url(payload_json).base64url(hmac_sha256(payload_json,
secret))``, ``payload = {"user_id", "email", "jti", "exp"}``. Verification
is fail-closed end to end: any malformed/tampered/expired/replayed
assertion resolves to ``user_id = None`` (the deny path in
``core.auth.acl.can_user_see``), never an exception that could
be caught into an open state.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.acl import can_user_see
from core.config import settings
from core.db.models import Audit, SeenAssertion, User
from server.api.deps import DbSession

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

ASSERTION_HEADER = "X-Prism-User-Assertion"


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _verify_assertion(raw: str) -> dict[str, object] | None:
    """Pure verification of the HMAC-signed assertion payload. Returns the
    decoded payload dict on success, ``None`` on ANY failure -- malformed
    input, bad signature, expired, missing secret. Never raises (§4
    fail-closed on ACL-lookup unavailability)."""
    secret = settings.prism_trust_secret
    if not secret:
        return None

    try:
        payload_b64, sig_b64 = raw.split(".", 1)
        payload_bytes = _b64url_decode(payload_b64)
        sig = _b64url_decode(sig_b64)
    except (ValueError, binascii.Error):
        return None

    expected_sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected_sig):
        return None

    try:
        payload = json.loads(payload_bytes)
    except (ValueError, TypeError):
        return None

    if not isinstance(payload, dict):
        return None

    exp = payload.get("exp")
    if not isinstance(exp, (int, float)) or exp < time.time():
        return None

    if not payload.get("user_id") or not payload.get("jti"):
        return None

    return payload


async def _check_and_mark_jti_seen(jti: str, exp: float, session: AsyncSession) -> bool:
    """True iff this jti has NOT been seen before -- i.e. this call is the
    first use and it is now recorded. False on replay. Backed by
    `seen_assertions` (a table, not an in-memory LRU) so the replay window
    survives a process restart and is correct under >1 uvicorn worker
    (06-plan.md §4 design note)."""
    expires_at = datetime.fromtimestamp(exp, tz=UTC)
    stmt = (
        pg_insert(SeenAssertion)
        .values(jti=jti, expires_at=expires_at)
        .on_conflict_do_nothing(index_elements=["jti"])
    )
    result = await session.execute(stmt)
    await session.commit()
    rowcount: int = result.rowcount  # type: ignore[attr-defined]
    return rowcount == 1


async def _upsert_user(user_id: str, email: str, session: AsyncSession) -> None:
    """Provision a real `users` row on first sight of a verified assertion
    (04-spec.md §4 [C3]) -- BEFORE any FK-dependent insert runs, so
    `create_audit`'s and `audit_shares`' FK inserts always have a
    satisfying `users` row."""
    stmt = (
        pg_insert(User)
        .values(id=user_id, email=email)
        .on_conflict_do_update(index_elements=["id"], set_={"email": email})
    )
    await session.execute(stmt)
    await session.commit()


async def resolve_user_id(
    session: DbSession,
    x_prism_user_assertion: Annotated[str | None, Header()] = None,
) -> str | None:
    """Verify the trust assertion; return the verified user_id or None.

    Fail-closed: any invalid/missing/replayed assertion -> None, never an
    exception (04-spec.md §4).
    """
    if not x_prism_user_assertion:
        return None

    payload = _verify_assertion(x_prism_user_assertion)
    if payload is None:
        logger.info("acl.assertion_rejected", reason="invalid_or_expired")
        return None

    user_id = str(payload["user_id"])
    email = str(payload.get("email") or "")
    jti = str(payload["jti"])
    exp = float(payload["exp"])  # type: ignore[arg-type]

    try:
        first_use = await _check_and_mark_jti_seen(jti, exp, session)
    except Exception as exc:
        logger.error("acl.jti_check_failed", error=str(exc))
        return None

    if not first_use:
        logger.info("acl.assertion_rejected", reason="replayed_jti", user_id=user_id)
        return None

    try:
        await _upsert_user(user_id, email, session)
    except Exception as exc:
        logger.error("acl.user_upsert_failed", error=str(exc), user_id=user_id)
        return None

    return user_id


async def require_audit_access(
    audit_id: uuid.UUID,
    session: DbSession,
    user_id: Annotated[str | None, Depends(resolve_user_id)],
) -> Audit:
    """Fetch the audit; 404 (never 403) if missing OR not `can_user_see()`
    -- one status code for both, so denial can't be used as an existence
    oracle. The one call site every gated endpoint depends on
    (04-spec.md §3).

    While `settings.acl_enforcement_enabled` is False (default,
    04-spec.md §10), `can_user_see()` still runs and logs its decision,
    but a deny is not acted on -- ships dark.
    """
    result = await session.execute(select(Audit).where(Audit.id == audit_id))
    audit = result.scalar_one_or_none()

    if audit is None:
        logger.info(
            "acl.decision",
            user_id=user_id,
            audit_id=str(audit_id),
            decision="deny",
            reason="not_found",
        )
        raise HTTPException(status_code=404, detail="Audit not found.")

    allowed = await can_user_see(user_id, audit, session)

    if not allowed and settings.acl_enforcement_enabled:
        raise HTTPException(status_code=404, detail="Audit not found.")

    return audit
