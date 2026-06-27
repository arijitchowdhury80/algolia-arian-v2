"""Synth Business Case schemas — output contract for ROI business-case synthesis.

Ported from the v1 module (output model only; the v1 *Input model is dropped — v2 reads
upstream data via `composes` + `{upstream_*}` playbook injection, not an input arg).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SaidVsFoundRow(BaseModel):
    """One row of the 4-column Said vs Found matrix."""

    model_config = ConfigDict(extra="forbid")

    exec_said: str = Field(
        description="Verbatim quote with speaker name and source, e.g. "
        "'CFO Jane Smith (Q4 earnings call): We are investing heavily in digital.'"
    )
    we_found: str = Field(
        description="What audit data shows with evidence, e.g. "
        "'Site search returns 0 results for 15% of queries (intel-traffic data).'"
    )
    competitors_doing: str = Field(
        description="What competitors are doing about the same topic, e.g. "
        "'HP uses Algolia with 37% conversion lift; Lenovo deployed AI search Q3 2024.'"
    )
    your_move: str = Field(
        description="How Algolia solves this AND puts prospect ahead of competitors, e.g. "
        "'Algolia NeuralSearch would eliminate zero-result queries and match HP performance.'"
    )
    category: Literal[
        "search_quality",
        "digital_investment",
        "competitive_gap",
        "customer_experience",
        "technology_modernization",
        "hiring_signal",
        "financial_opportunity",
    ] = Field(description="Category tag for this row. Must be one of the predefined values.")
    evidence_tier: str = Field(
        default="VERIFIED",
        description="Evidence quality: VERIFIED, WEBFETCH, WEBSEARCH, ESTIMATE, NO_SOURCE.",
    )


class ValueLever(BaseModel):
    """One component of the ROI model."""

    model_config = ConfigDict(extra="forbid")

    lever_name: str = Field(description="Name of the value lever, e.g. 'Search Conversion Uplift'.")
    description: str = Field(
        description="Explanation of how this lever creates value for the prospect."
    )
    conservative_estimate: float | None = Field(
        default=None,
        description="Annual USD impact, conservative assumptions. Float, not formatted string.",
    )
    moderate_estimate: float | None = Field(
        default=None,
        description="Annual USD impact using moderate assumptions. Float, not formatted string.",
    )
    case_study_proof: str = Field(
        default="",
        description="Case study evidence, e.g. 'Shoe Carnival saw 3.5x conversion lift'.",
    )
    calculation_method: str = Field(
        default="",
        description="Show all math used to derive the estimates.",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="List of assumptions underlying this lever's estimates.",
    )


class DisplacementCost(BaseModel):
    """Cost model for displacing the current search vendor."""

    model_config = ConfigDict(extra="forbid")

    current_vendor: str = Field(description="Name of the current search vendor being displaced.")
    cost_of_staying_annual: float | None = Field(
        default=None,
        description="Annual cost of maintaining the current vendor in USD.",
    )
    cost_of_switching: float | None = Field(
        default=None,
        description="One-time cost of switching to Algolia in USD.",
    )
    net_benefit_3yr: float | None = Field(
        default=None,
        description="Net benefit over 3 years of switching to Algolia in USD.",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions underlying the displacement cost model.",
    )


class CustomerProof(BaseModel):
    """A customer case study matched to a value lever."""

    model_config = ConfigDict(extra="forbid")

    customer_name: str = Field(description="Name of the Algolia customer.")
    industry: str = Field(description="Industry vertical of the customer.")
    use_case: str = Field(default="", description="Brief description of the use case.")
    key_metric: str = Field(description="Primary metric achieved, e.g. '37% conversion lift'.")
    matched_lever: str = Field(
        default="",
        description="Which value lever this case study proves.",
    )
    url: str | None = Field(
        default=None,
        description="URL to the public case study if available.",
    )


class TimingSignal(BaseModel):
    """A timing signal that creates urgency for the deal."""

    model_config = ConfigDict(extra="forbid")

    signal: str = Field(description="Description of the timing signal.")
    source_module: str = Field(
        description="Which PRISM module this signal came from, e.g. 'intel-news'."
    )
    urgency: Literal["high", "medium", "low"] = Field(description="Urgency level of this signal.")
    reason: str = Field(description="Why this signal creates urgency for Algolia.")


class BusinessCaseOutput(BaseModel):
    """Full business case output synthesized from upstream intelligence modules."""

    model_config = ConfigDict(extra="forbid")

    domain: str

    # Part 1 — Said vs Found (4-column matrix)
    said_vs_found: list[SaidVsFoundRow] = Field(default_factory=list)

    # Part 2 — ROI Calculator
    value_levers: list[ValueLever] = Field(default_factory=list)
    total_conservative_impact: float | None = Field(
        default=None,
        description="Sum of all conservative_estimate values across value levers in USD.",
    )
    total_moderate_impact: float | None = Field(
        default=None,
        description="Sum of all moderate_estimate values across value levers in USD.",
    )
    sensitivity_analysis: str = Field(
        default="",
        description="Narrative describing how estimates change under different assumptions.",
    )

    # Part 3 — Displacement cost
    displacement: DisplacementCost | None = None

    # Part 4 — Customer proofs
    customer_proofs: list[CustomerProof] = Field(default_factory=list)

    # Part 5 — Timing signals
    timing_signals: list[TimingSignal] = Field(default_factory=list)
    urgency_summary: str = Field(
        default="",
        description="1-2 sentence summary of why the prospect should act now.",
    )

    # Summary
    executive_summary: str = Field(
        default="",
        description="2-4 paragraph executive summary tying all parts together.",
    )
    one_line_pitch: str = Field(
        default="",
        description="Single sentence pitch, e.g. 'Dell can unlock $X annual revenue by...'.",
    )
