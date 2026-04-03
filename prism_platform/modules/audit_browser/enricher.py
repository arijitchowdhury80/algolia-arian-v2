"""Audit Browser enricher -- Claude Vision scoring of search experience.

Uses Instructor + Claude Sonnet to analyze screenshots and query results,
producing 10-dimension scores for the prospect's search experience and
each competitor's search experience.

Each scoring task makes ONE Claude call with base64-encoded screenshots
and structured query result data.
"""

from __future__ import annotations

import base64
import os
from typing import Any

import instructor
import structlog

from prism_platform.core.llm import create_completion
from prism_platform.modules.audit_browser.schemas import (
    SEARCH_DIMENSIONS,
    BrowserOutput,
    CompetitorBrowserResult,
    DimensionScore,
    MobileTestResult,
    NetworkInterception,
    QueryResult,
)

logger = structlog.get_logger(__name__)


class _ProspectScoring(instructor.OpenAISchema if hasattr(instructor, "OpenAISchema") else object):
    """Internal schema -- not used directly, we use DimensionScore list via Instructor."""


class BrowserEnricher:
    """Scores search experiences using Claude Vision on screenshots and query data."""

    def __init__(self) -> None:
        self._available = True

    async def enrich(
        self,
        domain: str,
        collector_output: dict[str, Any],
    ) -> tuple[BrowserOutput, int, float]:
        """Score the prospect and competitors using Claude Vision.

        Args:
            domain: Prospect domain.
            collector_output: Raw dict from BrowserCollector.collect_all().

        Returns:
            Tuple of (BrowserOutput, llm_calls, llm_cost_usd).
        """
        logger.info("[BrowserEnricher] enrich started", domain=domain)

        llm_calls = 0
        llm_cost = 0.0

        # Parse collector output into schema objects
        prospect_query_results = [
            QueryResult.model_validate(qr)
            for qr in collector_output.get("prospect_query_results", [])
        ]
        mobile_test_results = [
            MobileTestResult.model_validate(mr)
            for mr in collector_output.get("mobile_test_results", [])
        ]
        network_interceptions = [
            NetworkInterception.model_validate(ni)
            for ni in collector_output.get("network_interceptions", [])
        ]
        logger.info(
            "[BrowserEnricher] collector output validated via Pydantic",
            domain=domain,
            prospect_queries=len(prospect_query_results),
            mobile_tests=len(mobile_test_results),
            network_interceptions=len(network_interceptions),
        )

        # Score the prospect
        prospect_scores: list[DimensionScore] = []
        if self._available and prospect_query_results:
            try:
                prospect_scores, calls, cost = await self._score_site(
                    domain=domain,
                    query_results=prospect_query_results,
                    mobile_results=mobile_test_results,
                    network_data=network_interceptions,
                    label="prospect",
                )
                llm_calls += calls
                llm_cost += cost
            except Exception as exc:
                logger.error(
                    "[BrowserEnricher] prospect scoring failed",
                    domain=domain,
                    error=str(exc),
                )
                prospect_scores = self._default_scores()
        else:
            prospect_scores = self._default_scores()

        # Score competitors
        competitor_results: list[CompetitorBrowserResult] = []
        for comp_data in collector_output.get("competitor_results", []):
            comp_domain = comp_data.get("domain", "")
            comp_name = comp_data.get("company_name", comp_domain)
            comp_query_results = [
                QueryResult.model_validate(qr) for qr in comp_data.get("query_results", [])
            ]

            comp_scores: list[DimensionScore] = []
            if self._available and comp_query_results:
                try:
                    comp_scores, calls, cost = await self._score_site(
                        domain=comp_domain,
                        query_results=comp_query_results,
                        mobile_results=[],
                        network_data=[],
                        label=f"competitor:{comp_name}",
                    )
                    llm_calls += calls
                    llm_cost += cost
                except Exception as exc:
                    logger.error(
                        "[BrowserEnricher] competitor scoring failed",
                        competitor=comp_name,
                        error=str(exc),
                    )
                    comp_scores = self._default_scores()
            else:
                comp_scores = self._default_scores()

            competitor_results.append(
                CompetitorBrowserResult(
                    company_name=comp_name,
                    domain=comp_domain,
                    query_results=comp_query_results,
                    dimension_scores=comp_scores,
                )
            )

        # Build the final output
        logger.debug(
            "[BrowserEnricher] building BrowserOutput",
            domain=domain,
            prospect_scores_count=len(prospect_scores),
            competitor_results_count=len(competitor_results),
        )
        output = BrowserOutput(
            domain=domain,
            prospect_query_results=prospect_query_results,
            mobile_test_results=mobile_test_results,
            network_interceptions=network_interceptions,
            dimension_scores=prospect_scores,
            competitor_results=competitor_results,
            detected_search_provider=collector_output.get("detected_search_provider"),
            search_bar_found=collector_output.get("search_bar_found", False),
            search_bar_selector=collector_output.get("search_bar_selector"),
            total_queries_executed=collector_output.get("total_queries_executed", 0),
            total_screenshots=collector_output.get("total_screenshots", 0),
            was_blocked=collector_output.get("was_blocked", False),
            block_details=collector_output.get("block_details"),
        )

        logger.info(
            "[BrowserEnricher] enrich completed",
            domain=domain,
            llm_calls=llm_calls,
            llm_cost_usd=round(llm_cost, 4),
            dimensions_scored=len(prospect_scores),
            competitors_scored=len(competitor_results),
        )

        return output, llm_calls, llm_cost

    async def _score_site(
        self,
        domain: str,
        query_results: list[QueryResult],
        mobile_results: list[MobileTestResult],
        network_data: list[NetworkInterception],
        label: str,
    ) -> tuple[list[DimensionScore], int, float]:
        """Score a single site across 10 dimensions using Claude.

        Args:
            domain: Domain being scored.
            query_results: Query results from browser testing.
            mobile_results: Mobile test results.
            network_data: Network interception data.
            label: Label for logging (e.g. 'prospect' or 'competitor:HP').

        Returns:
            Tuple of (list[DimensionScore], llm_calls, cost_usd).

        Raises:
            Exception: If Claude call fails after retries.
        """
        # Collect screenshot paths
        screenshot_paths = [qr.screenshot_path for qr in query_results if qr.screenshot_path]
        screenshot_paths += [mr.screenshot_path for mr in mobile_results if mr.screenshot_path]

        # Load screenshots as base64
        screenshots_b64 = self._load_screenshots(screenshot_paths)
        logger.info(
            "[BrowserEnricher] screenshots loaded for scoring",
            domain=domain,
            label=label,
            screenshot_paths_found=len(screenshot_paths),
            screenshots_loaded=len(screenshots_b64),
            screenshots_sent=min(len(screenshots_b64), 10),
        )

        # Build the scoring prompt
        prompt = self._build_scoring_prompt(
            domain=domain,
            query_results=query_results,
            mobile_results=mobile_results,
            network_data=network_data,
            screenshot_count=len(screenshots_b64),
        )

        # Build message content with screenshots
        content_parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for ss in screenshots_b64[:10]:  # Limit to 10 screenshots
            content_parts.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{ss['base64']}",
                    },
                }
            )

        logger.info(
            "[BrowserEnricher] Claude scoring call started",
            domain=domain,
            label=label,
            query_results_count=len(query_results),
            prompt_chars=len(prompt),
        )

        try:
            # Use Instructor to get structured output
            scores_model = create_completion(
                response_model=list[DimensionScore],  # type: ignore[arg-type]
                max_retries=3,
                messages=[
                    {"role": "user", "content": content_parts},
                ],
            )

            # Estimate cost
            input_chars = len(prompt) + len(screenshots_b64) * 50_000  # ~50KB avg per screenshot
            estimated_cost = (input_chars / 4 / 1_000_000 * 0.10) + (2000 / 1_000_000 * 0.40)

            logger.info(
                "[BrowserEnricher] scoring complete",
                domain=domain,
                label=label,
                dimensions_scored=len(scores_model),
                est_input_chars=input_chars,
                est_input_tokens=input_chars // 4,
                cost_usd=round(estimated_cost, 4),
            )

            return scores_model, 1, round(estimated_cost, 4)

        except Exception as exc:
            logger.error(
                "[BrowserEnricher] Claude scoring failed",
                domain=domain,
                label=label,
                error=str(exc),
            )
            raise

    def _load_screenshots(self, paths: list[str | None]) -> list[dict[str, str]]:
        """Load screenshot files as base64.

        Args:
            paths: List of filesystem paths (may contain None).

        Returns:
            List of dicts with 'path' and 'base64' keys.
        """
        encoded: list[dict[str, str]] = []
        for path in paths:
            if not path or not os.path.exists(path):
                continue
            try:
                with open(path, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                encoded.append({"path": path, "base64": data})
            except Exception as exc:
                logger.warning(
                    "[BrowserEnricher] failed to load screenshot",
                    path=path,
                    error=str(exc),
                )
        return encoded

    def _default_scores(self) -> list[DimensionScore]:
        """Return default zero scores for all 10 dimensions.

        Used when Claude is unavailable or scoring fails.

        Returns:
            List of 10 DimensionScores with score=0.0.
        """
        return [
            DimensionScore(
                dimension=dim,  # type: ignore[arg-type]
                score=0.0,
                evidence="Score unavailable -- Claude Vision not available or scoring failed",
            )
            for dim in SEARCH_DIMENSIONS
        ]

    @staticmethod
    def _build_scoring_prompt(
        domain: str,
        query_results: list[QueryResult],
        mobile_results: list[MobileTestResult],
        network_data: list[NetworkInterception],
        screenshot_count: int,
    ) -> str:
        """Build the Claude scoring prompt.

        Args:
            domain: Domain being scored.
            query_results: Query results from browser testing.
            mobile_results: Mobile test results.
            network_data: Network interception data.
            screenshot_count: Number of screenshots included.

        Returns:
            Formatted prompt string.
        """
        # Summarize query results
        query_summary_lines: list[str] = []
        for qr in query_results:
            query_summary_lines.append(
                f"- Query: '{qr.query}' (type: {qr.query_type}) → "
                f"{qr.result_count} results in {qr.response_time_ms}ms, "
                f"autocomplete={qr.has_autocomplete}, facets={qr.has_facets}, "
                f"did_you_mean={qr.has_did_you_mean}, zero_results={qr.has_zero_result_page}"
            )
        query_summary = (
            "\n".join(query_summary_lines) if query_summary_lines else "No queries executed"
        )

        # Summarize mobile results
        mobile_lines: list[str] = []
        for mr in mobile_results:
            mobile_lines.append(
                f"- Mobile query: '{mr.query}' → {mr.response_time_ms}ms ({mr.viewport})"
            )
        mobile_summary = "\n".join(mobile_lines) if mobile_lines else "No mobile tests"

        # Summarize network data
        providers = set()
        for ni in network_data:
            if ni.provider_detected:
                providers.add(ni.provider_detected)
        network_summary = (
            f"Detected providers: {', '.join(providers)}"
            if providers
            else "No search providers detected via network interception"
        )

        return f"""You are an expert in site search evaluation. Score the search experience on {domain} across 10 dimensions.

## Data from browser testing:

### Query Results ({len(query_results)} queries):
{query_summary}

### Mobile Testing:
{mobile_summary}

### Network Analysis:
{network_summary}

### Screenshots: {screenshot_count} screenshots attached (review for UI quality, result relevance, facet presence, etc.)

## Score each of these 10 dimensions from 0.0 to 10.0:

1. **relevance** — Are search results relevant to the query? Do product results match intent?
2. **speed** — How fast do results appear? Under 200ms is excellent, over 2000ms is poor.
3. **typo_tolerance** — Does the search handle misspellings? Does it auto-correct or suggest corrections?
4. **nlp** — Does it understand natural language queries? Can it parse "black yoga pants under $100"?
5. **autocomplete** — Does it show suggestions while typing? Are they helpful and relevant?
6. **faceting** — Are there filters/facets? Can users refine by category, price, brand, etc.?
7. **zero_result_handling** — What happens on zero results? Are there recommendations or suggestions?
8. **personalization** — Any evidence of personalized results? Geo, history, or behavioral signals?
9. **merchandising** — Are featured/promoted results visible? Is there visual merchandising?
10. **analytics** — Any evidence of search analytics? A/B tests, tracking, result click tracking?

For each dimension, provide:
- The score (0.0 to 10.0, one decimal place)
- Evidence explaining the score, referencing specific queries or screenshots
- A screenshot reference if applicable

Be objective. Base scores on observable evidence only. If you cannot assess a dimension from the available data, score it 5.0 with a note explaining the limitation."""
