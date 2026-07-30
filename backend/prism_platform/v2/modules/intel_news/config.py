"""Intel News v2 module configuration."""

from __future__ import annotations

from core.types import ModuleConfig

INTEL_NEWS_CONFIG = ModuleConfig(
    name="intel-news",
    version="2.0.0",
    description=(
        "News intelligence agent. Collects recent news (last 90 days) for the prospect "
        "and competitor set. Classifies articles by urgency and sell signal status. "
        "Produces outreach angle from the single most actionable news item."
    ),
    layer="intelligence",
    cost_tier="pro-search",
    timeout_seconds=90,
    max_retries=2,
    cache_ttl_days=3,
    api_clients=[],
    composes=[],
)
