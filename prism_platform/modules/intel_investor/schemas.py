"""Intel Investor schemas -- input/output contracts for investor intelligence.

These schemas define the Pydantic models for the intel-investor module.
Covers earnings call quotes, Said vs Found mappings, competitor investor intel,
YouTube/media appearances, board composition, and 10-K risk factors.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class InvestorInput(BaseModel):
    """Input for the intel-investor module."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Website domain to analyze, e.g. 'dell.com'")


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class EarningsQuote(BaseModel):
    """A verbatim quote from an earnings call transcript."""

    model_config = ConfigDict(extra="forbid")

    speaker_name: str = Field(description="Name of the executive who spoke")
    speaker_title: str = Field(description="Title of the executive, e.g. 'CEO'")
    quote: str = Field(description="Verbatim or near-verbatim quote from the earnings call")
    context: str = Field(description="What was being discussed when this quote was made")
    quarter: str = Field(description="Quarter label, e.g. 'Q1 FY2026'")
    source: str = Field(description="Source document, e.g. 'Q1 FY2026 Earnings Call Transcript'")
    source_url: str | None = Field(
        default=None,
        description="URL to the transcript source, if available",
    )
    category: Literal[
        "digital_investment",
        "technology_strategy",
        "customer_experience",
        "search_related",
        "ai_related",
        "platform_modernization",
        "revenue_growth",
        "cost_optimization",
        "competitive",
        "pain_signal",
        "other",
    ] = Field(
        default="other",
        description="Category classifying the quote's topic area",
    )
    dollar_amount: str | None = Field(
        default=None,
        description="Exact dollar amount if mentioned, e.g. '$200M in digital'",
    )
    is_commitment: bool = Field(
        default=False,
        description="True if the executive is committing to something specific",
    )
    urgency_level: Literal["high", "medium", "low"] = Field(
        default="low",
        description="How urgent this initiative appears to be for the company",
    )


class SaidVsFound(BaseModel):
    """Maps an executive quote to an Algolia sales angle."""

    model_config = ConfigDict(extra="forbid")

    executive_quote: EarningsQuote = Field(
        description="The executive quote being mapped to an Algolia angle",
    )
    algolia_angle: str = Field(
        description="How this quote connects to Algolia's value proposition",
    )
    recommended_talking_point: str = Field(
        description="What an AE should say to leverage this quote in a sales conversation",
    )
    product_relevance: list[str] = Field(
        default_factory=list,
        description="Relevant Algolia products, e.g. ['Algolia Search', 'AI Search']",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="Confidence that this angle is relevant and actionable",
    )


class CompetitorInvestorIntel(BaseModel):
    """Investor intelligence extracted from a competitor's earnings calls."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Competitor company name")
    ticker: str | None = Field(default=None, description="Competitor ticker symbol, if public")
    domain: str = Field(description="Competitor website domain")
    key_quotes: list[EarningsQuote] = Field(
        default_factory=list,
        description="Key executive quotes from competitor earnings calls",
    )
    competitive_ammunition: list[str] = Field(
        default_factory=list,
        description="How competitor quotes can be used to strengthen our pitch",
    )


class BoardMember(BaseModel):
    """A member of the company's board of directors."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Board member's full name")
    title: str = Field(description="Board title, e.g. 'Independent Director', 'Board Chair'")
    background: str = Field(
        default="",
        description="Brief description of their professional background",
    )
    has_tech_background: bool = Field(
        default=False,
        description="True if the board member has a technology or digital background",
    )
    relevance_note: str = Field(
        default="",
        description="Why this board member is relevant to an Algolia pitch",
    )


class RiskFactor(BaseModel):
    """A risk factor extracted from a 10-K filing."""

    model_config = ConfigDict(extra="forbid")

    category: Literal[
        "technology",
        "cybersecurity",
        "competition",
        "digital_disruption",
        "legacy_systems",
        "other",
    ] = Field(
        default="other",
        description="Risk factor category",
    )
    excerpt: str = Field(description="Excerpt from the 10-K risk factor section")
    filing_source: str = Field(description="Filing source, e.g. '10-K FY2025'")
    algolia_relevance: str = Field(
        default="",
        description="How this risk factor connects to search/discovery",
    )


class YouTubeAppearance(BaseModel):
    """An executive's YouTube or conference appearance."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Video or presentation title")
    channel: str = Field(default="", description="YouTube channel or conference name")
    date: str = Field(default="", description="Date of the appearance, if known")
    url: str | None = Field(default=None, description="URL to the video or presentation")
    speaker: str = Field(default="", description="Name of the executive speaking")
    key_topics: list[str] = Field(
        default_factory=list,
        description="Key topics discussed in the appearance",
    )
    key_quotes: list[str] = Field(
        default_factory=list,
        description="Notable quotes from the appearance",
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class InvestorOutput(BaseModel):
    """Full investor intelligence output for a company.

    Covers earnings call quotes, Said vs Found mappings, competitor investor intel,
    YouTube appearances, board composition, 10-K risk factors, and sales angles.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Primary website domain, e.g. 'dell.com'")
    ticker: str | None = Field(
        default=None,
        description="Stock ticker symbol, e.g. 'DELL'. None for private companies.",
    )

    # Part 1 -- Earnings call quotes (prospect)
    prospect_quotes: list[EarningsQuote] = Field(
        default_factory=list,
        description="Executive quotes from the prospect's earnings calls",
    )
    commitment_count: int = Field(
        default=0,
        description="Number of quotes where an exec commits to something specific",
    )
    pain_signal_count: int = Field(
        default=0,
        description="Number of quotes revealing pain points",
    )

    # Part 2 -- Said vs Found mapping (THE CORE DELIVERABLE)
    said_vs_found: list[SaidVsFound] = Field(
        default_factory=list,
        description="Mappings from executive quotes to Algolia sales angles",
    )

    # Part 3 -- Competitor investor intel
    competitor_intel: list[CompetitorInvestorIntel] = Field(
        default_factory=list,
        description="Investor intelligence from competitor earnings calls",
    )

    # Part 4 -- YouTube and media appearances
    youtube_appearances: list[YouTubeAppearance] = Field(
        default_factory=list,
        description="Executive YouTube and conference appearances",
    )

    # Part 5 -- Board composition
    board_members: list[BoardMember] = Field(
        default_factory=list,
        description="Board of directors with tech background flags",
    )
    board_tech_count: int = Field(
        default=0,
        description="Number of board members with technology backgrounds",
    )

    # Part 6 -- 10-K Risk factors
    risk_factors: list[RiskFactor] = Field(
        default_factory=list,
        description="Technology-related risk factors from 10-K filings",
    )

    # Summary
    investor_summary: str = Field(
        default="",
        description="Executive summary of investor intelligence findings",
    )
    top_sales_angles: list[str] = Field(
        default_factory=list,
        description="Top 5 sales angles for the AE, prioritized by impact",
    )

    # Skip info (for private companies with no data)
    skipped: bool = Field(
        default=False,
        description="True if the module was skipped entirely",
    )
    skip_reason: str | None = Field(
        default=None,
        description="Reason the module was skipped, if applicable",
    )
