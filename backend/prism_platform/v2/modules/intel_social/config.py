"""Intel Social v2 module configuration."""

from __future__ import annotations

from core.types import ModuleConfig

INTEL_SOCIAL_CONFIG = ModuleConfig(
    name="intel-social",
    version="2.0.0",
    description=(
        "Social intelligence agent. Scrapes LinkedIn company posts and Twitter/X posts "
        "via Apify actors (deterministic Track 1), then scores each post for Algolia "
        "relevance using keyword rules first and LLM only for borderline cases (Track 2). "
        "Produces high-signal posts and a strategic summary for AE outreach."
    ),
    layer="intelligence",
    cost_tier="pro-search",
    timeout_seconds=120,
    max_retries=2,
    cache_ttl_days=7,
    # Track 1 collector uses Apify for LinkedIn + Twitter/X scraping.
    # api_clients documents collector dependencies (not used by the executor directly).
    api_clients=["apify"],
    composes=["intel-company"],
)
