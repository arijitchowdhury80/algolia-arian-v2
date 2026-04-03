"""Intel Company schemas -- input/output contracts for company intelligence.

These schemas define the Pydantic models for the intel-company module,
the foundation module that seeds every other module in the audit pipeline.
All fields match the spec in docs/specs/algolia-pip-spec-v2-temporal.md Section 2.5.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class CompanyInput(BaseModel):
    """Input for the intel-company module."""

    model_config = ConfigDict(extra="ignore")

    domain: str = Field(description="Website domain to analyze, e.g. 'dell.com'")


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class Executive(BaseModel):
    """A member of the company's leadership team."""

    model_config = ConfigDict(extra="ignore")

    full_name: str = Field(description="Full name of the executive")
    title: str = Field(description="Current job title")
    linkedin_url: str | None = Field(
        default=None,
        description="LinkedIn profile URL. Must start with https://linkedin.com/in/ or https://www.linkedin.com/in/",
    )
    headshot_url: str | None = Field(
        default=None,
        description="URL to headshot image, if available",
    )
    tenure_description: str | None = Field(
        default=None,
        description="How long they've been in this role, e.g. 'Since 2019' or '3 years'",
    )
    previous_company: str | None = Field(
        default=None,
        description="Most recent previous employer before current role",
    )
    previous_role: str | None = Field(
        default=None,
        description="Their title at the previous company",
    )
class Competitor(BaseModel):
    """A direct competitor of the prospect company."""

    model_config = ConfigDict(extra="ignore")

    company_name: str = Field(description="Competitor's legal or common name")
    domain: str = Field(description="Competitor's primary website domain")
    why_competitor: str = Field(
        description="One sentence explaining why they compete with the prospect"
    )
    is_algolia_customer: bool = Field(
        default=False,
        description="Whether this competitor is a known Algolia customer",
    )


class NewsItem(BaseModel):
    """A recent news article or press release about the company."""

    model_config = ConfigDict(extra="ignore")

    headline: str = Field(description="Article headline or title")
    source: str = Field(description="Publication name, e.g. 'TechCrunch', 'Reuters'")
    date: str = Field(
        description="Publication date as YYYY-MM-DD or approximate, e.g. '2026-03-15'",
    )
    url: str | None = Field(default=None, description="URL to the article")
    category: str = Field(
        default="other",
        description="News category for filtering (e.g. leadership_change, product_launch, partnership, financial, acquisition, technology, expansion, bankruptcy, other)",
    )


class BlogPost(BaseModel):
    """A recent blog post from the company's own blog or newsroom."""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(description="Blog post title")
    date: str = Field(description="Publication date as YYYY-MM-DD or approximate")
    url: str | None = Field(default=None, description="URL to the blog post")
    summary: str = Field(
        default="",
        description="One-sentence summary of the blog post content",
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class CompanyProfileOutput(BaseModel):
    """Full company intelligence output -- the foundation for all downstream modules.

    Every field description doubles as an LLM instruction when this schema
    is used with Instructor for structured extraction.
    """

    model_config = ConfigDict(extra="ignore")

    # Identity
    legal_name: str = Field(description="Official registered company name")
    common_name: str = Field(description="Name commonly used in press/marketing")
    domain: str = Field(description="Primary website domain, e.g. 'dell.com'")
    headquarters: str = Field(description="HQ city and country, e.g. 'Round Rock, Texas, USA'")
    employee_count: int | None = Field(
        default=None,
        description=(
            "Approximate number of employees as an integer, e.g. 133000. NOT a formatted string."
        ),
    )
    employee_count_source: str | None = Field(
        default=None,
        description="Where the employee count came from, e.g. 'LinkedIn', 'Company About page'",
    )
    year_founded: int | None = Field(
        default=None,
        description="Year the company was founded as a 4-digit integer, e.g. 1984",
    )
    business_model: str = Field(
        description=(
            "Detailed description of how the company makes money and serves customers. "
            "Minimum 50 characters. Include primary revenue streams, target market, "
            "and key product/service categories."
        ),
    )
    motto: str | None = Field(
        default=None,
        description="Company tagline or motto if publicly stated",
    )

    # Classification
    industry: str = Field(
        description=(
            "Primary industry classification, e.g. 'Enterprise Technology', 'E-commerce Retail'"
        ),
    )
    sub_vertical: str | None = Field(
        default=None,
        description="More specific sub-vertical, e.g. 'Consumer Electronics', 'Fashion Retail'",
    )
    is_public: bool = Field(
        default=False,
        description="True if the company is publicly traded on a stock exchange",
    )
    ticker: str | None = Field(
        default=None,
        description="Stock ticker symbol if public, e.g. 'DELL'. None if private.",
    )
    parent_company: str | None = Field(
        default=None,
        description="Parent company name if this is a subsidiary. None if independent.",
    )
    revenue_estimate: float | None = Field(
        default=None,
        description=(
            "Annual revenue in USD as a float, e.g. 88400000000.0 for $88.4B. "
            "NOT a formatted string like '$88.4B'. Set to None if unknown."
        ),
    )
    revenue_source: str | None = Field(
        default=None,
        description="Source of the revenue figure, e.g. 'SEC 10-K FY2025', 'Forbes estimate'",
    )

    # People, competitors, activity
    executives: list[Executive] = Field(
        default_factory=list,
        description=(
            "8-12 key executives. Include CEO, CTO, CFO, "
            "VP Engineering, VP Product, CMO at minimum."
        ),
    )
    competitors: list[Competitor] = Field(
        default_factory=list,
        description="5-7 direct competitors. Include domain for each.",
    )
    recent_news: list[NewsItem] = Field(
        default_factory=list,
        description="3-10 recent news items from the last 90 days",
    )
    recent_blog_posts: list[BlogPost] = Field(
        default_factory=list,
        description="3-5 recent blog posts from the company's own blog or newsroom",
    )

    # Website snapshot
    has_search_bar: bool | None = Field(
        default=None,
        description="Whether the company's website has a visible search bar on the homepage",
    )
    product_categories: list[str] = Field(
        default_factory=list,
        description="Top-level product/service categories visible on the website",
    )
    search_experience_description: str | None = Field(
        default=None,
        description=(
            "Brief description of the current search experience on the website. "
            "e.g. 'Basic keyword search with no autocomplete' or "
            "'Faceted search with filters and autocomplete powered by Elasticsearch'"
        ),
    )
