"""Unit tests for intel-traffic Pydantic schemas.

Tests cover:
- Valid construction of all models
- Rejection of extra fields (extra='forbid')
- Required field enforcement
- Type validation and constraints
- Literal type enforcement
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.intel_traffic.schemas import (
    CompetitorTraffic,
    Demographics,
    DeviceSplit,
    Engagement,
    GeoBreakdown,
    GoogleTrendsMomentum,
    Keyword,
    MonthlyVisit,
    TrafficInput,
    TrafficOutput,
    TrafficSource,
)


class TestTrafficInput:
    """Tests for TrafficInput schema."""

    def test_valid_input(self) -> None:
        inp = TrafficInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            TrafficInput(domain="dell.com", extra_field="bad")  # type: ignore[call-arg]

    def test_requires_domain(self) -> None:
        with pytest.raises(ValidationError):
            TrafficInput()  # type: ignore[call-arg]


class TestTrafficSource:
    """Tests for TrafficSource schema."""

    def test_valid_source(self) -> None:
        ts = TrafficSource(source_type="organic_search", share_pct=35.5)
        assert ts.source_type == "organic_search"
        assert ts.share_pct == 35.5
        assert ts.visits is None

    def test_with_visits(self) -> None:
        ts = TrafficSource(source_type="direct", share_pct=20.0, visits=1_000_000)
        assert ts.visits == 1_000_000

    def test_rejects_invalid_source_type(self) -> None:
        with pytest.raises(ValidationError):
            TrafficSource(source_type="invalid_type", share_pct=10.0)  # type: ignore[arg-type]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            TrafficSource(source_type="direct", share_pct=10.0, extra="bad")  # type: ignore[call-arg]

    def test_all_source_types(self) -> None:
        valid_types = [
            "direct", "organic_search", "paid_search",
            "social", "referral", "email", "display",
        ]
        for st in valid_types:
            ts = TrafficSource(source_type=st, share_pct=10.0)
            assert ts.source_type == st


class TestMonthlyVisit:
    """Tests for MonthlyVisit schema."""

    def test_valid_monthly_visit(self) -> None:
        mv = MonthlyVisit(year=2026, month=3, visits=5_000_000)
        assert mv.year == 2026
        assert mv.month == 3
        assert mv.visits == 5_000_000

    def test_requires_all_fields(self) -> None:
        with pytest.raises(ValidationError):
            MonthlyVisit(year=2026, month=3)  # type: ignore[call-arg]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            MonthlyVisit(year=2026, month=3, visits=100, extra="bad")  # type: ignore[call-arg]


class TestDeviceSplit:
    """Tests for DeviceSplit schema."""

    def test_valid_device_split(self) -> None:
        ds = DeviceSplit(desktop_pct=60.0, mobile_pct=40.0)
        assert ds.desktop_pct == 60.0
        assert ds.mobile_pct == 40.0
        assert ds.tablet_pct is None

    def test_with_all_fields(self) -> None:
        ds = DeviceSplit(
            desktop_pct=50.0, mobile_pct=45.0, tablet_pct=5.0,
            desktop_visits=500_000, mobile_visits=450_000,
        )
        assert ds.tablet_pct == 5.0
        assert ds.desktop_visits == 500_000

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            DeviceSplit(desktop_pct=50.0, mobile_pct=50.0, extra="bad")  # type: ignore[call-arg]


class TestGeoBreakdown:
    """Tests for GeoBreakdown schema."""

    def test_valid_geo(self) -> None:
        geo = GeoBreakdown(
            country="United States", country_code="US", share_pct=45.2
        )
        assert geo.country == "United States"
        assert geo.country_code == "US"
        assert geo.share_pct == 45.2

    def test_with_visits(self) -> None:
        geo = GeoBreakdown(
            country="Germany", country_code="DE",
            share_pct=8.5, visits=500_000,
        )
        assert geo.visits == 500_000

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            GeoBreakdown(
                country="UK", country_code="GB",
                share_pct=5.0, extra="bad",
            )  # type: ignore[call-arg]


class TestKeyword:
    """Tests for Keyword schema."""

    def test_valid_keyword(self) -> None:
        kw = Keyword(keyword="dell laptop", share_pct=5.2)
        assert kw.keyword == "dell laptop"
        assert kw.is_branded is False

    def test_branded_keyword(self) -> None:
        kw = Keyword(keyword="dell xps 15", share_pct=3.1, is_branded=True)
        assert kw.is_branded is True

    def test_with_all_fields(self) -> None:
        kw = Keyword(
            keyword="gaming laptop", share_pct=2.0,
            change_pct=15.5, search_volume=50_000, is_branded=False,
        )
        assert kw.change_pct == 15.5
        assert kw.search_volume == 50_000


class TestDemographics:
    """Tests for Demographics schema."""

    def test_all_none(self) -> None:
        demo = Demographics()
        assert demo.age_18_24_pct is None
        assert demo.male_pct is None

    def test_with_values(self) -> None:
        demo = Demographics(
            age_25_34_pct=28.5, age_35_44_pct=22.0,
            male_pct=55.0, female_pct=45.0,
        )
        assert demo.age_25_34_pct == 28.5

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            Demographics(age_18_24_pct=10.0, extra="bad")  # type: ignore[call-arg]


class TestEngagement:
    """Tests for Engagement schema."""

    def test_all_none(self) -> None:
        eng = Engagement()
        assert eng.bounce_rate is None
        assert eng.pages_per_visit is None

    def test_with_values(self) -> None:
        eng = Engagement(
            bounce_rate=0.45, pages_per_visit=4.2,
            avg_visit_duration_seconds=180.0, total_visits=5_000_000,
        )
        assert eng.bounce_rate == 0.45
        assert eng.total_visits == 5_000_000


class TestCompetitorTraffic:
    """Tests for CompetitorTraffic schema."""

    def test_minimal(self) -> None:
        ct = CompetitorTraffic(company_name="HP", domain="hp.com")
        assert ct.domain == "hp.com"
        assert ct.total_visits is None
        assert ct.traffic_sources == []

    def test_with_data(self) -> None:
        ct = CompetitorTraffic(
            company_name="HP",
            domain="hp.com",
            total_visits=3_000_000,
            bounce_rate=0.50,
            pages_per_visit=3.5,
            traffic_sources=[
                TrafficSource(source_type="direct", share_pct=30.0),
            ],
            top_keywords=[
                Keyword(keyword="hp laptop", share_pct=8.0),
            ],
        )
        assert len(ct.traffic_sources) == 1
        assert len(ct.top_keywords) == 1

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            CompetitorTraffic(
                company_name="HP", domain="hp.com", extra="bad"
            )  # type: ignore[call-arg]


class TestGoogleTrendsMomentum:
    """Tests for GoogleTrendsMomentum schema."""

    def test_valid_rising(self) -> None:
        gt = GoogleTrendsMomentum(
            company_name="Dell",
            direction="rising",
            yoy_change_description="+12% YoY",
            evidence="Based on Google Trends data",
        )
        assert gt.direction == "rising"

    def test_valid_directions(self) -> None:
        for direction in ("rising", "stable", "declining", "insufficient_data"):
            gt = GoogleTrendsMomentum(
                company_name="Test", direction=direction
            )
            assert gt.direction == direction

    def test_rejects_invalid_direction(self) -> None:
        with pytest.raises(ValidationError):
            GoogleTrendsMomentum(
                company_name="Test", direction="unknown"  # type: ignore[arg-type]
            )


class TestTrafficOutput:
    """Tests for TrafficOutput schema."""

    def test_minimal_output(self) -> None:
        output = TrafficOutput(domain="dell.com")
        assert output.domain == "dell.com"
        assert output.monthly_visits == []
        assert output.engagement is None
        assert output.google_trends is None

    def test_full_output(self) -> None:
        output = TrafficOutput(
            domain="dell.com",
            monthly_visits=[
                MonthlyVisit(year=2026, month=1, visits=5_000_000),
                MonthlyVisit(year=2026, month=2, visits=4_800_000),
                MonthlyVisit(year=2026, month=3, visits=5_200_000),
            ],
            traffic_sources=[
                TrafficSource(source_type="direct", share_pct=25.0),
                TrafficSource(source_type="organic_search", share_pct=40.0),
                TrafficSource(source_type="paid_search", share_pct=15.0),
            ],
            engagement=Engagement(
                bounce_rate=0.45, pages_per_visit=4.2,
                avg_visit_duration_seconds=180.0, total_visits=15_000_000,
            ),
            device_split=DeviceSplit(desktop_pct=60.0, mobile_pct=40.0),
            top_countries=[
                GeoBreakdown(country="US", country_code="US", share_pct=45.0),
            ],
            organic_keywords=[
                Keyword(keyword="dell laptop", share_pct=5.0, is_branded=True),
                Keyword(keyword="gaming laptop", share_pct=3.0),
                Keyword(keyword="workstation", share_pct=2.0),
            ],
            seasonal_pattern="Peak in Nov, Dec; Dip in Jan",
            google_trends=GoogleTrendsMomentum(
                company_name="Dell", direction="stable",
            ),
            competitor_traffic=[
                CompetitorTraffic(company_name="HP", domain="hp.com"),
            ],
            comparative_summary="Dell has more traffic than HP.",
        )
        assert len(output.monthly_visits) == 3
        assert len(output.traffic_sources) == 3
        assert output.engagement is not None
        assert output.google_trends is not None
        assert output.google_trends.direction == "stable"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            TrafficOutput(domain="dell.com", extra="bad")  # type: ignore[call-arg]

    def test_serialization_roundtrip(self) -> None:
        output = TrafficOutput(
            domain="dell.com",
            monthly_visits=[
                MonthlyVisit(year=2026, month=3, visits=5_000_000),
            ],
            traffic_sources=[
                TrafficSource(source_type="direct", share_pct=30.0),
            ],
        )
        dumped = output.model_dump()
        restored = TrafficOutput.model_validate(dumped)
        assert restored.domain == output.domain
        assert len(restored.monthly_visits) == 1
        assert len(restored.traffic_sources) == 1
