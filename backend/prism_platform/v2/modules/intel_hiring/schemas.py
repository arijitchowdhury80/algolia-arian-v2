"""Intel Hiring v2 schemas — hiring intelligence and ICP signal output.

Detects open roles, maps them to ICP tier (MEDDPICC roles), and produces
build-vs-buy signals from search-related job postings.

Execution strategy: prospect-only (one call for the prospect; competitor
hiring data included in same call for context).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ICP tiers based on MEDDPICC framework
ICPTier = Literal[
    "tier1_economic",  # VP/Director budget holder
    "tier2_technical",  # Architect/lead evaluator
    "tier3_champion",  # Internal advocate / power user
    "tier4_user",  # End user / individual contributor
]

# Build vs buy signal classification
BuildVsBuySignal = Literal["build", "buy", "mixed", "insufficient_data"]


class OpenRoleV2(BaseModel):
    """A single open job posting detected for a company."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(description="Job title, e.g. 'Senior Search Engineer'")
    department: str = Field(
        default="",
        description="Department or team: 'Engineering', 'Product', 'Digital'",
    )
    location: str = Field(
        default="",
        description="Job location: 'Austin, TX' or 'Remote'",
    )
    posted_date: str | None = Field(
        default=None,
        description="When posted, YYYY-MM-DD or approximate",
    )
    url: str | None = Field(default=None, description="URL to the job posting")
    icp_tier: ICPTier = Field(
        default="tier4_user",
        description=(
            "ICP tier classification: "
            "tier1_economic = VP/Director with budget (e.g. 'VP Digital Commerce'), "
            "tier2_technical = architect/lead evaluating solutions "
            "(e.g. 'Search Platform Lead'), "
            "tier3_champion = power user who would advocate internally "
            "(e.g. 'Search Relevance Engineer'), "
            "tier4_user = individual contributor / end user"
        ),
    )
    search_related: bool = Field(
        default=False,
        description=(
            "True if the role is directly related to search, discovery, or personalization. "
            "Triggers: 'search', 'discovery', 'relevance', 'merchandising', "
            "'Elasticsearch', 'Solr', 'Algolia', 'Typesense'"
        ),
    )
    build_vs_buy_signal: BuildVsBuySignal = Field(
        default="insufficient_data",
        description=(
            "build = role suggests building in-house (e.g. 'Build search from scratch', "
            "mentions Lucene/Elasticsearch without existing deployment); "
            "buy = role suggests evaluating/implementing vendor solution "
            "(e.g. 'Algolia implementation', 'search vendor evaluation'); "
            "mixed = ambiguous; insufficient_data = not enough info"
        ),
    )
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How relevant this role is to Algolia sales, 0.0-1.0",
    )

    @field_validator("relevance_score")
    @classmethod
    def round_relevance(cls, v: float) -> float:
        return round(v, 2)


class HiringSignalSummary(BaseModel):
    """Summary of hiring signals across all open roles."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    total_open_roles: int = Field(default=0, description="Total open roles detected")
    search_related_roles: int = Field(
        default=0, description="Roles directly related to search/discovery"
    )
    tier1_economic_roles: int = Field(
        default=0, description="VP/Director level roles (economic buyers)"
    )
    build_vs_buy: BuildVsBuySignal = Field(
        default="insufficient_data",
        description="Overall build-vs-buy assessment from hiring patterns",
    )
    build_vs_buy_rationale: str = Field(
        default="",
        description=(
            "1-2 sentence rationale for the build_vs_buy assessment. "
            "e.g. '3 Elasticsearch engineer roles with no mention of commercial vendors "
            "suggests build orientation.'"
        ),
    )
    hiring_signal_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "0.0-1.0 buying signal score from hiring intelligence. "
            "1.0 = strong buy signal (search vendor evaluation role + VP Digital hired); "
            "0.5 = moderate signal (search-related engineering roles); "
            "0.0 = no signal"
        ),
    )


class HiringV2Output(BaseModel):
    """Hiring intelligence output for a prospect."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Prospect domain analyzed")

    # Open roles
    open_roles: list[OpenRoleV2] = Field(
        default_factory=list,
        description=(
            "Open job roles detected for the prospect. "
            "Focus on: search/discovery roles, VP/Director digital roles, "
            "ecommerce/product roles. "
            "Limit to top 10 most relevant roles."
        ),
    )

    # Signal summary
    signal_summary: HiringSignalSummary = Field(
        description="Aggregated signal summary across all detected roles."
    )

    # Competitor context
    competitor_hiring_notes: str = Field(
        default="",
        description=(
            "Notable competitor hiring patterns. "
            "e.g., 'Competitor HP is also hiring search engineers — market is hot.' "
            "Empty if no notable competitor hiring found."
        ),
    )

    # Narrative
    hiring_narrative: str = Field(
        description=(
            "A 2-4 sentence narrative summarising hiring signals. "
            "Lead with the build-vs-buy assessment and search investment level. "
            "Note any new executive hires. "
            "Written for a sales rep to read before outreach."
        )
    )
