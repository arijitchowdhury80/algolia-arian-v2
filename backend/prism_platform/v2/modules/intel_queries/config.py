"""Intel Queries v2 module configuration."""

from __future__ import annotations

from core.types import ModuleConfig

INTEL_QUERIES_CONFIG = ModuleConfig(
    name="intel-queries",
    version="2.0.0",
    description=(
        "Generates the browser-audit test-query set for a prospect. "
        "Produces broad, specific, NLP/conversational, typo-variant, synonym, "
        "non-product, brand, and zero-results query types from product categories "
        "(intel-company) and top organic keywords (intel-traffic). "
        "Track 1 is pure Python — no LLM, no external API."
    ),
    layer="intelligence",
    cost_tier="pro-search",
    timeout_seconds=30,  # pure Python generation — should complete in milliseconds
    max_retries=1,
    cache_ttl_days=30,
    api_clients=[],  # no external APIs — collector is pure Python
    composes=["intel-company", "intel-traffic"],
    # Output is generated test queries, not factual claims — there is nothing to cite.
    requires_citations=False,
)
