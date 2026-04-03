"""Audit Report module -- final delivery synthesis for PRISM audits.

This module runs LAST in the pipeline. It reads ALL upstream module outputs
from the database, then synthesizes them into the final deliverable package:
10-dimension scoring, competitor benchmarks, pre-call brief, leave-behind,
and the full assembled audit JSON.

Data flow:
1. Collector: DB read of all module_executions for this audit
2. Enricher: 5 Claude calls -> dimension scores, competitor scores,
   pre-call brief, leave-behind, audit summary
3. Validator: 10 quality checks
"""

from __future__ import annotations

import time
from typing import ClassVar

import structlog

from prism_platform.config import settings
from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import EvidenceTier, ModuleResult, Source, ValidationResult
from prism_platform.modules.audit_report.collector import AuditReportCollector
from prism_platform.modules.audit_report.enricher import AuditReportEnricher
from prism_platform.modules.audit_report.schemas import (
    AuditReportInput,
    AuditReportOutput,
)
from prism_platform.modules.audit_report.validator import validate_output

logger = structlog.get_logger(__name__)


class AuditReportModule(ModuleInterface):
    """Final delivery module -- synthesizes all upstream data into the audit report.

    Produces: 10-dimension scoring, competitor benchmarks, pre-call brief,
    leave-behind, full audit JSON, and executive summary.
    Consumed by: deliverable generators, API responses, and AE-facing UI.
    """

    name: ClassVar[str] = "audit-report"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Final delivery synthesis module. Reads all upstream intelligence and synthesis "
        "module outputs, scores 10 search quality dimensions, generates AE pre-call brief "
        "and prospect-safe leave-behind document."
    )
    layer: ClassVar[str] = "delivery"

    input_schema: ClassVar[type[AuditReportInput]] = AuditReportInput
    output_schema: ClassVar[type[AuditReportOutput]] = AuditReportOutput
    dependencies: ClassVar[list[str]] = [
        "synth-business-case",
        "synth-sales-plays",
        "intel-competitors",
    ]
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 300  # 5 minutes (5 Claude calls)
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        """Initialize collector and enricher components."""
        self._collector = AuditReportCollector()
        self._enricher = AuditReportEnricher()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run the full audit report generation pipeline.

        Steps:
        1. Read all upstream module outputs from DB
        2. Synthesize via 5 Claude LLM calls
        3. Validate output meets quality standards

        Args:
            context: Execution context with domain, audit_id, and company metadata.

        Returns:
            ModuleResult containing AuditReportOutput and source provenance.
        """
        logger.info(
            "[AuditReportModule] execute started",
            domain=context.domain,
            audit_id=context.audit_id,
        )
        start_ms = time.monotonic_ns() // 1_000_000
        sources: list[Source] = []

        try:
            # Step 1: Collect all upstream module outputs
            collected_data = await self._collector.collect_all(context.audit_id, context.domain)

            modules_found = collected_data.get("modules_found", [])
            modules_missing = collected_data.get("modules_missing", [])

            # Add source for the collection step
            sources.append(
                Source(
                    field="collected_modules",
                    value=f"Loaded {len(modules_found)} module outputs from DB",
                    tier=EvidenceTier.VERIFIED,
                    source_label="PRISM module_executions table",
                    method="direct_api",
                )
            )

            # Check we have minimum required data
            if len(modules_found) < 3:
                duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
                logger.error(
                    "[AuditReportModule] insufficient upstream data",
                    domain=context.domain,
                    modules_found=modules_found,
                    modules_missing=modules_missing,
                )
                return ModuleResult(
                    module_name=self.name,
                    module_version=self.version,
                    status="failed",
                    output={},
                    sources=sources,
                    duration_ms=duration_ms,
                    errors=[
                        f"Only {len(modules_found)} upstream modules available "
                        f"(minimum 3 required). Missing: {', '.join(modules_missing)}"
                    ],
                )

            # Resolve company name
            company_name = context.company_name
            if not company_name:
                company_data = collected_data.get("intel-company", {})
                company_name = (
                    company_data.get("common_name")
                    or company_data.get("legal_name")
                    or context.domain
                )

            # Step 2: Enrich via Claude
            output, llm_calls, llm_cost = await self._enricher.enrich(
                context.domain, company_name, collected_data
            )

            # Add enrichment source
            sources.append(
                Source(
                    field="enrichment",
                    value=f"Claude {llm_calls} calls, ${llm_cost:.4f}",
                    tier=EvidenceTier.ESTIMATE,
                    source_label="Claude via Instructor (synthesis)",
                    method="llm_extraction",
                )
            )

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

            # Determine status based on completeness
            status = "success"
            result_warnings: list[str] = []
            if modules_missing:
                status = "partial"
                result_warnings.append(f"Missing upstream modules: {', '.join(modules_missing)}")

            result = ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status=status,
                output=output.model_dump(),
                sources=sources,
                duration_ms=duration_ms,
                llm_calls=llm_calls,
                llm_cost_usd=llm_cost,
                warnings=result_warnings,
            )

            logger.info(
                "[AuditReportModule] execute completed",
                domain=context.domain,
                status=status,
                duration_ms=duration_ms,
                llm_calls=llm_calls,
                llm_cost_usd=llm_cost,
                overall_score=output.overall_score,
                dimension_count=len(output.dimension_scores),
                competitor_count=len(output.competitor_scores),
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.exception(
                "[AuditReportModule] execute failed",
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
        """Validate module output meets quality standards (10 checks).

        Args:
            result: The ModuleResult from execute().

        Returns:
            ValidationResult with pass/fail and diagnostic details.
        """
        logger.info("[AuditReportModule] validate started", module=self.name)

        try:
            output = AuditReportOutput.model_validate(result.output)
            return validate_output(output, result.sources)
        except Exception as error:
            logger.error(
                "[AuditReportModule] validate failed -- output deserialization error",
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
        try:
            settings.get_enricher_provider()
            has_llm = True
        except (ValueError, AttributeError):
            has_llm = False

        if not has_llm:
            logger.warning("[AuditReportModule] No LLM provider configured")

        return has_llm
