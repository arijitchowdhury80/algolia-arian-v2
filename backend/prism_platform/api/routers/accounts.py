"""PRISM Accounts Router — list accounts and retrieve module results."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from prism_platform.api.deps import DbSession
from prism_platform.auth.deps import resolve_user_id
from prism_platform.auth.queries import latest_visible_audit_per_account, visible_audits_select
from prism_platform.config import settings
from prism_platform.db.models import Account, Audit, ModuleExecution
from prism_platform.v2.domain_normalizer import normalize_domain

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class AccountResponse(BaseModel):
    """Serialised account for the frontend sidebar."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    company_name: str
    domain: str
    status: str  # "complete", "running", "pending", "none"
    last_audit: str | None = None
    score: float | None = None


class AccountResultsResponse(BaseModel):
    """All module results for a single domain."""

    model_config = ConfigDict(from_attributes=True)

    domain: str
    company_name: str | None = None
    modules: dict[str, Any]  # module_name -> output_json
    last_audit_date: str | None = None
    audit_status: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATUS_PRIORITY: dict[str, int] = {
    "complete": 4,
    "running": 3,
    "pending": 2,
    "none": 0,
}


def _pick_best_account(
    group: list[tuple[Account, str, str | None, float | None]],
) -> AccountResponse:
    """Pick the best account from a group sharing the same normalized domain.

    Each tuple is (account, status, last_audit_date_str, score).

    Priority:
      1. Has a completed audit (status == 'complete') with the most recent date.
      2. Has the highest-priority status.
      3. Has a score.
      4. Has more data populated (legal_name present as heuristic).
    """

    def sort_key(item: tuple[Account, str, str | None, float | None]) -> tuple[int, str, int, int]:
        account, status, last_audit, score = item
        return (
            _STATUS_PRIORITY.get(status, 1),
            last_audit or "",
            1 if score is not None else 0,
            1 if account.legal_name else 0,
        )

    best_account, best_status, best_last_audit, best_score = max(group, key=sort_key)
    return AccountResponse(
        id=str(best_account.id),
        company_name=best_account.company_name,
        domain=best_account.domain,
        status=best_status,
        last_audit=best_last_audit,
        score=best_score,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/", response_model=list[AccountResponse])
async def list_accounts(
    session: DbSession,
    user_id: Annotated[str | None, Depends(resolve_user_id)],
) -> list[AccountResponse]:
    """List all accounts, deduplicated by normalized domain.

    For each unique normalized domain, the account with the most recent
    completed audit (or the richest data) is returned.

    Auth (04-spec.md §3 row 4, §2b, Arch Review I-1): while
    `ACL_ENFORCEMENT_ENABLED=true`, each account's "latest audit" is
    resolved via one joined query for ALL accounts
    (`latest_visible_audit_per_account`), not a per-account
    `can_user_see()` call inside this loop -- filtered to audits visible
    to the requesting user. Accounts with zero visible audits still list
    (status "none"), not omitted. While the flag is false (default), this
    resolves exactly as before this slice -- ships dark (§10).
    """
    logger.info("list_accounts.start")
    try:
        # Get all accounts, excluding test artifacts
        result = await session.execute(
            select(Account)
            .where(
                ~Account.domain.like("test-%.example.com"),
                ~Account.domain.like("roundtrip-%.example.com"),
            )
            .order_by(Account.company_name)
        )
        accounts = result.scalars().all()

        logger.info("list_accounts.accounts_found", count=len(accounts))

        visible_by_account: dict[uuid.UUID, Audit] = {}
        if settings.acl_enforcement_enabled:
            visible_by_account = await latest_visible_audit_per_account(user_id, session)

        # Build per-account metadata and group by normalized domain
        groups: dict[str, list[tuple[Account, str, str | None, float | None]]] = {}

        for account in accounts:
            if settings.acl_enforcement_enabled:
                latest_audit = visible_by_account.get(account.id)
            else:
                # ACL_ENFORCEMENT_ENABLED=false (default): unchanged from
                # pre-ACL behavior -- ships dark, 04-spec.md §10.
                audit_result = await session.execute(
                    select(Audit)
                    .where(Audit.account_id == account.id)
                    .order_by(Audit.created_at.desc())
                    .limit(1)
                )
                latest_audit = audit_result.scalar_one_or_none()

            status = "none"
            last_audit_date: str | None = None
            score: float | None = None

            if latest_audit is not None:
                status = latest_audit.status or "pending"
                if latest_audit.created_at:
                    last_audit_date = latest_audit.created_at.strftime("%Y-%m-%d")
                if latest_audit.score is not None:
                    score = float(latest_audit.score)

            normalized = normalize_domain(account.domain)
            groups.setdefault(normalized, []).append((account, status, last_audit_date, score))

        # Deduplicate: pick the best account per normalized domain
        responses: list[AccountResponse] = []
        for _norm_domain, group in groups.items():
            responses.append(_pick_best_account(group))

        # Sort by company name for consistent ordering
        responses.sort(key=lambda r: r.company_name.lower())

        logger.info(
            "list_accounts.done",
            raw_count=len(accounts),
            deduped_count=len(responses),
        )
        return responses

    except Exception as exc:
        logger.error("list_accounts.failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to list accounts.") from exc


@router.get("/{domain}/results", response_model=AccountResultsResponse)
async def get_account_results(
    domain: str,
    session: DbSession,
    user_id: Annotated[str | None, Depends(resolve_user_id)],
) -> AccountResultsResponse:
    """Get all module results for a domain.

    Normalizes the domain, finds all matching accounts (covering domain
    variants like www.example.com and example.com), then returns the most
    recent successful or partial execution of each module.

    Auth (04-spec.md §3 row 5, §2b): the "latest audit" used for
    `audit_status`/`last_audit_date` is resolved from the caller's visible
    set (same joined-query shape as list_accounts) while
    `ACL_ENFORCEMENT_ENABLED=true` -- "latest visible, not latest
    overall." While the flag is false (default), unchanged from pre-ACL
    behavior (§10).

    Args:
        domain: Raw domain string (will be normalized).
        session: Injected async DB session.
        user_id: Resolved caller identity (may be None if unauthenticated).

    Returns:
        AccountResultsResponse with module_name -> output_json mapping.
    """
    normalized = normalize_domain(domain)
    logger.info("get_account_results.start", domain=domain, normalized=normalized)

    try:
        # -----------------------------------------------------------------
        # 1. Find all accounts whose domain normalizes to the same value
        # -----------------------------------------------------------------
        accounts_result = await session.execute(select(Account))
        all_accounts = accounts_result.scalars().all()

        matching_account_ids: list[uuid.UUID] = []
        best_account: Account | None = None

        for account in all_accounts:
            if normalize_domain(account.domain) == normalized:
                matching_account_ids.append(account.id)
                # Keep the first match (or one with more data populated)
                if best_account is None or (
                    bool(account.legal_name) and not bool(best_account.legal_name)
                ):
                    best_account = account

        if not matching_account_ids:
            logger.warning("get_account_results.no_account", normalized=normalized)
            raise HTTPException(
                status_code=404,
                detail=f"No account found for domain '{domain}'.",
            )

        logger.info(
            "get_account_results.accounts_matched",
            normalized=normalized,
            account_count=len(matching_account_ids),
        )

        # -----------------------------------------------------------------
        # 2. Get latest audit info
        # -----------------------------------------------------------------
        if settings.acl_enforcement_enabled:
            visible_stmt = (
                visible_audits_select(user_id)
                .where(Audit.account_id.in_(matching_account_ids))
                .order_by(Audit.created_at.desc())
                .limit(1)
            )
            latest_audit = (await session.execute(visible_stmt)).scalars().first()
        else:
            # ACL_ENFORCEMENT_ENABLED=false (default): unchanged from
            # pre-ACL behavior -- ships dark, 04-spec.md §10.
            audit_result = await session.execute(
                select(Audit)
                .where(Audit.account_id.in_(matching_account_ids))
                .order_by(Audit.created_at.desc())
                .limit(1)
            )
            latest_audit = audit_result.scalar_one_or_none()

        last_audit_date: str | None = None
        audit_status: str | None = None
        if latest_audit is not None:
            audit_status = latest_audit.status
            if latest_audit.created_at:
                last_audit_date = latest_audit.created_at.strftime("%Y-%m-%d")

        # -----------------------------------------------------------------
        # 3. For each module_name, get the most recent successful/partial
        #    execution across all matching domain variants.
        #
        #    We use a subquery to find the max completed_at per module_name,
        #    then join back to get the full row.
        # -----------------------------------------------------------------

        # Build list of domain variants that normalize to the same value
        domain_variants = [
            a.domain for a in all_accounts if normalize_domain(a.domain) == normalized
        ]

        # Subquery: latest completed_at per module_name
        latest_sub = (
            select(
                ModuleExecution.module_name,
                func.max(ModuleExecution.completed_at).label("max_completed"),
            )
            .where(
                ModuleExecution.domain.in_(domain_variants),
                ModuleExecution.status.in_(["success", "partial"]),
                ModuleExecution.output_json.isnot(None),
            )
            .group_by(ModuleExecution.module_name)
            .subquery()
        )

        # Main query: join back to get the full row for each latest execution
        me_alias = aliased(ModuleExecution)
        exec_result = await session.execute(
            select(me_alias)
            .join(
                latest_sub,
                (me_alias.module_name == latest_sub.c.module_name)
                & (me_alias.completed_at == latest_sub.c.max_completed),
            )
            .where(
                me_alias.domain.in_(domain_variants),
                me_alias.status.in_(["success", "partial"]),
                me_alias.output_json.isnot(None),
            )
        )
        executions = exec_result.scalars().all()

        # Build the module results dict (deduplicate by module_name just in case)
        modules: dict[str, Any] = {}
        for exe in executions:
            if exe.module_name not in modules:
                modules[exe.module_name] = exe.output_json

        logger.info(
            "get_account_results.done",
            normalized=normalized,
            module_count=len(modules),
            modules=list(modules.keys()),
        )

        return AccountResultsResponse(
            domain=normalized,
            company_name=best_account.company_name if best_account else None,
            modules=modules,
            last_audit_date=last_audit_date,
            audit_status=audit_status,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "get_account_results.failed",
            domain=domain,
            normalized=normalized,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve results for domain '{domain}'.",
        ) from exc
