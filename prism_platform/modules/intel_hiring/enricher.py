"""Intel Hiring enricher -- Instructor + Claude to structure raw hiring data.

Takes raw data from the collector (Apify job listings or Perplexity text) and
uses Claude via Instructor to produce:
1. Classified open roles with ICP tiers
2. Build vs buy signal assessment
3. Buying committee mapping from executives + open roles
4. Hiring velocity metrics
5. Comparative summary across competitors
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from prism_platform.core.llm import create_completion
from prism_platform.modules.intel_hiring.schemas import (
    BuildVsBuySignal,
    BuyingCommittee,
    CompetitorHiring,
    HiringOutput,
    HiringVelocity,
    OpenRole,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Instructor wrapper models
# ---------------------------------------------------------------------------


class StructuredRoles(BaseModel):
    """Wrapper model for extracting classified open roles via Instructor."""

    model_config = ConfigDict(extra="forbid")
    roles: list[OpenRole] = Field(default_factory=list)


class StructuredVelocity(BaseModel):
    """Wrapper model for hiring velocity assessment."""

    model_config = ConfigDict(extra="forbid")
    velocity: HiringVelocity


class StructuredBuildVsBuy(BaseModel):
    """Wrapper model for build vs buy signal assessment."""

    model_config = ConfigDict(extra="forbid")
    build_vs_buy: BuildVsBuySignal


class StructuredBuyingCommittee(BaseModel):
    """Wrapper model for buying committee mapping."""

    model_config = ConfigDict(extra="forbid")
    buying_committee: BuyingCommittee


class StructuredSummary(BaseModel):
    """Wrapper model for generating summary and comparison text."""

    model_config = ConfigDict(extra="forbid")
    hiring_summary: str = Field(description="2-4 sentence overall hiring intelligence summary")
    comparative_summary: str = Field(
        default="",
        description="Summary comparing prospect and competitor hiring patterns",
    )


class HiringEnricher:
    """Structures raw hiring data into HiringOutput via Instructor + Claude."""

    def __init__(self) -> None:
        pass

    async def enrich(
        self,
        domain: str,
        company_name: str,
        raw_data: dict[str, Any],
        executives: list[dict[str, Any]],
    ) -> tuple[HiringOutput, int, float]:
        """Structure raw collector output into validated HiringOutput.

        Args:
            domain: The domain being researched.
            company_name: Name of the prospect company.
            raw_data: Dict from HiringCollector.collect_all() with keys:
                prospect_roles, competitor_roles, champion_signals, source_type.
            executives: List of executive dicts with 'name', 'title', 'relevance'.

        Returns:
            Tuple of (HiringOutput, llm_calls, llm_cost_usd).
        """
        logger.info("[HiringEnricher] structuring raw data", domain=domain)

        llm_calls = 0
        total_input_chars = 0
        total_output_chars = 0
        source_type = raw_data.get("source_type", "perplexity")

        # Step 1: Classify prospect open roles
        prospect_roles: list[OpenRole] = []
        raw_prospect = raw_data.get("prospect_roles", [])
        if raw_prospect:
            try:
                roles_text = self._format_raw_roles(raw_prospect, source_type, company_name)
                result = create_completion(
                    response_model=StructuredRoles,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_roles_prompt(
                                company_name, domain, roles_text, source_type
                            ),
                        },
                    ],
                )
                prospect_roles = result.roles
                llm_calls += 1
                total_input_chars += len(roles_text)
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[HiringEnricher] prospect roles classified",
                    count=len(prospect_roles),
                )
            except Exception as exc:
                logger.error(
                    "[HiringEnricher] prospect roles classification failed",
                    error=str(exc),
                )

        # Compute role_count_by_tier and search_related_count
        role_count_by_tier: dict[str, int] = {}
        for role in prospect_roles:
            tier = role.icp_tier
            role_count_by_tier[tier] = role_count_by_tier.get(tier, 0) + 1
        search_related_count = sum(1 for r in prospect_roles if r.search_related)

        # Step 2: Determine hiring velocity
        hiring_velocity: HiringVelocity | None = None
        if prospect_roles:
            try:
                velocity_text = self._format_velocity_context(prospect_roles, company_name)
                result = create_completion(
                    response_model=StructuredVelocity,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_velocity_prompt(company_name, velocity_text),
                        },
                    ],
                )
                hiring_velocity = result.velocity
                llm_calls += 1
                total_input_chars += len(velocity_text)
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[HiringEnricher] hiring velocity assessed",
                    trend=hiring_velocity.trend,
                )
            except Exception as exc:
                logger.error(
                    "[HiringEnricher] hiring velocity assessment failed",
                    error=str(exc),
                )

        # Step 3: Determine build vs buy signal
        build_vs_buy: BuildVsBuySignal | None = None
        if prospect_roles:
            try:
                bvb_text = self._format_build_vs_buy_context(prospect_roles, company_name)
                result = create_completion(
                    response_model=StructuredBuildVsBuy,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_bvb_prompt(company_name, bvb_text),
                        },
                    ],
                )
                build_vs_buy = result.build_vs_buy
                llm_calls += 1
                total_input_chars += len(bvb_text)
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[HiringEnricher] build vs buy assessed",
                    signal=build_vs_buy.signal,
                    confidence=build_vs_buy.confidence,
                )
            except Exception as exc:
                logger.error(
                    "[HiringEnricher] build vs buy assessment failed",
                    error=str(exc),
                )

        # Step 4: Map buying committee
        buying_committee: BuyingCommittee | None = None
        champion_signals = raw_data.get("champion_signals", {})
        if executives or prospect_roles:
            try:
                bc_text = self._format_buying_committee_context(
                    executives, prospect_roles, champion_signals, company_name
                )
                result = create_completion(
                    response_model=StructuredBuyingCommittee,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_buying_committee_prompt(company_name, bc_text),
                        },
                    ],
                )
                buying_committee = result.buying_committee
                llm_calls += 1
                total_input_chars += len(bc_text)
                total_output_chars += len(result.model_dump_json())
                logger.info(
                    "[HiringEnricher] buying committee mapped",
                    member_count=len(buying_committee.members),
                    confidence=buying_committee.confidence,
                )
            except Exception as exc:
                logger.error(
                    "[HiringEnricher] buying committee mapping failed",
                    error=str(exc),
                )

        # Step 5: Process competitor hiring
        competitor_hiring: list[CompetitorHiring] = []
        raw_competitors = raw_data.get("competitor_roles", {})
        for comp_name, comp_data in raw_competitors.items():
            if not isinstance(comp_data, dict):
                continue
            comp_domain = comp_data.get("domain", "")
            comp_raw_roles = comp_data.get("roles", [])

            if not comp_raw_roles:
                competitor_hiring.append(
                    CompetitorHiring(company_name=comp_name, domain=comp_domain)
                )
                continue

            try:
                comp_roles_text = self._format_raw_roles(comp_raw_roles, source_type, comp_name)
                result = create_completion(
                    response_model=StructuredRoles,
                    max_retries=3,
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_roles_prompt(
                                comp_name, comp_domain, comp_roles_text, source_type
                            ),
                        },
                    ],
                )
                comp_roles = result.roles
                comp_search_count = sum(1 for r in comp_roles if r.search_related)

                # Velocity for competitor
                comp_velocity: HiringVelocity | None = None
                if comp_roles:
                    try:
                        cv_text = self._format_velocity_context(comp_roles, comp_name)
                        cv_result = create_completion(
                            response_model=StructuredVelocity,
                            max_retries=3,
                            messages=[
                                {
                                    "role": "user",
                                    "content": self._build_velocity_prompt(comp_name, cv_text),
                                },
                            ],
                        )
                        comp_velocity = cv_result.velocity
                        llm_calls += 1
                        total_input_chars += len(cv_text)
                        total_output_chars += len(cv_result.model_dump_json())
                    except Exception as cv_exc:
                        logger.error(
                            "[HiringEnricher] competitor velocity failed",
                            competitor=comp_name,
                            error=str(cv_exc),
                        )

                competitor_hiring.append(
                    CompetitorHiring(
                        company_name=comp_name,
                        domain=comp_domain,
                        open_roles=comp_roles,
                        search_related_count=comp_search_count,
                        hiring_velocity=comp_velocity,
                    )
                )
                llm_calls += 1
                total_input_chars += len(comp_roles_text)
                total_output_chars += len(result.model_dump_json())
            except Exception as exc:
                logger.error(
                    "[HiringEnricher] competitor roles classification failed",
                    competitor=comp_name,
                    error=str(exc),
                )
                competitor_hiring.append(
                    CompetitorHiring(company_name=comp_name, domain=comp_domain)
                )

        # Step 6: Generate summary and comparative summary
        hiring_summary = ""
        comparative_summary = ""
        summary_context = self._build_summary_context(
            company_name,
            prospect_roles,
            hiring_velocity,
            build_vs_buy,
            buying_committee,
            competitor_hiring,
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
                hiring_summary = result.hiring_summary
                comparative_summary = result.comparative_summary
                llm_calls += 1
                total_input_chars += len(summary_context)
                total_output_chars += len(result.model_dump_json())
            except Exception as exc:
                logger.error(
                    "[HiringEnricher] summary generation failed",
                    error=str(exc),
                )

        # Claude Sonnet cost estimate: ~$0.10/1M input tokens, ~$0.40/1M output tokens
        estimated_cost = (total_input_chars / 4 / 1_000_000 * 0.10) + (
            total_output_chars / 4 / 1_000_000 * 0.40
        )

        output = HiringOutput(
            domain=domain,
            open_roles=prospect_roles,
            role_count_by_tier=role_count_by_tier,
            search_related_count=search_related_count,
            hiring_velocity=hiring_velocity,
            build_vs_buy=build_vs_buy,
            buying_committee=buying_committee,
            competitor_hiring=competitor_hiring,
            comparative_summary=comparative_summary,
            hiring_summary=hiring_summary,
        )

        logger.info(
            "[HiringEnricher] enrichment complete",
            domain=domain,
            roles_count=len(prospect_roles),
            search_related=search_related_count,
            velocity_trend=hiring_velocity.trend if hiring_velocity else "none",
            bvb_signal=build_vs_buy.signal if build_vs_buy else "none",
            committee_members=len(buying_committee.members) if buying_committee else 0,
            competitors_count=len(competitor_hiring),
            llm_calls=llm_calls,
            estimated_cost_usd=round(estimated_cost, 4),
        )

        return output, llm_calls, round(estimated_cost, 4)

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_raw_roles(
        raw_roles: list[Any],
        source_type: str,
        company_name: str,
    ) -> str:
        """Format raw role data into text for the LLM.

        Args:
            raw_roles: List of Apify job dicts or Perplexity text strings.
            source_type: 'linkedin' or 'perplexity'.
            company_name: Company name.

        Returns:
            Formatted text string.
        """
        if source_type == "linkedin":
            lines: list[str] = []
            for job in raw_roles:
                title = job.get("title", job.get("jobTitle", "Unknown"))
                location = job.get("location", job.get("formattedLocation", ""))
                url = job.get("url", job.get("link", ""))
                posted = job.get("postedDate", job.get("postedAt", ""))
                company = job.get("company", job.get("companyName", company_name))
                lines.append(
                    f"- Title: {title} | Location: {location} | "
                    f"Posted: {posted} | URL: {url} | Company: {company}"
                )
            return "\n".join(lines)
        else:
            # Perplexity returns list of text strings
            return "\n\n---\n\n".join(str(item) for item in raw_roles if item)

    @staticmethod
    def _format_velocity_context(roles: list[OpenRole], company_name: str) -> str:
        """Format role data for velocity assessment.

        Args:
            roles: Classified open roles.
            company_name: Company name.

        Returns:
            Formatted text.
        """
        lines = [f"Open roles for {company_name}:"]
        for r in roles:
            posted = r.posted_date or "unknown"
            lines.append(f"- {r.title} ({r.department}) posted {posted}")
        return "\n".join(lines)

    @staticmethod
    def _format_build_vs_buy_context(roles: list[OpenRole], company_name: str) -> str:
        """Format role data for build-vs-buy assessment.

        Args:
            roles: Classified open roles.
            company_name: Company name.

        Returns:
            Formatted text.
        """
        lines = [f"Open roles at {company_name} that may indicate build vs buy:"]
        for r in roles:
            signals_str = ", ".join(r.signals) if r.signals else "none"
            lines.append(
                f"- {r.title} (tier: {r.icp_tier}, search_related: {r.search_related}, "
                f"relevance: {r.relevance_score}, signals: {signals_str})"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_buying_committee_context(
        executives: list[dict[str, Any]],
        roles: list[OpenRole],
        champion_signals: dict[str, str],
        company_name: str,
    ) -> str:
        """Format executive and role data for buying committee mapping.

        Args:
            executives: List of executive dicts.
            roles: Classified open roles.
            champion_signals: Dict of exec_name -> Perplexity text.
            company_name: Company name.

        Returns:
            Formatted text.
        """
        parts: list[str] = [f"Buying committee context for {company_name}:"]

        if executives:
            parts.append("\n## Known Executives:")
            for ex in executives:
                name = ex.get("name", ex.get("full_name", ""))
                title = ex.get("title", "")
                relevance = ex.get("relevance", "other")
                signal_text = champion_signals.get(name, "")
                parts.append(f"- {name}, {title} (relevance: {relevance})")
                if signal_text:
                    parts.append(f"  Champion signals: {signal_text[:500]}")

        if roles:
            search_roles = [r for r in roles if r.search_related]
            leadership_roles = [
                r for r in roles if r.icp_tier in ("tier1_economic", "tier2_technical")
            ]
            if search_roles:
                parts.append("\n## Search-Related Open Roles:")
                for r in search_roles[:10]:
                    parts.append(f"- {r.title} ({r.department}, {r.location})")
            if leadership_roles:
                parts.append("\n## Leadership Open Roles:")
                for r in leadership_roles[:10]:
                    parts.append(f"- {r.title} ({r.department}, {r.location})")

        return "\n".join(parts)

    @staticmethod
    def _build_summary_context(
        company_name: str,
        roles: list[OpenRole],
        velocity: HiringVelocity | None,
        bvb: BuildVsBuySignal | None,
        committee: BuyingCommittee | None,
        competitors: list[CompetitorHiring],
    ) -> str:
        """Build summary context text.

        Args:
            company_name: Prospect company name.
            roles: Prospect open roles.
            velocity: Hiring velocity.
            bvb: Build vs buy signal.
            committee: Buying committee.
            competitors: Competitor hiring data.

        Returns:
            Combined context string.
        """
        parts: list[str] = []

        if roles:
            search_count = sum(1 for r in roles if r.search_related)
            parts.append(
                f"## {company_name} Hiring:\n"
                f"- Total open roles analyzed: {len(roles)}\n"
                f"- Search-related roles: {search_count}"
            )

        if velocity:
            parts.append(
                f"- Hiring velocity: {velocity.trend} "
                f"(30d: {velocity.roles_last_30d}, 90d: {velocity.roles_last_90d})"
            )

        if bvb:
            parts.append(f"- Build vs Buy: {bvb.signal} (confidence: {bvb.confidence})")

        if committee and committee.members:
            parts.append(f"- Buying committee: {len(committee.members)} members identified")

        for comp in competitors:
            if comp.open_roles:
                parts.append(
                    f"\n## {comp.company_name} Hiring:\n"
                    f"- Open roles: {len(comp.open_roles)}\n"
                    f"- Search-related: {comp.search_related_count}"
                )

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_roles_prompt(
        company_name: str,
        domain: str,
        roles_text: str,
        source_type: str,
    ) -> str:
        """Build the prompt for classifying open roles.

        Args:
            company_name: Company name.
            domain: Company domain.
            roles_text: Formatted role text.
            source_type: 'linkedin' or 'perplexity'.

        Returns:
            Formatted prompt string.
        """
        return f"""You are classifying open job roles for {company_name} ({domain}).
Source: {source_type}

Below is raw data about open positions. Extract and classify ALL roles into the required schema.
For each role:
- title: exact job title
- department: department or team (infer if not explicit)
- location: job location
- posted_date: YYYY-MM-DD format if available
- url: URL to the posting if available
- icp_tier: classify as:
  * tier1_economic: VP/Director/C-suite who controls budget (e.g. VP Engineering, CTO, VP Digital)
  * tier2_technical: Architect/Lead who evaluates technology (e.g. Principal Engineer, Tech Lead)
  * tier3_champion: Internal advocate/power user (e.g. Senior Search Engineer, Product Manager - Search)
  * tier4_user: End-user or IC (e.g. Frontend Developer, Content Editor)
- relevance_score: 0.0 to 1.0 how relevant to Algolia search/discovery technology
- search_related: True if directly related to search, discovery, personalization, or recommendation
- signals: list of hiring signals (e.g. "building search team", "replacing search vendor", "Elasticsearch experience required")
- source: "{source_type}"
- company_name: "{company_name}"

RAW DATA:
{roles_text}"""

    @staticmethod
    def _build_velocity_prompt(company_name: str, velocity_text: str) -> str:
        """Build the prompt for hiring velocity assessment.

        Args:
            company_name: Company name.
            velocity_text: Formatted velocity context.

        Returns:
            Formatted prompt string.
        """
        return f"""Assess the hiring velocity for {company_name} based on the open roles below.

Determine:
- roles_last_30d: estimate how many roles were posted in the last 30 days based on posted dates. If dates are unknown, estimate based on the total volume.
- roles_last_90d: estimate how many roles were posted in the last 90 days
- trend: classify as accelerating (hiring increasing), steady (stable), decelerating (hiring slowing), or insufficient_data
- interpretation: explain what the hiring velocity means for a sales team selling search technology

DATA:
{velocity_text}"""

    @staticmethod
    def _build_bvb_prompt(company_name: str, bvb_text: str) -> str:
        """Build the prompt for build vs buy signal assessment.

        Args:
            company_name: Company name.
            bvb_text: Formatted build-vs-buy context.

        Returns:
            Formatted prompt string.
        """
        return f"""Assess whether {company_name} is more likely to BUILD or BUY search technology based on their hiring patterns.

Signals for BUILD:
- Hiring search engineers, Elasticsearch/Solr engineers
- Building an internal search/discovery team
- Roles mention "building search from scratch"

Signals for BUY:
- Hiring product managers for search (evaluators, not builders)
- VP/Director-level search roles (decision-makers, not implementers)
- Roles mention "evaluating search vendors" or "integrating search APIs"
- No deep search engineering roles

Determine:
- signal: build, buy, mixed, or insufficient_data
- evidence: list of evidence items supporting the assessment
- confidence: high, medium, or low

DATA:
{bvb_text}"""

    @staticmethod
    def _build_buying_committee_prompt(company_name: str, bc_text: str) -> str:
        """Build the prompt for buying committee mapping.

        Args:
            company_name: Company name.
            bc_text: Formatted buying committee context.

        Returns:
            Formatted prompt string.
        """
        return f"""Map the buying committee for search technology at {company_name}.

From the executives and open roles below, identify who would be involved in a search technology purchase decision.

For each person, determine:
- name: full name
- title: job title
- role: classify as:
  * economic_buyer: controls the budget (VP/Director/C-suite)
  * technical_evaluator: evaluates technology fit (architect/lead engineer)
  * champion_candidate: likely internal advocate for new search tech
  * influencer: can influence the decision but doesn't control budget
  * blocker: may resist change (e.g. invested in current solution)
  * unknown: insufficient data to classify
- linkedin_url: LinkedIn URL if found in champion signals
- tenure_description: how long in current role if known
- previous_company: previous employer if known
- champion_signals: list of signals indicating champion potential (e.g. "previously used Algolia", "spoke at search conference")

Also assess:
- confidence: how confident we are in this mapping (high/medium/low)
- methodology: brief description of how the committee was identified

DATA:
{bc_text}"""

    @staticmethod
    def _build_summary_prompt(company_name: str, context_text: str) -> str:
        """Build the prompt for summary generation.

        Args:
            company_name: Prospect company name.
            context_text: Combined summary context.

        Returns:
            Formatted prompt string.
        """
        return f"""You are writing a hiring intelligence summary for {company_name} for an Algolia sales team.

Based on the following data, produce:

1. hiring_summary: A 2-4 sentence overall intelligence summary highlighting the most important
   hiring signals for a sales team selling search/discovery technology. Focus on:
   - Are they building or buying search?
   - Who are the key decision-makers?
   - What is the urgency based on hiring velocity?
   - What is the competitive context?

2. comparative_summary: If competitor data is available, compare {company_name}'s hiring patterns
   with competitors. Frame it as market context for the sales team.
   If no competitor data, leave empty.

CONTEXT:
{context_text}"""
