"""Intel Financial Private schemas -- private company revenue estimation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FinancialPrivateInput(BaseModel):
    """Input contract for the private financial intelligence module."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="The company domain to estimate revenue for.")


class RevenueEstimate(BaseModel):
    """A single revenue estimate from one source in the waterfall."""

    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(
        description=(
            "Origin of estimate, e.g. 'Company press release', "
            "'Industry report', 'Crunchbase funding'."
        ),
    )
    methodology: str = Field(
        description=(
            "How this estimate was derived, e.g. 'Extracted from IDC SaaS market report 2025'."
        ),
    )
    estimated_revenue: float | None = Field(
        default=None,
        description=(
            "Estimated annual revenue in USD as a float. None if source did not yield a number."
        ),
    )
    confidence: Literal["high", "medium", "low"] = Field(
        default="low",
        description="Confidence in this specific estimate.",
    )
    evidence: str = Field(
        default="",
        description="The specific quote, data point, or passage that supports this estimate.",
    )
    evidence_url: str | None = Field(
        default=None,
        description="URL where the evidence was found. None if not available.",
    )
    evidence_tier: Literal["VERIFIED", "WEBFETCH", "WEBSEARCH", "ESTIMATE"] = Field(
        default="ESTIMATE",
        description="Evidence quality tier. Never NO_SOURCE for revenue estimates.",
    )


class FundingData(BaseModel):
    """Venture/private-equity funding information for the company."""

    model_config = ConfigDict(extra="forbid")

    total_funding: float | None = Field(default=None, description="Total funding raised in USD.")
    last_round: str | None = Field(
        default=None, description="Last funding round name, e.g. 'Series D'."
    )
    last_round_amount: float | None = Field(
        default=None, description="Amount raised in last round in USD."
    )
    last_round_date: str | None = Field(
        default=None, description="Date of last round, e.g. '2024-03-15'."
    )
    lead_investor: str | None = Field(default=None, description="Lead investor of the last round.")
    valuation: float | None = Field(default=None, description="Last known valuation in USD.")
    source: str = Field(default="", description="Where this funding data came from.")


class EmployeeRevenueModel(BaseModel):
    """Revenue estimate derived from employee count and industry benchmarks."""

    model_config = ConfigDict(extra="forbid")

    employee_count: int | None = Field(default=None, description="Number of employees.")
    revenue_per_employee: float | None = Field(
        default=None, description="Industry benchmark revenue per employee in USD."
    )
    estimated_revenue: float | None = Field(
        default=None, description="employee_count * revenue_per_employee in USD."
    )
    vertical_benchmark: str = Field(
        default="", description="Industry benchmark used, e.g. 'SaaS average: $200K/employee'."
    )
    confidence: Literal["high", "medium", "low"] = Field(
        default="low", description="Confidence in this model-based estimate."
    )


class CompetitorRevenueEstimate(BaseModel):
    """Revenue estimate for a competitor, used for triangulation."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Competitor company name.")
    domain: str = Field(description="Competitor domain.")
    estimated_revenue: float | None = Field(
        default=None, description="Estimated annual revenue in USD."
    )
    methodology: str = Field(default="", description="How this competitor estimate was derived.")
    confidence: Literal["high", "medium", "low"] = Field(
        default="low", description="Confidence in competitor estimate."
    )


class RevenueWaterfall(BaseModel):
    """Aggregated revenue waterfall from multiple independent sources."""

    model_config = ConfigDict(extra="forbid")

    estimates: list[RevenueEstimate] = Field(
        default_factory=list,
        description="Individual estimates from each source in the waterfall.",
    )
    best_estimate: float | None = Field(
        default=None,
        description=(
            "Best single revenue estimate in USD, derived from "
            "median of available estimates weighted by confidence."
        ),
    )
    best_estimate_confidence: Literal["high", "medium", "low"] = Field(
        default="low",
        description="Confidence in the best estimate.",
    )
    best_estimate_methodology: str = Field(
        default="",
        description="How the best estimate was selected from the waterfall.",
    )
    range_low: float | None = Field(
        default=None, description="Lower bound of revenue range in USD."
    )
    range_high: float | None = Field(
        default=None, description="Upper bound of revenue range in USD."
    )


class FinancialPrivateOutput(BaseModel):
    """Output contract for the private financial intelligence module."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="The domain that was analyzed.")

    # Revenue waterfall
    revenue_waterfall: RevenueWaterfall | None = Field(
        default=None,
        description="Multi-source revenue waterfall with estimates, ranges, and best estimate.",
    )

    # Supporting data
    funding_data: FundingData | None = Field(default=None, description="Venture/PE funding data.")
    employee_revenue_model: EmployeeRevenueModel | None = Field(
        default=None, description="Employee-count-based revenue model."
    )

    # Competitor estimates
    competitor_estimates: list[CompetitorRevenueEstimate] = Field(
        default_factory=list, description="Revenue estimates for competitors."
    )
    comparative_summary: str = Field(
        default="", description="Narrative comparing the company to competitors."
    )

    # Skip info
    skipped: bool = Field(
        default=False, description="True if module was skipped (e.g. company is public)."
    )
    skip_reason: str | None = Field(default=None, description="Reason for skipping, if skipped.")
