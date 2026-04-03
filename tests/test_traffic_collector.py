"""Tests for intel-traffic collector and validator logic.

Includes:
- Validator tests with synthetic data (no API calls)
- Enricher parsing tests (no API calls)
- Helper function tests (brand tagging, seasonal detection, comparative summary)
"""

from __future__ import annotations

from prism_platform.core.types import EvidenceTier, Source
from prism_platform.modules.intel_traffic.enricher import TrafficEnricher
from prism_platform.modules.intel_traffic.module import (
    _build_comparative_summary,
    _detect_seasonal_pattern,
    _extract_brand_terms,
)
from prism_platform.modules.intel_traffic.schemas import (
    CompetitorTraffic,
    DeviceSplit,
    Engagement,
    GeoBreakdown,
    Keyword,
    MonthlyVisit,
    TrafficOutput,
    TrafficSource,
)
from prism_platform.modules.intel_traffic.validator import validate_output


class TestValidator:
    """Test the traffic validator with synthetic data."""

    def _make_valid_output(self) -> TrafficOutput:
        """Build a valid TrafficOutput that passes all 9 checks."""
        return TrafficOutput(
            domain="dell.com",
            monthly_visits=[
                MonthlyVisit(year=2026, month=1, visits=5_000_000),
                MonthlyVisit(year=2026, month=2, visits=4_800_000),
                MonthlyVisit(year=2026, month=3, visits=5_200_000),
            ],
            traffic_sources=[
                TrafficSource(source_type="direct", share_pct=25.0),
                TrafficSource(source_type="organic_search", share_pct=40.0),
            ],
            engagement=Engagement(
                bounce_rate=0.45,
                pages_per_visit=4.2,
                total_visits=15_000_000,
            ),
            top_countries=[
                GeoBreakdown(country="US", country_code="US", share_pct=45.0),
            ],
            organic_keywords=[
                Keyword(keyword="dell laptop", share_pct=5.0),
                Keyword(keyword="gaming laptop", share_pct=3.0),
                Keyword(keyword="workstation", share_pct=2.0),
            ],
        )

    def _make_source(self) -> Source:
        return Source(
            field="test",
            value="test",
            tier=EvidenceTier.VERIFIED,
            source_label="SimilarWeb API",
        )

    def test_valid_output_passes(self) -> None:
        output = self._make_valid_output()
        result = validate_output(output, [self._make_source()], expected_domain="dell.com")
        assert result.passed is True
        assert result.checks_run == 9
        assert result.checks_passed >= 8

    def test_insufficient_monthly_visits_fails(self) -> None:
        output = self._make_valid_output()
        output = output.model_copy(update={"monthly_visits": [
            MonthlyVisit(year=2026, month=1, visits=5_000_000),
        ]})
        result = validate_output(output, [self._make_source()], expected_domain="dell.com")
        assert result.passed is False
        assert any("months" in e.lower() for e in result.errors)

    def test_insufficient_traffic_sources_fails(self) -> None:
        output = self._make_valid_output()
        output = output.model_copy(update={"traffic_sources": [
            TrafficSource(source_type="direct", share_pct=100.0),
        ]})
        result = validate_output(output, [self._make_source()], expected_domain="dell.com")
        assert result.passed is False
        assert any("traffic source" in e.lower() for e in result.errors)

    def test_missing_engagement_is_warning(self) -> None:
        output = self._make_valid_output()
        output = output.model_copy(update={"engagement": None})
        result = validate_output(output, [self._make_source()], expected_domain="dell.com")
        # Engagement missing is a warning, not an error
        assert len(result.warnings) >= 1
        assert any("engagement" in w.lower() for w in result.warnings)

    def test_no_countries_fails(self) -> None:
        output = self._make_valid_output()
        output = output.model_copy(update={"top_countries": []})
        result = validate_output(output, [self._make_source()], expected_domain="dell.com")
        assert result.passed is False
        assert any("geographic" in e.lower() or "country" in e.lower() for e in result.errors)

    def test_insufficient_keywords_is_warning(self) -> None:
        output = self._make_valid_output()
        output = output.model_copy(update={"organic_keywords": [
            Keyword(keyword="dell", share_pct=10.0),
        ]})
        result = validate_output(output, [self._make_source()], expected_domain="dell.com")
        assert len(result.warnings) >= 1
        assert any("keyword" in w.lower() for w in result.warnings)

    def test_domain_mismatch_fails(self) -> None:
        output = self._make_valid_output()
        result = validate_output(output, [self._make_source()], expected_domain="hp.com")
        assert result.passed is False
        assert any("domain mismatch" in e for e in result.errors)

    def test_invalid_share_pct_fails(self) -> None:
        output = self._make_valid_output()
        output = output.model_copy(update={"traffic_sources": [
            TrafficSource(source_type="direct", share_pct=150.0),
            TrafficSource(source_type="organic_search", share_pct=40.0),
        ]})
        result = validate_output(output, [self._make_source()], expected_domain="dell.com")
        assert result.passed is False
        assert any("share_pct" in e for e in result.errors)

    def test_no_sources_fails(self) -> None:
        output = self._make_valid_output()
        result = validate_output(output, [], expected_domain="dell.com")
        assert result.passed is False
        assert any("provenance" in e.lower() for e in result.errors)

    def test_missing_comparative_summary_with_competitors_warns(self) -> None:
        output = self._make_valid_output()
        output = output.model_copy(update={
            "competitor_traffic": [
                CompetitorTraffic(company_name="HP", domain="hp.com"),
            ],
            "comparative_summary": "",
        })
        result = validate_output(output, [self._make_source()], expected_domain="dell.com")
        assert any("comparative_summary" in w for w in result.warnings)


class TestEnricherParsing:
    """Test the Perplexity response parser."""

    def test_parse_rising(self) -> None:
        response = """DIRECTION: rising

Brand interest for Dell has increased significantly. +12% YoY increase based on Google Trends data.
This is supported by strong Q4 performance."""

        result = TrafficEnricher._parse_trends_response("Dell", response)
        assert result.direction == "rising"
        assert result.company_name == "Dell"
        assert result.evidence

    def test_parse_declining(self) -> None:
        response = """DIRECTION: declining

Search interest has dropped year-over-year by approximately 8%. The YoY change is negative."""

        result = TrafficEnricher._parse_trends_response("TestCo", response)
        assert result.direction == "declining"

    def test_parse_stable(self) -> None:
        response = """DIRECTION: stable

Year-over-year change is minimal at +2%."""

        result = TrafficEnricher._parse_trends_response("TestCo", response)
        assert result.direction == "stable"

    def test_parse_insufficient_data(self) -> None:
        response = """DIRECTION: insufficient_data

Not enough Google Trends data available."""

        result = TrafficEnricher._parse_trends_response("TestCo", response)
        assert result.direction == "insufficient_data"

    def test_parse_no_direction_prefix(self) -> None:
        response = """The brand interest is generally going up but there's no clear prefix."""

        result = TrafficEnricher._parse_trends_response("TestCo", response)
        assert result.direction == "insufficient_data"  # default fallback

    def test_evidence_capped_at_500_chars(self) -> None:
        response = "DIRECTION: rising\n" + "x" * 1000
        result = TrafficEnricher._parse_trends_response("TestCo", response)
        assert len(result.evidence) <= 500


class TestBrandTermExtraction:
    """Test the brand keyword tagging helper."""

    def test_dell(self) -> None:
        terms = _extract_brand_terms("Dell Technologies", "dell.com")
        assert "dell" in terms
        # "technologies" should be skipped
        assert "technologies" not in terms

    def test_hp(self) -> None:
        terms = _extract_brand_terms("HP Inc.", "hp.com")
        assert "hp" in terms
        assert "inc." not in terms

    def test_short_words_skipped(self) -> None:
        terms = _extract_brand_terms("AB Co", "ab.com")
        # "co" and "ab" are both too short or in skip list
        assert "co" not in terms


class TestSeasonalPatternDetection:
    """Test the seasonal pattern detection helper."""

    def test_with_peak(self) -> None:
        visits = [
            MonthlyVisit(year=2026, month=1, visits=1_000_000),
            MonthlyVisit(year=2026, month=2, visits=1_000_000),
            MonthlyVisit(year=2026, month=3, visits=1_000_000),
            MonthlyVisit(year=2025, month=11, visits=2_000_000),  # Peak
            MonthlyVisit(year=2025, month=12, visits=2_200_000),  # Peak
        ]
        pattern = _detect_seasonal_pattern(visits)
        assert "Peak" in pattern or "Nov" in pattern or "Dec" in pattern

    def test_insufficient_data(self) -> None:
        visits = [MonthlyVisit(year=2026, month=1, visits=1_000_000)]
        pattern = _detect_seasonal_pattern(visits)
        assert pattern == ""

    def test_stable_traffic(self) -> None:
        visits = [
            MonthlyVisit(year=2026, month=1, visits=1_000_000),
            MonthlyVisit(year=2026, month=2, visits=1_050_000),
            MonthlyVisit(year=2026, month=3, visits=980_000),
        ]
        pattern = _detect_seasonal_pattern(visits)
        assert "stable" in pattern.lower() or pattern == ""


class TestComparativeSummary:
    """Test the comparative summary builder."""

    def test_no_competitors(self) -> None:
        summary = _build_comparative_summary("dell.com", None, [])
        assert summary == ""

    def test_with_competitor_visits(self) -> None:
        engagement = Engagement(total_visits=5_000_000)
        competitors = [
            CompetitorTraffic(
                company_name="HP", domain="hp.com", total_visits=3_000_000
            ),
        ]
        summary = _build_comparative_summary("dell.com", engagement, competitors)
        assert "dell.com" in summary
        assert "HP" in summary

    def test_with_no_prospect_visits(self) -> None:
        competitors = [
            CompetitorTraffic(
                company_name="HP", domain="hp.com", total_visits=3_000_000
            ),
        ]
        summary = _build_comparative_summary("dell.com", None, competitors)
        assert "HP" in summary
        assert "3,000,000" in summary
