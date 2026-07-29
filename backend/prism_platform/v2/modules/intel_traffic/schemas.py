"""Intel Traffic v2 schemas — traffic intelligence output contract.

Covers SimilarWeb traffic data and Google Trends momentum.
Execution strategy: comparative (one call covering prospect + all competitors).

The output describes traffic patterns for the prospect domain alongside
competitor benchmarks in a single research document.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TrafficSourceV2(BaseModel):
    """Traffic source breakdown entry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_type: Literal[
        "direct", "organic_search", "paid_search", "social", "referral", "email", "display"
    ] = Field(description="Traffic source channel")
    share_pct: float = Field(description="Percentage share of total traffic, 0-100")


class CompetitorTrafficSummary(BaseModel):
    """High-level traffic summary for a competitor (from comparative research)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    domain: str = Field(description="Competitor domain, e.g. 'hp.com'")
    monthly_visits_estimate: str = Field(
        description=(
            "Estimated monthly visits as a human-readable range: "
            "'5M-10M', '50M+', '< 1M', 'unavailable'"
        )
    )
    traffic_trend: Literal["growing", "stable", "declining", "unknown"] = Field(
        description="Traffic trend direction based on available data"
    )
    primary_traffic_source: str = Field(
        default="",
        description="Primary traffic source channel for this competitor, e.g. 'organic_search'",
    )
    evidence_url: str | None = Field(
        default=None,
        description="URL where this traffic data was sourced from",
    )


class TrafficV2Output(BaseModel):
    """Traffic intelligence output for a prospect + competitive set.

    Produced by the comparative execution strategy: one Agent API call
    covering the prospect domain and all competitor domains in context.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Prospect domain analyzed, e.g. 'dell.com'")

    # Prospect traffic profile
    monthly_visits_estimate: str = Field(
        description=(
            "Estimated monthly visits for the prospect as a human-readable range: "
            "'5M-10M', '50M+', '< 1M', 'data_unavailable'. "
            "Use SimilarWeb or similar sources. Cite the source."
        )
    )
    traffic_trend: Literal["growing", "stable", "declining", "unknown"] = Field(
        description=(
            "Prospect traffic trend: growing/stable/declining based on YoY or MoM data. "
            "Use 'unknown' if no trend data found."
        )
    )
    traffic_sources: list[TrafficSourceV2] = Field(
        default_factory=list,
        description=(
            "Traffic source breakdown for the prospect. Include the top 3-5 sources if available."
        ),
    )
    top_organic_keywords: list[str] = Field(
        default_factory=list,
        description=(
            "Top 5 organic search keywords driving traffic to the prospect. "
            "Use exact keyword strings, not paraphrases."
        ),
    )
    bounce_rate_description: str = Field(
        default="",
        description=(
            "Bounce rate description: e.g. '55% (above average for retail)' or 'unavailable'"
        ),
    )
    google_trends_direction: Literal["rising", "stable", "declining", "insufficient_data"] = Field(
        description="Google Trends momentum for the brand over the last 12 months"
    )
    seasonal_pattern: str = Field(
        default="",
        description=(
            "Seasonal traffic pattern if detectable: "
            "'Peak in Q4 (Nov-Dec), dip in Q1' or 'No strong seasonality detected'"
        ),
    )

    # Competitive traffic comparison
    competitor_summaries: list[CompetitorTrafficSummary] = Field(
        default_factory=list,
        description=(
            "Traffic summary for each competitor domain in the research context. "
            "Cover all competitors passed in the {competitors} variable."
        ),
    )
    comparative_narrative: str = Field(
        description=(
            "A 3-5 sentence comparative traffic narrative. "
            "How does the prospect's traffic compare to competitors? "
            "Who is growing faster? Any notable traffic patterns or seasonal signals? "
            "Written for a sales rep to read before an account call."
        )
    )

    # Evidence
    primary_data_source: str = Field(
        default="",
        description="Primary data source used: 'SimilarWeb', 'Semrush', 'Ahrefs', 'research', etc.",
    )
    data_freshness: str = Field(
        default="",
        description=(
            "How recent the data is: 'Last 3 months (SimilarWeb)', "
            "'Estimated from 2025 Semrush export', etc."
        ),
    )
