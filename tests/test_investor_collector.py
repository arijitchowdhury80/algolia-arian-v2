"""Unit and integration tests for intel-investor collector.

Tests the InvestorCollector's Perplexity and SEC EDGAR integration.

Requires: PERPLEXITY_API_KEY set in .env for Perplexity tests.
SEC EDGAR CIK lookup tests run without any API keys.

Run with: pytest tests/test_investor_collector.py -v
"""

from __future__ import annotations

import os

import pytest

from prism_platform.modules.intel_investor.collector import InvestorCollector

# Marker for tests that require Perplexity API key
requires_perplexity = pytest.mark.skipif(
    not os.environ.get("PERPLEXITY_API_KEY"),
    reason="PERPLEXITY_API_KEY required",
)


# ---------------------------------------------------------------------------
# SEC EDGAR CIK Lookup (free, no API key)
# ---------------------------------------------------------------------------


class TestSECEdgarCIKLookup:
    """Integration tests for SEC EDGAR CIK lookup."""

    @pytest.mark.asyncio
    async def test_cik_lookup_dell(self) -> None:
        """CIK lookup for DELL should return a valid CIK string."""
        collector = InvestorCollector()
        cik = await collector._lookup_cik("DELL")

        assert cik != "", "Expected non-empty CIK for DELL"
        assert len(cik) == 10, f"CIK should be 10 digits, got {len(cik)}: {cik}"
        assert cik.isdigit(), f"CIK should be all digits: {cik}"

    @pytest.mark.asyncio
    async def test_cik_lookup_apple(self) -> None:
        """CIK lookup for AAPL should return a valid CIK string."""
        collector = InvestorCollector()
        cik = await collector._lookup_cik("AAPL")

        assert cik != "", "Expected non-empty CIK for AAPL"
        assert cik.isdigit(), f"CIK should be all digits: {cik}"

    @pytest.mark.asyncio
    async def test_cik_lookup_invalid_ticker(self) -> None:
        """CIK lookup for invalid ticker should return empty string."""
        collector = InvestorCollector()
        cik = await collector._lookup_cik("ZZZZZINVALID")

        assert cik == "", f"Expected empty CIK for invalid ticker, got: {cik}"


# ---------------------------------------------------------------------------
# Perplexity Integration (requires API key)
# ---------------------------------------------------------------------------


@requires_perplexity
class TestPerplexityIntegration:
    """Integration tests for Perplexity API calls."""

    @pytest.mark.asyncio
    async def test_perplexity_call(self) -> None:
        """Basic Perplexity API call should return non-empty text."""
        collector = InvestorCollector()
        text = await collector._call_perplexity(
            "Dell Technologies Q4 FY2025 earnings call highlights summary"
        )

        assert text != "", "Expected non-empty response from Perplexity"
        assert len(text) > 100, f"Expected substantive response, got {len(text)} chars"
        assert collector.perplexity_calls == 1

    @pytest.mark.asyncio
    async def test_collect_earnings_transcripts(self) -> None:
        """Earnings transcript collection for Dell should return at least 1 result."""
        collector = InvestorCollector()
        transcripts = await collector.collect_earnings_transcripts("Dell Technologies", "DELL")

        assert len(transcripts) >= 1, f"Expected at least 1 transcript, got {len(transcripts)}"
        # Each transcript should be substantive
        for t in transcripts:
            assert len(t) > 50, f"Transcript too short: {len(t)} chars"

    @pytest.mark.asyncio
    async def test_collect_youtube_appearances(self) -> None:
        """YouTube appearance search for Dell should return text."""
        collector = InvestorCollector()
        text = await collector.collect_youtube_appearances("Dell Technologies")

        assert isinstance(text, str)
        # May be empty if no results, but should not error
        assert collector.perplexity_calls >= 1

    @pytest.mark.asyncio
    async def test_collect_board_composition(self) -> None:
        """Board composition search for Dell should return text."""
        collector = InvestorCollector()
        text = await collector.collect_board_composition("Dell Technologies")

        assert text != "", "Expected non-empty board composition for Dell"
        assert len(text) > 50, f"Board text too short: {len(text)} chars"

    @pytest.mark.asyncio
    async def test_collect_risk_factors(self) -> None:
        """Risk factor collection for Dell should return text."""
        collector = InvestorCollector()
        text = await collector.collect_risk_factors("Dell Technologies", "DELL")

        assert text != "", "Expected non-empty risk factors for Dell"
        assert len(text) > 50, f"Risk factor text too short: {len(text)} chars"

    @pytest.mark.asyncio
    async def test_collect_private_company_intel(self) -> None:
        """Private company intel collection should return at least 1 section."""
        collector = InvestorCollector()
        intel = await collector.collect_private_company_intel("Stripe", "stripe.com")

        assert len(intel) >= 1, f"Expected at least 1 section, got {len(intel)}"
        for key, value in intel.items():
            assert isinstance(value, str)
            assert len(value) > 0, f"Section '{key}' is empty"


# ---------------------------------------------------------------------------
# Collector state tracking
# ---------------------------------------------------------------------------


class TestCollectorState:
    """Test collector state tracking."""

    def test_initial_perplexity_calls_zero(self) -> None:
        """Perplexity call count should start at zero."""
        collector = InvestorCollector()
        assert collector.perplexity_calls == 0
