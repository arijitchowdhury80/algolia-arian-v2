"""Intel Industry enricher -- Instructor + Claude to structure raw Perplexity output.

Takes the raw text responses from the collector and uses Claude via Instructor
to produce validated IndustryOutput with structured benchmarks, trends,
pain points, case studies, vendor landscape, and summary.
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from prism_platform.core.llm import create_completion
from prism_platform.modules.intel_industry.schemas import (
    AlgoliaCaseStudy,
    IndustryOutput,
    IndustryTrend,
    PainPoint,
    SearchVendorMarketShare,
    VerticalBenchmark,
)

logger = structlog.get_logger(__name__)


class StructuredBenchmarks(BaseModel):
    """Wrapper model for extracting a list of vertical benchmarks via Instructor."""

    model_config = ConfigDict(extra="forbid")
    benchmarks: list[VerticalBenchmark] = Field(default_factory=list)


class StructuredTrends(BaseModel):
    """Wrapper model for extracting a list of industry trends via Instructor."""

    model_config = ConfigDict(extra="forbid")
    trends: list[IndustryTrend] = Field(default_factory=list)


class StructuredPainPoints(BaseModel):
    """Wrapper model for extracting a list of pain points via Instructor."""

    model_config = ConfigDict(extra="forbid")
    pain_points: list[PainPoint] = Field(default_factory=list)


class StructuredCaseStudies(BaseModel):
    """Wrapper model for extracting a list of Algolia case studies via Instructor."""

    model_config = ConfigDict(extra="forbid")
    case_studies: list[AlgoliaCaseStudy] = Field(default_factory=list)


class StructuredVendorLandscape(BaseModel):
    """Wrapper model for extracting search vendor market share data via Instructor."""

    model_config = ConfigDict(extra="forbid")
    vendors: list[SearchVendorMarketShare] = Field(default_factory=list)


class StructuredSummary(BaseModel):
    """Wrapper model for generating industry summary and ROI context."""

    model_config = ConfigDict(extra="forbid")
    industry_summary: str = Field(
        description=(
            "2-4 sentence summary of the industry landscape for sales context. "
            "Highlight key benchmarks, trends, and pain points."
        ),
    )
    roi_context: str = Field(
        default="",
        description=(
            "ROI framing for this industry, e.g. "
            "'In your vertical, Algolia customers see average 37% conversion lift'"
        ),
    )


class IndustryEnricher:
    """Structures raw Perplexity text into IndustryOutput via Instructor + Claude."""

    def __init__(self) -> None:
        """Initialize the Claude Instructor client."""
        pass

    async def enrich(
        self,
        domain: str,
        industry: str,
        sub_vertical: str | None,
        raw_data: dict[str, Any],
    ) -> tuple[IndustryOutput, int, float]:
        """Structure raw collector output into validated IndustryOutput.

        Args:
            domain: The domain being researched.
            industry: Primary industry vertical.
            sub_vertical: Optional sub-vertical.
            raw_data: Dict from IndustryCollector.collect_all() with keys:
                benchmarks, trends, pain_points, case_studies, vendor_landscape.

        Returns:
            Tuple of (IndustryOutput, llm_calls, llm_cost_usd).

        Raises:
            instructor.exceptions.InstructorRetryException: After failed attempts.
        """
        logger.info(
            "[IndustryEnricher] structuring raw data",
            domain=domain,
            industry=industry,
        )

        llm_calls = 0
        total_input_chars = 0
        total_output_chars = 0

        # Step 1: Extract vertical benchmarks
        vertical_benchmarks: list[VerticalBenchmark] = []
        if raw_data.get("benchmarks"):
            try:
                result = create_completion(
                    response_model=StructuredBenchmarks,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_benchmarks_prompt(
                                industry, raw_data["benchmarks"]
                            ),
                        },
                    ],
                )
                vertical_benchmarks = result.benchmarks
                llm_calls += 1
                total_input_chars += len(raw_data["benchmarks"])
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[IndustryEnricher] benchmarks extracted",
                    count=len(vertical_benchmarks),
                )
            except Exception as exc:
                logger.error(
                    "[IndustryEnricher] benchmarks extraction failed",
                    error=str(exc),
                )

        # Step 2: Extract industry trends
        industry_trends: list[IndustryTrend] = []
        if raw_data.get("trends"):
            try:
                result = create_completion(
                    response_model=StructuredTrends,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_trends_prompt(industry, raw_data["trends"]),
                        },
                    ],
                )
                industry_trends = result.trends
                llm_calls += 1
                total_input_chars += len(raw_data["trends"])
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[IndustryEnricher] trends extracted",
                    count=len(industry_trends),
                )
            except Exception as exc:
                logger.error(
                    "[IndustryEnricher] trends extraction failed",
                    error=str(exc),
                )

        # Step 3: Extract pain points
        pain_points: list[PainPoint] = []
        if raw_data.get("pain_points"):
            try:
                result = create_completion(
                    response_model=StructuredPainPoints,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_pain_points_prompt(
                                industry, raw_data["pain_points"]
                            ),
                        },
                    ],
                )
                pain_points = result.pain_points
                llm_calls += 1
                total_input_chars += len(raw_data["pain_points"])
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[IndustryEnricher] pain points extracted",
                    count=len(pain_points),
                )
            except Exception as exc:
                logger.error(
                    "[IndustryEnricher] pain points extraction failed",
                    error=str(exc),
                )

        # Step 4: Extract case studies
        algolia_case_studies: list[AlgoliaCaseStudy] = []
        if raw_data.get("case_studies"):
            try:
                result = create_completion(
                    response_model=StructuredCaseStudies,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_case_studies_prompt(
                                industry, raw_data["case_studies"]
                            ),
                        },
                    ],
                )
                algolia_case_studies = result.case_studies
                llm_calls += 1
                total_input_chars += len(raw_data["case_studies"])
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[IndustryEnricher] case studies extracted",
                    count=len(algolia_case_studies),
                )
            except Exception as exc:
                logger.error(
                    "[IndustryEnricher] case studies extraction failed",
                    error=str(exc),
                )

        # Step 5: Extract vendor landscape
        search_vendor_landscape: list[SearchVendorMarketShare] = []
        if raw_data.get("vendor_landscape"):
            try:
                result = create_completion(
                    response_model=StructuredVendorLandscape,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_vendor_landscape_prompt(
                                industry, raw_data["vendor_landscape"]
                            ),
                        },
                    ],
                )
                search_vendor_landscape = result.vendors
                llm_calls += 1
                total_input_chars += len(raw_data["vendor_landscape"])
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[IndustryEnricher] vendor landscape extracted",
                    count=len(search_vendor_landscape),
                )
            except Exception as exc:
                logger.error(
                    "[IndustryEnricher] vendor landscape extraction failed",
                    error=str(exc),
                )

        # Step 6: Generate summary and ROI context
        industry_summary = ""
        roi_context = ""
        summary_context = self._build_summary_context(
            industry, vertical_benchmarks, industry_trends, pain_points, algolia_case_studies
        )
        if summary_context.strip():
            try:
                result = create_completion(
                    response_model=StructuredSummary,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_summary_prompt(industry, summary_context),
                        },
                    ],
                )
                industry_summary = result.industry_summary
                roi_context = result.roi_context
                llm_calls += 1
                total_input_chars += len(summary_context)
                total_output_chars += len(result.model_dump_json())
            except Exception as exc:
                logger.error(
                    "[IndustryEnricher] summary generation failed",
                    error=str(exc),
                )

        # Claude Sonnet cost estimate: ~$0.10/1M input tokens, ~$0.40/1M output tokens
        estimated_cost = (total_input_chars / 4 / 1_000_000 * 0.10) + (
            total_output_chars / 4 / 1_000_000 * 0.40
        )

        output = IndustryOutput(
            domain=domain,
            industry=industry,
            sub_vertical=sub_vertical,
            vertical_benchmarks=vertical_benchmarks,
            industry_trends=industry_trends,
            pain_points=pain_points,
            algolia_case_studies=algolia_case_studies,
            search_vendor_landscape=search_vendor_landscape,
            industry_summary=industry_summary,
            roi_context=roi_context,
        )

        logger.info(
            "[IndustryEnricher] enrichment complete",
            domain=domain,
            industry=industry,
            benchmarks_count=len(vertical_benchmarks),
            trends_count=len(industry_trends),
            pain_points_count=len(pain_points),
            case_studies_count=len(algolia_case_studies),
            vendors_count=len(search_vendor_landscape),
            llm_calls=llm_calls,
            estimated_cost_usd=round(estimated_cost, 4),
        )

        return output, llm_calls, round(estimated_cost, 4)

    @staticmethod
    def _build_benchmarks_prompt(industry: str, raw_text: str) -> str:
        """Build the prompt for extracting structured benchmarks from raw text.

        Args:
            industry: Industry vertical.
            raw_text: Raw Perplexity response text.

        Returns:
            Formatted prompt string.
        """
        return f"""You are extracting structured industry benchmarks for the {industry} vertical.

Below is raw research text. Extract ALL benchmark metrics into the required schema.
For each benchmark:
- metric_name: name of the metric (e.g. "Average Conversion Rate", "Average AOV", "Search Conversion Rate")
- value: the benchmark value as a formatted string (e.g. "2.8%", "$127", "15.3%")
- source: the source attribution with year (e.g. "Baymard Institute 2025", "Forrester 2026")
- industry: set to "{industry}"
- year: the year the data was published or measured
- notes: any additional context

Include ALL benchmarks mentioned, especially those related to search, conversion, and digital commerce.

RAW TEXT:
{raw_text}"""

    @staticmethod
    def _build_trends_prompt(industry: str, raw_text: str) -> str:
        """Build the prompt for extracting structured trends from raw text.

        Args:
            industry: Industry vertical.
            raw_text: Raw Perplexity response text.

        Returns:
            Formatted prompt string.
        """
        return f"""You are extracting structured industry trends for the {industry} vertical.

Below is raw research text. Extract ALL industry trends into the required schema.
For each trend:
- trend_name: short name (e.g. "AI-Powered Personalization", "Composable Commerce")
- description: 1-3 sentence description of the trend
- relevance_to_search: how relevant to search/discovery technology:
  high = directly about search/discovery, medium = related to digital experience, low = tangential
- source: attribution (e.g. "Gartner 2026 Hype Cycle")
- analyst_quote: verbatim analyst quote if available, null otherwise

RAW TEXT:
{raw_text}"""

    @staticmethod
    def _build_pain_points_prompt(industry: str, raw_text: str) -> str:
        """Build the prompt for extracting structured pain points from raw text.

        Args:
            industry: Industry vertical.
            raw_text: Raw Perplexity response text.

        Returns:
            Formatted prompt string.
        """
        return f"""You are extracting industry pain points for the {industry} vertical that are relevant to an Algolia search technology pitch.

Below is raw research text. Extract ALL pain points into the required schema.
For each pain point:
- pain_point: short name (e.g. "Poor Search Relevance", "No Personalization")
- description: 1-3 sentence description of the pain and its business impact
- algolia_capability: which Algolia product or feature addresses this:
  Options include: "AI Search (NeuralSearch)", "Algolia Recommend", "Dynamic Re-Ranking",
  "Personalization", "Analytics & A/B Testing", "Federated Search", "Query Suggestions",
  "Visual Discovery", "Algolia Crawler", "InstantSearch UI"
- severity: critical (revenue-impacting), high (significant UX issue), medium (improvement area), low (nice-to-have)

Every pain point MUST have a non-empty algolia_capability.

RAW TEXT:
{raw_text}"""

    @staticmethod
    def _build_case_studies_prompt(industry: str, raw_text: str) -> str:
        """Build the prompt for extracting Algolia case studies from raw text.

        Args:
            industry: Industry vertical.
            raw_text: Raw Perplexity response text.

        Returns:
            Formatted prompt string.
        """
        return f"""You are extracting Algolia customer case studies for the {industry} vertical.

Below is raw research text. Extract ALL Algolia case studies into the required schema.
For each case study:
- customer_name: name of the Algolia customer
- industry: their industry vertical
- use_case: what they used Algolia for (e.g. "Site Search + Recommendations")
- key_metrics: list of quantitative results (e.g. ["37% conversion lift", "2x search usage"])
- url: URL to the case study on algolia.com if available, null otherwise

Only include actual Algolia customers, not competitors' customers.

RAW TEXT:
{raw_text}"""

    @staticmethod
    def _build_vendor_landscape_prompt(industry: str, raw_text: str) -> str:
        """Build the prompt for extracting search vendor market share from raw text.

        Args:
            industry: Industry vertical.
            raw_text: Raw Perplexity response text.

        Returns:
            Formatted prompt string.
        """
        return f"""You are extracting search vendor market share data for the {industry} vertical.

Below is raw research text. Extract ALL search vendors mentioned into the required schema.
For each vendor:
- vendor_name: name of the search vendor (e.g. "Algolia", "Elasticsearch", "Coveo")
- estimated_share_pct: estimated market share as a percentage (0-100), null if unknown
- notes: additional context about their presence in {industry}

Include ALL search vendors mentioned, even if market share is unknown.

RAW TEXT:
{raw_text}"""

    @staticmethod
    def _build_summary_context(
        industry: str,
        benchmarks: list[VerticalBenchmark],
        trends: list[IndustryTrend],
        pain_points: list[PainPoint],
        case_studies: list[AlgoliaCaseStudy],
    ) -> str:
        """Build context text for summary generation.

        Args:
            industry: Industry vertical.
            benchmarks: Extracted benchmarks.
            trends: Extracted trends.
            pain_points: Extracted pain points.
            case_studies: Extracted case studies.

        Returns:
            Combined context string.
        """
        parts: list[str] = []

        if benchmarks:
            bench_lines = [f"- {b.metric_name}: {b.value} ({b.source})" for b in benchmarks[:10]]
            parts.append(f"## {industry} Benchmarks:\n" + "\n".join(bench_lines))

        if trends:
            trend_lines = [f"- {t.trend_name}: {t.description[:150]}" for t in trends[:10]]
            parts.append(f"## {industry} Trends:\n" + "\n".join(trend_lines))

        if pain_points:
            pain_lines = [
                f"- {p.pain_point} ({p.severity}): {p.description[:150]}" for p in pain_points[:10]
            ]
            parts.append(f"## {industry} Pain Points:\n" + "\n".join(pain_lines))

        if case_studies:
            case_lines = [
                f"- {c.customer_name}: {', '.join(c.key_metrics[:3])}" for c in case_studies[:10]
            ]
            parts.append(f"## Algolia Case Studies in {industry}:\n" + "\n".join(case_lines))

        return "\n\n".join(parts)

    @staticmethod
    def _build_summary_prompt(industry: str, context_text: str) -> str:
        """Build the prompt for generating industry summary and ROI context.

        Args:
            industry: Industry vertical.
            context_text: Combined context from all extracted data.

        Returns:
            Formatted prompt string.
        """
        return f"""You are writing an industry intelligence summary for the {industry} vertical for an Algolia sales team.

Based on the following structured data, produce:

1. industry_summary: A 2-4 sentence summary of the {industry} landscape for sales context.
   Highlight key benchmarks, trends, and pain points that make this industry
   a good fit for Algolia's search and discovery technology.

2. roi_context: A single sentence framing ROI for this industry based on the case studies
   and benchmarks. Example: "In {industry}, Algolia customers see average 37% conversion lift
   and 2x search engagement." Use actual numbers from the case studies when available.

CONTEXT:
{context_text}"""
