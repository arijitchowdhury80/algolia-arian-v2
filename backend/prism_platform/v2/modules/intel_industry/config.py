"""Intel Industry v2 module configuration."""

from __future__ import annotations

from core.types import ModuleConfig

INTEL_INDUSTRY_CONFIG = ModuleConfig(
    name="intel-industry",
    version="2.0.0",
    description=(
        "Industry intelligence agent. Researches the prospect's vertical using "
        "Perplexity pro-search: vertical benchmarks (Baymard, Forrester, NRF), "
        "ecommerce search conversion stats, 2025-26 trend analysis, named analyst "
        "quotes with citations, and a narrative on why Algolia is the right solution "
        "in this vertical right now. This is the one justified pure-LLM module — "
        "industry benchmarks and analyst quotes have no structured API."
    ),
    layer="intelligence",
    cost_tier="pro-search",
    timeout_seconds=120,
    max_retries=2,
    cache_ttl_days=30,
    api_clients=[],
    composes=["intel-company"],
)
