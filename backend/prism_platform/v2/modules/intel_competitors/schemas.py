"""Intel Competitors v2 schemas — competitive search-landscape output.

The deterministic Track-1 collector detects each competitor's search vendor
(Scout source scan). The Track-2 LLM copies those facts through verbatim and
adds the parts that genuinely need reasoning: Algolia case-study matching and
the competitive narrative.

Execution strategy: comparative (one LLM call with all competitor profiles in
context — the model needs the full set to classify the overall scenario).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# How a competitor's search vendor was determined.
DetectionSource = Literal["scout_source_scan", "network_confirmed", "research", "undetected"]

# Confidence in the vendor being live in production.
SearchVendorStatus = Literal[
    "DETECTED",
    "ACTIVE_NETWORK_CONFIRMED",
    "UNDETECTED",
    "UNCONFIRMED_WAF_BLOCK",
    "FETCH_FAILED",
]

# Overall competitive picture — drives the sales motion.
CompetitiveScenario = Literal["golden", "defensive", "offensive", "mixed"]


class CompetitorSearchProfile(BaseModel):
    """One competitor's search-technology profile (mostly from the deterministic scan)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    company_name: str = Field(description="Competitor company name")
    domain: str = Field(description="Competitor primary domain")
    search_vendor: str | None = Field(
        default=None, description="Detected search vendor, or null if undetected"
    )
    search_vendor_status: SearchVendorStatus = Field(
        default="UNDETECTED", description="Confidence the vendor is live in production"
    )
    detection_source: DetectionSource = Field(
        default="scout_source_scan",
        description="How the vendor was determined. Copy from the Track-1 detection verbatim.",
    )
    is_algolia_customer: bool = Field(
        default=False, description="True if the competitor runs Algolia (golden angle)"
    )
    evidence: str = Field(
        default="",
        description="The matched signature(s) or URL backing this detection. No fabrication.",
    )


class AlgoliaCaseStudy(BaseModel):
    """An Algolia customer story relevant to the prospect's vertical."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(description="Case study title")
    url: str = Field(description="Link to the case study on algolia.com")
    vertical: str = Field(description="Vertical/industry of the case study")
    relevance_to_prospect: str = Field(
        description="One sentence: why this case study matters for the prospect"
    )


class CompetitorsV2Output(BaseModel):
    """Competitive search-landscape output for a prospect + its competitor set."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Prospect domain analyzed")

    competitor_profiles: list[CompetitorSearchProfile] = Field(
        default_factory=list,
        description=(
            "One profile per competitor. Search-vendor fields MUST be copied verbatim "
            "from the Track-1 detection provided in the prompt — do NOT re-research them."
        ),
    )
    golden_angle_competitors: list[str] = Field(
        default_factory=list,
        description="Domains of competitors confirmed running Algolia (the strongest pitch).",
    )
    algolia_case_studies: list[AlgoliaCaseStudy] = Field(
        default_factory=list,
        description="Algolia case studies matched to the prospect's vertical (2-4).",
    )
    competitive_scenario: CompetitiveScenario = Field(
        default="offensive",
        description=(
            "golden = a competitor runs Algolia; defensive = the prospect already runs "
            "Algolia (retention); offensive = neither runs Algolia (displacement); "
            "mixed = varies across the set."
        ),
    )
    competitive_landscape_narrative: str = Field(
        description=(
            "A 3-5 sentence narrative for a sales rep: who competes, how they compare on "
            "search, and the single sharpest angle. Lead with any golden-angle finding."
        )
    )
