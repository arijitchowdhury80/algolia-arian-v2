"""End-to-end integration tests for intel-financial-public module.

These tests run the full module pipeline against dell.com with real API calls.

Requires: PERPLEXITY_API_KEY and GEMINI_API_KEY set in .env for enricher tests.
Yahoo Finance and SEC EDGAR tests run without any API keys.

Run with: pytest tests/test_financial_public_integration.py -v
"""

from __future__ import annotations

import os

import pytest

from prism_platform.core.module import ExecutionContext
from prism_platform.modules.intel_financial_public.collector import FinancialCollector
from prism_platform.modules.intel_financial_public.module import FinancialPublicModule
from prism_platform.modules.intel_financial_public.schemas import FinancialPublicOutput
from prism_platform.modules.intel_financial_public.validator import validate_output

# Marker for tests that require Perplexity + Gemini API keys
requires_api_keys = pytest.mark.skipif(
    not (os.environ.get("PERPLEXITY_API_KEY") and os.environ.get("GEMINI_API_KEY")),
    reason="PERPLEXITY_API_KEY and GEMINI_API_KEY required",
)


def _make_public_context() -> ExecutionContext:
    """Build a test ExecutionContext for dell.com (public company)."""
    return ExecutionContext(
        audit_id="test-audit-fin-001",
        account_id="00000000-0000-0000-0000-000000000001",
        domain="dell.com",
        company_name="Dell Technologies",
        ticker="DELL",
        is_private=False,
    )


def _make_private_context() -> ExecutionContext:
    """Build a test ExecutionContext for a private company."""
    return ExecutionContext(
        audit_id="test-audit-fin-002",
        account_id="00000000-0000-0000-0000-000000000002",
        domain="stripe.com",
        company_name="Stripe Inc.",
        ticker=None,
        is_private=True,
    )


# ---------------------------------------------------------------------------
# Module skip behavior
# ---------------------------------------------------------------------------


class TestModuleSkipBehavior:
    """Test that the module correctly skips private companies."""

    @pytest.mark.asyncio
    async def test_skip_private_company(self) -> None:
        """Private company should return skipped result immediately."""
        module = FinancialPublicModule()
        context = _make_private_context()
        result = await module.execute(context)

        assert result.status == "success"
        assert result.module_name == "intel-financial-public"

        output = FinancialPublicOutput.model_validate(result.output)
        assert output.skipped is True
        assert output.skip_reason is not None
        assert "private" in output.skip_reason.lower() or "ticker" in output.skip_reason.lower()

    @pytest.mark.asyncio
    async def test_skip_no_ticker(self) -> None:
        """Company with no ticker should be skipped."""
        module = FinancialPublicModule()
        context = ExecutionContext(
            audit_id="test-audit-fin-003",
            account_id="00000000-0000-0000-0000-000000000003",
            domain="example.com",
            company_name="Example Corp",
            ticker=None,
            is_private=False,
        )
        result = await module.execute(context)

        assert result.status == "success"
        output = FinancialPublicOutput.model_validate(result.output)
        assert output.skipped is True
        assert output.skip_reason is not None

    @pytest.mark.asyncio
    async def test_skipped_output_validates(self) -> None:
        """Skipped output should pass validation."""
        module = FinancialPublicModule()
        context = _make_private_context()
        result = await module.execute(context)

        validation = await module.validate(result)
        assert validation.passed is True
        assert validation.checks_run == 1


# ---------------------------------------------------------------------------
# Yahoo Finance collection (free, no API key)
# ---------------------------------------------------------------------------


class TestYahooFinanceIntegration:
    """Integration tests for Yahoo Finance data collection."""

    @pytest.mark.asyncio
    async def test_full_yahoo_finance_pipeline(self) -> None:
        """Collect all Yahoo Finance data for DELL and verify structure."""
        collector = FinancialCollector()
        annual, market, analyst = await collector.collect_yahoo_finance("DELL")

        # Annual financials
        assert len(annual) >= 2, f"Expected >= 2 years, got {len(annual)}"
        for af in annual:
            assert af.fiscal_year, "fiscal_year should not be empty"
            # Revenue should be populated for most years
            if af.revenue is not None:
                assert af.revenue > 0, f"Revenue should be positive: {af.revenue}"

        # Market data
        assert market is not None, "Market data should not be None for DELL"
        assert market.market_cap is not None and market.market_cap > 0
        assert market.stock_price is not None and market.stock_price > 0

        # Analyst data
        if analyst is not None:
            if analyst.recommendation is not None:
                assert isinstance(analyst.recommendation, str)
                assert len(analyst.recommendation) > 0

    @pytest.mark.asyncio
    async def test_apple_as_second_ticker(self) -> None:
        """Verify collection works for AAPL too -- not just DELL."""
        collector = FinancialCollector()
        annual, market, analyst = await collector.collect_yahoo_finance("AAPL")

        assert len(annual) >= 2, f"Expected >= 2 years for AAPL, got {len(annual)}"
        assert market is not None, "Market data should not be None for AAPL"
        assert market.market_cap is not None


# ---------------------------------------------------------------------------
# SEC EDGAR integration (free, no API key)
# ---------------------------------------------------------------------------


class TestSECEdgarIntegration:
    """Integration tests for SEC EDGAR filing search."""

    @pytest.mark.asyncio
    async def test_sec_edgar_dell_filings(self) -> None:
        """Search SEC EDGAR for Dell Technologies filings."""
        collector = FinancialCollector()
        insights = await collector.collect_sec_filings("Dell Technologies", "DELL")

        # Dell should have filings
        assert len(insights) >= 1, "Expected at least 1 SEC filing for Dell"

        for insight in insights:
            assert insight.filing_type in ("10-K", "10-Q")
            assert insight.filing_date, "Filing date should be set"


# ---------------------------------------------------------------------------
# Validator integration
# ---------------------------------------------------------------------------


class TestValidatorIntegration:
    """Test validation with real Yahoo Finance data."""

    @pytest.mark.asyncio
    async def test_real_data_passes_validation(self) -> None:
        """Yahoo Finance data for DELL should produce a validatable output."""
        collector = FinancialCollector()
        annual, market, analyst = await collector.collect_yahoo_finance("DELL")
        sec_insights = await collector.collect_sec_filings("Dell Technologies", "DELL")

        from prism_platform.core.types import Source

        output = FinancialPublicOutput(
            domain="dell.com",
            ticker="DELL",
            annual_financials=annual,
            market_data=market,
            analyst_data=analyst,
            sec_insights=sec_insights,
        )

        sources = [
            Source(
                field="annual_financials",
                value="Yahoo Finance data",
                tier="VERIFIED",
                source_label="Yahoo Finance",
            ),
        ]

        result = validate_output(
            output, sources, expected_domain="dell.com", expected_ticker="DELL"
        )

        # Should pass core checks (annual data + market data)
        assert result.checks_run >= 8, f"Expected >= 8 checks, got {result.checks_run}"
        # Log any failures for debugging
        if not result.passed:
            for err in result.errors:
                print(f"  ERROR: {err}")
            for warn in result.warnings:
                print(f"  WARNING: {warn}")


# ---------------------------------------------------------------------------
# Module health check
# ---------------------------------------------------------------------------


@requires_api_keys
class TestModuleHealthCheck:
    """Test module health check."""

    @pytest.mark.asyncio
    async def test_health_check_passes(self) -> None:
        """Health check should pass when API keys are set."""
        module = FinancialPublicModule()
        healthy = await module.health_check()
        assert healthy is True, (
            "Health check failed -- check PERPLEXITY_API_KEY and GEMINI_API_KEY in .env"
        )


# ---------------------------------------------------------------------------
# Module metadata
# ---------------------------------------------------------------------------


class TestModuleMetadata:
    """Test module class properties."""

    def test_module_name(self) -> None:
        module = FinancialPublicModule()
        assert module.name == "intel-financial-public"

    def test_module_version(self) -> None:
        module = FinancialPublicModule()
        assert module.version == "0.1.0"

    def test_module_dependencies(self) -> None:
        module = FinancialPublicModule()
        assert "intel-company" in module.dependencies

    def test_module_requires_llm(self) -> None:
        module = FinancialPublicModule()
        assert module.requires_llm is True

    def test_module_timeout(self) -> None:
        module = FinancialPublicModule()
        assert module.timeout_seconds == 300
