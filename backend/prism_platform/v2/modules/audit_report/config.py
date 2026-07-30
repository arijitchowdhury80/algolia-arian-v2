"""Audit Report v2 module configuration (Wave 6, pure synthesis — final deliverable).

Reads ALL upstream output via `composes` + `{upstream_*}` injection. No external calls.
NOTE: audit-browser (W2) will be added to `composes` once that module is rebuilt — until then,
dimension scores are estimated from techstack + traffic (is_estimated=True).
"""

from __future__ import annotations

from core.types import ModuleConfig

AUDIT_REPORT_CONFIG = ModuleConfig(
    name="audit-report",
    version="2.0.0",
    description=(
        "Final audit deliverable synthesis. Pure synthesis from all upstream modules — no "
        "external calls. Produces 10-dimension search scoring (estimated until browser audit "
        "confirms), competitor benchmark, AE pre-call brief, and a prospect-safe leave-behind."
    ),
    layer="delivery",
    cost_tier="pro-search",
    timeout_seconds=180,
    max_retries=2,
    cache_ttl_days=30,
    api_clients=[],
    composes=[
        "synth-business-case",
        "synth-sales-plays",
        "intel-competitors",
        "intel-company",
        "intel-techstack",
        "intel-traffic",
        "intel-industry",
        # "audit-browser",  # added when W2 audit-browser is rebuilt
    ],
)
