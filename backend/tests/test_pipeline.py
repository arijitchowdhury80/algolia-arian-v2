"""Tests for the Temporal-free in-process audit sequencer (pipeline.py).

Pure-logic tests — no DB, no network, no Temporal worker. The module runner is
injected so we exercise wave ordering, the intel-company abort gate, skip
handling, and status computation without executing real modules.
"""

from __future__ import annotations

import pytest

from server.orchestrator.pipeline import (
    compute_overall_status,
    resolve_waves,
    run_pipeline,
)
from server.orchestrator.workflows import (
    QUICK_MODULES,
    RunModuleInput,
)


def _input(mode: str = "full", **kw):
    from server.orchestrator.workflows import AuditInput

    return AuditInput(
        audit_id="aud-1",
        account_id="acc-1",
        domain="example.com",
        company_name="Example",
        audit_mode=mode,
        **kw,
    )


# ---------------------------------------------------------------------------
# resolve_waves
# ---------------------------------------------------------------------------


def test_resolve_waves_full_runs_all_six_waves_in_order():
    waves = resolve_waves(_input("full"))
    wave_nums = [wn for wn, _ in waves]
    # 1A/1B/1C all wave 1, then 2..6 — monotonic non-decreasing
    assert wave_nums == sorted(wave_nums)
    assert wave_nums[0] == 1 and wave_nums[-1] == 6
    # First sub-wave is the intel-company seed alone
    assert waves[0] == (1, ["intel-company"])
    # Every wave 1..6 represented
    assert set(wave_nums) == {1, 2, 3, 4, 5, 6}


def test_resolve_waves_quick_is_single_wave():
    waves = resolve_waves(_input("quick"))
    assert waves == [(1, QUICK_MODULES)]


def test_resolve_waves_bulk_triage_quick_plus_report():
    waves = resolve_waves(_input("bulk_triage"))
    assert waves == [(1, QUICK_MODULES), (6, ["audit-report"])]


def test_resolve_waves_refresh_includes_requested_and_downstream_sorted():
    waves = resolve_waves(_input("refresh", refresh_modules=["intel-traffic", "audit-browser"]))
    wave_nums = [wn for wn, _ in waves]
    assert wave_nums == sorted(wave_nums)
    # requested wave-1 module present in a wave-1 entry
    wave1_mods = [m for wn, mods in waves if wn == 1 for m in mods]
    assert "intel-traffic" in wave1_mods
    # browser requested → wave 2 present
    assert 2 in wave_nums
    # downstream always re-run
    assert {3, 4, 5, 6} <= set(wave_nums)


# ---------------------------------------------------------------------------
# compute_overall_status
# ---------------------------------------------------------------------------


def test_status_empty_is_failed():
    assert compute_overall_status({}) == "failed"


def test_status_all_success_is_complete():
    got = compute_overall_status({"intel-company": "success", "intel-traffic": "success"})
    assert got == "complete"


def test_status_partial_when_some_fail_but_company_ok():
    got = compute_overall_status({"intel-company": "success", "intel-traffic": "failed"})
    assert got == "partial"


def test_status_failed_when_company_failed():
    got = compute_overall_status({"intel-company": "failed", "intel-traffic": "success"})
    assert got == "failed"


# ---------------------------------------------------------------------------
# run_pipeline (injected runner — no real modules)
# ---------------------------------------------------------------------------


def _runner_factory(status_by_module=None, record=None):
    status_by_module = status_by_module or {}

    async def runner(inp: RunModuleInput) -> dict:
        if record is not None:
            record.append((inp.wave, inp.module_name))
        return {
            "status": status_by_module.get(inp.module_name, "success"),
            "module_name": inp.module_name,
        }

    return runner


@pytest.mark.asyncio
async def test_run_pipeline_quick_all_success_is_complete():
    record: list = []
    result = await run_pipeline(_input("quick"), runner=_runner_factory(record=record))
    assert result.status == "complete"
    assert {m for _, m in record} == set(QUICK_MODULES)
    assert all(s == "success" for s in result.module_results.values())


@pytest.mark.asyncio
async def test_run_pipeline_intel_company_failure_aborts_before_downstream():
    record: list = []
    runner = _runner_factory(status_by_module={"intel-company": "failed"}, record=record)
    result = await run_pipeline(_input("full"), runner=runner)
    assert result.status == "aborted"
    # No wave > 1 module ever ran
    assert all(wave == 1 for wave, _ in record)
    # intel-company recorded as failed
    assert result.module_results.get("intel-company") == "failed"


@pytest.mark.asyncio
async def test_run_pipeline_skip_modules_filtered_out():
    record: list = []
    runner = _runner_factory(record=record)
    await run_pipeline(_input("quick", skip_modules=["intel-traffic"]), runner=runner)
    ran = {m for _, m in record}
    assert "intel-traffic" not in ran
    assert "intel-company" in ran


@pytest.mark.asyncio
async def test_run_pipeline_wave_with_all_modules_skipped_marked_skipped():
    runner = _runner_factory()
    result = await run_pipeline(
        _input("bulk_triage", skip_modules=["audit-report"]), runner=runner
    )
    # wave 6 had only audit-report which was skipped
    assert result.wave_results.get(6) == "skipped"


@pytest.mark.asyncio
async def test_run_pipeline_records_each_module_status():
    runner = _runner_factory(status_by_module={"intel-traffic": "failed"})
    result = await run_pipeline(_input("quick"), runner=runner)
    assert result.module_results["intel-traffic"] == "failed"
    assert result.module_results["intel-company"] == "success"
    # one failure among quick modules, company ok → partial
    assert result.status == "partial"
