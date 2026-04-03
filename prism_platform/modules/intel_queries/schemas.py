"""Intel Queries schemas -- input/output contracts for query generation.

These schemas define the Pydantic models for the intel-queries module,
which generates vertically-calibrated test queries for the browser-based
search experience audit. Queries cover 8 types across easy/medium/hard
difficulty to stress-test a prospect's search implementation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

QUERY_TYPES: list[str] = [
    "exact_product",
    "category_browse",
    "natural_language",
    "misspelled",
    "zero_result",
    "long_tail",
    "competitor_product",
    "ambiguous",
]
"""All 8 query types that must be represented in every query set."""

DIFFICULTY_LEVELS: list[str] = ["easy", "medium", "hard"]
"""Valid difficulty levels for test queries."""

# Difficulty classification per query type
DIFFICULTY_MAP: dict[str, str] = {
    "exact_product": "easy",
    "category_browse": "medium",
    "natural_language": "medium",
    "misspelled": "hard",
    "zero_result": "hard",
    "long_tail": "hard",
    "competitor_product": "hard",
    "ambiguous": "hard",
}
"""Default difficulty assignment per query type."""

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class QueriesInput(BaseModel):
    """Input for the intel-queries module."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Website domain to generate queries for, e.g. 'dell.com'")


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class TestQuery(BaseModel):
    """A single test query for the browser-based search audit.

    Each query targets a specific search behavior and includes success/failure
    criteria so the browser audit can objectively score the search experience.
    """

    model_config = ConfigDict(extra="forbid")

    query: str = Field(description="The exact search string to type into the search bar")
    query_type: Literal[
        "exact_product",
        "category_browse",
        "natural_language",
        "misspelled",
        "zero_result",
        "long_tail",
        "competitor_product",
        "ambiguous",
    ] = Field(
        description=(
            "Classification of the query type. "
            "exact_product = specific product name. "
            "category_browse = product category search. "
            "natural_language = conversational intent query. "
            "misspelled = common misspelling of a product or brand. "
            "zero_result = something the company does not sell. "
            "long_tail = very specific multi-attribute query. "
            "competitor_product = a competitor's product name. "
            "ambiguous = single word with multiple possible meanings."
        )
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(
        description=(
            "Difficulty level for the search engine. "
            "easy = any competent search handles this. "
            "medium = requires understanding of categories or intent. "
            "hard = requires advanced NLP, typo tolerance, or edge-case handling."
        )
    )
    expected_behavior: str = Field(
        description="What a good search engine should do with this query"
    )
    what_good_looks_like: str = Field(
        description="Specific positive outcome that indicates search quality"
    )
    what_bad_looks_like: str = Field(
        description="Specific negative outcome that indicates search failure"
    )
    target_domain: str = Field(description="The domain this query is designed for, e.g. 'dell.com'")


class CompetitorQuerySet(BaseModel):
    """A set of test queries generated for a specific competitor domain.

    During the browser audit, we test competitors' search experiences
    to benchmark the prospect's search against the competition.
    """

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Competitor company name")
    domain: str = Field(description="Competitor website domain")
    queries: list[TestQuery] = Field(
        default_factory=list,
        description="Test queries calibrated for this competitor's catalog",
    )


class QueryDifficultyDistribution(BaseModel):
    """Counts of queries by difficulty level for quality reporting."""

    model_config = ConfigDict(extra="forbid")

    easy_count: int = Field(default=0, description="Number of easy difficulty queries")
    medium_count: int = Field(default=0, description="Number of medium difficulty queries")
    hard_count: int = Field(default=0, description="Number of hard difficulty queries")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class QueriesOutput(BaseModel):
    """Full output from the intel-queries module.

    Contains the prospect's test queries, competitor query sets,
    difficulty distribution, and metadata about query coverage.
    """

    model_config = ConfigDict(extra="forbid")

    # Context
    domain: str = Field(description="Prospect domain these queries are for")
    industry: str = Field(default="", description="Industry classification from intel-company")
    sub_vertical: str | None = Field(
        default=None,
        description="More specific sub-vertical, e.g. 'Consumer Electronics'",
    )

    # Part 1 -- Prospect queries
    prospect_queries: list[TestQuery] = Field(
        default_factory=list,
        description="16 test queries (2 per type) calibrated to the prospect's catalog",
    )

    # Part 2 -- Competitor queries
    competitor_query_sets: list[CompetitorQuerySet] = Field(
        default_factory=list,
        description="Query sets for each identified competitor domain",
    )

    # Part 3 -- Difficulty distribution
    difficulty_distribution: QueryDifficultyDistribution | None = Field(
        default=None,
        description="Breakdown of prospect queries by difficulty level",
    )

    # Metadata
    query_count: int = Field(
        default=0,
        description="Total number of prospect queries generated",
    )
    types_covered: list[str] = Field(
        default_factory=list,
        description="List of query types represented in the prospect queries",
    )
    generation_notes: str = Field(
        default="",
        description="Notes about the generation process, model used, or issues encountered",
    )
