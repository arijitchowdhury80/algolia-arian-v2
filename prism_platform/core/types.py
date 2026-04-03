"""PRISM Core Types -- immutable contracts for all modules."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceTier(StrEnum):
    """How confident are we in this data point?"""

    VERIFIED = "VERIFIED"  # Direct API, SEC filing, official source
    WEBFETCH = "WEBFETCH"  # Third-party page fetched and confirmed
    WEBSEARCH = "WEBSEARCH"  # Found via search, not independently confirmed
    ESTIMATE = "ESTIMATE"  # Derived/inferred, not directly sourced
    NO_SOURCE = "NO_SOURCE"  # Cannot be verified -- MUST be dropped


class Source(BaseModel):
    """Provenance for a single data point."""

    model_config = ConfigDict(frozen=True)

    field: str
    value: str
    tier: EvidenceTier
    source_url: str | None = None
    source_label: str
    method: str = "direct_api"  # direct_api, scrape, llm_extraction, model_estimate
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    as_of_date: date | None = None
    confidence: Literal["high", "medium", "low"] = "high"
    conflicts_with: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Result of validating a module's output."""

    model_config = ConfigDict(frozen=True)

    passed: bool
    checks_run: int
    checks_passed: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ModuleResult(BaseModel):
    """Standard return type for every module execution."""

    module_name: str
    module_version: str
    status: Literal["success", "partial", "failed"]
    output: dict[str, object]
    sources: list[Source] = Field(default_factory=list)
    duration_ms: int = 0
    llm_calls: int = 0
    llm_cost_usd: float = 0.0
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    executed_at: datetime = Field(default_factory=datetime.utcnow)
