"""Intel Hiring v2 module configuration."""

from __future__ import annotations

from prism_platform.v2.types import ModuleConfig

INTEL_HIRING_CONFIG = ModuleConfig(
    name="intel-hiring",
    version="2.0.0",
    description=(
        "Hiring intelligence agent. Detects open roles, maps them to MEDDPICC ICP tiers, "
        "classifies build-vs-buy intent from search-related job postings, "
        "and produces a quantified hiring_signal_score for downstream buying signal inference."
    ),
    layer="intelligence",
    cost_tier="pro-search",
    timeout_seconds=120,
    max_retries=2,
    cache_ttl_days=7,
    api_clients=[],
    composes=[],
)
