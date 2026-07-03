"""Tests for the deterministic scripted self-heal loop.

See prism_platform/pipeline/self_heal.py and
docs/plans/2026-07-02-cassandra-airtight-pipeline-goal.md §1.3 for design intent.
"""

from __future__ import annotations

import sys
from collections.abc import Callable

import pytest

from prism_platform.pipeline.self_heal import (
    Attempt,
    GateResult,
    GateStatus,
    PhaseOutcome,
    SelfHealLoop,
    subprocess_gate,
)


def make_clock() -> Callable[[], float]:
    """Deterministic fake clock — increments by 1.0 on every call, no real time."""
    counter = {"t": 0.0}

    def _clock() -> float:
        counter["t"] += 1.0
        return counter["t"]

    return _clock


def scripted_gate(results: list[GateResult]) -> Callable[[str], GateResult]:
    """Returns a gate callable that yields `results` in order, then repeats the last."""
    calls: list[str] = []

    def _gate(phase: str) -> GateResult:
        calls.append(phase)
        idx = min(len(calls) - 1, len(results) - 1)
        return results[idx]

    _gate.calls = calls  # type: ignore[attr-defined]
    return _gate


def always_dispatch_ok(phase: str, attempt_number: int) -> bool:
    return True


class TestRunPhaseCleanFirstTry:
    def test_clean_on_first_attempt_returns_clean_outcome_with_one_attempt(self) -> None:
        gate = scripted_gate([GateResult(status=GateStatus.CLEAN)])
        loop = SelfHealLoop(dispatch=always_dispatch_ok, gate=gate, clock=make_clock())

        report = loop.run_phase("research")

        assert report.outcome == PhaseOutcome.CLEAN
        assert len(report.attempts) == 1
        assert report.attempts[0].attempt_number == 1
        assert report.attempts[0].gate is not None
        assert report.attempts[0].gate.status == GateStatus.CLEAN
        assert report.escalation_reason is None


class TestRunPhaseBlockedThenClean:
    def test_blocked_twice_then_clean_takes_three_attempts_and_recovers(self) -> None:
        gate = scripted_gate(
            [
                GateResult(status=GateStatus.BLOCKED, findings=("missing field A",)),
                GateResult(status=GateStatus.BLOCKED, findings=("missing field B",)),
                GateResult(status=GateStatus.CLEAN),
            ]
        )
        loop = SelfHealLoop(dispatch=always_dispatch_ok, gate=gate, clock=make_clock())

        report = loop.run_phase("browser")

        assert report.outcome == PhaseOutcome.CLEAN
        assert len(report.attempts) == 3
        assert [a.attempt_number for a in report.attempts] == [1, 2, 3]
        assert report.attempts[0].gate.status == GateStatus.BLOCKED
        assert report.attempts[1].gate.status == GateStatus.BLOCKED
        assert report.attempts[2].gate.status == GateStatus.CLEAN


class TestRunPhaseAlwaysBlocked:
    def test_always_blocked_exhausts_max_passes_and_escalates(self) -> None:
        gate = scripted_gate([GateResult(status=GateStatus.BLOCKED, findings=("perpetual issue",))])
        loop = SelfHealLoop(
            dispatch=always_dispatch_ok, gate=gate, max_passes=4, clock=make_clock()
        )

        report = loop.run_phase("report")

        assert report.outcome == PhaseOutcome.NEEDS_HUMAN
        assert len(report.attempts) == 4
        assert report.escalation_reason is not None
        assert "perpetual issue" in report.escalation_reason

    def test_max_passes_of_one_means_single_attempt_before_escalation(self) -> None:
        gate = scripted_gate([GateResult(status=GateStatus.BLOCKED, findings=("x",))])
        loop = SelfHealLoop(
            dispatch=always_dispatch_ok, gate=gate, max_passes=1, clock=make_clock()
        )

        report = loop.run_phase("report")

        assert report.outcome == PhaseOutcome.NEEDS_HUMAN
        assert len(report.attempts) == 1


class TestGateErrorFailsClosed:
    def test_gate_error_is_never_treated_as_clean(self) -> None:
        gate = scripted_gate(
            [GateResult(status=GateStatus.ERROR, raw="factcheck crashed: traceback...")]
        )
        loop = SelfHealLoop(
            dispatch=always_dispatch_ok, gate=gate, max_passes=3, clock=make_clock()
        )

        report = loop.run_phase("factcheck")

        assert report.outcome == PhaseOutcome.NEEDS_HUMAN
        assert len(report.attempts) == 3
        assert all(
            a.gate is not None and a.gate.status == GateStatus.ERROR for a in report.attempts
        )

    def test_gate_error_then_clean_recovers(self) -> None:
        gate = scripted_gate(
            [
                GateResult(status=GateStatus.ERROR, raw="transient crash"),
                GateResult(status=GateStatus.CLEAN),
            ]
        )
        loop = SelfHealLoop(dispatch=always_dispatch_ok, gate=gate, clock=make_clock())

        report = loop.run_phase("factcheck")

        assert report.outcome == PhaseOutcome.CLEAN
        assert len(report.attempts) == 2


class TestDispatchFailure:
    def test_dispatch_failure_records_attempt_without_running_gate(self) -> None:
        gate_calls: list[str] = []

        def failing_dispatch(phase: str, attempt_number: int) -> bool:
            return False

        def counting_gate(phase: str) -> GateResult:
            gate_calls.append(phase)
            return GateResult(status=GateStatus.CLEAN)

        loop = SelfHealLoop(
            dispatch=failing_dispatch, gate=counting_gate, max_passes=2, clock=make_clock()
        )

        report = loop.run_phase("research")

        assert report.outcome == PhaseOutcome.NEEDS_HUMAN
        assert gate_calls == []  # gate never invoked when dispatch fails
        assert all(a.dispatch_ok is False and a.gate is None for a in report.attempts)
        assert report.escalation_reason is not None
        assert "dispatch" in report.escalation_reason.lower()

    def test_dispatch_failure_then_success_recovers(self) -> None:
        attempt_counter = {"n": 0}

        def flaky_dispatch(phase: str, attempt_number: int) -> bool:
            attempt_counter["n"] += 1
            return attempt_counter["n"] > 1

        gate = scripted_gate([GateResult(status=GateStatus.CLEAN)])
        loop = SelfHealLoop(dispatch=flaky_dispatch, gate=gate, clock=make_clock())

        report = loop.run_phase("research")

        assert report.outcome == PhaseOutcome.CLEAN
        assert len(report.attempts) == 2
        assert report.attempts[0].dispatch_ok is False
        assert report.attempts[0].gate is None
        assert report.attempts[1].dispatch_ok is True
        assert report.attempts[1].gate is not None


class TestObserver:
    def test_observer_receives_every_attempt_in_order(self) -> None:
        received: list[Attempt] = []
        gate = scripted_gate(
            [
                GateResult(status=GateStatus.BLOCKED, findings=("a",)),
                GateResult(status=GateStatus.CLEAN),
            ]
        )
        loop = SelfHealLoop(
            dispatch=always_dispatch_ok,
            gate=gate,
            clock=make_clock(),
            on_attempt=received.append,
        )

        loop.run_phase("research")

        assert len(received) == 2
        assert [a.attempt_number for a in received] == [1, 2]
        assert received[0].gate.status == GateStatus.BLOCKED
        assert received[1].gate.status == GateStatus.CLEAN

    def test_observer_exception_does_not_break_the_loop(self) -> None:
        def raising_observer(attempt: Attempt) -> None:
            raise RuntimeError("observer boom")

        gate = scripted_gate([GateResult(status=GateStatus.CLEAN)])
        loop = SelfHealLoop(
            dispatch=always_dispatch_ok,
            gate=gate,
            clock=make_clock(),
            on_attempt=raising_observer,
        )

        report = loop.run_phase("research")

        assert report.outcome == PhaseOutcome.CLEAN
        assert len(report.attempts) == 1


class TestRunPipeline:
    def test_pipeline_runs_all_phases_when_all_clean(self) -> None:
        gate = scripted_gate([GateResult(status=GateStatus.CLEAN)])
        loop = SelfHealLoop(dispatch=always_dispatch_ok, gate=gate, clock=make_clock())

        reports = loop.run_pipeline(["research", "browser", "report"])

        assert [r.phase for r in reports] == ["research", "browser", "report"]
        assert all(r.outcome == PhaseOutcome.CLEAN for r in reports)

    def test_pipeline_stops_at_first_needs_human_phase(self) -> None:
        # "browser" always blocks; downstream phases must never be attempted.
        def gate(phase: str) -> GateResult:
            if phase == "browser":
                return GateResult(status=GateStatus.BLOCKED, findings=("broken",))
            return GateResult(status=GateStatus.CLEAN)

        dispatched_phases: list[str] = []

        def dispatch(phase: str, attempt_number: int) -> bool:
            dispatched_phases.append(phase)
            return True

        loop = SelfHealLoop(dispatch=dispatch, gate=gate, max_passes=2, clock=make_clock())

        reports = loop.run_pipeline(["research", "browser", "report", "factcheck"])

        assert [r.phase for r in reports] == ["research", "browser"]
        assert reports[0].outcome == PhaseOutcome.CLEAN
        assert reports[1].outcome == PhaseOutcome.NEEDS_HUMAN
        assert "report" not in dispatched_phases
        assert "factcheck" not in dispatched_phases


class TestMaxPassesValidation:
    def test_zero_max_passes_raises_value_error(self) -> None:
        gate = scripted_gate([GateResult(status=GateStatus.CLEAN)])
        with pytest.raises(ValueError):
            SelfHealLoop(dispatch=always_dispatch_ok, gate=gate, max_passes=0)

    def test_negative_max_passes_raises_value_error(self) -> None:
        gate = scripted_gate([GateResult(status=GateStatus.CLEAN)])
        with pytest.raises(ValueError):
            SelfHealLoop(dispatch=always_dispatch_ok, gate=gate, max_passes=-1)


class TestDeterminism:
    def test_clock_is_injected_never_wall_clock(self) -> None:
        clock = make_clock()
        gate = scripted_gate([GateResult(status=GateStatus.CLEAN)])
        loop = SelfHealLoop(dispatch=always_dispatch_ok, gate=gate, clock=clock)

        report = loop.run_phase("research")

        # Our fake clock increments by exactly 1.0 per call; two calls per attempt
        # (started_at, finished_at) means deterministic, predictable values.
        assert report.attempts[0].started_at == 1.0
        assert report.attempts[0].finished_at == 2.0

    def test_attempt_numbers_are_one_based_and_sequential(self) -> None:
        gate = scripted_gate(
            [
                GateResult(status=GateStatus.BLOCKED, findings=("x",)),
                GateResult(status=GateStatus.BLOCKED, findings=("x",)),
                GateResult(status=GateStatus.CLEAN),
            ]
        )
        loop = SelfHealLoop(dispatch=always_dispatch_ok, gate=gate, clock=make_clock())

        report = loop.run_phase("research")

        assert [a.attempt_number for a in report.attempts] == [1, 2, 3]


class TestSubprocessGate:
    def test_exit_code_zero_maps_to_clean(self) -> None:
        gate = subprocess_gate([sys.executable, "-c", "import sys; sys.exit(0)"])

        result = gate("research")

        assert result.status == GateStatus.CLEAN

    def test_exit_code_two_maps_to_blocked_with_stdout_findings(self) -> None:
        script = (
            "import sys; "
            "print('finding: missing traffic data'); "
            "print('finding: dead citation link'); "
            "sys.exit(2)"
        )
        gate = subprocess_gate([sys.executable, "-c", script])

        result = gate("research")

        assert result.status == GateStatus.BLOCKED
        assert "finding: missing traffic data" in result.findings
        assert "finding: dead citation link" in result.findings

    def test_other_exit_code_maps_to_error(self) -> None:
        gate = subprocess_gate([sys.executable, "-c", "import sys; sys.exit(1)"])

        result = gate("research")

        assert result.status == GateStatus.ERROR

    def test_subprocess_gate_integrates_with_self_heal_loop_end_to_end(self) -> None:
        # A "gate" that blocks on attempt 1, then a *different* fixed command would be
        # needed to simulate recovery — subprocess_gate wraps a fixed cmd, so here we
        # just prove wiring: a fixed always-clean command drives the loop to CLEAN.
        gate = subprocess_gate([sys.executable, "-c", "import sys; sys.exit(0)"])
        loop = SelfHealLoop(dispatch=always_dispatch_ok, gate=gate, clock=make_clock())

        report = loop.run_phase("factcheck")

        assert report.outcome == PhaseOutcome.CLEAN
