"""intel-company v2 schemas — the seed module's data contracts.

CompanySeedOutput is the foundation that every downstream module reads.
Field descriptions double as LLM instructions when the schema is passed
to the Agent API as response_format or included in the system prompt.

Changes from v1:
- extra="forbid" (v1 used extra="ignore" — silently ate bad fields)
- Literal types for role_classification (v1 used bare str)
- min_length on business_model (v1 validated post-hoc in validator.py)
- ExecutiveSeed includes role_classification for MEDDPICC mapping
- CompetitorSeed includes linkedin_url for social intelligence
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExecutiveSeed(BaseModel):
    """An executive discovered during seed research.

    role_classification maps to MEDDPICC buyer roles for downstream
    sales intelligence generation.
    """

    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(description="Full name of the executive")
    title: str = Field(description="Current job title")
    role_classification: (
        Literal[
            "economic_buyer",
            "technical_buyer",
            "champion",
            "influencer",
            "end_user",
        ]
        | None
    ) = Field(
        default=None,
        description=(
            "MEDDPICC role classification based on title. "
            "CEO/CFO/CRO = economic_buyer. CTO/VP Eng = technical_buyer. "
            "VP Digital/Head of Search = champion. Director level = influencer. "
            "None if unclear."
        ),
    )
    linkedin_url: str | None = Field(
        default=None,
        description=(
            "LinkedIn profile URL. Must start with https://linkedin.com/in/ or "
            "https://www.linkedin.com/in/. Do NOT fabricate — only include if found."
        ),
    )
    tenure_description: str | None = Field(
        default=None,
        description="How long in current role, e.g. 'Since 2021' or '3 years'",
    )
    previous_company: str | None = Field(
        default=None,
        description="Most recent previous employer",
    )


class CompetitorSeed(BaseModel):
    """A direct competitor discovered during seed research."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Competitor's name")
    domain: str = Field(description="Competitor's primary website domain")
    why_competitor: str = Field(description="One sentence: why they compete with the prospect")
    linkedin_url: str | None = Field(
        default=None,
        description="Company LinkedIn page URL, if found",
    )


class CompanySeedOutput(BaseModel):
    """Full output from the intel-company seed module.

    This is the identity card that every downstream module reads.
    Every field description is an LLM instruction — write them carefully.
    """

    model_config = ConfigDict(extra="forbid")

    # Identity
    legal_name: str = Field(description="Official registered company name")
    common_name: str = Field(description="Name used in press/marketing")
    domain: str = Field(description="Primary website domain, e.g. 'dell.com'")
    headquarters: str = Field(description="HQ city and country, e.g. 'Round Rock, Texas, USA'")
    employee_count: int | None = Field(
        default=None,
        description="Approximate employee count as integer, e.g. 133000. NOT a string.",
    )
    employee_count_source: str | None = Field(
        default=None,
        description="Source of employee count, e.g. 'LinkedIn', 'Company website'",
    )
    year_founded: int | None = Field(
        default=None,
        description="Year founded as 4-digit integer, e.g. 1984",
    )
    business_model: str = Field(
        min_length=50,
        description=(
            "Detailed description of how the company makes money. "
            "Minimum 50 characters. Include revenue streams, target market, "
            "and key products/services."
        ),
    )

    # Classification
    industry: str = Field(
        description="Primary industry, e.g. 'Enterprise Technology', 'E-commerce Retail'"
    )
    sub_vertical: str | None = Field(
        default=None,
        description="Specific sub-vertical, e.g. 'Consumer Electronics', 'Fashion Retail'",
    )
    is_public: bool = Field(
        default=False,
        description="True if publicly traded on a stock exchange",
    )
    ticker: str | None = Field(
        default=None,
        description="Stock ticker if public, e.g. 'DELL'. None if private.",
    )
    parent_company: str | None = Field(
        default=None,
        description="Parent company name if subsidiary. None if independent.",
    )
    revenue_estimate: float | None = Field(
        default=None,
        description=(
            "Annual revenue in USD as float, e.g. 88400000000.0 for $88.4B. "
            "NOT a formatted string. None if unknown."
        ),
    )
    revenue_source: str | None = Field(
        default=None,
        description="Source of revenue figure, e.g. 'SEC 10-K FY2025'",
    )

    # People & competitors
    executives: list[ExecutiveSeed] = Field(
        default_factory=list,
        description=(
            "5-12 key executives. Must include CEO, CTO, CFO at minimum. "
            "Include VP/Director of Engineering, Product, E-commerce, Digital, Search. "
            "For subsidiaries, include both subsidiary and relevant parent company leaders."
        ),
    )
    competitors: list[CompetitorSeed] = Field(
        default_factory=list,
        description=(
            "5-7 direct competitors selling similar products/services "
            "to similar customers in the same market."
        ),
    )

    # Website snapshot
    product_categories: list[str] = Field(
        default_factory=list,
        description="Top-level product/service categories visible on the website",
    )
    company_linkedin_url: str | None = Field(
        default=None,
        description="Company LinkedIn page URL",
    )
    recent_headline: str | None = Field(
        default=None,
        description="One recent newsworthy headline about the company (last 90 days)",
    )
