"""intel-company v2 ModuleConfig — the agent's identity card.

This is the SEED module. It runs first in every audit, using a single
Perplexity pro-search call to produce the company identity card that
every downstream module reads.
"""

from prism_platform.v2.types import ModuleConfig

INTEL_COMPANY_CONFIG = ModuleConfig(
    name="intel-company",
    version="2.0.0",
    description=(
        "Foundation company intelligence researcher. Discovers company identity, "
        "leadership team, competitors, and business model from a single domain input."
    ),
    layer="seed",
    cost_tier="pro-search",
    timeout_seconds=120,
    max_retries=2,
    cache_ttl_days=180,
    api_clients=[],  # Seed uses only Agent API, no structured APIs
    composes=[],  # Seed has no upstream dependencies
)
