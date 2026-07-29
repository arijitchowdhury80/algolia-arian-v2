"""Plain in-process audit sequencer — Temporal-free wave orchestration.

Replaces the Temporal ``AuditWorkflow`` *scheduler* for single-box execution.
The Temporal worker was never the executor: ``run_module`` is a plain coroutine
(cache → context → Track-1 collector → Track-2 executor → persist). Temporal
only sequenced the waves and supplied retry/durability this workload doesn't
need. This module walks the same wave plan (single source of truth:
``workflows.ALL_WAVES`` and friends) by calling ``run_module`` directly.

Why this exists: with no Temporal worker deployed, ``POST /audits/{id}/run``
dispatched into a void. ``run_pipeline`` runs the audit in-process so Cass (and
the API) can actually execute a pipeline with zero new infrastructure.

The module runner is injectable so the orchestration logic is unit-testable
without DB, network, or an LLM key.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

import structlog

from prism_platform.orchestrator.activities import run_module
from prism_platform.orchestrator.workflows import (
    QUICK_MODULES,
    WAVE_1_INTEL,
    WAVE_1A_SEED,
    WAVE_1B_BASE,
    WAVE_1C_DERIVED,
    WAVE_2_BROWSER,
    WAVE_3_FACTCHECK,
    WAVE_4_INSIGHTS,
    WAVE_5A_BASE,
    WAVE_5B_DERIVED,
    WAVE_6_REPORT,
    AuditInput,
    AuditResult,
    RunModuleInput,
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# Type of a single-module runner: takes a RunModuleInput, returns a result dict.
ModuleRunner = Callable[[RunModuleInput], Awaitable[dict[str, Any]]]

# Optional progress callback: (event_name, payload). Used for SSE streaming.
ProgressCb = Callable[[str, dict[str, Any]], None]

# Terminal statuses that count as "the module did its job" (mirrors the
# Temporal workflow's _compute_overall_status set).
_OK_STATUSES = {"success", "partial", "started", "skipped"}


def resolve_waves(audit_input: AuditInput) -> list[tuple[int, list[str]]]:
    """Determine which (wave_num, modules) tuples to run for an audit mode.

    Mirrors ``AuditWorkflow._resolve_waves`` but is a pure function (no Temporal
    logger). Full mode splits wave 1 into 1A seed → 1B base → 1C derived so
    composing modules read upstream output from the DB cache.
    """
    mode = audit_input.audit_mode

    if mode == "quick":
        return [(1, QUICK_MODULES)]

    if mode == "bulk_triage":
        return [(1, QUICK_MODULES), (6, ["audit-report"])]

    if mode == "refresh":
        waves: list[tuple[int, list[str]]] = []
        if audit_input.refresh_modules:
            wave_1_modules = [m for m in audit_input.refresh_modules if m in WAVE_1_INTEL]
            if wave_1_modules:
                waves.append((1, wave_1_modules))
        if "audit-browser" in audit_input.refresh_modules:
            waves.append((2, list(WAVE_2_BROWSER)))
        waves.append((3, list(WAVE_3_FACTCHECK)))
        waves.append((4, list(WAVE_4_INSIGHTS)))
        waves.append((5, list(WAVE_5A_BASE)))
        waves.append((5, list(WAVE_5B_DERIVED)))
        waves.append((6, list(WAVE_6_REPORT)))
        waves.sort(key=lambda w: w[0])
        return waves

    # "full" — all six waves; wave 1 split into 3 ordered sub-waves.
    return [
        (1, list(WAVE_1A_SEED)),
        (1, list(WAVE_1B_BASE)),
        (1, list(WAVE_1C_DERIVED)),
        (2, list(WAVE_2_BROWSER)),
        (3, list(WAVE_3_FACTCHECK)),
        (4, list(WAVE_4_INSIGHTS)),
        (5, list(WAVE_5A_BASE)),
        (5, list(WAVE_5B_DERIVED)),
        (6, list(WAVE_6_REPORT)),
    ]


def compute_overall_status(module_results: dict[str, str]) -> str:
    """Derive the audit's overall status from per-module statuses.

    Mirrors ``AuditWorkflow._compute_overall_status`` as a pure function.
    """
    statuses = set(module_results.values())
    if not statuses:
        return "failed"
    if statuses <= _OK_STATUSES:
        return "complete"
    if module_results.get("intel-company") in ("success", "partial"):
        return "partial"
    return "failed"


def _wave_timeout(wave_num: int) -> timedelta:
    """Per-wave timeout, mirroring the Temporal workflow's choices."""
    if wave_num == 2:
        return timedelta(minutes=10)  # browser audit
    if wave_num == 6:
        return timedelta(minutes=20)  # final report generation
    return timedelta(minutes=15)


async def _run_one(
    audit_input: AuditInput,
    module_name: str,
    wave_num: int,
    runner: ModuleRunner,
    timeout: timedelta,
) -> dict[str, Any]:
    """Run a single module with a timeout; never raises — returns a status dict."""
    run_input = RunModuleInput(
        audit_id=audit_input.audit_id,
        account_id=audit_input.account_id,
        module_name=module_name,
        domain=audit_input.domain,
        company_name=audit_input.company_name,
        ticker=audit_input.ticker,
        is_private=audit_input.is_private,
        wave=wave_num,
    )
    try:
        return await asyncio.wait_for(runner(run_input), timeout=timeout.total_seconds())
    except TimeoutError:
        logger.error(
            "module_timeout",
            module_name=module_name,
            wave_num=wave_num,
            timeout_s=timeout.total_seconds(),
        )
        return {"status": "failed", "module_name": module_name, "error": "timeout"}
    except Exception as exc:
        logger.error("module_exception", module_name=module_name, error=str(exc))
        return {"status": "failed", "module_name": module_name, "error": str(exc)}


async def _run_wave(
    audit_input: AuditInput,
    modules: list[str],
    wave_num: int,
    result: AuditResult,
    runner: ModuleRunner,
    on_progress: ProgressCb | None,
) -> str:
    """Run all modules in a wave concurrently; record statuses on ``result``."""
    timeout = _wave_timeout(wave_num)
    outcomes = await asyncio.gather(
        *[_run_one(audit_input, m, wave_num, runner, timeout) for m in modules]
    )

    wave_failed = False
    for name, outcome in zip(modules, outcomes, strict=True):
        status = outcome.get("status", "unknown")
        result.module_results[name] = status
        if status == "failed":
            wave_failed = True
            result.errors.append(f"{name}: {outcome.get('error', 'failed')}")
        if on_progress is not None:
            on_progress("module_complete", {"module": name, "status": status, "wave": wave_num})

    return "failed" if wave_failed else "complete"


async def run_pipeline(
    audit_input: AuditInput,
    *,
    runner: ModuleRunner = run_module,
    on_progress: ProgressCb | None = None,
) -> AuditResult:
    """Run a full audit in-process, wave by wave, without Temporal.

    Args:
        audit_input: Which audit/domain to run and in which mode.
        runner: Per-module coroutine (defaults to the real ``run_module``;
            injected in tests). Must never raise — failures are caught here too.
        on_progress: Optional callback fired after each module completes
            (for SSE streaming to Cass / the SPA).

    Returns:
        AuditResult with per-module + per-wave statuses and an overall verdict.
        intel-company failure in wave 1 aborts the run (all modules depend on it).
    """
    result = AuditResult(
        audit_id=audit_input.audit_id,
        status="running",
        audit_mode=audit_input.audit_mode,
    )

    for wave_num, wave_modules in resolve_waves(audit_input):
        modules = [m for m in wave_modules if m not in audit_input.skip_modules]
        if not modules:
            result.wave_results[wave_num] = "skipped"
            continue

        logger.info("wave_start", audit_id=audit_input.audit_id, wave_num=wave_num, modules=modules)
        result.wave_results[wave_num] = await _run_wave(
            audit_input, modules, wave_num, result, runner, on_progress
        )

        # Gate: intel-company failure aborts the whole audit.
        if wave_num == 1 and result.module_results.get("intel-company") == "failed":
            result.status = "aborted"
            result.errors.append(
                "intel-company failed — aborting audit (all modules depend on it)"
            )
            logger.error("audit_aborted_intel_company_failed", audit_id=audit_input.audit_id)
            return result

    result.status = compute_overall_status(result.module_results)
    logger.info(
        "audit_complete",
        audit_id=audit_input.audit_id,
        overall_status=result.status,
        module_results=result.module_results,
    )
    return result
