"""Campaign ABX enricher -- Instructor + Claude for personalized campaign generation.

Takes collected upstream module outputs and generates a complete ABX campaign package
using multiple Claude calls:
1. 5-email outreach sequence
2. LinkedIn messages for buying committee
3. Loom video script
4. Collateral schedule
5. Competitor-specific messaging
6. Campaign summary
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from prism_platform.core.llm import create_completion
from prism_platform.modules.campaign_abx.schemas import (
    CampaignOutput,
    CollateralSchedule,
    CompetitorMessaging,
    Email,
    LinkedInMessage,
    LoomScript,
)

logger = structlog.get_logger(__name__)


# -----------------------------------------------------------------------
# Intermediate Pydantic models for Instructor extraction
# -----------------------------------------------------------------------
class EmailSequenceOutput(BaseModel):
    """LLM output for the 5-email sequence."""

    model_config = ConfigDict(extra="forbid")
    emails: list[Email] = Field(description="Exactly 5 emails in sequence order.")


class LinkedInMessagesOutput(BaseModel):
    """LLM output for LinkedIn messages."""

    model_config = ConfigDict(extra="forbid")
    messages: list[LinkedInMessage] = Field(
        description="LinkedIn messages for buying committee members. At least 2."
    )


class LoomScriptOutput(BaseModel):
    """LLM output for the Loom script."""

    model_config = ConfigDict(extra="forbid")
    script: LoomScript


class ScheduleOutput(BaseModel):
    """LLM output for the collateral schedule."""

    model_config = ConfigDict(extra="forbid")
    schedule: list[CollateralSchedule] = Field(
        description="Week-by-week schedule for at least 3 weeks."
    )


class CompetitorMessagingOutput(BaseModel):
    """LLM output for competitor-specific messaging."""

    model_config = ConfigDict(extra="forbid")
    messaging: CompetitorMessaging


class CampaignSummaryOutput(BaseModel):
    """LLM output for overall campaign summary."""

    model_config = ConfigDict(extra="forbid")
    campaign_summary: str = Field(
        description="2-4 sentence executive summary of the campaign strategy."
    )
    target_contacts: list[str] = Field(
        default_factory=list,
        description="Names of people from the buying committee to target.",
    )


class CampaignEnricher:
    """Generates ABX campaign content using Instructor + Claude."""

    def __init__(self) -> None:
        pass

    async def generate_campaign(
        self,
        domain: str,
        company_name: str,
        buying_committee: list[dict[str, str]],
        executive_quotes: list[dict[str, str]],
        competitor_context: dict[str, Any],
        business_case_data: dict[str, Any],
        sales_plays_data: dict[str, Any],
        raw_data: dict[str, Any],
    ) -> tuple[CampaignOutput, int, float]:
        """Generate the full ABX campaign from upstream intelligence.

        Makes 6 sequential Claude calls to produce each campaign component.

        Args:
            domain: Prospect domain.
            company_name: Prospect company name.
            buying_committee: Extracted buying committee members.
            executive_quotes: Extracted exec quotes.
            competitor_context: Extracted competitor/vendor context.
            business_case_data: Extracted ROI, Said vs Found, proofs.
            sales_plays_data: Extracted MEDDPICC, objections, talking points.
            raw_data: Full upstream module output dict for additional context.

        Returns:
            Tuple of (CampaignOutput, llm_calls count, llm_cost_usd).
        """
        logger.info(
            "[CampaignABX] generate_campaign started",
            domain=domain,
            company_name=company_name,
            committee_size=len(buying_committee),
            quotes_count=len(executive_quotes),
        )

        llm_calls = 0
        llm_cost_usd = 0.0

        # Build shared context block used in all prompts
        context_block = self._build_context_block(
            domain=domain,
            company_name=company_name,
            buying_committee=buying_committee,
            executive_quotes=executive_quotes,
            competitor_context=competitor_context,
            business_case_data=business_case_data,
            sales_plays_data=sales_plays_data,
        )

        # 1. Generate 5-email sequence
        emails: list[Email] = []
        try:
            email_result = self._call_claude(
                prompt=self._build_email_prompt(context_block, domain, company_name),
                response_model=EmailSequenceOutput,
            )
            emails = email_result.emails
            llm_calls += 1
            llm_cost_usd += 0.005
            logger.info(
                "[CampaignABX] email sequence generated",
                domain=domain,
                email_count=len(emails),
            )
        except Exception as exc:
            logger.error(
                "[CampaignABX] email sequence generation failed",
                domain=domain,
                error=str(exc),
            )

        # 2. Generate LinkedIn messages
        linkedin_messages: list[LinkedInMessage] = []
        try:
            linkedin_result = self._call_claude(
                prompt=self._build_linkedin_prompt(
                    context_block, domain, company_name, buying_committee
                ),
                response_model=LinkedInMessagesOutput,
            )
            linkedin_messages = linkedin_result.messages
            llm_calls += 1
            llm_cost_usd += 0.005
            logger.info(
                "[CampaignABX] LinkedIn messages generated",
                domain=domain,
                message_count=len(linkedin_messages),
            )
        except Exception as exc:
            logger.error(
                "[CampaignABX] LinkedIn message generation failed",
                domain=domain,
                error=str(exc),
            )

        # 3. Generate Loom script
        loom_script: LoomScript | None = None
        try:
            loom_result = self._call_claude(
                prompt=self._build_loom_prompt(context_block, domain, company_name),
                response_model=LoomScriptOutput,
            )
            loom_script = loom_result.script
            llm_calls += 1
            llm_cost_usd += 0.005
            logger.info("[CampaignABX] Loom script generated", domain=domain)
        except Exception as exc:
            logger.error(
                "[CampaignABX] Loom script generation failed",
                domain=domain,
                error=str(exc),
            )

        # 4. Generate collateral schedule
        schedule: list[CollateralSchedule] = []
        try:
            schedule_result = self._call_claude(
                prompt=self._build_schedule_prompt(
                    context_block, domain, company_name, buying_committee
                ),
                response_model=ScheduleOutput,
            )
            schedule = schedule_result.schedule
            llm_calls += 1
            llm_cost_usd += 0.005
            logger.info(
                "[CampaignABX] collateral schedule generated",
                domain=domain,
                weeks=len(schedule),
            )
        except Exception as exc:
            logger.error(
                "[CampaignABX] collateral schedule generation failed",
                domain=domain,
                error=str(exc),
            )

        # 5. Generate competitor-specific messaging
        competitor_messaging: CompetitorMessaging | None = None
        try:
            comp_result = self._call_claude(
                prompt=self._build_competitor_messaging_prompt(
                    context_block, domain, company_name, competitor_context
                ),
                response_model=CompetitorMessagingOutput,
            )
            competitor_messaging = comp_result.messaging
            llm_calls += 1
            llm_cost_usd += 0.005
            logger.info(
                "[CampaignABX] competitor messaging generated",
                domain=domain,
                vendor=competitor_messaging.current_vendor,
            )
        except Exception as exc:
            logger.error(
                "[CampaignABX] competitor messaging generation failed",
                domain=domain,
                error=str(exc),
            )

        # 6. Generate campaign summary
        campaign_summary = ""
        target_contacts: list[str] = []
        try:
            summary_result = self._call_claude(
                prompt=self._build_summary_prompt(
                    context_block, domain, company_name, buying_committee
                ),
                response_model=CampaignSummaryOutput,
            )
            campaign_summary = summary_result.campaign_summary
            target_contacts = summary_result.target_contacts
            llm_calls += 1
            llm_cost_usd += 0.005
            logger.info(
                "[CampaignABX] campaign summary generated",
                domain=domain,
                contacts_count=len(target_contacts),
            )
        except Exception as exc:
            logger.error(
                "[CampaignABX] campaign summary generation failed",
                domain=domain,
                error=str(exc),
            )

        output = CampaignOutput(
            domain=domain,
            emails=emails,
            linkedin_messages=linkedin_messages,
            loom_script=loom_script,
            schedule=schedule,
            competitor_messaging=competitor_messaging,
            campaign_summary=campaign_summary,
            target_contacts=target_contacts,
        )

        logger.info(
            "[CampaignABX] generate_campaign completed",
            domain=domain,
            llm_calls=llm_calls,
            llm_cost_usd=round(llm_cost_usd, 4),
            emails=len(emails),
            linkedin=len(linkedin_messages),
            has_loom=loom_script is not None,
            schedule_weeks=len(schedule),
            has_competitor_msg=competitor_messaging is not None,
        )

        return output, llm_calls, round(llm_cost_usd, 4)

    def _call_claude(
        self,
        prompt: str,
        response_model: type[BaseModel],
    ) -> Any:
        """Call Claude via Instructor with structured output.

        Args:
            prompt: The user prompt.
            response_model: Pydantic model to constrain the output.

        Returns:
            Validated instance of response_model.

        Raises:
            Exception: On LLM call failure after retries.
        """
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
            return result
        except Exception as exc:
            logger.error(
                "[CampaignABX] Claude call failed",
                response_model=response_model.__name__,
                error=str(exc),
            )
            raise

    # ------------------------------------------------------------------
    # Context block builder
    # ------------------------------------------------------------------
    def _build_context_block(
        self,
        domain: str,
        company_name: str,
        buying_committee: list[dict[str, str]],
        executive_quotes: list[dict[str, str]],
        competitor_context: dict[str, Any],
        business_case_data: dict[str, Any],
        sales_plays_data: dict[str, Any],
    ) -> str:
        """Build the shared audit context block used across all prompts.

        Args:
            domain: Prospect domain.
            company_name: Prospect company name.
            buying_committee: Buying committee members.
            executive_quotes: Executive quotes.
            competitor_context: Competitor/vendor context.
            business_case_data: ROI and business case data.
            sales_plays_data: MEDDPICC and sales plays data.

        Returns:
            Formatted context string.
        """
        sections: list[str] = []

        sections.append(
            f"# Prospect: {company_name} ({domain})\n"
            f"Current search vendor: {competitor_context.get('current_vendor', 'Unknown')}\n"
            f"Competitive position: {competitor_context.get('competitive_position', 'Unknown')}\n"
        )

        # Buying committee
        if buying_committee:
            committee_lines = ["## Buying Committee"]
            for member in buying_committee:
                committee_lines.append(
                    f"- {member.get('name', 'N/A')} | {member.get('title', 'N/A')} "
                    f"| Role: {member.get('relevance', 'N/A')}"
                )
            sections.append("\n".join(committee_lines))

        # Executive quotes
        if executive_quotes:
            quote_lines = ["## Executive Quotes (use in personalization)"]
            for eq in executive_quotes[:8]:
                quote_lines.append(
                    f'- "{eq.get("quote", "")}" -- {eq.get("speaker", "")} ({eq.get("source", "")})'
                )
            sections.append("\n".join(quote_lines))

        # ROI data
        roi_lines = ["## Business Case / ROI"]
        conservative = business_case_data.get("total_conservative_impact")
        moderate = business_case_data.get("total_moderate_impact")
        if conservative is not None:
            roi_lines.append(f"- Conservative annual impact: ${conservative:,.0f}")
        if moderate is not None:
            roi_lines.append(f"- Moderate annual impact: ${moderate:,.0f}")
        pitch = business_case_data.get("one_line_pitch", "")
        if pitch:
            roi_lines.append(f"- One-line pitch: {pitch}")

        # Customer proofs
        proofs = business_case_data.get("customer_proofs", [])
        if proofs:
            roi_lines.append("### Customer Proofs")
            for proof in proofs[:5]:
                if isinstance(proof, dict):
                    roi_lines.append(
                        f"- {proof.get('customer_name', 'N/A')}: "
                        f"{proof.get('key_metric', 'N/A')} ({proof.get('industry', 'N/A')})"
                    )
        sections.append("\n".join(roi_lines))

        # Said vs Found
        svf_rows = business_case_data.get("said_vs_found", [])
        if svf_rows:
            svf_lines = ["## Said vs Found"]
            for row in svf_rows[:5]:
                if isinstance(row, dict):
                    svf_lines.append(
                        f"- EXEC SAID: {row.get('exec_said', 'N/A')}\n"
                        f"  WE FOUND: {row.get('we_found', 'N/A')}\n"
                        f"  COMPETITORS: {row.get('competitors_doing', 'N/A')}\n"
                        f"  YOUR MOVE: {row.get('your_move', 'N/A')}"
                    )
            sections.append("\n".join(svf_lines))

        # Competitive angles
        angles = competitor_context.get("top_angles", [])
        if angles:
            angle_lines = ["## Competitive Angles"]
            for angle in angles:
                angle_lines.append(f"- {angle}")
            sections.append("\n".join(angle_lines))

        # Golden angle
        golden = competitor_context.get("golden_angle_competitors", [])
        if golden:
            sections.append(f"## Golden Angle\nCompetitors using Algolia: {', '.join(golden)}")

        # MEDDPICC
        meddpicc = sales_plays_data.get("meddpicc", {})
        if meddpicc and isinstance(meddpicc, dict):
            meddpicc_lines = ["## MEDDPICC"]
            for key, value in meddpicc.items():
                if value:
                    meddpicc_lines.append(f"- {key}: {value}")
            if len(meddpicc_lines) > 1:
                sections.append("\n".join(meddpicc_lines))

        # Objection handlers
        objections = sales_plays_data.get("objection_handlers", [])
        if objections:
            obj_lines = ["## Objection Handlers"]
            for obj in objections[:5]:
                if isinstance(obj, dict):
                    obj_lines.append(
                        f"- Objection: {obj.get('objection', 'N/A')}\n"
                        f"  Response: {obj.get('response', 'N/A')}"
                    )
                elif isinstance(obj, str):
                    obj_lines.append(f"- {obj}")
            sections.append("\n".join(obj_lines))

        return "\n\n".join(sections)

    # ------------------------------------------------------------------
    # Prompt builders for each campaign component
    # ------------------------------------------------------------------
    def _build_email_prompt(self, context_block: str, domain: str, company_name: str) -> str:
        """Build prompt for the 5-email outreach sequence.

        Args:
            context_block: Shared audit context.
            domain: Prospect domain.
            company_name: Prospect company name.

        Returns:
            Formatted prompt string.
        """
        return f"""You are writing a personalized 5-email outreach sequence for Algolia to {company_name} ({domain}).

{context_block}

---

Generate EXACTLY 5 emails with these purposes in order:
1. **Email 1 (hook)**: Grab attention by referencing a specific exec quote from the audit data.
   Open with something like "Your [CTO/CFO] mentioned [quote] -- we found [finding]."
2. **Email 2 (insight)**: Share a competitive insight. Reference what competitors are doing
   with search technology. If a Golden Angle competitor uses Algolia, mention it.
3. **Email 3 (proof)**: Cite a specific Algolia customer case study that matches the prospect's
   industry. Include the exact metric (e.g. "37% conversion lift").
4. **Email 4 (roi)**: Share the ROI calculation from the business case. Reference the
   conservative/moderate impact numbers. Show the math.
5. **Email 5 (ask)**: Direct meeting request. Summarize the 3 most compelling data points and
   ask for 15 minutes.

RULES:
- Every email MUST reference specific data from the audit context above -- NO generic templates
- Subject lines must be concise (<80 chars) and personalized
- Include personalization_tokens listing which data points you used
- Include recommended_send_day (spread across Tue/Wed/Thu)
- Include target_role for each email
- Body should be 150-300 words, professional but conversational
- sequence_number must be 1, 2, 3, 4, 5 in order"""

    def _build_linkedin_prompt(
        self,
        context_block: str,
        domain: str,
        company_name: str,
        buying_committee: list[dict[str, str]],
    ) -> str:
        """Build prompt for LinkedIn messages.

        Args:
            context_block: Shared audit context.
            domain: Prospect domain.
            company_name: Prospect company name.
            buying_committee: Buying committee members.

        Returns:
            Formatted prompt string.
        """
        committee_json = json.dumps(buying_committee[:6], indent=2)

        return f"""You are writing personalized LinkedIn outreach messages for Algolia targeting {company_name} ({domain}).

{context_block}

## Target People:
{committee_json}

---

Generate LinkedIn messages for the buying committee. For each person, create:
- A **connection_request** (max 300 chars -- LinkedIn limit). Mention something specific about
  their role or a company initiative.
- A **follow_up_1** message (sent 3 days after connection accepted). Share an insight relevant
  to their role from the audit data.

For the most senior person (economic_buyer or technical_evaluator), also create:
- A **follow_up_2** message with ROI data
- An **inmail** as an alternative if connection request is not accepted

RULES:
- Use real names and titles from the buying committee
- Reference specific audit findings relevant to each person's role
- Keep connection requests under 300 characters
- Keep follow-ups under 500 characters
- Include personalization_context explaining what data you used
- Generate at least 2 messages total, ideally 4-8"""

    def _build_loom_prompt(self, context_block: str, domain: str, company_name: str) -> str:
        """Build prompt for the Loom video script.

        Args:
            context_block: Shared audit context.
            domain: Prospect domain.
            company_name: Prospect company name.

        Returns:
            Formatted prompt string.
        """
        return f"""You are writing a 2-minute personalized Loom video script for Algolia targeting {company_name} ({domain}).

{context_block}

---

Create a script for a screen-recorded video that walks through the 3 most compelling findings
from the audit. Structure:

1. **Opening** (10 seconds): Greet by name, mention why you're reaching out.
   "Hi [name], I'm [name] from Algolia. I just completed a search audit on {domain} and
   found some things I think you'd want to see."

2. **Screen 1** (~30 seconds): Show the most compelling finding. Describe what to display
   on screen (website screenshot, data chart, etc.) and what to SAY while showing it.

3. **Screen 2** (~30 seconds): Show the competitive angle. What competitors are doing.
   Describe screen content and narration.

4. **Screen 3** (~30 seconds): Show the ROI opportunity. Reference specific numbers.
   Describe screen content and narration.

5. **Closing** (10 seconds): Tie back to business impact. Be specific with the dollar amount.

6. **CTA**: Clear next step. "Book a 15-minute demo" or "Reply to this email."

RULES:
- Reference REAL audit data -- no generic statements
- Each screen section describes both what to SHOW and what to SAY
- Total duration target: 2 minutes
- Tone: professional, helpful, not salesy"""

    def _build_schedule_prompt(
        self,
        context_block: str,
        domain: str,
        company_name: str,
        buying_committee: list[dict[str, str]],
    ) -> str:
        """Build prompt for the collateral schedule.

        Args:
            context_block: Shared audit context.
            domain: Prospect domain.
            company_name: Prospect company name.
            buying_committee: Buying committee members.

        Returns:
            Formatted prompt string.
        """
        contact_names = [m.get("name", "Unknown") for m in buying_committee[:6]]

        return f"""You are creating a week-by-week campaign execution plan for Algolia targeting {company_name} ({domain}).

{context_block}

## Available Contacts: {", ".join(contact_names) if contact_names else "TBD"}

---

Create a 5-week collateral schedule. Each week should specify:
- **actions**: What to send/do (email, LinkedIn, Loom, case study, etc.)
- **target_contacts**: Which people to engage
- **notes**: Timing tips, what to watch for

Week-by-week strategy:
- Week 1: Initial outreach (Email 1 + LinkedIn connection requests)
- Week 2: Value delivery (Email 2 + Loom video + LinkedIn follow-ups)
- Week 3: Proof points (Email 3 + case study share + Email 4 ROI)
- Week 4: Ask for meeting (Email 5 + LinkedIn InMail to economic buyer)
- Week 5: Follow-up / escalation (re-engage, try different contact)

RULES:
- At least 3 weeks (preferably 5)
- Actions should be specific, not generic
- Reference specific content to send
- Assign contacts by role relevance"""

    def _build_competitor_messaging_prompt(
        self,
        context_block: str,
        domain: str,
        company_name: str,
        competitor_context: dict[str, Any],
    ) -> str:
        """Build prompt for competitor-specific messaging.

        Args:
            context_block: Shared audit context.
            domain: Prospect domain.
            company_name: Prospect company name.
            competitor_context: Competitor/vendor context.

        Returns:
            Formatted prompt string.
        """
        current_vendor = competitor_context.get("current_vendor", "None/Custom")

        return f"""You are creating competitor-specific messaging for Algolia targeting {company_name} ({domain}).

{context_block}

## Current Search Vendor: {current_vendor}

---

Create messaging tailored to the current vendor situation:

- If vendor is "Elasticsearch" or "Elastic": Focus on operational complexity, maintenance burden,
  relevance tuning difficulty. Messaging angle = "displacement".
- If vendor is "Coveo": Focus on cost, implementation complexity, and Algolia's developer
  experience. Messaging angle = "displacement".
- If vendor is "Bloomreach" or "SearchSpring": Focus on AI capabilities, speed, and scalability.
  Messaging angle = "performance".
- If vendor is "None/Custom" or custom-built: Focus on build-vs-buy, time to market, total
  cost of ownership. Messaging angle = "greenfield".
- Otherwise: Focus on Algolia's unique strengths vs the specific vendor.

Provide:
1. **current_vendor**: The detected vendor name
2. **messaging_angle**: "displacement", "performance", or "greenfield"
3. **key_points**: 4-6 specific messaging points
4. **differentiators**: 3-5 Algolia differentiators relevant to this situation

RULES:
- Reference specific audit data where possible
- Key points should be concrete, not generic"""

    def _build_summary_prompt(
        self,
        context_block: str,
        domain: str,
        company_name: str,
        buying_committee: list[dict[str, str]],
    ) -> str:
        """Build prompt for campaign summary.

        Args:
            context_block: Shared audit context.
            domain: Prospect domain.
            company_name: Prospect company name.
            buying_committee: Buying committee members.

        Returns:
            Formatted prompt string.
        """
        return f"""You are summarizing an ABX campaign strategy for Algolia targeting {company_name} ({domain}).

{context_block}

---

Provide:
1. **campaign_summary**: A 2-4 sentence executive summary of the campaign strategy.
   Mention the key themes (e.g. "displacement of Elasticsearch", "ROI of $X",
   "leveraging [CTO]'s stated priority on digital transformation").

2. **target_contacts**: List the names of the top 3-5 people from the buying committee
   who should be targeted in this campaign, in priority order.

RULES:
- Be specific -- reference real data points
- Keep the summary concise but impactful
- Contact names must match actual names from the buying committee data"""
