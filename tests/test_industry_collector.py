"""Tests for intel-industry collector -- prompt builders and validator unit tests.

Perplexity quota is exhausted so API-calling tests are skipped.
This file tests prompt builder functions and the validator independently.
"""

from __future__ import annotations

from prism_platform.core.types import EvidenceTier, Source
from prism_platform.modules.intel_industry.collector import (
    build_benchmarks_prompt,
    build_case_studies_prompt,
    build_pain_points_prompt,
    build_trends_prompt,
    build_vendor_landscape_prompt,
)
from prism_platform.modules.intel_industry.schemas import (
    IndustryOutput,
    IndustryTrend,
    PainPoint,
    VerticalBenchmark,
)
from prism_platform.modules.intel_industry.validator import validate_output

# ---------------------------------------------------------------------------
# Prompt builder tests
# ---------------------------------------------------------------------------


class TestBuildBenchmarksPrompt:
    """Tests for build_benchmarks_prompt."""

    def test_includes_industry(self) -> None:
        """Prompt includes the industry name."""
        prompt = build_benchmarks_prompt("Retail")
        assert "Retail" in prompt

    def test_includes_sub_vertical(self) -> None:
        """Prompt includes sub_vertical when provided."""
        prompt = build_benchmarks_prompt("Retail", "Luxury Fashion")
        assert "Luxury Fashion" in prompt

    def test_no_sub_vertical(self) -> None:
        """Prompt works without sub_vertical."""
        prompt = build_benchmarks_prompt("Technology")
        assert "Technology" in prompt
        assert "None" not in prompt

    def test_includes_benchmark_keywords(self) -> None:
        """Prompt includes relevant benchmark keywords."""
        prompt = build_benchmarks_prompt("Retail")
        assert "conversion rate" in prompt.lower()
        assert "average order value" in prompt.lower()

    def test_includes_source_names(self) -> None:
        """Prompt mentions expected source names."""
        prompt = build_benchmarks_prompt("Retail")
        assert "Baymard Institute" in prompt
        assert "Forrester" in prompt


class TestBuildTrendsPrompt:
    """Tests for build_trends_prompt."""

    def test_includes_industry(self) -> None:
        """Prompt includes the industry name."""
        prompt = build_trends_prompt("B2B Manufacturing")
        assert "B2B Manufacturing" in prompt

    def test_includes_sub_vertical(self) -> None:
        """Prompt includes sub_vertical when provided."""
        prompt = build_trends_prompt("Retail", "Grocery")
        assert "Grocery" in prompt

    def test_includes_trend_keywords(self) -> None:
        """Prompt includes trend-related keywords."""
        prompt = build_trends_prompt("Retail")
        assert "AI" in prompt
        assert "personalization" in prompt

    def test_includes_analyst_names(self) -> None:
        """Prompt mentions analyst firms."""
        prompt = build_trends_prompt("Retail")
        assert "Gartner" in prompt


class TestBuildPainPointsPrompt:
    """Tests for build_pain_points_prompt."""

    def test_includes_industry(self) -> None:
        """Prompt includes the industry name."""
        prompt = build_pain_points_prompt("Healthcare")
        assert "Healthcare" in prompt

    def test_includes_search_keywords(self) -> None:
        """Prompt includes search-related keywords."""
        prompt = build_pain_points_prompt("Retail")
        assert "search" in prompt.lower()
        assert "discovery" in prompt.lower()

    def test_includes_algolia_mention(self) -> None:
        """Prompt mentions Algolia for pain point mapping."""
        prompt = build_pain_points_prompt("Retail")
        assert "Algolia" in prompt


class TestBuildCaseStudiesPrompt:
    """Tests for build_case_studies_prompt."""

    def test_includes_algolia(self) -> None:
        """Prompt mentions Algolia."""
        prompt = build_case_studies_prompt("Retail")
        assert "Algolia" in prompt

    def test_includes_industry(self) -> None:
        """Prompt includes the industry name."""
        prompt = build_case_studies_prompt("Financial Services")
        assert "Financial Services" in prompt

    def test_includes_case_study_keywords(self) -> None:
        """Prompt includes case study keywords."""
        prompt = build_case_studies_prompt("Retail")
        assert "case study" in prompt.lower() or "customer story" in prompt.lower()


class TestBuildVendorLandscapePrompt:
    """Tests for build_vendor_landscape_prompt."""

    def test_includes_industry(self) -> None:
        """Prompt includes the industry name."""
        prompt = build_vendor_landscape_prompt("Retail")
        assert "Retail" in prompt

    def test_includes_vendor_names(self) -> None:
        """Prompt mentions known search vendors."""
        prompt = build_vendor_landscape_prompt("Retail")
        assert "Algolia" in prompt
        assert "Elasticsearch" in prompt
        assert "Coveo" in prompt

    def test_includes_market_share_keywords(self) -> None:
        """Prompt includes market share keywords."""
        prompt = build_vendor_landscape_prompt("Retail")
        assert "market share" in prompt.lower()


# ---------------------------------------------------------------------------
# Validator unit tests
# ---------------------------------------------------------------------------


def _make_valid_output(**overrides: object) -> IndustryOutput:
    """Build a valid IndustryOutput for testing the validator."""
    data: dict = {
        "domain": "dell.com",
        "industry": "Technology",
        "sub_vertical": None,
        "vertical_benchmarks": [
            VerticalBenchmark(
                metric_name="Conversion Rate",
                value="2.8%",
                source="Baymard Institute 2025",
                industry="Technology",
            )
        ],
        "industry_trends": [
            IndustryTrend(
                trend_name="AI Personalization",
                description="AI-driven search personalization is growing.",
                relevance_to_search="high",
            )
        ],
        "pain_points": [
            PainPoint(
                pain_point="Poor Relevance",
                description="Search results are not relevant.",
                algolia_capability="AI Search (NeuralSearch)",
            )
        ],
        "industry_summary": "Technology sector is evolving rapidly.",
    }
    data.update(overrides)
    return IndustryOutput(**data)


def _make_source(**overrides: object) -> Source:
    """Build a valid Source for testing."""
    data: dict = {
        "field": "vertical_benchmarks",
        "value": "3 benchmarks collected",
        "tier": EvidenceTier.WEBSEARCH,
        "source_label": "Perplexity sonar-pro",
        "method": "llm_extraction",
    }
    data.update(overrides)
    return Source(**data)


class TestValidateOutput:
    """Tests for validate_output function."""

    def test_valid_output_passes(self) -> None:
        """Valid output passes all checks."""
        output = _make_valid_output()
        sources = [_make_source()]
        result = validate_output(output, sources)
        assert result.passed is True
        assert result.checks_run == 10
        assert result.checks_passed == 10
        assert len(result.errors) == 0

    def test_empty_domain_fails(self) -> None:
        """Empty domain fails check 1."""
        output = _make_valid_output(domain="")
        sources = [_make_source()]
        result = validate_output(output, sources)
        assert result.passed is False
        assert "domain is empty" in result.errors[0]

    def test_empty_industry_fails(self) -> None:
        """Empty industry fails check 2."""
        output = _make_valid_output(industry="")
        sources = [_make_source()]
        result = validate_output(output, sources)
        assert result.passed is False
        assert "industry is empty" in result.errors[0]

    def test_no_benchmarks_fails(self) -> None:
        """No benchmarks fails check 3."""
        output = _make_valid_output(vertical_benchmarks=[])
        sources = [_make_source()]
        result = validate_output(output, sources)
        assert result.passed is False
        assert any("benchmark" in e.lower() for e in result.errors)

    def test_no_trends_fails(self) -> None:
        """No trends fails check 4."""
        output = _make_valid_output(industry_trends=[])
        sources = [_make_source()]
        result = validate_output(output, sources)
        assert result.passed is False
        assert any("trend" in e.lower() for e in result.errors)

    def test_no_pain_points_fails(self) -> None:
        """No pain points fails check 5."""
        output = _make_valid_output(pain_points=[])
        sources = [_make_source()]
        result = validate_output(output, sources)
        assert result.passed is False
        assert any("pain point" in e.lower() for e in result.errors)

    def test_empty_algolia_capability_fails(self) -> None:
        """Pain point with empty algolia_capability fails check 6."""
        output = _make_valid_output(
            pain_points=[
                PainPoint(
                    pain_point="Bad Search",
                    description="Search is broken.",
                    algolia_capability="",
                )
            ]
        )
        sources = [_make_source()]
        result = validate_output(output, sources)
        assert result.passed is False
        assert any("algolia_capability" in e for e in result.errors)

    def test_no_sources_fails(self) -> None:
        """No source provenance fails check 7."""
        output = _make_valid_output()
        result = validate_output(output, sources=[])
        assert result.passed is False
        assert any("source" in e.lower() for e in result.errors)

    def test_empty_summary_warns(self) -> None:
        """Empty industry_summary generates a warning, not an error."""
        output = _make_valid_output(industry_summary="")
        sources = [_make_source()]
        result = validate_output(output, sources)
        # Warning means it still passes but with a warning
        assert any("industry_summary" in w for w in result.warnings)

    def test_bad_benchmark_fields_fails(self) -> None:
        """Benchmark with empty metric_name fails check 9."""
        output = _make_valid_output(
            vertical_benchmarks=[
                VerticalBenchmark(
                    metric_name="",
                    value="2.8%",
                    source="Baymard",
                    industry="Tech",
                )
            ]
        )
        sources = [_make_source()]
        result = validate_output(output, sources)
        assert result.passed is False
        assert any("metric_name" in e or "Benchmark" in e for e in result.errors)

    def test_bad_trend_fields_fails(self) -> None:
        """Trend with empty trend_name fails check 10."""
        output = _make_valid_output(
            industry_trends=[
                IndustryTrend(
                    trend_name="",
                    description="Some trend.",
                )
            ]
        )
        sources = [_make_source()]
        result = validate_output(output, sources)
        assert result.passed is False
        assert any("trend_name" in e or "Trend" in e for e in result.errors)

    def test_multiple_errors_reported(self) -> None:
        """Multiple failures are all reported."""
        output = _make_valid_output(
            domain="",
            industry="",
            vertical_benchmarks=[],
            industry_trends=[],
            pain_points=[],
        )
        result = validate_output(output, sources=[])
        assert result.passed is False
        assert len(result.errors) >= 5

    def test_checks_run_count_always_10(self) -> None:
        """All 10 checks are always run regardless of failures."""
        output = _make_valid_output()
        sources = [_make_source()]
        result = validate_output(output, sources)
        assert result.checks_run == 10
