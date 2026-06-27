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


class SalesPlaysOutput(BaseModel):
    """Full sales playbook output synthesized from upstream intelligence modules."""

    model_config = ConfigDict(extra="forbid")

    domain: str

    # Part 1 — MEDDPICC
    meddpicc: list[MEDDPICCField] = Field(default_factory=list)

    # Part 2 — SPIN questions
    spin_questions: list[SPINQuestion] = Field(default_factory=list)

    # Part 3 — Objection handling
    objection_handlers: list[ObjectionHandler] = Field(default_factory=list)

    # Part 4 — Talk tracks
    talk_tracks: list[TalkTrack] = Field(default_factory=list)

    # Part 5 — Power map
    power_map: list[PowerMapMember] = Field(default_factory=list)

    # Summary
    playbook_summary: str = ""
    top_3_actions: list[str] = Field(default_factory=list)
