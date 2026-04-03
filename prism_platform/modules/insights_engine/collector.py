"""Insights Engine collector -- reads audit data from DB for vertical benchmarking.

Reads the current audit's module_executions and intel-company output to determine
vertical classification, then queries ALL historical audits in the same vertical
by joining audits with accounts.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select

from prism_platform.db.models import Account, Audit, ModuleExecution
from prism_platform.db.session import async_session_factory

logger = structlog.get_logger(__name__)

# Modules whose outputs we aggregate for vertical benchmarking.
BENCHMARK_MODULES = [
    "intel-techstack",
    "intel-traffic",
    "intel-financial-public",
    "intel-financial-private",
    "intel-hiring",
    "audit-report",
]


class InsightsCollector:
    """Reads current + historical audit data from DB for vertical analysis."""

    async def collect_all(
        self,
        audit_id: str,
        domain: str,
    ) -> dict[str, Any]:
        """Read current audit data and all historical audits in the same vertical.

        Args:
            audit_id: The current audit ID.
            domain: The current audit's domain.

        Returns:
            Dict with keys:
                - vertical: str -- the vertical classification
                - current_audit: dict mapping module name to output_json
                - historical_audits: list of dicts, each mapping module name to output_json
                - historical_audit_ids: list of audit ID strings
                - total_audits: int -- total audits in this vertical (including current)
        """
        logger.info(
            "[InsightsCollector] collect_all started",
            audit_id=audit_id,
            domain=domain,
        )

        result: dict[str, Any] = {
            "vertical": "",
            "current_audit": {},
            "historical_audits": [],
            "historical_audit_ids": [],
            "total_audits": 1,
        }

        try:
            # Step 1: Read current audit's module outputs
            current_data = await self._read_audit_modules(audit_id, domain)
            result["current_audit"] = current_data

            # Step 2: Get vertical from intel-company output
            vertical = self._extract_vertical(current_data)
            result["vertical"] = vertical
            logger.info(
                "[InsightsCollector] vertical extracted from intel-company",
                audit_id=audit_id,
                vertical=vertical or "(empty)",
            )

            if not vertical:
                logger.warning(
                    "[InsightsCollector] no vertical found in intel-company output",
                    audit_id=audit_id,
                    domain=domain,
                )
                return result

            # Step 3: Query all historical audits in the same vertical
            historical_audits, historical_ids = await self._read_vertical_audits(
                vertical=vertical,
                exclude_audit_id=audit_id,
            )
            result["historical_audits"] = historical_audits
            result["historical_audit_ids"] = historical_ids
            result["total_audits"] = len(historical_ids) + 1  # +1 for current

            logger.info(
                "[InsightsCollector] collect_all completed",
                audit_id=audit_id,
                domain=domain,
                vertical=vertical,
                historical_count=len(historical_ids),
                total_audits=result["total_audits"],
            )

        except Exception as exc:
            logger.exception(
                "[InsightsCollector] collect_all failed",
                audit_id=audit_id,
                domain=domain,
                error=str(exc),
            )

        return result

    async def _read_audit_modules(
        self,
        audit_id: str,
        domain: str,
    ) -> dict[str, Any]:
        """Read all module outputs for a specific audit.

        Args:
            audit_id: The audit ID to read.
            domain: The audit domain (fallback for lookup).

        Returns:
            Dict mapping module name to output_json.
        """
        data: dict[str, Any] = {}

        logger.info(
            "[InsightsCollector] querying module_executions for current audit",
            audit_id=audit_id,
            domain=domain,
        )
        try:
            async with async_session_factory() as session:
                stmt = (
                    select(ModuleExecution)
                    .where(
                        ModuleExecution.domain == domain,
                        ModuleExecution.status.in_(["success", "partial"]),
                    )
                    .order_by(ModuleExecution.completed_at.desc())
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

                seen_modules: set[str] = set()
                for row in rows:
                    if row.module_name not in seen_modules and row.output_json:
                        data[row.module_name] = dict(row.output_json)
                        seen_modules.add(row.module_name)

                logger.info(
                    "[InsightsCollector] current audit module_executions loaded",
                    audit_id=audit_id,
                    domain=domain,
                    row_count=len(rows),
                    modules_with_data=len(seen_modules),
                    modules_found=list(seen_modules),
                )

        except Exception as exc:
            logger.error(
                "[InsightsCollector] failed to read audit modules",
                audit_id=audit_id,
                domain=domain,
                error=str(exc),
            )

        return data

    def _extract_vertical(self, audit_data: dict[str, Any]) -> str:
        """Extract vertical classification from intel-company output.

        Args:
            audit_data: Dict mapping module name to output_json.

        Returns:
            The vertical string, or empty string if not found.
        """
        try:
            company_output = audit_data.get("intel-company")
            if not company_output or not isinstance(company_output, dict):
                return ""
            vertical = company_output.get("industry", "")
            if isinstance(vertical, str):
                return vertical.strip()
            return ""
        except Exception as exc:
            logger.error(
                "[InsightsCollector] failed to extract vertical",
                error=str(exc),
            )
            return ""

    async def _read_vertical_audits(
        self,
        vertical: str,
        exclude_audit_id: str,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Query all historical audits in the same vertical.

        Joins audits with accounts on account_id and filters by accounts.industry.

        Args:
            vertical: The vertical to match.
            exclude_audit_id: Audit ID to exclude (current audit).

        Returns:
            Tuple of (list of module output dicts, list of audit ID strings).
        """
        historical_audits: list[dict[str, Any]] = []
        historical_ids: list[str] = []

        logger.info(
            "[InsightsCollector] querying historical audits",
            vertical=vertical,
            exclude_audit_id=exclude_audit_id,
        )
        try:
            async with async_session_factory() as session:
                # Find all audits in the same vertical via accounts table
                stmt = (
                    select(Audit)
                    .join(Account, Audit.account_id == Account.id)
                    .where(
                        Account.industry == vertical,
                        Audit.id != uuid.UUID(exclude_audit_id),
                        Audit.status.in_(["completed", "success"]),
                    )
                    .order_by(Audit.created_at.desc())
                    .limit(50)  # Cap to avoid huge queries
                )
                result = await session.execute(stmt)
                audits = result.scalars().all()

                for audit in audits:
                    audit_id_str = str(audit.id)
                    historical_ids.append(audit_id_str)

                    # Read module executions for this audit
                    me_stmt = select(ModuleExecution).where(
                        ModuleExecution.audit_id == audit.id,
                        ModuleExecution.status.in_(["success", "partial"]),
                        ModuleExecution.module_name.in_(BENCHMARK_MODULES),
                    )
                    me_result = await session.execute(me_stmt)
                    me_rows = me_result.scalars().all()

                    audit_modules: dict[str, Any] = {}
                    for row in me_rows:
                        if row.output_json:
                            audit_modules[row.module_name] = dict(row.output_json)

                    historical_audits.append(audit_modules)
                    logger.info(
                        "[InsightsCollector] loaded historical audit modules",
                        audit_id=audit_id_str,
                        modules_loaded=len(audit_modules),
                        module_names=list(audit_modules.keys()),
                    )

                logger.info(
                    "[InsightsCollector] historical audit query completed",
                    vertical=vertical,
                    audits_found=len(audits),
                    audits_with_modules=sum(1 for a in historical_audits if a),
                )

        except Exception as exc:
            logger.error(
                "[InsightsCollector] failed to read vertical audits",
                vertical=vertical,
                error=str(exc),
            )

        return historical_audits, historical_ids
