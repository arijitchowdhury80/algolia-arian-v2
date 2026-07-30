"""Intel Financial Private v2 module configuration."""

from __future__ import annotations

from core.types import ModuleConfig

INTEL_FINANCIAL_PRIVATE_CONFIG = ModuleConfig(
    name="intel-financial-private",
    version="2.0.0",
    description=(
        "Private company revenue estimation agent. "
        "Multi-source waterfall: press releases, industry reports, Crunchbase funding, "
        "employee count model, Inc 5000 rankings. "
        "Skipped automatically for public companies (use intel-financial-public instead)."
    ),
    layer="intelligence",
    cost_tier="pro-search",
    timeout_seconds=120,
    max_retries=2,
    cache_ttl_days=30,
    api_clients=[],
    composes=[],
)
