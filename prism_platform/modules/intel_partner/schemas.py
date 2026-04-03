"""Intel Partner schemas -- input/output contracts for partner intelligence.

These schemas define the Pydantic models for the intel-partner module,
which collects partner overlaps, co-sell opportunities, SI relationships,
vertical case studies, competitor partners, and recommended partner plays.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class PartnerInput(BaseModel):
    """Input for the intel-partner module."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Website domain to analyze, e.g. 'dell.com'")


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class PartnerOverlap(BaseModel):
    """A single partner overlap from Crossbeam or Perplexity research."""

    model_config = ConfigDict(extra="forbid")

    partner_name: str = Field(description="Name of the partner organization")
    partner_type: Literal["si", "technology", "agency", "consulting", "other"] = Field(
        default="other",
        description=(
            "Category of partner: system integrator, technology, agency, consulting, or other"
        ),
    )
    shared_account_count: int | None = Field(
        default=None,
        description="Number of accounts shared between Algolia and this partner. None if unknown.",
    )
    prospect_overlap: bool = Field(
        default=False,
        description="True if this partner has a direct overlap with the prospect being analyzed",
    )
    relationship_strength: Literal["strong", "moderate", "weak", "unknown"] = Field(
        default="unknown",
        description="Strength of the existing relationship between Algolia and this partner",
    )
    notes: str = Field(
        default="",
        description="Additional context about the overlap, e.g. 'Partner manages prospect CMS'",
    )


class CoSellOpportunity(BaseModel):
    """A co-sell opportunity identified from partner and tech stack data."""

    model_config = ConfigDict(extra="forbid")

    partner_name: str = Field(description="Name of the partner for co-sell")
    partner_type: Literal["si", "technology", "agency", "consulting", "other"] = Field(
        default="other",
        description="Category of the partner",
    )
    technology_confirmed: bool = Field(
        default=False,
        description=(
            "True if the prospect's use of this partner's technology is confirmed via BuiltWith"
        ),
    )
    algolia_integration: bool = Field(
        default=False,
        description="True if Algolia has a known integration with this partner's platform",
    )
    pitch: str = Field(
        default="",
        description=(
            "Pitch narrative connecting partner, prospect, and Algolia. "
            "e.g. 'Prospect uses SFCC (confirmed) -> Algolia has "
            "SFCC connector -> Partner X implements both'"
        ),
    )
    confidence: Literal["high", "medium", "low"] = Field(
        default="low",
        description="Confidence in this co-sell opportunity",
    )


class SIRelationship(BaseModel):
    """A system integrator relationship with the prospect."""

    model_config = ConfigDict(extra="forbid")

    si_name: str = Field(description="Name of the system integrator")
    relationship_type: Literal["implementation", "consulting", "managed_services", "unknown"] = (
        Field(
            default="unknown",
            description="Type of SI engagement with the prospect",
        )
    )
    confirmed_source: Literal["crossbeam", "perplexity", "both"] = Field(
        default="perplexity",
        description="Which source confirmed the SI relationship",
    )
    warm_intro_path: str | None = Field(
        default=None,
        description=(
            "Path to a warm introduction via shared customers. "
            "e.g. 'Slalom serves both Dell and Shoe Carnival (Algolia customer)'"
        ),
    )
    algolia_customer_connection: str | None = Field(
        default=None,
        description="Name of an existing Algolia customer that also uses this SI",
    )


class VerticalCaseStudy(BaseModel):
    """An Algolia case study relevant to the prospect's vertical."""

    model_config = ConfigDict(extra="forbid")

    customer_name: str = Field(description="Name of the Algolia customer in the case study")
    domain: str | None = Field(
        default=None,
        description="Domain of the customer, e.g. 'gymshark.com'",
    )
    industry: str = Field(
        default="",
        description="Industry vertical, e.g. 'Retail', 'Media', 'B2B SaaS'",
    )
    use_case: str = Field(
        default="",
        description="Primary use case, e.g. 'site search', 'product discovery', 'recommendations'",
    )
    key_metric: str | None = Field(
        default=None,
        description="Key outcome metric, e.g. '37% conversion lift'",
    )
    url: str | None = Field(
        default=None,
        description="URL to the published case study",
    )


class PartnerPlay(BaseModel):
    """Recommended partner play -- the top partner approach for the sales team."""

    model_config = ConfigDict(extra="forbid")

    recommended_partner: str = Field(description="Name of the recommended partner to engage first")
    partner_type: Literal["si", "technology", "agency", "consulting", "other"] = Field(
        default="other",
        description="Category of the recommended partner",
    )
    approach_reason: str = Field(
        description="Why this partner should be engaged first. Concise strategic reasoning.",
    )
    pitch_message: str = Field(
        description=(
            "What to say to the partner. A ready-to-use outreach message or talking points."
        ),
    )
    confidence: Literal["high", "medium", "low"] = Field(
        default="low",
        description="Confidence in this recommendation",
    )


class CompetitorPartner(BaseModel):
    """A competitor's known partner relationships."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Competitor company name")
    domain: str = Field(description="Competitor domain")
    known_partners: list[str] = Field(
        default_factory=list,
        description="List of known partner names for this competitor",
    )
    overlap_with_prospect_partners: list[str] = Field(
        default_factory=list,
        description="Partners that overlap between the competitor and the prospect",
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class PartnerOutput(BaseModel):
    """Full partner intelligence output for a prospect domain.

    Contains partner overlaps, co-sell opportunities, SI relationships,
    vertical case studies, recent partnerships, competitor partners,
    recommended partner play, and overall summary.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Domain that was analyzed")

    # Part 1 -- Crossbeam overlaps
    partner_overlaps: list[PartnerOverlap] = Field(
        default_factory=list,
        description="Partner overlaps from Crossbeam or research",
    )

    # Part 2 -- Co-sell opportunities
    co_sell_opportunities: list[CoSellOpportunity] = Field(
        default_factory=list,
        description="Identified co-sell opportunities via partner ecosystem",
    )

    # Part 3 -- SI relationships
    si_relationships: list[SIRelationship] = Field(
        default_factory=list,
        description="System integrator relationships with the prospect",
    )

    # Part 4 -- Vertical case studies
    vertical_case_studies: list[VerticalCaseStudy] = Field(
        default_factory=list,
        description="Algolia case studies relevant to the prospect's vertical",
    )

    # Part 5 -- Partnership news
    recent_partnerships: list[str] = Field(
        default_factory=list,
        description="Recent partnership announcements or news involving the prospect",
    )

    # Part 6 -- Competitor partners
    competitor_partners: list[CompetitorPartner] = Field(
        default_factory=list,
        description="Partner ecosystems of the prospect's competitors",
    )

    # Part 7 -- Recommended play
    partner_play: PartnerPlay | None = Field(
        default=None,
        description="Top recommended partner play for the sales team",
    )

    # Summary
    partner_summary: str = Field(
        default="",
        description=(
            "Overall partner intelligence summary. 2-4 sentences highlighting "
            "the most actionable partner insights for an Algolia sales team."
        ),
    )
    crossbeam_available: bool = Field(
        default=False,
        description="True if Crossbeam data was used in this analysis",
    )
