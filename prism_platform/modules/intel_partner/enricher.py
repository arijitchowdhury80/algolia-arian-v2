"""Intel Partner enricher -- Instructor + Claude to structure raw partner data.

Takes raw data from the collector (Crossbeam overlaps + Perplexity text) and
uses Claude via Instructor to produce:
1. Structured partner overlaps
2. Co-sell opportunities with pitch narratives
3. SI relationship mapping
4. Vertical case studies
5. Competitor partner analysis
6. Recommended partner play
7. Overall summary
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from prism_platform.core.llm import create_completion
from prism_platform.modules.intel_partner.schemas import (
    CompetitorPartner,
    CoSellOpportunity,
    PartnerOutput,
    PartnerOverlap,
    PartnerPlay,
    SIRelationship,
    VerticalCaseStudy,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Instructor wrapper models
# ---------------------------------------------------------------------------


class StructuredPartnerOverlaps(BaseModel):
    """Wrapper model for extracting partner overlaps via Instructor."""

    model_config = ConfigDict(extra="forbid")
    overlaps: list[PartnerOverlap] = Field(default_factory=list)


class StructuredCoSellOpportunities(BaseModel):
    """Wrapper model for extracting co-sell opportunities via Instructor."""

    model_config = ConfigDict(extra="forbid")
    opportunities: list[CoSellOpportunity] = Field(default_factory=list)


class StructuredSIRelationships(BaseModel):
    """Wrapper model for extracting SI relationships via Instructor."""

    model_config = ConfigDict(extra="forbid")
    relationships: list[SIRelationship] = Field(default_factory=list)


class StructuredCaseStudies(BaseModel):
    """Wrapper model for extracting vertical case studies via Instructor."""

    model_config = ConfigDict(extra="forbid")
    case_studies: list[VerticalCaseStudy] = Field(default_factory=list)


class StructuredPartnershipNews(BaseModel):
    """Wrapper model for extracting recent partnership news."""

    model_config = ConfigDict(extra="forbid")
    partnerships: list[str] = Field(
        default_factory=list,
        description="List of recent partnership announcements as concise descriptions",
    )


class StructuredCompetitorPartners(BaseModel):
    """Wrapper model for extracting competitor partner data."""

    model_config = ConfigDict(extra="forbid")
    competitors: list[CompetitorPartner] = Field(default_factory=list)


class StructuredPartnerPlayAndSummary(BaseModel):
    """Wrapper model for generating partner play and summary."""

    model_config = ConfigDict(extra="forbid")
    partner_play: PartnerPlay
    partner_summary: str = Field(
        description=(
            "2-4 sentence overall partner intelligence summary highlighting "
            "the most actionable insights for an Algolia sales team."
        ),
    )


class PartnerEnricher:
    """Structures raw partner data into PartnerOutput via Instructor + Claude."""

    def __init__(self) -> None:
        pass

    async def enrich(
        self,
        domain: str,
        company_name: str,
        industry: str,
        raw_data: dict[str, Any],
    ) -> tuple[PartnerOutput, int, float]:
        """Structure raw collector output into validated PartnerOutput.

        Args:
            domain: The domain being researched.
            company_name: Name of the prospect company.
            industry: Industry vertical of the prospect.
            raw_data: Dict from PartnerCollector.collect_all().

        Returns:
            Tuple of (PartnerOutput, llm_calls, llm_cost_usd).
        """
        logger.info("[PartnerEnricher] structuring raw data", domain=domain)

        llm_calls = 0
        total_input_chars = 0
        total_output_chars = 0
        crossbeam_available = raw_data.get("crossbeam_available", False)

        # Step 1: Structure partner overlaps
        partner_overlaps: list[PartnerOverlap] = []
        overlaps_context = self._build_overlaps_context(raw_data, company_name, domain)
        if overlaps_context.strip():
            try:
                result = create_completion(
                    response_model=StructuredPartnerOverlaps,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_overlaps_prompt(
                                company_name, domain, overlaps_context
                            ),
                        },
                    ],
                )
                partner_overlaps = result.overlaps
                llm_calls += 1
                total_input_chars += len(overlaps_context)
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[PartnerEnricher] partner overlaps structured",
                    count=len(partner_overlaps),
                )
            except Exception as exc:
                logger.error(
                    "[PartnerEnricher] partner overlaps structuring failed",
                    error=str(exc),
                )

        # Step 2: Structure SI relationships
        si_relationships: list[SIRelationship] = []
        si_text = raw_data.get("si_research", "")
        if si_text.strip():
            try:
                result = create_completion(
                    response_model=StructuredSIRelationships,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_si_prompt(company_name, domain, si_text),
                        },
                    ],
                )
                si_relationships = result.relationships
                llm_calls += 1
                total_input_chars += len(si_text)
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[PartnerEnricher] SI relationships structured",
                    count=len(si_relationships),
                )
            except Exception as exc:
                logger.error(
                    "[PartnerEnricher] SI relationships structuring failed",
                    error=str(exc),
                )

        # Step 3: Structure co-sell opportunities
        co_sell_opportunities: list[CoSellOpportunity] = []
        tech_text = raw_data.get("tech_partners_research", "")
        if tech_text.strip():
            try:
                result = create_completion(
                    response_model=StructuredCoSellOpportunities,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_cosell_prompt(company_name, domain, tech_text),
                        },
                    ],
                )
                co_sell_opportunities = result.opportunities
                llm_calls += 1
                total_input_chars += len(tech_text)
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[PartnerEnricher] co-sell opportunities structured",
                    count=len(co_sell_opportunities),
                )
            except Exception as exc:
                logger.error(
                    "[PartnerEnricher] co-sell opportunities structuring failed",
                    error=str(exc),
                )

        # Step 4: Structure vertical case studies
        vertical_case_studies: list[VerticalCaseStudy] = []
        case_text = raw_data.get("case_studies_research", "")
        if case_text.strip():
            try:
                result = create_completion(
                    response_model=StructuredCaseStudies,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_case_studies_prompt(
                                company_name, domain, industry, case_text
                            ),
                        },
                    ],
                )
                vertical_case_studies = result.case_studies
                llm_calls += 1
                total_input_chars += len(case_text)
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[PartnerEnricher] case studies structured",
                    count=len(vertical_case_studies),
                )
            except Exception as exc:
                logger.error(
                    "[PartnerEnricher] case studies structuring failed",
                    error=str(exc),
                )

        # Step 5: Structure partnership news
        recent_partnerships: list[str] = []
        news_text = raw_data.get("partnership_news", "")
        if news_text.strip():
            try:
                result = create_completion(
                    response_model=StructuredPartnershipNews,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_news_prompt(company_name, domain, news_text),
                        },
                    ],
                )
                recent_partnerships = result.partnerships
                llm_calls += 1
                total_input_chars += len(news_text)
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[PartnerEnricher] partnership news structured",
                    count=len(recent_partnerships),
                )
            except Exception as exc:
                logger.error(
                    "[PartnerEnricher] partnership news structuring failed",
                    error=str(exc),
                )

        # Step 6: Structure competitor partners
        competitor_partners: list[CompetitorPartner] = []
        comp_text = raw_data.get("competitor_partners_research", "")
        if comp_text.strip():
            try:
                result = create_completion(
                    response_model=StructuredCompetitorPartners,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_competitor_prompt(
                                company_name, domain, comp_text
                            ),
                        },
                    ],
                )
                competitor_partners = result.competitors
                llm_calls += 1
                total_input_chars += len(comp_text)
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[PartnerEnricher] competitor partners structured",
                    count=len(competitor_partners),
                )
            except Exception as exc:
                logger.error(
                    "[PartnerEnricher] competitor partners structuring failed",
                    error=str(exc),
                )

        # Step 7: Generate partner play and summary
        partner_play: PartnerPlay | None = None
        partner_summary = ""
        play_context = self._build_play_context(
            company_name,
            domain,
            industry,
            partner_overlaps,
            co_sell_opportunities,
            si_relationships,
            vertical_case_studies,
            recent_partnerships,
            competitor_partners,
            crossbeam_available,
        )
        if play_context.strip():
            try:
                result = create_completion(
                    response_model=StructuredPartnerPlayAndSummary,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_play_prompt(company_name, domain, play_context),
                        },
                    ],
                )
                partner_play = result.partner_play
                partner_summary = result.partner_summary
                llm_calls += 1
                total_input_chars += len(play_context)
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[PartnerEnricher] partner play and summary generated",
                    recommended_partner=partner_play.recommended_partner,
                    confidence=partner_play.confidence,
                )
            except Exception as exc:
                logger.error(
                    "[PartnerEnricher] partner play and summary generation failed",
                    error=str(exc),
                )

        # Claude Sonnet cost: ~$0.10/1M input tokens, ~$0.40/1M output tokens
        estimated_cost = (total_input_chars / 4 / 1_000_000 * 0.10) + (
            total_output_chars / 4 / 1_000_000 * 0.40
        )

        output = PartnerOutput(
            domain=domain,
            partner_overlaps=partner_overlaps,
            co_sell_opportunities=co_sell_opportunities,
            si_relationships=si_relationships,
            vertical_case_studies=vertical_case_studies,
            recent_partnerships=recent_partnerships,
            competitor_partners=competitor_partners,
            partner_play=partner_play,
            partner_summary=partner_summary,
            crossbeam_available=crossbeam_available,
        )

        logger.info(
            "[PartnerEnricher] enrichment complete",
            domain=domain,
            overlaps_count=len(partner_overlaps),
            cosell_count=len(co_sell_opportunities),
            si_count=len(si_relationships),
            case_studies_count=len(vertical_case_studies),
            news_count=len(recent_partnerships),
            competitor_count=len(competitor_partners),
            has_play=partner_play is not None,
            crossbeam_available=crossbeam_available,
            llm_calls=llm_calls,
            estimated_cost_usd=round(estimated_cost, 4),
        )

        return output, llm_calls, round(estimated_cost, 4)

    # ------------------------------------------------------------------
    # Context builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_overlaps_context(
        raw_data: dict[str, Any],
        company_name: str,
        domain: str,
    ) -> str:
        """Build context text for partner overlap structuring.

        Args:
            raw_data: Raw collector output.
            company_name: Company name.
            domain: Company domain.

        Returns:
            Combined context string.
        """
        parts: list[str] = []

        # Crossbeam data if available
        crossbeam_overlaps = raw_data.get("crossbeam_overlaps", {})
        if crossbeam_overlaps and crossbeam_overlaps.get("data"):
            parts.append("## Crossbeam Overlap Data:")
            for item in crossbeam_overlaps["data"]:
                partner = item.get("partner_name", "Unknown")
                count = item.get("shared_account_count", 0)
                parts.append(f"- {partner}: {count} shared accounts")

        crossbeam_pops = raw_data.get("crossbeam_populations", {})
        if crossbeam_pops and crossbeam_pops.get("data"):
            parts.append("\n## Crossbeam Partner Populations:")
            for item in crossbeam_pops["data"]:
                partner = item.get("partner_name", "Unknown")
                pop_type = item.get("type", "")
                parts.append(f"- {partner} ({pop_type})")

        # Perplexity tech partners research (supplements Crossbeam)
        tech_text = raw_data.get("tech_partners_research", "")
        if tech_text.strip():
            parts.append(f"\n## Technology Partner Research for {company_name} ({domain}):")
            parts.append(tech_text)

        return "\n".join(parts)

    @staticmethod
    def _build_play_context(
        company_name: str,
        domain: str,
        industry: str,
        overlaps: list[PartnerOverlap],
        cosell: list[CoSellOpportunity],
        si_rels: list[SIRelationship],
        case_studies: list[VerticalCaseStudy],
        news: list[str],
        competitor_partners: list[CompetitorPartner],
        crossbeam_available: bool,
    ) -> str:
        """Build context text for partner play and summary generation.

        Args:
            company_name: Company name.
            domain: Company domain.
            industry: Industry vertical.
            overlaps: Structured partner overlaps.
            cosell: Structured co-sell opportunities.
            si_rels: Structured SI relationships.
            case_studies: Structured case studies.
            news: Recent partnership news.
            competitor_partners: Competitor partner data.
            crossbeam_available: Whether Crossbeam data was used.

        Returns:
            Combined context string.
        """
        parts: list[str] = [
            f"## Partner Intelligence for {company_name} ({domain})",
            f"Industry: {industry}",
            f"Crossbeam data available: {crossbeam_available}",
        ]

        if overlaps:
            parts.append(f"\n### Partner Overlaps ({len(overlaps)}):")
            for o in overlaps:
                parts.append(
                    f"- {o.partner_name} ({o.partner_type}): "
                    f"strength={o.relationship_strength}, "
                    f"prospect_overlap={o.prospect_overlap}"
                )

        if cosell:
            parts.append(f"\n### Co-Sell Opportunities ({len(cosell)}):")
            for c in cosell:
                parts.append(
                    f"- {c.partner_name} ({c.partner_type}): "
                    f"tech_confirmed={c.technology_confirmed}, "
                    f"algolia_integration={c.algolia_integration}, "
                    f"confidence={c.confidence}"
                )
                if c.pitch:
                    parts.append(f"  Pitch: {c.pitch}")

        if si_rels:
            parts.append(f"\n### SI Relationships ({len(si_rels)}):")
            for s in si_rels:
                parts.append(f"- {s.si_name} ({s.relationship_type}): source={s.confirmed_source}")
                if s.warm_intro_path:
                    parts.append(f"  Warm intro: {s.warm_intro_path}")

        if case_studies:
            parts.append(f"\n### Vertical Case Studies ({len(case_studies)}):")
            for cs in case_studies:
                metric = f" ({cs.key_metric})" if cs.key_metric else ""
                parts.append(f"- {cs.customer_name}: {cs.use_case}{metric}")

        if news:
            parts.append(f"\n### Recent Partnership News ({len(news)}):")
            for n in news:
                parts.append(f"- {n}")

        if competitor_partners:
            parts.append(f"\n### Competitor Partners ({len(competitor_partners)}):")
            for cp in competitor_partners:
                parts.append(f"- {cp.company_name}: {', '.join(cp.known_partners[:5])}")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_overlaps_prompt(company_name: str, domain: str, context: str) -> str:
        """Build prompt for structuring partner overlaps.

        Args:
            company_name: Company name.
            domain: Company domain.
            context: Formatted context text.

        Returns:
            Formatted prompt string.
        """
        return f"""Extract and structure partner overlaps for {company_name} ({domain}).

From the data below, identify all partners and their relationship to {company_name}.
For each partner:
- partner_name: name of the partner organization
- partner_type: classify as 'si' (system integrator), 'technology', 'agency', 'consulting', or 'other'
- shared_account_count: number of shared accounts if from Crossbeam data, null otherwise
- prospect_overlap: True if this partner has a direct relationship with {company_name}
- relationship_strength: 'strong' (confirmed multi-year), 'moderate' (recent/active), 'weak' (rumored/indirect), or 'unknown'
- notes: brief context about the relationship

DATA:
{context}"""

    @staticmethod
    def _build_si_prompt(company_name: str, domain: str, si_text: str) -> str:
        """Build prompt for structuring SI relationships.

        Args:
            company_name: Company name.
            domain: Company domain.
            si_text: Raw Perplexity text about SI relationships.

        Returns:
            Formatted prompt string.
        """
        return f"""Extract system integrator (SI) relationships for {company_name} ({domain}).

For each SI found:
- si_name: name of the system integrator
- relationship_type: 'implementation', 'consulting', 'managed_services', or 'unknown'
- confirmed_source: 'perplexity' (since this is from web research)
- warm_intro_path: if there's a path to a warm intro via shared customers, describe it. e.g. 'Slalom serves both {company_name} and Shoe Carnival (Algolia customer)'. null if no path found.
- algolia_customer_connection: name of an existing Algolia customer that also uses this SI, if known. null otherwise.

RAW DATA:
{si_text}"""

    @staticmethod
    def _build_cosell_prompt(company_name: str, domain: str, tech_text: str) -> str:
        """Build prompt for structuring co-sell opportunities.

        Args:
            company_name: Company name.
            domain: Company domain.
            tech_text: Raw Perplexity text about tech partners.

        Returns:
            Formatted prompt string.
        """
        return f"""Identify co-sell opportunities for Algolia at {company_name} ({domain}).

Algolia has integrations/connectors with these platforms:
- Salesforce Commerce Cloud (SFCC)
- Adobe Commerce / Magento
- Shopify / Shopify Plus
- BigCommerce
- commercetools
- SAP Commerce Cloud
- Contentful
- Contentstack
- Adobe Experience Manager

For each co-sell opportunity:
- partner_name: technology partner or SI name
- partner_type: 'si', 'technology', 'agency', 'consulting', or 'other'
- technology_confirmed: True ONLY if there is strong evidence {company_name} uses this technology
- algolia_integration: True if Algolia has a known connector/integration (see list above)
- pitch: a 1-2 sentence pitch connecting {company_name}, the partner, and Algolia. Format: "Prospect uses [platform] (confirmed/suspected) -> Algolia has [platform] connector -> [Partner] implements both"
- confidence: 'high' if technology is confirmed AND Algolia has integration, 'medium' if one is confirmed, 'low' if speculative

RAW DATA:
{tech_text}"""

    @staticmethod
    def _build_case_studies_prompt(
        company_name: str,
        domain: str,
        industry: str,
        case_text: str,
    ) -> str:
        """Build prompt for structuring vertical case studies.

        Args:
            company_name: Company name.
            domain: Company domain.
            industry: Industry vertical.
            case_text: Raw Perplexity text about case studies.

        Returns:
            Formatted prompt string.
        """
        return f"""Extract Algolia case studies relevant to {company_name} ({domain}) in the {industry} industry.

For each case study:
- customer_name: name of the Algolia customer
- domain: customer's website domain if mentioned
- industry: their industry vertical
- use_case: primary use case (site search, product discovery, recommendations, etc.)
- key_metric: key outcome metric if mentioned (e.g. '37% conversion lift', '10x faster search'). null if not available.
- url: URL to the published case study if available. null if not found.

Only include real Algolia case studies. Do not fabricate customers or metrics.

RAW DATA:
{case_text}"""

    @staticmethod
    def _build_news_prompt(company_name: str, domain: str, news_text: str) -> str:
        """Build prompt for structuring partnership news.

        Args:
            company_name: Company name.
            domain: Company domain.
            news_text: Raw Perplexity text about partnership news.

        Returns:
            Formatted prompt string.
        """
        return f"""Extract recent partnership announcements for {company_name} ({domain}).

Return a list of concise 1-sentence descriptions of each partnership or technology announcement.
Focus on partnerships relevant to e-commerce, search, digital transformation, and technology platforms.
Include the date and source if available in the description.

Only include real, verifiable announcements. Do not fabricate news.

RAW DATA:
{news_text}"""

    @staticmethod
    def _build_competitor_prompt(company_name: str, domain: str, comp_text: str) -> str:
        """Build prompt for structuring competitor partner data.

        Args:
            company_name: Company name.
            domain: Company domain.
            comp_text: Raw Perplexity text about competitor partners.

        Returns:
            Formatted prompt string.
        """
        return f"""Extract competitor partner ecosystem data for {company_name} ({domain}).

For each competitor:
- company_name: competitor name
- domain: competitor domain
- known_partners: list of known technology and SI partners
- overlap_with_prospect_partners: list of partners that both {company_name} and this competitor use

RAW DATA:
{comp_text}"""

    @staticmethod
    def _build_play_prompt(company_name: str, domain: str, context: str) -> str:
        """Build prompt for generating partner play and summary.

        Args:
            company_name: Company name.
            domain: Company domain.
            context: Combined context with all partner intelligence.

        Returns:
            Formatted prompt string.
        """
        return f"""You are an Algolia partner sales strategist. Based on the partner intelligence below for {company_name} ({domain}), generate:

1. partner_play: The single best partner play for the Algolia sales team.
   - recommended_partner: Which partner to engage FIRST
   - partner_type: 'si', 'technology', 'agency', 'consulting', or 'other'
   - approach_reason: WHY this partner should be engaged first (2-3 sentences). Consider: existing relationship strength, technology confirmation, warm intro paths, and deal acceleration potential.
   - pitch_message: WHAT to say to the partner (3-5 sentences). This should be a ready-to-use outreach message or talking points that connect {company_name}'s needs with the partner's value and Algolia's solution.
   - confidence: 'high' if backed by confirmed data, 'medium' if partially confirmed, 'low' if speculative

2. partner_summary: A 2-4 sentence executive summary of the partner landscape for {company_name}. Focus on:
   - Key partners that could accelerate the deal
   - Strongest co-sell opportunities
   - Any warm introduction paths
   - Competitive context from partner ecosystems

PARTNER INTELLIGENCE:
{context}"""
