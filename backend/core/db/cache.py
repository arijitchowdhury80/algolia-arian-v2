"""PRISM Module Result Cache -- PostgreSQL-backed persistent storage for module results.

Database-first pattern: always return existing data from the database.
Data is persistent — it never expires. The executed_at date is stored so
the freshness endpoint can inform the user how old the data is, and they
can decide whether to refresh specific modules.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select

from core.db.models import ModuleExecution
from core.db.session import async_session_factory

logger = structlog.get_logger(__name__)


async def get_cached_result(
    module_name: str,
    domain: str,
) -> dict[str, Any] | None:
    """Check PostgreSQL for existing module result data.

    Returns the most recent successful/partial result for this module+domain,
    regardless of age. Data is persistent — the date is stored so the
    freshness endpoint can tell the user how old it is.

    Args:
        module_name: The module to look up (e.g., "intel-techstack").
        domain: The domain to look up (e.g., "dell.com").

    Returns:
        The stored ModuleResult as a dict, or None if no data exists.
    """
    async with async_session_factory() as session:
        try:
            result = await session.execute(
                select(ModuleExecution)
                .where(
                    ModuleExecution.module_name == module_name,
                    ModuleExecution.domain == domain,
                    ModuleExecution.status.in_(["success", "partial"]),
                )
                .order_by(ModuleExecution.completed_at.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()

            if row is None:
                logger.info(
                    "[Cache] MISS",
                    module_name=module_name,
                    domain=domain,
                    reason="no data exists",
                )
                return None

            age_hours = (
                round((datetime.now(UTC) - row.completed_at).total_seconds() / 3600, 1)
                if row.completed_at
                else 0
            )
            logger.info(
                "[Cache] HIT",
                module_name=module_name,
                domain=domain,
                executed_at=row.completed_at.isoformat() if row.completed_at else "unknown",
                age_hours=age_hours,
            )

            return {
                "module_name": row.module_name,
                "module_version": row.module_version,
                "status": row.status,
                "output": row.output_json or {},
                "sources": row.sources_json.get("sources", []) if row.sources_json else [],
                "duration_ms": row.duration_ms or 0,
                "llm_calls": row.llm_calls,
                "llm_cost_usd": float(row.llm_cost_usd),
                "errors": [],
                "warnings": [],
                "executed_at": row.completed_at.isoformat() if row.completed_at else None,
                "_cached": True,
            }

        except Exception as exc:
            logger.error("[Cache] lookup failed, proceeding without cache", error=str(exc))
            return None


async def persist_result(
    module_name: str,
    domain: str,
    result_dict: dict[str, Any],
    audit_id: str | None = None,
) -> None:
    """Persist a module execution result to PostgreSQL.

    Args:
        module_name: The module that produced this result.
        domain: The domain that was analyzed.
        result_dict: The ModuleResult as a dict (from model_dump).
        audit_id: Optional audit ID if this was part of a workflow.
    """
    now = datetime.now(UTC)

    async with async_session_factory() as session:
        try:
            execution = ModuleExecution(
                id=uuid.uuid4(),
                audit_id=uuid.UUID(audit_id) if audit_id else None,
                domain=domain,
                module_name=module_name,
                module_version=result_dict.get("module_version", "unknown"),
                status=result_dict.get("status", "failed"),
                output_json=result_dict.get("output", {}),
                sources_json={"sources": result_dict.get("sources", [])},
                duration_ms=result_dict.get("duration_ms", 0),
                llm_calls=result_dict.get("llm_calls", 0),
                llm_cost_usd=result_dict.get("llm_cost_usd", 0.0),
                error_message="; ".join(result_dict.get("errors", [])) or None,
                started_at=now - timedelta(milliseconds=result_dict.get("duration_ms", 0)),
                completed_at=now,
            )
            session.add(execution)
            await session.commit()

            logger.info(
                "[Cache] STORED",
                module_name=module_name,
                domain=domain,
                status=result_dict.get("status"),
                execution_id=str(execution.id),
            )

        except Exception as exc:
            await session.rollback()
            logger.error(
                "[Cache] persist failed",
                module_name=module_name,
                domain=domain,
                error=str(exc),
            )
