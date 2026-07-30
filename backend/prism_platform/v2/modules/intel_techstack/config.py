"""Intel TechStack v2 module configuration."""

from __future__ import annotations

from core.types import ModuleConfig

INTEL_TECHSTACK_CONFIG = ModuleConfig(
    name="intel-techstack",
    version="2.0.0",
    description=(
        "Technology stack detection agent. Identifies the search vendor powering a domain, "
        "assesses the full tech stack, and flags competitors using Algolia (golden angle signal). "
        "Runs once per company (prospect + each competitor) via per-company fan-out strategy."
    ),
    layer="intelligence",
    cost_tier="pro-search",
    timeout_seconds=90,
    max_retries=2,
    cache_ttl_days=30,
    api_clients=["builtwith"],
    composes=[],
)
