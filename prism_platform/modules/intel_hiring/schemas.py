"""Intel Hiring schemas -- input/output contracts for hiring intelligence.

These schemas define the Pydantic models for the intel-hiring module,
which collects open roles, hiring velocity, build-vs-buy signals,
buying committee mapping, and competitor hiring comparison.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class HiringInput(BaseModel):
    """Input for the intel-hiring module."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Website domain to analyze, e.g. 'dell.com'")


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class OpenRole(BaseModel):
    """A single open job posting detected for a company."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Job title, e.g. 'Senior Search Engineer'")
    department: str = Field(
        default="",
        description="Department or team, e.g. 'Engineering', 'Product'",
    )
    location: str = Field(
        default="",
        description="Job location, e.g. 'Austin, TX' or 'Remote'",
    )
    posted_date: str | None = Field(
        default=None,
        description="When the role was posted, YYYY-MM-DD or approximate",
    )
    url: str | None = Field(
        default=None,
        description="URL to the job posting",
    )
    icp_tier: Literal[
        "tier1_economic",
        "tier2_technical",
        "tier3_champion",
        "tier4_user",
    ] = Field(
        default="tier4_user",
        description=(
            "ICP tier classification: "
            "tier1_economic = VP/Director budget holder, "
            "tier2_technical = architect/lead evaluator, "
            "tier3_champion = internal advocate/power user, "
            "tier4_user = end-user/individual contributor"
        ),
    )
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How relevant this role is to Algolia search/discovery, 0.0 to 1.0",
    )
    search_related: bool = Field(
        default=False,
        description="True if the role is directly related to search, discovery, or personalization",
    )
    signals: list[str] = Field(
        default_factory=list,
        description=(
            "Signals extracted from the role, e.g. "
            "'building internal search', 'Algolia experience preferred'"
        ),
    )
    source: str = Field(
        default="",
        description="Where this role was found: 'linkedin', 'perplexity', 'careers_page'",
    )
    company_name: str = Field(
        default="",
        description="Which company this role belongs to",
    )


class HiringVelocity(BaseModel):
    """Hiring velocity metrics over time windows."""

    model_config = ConfigDict(extra="forbid")

    roles_last_30d: int = Field(
        default=0,
        ge=0,
        description="Number of roles posted in the last 30 days",
    )
    roles_last_90d: int = Field(
        default=0,
        ge=0,
        description="Number of roles posted in the last 90 days",
    )
    trend: Literal[
        "accelerating",
        "steady",
        "decelerating",
        "insufficient_data",
    ] = Field(
        default="insufficient_data",
        description="Hiring trend direction based on velocity comparison",
    )
    interpretation: str = Field(
        default="",
        description=(
            "Human-readable interpretation of hiring velocity and what it means for sales outreach"
        ),
    )


class BuildVsBuySignal(BaseModel):
    """Assessment of whether the company is building or buying search capability."""

    model_config = ConfigDict(extra="forbid")

    signal: Literal[
        "build",
        "buy",
        "mixed",
        "insufficient_data",
    ] = Field(
        default="insufficient_data",
        description=(
            "build = hiring search engineers to build in-house, "
            "buy = likely to purchase search solution, "
            "mixed = both signals present, "
            "insufficient_data = cannot determine"
        ),
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence items supporting the build-vs-buy assessment",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        default="low",
        description="Confidence level in the assessment",
    )


class BuyingCommitteeMember(BaseModel):
    """A member of the buying committee for search technology decisions."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Full name of the person")
    title: str = Field(description="Job title")
    role: Literal[
        "economic_buyer",
        "technical_evaluator",
        "champion_candidate",
        "influencer",
        "blocker",
        "unknown",
    ] = Field(
        default="unknown",
        description="Role in the buying committee",
    )
    linkedin_url: str | None = Field(
        default=None,
        description="LinkedIn profile URL if available",
    )
    tenure_description: str | None = Field(
        default=None,
        description="How long they have been in this role, e.g. '2 years'",
    )
    previous_company: str | None = Field(
        default=None,
        description="Previous employer if known, useful for champion identification",
    )
    champion_signals: list[str] = Field(
        default_factory=list,
        description=(
            "Signals that this person could be an Algolia champion, "
            "e.g. 'previously used Algolia at prior company'"
        ),
    )


class BuyingCommittee(BaseModel):
    """Mapped buying committee for search technology purchase decisions."""

    model_config = ConfigDict(extra="forbid")

    members: list[BuyingCommitteeMember] = Field(
        default_factory=list,
        description="Identified buying committee members",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        default="low",
        description="Confidence in the buying committee mapping",
    )
    methodology: str = Field(
        default="",
        description=(
            "How the buying committee was identified, "
            "e.g. 'executive list + open roles + Perplexity enrichment'"
        ),
    )


class CompetitorHiring(BaseModel):
    """Hiring intelligence for a single competitor company."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Competitor company name")
    domain: str = Field(description="Competitor domain")
    open_roles: list[OpenRole] = Field(
        default_factory=list,
        description="Open roles detected for this competitor",
    )
    search_related_count: int = Field(
        default=0,
        ge=0,
        description="Number of search-related roles at this competitor",
    )
    hiring_velocity: HiringVelocity | None = Field(
        default=None,
        description="Hiring velocity for this competitor",
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class HiringOutput(BaseModel):
    """Full hiring intelligence output for a prospect domain.

    Contains open roles, hiring velocity, build-vs-buy signals,
    buying committee mapping, and competitor hiring comparison.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Domain that was analyzed")

    # Part 1 -- Open roles
    open_roles: list[OpenRole] = Field(
        default_factory=list,
        description="Open roles detected for the prospect company",
    )
    role_count_by_tier: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Count of open roles by ICP tier, e.g. {'tier1_economic': 2, 'tier2_technical': 5}"
        ),
    )
    search_related_count: int = Field(
        default=0,
        ge=0,
        description="Total number of search-related open roles",
    )

    # Part 2 -- Hiring velocity
    hiring_velocity: HiringVelocity | None = Field(
        default=None,
        description="Hiring velocity metrics for the prospect",
    )

    # Part 3 -- Build vs Buy
    build_vs_buy: BuildVsBuySignal | None = Field(
        default=None,
        description="Assessment of build vs buy intent for search technology",
    )

    # Part 4 -- Buying committee
    buying_committee: BuyingCommittee | None = Field(
        default=None,
        description="Mapped buying committee for search technology decisions",
    )

    # Part 5 -- Competitor comparison
    competitor_hiring: list[CompetitorHiring] = Field(
        default_factory=list,
        description="Hiring intelligence for competitor companies",
    )
    comparative_summary: str = Field(
        default="",
        description="Summary comparing prospect and competitor hiring patterns",
    )

    # Summary
    hiring_summary: str = Field(
        default="",
        description=(
            "Overall hiring intelligence summary. 2-4 sentences highlighting "
            "the most important findings for a search technology sales team."
        ),
    )
