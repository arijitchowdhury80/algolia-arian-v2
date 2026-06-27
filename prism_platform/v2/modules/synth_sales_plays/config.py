"""Synth Sales Plays v2 module configuration (Wave 5, pure synthesis).

Reads upstream intel (incl. synth-business-case) via `composes` + `{upstream_*}` injection.
No external calls. Note: composes synth-business-case, a W5 sibling — requires W5 sub-wave
ordering (5A business-case → 5B sales-plays) so the cache is populated before this runs.
"""

from __future__ import annotations

from prism_platform.v2.types import ModuleConfig

SYNTH_SALES_PLAYS_CONFIG = ModuleConfig(
    name="synth-sales-plays",
    version="2.0.0",
    description=(
        "AE/BDR sales playbook synthesis. Pure synthesis from upstream intelligence — no "
        "external calls. Produces MEDDPICC mapping, SPIN questions, objection handlers, talk "
        "tracks that mirror the prospect's own executive language, and a buying-committee power "
        "map — grounded in the business case and intel modules."
    ),
    layer="synthesis",
    cost_tier="pro-search",
    timeout_seconds=120,
    max_retries=2,
    cache_ttl_days=30,
    api_clients=[],
    composes=[
        "intel-company",
        "intel-hiring",
        "intel-investor",
        "intel-competitors",
        "intel-techstack",
        "intel-financial-public",
        "intel-financial-private",
        "intel-social",
        "synth-business-case",
    ],
)
