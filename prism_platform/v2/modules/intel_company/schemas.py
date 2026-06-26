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


class SubsidiarySeed(BaseModel):
    """A brand or subsidiary owned by the prospect company.

    Captures the full brand portfolio — wholly-owned subsidiaries,
    acquired brands, and operating divisions with their own identity.
    Examples: Nike owns Jordan and Converse; Berkshire Hathaway owns
    Oriental Trading which owns MindWare, Fun Express, Smile Makers.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Brand or subsidiary name, e.g. 'Jordan', 'MindWare'")
    domain: str | None = Field(
        default=None,
        description="Their own domain if they have one, e.g. 'jordan.com'. None if no separate domain.",
    )
    description: str | None = Field(
        default=None,
        description="One sentence: what this brand/subsidiary does and how it relates to the parent company.",
    )


class CompetitorSeed(BaseModel):
    """A direct competitor discovered during seed research."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Competitor's name")
    domain: str = Field(description="Competitor's primary website domain")
    why_competitor: str = Field(description="One sentence: why they compete with the prospect")
    ticker: str | None = Field(
        default=None,
        description="Stock ticker symbol if publicly traded, e.g. 'ADDYY'. None if private.",
    )
    linkedin_url: str | None = Field(
        default=None,
        description=(
            "Company LinkedIn page URL, e.g. 'https://www.linkedin.com/company/adidas/'. "
            "Only include if actually found."
        ),
    )
    twitter_handle: str | None = Field(
        default=None,
        description="Twitter/X handle without @ symbol, e.g. 'adidas'. None if not found.",
    )
    youtube_url: str | None = Field(
        default=None,
        description="YouTube channel URL, e.g. 'https://www.youtube.com/@adidas'. None if not found.",  # noqa: E501
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
        description="Parent company name if subsidiary, e.g. 'Berkshire Hathaway Inc.'. None if independent.",
    )
    parent_domain: str | None = Field(
        default=None,
        description="Parent company's primary domain, e.g. 'berkshirehathaway.com'. None if independent or unknown.",
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

    # Company hierarchy
    subsidiaries: list[SubsidiarySeed] = Field(
        default_factory=list,
        description=(
            "All brands and subsidiaries OWNED by this company. "
            "Include wholly-owned subsidiaries, acquired brands, and operating divisions "
            "that have their own identity. "
            "Nike example: [Jordan, Converse, Hurley]. "
            "Oriental Trading example: [MindWare, Fun Express, Smile Makers, Morris Costumes]. "
            "Empty list if the company owns no distinct sub-brands."
        ),
    )

    # People & competitors
    executives: list[ExecutiveSeed] = Field(
        default_factory=list,
        description=(
            "5-12 CURRENT, ACTIVE key executives. Must include CEO, CTO, CFO at minimum. "
            "Include VP/Director of Engineering, Product, E-commerce, Digital, Search. "
            "For subsidiaries, include both subsidiary and relevant parent company leaders. "
            "Do NOT include historical figures or anyone with 'Former' in their title."
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
        description=(
            "Company LinkedIn page URL, e.g. 'https://www.linkedin.com/company/nike/'. "
            "Only include if actually found."
        ),
    )
    twitter_handle: str | None = Field(
        default=None,
        description="Twitter/X handle without @ symbol, e.g. 'Nike'. None if not found.",
    )
    youtube_url: str | None = Field(
        default=None,
        description="YouTube channel URL, e.g. 'https://www.youtube.com/@nike'. None if not found.",
    )
    recent_headline: str | None = Field(
        default=None,
        description="One recent newsworthy headline about the company (last 90 days)",
    )
