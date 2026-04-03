"""Contract tests for intel-social schemas.

Validates Pydantic models accept valid data, reject invalid data,
and enforce all constraints specified in the module spec.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.intel_social.schemas import (
    CompetitorSocial,
    ExecutiveQuote,
    SocialInput,
    SocialOutput,
    SocialPost,
    TwitterActivity,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_post(**overrides: object) -> dict:
    """Build a valid SocialPost dict with optional overrides."""
    base: dict = {
        "author_name": "Michael Dell",
        "author_title": "Chairman and CEO",
        "company_name": "Dell Technologies",
        "platform": "linkedin",
        "content_summary": (
            "Excited about our AI-powered solutions driving enterprise transformation in 2026."
        ),
        "date": "2026-03-10",
        "url": "https://linkedin.com/posts/michael-dell-123",
        "engagement_likes": 1500,
        "engagement_comments": 200,
        "topic": "ai_related",
        "algolia_relevance": "medium",
        "quotable_statement": "AI is not just a trend, it's a transformation.",
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
        "topic": "search_related",
        "algolia_relevance": "high",
        "sales_angle": "Direct mention of search and discovery investment",
    }
    base.update(overrides)
    return base


def _make_competitor_social(**overrides: object) -> dict:
    """Build a valid CompetitorSocial dict with optional overrides."""
    base: dict = {
        "company_name": "HP Inc.",
        "domain": "hp.com",
        "posts": [
            _make_post(
                author_name="Enrique Lores",
                company_name="HP Inc.",
                content_summary="HP launches next-gen AI PCs for enterprise.",
            )
        ],
        "exec_quotes": [],
        "key_finding": "HP focusing on AI PC hardware rather than software search.",
    }
    base.update(overrides)
    return base


def _make_twitter_activity(**overrides: object) -> dict:
    """Build a valid TwitterActivity dict with optional overrides."""
    base: dict = {
        "company_name": "Dell Technologies",
        "is_active": True,
        "recent_posts": [
            _make_post(platform="twitter", content_summary="Dell announces new AI server line.")
        ],
        "summary": "Dell active on Twitter/X, primarily sharing AI and server announcements.",
    }
    base.update(overrides)
    return base


def _make_full_output(**overrides: object) -> dict:
    """Build a valid SocialOutput dict with optional overrides."""
    base: dict = {
        "domain": "dell.com",
        "prospect_posts": [_make_post()],
        "prospect_exec_quotes": [_make_exec_quote()],
        "high_relevance_count": 1,
        "medium_relevance_count": 1,
        "most_quotable": [
            "AI is not just a trend, it's a transformation.",
            "We are investing heavily in AI-powered search.",
        ],
        "twitter_activity": _make_twitter_activity(),
        "competitor_social": [_make_competitor_social()],
        "competitive_comparison": (
            "Dell execs focus on AI and search investment while HP emphasizes AI hardware."
        ),
        "social_summary": (
            "Dell executives are actively signaling AI and search investment. "
            "Michael Dell's CES keynote directly mentioned discovery experiences."
        ),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# SocialInput
# ---------------------------------------------------------------------------


class TestSocialInput:
    """Tests for the SocialInput schema."""

    def test_valid_input(self) -> None:
        """SocialInput accepts a valid domain string."""
        inp = SocialInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        """SocialInput rejects extra fields due to extra='forbid'."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            SocialInput(domain="dell.com", extra_field="nope")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# SocialPost
# ---------------------------------------------------------------------------


class TestSocialPost:
    """Tests for the SocialPost schema."""

    def test_valid_post(self) -> None:
        """SocialPost accepts valid data."""
        post = SocialPost.model_validate(_make_post())
        assert post.author_name == "Michael Dell"
        assert post.platform == "linkedin"
        assert post.topic == "ai_related"
        assert post.algolia_relevance == "medium"
        assert post.engagement_likes == 1500

    @pytest.mark.parametrize(
        "platform",
        ["linkedin", "twitter", "youtube", "conference", "podcast", "interview", "other"],
    )
    def test_all_platform_values(self, platform: str) -> None:
        """SocialPost accepts all valid platform values."""
        post = SocialPost.model_validate(_make_post(platform=platform))
        assert post.platform == platform

    def test_invalid_platform_rejected(self) -> None:
        """SocialPost rejects invalid platform values."""
        with pytest.raises(ValidationError):
            SocialPost.model_validate(_make_post(platform="facebook"))

    @pytest.mark.parametrize(
        "topic",
        [
            "digital_strategy",
            "technology_investment",
            "customer_experience",
            "search_related",
            "ai_related",
            "hiring",
            "culture",
            "product_launch",
            "competitive",
            "other",
        ],
    )
    def test_all_topic_values(self, topic: str) -> None:
        """SocialPost accepts all valid topic values."""
        post = SocialPost.model_validate(_make_post(topic=topic))
        assert post.topic == topic

    def test_invalid_topic_rejected(self) -> None:
        """SocialPost rejects invalid topic values."""
        with pytest.raises(ValidationError):
            SocialPost.model_validate(_make_post(topic="gossip"))

    @pytest.mark.parametrize("relevance", ["high", "medium", "low"])
    def test_all_relevance_values(self, relevance: str) -> None:
        """SocialPost accepts all valid algolia_relevance values."""
        post = SocialPost.model_validate(_make_post(algolia_relevance=relevance))
        assert post.algolia_relevance == relevance

    def test_invalid_relevance_rejected(self) -> None:
        """SocialPost rejects invalid algolia_relevance values."""
        with pytest.raises(ValidationError):
            SocialPost.model_validate(_make_post(algolia_relevance="critical"))

    def test_defaults(self) -> None:
        """SocialPost applies correct defaults for optional fields."""
        post = SocialPost.model_validate(
            {
                "author_name": "Jane Doe",
                "content_summary": "A post about technology.",
            }
        )
        assert post.platform == "other"
        assert post.topic == "other"
        assert post.algolia_relevance == "low"
        assert post.author_title == ""
        assert post.company_name == ""
        assert post.date == ""
        assert post.url is None
        assert post.engagement_likes is None
        assert post.engagement_comments is None
        assert post.quotable_statement is None

    def test_rejects_extra_fields(self) -> None:
        """SocialPost rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            SocialPost.model_validate({**_make_post(), "sentiment": "positive"})


# ---------------------------------------------------------------------------
# ExecutiveQuote
# ---------------------------------------------------------------------------


class TestExecutiveQuote:
    """Tests for the ExecutiveQuote schema."""

    def test_valid_quote(self) -> None:
        """ExecutiveQuote accepts valid data."""
        quote = ExecutiveQuote.model_validate(_make_exec_quote())
        assert quote.executive_name == "Michael Dell"
        assert quote.source_type == "keynote"
        assert quote.topic == "search_related"
        assert quote.algolia_relevance == "high"

    @pytest.mark.parametrize(
        "source_type",
        ["keynote", "conference", "podcast", "interview", "webinar", "article", "youtube", "other"],
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
        "topic",
        [
            "digital_strategy",
            "technology_investment",
            "customer_experience",
            "search_related",
            "ai_related",
            "competitive_positioning",
            "growth_commitment",
            "cost_optimization",
            "other",
        ],
    )
    def test_all_topic_values(self, topic: str) -> None:
        """ExecutiveQuote accepts all valid topic values."""
        quote = ExecutiveQuote.model_validate(_make_exec_quote(topic=topic))
        assert quote.topic == topic

    def test_invalid_topic_rejected(self) -> None:
        """ExecutiveQuote rejects invalid topic values."""
        with pytest.raises(ValidationError):
            ExecutiveQuote.model_validate(_make_exec_quote(topic="random"))

    @pytest.mark.parametrize("relevance", ["high", "medium", "low"])
    def test_all_relevance_values(self, relevance: str) -> None:
        """ExecutiveQuote accepts all valid algolia_relevance values."""
        quote = ExecutiveQuote.model_validate(_make_exec_quote(algolia_relevance=relevance))
        assert quote.algolia_relevance == relevance

    def test_defaults(self) -> None:
        """ExecutiveQuote applies correct defaults."""
        quote = ExecutiveQuote.model_validate(
            {
                "executive_name": "Jane Doe",
                "executive_title": "CTO",
                "company_name": "TestCo",
                "quote": "We are investing in search.",
                "context": "Interview",
            }
        )
        assert quote.source_type == "other"
        assert quote.topic == "other"
        assert quote.algolia_relevance == "low"
        assert quote.date == ""
        assert quote.source_url is None
        assert quote.sales_angle is None

    def test_rejects_extra_fields(self) -> None:
        """ExecutiveQuote rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ExecutiveQuote.model_validate({**_make_exec_quote(), "mood": "optimistic"})


# ---------------------------------------------------------------------------
# CompetitorSocial
# ---------------------------------------------------------------------------


class TestCompetitorSocial:
    """Tests for the CompetitorSocial schema."""

    def test_valid_competitor_social(self) -> None:
        """CompetitorSocial accepts valid data."""
        cs = CompetitorSocial.model_validate(_make_competitor_social())
        assert cs.company_name == "HP Inc."
        assert cs.domain == "hp.com"
        assert len(cs.posts) == 1
        assert cs.key_finding != ""

    def test_defaults(self) -> None:
        """CompetitorSocial has empty lists and string as defaults."""
        cs = CompetitorSocial(company_name="Test", domain="test.com")
        assert cs.posts == []
        assert cs.exec_quotes == []
        assert cs.key_finding == ""

    def test_rejects_extra_fields(self) -> None:
        """CompetitorSocial rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CompetitorSocial.model_validate({**_make_competitor_social(), "market_share": 0.15})


# ---------------------------------------------------------------------------
# TwitterActivity
# ---------------------------------------------------------------------------


class TestTwitterActivity:
    """Tests for the TwitterActivity schema."""

    def test_valid_twitter_activity(self) -> None:
        """TwitterActivity accepts valid data."""
        ta = TwitterActivity.model_validate(_make_twitter_activity())
        assert ta.company_name == "Dell Technologies"
        assert ta.is_active is True
        assert len(ta.recent_posts) == 1
        assert ta.summary != ""

    def test_defaults(self) -> None:
        """TwitterActivity has correct defaults."""
        ta = TwitterActivity(company_name="TestCo")
        assert ta.is_active is False
        assert ta.recent_posts == []
        assert ta.summary == ""

    def test_rejects_extra_fields(self) -> None:
        """TwitterActivity rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            TwitterActivity.model_validate({**_make_twitter_activity(), "follower_count": 100000})


# ---------------------------------------------------------------------------
# SocialOutput
# ---------------------------------------------------------------------------


class TestSocialOutput:
    """Tests for the SocialOutput schema."""

    def test_valid_full_output(self) -> None:
        """SocialOutput accepts a complete valid output."""
        output = SocialOutput.model_validate(_make_full_output())
        assert output.domain == "dell.com"
        assert len(output.prospect_posts) == 1
        assert len(output.prospect_exec_quotes) == 1
        assert output.high_relevance_count == 1
        assert output.medium_relevance_count == 1
        assert len(output.most_quotable) == 2
        assert output.twitter_activity is not None
        assert len(output.competitor_social) == 1
        assert output.social_summary != ""

    def test_minimal_defaults(self) -> None:
        """SocialOutput with only required field (domain)."""
        output = SocialOutput(domain="test.com")
        assert output.prospect_posts == []
        assert output.prospect_exec_quotes == []
        assert output.high_relevance_count == 0
        assert output.medium_relevance_count == 0
        assert output.most_quotable == []
        assert output.twitter_activity is None
        assert output.competitor_social == []
        assert output.competitive_comparison == ""
        assert output.social_summary == ""

    def test_rejects_extra_fields(self) -> None:
        """SocialOutput rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            SocialOutput.model_validate({**_make_full_output(), "secret_field": "no"})

    def test_nested_post_validation(self) -> None:
        """SocialOutput validates nested social posts."""
        bad_data = _make_full_output()
        bad_data["prospect_posts"] = [
            {
                "author_name": "Test",
                "content_summary": "Test",
                "platform": "INVALID",
            }
        ]
        with pytest.raises(ValidationError):
            SocialOutput.model_validate(bad_data)

    def test_nested_quote_validation(self) -> None:
        """SocialOutput validates nested exec quotes."""
        bad_data = _make_full_output()
        bad_data["prospect_exec_quotes"] = [
            {
                "executive_name": "Jane",
                "executive_title": "CEO",
                "company_name": "Test",
                "quote": "Test",
                "context": "Test",
                "source_type": "INVALID",
            }
        ]
        with pytest.raises(ValidationError):
            SocialOutput.model_validate(bad_data)

    def test_nested_twitter_validation(self) -> None:
        """SocialOutput validates nested twitter activity."""
        bad_data = _make_full_output()
        bad_data["twitter_activity"] = {"company_name": "Test", "extra_field": "bad"}
        with pytest.raises(ValidationError):
            SocialOutput.model_validate(bad_data)

    def test_high_relevance_count_is_int(self) -> None:
        """high_relevance_count must be an integer."""
        output = SocialOutput.model_validate(_make_full_output(high_relevance_count=3))
        assert isinstance(output.high_relevance_count, int)

    def test_medium_relevance_count_is_int(self) -> None:
        """medium_relevance_count must be an integer."""
        output = SocialOutput.model_validate(_make_full_output(medium_relevance_count=2))
        assert isinstance(output.medium_relevance_count, int)

    def test_twitter_activity_optional(self) -> None:
        """SocialOutput allows twitter_activity to be None."""
        output = SocialOutput.model_validate(_make_full_output(twitter_activity=None))
        assert output.twitter_activity is None
