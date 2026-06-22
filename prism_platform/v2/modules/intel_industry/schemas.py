"""Intel Industry v2 schemas — vertical intelligence output.

This is a pure Track-2 (LLM) module. Vertical benchmarks, analyst quotes, and
2025-26 trend data have no structured API — Perplexity pro-search with citations
is the right tool. The output drives the "why now / why Algolia in this vertical"
sales narrative.

Execution strategy: prospect-only (the LLM researches the vertical, not a set of
companies — one call is sufficient).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VerticalBenchmarkStat(BaseModel):
    """A single benchmark statistic from a named industry source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stat: str = Field(description="The benchmark statistic as a plain sentence (include number)")
    source: str = Field(description="Named source (e.g. 'Baymard Institute', 'Forrester', 'NRF')")
    url: str | None = Field(
        default=None,
        description="Citation URL if available. Null if not found — never fabricate.",
    )
    relevance: str = Field(
        description="One sentence: why this stat matters in an Algolia sales conversation"
    )


class AnalystQuote(BaseModel):
    """A verbatim or close-paraphrase quote from a named analyst or executive."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    quote: str = Field(
        description=(
            "The quote, verbatim or close paraphrase. Must be sourced — do not fabricate."
        )
    )
    attribution: str = Field(
        description="Name and title of the person quoted (e.g. 'Jane Smith, VP Research, Gartner')"
    )
    source: str = Field(
        description="Publication or report the quote appeared in"
    )
    url: str | None = Field(
        default=None,
        description="Citation URL. Null if not available — never fabricate.",
    )
    algolia_theme: str | None = Field(
        default=None,
        description=(
            "The Algolia sales theme this quote supports: e.g. 'search-as-conversion-driver', "
            "'personalization', 'ai-search', 'speed', 'zero-results-cost'. Null if none fits."
        ),
    )


class IndustryIntelOutput(BaseModel):
    """Vertical intelligence output for a prospect's industry."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Prospect domain analyzed")

    vertical: str = Field(
        description=(
            "Canonical vertical label (e.g. 'B2C Fashion & Apparel', 'B2B Industrial "
            "Distribution', 'Marketplace', 'Luxury Retail', 'Home & Garden')"
        )
    )

    benchmark_stats: list[VerticalBenchmarkStat] = Field(
        default_factory=list,
        description=(
            "3-6 benchmark statistics from authoritative industry sources (Baymard, "
            "Forrester, NRF, Nielsen, ECDB, eMarketer). Each must carry a named source. "
            "Do not include stats you cannot attribute."
        ),
    )

    trend_summary: str = Field(
        description=(
            "A 3-5 sentence narrative on the 2-3 most important trends shaping search "
            "and discovery in this vertical in 2025-26. Written for a sales rep — "
            "concrete, named trends with numbers where possible."
        )
    )

    analyst_quotes: list[AnalystQuote] = Field(
        default_factory=list,
        description=(
            "2-4 quotes from named analysts or industry executives that support the "
            "Algolia pitch in this vertical. Verbatim or close paraphrase. Never fabricated."
        ),
    )

    algolia_relevance_narrative: str = Field(
        description=(
            "A 3-4 sentence narrative for a sales rep: why Algolia is the right solution "
            "for this vertical right now. Ground it in the benchmark stats and trends above. "
            "Specific and actionable — not generic product marketing copy."
        )
    )

    sources: list[str] = Field(
        default_factory=list,
        description=(
            "All citation URLs used in this output. Copied from benchmark_stats and "
            "analyst_quotes. Deduplicated. Perplexity should populate this automatically."
        ),
    )
