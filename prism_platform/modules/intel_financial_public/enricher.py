"""Intel Financial Public enricher -- Perplexity + Instructor for SEC and IR analysis.

Uses:
1. Perplexity API to search for investor presentations and IR materials
2. Perplexity API to analyze SEC filing content for tech/digital mentions
3. Instructor + Claude to structure findings into validated Pydantic models
4. Instructor + Claude to generate comparative summary narrative
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field

from prism_platform.config import settings
from prism_platform.core.llm import create_completion
from prism_platform.modules.intel_financial_public.schemas import (
    CompetitorFinancials,
    InvestorPresentation,
    SECInsight,
)

logger = structlog.get_logger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar-pro"
PERPLEXITY_TIMEOUT = 60.0


class InvestorPresentationListModel(BaseModel):
    """Wrapper model for extracting a list of investor presentations via Instructor."""

    model_config = ConfigDict(extra="forbid")

    presentations: list[InvestorPresentation] = Field(
        default_factory=list,
        description="List of investor presentations extracted from search results",
    )


class SECInsightEnriched(BaseModel):
    """Enriched SEC insight with technology mentions and excerpts from Perplexity analysis."""

    model_config = ConfigDict(extra="forbid")

    digital_revenue_pct: float | None = Field(
        default=None,
        description="Digital revenue as a percentage of total, if mentioned",
    )
    technology_mentions: list[str] = Field(
        default_factory=list,
        description="Technology keywords found: search, AI, personalization, ML, etc.",
    )
    key_excerpts: list[str] = Field(
        default_factory=list,
        description="Notable excerpts about digital strategy or technology investment",
    )
    management_discussion_summary: str = Field(
        default="",
        description="Summary of MD&A section focusing on digital/tech strategy",
    )


class ComparativeSummaryModel(BaseModel):
    """Wrapper model for extracting a comparative summary via Instructor."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(
        description=(
            "A 3-5 sentence narrative comparing the target company's financial "
            "position and growth trajectory to its competitors. Include revenue "
            "scale, growth rates, and margin comparisons."
        ),
    )


class FinancialEnricher:
    """Enriches financial data with Perplexity search and Instructor structuring."""

    def __init__(self) -> None:
        self._llm_calls = 0
        self._llm_cost = 0.0

    async def enrich_sec_insights(
        self,
        sec_insights: list[SECInsight],
        company_name: str,
        ticker: str,
    ) -> list[SECInsight]:
        """Enrich SEC filing metadata with technology analysis via Perplexity.

        Args:
            sec_insights: List of SECInsight with basic metadata from collector.
            company_name: Company name for search context.
            ticker: Ticker symbol.

        Returns:
            Enriched list of SECInsight with technology_mentions and key_excerpts.
        """
        if not sec_insights:
            logger.info("[FinancialEnricher] no SEC insights to enrich")
            return sec_insights

        logger.info(
            "[FinancialEnricher] enriching SEC insights",
            count=len(sec_insights),
            company_name=company_name,
        )

        enriched: list[SECInsight] = []
        for insight in sec_insights[:3]:  # Limit to 3 filings to control costs
            try:
                enriched_insight = await self._enrich_single_sec_insight(
                    insight, company_name, ticker
                )
                enriched.append(enriched_insight)
            except Exception:
                logger.exception(
                    "[FinancialEnricher] failed to enrich SEC insight",
                    filing_type=insight.filing_type,
                    filing_date=insight.filing_date,
                )
                enriched.append(insight)  # Keep original on failure

        return enriched

    async def search_investor_presentations(
        self,
        company_name: str,
        domain: str,
    ) -> list[InvestorPresentation]:
        """Search for and structure investor presentations via Perplexity + Instructor.

        Args:
            company_name: Company name for search queries.
            domain: Company domain for context.

        Returns:
            List of structured InvestorPresentation models.
        """
        logger.info(
            "[FinancialEnricher] searching investor presentations",
            company_name=company_name,
            domain=domain,
        )

        try:
            # Search for investor presentations via Perplexity
            raw_text = await self._call_perplexity(
                f"""Find investor presentations and investor relations materials for {company_name} ({domain}).

Search for:
1. Recent investor day presentations (2024-2026)
2. Annual shareholder meeting presentations
3. Investor relations page content about strategy and technology
4. Earnings call presentation slides
5. Capital markets day presentations

For each presentation found, provide:
- Title
- Date (YYYY-MM-DD or approximate)
- URL if available
- Strategic priorities mentioned
- Any digital transformation commitments
- Technology roadmap items
- Any mentions of search, discovery, recommendation, or personalization technology
- Key quotes from executives

Focus on digital strategy, technology investment, and search/AI mentions."""
            )

            if not raw_text:
                logger.warning(
                    "[FinancialEnricher] Perplexity returned no investor presentation data",
                    company_name=company_name,
                )
                return []

            # Structure via Instructor + Claude
            result = create_completion(
                response_model=InvestorPresentationListModel,
                max_retries=2,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Extract structured investor presentation data from this research "
                            f"about {company_name}.\n\n"
                            f"Research text:\n{raw_text}\n\n"
                            f"Extract all investor presentations, investor day materials, "
                            f"and IR page insights. Focus on digital strategy, technology, "
                            f"and search/AI mentions."
                        ),
                    },
                ],
            )
            self._llm_calls += 1
            self._estimate_cost(raw_text, result.model_dump_json())

            logger.info(
                "[FinancialEnricher] investor presentations structured",
                company_name=company_name,
                count=len(result.presentations),
            )
            return result.presentations

        except Exception:
            logger.exception(
                "[FinancialEnricher] investor presentation search failed",
                company_name=company_name,
            )
            return []

    async def generate_comparative_summary(
        self,
        company_name: str,
        ticker: str,
        revenue: float | None,
        competitors: list[CompetitorFinancials],
    ) -> str:
        """Generate a narrative summary comparing the company to competitors.

        Args:
            company_name: Target company name.
            ticker: Target company ticker.
            revenue: Target company's most recent revenue.
            competitors: List of competitor financial data.

        Returns:
            Comparative summary text, or empty string on failure.
        """
        if not competitors:
            return ""

        logger.info(
            "[FinancialEnricher] generating comparative summary",
            company_name=company_name,
            competitor_count=len(competitors),
        )

        try:
            comp_lines = []
            for c in competitors:
                rev_str = f"${c.revenue / 1e9:.1f}B" if c.revenue else "N/A"
                growth_str = (
                    f"{c.revenue_growth_pct:.1f}%" if c.revenue_growth_pct is not None else "N/A"
                )
                mcap_str = f"${c.market_cap / 1e9:.1f}B" if c.market_cap else "N/A"
                comp_lines.append(
                    f"- {c.company_name} ({c.ticker}): Revenue={rev_str}, "
                    f"Growth={growth_str}, Market Cap={mcap_str}"
                )

            target_rev = f"${revenue / 1e9:.1f}B" if revenue else "N/A"
            comp_text = "\n".join(comp_lines)

            result = create_completion(
                response_model=ComparativeSummaryModel,
                max_retries=2,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Write a 3-5 sentence comparative financial summary for "
                            f"{company_name} ({ticker}, Revenue: {target_rev}) "
                            f"versus these competitors:\n\n"
                            f"{comp_text}\n\n"
                            f"Compare revenue scale, growth trajectory, and margins. "
                            f"Highlight where {company_name} stands out or lags behind. "
                            f"Be specific with numbers."
                        ),
                    },
                ],
            )
            self._llm_calls += 1
            self._estimate_cost(comp_text, result.model_dump_json())

            logger.info(
                "[FinancialEnricher] comparative summary generated",
                company_name=company_name,
                summary_length=len(result.summary),
            )
            return result.summary

        except Exception:
            logger.exception(
                "[FinancialEnricher] comparative summary generation failed",
                company_name=company_name,
            )
            return ""

    @property
    def llm_calls(self) -> int:
        """Total LLM calls made by the enricher."""
        return self._llm_calls

    @property
    def llm_cost(self) -> float:
        """Estimated total LLM cost in USD."""
        return round(self._llm_cost, 4)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _enrich_single_sec_insight(
        self,
        insight: SECInsight,
        company_name: str,
        ticker: str,
    ) -> SECInsight:
        """Enrich a single SEC insight with technology analysis.

        Args:
            insight: Base SECInsight with metadata.
            company_name: Company name.
            ticker: Ticker symbol.

        Returns:
            Enriched SECInsight.
        """
        raw_text = await self._call_perplexity(
            f"""Analyze the {insight.filing_type} SEC filing for {company_name} ({ticker})
filed on {insight.filing_date}.

Focus on:
1. Any mention of digital revenue or e-commerce revenue as a percentage of total
2. Technology mentions: search, AI, machine learning, personalization, recommendation engines, natural language processing
3. Key excerpts about digital transformation or technology investment
4. Management Discussion & Analysis (MD&A) summary focusing on digital strategy

If the filing URL is available: {insight.filing_url or "not available"}

Provide specific quotes and data points from the filing."""
        )

        if not raw_text:
            return insight

        try:
            enrichment = create_completion(
                response_model=SECInsightEnriched,
                max_retries=2,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Extract SEC filing insights from this analysis of "
                            f"{company_name}'s {insight.filing_type} filing "
                            f"dated {insight.filing_date}:\n\n{raw_text}"
                        ),
                    },
                ],
            )
            self._llm_calls += 1
            self._estimate_cost(raw_text, enrichment.model_dump_json())

            return SECInsight(
                filing_type=insight.filing_type,
                filing_date=insight.filing_date,
                filing_url=insight.filing_url,
                digital_revenue_pct=enrichment.digital_revenue_pct,
                technology_mentions=enrichment.technology_mentions,
                key_excerpts=enrichment.key_excerpts,
                management_discussion_summary=enrichment.management_discussion_summary,
            )
        except Exception:
            logger.exception(
                "[FinancialEnricher] Instructor extraction failed for SEC insight",
                filing_type=insight.filing_type,
                filing_date=insight.filing_date,
            )
            return insight

    async def _call_perplexity(self, prompt: str) -> str:
        """Call the Perplexity chat completions API.

        Args:
            prompt: The user message to send.

        Returns:
            The assistant's response text, or empty string on failure.
        """
        try:
            async with httpx.AsyncClient(timeout=PERPLEXITY_TIMEOUT) as client:
                resp = await client.post(
                    PERPLEXITY_API_URL,
                    headers={
                        "Authorization": f"Bearer {settings.perplexity_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": PERPLEXITY_MODEL,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are a financial analyst specializing in "
                                    "technology and digital transformation. "
                                    "Return factual, well-sourced information. "
                                    "Cite sources inline where possible."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 4096,
                        "return_citations": True,
                    },
                )
                resp.raise_for_status()

            data: dict[str, Any] = resp.json()
            choices = data.get("choices", [])
            if not choices:
                logger.warning("[FinancialEnricher] Perplexity returned no choices")
                return ""

            self._llm_calls += 1
            content: str = choices[0].get("message", {}).get("content", "")
            return content

        except httpx.TimeoutException as exc:
            logger.error(
                "[FinancialEnricher] Perplexity timeout",
                error=str(exc),
            )
            return ""
        except httpx.HTTPStatusError as exc:
            logger.error(
                "[FinancialEnricher] Perplexity HTTP error",
                status_code=exc.response.status_code,
                error=str(exc),
            )
            return ""
        except Exception:
            logger.exception("[FinancialEnricher] Perplexity call failed")
            return ""

    def _estimate_cost(self, input_text: str, output_text: str) -> None:
        """Estimate LLM cost for Claude Sonnet call.

        Args:
            input_text: Input text sent to the model.
            output_text: Output text received from the model.
        """
        # Claude Sonnet: ~$0.10/1M input tokens, ~$0.40/1M output tokens
        # Rough estimate: 4 chars per token
        input_tokens = len(input_text) / 4
        output_tokens = len(output_text) / 4
        cost = (input_tokens / 1_000_000 * 0.10) + (output_tokens / 1_000_000 * 0.40)
        self._llm_cost += cost
