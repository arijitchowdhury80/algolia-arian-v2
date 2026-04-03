"""Intel Social schemas -- input/output contracts for social intelligence.

These schemas define the Pydantic models for the intel-social module,
which collects executive LinkedIn activity, public statements, Twitter/X
activity, and competitor social signals for Algolia sales intelligence.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class SocialInput(BaseModel):
    """Input for the intel-social module."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Website domain to analyze, e.g. 'dell.com'")


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class SocialPost(BaseModel):
    """A social media post or activity from an executive or company."""

    model_config = ConfigDict(extra="forbid")

    author_name: str = Field(description="Full name of the post author")
    author_title: str = Field(
        default="",
        description="Job title of the post author",
    )
    company_name: str = Field(
        default="",
        description="Company the author works for",
    )
    platform: Literal[
        "linkedin",
        "twitter",
        "youtube",
        "conference",
        "podcast",
        "interview",
        "other",
    ] = Field(
        default="other",
        description="Platform where the post was published",
    )
    content_summary: str = Field(
        description="Summary of the post content in 1-3 sentences",
    )
    date: str = Field(
        default="",
        description="Publication date as YYYY-MM-DD or approximate",
    )
    url: str | None = Field(
        default=None,
        description="URL to the original post",
    )
    engagement_likes: int | None = Field(
        default=None,
        description="Number of likes/reactions if known",
    )
    engagement_comments: int | None = Field(
        default=None,
        description="Number of comments if known",
    )
    topic: Literal[
        "digital_strategy",
        "technology_investment",
        "customer_experience",
        "search_related",
        "ai_related",
        "hiring",
        "culture",
        "product_launch",
        "competitive",
        "other",
    ] = Field(
        default="other",
        description="Primary topic of the post for downstream filtering",
    )
    algolia_relevance: Literal["high", "medium", "low"] = Field(
        default="low",
        description=(
            "Relevance to an Algolia sales pitch. "
            "high = mentions search/discovery/AI. "
            "medium = mentions digital transformation/tech investment. "
            "low = general business content."
        ),
    )
    quotable_statement: str | None = Field(
        default=None,
        description="The most quotable part of the post for sales use",
    )


class ExecutiveQuote(BaseModel):
    """A verbatim or near-verbatim public statement from an executive."""

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
        description=(
            "Where/when the quote was said, e.g. 'CES 2026 keynote' or 'Bloomberg interview'"
        ),
    )
    source_type: Literal[
        "keynote",
        "conference",
        "podcast",
        "interview",
        "webinar",
        "article",
        "youtube",
        "other",
    ] = Field(
        default="other",
        description="Type of source where the quote was found",
    )
    source_url: str | None = Field(
        default=None,
        description="URL to the source of the quote",
    )
    date: str = Field(
        default="",
        description="Date of the quote as YYYY-MM-DD or approximate",
    )
    topic: Literal[
        "digital_strategy",
        "technology_investment",
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
    algolia_relevance: Literal["high", "medium", "low"] = Field(
        default="low",
        description=(
            "Relevance to an Algolia sales pitch. "
            "high = mentions search/discovery/AI investment. "
            "medium = mentions digital transformation/tech budget. "
            "low = general business statement."
        ),
    )
    sales_angle: str | None = Field(
        default=None,
        description="How an AE can use this quote in a pitch. None if no clear connection.",
    )


class CompetitorSocial(BaseModel):
    """Aggregated social activity for a single competitor."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Competitor company name")
    domain: str = Field(description="Competitor's primary website domain")
    posts: list[SocialPost] = Field(
        default_factory=list,
        description="Social posts from this competitor's executives",
    )
    exec_quotes: list[ExecutiveQuote] = Field(
        default_factory=list,
        description="Public statements from this competitor's executives",
    )
    key_finding: str = Field(
        default="",
        description="One-line summary of the most important finding for this competitor",
    )


class TwitterActivity(BaseModel):
    """Twitter/X activity for the prospect company."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Company name")
    is_active: bool = Field(
        default=False,
        description="Whether the company has been active on Twitter/X recently",
    )
    recent_posts: list[SocialPost] = Field(
        default_factory=list,
        description="Recent Twitter/X posts from the company or its executives",
    )
    summary: str = Field(
        default="",
        description="One-line summary of Twitter/X activity and themes",
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class SocialOutput(BaseModel):
    """Full social intelligence output for a prospect domain.

    Contains executive LinkedIn activity, public statements, Twitter/X
    activity, competitor social signals, and relevance classifications.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Domain that was analyzed")

    # Part 1 -- Executive LinkedIn activity
    prospect_posts: list[SocialPost] = Field(
        default_factory=list,
        description="Social posts from the prospect's executives",
    )

    # Part 2 -- Executive public statements (beyond LinkedIn)
    prospect_exec_quotes: list[ExecutiveQuote] = Field(
        default_factory=list,
        description="Verbatim public statements from the prospect's executives",
    )

    # Part 3 -- Classification summary
    high_relevance_count: int = Field(
        default=0,
        description="Count of posts + quotes with algolia_relevance='high'",
    )
    medium_relevance_count: int = Field(
        default=0,
        description="Count of posts + quotes with algolia_relevance='medium'",
    )
    most_quotable: list[str] = Field(
        default_factory=list,
        description="Top 5 most quotable statements for sales use",
    )

    # Part 4 -- Twitter/X
    twitter_activity: TwitterActivity | None = Field(
        default=None,
        description="Twitter/X activity for the prospect company",
    )

    # Part 5 -- Competitor social
    competitor_social: list[CompetitorSocial] = Field(
        default_factory=list,
        description="Social activity aggregated per competitor",
    )
    competitive_comparison: str = Field(
        default="",
        description=(
            "Summary comparing prospect and competitor social activity. "
            "e.g. 'Dell execs are vocal about AI investment while HP focuses on sustainability.'"
        ),
    )

    # Summary
    social_summary: str = Field(
        default="",
        description=(
            "Overall intelligence summary of all social signals. "
            "2-4 sentences highlighting the most important findings for sales."
        ),
    )
