"""Intel Traffic module -- web traffic intelligence via SimilarWeb + Perplexity.

This module collects comprehensive traffic data for a prospect domain and
its competitors. It depends on intel-company for competitor domain list.

Data flow:
1. Collector: 10 SimilarWeb endpoints for prospect domain
2. Collector: subset of SimilarWeb endpoints per competitor domain
3. Enricher: Perplexity for Google Trends momentum (prospect + competitors)
4. Validator: 9 quality checks
5. Persist: module_executions (full) + accounts.intelligence (key fields)
"""

from __future__ import annotations

import time
import uuid
from typing import Any, ClassVar

import structlog
from sqlalchemy import select

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import EvidenceTier, ModuleResult, Source, ValidationResult
from prism_platform.db.models import Account
from prism_platform.db.session import async_session_factory
from prism_platform.modules.intel_traffic.collector import TrafficCollector
from prism_platform.modules.intel_traffic.enricher import TrafficEnricher
from prism_platform.modules.intel_traffic.schemas import (
    TrafficInput,
    TrafficOutput,
)
from prism_platform.modules.intel_traffic.validator import validate_output

logger = structlog.get_logger(__name__)


class TrafficModule(ModuleInterface):
    """Web traffic and engagement intelligence module.

    Produces: monthly visits, traffic sources, engagement, device split,
    geo breakdown, keywords, Google Trends momentum, competitor comparison.
    Consumed by: synthesis modules for ROI and business case generation.
    """

    name: ClassVar[str] = "intel-traffic"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Web traffic intelligence via SimilarWeb API + Google Trends via Perplexity. "
        "Produces traffic profile, engagement metrics, keyword analysis, and "
        "competitor traffic comparison."
    )
    layer: ClassVar[str] = "intelligence"

    input_schema: ClassVar[type[TrafficInput]] = TrafficInput
    output_schema: ClassVar[type[TrafficOutput]] = TrafficOutput
    dependencies: ClassVar[list[str]] = ["intel-company"]
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 300  # 5 minutes (SimilarWeb can be slow)
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        self._collector = TrafficCollector()
        self._enricher = TrafficEnricher()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run full traffic intelligence collection and enrichment.

        Steps:
        1. Read competitor domains from Account.competitors column
        2. Collect SimilarWeb data for prospect
        3. Collect SimilarWeb data for each competitor
        4. Enrich with Google Trends via Perplexity
        5. Build seasonal pattern description
        6. Build comparative summary

        Args:
            context: Execution context with domain and audit metadata.

        Returns:
            ModuleResult containing TrafficOutput and source provenance.
        """
        logger.info(
            "[TrafficModule] execute started",
            domain=context.domain,
            audit_id=context.audit_id,
        )
        start_ms = time.monotonic_ns() // 1_000_000
        sources: list[Source] = []
        total_llm_calls = 0
        total_llm_cost = 0.0

        try:
            # Step 1: Read competitor info from Account.competitors column
            competitor_info = await self._read_competitor_info(context.account_id, context.domain)
            competitor_domains = [c["domain"] for c in competitor_info if c.get("domain")]

            logger.info(
                "[TrafficModule] competitor domains loaded",
                domain=context.domain,
                competitor_count=len(competitor_domains),
            )

            # Step 2: Collect SimilarWeb data for prospect
            prospect_data = await self._collector.collect_domain(context.domain)

            # Add SimilarWeb source provenance
            populated_endpoints = [k for k, v in prospect_data.items() if v]
            if populated_endpoints:
                sources.append(
                    Source(
                        field="similarweb_prospect",
                        value=(
                            f"SimilarWeb API: {len(populated_endpoints)} endpoints returned data"
                        ),
                        tier=EvidenceTier.VERIFIED,
                        source_url=f"https://api.similarweb.com/v1/website/{context.domain}/",
                        source_label=f"SimilarWeb API ({context.domain})",
                        method="direct_api",
                    )
                )

            # Step 3: Collect SimilarWeb data for competitors
            competitor_traffic_list = []
            for comp in competitor_info:
                comp_domain = comp.get("domain", "")
                comp_name = comp.get("company_name", comp_domain)
                if not comp_domain:
                    continue

                try:
                    comp_traffic = await self._collector.collect_competitor(comp_domain, comp_name)
                    competitor_traffic_list.append(comp_traffic)
                    sources.append(
                        Source(
                            field=f"similarweb_competitor_{comp_domain}",
                            value=f"SimilarWeb API competitor data for {comp_domain}",
                            tier=EvidenceTier.VERIFIED,
                            source_url=f"https://api.similarweb.com/v1/website/{comp_domain}/",
                            source_label=f"SimilarWeb API ({comp_domain})",
                            method="direct_api",
                        )
                    )
                except Exception as exc:
                    logger.warning(
                        "[TrafficModule] competitor collection failed",
                        competitor_domain=comp_domain,
                        error=str(exc),
                    )

            # Step 4: Google Trends enrichment via Perplexity
            trends_result, trends_calls, trends_cost = await self._enricher.assess_trends(
                context.company_name, context.domain
            )
            total_llm_calls += trends_calls
            total_llm_cost += trends_cost

            if trends_result:
                sources.append(
                    Source(
                        field="google_trends_prospect",
                        value=f"Google Trends assessment: {trends_result.direction}",
                        tier=EvidenceTier.WEBSEARCH,
                        source_label="Perplexity API (Google Trends assessment)",
                        method="llm_extraction",
                    )
                )

            # Step 5: Brand keyword tagging
            brand_terms = _extract_brand_terms(context.company_name, context.domain)
            organic_keywords = prospect_data.get("organic_keywords", [])
            for kw in organic_keywords:
                kw_text = kw.keyword.lower() if hasattr(kw, "keyword") else ""
                if any(term in kw_text for term in brand_terms):
                    kw.is_branded = True

            # Step 6: Build seasonal pattern
            monthly_visits = prospect_data.get("monthly_visits", [])
            seasonal_pattern = _detect_seasonal_pattern(monthly_visits)

            # Step 7: Build comparative summary
            comparative_summary = _build_comparative_summary(
                context.domain,
                prospect_data.get("engagement"),
                competitor_traffic_list,
            )

            # Assemble output
            output = TrafficOutput(
                domain=context.domain,
                monthly_visits=prospect_data.get("monthly_visits", []),
                traffic_sources=prospect_data.get("traffic_sources", []),
                engagement=prospect_data.get("engagement"),
                device_split=prospect_data.get("device_split"),
                demographics=None,  # SimilarWeb demographics requires premium
                top_countries=prospect_data.get("top_countries", []),
                organic_keywords=prospect_data.get("organic_keywords", []),
                paid_keywords=prospect_data.get("paid_keywords", []),
                seasonal_pattern=seasonal_pattern,
                google_trends=trends_result,
                competitor_traffic=competitor_traffic_list,
                comparative_summary=comparative_summary,
            )

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

            result = ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="success" if prospect_data.get("monthly_visits") else "partial",
                output=output.model_dump(),
                sources=sources,
                duration_ms=duration_ms,
                llm_calls=total_llm_calls,
                llm_cost_usd=total_llm_cost,
            )

            logger.info(
                "[TrafficModule] execute completed",
                domain=context.domain,
                status=result.status,
                duration_ms=duration_ms,
                llm_calls=total_llm_calls,
                llm_cost_usd=round(total_llm_cost, 4),
                monthly_visit_months=len(output.monthly_visits),
                traffic_source_count=len(output.traffic_sources),
                competitor_count=len(output.competitor_traffic),
                keyword_count=len(output.organic_keywords),
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.exception(
                "[TrafficModule] execute failed",
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
                llm_calls=total_llm_calls,
                llm_cost_usd=total_llm_cost,
                errors=[f"{type(error).__name__}: {error}"],
            )

    async def validate(self, result: ModuleResult) -> ValidationResult:
        """Validate module output meets quality standards (9 checks).

        Args:
            result: The ModuleResult from execute().

        Returns:
            ValidationResult with pass/fail and diagnostic details.
        """
        logger.info("[TrafficModule] validate started", module=self.name)

        try:
            output = TrafficOutput.model_validate(result.output)
            return validate_output(output, result.sources, expected_domain=output.domain)
        except Exception as error:
            logger.error(
                "[TrafficModule] validate failed -- output deserialization error",
                error=str(error),
            )
            return ValidationResult(
                passed=False,
                checks_run=0,
                checks_passed=0,
                errors=[f"Output deserialization failed: {error}"],
            )

    async def health_check(self) -> bool:
        """Check if SimilarWeb and Perplexity API keys are configured.

        Returns:
            True if all required API keys are set.
        """
        from prism_platform.config import settings

        has_similarweb = bool(settings.similarweb_api_key)
        has_perplexity = bool(settings.perplexity_api_key)

        if not has_similarweb:
            logger.warning("[TrafficModule] SIMILARWEB_API_KEY not set")
        if not has_perplexity:
            logger.warning("[TrafficModule] PERPLEXITY_API_KEY not set")

        return has_similarweb and has_perplexity

    async def _read_competitor_info(self, account_id: str, domain: str = "") -> list[dict[str, str]]:
        """Read competitor domains and names from the Account.competitors column.

        Queries by domain first (works for diagnostic runs where account_id
        may be a placeholder). Falls back to account_id lookup.

        Args:
            account_id: UUID of the account.
            domain: Domain of the account (preferred lookup key).

        Returns:
            List of dicts with 'domain' and 'company_name' keys.
        """
        try:
            async with async_session_factory() as session:
                # Prefer lookup by domain; fall back to account_id
                if domain:
                    stmt = select(Account).where(Account.domain == domain)
                else:
                    stmt = select(Account).where(Account.id == uuid.UUID(account_id))

                row = await session.execute(stmt)
                account = row.scalar_one_or_none()

                if account and account.competitors:
                    return [
                        {
                            "domain": c.get("domain", ""),
                            "company_name": c.get("company_name", ""),
                        }
                        for c in account.competitors
                        if isinstance(c, dict) and c.get("domain")
                    ]

            return []
        except Exception as exc:
            logger.warning(
                "[TrafficModule] failed to read competitor info from DB",
                account_id=account_id,
                domain=domain,
                error=str(exc),
            )
            return []


# ------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------


def _extract_brand_terms(company_name: str, domain: str) -> list[str]:
    """Extract brand-related terms for keyword classification.

    Args:
        company_name: Company name, e.g. 'Dell Technologies'.
        domain: Domain, e.g. 'dell.com'.

    Returns:
        List of lowercase brand terms to match against keywords.
    """
    terms: set[str] = set()
    # Domain without TLD
    domain_base = domain.split(".")[0].lower()
    terms.add(domain_base)

    # Company name words (skip common suffixes)
    skip_words = {"inc", "inc.", "corp", "corp.", "co", "ltd", "llc", "technologies", "group"}
    for word in company_name.lower().split():
        if word not in skip_words and len(word) > 2:
            terms.add(word)

    return list(terms)


def _detect_seasonal_pattern(monthly_visits: list[Any]) -> str:
    """Detect seasonal patterns from monthly visit data.

    Analyzes which months have the highest and lowest traffic to identify
    seasonal patterns like Q4 holiday surges.

    Args:
        monthly_visits: List of MonthlyVisit models.

    Returns:
        Human-readable seasonal pattern description, or empty string if
        insufficient data.
    """
    if len(monthly_visits) < 3:
        return ""

    # Build month -> visits mapping
    month_visits: dict[int, int] = {}
    for mv in monthly_visits:
        month = mv.month if hasattr(mv, "month") else 0
        visits = mv.visits if hasattr(mv, "visits") else 0
        if month > 0 and visits > 0:
            month_visits[month] = visits

    if len(month_visits) < 3:
        return ""

    avg_visits = sum(month_visits.values()) / len(month_visits)
    if avg_visits == 0:
        return ""

    # Find peaks and dips (>15% deviation from average)
    peaks: list[str] = []
    dips: list[str] = []
    month_names = [
        "",
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    for month, visits in sorted(month_visits.items()):
        deviation = (visits - avg_visits) / avg_visits
        if deviation > 0.15:
            peaks.append(month_names[month])
        elif deviation < -0.15:
            dips.append(month_names[month])

    parts: list[str] = []
    if peaks:
        parts.append(f"Peak in {', '.join(peaks)}")
    if dips:
        parts.append(f"Dip in {', '.join(dips)}")

    return "; ".join(parts) if parts else "Relatively stable traffic across months"


def _build_comparative_summary(
    prospect_domain: str,
    engagement: Any | None,
    competitor_traffic: list[Any],
) -> str:
    """Build a narrative summary comparing prospect traffic to competitors.

    Args:
        prospect_domain: The prospect's domain.
        engagement: Prospect's Engagement model (or None).
        competitor_traffic: List of CompetitorTraffic models.

    Returns:
        Comparative narrative string.
    """
    if not competitor_traffic:
        return ""

    parts: list[str] = [f"Traffic comparison for {prospect_domain}:"]

    prospect_visits = engagement.total_visits if engagement and engagement.total_visits else None

    for comp in competitor_traffic:
        comp_name = comp.company_name if hasattr(comp, "company_name") else "Unknown"
        comp_visits = comp.total_visits if hasattr(comp, "total_visits") else None

        if prospect_visits and comp_visits:
            if prospect_visits > comp_visits:
                ratio = prospect_visits / comp_visits
                parts.append(f"{prospect_domain} has {ratio:.1f}x more traffic than {comp_name}")
            elif comp_visits > prospect_visits:
                ratio = comp_visits / prospect_visits
                parts.append(f"{comp_name} has {ratio:.1f}x more traffic than {prospect_domain}")
            else:
                parts.append(f"{prospect_domain} and {comp_name} have similar traffic levels")
        elif comp_visits:
            parts.append(f"{comp_name}: {comp_visits:,} total visits")

    return " ".join(parts) if len(parts) > 1 else ""
