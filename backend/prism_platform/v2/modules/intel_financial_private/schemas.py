"""Intel Financial Private v2 schemas — revenue estimation for private companies.

Multi-source waterfall estimation. Each source produces a RevenueEstimateV2.
The LLM is instructed to triangulate from multiple sources and produce a
best_estimate with confidence rating.

Execution strategy: prospect-only (run only when company is private).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RevenueEstimateV2(BaseModel):
    """A single revenue estimate from one source in the waterfall."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_name: str = Field(
        description=(
            "Origin of estimate: 'Company press release', 'Industry report', "
            "'Crunchbase funding', 'Employee count model', 'Inc 5000 ranking', etc."
        )
    )
    estimated_revenue_usd: float | None = Field(
        default=None,
        description="Estimated annual revenue in USD as a float. None if source gave no number.",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence: high=direct disclosure, medium=industry report, low=model estimate"
    )
    evidence: str = Field(
        description=(
            "The specific quote, data point, or methodology that supports this estimate. "
            "For employee model: 'LinkedIn: ~4,500 employees x $180K/employee (SaaS benchmark)'"
        )
    )
    evidence_url: str | None = Field(
        default=None,
        description="URL where the evidence was found. None if not available.",
    )


class FundingDataV2(BaseModel):
    """Funding data for private companies."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    total_funding_usd: float | None = Field(
        default=None, description="Total funding raised in USD."
    )
    last_round_name: str | None = Field(
        default=None, description="Last round name: 'Series D', 'Growth Equity', 'Seed', etc."
    )
    last_round_amount_usd: float | None = Field(
        default=None, description="Amount raised in last round in USD."
    )
    last_round_date: str | None = Field(
        default=None, description="Date of last round, YYYY-MM-DD or approximate."
    )
    lead_investor: str | None = Field(default=None, description="Lead investor of the last round.")
    valuation_usd: float | None = Field(default=None, description="Last known valuation in USD.")
    source_url: str | None = Field(
        default=None, description="Crunchbase or PitchBook URL for this funding data."
    )


class FinancialPrivateV2Output(BaseModel):
    """Revenue estimation output for a private company.

    Uses a waterfall approach: try multiple sources, triangulate, produce a
    best estimate with confidence and full source trail.

    If the company is public, this module is skipped (skipped=True).
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Company domain, e.g. 'company.com'")

    # Skip logic
    skipped: bool = Field(
        default=False,
        description="True if skipped because the company is public (has ticker).",
    )
    skip_reason: str | None = Field(
        default=None,
        description="'Public company — use intel-financial-public instead'",
    )

    # Revenue waterfall
    revenue_estimates: list[RevenueEstimateV2] = Field(
        default_factory=list,
        description=(
            "All revenue estimates found, one per source. "
            "Cover these sources in order: press releases, industry reports, "
            "Crunchbase/PitchBook, employee count model, Inc 5000/Deloitte ranking. "
            "Include all sources tried, even those that yielded no number."
        ),
    )
    best_estimate_usd: float | None = Field(
        default=None,
        description=(
            "Your best estimate of annual revenue in USD, triangulated from all sources. "
            "None if insufficient data."
        ),
    )
    estimate_range: str = Field(
        default="",
        description=(
            "Revenue range as a human-readable string: '$50M-$100M', '$500M+', 'Under $10M', "
            "or 'Insufficient data to estimate'"
        ),
    )
    confidence: Literal["high", "medium", "low", "insufficient_data"] = Field(
        default="insufficient_data",
        description=(
            "Overall confidence in best_estimate: "
            "high=direct disclosure, medium=2+ corroborating sources, "
            "low=single source or model-only, insufficient_data=no reliable estimate"
        ),
    )

    # Funding intelligence
    funding_data: FundingDataV2 | None = Field(
        default=None,
        description="Funding history if found. Null if private equity / bootstrapped / unknown.",
    )

    # Narrative
    financial_narrative: str = Field(
        description=(
            "A 2-4 sentence summary of the financial picture for this private company. "
            "Lead with the best revenue estimate and confidence level. "
            "Note funding history if relevant. "
            "Written for a sales rep to understand budget context."
        )
    )
