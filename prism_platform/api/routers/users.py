"""PRISM Users Router — tenant identity upsert (Clerk-mirrored).

Loopback-trusted: reachable ONLY at 127.0.0.1:8000 (never Caddy-exposed). The
Next.js server (holding a Clerk-verified session) is the only caller.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from prism_platform.api.deps import DbSession
from prism_platform.db.models import User

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()


class UpsertUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    email: str | None = None
    name: str | None = None
    org_id: str | None = None


class UpsertUserResponse(BaseModel):
    id: str
    created: bool
    updated: bool


@router.post("/upsert", response_model=UpsertUserResponse)
async def upsert_user(body: UpsertUserRequest, session: DbSession) -> UpsertUserResponse:
    """Insert or refresh a tenant-identity row keyed by Clerk userId. Idempotent."""
    try:
        result = await session.execute(select(User).where(User.id == body.id))
        user = result.scalar_one_or_none()

        if user is None:
            session.add(User(id=body.id, email=body.email, name=body.name, org_id=body.org_id))
            await session.flush()
            logger.info("upsert_user.created", user_id=body.id)
            return UpsertUserResponse(id=body.id, created=True, updated=False)

        user.email = body.email
        user.name = body.name
        if body.org_id is not None:
            user.org_id = body.org_id
        await session.flush()
        logger.info("upsert_user.updated", user_id=body.id)
        return UpsertUserResponse(id=body.id, created=False, updated=True)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("upsert_user.failed", error=str(exc), user_id=body.id)
        raise HTTPException(status_code=500, detail="User upsert failed.") from exc
