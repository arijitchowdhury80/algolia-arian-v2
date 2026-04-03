"""Tests for intel-social collector -- Perplexity + Apify social data collection.

Tests use real API calls against Perplexity. Requires PERPLEXITY_API_KEY in .env.
Test domain: dell.com (Michael Dell, Jeff Clarke social activity).
"""

from __future__ import annotations

import os

import pytest

from prism_platform.modules.intel_social.collector import (
    SocialCollector,
    _build_competitor_exec_prompt,
    _build_linkedin_activity_prompt,
    _build_public_statements_prompt,
    _build_twitter_prompt,
    _perplexity_query,
)

# Skip all tests in this file if PERPLEXITY_API_KEY is not set
pytestmark = pytest.mark.skipif(
    not os.environ.get("PERPLEXITY_API_KEY"),
    reason="PERPLEXITY_API_KEY not set",
)


# ---------------------------------------------------------------------------
# Unit tests -- prompt builders
# ---------------------------------------------------------------------------


class TestPromptBuilders:
    """Tests for prompt builder functions (no API calls)."""

    def test_linkedin_activity_prompt(self) -> None:
        """LinkedIn activity prompt includes exec name, title, and company."""
        prompt = _build_linkedin_activity_prompt(
            "Michael Dell", "Chairman and CEO", "Dell Technologies"
        )
        assert "Michael Dell" in prompt
        assert "Chairman and CEO" in prompt
        assert "Dell Technologies" in prompt
        assert "LinkedIn" in prompt
        assert "2025-2026" in prompt

    def test_public_statements_prompt(self) -> None:
        """Public statements prompt includes exec name and company."""
        prompt = _build_public_statements_prompt("Michael Dell", "Dell Technologies")
        assert "Michael Dell" in prompt
        assert "Dell Technologies" in prompt
        assert "keynote" in prompt
        assert "conference" in prompt

    def test_twitter_prompt(self) -> None:
        """Twitter prompt includes company name."""
        prompt = _build_twitter_prompt("Dell Technologies")
        assert "Dell Technologies" in prompt
        assert "Twitter" in prompt

    def test_competitor_exec_prompt(self) -> None:
        """Competitor exec prompt includes exec name, title, and company."""
        prompt = _build_competitor_exec_prompt("HP Inc. CEO", "CEO", "HP Inc.")
        assert "HP Inc. CEO" in prompt
        assert "HP Inc." in prompt
        assert "LinkedIn" in prompt


# ---------------------------------------------------------------------------
# Integration tests -- real Perplexity API calls
# ---------------------------------------------------------------------------


class TestPerplexityQuery:
    """Tests for the raw Perplexity query function."""

    @pytest.mark.asyncio
    async def test_perplexity_returns_content(self) -> None:
        """Perplexity returns non-empty string content for a simple query."""
        result = await _perplexity_query(
            "Michael Dell, Chairman and CEO at Dell Technologies: recent LinkedIn posts "
            "and activity in 2025-2026.",
            label="test:dell_linkedin",
        )
        assert isinstance(result, str)
        assert len(result) > 50
        # Should mention Dell or Michael Dell somewhere
        assert "dell" in result.lower() or "michael" in result.lower()


class TestSocialCollector:
    """Integration tests for the full SocialCollector."""

    @pytest.mark.asyncio
    async def test_collect_all_dell(self) -> None:
        """SocialCollector.collect_all returns structured raw data for dell.com."""
        collector = SocialCollector()
        executives = [
            {"name": "Michael Dell", "title": "Chairman and CEO", "relevance": "economic_buyer"},
            {
                "name": "Jeff Clarke",
                "title": "Vice Chairman and COO",
                "relevance": "economic_buyer",
            },
        ]
        competitors = [
            {"company_name": "HP Inc.", "domain": "hp.com"},
        ]

        raw = await collector.collect_all(
            domain="dell.com",
            company_name="Dell Technologies",
            executives=executives,
            competitor_domains=competitors,
        )

        # Verify structure
        assert "linkedin_activity" in raw
        assert "public_statements" in raw
        assert "apify_posts" in raw
        assert "twitter" in raw
        assert "competitor_social" in raw

        # LinkedIn activity should have entries for our execs
        assert isinstance(raw["linkedin_activity"], dict)
        assert len(raw["linkedin_activity"]) >= 1

        # Public statements should have entries
        assert isinstance(raw["public_statements"], dict)
        assert len(raw["public_statements"]) >= 1

        # Twitter should be a string
        assert isinstance(raw["twitter"], str)

        # At least some exec data should be non-empty
        has_linkedin_data = any(
            isinstance(v, str) and len(v) > 50 for v in raw["linkedin_activity"].values()
        )
        has_statement_data = any(
            isinstance(v, str) and len(v) > 50 for v in raw["public_statements"].values()
        )
        assert has_linkedin_data or has_statement_data, (
            "Expected at least one exec to have substantial social data"
        )

    @pytest.mark.asyncio
    async def test_collect_all_no_executives(self) -> None:
        """SocialCollector handles empty executive list gracefully."""
        collector = SocialCollector()

        raw = await collector.collect_all(
            domain="dell.com",
            company_name="Dell Technologies",
            executives=[],
            competitor_domains=[],
        )

        assert "linkedin_activity" in raw
        assert "public_statements" in raw
        assert "twitter" in raw
        # With no execs, linkedin and statements should be mostly empty
        # but company page fallback or twitter should still work
        assert isinstance(raw["twitter"], str)
