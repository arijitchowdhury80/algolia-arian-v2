"""Audit Factcheck collector -- reads ALL module_executions for an audit and extracts claims.

This module does NOT call external APIs. It reads the output_json from all upstream
modules that have run for the same audit, then extracts factual claims organized
by 8 verification categories.
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select

from prism_platform.core.types import EvidenceTier, Source
from prism_platform.db.models import ModuleExecution
from prism_platform.db.session import async_session_factory
from prism_platform.modules.audit_factcheck.schemas import Claim, VerificationCategory

logger = structlog.get_logger(__name__)

# Mapping from module name to verification category.
MODULE_CATEGORY_MAP: dict[str, VerificationCategory] = {
    "intel-company": VerificationCategory.COMPANY_FACTS,
    "intel-financial-public": VerificationCategory.FINANCIAL_CLAIMS,
    "intel-financial-private": VerificationCategory.FINANCIAL_CLAIMS,
    "intel-techstack": VerificationCategory.TECHNOLOGY_CLAIMS,
    "intel-traffic": VerificationCategory.TRAFFIC_CLAIMS,
    "intel-competitors": VerificationCategory.COMPETITIVE_CLAIMS,
    "synth-business-case": VerificationCategory.SYNTHESIS_CLAIMS,
    "synth-sales-plays": VerificationCategory.SYNTHESIS_CLAIMS,
    "intel-hiring": VerificationCategory.HIRING_CLAIMS,
    "intel-investor": VerificationCategory.QUOTE_CLAIMS,
    "intel-social": VerificationCategory.QUOTE_CLAIMS,
    "intel-news": VerificationCategory.QUOTE_CLAIMS,
}


class FactcheckCollector:
    """Reads all module_executions for an audit and extracts factual claims."""

    async def collect_all(
        self,
        audit_id: str,
        domain: str,
    ) -> tuple[dict[VerificationCategory, list[Claim]], list[Source]]:
        """Read all upstream module outputs and extract factual claims.

        Args:
            audit_id: The audit ID to scope the query.
            domain: The prospect domain.

        Returns:
            Tuple of (dict mapping category to list of Claims, list of Source records).
        """
        logger.info(
            "[Factcheck] collect_all started",
            audit_id=audit_id,
            domain=domain,
        )

        # Initialize empty lists for all 8 categories
        categorized_claims: dict[VerificationCategory, list[Claim]] = {
            cat: [] for cat in VerificationCategory
        }
        sources: list[Source] = []

        logger.info(
            "[Factcheck] reading all module_executions from DB",
            audit_id=audit_id,
            domain=domain,
        )
        try:
            module_outputs = await self._read_all_module_outputs(audit_id, domain)
        except Exception as exc:
            logger.error(
                "[Factcheck] failed to read module_executions",
                audit_id=audit_id,
                domain=domain,
                error=str(exc),
            )
            return categorized_claims, sources

        for module_name, output_json in module_outputs.items():
            if output_json is None:
                logger.debug(
                    "[Factcheck] skipping module with no output",
                    module_name=module_name,
                )
                continue

            category = MODULE_CATEGORY_MAP.get(module_name)
            if category is None:
                logger.debug(
                    "[Factcheck] module not in category map, skipping",
                    module_name=module_name,
                )
                continue

            try:
                claims = extract_claims_from_output(module_name, category, output_json)
                categorized_claims[category].extend(claims)

                sources.append(
                    Source(
                        field=f"upstream.{module_name}",
                        value=f"Extracted {len(claims)} claims from {module_name}",
                        tier=EvidenceTier.VERIFIED,
                        source_label=f"{module_name} module output",
                        method="db_read",
                    )
                )

                logger.info(
                    "[Factcheck] extracted claims from module",
                    module_name=module_name,
                    category=category.value,
                    claim_count=len(claims),
                )
            except Exception as exc:
                logger.error(
                    "[Factcheck] failed to extract claims from module",
                    module_name=module_name,
                    error=str(exc),
                )

        total_claims = sum(len(v) for v in categorized_claims.values())
        category_breakdown = {
            cat.value: len(claims) for cat, claims in categorized_claims.items() if len(claims) > 0
        }
        logger.info(
            "[Factcheck] collect_all completed",
            audit_id=audit_id,
            domain=domain,
            total_claims=total_claims,
            categories_with_claims=sum(1 for v in categorized_claims.values() if len(v) > 0),
            category_breakdown=category_breakdown,
            modules_processed=len(module_outputs),
        )

        return categorized_claims, sources

    async def _read_all_module_outputs(
        self,
        audit_id: str,
        domain: str,
    ) -> dict[str, dict[str, Any] | None]:
        """Read all module outputs from the DB for a given audit.

        Args:
            audit_id: The audit ID.
            domain: The prospect domain.

        Returns:
            Dict mapping module_name to output_json (or None if no output).
        """
        data: dict[str, dict[str, Any] | None] = {}

        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(ModuleExecution)
                    .where(
                        ModuleExecution.domain == domain,
                        ModuleExecution.status.in_(["success", "partial"]),
                    )
                    .order_by(ModuleExecution.completed_at.desc())
                )
                rows = result.scalars().all()
                logger.info(
                    "[Factcheck] DB query returned rows",
                    audit_id=audit_id,
                    domain=domain,
                    row_count=len(rows),
                )

                for row in rows:
                    # Only take the first (most recent) execution per module
                    if row.module_name not in data:
                        data[row.module_name] = dict(row.output_json) if row.output_json else None

            logger.info(
                "[Factcheck] read module outputs from DB",
                audit_id=audit_id,
                domain=domain,
                modules_found=len(data),
                modules_with_data=sum(1 for v in data.values() if v is not None),
            )
        except Exception as exc:
            logger.error(
                "[Factcheck] DB read failed",
                audit_id=audit_id,
                domain=domain,
                error=str(exc),
            )
            raise

        return data


def extract_claims_from_output(
    module_name: str,
    category: VerificationCategory,
    output_json: dict[str, Any],
) -> list[Claim]:
    """Extract factual claims from a module's output JSON.

    Walks the output dictionary and creates Claim objects for values that
    represent factual assertions (strings, numbers, booleans with context).

    Args:
        module_name: Name of the source module.
        category: The verification category for these claims.
        output_json: The raw output_json from the module execution.

    Returns:
        List of Claim objects extracted from the output.
    """
    claims: list[Claim] = []

    try:
        _extract_recursive(
            module_name=module_name,
            category=category,
            data=output_json,
            path="",
            claims=claims,
        )
    except Exception as exc:
        logger.error(
            "[Factcheck] recursive extraction failed",
            module_name=module_name,
            error=str(exc),
        )

    return claims


def _extract_recursive(
    module_name: str,
    category: VerificationCategory,
    data: Any,
    path: str,
    claims: list[Claim],
) -> None:
    """Recursively walk a nested dict/list and extract factual claim text.

    Args:
        module_name: Name of the source module.
        category: The verification category.
        data: Current data node to process.
        path: Dot-separated path for context.
        claims: Accumulator list for extracted claims.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key
            _extract_recursive(module_name, category, value, new_path, claims)
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            new_path = f"{path}[{idx}]"
            _extract_recursive(module_name, category, item, new_path, claims)
    elif isinstance(data, str) and len(data) > 10:
        # Only extract non-trivial strings as claims
        claims.append(
            Claim(
                claim_text=data,
                source_module=module_name,
                category=category,
                evidence_text=f"Field: {path}",
                evidence_source_url=None,
            )
        )
    elif isinstance(data, (int, float)) and path:
        # Numeric claims with context
        claims.append(
            Claim(
                claim_text=f"{path} = {data}",
                source_module=module_name,
                category=category,
                evidence_text=f"Field: {path}",
                evidence_source_url=None,
            )
        )
