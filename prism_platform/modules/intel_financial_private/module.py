"""Intel Financial Private module -- revenue estimation for private companies.

Uses a 6-source Perplexity waterfall to estimate revenue from multiple
independent sources, then structures the findings with Instructor + Claude.
"""

from __future__ import annotations

import time
from typing import ClassVar

import structlog

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import EvidenceTier, ModuleResult, Source, ValidationResult
from prism_platform.modules.intel_financial_private.collector import FinancialPrivateCollector
from prism_platform.modules.intel_financial_private.enricher import FinancialPrivateEnricher
from prism_platform.modules.intel_financial_private.schemas import (
    FinancialPrivateInput,
    FinancialPrivateOutput,
)
from prism_platform.modules.intel_financial_private.validator import validate_output

logger = structlog.get_logger(__name__)


class FinancialPrivateModule(ModuleInterface):
    """Revenue estimation for private companies via multi-source waterfall."""

    name: ClassVar[str] = "intel-financial-private"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Estimates private company revenue using a 6-source Perplexity waterfall "
        "structured by Instructor + Claude."
    )
    layer: ClassVar[str] = "intelligence"

    input_schema: ClassVar[type[FinancialPrivateInput]] = FinancialPrivateInput
    output_schema: ClassVar[type[FinancialPrivateOutput]] = FinancialPrivateOutput
    dependencies: ClassVar[list[str]] = ["intel-company"]
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 180
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        self._collector = FinancialPrivateCollector()
        self._enricher = FinancialPrivateEnricher()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run private financial intelligence for the given company.

        If the company is NOT private (i.e., has a ticker / is_private is False),
        returns a skipped result immediately.

        Args:
            context: Execution context with domain, company_name, and is_private flag.

        Returns:
            ModuleResult containing FinancialPrivateOutput and source provenance.
        """
        logger.info(
            "[FinancialPrivate] execute started",
            domain=context.domain,
            audit_id=context.audit_id,
            is_private=context.is_private,
            ticker=context.ticker,
        )
        start_ms = time.monotonic_ns() // 1_000_000

        # Skip if company is public
        if not context.is_private:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            output = FinancialPrivateOutput(
                domain=context.domain,
                skipped=True,
                skip_reason="Company is public (has ticker). Use intel-financial-public instead.",
            )
            logger.info(
                "[FinancialPrivate] skipped -- company is public",
                domain=context.domain,
                ticker=context.ticker,
            )
            return ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="success",
                output=output.model_dump(),
                duration_ms=duration_ms,
            )

        try:
            # Step 1: Collect 6-source waterfall via Perplexity
            waterfall_responses = await self._collector.collect_waterfall(
                company_name=context.company_name,
                domain=context.domain,
            )

            # Step 2: Structure via Instructor + Claude
            waterfall, funding, employee_model, competitors = await self._enricher.enrich_waterfall(
                company_name=context.company_name,
                domain=context.domain,
                waterfall_responses=waterfall_responses,
            )

            # Build output
            output = FinancialPrivateOutput(
                domain=context.domain,
                revenue_waterfall=waterfall,
                funding_data=funding,
                employee_revenue_model=employee_model,
                competitor_estimates=competitors,
                comparative_summary=self._build_comparative_summary(waterfall, competitors),
            )

            # Build sources
            sources = self._build_sources(output, waterfall_responses)

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            status = "success" if waterfall and len(waterfall.estimates) >= 2 else "partial"

            # Count LLM calls: 6 Perplexity + up to 4 Claude enrichment calls
            llm_calls = len(waterfall_responses) + sum(
                [
                    1 if waterfall is not None else 0,
                    1 if funding is not None else 0,
                    1 if employee_model is not None else 0,
                    1 if competitors else 0,
                ]
            )

            result = ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status=status,
                output=output.model_dump(),
                sources=sources,
                duration_ms=duration_ms,
                llm_calls=llm_calls,
                llm_cost_usd=0.0,  # Cost tracking TBD
            )

            logger.info(
                "[FinancialPrivate] execute completed",
                domain=context.domain,
                status=status,
                duration_ms=duration_ms,
                estimate_count=len(waterfall.estimates) if waterfall else 0,
                best_estimate=waterfall.best_estimate if waterfall else None,
                llm_calls=llm_calls,
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.exception(
                "[FinancialPrivate] execute failed",
                domain=context.domain,
                audit_id=context.audit_id,
            )
            return ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="failed",
                output={},
                duration_ms=duration_ms,
                errors=[f"{type(error).__name__}: {error}"],
            )

    async def validate(self, result: ModuleResult) -> ValidationResult:
        """Validate module output meets quality standards.

        Args:
            result: The ModuleResult from execute().

        Returns:
            ValidationResult with pass/fail and diagnostic details.
        """
        logger.info("[FinancialPrivate] validate started", module=self.name)

        try:
            output = FinancialPrivateOutput.model_validate(result.output)
            return validate_output(output, result.sources)
        except Exception as error:
            logger.error(
                "[FinancialPrivate] validate failed",
                error=str(error),
            )
            return ValidationResult(
                passed=False,
                checks_run=0,
                checks_passed=0,
                errors=[f"Output deserialization failed: {error}"],
            )

    async def health_check(self) -> bool:
        """Check if Perplexity and an LLM provider are configured.

        Returns:
            True if both API keys are present.
        """
        from prism_platform.config import settings

        has_perplexity = bool(settings.perplexity_api_key)
        try:
            settings.get_enricher_provider()
            has_llm = True
        except (ValueError, AttributeError):
            has_llm = False

        if not has_perplexity:
            logger.warning("[FinancialPrivate] perplexity_api_key is not configured")
        if not has_llm:
            logger.warning("[FinancialPrivate] No LLM provider configured")

        return has_perplexity and has_llm

    @staticmethod
    def _build_sources(
        output: FinancialPrivateOutput,
        waterfall_responses: list[dict[str, str]],
    ) -> list[Source]:
        """Build source provenance records for the output.

        Args:
            output: The structured output.
            waterfall_responses: The raw waterfall responses for source labels.

        Returns:
            List of Source records.
        """
        sources: list[Source] = []

        # Source for each waterfall response
        for resp in waterfall_responses:
            if not resp.get("content", "").startswith("[ERROR"):
                sources.append(
                    Source(
                        field="revenue_waterfall",
                        value=f"Perplexity research: {resp['label']}",
                        tier=EvidenceTier.WEBSEARCH,
                        source_label=f"Perplexity sonar-pro: {resp['label']}",
                        method="llm_extraction",
                    )
                )

        # Source for best estimate
        if output.revenue_waterfall and output.revenue_waterfall.best_estimate is not None:
            sources.append(
                Source(
                    field="best_estimate",
                    value=f"${output.revenue_waterfall.best_estimate:,.0f}",
                    tier=EvidenceTier.ESTIMATE,
                    source_label="Claude structured extraction (median of waterfall estimates)",
                    method="model_estimate",
                    confidence="medium",
                )
            )

        # Source for funding data
        if output.funding_data and output.funding_data.total_funding is not None:
            sources.append(
                Source(
                    field="total_funding",
                    value=f"${output.funding_data.total_funding:,.0f}",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label=output.funding_data.source or "Perplexity funding research",
                    method="llm_extraction",
                )
            )

        return sources

    @staticmethod
    def _build_comparative_summary(
        waterfall: object | None,
        competitors: list[object],
    ) -> str:
        """Build a narrative comparing the company to competitors.

        Args:
            waterfall: The RevenueWaterfall (or None).
            competitors: List of CompetitorRevenueEstimate objects.

        Returns:
            A summary string, empty if no data.
        """
        from prism_platform.modules.intel_financial_private.schemas import (
            CompetitorRevenueEstimate,
            RevenueWaterfall,
        )

        if not isinstance(waterfall, RevenueWaterfall) or not waterfall.best_estimate:
            return ""

        if not competitors:
            return (
                f"Estimated revenue: ${waterfall.best_estimate:,.0f}. No competitor data available."
            )

        parts = [f"Estimated revenue: ${waterfall.best_estimate:,.0f}."]
        for comp in competitors:
            if isinstance(comp, CompetitorRevenueEstimate) and comp.estimated_revenue:
                parts.append(f"{comp.company_name}: ~${comp.estimated_revenue:,.0f}.")

        return " ".join(parts)
