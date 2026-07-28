"""PRISM Chat Router — Task 5 (Track C.3) embedded, grounded chat agent.

POST /api/v1/audits/{audit_id}/chat -- takes a question, retrieves grounding
chunks from `report_chunks` (pgvector cosine similarity), and answers via a
plain `claude -p` invocation with section-name citation discipline. See
prism_platform/pipeline/chat_agent.py and retrieval.py for the mechanism.

Patch #6 (auth) -- see `authorize_audit_access`'s docstring: this repo has
NO Clerk/auth layer at all (Clerk lives entirely in prism-hub, the separate
frontend repo, and today only gates page loads, not `/api/*` calls -- see
`~/prism/server/chat-proxy.mjs`'s `PUBLIC_PREFIXES`). `authorize_audit_access`
is the wire point for a per-user-slug authorization check once one exists
upstream; it is intentionally fail-open when the placeholder header is
absent, matching the real (unenforced) state of the stack today -- see the
task-5 report for the concrete gap and test plan.
"""

from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from prism_platform.api.deps import DbSession
from prism_platform.db.models import Account, Audit
from prism_platform.pipeline.chat_agent import run_chat_agent

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()

# Placeholder header a trusted upstream proxy would set after validating a
# Clerk session server-side, e.g. `X-Prism-Authorized-Slugs: dell.com,belk.com`.
AUTHORIZED_SLUGS_HEADER = "X-Prism-Authorized-Slugs"


class ChatRequest(BaseModel):
    """Body for POST /api/v1/audits/{audit_id}/chat."""

    model_config = ConfigDict(extra="forbid")

    question: str


class ChatResponse(BaseModel):
    """Grounded answer + its citations, for the SPA chat widget."""

    answer: str
    cited_sections: list[str]
    retrieved_sections: list[str]


def check_slug_authorization(domain: str, authorized_slugs_header: str | None) -> None:
    """Pure authorization decision (no I/O) -- raises HTTPException(403) if
    the caller supplied an authorized-slugs allowlist and `domain` isn't in
    it. No header at all -> fail OPEN (see module docstring: this is the
    real, unenforced state of the stack today, not a regression)."""
    if authorized_slugs_header is None:
        return
    allowed = {s.strip().lower() for s in authorized_slugs_header.split(",") if s.strip()}
    if domain.lower() not in allowed:
        raise HTTPException(status_code=403, detail=f"not authorized for domain '{domain}'")


async def authorize_audit_access(
    audit_id: uuid.UUID,
    session: DbSession,
    x_prism_authorized_slugs: Annotated[str | None, Header()] = None,
) -> Audit:
    """Fetch the audit (404 if missing) and apply `check_slug_authorization`
    against its account's domain."""
    audit = (await session.execute(select(Audit).where(Audit.id == audit_id))).scalar_one_or_none()
    if audit is None:
        raise HTTPException(status_code=404, detail="audit not found")

    account = (
        await session.execute(select(Account).where(Account.id == audit.account_id))
    ).scalar_one_or_none()
    domain = account.domain if account else ""
    check_slug_authorization(domain, x_prism_authorized_slugs)
    return audit


@router.post("/{audit_id}/chat", response_model=ChatResponse)
async def chat_with_audit(
    body: ChatRequest,
    session: DbSession,
    audit: Annotated[Audit, Depends(authorize_audit_access)],
) -> ChatResponse:
    """Answer a question grounded in `audit`'s report_chunks."""
    result = await run_chat_agent(session=session, question=body.question, audit_id=audit.id)
    logger.info(
        "chat_answer",
        audit_id=str(audit.id),
        retrieved=result.retrieved_sections,
        cited=sorted(result.cited_sections),
    )
    return ChatResponse(
        answer=result.answer,
        cited_sections=sorted(result.cited_sections),
        retrieved_sections=list(result.retrieved_sections),
    )
