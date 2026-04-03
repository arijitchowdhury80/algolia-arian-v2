"""Intel Industry schemas -- input/output contracts for industry intelligence.

These schemas define the Pydantic models for the intel-industry module,
which collects vertical benchmarks, industry trends, pain points,
Algolia case studies, and search vendor landscape data.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class IndustryInput(BaseModel):
    """Input for the intel-industry module."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Website domain to analyze, e.g. 'dell.com'")
    industry: str = Field(
        description="Primary industry vertical, e.g. 'Retail', 'B2B Manufacturing'"
    )
    sub_vertical: str | None = Field(
        default=None,
        description="Optional sub-vertical, e.g. 'Luxury Fashion', 'Industrial Supplies'",
    )


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class VerticalBenchmark(BaseModel):
    """An industry benchmark metric with source attribution."""

    model_config = ConfigDict(extra="forbid")

    metric_name: str = Field(
        description="Name of the benchmark, e.g. 'Average Conversion Rate', 'Average AOV'"
    )
    value: str = Field(description="Benchmark value as a formatted string, e.g. '2.8%', '$127'")
    source: str = Field(
        description="Source attribution, e.g. 'Baymard Institute 2025', 'Forrester 2026'"
    )
    industry: str = Field(description="Which industry this benchmark applies to")
    year: str = Field(
        default="",
        description="Year the benchmark was published or measured, e.g. '2025'",
    )
    notes: str = Field(
        default="",
        description="Additional context about the benchmark",
    )


class IndustryTrend(BaseModel):
    """A current industry trend relevant to search and digital commerce."""

    model_config = ConfigDict(extra="forbid")

    trend_name: str = Field(
        description="Short name for the trend, e.g. 'AI-Powered Personalization'"
    )
    description: str = Field(description="One to three sentence description of the trend")
    relevance_to_search: Literal["high", "medium", "low"] = Field(
        default="low",
        description=(
            "How relevant this trend is to search/discovery technology. "
            "high = directly about search, medium = related, low = tangential"
        ),
    )
    source: str = Field(
        default="",
        description="Source for this trend, e.g. 'Gartner 2026 Hype Cycle'",
    )
    analyst_quote: str | None = Field(
        default=None,
        description="Verbatim analyst quote about this trend, if available",
    )


class PainPoint(BaseModel):
    """An industry-specific pain point and how Algolia addresses it."""

    model_config = ConfigDict(extra="forbid")

    pain_point: str = Field(
        description="Short name of the pain point, e.g. 'Poor Search Relevance'"
    )
    description: str = Field(description="One to three sentence description of the pain point")
    algolia_capability: str = Field(
        description=(
            "Which Algolia product or feature addresses this pain point, "
            "e.g. 'AI Search with NeuralSearch', 'Algolia Recommend'"
        ),
    )
    severity: Literal["critical", "high", "medium", "low"] = Field(
        default="medium",
        description="How severe this pain point is for the industry",
    )


class AlgoliaCaseStudy(BaseModel):
    """An Algolia customer case study relevant to this industry."""

    model_config = ConfigDict(extra="forbid")

    customer_name: str = Field(
        description="Name of the Algolia customer, e.g. 'Lacoste', 'Under Armour'"
    )
    industry: str = Field(description="Customer's industry vertical")
    use_case: str = Field(
        default="",
        description="What the customer used Algolia for, e.g. 'Site Search + Recommendations'",
    )
    key_metrics: list[str] = Field(
        default_factory=list,
        description=(
            "Quantitative results, e.g. ['37% conversion lift', '2x search usage']. "
            "Include specific numbers when available."
        ),
    )
    url: str | None = Field(
        default=None,
        description="URL to the case study on algolia.com, if available",
    )


class SearchVendorMarketShare(BaseModel):
    """Estimated market share of a search vendor in this industry."""

    model_config = ConfigDict(extra="forbid")

    vendor_name: str = Field(
        description="Name of the search vendor, e.g. 'Algolia', 'Elasticsearch', 'Coveo'"
    )
    estimated_share_pct: float | None = Field(
        default=None,
        description="Estimated market share as a percentage (0-100). None if unknown.",
    )
    notes: str = Field(
        default="",
        description="Additional context about this vendor's presence in the industry",
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class IndustryOutput(BaseModel):
    """Full industry intelligence output for a prospect domain.

    Contains vertical benchmarks, industry trends, pain points,
    Algolia case studies, and search vendor landscape data.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Domain that was analyzed")
    industry: str = Field(description="Primary industry vertical")
    sub_vertical: str | None = Field(
        default=None,
        description="Sub-vertical if applicable",
    )

    # Part 1 -- Benchmarks
    vertical_benchmarks: list[VerticalBenchmark] = Field(
        default_factory=list,
        description="Industry benchmark metrics with source attribution",
    )

    # Part 2 -- Trends
    industry_trends: list[IndustryTrend] = Field(
        default_factory=list,
        description="Current industry trends relevant to search and digital commerce",
    )

    # Part 3 -- Pain points
    pain_points: list[PainPoint] = Field(
        default_factory=list,
        description="Industry-specific pain points with Algolia capability mapping",
    )

    # Part 4 -- Case studies
    algolia_case_studies: list[AlgoliaCaseStudy] = Field(
        default_factory=list,
        description="Algolia customer case studies in this industry",
    )

    # Part 5 -- Vendor landscape
    search_vendor_landscape: list[SearchVendorMarketShare] = Field(
        default_factory=list,
        description="Search vendor market share estimates for this industry",
    )

    # Summary
    industry_summary: str = Field(
        default="",
        description=(
            "2-4 sentence summary of the industry landscape for sales context. "
            "Highlights key benchmarks, trends, and pain points."
        ),
    )
    roi_context: str = Field(
        default="",
        description=(
            "ROI framing for this industry, e.g. "
            "'In your vertical, Algolia customers see average 37% conversion lift'"
        ),
    )
