"""Synth Business Case v2 module configuration.

Pure synthesis (Wave 5). Reads upstream intel from the cache via `composes` and the
generic executor injects each as `{upstream_<name>}` into the playbook. No external calls.
"""

from __future__ import annotations

from prism_platform.v2.types import ModuleConfig

SYNTH_BUSINESS_CASE_CONFIG = ModuleConfig(
    name="synth-business-case",
    version="2.0.0",
    description=(
        "ROI business-case synthesis. Pure synthesis from upstream intelligence — no external "
        "API calls. Produces the Said-vs-Found matrix, value levers (conservative + moderate "
        "annual impact), displacement cost vs the incumbent search vendor, matched Algolia "
        "customer proofs, and timing signals — an AE-ready ROI narrative."
    ),
    layer="synthesis",
    cost_tier="pro-search",
    timeout_seconds=120,
    max_retries=2,
    cache_ttl_days=30,
    api_clients=[],
    composes=[
        "intel-company",
        "intel-investor",
        "intel-industry",
        "intel-competitors",
        "intel-techstack",
        "intel-traffic",
        "intel-financial-public",
        "intel-financial-private",
        "intel-news",
        "intel-hiring",
        "intel-social",
    ],
)
