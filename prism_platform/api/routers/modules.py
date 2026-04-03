"""PRISM Modules Router -- list and execute registered modules."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from prism_platform.core.domain_normalizer import normalize_domain
from prism_platform.core.module import ExecutionContext
from prism_platform.core.registry import MODULE_REGISTRY
from prism_platform.db.cache import get_cached_result, persist_result

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
    company_name: str


@router.get("/", response_model=list[ModuleInfo])
async def list_modules() -> list[ModuleInfo]:
    """List every registered module with its health status."""
    logger.info("list_modules.start", count=len(MODULE_REGISTRY))
    try:
        modules: list[ModuleInfo] = []
        for name, mod in MODULE_REGISTRY.items():
            healthy = await mod.health_check()
            modules.append(
                ModuleInfo(
                    name=name,
                    version=mod.version,
                    description=mod.description,
                    layer=mod.layer,
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
    """Execute a single module with database-first caching.

    1. Check PostgreSQL for a cached result within TTL
    2. If fresh cache exists, return it immediately (no API call)
    3. If no cache or stale, execute the module and persist the result
    """
    domain = normalize_domain(body.domain)
    logger.info("execute_module.start", module_name=module_name, domain=domain, raw_domain=body.domain)

    mod = MODULE_REGISTRY.get(module_name)
    if mod is None:
        logger.warning("execute_module.not_found", module_name=module_name)
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found.")

    # Step 1: Check cache
    try:
        cached = await get_cached_result(module_name, domain)
        if cached is not None:
            logger.info(
                "execute_module.cache_hit",
                module_name=module_name,
                domain=domain,
            )
            return cached
    except Exception as exc:
        logger.error("execute_module.cache_check_failed", error=str(exc))
        # Continue to fresh execution if cache check fails

    # Step 2: No cache — execute fresh
    try:
        context = ExecutionContext(
            audit_id=str(uuid.uuid4()),
            account_id=str(uuid.uuid4()),
            domain=domain,
            company_name=body.company_name,
        )

        result = await mod.execute(context)
        result_dict = result.model_dump(mode="json")

        logger.info(
            "execute_module.fresh_api_call",
            module_name=module_name,
            domain=domain,
            status=result.status,
            duration_ms=result.duration_ms,
        )

        # Step 3: Persist to PostgreSQL for future cache hits
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
