"""Intel Financial Public v2 schemas — public company financial intelligence.

Covers Yahoo Finance market data, SEC EDGAR filings, earnings call verbatim quotes,
and investor presentation analysis.

Execution strategy: prospect-only (skipped for private companies).
The LLM is instructed to produce exact executive quotes — these are the
highest-value output of this module for sales teams.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EarningsCallQuote(BaseModel):
    """A verbatim executive quote from an earnings call or investor presentation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    speaker: str = Field(description="Speaker name and title, e.g. 'Jeff Clarke, CEO'")
    quote: str = Field(
        description=(
            "Exact verbatim quote. Do NOT paraphrase. "
            "If you cannot find the exact words, do not include this entry."
        )
    )
    date: str = Field(description="Date of the call or presentation, YYYY-MM-DD or 'Q3 FY2025'")
    source: str = Field(
        description="Source: 'Q2 FY2026 Earnings Call', 'Investor Day 2025', '10-K FY2025'"
    )
    source_url: str | None = Field(
        default=None,
        description="URL to the transcript or filing where the quote appears",
    )
    relevance_to_search: Literal["high", "medium", "low"] = Field(
        default="low",
        description=(
            "Relevance to Algolia sales: "
            "high = directly mentions search, discovery, AI, customer experience, "
            "site performance; "
            "medium = mentions digital transformation, tech investment, conversion; "
            "low = general business commentary"
        ),
    )


class AnnualFinancialSummary(BaseModel):
    """Annual financial data for a single fiscal year."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fiscal_year: str = Field(description="Fiscal year label, e.g. 'FY2025'")
    revenue_usd: float | None = Field(
        default=None,
        description="Annual revenue in USD as a float. 88400000000.0 not '$88.4B'.",
    )
    revenue_growth_pct: float | None = Field(
        default=None,
        description="YoY revenue growth as a percentage. 8.1 means 8.1%.",
    )
    gross_margin_pct: float | None = Field(
        default=None,
        description="Gross margin as a percentage.",
    )
    source: str = Field(
        default="",
        description="Source of financial data: '10-K FY2025', 'Yahoo Finance', etc.",
    )


class FinancialPublicV2Output(BaseModel):
    """Financial intelligence output for a publicly traded company.

    Skipped (skipped=True) for private companies or when ticker is unavailable.
    The crown jewel of this module is earnings_call_quotes — verbatim executive
    language about technology investment, customer experience, and digital strategy.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Primary website domain, e.g. 'dell.com'")
    ticker: str | None = Field(
        default=None,
        description="Stock ticker symbol, e.g. 'DELL'. None if private.",
    )

    # Skip logic
    skipped: bool = Field(
        default=False,
        description="True if this module was skipped (private company or no ticker).",
    )
    skip_reason: str | None = Field(
        default=None,
        description="Reason skipped, e.g. 'Private company — no public financial data'",
    )

    # Financial data
    annual_financials: list[AnnualFinancialSummary] = Field(
        default_factory=list,
        description=(
            "Up to 3 years of annual financial data. "
            "Most recent year first. Empty if private/skipped."
        ),
    )
    market_cap_usd: float | None = Field(
        default=None,
        description="Current market cap in USD. None if unavailable.",
    )
    analyst_recommendation: str | None = Field(
        default=None,
        description="Consensus analyst recommendation: 'Buy', 'Hold', 'Sell', 'Strong Buy'",
    )
    analyst_target_price_usd: float | None = Field(
        default=None,
        description="Mean analyst target price in USD.",
    )

    # THE most valuable output: exact words from leadership about technology
    earnings_call_quotes: list[EarningsCallQuote] = Field(
        default_factory=list,
        description=(
            "Verbatim executive quotes from earnings calls and investor presentations. "
            "Prioritise quotes about: digital transformation, search, AI, customer experience, "
            "site performance, conversion, omnichannel, technology investment. "
            "These are sales ammunition — get the exact words."
        ),
    )

    # Investment priorities stated by management
    stated_technology_priorities: list[str] = Field(
        default_factory=list,
        description=(
            "Technology investment priorities stated by management in filings or calls. "
            "e.g. 'AI-powered personalization', 'unified commerce platform', 'search improvement'"
        ),
    )
    digital_revenue_signals: list[str] = Field(
        default_factory=list,
        description=(
            "Any signals about digital/ecommerce revenue: "
            "'Digital revenue grew 15% YoY', '40% of revenue now comes from digital channels'"
        ),
    )

    # Narrative
    financial_narrative: str = Field(
        description=(
            "A 3-5 sentence narrative summarising the financial intelligence. "
            "Lead with revenue trajectory and market position. "
            "Highlight any quotes or stated priorities relevant to search/discovery. "
            "Written for a sales rep to use in account planning."
        )
    )
