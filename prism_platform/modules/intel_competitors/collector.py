"""Intel Competitors collector -- reads upstream module outputs from module_executions table.

This module does NOT call external APIs. It reads the output_json from other modules
that have already run for the same audit, then passes that data to the enricher for
LLM-powered synthesis.
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select

from prism_platform.core.types import EvidenceTier, Source
from prism_platform.db.models import ModuleExecution
from prism_platform.db.session import async_session_factory
from prism_platform.modules.intel_competitors.schemas import (
    ExecutiveSentiment,
    FinancialComparison,
    HiringComparison,
    TechComparison,
    TrafficComparison,
)

logger = structlog.get_logger(__name__)

# Modules whose outputs we read for competitive synthesis.
UPSTREAM_MODULES = [
    "intel-techstack",
    "intel-traffic",
    "intel-financial-public",
    "intel-financial-private",
    "intel-hiring",
    "intel-news",
    "intel-social",
    "intel-investor",
]


class CompetitorsCollector:
    """Reads outputs from other modules for synthesis. NO external API calls."""

    async def collect_all(self, audit_id: str, domain: str) -> tuple[dict[str, Any], list[Source]]:
        """Read all upstream module outputs from module_executions.

        Args:
            audit_id: The audit ID to scope the query.
            domain: The prospect domain.

        Returns:
            Tuple of (dict mapping module name to output_json, list of Source records).
        """
        logger.info(
            "[Competitors] collect_all started",
            audit_id=audit_id,
            domain=domain,
        )
        data: dict[str, Any] = {}
        sources: list[Source] = []

        for module_name in UPSTREAM_MODULES:
            try:
                output = await self._read_module_output(audit_id, domain, module_name)
                data[module_name] = output
                if output is not None:
                    sources.append(
                        Source(
                            field=f"upstream.{module_name}",
                            value=f"Read from module_executions for {domain}",
                            tier=EvidenceTier.VERIFIED,
                            source_label=f"{module_name} module output",
                            method="db_read",
                        )
                    )
                    logger.debug(
                        "[Competitors] read upstream module output",
                        module_name=module_name,
                        domain=domain,
                        has_data=True,
                    )
                else:
                    logger.warning(
                        "[Competitors] no output found for upstream module",
                        module_name=module_name,
                        domain=domain,
                    )
            except Exception as exc:
                logger.error(
                    "[Competitors] failed to read upstream module",
                    module_name=module_name,
                    domain=domain,
                    error=str(exc),
                )
                data[module_name] = None

        modules_with_data = sum(1 for v in data.values() if v is not None)
        logger.info(
            "[Competitors] collect_all completed",
            audit_id=audit_id,
            domain=domain,
            modules_read=len(UPSTREAM_MODULES),
            modules_with_data=modules_with_data,
        )
        return data, sources

    async def _read_module_output(
        self, audit_id: str, domain: str, module_name: str
    ) -> dict[str, Any] | None:
        """Read a single module's output from DB.

        Args:
            audit_id: The audit ID.
            domain: The prospect domain.
            module_name: Name of the upstream module.

        Returns:
            The output_json dict, or None if not found.
        """
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(ModuleExecution)
                    .where(
                        ModuleExecution.domain == domain,
                        ModuleExecution.module_name == module_name,
                        ModuleExecution.status.in_(["success", "partial"]),
                    )
                    .order_by(ModuleExecution.completed_at.desc())
                    .limit(1)
                )
                row = result.scalar_one_or_none()
                if row and row.output_json:
                    return dict(row.output_json)
                return None
        except Exception as exc:
            logger.error(
                "[Competitors] DB read failed",
                module_name=module_name,
                domain=domain,
                error=str(exc),
            )
            raise


def extract_tech_comparisons(
    techstack_output: dict[str, Any] | None,
    domain: str,
    company_name: str,
) -> tuple[list[TechComparison], list[str], list[str]]:
    """Extract TechComparison objects from intel-techstack output.

    Args:
        techstack_output: The raw output_json from intel-techstack module.
        domain: The prospect domain.
        company_name: The prospect company name.

    Returns:
        Tuple of (tech_comparisons, golden_angle_competitors, tech_gaps).
    """
    if not techstack_output:
        return [], [], []

    comparisons: list[TechComparison] = []
    golden_angle: list[str] = []
    tech_gaps: list[str] = []

    try:
        # Build prospect comparison
        search_vendor_data = techstack_output.get("search_vendor")
        search_vendor_name: str | None = None
        if search_vendor_data and isinstance(search_vendor_data, dict):
            search_vendor_name = search_vendor_data.get("name")

        all_techs = techstack_output.get("all_technologies", [])
        key_tech_names = [
            t.get("Name", "") for t in all_techs if isinstance(t, dict) and t.get("Name")
        ][:20]  # Cap at 20 key technologies

        prospect_comp = TechComparison(
            company_name=company_name,
            domain=domain,
            search_vendor=search_vendor_name,
            ecommerce_platform=techstack_output.get("ecommerce_platform"),
            key_technologies=key_tech_names,
            algolia_detected=techstack_output.get("algolia_detected", False),
        )
        comparisons.append(prospect_comp)

        # Build competitor comparisons
        competitor_stacks = techstack_output.get("competitor_tech_stacks", [])
        for cs in competitor_stacks:
            if not isinstance(cs, dict):
                continue
            cs_vendor = cs.get("search_vendor")
            cs_vendor_name: str | None = None
            if cs_vendor and isinstance(cs_vendor, dict):
                cs_vendor_name = cs_vendor.get("name")

            cs_techs = cs.get("all_technologies", [])
            cs_key_techs = [
                t.get("Name", "") for t in cs_techs if isinstance(t, dict) and t.get("Name")
            ][:20]

            is_algolia = cs.get("is_algolia_customer", False)
            comp_name = cs.get("company_name", cs.get("domain", "Unknown"))

            comp = TechComparison(
                company_name=comp_name,
                domain=cs.get("domain", ""),
                search_vendor=cs_vendor_name,
                ecommerce_platform=cs.get("ecommerce_platform"),
                key_technologies=cs_key_techs,
                algolia_detected=is_algolia,
            )
            comparisons.append(comp)

            if is_algolia:
                golden_angle.append(comp_name)

        # Copy golden_angle_competitors from techstack if available
        golden_from_ts = techstack_output.get("golden_angle_competitors", [])
        for name in golden_from_ts:
            if name not in golden_angle:
                golden_angle.append(name)

        # Identify tech gaps: prospect missing key categories competitors have
        if not prospect_comp.search_vendor and any(c.search_vendor for c in comparisons[1:]):
            tech_gaps.append("Prospect has no detected search vendor while competitors do")

        if not prospect_comp.ecommerce_platform and any(
            c.ecommerce_platform for c in comparisons[1:]
        ):
            tech_gaps.append("Prospect has no detected ecommerce platform while competitors do")

    except Exception as exc:
        logger.error(
            "[Competitors] failed to extract tech comparisons",
            domain=domain,
            error=str(exc),
        )

    return comparisons, golden_angle, tech_gaps


def extract_traffic_comparisons(
    traffic_output: dict[str, Any] | None,
    domain: str,
    company_name: str,
) -> list[TrafficComparison]:
    """Extract TrafficComparison objects from intel-traffic output.

    Args:
        traffic_output: The raw output_json from intel-traffic module.
        domain: The prospect domain.
        company_name: The prospect company name.

    Returns:
        List of TrafficComparison objects.
    """
    if not traffic_output:
        return []

    comparisons: list[TrafficComparison] = []

    try:
        # Build prospect traffic comparison
        monthly_visits = traffic_output.get("total_visits")
        if monthly_visits and isinstance(monthly_visits, (int, float)):
            monthly_visits = int(monthly_visits)
        else:
            monthly_visits = None

        bounce_rate = traffic_output.get("bounce_rate")
        if bounce_rate is not None and not isinstance(bounce_rate, (int, float)):
            bounce_rate = None

        pages_per_visit = traffic_output.get("pages_per_visit")
        if pages_per_visit is not None and not isinstance(pages_per_visit, (int, float)):
            pages_per_visit = None

        # Extract organic search percentage from traffic sources
        organic_pct: float | None = None
        traffic_sources = traffic_output.get("traffic_sources", {})
        if isinstance(traffic_sources, dict):
            organic_pct = traffic_sources.get("organic_search")
            if organic_pct is not None and not isinstance(organic_pct, (int, float)):
                organic_pct = None

        # Determine growth trend from visit history
        growth_trend = ""
        visit_history = traffic_output.get("visit_history", [])
        if isinstance(visit_history, list) and len(visit_history) >= 2:
            try:
                recent = visit_history[-1]
                previous = visit_history[-2]
                r_val = recent.get("visits", 0) if isinstance(recent, dict) else 0
                p_val = previous.get("visits", 0) if isinstance(previous, dict) else 0
                if p_val > 0:
                    change = (r_val - p_val) / p_val
                    if change > 0.05:
                        growth_trend = "growing"
                    elif change < -0.05:
                        growth_trend = "declining"
                    else:
                        growth_trend = "stable"
            except (TypeError, ValueError, ZeroDivisionError):
                pass

        prospect_traffic = TrafficComparison(
            company_name=company_name,
            domain=domain,
            monthly_visits=monthly_visits,
            bounce_rate=float(bounce_rate) if bounce_rate is not None else None,
            pages_per_visit=float(pages_per_visit) if pages_per_visit is not None else None,
            organic_search_pct=float(organic_pct) if organic_pct is not None else None,
            growth_trend=growth_trend,
        )
        comparisons.append(prospect_traffic)

    except Exception as exc:
        logger.error(
            "[Competitors] failed to extract traffic comparisons",
            domain=domain,
            error=str(exc),
        )

    return comparisons


def extract_financial_comparisons(
    public_output: dict[str, Any] | None,
    private_output: dict[str, Any] | None,
    domain: str,
    company_name: str,
    is_private: bool,
) -> list[FinancialComparison]:
    """Extract FinancialComparison objects from financial module outputs.

    Args:
        public_output: The raw output_json from intel-financial-public.
        private_output: The raw output_json from intel-financial-private.
        domain: The prospect domain.
        company_name: The prospect company name.
        is_private: Whether the company is private.

    Returns:
        List of FinancialComparison objects.
    """
    comparisons: list[FinancialComparison] = []

    try:
        source = private_output if is_private else public_output
        if not source:
            # Fall back to whichever is available
            source = public_output or private_output
        if not source:
            return []

        revenue = source.get("revenue") or source.get("annual_revenue")
        if revenue is not None and not isinstance(revenue, (int, float)):
            try:
                revenue = float(revenue)
            except (TypeError, ValueError):
                revenue = None

        revenue_growth = source.get("revenue_growth_pct") or source.get("revenue_growth")
        if revenue_growth is not None and not isinstance(revenue_growth, (int, float)):
            try:
                revenue_growth = float(revenue_growth)
            except (TypeError, ValueError):
                revenue_growth = None

        digital_rev = source.get("digital_revenue_pct") or source.get("ecommerce_revenue_pct")
        if digital_rev is not None and not isinstance(digital_rev, (int, float)):
            try:
                digital_rev = float(digital_rev)
            except (TypeError, ValueError):
                digital_rev = None

        market_cap = source.get("market_cap")
        if market_cap is not None and not isinstance(market_cap, (int, float)):
            try:
                market_cap = float(market_cap)
            except (TypeError, ValueError):
                market_cap = None

        comp = FinancialComparison(
            company_name=company_name,
            domain=domain,
            revenue=float(revenue) if revenue is not None else None,
            revenue_growth_pct=float(revenue_growth) if revenue_growth is not None else None,
            digital_revenue_pct=float(digital_rev) if digital_rev is not None else None,
            market_cap=float(market_cap) if market_cap is not None else None,
        )
        comparisons.append(comp)

    except Exception as exc:
        logger.error(
            "[Competitors] failed to extract financial comparisons",
            domain=domain,
            error=str(exc),
        )

    return comparisons


def extract_hiring_comparisons(
    hiring_output: dict[str, Any] | None,
    domain: str,
    company_name: str,
) -> list[HiringComparison]:
    """Extract HiringComparison objects from intel-hiring output.

    Args:
        hiring_output: The raw output_json from intel-hiring module.
        domain: The prospect domain.
        company_name: The prospect company name.

    Returns:
        List of HiringComparison objects.
    """
    if not hiring_output:
        return []

    comparisons: list[HiringComparison] = []

    try:
        total_roles = hiring_output.get("total_open_roles", 0)
        if not isinstance(total_roles, int):
            try:
                total_roles = int(total_roles)
            except (TypeError, ValueError):
                total_roles = 0

        search_roles = hiring_output.get("search_related_roles", 0)
        if not isinstance(search_roles, int):
            try:
                search_roles = int(search_roles)
            except (TypeError, ValueError):
                search_roles = 0

        build_vs_buy = hiring_output.get("build_vs_buy", "")
        if not isinstance(build_vs_buy, str):
            build_vs_buy = str(build_vs_buy)

        hiring_trend = hiring_output.get("hiring_trend", "")
        if not isinstance(hiring_trend, str):
            hiring_trend = str(hiring_trend)

        comp = HiringComparison(
            company_name=company_name,
            domain=domain,
            total_open_roles=total_roles,
            search_related_roles=search_roles,
            build_vs_buy=build_vs_buy,
            hiring_trend=hiring_trend,
        )
        comparisons.append(comp)

    except Exception as exc:
        logger.error(
            "[Competitors] failed to extract hiring comparisons",
            domain=domain,
            error=str(exc),
        )

    return comparisons


def extract_executive_sentiments(
    investor_output: dict[str, Any] | None,
    social_output: dict[str, Any] | None,
    domain: str,
    company_name: str,
) -> list[ExecutiveSentiment]:
    """Extract ExecutiveSentiment objects from investor and social module outputs.

    Args:
        investor_output: The raw output_json from intel-investor module.
        social_output: The raw output_json from intel-social module.
        domain: The prospect domain.
        company_name: The prospect company name.

    Returns:
        List of ExecutiveSentiment objects.
    """
    comparisons: list[ExecutiveSentiment] = []

    try:
        key_quotes: list[str] = []
        search_mentions = 0
        digital_commitment: str = "unknown"

        # Extract from investor output
        if investor_output:
            quotes = investor_output.get("key_quotes", [])
            if isinstance(quotes, list):
                key_quotes.extend(str(q) for q in quotes[:10])

            exec_quotes = investor_output.get("executive_quotes", [])
            if isinstance(exec_quotes, list):
                for eq in exec_quotes[:10]:
                    if isinstance(eq, dict):
                        quote_text = eq.get("quote", "")
                        if quote_text and str(quote_text) not in key_quotes:
                            key_quotes.append(str(quote_text))
                    elif isinstance(eq, str) and eq not in key_quotes:
                        key_quotes.append(eq)

            inv_search_mentions = investor_output.get("search_mentions", 0)
            if isinstance(inv_search_mentions, int):
                search_mentions += inv_search_mentions

            digital_level = investor_output.get("digital_commitment_level", "")
            if digital_level and isinstance(digital_level, str):
                digital_commitment = digital_level

        # Extract from social output
        if social_output:
            social_quotes = social_output.get("key_quotes", [])
            if isinstance(social_quotes, list):
                for sq in social_quotes[:5]:
                    if isinstance(sq, str) and sq not in key_quotes:
                        key_quotes.append(sq)

            social_search = social_output.get("search_mentions", 0)
            if isinstance(social_search, int):
                search_mentions += social_search

            # Upgrade digital commitment if social shows higher engagement
            if digital_commitment == "unknown":
                social_level = social_output.get("digital_commitment_level", "")
                if social_level and isinstance(social_level, str):
                    digital_commitment = social_level

        # Validate the literal
        if digital_commitment not in ("high", "medium", "low", "unknown"):
            digital_commitment = "unknown"

        if key_quotes or search_mentions > 0 or digital_commitment != "unknown":
            sentiment = ExecutiveSentiment(
                company_name=company_name,
                domain=domain,
                key_quotes=key_quotes,
                digital_commitment_level=digital_commitment,  # type: ignore[arg-type]
                search_mentions=search_mentions,
            )
            comparisons.append(sentiment)

    except Exception as exc:
        logger.error(
            "[Competitors] failed to extract executive sentiments",
            domain=domain,
            error=str(exc),
        )

    return comparisons
