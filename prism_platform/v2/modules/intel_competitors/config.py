"""Intel Competitors v2 module configuration."""

from __future__ import annotations

from prism_platform.v2.types import ModuleConfig

INTEL_COMPETITORS_CONFIG = ModuleConfig(
    name="intel-competitors",
    version="2.0.0",
    description=(
        "Competitive search-landscape agent. For each competitor it determines the "
        "search vendor (via PRISM's own Scout-based detector — no BuiltWith), flags any "
        "running Algolia (the golden angle), classifies the competitive scenario, and "
        "matches Algolia case studies to the prospect's vertical."
    ),
    layer="intelligence",
    cost_tier="pro-search",
    timeout_seconds=150,  # Track-1 scans N competitor domains before the single LLM call
    max_retries=2,
    cache_ttl_days=30,
    # No paid API clients — search-vendor detection is in-app (Scout source scan).
    api_clients=[],
    composes=["intel-company", "intel-techstack"],
)
