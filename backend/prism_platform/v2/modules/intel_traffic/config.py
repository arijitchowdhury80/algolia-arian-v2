"""Intel Traffic v2 module configuration."""

from __future__ import annotations

from core.types import ModuleConfig

INTEL_TRAFFIC_CONFIG = ModuleConfig(
    name="intel-traffic",
    version="2.0.0",
    description=(
        "Traffic intelligence agent. Analyzes website traffic patterns for the prospect "
        "and competitor set using SimilarWeb data and Google Trends. "
        "Runs as a single comparative call covering all companies in context."
    ),
    layer="intelligence",
    cost_tier="pro-search",
    timeout_seconds=120,
    max_retries=2,
    cache_ttl_days=14,
    api_clients=["similarweb"],
    composes=[],
)
