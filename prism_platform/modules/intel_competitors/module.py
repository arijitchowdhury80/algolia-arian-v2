"""Intel Competitors module -- synthesis of upstream module outputs into competitive intelligence.

This is a PURE SYNTHESIS module. It does NOT call external APIs. It reads outputs
from other modules (stored in the module_executions table) and uses Claude for
LLM-powered competitive positioning and summary generation.
"""

from __future__ import annotations

import time
from typing import ClassVar

import structlog

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import ModuleResult, ValidationResult
from prism_platform.modules.intel_competitors.collector import (
    CompetitorsCollector,
    extract_executive_sentiments,
    extract_financial_comparisons,
    extract_hiring_comparisons,
    extract_tech_comparisons,
    extract_traffic_comparisons,
)
from prism_platform.modules.intel_competitors.enricher import CompetitorsEnricher
from prism_platform.modules.intel_competitors.schemas import CompetitorsInput, CompetitorsOutput
from prism_platform.modules.intel_competitors.validator import validate_output

logger = structlog.get_logger(__name__)


class CompetitorsModule(ModuleInterface):
    """Competitive intelligence synthesis from upstream module outputs."""

    name: ClassVar[str] = "intel-competitors"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Synthesizes upstream module outputs into competitive intelligence "
        "using Claude for positioning and scenario analysis"
    )
    layer: ClassVar[str] = "synthesis"

    input_schema: ClassVar[type[CompetitorsInput]] = CompetitorsInput
    output_schema: ClassVar[type[CompetitorsOutput]] = CompetitorsOutput
    dependencies: ClassVar[list[str]] = [
        "intel-company",
        "intel-techstack",
        "intel-traffic",
        "intel-hiring",
    ]
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 180
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        self._collector = CompetitorsCollector()
        self._enricher = CompetitorsEnricher()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run competitive intelligence synthesis for the given domain.

        Reads all upstream module outputs from the DB, extracts comparison
        data, and uses Claude to synthesize competitive positioning.

        Args:
            context: Execution context with domain and audit metadata.

        Returns:
            ModuleResult containing CompetitorsOutput and source provenance.
        """
        logger.info(
            "[Competitors] execute started",
            domain=context.domain,
            audit_id=context.audit_id,
            company_name=context.company_name,
        )
        start_ms = time.monotonic_ns() // 1_000_000

        try:
            # Step 1: Read all upstream module outputs from DB
            raw_data, sources = await self._collector.collect_all(
                audit_id=context.audit_id,
                domain=context.domain,
            )

            modules_with_data = sum(1 for v in raw_data.values() if v is not None)
            if modules_with_data == 0:
                logger.warning(
                    "[Competitors] no upstream module data found",
                    domain=context.domain,
                    audit_id=context.audit_id,
                )
                duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
                return ModuleResult(
                    module_name=self.name,
                    module_version=self.version,
                    status="failed",
                    output=CompetitorsOutput(domain=context.domain).model_dump(),
                    sources=sources,
                    duration_ms=duration_ms,
                    errors=["No upstream module data found -- cannot synthesize"],
                )

            # Step 2: Extract comparison objects from raw outputs
            tech_comparisons, golden_angle, tech_gaps = extract_tech_comparisons(
                techstack_output=raw_data.get("intel-techstack"),
                domain=context.domain,
                company_name=context.company_name,
            )

            traffic_comparisons = extract_traffic_comparisons(
                traffic_output=raw_data.get("intel-traffic"),
                domain=context.domain,
                company_name=context.company_name,
            )

            financial_comparisons = extract_financial_comparisons(
                public_output=raw_data.get("intel-financial-public"),
                private_output=raw_data.get("intel-financial-private"),
                domain=context.domain,
                company_name=context.company_name,
                is_private=context.is_private,
            )

            hiring_comparisons = extract_hiring_comparisons(
                hiring_output=raw_data.get("intel-hiring"),
                domain=context.domain,
                company_name=context.company_name,
            )

            executive_sentiments = extract_executive_sentiments(
                investor_output=raw_data.get("intel-investor"),
                social_output=raw_data.get("intel-social"),
                domain=context.domain,
                company_name=context.company_name,
            )

            # Step 3: Synthesize with Claude
            output, llm_calls, llm_cost_usd = await self._enricher.synthesize(
                domain=context.domain,
                company_name=context.company_name,
                tech_comparisons=tech_comparisons,
                traffic_comparisons=traffic_comparisons,
                financial_comparisons=financial_comparisons,
                hiring_comparisons=hiring_comparisons,
                executive_sentiments=executive_sentiments,
                golden_angle_competitors=golden_angle,
                tech_gaps=tech_gaps,
                raw_data=raw_data,
            )

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

            # Determine status: success if we have at least comparisons + summary
            has_comparisons = (
                len(tech_comparisons) > 0
                or len(traffic_comparisons) > 0
                or len(financial_comparisons) > 0
                or len(hiring_comparisons) > 0
            )
            has_summary = bool(output.competitive_summary.strip())
            status = "success" if (has_comparisons and has_summary) else "partial"

            result = ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status=status,
                output=output.model_dump(),
                sources=sources,
                duration_ms=duration_ms,
                llm_calls=llm_calls,
                llm_cost_usd=llm_cost_usd,
            )

            logger.info(
                "[Competitors] execute completed",
                domain=context.domain,
                status=status,
                duration_ms=duration_ms,
                tech_count=len(tech_comparisons),
                traffic_count=len(traffic_comparisons),
                financial_count=len(financial_comparisons),
                hiring_count=len(hiring_comparisons),
                sentiment_count=len(executive_sentiments),
                llm_calls=llm_calls,
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.error(
                "[Competitors] execute failed",
                error=str(error),
                context={"domain": context.domain, "audit_id": context.audit_id},
            )
            return ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="failed",
                output=CompetitorsOutput(domain=context.domain).model_dump(),
                duration_ms=duration_ms,
                errors=[str(error)],
            )

    async def validate(self, result: ModuleResult) -> ValidationResult:
        """Validate module output meets quality standards.

        Args:
            result: The ModuleResult from execute().

        Returns:
            ValidationResult with pass/fail and diagnostic details.
        """
        logger.info("[Competitors] validate started", module=self.name)

        try:
            output = CompetitorsOutput.model_validate(result.output)
            return validate_output(output, result.sources)
        except Exception as error:
            logger.error(
                "[Competitors] validate failed",
                error=str(error),
            )
            return ValidationResult(
                passed=False,
                checks_run=0,
                checks_passed=0,
                errors=[f"Output deserialization failed: {error}"],
            )

    async def health_check(self) -> bool:
        """Check if an LLM provider is configured."""
        from prism_platform.config import settings

        try:
            settings.get_enricher_provider()
            return True
        except (ValueError, AttributeError):
            logger.warning("[Competitors] No LLM provider configured")
            return False
