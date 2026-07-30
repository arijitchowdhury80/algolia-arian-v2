"""Post-execute hooks for intel-company v2.

intel-company is the only module that writes structured fields back to the
accounts table (it owns the company identity card). All other modules write
only to module_executions via the cache layer.

The hook is registered in the v2 registry as intel-company's post_execute.
It runs after a successful execution, updates the accounts row by domain,
and logs the outcome. Failures are logged but do not fail the module result
— module_executions always gets the output regardless.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select, update

from core.db.models import Account
from core.db.session import async_session_factory
from core.types import ExecutionContextV2
from prism_platform.v2.modules.intel_company.schemas import CompanySeedOutput

logger = structlog.get_logger(__name__)


async def intel_company_post_execute(
    result: Any,  # ModuleExecutorResult — avoid circular import
    context: ExecutionContextV2,
) -> None:
    """Write CompanySeedOutput fields to the accounts table after a successful run.

    Looks up the account by domain (the natural key), not by UUID.
    This means the post_execute works whether called from Temporal (where
    account_id is known) or from a direct API call (where account_id may
    be a synthetic UUID with no matching row).

    If no account row exists for the domain, this is a silent no-op.
    The module_executions cache always has the output.

    Args:
        result: ModuleExecutorResult from the executor.
        context: ExecutionContextV2 with account_domain.
    """
    if result.status != "success" or not result.output:
        return

    try:
        output = CompanySeedOutput.model_validate(result.output)
    except Exception as exc:
        logger.error(
            "[intel-company] post_execute: schema validation failed",
            domain=context.account_domain,
            error=str(exc),
        )
        return

    await _update_account_by_domain(context.account_domain, output)


async def _update_account_by_domain(domain: str, output: CompanySeedOutput) -> None:
    """UPDATE accounts SET ... WHERE domain = domain.

    Uses domain as the lookup key — the accounts table has a unique constraint
    on domain. If the domain has no account row, this is a silent no-op.
    """
    # Encode recent_headline as a single-item recent_news list
    recent_news: list[dict[str, Any]] = []
    if output.recent_headline:
        recent_news = [{"headline": output.recent_headline, "source": "intel-company-v2"}]

    async with async_session_factory() as session:
        try:
            # Verify the account exists before attempting the update
            existing = await session.execute(
                select(Account).where(Account.domain == domain).limit(1)
            )
            if existing.scalar_one_or_none() is None:
                logger.debug(
                    "[intel-company] post_execute: no account row for domain — skipping",
                    domain=domain,
                )
                return

            await session.execute(
                update(Account)
                .where(Account.domain == domain)
                .values(
                    legal_name=output.legal_name,
                    company_name=output.common_name or output.legal_name,
                    headquarters=output.headquarters,
                    employee_count=output.employee_count,
                    employee_count_source=output.employee_count_source,
                    year_founded=output.year_founded,
                    business_model=output.business_model,
                    industry=output.industry,
                    sub_vertical=output.sub_vertical,
                    is_public=output.is_public,
                    ticker=output.ticker,
                    parent_company=output.parent_company,
                    revenue_estimate=output.revenue_estimate,
                    revenue_source=output.revenue_source,
                    company_linkedin_url=output.company_linkedin_url,
                    twitter_handle=output.twitter_handle,
                    youtube_url=output.youtube_url,
                    product_categories=output.product_categories,
                    executives=[e.model_dump() for e in output.executives],
                    competitors=[c.model_dump() for c in output.competitors],
                    subsidiaries=[s.model_dump() for s in output.subsidiaries],
                    parent_domain=output.parent_domain,
                    recent_news=recent_news,
                    updated_at=datetime.now(UTC),
                )
            )
            await session.commit()

            logger.info(
                "[intel-company] post_execute: accounts table updated",
                domain=domain,
                executives=len(output.executives),
                competitors=len(output.competitors),
            )

        except Exception as exc:
            await session.rollback()
            logger.error(
                "[intel-company] post_execute: accounts table update failed",
                domain=domain,
                error=str(exc),
            )
            raise
