"""Synth Sales Plays schemas — output contract for AE/BDR playbook synthesis.

Ported from the v1 module (output model only; v1 *Input dropped — v2 reads upstream via
`composes` + `{upstream_*}` injection).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MEDDPICCField(BaseModel):
    """A single MEDDPICC framework field with evidence and recommended approach."""

    model_config = ConfigDict(extra="forbid")

    field_name: Literal[
        "metrics",
        "economic_buyer",
        "decision_criteria",
        "decision_process",
        "paper_process",
        "identified_pain",
        "champion",
        "competition",
    ]
    person: str | None = None
    evidence: str
    recommended_approach: str
    confidence: Literal["high", "medium", "low"] = "medium"


class SPINQuestion(BaseModel):
    """A SPIN selling question with context and expected response."""

    model_config = ConfigDict(extra="forbid")

    category: Literal["situation", "problem", "implication", "need_payoff"]
    question: str
    context: str
    expected_response: str = ""


class ObjectionHandler(BaseModel):
    """Anticipated objection with a data-backed counter argument."""

    model_config = ConfigDict(extra="forbid")

    objection: str
    likelihood: Literal["high", "medium", "low"] = "medium"
    counter: str
    evidence_to_cite: list[str] = Field(default_factory=list)


class TalkTrack(BaseModel):
    """A sales talk track element — opener, bridge, or close."""

    model_config = ConfigDict(extra="forbid")

    line_type: Literal["opener", "bridge", "close"]
    text: str
    mirrors_exec_language: bool = False
    source_quote: str | None = None


class PowerMapMember(BaseModel):
    """A member of the prospect's power map / buying committee."""

    model_config = ConfigDict(extra="forbid")

    name: str
    title: str
    meddpicc_role: Literal[
        "economic_buyer",
        "technical_evaluator",
        "champion",
        "influencer",
        "blocker",
        "unknown",
    ] = "unknown"
    attitude: Literal[
        "champion",
        "supportive",
        "neutral",
        "skeptical",
        "blocker",
        "unknown",
    ] = "unknown"
    recommended_approach: str = ""
    linkedin_url: str | None = None


class BlufHeader(BaseModel):
    """30-second AE read at the top of the playbook."""

    model_config = ConfigDict(extra="forbid")

    signal_tier: Literal["hot", "warm", "cold"] = "warm"
    campaign_type: str = ""
    top_angle: str = Field(description="The single challenger insight to lead with.")
    key_exec_name: str = ""
    key_exec_title: str = ""
    key_exec_contact_route: str = Field(default="", description="warm intro / LinkedIn / cold")
    partner_play: str = Field(default="", description="SI warm intro, or 'no confirmed partner'.")
    urgency_signal: str = Field(default="", description="Most urgent trigger + date.")


class TalkingPoint(BaseModel):
    """One of the 5 talking points — each grounded in a verbatim exec quote."""

    model_config = ConfigDict(extra="forbid")

    hook: str = Field(description="Opener using the prospect's own language.")
    audit_finding: str = Field(description="What the browser/intel audit found (cite module).")
    their_words: str = Field(description="Verbatim exec quote + speaker + title + source + date.")
    competitor_proof: str = Field(default="", description="What a competitor does (Golden Angle).")
    open_with: str = Field(description="The exact line the AE says.")
    expected_reaction: str = Field(default="", description="Anticipated prospect response.")


class PartnerAngles(BaseModel):
    """Partner motion in priority order — SI partner first if confirmed."""

    model_config = ConfigDict(extra="forbid")

    si_partner: str = Field(default="", description="HIGH-confidence SI (Crossbeam); #1 if any.")
    si_activation: str = Field(default="", description="How to activate the SI relationship.")
    tech_partner: str = Field(default="", description="Tech partner co-sell angle.")
    competitor_angle: str = Field(default="", description="Golden-Angle competitor-based play.")
    fallback_approach: str = Field(default="", description="Cold outbound (last resort).")


class SalesPlaysOutput(BaseModel):
    """Full sales playbook output synthesized from upstream intelligence modules."""

    model_config = ConfigDict(extra="forbid")

    domain: str

    # Part 0 — BLUF header (AE's 30-second read)
    bluf: BlufHeader | None = None

    # Part 1 — MEDDPICC
    meddpicc: list[MEDDPICCField] = Field(default_factory=list)

    # Part 2 — SPIN questions
    spin_questions: list[SPINQuestion] = Field(default_factory=list)

    # Part 3 — Objection handling
    objection_handlers: list[ObjectionHandler] = Field(default_factory=list)

    # Part 4 — Talk tracks (legacy opener/bridge/close lines)
    talk_tracks: list[TalkTrack] = Field(default_factory=list)
    # Part 4b — Structured talking points (skill: 5, each grounded in an exec quote)
    talking_points: list[TalkingPoint] = Field(default_factory=list)

    # Part 5 — Power map
    power_map: list[PowerMapMember] = Field(default_factory=list)

    # Part 6 — Partner angles (SI-partner-first per the skill)
    partner_angles: PartnerAngles | None = None

    # Summary
    playbook_summary: str = ""
    top_3_actions: list[str] = Field(default_factory=list)
