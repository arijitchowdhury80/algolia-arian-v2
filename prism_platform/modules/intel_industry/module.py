"""Intel Industry module -- Perplexity-powered industry intelligence."""

from __future__ import annotations

import time
from typing import Any, ClassVar

import structlog
from sqlalchemy import select

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import EvidenceTier, ModuleResult, Source, ValidationResult
from prism_platform.db.models import Account
from prism_platform.db.session import async_session_factory
from prism_platform.modules.intel_industry.collector import IndustryCollector
from prism_platform.modules.intel_industry.enricher import IndustryEnricher
from prism_platform.modules.intel_industry.schemas import IndustryInput, IndustryOutput
from prism_platform.modules.intel_industry.validator import validate_output

logger = structlog.get_logger(__name__)


def _extract_industry(account: Any) -> str:
    """Extract industry from Account.industry column.

    Args:
        account: The Account ORM object with industry column.

    Returns:
        Industry string. Defaults to "Technology" if not found.
    """
    return account.industry or "Technology"


def _extract_sub_vertical(account: Any) -> str | None:
    """Extract sub_vertical from Account.sub_vertical column.

    Args:
        account: The Account ORM object with sub_vertical column.

    Returns:
        Sub-vertical string or None.
    """
    return account.sub_vertical or None


class IndustryModule(ModuleInterface):
    """Industry intelligence via Perplexity + Claude.

    Collects vertical benchmarks, industry trends, pain points,
    Algolia case studies, and search vendor landscape data.
    Structures all raw data via Instructor + Claude into typed Pydantic schemas.
    """

    name: ClassVar[str] = "intel-industry"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Industry benchmarks, trends, pain points, and case studies via Perplexity + Claude"
    )
    layer: ClassVar[str] = "intelligence"

    input_schema: ClassVar[type[IndustryInput]] = IndustryInput
    output_schema: ClassVar[type[IndustryOutput]] = IndustryOutput
    dependencies: ClassVar[list[str]] = ["intel-company"]
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 180
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        """Initialize collector and enricher."""
        self._collector = IndustryCollector()
        self._enricher = IndustryEnricher()

    async def execute(
        self,
        context: ExecutionContext,
        intelligence: dict[str, Any] | None = None,
    ) -> ModuleResult:
        """Run industry intelligence collection and enrichment.

        Args:
            context: Execution context with domain and audit metadata.
            intelligence: Deprecated, ignored. Data is read from Account columns.

        Returns:
            ModuleResult containing IndustryOutput and source provenance.
        """
        logger.info(
            "[Industry] execute started",
            domain=context.domain,
            audit_id=context.audit_id,
        )
        start_ms = time.monotonic_ns() // 1_000_000

        try:
            # Read industry context from Account columns
            account = await self._load_account(context.domain)
            if account:
                industry = _extract_industry(account)
                sub_vertical = _extract_sub_vertical(account)
            else:
                logger.warning(
                    "[Industry] account not found, defaulting to Technology",
                    domain=context.domain,
                )
                industry = "Technology"
                sub_vertical = None

            logger.info(
                "[Industry] industry context resolved",
                domain=context.domain,
                industry=industry,
                sub_vertical=sub_vertical,
            )

            # Phase 1: Collect raw data from Perplexity
            raw_data = await self._collector.collect_all(
                domain=context.domain,
                industry=industry,
                sub_vertical=sub_vertical,
            )

            # Phase 2: Enrich with Claude via Instructor
            output, llm_calls, llm_cost = await self._enricher.enrich(
                domain=context.domain,
                industry=industry,
                sub_vertical=sub_vertical,
                raw_data=raw_data,
            )

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

            # Build source provenance
            sources = self._build_sources(output)

            # Determine status based on data quality
            has_benchmarks = len(output.vertical_benchmarks) >= 1
            has_trends = len(output.industry_trends) >= 1
            has_pain_points = len(output.pain_points) >= 1

            if has_benchmarks and has_trends and has_pain_points:
                status = "success"
            elif has_benchmarks or has_trends or has_pain_points:
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
                llm_cost_usd=llm_cost,
            )

            logger.info(
                "[Industry] execute completed",
                domain=context.domain,
                status=status,
                duration_ms=duration_ms,
                benchmarks_count=len(output.vertical_benchmarks),
                trends_count=len(output.industry_trends),
                pain_points_count=len(output.pain_points),
                case_studies_count=len(output.algolia_case_studies),
                vendors_count=len(output.search_vendor_landscape),
                llm_calls=llm_calls,
                llm_cost_usd=llm_cost,
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.error(
                "[Industry] execute failed",
                error=str(error),
                context={"domain": context.domain, "audit_id": context.audit_id},
            )
            return ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="failed",
                output={},
                duration_ms=duration_ms,
                errors=[str(error)],
            )

    @staticmethod
    async def _load_account(domain: str) -> Account | None:
        """Load Account by domain for extracting industry and sub_vertical.

        Args:
            domain: The prospect domain.

        Returns:
            Account object or None if not found.
        """
        try:
            async with async_session_factory() as session:
                stmt = select(Account).where(Account.domain == domain)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        except Exception as exc:
            logger.warning(
                "[Industry] failed to load account from DB",
                domain=domain,
                error=str(exc),
            )
            return None

    def _build_sources(self, output: IndustryOutput) -> list[Source]:
        """Build source provenance records from the enriched output.

        Args:
            output: The enriched IndustryOutput.

        Returns:
            List of Source records for provenance tracking.
        """
        sources: list[Source] = []

        # Source for benchmarks
        if output.vertical_benchmarks:
            sources.append(
                Source(
                    field="vertical_benchmarks",
                    value=f"{len(output.vertical_benchmarks)} benchmarks collected",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Perplexity sonar-pro + Claude structuring",
                    method="llm_extraction",
                    confidence="medium",
                )
            )

        # Source for trends
        if output.industry_trends:
            sources.append(
                Source(
                    field="industry_trends",
                    value=f"{len(output.industry_trends)} trends identified",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Perplexity sonar-pro + Claude structuring",
                    method="llm_extraction",
                    confidence="medium",
                )
            )

        # Source for pain points
        if output.pain_points:
            sources.append(
                Source(
                    field="pain_points",
                    value=f"{len(output.pain_points)} pain points identified",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Perplexity sonar-pro + Claude structuring",
                    method="llm_extraction",
                    confidence="medium",
                )
            )

        # Source for case studies
        if output.algolia_case_studies:
            sources.append(
                Source(
                    field="algolia_case_studies",
                    value=f"{len(output.algolia_case_studies)} case studies found",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Perplexity sonar-pro + Claude structuring",
                    method="llm_extraction",
                    confidence="medium",
                )
            )

        # Source for vendor landscape
        if output.search_vendor_landscape:
            sources.append(
                Source(
                    field="search_vendor_landscape",
                    value=f"{len(output.search_vendor_landscape)} vendors mapped",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Perplexity sonar-pro + Claude structuring",
                    method="llm_extraction",
                    confidence="low",
                )
            )

        return sources

    async def validate(self, result: ModuleResult) -> ValidationResult:
        """Validate module output meets quality standards.

        Args:
            result: The ModuleResult from execute().

        Returns:
            ValidationResult with pass/fail and diagnostic details.
        """
        logger.info("[Industry] validate started", module=self.name)

        try:
            output = IndustryOutput.model_validate(result.output)
            return validate_output(output, result.sources)
        except Exception as error:
            logger.error(
                "[Industry] validate failed",
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

        Returns:
            True if both Perplexity and an LLM provider are configured.
        """
        from prism_platform.config import settings

        has_perplexity = bool(settings.perplexity_api_key)
        try:
            settings.get_enricher_provider()
            has_llm = True
        except (ValueError, AttributeError):
            has_llm = False

        if not has_perplexity:
            logger.warning("[Industry] perplexity_api_key is not configured")
        if not has_llm:
            logger.warning("[Industry] No LLM provider configured")

        return has_perplexity and has_llm
