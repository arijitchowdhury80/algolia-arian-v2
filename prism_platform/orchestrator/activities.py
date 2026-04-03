"""PRISM Activities -- module execution as Temporal activities with DB-first caching."""

from __future__ import annotations

import time
from typing import Any

import structlog
from temporalio import activity

from prism_platform.core.module import ExecutionContext
from prism_platform.core.registry import MODULE_REGISTRY
from prism_platform.db.cache import get_cached_result, persist_result
from prism_platform.orchestrator.workflows import RunModuleInput

logger = structlog.get_logger(__name__)


@activity.defn(name="run_module")
async def run_module(input: RunModuleInput) -> dict[str, Any]:
    """Execute a single module with database-first caching.

    1. Check PostgreSQL for a cached result within TTL
    2. If fresh cache exists, return it (no API call)
    3. If no cache or stale, execute and persist

    Args:
        input: RunModuleInput with module_name, domain, audit_id, wave, etc.

    Returns:
        Module result as a dict with status, output, sources, etc.
    """
    module = MODULE_REGISTRY.get(input.module_name)
    if not module:
        logger.error("Unknown module requested", module_name=input.module_name)
        return {"status": "failed", "error": f"Unknown module: {input.module_name}"}

    # Step 1: Check cache
    try:
        cached = await get_cached_result(input.module_name, input.domain)
        if cached is not None:
            logger.info(
                "Module cache hit — skipping API call",
                module_name=input.module_name,
                domain=input.domain,
                audit_id=input.audit_id,
                wave=input.wave,
            )
            return cached
    except Exception as exc:
        logger.error("Cache check failed, proceeding with fresh call", error=str(exc))

    # Step 2: No cache — execute fresh
    context = ExecutionContext(
        audit_id=input.audit_id,
        account_id=input.account_id,
        domain=input.domain,
        company_name=input.company_name,
        ticker=input.ticker,
        is_private=input.is_private,
    )

    start_time = time.monotonic()

    try:
        logger.info(
            "Module execution started (fresh API call)",
            module_name=input.module_name,
            domain=input.domain,
            audit_id=input.audit_id,
            wave=input.wave,
        )

        result = await module.execute(context)

        validation = await module.validate(result)
        if not validation.passed:
            logger.warning(
                "Module validation warnings",
                module_name=input.module_name,
                wave=input.wave,
                errors=validation.errors,
                warnings=validation.warnings,
            )

        duration_ms = int((time.monotonic() - start_time) * 1000)
        result_dict = result.model_dump(mode="json")

        logger.info(
            "Module execution complete (fresh)",
            module_name=input.module_name,
            domain=input.domain,
            status=result.status,
            duration_ms=duration_ms,
            wave=input.wave,
            sources_count=len(result.sources),
        )

        # Step 3: Persist to PostgreSQL
        await persist_result(
            module_name=input.module_name,
            domain=input.domain,
            result_dict=result_dict,
            audit_id=input.audit_id,
        )

        return result_dict

    except Exception as e:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        logger.exception(
            "Module execution failed",
            module_name=input.module_name,
            domain=input.domain,
            wave=input.wave,
            duration_ms=duration_ms,
        )
        return {
            "status": "failed",
            "error": str(e),
            "module_name": input.module_name,
            "duration_ms": duration_ms,
        }
