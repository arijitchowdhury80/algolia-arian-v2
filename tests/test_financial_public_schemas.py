"""Contract tests for intel-financial-public schemas.

Validates Pydantic models accept valid data, reject invalid data,
and enforce all constraints for financial intelligence output.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.intel_financial_public.schemas import (
    AnalystData,
    AnnualFinancials,
    CompetitorFinancials,
    FinancialPublicInput,
    FinancialPublicOutput,
    InvestorPresentation,
    MarketData,
    SECInsight,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_annual_financials(**overrides: object) -> dict:
    """Build a valid AnnualFinancials dict with optional overrides."""
    base: dict[str, object] = {
        "fiscal_year": "FY2025",
        "revenue": 88400000000.0,
        "net_income": 4500000000.0,
        "gross_margin_pct": 23.5,
        "operating_margin_pct": 6.2,
        "revenue_growth_pct": 8.1,
    }
    base.update(overrides)
    return base


def _make_market_data(**overrides: object) -> dict:
    """Build a valid MarketData dict with optional overrides."""
    base: dict[str, object] = {
        "market_cap": 95000000000.0,
        "stock_price": 135.50,
        "fifty_two_week_high": 179.70,
        "fifty_two_week_low": 91.20,
        "pe_ratio": 21.1,
        "forward_pe": 15.8,
    }
    base.update(overrides)
    return base


def _make_analyst_data(**overrides: object) -> dict:
    """Build a valid AnalystData dict with optional overrides."""
    base: dict[str, object] = {
        "recommendation": "Buy",
        "target_price": 160.0,
        "number_of_analysts": 25,
    }
    base.update(overrides)
    return base


def _make_sec_insight(**overrides: object) -> dict:
    """Build a valid SECInsight dict with optional overrides."""
    base: dict[str, object] = {
        "filing_type": "10-K",
        "filing_date": "2025-03-15",
        "filing_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=DELL",
        "digital_revenue_pct": 35.0,
        "technology_mentions": ["AI", "search", "personalization"],
        "key_excerpts": ["We are investing heavily in AI-powered solutions."],
        "management_discussion_summary": "Management highlighted digital transformation as a key priority.",
    }
    base.update(overrides)
    return base


def _make_investor_presentation(**overrides: object) -> dict:
    """Build a valid InvestorPresentation dict with optional overrides."""
    base: dict[str, object] = {
        "title": "Dell Technologies Investor Day 2025",
        "date": "2025-09-15",
        "url": "https://investors.delltechnologies.com/presentations/2025",
        "strategic_priorities": ["AI infrastructure", "Cloud services"],
        "digital_commitments": ["Double digital revenue by FY2027"],
        "technology_roadmap": ["AI Factory expansion", "Edge computing"],
        "search_mentions": ["Enterprise search powered by AI"],
        "key_quotes": ["We see AI as the next major growth driver - Michael Dell"],
    }
    base.update(overrides)
    return base


def _make_competitor_financials(**overrides: object) -> dict:
    """Build a valid CompetitorFinancials dict with optional overrides."""
    base: dict[str, object] = {
        "company_name": "HP Inc.",
        "ticker": "HPQ",
        "revenue": 54000000000.0,
        "revenue_growth_pct": 3.2,
        "market_cap": 35000000000.0,
        "gross_margin_pct": 21.0,
    }
    base.update(overrides)
    return base


def _make_full_output(**overrides: object) -> dict:
    """Build a valid FinancialPublicOutput dict with optional overrides."""
    base: dict[str, object] = {
        "domain": "dell.com",
        "ticker": "DELL",
        "annual_financials": [
            _make_annual_financials(fiscal_year="FY2023", revenue=85000000000.0),
            _make_annual_financials(fiscal_year="FY2024", revenue=86500000000.0),
            _make_annual_financials(fiscal_year="FY2025", revenue=88400000000.0),
        ],
        "market_data": _make_market_data(),
        "analyst_data": _make_analyst_data(),
        "sec_insights": [_make_sec_insight()],
        "investor_presentations": [_make_investor_presentation()],
        "competitor_financials": [_make_competitor_financials()],
        "comparative_summary": (
            "Dell Technologies leads its peer group in revenue scale at $88.4B, "
            "with 8.1% YoY growth outpacing HP's 3.2%. Market cap is significantly "
            "higher at $95B vs HP's $35B."
        ),
        "skipped": False,
        "skip_reason": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# FinancialPublicInput
# ---------------------------------------------------------------------------


class TestFinancialPublicInput:
    def test_valid_input(self) -> None:
        inp = FinancialPublicInput(domain="dell.com", ticker="DELL")
        assert inp.domain == "dell.com"
        assert inp.ticker == "DELL"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            FinancialPublicInput(domain="dell.com", ticker="DELL", extra="nope")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# AnnualFinancials
# ---------------------------------------------------------------------------


class TestAnnualFinancials:
    def test_valid_annual_financials(self) -> None:
        af = AnnualFinancials.model_validate(_make_annual_financials())
        assert af.fiscal_year == "FY2025"
        assert af.revenue == 88400000000.0
        assert af.gross_margin_pct == 23.5

    def test_all_optional_fields(self) -> None:
        af = AnnualFinancials(fiscal_year="FY2025")
        assert af.revenue is None
        assert af.net_income is None
        assert af.gross_margin_pct is None
        assert af.operating_margin_pct is None
        assert af.revenue_growth_pct is None

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            AnnualFinancials.model_validate({**_make_annual_financials(), "ebitda": 999})


# ---------------------------------------------------------------------------
# MarketData
# ---------------------------------------------------------------------------


class TestMarketData:
    def test_valid_market_data(self) -> None:
        md = MarketData.model_validate(_make_market_data())
        assert md.market_cap == 95000000000.0
        assert md.stock_price == 135.50

    def test_all_optional_fields(self) -> None:
        md = MarketData()
        assert md.market_cap is None
        assert md.stock_price is None
        assert md.pe_ratio is None

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            MarketData.model_validate({**_make_market_data(), "volume": 1000000})


# ---------------------------------------------------------------------------
# AnalystData
# ---------------------------------------------------------------------------


class TestAnalystData:
    def test_valid_analyst_data(self) -> None:
        ad = AnalystData.model_validate(_make_analyst_data())
        assert ad.recommendation == "Buy"
        assert ad.target_price == 160.0
        assert ad.number_of_analysts == 25

    def test_all_optional_fields(self) -> None:
        ad = AnalystData()
        assert ad.recommendation is None
        assert ad.target_price is None
        assert ad.number_of_analysts is None


# ---------------------------------------------------------------------------
# SECInsight
# ---------------------------------------------------------------------------


class TestSECInsight:
    def test_valid_sec_insight(self) -> None:
        si = SECInsight.model_validate(_make_sec_insight())
        assert si.filing_type == "10-K"
        assert si.filing_date == "2025-03-15"
        assert "AI" in si.technology_mentions

    def test_filing_type_literal(self) -> None:
        # Valid types
        SECInsight.model_validate(_make_sec_insight(filing_type="10-K"))
        SECInsight.model_validate(_make_sec_insight(filing_type="10-Q"))

        # Invalid type
        with pytest.raises(ValidationError):
            SECInsight.model_validate(_make_sec_insight(filing_type="8-K"))

    def test_defaults(self) -> None:
        si = SECInsight(filing_type="10-K", filing_date="2025-01-01")
        assert si.filing_url is None
        assert si.technology_mentions == []
        assert si.key_excerpts == []
        assert si.management_discussion_summary == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            SECInsight.model_validate({**_make_sec_insight(), "revenue": 999})


# ---------------------------------------------------------------------------
# InvestorPresentation
# ---------------------------------------------------------------------------


class TestInvestorPresentation:
    def test_valid_presentation(self) -> None:
        ip = InvestorPresentation.model_validate(_make_investor_presentation())
        assert ip.title == "Dell Technologies Investor Day 2025"
        assert len(ip.strategic_priorities) == 2

    def test_defaults(self) -> None:
        ip = InvestorPresentation(title="Test", date="2025-01-01")
        assert ip.url is None
        assert ip.strategic_priorities == []
        assert ip.digital_commitments == []
        assert ip.search_mentions == []

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            InvestorPresentation.model_validate(
                {**_make_investor_presentation(), "slides_count": 50}
            )


# ---------------------------------------------------------------------------
# CompetitorFinancials
# ---------------------------------------------------------------------------


class TestCompetitorFinancials:
    def test_valid_competitor_financials(self) -> None:
        cf = CompetitorFinancials.model_validate(_make_competitor_financials())
        assert cf.company_name == "HP Inc."
        assert cf.ticker == "HPQ"
        assert cf.revenue == 54000000000.0

    def test_optional_fields(self) -> None:
        cf = CompetitorFinancials(company_name="Test Corp", ticker="TST")
        assert cf.revenue is None
        assert cf.revenue_growth_pct is None
        assert cf.market_cap is None
        assert cf.gross_margin_pct is None

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CompetitorFinancials.model_validate(
                {**_make_competitor_financials(), "pe_ratio": 15.0}
            )


# ---------------------------------------------------------------------------
# FinancialPublicOutput
# ---------------------------------------------------------------------------


class TestFinancialPublicOutput:
    def test_valid_full_output(self) -> None:
        output = FinancialPublicOutput.model_validate(_make_full_output())
        assert output.domain == "dell.com"
        assert output.ticker == "DELL"
        assert len(output.annual_financials) == 3
        assert output.market_data is not None
        assert output.analyst_data is not None
        assert len(output.sec_insights) == 1
        assert len(output.investor_presentations) == 1
        assert len(output.competitor_financials) == 1
        assert output.comparative_summary != ""
        assert output.skipped is False

    def test_minimal_defaults(self) -> None:
        output = FinancialPublicOutput(domain="dell.com", ticker="DELL")
        assert output.annual_financials == []
        assert output.market_data is None
        assert output.analyst_data is None
        assert output.sec_insights == []
        assert output.investor_presentations == []
        assert output.competitor_financials == []
        assert output.comparative_summary == ""
        assert output.skipped is False
        assert output.skip_reason is None

    def test_skipped_output(self) -> None:
        output = FinancialPublicOutput(
            domain="private.com",
            ticker="",
            skipped=True,
            skip_reason="Company is private",
        )
        assert output.skipped is True
        assert output.skip_reason == "Company is private"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            FinancialPublicOutput.model_validate(
                {**_make_full_output(), "secret_field": "no"}
            )

    def test_revenue_is_float(self) -> None:
        output = FinancialPublicOutput.model_validate(_make_full_output())
        assert isinstance(output.annual_financials[0].revenue, float)

    def test_nested_model_validation(self) -> None:
        """Ensure nested models are validated -- invalid filing_type should fail."""
        bad_data = _make_full_output()
        bad_data["sec_insights"] = [{"filing_type": "8-K", "filing_date": "2025-01-01"}]
        with pytest.raises(ValidationError):
            FinancialPublicOutput.model_validate(bad_data)
