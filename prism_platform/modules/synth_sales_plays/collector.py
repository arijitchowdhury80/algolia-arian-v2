"""Synth Sales Plays collector -- reads upstream module outputs from module_executions table.

This module does NOT call external APIs. It reads the output_json from other modules
that have already run for the same audit, then passes that data to the enricher for
LLM-powered sales playbook generation.
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

# Modules whose outputs we read for sales playbook synthesis.
UPSTREAM_MODULES = [
    "intel-company",
    "intel-hiring",
    "intel-investor",
    "intel-competitors",
    "intel-social",
    "intel-financial-public",
    "intel-financial-private",
    "intel-techstack",
    "synth-business-case",
]


class SalesPlaysCollector:
    """Reads outputs from other modules for sales playbook synthesis. NO external API calls."""

    async def collect_all(self, audit_id: str, domain: str) -> tuple[dict[str, Any], list[Source]]:
        """Read all upstream module outputs from module_executions.

        Args:
            audit_id: The audit ID to scope the query.
            domain: The prospect domain.

        Returns:
            Tuple of (dict mapping module name to output_json, list of Source records).
        """
        logger.info(
            "[SalesPlays] collect_all started",
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
                        "[SalesPlays] read upstream module output",
                        module_name=module_name,
                        domain=domain,
                        has_data=True,
                    )
                else:
                    logger.warning(
                        "[SalesPlays] no output found for upstream module",
                        module_name=module_name,
                        domain=domain,
                    )
            except Exception as exc:
                logger.error(
                    "[SalesPlays] failed to read upstream module",
                    module_name=module_name,
                    domain=domain,
                    error=str(exc),
                )
                data[module_name] = None

        modules_with_data = sum(1 for v in data.values() if v is not None)
        logger.info(
            "[SalesPlays] collect_all completed",
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
                "[SalesPlays] DB read failed",
                module_name=module_name,
                domain=domain,
                error=str(exc),
            )
            raise


def extract_buying_committee(
    hiring_output: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Extract buying committee members from intel-hiring output.

    Args:
        hiring_output: The raw output_json from intel-hiring module.

    Returns:
        List of dicts with name, title, tier, and linkedin_url.
    """
    if not hiring_output:
        return []

    members: list[dict[str, Any]] = []
    try:
        # Look for buying_committee or key_contacts fields
        committee = hiring_output.get("buying_committee", [])
        if isinstance(committee, list):
            for member in committee:
                if isinstance(member, dict):
                    members.append(
                        {
                            "name": member.get("name", "Unknown"),
                            "title": member.get("title", "Unknown"),
                            "tier": member.get("tier", "unknown"),
                            "linkedin_url": member.get("linkedin_url"),
                        }
                    )

        # Also check key_contacts
        contacts = hiring_output.get("key_contacts", [])
        if isinstance(contacts, list):
            existing_names = {m["name"] for m in members}
            for contact in contacts:
                if isinstance(contact, dict):
                    name = contact.get("name", "Unknown")
                    if name not in existing_names:
                        members.append(
                            {
                                "name": name,
                                "title": contact.get("title", "Unknown"),
                                "tier": contact.get("tier", "unknown"),
                                "linkedin_url": contact.get("linkedin_url"),
                            }
                        )
    except Exception as exc:
        logger.error(
            "[SalesPlays] failed to extract buying committee",
            error=str(exc),
        )

    return members


def extract_exec_quotes(
    investor_output: dict[str, Any] | None,
    social_output: dict[str, Any] | None,
) -> list[dict[str, str]]:
    """Extract executive quotes from investor and social intelligence.

    Args:
        investor_output: The raw output_json from intel-investor module.
        social_output: The raw output_json from intel-social module.

    Returns:
        List of dicts with quote, speaker, and source fields.
    """
    quotes: list[dict[str, str]] = []

    try:
        if investor_output:
            # Executive quotes from investor module
            exec_quotes = investor_output.get("executive_quotes", [])
            if isinstance(exec_quotes, list):
                for eq in exec_quotes[:15]:
                    if isinstance(eq, dict):
                        quotes.append(
                            {
                                "quote": str(eq.get("quote", "")),
                                "speaker": str(eq.get("speaker", eq.get("name", "Executive"))),
                                "source": "investor_intelligence",
                            }
                        )
                    elif isinstance(eq, str):
                        quotes.append(
                            {
                                "quote": eq,
                                "speaker": "Executive",
                                "source": "investor_intelligence",
                            }
                        )

            # Key quotes
            key_quotes = investor_output.get("key_quotes", [])
            if isinstance(key_quotes, list):
                existing = {q["quote"] for q in quotes}
                for kq in key_quotes[:10]:
                    q_text = str(kq) if not isinstance(kq, dict) else str(kq.get("quote", kq))
                    if q_text not in existing:
                        quotes.append(
                            {
                                "quote": q_text,
                                "speaker": "Executive",
                                "source": "investor_intelligence",
                            }
                        )

        if social_output:
            social_quotes = social_output.get("key_quotes", [])
            if isinstance(social_quotes, list):
                existing = {q["quote"] for q in quotes}
                for sq in social_quotes[:10]:
                    q_text = str(sq) if not isinstance(sq, dict) else str(sq.get("quote", sq))
                    if q_text not in existing:
                        quotes.append(
                            {
                                "quote": q_text,
                                "speaker": "Executive",
                                "source": "social_signals",
                            }
                        )

    except Exception as exc:
        logger.error(
            "[SalesPlays] failed to extract exec quotes",
            error=str(exc),
        )

    return quotes


def extract_competitive_context(
    competitors_output: dict[str, Any] | None,
    techstack_output: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract competitive context for objection handling.

    Args:
        competitors_output: The raw output_json from intel-competitors module.
        techstack_output: The raw output_json from intel-techstack module.

    Returns:
        Dict with current_vendor, golden_angle, tech_gaps, and competitive_summary.
    """
    context: dict[str, Any] = {
        "current_vendor": None,
        "golden_angle_competitors": [],
        "tech_gaps": [],
        "competitive_summary": "",
        "build_signal": False,
    }

    try:
        if techstack_output:
            search_vendor = techstack_output.get("search_vendor")
            if isinstance(search_vendor, dict):
                context["current_vendor"] = search_vendor.get("name")
            elif isinstance(search_vendor, str):
                context["current_vendor"] = search_vendor

        if competitors_output:
            context["golden_angle_competitors"] = competitors_output.get(
                "golden_angle_competitors", []
            )
            context["tech_gaps"] = competitors_output.get("tech_gaps", [])
            context["competitive_summary"] = competitors_output.get("competitive_summary", "")

    except Exception as exc:
        logger.error(
            "[SalesPlays] failed to extract competitive context",
            error=str(exc),
        )

    return context


def extract_financial_context(
    public_output: dict[str, Any] | None,
    private_output: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract financial context for the sales playbook.

    Args:
        public_output: The raw output_json from intel-financial-public module.
        private_output: The raw output_json from intel-financial-private module.

    Returns:
        Dict with revenue, growth, and digital commerce data.
    """
    context: dict[str, Any] = {
        "revenue": None,
        "revenue_growth_pct": None,
        "digital_revenue_pct": None,
        "market_cap": None,
    }

    try:
        source = public_output or private_output
        if not source:
            return context

        for key in ["revenue", "annual_revenue"]:
            val = source.get(key)
            if val is not None:
                try:
                    context["revenue"] = float(val)
                    break
                except (TypeError, ValueError):
                    pass

        for key in ["revenue_growth_pct", "revenue_growth"]:
            val = source.get(key)
            if val is not None:
                try:
                    context["revenue_growth_pct"] = float(val)
                    break
                except (TypeError, ValueError):
                    pass

        for key in ["digital_revenue_pct", "ecommerce_revenue_pct"]:
            val = source.get(key)
            if val is not None:
                try:
                    context["digital_revenue_pct"] = float(val)
                    break
                except (TypeError, ValueError):
                    pass

        val = source.get("market_cap")
        if val is not None:
            with contextlib.suppress(TypeError, ValueError):
                context["market_cap"] = float(val)

    except Exception as exc:
        logger.error(
            "[SalesPlays] failed to extract financial context",
            error=str(exc),
        )

    return context


def extract_company_context(
    company_output: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract company context for the sales playbook.

    Args:
        company_output: The raw output_json from intel-company module.

    Returns:
        Dict with company_name, vertical, description, and employee_count.
    """
    context: dict[str, Any] = {
        "company_name": "",
        "vertical": "",
        "description": "",
        "employee_count": None,
    }

    try:
        if not company_output:
            return context

        context["company_name"] = str(company_output.get("company_name", ""))
        context["vertical"] = str(company_output.get("vertical", ""))
        context["description"] = str(company_output.get("description", ""))

        emp = company_output.get("employee_count")
        if emp is not None:
            with contextlib.suppress(TypeError, ValueError):
                context["employee_count"] = int(emp)

    except Exception as exc:
        logger.error(
            "[SalesPlays] failed to extract company context",
            error=str(exc),
        )

    return context


def extract_business_case_context(
    business_case_output: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract business case context for the sales playbook.

    Args:
        business_case_output: The raw output_json from synth-business-case module.

    Returns:
        Dict with ROI data and value propositions.
    """
    context: dict[str, Any] = {
        "total_roi_usd": None,
        "roi_summary": "",
        "value_drivers": [],
    }

    try:
        if not business_case_output:
            return context

        roi = business_case_output.get("total_roi_usd")
        if roi is not None:
            with contextlib.suppress(TypeError, ValueError):
                context["total_roi_usd"] = float(roi)

        context["roi_summary"] = str(business_case_output.get("roi_summary", ""))

        drivers = business_case_output.get("value_drivers", [])
        if isinstance(drivers, list):
            context["value_drivers"] = [str(d) for d in drivers[:10]]

    except Exception as exc:
        logger.error(
            "[SalesPlays] failed to extract business case context",
            error=str(exc),
        )

    return context
