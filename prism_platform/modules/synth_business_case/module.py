"""Synth Business Case module -- AI-powered ROI business case synthesis.

This is a PURE SYNTHESIS module. It does NOT call external APIs. It reads outputs
from other modules (stored in the module_executions table) and uses Claude for
LLM-powered business case generation including Said vs Found matrix, ROI model,
displacement cost, customer proofs, timing signals, and executive summary.
"""

from __future__ import annotations

import time
from typing import ClassVar

import structlog

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import ModuleResult, ValidationResult
from prism_platform.modules.synth_business_case.collector import (
    BusinessCaseCollector,
    extract_executive_quotes,
    extract_financial_data,
    extract_search_vendor,
    extract_timing_signals_from_modules,
    extract_traffic_data,
)
from prism_platform.modules.synth_business_case.enricher import BusinessCaseEnricher
from prism_platform.modules.synth_business_case.schemas import (
    BusinessCaseInput,
    BusinessCaseOutput,
)
from prism_platform.modules.synth_business_case.validator import validate_output

logger = structlog.get_logger(__name__)


class BusinessCaseModule(ModuleInterface):
    """ROI business case synthesis from upstream module outputs."""

    name: ClassVar[str] = "synth-business-case"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Synthesizes upstream module outputs into a complete ROI business case "
        "using Claude for Said vs Found, ROI model, displacement cost, customer "
        "proofs, timing signals, and executive summary generation"
    )
    layer: ClassVar[str] = "synthesis"

    input_schema: ClassVar[type[BusinessCaseInput]] = BusinessCaseInput
    output_schema: ClassVar[type[BusinessCaseOutput]] = BusinessCaseOutput
    dependencies: ClassVar[list[str]] = [
        "intel-company",
        "intel-investor",
        "intel-industry",
        "intel-competitors",
    ]
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 300
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        self._collector = BusinessCaseCollector()
        self._enricher = BusinessCaseEnricher()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run business case synthesis for the given domain.

        Reads all upstream module outputs from the DB, extracts key data,
        and uses Claude to synthesize the complete business case.

        Args:
            context: Execution context with domain and audit metadata.

        Returns:
            ModuleResult containing BusinessCaseOutput and source provenance.
        """
        logger.info(
            "[BusinessCase] execute started",
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
                    "[BusinessCase] no upstream module data found",
                    domain=context.domain,
                    audit_id=context.audit_id,
                )
                duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
                return ModuleResult(
                    module_name=self.name,
                    module_version=self.version,
                    status="failed",
                    output=BusinessCaseOutput(domain=context.domain).model_dump(),
                    sources=sources,
                    duration_ms=duration_ms,
                    errors=["No upstream module data found -- cannot synthesize"],
                )

            # Step 2: Extract structured data from raw outputs
            executive_quotes = extract_executive_quotes(
                investor_output=raw_data.get("intel-investor"),
                social_output=raw_data.get("intel-social"),
            )

            financial_data = extract_financial_data(
                public_output=raw_data.get("intel-financial-public"),
                private_output=raw_data.get("intel-financial-private"),
            )

            search_vendor = extract_search_vendor(
                techstack_output=raw_data.get("intel-techstack"),
            )

            traffic_data = extract_traffic_data(
                traffic_output=raw_data.get("intel-traffic"),
            )

            raw_timing_signals = extract_timing_signals_from_modules(
                news_output=raw_data.get("intel-news"),
                hiring_output=raw_data.get("intel-hiring"),
                investor_output=raw_data.get("intel-investor"),
                competitors_output=raw_data.get("intel-competitors"),
            )

            # Step 3: Synthesize with Claude
            output, llm_calls, llm_cost_usd = await self._enricher.synthesize(
                domain=context.domain,
                company_name=context.company_name,
                raw_data=raw_data,
                executive_quotes=executive_quotes,
                financial_data=financial_data,
                search_vendor=search_vendor,
                traffic_data=traffic_data,
                raw_timing_signals=raw_timing_signals,
            )

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

            # Determine status
            has_said_vs_found = len(output.said_vs_found) >= 3
            has_value_levers = len(output.value_levers) >= 3
            has_summary = bool(output.executive_summary.strip())
            all_good = has_said_vs_found and has_value_levers and has_summary
            status = "success" if all_good else "partial"

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
                "[BusinessCase] execute completed",
                domain=context.domain,
                status=status,
                duration_ms=duration_ms,
                said_vs_found_rows=len(output.said_vs_found),
                value_lever_count=len(output.value_levers),
                timing_signal_count=len(output.timing_signals),
                customer_proof_count=len(output.customer_proofs),
                llm_calls=llm_calls,
                llm_cost_usd=llm_cost_usd,
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.error(
                "[BusinessCase] execute failed",
                error=str(error),
                context={"domain": context.domain, "audit_id": context.audit_id},
            )
            return ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="failed",
                output=BusinessCaseOutput(domain=context.domain).model_dump(),
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
        logger.info("[BusinessCase] validate started", module=self.name)

        try:
            output = BusinessCaseOutput.model_validate(result.output)
            return validate_output(output, result.sources)
        except Exception as error:
            logger.error(
                "[BusinessCase] validate failed",
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
            logger.warning("[BusinessCase] No LLM provider configured")
            return False
