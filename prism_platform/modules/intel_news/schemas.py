"""Intel News schemas -- input/output contracts for news and executive media intelligence.

These schemas define the Pydantic models for the intel-news module,
which collects company news, executive quotes, competitor news,
and urgency signals for Algolia sales intelligence.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class NewsInput(BaseModel):
    """Input for the intel-news module."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Website domain to analyze, e.g. 'dell.com'")


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class NewsArticle(BaseModel):
    """A news article about a company within the last 90 days."""

    model_config = ConfigDict(extra="forbid")

    headline: str = Field(description="Article headline or title")
    source: str = Field(description="Publication name, e.g. 'Reuters', 'TechCrunch'")
    date: str = Field(
        description="Publication date as YYYY-MM-DD or approximate, e.g. '2026-03-15'",
    )
    url: str | None = Field(default=None, description="URL to the article")
    summary: str = Field(
        default="",
        description="One to two sentence summary of the article content",
    )
    category: Literal[
        "leadership_change",
        "product_launch",
        "partnership",
        "financial",
        "acquisition",
        "technology",
        "search_related",
        "digital_transformation",
        "other",
    ] = Field(
        default="other",
        description="Category of the news item for downstream filtering",
    )
    is_sell_signal: bool = Field(
        default=False,
        description=(
            "True if this article mentions search, digital transformation, "
            "platform migration, or similar topics relevant to an Algolia pitch"
        ),
    )
    sell_signal_reason: str | None = Field(
        default=None,
        description="Why this article is a sell signal. None if is_sell_signal is False.",
    )
    urgency: Literal["high", "medium", "low"] = Field(
        default="low",
        description=(
            "How urgent this news is for sales outreach. "
            "high = act within days, medium = act within weeks, low = background context"
        ),
    )
    urgency_reason: str | None = Field(
        default=None,
        description="Why this article has the given urgency level. None if urgency is low.",
    )
    company_name: str = Field(
        default="",
        description="Which company this article is about",
    )


class ExecutiveQuote(BaseModel):
    """A verbatim or near-verbatim quote from an executive."""

    model_config = ConfigDict(extra="forbid")

    executive_name: str = Field(description="Full name of the executive")
    executive_title: str = Field(description="Job title of the executive")
    company_name: str = Field(description="Company the executive works for")
    quote: str = Field(
        description=(
            "Verbatim or near-verbatim quote from the executive. "
            "Must be an actual quote, not a paraphrase."
        ),
    )
    context: str = Field(
        description="Where/when the quote was said, e.g. 'CES 2026 keynote' or 'Q4 earnings call'",
    )
    source_type: Literal[
        "interview",
        "keynote",
        "podcast",
        "earnings_call",
        "conference",
        "press_release",
        "social_media",
        "article",
    ] = Field(
        description="Type of source where the quote was found",
    )
    source_url: str | None = Field(
        default=None,
        description="URL to the source of the quote",
    )
    date: str = Field(
        description="Date of the quote as YYYY-MM-DD or approximate",
    )
    classification: Literal[
        "digital_investment",
        "technology_strategy",
        "customer_experience",
        "search_related",
        "ai_related",
        "competitive_positioning",
        "growth_commitment",
        "cost_optimization",
        "other",
    ] = Field(
        default="other",
        description="Classification of the quote's topic area",
    )
    is_high_value: bool = Field(
        default=False,
        description=(
            "True if exec is committing budget, stating priorities, "
            "mentioning pain points, or signaling technology investment"
        ),
    )
    algolia_angle: str | None = Field(
        default=None,
        description=("How this quote connects to an Algolia pitch. None if no clear connection."),
    )


class CompetitorNews(BaseModel):
    """Aggregated news and executive quotes for a single competitor."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Competitor company name")
    domain: str = Field(description="Competitor's primary website domain")
    articles: list[NewsArticle] = Field(
        default_factory=list,
        description="Recent news articles about this competitor",
    )
    exec_quotes: list[ExecutiveQuote] = Field(
        default_factory=list,
        description="Executive quotes from this competitor's leadership",
    )


class UrgencySignal(BaseModel):
    """A signal that indicates time-sensitive sales opportunity."""

    model_config = ConfigDict(extra="forbid")

    signal_type: str = Field(
        description=(
            "Type of urgency signal, e.g. 'leadership_change', "
            "'competitor_tech_move', 'exec_public_commitment'"
        ),
    )
    description: str = Field(
        description="Detailed description of the urgency signal",
    )
    urgency_level: Literal["high", "medium", "low"] = Field(
        description="How urgent this signal is for sales outreach",
    )
    source_headline: str = Field(
        description="Headline of the article or quote that triggered this signal",
    )
    date: str = Field(
        description="Date of the signal as YYYY-MM-DD or approximate",
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class NewsOutput(BaseModel):
    """Full news intelligence output for a prospect domain.

    Contains company news, executive media, urgency signals,
    and competitive news from the last 90 days.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Domain that was analyzed")

    # Part 1 -- Company news (90-day sweep)
    prospect_articles: list[NewsArticle] = Field(
        default_factory=list,
        description="News articles about the prospect company from the last 90 days",
    )

    # Part 2 -- Executive media and interviews
    prospect_exec_quotes: list[ExecutiveQuote] = Field(
        default_factory=list,
        description="Quotes from the prospect's executives",
    )

    # Part 3 -- Signal extraction
    urgency_signals: list[UrgencySignal] = Field(
        default_factory=list,
        description="Time-sensitive signals extracted from news and quotes",
    )
    sell_signal_count: int = Field(
        default=0,
        description="Count of articles with is_sell_signal=True",
    )
    high_value_quote_count: int = Field(
        default=0,
        description="Count of exec quotes with is_high_value=True",
    )

    # Part 4 -- Competitive news
    competitor_news: list[CompetitorNews] = Field(
        default_factory=list,
        description="News and quotes aggregated per competitor",
    )
    competitive_comparison: str = Field(
        default="",
        description=(
            "Summary comparing prospect and competitor news. "
            "e.g. 'Dell announced X. Meanwhile HP did Y.'"
        ),
    )

    # Summary
    news_summary: str = Field(
        default="",
        description=(
            "Overall intelligence summary of all news, quotes, and signals. "
            "2-4 sentences highlighting the most important findings."
        ),
    )
