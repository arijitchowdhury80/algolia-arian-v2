"""Tests for the Track G 5-stage `gate()` verification pipeline.

Stages 2-4 are LLM-backed but dependency-injected (no live LLM access in
this test environment) -- see prism_platform/pipeline/gate.py's module
docstring. Stage 1 (mechanical) is exercised against a real subprocess
(a throwaway python -c script standing in for factcheck_mechanical.py) using
the exact exit-code contract self_heal.subprocess_gate already implements
and tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from prism_platform.pipeline.gate import (
    BlockClass,
    SkillOutput,
    VerdictStatus,
    gate,
)
from prism_platform.pipeline.self_heal import (
    GateResult,
    GateStatus,
    PhaseOutcome,
    SelfHealLoop,
)
from prism_platform.pipeline.verdicts import (
    AdversarialVerdict,
    AdversarialVoterVerdict,
    FactCheckVerdict,
    QualityScore,
)


def _skill_output(skill_name: str = "algolia-intel-financial-public") -> SkillOutput:
    return SkillOutput(
        skill_name=skill_name,
        domain="belk.com",
        audit_dir=Path("/tmp/does-not-need-to-exist/Belk"),
        company_name="Belk",
    )


def _clean_mechanical_cmd() -> list[str]:
    return [sys.executable, "-c", "import sys; sys.exit(0)"]


def _blocked_mechanical_cmd(*findings: str) -> list[str]:
    prints = "; ".join(f"print({f!r})" for f in findings) or "pass"
    return [sys.executable, "-c", f"{prints}; import sys; sys.exit(2)"]


def _error_mechanical_cmd() -> list[str]:
    return [sys.executable, "-c", "import sys; sys.exit(1)"]


def _supported_factcheck(*, tier: str = "AUTHENTIC") -> tuple[FactCheckVerdict, ...]:
    return (
        FactCheckVerdict(
            claim="Belk operates 291 stores.",
            evidence_tier=tier,  # type: ignore[arg-type]
            verdict="SUPPORTED",
            citation="https://belk.com/about" if tier == "AUTHENTIC" else None,
            reasoning="Matches source.",
        ),
    )


def _contradicted_factcheck() -> tuple[FactCheckVerdict, ...]:
    return (
        FactCheckVerdict(
            claim="Belk is headquartered in Miami.",
            evidence_tier="AUTHENTIC",
            verdict="CONTRADICTED",
            citation="https://belk.com/about",
            reasoning="Source says Charlotte, NC, not Miami.",
        ),
    )


def _passing_quality() -> QualityScore:
    return QualityScore(
        dimension="instruction_adherence",
        score=9.0,
        passing_checks=18,
        total_checks=20,
        reasoning="Followed nearly all checklist items.",
    )


def _failing_quality() -> QualityScore:
    return QualityScore(
        dimension="instruction_adherence",
        score=4.0,
        passing_checks=8,
        total_checks=20,
        reasoning="Skipped several required checklist items.",
    )


class TestStage1Mechanical:
    def test_clean_exit_advances_past_stage_1(self) -> None:
        # No factcheck_fn/quality_fn injected -- if this raised
        # NotImplementedError from a later stage, it proves stage 1 passed.
        with pytest.raises(NotImplementedError, match="stage 2"):
            gate(_skill_output(), mechanical_cmd=_clean_mechanical_cmd())

    def test_exit_two_blocks_at_stage_1_retry_worthy(self) -> None:
        v = gate(
            _skill_output(),
            mechanical_cmd=_blocked_mechanical_cmd("missing traffic data"),
        )
        assert v.stage == 1
        assert v.status == VerdictStatus.BLOCK
        assert v.block_class == BlockClass.RETRY_WORTHY
        assert "missing traffic data" in v.findings

    def test_other_exit_code_also_blocks_at_stage_1_fail_closed(self) -> None:
        v = gate(_skill_output(), mechanical_cmd=_error_mechanical_cmd())
        assert v.stage == 1
        assert v.status == VerdictStatus.BLOCK
        assert v.block_class == BlockClass.RETRY_WORTHY


class TestStage2Factcheck:
    def test_all_supported_advances_past_stage_2(self) -> None:
        with pytest.raises(NotImplementedError, match="stage 4"):
            gate(
                _skill_output(),
                mechanical_cmd=_clean_mechanical_cmd(),
                factcheck_fn=lambda so: _supported_factcheck(),
                adversarial_fn=lambda so, claims: (),
            )

    def test_contradicted_blocks_at_stage_2_unfixable(self) -> None:
        v = gate(
            _skill_output(),
            mechanical_cmd=_clean_mechanical_cmd(),
            factcheck_fn=lambda so: _contradicted_factcheck(),
        )
        assert v.stage == 2
        assert v.status == VerdictStatus.BLOCK
        assert v.block_class == BlockClass.UNFIXABLE
        assert v.factcheck is not None
        assert v.factcheck.verdict == "CONTRADICTED"

    def test_unsupported_blocks_at_stage_2_unfixable(self) -> None:
        unsupported = (
            FactCheckVerdict(
                claim="x",
                evidence_tier="NO_SOURCE",
                verdict="UNSUPPORTED",
                citation=None,
                reasoning="No source found anywhere.",
            ),
        )
        v = gate(
            _skill_output(),
            mechanical_cmd=_clean_mechanical_cmd(),
            factcheck_fn=lambda so: unsupported,
        )
        assert v.stage == 2
        assert v.block_class == BlockClass.UNFIXABLE

    def test_missing_factcheck_fn_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError, match="stage 2"):
            gate(_skill_output(), mechanical_cmd=_clean_mechanical_cmd())


class TestStage3AdversarialPanel:
    def test_no_risky_claims_skips_panel_entirely_no_fn_required(self) -> None:
        # All claims AUTHENTIC -- no risky claims, so adversarial_fn is never
        # called and doesn't even need to be supplied.
        with pytest.raises(NotImplementedError, match="stage 4"):
            gate(
                _skill_output(),
                mechanical_cmd=_clean_mechanical_cmd(),
                factcheck_fn=lambda so: _supported_factcheck(tier="AUTHENTIC"),
            )

    def test_risky_claim_without_adversarial_fn_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError, match="stage 3"):
            gate(
                _skill_output(),
                mechanical_cmd=_clean_mechanical_cmd(),
                factcheck_fn=lambda so: _supported_factcheck(tier="WEBSEARCH"),
            )

    def test_panel_majority_survives_advances_to_stage_4(self) -> None:
        def panel(so: SkillOutput, claims: tuple[str, ...]) -> tuple[AdversarialVerdict, ...]:
            votes = [
                AdversarialVoterVerdict(voter_id=1, refuted=False, reasoning="holds"),
                AdversarialVoterVerdict(voter_id=2, refuted=False, reasoning="holds"),
                AdversarialVoterVerdict(voter_id=3, refuted=True, reasoning="unsure"),
            ]
            return tuple(AdversarialVerdict(claim=c, votes=votes, survives=True) for c in claims)

        with pytest.raises(NotImplementedError, match="stage 4"):
            gate(
                _skill_output(),
                mechanical_cmd=_clean_mechanical_cmd(),
                factcheck_fn=lambda so: _supported_factcheck(tier="WEBSEARCH"),
                adversarial_fn=panel,
            )

    def test_panel_majority_refuted_blocks_at_stage_3_unfixable(self) -> None:
        def panel(so: SkillOutput, claims: tuple[str, ...]) -> tuple[AdversarialVerdict, ...]:
            votes = [
                AdversarialVoterVerdict(voter_id=1, refuted=True, reasoning="doesn't hold"),
                AdversarialVoterVerdict(voter_id=2, refuted=True, reasoning="doesn't hold"),
                AdversarialVoterVerdict(voter_id=3, refuted=False, reasoning="maybe"),
            ]
            return tuple(AdversarialVerdict(claim=c, votes=votes, survives=False) for c in claims)

        v = gate(
            _skill_output(),
            mechanical_cmd=_clean_mechanical_cmd(),
            factcheck_fn=lambda so: _supported_factcheck(tier="NO_SOURCE"),
            adversarial_fn=panel,
        )
        assert v.stage == 3
        assert v.status == VerdictStatus.BLOCK
        assert v.block_class == BlockClass.UNFIXABLE
        assert v.adversarial is not None
        assert v.adversarial.survives is False


class TestStage4Quality:
    def test_passing_score_advances_to_stage_5(self) -> None:
        v = gate(
            _skill_output(),
            mechanical_cmd=_clean_mechanical_cmd(),
            factcheck_fn=lambda so: _supported_factcheck(),
            adversarial_fn=lambda so, claims: (),
            quality_fn=lambda so: _passing_quality(),
        )
        assert v.stage == 5
        assert v.status == VerdictStatus.PASS

    def test_failing_score_blocks_at_stage_4_retry_worthy(self) -> None:
        v = gate(
            _skill_output(),
            mechanical_cmd=_clean_mechanical_cmd(),
            factcheck_fn=lambda so: _supported_factcheck(),
            adversarial_fn=lambda so, claims: (),
            quality_fn=lambda so: _failing_quality(),
        )
        assert v.stage == 4
        assert v.status == VerdictStatus.BLOCK
        assert v.block_class == BlockClass.RETRY_WORTHY
        assert v.quality is not None
        assert v.quality.score == 4.0

    def test_custom_threshold_is_respected(self) -> None:
        # Score of 8.0 fails a threshold of 9.0 even though it would pass the default.
        borderline = QualityScore(
            dimension="instruction_adherence",
            score=8.0,
            passing_checks=16,
            total_checks=20,
            reasoning="Good but not perfect.",
        )
        v = gate(
            _skill_output(),
            mechanical_cmd=_clean_mechanical_cmd(),
            factcheck_fn=lambda so: _supported_factcheck(),
            adversarial_fn=lambda so, claims: (),
            quality_fn=lambda so: borderline,
            quality_pass_threshold=9.0,
        )
        assert v.stage == 4
        assert v.status == VerdictStatus.BLOCK

    def test_missing_quality_fn_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError, match="stage 4"):
            gate(
                _skill_output(),
                mechanical_cmd=_clean_mechanical_cmd(),
                factcheck_fn=lambda so: _supported_factcheck(),
                adversarial_fn=lambda so, claims: (),
            )


class TestStage5Legal:
    def test_full_pass_through_all_stages_yields_needs_human_review_legal_stub(self) -> None:
        v = gate(
            _skill_output(),
            mechanical_cmd=_clean_mechanical_cmd(),
            factcheck_fn=lambda so: _supported_factcheck(),
            adversarial_fn=lambda so, claims: (),
            quality_fn=lambda so: _passing_quality(),
        )
        assert v.stage == 5
        assert v.status == VerdictStatus.PASS
        assert v.block_class is None
        assert v.legal is not None
        assert v.legal.status == "needs_human_review"
        assert v.legal.note  # non-empty explanation

    def test_legal_stage_never_auto_blocks_regardless_of_content(self) -> None:
        # Legal has no automated logic at all -- reaching stage 5 always
        # yields PASS at the gate level; the note field is the only thing
        # that varies, never the status.
        v1 = gate(
            _skill_output("algolia-intel-company"),
            mechanical_cmd=_clean_mechanical_cmd(),
            factcheck_fn=lambda so: _supported_factcheck(),
            adversarial_fn=lambda so, claims: (),
            quality_fn=lambda so: _passing_quality(),
        )
        v2 = gate(
            _skill_output("algolia-intel-investor"),
            mechanical_cmd=_clean_mechanical_cmd(),
            factcheck_fn=lambda so: _supported_factcheck(),
            adversarial_fn=lambda so, claims: (),
            quality_fn=lambda so: _passing_quality(),
        )
        assert v1.legal is not None and v1.legal.status == "needs_human_review"
        assert v2.legal is not None and v2.legal.status == "needs_human_review"


class TestSkillNamePropagation:
    def test_verdict_carries_the_skill_name_through_every_stage(self) -> None:
        for cmd, kwargs, expected_stage in [
            (_blocked_mechanical_cmd("x"), {}, 1),
            (
                _clean_mechanical_cmd(),
                {"factcheck_fn": lambda so: _contradicted_factcheck()},
                2,
            ),
        ]:
            v = gate(_skill_output("algolia-intel-hiring"), mechanical_cmd=cmd, **kwargs)  # type: ignore[arg-type]
            assert v.skill_name == "algolia-intel-hiring"
            assert v.stage == expected_stage


class TestPatchFourStageNotClaimScopedStrikeCounting:
    """Patch #4: the 3-strike kill condition in the self-heal loop counts
    'same stage' not 'same claim' -- proven end-to-end by wiring gate()'s
    Verdict into a self_heal.GateFn and showing that 3 attempts whose BLOCK
    reasoning text differs every time (different specific findings) still
    exhaust max_passes and escalate, because they all block at the same
    stage number."""

    @staticmethod
    def _verdict_to_gate_result(v) -> GateResult:  # type: ignore[no-untyped-def]
        if v.status == VerdictStatus.PASS:
            return GateResult(status=GateStatus.CLEAN, raw=f"stage {v.stage} PASS")
        fatal = v.block_class == BlockClass.UNFIXABLE
        return GateResult(status=GateStatus.BLOCKED, findings=v.findings, fatal=fatal)

    def test_three_distinct_quality_failures_at_stage_4_still_exhaust_max_passes(self) -> None:
        call_count = {"n": 0}
        reasonings = ["missing pricing section", "missing hiring section", "missing news section"]

        def flaky_quality(so: SkillOutput) -> QualityScore:
            reason = reasonings[min(call_count["n"], len(reasonings) - 1)]
            call_count["n"] += 1
            return QualityScore(
                dimension="instruction_adherence",
                score=3.0,
                passing_checks=2,
                total_checks=20,
                reasoning=reason,
            )

        to_gate_result = TestPatchFourStageNotClaimScopedStrikeCounting._verdict_to_gate_result

        def make_gate_fn():  # type: ignore[no-untyped-def]
            def _gate(phase: str) -> GateResult:
                v = gate(
                    _skill_output(phase),
                    mechanical_cmd=_clean_mechanical_cmd(),
                    factcheck_fn=lambda so: _supported_factcheck(),
                    adversarial_fn=lambda so, claims: (),
                    quality_fn=flaky_quality,
                )
                return to_gate_result(v)

            return _gate

        loop = SelfHealLoop(
            dispatch=lambda phase, n: True,
            gate=make_gate_fn(),
            max_passes=3,
        )

        report = loop.run_phase("algolia-intel-industry")

        assert report.outcome == PhaseOutcome.NEEDS_HUMAN
        assert len(report.attempts) == 3
        # Every attempt blocked at stage 4 (quality), but each with distinct
        # reasoning text -- proving the strike counter tracked stage
        # identity, not exact claim/finding wording.
        distinct_findings = {a.gate.findings for a in report.attempts if a.gate is not None}
        assert len(distinct_findings) == 3  # all three attempts' findings differed
