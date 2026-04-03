"""Collector tests for intel-news module.

Tests Perplexity API calls with real API keys against real services.
Uses dell.com as the standard test domain per project convention.
"""

from __future__ import annotations

import os

import pytest

from prism_platform.modules.intel_news.collector import (
    NewsCollector,
    _build_company_news_prompt,
    _build_exec_interviews_prompt,
    _build_exec_quotes_prompt,
    _build_signal_classification_prompt,
    _perplexity_query,
)

# Skip all tests in this file if Perplexity key is missing
pytestmark = pytest.mark.skipif(
    not os.environ.get("PERPLEXITY_API_KEY"),
    reason="PERPLEXITY_API_KEY not set -- skipping real API tests",
)


# ---------------------------------------------------------------------------
# Prompt builder tests (no API calls)
# ---------------------------------------------------------------------------


class TestPromptBuilders:
    """Test that prompt builders produce non-empty, well-formed prompts."""

    def test_company_news_prompt(self) -> None:
        """Company news prompt includes company name and domain."""
        prompt = _build_company_news_prompt("Dell Technologies", "dell.com")
        assert "Dell Technologies" in prompt
        assert "dell.com" in prompt
        assert "90 days" in prompt

    def test_exec_interviews_prompt(self) -> None:
        """Executive interviews prompt includes exec details."""
        prompt = _build_exec_interviews_prompt(
            "Michael Dell", "Chairman and CEO", "Dell Technologies"
        )
        assert "Michael Dell" in prompt
        assert "Chairman and CEO" in prompt
        assert "Dell Technologies" in prompt

    def test_exec_quotes_prompt(self) -> None:
        """Targeted quotes prompt includes exec name and company."""
        prompt = _build_exec_quotes_prompt("Michael Dell", "Dell Technologies")
        assert "Michael Dell" in prompt
        assert "Dell Technologies" in prompt

    def test_signal_classification_prompt(self) -> None:
        """Signal classification prompt includes company name and news text."""
        prompt = _build_signal_classification_prompt(
            "Dell Technologies", "Dell announced new AI servers"
        )
        assert "Dell Technologies" in prompt
        assert "Dell announced new AI servers" in prompt


# ---------------------------------------------------------------------------
# Real Perplexity API tests
# ---------------------------------------------------------------------------


class TestPerplexityQuery:
    """Tests that make real Perplexity API calls."""

    @pytest.mark.asyncio
    async def test_basic_perplexity_query(self) -> None:
        """Perplexity returns non-empty content for a simple query."""
        result = await _perplexity_query(
            "What is Dell Technologies? One sentence answer.",
            label="test:basic",
        )
        assert isinstance(result, str)
        assert len(result) > 10
        assert "dell" in result.lower() or "technology" in result.lower()

    @pytest.mark.asyncio
    async def test_company_news_query(self) -> None:
        """Perplexity returns news content for Dell."""
        prompt = _build_company_news_prompt("Dell Technologies", "dell.com")
        result = await _perplexity_query(prompt, label="test:company_news")
        assert isinstance(result, str)
        assert len(result) > 50


class TestNewsCollectorCollectAll:
    """Integration tests for the full collection pipeline."""

    @pytest.mark.asyncio
    async def test_collect_all_basic(self) -> None:
        """collect_all returns structured raw data with prospect news."""
        collector = NewsCollector()
        raw = await collector.collect_all(
            domain="dell.com",
            company_name="Dell Technologies",
            executives=[
                {
                    "name": "Michael Dell",
                    "title": "Chairman and CEO",
                    "relevance": "economic_buyer",
                },
            ],
            competitor_domains=[
                {"company_name": "HP Inc.", "domain": "hp.com"},
            ],
        )

        assert isinstance(raw, dict)
        assert "prospect_news" in raw
        assert "exec_media" in raw
        assert "competitor_news" in raw
        assert "signals" in raw

        # Prospect news should have content
        assert isinstance(raw["prospect_news"], str)
        assert len(raw["prospect_news"]) > 50

        # Exec media should have at least one entry
        assert isinstance(raw["exec_media"], dict)
        assert len(raw["exec_media"]) >= 1

    @pytest.mark.asyncio
    async def test_collect_all_no_executives(self) -> None:
        """collect_all works with empty executive list."""
        collector = NewsCollector()
        raw = await collector.collect_all(
            domain="dell.com",
            company_name="Dell Technologies",
            executives=[],
            competitor_domains=[],
        )

        assert isinstance(raw, dict)
        assert "prospect_news" in raw
        assert isinstance(raw["prospect_news"], str)
        assert len(raw["prospect_news"]) > 50
        assert raw["exec_media"] == {}
        assert raw["competitor_news"] == {}
