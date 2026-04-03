"""Audit Report schemas -- input/output contracts for the final audit report delivery.

This module synthesizes ALL upstream intelligence and synthesis module outputs
into the final deliverable package: 10-dimension scoring, competitor benchmarks,
pre-call brief, leave-behind, and full audit JSON.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AuditReportInput(BaseModel):
    """Input for the audit report module -- just the domain to report on."""

    model_config = ConfigDict(extra="forbid")
    domain: str


class DimensionScore(BaseModel):
    """Score for one of the 10 search quality dimensions."""

    model_config = ConfigDict(extra="forbid")

    dimension: Literal[
        "relevance",
        "speed",
        "typo_tolerance",
        "nlp",
        "autocomplete",
        "faceting",
        "zero_result_handling",
        "personalization",
        "merchandising",
        "analytics",
    ]
    score: float = Field(ge=0, le=10, description="Score from 0 (worst) to 10 (best).")
    evidence: str = Field(description="Evidence supporting this score.")
    severity: Literal["critical", "major", "minor", "ok"] = Field(
        description="Severity classification based on score."
    )
    is_estimated: bool = Field(
        default=True,
        description="True until browser audit confirms. Estimated from techstack + traffic data.",
    )


class CompetitorScore(BaseModel):
    """Search quality scores for one competitor."""

    model_config = ConfigDict(extra="forbid")

    company_name: str
    domain: str
    overall_score: float | None = None
    dimension_scores: list[DimensionScore] = Field(default_factory=list)


class PreCallBrief(BaseModel):
    """60-second read for the AE before the call.

    Contains the 6 most important data points distilled from the full audit.
    """

    model_config = ConfigDict(extra="forbid")

    company_name: str
    search_score: float = Field(ge=0, le=10, description="Overall search quality score.")
    top_angle: str = Field(description="The single best angle to lead the conversation with.")
    key_exec_to_reference: str = Field(
        description="Executive quote to reference, e.g. 'Michael Dell said...'."
    )
    partner_play: str | None = Field(
        default=None,
        description="Partner ecosystem play if applicable.",
    )
    most_urgent_signal: str = Field(description="The most time-sensitive signal creating urgency.")
    recommended_first_play: str = Field(description="Recommended opening play for the AE.")


class LeaveBehind(BaseModel):
    """3-page prospect-safe document.

    Contains ONLY information safe to share with the prospect.
    NO hiring signals, NO buying committee data, NO internal strategy data.
    """

    model_config = ConfigDict(extra="forbid")

    search_quality_summary: str = Field(
        description="Summary of search quality findings safe for the prospect."
    )
    competitive_benchmark: str = Field(
        description="Anonymized competitive benchmark (no competitor names)."
    )
    top_3_recommendations: list[str] = Field(
        default_factory=list,
        description="Top 3 actionable recommendations for the prospect.",
    )
    roi_summary: str = Field(description="ROI summary from the business case module.")
    next_steps: str = Field(
        default="",
        description="Recommended next steps for the prospect.",
    )


class AuditReportOutput(BaseModel):
    """Full audit report output synthesized from all upstream modules.

    This is the final deliverable package for the PRISM audit pipeline.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str
    company_name: str = ""

    # Part 1 -- 10-Dimension scoring
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    overall_score: float | None = None
    score_methodology: str = ""

    # Part 2 -- Comparative
    competitor_scores: list[CompetitorScore] = Field(default_factory=list)
    industry_average_score: float | None = None

    # Part 3 -- Full audit JSON (all data assembled)
    full_audit_data: dict[str, object] = Field(default_factory=dict)

    # Part 4 -- Pre-call brief
    pre_call_brief: PreCallBrief | None = None

    # Part 5 -- Leave-behind
    leave_behind: LeaveBehind | None = None

    # Summary
    audit_summary: str = ""


# All 10 dimensions that must be scored
ALL_DIMENSIONS: list[str] = [
    "relevance",
    "speed",
    "typo_tolerance",
    "nlp",
    "autocomplete",
    "faceting",
    "zero_result_handling",
    "personalization",
    "merchandising",
    "analytics",
]
