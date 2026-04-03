"""Campaign ABX schemas -- input/output contracts for multi-touch ABX campaign generation.

Produces:
- 5-email outreach sequence referencing real audit data
- LinkedIn messages personalized per buying committee member
- Loom video script with 3 top findings
- Week-by-week collateral schedule
- Competitor-specific displacement messaging
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CampaignInput(BaseModel):
    """Input for the campaign ABX module -- just the domain to generate campaigns for."""

    model_config = ConfigDict(extra="forbid")
    domain: str


class Email(BaseModel):
    """One email in the 5-email outreach sequence.

    Each email serves a distinct purpose and MUST reference specific audit data
    (exec quotes, competitive insights, case studies, ROI numbers).
    """

    model_config = ConfigDict(extra="forbid")

    sequence_number: int = Field(description="Position in the sequence, 1 through 5.")
    subject_line: str = Field(
        description="Email subject line. Must be concise (<80 chars) and personalized."
    )
    body: str = Field(
        description="Full email body text. Must reference real audit data -- no generic templates."
    )
    purpose: Literal["hook", "insight", "proof", "roi", "ask"] = Field(
        description=(
            "The strategic purpose of this email: "
            "'hook' = grab attention with an exec quote, "
            "'insight' = share competitive intelligence, "
            "'proof' = cite a case study, "
            "'roi' = share ROI numbers, "
            "'ask' = request a meeting."
        )
    )
    personalization_tokens: list[str] = Field(
        default_factory=list,
        description="Specific data points from audit used to personalize this email.",
    )
    recommended_send_day: str = Field(
        default="",
        description="Recommended day of the week to send, e.g. 'Tuesday'.",
    )
    target_role: str = Field(
        default="",
        description="Target recipient role, e.g. 'CTO', 'VP Engineering'.",
    )


class LinkedInMessage(BaseModel):
    """A personalized LinkedIn message for a specific buying committee member."""

    model_config = ConfigDict(extra="forbid")

    message_type: Literal["connection_request", "follow_up_1", "follow_up_2", "inmail"] = Field(
        description="Type of LinkedIn outreach message."
    )
    target_name: str = Field(description="Full name of the target person from buying committee.")
    target_title: str = Field(description="Current job title of the target person.")
    message: str = Field(description="Full message text, personalized using audit intelligence.")
    personalization_context: str = Field(
        default="",
        description="Brief note on what audit data was used to personalize this message.",
    )


class LoomScript(BaseModel):
    """Script for a 2-minute personalized Loom video walkthrough."""

    model_config = ConfigDict(extra="forbid")

    duration_target: str = Field(
        default="2 minutes",
        description="Target video duration.",
    )
    opening: str = Field(
        description="Opening hook (first 10 seconds). Must mention the prospect by name."
    )
    screen_1: str = Field(
        description="Screen 1: What to show on screen + what to say. Most compelling finding."
    )
    screen_2: str = Field(
        description="Screen 2: What to show on screen + what to say. Second finding."
    )
    screen_3: str = Field(
        description="Screen 3: What to show on screen + what to say. Third finding."
    )
    closing: str = Field(
        description="Closing statement (last 10 seconds). Tie back to business impact."
    )
    call_to_action: str = Field(description="Clear CTA, e.g. 'Book a 15-minute demo at [link]'.")


class CollateralSchedule(BaseModel):
    """Week-by-week campaign execution plan."""

    model_config = ConfigDict(extra="forbid")

    week: int = Field(description="Week number in the campaign, 1 through 5.")
    actions: list[str] = Field(
        default_factory=list,
        description="List of actions to execute this week.",
    )
    target_contacts: list[str] = Field(
        default_factory=list,
        description="Names of people to engage this week.",
    )
    notes: str = Field(
        default="",
        description="Additional context or timing notes for this week.",
    )


class CompetitorMessaging(BaseModel):
    """Competitor-specific displacement or differentiation messaging."""

    model_config = ConfigDict(extra="forbid")

    current_vendor: str = Field(
        description=(
            "Name of the current search vendor, e.g. 'Elasticsearch', 'Coveo', 'None/Custom'."
        )
    )
    messaging_angle: str = Field(
        description="Primary messaging angle: 'displacement', 'performance', or 'greenfield'."
    )
    key_points: list[str] = Field(
        default_factory=list,
        description="Key messaging points tailored to the current vendor situation.",
    )
    differentiators: list[str] = Field(
        default_factory=list,
        description="Algolia differentiators relevant to displacing the current vendor.",
    )


class CampaignOutput(BaseModel):
    """Full ABX campaign output synthesized from upstream intelligence and synthesis modules."""

    model_config = ConfigDict(extra="forbid")

    domain: str

    # Part 1 -- Email sequence
    emails: list[Email] = Field(default_factory=list)

    # Part 2 -- LinkedIn messages
    linkedin_messages: list[LinkedInMessage] = Field(default_factory=list)

    # Part 3 -- Loom script
    loom_script: LoomScript | None = None

    # Part 4 -- Collateral schedule
    schedule: list[CollateralSchedule] = Field(default_factory=list)

    # Part 5 -- Competitor-specific messaging
    competitor_messaging: CompetitorMessaging | None = None

    # Summary
    campaign_summary: str = Field(
        default="",
        description="Executive summary of the campaign strategy and key themes.",
    )
    target_contacts: list[str] = Field(
        default_factory=list,
        description="Names of people from the buying committee to target.",
    )
