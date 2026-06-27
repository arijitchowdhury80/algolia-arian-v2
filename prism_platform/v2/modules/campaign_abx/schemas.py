"""Campaign ABX schemas — output contract for multi-touch ABX campaign synthesis.

Ported from the v1 module (output model only; v1 *Input dropped — v2 reads upstream via
`composes` + `{upstream_*}` injection).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Email(BaseModel):
    """One email in the 5-email outreach sequence."""

    model_config = ConfigDict(extra="forbid")

    sequence_number: int = Field(description="Position in the sequence, 1 through 5.")
    subject_line: str = Field(
        description="Email subject line. Must be concise (<80 chars) and personalized."
    )
    body: str = Field(
        description="Full email body. Must reference real audit data — no generic templates."
    )
    purpose: Literal["hook", "insight", "proof", "roi", "ask"] = Field(
        description=(
            "Strategic purpose: hook=exec quote, insight=competitive intel, proof=case study, "
            "roi=ROI numbers, ask=request a meeting."
        )
    )
    personalization_tokens: list[str] = Field(
        default_factory=list,
        description="Specific data points from the audit used to personalize this email.",
    )
    recommended_send_day: str = Field(
        default="", description="Recommended day of the week to send, e.g. 'Tuesday'."
    )
    target_role: str = Field(default="", description="Target recipient role, e.g. 'CTO'.")


class LinkedInMessage(BaseModel):
    """A personalized LinkedIn message for a specific buying committee member."""

    model_config = ConfigDict(extra="forbid")

    message_type: Literal["connection_request", "follow_up_1", "follow_up_2", "inmail"] = Field(
        description="Type of LinkedIn outreach message."
    )
    target_name: str = Field(description="Full name of the target from the buying committee.")
    target_title: str = Field(description="Current job title of the target person.")
    message: str = Field(description="Full message text, personalized using audit intelligence.")
    personalization_context: str = Field(
        default="", description="What audit data was used to personalize this message."
    )


class LoomScript(BaseModel):
    """Script for a 2-minute personalized Loom video walkthrough."""

    model_config = ConfigDict(extra="forbid")

    duration_target: str = Field(default="2 minutes", description="Target video duration.")
    opening: str = Field(description="Opening hook (first 10s). Must mention the prospect by name.")
    screen_1: str = Field(description="Screen 1: what to show + say. Most compelling finding.")
    screen_2: str = Field(description="Screen 2: what to show + say. Second finding.")
    screen_3: str = Field(description="Screen 3: what to show + say. Third finding.")
    closing: str = Field(description="Closing (last 10s). Tie back to business impact.")
    call_to_action: str = Field(description="Clear CTA, e.g. 'Book a 15-minute demo at [link]'.")


class CollateralSchedule(BaseModel):
    """Week-by-week campaign execution plan."""

    model_config = ConfigDict(extra="forbid")

    week: int = Field(description="Week number in the campaign, 1 through 5.")
    actions: list[str] = Field(default_factory=list, description="Actions to execute this week.")
    target_contacts: list[str] = Field(
        default_factory=list, description="Names of people to engage this week."
    )
    notes: str = Field(default="", description="Additional context or timing notes.")


class CompetitorMessaging(BaseModel):
    """Competitor-specific displacement or differentiation messaging."""

    model_config = ConfigDict(extra="forbid")

    current_vendor: str = Field(
        description="Current search vendor, e.g. 'Elasticsearch', 'Coveo', 'None/Custom'."
    )
    messaging_angle: str = Field(
        description="Primary angle: 'displacement', 'performance', or 'greenfield'."
    )
    key_points: list[str] = Field(
        default_factory=list, description="Key messaging points for the vendor situation."
    )
    differentiators: list[str] = Field(
        default_factory=list, description="Algolia differentiators relevant to displacement."
    )


class CampaignOutput(BaseModel):
    """Full ABX campaign output synthesized from upstream intelligence + synthesis modules."""

    model_config = ConfigDict(extra="forbid")

    domain: str

    emails: list[Email] = Field(default_factory=list)
    linkedin_messages: list[LinkedInMessage] = Field(default_factory=list)
    loom_script: LoomScript | None = None
    schedule: list[CollateralSchedule] = Field(default_factory=list)
    competitor_messaging: CompetitorMessaging | None = None
    campaign_summary: str = Field(
        default="", description="Executive summary of the campaign strategy and key themes."
    )
    target_contacts: list[str] = Field(
        default_factory=list, description="Names of buying-committee people to target."
    )
