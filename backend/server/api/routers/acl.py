"""PRISM ACL Router — GET /api/v1/acl/visible (04-spec.md §5).

The proxy calls this to build "which audits/slugs can this Clerk user
see" before it has a specific `audit_id` in hand (e.g. for the accounts
list).
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.auth.deps import resolve_user_id
from core.auth.queries import visible_audit_ids_for_user
from server.api.deps import DbSession

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()


class VisibleAuditsResponse(BaseModel):
    """Response for GET /api/v1/acl/visible (04-spec.md §5 [I-7])."""

    visible_audit_ids: list[str]


@router.get("/visible", response_model=VisibleAuditsResponse)
async def get_visible_audits(
    session: DbSession,
    user_id_param: Annotated[str, Query(alias="user_id")],
    caller_user_id: Annotated[str | None, Depends(resolve_user_id)],
) -> VisibleAuditsResponse:
    """The set of audit_ids where `is_owner()` or an `audit_shares` row
    resolves true for the caller.

    Requires a valid `X-Prism-User-Assertion` whose `user_id` claim
    matches the `user_id` query param exactly -- a mismatch is 403, not a
    substitution opportunity. Does NOT accept an unauthenticated `user_id`
    param from any loopback caller (04-spec.md §5's explicit disclosure-
    oracle warning).
    """
    if caller_user_id is None or caller_user_id != user_id_param:
        logger.info(
            "acl.decision",
            user_id=caller_user_id,
            audit_id=None,
            decision="deny",
            reason="no_match",
        )
        raise HTTPException(
            status_code=403, detail="user_id does not match the caller's assertion."
        )

    audit_ids = await visible_audit_ids_for_user(caller_user_id, session)
    return VisibleAuditsResponse(visible_audit_ids=[str(a) for a in audit_ids])
