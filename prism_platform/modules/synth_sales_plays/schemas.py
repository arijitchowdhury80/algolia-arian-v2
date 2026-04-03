"""Synth Sales Plays schemas -- input/output contracts for sales playbook generation.

This module defines the Pydantic models for the synth-sales-plays module,
which synthesizes upstream intelligence into actionable sales playbooks
including MEDDPICC mapping, SPIN questions, objection handling, talk tracks,
and power maps.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SalesPlaysInput(BaseModel):
    """Input for the sales plays module -- just the domain to analyze."""

    model_config = ConfigDict(extra="forbid")
    domain: str


class MEDDPICCField(BaseModel):
    """A single MEDDPICC framework field with evidence and recommended approach.

    Attributes:
        field_name: Which MEDDPICC field this maps to.
        person: Specific person if applicable (e.g., the economic buyer name).
        evidence: The data backing this field mapping.
        recommended_approach: How the AE should approach this field in the deal.
        confidence: How confident we are in this mapping.
    """

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
    """A SPIN selling question with context and expected response.

    Attributes:
        category: SPIN category -- Situation, Problem, Implication, or Need-payoff.
        question: The actual question to ask.
        context: Why this question matters and what data drives it.
        expected_response: What we think the prospect will say.
    """

    model_config = ConfigDict(extra="forbid")

    category: Literal["situation", "problem", "implication", "need_payoff"]
    question: str
    context: str
    expected_response: str = ""


class ObjectionHandler(BaseModel):
    """Anticipated objection with a data-backed counter argument.

    Attributes:
        objection: The objection we expect (e.g., "We're building in-house").
        likelihood: How likely this objection is to come up.
        counter: Data-backed counter argument.
        evidence_to_cite: Specific evidence points to support the counter.
    """

    model_config = ConfigDict(extra="forbid")

    objection: str
    likelihood: Literal["high", "medium", "low"] = "medium"
    counter: str
    evidence_to_cite: list[str] = Field(default_factory=list)


class TalkTrack(BaseModel):
    """A sales talk track element -- opener, bridge, or close.

    Attributes:
        line_type: Whether this is an opener, bridge, or close.
        text: The actual talk track text.
        mirrors_exec_language: True if it uses the prospect's own vocabulary.
        source_quote: The executive quote being mirrored, if applicable.
    """

    model_config = ConfigDict(extra="forbid")

    line_type: Literal["opener", "bridge", "close"]
    text: str
    mirrors_exec_language: bool = False
    source_quote: str | None = None


class PowerMapMember(BaseModel):
    """A member of the prospect's power map / buying committee.

    Attributes:
        name: Full name of the person.
        title: Job title.
        meddpicc_role: Their role in the MEDDPICC framework.
        attitude: Predicted attitude toward Algolia.
        recommended_approach: How to engage this person.
        linkedin_url: LinkedIn profile URL if available.
    """

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


class SalesPlaysOutput(BaseModel):
    """Full sales playbook output synthesized from upstream intelligence modules.

    Combines MEDDPICC mapping, SPIN questions, objection handling, talk tracks,
    and power map into a comprehensive sales playbook.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str

    # Part 1 -- MEDDPICC
    meddpicc: list[MEDDPICCField] = Field(default_factory=list)

    # Part 2 -- SPIN questions
    spin_questions: list[SPINQuestion] = Field(default_factory=list)

    # Part 3 -- Objection handling
    objection_handlers: list[ObjectionHandler] = Field(default_factory=list)

    # Part 4 -- Talk tracks
    talk_tracks: list[TalkTrack] = Field(default_factory=list)

    # Part 5 -- Power map
    power_map: list[PowerMapMember] = Field(default_factory=list)

    # Summary
    playbook_summary: str = ""
    top_3_actions: list[str] = Field(default_factory=list)
