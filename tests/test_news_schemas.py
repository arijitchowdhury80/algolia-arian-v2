"""Contract tests for intel-news schemas.

Validates Pydantic models accept valid data, reject invalid data,
and enforce all constraints specified in the module spec.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.intel_news.schemas import (
    CompetitorNews,
    ExecutiveQuote,
    NewsArticle,
    NewsInput,
    NewsOutput,
    UrgencySignal,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_article(**overrides: object) -> dict:
    """Build a valid NewsArticle dict with optional overrides."""
    base: dict = {
        "headline": "Dell Reports Record Q4 Revenue Driven by AI Demand",
        "source": "Reuters",
        "date": "2026-02-15",
        "url": "https://reuters.com/dell-q4-2026",
        "summary": (
            "Dell Technologies reported record Q4 revenue "
            "of $24.5B, driven by strong AI server demand."
        ),
        "category": "financial",
        "is_sell_signal": False,
        "sell_signal_reason": None,
        "urgency": "low",
        "urgency_reason": None,
        "company_name": "Dell Technologies",
    }
    base.update(overrides)
    return base


def _make_exec_quote(**overrides: object) -> dict:
    """Build a valid ExecutiveQuote dict with optional overrides."""
    base: dict = {
        "executive_name": "Michael Dell",
        "executive_title": "Chairman and CEO",
        "company_name": "Dell Technologies",
        "quote": (
            "We are investing heavily in AI-powered search "
            "and discovery experiences for our customers."
        ),
        "context": "CES 2026 keynote address",
        "source_type": "keynote",
        "source_url": "https://ces.tech/2026/keynotes/dell",
        "date": "2026-01-07",
        "classification": "technology_strategy",
        "is_high_value": True,
        "algolia_angle": "Direct mention of search and discovery investment",
    }
    base.update(overrides)
    return base


def _make_urgency_signal(**overrides: object) -> dict:
    """Build a valid UrgencySignal dict with optional overrides."""
    base: dict = {
        "signal_type": "exec_public_commitment",
        "description": "CEO publicly committed to digital transformation and AI investment in 2026",
        "urgency_level": "high",
        "source_headline": "Dell CEO Pledges $2B AI Investment",
        "date": "2026-01-15",
    }
    base.update(overrides)
    return base


def _make_competitor_news(**overrides: object) -> dict:
    """Build a valid CompetitorNews dict with optional overrides."""
    base: dict = {
        "company_name": "HP Inc.",
        "domain": "hp.com",
        "articles": [_make_article(company_name="HP Inc.", headline="HP Launches AI PCs")],
        "exec_quotes": [],
    }
    base.update(overrides)
    return base


def _make_full_output(**overrides: object) -> dict:
    """Build a valid NewsOutput dict with optional overrides."""
    base: dict = {
        "domain": "dell.com",
        "prospect_articles": [_make_article()],
        "prospect_exec_quotes": [_make_exec_quote()],
        "urgency_signals": [_make_urgency_signal()],
        "sell_signal_count": 0,
        "high_value_quote_count": 1,
        "competitor_news": [_make_competitor_news()],
        "competitive_comparison": "Dell is investing in AI servers while HP focuses on AI PCs.",
        "news_summary": (
            "Dell reported record revenue driven by AI demand. "
            "CEO committed to digital transformation."
        ),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# NewsInput
# ---------------------------------------------------------------------------


class TestNewsInput:
    """Tests for the NewsInput schema."""

    def test_valid_input(self) -> None:
        """NewsInput accepts a valid domain string."""
        inp = NewsInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        """NewsInput rejects extra fields due to extra='forbid'."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            NewsInput(domain="dell.com", extra_field="nope")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# NewsArticle
# ---------------------------------------------------------------------------


class TestNewsArticle:
    """Tests for the NewsArticle schema."""

    def test_valid_article(self) -> None:
        """NewsArticle accepts valid data."""
        article = NewsArticle.model_validate(_make_article())
        assert article.headline == "Dell Reports Record Q4 Revenue Driven by AI Demand"
        assert article.source == "Reuters"
        assert article.category == "financial"
        assert article.is_sell_signal is False
        assert article.company_name == "Dell Technologies"

    @pytest.mark.parametrize(
        "category",
        [
            "leadership_change",
            "product_launch",
            "partnership",
            "financial",
            "acquisition",
            "technology",
            "search_related",
            "digital_transformation",
            "other",
        ],
    )
    def test_all_category_values(self, category: str) -> None:
        """NewsArticle accepts all valid category values."""
        article = NewsArticle.model_validate(_make_article(category=category))
        assert article.category == category

    def test_invalid_category_rejected(self) -> None:
        """NewsArticle rejects invalid category values."""
        with pytest.raises(ValidationError):
            NewsArticle.model_validate(_make_article(category="gossip"))

    @pytest.mark.parametrize("urgency", ["high", "medium", "low"])
    def test_all_urgency_values(self, urgency: str) -> None:
        """NewsArticle accepts all valid urgency values."""
        article = NewsArticle.model_validate(_make_article(urgency=urgency))
        assert article.urgency == urgency

    def test_invalid_urgency_rejected(self) -> None:
        """NewsArticle rejects invalid urgency values."""
        with pytest.raises(ValidationError):
            NewsArticle.model_validate(_make_article(urgency="critical"))

    def test_defaults(self) -> None:
        """NewsArticle applies correct defaults for optional fields."""
        article = NewsArticle.model_validate(
            {
                "headline": "Test",
                "source": "TestPub",
                "date": "2026-01-01",
            }
        )
        assert article.category == "other"
        assert article.is_sell_signal is False
        assert article.urgency == "low"
        assert article.url is None
        assert article.summary == ""
        assert article.company_name == ""

    def test_sell_signal_with_reason(self) -> None:
        """NewsArticle allows sell signal with reason."""
        article = NewsArticle.model_validate(
            _make_article(
                is_sell_signal=True,
                sell_signal_reason="Mentions search technology migration",
                category="search_related",
            )
        )
        assert article.is_sell_signal is True
        assert article.sell_signal_reason is not None

    def test_rejects_extra_fields(self) -> None:
        """NewsArticle rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            NewsArticle.model_validate({**_make_article(), "sentiment": "positive"})


# ---------------------------------------------------------------------------
# ExecutiveQuote
# ---------------------------------------------------------------------------


class TestExecutiveQuote:
    """Tests for the ExecutiveQuote schema."""

    def test_valid_quote(self) -> None:
        """ExecutiveQuote accepts valid data."""
        quote = ExecutiveQuote.model_validate(_make_exec_quote())
        assert quote.executive_name == "Michael Dell"
        assert quote.is_high_value is True
        assert quote.classification == "technology_strategy"

    @pytest.mark.parametrize(
        "source_type",
        [
            "interview",
            "keynote",
            "podcast",
            "earnings_call",
            "conference",
            "press_release",
            "social_media",
            "article",
        ],
    )
    def test_all_source_type_values(self, source_type: str) -> None:
        """ExecutiveQuote accepts all valid source_type values."""
        quote = ExecutiveQuote.model_validate(_make_exec_quote(source_type=source_type))
        assert quote.source_type == source_type

    def test_invalid_source_type_rejected(self) -> None:
        """ExecutiveQuote rejects invalid source_type values."""
        with pytest.raises(ValidationError):
            ExecutiveQuote.model_validate(_make_exec_quote(source_type="rumor"))

    @pytest.mark.parametrize(
        "classification",
        [
            "digital_investment",
            "technology_strategy",
            "customer_experience",
            "search_related",
            "ai_related",
            "competitive_positioning",
            "growth_commitment",
            "cost_optimization",
            "other",
        ],
    )
    def test_all_classification_values(self, classification: str) -> None:
        """ExecutiveQuote accepts all valid classification values."""
        quote = ExecutiveQuote.model_validate(_make_exec_quote(classification=classification))
        assert quote.classification == classification

    def test_invalid_classification_rejected(self) -> None:
        """ExecutiveQuote rejects invalid classification values."""
        with pytest.raises(ValidationError):
            ExecutiveQuote.model_validate(_make_exec_quote(classification="random"))

    def test_defaults(self) -> None:
        """ExecutiveQuote applies correct defaults."""
        quote = ExecutiveQuote.model_validate(
            {
                "executive_name": "Jane Doe",
                "executive_title": "CTO",
                "company_name": "TestCo",
                "quote": "We are investing in search.",
                "context": "Interview",
                "source_type": "interview",
                "date": "2026-01-01",
            }
        )
        assert quote.classification == "other"
        assert quote.is_high_value is False
        assert quote.algolia_angle is None
        assert quote.source_url is None

    def test_rejects_extra_fields(self) -> None:
        """ExecutiveQuote rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ExecutiveQuote.model_validate({**_make_exec_quote(), "mood": "optimistic"})


# ---------------------------------------------------------------------------
# CompetitorNews
# ---------------------------------------------------------------------------


class TestCompetitorNews:
    """Tests for the CompetitorNews schema."""

    def test_valid_competitor_news(self) -> None:
        """CompetitorNews accepts valid data."""
        cn = CompetitorNews.model_validate(_make_competitor_news())
        assert cn.company_name == "HP Inc."
        assert cn.domain == "hp.com"
        assert len(cn.articles) == 1

    def test_defaults(self) -> None:
        """CompetitorNews has empty lists as defaults."""
        cn = CompetitorNews(company_name="Test", domain="test.com")
        assert cn.articles == []
        assert cn.exec_quotes == []

    def test_rejects_extra_fields(self) -> None:
        """CompetitorNews rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CompetitorNews.model_validate({**_make_competitor_news(), "market_share": 0.15})


# ---------------------------------------------------------------------------
# UrgencySignal
# ---------------------------------------------------------------------------


class TestUrgencySignal:
    """Tests for the UrgencySignal schema."""

    def test_valid_signal(self) -> None:
        """UrgencySignal accepts valid data."""
        signal = UrgencySignal.model_validate(_make_urgency_signal())
        assert signal.signal_type == "exec_public_commitment"
        assert signal.urgency_level == "high"

    @pytest.mark.parametrize("level", ["high", "medium", "low"])
    def test_all_urgency_levels(self, level: str) -> None:
        """UrgencySignal accepts all valid urgency_level values."""
        signal = UrgencySignal.model_validate(_make_urgency_signal(urgency_level=level))
        assert signal.urgency_level == level

    def test_invalid_urgency_level_rejected(self) -> None:
        """UrgencySignal rejects invalid urgency_level values."""
        with pytest.raises(ValidationError):
            UrgencySignal.model_validate(_make_urgency_signal(urgency_level="critical"))

    def test_rejects_extra_fields(self) -> None:
        """UrgencySignal rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            UrgencySignal.model_validate({**_make_urgency_signal(), "score": 95})


# ---------------------------------------------------------------------------
# NewsOutput
# ---------------------------------------------------------------------------


class TestNewsOutput:
    """Tests for the NewsOutput schema."""

    def test_valid_full_output(self) -> None:
        """NewsOutput accepts a complete valid output."""
        output = NewsOutput.model_validate(_make_full_output())
        assert output.domain == "dell.com"
        assert len(output.prospect_articles) == 1
        assert len(output.prospect_exec_quotes) == 1
        assert len(output.urgency_signals) == 1
        assert output.sell_signal_count == 0
        assert output.high_value_quote_count == 1
        assert len(output.competitor_news) == 1
        assert output.news_summary != ""

    def test_minimal_defaults(self) -> None:
        """NewsOutput with only required field (domain)."""
        output = NewsOutput(domain="test.com")
        assert output.prospect_articles == []
        assert output.prospect_exec_quotes == []
        assert output.urgency_signals == []
        assert output.sell_signal_count == 0
        assert output.high_value_quote_count == 0
        assert output.competitor_news == []
        assert output.competitive_comparison == ""
        assert output.news_summary == ""

    def test_rejects_extra_fields(self) -> None:
        """NewsOutput rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            NewsOutput.model_validate({**_make_full_output(), "secret_field": "no"})

    def test_nested_article_validation(self) -> None:
        """NewsOutput validates nested articles."""
        bad_data = _make_full_output()
        bad_data["prospect_articles"] = [
            {"headline": "Test", "source": "X", "date": "2026-01-01", "category": "INVALID"}
        ]
        with pytest.raises(ValidationError):
            NewsOutput.model_validate(bad_data)

    def test_nested_quote_validation(self) -> None:
        """NewsOutput validates nested exec quotes."""
        bad_data = _make_full_output()
        bad_data["prospect_exec_quotes"] = [
            {
                "executive_name": "Jane",
                "executive_title": "CEO",
                "company_name": "Test",
                "quote": "Test",
                "context": "Test",
                "source_type": "INVALID",
                "date": "2026-01-01",
            }
        ]
        with pytest.raises(ValidationError):
            NewsOutput.model_validate(bad_data)

    def test_nested_signal_validation(self) -> None:
        """NewsOutput validates nested urgency signals."""
        bad_data = _make_full_output()
        bad_data["urgency_signals"] = [
            {
                "signal_type": "test",
                "description": "test",
                "urgency_level": "INVALID",
                "source_headline": "test",
                "date": "2026-01-01",
            }
        ]
        with pytest.raises(ValidationError):
            NewsOutput.model_validate(bad_data)

    def test_sell_signal_count_is_int(self) -> None:
        """sell_signal_count must be an integer."""
        output = NewsOutput.model_validate(_make_full_output(sell_signal_count=3))
        assert isinstance(output.sell_signal_count, int)

    def test_high_value_quote_count_is_int(self) -> None:
        """high_value_quote_count must be an integer."""
        output = NewsOutput.model_validate(_make_full_output(high_value_quote_count=2))
        assert isinstance(output.high_value_quote_count, int)
