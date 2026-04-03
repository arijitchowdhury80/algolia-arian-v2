"""Intel Company module — THE FOUNDATION HUB.

This module runs FIRST in every audit. All spoke modules depend on its output.
It populates the accounts table with the canonical company profile.

Data flow:
    1. Collector: ONE Perplexity call (JSON) + homepage fetch
    2. Parser: json.loads + citation extraction + Pydantic validation (NO LLM)
    3. Persist: write every field to proper columns on accounts table
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

import structlog
from sqlalchemy import update

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import EvidenceTier, ModuleResult, Source, ValidationResult
from prism_platform.db.models import Account
from prism_platform.db.session import async_session_factory
from prism_platform.modules.intel_company.collector import CompanyCollector
from prism_platform.modules.intel_company.parser import parse_perplexity_json
from prism_platform.modules.intel_company.schemas import (
    CompanyInput,
    CompanyProfileOutput,
)
from prism_platform.modules.intel_company.validator import validate_output

logger = structlog.get_logger(__name__)

# Known Algolia customers for competitor cross-check
KNOWN_ALGOLIA_CUSTOMERS: set[str] = {
    "twitch.tv", "lacoste.com", "gymshark.com", "stripe.com", "netlify.com",
    "discourse.org", "medium.com", "birchbox.com", "hm.com", "decathlon.com",
    "under-armour.com", "underarmour.com",
}


class CompanyModule(ModuleInterface):
    """Foundation company intelligence module — the hub.

    Produces: canonical company profile written to accounts table.
    Consumed by: every spoke module in the audit pipeline.
    """

    name: ClassVar[str] = "intel-company"
    version: ClassVar[str] = "0.2.0"
    description: ClassVar[str] = (
        "Foundation company intelligence via single Perplexity API call. "
        "Populates accounts table with company identity, executives, "
        "competitors, financials, and field-level source citations."
    )
    layer: ClassVar[str] = "intelligence"

    input_schema: ClassVar[type[CompanyInput]] = CompanyInput
    output_schema: ClassVar[type[CompanyProfileOutput]] = CompanyProfileOutput
    dependencies: ClassVar[list[str]] = []
    requires_llm: ClassVar[bool] = False

    timeout_seconds: ClassVar[int] = 120
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        self._collector = CompanyCollector()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run company intelligence collection: Perplexity → parse → persist.

        Args:
            context: Execution context with domain, account_id, audit metadata.

        Returns:
            ModuleResult with CompanyProfileOutput and field-level sources.
        """
        logger.info(
            "[CompanyModule] execute started",
            domain=context.domain,
            audit_id=context.audit_id,
            account_id=context.account_id,
        )
        start_ms = time.monotonic_ns() // 1_000_000
        sources: list[Source] = []

        try:
            # Steps 1+2: Collect + Parse with retry (3 attempts, 5s gap)
            # Retries on: empty response, malformed JSON, Pydantic validation failure
            import asyncio as _asyncio

            max_attempts = 3
            retry_delay = 5
            raw_data: dict[str, Any] = {}
            output: CompanyProfileOutput | None = None
            citations: list[dict[str, str]] = []
            last_parse_error: str = ""

            for attempt in range(1, max_attempts + 1):
                try:
                    raw_data = await self._collector.collect(context.domain)

                    if not raw_data.get("perplexity_raw"):
                        last_parse_error = "Perplexity returned empty response"
                        logger.warning(
                            "[CompanyModule] empty response, retrying",
                            domain=context.domain,
                            attempt=attempt,
                            max_attempts=max_attempts,
                        )
                        if attempt < max_attempts:
                            await _asyncio.sleep(retry_delay)
                        continue

                    output, citations = parse_perplexity_json(raw_data["perplexity_raw"])
                    logger.info(
                        "[CompanyModule] collect + parse succeeded",
                        domain=context.domain,
                        attempt=attempt,
                    )
                    break

                except (json.JSONDecodeError, ValueError) as parse_exc:
                    last_parse_error = f"Parse failed: {parse_exc}"
                    logger.warning(
                        "[CompanyModule] JSON parse failed, retrying",
                        domain=context.domain,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        error=str(parse_exc),
                    )
                    if attempt < max_attempts:
                        await _asyncio.sleep(retry_delay)

                except Exception as parse_exc:
                    last_parse_error = f"Parse failed: {parse_exc}"
                    logger.warning(
                        "[CompanyModule] parse/validation failed, retrying",
                        domain=context.domain,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        error=str(parse_exc),
                    )
                    if attempt < max_attempts:
                        await _asyncio.sleep(retry_delay)

            if output is None:
                duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
                logger.error(
                    "[CompanyModule] failed after all retries",
                    domain=context.domain,
                    max_attempts=max_attempts,
                    last_error=last_parse_error,
                )
                return ModuleResult(
                    module_name=self.name,
                    module_version=self.version,
                    status="failed",
                    output={},
                    sources=sources,
                    duration_ms=duration_ms,
                    llm_calls=max_attempts,
                    errors=[f"Failed after {max_attempts} attempts: {last_parse_error}"],
                )

            # Apply search bar detection from homepage
            if raw_data.get("has_search_bar") is not None:
                output_dict = output.model_dump()
                output_dict["has_search_bar"] = raw_data["has_search_bar"]
                output = CompanyProfileOutput.model_validate(output_dict)

            # Cross-check competitors against Algolia customer list
            for comp in output.competitors:
                if comp.domain.lower().strip() in KNOWN_ALGOLIA_CUSTOMERS:
                    comp.is_algolia_customer = True

            # Build Source provenance records
            sources.append(
                Source(
                    field="perplexity_response",
                    value=f"Perplexity sonar JSON ({len(raw_data['perplexity_raw'])} chars)",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Perplexity API (composite company research)",
                    method="llm_extraction",
                )
            )
            for citation in citations:
                sources.append(
                    Source(
                        field=citation.get("field", "general"),
                        value=citation["source_label"],
                        tier=EvidenceTier.WEBSEARCH,
                        source_url=citation["source_url"],
                        source_label=citation["source_label"],
                        method="llm_extraction",
                    )
                )
            if raw_data.get("homepage_fetched"):
                sources.append(
                    Source(
                        field="has_search_bar",
                        value=f"Homepage fetched, search_bar={raw_data['has_search_bar']}",
                        tier=EvidenceTier.WEBFETCH,
                        source_url=f"https://{context.domain}",
                        source_label=f"{context.domain} homepage",
                        method="scrape",
                    )
                )

            # Step 3: Persist to accounts table
            try:
                await self._update_account(context.account_id, context.domain, output, citations)
            except Exception as exc:
                logger.error(
                    "[CompanyModule] failed to update accounts table",
                    domain=context.domain,
                    error=str(exc),
                )

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

            result = ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="success",
                output=output.model_dump(),
                sources=sources,
                duration_ms=duration_ms,
                llm_calls=1,
                llm_cost_usd=0.0,
            )

            logger.info(
                "[CompanyModule] execute completed",
                domain=context.domain,
                status="success",
                duration_ms=duration_ms,
                executives_count=len(output.executives),
                competitors_count=len(output.competitors),
                news_count=len(output.recent_news),
                citation_count=len(citations),
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.exception(
                "[CompanyModule] execute failed",
                domain=context.domain,
                audit_id=context.audit_id,
            )
            return ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="failed",
                output={},
                sources=sources,
                duration_ms=duration_ms,
                errors=[f"{type(error).__name__}: {error}"],
            )

    async def validate(self, result: ModuleResult) -> ValidationResult:
        """Validate module output meets quality standards (8 checks).

        Args:
            result: The ModuleResult from execute().

        Returns:
            ValidationResult with pass/fail and diagnostic details.
        """
        logger.info("[CompanyModule] validate started", module=self.name)
        try:
            output = CompanyProfileOutput.model_validate(result.output)
            return validate_output(output, result.sources, expected_domain=output.domain)
        except Exception as error:
            logger.error("[CompanyModule] validate failed", error=str(error))
            return ValidationResult(
                passed=False, checks_run=0, checks_passed=0,
                errors=[f"Output deserialization failed: {error}"],
            )

    async def health_check(self) -> bool:
        """Check if Perplexity API key is configured."""
        from prism_platform.config import settings

        has_perplexity = bool(settings.perplexity_api_key)
        if not has_perplexity:
            logger.warning("[CompanyModule] PERPLEXITY_API_KEY not set")
        return has_perplexity

    async def _update_account(
        self,
        account_id: str,
        domain: str,
        output: CompanyProfileOutput,
        citations: list[dict[str, str]],
    ) -> None:
        """Write every field to proper columns on the accounts table.

        Args:
            account_id: UUID of the account to update.
            domain: Domain of the account.
            output: The structured company profile.
            citations: Field-level source citations from Perplexity.
        """
        if not account_id:
            logger.warning("[CompanyModule] account_id is empty, skipping account update")
            return

        async with async_session_factory() as session:
            try:
                await session.execute(
                    update(Account)
                    .where(Account.id == uuid.UUID(account_id))
                    .values(
                        legal_name=output.legal_name,
                        company_name=output.common_name or output.legal_name,
                        headquarters=output.headquarters,
                        employee_count=output.employee_count,
                        employee_count_source=output.employee_count_source,
                        year_founded=output.year_founded,
                        business_model=output.business_model,
                        motto=output.motto,
                        industry=output.industry,
                        sub_vertical=output.sub_vertical,
                        is_public=output.is_public,
                        ticker=output.ticker,
                        parent_company=output.parent_company,
                        revenue_estimate=output.revenue_estimate,
                        revenue_source=output.revenue_source,
                        has_search_bar=output.has_search_bar,
                        product_categories=[c for c in output.product_categories],
                        executives=[e.model_dump() for e in output.executives],
                        competitors=[c.model_dump() for c in output.competitors],
                        recent_news=[n.model_dump() for n in output.recent_news],
                        recent_blog_posts=[b.model_dump() for b in output.recent_blog_posts],
                        sources=citations,
                        updated_at=datetime.now(UTC),
                    )
                )
                await session.commit()
                logger.info(
                    "[CompanyModule] accounts table updated",
                    account_id=account_id,
                    domain=domain,
                    citation_count=len(citations),
                )
            except Exception as exc:
                await session.rollback()
                logger.error(
                    "[CompanyModule] accounts table update failed",
                    account_id=account_id,
                    error=str(exc),
                )
                raise
