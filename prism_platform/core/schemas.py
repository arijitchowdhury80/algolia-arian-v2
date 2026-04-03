"""PRISM Core Schemas -- shared models used across modules."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Person(BaseModel):
    """A person associated with a company (executive, contact, etc.)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    title: str | None = None
    linkedin_url: str | None = None
    email: str | None = None


class Company(BaseModel):
    """Core company information shared across modules."""

    model_config = ConfigDict(extra="forbid")

    name: str
    domain: str
    vertical: str | None = None
    is_public: bool = False
    ticker: str | None = None
    headquarters: str | None = None
    employee_count: int | None = None
    annual_revenue_usd: float | None = None
    executives: list[Person] = Field(default_factory=list)
