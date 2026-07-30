"""PRISM Benchmarks Router -- read vertical benchmark data."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from core.db.models import VerticalBenchmark
from server.api.deps import DbSession

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/{vertical}", response_model=list[dict[str, Any]])
async def get_benchmarks(vertical: str, session: DbSession) -> list[dict[str, Any]]:
    """Return all benchmarks for a given vertical.

    Args:
        vertical: The vertical classification to look up.
        session: Injected database session.

    Returns:
        List of benchmark dicts with metric data.
    """
    logger.info("get_benchmarks.start", vertical=vertical)
    try:
        result = await session.execute(
            select(VerticalBenchmark).where(
                VerticalBenchmark.vertical == vertical,
            )
        )
        rows = result.scalars().all()

        benchmarks: list[dict[str, Any]] = []
        for row in rows:
            benchmarks.append(
                {
                    "id": str(row.id),
                    "vertical": row.vertical,
                    "metric_name": row.metric_name,
                    "metric_value": row.metric_value,
                    "sample_size": row.sample_size,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    "audit_ids": row.audit_ids,
                }
            )

        logger.info(
            "get_benchmarks.done",
            vertical=vertical,
            count=len(benchmarks),
        )
        return benchmarks

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_benchmarks.failed", error=str(exc), vertical=vertical)
        raise HTTPException(status_code=500, detail="Failed to fetch benchmarks.") from exc
