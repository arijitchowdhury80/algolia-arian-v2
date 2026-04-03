"""Collector tests for intel-hiring module.

Tests the HiringCollector helper functions and Perplexity query construction.
Integration tests with real API calls when keys are available.
"""

from __future__ import annotations

import os

import pytest

from prism_platform.modules.intel_hiring.collector import (
    HiringCollector,
    _build_champion_signals_prompt,
    _build_perplexity_jobs_prompt,
    _build_search_queries,
    _perplexity_query,
)

# ---------------------------------------------------------------------------
# Prompt / query builder tests (no API calls)
# ---------------------------------------------------------------------------


class TestSearchQueryBuilder:
    """Tests for _build_search_queries."""

    def test_returns_three_queries(self) -> None:
        """Always returns exactly 3 queries."""
        queries = _build_search_queries("Dell Technologies")
        assert len(queries) == 3

    def test_company_name_in_queries(self) -> None:
        """Company name appears in every query."""
        queries = _build_search_queries("Dell Technologies")
        for q in queries:
            assert "Dell Technologies" in q

    def test_first_query_search_focused(self) -> None:
        """First query focuses on search/discovery/personalization."""
        queries = _build_search_queries("Dell Technologies")
        assert "search" in queries[0].lower()

    def test_second_query_engineering_focused(self) -> None:
        """Second query focuses on engineering/platform/architecture."""
        queries = _build_search_queries("Dell Technologies")
        assert "engineer" in queries[1].lower() or "platform" in queries[1].lower()

    def test_third_query_leadership_focused(self) -> None:
        """Third query focuses on VP/director/head roles."""
        queries = _build_search_queries("Dell Technologies")
        assert "vp" in queries[2].lower() or "director" in queries[2].lower()


class TestPerplexityJobsPrompt:
    """Tests for _build_perplexity_jobs_prompt."""

    def test_prompt_contains_company_name(self) -> None:
        """Prompt includes the company name."""
        prompt = _build_perplexity_jobs_prompt("Dell Technologies", "search technology")
        assert "Dell Technologies" in prompt

    def test_prompt_contains_focus(self) -> None:
        """Prompt includes the query focus area."""
        prompt = _build_perplexity_jobs_prompt("Dell Technologies", "search technology")
        assert "search technology" in prompt


class TestChampionSignalsPrompt:
    """Tests for _build_champion_signals_prompt."""

    def test_prompt_contains_exec_info(self) -> None:
        """Prompt includes executive name and title."""
        prompt = _build_champion_signals_prompt(
            "Michael Dell", "Chairman and CEO", "Dell Technologies"
        )
        assert "Michael Dell" in prompt
        assert "Chairman and CEO" in prompt
        assert "Dell Technologies" in prompt

    def test_prompt_asks_for_search_signals(self) -> None:
        """Prompt asks about search technology connections."""
        prompt = _build_champion_signals_prompt("Jane Doe", "CTO", "TestCo")
        assert "search" in prompt.lower() or "Algolia" in prompt


# ---------------------------------------------------------------------------
# Integration tests (real API calls)
# ---------------------------------------------------------------------------


class TestPerplexityQueryIntegration:
    """Integration tests for Perplexity API calls."""

    @pytest.mark.skipif(
        not os.environ.get("PERPLEXITY_API_KEY"),
        reason="PERPLEXITY_API_KEY not set",
    )
    @pytest.mark.asyncio
    async def test_perplexity_query_returns_content(self) -> None:
        """Perplexity query returns non-empty content."""
        result = await _perplexity_query(
            "List 5 current open jobs at Dell Technologies related to search technology.",
            label="test:dell_jobs",
        )
        assert isinstance(result, str)
        assert len(result) > 50


class TestHiringCollectorIntegration:
    """Integration tests for the full HiringCollector."""

    @pytest.mark.skipif(
        not os.environ.get("PERPLEXITY_API_KEY"),
        reason="PERPLEXITY_API_KEY not set",
    )
    @pytest.mark.asyncio
    async def test_collect_all_perplexity_fallback(self) -> None:
        """Collector works with Perplexity fallback when APIFY_TOKEN is not set.

        Note: This test uses real Perplexity API calls.
        """
        # Force Perplexity fallback by temporarily unsetting apify_api_key
        from prism_platform.config import settings

        original_token = settings.apify_api_key
        settings.apify_api_key = ""

        try:
            collector = HiringCollector()
            raw_data = await collector.collect_all(
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

            assert isinstance(raw_data, dict)
            assert "prospect_roles" in raw_data
            assert "competitor_roles" in raw_data
            assert "champion_signals" in raw_data
            assert raw_data["source_type"] == "perplexity"

            # Prospect roles should have data
            assert len(raw_data["prospect_roles"]) >= 1

        finally:
            settings.apify_api_key = original_token
