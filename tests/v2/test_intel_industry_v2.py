"""Tests for intel-industry v2 module.

intel-industry is a pure Track-2 (LLM) module — no collector, no live API calls.
All tests here are fast schema unit tests. No mocks of fabricated intelligence.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from prism_platform.v2.modules.intel_industry.config import INTEL_INDUSTRY_CONFIG
from prism_platform.v2.modules.intel_industry.schemas import (
    AnalystQuote,
    IndustryIntelOutput,
    VerticalBenchmarkStat,
)
from prism_platform.v2.playbook import PlaybookLoader

PLAYBOOK_PATH = (
    Path(__file__).parent.parent.parent
    / "prism_platform/v2/modules/intel_industry/playbook.md"
)


# ── VerticalBenchmarkStat ──────────────────────────────────────────────────────


class TestVerticalBenchmarkStat:
    def test_valid_stat(self) -> None:
        stat = VerticalBenchmarkStat(
            stat="43% of online shoppers go directly to the search bar on arrival",
            source="Baymard Institute",
            url="https://baymard.com/lists/cart-abandonment-rate",
            relevance="Proves search is the primary discovery path — not navigation.",
        )
        assert stat.source == "Baymard Institute"
        assert stat.url is not None

    def test_url_is_optional(self) -> None:
        stat = VerticalBenchmarkStat(
            stat="Ecommerce search drives 2.4x higher conversion than browsing",
            source="Forrester",
            relevance="Positions search investment as a conversion lever.",
        )
        assert stat.url is None

    def test_is_frozen(self) -> None:
        stat = VerticalBenchmarkStat(
            stat="test stat",
            source="Baymard",
            relevance="relevant",
        )
        with pytest.raises(ValidationError):
            stat.stat = "changed"  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            VerticalBenchmarkStat(
                stat="test",
                source="Baymard",
                relevance="relevant",
                fabricated_field="oops",  # type: ignore[call-arg]
            )


# ── AnalystQuote ───────────────────────────────────────────────────────────────


class TestAnalystQuote:
    def test_valid_quote(self) -> None:
        q = AnalystQuote(
            quote="Retailers that personalise search see 15% uplift in conversion.",
            attribution="Alice Chen, VP Analyst, Forrester",
            source="Forrester Wave: Commerce Search, Q1 2025",
            url="https://forrester.com/report/commerce-search-2025",
            algolia_theme="search-as-conversion-driver",
        )
        assert q.algolia_theme == "search-as-conversion-driver"

    def test_url_and_theme_optional(self) -> None:
        q = AnalystQuote(
            quote="AI-driven search is the new baseline expectation.",
            attribution="Bob Singh, Research Director, Gartner",
            source="Gartner Magic Quadrant for Digital Commerce, 2025",
        )
        assert q.url is None
        assert q.algolia_theme is None

    def test_is_frozen(self) -> None:
        q = AnalystQuote(
            quote="test quote",
            attribution="Analyst Name, Title",
            source="Some Report",
        )
        with pytest.raises(ValidationError):
            q.quote = "changed"  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            AnalystQuote(
                quote="test",
                attribution="Name, Title",
                source="Report",
                bad_field="oops",  # type: ignore[call-arg]
            )


# ── IndustryIntelOutput ────────────────────────────────────────────────────────


class TestIndustryIntelOutput:
    def test_minimal_valid_output(self) -> None:
        out = IndustryIntelOutput(
            domain="example.com",
            vertical="B2C Fashion & Apparel",
            trend_summary="Fast-fashion search volumes grew 18% YoY.",
            algolia_relevance_narrative=(
                "Fashion retailers face acute catalogue churn — new SKUs weekly. "
                "Algolia's real-time indexing and NLP handling of colour/style queries "
                "directly address the two highest-abandonment scenarios in this vertical."
            ),
        )
        assert out.domain == "example.com"
        assert out.benchmark_stats == []
        assert out.analyst_quotes == []
        assert out.sources == []

    def test_full_output(self) -> None:
        stat = VerticalBenchmarkStat(
            stat="43% of shoppers use site search as primary discovery",
            source="Baymard Institute",
            relevance="Search-first behaviour makes search UX a top conversion lever.",
        )
        quote = AnalystQuote(
            quote="Search is the new homepage for fashion shoppers.",
            attribution="Jane Doe, Analyst, Forrester",
            source="Forrester Wave Q1 2025",
            algolia_theme="search-as-conversion-driver",
        )
        out = IndustryIntelOutput(
            domain="zara.com",
            vertical="B2C Fashion & Apparel",
            benchmark_stats=[stat],
            trend_summary="AI search adoption accelerated in fashion in 2025.",
            analyst_quotes=[quote],
            algolia_relevance_narrative="Algolia's AI ranking handles fast-moving SKUs natively.",
            sources=["https://forrester.com/wave-2025"],
        )
        assert len(out.benchmark_stats) == 1
        assert len(out.analyst_quotes) == 1
        assert out.sources[0].startswith("https://")

    def test_domain_required(self) -> None:
        with pytest.raises(ValidationError):
            IndustryIntelOutput(  # type: ignore[call-arg]
                vertical="B2C Fashion",
                trend_summary="trend",
                algolia_relevance_narrative="narrative",
            )

    def test_trend_summary_required(self) -> None:
        with pytest.raises(ValidationError):
            IndustryIntelOutput(  # type: ignore[call-arg]
                domain="example.com",
                vertical="B2C Fashion",
                algolia_relevance_narrative="narrative",
            )

    def test_algolia_relevance_narrative_required(self) -> None:
        with pytest.raises(ValidationError):
            IndustryIntelOutput(  # type: ignore[call-arg]
                domain="example.com",
                vertical="B2C Fashion",
                trend_summary="trend",
            )

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            IndustryIntelOutput(
                domain="example.com",
                vertical="B2C Fashion",
                trend_summary="trend",
                algolia_relevance_narrative="narrative",
                invented_field="oops",  # type: ignore[call-arg]
            )

    def test_json_schema_has_expected_fields(self) -> None:
        schema = IndustryIntelOutput.model_json_schema()
        props = schema["properties"]
        assert "domain" in props
        assert "vertical" in props
        assert "benchmark_stats" in props
        assert "trend_summary" in props
        assert "analyst_quotes" in props
        assert "algolia_relevance_narrative" in props
        assert "sources" in props


# ── Config ─────────────────────────────────────────────────────────────────────


class TestIntelIndustryConfig:
    def test_name(self) -> None:
        assert INTEL_INDUSTRY_CONFIG.name == "intel-industry"

    def test_version(self) -> None:
        assert INTEL_INDUSTRY_CONFIG.version.startswith("2.")

    def test_layer(self) -> None:
        assert INTEL_INDUSTRY_CONFIG.layer == "intelligence"

    def test_cost_tier(self) -> None:
        assert INTEL_INDUSTRY_CONFIG.cost_tier == "pro-search"

    def test_composes_intel_company(self) -> None:
        assert "intel-company" in INTEL_INDUSTRY_CONFIG.composes

    def test_no_api_clients(self) -> None:
        # LLM-only module — no external API clients required
        assert INTEL_INDUSTRY_CONFIG.api_clients == []

    def test_cache_ttl_appropriate(self) -> None:
        # Industry benchmarks are slow-moving — 30-day cache is correct
        assert INTEL_INDUSTRY_CONFIG.cache_ttl_days >= 14


# ── Playbook ───────────────────────────────────────────────────────────────────


class TestIntelIndustryPlaybook:
    def test_playbook_exists(self) -> None:
        assert PLAYBOOK_PATH.exists()

    def test_execution_strategy_is_prospect_only(self) -> None:
        loader = PlaybookLoader()
        meta, _ = loader.load(PLAYBOOK_PATH)
        assert meta.execution_strategy == "prospect-only"

    def test_playbook_resolves_domain_and_company(self) -> None:
        loader = PlaybookLoader()
        context_kwargs = {
            "audit_id": "test-123",
            "account_domain": "nordstrom.com",
            "company_name": "Nordstrom",
            "industry": "B2C Fashion & Apparel",
        }
        from prism_platform.v2.types import ExecutionContextV2

        context = ExecutionContextV2(**context_kwargs)
        _, body = loader.load(PLAYBOOK_PATH)
        resolved = loader.resolve(body, context)
        assert "nordstrom.com" in resolved
        assert "Nordstrom" in resolved
        assert "B2C Fashion & Apparel" in resolved
