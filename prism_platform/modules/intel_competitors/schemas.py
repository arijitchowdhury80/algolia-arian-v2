"""Intel Competitors schemas -- input/output contracts for competitive intelligence synthesis."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CompetitorsInput(BaseModel):
    """Input for the competitors module -- just the domain to analyze."""

    model_config = ConfigDict(extra="forbid")
    domain: str


class TechComparison(BaseModel):
    """Technology stack comparison for a single company (prospect or competitor)."""

    model_config = ConfigDict(extra="forbid")

    company_name: str
    domain: str
    search_vendor: str | None = None
    ecommerce_platform: str | None = None
    key_technologies: list[str] = Field(default_factory=list)
    algolia_detected: bool = False


class TrafficComparison(BaseModel):
    """Traffic and engagement comparison for a single company."""

    model_config = ConfigDict(extra="forbid")

    company_name: str
    domain: str
    monthly_visits: int | None = None
    bounce_rate: float | None = None
    pages_per_visit: float | None = None
    organic_search_pct: float | None = None
    growth_trend: str = ""


class FinancialComparison(BaseModel):
    """Financial comparison for a single company."""

    model_config = ConfigDict(extra="forbid")

    company_name: str
    domain: str
    revenue: float | None = None
    revenue_growth_pct: float | None = None
    digital_revenue_pct: float | None = None
    market_cap: float | None = None


class HiringComparison(BaseModel):
    """Hiring activity comparison for a single company."""

    model_config = ConfigDict(extra="forbid")

    company_name: str
    domain: str
    total_open_roles: int = 0
    search_related_roles: int = 0
    build_vs_buy: str = ""
    hiring_trend: str = ""


class ExecutiveSentiment(BaseModel):
    """Executive sentiment and digital commitment for a single company."""

    model_config = ConfigDict(extra="forbid")

    company_name: str
    domain: str
    key_quotes: list[str] = Field(default_factory=list)
    digital_commitment_level: Literal["high", "medium", "low", "unknown"] = "unknown"
    search_mentions: int = 0


class CompetitiveScenario(BaseModel):
    """Recommended competitive play based on synthesized intelligence."""

    model_config = ConfigDict(extra="forbid")

    scenario_type: Literal["golden", "offensive", "defensive", "displacement"]
    description: str
    evidence: list[str] = Field(default_factory=list)
    recommended_play: str = ""


class CompetitorsOutput(BaseModel):
    """Full competitive intelligence output synthesized from upstream modules."""

    model_config = ConfigDict(extra="forbid")

    domain: str

    # Part 1 -- Technology matrix
    tech_comparisons: list[TechComparison] = Field(default_factory=list)
    golden_angle_competitors: list[str] = Field(default_factory=list)
    tech_gaps: list[str] = Field(default_factory=list)

    # Part 2 -- Traffic comparison
    traffic_comparisons: list[TrafficComparison] = Field(default_factory=list)

    # Part 3 -- Financial comparison
    financial_comparisons: list[FinancialComparison] = Field(default_factory=list)

    # Part 4 -- Hiring comparison
    hiring_comparisons: list[HiringComparison] = Field(default_factory=list)

    # Part 5 -- Executive sentiment
    executive_sentiments: list[ExecutiveSentiment] = Field(default_factory=list)

    # Part 6 -- Positioning
    competitive_position: Literal["leader", "fast_follower", "laggard", "unknown"] = "unknown"
    competitive_pressure: Literal["increasing", "stable", "decreasing", "unknown"] = "unknown"
    competitive_scenario: CompetitiveScenario | None = None

    # Summary
    competitive_summary: str = ""
    top_competitive_angles: list[str] = Field(default_factory=list)
