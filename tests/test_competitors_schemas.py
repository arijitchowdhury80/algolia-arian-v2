"""Contract tests for intel-competitors schemas -- 30+ pure Pydantic tests, no API/DB calls."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.intel_competitors.schemas import (
    CompetitiveScenario,
    CompetitorsInput,
    CompetitorsOutput,
    ExecutiveSentiment,
    FinancialComparison,
    HiringComparison,
    TechComparison,
    TrafficComparison,
)


# ---------------------------------------------------------------------------
# CompetitorsInput
# ---------------------------------------------------------------------------
class TestCompetitorsInput:
    def test_valid_input(self) -> None:
        inp = CompetitorsInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CompetitorsInput(domain="dell.com", bogus="nope")  # type: ignore[call-arg]

    def test_empty_domain_allowed_by_schema(self) -> None:
        """Domain validation is handled by the validator, not the schema."""
        inp = CompetitorsInput(domain="")
        assert inp.domain == ""


# ---------------------------------------------------------------------------
# TechComparison
# ---------------------------------------------------------------------------
class TestTechComparison:
    def test_valid_full(self) -> None:
        tc = TechComparison(
            company_name="Dell Inc",
            domain="dell.com",
            search_vendor="Algolia",
            ecommerce_platform="Salesforce Commerce Cloud",
            key_technologies=["React", "Algolia", "Salesforce"],
            algolia_detected=True,
        )
        assert tc.company_name == "Dell Inc"
        assert tc.algolia_detected is True
        assert len(tc.key_technologies) == 3

    def test_minimal_defaults(self) -> None:
        tc = TechComparison(company_name="Test", domain="test.com")
        assert tc.search_vendor is None
        assert tc.ecommerce_platform is None
        assert tc.key_technologies == []
        assert tc.algolia_detected is False

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            TechComparison(company_name="X", domain="x.com", bogus="no")  # type: ignore[call-arg]

    def test_search_vendor_none(self) -> None:
        tc = TechComparison(company_name="Test", domain="test.com", search_vendor=None)
        assert tc.search_vendor is None


# ---------------------------------------------------------------------------
# TrafficComparison
# ---------------------------------------------------------------------------
class TestTrafficComparison:
    def test_valid_full(self) -> None:
        tc = TrafficComparison(
            company_name="Dell Inc",
            domain="dell.com",
            monthly_visits=50_000_000,
            bounce_rate=0.35,
            pages_per_visit=4.2,
            organic_search_pct=0.45,
            growth_trend="growing",
        )
        assert tc.monthly_visits == 50_000_000
        assert tc.growth_trend == "growing"

    def test_minimal_defaults(self) -> None:
        tc = TrafficComparison(company_name="Test", domain="test.com")
        assert tc.monthly_visits is None
        assert tc.bounce_rate is None
        assert tc.pages_per_visit is None
        assert tc.organic_search_pct is None
        assert tc.growth_trend == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            TrafficComparison(company_name="X", domain="x.com", extra="no")  # type: ignore[call-arg]

    def test_negative_visits_allowed(self) -> None:
        """Schema does not enforce min value; validator handles this."""
        tc = TrafficComparison(company_name="X", domain="x.com", monthly_visits=-1)
        assert tc.monthly_visits == -1


# ---------------------------------------------------------------------------
# FinancialComparison
# ---------------------------------------------------------------------------
class TestFinancialComparison:
    def test_valid_full(self) -> None:
        fc = FinancialComparison(
            company_name="Dell Inc",
            domain="dell.com",
            revenue=102_300_000_000.0,
            revenue_growth_pct=8.5,
            digital_revenue_pct=45.0,
            market_cap=85_000_000_000.0,
        )
        assert fc.revenue == 102_300_000_000.0
        assert fc.market_cap == 85_000_000_000.0

    def test_minimal_defaults(self) -> None:
        fc = FinancialComparison(company_name="Test", domain="test.com")
        assert fc.revenue is None
        assert fc.revenue_growth_pct is None
        assert fc.digital_revenue_pct is None
        assert fc.market_cap is None

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            FinancialComparison(company_name="X", domain="x.com", extra="no")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# HiringComparison
# ---------------------------------------------------------------------------
class TestHiringComparison:
    def test_valid_full(self) -> None:
        hc = HiringComparison(
            company_name="Dell Inc",
            domain="dell.com",
            total_open_roles=450,
            search_related_roles=12,
            build_vs_buy="buy",
            hiring_trend="accelerating",
        )
        assert hc.total_open_roles == 450
        assert hc.build_vs_buy == "buy"

    def test_minimal_defaults(self) -> None:
        hc = HiringComparison(company_name="Test", domain="test.com")
        assert hc.total_open_roles == 0
        assert hc.search_related_roles == 0
        assert hc.build_vs_buy == ""
        assert hc.hiring_trend == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            HiringComparison(company_name="X", domain="x.com", extra="no")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# ExecutiveSentiment
# ---------------------------------------------------------------------------
class TestExecutiveSentiment:
    def test_valid_full(self) -> None:
        es = ExecutiveSentiment(
            company_name="Dell Inc",
            domain="dell.com",
            key_quotes=["We are investing heavily in digital transformation."],
            digital_commitment_level="high",
            search_mentions=5,
        )
        assert es.digital_commitment_level == "high"
        assert es.search_mentions == 5

    def test_minimal_defaults(self) -> None:
        es = ExecutiveSentiment(company_name="Test", domain="test.com")
        assert es.key_quotes == []
        assert es.digital_commitment_level == "unknown"
        assert es.search_mentions == 0

    @pytest.mark.parametrize("level", ["high", "medium", "low", "unknown"])
    def test_valid_commitment_levels(self, level: str) -> None:
        es = ExecutiveSentiment(
            company_name="X",
            domain="x.com",
            digital_commitment_level=level,  # type: ignore[arg-type]
        )
        assert es.digital_commitment_level == level

    def test_invalid_commitment_level_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExecutiveSentiment(
                company_name="X",
                domain="x.com",
                digital_commitment_level="very_high",  # type: ignore[arg-type]
            )

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ExecutiveSentiment(company_name="X", domain="x.com", extra="no")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# CompetitiveScenario
# ---------------------------------------------------------------------------
class TestCompetitiveScenario:
    @pytest.mark.parametrize("scenario_type", ["golden", "offensive", "defensive", "displacement"])
    def test_valid_scenario_types(self, scenario_type: str) -> None:
        cs = CompetitiveScenario(
            scenario_type=scenario_type,  # type: ignore[arg-type]
            description="Test scenario",
        )
        assert cs.scenario_type == scenario_type

    def test_invalid_scenario_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompetitiveScenario(
                scenario_type="invalid",  # type: ignore[arg-type]
                description="Test",
            )

    def test_full_scenario(self) -> None:
        cs = CompetitiveScenario(
            scenario_type="golden",
            description="Competitor uses Algolia, proving value in vertical.",
            evidence=["HP uses Algolia for search", "Lenovo evaluating Algolia"],
            recommended_play="Reference HP success with Algolia.",
        )
        assert len(cs.evidence) == 2
        assert cs.recommended_play != ""

    def test_minimal_defaults(self) -> None:
        cs = CompetitiveScenario(scenario_type="offensive", description="Basic scenario")
        assert cs.evidence == []
        assert cs.recommended_play == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CompetitiveScenario(
                scenario_type="golden",
                description="Test",
                extra="no",
            )  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# CompetitorsOutput
# ---------------------------------------------------------------------------
class TestCompetitorsOutput:
    def test_minimal_defaults(self) -> None:
        output = CompetitorsOutput(domain="dell.com")
        assert output.domain == "dell.com"
        assert output.tech_comparisons == []
        assert output.golden_angle_competitors == []
        assert output.tech_gaps == []
        assert output.traffic_comparisons == []
        assert output.financial_comparisons == []
        assert output.hiring_comparisons == []
        assert output.executive_sentiments == []
        assert output.competitive_position == "unknown"
        assert output.competitive_pressure == "unknown"
        assert output.competitive_scenario is None
        assert output.competitive_summary == ""
        assert output.top_competitive_angles == []

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CompetitorsOutput(domain="dell.com", bogus="no")  # type: ignore[call-arg]

    @pytest.mark.parametrize("position", ["leader", "fast_follower", "laggard", "unknown"])
    def test_valid_competitive_positions(self, position: str) -> None:
        output = CompetitorsOutput(
            domain="test.com",
            competitive_position=position,  # type: ignore[arg-type]
        )
        assert output.competitive_position == position

    def test_invalid_competitive_position_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompetitorsOutput(
                domain="test.com",
                competitive_position="winner",  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize("pressure", ["increasing", "stable", "decreasing", "unknown"])
    def test_valid_competitive_pressures(self, pressure: str) -> None:
        output = CompetitorsOutput(
            domain="test.com",
            competitive_pressure=pressure,  # type: ignore[arg-type]
        )
        assert output.competitive_pressure == pressure

    def test_invalid_competitive_pressure_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompetitorsOutput(
                domain="test.com",
                competitive_pressure="extreme",  # type: ignore[arg-type]
            )

    def test_full_output(self) -> None:
        output = CompetitorsOutput(
            domain="dell.com",
            tech_comparisons=[
                TechComparison(
                    company_name="Dell Inc",
                    domain="dell.com",
                    search_vendor="Elasticsearch",
                    algolia_detected=False,
                ),
                TechComparison(
                    company_name="HP Inc",
                    domain="hp.com",
                    search_vendor="Algolia",
                    algolia_detected=True,
                ),
            ],
            golden_angle_competitors=["HP Inc"],
            tech_gaps=["Prospect uses Elasticsearch while HP uses Algolia"],
            traffic_comparisons=[
                TrafficComparison(
                    company_name="Dell Inc",
                    domain="dell.com",
                    monthly_visits=50_000_000,
                )
            ],
            financial_comparisons=[
                FinancialComparison(
                    company_name="Dell Inc",
                    domain="dell.com",
                    revenue=102_000_000_000.0,
                )
            ],
            hiring_comparisons=[
                HiringComparison(
                    company_name="Dell Inc",
                    domain="dell.com",
                    total_open_roles=450,
                )
            ],
            executive_sentiments=[
                ExecutiveSentiment(
                    company_name="Dell Inc",
                    domain="dell.com",
                    digital_commitment_level="high",
                )
            ],
            competitive_position="fast_follower",
            competitive_pressure="increasing",
            competitive_scenario=CompetitiveScenario(
                scenario_type="golden",
                description="HP uses Algolia, proving value in the PC OEM vertical.",
                evidence=["HP uses Algolia for product search"],
                recommended_play="Reference HP case study.",
            ),
            competitive_summary="Dell faces increasing competitive pressure.",
            top_competitive_angles=["Golden Angle: HP trusts Algolia"],
        )
        assert len(output.tech_comparisons) == 2
        assert output.competitive_position == "fast_follower"
        assert output.competitive_scenario is not None
        assert output.competitive_scenario.scenario_type == "golden"

    def test_scenario_can_be_none(self) -> None:
        output = CompetitorsOutput(domain="test.com", competitive_scenario=None)
        assert output.competitive_scenario is None

    def test_model_dump_roundtrip(self) -> None:
        output = CompetitorsOutput(
            domain="dell.com",
            tech_comparisons=[
                TechComparison(company_name="Dell", domain="dell.com", algolia_detected=False)
            ],
            competitive_summary="Test summary",
            top_competitive_angles=["Angle 1"],
        )
        data = output.model_dump()
        restored = CompetitorsOutput.model_validate(data)
        assert restored.domain == output.domain
        assert len(restored.tech_comparisons) == 1
        assert restored.competitive_summary == "Test summary"
