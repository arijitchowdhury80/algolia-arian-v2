"""Contract tests for intel-industry schemas.

Validates Pydantic models accept valid data, reject invalid data,
and enforce all constraints specified in the module spec.
NO API calls -- pure schema validation only.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.intel_industry.schemas import (
    AlgoliaCaseStudy,
    IndustryInput,
    IndustryOutput,
    IndustryTrend,
    PainPoint,
    SearchVendorMarketShare,
    VerticalBenchmark,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_benchmark(**overrides: object) -> dict:
    """Build a valid VerticalBenchmark dict with optional overrides."""
    base: dict = {
        "metric_name": "Average Conversion Rate",
        "value": "2.8%",
        "source": "Baymard Institute 2025",
        "industry": "Retail",
        "year": "2025",
        "notes": "Desktop only, excludes mobile",
    }
    base.update(overrides)
    return base


def _make_trend(**overrides: object) -> dict:
    """Build a valid IndustryTrend dict with optional overrides."""
    base: dict = {
        "trend_name": "AI-Powered Personalization",
        "description": (
            "Retailers are increasingly adopting AI to personalize search results "
            "and product recommendations based on individual user behavior."
        ),
        "relevance_to_search": "high",
        "source": "Gartner 2026 Hype Cycle",
        "analyst_quote": "AI personalization will become table stakes by 2027.",
    }
    base.update(overrides)
    return base


def _make_pain_point(**overrides: object) -> dict:
    """Build a valid PainPoint dict with optional overrides."""
    base: dict = {
        "pain_point": "Poor Search Relevance",
        "description": (
            "Most retailers report that their site search returns irrelevant results, "
            "leading to high bounce rates and lost revenue."
        ),
        "algolia_capability": "AI Search (NeuralSearch)",
        "severity": "critical",
    }
    base.update(overrides)
    return base


def _make_case_study(**overrides: object) -> dict:
    """Build a valid AlgoliaCaseStudy dict with optional overrides."""
    base: dict = {
        "customer_name": "Lacoste",
        "industry": "Retail",
        "use_case": "Site Search + Recommendations",
        "key_metrics": ["37% conversion lift", "2x search usage"],
        "url": "https://www.algolia.com/customers/lacoste/",
    }
    base.update(overrides)
    return base


def _make_vendor(**overrides: object) -> dict:
    """Build a valid SearchVendorMarketShare dict with optional overrides."""
    base: dict = {
        "vendor_name": "Algolia",
        "estimated_share_pct": 18.5,
        "notes": "Strong presence in mid-market retail",
    }
    base.update(overrides)
    return base


def _make_output(**overrides: object) -> dict:
    """Build a valid IndustryOutput dict with optional overrides."""
    base: dict = {
        "domain": "dell.com",
        "industry": "Technology",
        "sub_vertical": "Enterprise Hardware",
        "vertical_benchmarks": [_make_benchmark()],
        "industry_trends": [_make_trend()],
        "pain_points": [_make_pain_point()],
        "algolia_case_studies": [_make_case_study()],
        "search_vendor_landscape": [_make_vendor()],
        "industry_summary": (
            "The Technology sector is undergoing rapid AI adoption, "
            "with search and discovery becoming a key differentiator."
        ),
        "roi_context": (
            "In your vertical, Algolia customers see average 37% conversion lift "
            "and 2x search engagement."
        ),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# IndustryInput
# ---------------------------------------------------------------------------


class TestIndustryInput:
    """Tests for IndustryInput schema."""

    def test_valid_input_with_all_fields(self) -> None:
        """Accept valid input with domain, industry, and sub_vertical."""
        obj = IndustryInput(domain="dell.com", industry="Technology", sub_vertical="Enterprise")
        assert obj.domain == "dell.com"
        assert obj.industry == "Technology"
        assert obj.sub_vertical == "Enterprise"

    def test_valid_input_without_sub_vertical(self) -> None:
        """Accept valid input without optional sub_vertical."""
        obj = IndustryInput(domain="dell.com", industry="Retail")
        assert obj.sub_vertical is None

    def test_rejects_extra_fields(self) -> None:
        """extra='forbid' rejects unexpected fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            IndustryInput(domain="dell.com", industry="Retail", unknown_field="bad")  # type: ignore[call-arg]

    def test_rejects_missing_domain(self) -> None:
        """domain is required."""
        with pytest.raises(ValidationError):
            IndustryInput(industry="Retail")  # type: ignore[call-arg]

    def test_rejects_missing_industry(self) -> None:
        """industry is required."""
        with pytest.raises(ValidationError):
            IndustryInput(domain="dell.com")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# VerticalBenchmark
# ---------------------------------------------------------------------------


class TestVerticalBenchmark:
    """Tests for VerticalBenchmark schema."""

    def test_valid_benchmark(self) -> None:
        """Accept a fully populated benchmark."""
        obj = VerticalBenchmark(**_make_benchmark())
        assert obj.metric_name == "Average Conversion Rate"
        assert obj.value == "2.8%"
        assert obj.source == "Baymard Institute 2025"

    def test_valid_benchmark_minimal(self) -> None:
        """Accept benchmark with only required fields."""
        obj = VerticalBenchmark(
            metric_name="AOV", value="$127", source="Statista 2025", industry="Retail"
        )
        assert obj.year == ""
        assert obj.notes == ""

    def test_rejects_missing_metric_name(self) -> None:
        """metric_name is required."""
        data = _make_benchmark()
        del data["metric_name"]
        with pytest.raises(ValidationError):
            VerticalBenchmark(**data)

    def test_rejects_missing_value(self) -> None:
        """value is required."""
        data = _make_benchmark()
        del data["value"]
        with pytest.raises(ValidationError):
            VerticalBenchmark(**data)

    def test_rejects_missing_source(self) -> None:
        """source is required."""
        data = _make_benchmark()
        del data["source"]
        with pytest.raises(ValidationError):
            VerticalBenchmark(**data)

    def test_rejects_missing_industry(self) -> None:
        """industry is required."""
        data = _make_benchmark()
        del data["industry"]
        with pytest.raises(ValidationError):
            VerticalBenchmark(**data)

    def test_rejects_extra_fields(self) -> None:
        """extra='forbid' rejects unexpected fields."""
        data = _make_benchmark(unknown_field="bad")
        with pytest.raises(ValidationError, match="extra_forbidden"):
            VerticalBenchmark(**data)

    def test_serialization_round_trip(self) -> None:
        """model_dump and model_validate round-trip correctly."""
        original = VerticalBenchmark(**_make_benchmark())
        dumped = original.model_dump()
        restored = VerticalBenchmark.model_validate(dumped)
        assert restored == original


# ---------------------------------------------------------------------------
# IndustryTrend
# ---------------------------------------------------------------------------


class TestIndustryTrend:
    """Tests for IndustryTrend schema."""

    def test_valid_trend(self) -> None:
        """Accept a fully populated trend."""
        obj = IndustryTrend(**_make_trend())
        assert obj.trend_name == "AI-Powered Personalization"
        assert obj.relevance_to_search == "high"

    def test_valid_trend_minimal(self) -> None:
        """Accept trend with only required fields."""
        obj = IndustryTrend(
            trend_name="Composable Commerce",
            description="Retailers are adopting composable architectures.",
        )
        assert obj.relevance_to_search == "low"
        assert obj.source == ""
        assert obj.analyst_quote is None

    def test_rejects_invalid_relevance(self) -> None:
        """relevance_to_search must be high/medium/low."""
        data = _make_trend(relevance_to_search="very_high")
        with pytest.raises(ValidationError):
            IndustryTrend(**data)

    def test_rejects_missing_trend_name(self) -> None:
        """trend_name is required."""
        data = _make_trend()
        del data["trend_name"]
        with pytest.raises(ValidationError):
            IndustryTrend(**data)

    def test_rejects_missing_description(self) -> None:
        """description is required."""
        data = _make_trend()
        del data["description"]
        with pytest.raises(ValidationError):
            IndustryTrend(**data)

    def test_rejects_extra_fields(self) -> None:
        """extra='forbid' rejects unexpected fields."""
        data = _make_trend(unknown_field="bad")
        with pytest.raises(ValidationError, match="extra_forbidden"):
            IndustryTrend(**data)

    def test_relevance_high(self) -> None:
        """Accept relevance_to_search='high'."""
        obj = IndustryTrend(**_make_trend(relevance_to_search="high"))
        assert obj.relevance_to_search == "high"

    def test_relevance_medium(self) -> None:
        """Accept relevance_to_search='medium'."""
        obj = IndustryTrend(**_make_trend(relevance_to_search="medium"))
        assert obj.relevance_to_search == "medium"

    def test_relevance_low(self) -> None:
        """Accept relevance_to_search='low'."""
        obj = IndustryTrend(**_make_trend(relevance_to_search="low"))
        assert obj.relevance_to_search == "low"


# ---------------------------------------------------------------------------
# PainPoint
# ---------------------------------------------------------------------------


class TestPainPoint:
    """Tests for PainPoint schema."""

    def test_valid_pain_point(self) -> None:
        """Accept a fully populated pain point."""
        obj = PainPoint(**_make_pain_point())
        assert obj.pain_point == "Poor Search Relevance"
        assert obj.algolia_capability == "AI Search (NeuralSearch)"

    def test_valid_pain_point_minimal(self) -> None:
        """Accept pain point with only required fields."""
        obj = PainPoint(
            pain_point="No Personalization",
            description="Users see the same results regardless of behavior.",
            algolia_capability="Personalization",
        )
        assert obj.severity == "medium"

    def test_rejects_missing_algolia_capability(self) -> None:
        """algolia_capability is required."""
        data = _make_pain_point()
        del data["algolia_capability"]
        with pytest.raises(ValidationError):
            PainPoint(**data)

    def test_rejects_invalid_severity(self) -> None:
        """severity must be critical/high/medium/low."""
        data = _make_pain_point(severity="extreme")
        with pytest.raises(ValidationError):
            PainPoint(**data)

    def test_rejects_extra_fields(self) -> None:
        """extra='forbid' rejects unexpected fields."""
        data = _make_pain_point(unknown_field="bad")
        with pytest.raises(ValidationError, match="extra_forbidden"):
            PainPoint(**data)

    def test_severity_critical(self) -> None:
        """Accept severity='critical'."""
        obj = PainPoint(**_make_pain_point(severity="critical"))
        assert obj.severity == "critical"

    def test_severity_high(self) -> None:
        """Accept severity='high'."""
        obj = PainPoint(**_make_pain_point(severity="high"))
        assert obj.severity == "high"

    def test_severity_low(self) -> None:
        """Accept severity='low'."""
        obj = PainPoint(**_make_pain_point(severity="low"))
        assert obj.severity == "low"


# ---------------------------------------------------------------------------
# AlgoliaCaseStudy
# ---------------------------------------------------------------------------


class TestAlgoliaCaseStudy:
    """Tests for AlgoliaCaseStudy schema."""

    def test_valid_case_study(self) -> None:
        """Accept a fully populated case study."""
        obj = AlgoliaCaseStudy(**_make_case_study())
        assert obj.customer_name == "Lacoste"
        assert len(obj.key_metrics) == 2

    def test_valid_case_study_minimal(self) -> None:
        """Accept case study with only required fields."""
        obj = AlgoliaCaseStudy(customer_name="Acme Corp", industry="Retail")
        assert obj.use_case == ""
        assert obj.key_metrics == []
        assert obj.url is None

    def test_rejects_missing_customer_name(self) -> None:
        """customer_name is required."""
        data = _make_case_study()
        del data["customer_name"]
        with pytest.raises(ValidationError):
            AlgoliaCaseStudy(**data)

    def test_rejects_missing_industry(self) -> None:
        """industry is required."""
        data = _make_case_study()
        del data["industry"]
        with pytest.raises(ValidationError):
            AlgoliaCaseStudy(**data)

    def test_rejects_extra_fields(self) -> None:
        """extra='forbid' rejects unexpected fields."""
        data = _make_case_study(unknown_field="bad")
        with pytest.raises(ValidationError, match="extra_forbidden"):
            AlgoliaCaseStudy(**data)

    def test_key_metrics_empty_list(self) -> None:
        """key_metrics defaults to empty list."""
        obj = AlgoliaCaseStudy(customer_name="Test", industry="Tech")
        assert obj.key_metrics == []

    def test_key_metrics_multiple_entries(self) -> None:
        """key_metrics accepts multiple string entries."""
        obj = AlgoliaCaseStudy(
            customer_name="Test",
            industry="Tech",
            key_metrics=["10% lift", "2x usage", "50ms latency"],
        )
        assert len(obj.key_metrics) == 3


# ---------------------------------------------------------------------------
# SearchVendorMarketShare
# ---------------------------------------------------------------------------


class TestSearchVendorMarketShare:
    """Tests for SearchVendorMarketShare schema."""

    def test_valid_vendor(self) -> None:
        """Accept a fully populated vendor."""
        obj = SearchVendorMarketShare(**_make_vendor())
        assert obj.vendor_name == "Algolia"
        assert obj.estimated_share_pct == 18.5

    def test_valid_vendor_no_share(self) -> None:
        """Accept vendor with unknown market share."""
        obj = SearchVendorMarketShare(vendor_name="Coveo")
        assert obj.estimated_share_pct is None
        assert obj.notes == ""

    def test_rejects_missing_vendor_name(self) -> None:
        """vendor_name is required."""
        with pytest.raises(ValidationError):
            SearchVendorMarketShare(estimated_share_pct=10.0)  # type: ignore[call-arg]

    def test_rejects_extra_fields(self) -> None:
        """extra='forbid' rejects unexpected fields."""
        data = _make_vendor(unknown_field="bad")
        with pytest.raises(ValidationError, match="extra_forbidden"):
            SearchVendorMarketShare(**data)

    def test_share_pct_zero(self) -> None:
        """Accept zero market share."""
        obj = SearchVendorMarketShare(vendor_name="Obscure", estimated_share_pct=0.0)
        assert obj.estimated_share_pct == 0.0

    def test_share_pct_none(self) -> None:
        """Accept None market share."""
        obj = SearchVendorMarketShare(vendor_name="Unknown", estimated_share_pct=None)
        assert obj.estimated_share_pct is None


# ---------------------------------------------------------------------------
# IndustryOutput
# ---------------------------------------------------------------------------


class TestIndustryOutput:
    """Tests for IndustryOutput schema."""

    def test_valid_output_full(self) -> None:
        """Accept a fully populated output."""
        obj = IndustryOutput(**_make_output())
        assert obj.domain == "dell.com"
        assert obj.industry == "Technology"
        assert obj.sub_vertical == "Enterprise Hardware"
        assert len(obj.vertical_benchmarks) == 1
        assert len(obj.industry_trends) == 1
        assert len(obj.pain_points) == 1
        assert len(obj.algolia_case_studies) == 1
        assert len(obj.search_vendor_landscape) == 1
        assert obj.industry_summary != ""
        assert obj.roi_context != ""

    def test_valid_output_minimal(self) -> None:
        """Accept output with only required fields and defaults."""
        obj = IndustryOutput(domain="dell.com", industry="Technology")
        assert obj.sub_vertical is None
        assert obj.vertical_benchmarks == []
        assert obj.industry_trends == []
        assert obj.pain_points == []
        assert obj.algolia_case_studies == []
        assert obj.search_vendor_landscape == []
        assert obj.industry_summary == ""
        assert obj.roi_context == ""

    def test_rejects_missing_domain(self) -> None:
        """domain is required."""
        data = _make_output()
        del data["domain"]
        with pytest.raises(ValidationError):
            IndustryOutput(**data)

    def test_rejects_missing_industry(self) -> None:
        """industry is required."""
        data = _make_output()
        del data["industry"]
        with pytest.raises(ValidationError):
            IndustryOutput(**data)

    def test_rejects_extra_fields(self) -> None:
        """extra='forbid' rejects unexpected fields."""
        data = _make_output(unknown_field="bad")
        with pytest.raises(ValidationError, match="extra_forbidden"):
            IndustryOutput(**data)

    def test_serialization_round_trip(self) -> None:
        """model_dump and model_validate round-trip correctly."""
        original = IndustryOutput(**_make_output())
        dumped = original.model_dump()
        restored = IndustryOutput.model_validate(dumped)
        assert restored == original

    def test_output_with_multiple_benchmarks(self) -> None:
        """Accept output with multiple benchmarks."""
        data = _make_output(
            vertical_benchmarks=[
                _make_benchmark(metric_name="Conversion Rate"),
                _make_benchmark(metric_name="AOV", value="$127"),
                _make_benchmark(metric_name="Bounce Rate", value="45%"),
            ]
        )
        obj = IndustryOutput(**data)
        assert len(obj.vertical_benchmarks) == 3

    def test_output_with_multiple_trends(self) -> None:
        """Accept output with multiple trends."""
        data = _make_output(
            industry_trends=[
                _make_trend(trend_name="AI Personalization"),
                _make_trend(trend_name="Composable Commerce"),
                _make_trend(trend_name="Voice Search"),
            ]
        )
        obj = IndustryOutput(**data)
        assert len(obj.industry_trends) == 3

    def test_output_with_multiple_pain_points(self) -> None:
        """Accept output with multiple pain points."""
        data = _make_output(
            pain_points=[
                _make_pain_point(pain_point="Poor Relevance"),
                _make_pain_point(
                    pain_point="No Personalization",
                    algolia_capability="Personalization",
                ),
                _make_pain_point(pain_point="Slow Search", algolia_capability="InstantSearch UI"),
            ]
        )
        obj = IndustryOutput(**data)
        assert len(obj.pain_points) == 3

    def test_output_without_sub_vertical(self) -> None:
        """Accept output without sub_vertical."""
        data = _make_output(sub_vertical=None)
        obj = IndustryOutput(**data)
        assert obj.sub_vertical is None

    def test_output_empty_lists(self) -> None:
        """Accept output with all empty lists."""
        obj = IndustryOutput(
            domain="test.com",
            industry="Unknown",
            vertical_benchmarks=[],
            industry_trends=[],
            pain_points=[],
            algolia_case_studies=[],
            search_vendor_landscape=[],
        )
        assert len(obj.vertical_benchmarks) == 0
        assert len(obj.industry_trends) == 0

    def test_json_schema_generation(self) -> None:
        """JSON schema can be generated for LLM tool use."""
        schema = IndustryOutput.model_json_schema()
        assert "properties" in schema
        assert "domain" in schema["properties"]
        assert "industry" in schema["properties"]
        assert "vertical_benchmarks" in schema["properties"]
