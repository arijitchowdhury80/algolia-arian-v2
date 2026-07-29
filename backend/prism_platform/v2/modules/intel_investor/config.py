"""Intel Investor v2 module configuration."""

from __future__ import annotations

from prism_platform.v2.types import ModuleConfig

INTEL_INVESTOR_CONFIG = ModuleConfig(
    name="intel-investor",
    version="2.0.0",
    description=(
        "Investor and executive intelligence. For public companies, collects stock price, "
        "3-year revenue trend, analyst consensus, and recent news headlines via Yahoo Finance "
        "(deterministic Track 1). Track 2 LLM extracts verbatim executive quotes from earnings "
        "transcripts and 10-K MD&A, tagged with Algolia themes. For private companies, "
        "Track 1 is skipped and Perplexity handles CEO/founder interview research."
    ),
    layer="intelligence",
    cost_tier="deep-research",
    timeout_seconds=180,  # transcript reading is slow
    max_retries=2,
    cache_ttl_days=30,  # financial data and quotes go stale faster than company facts
    # yfinance is called by the Track-1 collector; Perplexity is Track-2 (wired centrally)
    api_clients=["yfinance"],
    composes=["intel-company"],
)
