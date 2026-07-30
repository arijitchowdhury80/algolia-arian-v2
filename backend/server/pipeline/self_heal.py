"""Deterministic, scripted self-heal loop for the PRISM audit pipeline.

Today the BLOCKED -> fix -> re-run cycle on `factcheck_mechanical.py` is
emergent LLM behaviour inside one long `claude -p` session — there is no
scripted retry anywhere (see docs/plans/2026-07-02-cassandra-airtight-pipeline-goal.md
§1.3, "The self-heal loop DOES NOT EXIST IN CODE"). This module is that
scripted loop: dispatch a phase, run a deterministic quality gate, and on
BLOCKED re-dispatch automatically up to a safety cap before escalating to a
human. Pure stdlib, fully dependency-injected (dispatch/gate/clock), so it is
deterministic and unit-testable without touching the VPS.

NOT wired into the live runner yet — integration is gated (see
server/pipeline/__init__.py).
"""

from __future__ import annotations

import contextlib
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum


class GateStatus(Enum):
    """Outcome of a deterministic quality-gate run for one phase attempt."""

    CLEAN = "clean"
    BLOCKED = "blocked"
    ERROR = "error"


@dataclass(frozen=True)
class GateResult:
    """Result of running the quality gate once.

    `fatal` (patch #3): set True when the gate has determined the failure is
    UNFIXABLE by retrying the same phase/skill (e.g. data genuinely absent or
    contradicted by source) -- retrying is not merely wasteful but actively
    misleading, so the loop must escalate to NEEDS_HUMAN on the first fatal
    result rather than burning the remaining max_passes attempts. Defaults to
    False so every pre-existing call site (and all 20 original tests) is
    unaffected.
    """

    status: GateStatus
    findings: tuple[str, ...] = ()
    raw: str = ""
    fatal: bool = False


@dataclass(frozen=True)
class Attempt:
    """One dispatch+gate cycle within a phase's self-heal loop."""

    phase: str
    attempt_number: int
    dispatch_ok: bool
    gate: GateResult | None
    started_at: float
    finished_at: float


class PhaseOutcome(Enum):
    """Terminal state of a phase after the self-heal loop finishes."""

    CLEAN = "clean"
    NEEDS_HUMAN = "needs_human"


@dataclass(frozen=True)
class PhaseReport:
    """Full record of a phase's self-heal run, for logging and escalation."""

    phase: str
    outcome: PhaseOutcome
    attempts: tuple[Attempt, ...]
    escalation_reason: str | None = None


DispatchFn = Callable[[str, int], bool]
GateFn = Callable[[str], GateResult]
ObserverFn = Callable[[Attempt], None]
ClockFn = Callable[[], float]


class SelfHealLoop:
    """Scripted dispatch -> gate -> retry-until-clean loop, capped for safety.

    `dispatch(phase, attempt_number) -> bool` re-runs the given phase and
    reports whether the dispatch itself succeeded. `gate(phase) -> GateResult`
    runs the deterministic quality gate (e.g. factcheck_mechanical.py) against
    the phase's current output. Neither callable is invoked with real
    concurrency or sleeping — this loop is synchronous and deterministic.
    """

    def __init__(
        self,
        dispatch: DispatchFn,
        gate: GateFn,
        max_passes: int = 4,
        clock: ClockFn = time.monotonic,
        on_attempt: ObserverFn | None = None,
    ) -> None:
        if max_passes < 1:
            raise ValueError(f"max_passes must be >= 1, got {max_passes}")
        self._dispatch = dispatch
        self._gate = gate
        self._max_passes = max_passes
        self._clock = clock
        self._on_attempt = on_attempt

    def run_phase(self, phase: str) -> PhaseReport:
        """Run one phase until the gate reports CLEAN or max_passes is exhausted."""
        attempts: list[Attempt] = []

        for attempt_number in range(1, self._max_passes + 1):
            started_at = self._clock()
            dispatch_ok = self._dispatch(phase, attempt_number)

            gate_result: GateResult | None = None
            if dispatch_ok:
                gate_result = self._gate(phase)

            finished_at = self._clock()
            attempt = Attempt(
                phase=phase,
                attempt_number=attempt_number,
                dispatch_ok=dispatch_ok,
                gate=gate_result,
                started_at=started_at,
                finished_at=finished_at,
            )
            attempts.append(attempt)
            self._notify(attempt)

            if dispatch_ok and gate_result is not None and gate_result.status == GateStatus.CLEAN:
                return PhaseReport(
                    phase=phase, outcome=PhaseOutcome.CLEAN, attempts=tuple(attempts)
                )

            if gate_result is not None and gate_result.fatal:
                return PhaseReport(
                    phase=phase,
                    outcome=PhaseOutcome.NEEDS_HUMAN,
                    attempts=tuple(attempts),
                    escalation_reason=self._escalation_reason(attempts[-1]),
                )

        return PhaseReport(
            phase=phase,
            outcome=PhaseOutcome.NEEDS_HUMAN,
            attempts=tuple(attempts),
            escalation_reason=self._escalation_reason(attempts[-1]),
        )

    def run_pipeline(self, phases: Sequence[str]) -> tuple[PhaseReport, ...]:
        """Run phases in order; stop at the first NEEDS_HUMAN so a broken phase
        never feeds garbage downstream. Later phases are simply never attempted."""
        reports: list[PhaseReport] = []
        for phase in phases:
            report = self.run_phase(phase)
            reports.append(report)
            if report.outcome == PhaseOutcome.NEEDS_HUMAN:
                break
        return tuple(reports)

    def _notify(self, attempt: Attempt) -> None:
        if self._on_attempt is None:
            return
        # The loop's correctness never depends on the observer.
        with contextlib.suppress(Exception):
            self._on_attempt(attempt)

    @staticmethod
    def _escalation_reason(last: Attempt) -> str:
        if not last.dispatch_ok:
            return f"dispatch failed on attempt {last.attempt_number}"
        if last.gate is None:
            return f"no gate result recorded on attempt {last.attempt_number}"
        findings = "; ".join(last.gate.findings) or last.gate.raw
        if last.gate.fatal:
            return (
                f"gate FATAL (unfixable) after {last.attempt_number} attempts: {findings}"
            ).strip()
        if last.gate.status == GateStatus.ERROR:
            return f"gate ERROR after {last.attempt_number} attempts: {findings}".strip()
        return f"gate BLOCKED after {last.attempt_number} attempts: {findings}".strip()


def subprocess_gate(cmd: Sequence[str]) -> GateFn:
    """Adapter: build a GateFn that runs a real command (e.g.
    factcheck_mechanical.py) via subprocess and maps its exit code to a
    GateStatus. Exit 0 -> CLEAN, exit 2 -> BLOCKED (stdout lines as findings),
    anything else -> ERROR (fail-closed, never CLEAN).
    """

    def _gate(phase: str) -> GateResult:
        try:
            result = subprocess.run(list(cmd), capture_output=True, text=True, check=False)
        except OSError as exc:
            return GateResult(status=GateStatus.ERROR, findings=(str(exc),), raw=str(exc))

        raw = (result.stdout or "") + (result.stderr or "")
        if result.returncode == 0:
            return GateResult(status=GateStatus.CLEAN, raw=raw)
        if result.returncode == 2:
            findings = tuple(line for line in result.stdout.splitlines() if line.strip())
            return GateResult(status=GateStatus.BLOCKED, findings=findings, raw=raw)
        return GateResult(status=GateStatus.ERROR, raw=raw)

    return _gate
