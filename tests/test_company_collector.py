"""Integration tests for intel-company collector -- real Perplexity API calls.

These tests call the real Perplexity API with dell.com as the test domain.
They require PERPLEXITY_API_KEY to be set in .env.

Run with: pytest tests/test_company_collector.py -v
"""

from __future__ import annotations

import os

import httpx
import pytest

from prism_platform.modules.intel_company.collector import CompanyCollector

# Skip entire module if no API key
pytestmark = pytest.mark.skipif(
    not os.environ.get("PERPLEXITY_API_KEY"),
    reason="PERPLEXITY_API_KEY not set",
)


@pytest.fixture
def collector() -> CompanyCollector:
    return CompanyCollector()


class TestPerplexityPrompts:
    """Test each Perplexity prompt individually with real API calls."""

    @pytest.mark.asyncio
    async def test_company_profile_prompt(self, collector: CompanyCollector) -> None:
        """Prompt 1: Company profile returns substantive content about Dell."""
        response = await collector._call_perplexity(collector._prompt_company_profile("dell.com"))
        assert len(response) > 200, f"Profile response too short: {len(response)} chars"
        # Should mention Dell somewhere
        assert "dell" in response.lower(), "Response doesn't mention Dell"

    @pytest.mark.asyncio
    async def test_executives_prompt(self, collector: CompanyCollector) -> None:
        """Prompt 2: Executives returns leadership data."""
        response = await collector._call_perplexity(collector._prompt_executives("dell.com"))
        assert len(response) > 200, f"Executives response too short: {len(response)} chars"
        # Should mention at least one common C-suite title
        response_lower = response.lower()
        assert any(title in response_lower for title in ["ceo", "cto", "cfo", "chief"]), (
            "Response doesn't mention any executive titles"
        )

    @pytest.mark.asyncio
    async def test_competitors_prompt(self, collector: CompanyCollector) -> None:
        """Prompt 3: Competitors returns competitive landscape."""
        response = await collector._call_perplexity(collector._prompt_competitors("dell.com"))
        assert len(response) > 100, f"Competitors response too short: {len(response)} chars"
        # Should mention at least one known Dell competitor
        response_lower = response.lower()
        assert any(comp in response_lower for comp in ["hp", "lenovo", "hewlett", "cisco"]), (
            "Response doesn't mention any known Dell competitors"
        )

    @pytest.mark.asyncio
    async def test_activity_prompt(self, collector: CompanyCollector) -> None:
        """Prompt 4: Recent activity returns news/blog items."""
        response = await collector._call_perplexity(collector._prompt_recent_activity("dell.com"))
        assert len(response) > 100, f"Activity response too short: {len(response)} chars"


class TestCollectAll:
    """Test the full collect_all flow with real API calls."""

    @pytest.mark.asyncio
    async def test_collect_all_dell(self, collector: CompanyCollector) -> None:
        """Full collection for dell.com returns all expected keys."""
        results = await collector.collect_all("dell.com")

        # All keys present
        assert "profile" in results
        assert "executives" in results
        assert "competitors" in results
        assert "activity" in results
        assert "homepage_html" in results
        assert "llm_calls" in results

        # Profile and executives should have substantive content
        assert len(results["profile"]) > 200, "Profile too short"
        assert len(results["executives"]) > 200, "Executives too short"

        # Should have made 4 LLM calls
        assert results["llm_calls"] == 4

        # Homepage should have some HTML
        assert len(results["homepage_html"]) > 100, "Homepage HTML too short"


class TestHomepageFetch:
    """Test homepage fetching independently."""

    @pytest.mark.asyncio
    async def test_fetch_dell_homepage(self, collector: CompanyCollector) -> None:
        """Dell homepage returns HTML with expected markers."""
        html = await collector._fetch_homepage("dell.com")
        assert len(html) > 1000, "Homepage HTML suspiciously short"
        assert "<" in html, "Response doesn't look like HTML"

    @pytest.mark.asyncio
    async def test_fetch_nonexistent_domain(self, collector: CompanyCollector) -> None:
        """Non-existent domain raises an error."""
        with pytest.raises((httpx.ConnectError, httpx.HTTPStatusError, httpx.TimeoutException)):
            await collector._fetch_homepage("this-domain-definitely-does-not-exist-xyz123.com")
