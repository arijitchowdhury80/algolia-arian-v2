"""Intel Queries v2 schemas — browser-audit test-query output contract.

Track-1 (pure Python) generates the full query set from structured upstream
data (intel-company product_categories + intel-traffic top_organic_keywords).
Track-2 LLM is intentionally skipped — query generation is fully deterministic.

QueryItem is frozen (immutable once generated).
QueryIntelOutput uses extra="forbid" to catch schema drift early.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Exhaustive set of query types the collector generates.
# Adding a new type here requires a corresponding generator branch in collector.py.
QueryType = Literal[
    "broad_category",
    "specific_product",
    "nlp_conversational",
    "typo_variant",
    "synonym_colloquial",
    "non_product_content",
    "brand_subbrand",
    "zero_results_gibberish",
]


class QueryItem(BaseModel):
    """A single test query for the browser audit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(description="The query string to type into the search box")
    type: QueryType = Field(description="Query category — determines what search behaviour it tests")
    source: str = Field(
        description=(
            "Where this query was derived from, e.g. 'product_categories', "
            "'top_organic_keywords', 'static', 'brand'. "
            "Supports traceability back to the upstream data."
        )
    )


class QueryIntelOutput(BaseModel):
    """Full browser-audit query set for a prospect domain.

    Generated entirely by the Track-1 pure-Python collector. The LLM
    (Track-2) is not used for this module — all fields are deterministic.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Prospect domain this query set was generated for")
    queries: list[QueryItem] = Field(
        default_factory=list,
        description="The complete ordered test-query set for the browser audit.",
    )
    query_coverage: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Count of queries per type, keyed by QueryType string. "
            "E.g. {'broad_category': 4, 'typo_variant': 3, ...}. "
            "Computed from the queries list — always consistent with it."
        ),
    )
    total_queries: int = Field(
        default=0,
        description="Total number of queries in the set (sum of query_coverage values).",
    )
