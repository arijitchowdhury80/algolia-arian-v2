"""Tests for the PRISM audit workflow — wave execution, gates, and audit modes.

These tests use Temporal's built-in test server (time-skipping mode).
Most tests mock the run_module activity to test workflow logic in isolation.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from prism_platform.core.registry import register_all_modules
from prism_platform.orchestrator.activities import run_module
from prism_platform.orchestrator.workflows import (
    ALL_WAVES,
    BULK_TRIAGE_MODULES,
    MODULE_WAVE_MAP,
    QUICK_MODULES,
    WAVE_1_INTEL,
    WAVE_2_BROWSER,
    WAVE_3_SYNTHESIS,
    WAVE_4_ACTIVATION,
    AuditInput,
    AuditResult,
    AuditWorkflow,
    FactcheckChildInput,
    FactcheckChildWorkflow,
    RunModuleInput,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _ensure_modules_registered() -> None:
    """Ensure all modules are registered before tests run."""
    register_all_modules()


def _make_success_result(module_name: str) -> dict[str, Any]:
    """Create a mock success result for a module."""
    return {
        "module_name": module_name,
        "module_version": "0.1.0",
        "status": "success",
        "output": {"domain": "test.com"},
        "sources": [],
        "duration_ms": 100,
        "llm_calls": 1,
        "llm_cost_usd": 0.01,
        "errors": [],
        "warnings": [],
    }


def _make_failed_result(module_name: str) -> dict[str, Any]:
    """Create a mock failed result for a module."""
    return {
        "module_name": module_name,
        "module_version": "0.1.0",
        "status": "failed",
        "output": {},
        "sources": [],
        "duration_ms": 50,
        "errors": [f"{module_name} failed"],
    }


# ---------------------------------------------------------------------------
# Shared test state for mock activities
# ---------------------------------------------------------------------------

# Module-level state that mock activities write to
_call_log: list[str] = []
_execution_order: list[tuple[int, str]] = []
_fail_modules: set[str] = set()


def _reset_mock_state(fail_modules: set[str] | None = None) -> None:
    """Reset mock activity state before each test."""
    _call_log.clear()
    _execution_order.clear()
    _fail_modules.clear()
    if fail_modules:
        _fail_modules.update(fail_modules)


@activity.defn(name="run_module")
async def mock_run_module(input: RunModuleInput) -> dict[str, Any]:
    """Mock activity that logs calls and returns success/failure based on config."""
    _call_log.append(input.module_name)
    _execution_order.append((input.wave, input.module_name))
    if input.module_name in _fail_modules:
        return _make_failed_result(input.module_name)
    if input.module_name == "audit-factcheck":
        return {
            "status": "success",
            "output": {"verdict": "PROCEED", "corrections": []},
            "sources": [],
            "duration_ms": 500,
        }
    return _make_success_result(input.module_name)


# ---------------------------------------------------------------------------
# Wave constants tests
# ---------------------------------------------------------------------------


class TestWaveDefinitions:
    """Verify wave constants are correct and consistent."""

    def test_wave_1_has_all_intel_modules(self) -> None:
        assert len(WAVE_1_INTEL) == 13
        assert all(m.startswith("intel-") for m in WAVE_1_INTEL)

    def test_wave_2_has_browser(self) -> None:
        assert WAVE_2_BROWSER == ["audit-browser"]

    def test_wave_3_has_synthesis(self) -> None:
        assert set(WAVE_3_SYNTHESIS) == {
            "synth-business-case",
            "synth-sales-plays",
            "audit-report",
        }

    def test_wave_4_has_campaign(self) -> None:
        assert WAVE_4_ACTIVATION == ["campaign-abx"]

    def test_all_waves_count(self) -> None:
        assert len(ALL_WAVES) == 6

    def test_module_wave_map_covers_all(self) -> None:
        all_modules: set[str] = set()
        for wave in ALL_WAVES:
            all_modules.update(wave)
        assert set(MODULE_WAVE_MAP.keys()) == all_modules

    def test_quick_modules(self) -> None:
        assert set(QUICK_MODULES) == {
            "intel-company",
            "intel-techstack",
            "intel-traffic",
        }

    def test_bulk_triage_modules(self) -> None:
        assert "audit-report" in BULK_TRIAGE_MODULES
        assert "intel-company" in BULK_TRIAGE_MODULES


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


class TestDataclasses:
    """Verify dataclass fields and defaults."""

    def test_audit_input_defaults(self) -> None:
        inp = AuditInput(
            audit_id="test",
            domain="test.com",
            company_name="Test Co",
        )
        assert inp.audit_mode == "full"
        assert inp.skip_modules == []
        assert inp.modules_to_run is None

    def test_audit_input_custom_mode(self) -> None:
        inp = AuditInput(
            audit_id="test",
            domain="test.com",
            company_name="Test Co",
            audit_mode="quick",
            skip_modules=["intel-news"],
        )
        assert inp.audit_mode == "quick"
        assert "intel-news" in inp.skip_modules

    def test_run_module_input_wave_field(self) -> None:
        rmi = RunModuleInput(
            audit_id="test",
            module_name="intel-company",
            domain="test.com",
            company_name="Test Co",
            wave=1,
        )
        assert rmi.wave == 1

    def test_run_module_input_default_wave(self) -> None:
        rmi = RunModuleInput(
            audit_id="test",
            module_name="intel-company",
            domain="test.com",
            company_name="Test Co",
        )
        assert rmi.wave == 0

    def test_audit_result_defaults(self) -> None:
        r = AuditResult(audit_id="test", status="complete")
        assert r.module_results == {}
        assert r.wave_results == {}
        assert r.factcheck_verdict is None
        assert r.errors == []

    def test_factcheck_child_input(self) -> None:
        fci = FactcheckChildInput(
            audit_id="test",
            domain="test.com",
            company_name="Test Co",
        )
        assert fci.audit_id == "test"


# ---------------------------------------------------------------------------
# Workflow integration tests (Temporal test server)
# ---------------------------------------------------------------------------


async def _run_workflow(
    audit_input: AuditInput,
    workflow_id: str,
    include_factcheck: bool = False,
) -> AuditResult:
    """Helper: spin up Temporal test env, register mock activity, run workflow."""
    workflows = [AuditWorkflow]
    if include_factcheck:
        workflows.append(FactcheckChildWorkflow)

    async with (
        await WorkflowEnvironment.start_time_skipping() as env,
        Worker(
            env.client,
            task_queue="test-queue",
            workflows=workflows,
            activities=[mock_run_module],
        ),
    ):
        return await env.client.execute_workflow(
            AuditWorkflow.run,
            audit_input,
            id=workflow_id,
            task_queue="test-queue",
        )


class TestAuditWorkflowQuickMode:
    """Quick mode should run only 3 intel modules."""

    async def test_quick_mode_runs_3_modules(self) -> None:
        """Quick mode: intel-company + intel-techstack + intel-traffic only."""
        _reset_mock_state()

        result = await _run_workflow(
            AuditInput(
                audit_id="q-001",
                domain="test.com",
                company_name="Test Co",
                audit_mode="quick",
            ),
            workflow_id="test-quick-001",
        )

        assert result.status == "complete"
        assert result.audit_mode == "quick"
        assert set(_call_log) == set(QUICK_MODULES)
        assert len(_call_log) == 3


class TestAuditWorkflowBulkTriageMode:
    """Bulk triage mode should run quick modules + audit-report."""

    async def test_bulk_triage_runs_quick_plus_report(self) -> None:
        _reset_mock_state()

        result = await _run_workflow(
            AuditInput(
                audit_id="bt-001",
                domain="test.com",
                company_name="Test Co",
                audit_mode="bulk_triage",
            ),
            workflow_id="test-bulk-001",
        )

        assert result.status == "complete"
        assert result.audit_mode == "bulk_triage"
        assert "audit-report" in _call_log
        assert "intel-company" in _call_log
        assert len(_call_log) == 4  # 3 quick + audit-report


class TestAuditWorkflowSkipModules:
    """skip_modules should exclude specified modules from execution."""

    async def test_skip_modules_excludes_from_wave(self) -> None:
        _reset_mock_state()

        result = await _run_workflow(
            AuditInput(
                audit_id="skip-001",
                domain="test.com",
                company_name="Test Co",
                audit_mode="quick",
                skip_modules=["intel-traffic"],
            ),
            workflow_id="test-skip-001",
        )

        assert result.status == "complete"
        assert "intel-traffic" not in _call_log
        assert "intel-company" in _call_log
        assert "intel-techstack" in _call_log


class TestAuditWorkflowIntelCompanyGate:
    """intel-company failure must abort the entire audit."""

    async def test_intel_company_failure_aborts_audit(self) -> None:
        _reset_mock_state(fail_modules={"intel-company"})

        result = await _run_workflow(
            AuditInput(
                audit_id="abort-001",
                domain="test.com",
                company_name="Test Co",
                audit_mode="full",
            ),
            workflow_id="test-abort-001",
            include_factcheck=True,
        )

        assert result.status == "aborted"
        assert "intel-company" in result.module_results
        assert result.module_results["intel-company"] == "failed"
        assert any("intel-company" in e for e in result.errors)
        # Should NOT have run Wave 2+
        assert "audit-browser" not in result.module_results


class TestAuditWorkflowDegradedMode:
    """Other intel module failures are non-fatal — audit continues."""

    async def test_other_intel_failure_continues(self) -> None:
        _reset_mock_state(fail_modules={"intel-news"})

        result = await _run_workflow(
            AuditInput(
                audit_id="degrade-001",
                domain="test.com",
                company_name="Test Co",
                audit_mode="full",
            ),
            workflow_id="test-degrade-001",
            include_factcheck=True,
        )

        # intel-news failed but audit continued
        assert result.module_results["intel-news"] == "failed"
        assert result.module_results["intel-company"] == "success"
        # Should have proceeded to Wave 2+
        assert result.status in ("partial", "complete")
        assert "audit-browser" in result.module_results


class TestAuditWorkflowWaveOrder:
    """Verify waves execute in correct sequential order."""

    async def test_wave_execution_order(self) -> None:
        """Modules from later waves should not start before earlier waves complete."""
        _reset_mock_state()

        result = await _run_workflow(
            AuditInput(
                audit_id="order-001",
                domain="test.com",
                company_name="Test Co",
                audit_mode="full",
            ),
            workflow_id="test-order-001",
            include_factcheck=True,
        )

        assert result.status in ("complete", "partial")

        # Verify waves are monotonically non-decreasing
        wave_order = [w for w, _ in _execution_order]
        seen_waves: list[int] = []
        for w in wave_order:
            if not seen_waves or w != seen_waves[-1]:
                seen_waves.append(w)

        for i in range(len(seen_waves) - 1):
            assert seen_waves[i] <= seen_waves[i + 1], (
                f"Wave {seen_waves[i + 1]} executed before wave {seen_waves[i]} finished"
            )


class TestFactcheckChildWorkflow:
    """Tests for the factcheck child workflow."""

    async def test_factcheck_child_returns_verdict(self) -> None:
        _reset_mock_state()

        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with Worker(
                env.client,
                task_queue="test-queue",
                workflows=[FactcheckChildWorkflow],
                activities=[mock_run_module],
            ):
                result = await env.client.execute_workflow(
                    FactcheckChildWorkflow.run,
                    FactcheckChildInput(
                        audit_id="fc-001",
                        domain="test.com",
                        company_name="Test Co",
                    ),
                    id="test-fc-001",
                    task_queue="test-queue",
                )

            assert result["verdict"] == "PROCEED"
            assert result["status"] == "success"


class TestFullWorkflowIntegration:
    """Full workflow with all waves — requires real modules."""

    builtwith_key_present = bool(os.environ.get("BUILTWITH_API_KEY"))

    @pytest.mark.skipif(
        not builtwith_key_present,
        reason="BUILTWITH_API_KEY not set — cannot run real API tests",
    )
    async def test_full_workflow_with_real_techstack(self) -> None:
        """Subset: Run intel-techstack via quick mode with real API."""
        async with (
            await WorkflowEnvironment.start_time_skipping() as env,
            Worker(
                env.client,
                task_queue="test-queue",
                workflows=[AuditWorkflow],
                activities=[run_module],
            ),
        ):
            result = await env.client.execute_workflow(
                AuditWorkflow.run,
                AuditInput(
                    audit_id="real-001",
                    domain="dell.com",
                    company_name="Dell Technologies",
                    audit_mode="quick",
                    skip_modules=["intel-company", "intel-traffic"],
                ),
                id="test-real-001",
                task_queue="test-queue",
            )

            assert result.module_results.get("intel-techstack") in (
                "success",
                "partial",
            )
