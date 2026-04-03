"""Collector tests for intel-financial-public module.

Tests Yahoo Finance data extraction, SEC EDGAR search, and the validator.
Uses real API calls where possible (yfinance and SEC EDGAR are free).

Run with: pytest tests/test_financial_public_collector.py -v
"""

from __future__ import annotations

import pytest

from prism_platform.core.types import Source
from prism_platform.modules.intel_financial_public.collector import FinancialCollector
from prism_platform.modules.intel_financial_public.schemas import (
    FinancialPublicOutput,
    MarketData,
)
from prism_platform.modules.intel_financial_public.validator import validate_output


# ---------------------------------------------------------------------------
# Yahoo Finance -- real API calls (free, no key needed)
# ---------------------------------------------------------------------------


class TestYahooFinanceCollector:
    """Tests using real Yahoo Finance API calls."""

    @pytest.mark.asyncio
    async def test_collect_dell_financials(self) -> None:
        """Collect Yahoo Finance data for DELL -- real API call."""
        collector = FinancialCollector()
        annual, market, analyst = await collector.collect_yahoo_finance("DELL")

        # Should have at least 2 years of annual data
        assert len(annual) >= 2, f"Only {len(annual)} years of annual financials for DELL"

        # Most recent year should have revenue
        assert annual[-1].revenue is not None, "Most recent year has no revenue"
        assert annual[-1].revenue > 0, "Revenue should be positive"

        # Market data should exist
        assert market is not None, "No market data for DELL"
        assert market.market_cap is not None, "No market cap for DELL"
        assert market.market_cap > 0, "Market cap should be positive"
        assert market.stock_price is not None, "No stock price for DELL"

        # Analyst data should exist for major companies
        assert analyst is not None, "No analyst data for DELL"

    @pytest.mark.asyncio
    async def test_collect_invalid_ticker(self) -> None:
        """Invalid ticker should return empty results, not raise."""
        collector = FinancialCollector()
        annual, market, analyst = await collector.collect_yahoo_finance("XYZNOTREAL999")

        # Should not raise, just return empty/None
        assert len(annual) == 0
        # market and analyst may be None or have None fields

    @pytest.mark.asyncio
    async def test_annual_financials_have_margins(self) -> None:
        """Verify margin calculations are populated for DELL."""
        collector = FinancialCollector()
        annual, _, _ = await collector.collect_yahoo_finance("DELL")

        # At least one year should have gross margin
        has_gross_margin = any(af.gross_margin_pct is not None for af in annual)
        assert has_gross_margin, "No gross margin data found for any year"

    @pytest.mark.asyncio
    async def test_revenue_growth_calculation(self) -> None:
        """Verify YoY revenue growth is calculated when multiple years present."""
        collector = FinancialCollector()
        annual, _, _ = await collector.collect_yahoo_finance("DELL")

        if len(annual) >= 2:
            # At least one year (not the first) should have growth
            has_growth = any(
                af.revenue_growth_pct is not None
                for af in annual[1:]  # Skip first year (no prior year)
            )
            assert has_growth, "No revenue growth calculated despite multiple years"


# ---------------------------------------------------------------------------
# SEC EDGAR -- real API calls (free, no key needed)
# ---------------------------------------------------------------------------


class TestSECEdgarCollector:
    """Tests using real SEC EDGAR API calls."""

    @pytest.mark.asyncio
    async def test_collect_dell_sec_filings(self) -> None:
        """Search SEC EDGAR for Dell Technologies filings -- real API call."""
        collector = FinancialCollector()
        insights = await collector.collect_sec_filings("Dell Technologies", "DELL")

        # Dell should have recent filings
        assert len(insights) >= 1, "No SEC filings found for Dell Technologies"

        # Verify filing structure
        for insight in insights:
            assert insight.filing_type in ("10-K", "10-Q")
            assert insight.filing_date, "Filing date should not be empty"

    @pytest.mark.asyncio
    async def test_collect_unknown_company(self) -> None:
        """Unknown company should return empty list, not raise."""
        collector = FinancialCollector()
        insights = await collector.collect_sec_filings("XYZNotARealCompany999", "XYZFAKE")

        # Should return empty, not raise
        assert isinstance(insights, list)


# ---------------------------------------------------------------------------
# Competitor Financials -- real API calls
# ---------------------------------------------------------------------------


class TestCompetitorFinancialsCollector:
    """Tests competitor financial data collection."""

    @pytest.mark.asyncio
    async def test_collect_competitor_financials(self) -> None:
        """Collect basic financials for HP and Lenovo -- real API calls."""
        collector = FinancialCollector()
        competitors = [
            {"company_name": "HP Inc.", "ticker": "HPQ"},
            {"company_name": "Lenovo Group", "ticker": "LNVGY"},
        ]
        results = await collector.collect_competitor_financials(competitors)

        assert len(results) >= 1, "Should collect at least 1 competitor"
        for cf in results:
            assert cf.ticker, "Competitor ticker should not be empty"
            assert cf.company_name, "Competitor name should not be empty"

    @pytest.mark.asyncio
    async def test_empty_ticker_skipped(self) -> None:
        """Competitors with empty ticker should be skipped."""
        collector = FinancialCollector()
        competitors = [
            {"company_name": "No Ticker Corp", "ticker": ""},
        ]
        results = await collector.collect_competitor_financials(competitors)
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Validator -- synthetic data
# ---------------------------------------------------------------------------


class TestValidator:
    """Test the validator with synthetic data."""

    def test_valid_output_passes(self) -> None:
        """Fully populated output should pass all checks."""
        from prism_platform.modules.intel_financial_public.schemas import (
            AnalystData,
            AnnualFinancials,
            CompetitorFinancials,
            SECInsight,
        )

        output = FinancialPublicOutput(
            domain="dell.com",
            ticker="DELL",
            annual_financials=[
                AnnualFinancials(fiscal_year="FY2024", revenue=86500000000.0),
                AnnualFinancials(fiscal_year="FY2025", revenue=88400000000.0),
            ],
            market_data=MarketData(market_cap=95000000000.0, stock_price=135.50),
            analyst_data=AnalystData(recommendation="Buy"),
            sec_insights=[
                SECInsight(filing_type="10-K", filing_date="2025-03-15"),
            ],
            competitor_financials=[
                CompetitorFinancials(company_name="HP", ticker="HPQ", revenue=54000000000.0),
            ],
            comparative_summary="Dell leads in revenue scale.",
        )
        sources = [
            Source(
                field="annual_financials",
                value="Yahoo Finance",
                tier="VERIFIED",
                source_label="Yahoo Finance",
            ),
        ]
        result = validate_output(output, sources, expected_domain="dell.com", expected_ticker="DELL")
        assert result.passed is True
        assert result.checks_run == 9

    def test_skipped_output_passes(self) -> None:
        """Skipped output with skip_reason should pass."""
        output = FinancialPublicOutput(
            domain="private.com",
            ticker="",
            skipped=True,
            skip_reason="Company is private",
        )
        result = validate_output(output, [])
        assert result.passed is True
        assert result.checks_run == 1
        assert result.checks_passed == 1

    def test_skipped_without_reason_fails(self) -> None:
        """Skipped output without skip_reason should fail."""
        output = FinancialPublicOutput(
            domain="private.com",
            ticker="",
            skipped=True,
            skip_reason=None,
        )
        result = validate_output(output, [])
        assert result.passed is False
        assert any("skip_reason" in e for e in result.errors)

    def test_too_few_annual_years_fails(self) -> None:
        """Less than 2 years of financials should fail."""
        from prism_platform.modules.intel_financial_public.schemas import AnnualFinancials

        output = FinancialPublicOutput(
            domain="dell.com",
            ticker="DELL",
            annual_financials=[
                AnnualFinancials(fiscal_year="FY2025", revenue=88400000000.0),
            ],
            market_data=MarketData(market_cap=95000000000.0),
        )
        result = validate_output(output, [], expected_domain="dell.com", expected_ticker="DELL")
        assert result.passed is False
        assert any("annual financials" in e for e in result.errors)

    def test_no_market_data_fails(self) -> None:
        """Missing market_data should fail."""
        from prism_platform.modules.intel_financial_public.schemas import AnnualFinancials

        output = FinancialPublicOutput(
            domain="dell.com",
            ticker="DELL",
            annual_financials=[
                AnnualFinancials(fiscal_year="FY2024"),
                AnnualFinancials(fiscal_year="FY2025"),
            ],
            market_data=None,
        )
        result = validate_output(output, [], expected_domain="dell.com", expected_ticker="DELL")
        assert result.passed is False
        assert any("market_data" in e for e in result.errors)

    def test_domain_mismatch_fails(self) -> None:
        """Domain mismatch should fail."""
        output = FinancialPublicOutput(
            domain="wrong.com",
            ticker="DELL",
        )
        result = validate_output(output, [], expected_domain="dell.com")
        assert result.passed is False
        assert any("domain mismatch" in e for e in result.errors)

    def test_ticker_mismatch_fails(self) -> None:
        """Ticker mismatch should fail."""
        output = FinancialPublicOutput(
            domain="dell.com",
            ticker="WRONG",
        )
        result = validate_output(output, [], expected_ticker="DELL")
        assert result.passed is False
        assert any("ticker mismatch" in e for e in result.errors)

    def test_no_sec_insights_is_warning(self) -> None:
        """Missing SEC insights should be a warning, not an error."""
        from prism_platform.modules.intel_financial_public.schemas import AnnualFinancials

        output = FinancialPublicOutput(
            domain="dell.com",
            ticker="DELL",
            annual_financials=[
                AnnualFinancials(fiscal_year="FY2024"),
                AnnualFinancials(fiscal_year="FY2025"),
            ],
            market_data=MarketData(market_cap=95000000000.0),
            sec_insights=[],
        )
        sources = [
            Source(
                field="test",
                value="test",
                tier="VERIFIED",
                source_label="test",
            ),
        ]
        result = validate_output(output, sources, expected_domain="dell.com", expected_ticker="DELL")
        # SEC insights missing is a warning, not an error
        assert any("SEC" in w for w in result.warnings)

    def test_competitors_without_summary_is_warning(self) -> None:
        """Competitors present but no comparative summary should be a warning."""
        from prism_platform.modules.intel_financial_public.schemas import (
            AnnualFinancials,
            CompetitorFinancials,
            SECInsight,
        )

        output = FinancialPublicOutput(
            domain="dell.com",
            ticker="DELL",
            annual_financials=[
                AnnualFinancials(fiscal_year="FY2024"),
                AnnualFinancials(fiscal_year="FY2025"),
            ],
            market_data=MarketData(market_cap=95000000000.0),
            sec_insights=[SECInsight(filing_type="10-K", filing_date="2025-03-15")],
            competitor_financials=[
                CompetitorFinancials(company_name="HP", ticker="HPQ"),
            ],
            comparative_summary="",
        )
        sources = [
            Source(field="test", value="test", tier="VERIFIED", source_label="test"),
        ]
        result = validate_output(output, sources, expected_domain="dell.com", expected_ticker="DELL")
        assert any("comparative_summary" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# safe_float utility
# ---------------------------------------------------------------------------


class TestSafeFloat:
    """Test the _safe_float utility."""

    def test_none_returns_none(self) -> None:
        assert FinancialCollector._safe_float(None) is None

    def test_valid_float(self) -> None:
        assert FinancialCollector._safe_float(42.5) == 42.5

    def test_valid_int(self) -> None:
        assert FinancialCollector._safe_float(42) == 42.0

    def test_string_number(self) -> None:
        assert FinancialCollector._safe_float("42.5") == 42.5

    def test_invalid_string(self) -> None:
        assert FinancialCollector._safe_float("not_a_number") is None

    def test_nan_returns_none(self) -> None:
        assert FinancialCollector._safe_float(float("nan")) is None

    def test_inf_returns_none(self) -> None:
        assert FinancialCollector._safe_float(float("inf")) is None
