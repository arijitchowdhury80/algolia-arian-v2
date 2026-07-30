"""Intel Partner v2 module configuration."""

from __future__ import annotations

from core.types import ModuleConfig

INTEL_PARTNER_CONFIG = ModuleConfig(
    name="intel-partner",
    version="2.0.0",
    description=(
        "Partner ecosystem agent. Cross-references the prospect's detected tech stack "
        "against a static Algolia partner table (Adobe Commerce, Salesforce Commerce Cloud, "
        "Shopify, SAP, commercetools, BigCommerce, and more) to identify co-sell opportunities. "
        "Adds SI/agency relationships and actionable partner motions via Perplexity."
    ),
    layer="intelligence",
    cost_tier="pro-search",
    timeout_seconds=120,
    max_retries=2,
    cache_ttl_days=30,
    # Track-1 is pure Python (static partner table lookup — no external API).
    # Track-2 uses Perplexity for SI/agency relationships.
    api_clients=[],
    composes=["intel-company", "intel-techstack"],
)
