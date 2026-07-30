"""Tests for the Track G 5-stage `gate()` verification pipeline.

Stages 2-4 are LLM-backed but dependency-injected (no live LLM access in
this test environment) -- see server/pipeline/gate.py's module
docstring. Stage 1 (mechanical) is exercised against a real subprocess
(a throwaway python -c script standing in for factcheck_mechanical.py) using
the exact exit-code contract self_heal.subprocess_gate already implements
and tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from server.pipeline.gate import (
    BlockClass,
    SkillOutput,
    VerdictStatus,
    find_audit_data_json,
    gate,
)
from server.pipeline.self_heal import (
    GateResult,
    GateStatus,
    PhaseOutcome,
    SelfHealLoop,
)
from server.pipeline.verdicts import (
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


class TestFindAuditDataJson:
    """Task 6d fix #1 -- the shared glob helper both gate.py's default
    mechanical command and claims.py's extractors now import, so the two
    modules can't drift on how a real audit-data.json is located."""

    def test_finds_the_real_slug_file_under_deliverables(self, tmp_path: Path) -> None:
        company_dir = tmp_path / "Belk"
        deliverables = company_dir / "deliverables"
        deliverables.mkdir(parents=True)
        target = deliverables / "belk-audit-data.json"
        target.write_text("{}")

        assert find_audit_data_json(company_dir) == target

    def test_returns_none_when_no_deliverables_dir(self, tmp_path: Path) -> None:
        assert find_audit_data_json(tmp_path / "NoSuchCompany") is None

    def test_returns_none_when_deliverables_dir_has_no_audit_data_json(
        self, tmp_path: Path
    ) -> None:
        deliverables = tmp_path / "Belk" / "deliverables"
        deliverables.mkdir(parents=True)
        (deliverables / "unrelated.json").write_text("{}")

        assert find_audit_data_json(tmp_path / "Belk") is None


class TestDefaultMechanicalCmdUsesAuditDataForm:
    """Task 6d fix #1: `gate()`'s DEFAULT mechanical-command builder must use
    the real `factcheck_mechanical.py --audit-data <path>` form, matching
    what `claims.py`'s extractors and `llm_stages.py`'s prompts already
    assume `SkillOutput.audit_dir` means (the company's own directory, not
    its parent) -- see task-6-local-report.md Findings #1. Proven here
    against a fixture matching the real shape, with NO explicit
    `mechanical_cmd` override -- exercising the actual default path."""

    @staticmethod
    def _company_dir_with_audit_data(tmp_path: Path) -> Path:
        company_dir = tmp_path / "Belk"
        deliverables = company_dir / "deliverables"
        deliverables.mkdir(parents=True)
        (deliverables / "belk-audit-data.json").write_text("{}")
        return company_dir

    @staticmethod
    def _argv_recording_script(tmp_path: Path, record_path: Path) -> Path:
        """A throwaway script standing in for factcheck_mechanical.py: records
        its own argv to `record_path`, then exits 0 (CLEAN) only if invoked
        with the real `--audit-data` form and NOT the old `--audit-dir`/
        `--company` form -- exits 1 (ERROR) otherwise, so a regression back
        to the old form fails loudly rather than silently passing."""
        script = tmp_path / "fake_factcheck_mechanical.py"
        script.write_text(
            "import sys, json\n"
            f"open({str(record_path)!r}, 'w').write(json.dumps(sys.argv[1:]))\n"
            "argv = sys.argv[1:]\n"
            "sys.exit(0 if '--audit-data' in argv and '--audit-dir' not in argv "
            "and '--company' not in argv else 1)\n"
        )
        return script

    def test_default_mechanical_cmd_passes_real_audit_data_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import server.pipeline.gate as gate_module

        company_dir = self._company_dir_with_audit_data(tmp_path)
        record_path = tmp_path / "argv.json"
        fake_script = self._argv_recording_script(tmp_path, record_path)
        monkeypatch.setattr(gate_module, "FACTCHECK_MECHANICAL_PATH", fake_script)

        skill_output = SkillOutput(
            skill_name="algolia-intel-techstack",
            domain="belk.com",
            audit_dir=company_dir,
            company_name="Belk",
        )

        # No mechanical_cmd override -- exercises gate()'s real default path.
        # No factcheck_fn injected either: if stage 1 had blocked/errored we'd
        # get a BLOCK verdict, not a NotImplementedError from stage 2 -- so
        # this exception is itself proof stage 1 passed CLEAN.
        with pytest.raises(NotImplementedError, match="stage 2"):
            gate(skill_output)

        recorded_argv = json.loads(record_path.read_text())
        assert "--audit-data" in recorded_argv
        audit_data_arg = recorded_argv[recorded_argv.index("--audit-data") + 1]
        assert audit_data_arg == str(company_dir / "deliverables" / "belk-audit-data.json")
        assert "--audit-dir" not in recorded_argv
        assert "--company" not in recorded_argv

    def test_default_mechanical_cmd_raises_clear_error_when_no_audit_data_json(
        self, tmp_path: Path
    ) -> None:
        skill_output = SkillOutput(
            skill_name="algolia-intel-techstack",
            domain="belk.com",
            audit_dir=tmp_path / "Belk",  # no deliverables/ under here
            company_name="Belk",
        )
        with pytest.raises(FileNotFoundError, match="audit-data"):
            gate(skill_output)
