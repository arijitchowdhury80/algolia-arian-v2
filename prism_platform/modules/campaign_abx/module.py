"""Campaign ABX module -- multi-touch ABX campaign synthesized from audit intelligence.

This is a DELIVERY-LAYER module. It reads outputs from intelligence and synthesis
modules (stored in module_executions) and uses Claude to generate personalized
campaign content.

Data flow:
1. Collector: reads upstream module outputs from DB
2. Extract: buying committee, exec quotes, competitor context, ROI data, sales plays
3. Enricher: 6 Claude calls → emails, LinkedIn, Loom, schedule, competitor messaging, summary
4. Validator: 10 quality checks
"""

from __future__ import annotations

import time
from typing import ClassVar

import structlog

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import ModuleResult, ValidationResult
from prism_platform.modules.campaign_abx.collector import (
    CampaignCollector,
    extract_business_case_data,
    extract_buying_committee,
    extract_competitor_context,
    extract_executive_quotes,
    extract_sales_plays_data,
)
from prism_platform.modules.campaign_abx.enricher import CampaignEnricher
from prism_platform.modules.campaign_abx.schemas import CampaignInput, CampaignOutput
from prism_platform.modules.campaign_abx.validator import validate_output

logger = structlog.get_logger(__name__)


class CampaignModule(ModuleInterface):
    """Multi-touch ABX campaign generation from audit intelligence.

    Produces: 5-email sequence, LinkedIn messages, Loom script, collateral schedule,
    competitor-specific messaging, and campaign summary.
    Consumed by: AE/BDR teams for prospect outreach.
    """

    name: ClassVar[str] = "campaign-abx"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Multi-touch ABX campaign package synthesized from audit intelligence. "
        "Generates personalized emails, LinkedIn messages, Loom scripts, and "
        "collateral schedule using Claude."
    )
    layer: ClassVar[str] = "delivery"

    input_schema: ClassVar[type[CampaignInput]] = CampaignInput
    output_schema: ClassVar[type[CampaignOutput]] = CampaignOutput
    dependencies: ClassVar[list[str]] = [
        "synth-business-case",
        "synth-sales-plays",
        "intel-hiring",
    ]
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 300  # 5 minutes (6 Claude calls)
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        self._collector = CampaignCollector()
        self._enricher = CampaignEnricher()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run campaign generation for the given domain.

        Reads all upstream module outputs from DB, extracts relevant data,
        and uses Claude to generate personalized campaign content.

        Args:
            context: Execution context with domain and audit metadata.

        Returns:
            ModuleResult containing CampaignOutput and source provenance.
        """
        logger.info(
            "[CampaignABX] execute started",
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
                    "[CampaignABX] no upstream module data found",
                    domain=context.domain,
                    audit_id=context.audit_id,
                )
                duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
                return ModuleResult(
                    module_name=self.name,
                    module_version=self.version,
                    status="failed",
                    output=CampaignOutput(domain=context.domain).model_dump(),
                    sources=sources,
                    duration_ms=duration_ms,
                    errors=["No upstream module data found -- cannot generate campaign"],
                )

            # Step 2: Extract structured data from raw outputs
            buying_committee = extract_buying_committee(
                company_output=raw_data.get("intel-company"),
                hiring_output=raw_data.get("intel-hiring"),
            )

            executive_quotes = extract_executive_quotes(
                investor_output=raw_data.get("intel-investor"),
                social_output=raw_data.get("intel-social"),
            )

            competitor_context = extract_competitor_context(
                competitors_output=raw_data.get("intel-competitors"),
                techstack_output=raw_data.get("intel-techstack"),
            )

            business_case_data = extract_business_case_data(
                business_case_output=raw_data.get("synth-business-case"),
            )

            sales_plays_data = extract_sales_plays_data(
                sales_plays_output=raw_data.get("synth-sales-plays"),
            )

            logger.info(
                "[CampaignABX] data extraction complete",
                domain=context.domain,
                committee_size=len(buying_committee),
                quotes_count=len(executive_quotes),
                has_roi=business_case_data.get("total_conservative_impact") is not None,
                current_vendor=competitor_context.get("current_vendor"),
            )

            # Step 3: Generate campaign with Claude
            output, llm_calls, llm_cost_usd = await self._enricher.generate_campaign(
                domain=context.domain,
                company_name=context.company_name,
                buying_committee=buying_committee,
                executive_quotes=executive_quotes,
                competitor_context=competitor_context,
                business_case_data=business_case_data,
                sales_plays_data=sales_plays_data,
                raw_data=raw_data,
            )

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

            # Determine status
            has_emails = len(output.emails) == 5
            has_linkedin = len(output.linkedin_messages) >= 2
            has_loom = output.loom_script is not None
            has_summary = bool(output.campaign_summary.strip())

            if has_emails and has_linkedin and has_loom and has_summary:
                status = "success"
            elif has_emails or has_linkedin:
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
                "[CampaignABX] execute completed",
                domain=context.domain,
                status=status,
                duration_ms=duration_ms,
                emails=len(output.emails),
                linkedin=len(output.linkedin_messages),
                has_loom=has_loom,
                schedule_weeks=len(output.schedule),
                has_competitor_msg=output.competitor_messaging is not None,
                llm_calls=llm_calls,
                llm_cost_usd=llm_cost_usd,
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.exception(
                "[CampaignABX] execute failed",
                domain=context.domain,
                audit_id=context.audit_id,
            )
            return ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="failed",
                output=CampaignOutput(domain=context.domain).model_dump(),
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
        logger.info("[CampaignABX] validate started", module=self.name)

        try:
            output = CampaignOutput.model_validate(result.output)
            return validate_output(output, result.sources)
        except Exception as error:
            logger.error(
                "[CampaignABX] validate failed -- output deserialization error",
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
            logger.warning("[CampaignABX] No LLM provider configured")
            return False
