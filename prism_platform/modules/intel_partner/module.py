"""Intel Partner module -- partner ecosystem, co-sell opportunities, and SI relationships.

Collects partner overlaps via Crossbeam (or Perplexity fallback), enriches with
Claude via Instructor for co-sell opportunity identification, SI relationship mapping,
vertical case study matching, competitor partner analysis, and recommended partner plays.
"""

from __future__ import annotations

import time
from typing import Any, ClassVar

import structlog
from sqlalchemy import select

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import EvidenceTier, ModuleResult, Source, ValidationResult
from prism_platform.db.models import Account
from prism_platform.db.session import async_session_factory
from prism_platform.modules.intel_partner.collector import PartnerCollector
from prism_platform.modules.intel_partner.enricher import PartnerEnricher
from prism_platform.modules.intel_partner.schemas import PartnerInput, PartnerOutput
from prism_platform.modules.intel_partner.validator import validate_output

logger = structlog.get_logger(__name__)


def _extract_industry(account: Any) -> str:
    """Extract industry from Account.industry column.

    Args:
        account: The Account ORM object with industry column.

    Returns:
        Industry string, or 'Unknown' if not found.
    """
    return account.industry or "Unknown"


def _extract_competitors(account: Any) -> list[dict[str, Any]]:
    """Extract competitor domains from Account.competitors JSONB column.

    Args:
        account: The Account ORM object with competitors JSONB column.

    Returns:
        List of competitor dicts with 'company_name', 'domain' keys.
    """
    raw_competitors: list[dict[str, Any]] = account.competitors or []
    result: list[dict[str, Any]] = []
    for comp in raw_competitors:
        result.append(
            {
                "company_name": comp.get("company_name", ""),
                "domain": comp.get("domain", ""),
            }
        )
    return result


class PartnerModule(ModuleInterface):
    """Partner intelligence via Crossbeam + Perplexity + Claude.

    Collects partner overlaps, identifies co-sell opportunities,
    maps SI relationships, finds vertical case studies, and generates
    recommended partner plays for the sales team.
    """

    name: ClassVar[str] = "intel-partner"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Partner ecosystem intelligence, co-sell opportunities, and SI relationships"
    )
    layer: ClassVar[str] = "intelligence"

    input_schema: ClassVar[type[PartnerInput]] = PartnerInput
    output_schema: ClassVar[type[PartnerOutput]] = PartnerOutput
    dependencies: ClassVar[list[str]] = ["intel-company", "intel-techstack"]
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 300
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        self._collector = PartnerCollector()
        self._enricher = PartnerEnricher()

    async def execute(
        self,
        context: ExecutionContext,
        intelligence: dict[str, Any] | None = None,
    ) -> ModuleResult:
        """Run partner intelligence collection and enrichment.

        Args:
            context: Execution context with domain and audit metadata.
            intelligence: Deprecated, ignored. Data is read from Account columns.

        Returns:
            ModuleResult containing PartnerOutput and source provenance.
        """
        logger.info(
            "[Partner] execute started",
            domain=context.domain,
            audit_id=context.audit_id,
        )
        start_ms = time.monotonic_ns() // 1_000_000

        try:
            # Read industry and competitors from Account columns
            account = await self._load_account(context.domain)
            if account:
                industry = _extract_industry(account)
                competitors = _extract_competitors(account)
            else:
                logger.warning(
                    "[Partner] account not found, falling back to basic search",
                    domain=context.domain,
                )
                industry = "Unknown"
                competitors = []

            # Phase 1: Collect raw data
            raw_data = await self._collector.collect_all(
                domain=context.domain,
                company_name=context.company_name,
                industry=industry,
                competitors=competitors,
            )

            # Phase 2: Enrich with Claude via Instructor
            output, llm_calls, llm_cost = await self._enricher.enrich(
                domain=context.domain,
                company_name=context.company_name,
                industry=industry,
                raw_data=raw_data,
            )

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

            # Build source provenance
            sources = self._build_sources(output, raw_data.get("crossbeam_available", False))

            status = "success" if output.partner_summary or output.partner_play else "partial"

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
                "[Partner] execute completed",
                domain=context.domain,
                status=status,
                duration_ms=duration_ms,
                overlaps_count=len(output.partner_overlaps),
                cosell_count=len(output.co_sell_opportunities),
                si_count=len(output.si_relationships),
                case_studies_count=len(output.vertical_case_studies),
                news_count=len(output.recent_partnerships),
                competitor_count=len(output.competitor_partners),
                has_play=output.partner_play is not None,
                crossbeam_available=output.crossbeam_available,
                llm_calls=llm_calls,
                llm_cost_usd=llm_cost,
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.error(
                "[Partner] execute failed",
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
        """Load Account by domain for extracting industry and competitors.

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
                "[Partner] failed to load account from DB",
                domain=domain,
                error=str(exc),
            )
            return None

    def _build_sources(
        self,
        output: PartnerOutput,
        crossbeam_used: bool,
    ) -> list[Source]:
        """Build source provenance records from the enriched output.

        Args:
            output: The enriched PartnerOutput.
            crossbeam_used: Whether Crossbeam data was actually used.

        Returns:
            List of Source records for provenance tracking.
        """
        sources: list[Source] = []

        # Source for partner overlaps
        if output.partner_overlaps:
            overlap_tier = EvidenceTier.VERIFIED if crossbeam_used else EvidenceTier.WEBSEARCH
            overlap_label = "Crossbeam API" if crossbeam_used else "Perplexity sonar-pro"
            overlap_method = "direct_api" if crossbeam_used else "llm_extraction"
            sources.append(
                Source(
                    field="partner_overlaps",
                    value=f"{len(output.partner_overlaps)} partner overlaps identified",
                    tier=overlap_tier,
                    source_label=overlap_label,
                    method=overlap_method,
                    confidence="high" if crossbeam_used else "medium",
                )
            )

        # Source for co-sell opportunities
        if output.co_sell_opportunities:
            sources.append(
                Source(
                    field="co_sell_opportunities",
                    value=f"{len(output.co_sell_opportunities)} co-sell opportunities identified",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Perplexity sonar-pro + Claude analysis",
                    method="llm_extraction",
                    confidence="medium",
                )
            )

        # Source for SI relationships
        if output.si_relationships:
            sources.append(
                Source(
                    field="si_relationships",
                    value=f"{len(output.si_relationships)} SI relationships identified",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Perplexity sonar-pro",
                    method="llm_extraction",
                    confidence="medium",
                )
            )

        # Source for vertical case studies
        if output.vertical_case_studies:
            sources.append(
                Source(
                    field="vertical_case_studies",
                    value=f"{len(output.vertical_case_studies)} case studies found",
                    tier=EvidenceTier.WEBFETCH,
                    source_label="Perplexity sonar-pro + Algolia case studies",
                    method="llm_extraction",
                    confidence="medium",
                )
            )

        # Source for partner play
        if output.partner_play:
            sources.append(
                Source(
                    field="partner_play",
                    value=f"Recommended: {output.partner_play.recommended_partner}",
                    tier=EvidenceTier.ESTIMATE,
                    source_label="Claude analysis",
                    method="llm_extraction",
                    confidence=output.partner_play.confidence,
                )
            )

        # Source for partnership news
        if output.recent_partnerships:
            sources.append(
                Source(
                    field="recent_partnerships",
                    value=f"{len(output.recent_partnerships)} recent partnerships",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Perplexity sonar-pro",
                    method="llm_extraction",
                    confidence="medium",
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
        logger.info("[Partner] validate started", module=self.name)

        try:
            output = PartnerOutput.model_validate(result.output)
            return validate_output(output, result.sources)
        except Exception as error:
            logger.error(
                "[Partner] validate failed",
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
            True if at least Claude key is set. Perplexity and Crossbeam are optional
            (module works in degraded mode without them).
        """
        from prism_platform.config import settings

        try:
            settings.get_enricher_provider()
            has_llm = True
        except (ValueError, AttributeError):
            has_llm = False
        has_perplexity = bool(settings.perplexity_api_key)
        has_crossbeam = bool(settings.crossbeam_api_key)

        if not has_llm:
            logger.warning("[Partner] No LLM provider configured")
        if not has_perplexity:
            logger.warning("[Partner] perplexity_api_key is not configured")
        if not has_crossbeam:
            logger.info(
                "[Partner] CROSSBEAM_API_KEY not set, will use Perplexity fallback for overlaps"
            )

        # Claude is required for enrichment; Perplexity needed for collection
        return has_llm and has_perplexity
