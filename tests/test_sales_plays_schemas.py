"""Contract tests for synth-sales-plays schemas -- 30+ pure Pydantic tests, no API/DB calls."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.synth_sales_plays.schemas import (
    MEDDPICCField,
    ObjectionHandler,
    PowerMapMember,
    SalesPlaysInput,
    SalesPlaysOutput,
    SPINQuestion,
    TalkTrack,
)


# ---------------------------------------------------------------------------
# SalesPlaysInput
# ---------------------------------------------------------------------------
class TestSalesPlaysInput:
    def test_valid_input(self) -> None:
        inp = SalesPlaysInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            SalesPlaysInput(domain="dell.com", bogus="nope")  # type: ignore[call-arg]

    def test_empty_domain_allowed_by_schema(self) -> None:
        """Domain validation is handled by the validator, not the schema."""
        inp = SalesPlaysInput(domain="")
        assert inp.domain == ""


# ---------------------------------------------------------------------------
# MEDDPICCField
# ---------------------------------------------------------------------------
class TestMEDDPICCField:
    def test_valid_full(self) -> None:
        field = MEDDPICCField(
            field_name="economic_buyer",
            person="John Smith",
            evidence="VP of Engineering listed in hiring data",
            recommended_approach="Schedule exec briefing via mutual connection",
            confidence="high",
        )
        assert field.field_name == "economic_buyer"
        assert field.person == "John Smith"
        assert field.confidence == "high"

    def test_minimal_defaults(self) -> None:
        field = MEDDPICCField(
            field_name="metrics",
            evidence="Revenue growing 15% YoY",
            recommended_approach="Tie ROI to their growth targets",
        )
        assert field.person is None
        assert field.confidence == "medium"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            MEDDPICCField(
                field_name="metrics",
                evidence="test",
                recommended_approach="test",
                bogus="no",  # type: ignore[call-arg]
            )

    def test_rejects_invalid_field_name(self) -> None:
        with pytest.raises(ValidationError):
            MEDDPICCField(
                field_name="invalid_field",  # type: ignore[arg-type]
                evidence="test",
                recommended_approach="test",
            )

    def test_all_valid_field_names(self) -> None:
        valid_names = [
            "metrics",
            "economic_buyer",
            "decision_criteria",
            "decision_process",
            "paper_process",
            "identified_pain",
            "champion",
            "competition",
        ]
        for name in valid_names:
            field = MEDDPICCField(
                field_name=name,  # type: ignore[arg-type]
                evidence="test evidence",
                recommended_approach="test approach",
            )
            assert field.field_name == name

    def test_rejects_invalid_confidence(self) -> None:
        with pytest.raises(ValidationError):
            MEDDPICCField(
                field_name="metrics",
                evidence="test",
                recommended_approach="test",
                confidence="very_high",  # type: ignore[arg-type]
            )

    def test_all_valid_confidences(self) -> None:
        for conf in ["high", "medium", "low"]:
            field = MEDDPICCField(
                field_name="metrics",
                evidence="test",
                recommended_approach="test",
                confidence=conf,  # type: ignore[arg-type]
            )
            assert field.confidence == conf


# ---------------------------------------------------------------------------
# SPINQuestion
# ---------------------------------------------------------------------------
class TestSPINQuestion:
    def test_valid_full(self) -> None:
        q = SPINQuestion(
            category="problem",
            question="What challenges do you face with search relevance?",
            context="BuiltWith shows legacy search vendor with no AI features",
            expected_response="We struggle with long-tail queries",
        )
        assert q.category == "problem"
        assert q.expected_response != ""

    def test_minimal_defaults(self) -> None:
        q = SPINQuestion(
            category="situation",
            question="How many SKUs does your catalog contain?",
            context="ecommerce platform detected",
        )
        assert q.expected_response == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            SPINQuestion(
                category="situation",
                question="test",
                context="test",
                bogus="no",  # type: ignore[call-arg]
            )

    def test_rejects_invalid_category(self) -> None:
        with pytest.raises(ValidationError):
            SPINQuestion(
                category="invalid",  # type: ignore[arg-type]
                question="test",
                context="test",
            )

    def test_all_valid_categories(self) -> None:
        for cat in ["situation", "problem", "implication", "need_payoff"]:
            q = SPINQuestion(
                category=cat,  # type: ignore[arg-type]
                question="test question",
                context="test context",
            )
            assert q.category == cat


# ---------------------------------------------------------------------------
# ObjectionHandler
# ---------------------------------------------------------------------------
class TestObjectionHandler:
    def test_valid_full(self) -> None:
        oh = ObjectionHandler(
            objection="We're building search in-house",
            likelihood="high",
            counter="Your hiring data shows 3 search engineering roles open for 6+ months",
            evidence_to_cite=["LinkedIn job posting from Jan 2026", "Glassdoor review"],
        )
        assert oh.objection == "We're building search in-house"
        assert oh.likelihood == "high"
        assert len(oh.evidence_to_cite) == 2

    def test_minimal_defaults(self) -> None:
        oh = ObjectionHandler(
            objection="Not a priority",
            counter="Your CEO mentioned search in the last earnings call",
        )
        assert oh.likelihood == "medium"
        assert oh.evidence_to_cite == []

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ObjectionHandler(
                objection="test",
                counter="test",
                bogus="no",  # type: ignore[call-arg]
            )

    def test_rejects_invalid_likelihood(self) -> None:
        with pytest.raises(ValidationError):
            ObjectionHandler(
                objection="test",
                counter="test",
                likelihood="very_likely",  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# TalkTrack
# ---------------------------------------------------------------------------
class TestTalkTrack:
    def test_valid_full(self) -> None:
        tt = TalkTrack(
            line_type="opener",
            text="I noticed your CEO recently said 'search is critical to our digital strategy'",
            mirrors_exec_language=True,
            source_quote="search is critical to our digital strategy",
        )
        assert tt.line_type == "opener"
        assert tt.mirrors_exec_language is True
        assert tt.source_quote is not None

    def test_minimal_defaults(self) -> None:
        tt = TalkTrack(
            line_type="bridge",
            text="That's exactly what Algolia helps with",
        )
        assert tt.mirrors_exec_language is False
        assert tt.source_quote is None

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            TalkTrack(
                line_type="opener",
                text="test",
                bogus="no",  # type: ignore[call-arg]
            )

    def test_rejects_invalid_line_type(self) -> None:
        with pytest.raises(ValidationError):
            TalkTrack(
                line_type="intro",  # type: ignore[arg-type]
                text="test",
            )

    def test_all_valid_line_types(self) -> None:
        for lt in ["opener", "bridge", "close"]:
            tt = TalkTrack(
                line_type=lt,  # type: ignore[arg-type]
                text="test text",
            )
            assert tt.line_type == lt


# ---------------------------------------------------------------------------
# PowerMapMember
# ---------------------------------------------------------------------------
class TestPowerMapMember:
    def test_valid_full(self) -> None:
        pm = PowerMapMember(
            name="Jane Doe",
            title="VP of Engineering",
            meddpicc_role="economic_buyer",
            attitude="supportive",
            recommended_approach="Engage via CTO introduction",
            linkedin_url="https://linkedin.com/in/janedoe",
        )
        assert pm.name == "Jane Doe"
        assert pm.meddpicc_role == "economic_buyer"
        assert pm.attitude == "supportive"
        assert pm.linkedin_url is not None

    def test_minimal_defaults(self) -> None:
        pm = PowerMapMember(name="John", title="Engineer")
        assert pm.meddpicc_role == "unknown"
        assert pm.attitude == "unknown"
        assert pm.recommended_approach == ""
        assert pm.linkedin_url is None

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            PowerMapMember(name="X", title="Y", bogus="no")  # type: ignore[call-arg]

    def test_rejects_invalid_meddpicc_role(self) -> None:
        with pytest.raises(ValidationError):
            PowerMapMember(
                name="X",
                title="Y",
                meddpicc_role="ceo",  # type: ignore[arg-type]
            )

    def test_rejects_invalid_attitude(self) -> None:
        with pytest.raises(ValidationError):
            PowerMapMember(
                name="X",
                title="Y",
                attitude="hostile",  # type: ignore[arg-type]
            )

    def test_all_valid_meddpicc_roles(self) -> None:
        valid_roles = [
            "economic_buyer",
            "technical_evaluator",
            "champion",
            "influencer",
            "blocker",
            "unknown",
        ]
        for role in valid_roles:
            pm = PowerMapMember(
                name="Test",
                title="Title",
                meddpicc_role=role,  # type: ignore[arg-type]
            )
            assert pm.meddpicc_role == role

    def test_all_valid_attitudes(self) -> None:
        valid_attitudes = [
            "champion",
            "supportive",
            "neutral",
            "skeptical",
            "blocker",
            "unknown",
        ]
        for att in valid_attitudes:
            pm = PowerMapMember(
                name="Test",
                title="Title",
                attitude=att,  # type: ignore[arg-type]
            )
            assert pm.attitude == att


# ---------------------------------------------------------------------------
# SalesPlaysOutput
# ---------------------------------------------------------------------------
class TestSalesPlaysOutput:
    def test_minimal_output(self) -> None:
        output = SalesPlaysOutput(domain="dell.com")
        assert output.domain == "dell.com"
        assert output.meddpicc == []
        assert output.spin_questions == []
        assert output.objection_handlers == []
        assert output.talk_tracks == []
        assert output.power_map == []
        assert output.playbook_summary == ""
        assert output.top_3_actions == []

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            SalesPlaysOutput(domain="dell.com", bogus="no")  # type: ignore[call-arg]

    def test_full_output(self) -> None:
        output = SalesPlaysOutput(
            domain="dell.com",
            meddpicc=[
                MEDDPICCField(
                    field_name="metrics",
                    evidence="Revenue $90B",
                    recommended_approach="Tie to growth",
                ),
            ],
            spin_questions=[
                SPINQuestion(
                    category="situation",
                    question="How many SKUs?",
                    context="ecommerce detected",
                ),
            ],
            objection_handlers=[
                ObjectionHandler(
                    objection="Too expensive",
                    counter="ROI is $2M/year",
                ),
            ],
            talk_tracks=[
                TalkTrack(
                    line_type="opener",
                    text="I saw your CEO mentioned search",
                ),
            ],
            power_map=[
                PowerMapMember(
                    name="Jane Doe",
                    title="VP Engineering",
                ),
            ],
            playbook_summary="Strong opportunity driven by digital transformation.",
            top_3_actions=["Book meeting with VP Eng", "Send ROI deck", "Reference case study"],
        )
        assert len(output.meddpicc) == 1
        assert len(output.spin_questions) == 1
        assert len(output.objection_handlers) == 1
        assert len(output.talk_tracks) == 1
        assert len(output.power_map) == 1
        assert len(output.top_3_actions) == 3

    def test_model_dump_roundtrip(self) -> None:
        output = SalesPlaysOutput(
            domain="dell.com",
            meddpicc=[
                MEDDPICCField(
                    field_name="identified_pain",
                    evidence="Search bounce rate is 45%",
                    recommended_approach="Show before/after demo",
                    confidence="high",
                ),
            ],
            playbook_summary="Test summary",
            top_3_actions=["action1", "action2", "action3"],
        )
        dumped = output.model_dump()
        restored = SalesPlaysOutput.model_validate(dumped)
        assert restored.domain == "dell.com"
        assert restored.meddpicc[0].field_name == "identified_pain"
        assert restored.meddpicc[0].confidence == "high"

    def test_nested_model_validation(self) -> None:
        """Ensure nested models in output are properly validated."""
        with pytest.raises(ValidationError):
            SalesPlaysOutput(
                domain="dell.com",
                meddpicc=[
                    {  # type: ignore[list-item]
                        "field_name": "invalid_field",
                        "evidence": "test",
                        "recommended_approach": "test",
                    }
                ],
            )

    def test_empty_string_domain(self) -> None:
        output = SalesPlaysOutput(domain="")
        assert output.domain == ""

    def test_top_3_actions_can_be_any_length(self) -> None:
        """Schema allows any count; validator enforces exactly 3."""
        output = SalesPlaysOutput(
            domain="dell.com",
            top_3_actions=["one", "two"],
        )
        assert len(output.top_3_actions) == 2

    def test_model_dump_keys(self) -> None:
        output = SalesPlaysOutput(domain="dell.com")
        dumped = output.model_dump()
        expected_keys = {
            "domain",
            "meddpicc",
            "spin_questions",
            "objection_handlers",
            "talk_tracks",
            "power_map",
            "playbook_summary",
            "top_3_actions",
        }
        assert set(dumped.keys()) == expected_keys
