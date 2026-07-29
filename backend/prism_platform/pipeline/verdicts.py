"""Pydantic verdict schemas for the 5-stage `gate()` pipeline (Task 3).

E2-compliant: every field the LLM must fill is explicit and schema-constrained
(forced tool-use JSON), never free-form prose parsed after the fact. See
docs/workspace/phase2-executioner/interface-contract.md for the binding shape
-- these classes are copied verbatim from that contract, do not invent a
different shape.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class FactCheckVerdict(BaseModel):
    """Stage 2 -- LLM judgment against the evidence-tier system already inside
    `algolia-audit-factcheck` (AUTHENTIC/WEBFETCH/WEBSEARCH/NO_SOURCE)."""

    claim: str
    evidence_tier: Literal["AUTHENTIC", "WEBFETCH", "WEBSEARCH", "NO_SOURCE"]
    verdict: Literal["SUPPORTED", "UNSUPPORTED", "CONTRADICTED"]
    citation: str | None
    reasoning: str


class AdversarialVoterVerdict(BaseModel):
    """One voter's ballot in the stage 3 adversarial panel (N=3)."""

    voter_id: int
    refuted: bool
    reasoning: str


class AdversarialVerdict(BaseModel):
    """Stage 3 -- aggregated panel verdict for one risky claim.

    `survives` is true iff a majority of `votes` are NOT refuted.
    """

    claim: str
    votes: list[AdversarialVoterVerdict]
    survives: bool


class QualityScore(BaseModel):
    """Stage 4 -- `algolia-audit-eval` Dimension 3 (instruction adherence),
    the one dimension not already delegated to factcheck_mechanical.py."""

    dimension: Literal["instruction_adherence"]
    score: float
    passing_checks: int
    total_checks: int
    reasoning: str


class LegalVerdict(BaseModel):
    """Stage 5 -- patch #8 stub. No rubric exists yet, so this stage NEVER
    renders an automated PASS/BLOCK judgment -- it only ever reports that a
    human (Arijit) must review. Do not add PASS/BLOCK values here until a
    real rubric is written and this contract is revised."""

    status: Literal["needs_human_review"]
    note: str
