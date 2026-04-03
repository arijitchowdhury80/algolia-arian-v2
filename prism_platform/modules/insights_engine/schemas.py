"""Insights Engine schemas -- input/output contracts for vertical benchmarking.

These schemas define the Pydantic models for the insights-engine module,
a cross-audit vertical benchmarking module that runs in Wave 6.
All metrics are ANONYMIZED -- no company names or domains in metric values.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class InsightsInput(BaseModel):
    """Input for the insights-engine module."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Website domain to analyze, e.g. 'dell.com'")


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class VerticalMetric(BaseModel):
    """A single anonymized vertical benchmark metric."""

    model_config = ConfigDict(extra="forbid")

    metric_name: str = Field(
        description="Identifier for this metric, e.g. 'avg_search_quality_score'"
    )
    metric_value: dict[str, object] = Field(
        description=(
            "Metric payload as a dict. Structure varies by metric type. "
            "Must NOT contain company names or domains -- only aggregated values."
        ),
    )
    sample_size: int = Field(
        description="Number of audits that contributed to this metric. Must be >= 1.",
        ge=1,
    )
    description: str = Field(
        description="Human-readable explanation of what this metric represents."
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class InsightsOutput(BaseModel):
    """Full insights engine output -- cross-audit vertical benchmarks.

    Every field description doubles as an LLM instruction when this schema
    is used with Instructor for structured extraction.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="The domain for the current audit.")
    vertical: str = Field(
        description="The vertical classification of this domain, e.g. 'E-commerce Retail'."
    )
    metrics: list[VerticalMetric] = Field(
        default_factory=list,
        description=(
            "List of anonymized vertical benchmark metrics. "
            "Must contain at least 3 metrics for a valid result."
        ),
    )
    audit_ids_included: list[str] = Field(
        default_factory=list,
        description="UUIDs of audits that were included in this benchmark analysis.",
    )
    total_audits_in_vertical: int = Field(
        default=1,
        description="Total number of audits in this vertical, including the current one.",
        ge=1,
    )
    summary: str = Field(
        default="",
        description=(
            "Human-readable summary of vertical insights. "
            "Must not contain company names or domains."
        ),
    )
    is_first_in_vertical: bool = Field(
        default=False,
        description=(
            "True if this is the first audit in this vertical. "
            "When True, metrics are based on the current audit only."
        ),
    )
