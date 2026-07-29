"""Tests for the Pydantic verdict schemas (prism_platform/pipeline/verdicts.py).

These schemas are the E2-compliant, schema-constrained shapes an LLM's
tool-use output must validate against -- no free-form prose parsed after.
Shape is fixed by docs/workspace/phase2-executioner/interface-contract.md.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.pipeline.verdicts import (
    AdversarialVerdict,
    AdversarialVoterVerdict,
    FactCheckVerdict,
    LegalVerdict,
    QualityScore,
)


class TestFactCheckVerdict:
    def test_valid_supported_verdict(self) -> None:
        v = FactCheckVerdict(
            claim="Belk operates 291 stores.",
            evidence_tier="AUTHENTIC",
            verdict="SUPPORTED",
            citation="https://belk.com/about",
            reasoning="Matches the company's own About page.",
        )
        assert v.verdict == "SUPPORTED"
        assert v.citation == "https://belk.com/about"

    def test_citation_may_be_none(self) -> None:
        v = FactCheckVerdict(
            claim="Belk was founded in 1888.",
            evidence_tier="NO_SOURCE",
            verdict="UNSUPPORTED",
            citation=None,
            reasoning="No source found for this date.",
        )
        assert v.citation is None

    def test_rejects_invalid_evidence_tier(self) -> None:
        with pytest.raises(ValidationError):
            FactCheckVerdict(
                claim="x",
                evidence_tier="MADE_UP_TIER",  # type: ignore[arg-type]
                verdict="SUPPORTED",
                citation=None,
                reasoning="x",
            )

    def test_rejects_invalid_verdict_literal(self) -> None:
        with pytest.raises(ValidationError):
            FactCheckVerdict(
                claim="x",
                evidence_tier="AUTHENTIC",
                verdict="MAYBE",  # type: ignore[arg-type]
                citation=None,
                reasoning="x",
            )

    def test_roundtrips_through_json(self) -> None:
        v = FactCheckVerdict(
            claim="x",
            evidence_tier="WEBFETCH",
            verdict="CONTRADICTED",
            citation="https://example.com",
            reasoning="Source disagrees.",
        )
        restored = FactCheckVerdict.model_validate_json(v.model_dump_json())
        assert restored == v


class TestAdversarialVerdict:
    def test_valid_panel_with_three_voters(self) -> None:
        votes = [
            AdversarialVoterVerdict(voter_id=1, refuted=False, reasoning="Holds up."),
            AdversarialVoterVerdict(voter_id=2, refuted=False, reasoning="Holds up."),
            AdversarialVoterVerdict(voter_id=3, refuted=True, reasoning="Unsure."),
        ]
        v = AdversarialVerdict(claim="claim under test", votes=votes, survives=True)
        assert len(v.votes) == 3
        assert v.survives is True

    def test_voter_refuted_defaults_to_explicit_bool_not_optional(self) -> None:
        with pytest.raises(ValidationError):
            AdversarialVoterVerdict(voter_id=1, reasoning="x")  # type: ignore[call-arg]

    def test_rejects_non_bool_survives(self) -> None:
        with pytest.raises(ValidationError):
            AdversarialVerdict(
                claim="x",
                votes=[AdversarialVoterVerdict(voter_id=1, refuted=False, reasoning="x")],
                survives={"not": "a bool"},  # type: ignore[arg-type]
            )


class TestQualityScore:
    def test_valid_score(self) -> None:
        q = QualityScore(
            dimension="instruction_adherence",
            score=8.5,
            passing_checks=17,
            total_checks=20,
            reasoning="Mostly followed the skill's checklist.",
        )
        assert q.score == 8.5
        assert q.dimension == "instruction_adherence"

    def test_rejects_wrong_dimension_literal(self) -> None:
        with pytest.raises(ValidationError):
            QualityScore(
                dimension="completeness",  # type: ignore[arg-type]
                score=5.0,
                passing_checks=1,
                total_checks=2,
                reasoning="x",
            )

    def test_score_accepts_zero_and_ten_boundaries(self) -> None:
        low = QualityScore(
            dimension="instruction_adherence",
            score=0.0,
            passing_checks=0,
            total_checks=10,
            reasoning="x",
        )
        high = QualityScore(
            dimension="instruction_adherence",
            score=10.0,
            passing_checks=10,
            total_checks=10,
            reasoning="x",
        )
        assert low.score == 0.0
        assert high.score == 10.0


class TestLegalVerdict:
    def test_only_needs_human_review_status_is_valid(self) -> None:
        v = LegalVerdict(status="needs_human_review", note="No rubric exists yet.")
        assert v.status == "needs_human_review"

    def test_rejects_pass_status(self) -> None:
        with pytest.raises(ValidationError):
            LegalVerdict(status="pass", note="x")  # type: ignore[arg-type]

    def test_rejects_block_status(self) -> None:
        with pytest.raises(ValidationError):
            LegalVerdict(status="block", note="x")  # type: ignore[arg-type]
