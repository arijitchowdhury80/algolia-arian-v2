"""PRISM Modules Router — list and execute registered v2 modules."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from core.db.cache import get_cached_result, persist_result
from core.domain_normalizer import normalize_domain
from core.executor import ModuleExecutor
from core.registry import V2_MODULE_REGISTRY
from core.research_client import make_research_client
from core.types import ExecutionContextV2

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()


class ModuleInfo(BaseModel):
    """Summary of a registered module."""

    name: str
    version: str
    description: str
    layer: str
    healthy: bool


class ExecuteModuleRequest(BaseModel):
    """Body for POST /api/v1/modules/{module_name}/execute."""

    model_config = ConfigDict(extra="forbid")

    domain: str
    company_name: str = ""


@router.get("/", response_model=list[ModuleInfo])
async def list_modules() -> list[ModuleInfo]:
    """List every registered v2 module with its health status."""
    logger.info("list_modules.start", count=len(V2_MODULE_REGISTRY))
    try:
        modules: list[ModuleInfo] = []
        for handle in V2_MODULE_REGISTRY.values():
            healthy = await handle.health_check()
            modules.append(
                ModuleInfo(
                    name=handle.name,
                    version=handle.version,
                    description=handle.description,
                    layer=handle.layer,
                    healthy=healthy,
                )
            )
        logger.info("list_modules.done", count=len(modules))
        return modules
    except Exception as exc:
        logger.error("list_modules.failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to list modules.") from exc


@router.post("/{module_name}/execute")
async def execute_module(module_name: str, body: ExecuteModuleRequest) -> dict[str, Any]:
    """Execute a single v2 module with database-first caching.

    1. Check PostgreSQL for an existing result for this module+domain
    2. If fresh cache exists, return it immediately (no API call)
    3. If no cache, execute via ModuleExecutor and persist the result
    """
    domain = normalize_domain(body.domain)
    logger.info(
        "execute_module.start",
        module_name=module_name,
        domain=domain,
        raw_domain=body.domain,
    )

    handle = V2_MODULE_REGISTRY.get(module_name)
    if handle is None:
        logger.warning("execute_module.not_found", module_name=module_name)
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found.")

    # Step 1: Check cache
    try:
        cached = await get_cached_result(module_name, domain)
        if cached is not None:
            logger.info("execute_module.cache_hit", module_name=module_name, domain=domain)
            return cached
    except Exception as exc:
        logger.error("execute_module.cache_check_failed", error=str(exc))

    # Step 2: Execute fresh
    try:
        v2_context = ExecutionContextV2(
            audit_id=str(uuid.uuid4()),
            account_domain=domain,
            company_name=body.company_name or domain.split(".")[0].title(),
        )

        api = make_research_client(timeout=float(handle.config.timeout_seconds))
        executor = ModuleExecutor(agent_api=api)

        result = await executor.execute(
            config=handle.config,
            context=v2_context,
            output_schema=handle.output_schema,
            playbook_path=handle.playbook_path,
        )

        logger.info(
            "execute_module.fresh_api_call",
            module_name=module_name,
            domain=domain,
            status=result.status,
            llm_calls=result.llm_calls,
        )

        # Optional post-execute hook (e.g. accounts table for intel-company)
        if handle.post_execute and result.status == "success":
            try:
                await handle.post_execute(result, v2_context)
            except Exception as exc:
                logger.error(
                    "execute_module.post_execute_failed",
                    module_name=module_name,
                    error=str(exc),
                )

        result_dict: dict[str, Any] = {
            "module_name": result.module_name,
            "module_version": result.module_version,
            "status": result.status,
            "output": result.output or {},
            "sources": result.citations,
            "duration_ms": result.duration_ms,
            "llm_calls": result.llm_calls,
            "llm_cost_usd": 0.0,
            "errors": result.errors,
        }

        # Step 3: Persist for future cache hits
        await persist_result(
            module_name=module_name,
            domain=domain,
            result_dict=result_dict,
        )

        return result_dict

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("execute_module.failed", error=str(exc), module_name=module_name)
        raise HTTPException(status_code=500, detail="Module execution failed.") from exc
