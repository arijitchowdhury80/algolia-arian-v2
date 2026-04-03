"""Synth Business Case collector -- reads upstream module outputs from module_executions table.

This module does NOT call external APIs. It reads the output_json from other modules
that have already run for the same audit, then passes that data to the enricher for
LLM-powered business case synthesis.
"""

from __future__ import annotations

import contextlib
from typing import Any

import structlog
from sqlalchemy import select

from prism_platform.core.types import EvidenceTier, Source
from prism_platform.db.models import ModuleExecution
from prism_platform.db.session import async_session_factory

logger = structlog.get_logger(__name__)

# Modules whose outputs we read for business case synthesis.
UPSTREAM_MODULES = [
    "intel-company",
    "intel-financial-public",
    "intel-financial-private",
    "intel-traffic",
    "intel-competitors",
    "intel-investor",
    "intel-industry",
    "intel-techstack",
    "intel-hiring",
    "intel-news",
    "intel-social",
]


class BusinessCaseCollector:
    """Reads outputs from other modules for business case synthesis. NO external API calls."""

    async def collect_all(self, audit_id: str, domain: str) -> tuple[dict[str, Any], list[Source]]:
        """Read all upstream module outputs from module_executions.

        Args:
            audit_id: The audit ID to scope the query.
            domain: The prospect domain.

        Returns:
            Tuple of (dict mapping module name to output_json, list of Source records).
        """
        logger.info(
            "[BusinessCase] collect_all started",
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
                        "[BusinessCase] read upstream module output",
                        module_name=module_name,
                        domain=domain,
                        has_data=True,
                    )
                else:
                    logger.warning(
                        "[BusinessCase] no output found for upstream module",
                        module_name=module_name,
                        domain=domain,
                    )
            except Exception as exc:
                logger.error(
                    "[BusinessCase] failed to read upstream module",
                    module_name=module_name,
                    domain=domain,
                    error=str(exc),
                )
                data[module_name] = None

        modules_with_data = sum(1 for v in data.values() if v is not None)
        logger.info(
            "[BusinessCase] collect_all completed",
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
                "[BusinessCase] DB read failed",
                module_name=module_name,
                domain=domain,
                error=str(exc),
            )
            raise


def extract_executive_quotes(
    investor_output: dict[str, Any] | None,
    social_output: dict[str, Any] | None,
) -> list[str]:
    """Extract executive quotes from investor and social module outputs.

    Args:
        investor_output: The raw output_json from intel-investor module.
        social_output: The raw output_json from intel-social module.

    Returns:
        List of quote strings.
    """
    quotes: list[str] = []

    try:
        if investor_output:
            key_quotes = investor_output.get("key_quotes", [])
            if isinstance(key_quotes, list):
                quotes.extend(str(q) for q in key_quotes[:10])

            exec_quotes = investor_output.get("executive_quotes", [])
            if isinstance(exec_quotes, list):
                for eq in exec_quotes[:10]:
                    if isinstance(eq, dict):
                        quote_text = eq.get("quote", "")
                        speaker = eq.get("speaker", "")
                        source = eq.get("source", "")
                        if quote_text:
                            formatted = str(quote_text)
                            if speaker:
                                formatted = f"{speaker}: {formatted}"
                            if source:
                                formatted = f"{formatted} ({source})"
                            if formatted not in quotes:
                                quotes.append(formatted)
                    elif isinstance(eq, str) and eq not in quotes:
                        quotes.append(eq)

        if social_output:
            social_quotes = social_output.get("key_quotes", [])
            if isinstance(social_quotes, list):
                for sq in social_quotes[:5]:
                    if isinstance(sq, str) and sq not in quotes:
                        quotes.append(sq)

    except Exception as exc:
        logger.error(
            "[BusinessCase] failed to extract executive quotes",
            error=str(exc),
        )

    return quotes


def extract_financial_data(
    public_output: dict[str, Any] | None,
    private_output: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract key financial data from financial module outputs.

    Args:
        public_output: The raw output_json from intel-financial-public.
        private_output: The raw output_json from intel-financial-private.

    Returns:
        Dict with normalized financial fields.
    """
    result: dict[str, Any] = {
        "revenue": None,
        "revenue_growth_pct": None,
        "digital_revenue_pct": None,
        "market_cap": None,
        "ecommerce_revenue": None,
    }

    try:
        source = public_output or private_output
        if not source:
            return result

        # Revenue
        revenue = source.get("revenue") or source.get("annual_revenue")
        if revenue is not None:
            with contextlib.suppress(TypeError, ValueError):
                result["revenue"] = float(revenue)

        # Revenue growth
        growth = source.get("revenue_growth_pct") or source.get("revenue_growth")
        if growth is not None:
            with contextlib.suppress(TypeError, ValueError):
                result["revenue_growth_pct"] = float(growth)

        # Digital revenue percentage
        digital = source.get("digital_revenue_pct") or source.get("ecommerce_revenue_pct")
        if digital is not None:
            with contextlib.suppress(TypeError, ValueError):
                result["digital_revenue_pct"] = float(digital)

        # Market cap
        mcap = source.get("market_cap")
        if mcap is not None:
            with contextlib.suppress(TypeError, ValueError):
                result["market_cap"] = float(mcap)

        # Calculate ecommerce revenue if possible
        if result["revenue"] and result["digital_revenue_pct"]:
            result["ecommerce_revenue"] = result["revenue"] * result["digital_revenue_pct"] / 100.0

    except Exception as exc:
        logger.error(
            "[BusinessCase] failed to extract financial data",
            error=str(exc),
        )

    return result


def extract_search_vendor(
    techstack_output: dict[str, Any] | None,
) -> str | None:
    """Extract the current search vendor from techstack output.

    Args:
        techstack_output: The raw output_json from intel-techstack module.

    Returns:
        Search vendor name or None.
    """
    if not techstack_output:
        return None

    try:
        vendor_data = techstack_output.get("search_vendor")
        if vendor_data and isinstance(vendor_data, dict):
            return vendor_data.get("name")
        if isinstance(vendor_data, str):
            return vendor_data
    except Exception as exc:
        logger.error(
            "[BusinessCase] failed to extract search vendor",
            error=str(exc),
        )

    return None


def extract_traffic_data(
    traffic_output: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract key traffic data from traffic module output.

    Args:
        traffic_output: The raw output_json from intel-traffic module.

    Returns:
        Dict with normalized traffic fields.
    """
    result: dict[str, Any] = {
        "monthly_visits": None,
        "bounce_rate": None,
        "pages_per_visit": None,
        "organic_search_pct": None,
    }

    if not traffic_output:
        return result

    try:
        visits = traffic_output.get("total_visits")
        if visits is not None:
            with contextlib.suppress(TypeError, ValueError):
                result["monthly_visits"] = int(visits)

        bounce = traffic_output.get("bounce_rate")
        if bounce is not None:
            with contextlib.suppress(TypeError, ValueError):
                result["bounce_rate"] = float(bounce)

        ppv = traffic_output.get("pages_per_visit")
        if ppv is not None:
            with contextlib.suppress(TypeError, ValueError):
                result["pages_per_visit"] = float(ppv)

        sources = traffic_output.get("traffic_sources", {})
        if isinstance(sources, dict):
            organic = sources.get("organic_search")
            if organic is not None:
                with contextlib.suppress(TypeError, ValueError):
                    result["organic_search_pct"] = float(organic)

    except Exception as exc:
        logger.error(
            "[BusinessCase] failed to extract traffic data",
            error=str(exc),
        )

    return result


def extract_timing_signals_from_modules(
    news_output: dict[str, Any] | None,
    hiring_output: dict[str, Any] | None,
    investor_output: dict[str, Any] | None,
    competitors_output: dict[str, Any] | None,
) -> list[dict[str, str]]:
    """Extract raw timing signals from multiple module outputs.

    Args:
        news_output: The raw output_json from intel-news module.
        hiring_output: The raw output_json from intel-hiring module.
        investor_output: The raw output_json from intel-investor module.
        competitors_output: The raw output_json from intel-competitors module.

    Returns:
        List of dicts with signal, source_module, and context fields.
    """
    signals: list[dict[str, str]] = []

    try:
        # News signals
        if news_output:
            articles = news_output.get("articles", []) or news_output.get("news_items", [])
            if isinstance(articles, list):
                for article in articles[:5]:
                    if isinstance(article, dict):
                        title = article.get("title", "")
                        if title:
                            signals.append(
                                {
                                    "signal": str(title),
                                    "source_module": "intel-news",
                                    "context": str(article.get("summary", "")),
                                }
                            )

        # Hiring signals
        if hiring_output:
            search_roles = hiring_output.get("search_related_roles", 0)
            if isinstance(search_roles, int) and search_roles > 0:
                signals.append(
                    {
                        "signal": f"{search_roles} search-related roles open",
                        "source_module": "intel-hiring",
                        "context": hiring_output.get("build_vs_buy", ""),
                    }
                )

            trend = hiring_output.get("hiring_trend", "")
            if (
                trend
                and isinstance(trend, str)
                and trend.lower() in ("accelerating", "growing", "rapid")
            ):
                signals.append(
                    {
                        "signal": f"Hiring trend: {trend}",
                        "source_module": "intel-hiring",
                        "context": "",
                    }
                )

        # Investor signals
        if investor_output:
            digital_level = investor_output.get("digital_commitment_level", "")
            if digital_level and isinstance(digital_level, str) and digital_level == "high":
                signals.append(
                    {
                        "signal": "High digital commitment from executive leadership",
                        "source_module": "intel-investor",
                        "context": "",
                    }
                )

        # Competitor signals
        if competitors_output:
            golden = competitors_output.get("golden_angle_competitors", [])
            if isinstance(golden, list) and golden:
                signals.append(
                    {
                        "signal": f"Competitors using Algolia: {', '.join(str(g) for g in golden)}",
                        "source_module": "intel-competitors",
                        "context": "Golden angle -- competitor success proves value in this vertical",
                    }
                )

    except Exception as exc:
        logger.error(
            "[BusinessCase] failed to extract timing signals",
            error=str(exc),
        )

    return signals
