"""Audit Factcheck schemas -- input/output contracts for the GAN-inspired quality gate.

Defines the claim verification pipeline: claims are extracted from upstream module
outputs, verified per-category via Claude, and a gate verdict is produced.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class FactcheckInput(BaseModel):
    """Input for the factcheck module -- just the domain to verify."""

    model_config = ConfigDict(extra="forbid")
    domain: str


class ClaimStatus(StrEnum):
    """Verification status for a single factual claim."""

    VERIFIED = "VERIFIED"
    PLAUSIBLE = "PLAUSIBLE"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"


class VerificationCategory(StrEnum):
    """Category for grouping claims by source module type."""

    COMPANY_FACTS = "company_facts"
    FINANCIAL_CLAIMS = "financial_claims"
    TECHNOLOGY_CLAIMS = "technology_claims"
    TRAFFIC_CLAIMS = "traffic_claims"
    COMPETITIVE_CLAIMS = "competitive_claims"
    SYNTHESIS_CLAIMS = "synthesis_claims"
    HIRING_CLAIMS = "hiring_claims"
    QUOTE_CLAIMS = "quote_claims"


class Claim(BaseModel):
    """A single factual claim extracted from an upstream module output."""

    model_config = ConfigDict(extra="forbid")

    claim_text: str = Field(description="The factual assertion to verify.")
    source_module: str = Field(description="Module that produced this claim, e.g. 'intel-company'.")
    category: VerificationCategory = Field(
        description="Which verification category this belongs to.",
    )
    evidence_text: str | None = Field(
        default=None,
        description="Supporting evidence text from the source module, if available.",
    )
    evidence_source_url: str | None = Field(
        default=None,
        description="URL of the evidence source, if available.",
    )


class VerifiedClaim(BaseModel):
    """A claim after verification by the Claude evaluator."""

    model_config = ConfigDict(extra="forbid")

    claim: Claim = Field(description="The original claim that was verified.")
    status: ClaimStatus = Field(description="Verification result.")
    verification_notes: str = Field(
        description="Explanation of how the claim was verified or why it failed.",
    )
    corrected_value: str | None = Field(
        default=None,
        description="If CONTRADICTED, the corrected value. None otherwise.",
    )


class CategoryResult(BaseModel):
    """Verification results for a single claim category."""

    model_config = ConfigDict(extra="forbid")

    category: VerificationCategory = Field(description="The claim category.")
    claims_count: int = Field(description="Total claims in this category.")
    verified: int = Field(default=0, description="Count of VERIFIED claims.")
    plausible: int = Field(default=0, description="Count of PLAUSIBLE claims.")
    unverified: int = Field(default=0, description="Count of UNVERIFIED claims.")
    contradicted: int = Field(default=0, description="Count of CONTRADICTED claims.")
    claims: list[VerifiedClaim] = Field(
        default_factory=list,
        description="All verified claims in this category.",
    )


class Correction(BaseModel):
    """A correction for a contradicted claim, to be applied downstream."""

    model_config = ConfigDict(extra="forbid")

    claim_text: str = Field(description="The original claim text.")
    source_module: str = Field(description="Module that produced the contradicted claim.")
    incorrect_value: str = Field(description="The incorrect value from the original claim.")
    corrected_value: str = Field(description="The corrected value.")
    correction_reason: str = Field(description="Why the original value was wrong.")


class GateVerdict(StrEnum):
    """Gate verdict for the factcheck quality gate."""

    PROCEED = "PROCEED"
    WARN = "WARN"
    BLOCKED = "BLOCKED"


class FactcheckOutput(BaseModel):
    """Full output of the factcheck quality gate module."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Domain that was fact-checked.")
    verdict: GateVerdict = Field(description="Overall gate verdict.")
    category_results: list[CategoryResult] = Field(
        default_factory=list,
        description="Verification results per category.",
    )
    total_claims: int = Field(default=0, description="Total claims evaluated.")
    verified_count: int = Field(default=0, description="Total VERIFIED claims.")
    plausible_count: int = Field(default=0, description="Total PLAUSIBLE claims.")
    unverified_count: int = Field(default=0, description="Total UNVERIFIED claims.")
    contradicted_count: int = Field(default=0, description="Total CONTRADICTED claims.")
    contradicted_pct: float = Field(
        default=0.0,
        description="Percentage of claims that are CONTRADICTED (0.0-100.0).",
    )
    unverified_pct: float = Field(
        default=0.0,
        description="Percentage of claims that are UNVERIFIED (0.0-100.0).",
    )
    corrections: list[Correction] = Field(
        default_factory=list,
        description="Correction manifest for contradicted claims. NEVER modifies upstream data.",
    )
    summary: str = Field(
        default="",
        description="Human-readable summary of the factcheck results.",
    )
