"""Contract tests for intel-hiring schemas.

Validates Pydantic models accept valid data, reject invalid data,
and enforce all constraints specified in the module spec.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.intel_hiring.schemas import (
    BuildVsBuySignal,
    BuyingCommittee,
    BuyingCommitteeMember,
    CompetitorHiring,
    HiringInput,
    HiringOutput,
    HiringVelocity,
    OpenRole,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_open_role(**overrides: object) -> dict:
    """Build a valid OpenRole dict with optional overrides."""
    base: dict = {
        "title": "Senior Search Engineer",
        "department": "Engineering",
        "location": "Austin, TX",
        "posted_date": "2026-03-15",
        "url": "https://linkedin.com/jobs/123",
        "icp_tier": "tier3_champion",
        "relevance_score": 0.85,
        "search_related": True,
        "signals": ["building search team", "Elasticsearch experience required"],
        "source": "linkedin",
        "company_name": "Dell Technologies",
    }
    base.update(overrides)
    return base


def _make_hiring_velocity(**overrides: object) -> dict:
    """Build a valid HiringVelocity dict with optional overrides."""
    base: dict = {
        "roles_last_30d": 12,
        "roles_last_90d": 35,
        "trend": "accelerating",
        "interpretation": "Dell is ramping up hiring in search and platform engineering.",
    }
    base.update(overrides)
    return base


def _make_build_vs_buy(**overrides: object) -> dict:
    """Build a valid BuildVsBuySignal dict with optional overrides."""
    base: dict = {
        "signal": "mixed",
        "evidence": [
            "Hiring search engineers (build signal)",
            "VP of Digital Commerce role open (buy signal)",
        ],
        "confidence": "medium",
    }
    base.update(overrides)
    return base


def _make_buying_committee_member(**overrides: object) -> dict:
    """Build a valid BuyingCommitteeMember dict with optional overrides."""
    base: dict = {
        "name": "Michael Dell",
        "title": "Chairman and CEO",
        "role": "economic_buyer",
        "linkedin_url": "https://linkedin.com/in/michaeldell",
        "tenure_description": "Since 1984",
        "previous_company": None,
        "champion_signals": [],
    }
    base.update(overrides)
    return base


def _make_buying_committee(**overrides: object) -> dict:
    """Build a valid BuyingCommittee dict with optional overrides."""
    base: dict = {
        "members": [_make_buying_committee_member()],
        "confidence": "medium",
        "methodology": "executive list + open roles + Perplexity enrichment",
    }
    base.update(overrides)
    return base


def _make_competitor_hiring(**overrides: object) -> dict:
    """Build a valid CompetitorHiring dict with optional overrides."""
    base: dict = {
        "company_name": "HP Inc.",
        "domain": "hp.com",
        "open_roles": [_make_open_role(company_name="HP Inc.", title="Search Platform Lead")],
        "search_related_count": 1,
        "hiring_velocity": None,
    }
    base.update(overrides)
    return base


def _make_full_output(**overrides: object) -> dict:
    """Build a valid HiringOutput dict with optional overrides."""
    base: dict = {
        "domain": "dell.com",
        "open_roles": [_make_open_role()],
        "role_count_by_tier": {"tier3_champion": 1},
        "search_related_count": 1,
        "hiring_velocity": _make_hiring_velocity(),
        "build_vs_buy": _make_build_vs_buy(),
        "buying_committee": _make_buying_committee(),
        "competitor_hiring": [_make_competitor_hiring()],
        "comparative_summary": "Dell is hiring more search engineers than HP.",
        "hiring_summary": (
            "Dell is actively hiring for search-related roles, suggesting "
            "investment in search technology. Mixed build-vs-buy signals present."
        ),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# HiringInput
# ---------------------------------------------------------------------------


class TestHiringInput:
    """Tests for the HiringInput schema."""

    def test_valid_input(self) -> None:
        """HiringInput accepts a valid domain string."""
        inp = HiringInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        """HiringInput rejects extra fields due to extra='forbid'."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            HiringInput(domain="dell.com", extra_field="nope")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# OpenRole
# ---------------------------------------------------------------------------


class TestOpenRole:
    """Tests for the OpenRole schema."""

    def test_valid_role(self) -> None:
        """OpenRole accepts valid data."""
        role = OpenRole.model_validate(_make_open_role())
        assert role.title == "Senior Search Engineer"
        assert role.icp_tier == "tier3_champion"
        assert role.search_related is True
        assert role.relevance_score == 0.85

    @pytest.mark.parametrize(
        "tier",
        ["tier1_economic", "tier2_technical", "tier3_champion", "tier4_user"],
    )
    def test_all_icp_tier_values(self, tier: str) -> None:
        """OpenRole accepts all valid ICP tier values."""
        role = OpenRole.model_validate(_make_open_role(icp_tier=tier))
        assert role.icp_tier == tier

    def test_invalid_icp_tier_rejected(self) -> None:
        """OpenRole rejects invalid ICP tier values."""
        with pytest.raises(ValidationError):
            OpenRole.model_validate(_make_open_role(icp_tier="tier5_random"))

    def test_relevance_score_range(self) -> None:
        """OpenRole enforces 0.0-1.0 range on relevance_score."""
        # Valid boundaries
        role_low = OpenRole.model_validate(_make_open_role(relevance_score=0.0))
        assert role_low.relevance_score == 0.0
        role_high = OpenRole.model_validate(_make_open_role(relevance_score=1.0))
        assert role_high.relevance_score == 1.0

        # Out of range
        with pytest.raises(ValidationError):
            OpenRole.model_validate(_make_open_role(relevance_score=1.5))
        with pytest.raises(ValidationError):
            OpenRole.model_validate(_make_open_role(relevance_score=-0.1))

    def test_defaults(self) -> None:
        """OpenRole applies correct defaults for optional fields."""
        role = OpenRole.model_validate({"title": "Test Role"})
        assert role.department == ""
        assert role.location == ""
        assert role.posted_date is None
        assert role.url is None
        assert role.icp_tier == "tier4_user"
        assert role.relevance_score == 0.0
        assert role.search_related is False
        assert role.signals == []
        assert role.source == ""
        assert role.company_name == ""

    def test_rejects_extra_fields(self) -> None:
        """OpenRole rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            OpenRole.model_validate({**_make_open_role(), "salary": 150000})


# ---------------------------------------------------------------------------
# HiringVelocity
# ---------------------------------------------------------------------------


class TestHiringVelocity:
    """Tests for the HiringVelocity schema."""

    def test_valid_velocity(self) -> None:
        """HiringVelocity accepts valid data."""
        v = HiringVelocity.model_validate(_make_hiring_velocity())
        assert v.roles_last_30d == 12
        assert v.roles_last_90d == 35
        assert v.trend == "accelerating"

    @pytest.mark.parametrize(
        "trend",
        ["accelerating", "steady", "decelerating", "insufficient_data"],
    )
    def test_all_trend_values(self, trend: str) -> None:
        """HiringVelocity accepts all valid trend values."""
        v = HiringVelocity.model_validate(_make_hiring_velocity(trend=trend))
        assert v.trend == trend

    def test_invalid_trend_rejected(self) -> None:
        """HiringVelocity rejects invalid trend values."""
        with pytest.raises(ValidationError):
            HiringVelocity.model_validate(_make_hiring_velocity(trend="exploding"))

    def test_negative_roles_rejected(self) -> None:
        """HiringVelocity rejects negative role counts."""
        with pytest.raises(ValidationError):
            HiringVelocity.model_validate(_make_hiring_velocity(roles_last_30d=-1))

    def test_defaults(self) -> None:
        """HiringVelocity applies correct defaults."""
        v = HiringVelocity()
        assert v.roles_last_30d == 0
        assert v.roles_last_90d == 0
        assert v.trend == "insufficient_data"
        assert v.interpretation == ""

    def test_rejects_extra_fields(self) -> None:
        """HiringVelocity rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            HiringVelocity.model_validate({**_make_hiring_velocity(), "rate": 0.5})


# ---------------------------------------------------------------------------
# BuildVsBuySignal
# ---------------------------------------------------------------------------


class TestBuildVsBuySignal:
    """Tests for the BuildVsBuySignal schema."""

    def test_valid_signal(self) -> None:
        """BuildVsBuySignal accepts valid data."""
        s = BuildVsBuySignal.model_validate(_make_build_vs_buy())
        assert s.signal == "mixed"
        assert s.confidence == "medium"
        assert len(s.evidence) == 2

    @pytest.mark.parametrize(
        "signal",
        ["build", "buy", "mixed", "insufficient_data"],
    )
    def test_all_signal_values(self, signal: str) -> None:
        """BuildVsBuySignal accepts all valid signal values."""
        s = BuildVsBuySignal.model_validate(_make_build_vs_buy(signal=signal))
        assert s.signal == signal

    def test_invalid_signal_rejected(self) -> None:
        """BuildVsBuySignal rejects invalid signal values."""
        with pytest.raises(ValidationError):
            BuildVsBuySignal.model_validate(_make_build_vs_buy(signal="rent"))

    @pytest.mark.parametrize("confidence", ["high", "medium", "low"])
    def test_all_confidence_values(self, confidence: str) -> None:
        """BuildVsBuySignal accepts all valid confidence values."""
        s = BuildVsBuySignal.model_validate(_make_build_vs_buy(confidence=confidence))
        assert s.confidence == confidence

    def test_defaults(self) -> None:
        """BuildVsBuySignal applies correct defaults."""
        s = BuildVsBuySignal()
        assert s.signal == "insufficient_data"
        assert s.evidence == []
        assert s.confidence == "low"

    def test_rejects_extra_fields(self) -> None:
        """BuildVsBuySignal rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            BuildVsBuySignal.model_validate({**_make_build_vs_buy(), "score": 0.8})


# ---------------------------------------------------------------------------
# BuyingCommitteeMember
# ---------------------------------------------------------------------------


class TestBuyingCommitteeMember:
    """Tests for the BuyingCommitteeMember schema."""

    def test_valid_member(self) -> None:
        """BuyingCommitteeMember accepts valid data."""
        m = BuyingCommitteeMember.model_validate(_make_buying_committee_member())
        assert m.name == "Michael Dell"
        assert m.role == "economic_buyer"

    @pytest.mark.parametrize(
        "role",
        [
            "economic_buyer",
            "technical_evaluator",
            "champion_candidate",
            "influencer",
            "blocker",
            "unknown",
        ],
    )
    def test_all_role_values(self, role: str) -> None:
        """BuyingCommitteeMember accepts all valid role values."""
        m = BuyingCommitteeMember.model_validate(_make_buying_committee_member(role=role))
        assert m.role == role

    def test_invalid_role_rejected(self) -> None:
        """BuyingCommitteeMember rejects invalid role values."""
        with pytest.raises(ValidationError):
            BuyingCommitteeMember.model_validate(_make_buying_committee_member(role="sponsor"))

    def test_defaults(self) -> None:
        """BuyingCommitteeMember applies correct defaults."""
        m = BuyingCommitteeMember(name="Jane Doe", title="CTO")
        assert m.role == "unknown"
        assert m.linkedin_url is None
        assert m.tenure_description is None
        assert m.previous_company is None
        assert m.champion_signals == []

    def test_rejects_extra_fields(self) -> None:
        """BuyingCommitteeMember rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            BuyingCommitteeMember.model_validate(
                {**_make_buying_committee_member(), "email": "x@y.com"}
            )


# ---------------------------------------------------------------------------
# BuyingCommittee
# ---------------------------------------------------------------------------


class TestBuyingCommittee:
    """Tests for the BuyingCommittee schema."""

    def test_valid_committee(self) -> None:
        """BuyingCommittee accepts valid data."""
        bc = BuyingCommittee.model_validate(_make_buying_committee())
        assert len(bc.members) == 1
        assert bc.confidence == "medium"

    @pytest.mark.parametrize("confidence", ["high", "medium", "low"])
    def test_all_confidence_values(self, confidence: str) -> None:
        """BuyingCommittee accepts all valid confidence values."""
        bc = BuyingCommittee.model_validate(_make_buying_committee(confidence=confidence))
        assert bc.confidence == confidence

    def test_defaults(self) -> None:
        """BuyingCommittee applies correct defaults."""
        bc = BuyingCommittee()
        assert bc.members == []
        assert bc.confidence == "low"
        assert bc.methodology == ""

    def test_rejects_extra_fields(self) -> None:
        """BuyingCommittee rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            BuyingCommittee.model_validate({**_make_buying_committee(), "score": 95})


# ---------------------------------------------------------------------------
# CompetitorHiring
# ---------------------------------------------------------------------------


class TestCompetitorHiring:
    """Tests for the CompetitorHiring schema."""

    def test_valid_competitor(self) -> None:
        """CompetitorHiring accepts valid data."""
        ch = CompetitorHiring.model_validate(_make_competitor_hiring())
        assert ch.company_name == "HP Inc."
        assert ch.domain == "hp.com"
        assert len(ch.open_roles) == 1
        assert ch.search_related_count == 1

    def test_defaults(self) -> None:
        """CompetitorHiring applies correct defaults."""
        ch = CompetitorHiring(company_name="Test", domain="test.com")
        assert ch.open_roles == []
        assert ch.search_related_count == 0
        assert ch.hiring_velocity is None

    def test_rejects_extra_fields(self) -> None:
        """CompetitorHiring rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CompetitorHiring.model_validate({**_make_competitor_hiring(), "market_share": 0.15})


# ---------------------------------------------------------------------------
# HiringOutput
# ---------------------------------------------------------------------------


class TestHiringOutput:
    """Tests for the HiringOutput schema."""

    def test_valid_full_output(self) -> None:
        """HiringOutput accepts a complete valid output."""
        output = HiringOutput.model_validate(_make_full_output())
        assert output.domain == "dell.com"
        assert len(output.open_roles) == 1
        assert output.role_count_by_tier == {"tier3_champion": 1}
        assert output.search_related_count == 1
        assert output.hiring_velocity is not None
        assert output.build_vs_buy is not None
        assert output.buying_committee is not None
        assert len(output.competitor_hiring) == 1
        assert output.hiring_summary != ""

    def test_minimal_defaults(self) -> None:
        """HiringOutput with only required field (domain)."""
        output = HiringOutput(domain="test.com")
        assert output.open_roles == []
        assert output.role_count_by_tier == {}
        assert output.search_related_count == 0
        assert output.hiring_velocity is None
        assert output.build_vs_buy is None
        assert output.buying_committee is None
        assert output.competitor_hiring == []
        assert output.comparative_summary == ""
        assert output.hiring_summary == ""

    def test_rejects_extra_fields(self) -> None:
        """HiringOutput rejects extra fields."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            HiringOutput.model_validate({**_make_full_output(), "secret_field": "no"})

    def test_nested_role_validation(self) -> None:
        """HiringOutput validates nested roles."""
        bad_data = _make_full_output()
        bad_data["open_roles"] = [{"title": "Test", "icp_tier": "INVALID_TIER"}]
        with pytest.raises(ValidationError):
            HiringOutput.model_validate(bad_data)

    def test_nested_velocity_validation(self) -> None:
        """HiringOutput validates nested hiring_velocity."""
        bad_data = _make_full_output()
        bad_data["hiring_velocity"] = {"trend": "INVALID"}
        with pytest.raises(ValidationError):
            HiringOutput.model_validate(bad_data)

    def test_nested_bvb_validation(self) -> None:
        """HiringOutput validates nested build_vs_buy."""
        bad_data = _make_full_output()
        bad_data["build_vs_buy"] = {"signal": "INVALID"}
        with pytest.raises(ValidationError):
            HiringOutput.model_validate(bad_data)

    def test_nested_committee_validation(self) -> None:
        """HiringOutput validates nested buying_committee."""
        bad_data = _make_full_output()
        bad_data["buying_committee"] = {
            "members": [{"name": "Jane", "title": "CEO", "role": "INVALID"}],
        }
        with pytest.raises(ValidationError):
            HiringOutput.model_validate(bad_data)

    def test_role_count_by_tier_is_dict(self) -> None:
        """role_count_by_tier must be a dict."""
        output = HiringOutput.model_validate(
            _make_full_output(role_count_by_tier={"tier1_economic": 3, "tier4_user": 7})
        )
        assert isinstance(output.role_count_by_tier, dict)
        assert output.role_count_by_tier["tier1_economic"] == 3

    def test_search_related_count_non_negative(self) -> None:
        """search_related_count must be non-negative."""
        with pytest.raises(ValidationError):
            HiringOutput.model_validate(_make_full_output(search_related_count=-1))
