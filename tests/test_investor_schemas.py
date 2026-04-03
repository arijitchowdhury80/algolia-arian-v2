"""Contract tests for intel-investor schemas.

Validates Pydantic models accept valid data, reject invalid data,
and enforce all constraints for investor intelligence output.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.intel_investor.schemas import (
    BoardMember,
    CompetitorInvestorIntel,
    EarningsQuote,
    InvestorInput,
    InvestorOutput,
    RiskFactor,
    SaidVsFound,
    YouTubeAppearance,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_earnings_quote(**overrides: object) -> dict:
    """Build a valid EarningsQuote dict with optional overrides."""
    base: dict[str, object] = {
        "speaker_name": "Michael Dell",
        "speaker_title": "CEO",
        "quote": "Digital transformation is our top priority for the next fiscal year.",
        "context": "Opening remarks on strategic priorities",
        "quarter": "Q4 FY2025",
        "source": "Q4 FY2025 Earnings Call Transcript",
        "source_url": "https://seekingalpha.com/article/dell-q4-2025-earnings",
        "category": "digital_investment",
        "dollar_amount": "$2B in digital transformation",
        "is_commitment": True,
        "urgency_level": "high",
    }
    base.update(overrides)
    return base


def _make_said_vs_found(**overrides: object) -> dict:
    """Build a valid SaidVsFound dict with optional overrides."""
    base: dict[str, object] = {
        "executive_quote": _make_earnings_quote(),
        "algolia_angle": (
            "CEO's digital transformation commitment validates Algolia search/discovery "
            "investment conversation at the C-level."
        ),
        "recommended_talking_point": (
            "Michael Dell said digital transformation is the top priority. "
            "Algolia powers the search and discovery layer that makes digital "
            "transformation visible to customers."
        ),
        "product_relevance": ["Algolia Search", "Algolia AI Search"],
        "confidence": "high",
    }
    base.update(overrides)
    return base


def _make_competitor_intel(**overrides: object) -> dict:
    """Build a valid CompetitorInvestorIntel dict with optional overrides."""
    base: dict[str, object] = {
        "company_name": "HP Inc.",
        "ticker": "HPQ",
        "domain": "hp.com",
        "key_quotes": [_make_earnings_quote(speaker_name="Enrique Lores", speaker_title="CEO")],
        "competitive_ammunition": [
            "HP's CEO highlighted AI-powered search driving engagement -- "
            "Dell is falling behind on this front."
        ],
    }
    base.update(overrides)
    return base


def _make_board_member(**overrides: object) -> dict:
    """Build a valid BoardMember dict with optional overrides."""
    base: dict[str, object] = {
        "name": "Marc Benioff",
        "title": "Independent Director",
        "background": "CEO of Salesforce, pioneer in cloud computing and CRM.",
        "has_tech_background": True,
        "relevance_note": "Former Salesforce CEO -- likely champion for modern search technology.",
    }
    base.update(overrides)
    return base


def _make_risk_factor(**overrides: object) -> dict:
    """Build a valid RiskFactor dict with optional overrides."""
    base: dict[str, object] = {
        "category": "technology",
        "excerpt": (
            "Our legacy search infrastructure may not scale to meet "
            "increasing customer expectations for real-time results."
        ),
        "filing_source": "10-K FY2025",
        "algolia_relevance": (
            "Legacy search infrastructure risk -- Algolia can modernize "
            "without a full platform migration."
        ),
    }
    base.update(overrides)
    return base


def _make_youtube_appearance(**overrides: object) -> dict:
    """Build a valid YouTubeAppearance dict with optional overrides."""
    base: dict[str, object] = {
        "title": "Dell Technologies World 2025 Keynote",
        "channel": "Dell Technologies",
        "date": "2025-05-15",
        "url": "https://youtube.com/watch?v=abc123",
        "speaker": "Michael Dell",
        "key_topics": ["AI infrastructure", "Digital transformation"],
        "key_quotes": ["AI is the defining technology of our generation."],
    }
    base.update(overrides)
    return base


def _make_full_output(**overrides: object) -> dict:
    """Build a valid InvestorOutput dict with optional overrides."""
    base: dict[str, object] = {
        "domain": "dell.com",
        "ticker": "DELL",
        "prospect_quotes": [
            _make_earnings_quote(),
            _make_earnings_quote(
                speaker_name="Jeff Clarke",
                speaker_title="COO",
                quote="Our platform modernization is ahead of schedule.",
                category="platform_modernization",
                is_commitment=False,
                urgency_level="medium",
            ),
        ],
        "commitment_count": 1,
        "pain_signal_count": 0,
        "said_vs_found": [_make_said_vs_found()],
        "competitor_intel": [_make_competitor_intel()],
        "youtube_appearances": [_make_youtube_appearance()],
        "board_members": [
            _make_board_member(),
            _make_board_member(
                name="Jane Smith",
                title="Board Chair",
                has_tech_background=False,
                background="Former CFO of General Electric",
                relevance_note="",
            ),
        ],
        "board_tech_count": 1,
        "risk_factors": [_make_risk_factor()],
        "investor_summary": (
            "Dell's CEO has publicly committed to digital transformation as the top priority, "
            "with $2B allocated. Board includes tech-savvy directors. The 10-K reveals legacy "
            "search infrastructure as a risk factor."
        ),
        "top_sales_angles": [
            "CEO committed $2B to digital transformation -- Algolia powers the visible layer.",
            "10-K reveals legacy search risk -- position Algolia as modern replacement.",
            "Competitor HP already invested in AI search and saw results.",
        ],
        "skipped": False,
        "skip_reason": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# InvestorInput
# ---------------------------------------------------------------------------


class TestInvestorInput:
    """Tests for InvestorInput schema."""

    def test_valid_input(self) -> None:
        """Valid input should be accepted."""
        inp = InvestorInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            InvestorInput(domain="dell.com", extra="nope")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# EarningsQuote
# ---------------------------------------------------------------------------


class TestEarningsQuote:
    """Tests for EarningsQuote schema."""

    def test_valid_quote(self) -> None:
        """Valid quote should be accepted."""
        q = EarningsQuote.model_validate(_make_earnings_quote())
        assert q.speaker_name == "Michael Dell"
        assert q.is_commitment is True
        assert q.category == "digital_investment"
        assert q.urgency_level == "high"

    def test_defaults(self) -> None:
        """Defaults should be set for optional fields."""
        q = EarningsQuote(
            speaker_name="Test",
            speaker_title="CEO",
            quote="Test quote",
            context="Test context",
            quarter="Q1 FY2026",
            source="Q1 FY2026 Earnings Call Transcript",
        )
        assert q.source_url is None
        assert q.category == "other"
        assert q.dollar_amount is None
        assert q.is_commitment is False
        assert q.urgency_level == "low"

    def test_invalid_category(self) -> None:
        """Invalid category should be rejected."""
        with pytest.raises(ValidationError):
            EarningsQuote.model_validate(_make_earnings_quote(category="invalid_category"))

    def test_invalid_urgency(self) -> None:
        """Invalid urgency level should be rejected."""
        with pytest.raises(ValidationError):
            EarningsQuote.model_validate(_make_earnings_quote(urgency_level="critical"))

    def test_rejects_extra_fields(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            EarningsQuote.model_validate({**_make_earnings_quote(), "sentiment": "positive"})


# ---------------------------------------------------------------------------
# SaidVsFound
# ---------------------------------------------------------------------------


class TestSaidVsFound:
    """Tests for SaidVsFound schema."""

    def test_valid_mapping(self) -> None:
        """Valid mapping should be accepted."""
        svf = SaidVsFound.model_validate(_make_said_vs_found())
        assert svf.executive_quote.speaker_name == "Michael Dell"
        assert "Algolia" in svf.algolia_angle
        assert len(svf.product_relevance) == 2
        assert svf.confidence == "high"

    def test_defaults(self) -> None:
        """Defaults should be set for optional fields."""
        svf = SaidVsFound(
            executive_quote=EarningsQuote.model_validate(_make_earnings_quote()),
            algolia_angle="Test angle",
            recommended_talking_point="Test talking point",
        )
        assert svf.product_relevance == []
        assert svf.confidence == "medium"

    def test_invalid_confidence(self) -> None:
        """Invalid confidence should be rejected."""
        with pytest.raises(ValidationError):
            SaidVsFound.model_validate(_make_said_vs_found(confidence="very_high"))

    def test_rejects_extra_fields(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            SaidVsFound.model_validate({**_make_said_vs_found(), "score": 9.5})


# ---------------------------------------------------------------------------
# CompetitorInvestorIntel
# ---------------------------------------------------------------------------


class TestCompetitorInvestorIntel:
    """Tests for CompetitorInvestorIntel schema."""

    def test_valid_intel(self) -> None:
        """Valid competitor intel should be accepted."""
        ci = CompetitorInvestorIntel.model_validate(_make_competitor_intel())
        assert ci.company_name == "HP Inc."
        assert ci.ticker == "HPQ"
        assert len(ci.key_quotes) == 1
        assert len(ci.competitive_ammunition) == 1

    def test_defaults(self) -> None:
        """Defaults should be set for optional fields."""
        ci = CompetitorInvestorIntel(company_name="Test Corp", domain="test.com")
        assert ci.ticker is None
        assert ci.key_quotes == []
        assert ci.competitive_ammunition == []

    def test_rejects_extra_fields(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CompetitorInvestorIntel.model_validate(
                {**_make_competitor_intel(), "market_cap": 50000000000}
            )


# ---------------------------------------------------------------------------
# BoardMember
# ---------------------------------------------------------------------------


class TestBoardMember:
    """Tests for BoardMember schema."""

    def test_valid_board_member(self) -> None:
        """Valid board member should be accepted."""
        bm = BoardMember.model_validate(_make_board_member())
        assert bm.name == "Marc Benioff"
        assert bm.has_tech_background is True

    def test_defaults(self) -> None:
        """Defaults should be set for optional fields."""
        bm = BoardMember(name="Test Person", title="Director")
        assert bm.background == ""
        assert bm.has_tech_background is False
        assert bm.relevance_note == ""

    def test_rejects_extra_fields(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            BoardMember.model_validate({**_make_board_member(), "age": 60})


# ---------------------------------------------------------------------------
# RiskFactor
# ---------------------------------------------------------------------------


class TestRiskFactor:
    """Tests for RiskFactor schema."""

    def test_valid_risk_factor(self) -> None:
        """Valid risk factor should be accepted."""
        rf = RiskFactor.model_validate(_make_risk_factor())
        assert rf.category == "technology"
        assert rf.filing_source == "10-K FY2025"
        assert "Algolia" in rf.algolia_relevance

    def test_invalid_category(self) -> None:
        """Invalid category should be rejected."""
        with pytest.raises(ValidationError):
            RiskFactor.model_validate(_make_risk_factor(category="financial_risk"))

    def test_defaults(self) -> None:
        """Defaults should be set for optional fields."""
        rf = RiskFactor(excerpt="Test excerpt", filing_source="10-K FY2025")
        assert rf.category == "other"
        assert rf.algolia_relevance == ""

    def test_rejects_extra_fields(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            RiskFactor.model_validate({**_make_risk_factor(), "severity": "high"})


# ---------------------------------------------------------------------------
# YouTubeAppearance
# ---------------------------------------------------------------------------


class TestYouTubeAppearance:
    """Tests for YouTubeAppearance schema."""

    def test_valid_appearance(self) -> None:
        """Valid appearance should be accepted."""
        yt = YouTubeAppearance.model_validate(_make_youtube_appearance())
        assert yt.title == "Dell Technologies World 2025 Keynote"
        assert yt.speaker == "Michael Dell"
        assert len(yt.key_topics) == 2

    def test_defaults(self) -> None:
        """Defaults should be set for optional fields."""
        yt = YouTubeAppearance(title="Test Video")
        assert yt.channel == ""
        assert yt.date == ""
        assert yt.url is None
        assert yt.speaker == ""
        assert yt.key_topics == []
        assert yt.key_quotes == []

    def test_rejects_extra_fields(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            YouTubeAppearance.model_validate({**_make_youtube_appearance(), "views": 100000})


# ---------------------------------------------------------------------------
# InvestorOutput
# ---------------------------------------------------------------------------


class TestInvestorOutput:
    """Tests for InvestorOutput schema."""

    def test_valid_full_output(self) -> None:
        """Valid full output should be accepted."""
        output = InvestorOutput.model_validate(_make_full_output())
        assert output.domain == "dell.com"
        assert output.ticker == "DELL"
        assert len(output.prospect_quotes) == 2
        assert output.commitment_count == 1
        assert output.pain_signal_count == 0
        assert len(output.said_vs_found) == 1
        assert len(output.competitor_intel) == 1
        assert len(output.youtube_appearances) == 1
        assert len(output.board_members) == 2
        assert output.board_tech_count == 1
        assert len(output.risk_factors) == 1
        assert output.investor_summary != ""
        assert len(output.top_sales_angles) == 3
        assert output.skipped is False

    def test_minimal_defaults(self) -> None:
        """Minimal output with defaults should be accepted."""
        output = InvestorOutput(domain="dell.com")
        assert output.ticker is None
        assert output.prospect_quotes == []
        assert output.commitment_count == 0
        assert output.pain_signal_count == 0
        assert output.said_vs_found == []
        assert output.competitor_intel == []
        assert output.youtube_appearances == []
        assert output.board_members == []
        assert output.board_tech_count == 0
        assert output.risk_factors == []
        assert output.investor_summary == ""
        assert output.top_sales_angles == []
        assert output.skipped is False
        assert output.skip_reason is None

    def test_skipped_output(self) -> None:
        """Skipped output should be accepted."""
        output = InvestorOutput(
            domain="private.com",
            skipped=True,
            skip_reason="No public data available",
        )
        assert output.skipped is True
        assert output.skip_reason == "No public data available"

    def test_rejects_extra_fields(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            InvestorOutput.model_validate({**_make_full_output(), "secret_field": "no"})

    def test_nested_model_validation(self) -> None:
        """Invalid nested model data should fail validation."""
        bad_data = _make_full_output()
        bad_data["prospect_quotes"] = [{**_make_earnings_quote(), "category": "invalid_category"}]
        with pytest.raises(ValidationError):
            InvestorOutput.model_validate(bad_data)

    def test_private_company_output(self) -> None:
        """Output for private company (no ticker) should be valid."""
        output = InvestorOutput(
            domain="stripe.com",
            ticker=None,
            prospect_quotes=[
                EarningsQuote.model_validate(
                    _make_earnings_quote(
                        speaker_name="Patrick Collison",
                        speaker_title="CEO",
                        source="TechCrunch Disrupt 2025 Interview",
                        quarter="",
                    )
                )
            ],
            commitment_count=0,
            pain_signal_count=0,
        )
        assert output.domain == "stripe.com"
        assert output.ticker is None
        assert len(output.prospect_quotes) == 1
