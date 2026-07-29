"""Intel News v2 schemas — news intelligence and urgency signal output.

Covers company news, executive media activity, and competitor news.
Each article is classified with urgency and sell_signal status.

Execution strategy: prospect-only (one call for the prospect, covering
competitor news in the same call).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Urgency levels for sales action prioritization
UrgencyLevel = Literal["high", "medium", "low"]

# News article category taxonomy
NewsCategory = Literal[
    "leadership_change",
    "product_launch",
    "partnership",
    "financial",
    "acquisition",
    "technology",
    "search_related",
    "digital_transformation",
    "platform_migration",
    "funding_event",
    "other",
]


class NewsArticleV2(BaseModel):
    """A news article about a company within the last 90 days."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    headline: str = Field(description="Article headline or title")
    source: str = Field(description="Publication name: 'Reuters', 'TechCrunch', 'WSJ'")
    date: str = Field(description="Publication date as YYYY-MM-DD or approximate")
    url: str | None = Field(default=None, description="URL to the article")
    summary: str = Field(
        default="",
        description="One to two sentence summary of the article content",
    )
    category: NewsCategory = Field(
        default="other",
        description="Category for downstream filtering",
    )
    is_sell_signal: bool = Field(
        default=False,
        description=(
            "True if this article mentions: search quality, platform migration, "
            "digital transformation, tech investment, leadership change that could "
            "trigger a re-evaluation of the tech stack."
        ),
    )
    sell_signal_reason: str | None = Field(
        default=None,
        description="Why this is a sell signal. None if is_sell_signal is False.",
    )
    urgency: UrgencyLevel = Field(
        default="low",
        description=(
            "high = act within days (migration announced, new digital leader hired, "
            "platform switch imminent); "
            "medium = act within weeks (digital transformation announced, tech investment); "
            "low = background context"
        ),
    )
    urgency_reason: str | None = Field(
        default=None,
        description="Why this urgency level. None for 'low'.",
    )


class NewsV2Output(BaseModel):
    """News intelligence output for a prospect + competitive context.

    The module researches the prospect's news AND surfaces competitor news
    that creates urgency signals (e.g., competitor launches new search experience).
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Prospect domain analyzed")

    # Prospect news
    company_news: list[NewsArticleV2] = Field(
        default_factory=list,
        description=(
            "Recent news articles about the prospect company (last 90 days). "
            "Focus on: leadership changes, platform migrations, digital transformation, "
            "technology investments, M&A activity, funding events."
        ),
    )

    # Competitor news with urgency
    competitor_news: list[NewsArticleV2] = Field(
        default_factory=list,
        description=(
            "Notable recent news about competitor companies that creates urgency for the prospect. "
            "e.g., 'Competitor just launched Algolia-powered search' = high urgency signal."
        ),
    )

    # Headline counts
    high_urgency_count: int = Field(
        default=0,
        description="Number of high-urgency sell signals found across all news.",
    )
    medium_urgency_count: int = Field(
        default=0,
        description="Number of medium-urgency sell signals found.",
    )

    # Narrative
    news_narrative: str = Field(
        description=(
            "A 2-4 sentence narrative summarising the most relevant recent news. "
            "Lead with any high-urgency signals. "
            "Written for a sales rep to read before outreach."
        )
    )
    outreach_angle: str = Field(
        default="",
        description=(
            "The single best news-driven outreach angle for a sales rep. "
            "e.g., 'Dell just announced a $500M investment in AI-powered customer experiences "
            "(Reuters, 2025-11-15). Lead with this in your outreach.' "
            "Empty if no strong angle found."
        ),
    )
