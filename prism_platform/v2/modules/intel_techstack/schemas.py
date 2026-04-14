"""Intel TechStack v2 schemas — output contract for the tech stack detection agent.

Primary goal: identify the search vendor powering {domain}, assess quality,
and detect if any competitor uses Algolia (golden angle displacement signal).

Detection method hierarchy:
  1. BuiltWith structured data (highest confidence)
  2. Network request analysis / developer tools hints
  3. Job posting mentions
  4. Engineering blog / GitHub repos
  5. Agent API research (fallback, lowest confidence)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SearchVendorV2(BaseModel):
    """Detected search vendor for a single domain."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(
        description=(
            "Search vendor name. One of: Algolia, Elasticsearch, OpenSearch, "
            "Solr, Coveo, Bloomreach, Searchspring, Constructor.io, Typesense, "
            "Azure Cognitive Search, AWS CloudSearch, in-house/custom, unknown"
        )
    )
    status: Literal["ACTIVE", "TAG_ONLY", "REMOVED", "UNDETECTED"] = Field(
        description=(
            "ACTIVE = currently deployed; "
            "TAG_ONLY = tracking tag only, not full integration; "
            "REMOVED = was present, no longer detected; "
            "UNDETECTED = could not confirm"
        )
    )
    detection_method: str = Field(
        description=(
            "How this vendor was detected: 'builtwith', 'network_analysis', "
            "'job_posting', 'engineering_blog', 'research', 'github'"
        )
    )
    evidence_summary: str = Field(
        description=(
            "One to two sentence summary of the detection evidence. "
            "Be specific: 'BuiltWith reports Elasticsearch 8.x; job posting for "
            "Senior Elasticsearch Engineer posted 2025-11' is better than 'uses Elasticsearch'."
        )
    )
    evidence_url: str = Field(
        description="URL where the detection evidence was found (BuiltWith page, job posting, etc.)"
    )


class TechStackV2Output(BaseModel):
    """Full tech stack output for a single domain (prospect or competitor).

    One instance of this model is produced per domain in a per-company fan-out.
    The executor runs one Agent API call per domain; this schema is the
    validated output of each call.
    """

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="The domain this tech stack data applies to, e.g. 'dell.com'")

    # Primary intelligence target
    search_vendor: SearchVendorV2 | None = Field(
        default=None,
        description=(
            "The current search vendor, if detected. None if no search vendor found. "
            "Fill this field with evidence — do not guess."
        ),
    )

    # Secondary stack
    ecommerce_platform: str | None = Field(
        default=None,
        description=(
            "Ecommerce platform if applicable: "
            "Salesforce Commerce Cloud, Shopify Plus, Magento/Adobe Commerce, "
            "commercetools, SAP Hybris, custom, None if not an ecommerce site"
        ),
    )
    analytics: list[str] = Field(
        default_factory=list,
        description="Analytics tools detected: GA4, Adobe Analytics, Amplitude, Mixpanel, etc.",
    )
    all_detected_technologies: list[str] = Field(
        default_factory=list,
        description=(
            "All technologies detected for this domain. "
            "Use short names: 'Cloudflare', 'React', 'Next.js', 'Elasticsearch'"
        ),
    )

    # Algolia displacement signals
    is_algolia_customer: bool = Field(
        default=False,
        description=(
            "True if this domain is confirmed as an Algolia customer. "
            "Only set True if there is direct evidence (BuiltWith Algolia detection, "
            "algolia.net XHR calls, official Algolia case study)."
        ),
    )
    golden_angle_competitors: list[str] = Field(
        default_factory=list,
        description=(
            "Competitor domains (not the prospect) confirmed to use Algolia. "
            "If competitor.com uses Algolia, the prospect can be told: "
            "'Your competitor already uses Algolia.' "
            "Only include domains confirmed by evidence."
        ),
    )

    # Narrative
    tech_stack_narrative: str = Field(
        description=(
            "A 2-4 sentence narrative summarising the tech stack findings for this domain. "
            "Lead with the search vendor finding. Note evidence quality. "
            "Flag any golden angle competitor or Algolia displacement opportunity."
        )
    )
