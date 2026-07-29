"""PRISM v2 Core Types — immutable contracts for the agentic module pattern.

Key models:
- Finding: immutable research unit extracted from deep research documents
- ModuleConfig: agent identity card (system prompt equivalent)
- ExecutionContextV2: runtime context passed to every module
- ClaimRegistryEntry: auto-generated claim for factcheck consumption
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FindingCategory(StrEnum):
    """Taxonomy of research findings.

    Used to filter cluster findings by domain module relevance.
    Each domain module declares which categories it consumes.
    """

    # Cluster A: Company & Competitive Landscape
    COMPANY_OVERVIEW = "company_overview"
    BUSINESS_MODEL = "business_model"
    COMPETITIVE_POSITIONING = "competitive_positioning"
    MARKET_POSITION = "market_position"
    PARTNER_ECOSYSTEM = "partner_ecosystem"
    INDUSTRY_TREND = "industry_trend"

    # Cluster B: Financial & Investor Intelligence
    REVENUE = "revenue"
    MARGINS = "margins"
    GROWTH = "growth"
    ANALYST_CONSENSUS = "analyst_consensus"
    EARNINGS_CALL_QUOTE = "earnings_call_quote"
    SEC_FILING_INSIGHT = "sec_filing_insight"
    MA_ACTIVITY = "ma_activity"

    # Cluster C: Technology & Digital Experience
    SEARCH_TECHNOLOGY = "search_technology"
    TECH_STACK = "tech_stack"
    TECH_MIGRATION = "tech_migration"
    DIGITAL_UX = "digital_ux"
    ARCHITECTURE = "architecture"
    USER_REVIEW = "user_review"

    # Cluster D: People & Signals
    EXEC_STATEMENT = "exec_statement"
    LEADERSHIP_CHANGE = "leadership_change"
    SOCIAL_SENTIMENT = "social_sentiment"
    CONFERENCE_TALK = "conference_talk"
    NEWS_EVENT = "news_event"

    # Cluster E: Buying Signals & Intent
    HIRING_SIGNAL = "hiring_signal"
    TECH_REMOVAL = "tech_removal"
    BUDGET_SIGNAL = "budget_signal"
    EVALUATION_SIGNAL = "evaluation_signal"
    COMPETITIVE_PRESSURE = "competitive_pressure"
    FUNDING_EVENT = "funding_event"


class Finding(BaseModel):
    """An immutable research finding extracted from deep research.

    Findings are the atomic unit of research intelligence. Once extracted
    from a research document, they flow through the pipeline unchanged.
    The citation chain from final output back to source URL is always traceable.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: str = Field(description="Unique identifier, e.g. 'f-a-perplexity-001'")
    company: str = Field(description="Which company this finding applies to")
    category: FindingCategory = Field(description="Finding taxonomy category")
    statement: str = Field(description="The actual finding — one clear sentence")
    source_url: str = Field(
        min_length=1,
        description="Citation URL — REQUIRED. No URL = finding is rejected.",
    )
    source_date: date | None = Field(
        default=None,
        description="When the source was published, if known",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="high=multi-source confirmed, medium=single source, low=conflicting data"
    )
    raw_quote: str | None = Field(
        default=None,
        description="Verbatim quote from the source, if applicable",
    )
    provider: str = Field(
        description="Which research provider produced this: 'perplexity' or 'openai'"
    )


class CompetitorRef(BaseModel):
    """Lightweight competitor reference from the seed phase."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    domain: str
    linkedin_url: str | None = None


class ExecutiveRef(BaseModel):
    """Lightweight executive reference from the seed phase."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    title: str
    linkedin_url: str | None = None
    role_classification: (
        Literal["economic_buyer", "technical_buyer", "champion", "influencer", "end_user"] | None
    ) = None


class ModuleConfig(BaseModel):
    """Agent identity card — declares WHO the module is and WHAT it can access.

    This is the system prompt equivalent in the agentic mapping.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(description="Module identifier, e.g. 'intel-company'")
    version: str = Field(description="Semantic version, e.g. '2.0.0'")
    description: str = Field(description="One-line description of what this module discovers")
    layer: Literal["seed", "intelligence", "synthesis", "quality", "delivery"] = Field(
        description="Pipeline layer this module belongs to"
    )
    cost_tier: Literal["pro-search", "deep-research"] = Field(
        description="Perplexity API preset to use"
    )
    timeout_seconds: int = Field(default=120, description="Max execution time")
    max_retries: int = Field(default=2, description="Retry attempts on transient failure")
    cache_ttl_days: int = Field(default=90, description="How long cached results are valid")
    api_clients: list[str] = Field(
        default_factory=list,
        description="Structured API clients this module calls, e.g. ['builtwith', 'similarweb']",
    )
    composes: list[str] = Field(
        default_factory=list,
        description="Upstream modules whose cached output this module reads",
    )
    requires_citations: bool = Field(
        default=True,
        description=(
            "Whether this module's output must carry source citations. True for any "
            "module making factual claims: a zero-citation result is retried once and "
            "then downgraded to 'partial', because search grounding is non-deterministic "
            "and unsourced claims must never look evidenced. Set False only where there "
            "is nothing to cite (e.g. query generation)."
        ),
    )


class ExecutionContextV2(BaseModel):
    """Runtime context passed to every module execution.

    Populated progressively as pipeline phases complete:
    - After seed: domain, company_name, industry, is_public, competitors, executives
    - After research: cluster_findings populated
    - During domain modules: upstream_results populated as each module completes
    """

    model_config = ConfigDict(extra="forbid")

    audit_id: str
    account_domain: str
    company_name: str = ""
    industry: str = ""
    is_public: bool = False
    ticker: str | None = None
    competitors: list[CompetitorRef] = Field(default_factory=list)
    executives: list[ExecutiveRef] = Field(default_factory=list)
    cluster_findings: dict[str, list[Finding]] = Field(
        default_factory=dict,
        description="Merged findings keyed by cluster ID: 'A', 'B', 'C', 'D', 'E'",
    )
    upstream_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Cached outputs from completed upstream modules, keyed by module name",
    )


class ClaimRegistryEntry(BaseModel):
    """A verifiable claim extracted from module output for factcheck consumption.

    Every module auto-generates these from its output fields.
    The factcheck evaluator (Phase 7) consumes all claim registries.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    statement: str = Field(description="The claim in natural language")
    source_url: str = Field(description="Citation URL backing this claim")
    evidence_tier: Literal["VERIFIED", "WEBFETCH", "WEBSEARCH", "ESTIMATE"] = Field(
        description="How confident we are in this data point"
    )
    module_origin: str = Field(description="Which module produced this claim")
    field_path: str = Field(description="Dot-path to the output field, e.g. 'revenue_estimate'")
