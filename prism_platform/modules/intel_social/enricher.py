"""Intel Social enricher -- Instructor + Claude to structure raw social data.

Takes the raw text responses from the collector and uses Claude via Instructor
to produce validated SocialOutput with structured posts, executive quotes,
Twitter activity, competitor social, and summary.
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from prism_platform.core.llm import create_completion
from prism_platform.modules.intel_social.schemas import (
    CompetitorSocial,
    ExecutiveQuote,
    SocialOutput,
    SocialPost,
    TwitterActivity,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Instructor wrapper models
# ---------------------------------------------------------------------------


class StructuredPosts(BaseModel):
    """Wrapper model for extracting a list of social posts via Instructor."""

    model_config = ConfigDict(extra="forbid")
    posts: list[SocialPost] = Field(default_factory=list)


class StructuredQuotes(BaseModel):
    """Wrapper model for extracting a list of executive quotes via Instructor."""

    model_config = ConfigDict(extra="forbid")
    quotes: list[ExecutiveQuote] = Field(default_factory=list)


class StructuredTwitter(BaseModel):
    """Wrapper model for extracting Twitter/X activity via Instructor."""

    model_config = ConfigDict(extra="forbid")
    activity: TwitterActivity


class StructuredCompetitor(BaseModel):
    """Wrapper model for extracting competitor social data via Instructor."""

    model_config = ConfigDict(extra="forbid")
    posts: list[SocialPost] = Field(default_factory=list)
    exec_quotes: list[ExecutiveQuote] = Field(default_factory=list)
    key_finding: str = Field(
        default="",
        description="One-line summary of the most important finding",
    )


class StructuredSummary(BaseModel):
    """Wrapper model for generating summary text."""

    model_config = ConfigDict(extra="forbid")
    social_summary: str = Field(description="2-4 sentence overall social intelligence summary")
    competitive_comparison: str = Field(
        default="",
        description="Summary comparing prospect and competitor social activity",
    )
    most_quotable: list[str] = Field(
        default_factory=list,
        description="Top 5 most quotable statements for sales use",
    )


class SocialEnricher:
    """Structures raw social data into SocialOutput via Instructor + Claude."""

    def __init__(self) -> None:
        pass

    async def enrich(
        self,
        domain: str,
        company_name: str,
        raw_data: dict[str, Any],
    ) -> tuple[SocialOutput, int, float]:
        """Structure raw collector output into validated SocialOutput.

        Args:
            domain: The domain being researched.
            company_name: Name of the prospect company.
            raw_data: Dict from SocialCollector.collect_all() with keys:
                linkedin_activity, public_statements, apify_posts,
                twitter, competitor_social.

        Returns:
            Tuple of (SocialOutput, llm_calls, llm_cost_usd).

        Raises:
            instructor.exceptions.InstructorRetryException: After failed attempts.
        """
        logger.info("[SocialEnricher] structuring raw data", domain=domain)

        llm_calls = 0
        total_input_chars = 0
        total_output_chars = 0

        # Step 1: Extract prospect posts from LinkedIn activity + Apify data
        prospect_posts: list[SocialPost] = []
        linkedin_text = self._combine_linkedin_text(raw_data, company_name)
        if linkedin_text.strip():
            try:
                result = create_completion(
                    response_model=StructuredPosts,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_posts_prompt(
                                company_name, domain, linkedin_text
                            ),
                        },
                    ],
                )
                prospect_posts = result.posts
                llm_calls += 1
                total_input_chars += len(linkedin_text)
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[SocialEnricher] prospect posts extracted",
                    count=len(prospect_posts),
                )
            except Exception as exc:
                logger.error(
                    "[SocialEnricher] prospect posts extraction failed",
                    error=str(exc),
                )

        # Step 2: Extract executive quotes from public statements
        prospect_exec_quotes: list[ExecutiveQuote] = []
        statements_text = self._combine_statements_text(raw_data)
        if statements_text.strip():
            try:
                result = create_completion(
                    response_model=StructuredQuotes,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_quotes_prompt(company_name, statements_text),
                        },
                    ],
                )
                prospect_exec_quotes = result.quotes
                llm_calls += 1
                total_input_chars += len(statements_text)
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[SocialEnricher] exec quotes extracted",
                    count=len(prospect_exec_quotes),
                )
            except Exception as exc:
                logger.error(
                    "[SocialEnricher] exec quotes extraction failed",
                    error=str(exc),
                )

        # Step 3: Extract Twitter/X activity
        twitter_activity: TwitterActivity | None = None
        twitter_text: str = raw_data.get("twitter", "")
        if twitter_text.strip():
            try:
                result = create_completion(
                    response_model=StructuredTwitter,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_twitter_prompt(company_name, twitter_text),
                        },
                    ],
                )
                twitter_activity = result.activity
                llm_calls += 1
                total_input_chars += len(twitter_text)
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[SocialEnricher] twitter activity extracted",
                    is_active=twitter_activity.is_active,
                    post_count=len(twitter_activity.recent_posts),
                )
            except Exception as exc:
                logger.error(
                    "[SocialEnricher] twitter extraction failed",
                    error=str(exc),
                )

        # Step 4: Extract competitor social
        competitor_social: list[CompetitorSocial] = []
        raw_competitors: dict[str, Any] = raw_data.get("competitor_social", {})
        for _key, comp_data in raw_competitors.items():
            if not isinstance(comp_data, dict):
                continue
            comp_name = comp_data.get("company_name", "")
            comp_domain = comp_data.get("domain", "")
            exec_texts: dict[str, str] = comp_data.get("exec_texts", {})
            combined_text = "\n\n".join(
                f"### {label}:\n{text}"
                for label, text in exec_texts.items()
                if isinstance(text, str) and text.strip()
            )
            if not combined_text.strip():
                competitor_social.append(
                    CompetitorSocial(company_name=comp_name, domain=comp_domain)
                )
                continue

            try:
                result = create_completion(
                    response_model=StructuredCompetitor,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_competitor_prompt(comp_name, combined_text),
                        },
                    ],
                )
                competitor_social.append(
                    CompetitorSocial(
                        company_name=comp_name,
                        domain=comp_domain,
                        posts=result.posts,
                        exec_quotes=result.exec_quotes,
                        key_finding=result.key_finding,
                    )
                )
                llm_calls += 1
                total_input_chars += len(combined_text)
                total_output_chars += len(result.model_dump_json())
            except Exception as exc:
                logger.error(
                    "[SocialEnricher] competitor social extraction failed",
                    competitor=comp_name,
                    error=str(exc),
                )
                competitor_social.append(
                    CompetitorSocial(company_name=comp_name, domain=comp_domain)
                )

        # Step 5: Generate summary, competitive comparison, most quotable
        social_summary = ""
        competitive_comparison = ""
        most_quotable: list[str] = []
        summary_context = self._build_summary_context(
            company_name, prospect_posts, prospect_exec_quotes, competitor_social
        )
        if summary_context.strip():
            try:
                result = create_completion(
                    response_model=StructuredSummary,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_summary_prompt(company_name, summary_context),
                        },
                    ],
                )
                social_summary = result.social_summary
                competitive_comparison = result.competitive_comparison
                most_quotable = result.most_quotable[:5]
                llm_calls += 1
                total_input_chars += len(summary_context)
                total_output_chars += len(result.model_dump_json())
            except Exception as exc:
                logger.error(
                    "[SocialEnricher] summary generation failed",
                    error=str(exc),
                )

        # Compute relevance counts
        high_relevance_count = sum(
            1
            for item in [*prospect_posts, *prospect_exec_quotes]
            if item.algolia_relevance == "high"
        )
        medium_relevance_count = sum(
            1
            for item in [*prospect_posts, *prospect_exec_quotes]
            if item.algolia_relevance == "medium"
        )

        # Claude Sonnet cost estimate: ~$0.10/1M input tokens, ~$0.40/1M output tokens
        estimated_cost = (total_input_chars / 4 / 1_000_000 * 0.10) + (
            total_output_chars / 4 / 1_000_000 * 0.40
        )

        output = SocialOutput(
            domain=domain,
            prospect_posts=prospect_posts,
            prospect_exec_quotes=prospect_exec_quotes,
            high_relevance_count=high_relevance_count,
            medium_relevance_count=medium_relevance_count,
            most_quotable=most_quotable,
            twitter_activity=twitter_activity,
            competitor_social=competitor_social,
            competitive_comparison=competitive_comparison,
            social_summary=social_summary,
        )

        logger.info(
            "[SocialEnricher] enrichment complete",
            domain=domain,
            posts_count=len(prospect_posts),
            quotes_count=len(prospect_exec_quotes),
            high_relevance=high_relevance_count,
            medium_relevance=medium_relevance_count,
            quotable_count=len(most_quotable),
            competitors_count=len(competitor_social),
            llm_calls=llm_calls,
            estimated_cost_usd=round(estimated_cost, 4),
        )

        return output, llm_calls, round(estimated_cost, 4)

    # ------------------------------------------------------------------
    # Text combination helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _combine_linkedin_text(raw_data: dict[str, Any], company_name: str) -> str:
        """Combine LinkedIn activity text and Apify posts into a single prompt input.

        Args:
            raw_data: Raw collector output.
            company_name: Company name for context.

        Returns:
            Combined text string.
        """
        parts: list[str] = []

        # Perplexity LinkedIn activity
        linkedin_activity: dict[str, str] = raw_data.get("linkedin_activity", {})
        for name, text in linkedin_activity.items():
            if isinstance(text, str) and text.strip():
                label = "Company Page" if name == "__company_page__" else name
                parts.append(f"### LinkedIn activity for {label}:\n{text}")

        # Apify posts
        apify_posts: list[dict[str, Any]] = raw_data.get("apify_posts", [])
        if apify_posts:
            apify_lines: list[str] = []
            for post in apify_posts[:20]:
                text = post.get("text", post.get("content", ""))
                author = post.get("authorName", post.get("author", company_name))
                date = post.get("postedDate", post.get("date", ""))
                likes = post.get("numLikes", post.get("likes", 0))
                comments = post.get("numComments", post.get("comments", 0))
                apify_lines.append(
                    f"- Author: {author} | Date: {date} | Likes: {likes} | Comments: {comments}\n"
                    f"  Content: {text[:500]}"
                )
            parts.append(
                f"### Apify LinkedIn company posts for {company_name}:\n" + "\n".join(apify_lines)
            )

        return "\n\n".join(parts)

    @staticmethod
    def _combine_statements_text(raw_data: dict[str, Any]) -> str:
        """Combine public statement texts into a single prompt input.

        Args:
            raw_data: Raw collector output.

        Returns:
            Combined text string.
        """
        statements: dict[str, str] = raw_data.get("public_statements", {})
        parts: list[str] = []
        for name, text in statements.items():
            if isinstance(text, str) and text.strip():
                parts.append(f"### Public statements by {name}:\n{text}")
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_posts_prompt(company_name: str, domain: str, raw_text: str) -> str:
        """Build prompt for extracting structured social posts.

        Args:
            company_name: Company name.
            domain: Company domain.
            raw_text: Raw LinkedIn/social activity text.

        Returns:
            Formatted prompt string.
        """
        return f"""You are extracting structured social media posts for {company_name} ({domain}).

Below is raw research text about LinkedIn activity and social posts. Extract ALL posts
into the required schema.
For each post:
- author_name: full name of the post author
- author_title: their job title
- company_name: set to "{company_name}" unless they work elsewhere
- platform: linkedin, twitter, youtube, conference, podcast, interview, or other
- content_summary: 1-3 sentence summary of the post content
- date: YYYY-MM-DD or approximate
- url: post URL if mentioned
- engagement_likes: number of likes if mentioned
- engagement_comments: number of comments if mentioned
- topic: digital_strategy, technology_investment, customer_experience, search_related,
  ai_related, hiring, culture, product_launch, competitive, or other
- algolia_relevance: high (mentions search/discovery/AI directly), medium (mentions
  digital transformation/tech investment), or low (general business)
- quotable_statement: the most quotable part for a sales team, or null if nothing quotable

RAW TEXT:
{raw_text}"""

    @staticmethod
    def _build_quotes_prompt(company_name: str, raw_text: str) -> str:
        """Build prompt for extracting structured executive quotes.

        Args:
            company_name: Company name.
            raw_text: Combined public statements text.

        Returns:
            Formatted prompt string.
        """
        return f"""You are extracting executive public statements for {company_name}.

Below is raw research text about executives at {company_name}. Extract ALL verbatim
or near-verbatim quotes from public appearances (conferences, podcasts, interviews,
webinars, keynotes).
For each quote:
- executive_name: full name
- executive_title: job title
- company_name: "{company_name}"
- quote: the verbatim quote text (must be actual quote, not a paraphrase)
- context: where/when it was said (e.g. "CES 2026 keynote", "Bloomberg interview")
- source_type: keynote, conference, podcast, interview, webinar, article, youtube, or other
- source_url: URL if available
- date: YYYY-MM-DD or approximate
- topic: digital_strategy, technology_investment, customer_experience, search_related,
  ai_related, competitive_positioning, growth_commitment, cost_optimization, or other
- algolia_relevance: high (mentions search/discovery/AI investment), medium (mentions
  digital transformation/tech budget), or low (general statement)
- sales_angle: how an AE can use this quote in a pitch (if applicable), or null

Only include quotes that are actual statements by the executive, not reporter paraphrases.

RAW TEXT:
{raw_text}"""

    @staticmethod
    def _build_twitter_prompt(company_name: str, raw_text: str) -> str:
        """Build prompt for extracting Twitter/X activity.

        Args:
            company_name: Company name.
            raw_text: Raw Twitter/X search text.

        Returns:
            Formatted prompt string.
        """
        return f"""You are extracting Twitter/X activity for {company_name}.

Below is raw research text about {company_name}'s Twitter/X presence. Structure it as:
- company_name: "{company_name}"
- is_active: true if there is meaningful recent activity (2025-2026), false otherwise
- recent_posts: list of social posts (same schema as LinkedIn posts, but platform="twitter")
- summary: one-line summary of their Twitter/X activity themes

RAW TEXT:
{raw_text}"""

    @staticmethod
    def _build_competitor_prompt(comp_name: str, raw_text: str) -> str:
        """Build prompt for extracting competitor social data.

        Args:
            comp_name: Competitor company name.
            raw_text: Combined competitor exec social text.

        Returns:
            Formatted prompt string.
        """
        return f"""You are extracting social intelligence for competitor {comp_name}.

Below is raw research text about {comp_name}'s executive social activity. Extract:
1. posts: social media posts from their executives
2. exec_quotes: verbatim public statements from their executives
3. key_finding: one-line summary of the most important finding for a sales team

For posts, use the same schema as prospect posts.
For exec_quotes, use the same schema as prospect quotes.

RAW TEXT:
{raw_text}"""

    @staticmethod
    def _build_summary_context(
        company_name: str,
        posts: list[SocialPost],
        quotes: list[ExecutiveQuote],
        competitor_social: list[CompetitorSocial],
    ) -> str:
        """Build context text for summary generation.

        Args:
            company_name: Prospect company name.
            posts: Extracted prospect posts.
            quotes: Extracted executive quotes.
            competitor_social: Extracted competitor social data.

        Returns:
            Combined context string.
        """
        parts: list[str] = []

        if posts:
            post_lines = [
                f"- {p.author_name} ({p.platform}, {p.date}): {p.content_summary[:200]}"
                for p in posts[:10]
            ]
            parts.append(f"## {company_name} Social Posts:\n" + "\n".join(post_lines))

        if quotes:
            quote_lines = [
                f'- {q.executive_name} ({q.executive_title}): "{q.quote[:200]}" -- {q.context}'
                for q in quotes[:10]
            ]
            parts.append(f"## {company_name} Executive Quotes:\n" + "\n".join(quote_lines))

        for comp in competitor_social:
            comp_parts: list[str] = []
            if comp.posts:
                comp_parts.extend(
                    f"- {p.author_name}: {p.content_summary[:150]}" for p in comp.posts[:5]
                )
            if comp.exec_quotes:
                comp_parts.extend(
                    f'- {q.executive_name}: "{q.quote[:150]}"' for q in comp.exec_quotes[:5]
                )
            if comp_parts:
                parts.append(f"## {comp.company_name} Social Activity:\n" + "\n".join(comp_parts))

        return "\n\n".join(parts)

    @staticmethod
    def _build_summary_prompt(company_name: str, context_text: str) -> str:
        """Build prompt for generating social summary and competitive comparison.

        Args:
            company_name: Prospect company name.
            context_text: Combined context from posts and quotes.

        Returns:
            Formatted prompt string.
        """
        return f"""You are writing a social intelligence summary for {company_name} for an Algolia sales team.

Based on the following structured social posts and executive quotes, produce:

1. social_summary: A 2-4 sentence overall social intelligence summary highlighting
   the most important findings for a sales team selling search/discovery technology.
   Focus on executive priorities, technology signals, and any search/AI mentions.

2. competitive_comparison: If competitor social data is available, write a brief
   comparison of what {company_name} executives are saying vs competitors.
   Frame it as competitive intelligence. If no competitor data, leave empty.

3. most_quotable: Extract the top 5 most useful quotable statements for an AE.
   These should be verbatim quotes or near-verbatim statements that a sales rep
   can reference in a pitch. If fewer than 5, include what's available.

CONTEXT:
{context_text}"""
