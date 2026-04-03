"""Contract tests for intel-financial-private schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.intel_financial_private.schemas import (
    CompetitorRevenueEstimate,
    EmployeeRevenueModel,
    FinancialPrivateInput,
    FinancialPrivateOutput,
    FundingData,
    RevenueEstimate,
    RevenueWaterfall,
)


class TestFinancialPrivateInput:
    """Tests for FinancialPrivateInput schema."""

    def test_valid_input(self) -> None:
        inp = FinancialPrivateInput(domain="example.com")
        assert inp.domain == "example.com"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            FinancialPrivateInput(domain="example.com", bogus="nope")  # type: ignore[call-arg]


class TestRevenueEstimate:
    """Tests for RevenueEstimate schema."""

    def test_valid_full_estimate(self) -> None:
        est = RevenueEstimate(
            source_name="IDC Market Report",
            methodology="Extracted from IDC SaaS market report 2025",
            estimated_revenue=50_000_000.0,
            confidence="medium",
            evidence="IDC estimates Company X at $50M ARR in 2025",
            evidence_url="https://idc.com/report/123",
            evidence_tier="WEBSEARCH",
        )
        assert est.estimated_revenue == 50_000_000.0
        assert est.confidence == "medium"
        assert est.evidence_tier == "WEBSEARCH"

    def test_minimal_estimate(self) -> None:
        est = RevenueEstimate(
            source_name="News article",
            methodology="Mentioned in TechCrunch article",
        )
        assert est.estimated_revenue is None
        assert est.confidence == "low"
        assert est.evidence_tier == "ESTIMATE"

    def test_rejects_invalid_confidence(self) -> None:
        with pytest.raises(ValidationError):
            RevenueEstimate(
                source_name="test",
                methodology="test",
                confidence="very_high",  # type: ignore[arg-type]
            )

    def test_rejects_invalid_evidence_tier(self) -> None:
        with pytest.raises(ValidationError):
            RevenueEstimate(
                source_name="test",
                methodology="test",
                evidence_tier="NO_SOURCE",  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize("tier", ["VERIFIED", "WEBFETCH", "WEBSEARCH", "ESTIMATE"])
    def test_all_valid_evidence_tiers(self, tier: str) -> None:
        est = RevenueEstimate(
            source_name="test",
            methodology="test",
            evidence_tier=tier,  # type: ignore[arg-type]
        )
        assert est.evidence_tier == tier

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            RevenueEstimate(
                source_name="test",
                methodology="test",
                extra_field="bad",  # type: ignore[call-arg]
            )


class TestFundingData:
    """Tests for FundingData schema."""

    def test_valid_full_funding(self) -> None:
        fd = FundingData(
            total_funding=150_000_000.0,
            last_round="Series D",
            last_round_amount=50_000_000.0,
            last_round_date="2024-03-15",
            lead_investor="Sequoia Capital",
            valuation=800_000_000.0,
            source="Crunchbase",
        )
        assert fd.total_funding == 150_000_000.0
        assert fd.last_round == "Series D"

    def test_all_none(self) -> None:
        fd = FundingData()
        assert fd.total_funding is None
        assert fd.last_round is None
        assert fd.source == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            FundingData(extra="bad")  # type: ignore[call-arg]


class TestEmployeeRevenueModel:
    """Tests for EmployeeRevenueModel schema."""

    def test_valid_model(self) -> None:
        model = EmployeeRevenueModel(
            employee_count=500,
            revenue_per_employee=200_000.0,
            estimated_revenue=100_000_000.0,
            vertical_benchmark="SaaS average: $200K/employee",
            confidence="low",
        )
        assert model.estimated_revenue == 100_000_000.0

    def test_defaults(self) -> None:
        model = EmployeeRevenueModel()
        assert model.employee_count is None
        assert model.confidence == "low"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            EmployeeRevenueModel(bogus="no")  # type: ignore[call-arg]


class TestCompetitorRevenueEstimate:
    """Tests for CompetitorRevenueEstimate schema."""

    def test_valid_competitor(self) -> None:
        comp = CompetitorRevenueEstimate(
            company_name="Rival Inc",
            domain="rival.com",
            estimated_revenue=75_000_000.0,
            methodology="Public filing",
            confidence="high",
        )
        assert comp.company_name == "Rival Inc"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CompetitorRevenueEstimate(
                company_name="test",
                domain="test.com",
                extra="bad",  # type: ignore[call-arg]
            )


class TestRevenueWaterfall:
    """Tests for RevenueWaterfall schema."""

    def test_valid_waterfall(self) -> None:
        wf = RevenueWaterfall(
            estimates=[
                RevenueEstimate(
                    source_name="IDC",
                    methodology="Market report",
                    estimated_revenue=50_000_000.0,
                    confidence="medium",
                    evidence_tier="WEBSEARCH",
                ),
                RevenueEstimate(
                    source_name="News",
                    methodology="TechCrunch article",
                    estimated_revenue=60_000_000.0,
                    confidence="low",
                    evidence_tier="WEBSEARCH",
                ),
            ],
            best_estimate=55_000_000.0,
            best_estimate_confidence="medium",
            best_estimate_methodology="Median of IDC and News estimates",
            range_low=50_000_000.0,
            range_high=60_000_000.0,
        )
        assert wf.best_estimate == 55_000_000.0
        assert len(wf.estimates) == 2

    def test_empty_waterfall(self) -> None:
        wf = RevenueWaterfall()
        assert wf.estimates == []
        assert wf.best_estimate is None

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            RevenueWaterfall(bogus="no")  # type: ignore[call-arg]


class TestFinancialPrivateOutput:
    """Tests for FinancialPrivateOutput schema."""

    def test_valid_full_output(self) -> None:
        output = FinancialPrivateOutput(
            domain="example.com",
            revenue_waterfall=RevenueWaterfall(
                estimates=[
                    RevenueEstimate(
                        source_name="IDC",
                        methodology="Market report",
                        estimated_revenue=50_000_000.0,
                        evidence_tier="WEBSEARCH",
                    ),
                ],
                best_estimate=50_000_000.0,
            ),
            funding_data=FundingData(total_funding=100_000_000.0),
            employee_revenue_model=EmployeeRevenueModel(employee_count=300),
            competitor_estimates=[
                CompetitorRevenueEstimate(
                    company_name="Rival",
                    domain="rival.com",
                    estimated_revenue=70_000_000.0,
                ),
            ],
            comparative_summary="Estimated at $50M, rival at $70M.",
        )
        assert output.domain == "example.com"
        assert output.skipped is False

    def test_skipped_output(self) -> None:
        output = FinancialPrivateOutput(
            domain="dell.com",
            skipped=True,
            skip_reason="Company is public (has ticker). Use intel-financial-public instead.",
        )
        assert output.skipped is True
        assert output.skip_reason is not None
        assert output.revenue_waterfall is None

    def test_minimal_defaults(self) -> None:
        output = FinancialPrivateOutput(domain="example.com")
        assert output.revenue_waterfall is None
        assert output.funding_data is None
        assert output.competitor_estimates == []
        assert output.skipped is False

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            FinancialPrivateOutput(domain="example.com", bogus="no")  # type: ignore[call-arg]
