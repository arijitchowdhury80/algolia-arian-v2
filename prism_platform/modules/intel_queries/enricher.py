"""Intel Queries enricher -- Instructor + Claude for query generation.

Uses Claude via Instructor to generate vertically-calibrated test queries
for the browser-based search experience audit. Generates:
1. 16 prospect queries (2 per query type)
2. 8 queries per competitor (1 per query type)

The prompts are calibrated to the company's industry, sub-vertical,
and product categories to ensure realistic, testable queries.
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from prism_platform.core.llm import create_completion
from prism_platform.modules.intel_queries.schemas import (
    CompetitorQuerySet,
    QueryDifficultyDistribution,
    TestQuery,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Instructor response models (internal, used only for LLM extraction)
# ---------------------------------------------------------------------------


class ProspectQuerySetResponse(BaseModel):
    """Response model for prospect query generation via Instructor."""

    model_config = ConfigDict(extra="forbid")

    queries: list[TestQuery] = Field(description="Exactly 16 test queries, 2 per query type")


class CompetitorQuerySetResponse(BaseModel):
    """Response model for competitor query generation via Instructor."""

    model_config = ConfigDict(extra="forbid")

    queries: list[TestQuery] = Field(description="Exactly 8 test queries, 1 per query type")


# ---------------------------------------------------------------------------
# Enricher
# ---------------------------------------------------------------------------


class QueriesEnricher:
    """Generates test queries via Instructor + Claude.

    Produces vertically-calibrated queries for the prospect and each
    competitor, covering all 8 query types at appropriate difficulty levels.
    """

    def __init__(self) -> None:
        """Initialize the Claude Instructor client."""
        pass

    async def generate_prospect_queries(
        self,
        context: dict[str, Any],
    ) -> tuple[list[TestQuery], int, float]:
        """Generate 16 test queries for the prospect domain.

        Args:
            context: Dict from QueriesCollector with domain, company_name,
                industry, sub_vertical, product_categories.

        Returns:
            Tuple of (list[TestQuery], llm_calls, estimated_cost_usd).

        Raises:
            ValidationError: If Instructor extraction fails after retries.
            Exception: If Claude API call fails.
        """
        domain = context["domain"]
        logger.info(
            "[QueriesEnricher] generating prospect queries",
            domain=domain,
            industry=context.get("industry", ""),
        )

        prompt = self._build_prospect_prompt(context)

        try:
            result = create_completion(
                response_model=ProspectQuerySetResponse,
                max_retries=3,
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )
        except ValidationError as exc:
            logger.error(
                "[QueriesEnricher] prospect query validation failed after retries",
                domain=domain,
                error=str(exc),
            )
            raise
        except Exception as exc:
            logger.error(
                "[QueriesEnricher] prospect query generation failed",
                domain=domain,
                error=f"{type(exc).__name__}: {exc}",
            )
            raise

        # Ensure target_domain is set correctly on all queries
        queries = []
        for q in result.queries:
            q_dict = q.model_dump()
            q_dict["target_domain"] = domain
            queries.append(TestQuery.model_validate(q_dict))

        # Estimate cost: Claude Sonnet ~$0.10/1M input, ~$0.40/1M output
        input_chars = len(prompt)
        output_chars = sum(len(q.model_dump_json()) for q in queries)
        estimated_cost = (input_chars / 4 / 1_000_000 * 0.10) + (
            output_chars / 4 / 1_000_000 * 0.40
        )

        logger.info(
            "[QueriesEnricher] prospect queries generated",
            domain=domain,
            query_count=len(queries),
            types_covered=list({q.query_type for q in queries}),
            estimated_cost_usd=round(estimated_cost, 4),
        )

        return queries, 1, round(estimated_cost, 4)

    async def generate_competitor_queries(
        self,
        context: dict[str, Any],
        competitor: dict[str, str],
    ) -> tuple[CompetitorQuerySet, int, float]:
        """Generate 8 test queries for a single competitor domain.

        Args:
            context: Dict from QueriesCollector with industry/vertical context.
            competitor: Dict with 'company_name' and 'domain' keys.

        Returns:
            Tuple of (CompetitorQuerySet, llm_calls, estimated_cost_usd).

        Raises:
            ValidationError: If Instructor extraction fails after retries.
            Exception: If Claude API call fails.
        """
        comp_domain = competitor.get("domain", "")
        comp_name = competitor.get("company_name", comp_domain)

        logger.info(
            "[QueriesEnricher] generating competitor queries",
            competitor=comp_name,
            domain=comp_domain,
        )

        prompt = self._build_competitor_prompt(context, comp_name, comp_domain)

        try:
            result = create_completion(
                response_model=CompetitorQuerySetResponse,
                max_retries=3,
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )
        except ValidationError as exc:
            logger.error(
                "[QueriesEnricher] competitor query validation failed after retries",
                competitor=comp_name,
                domain=comp_domain,
                error=str(exc),
            )
            raise
        except Exception as exc:
            logger.error(
                "[QueriesEnricher] competitor query generation failed",
                competitor=comp_name,
                domain=comp_domain,
                error=f"{type(exc).__name__}: {exc}",
            )
            raise

        # Ensure target_domain is set correctly
        queries = []
        for q in result.queries:
            q_dict = q.model_dump()
            q_dict["target_domain"] = comp_domain
            queries.append(TestQuery.model_validate(q_dict))

        query_set = CompetitorQuerySet(
            company_name=comp_name,
            domain=comp_domain,
            queries=queries,
        )

        # Estimate cost
        input_chars = len(prompt)
        output_chars = sum(len(q.model_dump_json()) for q in queries)
        estimated_cost = (input_chars / 4 / 1_000_000 * 0.10) + (
            output_chars / 4 / 1_000_000 * 0.40
        )

        logger.info(
            "[QueriesEnricher] competitor queries generated",
            competitor=comp_name,
            domain=comp_domain,
            query_count=len(queries),
            estimated_cost_usd=round(estimated_cost, 4),
        )

        return query_set, 1, round(estimated_cost, 4)

    @staticmethod
    def compute_difficulty_distribution(
        queries: list[TestQuery],
    ) -> QueryDifficultyDistribution:
        """Compute the difficulty breakdown for a list of queries.

        Args:
            queries: List of TestQuery objects.

        Returns:
            QueryDifficultyDistribution with counts.
        """
        easy = sum(1 for q in queries if q.difficulty == "easy")
        medium = sum(1 for q in queries if q.difficulty == "medium")
        hard = sum(1 for q in queries if q.difficulty == "hard")

        return QueryDifficultyDistribution(
            easy_count=easy,
            medium_count=medium,
            hard_count=hard,
        )

    @staticmethod
    def _build_prospect_prompt(context: dict[str, Any]) -> str:
        """Build the Claude prompt for prospect query generation.

        Args:
            context: Dict with domain, company_name, industry, sub_vertical,
                product_categories.

        Returns:
            Prompt string for Instructor extraction.
        """
        domain = context["domain"]
        company_name = context.get("company_name", domain)
        industry = context.get("industry", "General")
        sub_vertical = context.get("sub_vertical", "")
        product_categories = context.get("product_categories", [])

        vertical_str = industry
        if sub_vertical:
            vertical_str = f"{industry} / {sub_vertical}"

        categories_str = ", ".join(product_categories) if product_categories else "not specified"

        return f"""You are a search quality analyst generating test queries for {company_name} ({domain}),
a company in the {vertical_str} vertical.

Their product categories include: {categories_str}

Generate exactly 16 test queries across 8 types (2 per type):

Type 1 - exact_product: Search for a specific product the company actually sells.
  Difficulty: easy. Any competent search engine should find exact product matches.

Type 2 - category_browse: Search for a product category (not a specific product).
  Difficulty: medium. Requires category understanding and proper faceting.

Type 3 - natural_language: Conversational query with intent, like "best laptop for video editing under $1500".
  Difficulty: medium. Requires NLP to understand intent and constraints.

Type 4 - misspelled: Common misspelling of a product or brand name the company sells.
  Difficulty: hard. Requires typo tolerance / fuzzy matching.

Type 5 - zero_result: Something the company definitely does NOT sell.
  Difficulty: hard. A good search should handle gracefully with suggestions, not a blank page.

Type 6 - long_tail: Very specific multi-attribute query like "red wireless noise-canceling headphones under $200".
  Difficulty: hard. Requires understanding multiple attributes and constraints.

Type 7 - competitor_product: Search for a well-known competitor's product name on this site.
  Difficulty: hard. Good search redirects to equivalent products; bad search returns nothing.

Type 8 - ambiguous: Single word or short phrase that could mean multiple things.
  Difficulty: hard. Good search shows disambiguated results across categories.

For each query, provide:
- query: The exact search string to type into the search bar
- query_type: One of the 8 types above
- difficulty: easy, medium, or hard (follow the difficulty assignments above)
- expected_behavior: What a good search engine should do with this query
- what_good_looks_like: Specific positive outcome (e.g., "Top 3 results show the exact product")
- what_bad_looks_like: Specific negative outcome (e.g., "Returns 0 results or completely irrelevant items")
- target_domain: Set this to "{domain}" for all queries

CRITICAL REQUIREMENTS:
- Queries MUST be realistic for the {vertical_str} vertical
- Use real product names, real categories, and real competitor brands that exist in this vertical
- For exact_product queries, use products that {company_name} is known to sell
- For competitor_product queries, use products from well-known competitors in this space
- For misspelled queries, use realistic typos (one letter off, transposed letters)
- Every query must be unique -- no duplicates
- Each query_type must appear exactly 2 times"""

    @staticmethod
    def _build_competitor_prompt(
        context: dict[str, Any],
        comp_name: str,
        comp_domain: str,
    ) -> str:
        """Build the Claude prompt for competitor query generation.

        Args:
            context: Dict with industry/vertical context from the prospect.
            comp_name: Competitor company name.
            comp_domain: Competitor website domain.

        Returns:
            Prompt string for Instructor extraction.
        """
        industry = context.get("industry", "General")
        sub_vertical = context.get("sub_vertical", "")

        vertical_str = industry
        if sub_vertical:
            vertical_str = f"{industry} / {sub_vertical}"

        return f"""You are a search quality analyst generating test queries for {comp_name} ({comp_domain}),
a company in the {vertical_str} vertical.

Generate exactly 8 test queries, one per type:

1. exact_product (difficulty: easy) - A specific product {comp_name} sells
2. category_browse (difficulty: medium) - A product category they carry
3. natural_language (difficulty: medium) - A conversational intent query
4. misspelled (difficulty: hard) - Common misspelling of one of their products
5. zero_result (difficulty: hard) - Something they do not sell
6. long_tail (difficulty: hard) - Very specific multi-attribute query
7. competitor_product (difficulty: hard) - A competitor's product searched on their site
8. ambiguous (difficulty: hard) - Single word with multiple meanings

For each query, provide:
- query: The exact search string to type
- query_type: One of the 8 types
- difficulty: easy, medium, or hard
- expected_behavior: What good search should do
- what_good_looks_like: Specific positive outcome
- what_bad_looks_like: Specific negative outcome
- target_domain: Set to "{comp_domain}" for all queries

Use real products and brands relevant to {comp_name} in the {vertical_str} vertical.
Every query must be unique and realistic for this company's catalog."""
