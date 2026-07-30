"""Intel Financial Public v2 module configuration."""

from __future__ import annotations

from core.types import ModuleConfig

INTEL_FINANCIAL_PUBLIC_CONFIG = ModuleConfig(
    name="intel-financial-public",
    version="2.0.0",
    description=(
        "Public company financial intelligence agent. "
        "Extracts structured financials (Yahoo Finance), SEC EDGAR filing insights, "
        "and verbatim executive quotes from earnings calls and investor presentations. "
        "Only runs for public companies with a known ticker. Skips private companies."
    ),
    layer="intelligence",
    cost_tier="deep-research",
    timeout_seconds=180,
    max_retries=2,
    cache_ttl_days=7,
    api_clients=["yahoo_finance", "sec_edgar"],
    composes=[],
)
