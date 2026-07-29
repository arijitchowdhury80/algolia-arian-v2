"""Intel Partner v2 schemas — partner ecosystem output.

The deterministic Track-1 collector cross-references the prospect's detected
tech stack against ALGOLIA_PARTNER_TABLE and returns a structured list of
matched technology partners.  The Track-2 LLM adds the parts that need
open-web reasoning: SI/agency relationships and the actionable motions
narrative.

Execution strategy: prospect-only (one LLM call; all partner facts already
resolved deterministically by Track-1).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Broad category of the matched platform.
IntegrationType = Literal["commerce_platform", "analytics", "crm"]

# How confident we are in the SI relationship claim.
SIConfidence = Literal["confirmed", "likely", "possible"]


class TechPartner(BaseModel):
    """One Algolia technology partner detected in the prospect's stack."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    partner_name: str = Field(description="Canonical Algolia partner name, e.g. 'Shopify'")
    integration_type: IntegrationType = Field(
        description="Broad category: commerce_platform, analytics, or crm"
    )
    integration_doc_url: str = Field(
        description="URL to the Algolia integration or partner page for this platform"
    )
    detected_via: str = Field(
        description=(
            "Which intel-techstack field surfaced this platform, "
            "e.g. 'ecommerce_platform' or 'analytics_stack'"
        )
    )
    raw_detected_value: str = Field(
        description="The raw platform string from intel-techstack that matched this partner"
    )


class SIRelationship(BaseModel):
    """A system integrator or agency relationship with the prospect."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    firm_name: str = Field(description="SI or agency name, e.g. 'Accenture'")
    relationship_type: str = Field(
        description="Nature of relationship, e.g. 'implementation partner', 'AOR'"
    )
    evidence: str = Field(
        description="One-sentence evidence for this relationship (source or inference)"
    )
    confidence: SIConfidence = Field(
        description="confirmed=multiple sources, likely=single strong source, possible=inferred"
    )
    algolia_relevance: str = Field(
        description=(
            "One sentence on how this SI relationship is relevant to an Algolia sales motion"
        )
    )


class PartnerV2Output(BaseModel):
    """Partner ecosystem output for a prospect."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Prospect domain analyzed")

    tech_partners: list[TechPartner] = Field(
        default_factory=list,
        description=(
            "Algolia technology partners detected in the prospect's stack. "
            "Populated verbatim from the Track-1 static table lookup — "
            "do NOT modify or add partners not in that list."
        ),
    )
    si_relationships: list[SIRelationship] = Field(
        default_factory=list,
        description=(
            "SI/agency firms with known relationships with the prospect. "
            "Sourced from Track-2 LLM research."
        ),
    )
    partner_narrative: str = Field(
        description=(
            "A 3-5 sentence narrative for a sales rep: which Algolia tech partners the "
            "prospect already uses, any SI leverage points, and the single sharpest "
            "co-sell or partner-led angle."
        )
    )
    actionable_motions: list[str] = Field(
        default_factory=list,
        description=(
            "2-4 concrete sales actions enabled by the partner landscape, "
            "e.g. 'Engage Accenture SFCC practice to co-sell Algolia connector'."
        ),
    )
    has_algolia_partner_overlap: bool = Field(
        default=False,
        description=(
            "True if at least one Algolia technology partner was detected in the stack "
            "(i.e. tech_partners is non-empty). Set by the Track-1 collector."
        ),
    )
