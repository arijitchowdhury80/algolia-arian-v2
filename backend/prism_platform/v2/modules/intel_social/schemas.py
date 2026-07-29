"""Intel Social v2 schemas — LinkedIn and Twitter/X post intelligence.

Track 1 (Apify) fetches raw posts deterministically.
Track 2 (LLM) scores each post for Algolia relevance and writes the signal summary.

Execution strategy: prospect-only (one LLM call after Apify collection).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SocialPost(BaseModel):
    """A single post scraped from LinkedIn or Twitter/X."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(description="Post text content")
    platform: str = Field(description="Social platform: 'linkedin' or 'twitter'")
    date: str | None = Field(default=None, description="Post date as YYYY-MM-DD or raw string")
    url: str | None = Field(default=None, description="Permalink to the post")
    relevance_score: float = Field(
        default=0.0,
        description=(
            "Algolia relevance score 0.0–1.0. "
            "High (>0.7): mentions search, digital experience, tech investment, "
            "platform migration, AI/ML features, customer experience, ecommerce scale. "
            "Low (<0.3): HR posts, generic brand content, charity/CSR."
        ),
    )
    relevance_tags: list[str] = Field(
        default_factory=list,
        description=(
            "Signal tags for this post, e.g. ['search_mention', 'tech_investment', "
            "'platform_migration', 'ai_ml', 'cx_focus', 'scale_signal']."
        ),
    )


class SocialIntelOutput(BaseModel):
    """Social intelligence output — LinkedIn and Twitter/X posts with Algolia relevance scoring."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Prospect domain analyzed")

    linkedin_posts: list[SocialPost] = Field(
        default_factory=list,
        description=(
            "LinkedIn company posts scraped by Apify (up to 10). "
            "Empty list if LinkedIn URL not found or Apify key not configured."
        ),
    )
    twitter_posts: list[SocialPost] = Field(
        default_factory=list,
        description=(
            "Twitter/X posts scraped by Apify (up to 10). "
            "Empty list if Twitter handle not found or Apify key not configured."
        ),
    )
    high_signal_posts: list[SocialPost] = Field(
        default_factory=list,
        description="Posts scoring above 0.7 relevance — the highest-value signals for AE outreach.",
    )
    signal_summary: str | None = Field(
        default=None,
        description=(
            "2-4 sentence summary of the strongest social signals for a sales rep. "
            "Lead with the highest-scoring post. None if no posts were collected."
        ),
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Source URLs or descriptors for the collected posts.",
    )
