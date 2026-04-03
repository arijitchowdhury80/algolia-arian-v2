"""Audit Browser schemas -- input/output contracts for live search testing.

These schemas define the Pydantic models for the audit-browser module,
which drives a real browser (Playwright) to test a prospect's site search
experience. Captures query results, screenshots, network interceptions,
mobile viewport tests, and 10-dimension scoring from Claude Vision.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEARCH_DIMENSIONS: list[str] = [
    "relevance",
    "speed",
    "typo_tolerance",
    "nlp",
    "autocomplete",
    "faceting",
    "zero_result_handling",
    "personalization",
    "merchandising",
    "analytics",
]
"""All 10 scoring dimensions for the browser audit."""

COMMON_SEARCH_SELECTORS: list[str] = [
    'input[type="search"]',
    'input[name="q"]',
    'input[name="query"]',
    'input[name="search"]',
    'input[name="s"]',
    'input[placeholder*="search" i]',
    'input[placeholder*="Search" i]',
    "#search-input",
    ".search-input",
    '[role="search"] input',
    '[data-testid="search-input"]',
    "#search",
    ".search-bar input",
    'input[aria-label*="search" i]',
]
"""CSS selectors tried in order when locating a search bar."""

MOBILE_VIEWPORT = {"width": 390, "height": 844}
"""iPhone 14 Pro viewport dimensions for mobile tests."""


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class BrowserInput(BaseModel):
    """Input for the audit-browser module."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Website domain to test, e.g. 'dell.com'")


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class QueryResult(BaseModel):
    """Result of executing a single search query on the prospect's site."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(description="The exact search string typed into the search bar")
    query_type: str = Field(
        default="unknown",
        description="Classification of the query type from intel-queries",
    )
    response_time_ms: int = Field(
        default=0,
        description="Time in ms from pressing Enter to results appearing",
    )
    result_count: int = Field(
        default=0,
        description="Number of search results returned on the page",
    )
    screenshot_path: str | None = Field(
        default=None,
        description="Local filesystem path to the screenshot PNG",
    )
    has_autocomplete: bool = Field(
        default=False,
        description="Whether autocomplete/SAYT suggestions appeared while typing",
    )
    has_did_you_mean: bool = Field(
        default=False,
        description="Whether a 'did you mean' correction was shown",
    )
    has_facets: bool = Field(
        default=False,
        description="Whether faceted navigation / filters were shown",
    )
    has_zero_result_page: bool = Field(
        default=False,
        description="Whether the query returned zero results",
    )
    detected_search_provider: str | None = Field(
        default=None,
        description="Search provider detected from this query's network calls",
    )
    notes: str = Field(
        default="",
        description="Additional observations about this query result",
    )


class MobileTestResult(BaseModel):
    """Result of testing a query in a mobile viewport."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(description="The search query tested on mobile")
    viewport: str = Field(
        default="390x844",
        description="Viewport dimensions used, e.g. '390x844'",
    )
    screenshot_path: str | None = Field(
        default=None,
        description="Local filesystem path to the mobile screenshot PNG",
    )
    response_time_ms: int = Field(
        default=0,
        description="Time in ms from query to results on mobile",
    )
    notes: str = Field(
        default="",
        description="Observations about mobile search experience",
    )


class NetworkInterception(BaseModel):
    """A single intercepted network request during search testing."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(description="Full URL of the intercepted request")
    method: str = Field(
        default="GET",
        description="HTTP method (GET, POST, etc.)",
    )
    provider_detected: str | None = Field(
        default=None,
        description="Search provider name detected from this URL, e.g. 'Algolia'",
    )
    is_search_api: bool = Field(
        default=False,
        description="Whether this request appears to be a search API call",
    )


class DimensionScore(BaseModel):
    """Score for a single search experience dimension (0-10)."""

    model_config = ConfigDict(extra="forbid")

    dimension: Literal[
        "relevance",
        "speed",
        "typo_tolerance",
        "nlp",
        "autocomplete",
        "faceting",
        "zero_result_handling",
        "personalization",
        "merchandising",
        "analytics",
    ] = Field(description="Which of the 10 search dimensions this scores")
    score: float = Field(
        ge=0.0,
        le=10.0,
        description="Score from 0 (worst) to 10 (best)",
    )
    evidence: str = Field(
        description="Explanation of why this score was assigned, referencing observations",
    )
    screenshot_reference: str | None = Field(
        default=None,
        description="Path to screenshot that supports this score",
    )


class CompetitorBrowserResult(BaseModel):
    """Browser test results for a single competitor."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Competitor company name")
    domain: str = Field(description="Competitor website domain")
    query_results: list[QueryResult] = Field(
        default_factory=list,
        description="Results from running queries on competitor's site",
    )
    dimension_scores: list[DimensionScore] = Field(
        default_factory=list,
        description="10-dimension scores for competitor's search experience",
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class BrowserOutput(BaseModel):
    """Full output from the audit-browser module.

    Contains all browser test results: prospect queries, mobile tests,
    network interceptions, dimension scores, and competitor results.
    """

    model_config = ConfigDict(extra="forbid")

    # Context
    domain: str = Field(description="Prospect domain tested")

    # Prospect results
    prospect_query_results: list[QueryResult] = Field(
        default_factory=list,
        description="Results from running all test queries on the prospect's site",
    )
    mobile_test_results: list[MobileTestResult] = Field(
        default_factory=list,
        description="Results from mobile viewport tests",
    )
    network_interceptions: list[NetworkInterception] = Field(
        default_factory=list,
        description="All intercepted network requests during testing",
    )
    dimension_scores: list[DimensionScore] = Field(
        default_factory=list,
        description="10-dimension scoring of the prospect's search experience",
    )

    # Competitor results
    competitor_results: list[CompetitorBrowserResult] = Field(
        default_factory=list,
        description="Browser test results for each competitor",
    )

    # Search bar detection
    detected_search_provider: str | None = Field(
        default=None,
        description="Primary search provider detected via network interception",
    )
    search_bar_found: bool = Field(
        default=False,
        description="Whether a search bar was successfully located on the site",
    )
    search_bar_selector: str | None = Field(
        default=None,
        description="CSS selector that matched the search bar",
    )

    # Metadata
    total_queries_executed: int = Field(
        default=0,
        description="Total number of queries executed across prospect and competitors",
    )
    total_screenshots: int = Field(
        default=0,
        description="Total number of screenshots captured",
    )
    was_blocked: bool = Field(
        default=False,
        description="Whether the site blocked or challenged the browser (WAF/bot)",
    )
    block_details: str | None = Field(
        default=None,
        description="Details about the block if was_blocked is True",
    )
