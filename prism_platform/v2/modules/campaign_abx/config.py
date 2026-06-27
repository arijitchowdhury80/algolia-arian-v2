"""Campaign ABX v2 module configuration (Wave 5, pure synthesis).

Reads upstream intel + the two synth modules via `composes` + `{upstream_*}` injection.
No external calls. Composes W5 siblings (synth-business-case, synth-sales-plays) — requires
W5 sub-wave ordering so their cache is populated before this runs.
"""

from __future__ import annotations

from prism_platform.v2.types import ModuleConfig

CAMPAIGN_ABX_CONFIG = ModuleConfig(
    name="campaign-abx",
    version="2.0.0",
    description=(
        "Multi-touch ABX campaign synthesis. Pure synthesis from upstream intelligence + the "
        "business case + sales plays — no external calls. Produces a 5-email sequence, "
        "personalized LinkedIn messages per buying-committee member, a Loom video script, a "
        "week-by-week collateral schedule, and competitor-specific displacement messaging."
    ),
    layer="synthesis",
    cost_tier="pro-search",
    timeout_seconds=120,
    max_retries=2,
    cache_ttl_days=30,
    api_clients=[],
    composes=[
        "synth-business-case",
        "synth-sales-plays",
        "intel-hiring",
        "intel-company",
        "intel-investor",
        "intel-competitors",
        "intel-techstack",
        "intel-social",
    ],
)
