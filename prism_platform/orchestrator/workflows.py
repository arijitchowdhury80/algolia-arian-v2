"""PRISM Audit Workflow -- Temporal orchestration with wave-based execution.

Logical flow: gather → validate → analyze → synthesize → deliver

Wave execution order:
  Wave 1 — All 13 intel-* modules in parallel (intel-company must succeed)
  Wave 2 — audit-browser (live search testing, needs intel-queries from Wave 1)
  Wave 3 — audit-factcheck (validate all collected data before using it)
  Wave 4 — insights-engine (extract patterns and benchmarks from validated data)
  Wave 5 — synth-business-case, synth-sales-plays, campaign-abx (build deliverables)
  Wave 6 — audit-report (final package using everything from Waves 1-5)

Audit modes:
  "full"         — all 6 waves
  "quick"        — intel-company + intel-techstack + intel-traffic only
  "bulk_triage"  — quick + audit-report
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

# ---------------------------------------------------------------------------
# Wave definitions
# ---------------------------------------------------------------------------

WAVE_1_INTEL: list[str] = [
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
]

WAVE_2_BROWSER: list[str] = ["audit-browser"]

WAVE_3_FACTCHECK: list[str] = ["audit-factcheck"]

WAVE_4_INSIGHTS: list[str] = ["insights-engine"]

WAVE_5_SYNTHESIS: list[str] = [
    "synth-business-case",
    "synth-sales-plays",
    "campaign-abx",
]

WAVE_6_REPORT: list[str] = ["audit-report"]

QUICK_MODULES: list[str] = [
    "intel-company",
    "intel-techstack",
    "intel-traffic",
]

BULK_TRIAGE_MODULES: list[str] = [
    "intel-company",
    "intel-techstack",
    "intel-traffic",
    "audit-report",
]

ALL_WAVES: list[list[str]] = [
    WAVE_1_INTEL,
    WAVE_2_BROWSER,
    WAVE_3_FACTCHECK,
    WAVE_4_INSIGHTS,
    WAVE_5_SYNTHESIS,
    WAVE_6_REPORT,
]

# Map module name → wave number (1-indexed) for observability
MODULE_WAVE_MAP: dict[str, int] = {}
for _wave_idx, _wave_modules in enumerate(ALL_WAVES, start=1):
    for _mod in _wave_modules:
        MODULE_WAVE_MAP[_mod] = _wave_idx


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AuditInput:
    """Input for the audit workflow."""

    audit_id: str
    account_id: str
    domain: str
    company_name: str
    ticker: str | None = None
    is_private: bool = False
    modules_to_run: list[str] | None = None  # None = run all per audit_mode
    audit_mode: str = "full"  # "full", "quick", "bulk_triage", "refresh"
    skip_modules: list[str] = field(default_factory=list)
    refresh_modules: list[str] = field(default_factory=list)


@dataclass
class AuditResult:
    """Result of the audit workflow."""

    audit_id: str
    status: str
    audit_mode: str = "full"
    module_results: dict[str, str] = field(default_factory=dict)
    wave_results: dict[int, str] = field(default_factory=dict)
    factcheck_verdict: str | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class RunModuleInput:
    """Input for the run_module activity."""

    audit_id: str
    account_id: str
    module_name: str
    domain: str
    company_name: str
    ticker: str | None = None
    is_private: bool = False
    wave: int = 0


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


@workflow.defn
class AuditWorkflow:
    """Full prospect audit workflow with wave-based execution and gates.

    Implements proper wave ordering with dependency resolution:
    - intel-company failure in Wave 1 aborts the entire audit
    - Other intel failures are non-fatal (degraded mode)
    - Wave 2 (audit-browser) has a 10-minute timeout
    - Wave 5 (audit-factcheck) runs as a child workflow
    - Wave 6 (insights-engine) is fire-and-forget
    """

    @workflow.run
    async def run(self, input: AuditInput) -> AuditResult:
        """Execute the audit workflow in waves."""
        workflow.logger.info(
            "Audit workflow started",
            extra={
                "audit_id": input.audit_id,
                "domain": input.domain,
                "company_name": input.company_name,
                "audit_mode": input.audit_mode,
                "skip_modules_count": len(input.skip_modules),
                "skip_modules": input.skip_modules,
            },
        )

        result = AuditResult(
            audit_id=input.audit_id,
            status="running",
            audit_mode=input.audit_mode,
        )

        # Determine which modules to run based on audit_mode
        waves_to_run = self._resolve_waves(input)
        workflow.logger.info(
            "Resolved waves to execute",
            extra={
                "audit_id": input.audit_id,
                "wave_count": len(waves_to_run),
                "waves": [(wn, mods) for wn, mods in waves_to_run],
            },
        )

        # Execute waves sequentially
        for wave_num, wave_modules in waves_to_run:
            # Filter out skipped modules
            modules = [m for m in wave_modules if m not in input.skip_modules]
            if not modules:
                workflow.logger.info(
                    "Wave skipped — all modules filtered out",
                    extra={"audit_id": input.audit_id, "wave_num": wave_num},
                )
                result.wave_results[wave_num] = "skipped"
                continue

            workflow.logger.info(
                "Wave starting",
                extra={
                    "audit_id": input.audit_id,
                    "wave_num": wave_num,
                    "module_count": len(modules),
                    "modules": modules,
                },
            )

            wave_status = await self._execute_wave(input, modules, wave_num, result)
            result.wave_results[wave_num] = wave_status

            workflow.logger.info(
                "Wave completed",
                extra={
                    "audit_id": input.audit_id,
                    "wave_num": wave_num,
                    "wave_status": wave_status,
                },
            )

            # Gate: intel-company failure aborts everything
            if wave_num == 1 and result.module_results.get("intel-company") == "failed":
                workflow.logger.error(
                    "intel-company gate check FAILED — aborting audit",
                    extra={
                        "audit_id": input.audit_id,
                        "domain": input.domain,
                        "intel_company_status": result.module_results.get("intel-company"),
                    },
                )
                result.status = "aborted"
                result.errors.append(
                    "intel-company failed — aborting audit (all modules depend on it)"
                )
                return result

            if wave_num == 1:
                workflow.logger.info(
                    "intel-company gate check passed",
                    extra={
                        "audit_id": input.audit_id,
                        "intel_company_status": result.module_results.get("intel-company"),
                    },
                )

        # Determine overall status
        result.status = self._compute_overall_status(result)

        workflow.logger.info(
            "Audit workflow complete",
            extra={
                "audit_id": input.audit_id,
                "domain": input.domain,
                "overall_status": result.status,
                "module_results": result.module_results,
                "wave_results": result.wave_results,
                "factcheck_verdict": result.factcheck_verdict,
                "error_count": len(result.errors),
            },
        )
        return result

    def _resolve_waves(self, input: AuditInput) -> list[tuple[int, list[str]]]:
        """Determine which waves and modules to run based on audit_mode."""
        workflow.logger.debug(
            "Resolving waves for audit mode",
            extra={"audit_id": input.audit_id, "audit_mode": input.audit_mode},
        )

        if input.audit_mode == "quick":
            return [(1, QUICK_MODULES)]

        if input.audit_mode == "bulk_triage":
            return [
                (1, QUICK_MODULES),
                (6, ["audit-report"]),
            ]

        if input.audit_mode == "refresh":
            waves: list[tuple[int, list[str]]] = []
            # Wave 1: run only the specified refresh_modules from intel layer
            if input.refresh_modules:
                wave_1_modules = [m for m in input.refresh_modules if m in WAVE_1_INTEL]
                if wave_1_modules:
                    waves.append((1, wave_1_modules))
            # Always re-run downstream waves after refresh
            if "audit-browser" in input.refresh_modules:
                waves.append((2, list(WAVE_2_BROWSER)))
            waves.append((3, list(WAVE_3_FACTCHECK)))
            waves.append((4, list(WAVE_4_INSIGHTS)))
            waves.append((5, list(WAVE_5_SYNTHESIS)))
            waves.append((6, list(WAVE_6_REPORT)))
            # Sort waves by wave number so execution order is correct
            waves.sort(key=lambda w: w[0])
            return waves

        # "full" mode — all 6 waves
        # gather → validate → analyze → synthesize → deliver
        return [
            (1, list(WAVE_1_INTEL)),        # Gather all intelligence
            (2, list(WAVE_2_BROWSER)),       # Browser-based search audit
            (3, list(WAVE_3_FACTCHECK)),     # Validate collected data
            (4, list(WAVE_4_INSIGHTS)),      # Extract patterns and benchmarks
            (5, list(WAVE_5_SYNTHESIS)),     # Build deliverables from validated insights
            (6, list(WAVE_6_REPORT)),        # Final report package
        ]

    async def _execute_wave(
        self,
        input: AuditInput,
        modules: list[str],
        wave_num: int,
        result: AuditResult,
    ) -> str:
        """Execute all modules in a wave in parallel.

        Special handling:
        - Wave 3 (factcheck): run as child workflow with extended timeout
        - Wave 2 (browser): 10-minute timeout
        """
        # Wave 3 — child workflow for factcheck
        if wave_num == 3 and "audit-factcheck" in modules:
            workflow.logger.info(
                "Wave 3 delegating to factcheck child workflow",
                extra={"audit_id": input.audit_id},
            )
            return await self._execute_factcheck_child(input, result)

        # Determine timeout per wave
        if wave_num == 2:
            timeout = timedelta(minutes=10)  # Browser audit
        elif wave_num == 6:
            timeout = timedelta(minutes=20)  # Final report generation
        else:
            timeout = timedelta(minutes=15)

        workflow.logger.info(
            "Executing wave modules in parallel",
            extra={
                "audit_id": input.audit_id,
                "wave_num": wave_num,
                "modules": modules,
                "timeout_minutes": timeout.total_seconds() / 60,
            },
        )

        # Run all modules in parallel
        tasks = [
            workflow.execute_activity(
                "run_module",
                RunModuleInput(
                    audit_id=input.audit_id,
                    account_id=input.account_id,
                    module_name=name,
                    domain=input.domain,
                    company_name=input.company_name,
                    ticker=input.ticker,
                    is_private=input.is_private,
                    wave=wave_num,
                ),
                start_to_close_timeout=timeout,
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    backoff_coefficient=2.0,
                ),
            )
            for name in modules
        ]

        results_list: list[dict[str, Any]] = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        wave_failed = False
        success_count = 0
        failed_count = 0
        for name, mod_result in zip(modules, results_list, strict=True):
            if isinstance(mod_result, BaseException):
                result.module_results[name] = "failed"
                result.errors.append(f"{name}: {mod_result}")
                wave_failed = True
                failed_count += 1
                workflow.logger.error(
                    "Module failed with exception",
                    extra={
                        "audit_id": input.audit_id,
                        "wave_num": wave_num,
                        "module_name": name,
                        "error": str(mod_result),
                        "error_type": type(mod_result).__name__,
                    },
                )
            else:
                status = mod_result.get("status", "unknown")
                result.module_results[name] = status
                if status == "failed":
                    wave_failed = True
                    failed_count += 1
                    workflow.logger.warning(
                        "Module returned failed status",
                        extra={
                            "audit_id": input.audit_id,
                            "wave_num": wave_num,
                            "module_name": name,
                            "status": status,
                        },
                    )
                else:
                    success_count += 1
                    workflow.logger.info(
                        "Module completed",
                        extra={
                            "audit_id": input.audit_id,
                            "wave_num": wave_num,
                            "module_name": name,
                            "status": status,
                        },
                    )

        wave_status = "failed" if wave_failed else "complete"
        workflow.logger.info(
            "Wave execution finished",
            extra={
                "audit_id": input.audit_id,
                "wave_num": wave_num,
                "wave_status": wave_status,
                "success_count": success_count,
                "failed_count": failed_count,
                "total_modules": len(modules),
            },
        )
        return wave_status

    async def _execute_factcheck_child(
        self,
        input: AuditInput,
        result: AuditResult,
    ) -> str:
        """Execute audit-factcheck as a Temporal child workflow."""
        workflow.logger.info(
            "Factcheck child workflow starting",
            extra={
                "audit_id": input.audit_id,
                "domain": input.domain,
                "child_workflow_id": f"factcheck-{input.audit_id}",
            },
        )
        try:
            child_result: dict[str, Any] = await workflow.execute_child_workflow(
                "FactcheckChildWorkflow",
                FactcheckChildInput(
                    audit_id=input.audit_id,
                    account_id=input.account_id,
                    domain=input.domain,
                    company_name=input.company_name,
                ),
                id=f"factcheck-{input.audit_id}",
                retry_policy=RetryPolicy(
                    maximum_attempts=2,
                    backoff_coefficient=2.0,
                ),
                execution_timeout=timedelta(minutes=30),
            )
            verdict = child_result.get("verdict", "WARN")
            result.factcheck_verdict = verdict
            result.module_results["audit-factcheck"] = child_result.get("status", "success")
            workflow.logger.info(
                "Factcheck child workflow completed",
                extra={
                    "audit_id": input.audit_id,
                    "verdict": verdict,
                    "status": child_result.get("status", "success"),
                },
            )
            return "complete"
        except Exception as exc:
            result.module_results["audit-factcheck"] = "failed"
            result.errors.append(f"audit-factcheck child workflow failed: {exc}")
            result.factcheck_verdict = "WARN"
            workflow.logger.error(
                "Factcheck child workflow failed",
                extra={
                    "audit_id": input.audit_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "fallback_verdict": "WARN",
                },
            )
            return "failed"

    async def _execute_fire_and_forget(
        self,
        input: AuditInput,
        modules: list[str],
        wave_num: int,
        result: AuditResult,
    ) -> str:
        """Execute modules as fire-and-forget (don't block audit completion)."""
        for name in modules:
            workflow.logger.info(
                "Fire-and-forget module starting",
                extra={
                    "audit_id": input.audit_id,
                    "wave_num": wave_num,
                    "module_name": name,
                },
            )
            try:
                workflow.start_activity(
                    "run_module",
                    RunModuleInput(
                        audit_id=input.audit_id,
                        account_id=input.account_id,
                        module_name=name,
                        domain=input.domain,
                        company_name=input.company_name,
                        ticker=input.ticker,
                        is_private=input.is_private,
                        wave=wave_num,
                    ),
                    start_to_close_timeout=timedelta(minutes=20),
                    retry_policy=RetryPolicy(
                        maximum_attempts=2,
                        backoff_coefficient=2.0,
                    ),
                )
                result.module_results[name] = "started"
                workflow.logger.info(
                    "Fire-and-forget module started successfully",
                    extra={
                        "audit_id": input.audit_id,
                        "module_name": name,
                    },
                )
            except Exception as exc:
                result.module_results[name] = "failed"
                result.errors.append(f"{name} fire-and-forget start failed: {exc}")
                workflow.logger.error(
                    "Fire-and-forget module failed to start",
                    extra={
                        "audit_id": input.audit_id,
                        "module_name": name,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )
        return "started"

    @staticmethod
    def _compute_overall_status(result: AuditResult) -> str:
        """Determine the overall audit status from module results."""
        statuses = set(result.module_results.values())

        workflow.logger.debug(
            "Computing overall audit status",
            extra={
                "audit_id": result.audit_id,
                "unique_statuses": list(statuses),
                "intel_company_status": result.module_results.get("intel-company"),
                "module_count": len(result.module_results),
            },
        )

        if not statuses:
            workflow.logger.warning(
                "No module results — overall status is failed",
                extra={"audit_id": result.audit_id},
            )
            return "failed"

        # If all succeeded or started (fire-and-forget)
        if statuses <= {"success", "partial", "started", "skipped"}:
            workflow.logger.info(
                "Overall status computed: complete",
                extra={"audit_id": result.audit_id, "statuses": list(statuses)},
            )
            return "complete"

        # If some failed but intel-company succeeded, it's partial
        if result.module_results.get("intel-company") in ("success", "partial"):
            workflow.logger.info(
                "Overall status computed: partial (some modules failed but intel-company ok)",
                extra={"audit_id": result.audit_id, "statuses": list(statuses)},
            )
            return "partial"

        workflow.logger.warning(
            "Overall status computed: failed",
            extra={"audit_id": result.audit_id, "statuses": list(statuses)},
        )
        return "failed"


# ---------------------------------------------------------------------------
# Factcheck child workflow
# ---------------------------------------------------------------------------


@dataclass
class FactcheckChildInput:
    """Input for the factcheck child workflow."""

    audit_id: str
    account_id: str
    domain: str
    company_name: str


@workflow.defn(name="FactcheckChildWorkflow")
class FactcheckChildWorkflow:
    """Factcheck runs as its own child workflow with separate retry policy.

    Executes the audit-factcheck module and returns the verdict.
    """

    @workflow.run
    async def run(self, input: FactcheckChildInput) -> dict[str, Any]:
        """Execute factcheck module as child workflow."""
        workflow.logger.info(
            "FactcheckChildWorkflow started",
            extra={
                "audit_id": input.audit_id,
                "domain": input.domain,
                "company_name": input.company_name,
            },
        )

        mod_result: dict[str, Any] = await workflow.execute_activity(
            "run_module",
            RunModuleInput(
                audit_id=input.audit_id,
                account_id=input.account_id,
                module_name="audit-factcheck",
                domain=input.domain,
                company_name=input.company_name,
                wave=5,
            ),
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                backoff_coefficient=2.0,
            ),
        )

        workflow.logger.info(
            "FactcheckChildWorkflow module execution complete",
            extra={
                "audit_id": input.audit_id,
                "module_status": mod_result.get("status", "unknown"),
            },
        )

        verdict = "WARN"
        output = mod_result.get("output", {})
        if isinstance(output, dict):
            verdict = output.get("verdict", "WARN")

        workflow.logger.info(
            "FactcheckChildWorkflow verdict extracted",
            extra={
                "audit_id": input.audit_id,
                "verdict": verdict,
                "status": mod_result.get("status", "failed"),
            },
        )

        workflow.logger.info(
            "FactcheckChildWorkflow complete",
            extra={
                "audit_id": input.audit_id,
                "verdict": verdict,
                "status": mod_result.get("status", "failed"),
            },
        )

        return {
            "status": mod_result.get("status", "failed"),
            "verdict": verdict,
            "audit_id": input.audit_id,
        }
