"""Synth Sales Plays enricher -- Instructor + Claude for sales playbook generation.

Takes collected upstream module outputs and generates a comprehensive sales playbook
using Claude for the LLM-powered portions: MEDDPICC mapping, SPIN questions,
objection handling, talk tracks, power map, and summary.
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from prism_platform.core.llm import create_completion
from prism_platform.modules.synth_sales_plays.schemas import (
    MEDDPICCField,
    ObjectionHandler,
    PowerMapMember,
    SalesPlaysOutput,
    SPINQuestion,
    TalkTrack,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Instructor response models for each LLM call
# ---------------------------------------------------------------------------


class MEDDPICCSynthesis(BaseModel):
    """LLM-generated MEDDPICC mapping from upstream data."""

    model_config = ConfigDict(extra="forbid")

    fields: list[MEDDPICCField] = Field(
        description="MEDDPICC fields populated with evidence from the prospect's data. "
        "Aim for at least 5 of the 8 fields: metrics, economic_buyer, decision_criteria, "
        "decision_process, paper_process, identified_pain, champion, competition."
    )


class SPINSynthesis(BaseModel):
    """LLM-generated SPIN questions from upstream data."""

    model_config = ConfigDict(extra="forbid")

    questions: list[SPINQuestion] = Field(
        description="SPIN selling questions across all 4 categories: "
        "situation, problem, implication, need_payoff. "
        "At least 2 questions per category, 8+ total. "
        "Each question must reference specific data from the prospect's audit."
    )


class ObjectionSynthesis(BaseModel):
    """LLM-generated objection handlers from upstream data."""

    model_config = ConfigDict(extra="forbid")

    handlers: list[ObjectionHandler] = Field(
        description="Anticipated objections with data-backed counter arguments. "
        "At least 2 handlers. Common objections include: 'building in-house', "
        "'happy with current vendor', 'budget constraints', 'not a priority', "
        "'too complex to switch'."
    )


class TalkTrackSynthesis(BaseModel):
    """LLM-generated talk tracks from upstream data."""

    model_config = ConfigDict(extra="forbid")

    tracks: list[TalkTrack] = Field(
        description="Sales talk tracks with at least 1 opener, 1 bridge, and 1 close. "
        "Where possible, mirror executive language from investor calls or social posts."
    )


class PowerMapSynthesis(BaseModel):
    """LLM-generated power map from upstream data."""

    model_config = ConfigDict(extra="forbid")

    members: list[PowerMapMember] = Field(
        description="Buying committee members with MEDDPICC roles and attitudes. "
        "At least 1 member. Assign roles based on title and tier data."
    )


class SummarySynthesis(BaseModel):
    """LLM-generated playbook summary and top actions."""

    model_config = ConfigDict(extra="forbid")

    playbook_summary: str = Field(
        description="2-4 sentence executive summary of the entire sales playbook. "
        "Focus on the strongest selling angle and what makes this deal winnable."
    )
    top_3_actions: list[str] = Field(
        description="Exactly 3 concrete next-step actions for the AE. "
        "Each should be specific and actionable, not generic advice."
    )


class SalesPlaysEnricher:
    """Generates sales playbooks from upstream module outputs using Claude."""

    def __init__(self) -> None:
        pass

    async def synthesize(
        self,
        domain: str,
        company_name: str,
        company_context: dict[str, Any],
        buying_committee: list[dict[str, Any]],
        exec_quotes: list[dict[str, str]],
        competitive_context: dict[str, Any],
        financial_context: dict[str, Any],
        business_case_context: dict[str, Any],
        raw_data: dict[str, Any],
    ) -> tuple[SalesPlaysOutput, int, float]:
        """Synthesize all extracted data into a sales playbook.

        Makes multiple LLM calls to Claude via Instructor:
        1. MEDDPICC mapping
        2. SPIN questions
        3. Objection handling
        4. Talk tracks
        5. Power map
        6. Summary + top 3 actions

        Args:
            domain: The prospect domain.
            company_name: The prospect company name.
            company_context: Company overview data.
            buying_committee: Extracted buying committee members.
            exec_quotes: Executive quotes from investor/social modules.
            competitive_context: Competitive landscape data.
            financial_context: Financial data.
            business_case_context: ROI and business case data.
            raw_data: Full upstream module output dict for context.

        Returns:
            Tuple of (SalesPlaysOutput, llm_calls count, llm_cost_usd).
        """
        logger.info(
            "[SalesPlays] synthesize started",
            domain=domain,
            company_name=company_name,
            committee_size=len(buying_committee),
            quotes_count=len(exec_quotes),
            has_competitors=competitive_context.get("current_vendor") is not None,
            has_financials=financial_context.get("revenue") is not None,
        )

        llm_calls = 0
        llm_cost_usd = 0.0

        # Build shared context for all prompts
        base_context = self._build_base_context(
            domain=domain,
            company_name=company_name,
            company_context=company_context,
            buying_committee=buying_committee,
            exec_quotes=exec_quotes,
            competitive_context=competitive_context,
            financial_context=financial_context,
            business_case_context=business_case_context,
        )

        # 1. MEDDPICC mapping
        meddpicc_fields: list[MEDDPICCField] = []
        try:
            meddpicc_result = self._call_llm(
                prompt=self._build_meddpicc_prompt(base_context),
                response_model=MEDDPICCSynthesis,
                call_label="meddpicc",
                domain=domain,
            )
            meddpicc_fields = meddpicc_result.fields
            llm_calls += 1
            llm_cost_usd += 0.005
        except Exception as exc:
            logger.error(
                "[SalesPlays] MEDDPICC synthesis failed",
                domain=domain,
                error=str(exc),
            )

        # 2. SPIN questions
        spin_questions: list[SPINQuestion] = []
        try:
            spin_result = self._call_llm(
                prompt=self._build_spin_prompt(base_context),
                response_model=SPINSynthesis,
                call_label="spin",
                domain=domain,
            )
            spin_questions = spin_result.questions
            llm_calls += 1
            llm_cost_usd += 0.005
        except Exception as exc:
            logger.error(
                "[SalesPlays] SPIN synthesis failed",
                domain=domain,
                error=str(exc),
            )

        # 3. Objection handling
        objection_handlers: list[ObjectionHandler] = []
        try:
            objection_result = self._call_llm(
                prompt=self._build_objection_prompt(base_context),
                response_model=ObjectionSynthesis,
                call_label="objections",
                domain=domain,
            )
            objection_handlers = objection_result.handlers
            llm_calls += 1
            llm_cost_usd += 0.005
        except Exception as exc:
            logger.error(
                "[SalesPlays] Objection synthesis failed",
                domain=domain,
                error=str(exc),
            )

        # 4. Talk tracks
        talk_tracks: list[TalkTrack] = []
        try:
            talk_result = self._call_llm(
                prompt=self._build_talk_track_prompt(base_context),
                response_model=TalkTrackSynthesis,
                call_label="talk_tracks",
                domain=domain,
            )
            talk_tracks = talk_result.tracks
            llm_calls += 1
            llm_cost_usd += 0.005
        except Exception as exc:
            logger.error(
                "[SalesPlays] Talk track synthesis failed",
                domain=domain,
                error=str(exc),
            )

        # 5. Power map
        power_map: list[PowerMapMember] = []
        if buying_committee:
            try:
                power_result = self._call_llm(
                    prompt=self._build_power_map_prompt(base_context),
                    response_model=PowerMapSynthesis,
                    call_label="power_map",
                    domain=domain,
                )
                power_map = power_result.members
                llm_calls += 1
                llm_cost_usd += 0.005
            except Exception as exc:
                logger.error(
                    "[SalesPlays] Power map synthesis failed",
                    domain=domain,
                    error=str(exc),
                )

        # 6. Summary + top 3 actions
        playbook_summary = ""
        top_3_actions: list[str] = []
        try:
            summary_result = self._call_llm(
                prompt=self._build_summary_prompt(
                    base_context=base_context,
                    meddpicc_count=len(meddpicc_fields),
                    spin_count=len(spin_questions),
                    objection_count=len(objection_handlers),
                    power_map_count=len(power_map),
                ),
                response_model=SummarySynthesis,
                call_label="summary",
                domain=domain,
            )
            playbook_summary = summary_result.playbook_summary
            top_3_actions = summary_result.top_3_actions[:3]
            llm_calls += 1
            llm_cost_usd += 0.005
        except Exception as exc:
            logger.error(
                "[SalesPlays] Summary synthesis failed",
                domain=domain,
                error=str(exc),
            )

        output = SalesPlaysOutput(
            domain=domain,
            meddpicc=meddpicc_fields,
            spin_questions=spin_questions,
            objection_handlers=objection_handlers,
            talk_tracks=talk_tracks,
            power_map=power_map,
            playbook_summary=playbook_summary,
            top_3_actions=top_3_actions,
        )

        logger.info(
            "[SalesPlays] synthesize completed",
            domain=domain,
            meddpicc_count=len(meddpicc_fields),
            spin_count=len(spin_questions),
            objection_count=len(objection_handlers),
            talk_track_count=len(talk_tracks),
            power_map_count=len(power_map),
            has_summary=bool(playbook_summary),
            actions_count=len(top_3_actions),
            llm_calls=llm_calls,
            llm_cost_usd=llm_cost_usd,
        )

        return output, llm_calls, llm_cost_usd

    def _call_llm(
        self,
        prompt: str,
        response_model: type[BaseModel],
        call_label: str,
        domain: str,
    ) -> Any:
        """Make a single LLM call via Instructor + Claude.

        Args:
            prompt: The prompt to send.
            response_model: The Pydantic model to validate the response against.
            call_label: Label for logging this call.
            domain: Domain for log context.

        Returns:
            Validated instance of response_model.

        Raises:
            Exception: If the LLM call fails after retries.
        """
        logger.debug(
            "[SalesPlays] LLM call started",
            call_label=call_label,
            domain=domain,
        )

        try:
            result = create_completion(
                response_model=response_model,
                max_retries=3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            logger.info(
                "[SalesPlays] LLM call completed",
                call_label=call_label,
                domain=domain,
            )
            return result

        except Exception as exc:
            logger.error(
                "[SalesPlays] LLM call failed",
                call_label=call_label,
                domain=domain,
                error=str(exc),
            )
            raise

    # ------------------------------------------------------------------
    # Context and prompt builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_base_context(
        domain: str,
        company_name: str,
        company_context: dict[str, Any],
        buying_committee: list[dict[str, Any]],
        exec_quotes: list[dict[str, str]],
        competitive_context: dict[str, Any],
        financial_context: dict[str, Any],
        business_case_context: dict[str, Any],
    ) -> str:
        """Build the shared context section included in all prompts.

        Args:
            domain: The prospect domain.
            company_name: The prospect company name.
            company_context: Company overview data.
            buying_committee: Buying committee members.
            exec_quotes: Executive quotes.
            competitive_context: Competitive landscape data.
            financial_context: Financial data.
            business_case_context: ROI and business case data.

        Returns:
            Formatted context string.
        """
        sections: list[str] = []

        # Company overview
        sections.append(
            f"# Prospect: {company_name} ({domain})\n"
            f"Vertical: {company_context.get('vertical', 'Unknown')}\n"
            f"Description: {company_context.get('description', 'N/A')}\n"
            f"Employee Count: {company_context.get('employee_count', 'Unknown')}"
        )

        # Financial context
        fin = financial_context
        if fin.get("revenue"):
            rev_str = f"${fin['revenue']:,.0f}"
            growth_str = (
                f"{fin['revenue_growth_pct']:.1f}%"
                if fin.get("revenue_growth_pct") is not None
                else "N/A"
            )
            digital_str = (
                f"{fin['digital_revenue_pct']:.1f}%"
                if fin.get("digital_revenue_pct") is not None
                else "N/A"
            )
            sections.append(
                f"## Financial Context\n"
                f"Revenue: {rev_str}\n"
                f"Revenue Growth: {growth_str}\n"
                f"Digital Revenue %: {digital_str}"
            )

        # Competitive context
        comp = competitive_context
        if comp.get("current_vendor") or comp.get("competitive_summary"):
            lines = ["## Competitive Context"]
            if comp.get("current_vendor"):
                lines.append(f"Current Search Vendor: {comp['current_vendor']}")
            if comp.get("golden_angle_competitors"):
                lines.append(
                    f"Competitors Using Algolia: {', '.join(comp['golden_angle_competitors'])}"
                )
            if comp.get("tech_gaps"):
                lines.append(f"Tech Gaps: {'; '.join(comp['tech_gaps'])}")
            if comp.get("competitive_summary"):
                lines.append(f"Summary: {comp['competitive_summary']}")
            sections.append("\n".join(lines))

        # Executive quotes
        if exec_quotes:
            quote_lines = ["## Executive Quotes"]
            for eq in exec_quotes[:10]:
                quote_lines.append(f'- "{eq["quote"]}" -- {eq["speaker"]} ({eq["source"]})')
            sections.append("\n".join(quote_lines))

        # Buying committee
        if buying_committee:
            comm_lines = ["## Buying Committee"]
            for m in buying_committee:
                url = f" | {m['linkedin_url']}" if m.get("linkedin_url") else ""
                comm_lines.append(f"- {m['name']} | {m['title']} | Tier: {m['tier']}{url}")
            sections.append("\n".join(comm_lines))

        # Business case
        bc = business_case_context
        if bc.get("total_roi_usd") or bc.get("roi_summary"):
            bc_lines = ["## Business Case"]
            if bc.get("total_roi_usd"):
                bc_lines.append(f"Estimated ROI: ${bc['total_roi_usd']:,.0f}")
            if bc.get("roi_summary"):
                bc_lines.append(f"Summary: {bc['roi_summary']}")
            if bc.get("value_drivers"):
                bc_lines.append("Value Drivers:")
                for vd in bc["value_drivers"]:
                    bc_lines.append(f"  - {vd}")
            sections.append("\n".join(bc_lines))

        return "\n\n".join(sections)

    @staticmethod
    def _build_meddpicc_prompt(base_context: str) -> str:
        """Build the MEDDPICC mapping prompt.

        Args:
            base_context: Shared context string.

        Returns:
            Formatted prompt string.
        """
        return (
            f"{base_context}\n\n"
            "## Task: MEDDPICC Mapping\n\n"
            "You are an elite enterprise sales strategist. Using the prospect data above, "
            "populate the MEDDPICC framework with evidence-based mappings.\n\n"
            "For each MEDDPICC field, provide:\n"
            "- field_name: one of metrics, economic_buyer, decision_criteria, decision_process, "
            "paper_process, identified_pain, champion, competition\n"
            "- person: name of the specific person if applicable (from buying committee)\n"
            "- evidence: the specific data point from the prospect audit that backs this\n"
            "- recommended_approach: how the AE should work this field in the deal\n"
            "- confidence: high/medium/low based on data quality\n\n"
            "Populate at least 5 of the 8 fields. Use real data from the context above -- "
            "do NOT make up company names, quotes, or statistics. "
            "If data is missing for a field, skip it rather than fabricating."
        )

    @staticmethod
    def _build_spin_prompt(base_context: str) -> str:
        """Build the SPIN questions prompt.

        Args:
            base_context: Shared context string.

        Returns:
            Formatted prompt string.
        """
        return (
            f"{base_context}\n\n"
            "## Task: SPIN Questions\n\n"
            "You are an elite enterprise sales strategist specializing in discovery calls. "
            "Using the prospect data above, generate SPIN questions that are grounded in "
            "specific audit findings.\n\n"
            "Generate at least 8 questions total, with at least 2 in each category:\n"
            "- situation: questions that confirm what we already know about their setup\n"
            "- problem: questions that surface pain points related to search & discovery\n"
            "- implication: questions that make them feel the cost of inaction\n"
            "- need_payoff: questions that get them to articulate the value of solving this\n\n"
            "For each question:\n"
            "- context: why this question matters, referencing the specific data point\n"
            "- expected_response: what we think they'll say based on the data\n\n"
            "Every question must reference specific data from the context above. "
            "Do NOT ask generic questions. Each must be tailored to this prospect."
        )

    @staticmethod
    def _build_objection_prompt(base_context: str) -> str:
        """Build the objection handling prompt.

        Args:
            base_context: Shared context string.

        Returns:
            Formatted prompt string.
        """
        return (
            f"{base_context}\n\n"
            "## Task: Objection Handling\n\n"
            "You are an elite enterprise sales strategist. Based on the prospect's "
            "current tech stack, hiring signals, competitive landscape, and financial "
            "situation, anticipate the most likely objections and prepare data-backed "
            "counter arguments.\n\n"
            "Generate at least 3 objection handlers. Common objections to consider:\n"
            "- 'We're building in-house' (check hiring signals for search/engineering roles)\n"
            "- 'We're happy with our current vendor' (if a search vendor is detected)\n"
            "- 'Budget constraints' (reference ROI data if available)\n"
            "- 'Not a priority right now' (reference competitive pressure)\n"
            "- 'Too complex to switch' (reference implementation support)\n\n"
            "For each objection:\n"
            "- objection: the exact words the prospect might say\n"
            "- likelihood: high/medium/low\n"
            "- counter: data-backed counter argument referencing specific audit findings\n"
            "- evidence_to_cite: specific data points to reference in the conversation\n\n"
            "Only include objections that are supported by the data. "
            "Do NOT include generic objections without evidence-based counters."
        )

    @staticmethod
    def _build_talk_track_prompt(base_context: str) -> str:
        """Build the talk tracks prompt.

        Args:
            base_context: Shared context string.

        Returns:
            Formatted prompt string.
        """
        return (
            f"{base_context}\n\n"
            "## Task: Talk Tracks\n\n"
            "You are an elite enterprise sales strategist writing talk tracks for an "
            "Algolia AE preparing for a first call with this prospect.\n\n"
            "Generate at least 3 talk tracks:\n"
            "- At least 1 'opener': how to start the conversation referencing something "
            "specific about the prospect (an exec quote, a recent initiative, a data point)\n"
            "- At least 1 'bridge': how to transition from their situation to Algolia's value\n"
            "- At least 1 'close': how to move to next steps with urgency\n\n"
            "For each talk track:\n"
            "- line_type: opener/bridge/close\n"
            "- text: the actual words the AE should say\n"
            "- mirrors_exec_language: true if it deliberately uses words from exec quotes\n"
            "- source_quote: the specific exec quote being mirrored, if applicable\n\n"
            "Where possible, mirror the prospect's own executive language. "
            "Sales that echo the prospect's own words are dramatically more effective."
        )

    @staticmethod
    def _build_power_map_prompt(base_context: str) -> str:
        """Build the power map prompt.

        Args:
            base_context: Shared context string.

        Returns:
            Formatted prompt string.
        """
        return (
            f"{base_context}\n\n"
            "## Task: Power Map\n\n"
            "You are an elite enterprise sales strategist mapping the buying committee "
            "for an Algolia deal with this prospect.\n\n"
            "Using the buying committee members listed above, assign each person:\n"
            "- meddpicc_role: economic_buyer, technical_evaluator, champion, influencer, "
            "blocker, or unknown\n"
            "- attitude: champion, supportive, neutral, skeptical, blocker, or unknown\n"
            "- recommended_approach: specific strategy for engaging this person\n\n"
            "Use their title and tier to infer their role. "
            "VP/SVP/C-level in engineering or product = likely economic_buyer or influencer. "
            "Directors of search or discovery = likely champion or technical_evaluator. "
            "Procurement = paper_process stakeholder.\n\n"
            "Include the linkedin_url if provided in the data above."
        )

    @staticmethod
    def _build_summary_prompt(
        base_context: str,
        meddpicc_count: int,
        spin_count: int,
        objection_count: int,
        power_map_count: int,
    ) -> str:
        """Build the summary and top actions prompt.

        Args:
            base_context: Shared context string.
            meddpicc_count: Number of MEDDPICC fields populated.
            spin_count: Number of SPIN questions generated.
            objection_count: Number of objection handlers generated.
            power_map_count: Number of power map members mapped.

        Returns:
            Formatted prompt string.
        """
        return (
            f"{base_context}\n\n"
            f"## Playbook Stats\n"
            f"MEDDPICC fields populated: {meddpicc_count}\n"
            f"SPIN questions generated: {spin_count}\n"
            f"Objection handlers prepared: {objection_count}\n"
            f"Power map members: {power_map_count}\n\n"
            "## Task: Playbook Summary + Top 3 Actions\n\n"
            "You are an elite enterprise sales strategist writing the executive summary "
            "of this prospect's sales playbook.\n\n"
            "1. Write a 2-4 sentence playbook_summary that captures:\n"
            "   - The strongest selling angle for this deal\n"
            "   - What makes this deal winnable (or what risks exist)\n"
            "   - The recommended entry point\n\n"
            "2. List exactly 3 top_3_actions -- concrete next steps for the AE:\n"
            "   - Each must be specific (name a person, reference a data point)\n"
            "   - Each must be actionable within the next 2 weeks\n"
            "   - Ordered by priority (most important first)\n\n"
            "Do NOT be generic. Reference specific people, quotes, or data from the context."
        )
