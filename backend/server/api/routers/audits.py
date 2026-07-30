"""PRISM Audit Router — create, read, and trigger audits."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from core.auth.acl import can_user_see, is_owner
from core.auth.deps import require_audit_access, resolve_user_id
from core.auth.queries import visible_audits_select
from core.config import settings
from core.db.models import Account, Audit, AuditShare
from core.db.session import async_session_factory
from core.domain_normalizer import normalize_domain
from server.api.deps import DbSession, TemporalDep
from server.orchestrator.pipeline import run_pipeline
from server.orchestrator.workflows import AuditInput, AuditWorkflow

# Hold references to detached background pipeline tasks so they aren't GC'd
# mid-run (asyncio only keeps weak refs to tasks).
_BG_TASKS: set[asyncio.Task[None]] = set()

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CreateAuditRequest(BaseModel):
    """Body for POST /api/v1/audits/."""

    model_config = ConfigDict(extra="forbid")

    domain: str
    company_name: str
    ticker: str | None = None
    is_private: bool = False


class AuditResponse(BaseModel):
    """Serialised audit returned from the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    domain: str
    company_name: str
    status: str
    score: float | None = None
    created_at: datetime


class RunAuditRequest(BaseModel):
    """Body for POST /api/v1/audits/{audit_id}/run."""

    model_config = ConfigDict(extra="forbid")

    audit_mode: str = "full"  # "full", "quick", "bulk_triage", "refresh"
    modules_to_run: list[str] | None = None
    skip_modules: list[str] = []
    refresh_modules: list[str] = []


class RunAuditResponse(BaseModel):
    """Response after triggering a Temporal workflow."""

    workflow_id: str
    run_id: str
    status: str


class RunLocalResponse(BaseModel):
    """Response after launching an in-process (Temporal-free) audit run."""

    audit_id: uuid.UUID
    status: str
    audit_mode: str


class ShareAuditRequest(BaseModel):
    """Body for POST /api/v1/audits/{audit_id}/shares (04-spec.md §6).

    No `permission` field: it is hardcoded 'view' server-side, closing the
    "permissive default" risk finding by removing the choice entirely
    rather than defaulting it correctly.
    """

    model_config = ConfigDict(extra="forbid")

    shared_with_user_id: str


class ShareAuditResponse(BaseModel):
    """Response after granting a view share."""

    audit_id: uuid.UUID
    shared_with_user_id: str
    permission: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/", response_model=AuditResponse, status_code=201)
async def create_audit(
    body: CreateAuditRequest,
    session: DbSession,
    user_id: Annotated[str | None, Depends(resolve_user_id)],
) -> AuditResponse:
    """Create a new audit (and its parent account if needed).

    Stamps the real Clerk `user_id` resolved from the trust assertion
    (04-spec.md §1/§3 [C-4]); falls back to `"system"` when no assertion is
    present -- intentional back-compat for anonymous/internal callers, not
    a regression.
    """
    domain = normalize_domain(body.domain)
    logger.info(
        "create_audit.start", domain=domain, raw_domain=body.domain, company_name=body.company_name
    )
    try:
        # Upsert account by domain
        result = await session.execute(select(Account).where(Account.domain == domain))
        account = result.scalar_one_or_none()

        if account is None:
            account = Account(
                company_name=body.company_name,
                domain=domain,
                is_public=not body.is_private,
                ticker=body.ticker,
            )
            session.add(account)
            await session.flush()
            logger.info("create_audit.account_created", account_id=str(account.id))

        audit = Audit(account_id=account.id, user_id=user_id or "system")
        session.add(audit)
        await session.flush()

        response = AuditResponse(
            id=audit.id,
            account_id=account.id,
            domain=domain,
            company_name=body.company_name,
            status=audit.status,
            score=None,
            created_at=audit.created_at,
        )
        logger.info("create_audit.done", audit_id=str(audit.id), user_id=audit.user_id)
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("create_audit.failed", error=str(exc), domain=domain)
        raise HTTPException(status_code=500, detail="Failed to create audit.") from exc


@router.get("/{audit_id}", response_model=AuditResponse)
async def get_audit(
    session: DbSession,
    audit: Annotated[Audit, Depends(require_audit_access)],
) -> AuditResponse:
    """Fetch an audit by ID.

    Access is gated by `require_audit_access` (04-spec.md §3 [C-2]): 404
    for both "doesn't exist" and "exists but not yours" -- one status
    code, no exception, so denial never functions as an existence oracle.
    """
    logger.info("get_audit.start", audit_id=str(audit.id))
    try:
        acct_result = await session.execute(select(Account).where(Account.id == audit.account_id))
        account = acct_result.scalar_one()

        response = AuditResponse(
            id=audit.id,
            account_id=audit.account_id,
            domain=account.domain,
            company_name=account.company_name,
            status=audit.status,
            score=float(audit.score) if audit.score is not None else None,
            created_at=audit.created_at,
        )
        logger.info("get_audit.done", audit_id=str(audit.id))
        return response
    except Exception as exc:
        logger.error("get_audit.failed", error=str(exc), audit_id=str(audit.id))
        raise HTTPException(status_code=500, detail="Failed to fetch audit.") from exc


async def _resolve_audit_by_slug_unscoped(slug: str, session: DbSession) -> Audit | None:
    """Legacy resolution (pre-ACL) -- most-recent completed audit matching
    the slug, with NO visibility filter. This is the flag-off path, so
    this endpoint's behavior is unchanged while
    `ACL_ENFORCEMENT_ENABLED=false` (04-spec.md §10 -- ships dark)."""
    stmt = (
        select(Audit)
        .where(Audit.status == "completed", Audit.audit_data["meta"]["slug"].astext == slug)
        .order_by(Audit.completed_at.desc().nullslast())
        .limit(1)
    )
    audit = (await session.execute(stmt)).scalar_one_or_none()
    if audit is not None:
        return audit

    stmt2 = (
        select(Audit)
        .join(Account, Account.id == Audit.account_id)
        .where(
            Audit.status == "completed",
            (Account.domain == slug) | (Account.domain == f"{slug}.com"),
        )
        .order_by(Audit.completed_at.desc().nullslast())
        .limit(1)
    )
    return (await session.execute(stmt2)).scalar_one_or_none()


async def _resolve_visible_audit_by_slug(
    slug: str, user_id: str | None, session: DbSession
) -> Audit | None:
    """ACL-scoped resolution (04-spec.md §2b/§3 M-1) -- the most recent
    audit visible to `user_id` matching the slug, resolved from the
    VISIBLE set first (not most-recent-overall-then-gate), closing [I-2]."""
    stmt = (
        visible_audits_select(user_id)
        .where(Audit.status == "completed", Audit.audit_data["meta"]["slug"].astext == slug)
        .order_by(Audit.completed_at.desc().nullslast())
        .limit(1)
    )
    audit = (await session.execute(stmt)).scalars().first()
    if audit is not None:
        return audit

    stmt2 = (
        visible_audits_select(user_id)
        .join(Account, Account.id == Audit.account_id)
        .where(
            Audit.status == "completed",
            (Account.domain == slug) | (Account.domain == f"{slug}.com"),
        )
        .order_by(Audit.completed_at.desc().nullslast())
        .limit(1)
    )
    return (await session.execute(stmt2)).scalars().first()


@router.get("/by-slug/{slug}/data")
async def get_audit_data_by_slug(
    slug: str,
    session: DbSession,
    user_id: Annotated[str | None, Depends(resolve_user_id)],
) -> dict[str, Any]:
    """Return the completed audit's full audit_data JSON for a report slug.

    Powers DB-backed report serving: the static report shell fetches this
    at request time so a DB update reflects on the live page with no
    re-render. Resolves by audit_data.meta.slug, then falls back to
    domain == slug(.com).

    Auth (04-spec.md §3 [M-1]): this route has no `audit_id` path param,
    so it cannot use `require_audit_access` as a literal `Depends` -- it
    calls `is_owner`/`can_user_see` inline instead (same functions, called
    directly). Resolution is dual-mode, mirroring `require_audit_access`'s
    own flag semantics:
      - `ACL_ENFORCEMENT_ENABLED=false` (default): resolves exactly as
        before this slice (most-recent completed audit for the slug,
        unscoped) -- ships dark, zero behavior change (§10). The ACL
        decision is still computed and logged (§7), just not acted on.
      - `ACL_ENFORCEMENT_ENABLED=true`: if the unscoped pick isn't visible
        to this caller, re-resolves from the caller's VISIBLE set (§2b) so
        a legitimate owner is never 404'd just because a different user's
        newer audit for the same slug exists ([I-2]).
    """
    audit = await _resolve_audit_by_slug_unscoped(slug, session)
    if audit is None:
        raise HTTPException(status_code=404, detail=f"no completed audit for slug '{slug}'")

    allowed = await can_user_see(user_id, audit, session)

    if not allowed and settings.acl_enforcement_enabled:
        visible_audit = await _resolve_visible_audit_by_slug(slug, user_id, session)
        if visible_audit is None:
            raise HTTPException(status_code=404, detail=f"no completed audit for slug '{slug}'")
        audit = visible_audit

    return {"slug": slug, "audit_data": audit.audit_data}


@router.post("/{audit_id}/shares", response_model=ShareAuditResponse, status_code=201)
async def share_audit(
    body: ShareAuditRequest,
    session: DbSession,
    audit: Annotated[Audit, Depends(require_audit_access)],
    user_id: Annotated[str | None, Depends(resolve_user_id)],
) -> ShareAuditResponse:
    """Grant another user `view` access to this audit (04-spec.md §6).

    Owner-only: sharing is not transitively delegable from an existing
    share in this slice. Uses the same `is_owner()` `can_user_see`
    reuses -- not a second inline `==` comparison ([I-4]). `permission` is
    hardcoded `'view'` server-side; the request body has no `permission`
    field to set at all.
    """
    if not is_owner(user_id, audit):
        logger.info(
            "acl.decision",
            user_id=user_id,
            audit_id=str(audit.id),
            decision="deny",
            reason="not_owner",
        )
        raise HTTPException(status_code=403, detail="Only the audit owner can share it.")

    share = AuditShare(
        audit_id=audit.id,
        shared_with_user_id=body.shared_with_user_id,
        permission="view",
        created_by=user_id or "system",
    )
    session.add(share)
    await session.flush()

    logger.info(
        "acl.decision", user_id=user_id, audit_id=str(audit.id), decision="allow", reason="owner"
    )
    return ShareAuditResponse(
        audit_id=audit.id,
        shared_with_user_id=body.shared_with_user_id,
        permission="view",
    )


# ACL slice (run-2026-07-14-001): NOT gated -- compute-abuse risk accepted
# for this slice. A caller who has or guesses a UUID can re-trigger a real
# pipeline run against an audit they don't own. This is a compute-abuse
# risk, not a disclosure risk (Risk §0.A's scope was read/disclosure
# paths); accepted as residual risk for a follow-on slice, per 04-spec.md
# §3 "explicitly out of scope."
@router.post("/{audit_id}/run", response_model=RunAuditResponse)
async def run_audit(
    audit_id: uuid.UUID,
    body: RunAuditRequest,
    session: DbSession,
    client: TemporalDep,
) -> RunAuditResponse:
    """Trigger the Temporal AuditWorkflow for an existing audit."""
    logger.info(
        "run_audit.start",
        audit_id=str(audit_id),
        audit_mode=body.audit_mode,
        skip_modules=body.skip_modules,
        refresh_modules=body.refresh_modules,
    )
    try:
        # Verify audit exists
        result = await session.execute(select(Audit).where(Audit.id == audit_id))
        audit = result.scalar_one_or_none()
        if audit is None:
            raise HTTPException(status_code=404, detail="Audit not found.")

        acct_result = await session.execute(select(Account).where(Account.id == audit.account_id))
        account = acct_result.scalar_one()

        workflow_id = f"audit-{audit_id}"
        handle = await client.start_workflow(
            AuditWorkflow.run,
            AuditInput(
                audit_id=str(audit_id),
                account_id=str(account.id),
                domain=account.domain,
                company_name=account.company_name,
                ticker=account.ticker,
                is_private=not account.is_public,
                audit_mode=body.audit_mode,
                modules_to_run=body.modules_to_run,
                skip_modules=body.skip_modules,
                refresh_modules=body.refresh_modules,
            ),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        response = RunAuditResponse(
            workflow_id=workflow_id,
            run_id=handle.result_run_id,
            status="started",
        )
        logger.info(
            "run_audit.done",
            workflow_id=workflow_id,
            run_id=handle.result_run_id,
            audit_mode=body.audit_mode,
        )
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("run_audit.failed", error=str(exc), audit_id=str(audit_id))
        raise HTTPException(status_code=500, detail="Failed to start audit workflow.") from exc


async def _set_audit_status(audit_id: uuid.UUID, status: str, *, completed: bool = False) -> None:
    """Update an audit row's status in its own session (background-task safe)."""
    async with async_session_factory() as session:
        res = await session.execute(select(Audit).where(Audit.id == audit_id))
        audit = res.scalar_one_or_none()
        if audit is None:
            return
        audit.status = status
        now = datetime.now(UTC)
        if audit.started_at is None:
            audit.started_at = now
        if completed:
            audit.completed_at = now
        await session.commit()


async def _run_pipeline_bg(audit_input: AuditInput) -> None:
    """Run the in-process pipeline and reflect terminal status on the audit row."""
    audit_id = uuid.UUID(audit_input.audit_id)
    await _set_audit_status(audit_id, "running")
    try:
        result = await run_pipeline(audit_input)
        await _set_audit_status(audit_id, result.status, completed=True)
        logger.info("run_local.done", audit_id=audit_input.audit_id, status=result.status)
    except Exception as exc:
        logger.error("run_local.pipeline_failed", error=str(exc), audit_id=audit_input.audit_id)
        await _set_audit_status(audit_id, "failed", completed=True)


# ACL slice (run-2026-07-14-001): NOT gated -- see the residual-risk comment
# above run_audit; the same compute-abuse gap applies to this in-process
# execution path and is accepted for this slice, per 04-spec.md §3.
@router.post("/{audit_id}/run-local", response_model=RunLocalResponse, status_code=202)
async def run_audit_local(
    audit_id: uuid.UUID,
    body: RunAuditRequest,
    session: DbSession,
) -> RunLocalResponse:
    """Run an existing audit in-process (no Temporal worker required).

    Walks the same wave plan as the Temporal workflow via ``run_pipeline``,
    detached as a background task. Returns 202 immediately; poll
    ``GET /api/v1/audits/{audit_id}`` for status. This is the execution path
    Cass's ``run_audit`` tool calls — modules with deterministic collectors run
    at zero LLM cost; research modules use the configured Perplexity key.
    """
    logger.info("run_local.start", audit_id=str(audit_id), audit_mode=body.audit_mode)
    try:
        result = await session.execute(select(Audit).where(Audit.id == audit_id))
        audit = result.scalar_one_or_none()
        if audit is None:
            raise HTTPException(status_code=404, detail="Audit not found.")

        acct_result = await session.execute(select(Account).where(Account.id == audit.account_id))
        account = acct_result.scalar_one()

        audit_input = AuditInput(
            audit_id=str(audit_id),
            account_id=str(account.id),
            domain=account.domain,
            company_name=account.company_name,
            ticker=account.ticker,
            is_private=not account.is_public,
            audit_mode=body.audit_mode,
            modules_to_run=body.modules_to_run,
            skip_modules=body.skip_modules,
            refresh_modules=body.refresh_modules,
        )

        task = asyncio.create_task(_run_pipeline_bg(audit_input))
        _BG_TASKS.add(task)
        task.add_done_callback(_BG_TASKS.discard)

        return RunLocalResponse(audit_id=audit_id, status="running", audit_mode=body.audit_mode)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("run_local.failed", error=str(exc), audit_id=str(audit_id))
        raise HTTPException(status_code=500, detail="Failed to start local audit run.") from exc
