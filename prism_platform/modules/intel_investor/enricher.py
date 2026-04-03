"""Intel Investor enricher -- Instructor + Claude for quote extraction and Said vs Found.

This is where the magic happens. All raw Perplexity responses are structured into
typed Pydantic schemas via Instructor + Claude:

1. Extract EarningsQuote objects from earnings call transcripts
2. Generate SaidVsFound mappings (THE CORE DELIVERABLE)
3. Extract competitor quotes as competitive ammunition
4. Analyze board composition for tech backgrounds
5. Extract 10-K risk factors with Algolia relevance
6. Structure YouTube / conference appearances
7. Generate top_sales_angles summary
"""

from __future__ import annotations

import structlog
from pydantic import BaseModel, ConfigDict, Field

from prism_platform.core.llm import create_completion
from prism_platform.modules.intel_investor.schemas import (
    BoardMember,
    CompetitorInvestorIntel,
    EarningsQuote,
    RiskFactor,
    SaidVsFound,
    YouTubeAppearance,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Instructor wrapper models (for batch extraction)
# ---------------------------------------------------------------------------


class EarningsQuoteList(BaseModel):
    """Wrapper for extracting a list of earnings quotes via Instructor."""

    model_config = ConfigDict(extra="forbid")

    quotes: list[EarningsQuote] = Field(
        default_factory=list,
        description="List of executive quotes extracted from earnings call transcripts",
    )


class SaidVsFoundList(BaseModel):
    """Wrapper for generating Said vs Found mappings via Instructor."""

    model_config = ConfigDict(extra="forbid")

    mappings: list[SaidVsFound] = Field(
        default_factory=list,
        description="Mappings from executive quotes to Algolia sales angles",
    )


class CompetitorIntelModel(BaseModel):
    """Wrapper for extracting competitor investor intelligence via Instructor."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Competitor company name")
    ticker: str | None = Field(default=None, description="Competitor ticker")
    domain: str = Field(default="", description="Competitor domain")
    key_quotes: list[EarningsQuote] = Field(
        default_factory=list,
        description="Key executive quotes from competitor earnings calls",
    )
    competitive_ammunition: list[str] = Field(
        default_factory=list,
        description="How competitor quotes strengthen our pitch against them",
    )


class BoardMemberList(BaseModel):
    """Wrapper for extracting board members via Instructor."""

    model_config = ConfigDict(extra="forbid")

    members: list[BoardMember] = Field(
        default_factory=list,
        description="Board members extracted from search results",
    )


class RiskFactorList(BaseModel):
    """Wrapper for extracting risk factors via Instructor."""

    model_config = ConfigDict(extra="forbid")

    factors: list[RiskFactor] = Field(
        default_factory=list,
        description="Technology-related risk factors from 10-K filings",
    )


class YouTubeAppearanceList(BaseModel):
    """Wrapper for extracting YouTube appearances via Instructor."""

    model_config = ConfigDict(extra="forbid")

    appearances: list[YouTubeAppearance] = Field(
        default_factory=list,
        description="Executive YouTube and conference appearances",
    )


class InvestorSummaryModel(BaseModel):
    """Wrapper for generating investor intelligence summary via Instructor."""

    model_config = ConfigDict(extra="forbid")

    investor_summary: str = Field(
        description=(
            "3-5 sentence executive summary of all investor intelligence findings. "
            "Highlight the most important insights for an Algolia AE."
        ),
    )
    top_sales_angles: list[str] = Field(
        description=(
            "Top 5 sales angles for the AE, prioritized by impact. "
            "Each should be a 1-2 sentence actionable talking point."
        ),
    )


# ---------------------------------------------------------------------------
# Enricher class
# ---------------------------------------------------------------------------


class InvestorEnricher:
    """Enriches raw investor data into structured schemas via Instructor + Claude."""

    def __init__(self) -> None:
        self._llm_calls = 0
        self._llm_cost = 0.0

    @property
    def llm_calls(self) -> int:
        """Total LLM calls made by the enricher."""
        return self._llm_calls

    @property
    def llm_cost(self) -> float:
        """Estimated total LLM cost in USD."""
        return round(self._llm_cost, 4)

    # ------------------------------------------------------------------
    # Part 1: Extract Earnings Quotes
    # ------------------------------------------------------------------

    async def extract_earnings_quotes(
        self,
        transcript_texts: list[str],
        company_name: str,
    ) -> list[EarningsQuote]:
        """Extract structured EarningsQuote objects from raw transcript text.

        Args:
            transcript_texts: Raw text from Perplexity, one per quarter.
            company_name: Company name for context.

        Returns:
            List of EarningsQuote with categorization and flags.
        """
        if not transcript_texts:
            logger.info("[InvestorEnricher] no transcript texts to process")
            return []

        logger.info(
            "[InvestorEnricher] extracting earnings quotes",
            company_name=company_name,
            transcript_count=len(transcript_texts),
        )

        all_quotes: list[EarningsQuote] = []

        for i, text in enumerate(transcript_texts):
            try:
                result = create_completion(
                    response_model=EarningsQuoteList,
                    max_retries=2,
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                f"Extract executive quotes from this {company_name} earnings "
                                f"call transcript content.\n\n"
                                f"For each quote:\n"
                                f"- speaker_name: Full name of the executive\n"
                                f"- speaker_title: Their title (CEO, CFO, CTO, etc.)\n"
                                f"- quote: Verbatim or near-verbatim quote\n"
                                f"- context: What was being discussed\n"
                                f"- quarter: e.g. 'Q4 FY2025'\n"
                                f"- source: e.g. 'Q4 FY2025 Earnings Call Transcript'\n"
                                f"- category: Classify as one of: digital_investment, "
                                f"technology_strategy, customer_experience, search_related, "
                                f"ai_related, platform_modernization, revenue_growth, "
                                f"cost_optimization, competitive, pain_signal, other\n"
                                f"- dollar_amount: If a specific dollar amount is mentioned\n"
                                f"- is_commitment: True if exec is committing to something\n"
                                f"- urgency_level: high/medium/low\n\n"
                                f"Focus on quotes about:\n"
                                f"- Digital transformation and technology investment\n"
                                f"- Customer experience and search/discovery\n"
                                f"- AI and machine learning initiatives\n"
                                f"- Platform modernization\n"
                                f"- Revenue growth from digital channels\n"
                                f"- Pain points and challenges\n\n"
                                f"Transcript text:\n{text}"
                            ),
                        },
                    ],
                )
                self._llm_calls += 1
                self._estimate_cost(text, result.model_dump_json())

                all_quotes.extend(result.quotes)
                logger.debug(
                    "[InvestorEnricher] quotes extracted from transcript",
                    transcript_index=i,
                    quotes_found=len(result.quotes),
                )

            except Exception:
                logger.exception(
                    "[InvestorEnricher] quote extraction failed for transcript",
                    transcript_index=i,
                    company_name=company_name,
                )

        logger.info(
            "[InvestorEnricher] earnings quote extraction complete",
            company_name=company_name,
            total_quotes=len(all_quotes),
        )
        return all_quotes

    # ------------------------------------------------------------------
    # Part 2: Generate Said vs Found Mappings (THE CORE DELIVERABLE)
    # ------------------------------------------------------------------

    async def generate_said_vs_found(
        self,
        quotes: list[EarningsQuote],
        company_name: str,
    ) -> list[SaidVsFound]:
        """Generate Said vs Found mappings from executive quotes to Algolia angles.

        This is THE CORE DELIVERABLE of the investor module. Each mapping connects
        an executive quote to a specific Algolia sales angle with a recommended
        talking point for the AE.

        Args:
            quotes: List of EarningsQuote to map.
            company_name: Company name for context.

        Returns:
            List of SaidVsFound mappings.
        """
        if not quotes:
            logger.info("[InvestorEnricher] no quotes for Said vs Found mapping")
            return []

        logger.info(
            "[InvestorEnricher] generating Said vs Found mappings",
            company_name=company_name,
            quote_count=len(quotes),
        )

        # Serialize quotes for the prompt
        quotes_text = ""
        for i, q in enumerate(quotes):
            quotes_text += (
                f"\n--- Quote {i + 1} ---\n"
                f"Speaker: {q.speaker_name} ({q.speaker_title})\n"
                f"Quarter: {q.quarter}\n"
                f"Category: {q.category}\n"
                f'Quote: "{q.quote}"\n'
                f"Context: {q.context}\n"
                f"Commitment: {q.is_commitment}\n"
                f"Urgency: {q.urgency_level}\n"
            )

        try:
            result = create_completion(
                response_model=SaidVsFoundList,
                max_retries=2,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"You are an Algolia sales strategist. For each executive quote "
                            f"from {company_name}, create a Said vs Found mapping that connects "
                            f"the quote to an Algolia sales angle.\n\n"
                            f"Algolia products:\n"
                            f"- Algolia Search: AI-powered site search with instant results\n"
                            f"- Algolia Recommend: Product recommendations and personalization\n"
                            f"- Algolia AI Search: Natural language search with LLM understanding\n"
                            f"- Algolia Browse: Category and collection pages\n"
                            f"- Algolia Analytics: Search analytics and A/B testing\n\n"
                            f"For each mapping:\n"
                            f"- algolia_angle: How this quote connects to Algolia's value prop\n"
                            f"- recommended_talking_point: What an AE should say. Be specific "
                            f"and reference the exec's own words.\n"
                            f"- product_relevance: Which Algolia products are most relevant\n"
                            f"- confidence: high (direct search/discovery mention), medium "
                            f"(related digital/CX topic), low (general tech investment)\n\n"
                            f"Map the most impactful quotes. Skip generic quotes that don't "
                            f"connect to search, discovery, or customer experience.\n\n"
                            f"Executive quotes:\n{quotes_text}"
                        ),
                    },
                ],
            )
            self._llm_calls += 1
            self._estimate_cost(quotes_text, result.model_dump_json())

            logger.info(
                "[InvestorEnricher] Said vs Found mappings generated",
                company_name=company_name,
                mappings_count=len(result.mappings),
            )
            return result.mappings

        except Exception:
            logger.exception(
                "[InvestorEnricher] Said vs Found generation failed",
                company_name=company_name,
            )
            return []

    # ------------------------------------------------------------------
    # Part 3: Extract Competitor Investor Intel
    # ------------------------------------------------------------------

    async def extract_competitor_intel(
        self,
        competitor_transcripts: dict[str, list[str]],
        competitor_info: list[dict[str, str]],
    ) -> list[CompetitorInvestorIntel]:
        """Extract competitor investor intelligence from earnings transcripts.

        Args:
            competitor_transcripts: Dict mapping company_name to raw text list.
            competitor_info: List of dicts with 'company_name', 'ticker', 'domain'.

        Returns:
            List of CompetitorInvestorIntel with quotes and competitive ammunition.
        """
        if not competitor_transcripts:
            logger.info("[InvestorEnricher] no competitor transcripts to process")
            return []

        logger.info(
            "[InvestorEnricher] extracting competitor intel",
            competitors=len(competitor_transcripts),
        )

        results: list[CompetitorInvestorIntel] = []
        info_map = {c["company_name"]: c for c in competitor_info}

        for comp_name, texts in competitor_transcripts.items():
            combined = "\n\n---\n\n".join(texts)
            info = info_map.get(comp_name, {})

            try:
                result = create_completion(
                    response_model=CompetitorIntelModel,
                    max_retries=2,
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                f"Extract investor intelligence from {comp_name}'s earnings "
                                f"call content. Focus on quotes about technology, search, AI, "
                                f"customer experience, and digital transformation.\n\n"
                                f"For competitive_ammunition: explain how each finding can "
                                f"strengthen an Algolia pitch against this competitor. "
                                f"Example: 'Competitor CTO says AI search drove 35% lift -- "
                                f"your prospect is falling behind.'\n\n"
                                f"Company: {comp_name}\n"
                                f"Ticker: {info.get('ticker', 'N/A')}\n"
                                f"Domain: {info.get('domain', 'N/A')}\n\n"
                                f"Transcript content:\n{combined}"
                            ),
                        },
                    ],
                )
                self._llm_calls += 1
                self._estimate_cost(combined, result.model_dump_json())

                results.append(
                    CompetitorInvestorIntel(
                        company_name=result.company_name or comp_name,
                        ticker=result.ticker or info.get("ticker"),
                        domain=result.domain or info.get("domain", ""),
                        key_quotes=result.key_quotes,
                        competitive_ammunition=result.competitive_ammunition,
                    )
                )

            except Exception:
                logger.exception(
                    "[InvestorEnricher] competitor intel extraction failed",
                    company_name=comp_name,
                )

        logger.info(
            "[InvestorEnricher] competitor intel extraction complete",
            competitors_processed=len(results),
        )
        return results

    # ------------------------------------------------------------------
    # Part 4: Board Analysis
    # ------------------------------------------------------------------

    async def extract_board_members(
        self,
        board_text: str,
        company_name: str,
    ) -> list[BoardMember]:
        """Extract and analyze board members from raw text.

        Args:
            board_text: Raw text about board composition from Perplexity.
            company_name: Company name for context.

        Returns:
            List of BoardMember with tech background flags.
        """
        if not board_text:
            logger.info("[InvestorEnricher] no board text to process")
            return []

        logger.info(
            "[InvestorEnricher] extracting board members",
            company_name=company_name,
        )

        try:
            result = create_completion(
                response_model=BoardMemberList,
                max_retries=2,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Extract board of directors information for {company_name}.\n\n"
                            f"For each board member:\n"
                            f"- name: Full name\n"
                            f"- title: Board title (Independent Director, Board Chair, etc.)\n"
                            f"- background: Brief professional background\n"
                            f"- has_tech_background: True if they have technology, digital, "
                            f"or software experience\n"
                            f"- relevance_note: Why this board member matters for an Algolia "
                            f"pitch (e.g., 'Former CTO of Salesforce -- likely champion for "
                            f"modern search technology')\n\n"
                            f"Board information:\n{board_text}"
                        ),
                    },
                ],
            )
            self._llm_calls += 1
            self._estimate_cost(board_text, result.model_dump_json())

            logger.info(
                "[InvestorEnricher] board members extracted",
                company_name=company_name,
                count=len(result.members),
                tech_count=sum(1 for m in result.members if m.has_tech_background),
            )
            return result.members

        except Exception:
            logger.exception(
                "[InvestorEnricher] board extraction failed",
                company_name=company_name,
            )
            return []

    # ------------------------------------------------------------------
    # Part 5: Risk Factor Extraction
    # ------------------------------------------------------------------

    async def extract_risk_factors(
        self,
        risk_text: str,
        company_name: str,
    ) -> list[RiskFactor]:
        """Extract technology-related risk factors from 10-K analysis text.

        Args:
            risk_text: Raw text from Perplexity about 10-K risk factors.
            company_name: Company name for context.

        Returns:
            List of RiskFactor with Algolia relevance.
        """
        if not risk_text:
            logger.info("[InvestorEnricher] no risk factor text to process")
            return []

        logger.info(
            "[InvestorEnricher] extracting risk factors",
            company_name=company_name,
        )

        try:
            result = create_completion(
                response_model=RiskFactorList,
                max_retries=2,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Extract technology-related risk factors from {company_name}'s "
                            f"10-K filing analysis.\n\n"
                            f"For each risk factor:\n"
                            f"- category: technology, cybersecurity, competition, "
                            f"digital_disruption, legacy_systems, or other\n"
                            f"- excerpt: The relevant excerpt from the filing\n"
                            f"- filing_source: e.g. '10-K FY2025'\n"
                            f"- algolia_relevance: How this risk connects to search/discovery. "
                            f"Example: 'Legacy search infrastructure is a risk factor -- "
                            f"Algolia can modernize without a full platform migration.'\n\n"
                            f"Focus on risks related to:\n"
                            f"- Technology infrastructure\n"
                            f"- Customer experience / digital experience\n"
                            f"- Search and discovery capabilities\n"
                            f"- Competitive threats from digital-first players\n"
                            f"- Legacy system dependencies\n\n"
                            f"Risk factor analysis:\n{risk_text}"
                        ),
                    },
                ],
            )
            self._llm_calls += 1
            self._estimate_cost(risk_text, result.model_dump_json())

            logger.info(
                "[InvestorEnricher] risk factors extracted",
                company_name=company_name,
                count=len(result.factors),
            )
            return result.factors

        except Exception:
            logger.exception(
                "[InvestorEnricher] risk factor extraction failed",
                company_name=company_name,
            )
            return []

    # ------------------------------------------------------------------
    # Part 6: YouTube Appearances
    # ------------------------------------------------------------------

    async def extract_youtube_appearances(
        self,
        youtube_text: str,
        company_name: str,
    ) -> list[YouTubeAppearance]:
        """Extract structured YouTube/conference appearances from raw text.

        Args:
            youtube_text: Raw text from Perplexity about appearances.
            company_name: Company name for context.

        Returns:
            List of YouTubeAppearance objects.
        """
        if not youtube_text:
            logger.info("[InvestorEnricher] no YouTube text to process")
            return []

        logger.info(
            "[InvestorEnricher] extracting YouTube appearances",
            company_name=company_name,
        )

        try:
            result = create_completion(
                response_model=YouTubeAppearanceList,
                max_retries=2,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Extract YouTube and conference appearance information "
                            f"for {company_name} executives.\n\n"
                            f"For each appearance:\n"
                            f"- title: Video or presentation title\n"
                            f"- channel: YouTube channel or conference name\n"
                            f"- date: Date if known\n"
                            f"- url: URL if available\n"
                            f"- speaker: Executive name\n"
                            f"- key_topics: Topics discussed\n"
                            f"- key_quotes: Notable quotes\n\n"
                            f"Appearance information:\n{youtube_text}"
                        ),
                    },
                ],
            )
            self._llm_calls += 1
            self._estimate_cost(youtube_text, result.model_dump_json())

            logger.info(
                "[InvestorEnricher] YouTube appearances extracted",
                company_name=company_name,
                count=len(result.appearances),
            )
            return result.appearances

        except Exception:
            logger.exception(
                "[InvestorEnricher] YouTube extraction failed",
                company_name=company_name,
            )
            return []

    # ------------------------------------------------------------------
    # Part 7: Generate Summary and Top Sales Angles
    # ------------------------------------------------------------------

    async def generate_summary(
        self,
        company_name: str,
        quotes: list[EarningsQuote],
        said_vs_found: list[SaidVsFound],
        board_members: list[BoardMember],
        risk_factors: list[RiskFactor],
        competitor_intel: list[CompetitorInvestorIntel],
    ) -> tuple[str, list[str]]:
        """Generate investor summary and top sales angles.

        Args:
            company_name: Company name.
            quotes: All extracted earnings quotes.
            said_vs_found: All Said vs Found mappings.
            board_members: Board composition.
            risk_factors: 10-K risk factors.
            competitor_intel: Competitor intelligence.

        Returns:
            Tuple of (investor_summary, top_sales_angles).
        """
        logger.info(
            "[InvestorEnricher] generating investor summary",
            company_name=company_name,
            quotes=len(quotes),
            mappings=len(said_vs_found),
        )

        # Build context summary for the LLM
        context_parts: list[str] = []

        if quotes:
            commitment_count = sum(1 for q in quotes if q.is_commitment)
            pain_count = sum(1 for q in quotes if q.category == "pain_signal")
            context_parts.append(
                f"Earnings Quotes: {len(quotes)} total, {commitment_count} commitments, "
                f"{pain_count} pain signals"
            )

        if said_vs_found:
            high_conf = sum(1 for s in said_vs_found if s.confidence == "high")
            context_parts.append(
                f"Said vs Found: {len(said_vs_found)} mappings, {high_conf} high-confidence"
            )

        if board_members:
            tech_count = sum(1 for b in board_members if b.has_tech_background)
            context_parts.append(
                f"Board: {len(board_members)} members, {tech_count} with tech background"
            )

        if risk_factors:
            context_parts.append(f"Risk Factors: {len(risk_factors)} technology-related risks")

        if competitor_intel:
            context_parts.append(f"Competitors: {len(competitor_intel)} competitors analyzed")

        context_text = "\n".join(context_parts)

        # Add top Said vs Found for specificity
        svf_text = ""
        for s in said_vs_found[:5]:
            svf_text += f'\n- "{s.executive_quote.quote[:100]}..." -> {s.algolia_angle}\n'

        try:
            result = create_completion(
                response_model=InvestorSummaryModel,
                max_retries=2,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Generate an investor intelligence summary for {company_name} "
                            f"targeting an Algolia Account Executive.\n\n"
                            f"Intelligence gathered:\n{context_text}\n\n"
                            f"Top Said vs Found mappings:\n{svf_text}\n\n"
                            f"For investor_summary: Write a 3-5 sentence executive summary "
                            f"highlighting the most important findings for a sales conversation.\n\n"
                            f"For top_sales_angles: List the 5 most powerful angles for the AE, "
                            f"prioritized by impact. Each should be 1-2 sentences and actionable."
                        ),
                    },
                ],
            )
            self._llm_calls += 1
            self._estimate_cost(context_text + svf_text, result.model_dump_json())

            logger.info(
                "[InvestorEnricher] investor summary generated",
                company_name=company_name,
                angles_count=len(result.top_sales_angles),
            )
            return result.investor_summary, result.top_sales_angles

        except Exception:
            logger.exception(
                "[InvestorEnricher] summary generation failed",
                company_name=company_name,
            )
            return "", []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

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
