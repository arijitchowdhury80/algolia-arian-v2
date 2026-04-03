"""Intel TechStack schemas -- input/output contracts for tech stack detection."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from prism_platform.core.types import EvidenceTier


class TechStackInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: str


class SearchVendor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    status: Literal["ACTIVE", "TAG_ONLY", "REMOVED", "UNDETECTED"]
    detection_source: str
    evidence_tier: EvidenceTier


class CompetitorTechStack(BaseModel):
    """Technology stack data for a single competitor."""

    model_config = ConfigDict(extra="forbid")
    company_name: str
    domain: str
    search_vendor: SearchVendor | None = None
    ecommerce_platform: str | None = None
    all_technologies: list[dict[str, object]] = Field(default_factory=list)
    tech_count: int = 0
    is_algolia_customer: bool = False


class TechStackOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    search_vendor: SearchVendor | None = None
    ecommerce_platform: str | None = None
    cms: str | None = None
    cdn: str | None = None
    analytics: list[str] = Field(default_factory=list)
    personalization: list[str] = Field(default_factory=list)
    bot_detection: str | None = None
    all_technologies: list[dict[str, object]] = Field(default_factory=list)
    removed_technologies: list[dict[str, object]] = Field(default_factory=list)
    tech_stack_summary: str = ""
    algolia_detected: bool = False
    competitor_tech_stacks: list[CompetitorTechStack] = Field(default_factory=list)
    comparative_summary: str = ""
    golden_angle_competitors: list[str] = Field(default_factory=list)
