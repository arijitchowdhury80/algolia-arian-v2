"""Contract tests for synth-business-case schemas -- 30+ pure Pydantic tests, no API/DB calls."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.synth_business_case.schemas import (
    BusinessCaseInput,
    BusinessCaseOutput,
    CustomerProof,
    DisplacementCost,
    SaidVsFoundRow,
    TimingSignal,
    ValueLever,
)


# ---------------------------------------------------------------------------
# BusinessCaseInput
# ---------------------------------------------------------------------------
class TestBusinessCaseInput:
    def test_valid_input(self) -> None:
        inp = BusinessCaseInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            BusinessCaseInput(domain="dell.com", bogus="nope")  # type: ignore[call-arg]

    def test_empty_domain_allowed_by_schema(self) -> None:
        """Domain validation is handled by the validator, not the schema."""
        inp = BusinessCaseInput(domain="")
        assert inp.domain == ""


# ---------------------------------------------------------------------------
# SaidVsFoundRow
# ---------------------------------------------------------------------------
class TestSaidVsFoundRow:
    def test_valid_full(self) -> None:
        row = SaidVsFoundRow(
            exec_said="CFO Jane Smith: We are investing in digital.",
            we_found="Site search returns 0 results for 15% of queries.",
            competitors_doing="HP uses Algolia with 37% conversion lift.",
            your_move="Algolia NeuralSearch eliminates zero-result queries.",
            category="search_quality",
            evidence_tier="VERIFIED",
        )
        assert row.exec_said.startswith("CFO")
        assert row.category == "search_quality"

    @pytest.mark.parametrize(
        "category",
        [
            "search_quality",
            "digital_investment",
            "competitive_gap",
            "customer_experience",
            "technology_modernization",
            "hiring_signal",
            "financial_opportunity",
        ],
    )
    def test_valid_categories(self, category: str) -> None:
        row = SaidVsFoundRow(
            exec_said="Quote",
            we_found="Finding",
            competitors_doing="Action",
            your_move="Move",
            category=category,  # type: ignore[arg-type]
        )
        assert row.category == category

    def test_invalid_category_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SaidVsFoundRow(
                exec_said="Quote",
                we_found="Finding",
                competitors_doing="Action",
                your_move="Move",
                category="invalid_category",  # type: ignore[arg-type]
            )

    def test_default_evidence_tier(self) -> None:
        row = SaidVsFoundRow(
            exec_said="Q",
            we_found="F",
            competitors_doing="C",
            your_move="M",
            category="search_quality",
        )
        assert row.evidence_tier == "VERIFIED"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            SaidVsFoundRow(
                exec_said="Q",
                we_found="F",
                competitors_doing="C",
                your_move="M",
                category="search_quality",
                bogus="no",
            )  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# ValueLever
# ---------------------------------------------------------------------------
class TestValueLever:
    def test_valid_full(self) -> None:
        lever = ValueLever(
            lever_name="Search Conversion Uplift",
            description="Better search relevance drives more purchases.",
            conservative_estimate=500_000.0,
            moderate_estimate=1_500_000.0,
            case_study_proof="Shoe Carnival saw 3.5x conversion lift",
            calculation_method="50M visits x 40% search rate x 2% conversion x $50 AOV x 5% lift",
            assumptions=["40% of visits use search", "Average order value $50"],
        )
        assert lever.lever_name == "Search Conversion Uplift"
        assert lever.conservative_estimate == 500_000.0
        assert lever.moderate_estimate == 1_500_000.0
        assert len(lever.assumptions) == 2

    def test_minimal_defaults(self) -> None:
        lever = ValueLever(lever_name="Test", description="Test lever")
        assert lever.conservative_estimate is None
        assert lever.moderate_estimate is None
        assert lever.case_study_proof == ""
        assert lever.calculation_method == ""
        assert lever.assumptions == []

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ValueLever(lever_name="T", description="D", bogus="no")  # type: ignore[call-arg]

    def test_negative_estimate_allowed(self) -> None:
        """Schema does not enforce min value; business logic handles this."""
        lever = ValueLever(lever_name="T", description="D", conservative_estimate=-100.0)
        assert lever.conservative_estimate == -100.0


# ---------------------------------------------------------------------------
# DisplacementCost
# ---------------------------------------------------------------------------
class TestDisplacementCost:
    def test_valid_full(self) -> None:
        dc = DisplacementCost(
            current_vendor="Elasticsearch",
            cost_of_staying_annual=250_000.0,
            cost_of_switching=100_000.0,
            net_benefit_3yr=650_000.0,
            assumptions=["3 FTE engineers maintaining ES cluster at $120k each"],
        )
        assert dc.current_vendor == "Elasticsearch"
        assert dc.net_benefit_3yr == 650_000.0

    def test_minimal_defaults(self) -> None:
        dc = DisplacementCost(current_vendor="Coveo")
        assert dc.cost_of_staying_annual is None
        assert dc.cost_of_switching is None
        assert dc.net_benefit_3yr is None
        assert dc.assumptions == []

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            DisplacementCost(current_vendor="X", bogus="no")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# CustomerProof
# ---------------------------------------------------------------------------
class TestCustomerProof:
    def test_valid_full(self) -> None:
        cp = CustomerProof(
            customer_name="Lacoste",
            industry="Retail / Fashion",
            use_case="Product search and discovery",
            key_metric="37% conversion lift",
            matched_lever="Search Conversion Uplift",
            url="https://www.algolia.com/customers/lacoste/",
        )
        assert cp.customer_name == "Lacoste"
        assert cp.key_metric == "37% conversion lift"

    def test_minimal_defaults(self) -> None:
        cp = CustomerProof(
            customer_name="Test",
            industry="Tech",
            key_metric="10% improvement",
        )
        assert cp.use_case == ""
        assert cp.matched_lever == ""
        assert cp.url is None

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CustomerProof(
                customer_name="X",
                industry="Y",
                key_metric="Z",
                bogus="no",
            )  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# TimingSignal
# ---------------------------------------------------------------------------
class TestTimingSignal:
    def test_valid_full(self) -> None:
        ts = TimingSignal(
            signal="CFO announced digital transformation initiative",
            source_module="intel-investor",
            urgency="high",
            reason="Budget allocated for digital tools in current fiscal year",
        )
        assert ts.urgency == "high"
        assert ts.source_module == "intel-investor"

    @pytest.mark.parametrize("urgency", ["high", "medium", "low"])
    def test_valid_urgency_levels(self, urgency: str) -> None:
        ts = TimingSignal(
            signal="S",
            source_module="intel-news",
            urgency=urgency,  # type: ignore[arg-type]
            reason="R",
        )
        assert ts.urgency == urgency

    def test_invalid_urgency_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TimingSignal(
                signal="S",
                source_module="intel-news",
                urgency="critical",  # type: ignore[arg-type]
                reason="R",
            )

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            TimingSignal(
                signal="S",
                source_module="M",
                urgency="high",
                reason="R",
                bogus="no",
            )  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# BusinessCaseOutput
# ---------------------------------------------------------------------------
class TestBusinessCaseOutput:
    def test_minimal_defaults(self) -> None:
        output = BusinessCaseOutput(domain="dell.com")
        assert output.domain == "dell.com"
        assert output.said_vs_found == []
        assert output.value_levers == []
        assert output.total_conservative_impact is None
        assert output.total_moderate_impact is None
        assert output.sensitivity_analysis == ""
        assert output.displacement is None
        assert output.customer_proofs == []
        assert output.timing_signals == []
        assert output.urgency_summary == ""
        assert output.executive_summary == ""
        assert output.one_line_pitch == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            BusinessCaseOutput(domain="dell.com", bogus="no")  # type: ignore[call-arg]

    def test_full_output(self) -> None:
        output = BusinessCaseOutput(
            domain="dell.com",
            said_vs_found=[
                SaidVsFoundRow(
                    exec_said="CEO: We are investing in digital.",
                    we_found="Search is underperforming.",
                    competitors_doing="HP uses Algolia.",
                    your_move="Algolia fixes this.",
                    category="search_quality",
                ),
            ],
            value_levers=[
                ValueLever(
                    lever_name="Conversion",
                    description="Better search",
                    conservative_estimate=500_000.0,
                    moderate_estimate=1_500_000.0,
                ),
            ],
            total_conservative_impact=500_000.0,
            total_moderate_impact=1_500_000.0,
            sensitivity_analysis="Estimates vary with AOV assumptions.",
            displacement=DisplacementCost(
                current_vendor="Elasticsearch",
                net_benefit_3yr=650_000.0,
            ),
            customer_proofs=[
                CustomerProof(
                    customer_name="Lacoste",
                    industry="Retail",
                    key_metric="37% lift",
                ),
            ],
            timing_signals=[
                TimingSignal(
                    signal="Digital initiative announced",
                    source_module="intel-investor",
                    urgency="high",
                    reason="Budget allocated",
                ),
            ],
            urgency_summary="Act before fiscal year budget cycle closes.",
            executive_summary="Dell has a massive opportunity...",
            one_line_pitch="Dell can unlock $500K by switching to Algolia.",
        )
        assert len(output.said_vs_found) == 1
        assert len(output.value_levers) == 1
        assert output.total_conservative_impact == 500_000.0
        assert output.displacement is not None
        assert output.displacement.current_vendor == "Elasticsearch"
        assert len(output.customer_proofs) == 1
        assert len(output.timing_signals) == 1
        assert output.one_line_pitch.startswith("Dell")

    def test_displacement_can_be_none(self) -> None:
        output = BusinessCaseOutput(domain="test.com", displacement=None)
        assert output.displacement is None

    def test_model_dump_roundtrip(self) -> None:
        output = BusinessCaseOutput(
            domain="dell.com",
            said_vs_found=[
                SaidVsFoundRow(
                    exec_said="Quote",
                    we_found="Finding",
                    competitors_doing="Action",
                    your_move="Move",
                    category="search_quality",
                )
            ],
            value_levers=[
                ValueLever(
                    lever_name="Test",
                    description="Desc",
                    conservative_estimate=100.0,
                )
            ],
            total_conservative_impact=100.0,
            executive_summary="Summary text",
            one_line_pitch="Pitch text",
        )
        data = output.model_dump()
        restored = BusinessCaseOutput.model_validate(data)
        assert restored.domain == output.domain
        assert len(restored.said_vs_found) == 1
        assert len(restored.value_levers) == 1
        assert restored.total_conservative_impact == 100.0
        assert restored.executive_summary == "Summary text"

    def test_multiple_said_vs_found_rows(self) -> None:
        rows = [
            SaidVsFoundRow(
                exec_said=f"Quote {i}",
                we_found=f"Finding {i}",
                competitors_doing=f"Action {i}",
                your_move=f"Move {i}",
                category="search_quality",
            )
            for i in range(7)
        ]
        output = BusinessCaseOutput(domain="test.com", said_vs_found=rows)
        assert len(output.said_vs_found) == 7

    def test_multiple_value_levers(self) -> None:
        levers = [
            ValueLever(
                lever_name=f"Lever {i}",
                description=f"Desc {i}",
                conservative_estimate=float(i * 100_000),
                moderate_estimate=float(i * 200_000),
            )
            for i in range(1, 7)
        ]
        output = BusinessCaseOutput(domain="test.com", value_levers=levers)
        assert len(output.value_levers) == 6

    def test_multiple_timing_signals(self) -> None:
        signals = [
            TimingSignal(
                signal=f"Signal {i}",
                source_module="intel-news",
                urgency="high",
                reason=f"Reason {i}",
            )
            for i in range(5)
        ]
        output = BusinessCaseOutput(domain="test.com", timing_signals=signals)
        assert len(output.timing_signals) == 5

    def test_multiple_customer_proofs(self) -> None:
        proofs = [
            CustomerProof(
                customer_name=f"Customer {i}",
                industry=f"Industry {i}",
                key_metric=f"{i * 10}% lift",
            )
            for i in range(4)
        ]
        output = BusinessCaseOutput(domain="test.com", customer_proofs=proofs)
        assert len(output.customer_proofs) == 4
