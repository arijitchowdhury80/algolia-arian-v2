"""Intel Financial Public module -- financial intelligence for publicly traded companies.

This module runs after intel-company and collects:
1. Yahoo Finance: 3-year revenue trend, market data, analyst consensus
2. SEC EDGAR: recent 10-K and 10-Q filing metadata + enriched analysis
3. Investor presentations: via Perplexity search + Instructor structuring
4. Competitor financials: basic Yahoo Finance data for competitor tickers

Data flow:
1. Check if company is public (is_private=False, ticker is set)
2. Collector: Yahoo Finance + SEC EDGAR -> raw structured data
3. Enricher: Perplexity + Instructor -> enriched SEC insights + investor presentations
4. Validator: 9 quality checks
"""

from __future__ import annotations

import time
from typing import ClassVar

import structlog

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import EvidenceTier, ModuleResult, Source, ValidationResult
from prism_platform.modules.intel_financial_public.collector import FinancialCollector
from prism_platform.modules.intel_financial_public.enricher import FinancialEnricher
from prism_platform.modules.intel_financial_public.schemas import (
    FinancialPublicInput,
    FinancialPublicOutput,
)
from prism_platform.modules.intel_financial_public.validator import validate_output

logger = structlog.get_logger(__name__)


class FinancialPublicModule(ModuleInterface):
    """Financial intelligence module for publicly traded companies.

    Produces: 3-year financials, market data, analyst consensus, SEC filing
    insights, investor presentation analysis, and competitor comparative data.
    Consumed by: synthesis modules for ROI modeling and business case generation.
    """

    name: ClassVar[str] = "intel-financial-public"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Financial intelligence for public companies via Yahoo Finance, "
        "SEC EDGAR, and Perplexity-powered investor presentation analysis."
    )
    layer: ClassVar[str] = "intelligence"

    input_schema: ClassVar[type[FinancialPublicInput]] = FinancialPublicInput
    output_schema: ClassVar[type[FinancialPublicOutput]] = FinancialPublicOutput
    dependencies: ClassVar[list[str]] = ["intel-company"]
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 300  # 5 minutes
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        self._collector = FinancialCollector()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run full financial intelligence collection and enrichment.

        Steps:
        1. Check if company is public (skip if private or no ticker)
        2. Collect Yahoo Finance data + SEC EDGAR filings
        3. Enrich SEC insights and search investor presentations via Perplexity
        4. Collect competitor financials
        5. Generate comparative summary

        Args:
            context: Execution context with domain, ticker, and is_private.

        Returns:
            ModuleResult containing FinancialPublicOutput and source provenance.
        """
        logger.info(
            "[FinancialPublicModule] execute started",
            domain=context.domain,
            ticker=context.ticker,
            is_private=context.is_private,
            audit_id=context.audit_id,
        )
        start_ms = time.monotonic_ns() // 1_000_000
        sources: list[Source] = []

        # Skip if company is private or has no ticker
        if context.is_private or context.ticker is None:
            skip_reason = (
                "Company is private" if context.is_private else "No ticker symbol available"
            )
            logger.info(
                "[FinancialPublicModule] skipping -- not a public company",
                domain=context.domain,
                reason=skip_reason,
            )
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            output = FinancialPublicOutput(
                domain=context.domain,
                ticker=context.ticker or "",
                skipped=True,
                skip_reason=skip_reason,
            )
            return ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="success",
                output=output.model_dump(),
                sources=[],
                duration_ms=duration_ms,
            )

        ticker = context.ticker

        try:
            # Step 1: Collect Yahoo Finance data
            (
                annual_financials,
                market_data,
                analyst_data,
            ) = await self._collector.collect_yahoo_finance(ticker)

            sources.append(
                Source(
                    field="annual_financials",
                    value=f"Yahoo Finance: {len(annual_financials)} years of financials",
                    tier=EvidenceTier.VERIFIED,
                    source_url=f"https://finance.yahoo.com/quote/{ticker}",
                    source_label="Yahoo Finance API (yfinance)",
                    method="direct_api",
                )
            )

            if market_data:
                sources.append(
                    Source(
                        field="market_data",
                        value=f"Market cap: {market_data.market_cap}",
                        tier=EvidenceTier.VERIFIED,
                        source_url=f"https://finance.yahoo.com/quote/{ticker}",
                        source_label="Yahoo Finance API (yfinance)",
                        method="direct_api",
                    )
                )

            if analyst_data:
                sources.append(
                    Source(
                        field="analyst_data",
                        value=f"Recommendation: {analyst_data.recommendation}",
                        tier=EvidenceTier.VERIFIED,
                        source_url=f"https://finance.yahoo.com/quote/{ticker}",
                        source_label="Yahoo Finance API (yfinance)",
                        method="direct_api",
                    )
                )

            # Step 2: Collect SEC EDGAR filings
            sec_insights = await self._collector.collect_sec_filings(context.company_name, ticker)

            if sec_insights:
                sources.append(
                    Source(
                        field="sec_insights",
                        value=f"SEC EDGAR: {len(sec_insights)} filings found",
                        tier=EvidenceTier.VERIFIED,
                        source_url="https://www.sec.gov/cgi-bin/browse-edgar",
                        source_label="SEC EDGAR EFTS API",
                        method="direct_api",
                    )
                )

            # Step 3: Enrich via Perplexity + Instructor
            enricher = FinancialEnricher()

            enriched_sec = await enricher.enrich_sec_insights(
                sec_insights, context.company_name, ticker
            )

            investor_presentations = await enricher.search_investor_presentations(
                context.company_name, context.domain
            )

            if investor_presentations:
                sources.append(
                    Source(
                        field="investor_presentations",
                        value=f"Perplexity: {len(investor_presentations)} presentations found",
                        tier=EvidenceTier.WEBSEARCH,
                        source_label="Perplexity API + Claude (structuring)",
                        method="llm_extraction",
                    )
                )

            # Step 4: Collect competitor financials
            competitor_tickers = self._get_competitor_tickers(context)
            competitor_financials = await self._collector.collect_competitor_financials(
                competitor_tickers
            )

            if competitor_financials:
                sources.append(
                    Source(
                        field="competitor_financials",
                        value=f"Yahoo Finance: {len(competitor_financials)} competitors",
                        tier=EvidenceTier.VERIFIED,
                        source_label="Yahoo Finance API (yfinance)",
                        method="direct_api",
                    )
                )

            # Step 5: Generate comparative summary
            most_recent_revenue: float | None = None
            if annual_financials:
                most_recent_revenue = annual_financials[-1].revenue

            comparative_summary = await enricher.generate_comparative_summary(
                context.company_name, ticker, most_recent_revenue, competitor_financials
            )

            if comparative_summary:
                sources.append(
                    Source(
                        field="comparative_summary",
                        value=f"Claude: {len(comparative_summary)} chars",
                        tier=EvidenceTier.ESTIMATE,
                        source_label="Claude via Instructor (comparative analysis)",
                        method="llm_extraction",
                    )
                )

            # Build output
            output = FinancialPublicOutput(
                domain=context.domain,
                ticker=ticker,
                annual_financials=annual_financials,
                market_data=market_data,
                analyst_data=analyst_data,
                sec_insights=enriched_sec,
                investor_presentations=investor_presentations,
                competitor_financials=competitor_financials,
                comparative_summary=comparative_summary,
            )

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            total_llm_calls = enricher.llm_calls
            total_cost = enricher.llm_cost

            result = ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="success",
                output=output.model_dump(),
                sources=sources,
                duration_ms=duration_ms,
                llm_calls=total_llm_calls,
                llm_cost_usd=total_cost,
            )

            logger.info(
                "[FinancialPublicModule] execute completed",
                domain=context.domain,
                ticker=ticker,
                status="success",
                duration_ms=duration_ms,
                llm_calls=total_llm_calls,
                llm_cost_usd=total_cost,
                annual_years=len(annual_financials),
                sec_filings=len(enriched_sec),
                investor_presentations=len(investor_presentations),
                competitors=len(competitor_financials),
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.exception(
                "[FinancialPublicModule] execute failed",
                domain=context.domain,
                ticker=ticker,
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
        """Validate module output meets quality standards (9 checks).

        Args:
            result: The ModuleResult from execute().

        Returns:
            ValidationResult with pass/fail and diagnostic details.
        """
        logger.info("[FinancialPublicModule] validate started", module=self.name)

        try:
            output = FinancialPublicOutput.model_validate(result.output)
            return validate_output(
                output,
                result.sources,
                expected_domain=output.domain,
                expected_ticker=output.ticker,
            )
        except Exception as error:
            logger.error(
                "[FinancialPublicModule] validate failed -- output deserialization error",
                error=str(error),
            )
            return ValidationResult(
                passed=False,
                checks_run=0,
                checks_passed=0,
                errors=[f"Output deserialization failed: {error}"],
            )

    async def health_check(self) -> bool:
        """Check if required API keys are configured.

        Yahoo Finance and SEC EDGAR are free -- no keys needed.
        Perplexity and Claude are needed for enrichment.
        """
        from prism_platform.config import settings

        has_perplexity = bool(settings.perplexity_api_key)
        try:
            settings.get_enricher_provider()
            has_llm = True
        except (ValueError, AttributeError):
            has_llm = False

        if not has_perplexity:
            logger.warning("[FinancialPublicModule] PERPLEXITY_API_KEY not set")
        if not has_llm:
            logger.warning("[FinancialPublicModule] No LLM provider configured")

        return has_perplexity and has_llm

    @staticmethod
    def _get_competitor_tickers(context: ExecutionContext) -> list[dict[str, str]]:
        """Extract competitor ticker information from execution context.

        In a full pipeline, this would read from accounts.intelligence JSONB
        which is populated by the intel-company module. For now, we return
        an empty list since we don't have DB access in this context.

        Args:
            context: Execution context.

        Returns:
            List of dicts with 'company_name' and 'ticker' keys.
        """
        # TODO: Read competitor_domains from accounts.intelligence
        # and look up their tickers. For now, return empty list.
        # This will be populated when the DB integration is complete.
        logger.info(
            "[FinancialPublicModule] competitor ticker lookup not yet implemented",
            domain=context.domain,
        )
        return []
