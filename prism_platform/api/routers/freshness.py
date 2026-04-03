"""PRISM Freshness Router — module staleness tracking per account."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from prism_platform.api.deps import DbSession
from prism_platform.config import settings
from prism_platform.core.domain_normalizer import normalize_domain
from prism_platform.db.models import Account, Audit, ModuleExecution

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ModuleFreshness(BaseModel):
    """Freshness status of a single module."""

    model_config = ConfigDict(extra="forbid")

    module_name: str
    completed_at: str | None
    days_old: int | None
    stale: bool
    staleness_threshold_days: int


class FreshnessResponse(BaseModel):
    """Full freshness report for an account domain."""

    model_config = ConfigDict(extra="forbid")

    domain: str
    last_full_audit: str | None  # ISO timestamp
    days_since_audit: int | None
    modules: list[ModuleFreshness]
    stale_modules: list[str]
    fresh_modules: list[str]
    recommendation: str  # "no_data", "data_is_fresh", "selective_refresh", "full_rerun"


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/{domain}/freshness", response_model=FreshnessResponse)
async def get_freshness(domain: str, session: DbSession) -> FreshnessResponse:
    """Return freshness status for every tracked module on a given domain."""
    domain = normalize_domain(domain)
    logger.info("get_freshness.start", domain=domain)
    try:
        # 1. Look up the account
        result = await session.execute(select(Account).where(Account.domain == domain))
        account = result.scalar_one_or_none()

        if account is None:
            logger.warning("get_freshness.account_not_found", domain=domain)
            raise HTTPException(status_code=404, detail=f"Account not found for domain: {domain}")

        # 2. Find the latest audit for the account
        audit_result = await session.execute(
            select(Audit)
            .where(Audit.account_id == account.id)
            .order_by(Audit.created_at.desc())
            .limit(1)
        )
        latest_audit = audit_result.scalar_one_or_none()

        now = datetime.now(UTC)
        last_full_audit: str | None = None
        days_since_audit: int | None = None

        if latest_audit is not None and latest_audit.completed_at is not None:
            last_full_audit = latest_audit.completed_at.isoformat()
            days_since_audit = (now - latest_audit.completed_at).days
        elif latest_audit is not None and latest_audit.created_at is not None:
            last_full_audit = latest_audit.created_at.isoformat()
            days_since_audit = (now - latest_audit.created_at).days

        # 3. For each module in staleness_thresholds, find latest successful execution
        modules: list[ModuleFreshness] = []
        stale_modules: list[str] = []
        fresh_modules: list[str] = []

        for module_name, threshold_days in settings.staleness_thresholds.items():
            exec_result = await session.execute(
                select(ModuleExecution)
                .where(
                    ModuleExecution.domain == domain,
                    ModuleExecution.module_name == module_name,
                    ModuleExecution.status.in_(["success", "partial"]),
                )
                .order_by(ModuleExecution.completed_at.desc())
                .limit(1)
            )
            latest_exec = exec_result.scalar_one_or_none()

            completed_at_str: str | None = None
            days_old: int | None = None
            stale = True  # default to stale if no data

            if latest_exec is not None and latest_exec.completed_at is not None:
                completed_at_str = latest_exec.completed_at.isoformat()
                days_old = (now - latest_exec.completed_at).days
                stale = days_old > threshold_days

            if stale:
                stale_modules.append(module_name)
            else:
                fresh_modules.append(module_name)

            modules.append(
                ModuleFreshness(
                    module_name=module_name,
                    completed_at=completed_at_str,
                    days_old=days_old,
                    stale=stale,
                    staleness_threshold_days=threshold_days,
                )
            )

        # 4. Build recommendation
        total_modules = len(settings.staleness_thresholds)
        stale_count = len(stale_modules)

        if latest_audit is None:
            recommendation = "no_data"
        elif stale_count == 0:
            recommendation = "data_is_fresh"
        elif (
            days_since_audit is not None and days_since_audit > 180
        ) or stale_count > total_modules * 0.6:
            recommendation = "full_rerun"
        else:
            recommendation = "selective_refresh"

        response = FreshnessResponse(
            domain=domain,
            last_full_audit=last_full_audit,
            days_since_audit=days_since_audit,
            modules=modules,
            stale_modules=stale_modules,
            fresh_modules=fresh_modules,
            recommendation=recommendation,
        )

        logger.info(
            "get_freshness.done",
            domain=domain,
            stale_count=stale_count,
            fresh_count=len(fresh_modules),
            recommendation=recommendation,
        )
        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_freshness.failed", error=str(exc), domain=domain)
        raise HTTPException(status_code=500, detail="Failed to compute freshness.") from exc
