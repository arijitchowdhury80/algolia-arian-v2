"""Audit Factcheck module -- GAN-inspired quality gate for audit outputs.

This module reads ALL upstream module_executions for the current audit,
extracts factual claims, verifies them via Claude (8 batched calls, one
per category), and produces a gate verdict: PROCEED, WARN, or BLOCKED.

It runs as a Temporal child workflow in Wave 5. The workflow/activity
layer handles the child workflow execution.

Data flow:
1. Collector: reads all module_executions from DB -> categorized claims
2. Enricher: Instructor + Claude (8 calls) -> verified claims + verdict
3. Validator: 8 quality checks
"""

from __future__ import annotations

import time
from typing import ClassVar

import structlog

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import EvidenceTier, ModuleResult, Source, ValidationResult
from prism_platform.modules.audit_factcheck.collector import FactcheckCollector
from prism_platform.modules.audit_factcheck.enricher import FactcheckEnricher
from prism_platform.modules.audit_factcheck.schemas import (
    FactcheckInput,
    FactcheckOutput,
)
from prism_platform.modules.audit_factcheck.validator import validate_output

logger = structlog.get_logger(__name__)


class FactcheckModule(ModuleInterface):
    """GAN-inspired quality gate that fact-checks all upstream module outputs.

    Reads ALL module_executions from the DB, extracts factual claims,
    verifies them via Claude, and produces a gate verdict.
    """

    name: ClassVar[str] = "audit-factcheck"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "GAN-inspired quality gate that verifies factual claims from all upstream "
        "modules via Claude Sonnet. Produces gate verdict: PROCEED / WARN / BLOCKED."
    )
    layer: ClassVar[str] = "quality"

    input_schema: ClassVar[type[FactcheckInput]] = FactcheckInput
    output_schema: ClassVar[type[FactcheckOutput]] = FactcheckOutput
    dependencies: ClassVar[list[str]] = []  # Reads ALL upstream modules from DB
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 600  # 10 minutes (8 Claude calls)
    max_retries: ClassVar[int] = 1

    def __init__(self) -> None:
        self._collector = FactcheckCollector()
        self._enricher = FactcheckEnricher()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run full factcheck pipeline: collect claims, verify, produce verdict.

        Steps:
        1. Read all module_executions and extract categorized claims
        2. Verify claims via 8 batched Claude calls
        3. Return ModuleResult with FactcheckOutput

        Args:
            context: Execution context with domain and audit metadata.

        Returns:
            ModuleResult containing FactcheckOutput and source provenance.
        """
        logger.info(
            "[FactcheckModule] execute started",
            domain=context.domain,
            audit_id=context.audit_id,
        )
        start_ms = time.monotonic_ns() // 1_000_000
        sources: list[Source] = []

        try:
            # Step 1: Collect claims from all upstream modules
            categorized_claims, collector_sources = await self._collector.collect_all(
                context.audit_id, context.domain
            )
            sources.extend(collector_sources)

            total_claims = sum(len(v) for v in categorized_claims.values())
            if total_claims == 0:
                duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
                logger.warning(
                    "[FactcheckModule] no claims found in upstream modules",
                    domain=context.domain,
                )
                return ModuleResult(
                    module_name=self.name,
                    module_version=self.version,
                    status="partial",
                    output={},
                    sources=sources,
                    duration_ms=duration_ms,
                    warnings=["No factual claims found in upstream module outputs"],
                )

            # Step 2: Verify claims via Claude (8 calls)
            output, llm_calls, llm_cost = await self._enricher.enrich(
                context.domain, categorized_claims
            )

            # Add enricher source
            sources.append(
                Source(
                    field="factcheck_verification",
                    value=f"Claude {llm_calls} calls, ${llm_cost:.4f}",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Claude Sonnet via Instructor (factcheck)",
                    method="llm_extraction",
                )
            )

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            status = "success"

            result = ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status=status,
                output=output.model_dump(),
                sources=sources,
                duration_ms=duration_ms,
                llm_calls=llm_calls,
                llm_cost_usd=llm_cost,
            )

            logger.info(
                "[FactcheckModule] execute completed",
                domain=context.domain,
                status=status,
                duration_ms=duration_ms,
                llm_calls=llm_calls,
                llm_cost_usd=llm_cost,
                verdict=output.verdict.value,
                total_claims=output.total_claims,
                contradicted_pct=output.contradicted_pct,
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.exception(
                "[FactcheckModule] execute failed",
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
        logger.info("[FactcheckModule] validate started", module=self.name)

        try:
            output = FactcheckOutput.model_validate(result.output)
            return validate_output(output)
        except Exception as error:
            logger.error(
                "[FactcheckModule] validate failed -- output deserialization error",
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
            has_llm = True
        except (ValueError, AttributeError):
            has_llm = False

        if not has_llm:
            logger.warning("[FactcheckModule] No LLM provider configured")

        return has_llm
