"""Intel Investor v2 schemas — investor and executive intelligence output.

Track-1 (deterministic) collects Yahoo Finance signals for public companies:
stock price, 3-year revenue history, analyst consensus, recent news.

Track-2 (LLM) extracts verbatim executive quotes tagged with Algolia themes,
and handles private companies where Track-1 has nothing to offer.

Execution strategy: prospect-only (one set of outputs per company, not
comparative across competitors).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RevenueDataPoint(BaseModel):
    """One year of revenue data from a structured financial source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    year: int = Field(description="Fiscal year as a 4-digit integer, e.g. 2024")
    revenue_usd: float = Field(description="Total revenue in USD (not billions — raw dollars)")
    source: str = Field(
        description="Where this figure came from, e.g. 'yahoo_finance', 'sec_10k'"
    )


class ExecutiveQuote(BaseModel):
    """A verbatim executive quote, tagged with an Algolia sales theme."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    quote: str = Field(description="Verbatim quote from the executive — no paraphrasing")
    speaker: str = Field(description="Executive name, e.g. 'Jeff Clarke'")
    title: str = Field(description="Executive title at time of quote, e.g. 'CEO'")
    theme: str = Field(
        description=(
            "Algolia sales theme this quote maps to, e.g. 'search_conversion', "
            "'digital_experience', 'cost_reduction', 'developer_velocity', 'personalization'"
        )
    )
    source: str = Field(
        description="Source label, e.g. 'Q3 FY2025 Earnings Call' or '10-K FY2024 MD&A'"
    )


class InvestorIntelOutput(BaseModel):
    """Investor and executive intelligence for a prospect.

    For public companies, financial signals are sourced deterministically
    from Yahoo Finance (Track 1). For private companies, financial fields
    are empty and the LLM (Track 2) handles executive quote research.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Prospect domain analyzed")
    is_public: bool = Field(
        default=False,
        description="True if the company is publicly traded with SEC filings",
    )
    ticker: str | None = Field(
        default=None,
        description="Stock ticker symbol, e.g. 'DELL'. Null for private companies.",
    )

    # ── Track-1 fields (Yahoo Finance — public companies only) ────────────────

    stock_price: float | None = Field(
        default=None,
        description=(
            "Current stock price in USD at time of collection. "
            "Null if private or ticker unavailable."
        ),
    )
    revenue_3yr: list[RevenueDataPoint] = Field(
        default_factory=list,
        description=(
            "Up to 3 years of annual revenue data in descending order (most recent first). "
            "Empty for private companies."
        ),
    )
    analyst_consensus: str | None = Field(
        default=None,
        description=(
            "Analyst recommendation consensus: 'Buy', 'Hold', 'Sell', or a mean score label. "
            "Null if private or no analyst coverage."
        ),
    )
    recent_news: list[str] = Field(
        default_factory=list,
        description=(
            "Up to 5 recent news headlines from Yahoo Finance. "
            "Empty if private or no news available."
        ),
    )

    # ── Track-2 fields (LLM — all companies) ─────────────────────────────────

    executive_quotes: list[ExecutiveQuote] = Field(
        default_factory=list,
        description=(
            "Verbatim executive quotes tagged with Algolia sales themes. "
            "For public companies, drawn from earnings calls and 10-K MD&A. "
            "For private companies, from CEO/founder interviews via Perplexity."
        ),
    )

    # ── Provenance ────────────────────────────────────────────────────────────

    sources: list[str] = Field(
        default_factory=list,
        description=(
            "Citation URLs for every data point in this output. "
            "One URL per Track-1 Yahoo Finance fetch, plus one per executive quote source."
        ),
    )
