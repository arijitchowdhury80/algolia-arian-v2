"""Intel Financial Public schemas -- input/output contracts for public company financials.

These schemas define the Pydantic models for the intel-financial-public module.
Covers Yahoo Finance market data, SEC EDGAR filings, investor presentations,
and competitor comparative financials.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class FinancialPublicInput(BaseModel):
    """Input for the intel-financial-public module."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Website domain to analyze, e.g. 'dell.com'")
    ticker: str = Field(description="Stock ticker symbol, e.g. 'DELL'")


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class AnnualFinancials(BaseModel):
    """Annual financial data for a single fiscal year."""

    model_config = ConfigDict(extra="forbid")

    fiscal_year: str = Field(description="Fiscal year label, e.g. 'FY2025'")
    revenue: float | None = Field(
        default=None,
        description="Annual revenue in USD as a float, e.g. 88400000000.0",
    )
    net_income: float | None = Field(
        default=None,
        description="Annual net income in USD as a float",
    )
    gross_margin_pct: float | None = Field(
        default=None,
        description="Gross margin as a percentage, e.g. 23.5 for 23.5%",
    )
    operating_margin_pct: float | None = Field(
        default=None,
        description="Operating margin as a percentage, e.g. 6.2 for 6.2%",
    )
    revenue_growth_pct: float | None = Field(
        default=None,
        description="Year-over-year revenue growth as a percentage, e.g. 8.1 for 8.1%",
    )


class MarketData(BaseModel):
    """Current market data from Yahoo Finance."""

    model_config = ConfigDict(extra="forbid")

    market_cap: float | None = Field(
        default=None,
        description="Market capitalization in USD as a float",
    )
    stock_price: float | None = Field(
        default=None,
        description="Current stock price in USD",
    )
    fifty_two_week_high: float | None = Field(
        default=None,
        description="52-week high stock price in USD",
    )
    fifty_two_week_low: float | None = Field(
        default=None,
        description="52-week low stock price in USD",
    )
    pe_ratio: float | None = Field(
        default=None,
        description="Trailing price-to-earnings ratio",
    )
    forward_pe: float | None = Field(
        default=None,
        description="Forward price-to-earnings ratio",
    )


class AnalystData(BaseModel):
    """Analyst consensus data from Yahoo Finance."""

    model_config = ConfigDict(extra="forbid")

    recommendation: str | None = Field(
        default=None,
        description="Analyst consensus recommendation, e.g. 'Buy', 'Hold', 'Sell'",
    )
    target_price: float | None = Field(
        default=None,
        description="Mean analyst target price in USD",
    )
    number_of_analysts: int | None = Field(
        default=None,
        description="Number of analysts covering the stock",
    )


class SECInsight(BaseModel):
    """Insight extracted from an SEC filing (10-K or 10-Q)."""

    model_config = ConfigDict(extra="forbid")

    filing_type: Literal["10-K", "10-Q"] = Field(
        description="SEC filing type: 10-K (annual) or 10-Q (quarterly)"
    )
    filing_date: str = Field(description="Filing date in YYYY-MM-DD format")
    filing_url: str | None = Field(
        default=None,
        description="URL to the filing on SEC EDGAR",
    )
    digital_revenue_pct: float | None = Field(
        default=None,
        description="Digital revenue as a percentage of total revenue, if disclosed",
    )
    technology_mentions: list[str] = Field(
        default_factory=list,
        description=(
            "Technology keywords mentioned in the filing: "
            "'search', 'AI', 'personalization', 'machine learning', etc."
        ),
    )
    key_excerpts: list[str] = Field(
        default_factory=list,
        description="Notable excerpts from the filing relevant to digital/tech strategy",
    )
    management_discussion_summary: str = Field(
        default="",
        description="Summary of Management Discussion & Analysis section",
    )


class InvestorPresentation(BaseModel):
    """Insight extracted from an investor presentation or IR page."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Presentation title")
    date: str = Field(description="Presentation date in YYYY-MM-DD or approximate format")
    url: str | None = Field(
        default=None,
        description="URL to the presentation or IR page",
    )
    strategic_priorities: list[str] = Field(
        default_factory=list,
        description="Strategic priorities mentioned in the presentation",
    )
    digital_commitments: list[str] = Field(
        default_factory=list,
        description="Commitments to digital transformation or e-commerce",
    )
    technology_roadmap: list[str] = Field(
        default_factory=list,
        description="Technology roadmap items mentioned",
    )
    search_mentions: list[str] = Field(
        default_factory=list,
        description="Any mentions of search, discovery, or recommendation technology",
    )
    key_quotes: list[str] = Field(
        default_factory=list,
        description="Verbatim quotes from executives about strategy or technology",
    )


class CompetitorFinancials(BaseModel):
    """Basic financial data for a competitor company."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Competitor company name")
    ticker: str = Field(description="Competitor stock ticker symbol")
    revenue: float | None = Field(
        default=None,
        description="Most recent annual revenue in USD",
    )
    revenue_growth_pct: float | None = Field(
        default=None,
        description="Year-over-year revenue growth as a percentage",
    )
    market_cap: float | None = Field(
        default=None,
        description="Market capitalization in USD",
    )
    gross_margin_pct: float | None = Field(
        default=None,
        description="Gross margin as a percentage",
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class FinancialPublicOutput(BaseModel):
    """Full financial intelligence output for a publicly traded company.

    Covers structured financials from Yahoo Finance, SEC filing insights,
    investor presentation analysis, and competitor comparative data.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Primary website domain, e.g. 'dell.com'")
    ticker: str = Field(description="Stock ticker symbol, e.g. 'DELL'")

    # Part 1 -- Structured financials (Yahoo Finance)
    annual_financials: list[AnnualFinancials] = Field(
        default_factory=list,
        description="Up to 3 years of annual financial data",
    )
    market_data: MarketData | None = Field(
        default=None,
        description="Current market data snapshot",
    )
    analyst_data: AnalystData | None = Field(
        default=None,
        description="Analyst consensus data",
    )

    # Part 2 -- SEC filings
    sec_insights: list[SECInsight] = Field(
        default_factory=list,
        description="Insights extracted from recent SEC filings (10-K, 10-Q)",
    )

    # Part 3 -- Investor presentations
    investor_presentations: list[InvestorPresentation] = Field(
        default_factory=list,
        description="Insights from investor presentations and IR materials",
    )

    # Part 4 -- Comparative
    competitor_financials: list[CompetitorFinancials] = Field(
        default_factory=list,
        description="Financial data for competitor companies",
    )
    comparative_summary: str = Field(
        default="",
        description=(
            "Narrative summary comparing the company's financial position "
            "to its competitors. Empty if no competitor data available."
        ),
    )

    # Skip info
    skipped: bool = Field(
        default=False,
        description="True if the module was skipped (private company or no ticker)",
    )
    skip_reason: str | None = Field(
        default=None,
        description="Reason the module was skipped, if applicable",
    )
