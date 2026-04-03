"""Contract tests for intel-company schemas.

Validates Pydantic models accept valid data, reject invalid data,
and enforce all constraints specified in Section 2.5 of the spec.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.intel_company.schemas import (
    BlogPost,
    CompanyInput,
    CompanyProfileOutput,
    Competitor,
    Executive,
    NewsItem,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_executive(**overrides: object) -> dict:
    """Build a valid Executive dict with optional overrides."""
    base = {
        "full_name": "Michael Dell",
        "title": "Chairman and CEO",
        "linkedin_url": "https://www.linkedin.com/in/michaeldell",
        "headshot_url": None,
        "tenure_description": "Since 2013",
        "previous_company": "MSD Capital",
        "previous_role": "Managing Partner",
        "relevance": "economic_buyer",
    }
    base.update(overrides)
    return base


def _make_competitor(**overrides: object) -> dict:
    """Build a valid Competitor dict with optional overrides."""
    base = {
        "company_name": "HP Inc.",
        "domain": "hp.com",
        "why_competitor": "Competes in personal computing and printers",
        "relative_size": "similar",
        "is_algolia_customer": False,
    }
    base.update(overrides)
    return base


def _make_news_item(**overrides: object) -> dict:
    """Build a valid NewsItem dict with optional overrides."""
    base = {
        "headline": "Dell Reports Record Q4 Revenue",
        "source": "Reuters",
        "date": "2026-02-15",
        "url": "https://reuters.com/dell-q4",
        "category": "financial",
    }
    base.update(overrides)
    return base


def _make_blog_post(**overrides: object) -> dict:
    """Build a valid BlogPost dict with optional overrides."""
    base = {
        "title": "Introducing Dell AI Factory",
        "date": "2026-03-01",
        "url": "https://dell.com/blog/ai-factory",
        "summary": "Dell announces new AI infrastructure product line.",
    }
    base.update(overrides)
    return base


def _make_full_output(**overrides: object) -> dict:
    """Build a valid CompanyProfileOutput dict with optional overrides."""
    base = {
        "legal_name": "Dell Technologies Inc.",
        "common_name": "Dell",
        "domain": "dell.com",
        "headquarters": "Round Rock, Texas, USA",
        "employee_count": 133000,
        "employee_count_source": "LinkedIn",
        "year_founded": 1984,
        "business_model": (
            "Dell Technologies is a multinational technology company that designs, "
            "develops, and sells computing hardware, software, and IT services. "
            "Revenue comes from PC sales, enterprise servers, storage, and cloud solutions."
        ),
        "motto": "Technologies that drive human progress",
        "industry": "Enterprise Technology",
        "sub_vertical": "Computer Hardware & Services",
        "is_public": True,
        "ticker": "DELL",
        "parent_company": None,
        "revenue_estimate": 88400000000.0,
        "revenue_source": "SEC 10-K FY2025",
        "executives": [_make_executive()],
        "competitors": [_make_competitor()],
        "recent_news": [_make_news_item()],
        "recent_blog_posts": [_make_blog_post()],
        "has_search_bar": True,
        "product_categories": ["Laptops", "Desktops", "Servers", "Storage"],
        "search_experience_description": "Basic keyword search with category filtering",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# CompanyInput
# ---------------------------------------------------------------------------


class TestCompanyInput:
    def test_valid_input(self) -> None:
        inp = CompanyInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CompanyInput(domain="dell.com", extra_field="nope")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Executive
# ---------------------------------------------------------------------------


class TestExecutive:
    def test_valid_executive(self) -> None:
        exec_data = _make_executive()
        exc = Executive.model_validate(exec_data)
        assert exc.full_name == "Michael Dell"
        assert exc.relevance == "economic_buyer"

    @pytest.mark.parametrize(
        "relevance",
        ["economic_buyer", "technical_evaluator", "champion_candidate", "influencer", "other"],
    )
    def test_all_relevance_values(self, relevance: str) -> None:
        exc = Executive.model_validate(_make_executive(relevance=relevance))
        assert exc.relevance == relevance

    def test_invalid_relevance_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Executive.model_validate(_make_executive(relevance="boss"))

    def test_defaults_to_other(self) -> None:
        data = {"full_name": "Jane Doe", "title": "VP Marketing"}
        exc = Executive.model_validate(data)
        assert exc.relevance == "other"
        assert exc.linkedin_url is None

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            Executive.model_validate({**_make_executive(), "salary": 1000000})


# ---------------------------------------------------------------------------
# Competitor
# ---------------------------------------------------------------------------


class TestCompetitor:
    def test_valid_competitor(self) -> None:
        comp = Competitor.model_validate(_make_competitor())
        assert comp.company_name == "HP Inc."
        assert comp.is_algolia_customer is False

    @pytest.mark.parametrize("size", ["larger", "smaller", "similar", "unknown"])
    def test_all_relative_size_values(self, size: str) -> None:
        comp = Competitor.model_validate(_make_competitor(relative_size=size))
        assert comp.relative_size == size

    def test_invalid_size_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Competitor.model_validate(_make_competitor(relative_size="huge"))

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            Competitor.model_validate({**_make_competitor(), "market_cap": 999})


# ---------------------------------------------------------------------------
# NewsItem
# ---------------------------------------------------------------------------


class TestNewsItem:
    def test_valid_news_item(self) -> None:
        item = NewsItem.model_validate(_make_news_item())
        assert item.headline == "Dell Reports Record Q4 Revenue"
        assert item.category == "financial"

    @pytest.mark.parametrize(
        "category",
        [
            "leadership_change",
            "product_launch",
            "partnership",
            "financial",
            "acquisition",
            "technology",
            "other",
        ],
    )
    def test_all_category_values(self, category: str) -> None:
        item = NewsItem.model_validate(_make_news_item(category=category))
        assert item.category == category

    def test_invalid_category_rejected(self) -> None:
        with pytest.raises(ValidationError):
            NewsItem.model_validate(_make_news_item(category="gossip"))

    def test_defaults(self) -> None:
        item = NewsItem.model_validate({"headline": "Test", "source": "X", "date": "2026-01-01"})
        assert item.category == "other"
        assert item.url is None


# ---------------------------------------------------------------------------
# BlogPost
# ---------------------------------------------------------------------------


class TestBlogPost:
    def test_valid_blog_post(self) -> None:
        post = BlogPost.model_validate(_make_blog_post())
        assert post.title == "Introducing Dell AI Factory"

    def test_defaults(self) -> None:
        post = BlogPost.model_validate({"title": "Test", "date": "2026-01-01"})
        assert post.summary == ""
        assert post.url is None


# ---------------------------------------------------------------------------
# CompanyProfileOutput
# ---------------------------------------------------------------------------


class TestCompanyProfileOutput:
    def test_valid_full_output(self) -> None:
        output = CompanyProfileOutput.model_validate(_make_full_output())
        assert output.legal_name == "Dell Technologies Inc."
        assert output.is_public is True
        assert output.ticker == "DELL"
        assert len(output.executives) == 1
        assert len(output.competitors) == 1
        assert len(output.recent_news) == 1
        assert output.has_search_bar is True

    def test_minimal_defaults(self) -> None:
        """CompanyProfileOutput with only required fields."""
        output = CompanyProfileOutput(
            legal_name="Test Corp",
            common_name="Test",
            domain="test.com",
            headquarters="San Francisco, CA, USA",
            business_model=(
                "Test Corp sells software as a service to enterprise"
                " customers, generating recurring subscription revenue."
            ),
            industry="SaaS",
        )
        assert output.executives == []
        assert output.competitors == []
        assert output.recent_news == []
        assert output.has_search_bar is None
        assert output.is_public is False
        assert output.revenue_estimate is None

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CompanyProfileOutput.model_validate({**_make_full_output(), "secret_field": "no"})

    def test_revenue_must_be_float(self) -> None:
        """Revenue should be a float, not a string like '$88.4B'."""
        output = CompanyProfileOutput.model_validate(
            _make_full_output(revenue_estimate=88400000000.0)
        )
        assert isinstance(output.revenue_estimate, float)
        assert output.revenue_estimate == 88400000000.0

    def test_employee_count_must_be_int(self) -> None:
        output = CompanyProfileOutput.model_validate(_make_full_output(employee_count=133000))
        assert isinstance(output.employee_count, int)

    def test_nested_model_validation(self) -> None:
        """Ensure nested models (Executive, Competitor, etc.) are validated."""
        bad_data = _make_full_output()
        bad_data["executives"] = [{"full_name": "X", "title": "Y", "relevance": "INVALID"}]
        with pytest.raises(ValidationError):
            CompanyProfileOutput.model_validate(bad_data)
