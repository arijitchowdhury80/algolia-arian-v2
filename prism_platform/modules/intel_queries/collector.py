"""Intel Queries collector -- reads company context from Account columns.

This collector does NOT make external API calls. It reads upstream module
output (intel-company, intel-techstack) from proper Account columns to
provide context for query generation.

Data read:
- industry, sub_vertical (Account columns)
- product_categories (Account JSONB column)
- competitors (Account JSONB column)
- company_name (Account column)
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select

from prism_platform.db.models import Account
from prism_platform.db.session import async_session_factory

logger = structlog.get_logger(__name__)


class QueriesCollector:
    """Reads company context from Account columns for query generation.

    No external API calls. All data comes from the database, populated by
    upstream modules (intel-company, intel-techstack).
    """

    async def collect_from_db(self, account_id: str, domain: str) -> dict[str, Any]:
        """Read company context from proper Account columns.

        Queries by domain first (works for diagnostic runs where account_id
        may be a placeholder). Falls back to account_id lookup.

        Args:
            account_id: UUID of the account to read from.
            domain: Domain of the account (preferred lookup key).

        Returns:
            Dict with keys: domain, company_name, industry, sub_vertical,
            product_categories, competitor_domains.

        Raises:
            ValueError: If the account is not found.
        """
        logger.info(
            "[QueriesCollector] reading context from Account columns",
            account_id=account_id,
            domain=domain,
        )

        try:
            async with async_session_factory() as session:
                # Prefer lookup by domain; fall back to account_id
                if domain:
                    stmt = select(Account).where(Account.domain == domain)
                else:
                    stmt = select(Account).where(Account.id == uuid.UUID(account_id))

                result = await session.execute(stmt)
                account = result.scalar_one_or_none()

                if account is None:
                    logger.error(
                        "[QueriesCollector] account not found",
                        account_id=account_id,
                        domain=domain,
                    )
                    raise ValueError(f"Account {account_id} not found for domain {domain}")

                if not account.industry:
                    logger.warning(
                        "[QueriesCollector] account.industry is empty -- "
                        "intel-company may not have run yet",
                        account_id=account_id,
                        domain=domain,
                    )

                context = self._extract_context_from_account(domain, account)

                logger.info(
                    "[QueriesCollector] context extracted",
                    domain=domain,
                    industry=context["industry"],
                    product_categories_count=len(context["product_categories"]),
                    competitor_count=len(context["competitor_domains"]),
                )

                return context

        except ValueError:
            raise
        except Exception as exc:
            logger.exception(
                "[QueriesCollector] failed to read Account columns",
                account_id=account_id,
                domain=domain,
            )
            raise ValueError(
                f"Failed to read account data for {domain}: {type(exc).__name__}: {exc}"
            ) from exc

    def collect_context(
        self,
        domain: str,
        company_name: str,
        industry: str,
        sub_vertical: str | None,
        product_categories: list[str],
        competitor_domains: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Build context dict from explicit parameters (no DB needed).

        This method is useful for testing or when context is already available
        in memory (e.g., from a previous module execution in the same pipeline).

        Args:
            domain: Prospect website domain.
            company_name: Company name.
            industry: Industry classification.
            sub_vertical: Sub-vertical classification.
            product_categories: List of product/service categories.
            competitor_domains: List of dicts with 'company_name' and 'domain' keys.

        Returns:
            Dict with standardized context keys.
        """
        logger.info(
            "[QueriesCollector] building context from parameters",
            domain=domain,
            industry=industry,
        )

        return {
            "domain": domain,
            "company_name": company_name,
            "industry": industry,
            "sub_vertical": sub_vertical,
            "product_categories": product_categories,
            "competitor_domains": competitor_domains,
        }

    @staticmethod
    def _extract_context_from_account(
        domain: str,
        account: Account,
    ) -> dict[str, Any]:
        """Extract relevant fields from proper Account columns.

        Args:
            domain: Prospect domain.
            account: The Account ORM object with denormalized columns.

        Returns:
            Standardized context dict for query generation.
        """
        # Read competitors from Account.competitors JSONB array column
        raw_competitors = account.competitors or []
        competitor_domains: list[dict[str, str]] = []

        for item in raw_competitors:
            if isinstance(item, str):
                competitor_domains.append({"company_name": item, "domain": item})
            elif isinstance(item, dict):
                competitor_domains.append(
                    {
                        "company_name": item.get("company_name", item.get("domain", "")),
                        "domain": item.get("domain", ""),
                    }
                )

        return {
            "domain": domain,
            "company_name": account.company_name or "",
            "industry": account.industry or "",
            "sub_vertical": account.sub_vertical,
            "product_categories": account.product_categories or [],
            "competitor_domains": competitor_domains,
        }
