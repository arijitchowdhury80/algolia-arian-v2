"""Intel Hiring module -- hiring signals, build-vs-buy, and buying committee intelligence.

Collects open job postings via Apify LinkedIn Jobs Scraper (or Perplexity fallback),
enriches with Claude via Instructor for ICP classification, build-vs-buy assessment,
buying committee mapping, and hiring velocity analysis.
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
from prism_platform.modules.intel_hiring.collector import HiringCollector
from prism_platform.modules.intel_hiring.enricher import HiringEnricher
from prism_platform.modules.intel_hiring.schemas import HiringInput, HiringOutput
from prism_platform.modules.intel_hiring.validator import validate_output

logger = structlog.get_logger(__name__)


def _extract_executives(account: Any) -> list[dict[str, Any]]:
    """Extract executive names from Account.executives JSONB column.

    The intel-company module stores executives as a list of dicts with
    'full_name', 'title', 'relevance' keys. We normalize the key names
    for the collector which expects 'name'.

    Args:
        account: The Account ORM object with executives JSONB column.

    Returns:
        List of executive dicts with 'name', 'title', 'relevance' keys.
    """
    raw_execs: list[dict[str, Any]] = account.executives or []
    normalized: list[dict[str, Any]] = []
    for ex in raw_execs:
        normalized.append(
            {
                "name": ex.get("full_name", ex.get("name", "")),
                "title": ex.get("title", ""),
                "relevance": ex.get("relevance", "other"),
            }
        )
    return normalized


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


class HiringModule(ModuleInterface):
    """Hiring intelligence via Apify LinkedIn Jobs + Perplexity + Claude.

    Collects open roles, classifies by ICP tier, determines build-vs-buy
    signal, maps buying committee, computes hiring velocity, and generates
    competitive hiring comparison.
    """

    name: ClassVar[str] = "intel-hiring"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Hiring signals, build-vs-buy assessment, and buying committee intelligence"
    )
    layer: ClassVar[str] = "intelligence"

    input_schema: ClassVar[type[HiringInput]] = HiringInput
    output_schema: ClassVar[type[HiringOutput]] = HiringOutput
    dependencies: ClassVar[list[str]] = ["intel-company"]
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 300
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        self._collector = HiringCollector()
        self._enricher = HiringEnricher()

    async def execute(
        self,
        context: ExecutionContext,
        intelligence: dict[str, Any] | None = None,
    ) -> ModuleResult:
        """Run hiring intelligence collection and enrichment.

        Args:
            context: Execution context with domain and audit metadata.
            intelligence: Deprecated, ignored. Data is read from Account columns.

        Returns:
            ModuleResult containing HiringOutput and source provenance.
        """
        logger.info(
            "[Hiring] execute started",
            domain=context.domain,
            audit_id=context.audit_id,
        )
        start_ms = time.monotonic_ns() // 1_000_000

        try:
            # Read executives and competitors from Account columns
            account = await self._load_account(context.domain)
            if account:
                executives = _extract_executives(account)
                competitors = _extract_competitors(account)
            else:
                logger.warning(
                    "[Hiring] account not found, falling back to basic search",
                    domain=context.domain,
                )
                executives = []
                competitors = []

            # Phase 1: Collect raw data
            raw_data = await self._collector.collect_all(
                domain=context.domain,
                company_name=context.company_name,
                executives=executives,
                competitor_domains=competitors,
            )

            # Phase 2: Enrich with Claude via Instructor
            output, llm_calls, llm_cost = await self._enricher.enrich(
                domain=context.domain,
                company_name=context.company_name,
                raw_data=raw_data,
                executives=executives,
            )

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

            # Build source provenance
            sources = self._build_sources(output, raw_data.get("source_type", "perplexity"))

            status = (
                "success" if len(output.open_roles) >= 1 or output.hiring_summary else "partial"
            )

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
                "[Hiring] execute completed",
                domain=context.domain,
                status=status,
                duration_ms=duration_ms,
                roles_count=len(output.open_roles),
                search_related=output.search_related_count,
                velocity_trend=(output.hiring_velocity.trend if output.hiring_velocity else "none"),
                bvb_signal=output.build_vs_buy.signal if output.build_vs_buy else "none",
                committee_members=(
                    len(output.buying_committee.members) if output.buying_committee else 0
                ),
                competitors_count=len(output.competitor_hiring),
                llm_calls=llm_calls,
                llm_cost_usd=llm_cost,
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.error(
                "[Hiring] execute failed",
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
        """Load Account by domain for extracting executives and competitors.

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
                "[Hiring] failed to load account from DB",
                domain=domain,
                error=str(exc),
            )
            return None

    def _build_sources(
        self,
        output: HiringOutput,
        source_type: str,
    ) -> list[Source]:
        """Build source provenance records from the enriched output.

        Args:
            output: The enriched HiringOutput.
            source_type: 'linkedin' or 'perplexity'.

        Returns:
            List of Source records for provenance tracking.
        """
        sources: list[Source] = []

        # Determine evidence tier based on source
        role_tier = EvidenceTier.VERIFIED if source_type == "linkedin" else EvidenceTier.WEBSEARCH
        role_label = (
            "Apify LinkedIn Jobs Scraper" if source_type == "linkedin" else "Perplexity sonar-pro"
        )
        role_method = "direct_api" if source_type == "linkedin" else "llm_extraction"

        # Source for open roles
        if output.open_roles:
            sources.append(
                Source(
                    field="open_roles",
                    value=f"{len(output.open_roles)} roles collected",
                    tier=role_tier,
                    source_label=role_label,
                    method=role_method,
                    confidence="high" if source_type == "linkedin" else "medium",
                )
            )

        # Source for hiring velocity
        if output.hiring_velocity:
            sources.append(
                Source(
                    field="hiring_velocity",
                    value=f"trend: {output.hiring_velocity.trend}",
                    tier=EvidenceTier.ESTIMATE,
                    source_label="Claude classification",
                    method="llm_extraction",
                    confidence="medium",
                )
            )

        # Source for build vs buy
        if output.build_vs_buy:
            sources.append(
                Source(
                    field="build_vs_buy",
                    value=f"signal: {output.build_vs_buy.signal}",
                    tier=EvidenceTier.ESTIMATE,
                    source_label="Claude classification",
                    method="llm_extraction",
                    confidence=output.build_vs_buy.confidence,
                )
            )

        # Source for buying committee
        if output.buying_committee and output.buying_committee.members:
            sources.append(
                Source(
                    field="buying_committee",
                    value=f"{len(output.buying_committee.members)} members mapped",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Perplexity sonar-pro + Claude mapping",
                    method="llm_extraction",
                    confidence=output.buying_committee.confidence,
                )
            )

        # Source for competitor hiring
        if output.competitor_hiring:
            total_comp_roles = sum(len(c.open_roles) for c in output.competitor_hiring)
            sources.append(
                Source(
                    field="competitor_hiring",
                    value=(
                        f"{total_comp_roles} competitor roles "
                        f"across {len(output.competitor_hiring)} competitors"
                    ),
                    tier=role_tier,
                    source_label=role_label,
                    method=role_method,
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
        logger.info("[Hiring] validate started", module=self.name)

        try:
            output = HiringOutput.model_validate(result.output)
            return validate_output(output, result.sources)
        except Exception as error:
            logger.error(
                "[Hiring] validate failed",
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
            True if Perplexity and an LLM provider are configured.
            Apify token is optional (falls back to Perplexity).
        """
        from prism_platform.config import settings

        has_perplexity = bool(settings.perplexity_api_key)
        try:
            settings.get_enricher_provider()
            has_llm = True
        except (ValueError, AttributeError):
            has_llm = False

        if not has_perplexity:
            logger.warning("[Hiring] perplexity_api_key is not configured")
        if not has_llm:
            logger.warning("[Hiring] No LLM provider configured")
        if not settings.apify_api_key:
            logger.info(
                "[Hiring] APIFY_API_KEY not set, will use Perplexity fallback for job collection"
            )

        return has_perplexity and has_llm
