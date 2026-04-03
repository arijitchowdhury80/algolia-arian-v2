"""Intel Traffic schemas -- input/output contracts for traffic intelligence.

These schemas define the Pydantic models for the intel-traffic module.
All output models use extra='forbid' to reject unexpected fields and
catch schema drift immediately.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class TrafficInput(BaseModel):
    """Input for the intel-traffic module."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Website domain to analyze, e.g. 'dell.com'")


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class TrafficSource(BaseModel):
    """Breakdown of traffic by source type."""

    model_config = ConfigDict(extra="forbid")

    source_type: Literal[
        "direct",
        "organic_search",
        "paid_search",
        "social",
        "referral",
        "email",
        "display",
    ] = Field(description="Traffic source channel type")
    share_pct: float = Field(description="Percentage share of total traffic, 0-100")
    visits: int | None = Field(
        default=None,
        description="Absolute visit count for this source, if available",
    )


class MonthlyVisit(BaseModel):
    """Monthly visit count for a single month."""

    model_config = ConfigDict(extra="forbid")

    year: int = Field(description="Year of the data point, e.g. 2026")
    month: int = Field(description="Month of the data point, 1-12")
    visits: int = Field(description="Total visits for this month")


class DeviceSplit(BaseModel):
    """Desktop vs mobile vs tablet traffic split."""

    model_config = ConfigDict(extra="forbid")

    desktop_pct: float = Field(description="Desktop traffic percentage, 0-100")
    mobile_pct: float = Field(description="Mobile traffic percentage, 0-100")
    tablet_pct: float | None = Field(
        default=None,
        description="Tablet traffic percentage, 0-100. May not be available.",
    )
    desktop_visits: int | None = Field(
        default=None,
        description="Absolute desktop visit count",
    )
    mobile_visits: int | None = Field(
        default=None,
        description="Absolute mobile visit count",
    )


class GeoBreakdown(BaseModel):
    """Traffic breakdown by country."""

    model_config = ConfigDict(extra="forbid")

    country: str = Field(description="Country name, e.g. 'United States'")
    country_code: str = Field(description="ISO 3166-1 alpha-2 country code, e.g. 'US'")
    share_pct: float = Field(
        description="Percentage share of total traffic from this country, 0-100"
    )
    visits: int | None = Field(
        default=None,
        description="Absolute visit count from this country",
    )


class Keyword(BaseModel):
    """A search keyword driving traffic to the site."""

    model_config = ConfigDict(extra="forbid")

    keyword: str = Field(description="The search keyword text")
    share_pct: float = Field(description="Percentage of search traffic from this keyword, 0-100")
    change_pct: float | None = Field(
        default=None,
        description="Percentage change in share vs previous period",
    )
    search_volume: int | None = Field(
        default=None,
        description="Estimated monthly search volume for this keyword",
    )
    is_branded: bool = Field(
        default=False,
        description="True if the keyword contains the brand name",
    )


class Demographics(BaseModel):
    """Audience demographics for the website."""

    model_config = ConfigDict(extra="forbid")

    age_18_24_pct: float | None = Field(
        default=None, description="Percentage of audience aged 18-24"
    )
    age_25_34_pct: float | None = Field(
        default=None, description="Percentage of audience aged 25-34"
    )
    age_35_44_pct: float | None = Field(
        default=None, description="Percentage of audience aged 35-44"
    )
    age_45_54_pct: float | None = Field(
        default=None, description="Percentage of audience aged 45-54"
    )
    age_55_64_pct: float | None = Field(
        default=None, description="Percentage of audience aged 55-64"
    )
    age_65_plus_pct: float | None = Field(
        default=None, description="Percentage of audience aged 65+"
    )
    male_pct: float | None = Field(default=None, description="Percentage of male audience")
    female_pct: float | None = Field(default=None, description="Percentage of female audience")


class Engagement(BaseModel):
    """Engagement metrics for the website."""

    model_config = ConfigDict(extra="forbid")

    bounce_rate: float | None = Field(
        default=None,
        description="Bounce rate as a decimal 0-1, e.g. 0.45 = 45%",
    )
    pages_per_visit: float | None = Field(
        default=None,
        description="Average pages viewed per visit",
    )
    avg_visit_duration_seconds: float | None = Field(
        default=None,
        description="Average visit duration in seconds",
    )
    total_visits: int | None = Field(
        default=None,
        description="Total visits in the reporting period",
    )


class CompetitorTraffic(BaseModel):
    """Traffic profile for a competitor domain."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Competitor company name")
    domain: str = Field(description="Competitor domain, e.g. 'hp.com'")
    total_visits: int | None = Field(
        default=None,
        description="Total visits in the reporting period",
    )
    bounce_rate: float | None = Field(
        default=None,
        description="Bounce rate as a decimal 0-1",
    )
    pages_per_visit: float | None = Field(
        default=None,
        description="Average pages per visit",
    )
    traffic_sources: list[TrafficSource] = Field(
        default_factory=list,
        description="Traffic source breakdown for this competitor",
    )
    top_keywords: list[Keyword] = Field(
        default_factory=list,
        description="Top organic keywords for this competitor",
    )
    device_split: DeviceSplit | None = Field(
        default=None,
        description="Device split for this competitor",
    )


class GoogleTrendsMomentum(BaseModel):
    """Google Trends momentum assessment via Perplexity."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Company or brand name assessed")
    direction: Literal["rising", "stable", "declining", "insufficient_data"] = Field(
        description="Trend direction based on year-over-year analysis"
    )
    yoy_change_description: str = Field(
        default="",
        description="Human-readable description of year-over-year change",
    )
    evidence: str = Field(
        default="",
        description="Supporting evidence or source citation for the assessment",
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class TrafficOutput(BaseModel):
    """Full traffic intelligence output for a prospect domain.

    Combines SimilarWeb API data with Google Trends momentum from Perplexity
    to produce a comprehensive traffic profile.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Domain analyzed, e.g. 'dell.com'")

    # Core metrics
    monthly_visits: list[MonthlyVisit] = Field(
        default_factory=list,
        description="Monthly visit counts for the last 6 months",
    )
    traffic_sources: list[TrafficSource] = Field(
        default_factory=list,
        description="Traffic source breakdown (direct, organic, paid, etc.)",
    )
    engagement: Engagement | None = Field(
        default=None,
        description="Engagement metrics: bounce rate, pages/visit, duration",
    )
    device_split: DeviceSplit | None = Field(
        default=None,
        description="Desktop vs mobile traffic split",
    )
    demographics: Demographics | None = Field(
        default=None,
        description="Audience demographics (age and gender distribution)",
    )

    # Geo and keywords
    top_countries: list[GeoBreakdown] = Field(
        default_factory=list,
        description="Top countries by traffic share",
    )
    organic_keywords: list[Keyword] = Field(
        default_factory=list,
        description="Top organic search keywords driving traffic",
    )
    paid_keywords: list[Keyword] = Field(
        default_factory=list,
        description="Top paid search keywords",
    )

    # Seasonal and trends
    seasonal_pattern: str = Field(
        default="",
        description="Detected seasonal pattern, e.g. 'Peak in Q4 (Nov-Dec), dip in Q1'",
    )
    google_trends: GoogleTrendsMomentum | None = Field(
        default=None,
        description="Google Trends momentum assessment for the brand",
    )

    # Competitive
    competitor_traffic: list[CompetitorTraffic] = Field(
        default_factory=list,
        description="Traffic profiles for competitor domains",
    )
    comparative_summary: str = Field(
        default="",
        description="Narrative summary comparing prospect traffic to competitors",
    )
