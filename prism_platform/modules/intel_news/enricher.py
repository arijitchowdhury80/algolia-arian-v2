"""Intel News enricher -- Instructor + Claude to structure raw Perplexity output.

Takes the raw text responses from the collector and uses Claude via Instructor
to produce validated NewsOutput with structured articles, executive quotes,
urgency signals, and competitive comparison.
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from prism_platform.core.llm import create_completion
from prism_platform.modules.intel_news.schemas import (
    CompetitorNews,
    ExecutiveQuote,
    NewsArticle,
    NewsOutput,
    UrgencySignal,
)

logger = structlog.get_logger(__name__)


class StructuredArticles(BaseModel):
    """Wrapper model for extracting a list of news articles via Instructor."""

    model_config = ConfigDict(extra="forbid")
    articles: list[NewsArticle] = Field(default_factory=list)


class StructuredQuotes(BaseModel):
    """Wrapper model for extracting a list of executive quotes via Instructor."""

    model_config = ConfigDict(extra="forbid")
    quotes: list[ExecutiveQuote] = Field(default_factory=list)


class StructuredSignals(BaseModel):
    """Wrapper model for extracting urgency signals via Instructor."""

    model_config = ConfigDict(extra="forbid")
    signals: list[UrgencySignal] = Field(default_factory=list)


class StructuredSummary(BaseModel):
    """Wrapper model for generating summary and comparison text."""

    model_config = ConfigDict(extra="forbid")
    news_summary: str = Field(
        description="2-4 sentence overall intelligence summary of all findings"
    )
    competitive_comparison: str = Field(
        default="",
        description="Summary comparing prospect and competitor news",
    )


class NewsEnricher:
    """Structures raw Perplexity text into NewsOutput via Instructor + Claude."""

    def __init__(self) -> None:
        pass

    async def enrich(
        self,
        domain: str,
        company_name: str,
        raw_data: dict[str, Any],
    ) -> tuple[NewsOutput, int, float]:
        """Structure raw collector output into validated NewsOutput.

        Args:
            domain: The domain being researched.
            company_name: Name of the prospect company.
            raw_data: Dict from NewsCollector.collect_all() with keys:
                prospect_news, exec_media, competitor_news, signals.

        Returns:
            Tuple of (NewsOutput, llm_calls, llm_cost_usd).

        Raises:
            instructor.exceptions.InstructorRetryException: After failed attempts.
        """
        logger.info("[NewsEnricher] structuring raw data", domain=domain)

        llm_calls = 0
        total_input_chars = 0
        total_output_chars = 0

        # Step 1: Extract prospect articles
        prospect_articles: list[NewsArticle] = []
        if raw_data.get("prospect_news"):
            try:
                result = create_completion(
                    response_model=StructuredArticles,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_articles_prompt(
                                company_name, domain, raw_data["prospect_news"]
                            ),
                        },
                    ],
                )
                prospect_articles = result.articles
                llm_calls += 1
                total_input_chars += len(raw_data["prospect_news"])
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[NewsEnricher] prospect articles extracted",
                    count=len(prospect_articles),
                )
            except Exception as exc:
                logger.error(
                    "[NewsEnricher] prospect articles extraction failed",
                    error=str(exc),
                )

        # Step 2: Extract executive quotes
        prospect_exec_quotes: list[ExecutiveQuote] = []
        exec_media: dict[str, str] = raw_data.get("exec_media", {})
        if exec_media:
            combined_exec_text = "\n\n".join(
                f"### {name}:\n{text}"
                for name, text in exec_media.items()
                if isinstance(text, str) and text.strip()
            )
            if combined_exec_text.strip():
                try:
                    result = create_completion(
                        response_model=StructuredQuotes,
                        max_retries=3,
                        messages=[
                            {
                                "role": "user",
                                "content": self._build_quotes_prompt(
                                    company_name, combined_exec_text
                                ),
                            },
                        ],
                    )
                    prospect_exec_quotes = result.quotes
                    llm_calls += 1
                    total_input_chars += len(combined_exec_text)
                    total_output_chars += len(result.model_dump_json())
                    logger.info(
                        "[NewsEnricher] exec quotes extracted",
                        count=len(prospect_exec_quotes),
                    )
                except Exception as exc:
                    logger.error(
                        "[NewsEnricher] exec quotes extraction failed",
                        error=str(exc),
                    )

        # Step 3: Extract urgency signals
        urgency_signals: list[UrgencySignal] = []
        if raw_data.get("signals"):
            try:
                result = create_completion(
                    response_model=StructuredSignals,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_signals_prompt(
                                company_name, raw_data["signals"]
                            ),
                        },
                    ],
                )
                urgency_signals = result.signals
                llm_calls += 1
                total_input_chars += len(raw_data["signals"])
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[NewsEnricher] urgency signals extracted",
                    count=len(urgency_signals),
                )
            except Exception as exc:
                logger.error(
                    "[NewsEnricher] urgency signals extraction failed",
                    error=str(exc),
                )

        # Step 4: Extract competitor news
        competitor_news: list[CompetitorNews] = []
        raw_competitors: dict[str, dict[str, str]] = raw_data.get("competitor_news", {})
        for comp_name, comp_data in raw_competitors.items():
            if not isinstance(comp_data, dict):
                continue
            comp_text = comp_data.get("news", "")
            comp_domain = comp_data.get("domain", "")
            if not comp_text.strip():
                competitor_news.append(CompetitorNews(company_name=comp_name, domain=comp_domain))
                continue

            try:
                result = create_completion(
                    response_model=StructuredArticles,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_articles_prompt(
                                comp_name, comp_domain, comp_text
                            ),
                        },
                    ],
                )
                competitor_news.append(
                    CompetitorNews(
                        company_name=comp_name,
                        domain=comp_domain,
                        articles=result.articles,
                    )
                )
                llm_calls += 1
                total_input_chars += len(comp_text)
                total_output_chars += len(result.model_dump_json())
            except Exception as exc:
                logger.error(
                    "[NewsEnricher] competitor articles extraction failed",
                    competitor=comp_name,
                    error=str(exc),
                )
                competitor_news.append(CompetitorNews(company_name=comp_name, domain=comp_domain))

        # Step 5: Generate summary and competitive comparison
        news_summary = ""
        competitive_comparison = ""
        summary_text = self._build_summary_context(
            company_name, prospect_articles, prospect_exec_quotes, competitor_news
        )
        if summary_text.strip():
            try:
                result = create_completion(
                    response_model=StructuredSummary,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_summary_prompt(company_name, summary_text),
                        },
                    ],
                )
                news_summary = result.news_summary
                competitive_comparison = result.competitive_comparison
                llm_calls += 1
                total_input_chars += len(summary_text)
                total_output_chars += len(result.model_dump_json())
            except Exception as exc:
                logger.error(
                    "[NewsEnricher] summary generation failed",
                    error=str(exc),
                )

        # Compute signal counts
        sell_signal_count = sum(1 for a in prospect_articles if a.is_sell_signal)
        high_value_quote_count = sum(1 for q in prospect_exec_quotes if q.is_high_value)

        # Claude Sonnet cost estimate: ~$0.10/1M input tokens, ~$0.40/1M output tokens
        estimated_cost = (total_input_chars / 4 / 1_000_000 * 0.10) + (
            total_output_chars / 4 / 1_000_000 * 0.40
        )

        output = NewsOutput(
            domain=domain,
            prospect_articles=prospect_articles,
            prospect_exec_quotes=prospect_exec_quotes,
            urgency_signals=urgency_signals,
            sell_signal_count=sell_signal_count,
            high_value_quote_count=high_value_quote_count,
            competitor_news=competitor_news,
            competitive_comparison=competitive_comparison,
            news_summary=news_summary,
        )

        logger.info(
            "[NewsEnricher] enrichment complete",
            domain=domain,
            articles_count=len(prospect_articles),
            quotes_count=len(prospect_exec_quotes),
            signals_count=len(urgency_signals),
            competitors_count=len(competitor_news),
            sell_signals=sell_signal_count,
            high_value_quotes=high_value_quote_count,
            llm_calls=llm_calls,
            estimated_cost_usd=round(estimated_cost, 4),
        )

        return output, llm_calls, round(estimated_cost, 4)

    @staticmethod
    def _build_articles_prompt(company_name: str, domain: str, raw_text: str) -> str:
        """Build the prompt for extracting structured articles from raw text.

        Args:
            company_name: Company name.
            domain: Company domain.
            raw_text: Raw Perplexity response text.

        Returns:
            Formatted prompt string.
        """
        return f"""You are extracting structured news articles for {company_name} ({domain}).

Below is raw research text. Extract ALL news articles into the required schema.
For each article:
- headline: exact article headline
- source: publication name (Reuters, TechCrunch, etc.)
- date: YYYY-MM-DD format
- url: article URL if mentioned
- summary: 1-2 sentence summary
- category: classify as leadership_change, product_launch, partnership, financial, acquisition, technology, search_related, digital_transformation, or other
- is_sell_signal: True if the article mentions search, digital transformation, platform migration, AI-powered experiences, or similar topics relevant to an Algolia pitch
- sell_signal_reason: why it's a sell signal (if is_sell_signal is True)
- urgency: high (act within days), medium (act within weeks), or low (background context)
- urgency_reason: why urgent (if urgency is not low)
- company_name: set to "{company_name}"

RAW TEXT:
{raw_text}"""

    @staticmethod
    def _build_quotes_prompt(company_name: str, raw_text: str) -> str:
        """Build the prompt for extracting structured executive quotes.

        Args:
            company_name: Company name.
            raw_text: Combined executive media text.

        Returns:
            Formatted prompt string.
        """
        return f"""You are extracting executive quotes for {company_name}.

Below is raw research text about executives at {company_name}. Extract ALL verbatim or near-verbatim quotes.
For each quote:
- executive_name: full name
- executive_title: job title
- company_name: "{company_name}"
- quote: the verbatim quote text (must be actual quote, not paraphrase)
- context: where/when it was said (e.g. "CES 2026 keynote", "Q4 earnings call")
- source_type: interview, keynote, podcast, earnings_call, conference, press_release, social_media, or article
- source_url: URL if available
- date: YYYY-MM-DD or approximate
- classification: digital_investment, technology_strategy, customer_experience, search_related, ai_related, competitive_positioning, growth_commitment, cost_optimization, or other
- is_high_value: True if the exec is committing budget, stating priorities, mentioning pain points, or signaling technology investment
- algolia_angle: how this connects to an Algolia pitch (if applicable)

Only include quotes that are actual statements by the executive, not reporter paraphrases.

RAW TEXT:
{raw_text}"""

    @staticmethod
    def _build_signals_prompt(company_name: str, raw_text: str) -> str:
        """Build the prompt for extracting urgency signals.

        Args:
            company_name: Company name.
            raw_text: Raw signals text from Perplexity.

        Returns:
            Formatted prompt string.
        """
        return f"""You are extracting urgency signals for {company_name} that are relevant to a sales team selling Algolia search technology.

Below is a classification of news signals. Extract each signal into the required schema.
For each signal:
- signal_type: e.g. "leadership_change", "competitor_tech_move", "exec_public_commitment", "platform_migration", "ai_investment"
- description: detailed description of the signal
- urgency_level: high, medium, or low
- source_headline: the headline that triggered this signal
- date: YYYY-MM-DD or approximate

RAW TEXT:
{raw_text}"""

    @staticmethod
    def _build_summary_context(
        company_name: str,
        articles: list[NewsArticle],
        quotes: list[ExecutiveQuote],
        competitor_news: list[CompetitorNews],
    ) -> str:
        """Build context text for summary generation.

        Args:
            company_name: Prospect company name.
            articles: Extracted prospect articles.
            quotes: Extracted executive quotes.
            competitor_news: Extracted competitor news.

        Returns:
            Combined context string.
        """
        parts: list[str] = []

        if articles:
            article_lines = [
                f"- {a.headline} ({a.source}, {a.date}): {a.summary}" for a in articles[:10]
            ]
            parts.append(f"## {company_name} News:\n" + "\n".join(article_lines))

        if quotes:
            quote_lines = [
                f'- {q.executive_name} ({q.executive_title}): "{q.quote[:200]}" -- {q.context}'
                for q in quotes[:10]
            ]
            parts.append(f"## {company_name} Executive Quotes:\n" + "\n".join(quote_lines))

        for comp in competitor_news:
            if comp.articles:
                comp_lines = [f"- {a.headline} ({a.source}, {a.date})" for a in comp.articles[:5]]
                parts.append(f"## {comp.company_name} News:\n" + "\n".join(comp_lines))

        return "\n\n".join(parts)

    @staticmethod
    def _build_summary_prompt(company_name: str, context_text: str) -> str:
        """Build the prompt for generating news summary and competitive comparison.

        Args:
            company_name: Prospect company name.
            context_text: Combined context from articles and quotes.

        Returns:
            Formatted prompt string.
        """
        return f"""You are writing an intelligence summary for {company_name} for an Algolia sales team.

Based on the following structured news and quotes, produce:

1. news_summary: A 2-4 sentence overall intelligence summary highlighting the most important findings
   for a sales team selling search/discovery technology. Focus on sell signals, urgency,
   and strategic context.

2. competitive_comparison: If competitor news is available, write a brief comparison of what
   {company_name} is doing versus what competitors are doing. Frame it as market context.
   If no competitor news, leave empty.

CONTEXT:
{context_text}"""
