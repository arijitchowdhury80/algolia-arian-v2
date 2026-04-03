"""Integration tests for intel-news module.

Full pipeline: collect -> enrich -> validate with real API calls.
Uses dell.com as the standard test domain.
"""

from __future__ import annotations

import os

import pytest

from prism_platform.core.module import ExecutionContext
from prism_platform.core.types import ModuleResult
from prism_platform.modules.intel_news.enricher import NewsEnricher
from prism_platform.modules.intel_news.module import (
    NewsModule,
    _extract_competitors,
    _extract_executives,
)
from prism_platform.modules.intel_news.schemas import NewsOutput
from prism_platform.modules.intel_news.validator import validate_output

# Skip all tests if both API keys are missing
pytestmark = pytest.mark.skipif(
    not os.environ.get("PERPLEXITY_API_KEY") or not os.environ.get("GEMINI_API_KEY"),
    reason="PERPLEXITY_API_KEY and/or GEMINI_API_KEY not set",
)


# ---------------------------------------------------------------------------
# Helper data
# ---------------------------------------------------------------------------

DELL_INTELLIGENCE = {
    "executives": [
        {
            "full_name": "Michael Dell",
            "title": "Chairman and CEO",
            "relevance": "economic_buyer",
        },
        {
            "full_name": "Jeff Clarke",
            "title": "Vice Chairman and COO",
            "relevance": "economic_buyer",
        },
        {
            "full_name": "Yvonne McGill",
            "title": "Chief Financial Officer",
            "relevance": "economic_buyer",
        },
    ],
    "competitors": [
        {"company_name": "HP Inc.", "domain": "hp.com"},
        {"company_name": "Lenovo", "domain": "lenovo.com"},
    ],
}


def _make_context() -> ExecutionContext:
    """Build a test ExecutionContext for dell.com."""
    return ExecutionContext(
        audit_id="test-audit-news-001",
        account_id="test-account-001",
        domain="dell.com",
        company_name="Dell Technologies",
        ticker="DELL",
        is_private=False,
    )


# ---------------------------------------------------------------------------
# Helper extraction tests (no API calls)
# ---------------------------------------------------------------------------


class TestHelperExtraction:
    """Tests for _extract_executives and _extract_competitors."""

    def test_extract_executives(self) -> None:
        """Extracts and normalizes executive list."""
        execs = _extract_executives(DELL_INTELLIGENCE)
        assert len(execs) == 3
        assert execs[0]["name"] == "Michael Dell"
        assert execs[0]["title"] == "Chairman and CEO"
        assert execs[0]["relevance"] == "economic_buyer"

    def test_extract_executives_empty(self) -> None:
        """Returns empty list when no executives in intelligence."""
        execs = _extract_executives({})
        assert execs == []

    def test_extract_executives_alt_key(self) -> None:
        """Handles 'name' key instead of 'full_name'."""
        data = {
            "executives": [{"name": "Jane Doe", "title": "CTO", "relevance": "technical_evaluator"}]
        }
        execs = _extract_executives(data)
        assert execs[0]["name"] == "Jane Doe"

    def test_extract_competitors(self) -> None:
        """Extracts competitor list."""
        comps = _extract_competitors(DELL_INTELLIGENCE)
        assert len(comps) == 2
        assert comps[0]["company_name"] == "HP Inc."
        assert comps[0]["domain"] == "hp.com"

    def test_extract_competitors_empty(self) -> None:
        """Returns empty list when no competitors in intelligence."""
        comps = _extract_competitors({})
        assert comps == []


# ---------------------------------------------------------------------------
# Enricher integration test
# ---------------------------------------------------------------------------


class TestNewsEnricherIntegration:
    """Tests that the enricher structures raw data via Gemini."""

    @pytest.mark.asyncio
    async def test_enrich_prospect_articles(self) -> None:
        """Enricher extracts articles from raw Perplexity text."""
        enricher = NewsEnricher()

        # Simulated raw data (realistic structure)
        raw_data = {
            "prospect_news": (
                "1. Dell Technologies reported record Q4 FY2026 revenue of $24.5 billion "
                "(Reuters, 2026-02-28, https://reuters.com/dell-q4).\n"
                "2. Dell announced new AI-powered search capabilities for its e-commerce platform "
                "(TechCrunch, 2026-02-15, https://techcrunch.com/dell-ai-search).\n"
                "3. Michael Dell spoke at CES 2026 about digital transformation priorities "
                "(The Verge, 2026-01-07, https://theverge.com/ces-dell)."
            ),
            "exec_media": {},
            "competitor_news": {},
            "signals": "",
        }

        output, llm_calls, cost = await enricher.enrich(
            domain="dell.com",
            company_name="Dell Technologies",
            raw_data=raw_data,
        )

        assert isinstance(output, NewsOutput)
        assert output.domain == "dell.com"
        assert len(output.prospect_articles) >= 1
        assert llm_calls >= 1
        assert cost >= 0.0

        # Verify articles have required fields
        for article in output.prospect_articles:
            assert article.headline.strip() != ""
            assert article.source.strip() != ""
            assert article.date.strip() != ""


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------


class TestNewsValidator:
    """Tests for the validator with realistic data."""

    def test_valid_output_passes(self) -> None:
        """A well-formed output passes validation."""
        from prism_platform.core.types import EvidenceTier, Source

        output = NewsOutput(
            domain="dell.com",
            prospect_articles=[
                {  # type: ignore[arg-type]
                    "headline": "Dell Q4 Revenue Record",
                    "source": "Reuters",
                    "date": "2026-02-15",
                    "company_name": "Dell",
                }
            ],
            sell_signal_count=0,
            high_value_quote_count=0,
            news_summary="Dell reported strong Q4 results.",
        )

        sources = [
            Source(
                field="prospect_articles",
                value="1 articles collected",
                tier=EvidenceTier.WEBFETCH,
                source_label="Perplexity sonar-pro",
                method="llm_extraction",
            )
        ]

        result = validate_output(output, sources)
        assert result.passed is True
        assert result.checks_run == 9
        assert result.checks_passed >= 8

    def test_empty_output_fails(self) -> None:
        """An empty output fails validation."""
        output = NewsOutput(domain="dell.com")
        result = validate_output(output, [])
        assert result.passed is False
        assert len(result.errors) >= 2  # no articles, no sources

    def test_mismatched_sell_signal_count_fails(self) -> None:
        """Mismatched sell_signal_count triggers validation error."""
        from prism_platform.core.types import EvidenceTier, Source

        output = NewsOutput(
            domain="dell.com",
            prospect_articles=[
                {  # type: ignore[arg-type]
                    "headline": "Dell Search Migration",
                    "source": "TechCrunch",
                    "date": "2026-02-15",
                    "is_sell_signal": True,
                    "sell_signal_reason": "Search migration",
                    "company_name": "Dell",
                }
            ],
            sell_signal_count=0,  # Should be 1
            high_value_quote_count=0,
            news_summary="Dell migrating search.",
        )
        sources = [
            Source(
                field="prospect_articles",
                value="1 articles",
                tier=EvidenceTier.WEBFETCH,
                source_label="Perplexity",
                method="llm_extraction",
            )
        ]

        result = validate_output(output, sources)
        assert result.passed is False
        assert any("sell_signal_count" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Full module integration test
# ---------------------------------------------------------------------------


class TestNewsModuleIntegration:
    """Full pipeline integration test with real API calls."""

    @pytest.mark.asyncio
    async def test_full_pipeline_dell(self) -> None:
        """Run the full news pipeline for dell.com with real APIs.

        This test makes real Perplexity and Gemini API calls.
        It verifies the complete collect -> enrich -> validate flow.
        """
        module = NewsModule()
        context = _make_context()

        result = await module.execute(context, intelligence=DELL_INTELLIGENCE)

        # Basic result checks
        assert isinstance(result, ModuleResult)
        assert result.module_name == "intel-news"
        assert result.status in ("success", "partial")
        assert result.duration_ms > 0
        assert result.llm_calls >= 1

        # Deserialize and check output
        output = NewsOutput.model_validate(result.output)
        assert output.domain == "dell.com"
        assert len(output.prospect_articles) >= 1

        # Articles should have content
        for article in output.prospect_articles:
            assert article.headline.strip() != ""
            assert article.source.strip() != ""

        # Sources should be populated
        assert len(result.sources) >= 1

        # Validate
        validation = await module.validate(result)
        assert validation.checks_run >= 8

    @pytest.mark.asyncio
    async def test_full_pipeline_no_intelligence(self) -> None:
        """Run the pipeline without intel-company data (fallback mode)."""
        module = NewsModule()
        context = _make_context()

        result = await module.execute(context, intelligence=None)

        assert isinstance(result, ModuleResult)
        assert result.module_name == "intel-news"
        assert result.status in ("success", "partial")

        output = NewsOutput.model_validate(result.output)
        assert output.domain == "dell.com"

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        """Health check returns True when API keys are set."""
        module = NewsModule()
        is_healthy = await module.health_check()
        assert is_healthy is True
