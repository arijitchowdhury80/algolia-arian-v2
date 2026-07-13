"""Tests for prism_platform/pipeline/executioner.py (Task 4a — Track C.1).

Dependency-injected throughout: no real subprocess, no real VPS, no real
LLM call, no real DB. `make_dispatch_fn`'s default `build_cmd_fn` (the real
staged prism-runner.py's `build_audit_cmd`) is exercised in one dedicated
test to prove real reuse per the dispatch brief; every other test injects a
fake to stay fast and hermetic.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from prism_platform.pipeline import executioner, self_heal
from prism_platform.pipeline import gate as gate_module
from prism_platform.pipeline.verdicts import (
    AdversarialVerdict,
    AdversarialVoterVerdict,
    FactCheckVerdict,
    QualityScore,
)

# ---------------------------------------------------------------- make_dispatch_fn


def test_make_dispatch_fn_forces_skill_and_returns_true_on_exit_zero():
    seen_jobs = []

    def fake_build_cmd(job):
        seen_jobs.append(job)
        return ["echo", job["skill"]]

    dispatch = executioner.make_dispatch_fn(
        "dell.com", build_cmd_fn=fake_build_cmd, run_cmd_fn=lambda cmd: 0
    )
    ok = dispatch("algolia-intel-traffic", 1)
    assert ok is True
    assert seen_jobs == [{"domain": "dell.com", "skill": "algolia-intel-traffic"}]


def test_make_dispatch_fn_returns_false_on_nonzero_exit():
    dispatch = executioner.make_dispatch_fn(
        "dell.com", build_cmd_fn=lambda job: ["false"], run_cmd_fn=lambda cmd: 1
    )
    assert dispatch("algolia-intel-traffic", 1) is False


def test_make_dispatch_fn_never_threads_phase_or_skip():
    """A per-skill dispatch is never a phase/skip run -- only domain+skill."""
    captured = {}

    def fake_build_cmd(job):
        captured.update(job)
        return ["noop"]

    dispatch = executioner.make_dispatch_fn(
        "belk.com", build_cmd_fn=fake_build_cmd, run_cmd_fn=lambda cmd: 0
    )
    dispatch("algolia-intel-hiring", 3)
    assert "phase" not in captured
    assert "skip" not in captured
    assert captured == {"domain": "belk.com", "skill": "algolia-intel-hiring"}


def test_make_dispatch_fn_default_run_cmd_fn_uses_real_subprocess():
    """No run_cmd_fn injected -> falls back to a real subprocess.run call."""
    dispatch = executioner.make_dispatch_fn(
        "dell.com", build_cmd_fn=lambda job: [sys.executable, "-c", "import sys; sys.exit(0)"]
    )
    assert dispatch("algolia-intel-company", 1) is True

    dispatch_fail = executioner.make_dispatch_fn(
        "dell.com", build_cmd_fn=lambda job: [sys.executable, "-c", "import sys; sys.exit(1)"]
    )
    assert dispatch_fail("algolia-intel-company", 1) is False


def test_make_dispatch_fn_default_build_cmd_fn_reuses_real_build_audit_cmd():
    """Proves the DEFAULT build_cmd_fn is the real staged prism-runner.py's
    build_audit_cmd (per the brief: "reuse build_audit_cmd, don't duplicate
    its argv-building logic") -- run_cmd_fn is faked so no real subprocess
    runs, but the argv actually comes from the real function."""
    captured_cmds = []

    def fake_run_cmd(cmd):
        captured_cmds.append(list(cmd))
        return 0

    dispatch = executioner.make_dispatch_fn("dell.com", run_cmd_fn=fake_run_cmd)
    ok = dispatch("algolia-intel-traffic", 1)
    assert ok is True
    assert len(captured_cmds) == 1
    cmd = captured_cmds[0]
    # Real build_audit_cmd shape: bash <run-audit.sh> <domain> --skill <skill>
    # (no sudo -u: the runner process itself runs as the unprivileged
    # chowmesuser service account, not root, so no privilege-drop step is needed)
    assert cmd[0] == "bash"
    assert "dell.com" in cmd
    assert "--skill" in cmd
    assert "algolia-intel-traffic" in cmd
    assert "--phase" not in cmd
    assert "--skip" not in cmd


# ---------------------------------------------------------------- make_gate_fn


def _passing_factcheck_fn(skill_output):
    return (
        FactCheckVerdict(
            claim="claim A",
            evidence_tier="AUTHENTIC",
            verdict="SUPPORTED",
            citation="https://example.com",
            reasoning="matches source",
        ),
    )


def _passing_quality_fn(skill_output):
    return QualityScore(
        dimension="instruction_adherence",
        score=9.0,
        passing_checks=9,
        total_checks=10,
        reasoning="mostly good",
    )


def _exit0_mechanical_cmd_fn(skill_output):
    return [sys.executable, "-c", "import sys; sys.exit(0)"]


def _exit2_mechanical_cmd_fn(skill_output):
    return [sys.executable, "-c", "print('bad field'); import sys; sys.exit(2)"]


def test_make_gate_fn_maps_pass_verdict_to_clean_not_fatal(tmp_path: Path):
    gate_fn = executioner.make_gate_fn(
        "dell.com",
        "Dell",
        tmp_path,
        mechanical_cmd_fn=_exit0_mechanical_cmd_fn,
        factcheck_fn=_passing_factcheck_fn,
        quality_fn=_passing_quality_fn,
    )
    result = gate_fn("algolia-intel-traffic")
    assert result.status == self_heal.GateStatus.CLEAN
    assert result.fatal is False


def test_make_gate_fn_maps_mechanical_block_to_blocked_not_fatal(tmp_path: Path):
    """Stage 1 (mechanical) BLOCK is always RETRY_WORTHY -> fatal=False."""
    gate_fn = executioner.make_gate_fn(
        "dell.com",
        "Dell",
        tmp_path,
        mechanical_cmd_fn=_exit2_mechanical_cmd_fn,
        factcheck_fn=_passing_factcheck_fn,
        quality_fn=_passing_quality_fn,
    )
    result = gate_fn("algolia-intel-traffic")
    assert result.status == self_heal.GateStatus.BLOCKED
    assert result.fatal is False
    assert result.findings


def test_make_gate_fn_maps_factcheck_contradicted_to_blocked_and_fatal(tmp_path: Path):
    """Stage 2 CONTRADICTED/UNSUPPORTED is UNFIXABLE -> fatal=True (patch #3:
    the self-heal loop must escalate immediately, not burn max_passes)."""

    def contradicted_factcheck(skill_output):
        return (
            FactCheckVerdict(
                claim="revenue is $5B",
                evidence_tier="WEBFETCH",
                verdict="CONTRADICTED",
                citation="https://example.com/10k",
                reasoning="10-K says $3B",
            ),
        )

    gate_fn = executioner.make_gate_fn(
        "dell.com",
        "Dell",
        tmp_path,
        mechanical_cmd_fn=_exit0_mechanical_cmd_fn,
        factcheck_fn=contradicted_factcheck,
        quality_fn=_passing_quality_fn,
    )
    result = gate_fn("algolia-intel-financial-public")
    assert result.status == self_heal.GateStatus.BLOCKED
    assert result.fatal is True


def test_make_gate_fn_maps_quality_below_threshold_to_blocked_not_fatal(tmp_path: Path):
    def failing_quality(skill_output):
        return QualityScore(
            dimension="instruction_adherence",
            score=2.0,
            passing_checks=2,
            total_checks=10,
            reasoning="missed most instructions",
        )

    gate_fn = executioner.make_gate_fn(
        "dell.com",
        "Dell",
        tmp_path,
        mechanical_cmd_fn=_exit0_mechanical_cmd_fn,
        factcheck_fn=_passing_factcheck_fn,
        quality_fn=failing_quality,
    )
    result = gate_fn("algolia-intel-hiring")
    assert result.status == self_heal.GateStatus.BLOCKED
    assert result.fatal is False


def test_make_gate_fn_runs_adversarial_panel_only_on_risky_claims(tmp_path: Path):
    def weak_evidence_factcheck(skill_output):
        return (
            FactCheckVerdict(
                claim="rumored expansion",
                evidence_tier="NO_SOURCE",
                verdict="SUPPORTED",
                citation=None,
                reasoning="only a web search hit",
            ),
        )

    calls = []

    def refuting_adversarial(skill_output, risky_claims):
        calls.append(risky_claims)
        votes = tuple(
            AdversarialVoterVerdict(voter_id=i, refuted=True, reasoning="no corroboration")
            for i in range(3)
        )
        return (AdversarialVerdict(claim=risky_claims[0], votes=votes, survives=False),)

    gate_fn = executioner.make_gate_fn(
        "dell.com",
        "Dell",
        tmp_path,
        mechanical_cmd_fn=_exit0_mechanical_cmd_fn,
        factcheck_fn=weak_evidence_factcheck,
        adversarial_fn=refuting_adversarial,
        quality_fn=_passing_quality_fn,
    )
    result = gate_fn("algolia-intel-news")
    assert calls == [("rumored expansion",)]
    assert result.status == self_heal.GateStatus.BLOCKED
    assert result.fatal is True  # adversarial refutation is UNFIXABLE per contract


def test_make_gate_fn_default_stages_raise_notimplementederror_not_silent_pass(tmp_path: Path):
    """Per the brief: do NOT silently make stages 2-4 always pass. With no
    factcheck_fn/adversarial_fn/quality_fn overrides, reaching stage 2 must
    raise loudly."""
    gate_fn = executioner.make_gate_fn(
        "dell.com", "Dell", tmp_path, mechanical_cmd_fn=_exit0_mechanical_cmd_fn
    )
    with pytest.raises(NotImplementedError):
        gate_fn("algolia-intel-traffic")


def test_make_gate_fn_populates_verdict_sink(tmp_path: Path):
    sink: dict[str, gate_module.Verdict] = {}
    gate_fn = executioner.make_gate_fn(
        "dell.com",
        "Dell",
        tmp_path,
        mechanical_cmd_fn=_exit0_mechanical_cmd_fn,
        factcheck_fn=_passing_factcheck_fn,
        quality_fn=_passing_quality_fn,
        verdict_sink=sink,
    )
    gate_fn("algolia-intel-traffic")
    assert "algolia-intel-traffic" in sink
    assert sink["algolia-intel-traffic"].stage == 5
    assert sink["algolia-intel-traffic"].status == gate_module.VerdictStatus.PASS


def test_make_gate_fn_default_mechanical_uses_gate_default_when_no_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """No mechanical_cmd_fn override -> gate.gate() builds its own default
    `--audit-data <path>` command (Task 6d fix #1) against a real
    deliverables/*-audit-data.json under `audit_dir` -- `audit_dir` here
    means the company's own dir, matching what claims.py/llm_stages.py
    already assume. The fake `factcheck_mechanical.py` stand-in exits 2
    (BLOCKED) deliberately, so this proves the default-cmd path is really
    exercised (not skipped/short-circuited) and maps to a fail-closed
    BLOCKED/non-fatal result, never a crash and never a silent CLEAN."""
    deliverables = tmp_path / "deliverables"
    deliverables.mkdir()
    (deliverables / "dell-audit-data.json").write_text("{}")

    fake_script = tmp_path / "fake_factcheck_mechanical.py"
    fake_script.write_text("import sys; print('mechanical block'); sys.exit(2)\n")
    monkeypatch.setattr(gate_module, "FACTCHECK_MECHANICAL_PATH", fake_script)

    gate_fn = executioner.make_gate_fn("dell.com", "Dell", tmp_path)
    result = gate_fn("algolia-intel-traffic")
    assert result.status == self_heal.GateStatus.BLOCKED
    assert result.fatal is False


def test_make_gate_fn_default_mechanical_raises_clear_error_when_no_audit_data(
    tmp_path: Path,
):
    """When `audit_dir` has no deliverables/*-audit-data.json yet (skill ran
    before the report deliverable exists), gate.gate()'s default mechanical
    command builder raises a clear FileNotFoundError rather than building a
    command against a guessed/wrong path -- callers with a legitimate
    early-skill use case must pass an explicit mechanical_cmd_fn."""
    gate_fn = executioner.make_gate_fn("dell.com", "Dell", tmp_path)
    with pytest.raises(FileNotFoundError, match="audit-data"):
        gate_fn("algolia-intel-traffic")
