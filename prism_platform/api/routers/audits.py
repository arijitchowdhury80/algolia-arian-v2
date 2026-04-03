"""PRISM Audit Router — create, read, and trigger audits."""

from __future__ import annotations

import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from prism_platform.api.deps import DbSession, TemporalDep
from prism_platform.config import settings
from prism_platform.core.domain_normalizer import normalize_domain
from prism_platform.db.models import Account, Audit
from prism_platform.orchestrator.workflows import AuditInput, AuditWorkflow

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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/", response_model=AuditResponse, status_code=201)
async def create_audit(body: CreateAuditRequest, session: DbSession) -> AuditResponse:
    """Create a new audit (and its parent account if needed)."""
    domain = normalize_domain(body.domain)
    logger.info("create_audit.start", domain=domain, raw_domain=body.domain, company_name=body.company_name)
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

        audit = Audit(account_id=account.id)
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
        logger.info("create_audit.done", audit_id=str(audit.id))
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("create_audit.failed", error=str(exc), domain=domain)
        raise HTTPException(status_code=500, detail="Failed to create audit.") from exc


@router.get("/{audit_id}", response_model=AuditResponse)
async def get_audit(audit_id: uuid.UUID, session: DbSession) -> AuditResponse:
    """Fetch an audit by ID."""
    logger.info("get_audit.start", audit_id=str(audit_id))
    try:
        result = await session.execute(select(Audit).where(Audit.id == audit_id))
        audit = result.scalar_one_or_none()

        if audit is None:
            logger.warning("get_audit.not_found", audit_id=str(audit_id))
            raise HTTPException(status_code=404, detail="Audit not found.")

        # Fetch associated account for domain / company_name
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
        logger.info("get_audit.done", audit_id=str(audit_id))
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_audit.failed", error=str(exc), audit_id=str(audit_id))
        raise HTTPException(status_code=500, detail="Failed to fetch audit.") from exc


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
