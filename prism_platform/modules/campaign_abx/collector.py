"""Campaign ABX collector -- reads upstream module outputs from module_executions table.

This module does NOT call external APIs. It reads the output_json from other modules
that have already run for the same audit, then passes that data to the enricher for
LLM-powered campaign generation.

Upstream modules read:
- intel-company: company profile, executives, competitors
- intel-hiring: buying committee, open roles, build-vs-buy signal
- intel-investor: executive quotes from earnings calls
- intel-social: executive language and social signals
- intel-competitors: current search vendor, competitive landscape
- intel-techstack: current technology stack
- synth-business-case: ROI numbers, Said vs Found, customer proofs
- synth-sales-plays: MEDDPICC, objection handlers, pre-call talking points
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select

from prism_platform.core.types import EvidenceTier, Source
from prism_platform.db.models import ModuleExecution
from prism_platform.db.session import async_session_factory

logger = structlog.get_logger(__name__)

# Modules whose outputs we read for campaign generation.
UPSTREAM_MODULES = [
    "intel-company",
    "intel-hiring",
    "intel-investor",
    "intel-social",
    "intel-competitors",
    "intel-techstack",
    "synth-business-case",
    "synth-sales-plays",
]


class CampaignCollector:
    """Reads outputs from upstream modules for campaign synthesis. NO external API calls."""

    async def collect_all(self, audit_id: str, domain: str) -> tuple[dict[str, Any], list[Source]]:
        """Read all upstream module outputs from module_executions.

        Args:
            audit_id: The audit ID to scope the query.
            domain: The prospect domain.

        Returns:
            Tuple of (dict mapping module name to output_json, list of Source records).
        """
        logger.info(
            "[CampaignABX] collect_all started",
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
                        "[CampaignABX] read upstream module output",
                        module_name=module_name,
                        domain=domain,
                        has_data=True,
                    )
                else:
                    logger.warning(
                        "[CampaignABX] no output found for upstream module",
                        module_name=module_name,
                        domain=domain,
                    )
            except Exception as exc:
                logger.error(
                    "[CampaignABX] failed to read upstream module",
                    module_name=module_name,
                    domain=domain,
                    error=str(exc),
                )
                data[module_name] = None

        modules_with_data = sum(1 for v in data.values() if v is not None)
        logger.info(
            "[CampaignABX] collect_all completed",
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
                "[CampaignABX] DB read failed",
                module_name=module_name,
                domain=domain,
                error=str(exc),
            )
            raise


def extract_buying_committee(
    company_output: dict[str, Any] | None,
    hiring_output: dict[str, Any] | None,
) -> list[dict[str, str]]:
    """Extract buying committee members from company + hiring intelligence.

    Args:
        company_output: intel-company output_json.
        hiring_output: intel-hiring output_json.

    Returns:
        List of dicts with name, title, relevance, and linkedin_url.
    """
    committee: list[dict[str, str]] = []

    try:
        # From intel-company executives
        if company_output:
            executives = company_output.get("executives", [])
            for exec_data in executives:
                if not isinstance(exec_data, dict):
                    continue
                relevance = exec_data.get("relevance", "other")
                if relevance in ("economic_buyer", "technical_evaluator", "champion_candidate"):
                    committee.append(
                        {
                            "name": exec_data.get("full_name", ""),
                            "title": exec_data.get("title", ""),
                            "relevance": relevance,
                            "linkedin_url": exec_data.get("linkedin_url", ""),
                        }
                    )

        # From intel-hiring buying committee
        if hiring_output:
            hiring_committee = hiring_output.get("buying_committee", [])
            if isinstance(hiring_committee, list):
                existing_names = {m["name"].lower() for m in committee}
                for member in hiring_committee:
                    if not isinstance(member, dict):
                        continue
                    name = member.get("name", "")
                    if name.lower() not in existing_names:
                        committee.append(
                            {
                                "name": name,
                                "title": member.get("title", ""),
                                "relevance": member.get("tier", "other"),
                                "linkedin_url": member.get("linkedin_url", ""),
                            }
                        )

    except Exception as exc:
        logger.error(
            "[CampaignABX] failed to extract buying committee",
            error=str(exc),
        )

    return committee


def extract_executive_quotes(
    investor_output: dict[str, Any] | None,
    social_output: dict[str, Any] | None,
) -> list[dict[str, str]]:
    """Extract executive quotes from investor and social modules.

    Args:
        investor_output: intel-investor output_json.
        social_output: intel-social output_json.

    Returns:
        List of dicts with quote, speaker, source fields.
    """
    quotes: list[dict[str, str]] = []

    try:
        if investor_output:
            # Earnings call quotes
            exec_quotes = investor_output.get("executive_quotes", [])
            if isinstance(exec_quotes, list):
                for eq in exec_quotes[:10]:
                    if isinstance(eq, dict):
                        quotes.append(
                            {
                                "quote": eq.get("quote", ""),
                                "speaker": eq.get("speaker", ""),
                                "source": eq.get("source", "earnings call"),
                            }
                        )
                    elif isinstance(eq, str):
                        quotes.append(
                            {
                                "quote": eq,
                                "speaker": "Executive",
                                "source": "earnings call",
                            }
                        )

            # Key quotes fallback
            key_quotes = investor_output.get("key_quotes", [])
            if isinstance(key_quotes, list):
                existing = {q["quote"] for q in quotes}
                for kq in key_quotes[:5]:
                    text = str(kq) if not isinstance(kq, str) else kq
                    if text not in existing:
                        quotes.append(
                            {
                                "quote": text,
                                "speaker": "Executive",
                                "source": "investor intelligence",
                            }
                        )

        if social_output:
            social_quotes = social_output.get("key_quotes", [])
            if isinstance(social_quotes, list):
                existing = {q["quote"] for q in quotes}
                for sq in social_quotes[:5]:
                    text = str(sq) if not isinstance(sq, str) else sq
                    if text not in existing:
                        quotes.append(
                            {
                                "quote": text,
                                "speaker": "Executive",
                                "source": "social media",
                            }
                        )

    except Exception as exc:
        logger.error(
            "[CampaignABX] failed to extract executive quotes",
            error=str(exc),
        )

    return quotes


def extract_competitor_context(
    competitors_output: dict[str, Any] | None,
    techstack_output: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract competitor and search vendor context for messaging.

    Args:
        competitors_output: intel-competitors output_json.
        techstack_output: intel-techstack output_json.

    Returns:
        Dict with current_vendor, competitive_position, angles, etc.
    """
    context: dict[str, Any] = {
        "current_vendor": "None/Custom",
        "competitive_position": "unknown",
        "competitive_summary": "",
        "top_angles": [],
        "golden_angle_competitors": [],
    }

    try:
        # Search vendor from techstack
        if techstack_output:
            search_vendor = techstack_output.get("search_vendor")
            if search_vendor and isinstance(search_vendor, dict):
                vendor_name = search_vendor.get("name", "")
                if vendor_name:
                    context["current_vendor"] = vendor_name

        # Competitive intelligence
        if competitors_output:
            context["competitive_position"] = competitors_output.get(
                "competitive_position", "unknown"
            )
            context["competitive_summary"] = competitors_output.get("competitive_summary", "")
            context["top_angles"] = competitors_output.get("top_competitive_angles", [])
            context["golden_angle_competitors"] = competitors_output.get(
                "golden_angle_competitors", []
            )

    except Exception as exc:
        logger.error(
            "[CampaignABX] failed to extract competitor context",
            error=str(exc),
        )

    return context


def extract_business_case_data(
    business_case_output: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract ROI numbers, Said vs Found, and customer proofs from business case.

    Args:
        business_case_output: synth-business-case output_json.

    Returns:
        Dict with roi_summary, said_vs_found rows, customer_proofs, one_line_pitch.
    """
    data: dict[str, Any] = {
        "total_conservative_impact": None,
        "total_moderate_impact": None,
        "one_line_pitch": "",
        "said_vs_found": [],
        "customer_proofs": [],
        "value_levers": [],
    }

    try:
        if business_case_output:
            data["total_conservative_impact"] = business_case_output.get(
                "total_conservative_impact"
            )
            data["total_moderate_impact"] = business_case_output.get("total_moderate_impact")
            data["one_line_pitch"] = business_case_output.get("one_line_pitch", "")
            data["said_vs_found"] = business_case_output.get("said_vs_found", [])
            data["customer_proofs"] = business_case_output.get("customer_proofs", [])
            data["value_levers"] = business_case_output.get("value_levers", [])

    except Exception as exc:
        logger.error(
            "[CampaignABX] failed to extract business case data",
            error=str(exc),
        )

    return data


def extract_sales_plays_data(
    sales_plays_output: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract MEDDPICC and objection handlers from sales plays.

    Args:
        sales_plays_output: synth-sales-plays output_json.

    Returns:
        Dict with meddpicc, objection_handlers, pre_call_talking_points.
    """
    data: dict[str, Any] = {
        "meddpicc": {},
        "objection_handlers": [],
        "pre_call_talking_points": [],
    }

    try:
        if sales_plays_output:
            data["meddpicc"] = sales_plays_output.get("meddpicc", {})
            data["objection_handlers"] = sales_plays_output.get("objection_handlers", [])
            data["pre_call_talking_points"] = sales_plays_output.get("pre_call_talking_points", [])

    except Exception as exc:
        logger.error(
            "[CampaignABX] failed to extract sales plays data",
            error=str(exc),
        )

    return data
