"""Audit Report collector -- reads ALL upstream module outputs from the database.

This collector does not call external APIs. It reads the output_json from
module_executions for all modules that have completed for this audit.

Module outputs collected:
- intel-company, intel-techstack, intel-traffic
- intel-financial-public, intel-financial-private
- intel-news, intel-hiring, intel-social
- intel-investor, intel-partner, intel-industry
- intel-competitors, intel-queries
- synth-business-case, synth-sales-plays
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select

from prism_platform.db.models import ModuleExecution
from prism_platform.db.session import async_session_factory

logger = structlog.get_logger(__name__)

# All upstream modules whose outputs we need
UPSTREAM_MODULES: list[str] = [
    "intel-company",
    "intel-techstack",
    "intel-traffic",
    "intel-financial-public",
    "intel-financial-private",
    "intel-news",
    "intel-hiring",
    "intel-social",
    "intel-investor",
    "intel-partner",
    "intel-industry",
    "intel-competitors",
    "intel-queries",
    "synth-business-case",
    "synth-sales-plays",
]


class AuditReportCollector:
    """Reads all upstream module outputs from the database for a given audit."""

    async def collect_all(self, audit_id: str, domain: str) -> dict[str, Any]:
        """Read all upstream module outputs from the module_executions table.

        Args:
            audit_id: UUID of the audit to collect outputs for.
            domain: Domain being audited (used as fallback query key).

        Returns:
            Dict keyed by module name, value is the output_json dict.
            Missing or failed modules are omitted from the result.
            Also includes 'modules_found' (list of names) and 'modules_missing' (list of names).
        """
        logger.info(
            "[AuditReportCollector] collect_all started",
            audit_id=audit_id,
            domain=domain,
        )

        results: dict[str, Any] = {}
        modules_found: list[str] = []
        modules_missing: list[str] = []

        try:
            async with async_session_factory() as session:
                # Query by domain, accept success and partial, most recent first
                stmt = (
                    select(ModuleExecution)
                    .where(
                        ModuleExecution.domain == domain,
                        ModuleExecution.status.in_(["success", "partial"]),
                    )
                    .order_by(ModuleExecution.completed_at.desc())
                )
                result = await session.execute(stmt)
                executions = result.scalars().all()

                # Index by module_name (first match = most recent)
                exec_map: dict[str, ModuleExecution] = {}
                for ex in executions:
                    if ex.module_name not in exec_map:
                        exec_map[ex.module_name] = ex

                for module_name in UPSTREAM_MODULES:
                    if module_name in exec_map and exec_map[module_name].output_json:
                        results[module_name] = exec_map[module_name].output_json
                        modules_found.append(module_name)
                        logger.debug(
                            "[AuditReportCollector] module output loaded",
                            module=module_name,
                            output_keys=list(exec_map[module_name].output_json.keys())
                            if isinstance(exec_map[module_name].output_json, dict)
                            else "non-dict",
                        )
                    else:
                        modules_missing.append(module_name)
                        logger.warning(
                            "[AuditReportCollector] module output missing or failed",
                            module=module_name,
                            audit_id=audit_id,
                        )

        except Exception as exc:
            logger.exception(
                "[AuditReportCollector] database query failed",
                audit_id=audit_id,
                domain=domain,
                error=str(exc),
            )
            raise

        results["modules_found"] = modules_found
        results["modules_missing"] = modules_missing

        logger.info(
            "[AuditReportCollector] collect_all completed",
            audit_id=audit_id,
            domain=domain,
            modules_found=len(modules_found),
            modules_missing=len(modules_missing),
            found_list=modules_found,
            missing_list=modules_missing,
        )

        return results
