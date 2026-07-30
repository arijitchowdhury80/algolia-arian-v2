"""PRISM Chat Router — Task 5 (Track C.3) embedded, grounded chat agent.

POST /api/v1/audits/{audit_id}/chat -- takes a question, retrieves grounding
chunks from `report_chunks` (pgvector cosine similarity), and answers via a
plain `claude -p` invocation with section-name citation discipline. See
server/pipeline/chat_agent.py and retrieval.py for the mechanism.

Auth (run-2026-07-14-001, 04-spec.md §3 [C-1]): access is gated by the one
shared `require_audit_access` dependency (prism_platform/auth/deps.py) --
no second wrapper. This replaces the old `authorize_audit_access`/
`check_slug_authorization` pair (a second, independent ACL implementation
the architecture review flagged as a drift risk); both are deleted
entirely, not left as dead code.
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from core.auth.deps import require_audit_access, resolve_user_id
from core.db.models import Audit
from server.api.deps import DbSession
from server.pipeline.chat_agent import run_chat_agent

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    """Body for POST /api/v1/audits/{audit_id}/chat."""

    model_config = ConfigDict(extra="forbid")

    question: str


class ChatResponse(BaseModel):
    """Grounded answer + its citations, for the SPA chat widget."""

    answer: str
    cited_sections: list[str]
    retrieved_sections: list[str]


@router.post("/{audit_id}/chat", response_model=ChatResponse)
async def chat_with_audit(
    body: ChatRequest,
    session: DbSession,
    audit: Annotated[Audit, Depends(require_audit_access)],
    user_id: Annotated[str | None, Depends(resolve_user_id)],
) -> ChatResponse:
    """Answer a question grounded in `audit`'s report_chunks."""
    result = await run_chat_agent(session=session, question=body.question, audit_id=audit.id)
    logger.info(
        "chat_answer",
        audit_id=str(audit.id),
        user_id=user_id,
        retrieved=result.retrieved_sections,
        cited=sorted(result.cited_sections),
    )
    return ChatResponse(
        answer=result.answer,
        cited_sections=sorted(result.cited_sections),
        retrieved_sections=list(result.retrieved_sections),
    )
