"""Synth Sales Plays module -- AI-powered sales playbook generation from upstream intelligence.

This is a SYNTHESIS module. It reads outputs from other modules (stored in the
module_executions table) and uses Claude for LLM-powered playbook generation
including MEDDPICC mapping, SPIN questions, objection handling, talk tracks,
and power maps.
"""

from __future__ import annotations

import time
from typing import ClassVar

import structlog

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import ModuleResult, ValidationResult
from prism_platform.modules.synth_sales_plays.collector import (
    SalesPlaysCollector,
    extract_business_case_context,
    extract_buying_committee,
    extract_company_context,
    extract_competitive_context,
    extract_exec_quotes,
    extract_financial_context,
)
from prism_platform.modules.synth_sales_plays.enricher import SalesPlaysEnricher
from prism_platform.modules.synth_sales_plays.schemas import (
    SalesPlaysInput,
    SalesPlaysOutput,
)
from prism_platform.modules.synth_sales_plays.validator import validate_output

logger = structlog.get_logger(__name__)


class SalesPlaysModule(ModuleInterface):
    """AI-powered sales playbook synthesis from upstream intelligence modules."""

    name: ClassVar[str] = "synth-sales-plays"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Synthesizes upstream intelligence outputs into comprehensive sales playbooks "
        "including MEDDPICC mapping, SPIN questions, objection handling, talk tracks, "
        "and power maps using Claude"
    )
    layer: ClassVar[str] = "synthesis"

    input_schema: ClassVar[type[SalesPlaysInput]] = SalesPlaysInput
    output_schema: ClassVar[type[SalesPlaysOutput]] = SalesPlaysOutput
    dependencies: ClassVar[list[str]] = [
        "intel-company",
        "intel-hiring",
        "intel-investor",
        "intel-competitors",
    ]
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 300
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        self._collector = SalesPlaysCollector()
        self._enricher = SalesPlaysEnricher()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run sales playbook synthesis for the given domain.

        Reads all upstream module outputs from the DB, extracts relevant data,
        and uses Claude to synthesize a comprehensive sales playbook.

        Args:
            context: Execution context with domain and audit metadata.

        Returns:
            ModuleResult containing SalesPlaysOutput and source provenance.
        """
        logger.info(
            "[SalesPlays] execute started",
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
                    "[SalesPlays] no upstream module data found",
                    domain=context.domain,
                    audit_id=context.audit_id,
                )
                duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
                return ModuleResult(
                    module_name=self.name,
                    module_version=self.version,
                    status="failed",
                    output=SalesPlaysOutput(domain=context.domain).model_dump(),
                    sources=sources,
                    duration_ms=duration_ms,
                    errors=["No upstream module data found -- cannot synthesize"],
                )

            # Step 2: Extract structured data from raw outputs
            company_context = extract_company_context(
                company_output=raw_data.get("intel-company"),
            )
            buying_committee = extract_buying_committee(
                hiring_output=raw_data.get("intel-hiring"),
            )
            exec_quotes = extract_exec_quotes(
                investor_output=raw_data.get("intel-investor"),
                social_output=raw_data.get("intel-social"),
            )
            competitive_context = extract_competitive_context(
                competitors_output=raw_data.get("intel-competitors"),
                techstack_output=raw_data.get("intel-techstack"),
            )
            financial_context = extract_financial_context(
                public_output=raw_data.get("intel-financial-public"),
                private_output=raw_data.get("intel-financial-private"),
            )
            business_case_context = extract_business_case_context(
                business_case_output=raw_data.get("synth-business-case"),
            )

            # Step 3: Synthesize with Claude
            output, llm_calls, llm_cost_usd = await self._enricher.synthesize(
                domain=context.domain,
                company_name=context.company_name,
                company_context=company_context,
                buying_committee=buying_committee,
                exec_quotes=exec_quotes,
                competitive_context=competitive_context,
                financial_context=financial_context,
                business_case_context=business_case_context,
                raw_data=raw_data,
            )

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

            # Determine status based on playbook completeness
            has_meddpicc = len(output.meddpicc) >= 5
            has_spin = len(output.spin_questions) >= 8
            has_summary = bool(output.playbook_summary.strip())

            if has_meddpicc and has_spin and has_summary:
                status = "success"
            elif has_summary or len(output.meddpicc) > 0 or len(output.spin_questions) > 0:
                status = "partial"
            else:
                status = "failed"

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
                "[SalesPlays] execute completed",
                domain=context.domain,
                status=status,
                duration_ms=duration_ms,
                meddpicc_count=len(output.meddpicc),
                spin_count=len(output.spin_questions),
                objection_count=len(output.objection_handlers),
                talk_track_count=len(output.talk_tracks),
                power_map_count=len(output.power_map),
                llm_calls=llm_calls,
                llm_cost_usd=llm_cost_usd,
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.error(
                "[SalesPlays] execute failed",
                error=str(error),
                context={"domain": context.domain, "audit_id": context.audit_id},
            )
            return ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="failed",
                output=SalesPlaysOutput(domain=context.domain).model_dump(),
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
        logger.info("[SalesPlays] validate started", module=self.name)

        try:
            output = SalesPlaysOutput.model_validate(result.output)
            return validate_output(output, result.sources)
        except Exception as error:
            logger.error(
                "[SalesPlays] validate failed",
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
            logger.warning("[SalesPlays] No LLM provider configured")
            return False
