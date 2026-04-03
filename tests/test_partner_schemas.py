"""Contract tests for intel-partner schemas.

Validates Pydantic models accept valid data, reject invalid data,
and enforce all constraints specified in the module spec.
NO API calls in this file -- pure Pydantic validation only.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.intel_partner.schemas import (
    CompetitorPartner,
    CoSellOpportunity,
    PartnerInput,
    PartnerOutput,
    PartnerOverlap,
    PartnerPlay,
    SIRelationship,
    VerticalCaseStudy,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_partner_overlap(**overrides: object) -> dict:
    """Build a valid PartnerOverlap dict with optional overrides."""
    base: dict = {
        "partner_name": "Accenture",
        "partner_type": "si",
        "shared_account_count": 15,
        "prospect_overlap": True,
        "relationship_strength": "strong",
        "notes": "Accenture manages Dell's SFCC implementation",
    }
    base.update(overrides)
    return base


def _make_cosell_opportunity(**overrides: object) -> dict:
    """Build a valid CoSellOpportunity dict with optional overrides."""
    base: dict = {
        "partner_name": "Salesforce",
        "partner_type": "technology",
        "technology_confirmed": True,
        "algolia_integration": True,
        "pitch": (
            "Dell uses SFCC (confirmed) -> Algolia has SFCC connector -> Partner X implements both"
        ),
        "confidence": "high",
    }
    base.update(overrides)
    return base


def _make_si_relationship(**overrides: object) -> dict:
    """Build a valid SIRelationship dict with optional overrides."""
    base: dict = {
        "si_name": "Slalom",
        "relationship_type": "implementation",
        "confirmed_source": "perplexity",
        "warm_intro_path": "Slalom serves both Dell and Shoe Carnival (Algolia customer)",
        "algolia_customer_connection": "Shoe Carnival",
    }
    base.update(overrides)
    return base


def _make_vertical_case_study(**overrides: object) -> dict:
    """Build a valid VerticalCaseStudy dict with optional overrides."""
    base: dict = {
        "customer_name": "Gymshark",
        "domain": "gymshark.com",
        "industry": "Retail",
        "use_case": "product discovery",
        "key_metric": "37% conversion lift",
        "url": "https://algolia.com/customers/gymshark",
    }
    base.update(overrides)
    return base


def _make_partner_play(**overrides: object) -> dict:
    """Build a valid PartnerPlay dict with optional overrides."""
    base: dict = {
        "recommended_partner": "Accenture",
        "partner_type": "si",
        "approach_reason": "Accenture manages Dell SFCC and has strong Algolia relationship.",
        "pitch_message": "Dell is on SFCC. Algolia has a native SFCC connector. Let's co-sell.",
        "confidence": "high",
    }
    base.update(overrides)
    return base


def _make_competitor_partner(**overrides: object) -> dict:
    """Build a valid CompetitorPartner dict with optional overrides."""
    base: dict = {
        "company_name": "HP",
        "domain": "hp.com",
        "known_partners": ["Accenture", "Deloitte"],
        "overlap_with_prospect_partners": ["Accenture"],
    }
    base.update(overrides)
    return base


def _make_partner_output(**overrides: object) -> dict:
    """Build a valid PartnerOutput dict with optional overrides."""
    base: dict = {
        "domain": "dell.com",
        "partner_overlaps": [_make_partner_overlap()],
        "co_sell_opportunities": [_make_cosell_opportunity()],
        "si_relationships": [_make_si_relationship()],
        "vertical_case_studies": [_make_vertical_case_study()],
        "recent_partnerships": ["Dell announced SAP Commerce Cloud migration in Q1 2026"],
        "competitor_partners": [_make_competitor_partner()],
        "partner_play": _make_partner_play(),
        "partner_summary": "Dell has strong SI relationships and technology partnership ecosystem.",
        "crossbeam_available": False,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# PartnerInput
# ---------------------------------------------------------------------------


class TestPartnerInput:
    """Tests for PartnerInput schema."""

    def test_valid_input(self) -> None:
        """PartnerInput accepts a valid domain string."""
        inp = PartnerInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        """PartnerInput rejects extra fields due to extra='forbid'."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            PartnerInput(domain="dell.com", foo="bar")  # type: ignore[call-arg]

    def test_empty_domain_allowed(self) -> None:
        """PartnerInput allows empty domain (validator catches this downstream)."""
        inp = PartnerInput(domain="")
        assert inp.domain == ""


# ---------------------------------------------------------------------------
# PartnerOverlap
# ---------------------------------------------------------------------------


class TestPartnerOverlap:
    """Tests for PartnerOverlap schema."""

    def test_valid_overlap(self) -> None:
        """PartnerOverlap accepts valid data."""
        overlap = PartnerOverlap(**_make_partner_overlap())
        assert overlap.partner_name == "Accenture"
        assert overlap.partner_type == "si"
        assert overlap.shared_account_count == 15
        assert overlap.prospect_overlap is True
        assert overlap.relationship_strength == "strong"

    def test_defaults(self) -> None:
        """PartnerOverlap applies correct defaults."""
        overlap = PartnerOverlap(partner_name="TestPartner")
        assert overlap.partner_type == "other"
        assert overlap.shared_account_count is None
        assert overlap.prospect_overlap is False
        assert overlap.relationship_strength == "unknown"
        assert overlap.notes == ""

    def test_rejects_invalid_partner_type(self) -> None:
        """PartnerOverlap rejects invalid partner_type literal."""
        with pytest.raises(ValidationError, match="Input should be"):
            PartnerOverlap(**_make_partner_overlap(partner_type="invalid_type"))

    def test_rejects_invalid_relationship_strength(self) -> None:
        """PartnerOverlap rejects invalid relationship_strength literal."""
        with pytest.raises(ValidationError, match="Input should be"):
            PartnerOverlap(**_make_partner_overlap(relationship_strength="very_strong"))

    def test_all_partner_types(self) -> None:
        """PartnerOverlap accepts all valid partner_type values."""
        for pt in ("si", "technology", "agency", "consulting", "other"):
            overlap = PartnerOverlap(**_make_partner_overlap(partner_type=pt))
            assert overlap.partner_type == pt

    def test_all_relationship_strengths(self) -> None:
        """PartnerOverlap accepts all valid relationship_strength values."""
        for rs in ("strong", "moderate", "weak", "unknown"):
            overlap = PartnerOverlap(**_make_partner_overlap(relationship_strength=rs))
            assert overlap.relationship_strength == rs

    def test_rejects_extra_fields(self) -> None:
        """PartnerOverlap rejects extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            PartnerOverlap(**_make_partner_overlap(extra_field="nope"))

    def test_null_shared_account_count(self) -> None:
        """PartnerOverlap allows None for shared_account_count."""
        overlap = PartnerOverlap(**_make_partner_overlap(shared_account_count=None))
        assert overlap.shared_account_count is None


# ---------------------------------------------------------------------------
# CoSellOpportunity
# ---------------------------------------------------------------------------


class TestCoSellOpportunity:
    """Tests for CoSellOpportunity schema."""

    def test_valid_cosell(self) -> None:
        """CoSellOpportunity accepts valid data."""
        cosell = CoSellOpportunity(**_make_cosell_opportunity())
        assert cosell.partner_name == "Salesforce"
        assert cosell.technology_confirmed is True
        assert cosell.algolia_integration is True
        assert cosell.confidence == "high"

    def test_defaults(self) -> None:
        """CoSellOpportunity applies correct defaults."""
        cosell = CoSellOpportunity(partner_name="TestPartner")
        assert cosell.partner_type == "other"
        assert cosell.technology_confirmed is False
        assert cosell.algolia_integration is False
        assert cosell.pitch == ""
        assert cosell.confidence == "low"

    def test_rejects_invalid_confidence(self) -> None:
        """CoSellOpportunity rejects invalid confidence literal."""
        with pytest.raises(ValidationError, match="Input should be"):
            CoSellOpportunity(**_make_cosell_opportunity(confidence="very_high"))

    def test_all_confidence_levels(self) -> None:
        """CoSellOpportunity accepts all valid confidence values."""
        for conf in ("high", "medium", "low"):
            cosell = CoSellOpportunity(**_make_cosell_opportunity(confidence=conf))
            assert cosell.confidence == conf

    def test_rejects_extra_fields(self) -> None:
        """CoSellOpportunity rejects extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            CoSellOpportunity(**_make_cosell_opportunity(extra="nope"))


# ---------------------------------------------------------------------------
# SIRelationship
# ---------------------------------------------------------------------------


class TestSIRelationship:
    """Tests for SIRelationship schema."""

    def test_valid_si(self) -> None:
        """SIRelationship accepts valid data."""
        si = SIRelationship(**_make_si_relationship())
        assert si.si_name == "Slalom"
        assert si.relationship_type == "implementation"
        assert si.confirmed_source == "perplexity"
        assert si.warm_intro_path is not None
        assert si.algolia_customer_connection == "Shoe Carnival"

    def test_defaults(self) -> None:
        """SIRelationship applies correct defaults."""
        si = SIRelationship(si_name="Deloitte")
        assert si.relationship_type == "unknown"
        assert si.confirmed_source == "perplexity"
        assert si.warm_intro_path is None
        assert si.algolia_customer_connection is None

    def test_all_relationship_types(self) -> None:
        """SIRelationship accepts all valid relationship_type values."""
        for rt in ("implementation", "consulting", "managed_services", "unknown"):
            si = SIRelationship(**_make_si_relationship(relationship_type=rt))
            assert si.relationship_type == rt

    def test_all_confirmed_sources(self) -> None:
        """SIRelationship accepts all valid confirmed_source values."""
        for cs in ("crossbeam", "perplexity", "both"):
            si = SIRelationship(**_make_si_relationship(confirmed_source=cs))
            assert si.confirmed_source == cs

    def test_rejects_invalid_relationship_type(self) -> None:
        """SIRelationship rejects invalid relationship_type."""
        with pytest.raises(ValidationError, match="Input should be"):
            SIRelationship(**_make_si_relationship(relationship_type="partnership"))

    def test_rejects_extra_fields(self) -> None:
        """SIRelationship rejects extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            SIRelationship(**_make_si_relationship(extra="nope"))


# ---------------------------------------------------------------------------
# VerticalCaseStudy
# ---------------------------------------------------------------------------


class TestVerticalCaseStudy:
    """Tests for VerticalCaseStudy schema."""

    def test_valid_case_study(self) -> None:
        """VerticalCaseStudy accepts valid data."""
        cs = VerticalCaseStudy(**_make_vertical_case_study())
        assert cs.customer_name == "Gymshark"
        assert cs.domain == "gymshark.com"
        assert cs.key_metric == "37% conversion lift"

    def test_defaults(self) -> None:
        """VerticalCaseStudy applies correct defaults."""
        cs = VerticalCaseStudy(customer_name="TestCo")
        assert cs.domain is None
        assert cs.industry == ""
        assert cs.use_case == ""
        assert cs.key_metric is None
        assert cs.url is None

    def test_rejects_extra_fields(self) -> None:
        """VerticalCaseStudy rejects extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            VerticalCaseStudy(**_make_vertical_case_study(extra="nope"))

    def test_null_optional_fields(self) -> None:
        """VerticalCaseStudy allows None for optional fields."""
        cs = VerticalCaseStudy(
            customer_name="Test",
            domain=None,
            key_metric=None,
            url=None,
        )
        assert cs.domain is None
        assert cs.key_metric is None
        assert cs.url is None


# ---------------------------------------------------------------------------
# PartnerPlay
# ---------------------------------------------------------------------------


class TestPartnerPlay:
    """Tests for PartnerPlay schema."""

    def test_valid_play(self) -> None:
        """PartnerPlay accepts valid data."""
        play = PartnerPlay(**_make_partner_play())
        assert play.recommended_partner == "Accenture"
        assert play.partner_type == "si"
        assert play.confidence == "high"

    def test_requires_recommended_partner(self) -> None:
        """PartnerPlay requires recommended_partner."""
        with pytest.raises(ValidationError, match="Field required"):
            PartnerPlay(
                approach_reason="reason",
                pitch_message="pitch",
            )  # type: ignore[call-arg]

    def test_requires_approach_reason(self) -> None:
        """PartnerPlay requires approach_reason."""
        with pytest.raises(ValidationError, match="Field required"):
            PartnerPlay(
                recommended_partner="Test",
                pitch_message="pitch",
            )  # type: ignore[call-arg]

    def test_requires_pitch_message(self) -> None:
        """PartnerPlay requires pitch_message."""
        with pytest.raises(ValidationError, match="Field required"):
            PartnerPlay(
                recommended_partner="Test",
                approach_reason="reason",
            )  # type: ignore[call-arg]

    def test_all_partner_types(self) -> None:
        """PartnerPlay accepts all valid partner_type values."""
        for pt in ("si", "technology", "agency", "consulting", "other"):
            play = PartnerPlay(**_make_partner_play(partner_type=pt))
            assert play.partner_type == pt

    def test_rejects_invalid_confidence(self) -> None:
        """PartnerPlay rejects invalid confidence literal."""
        with pytest.raises(ValidationError, match="Input should be"):
            PartnerPlay(**_make_partner_play(confidence="very_high"))

    def test_rejects_extra_fields(self) -> None:
        """PartnerPlay rejects extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            PartnerPlay(**_make_partner_play(extra="nope"))

    def test_default_confidence(self) -> None:
        """PartnerPlay defaults confidence to 'low'."""
        play = PartnerPlay(
            recommended_partner="Test",
            approach_reason="reason",
            pitch_message="pitch",
        )
        assert play.confidence == "low"


# ---------------------------------------------------------------------------
# CompetitorPartner
# ---------------------------------------------------------------------------


class TestCompetitorPartner:
    """Tests for CompetitorPartner schema."""

    def test_valid_competitor(self) -> None:
        """CompetitorPartner accepts valid data."""
        cp = CompetitorPartner(**_make_competitor_partner())
        assert cp.company_name == "HP"
        assert cp.domain == "hp.com"
        assert len(cp.known_partners) == 2
        assert len(cp.overlap_with_prospect_partners) == 1

    def test_defaults(self) -> None:
        """CompetitorPartner applies correct defaults."""
        cp = CompetitorPartner(company_name="Lenovo", domain="lenovo.com")
        assert cp.known_partners == []
        assert cp.overlap_with_prospect_partners == []

    def test_rejects_extra_fields(self) -> None:
        """CompetitorPartner rejects extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            CompetitorPartner(**_make_competitor_partner(extra="nope"))

    def test_requires_company_name(self) -> None:
        """CompetitorPartner requires company_name."""
        with pytest.raises(ValidationError, match="Field required"):
            CompetitorPartner(domain="hp.com")  # type: ignore[call-arg]

    def test_requires_domain(self) -> None:
        """CompetitorPartner requires domain."""
        with pytest.raises(ValidationError, match="Field required"):
            CompetitorPartner(company_name="HP")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# PartnerOutput
# ---------------------------------------------------------------------------


class TestPartnerOutput:
    """Tests for PartnerOutput schema."""

    def test_valid_output(self) -> None:
        """PartnerOutput accepts valid, fully populated data."""
        output = PartnerOutput(**_make_partner_output())
        assert output.domain == "dell.com"
        assert len(output.partner_overlaps) == 1
        assert len(output.co_sell_opportunities) == 1
        assert len(output.si_relationships) == 1
        assert len(output.vertical_case_studies) == 1
        assert len(output.recent_partnerships) == 1
        assert len(output.competitor_partners) == 1
        assert output.partner_play is not None
        assert output.partner_summary != ""
        assert output.crossbeam_available is False

    def test_minimal_output(self) -> None:
        """PartnerOutput accepts minimal data with all defaults."""
        output = PartnerOutput(domain="dell.com")
        assert output.domain == "dell.com"
        assert output.partner_overlaps == []
        assert output.co_sell_opportunities == []
        assert output.si_relationships == []
        assert output.vertical_case_studies == []
        assert output.recent_partnerships == []
        assert output.competitor_partners == []
        assert output.partner_play is None
        assert output.partner_summary == ""
        assert output.crossbeam_available is False

    def test_rejects_extra_fields(self) -> None:
        """PartnerOutput rejects extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            PartnerOutput(**_make_partner_output(extra_field="nope"))

    def test_requires_domain(self) -> None:
        """PartnerOutput requires domain."""
        with pytest.raises(ValidationError, match="Field required"):
            PartnerOutput()  # type: ignore[call-arg]

    def test_crossbeam_available_true(self) -> None:
        """PartnerOutput accepts crossbeam_available=True."""
        output = PartnerOutput(**_make_partner_output(crossbeam_available=True))
        assert output.crossbeam_available is True

    def test_model_dump_roundtrip(self) -> None:
        """PartnerOutput survives model_dump -> model_validate roundtrip."""
        original = PartnerOutput(**_make_partner_output())
        dumped = original.model_dump()
        restored = PartnerOutput.model_validate(dumped)
        assert restored.domain == original.domain
        assert len(restored.partner_overlaps) == len(original.partner_overlaps)
        assert len(restored.co_sell_opportunities) == len(original.co_sell_opportunities)
        assert restored.partner_play is not None
        assert (  # type: ignore[union-attr]
            restored.partner_play.recommended_partner == original.partner_play.recommended_partner
        )

    def test_json_roundtrip(self) -> None:
        """PartnerOutput survives JSON serialization roundtrip."""
        original = PartnerOutput(**_make_partner_output())
        json_str = original.model_dump_json()
        restored = PartnerOutput.model_validate_json(json_str)
        assert restored.domain == original.domain
        assert len(restored.si_relationships) == len(original.si_relationships)

    def test_multiple_overlaps(self) -> None:
        """PartnerOutput handles multiple partner overlaps."""
        overlaps = [
            _make_partner_overlap(partner_name="Accenture"),
            _make_partner_overlap(partner_name="Deloitte", partner_type="consulting"),
            _make_partner_overlap(partner_name="Publicis Sapient", partner_type="agency"),
        ]
        output = PartnerOutput(**_make_partner_output(partner_overlaps=overlaps))
        assert len(output.partner_overlaps) == 3
        assert output.partner_overlaps[0].partner_name == "Accenture"
        assert output.partner_overlaps[1].partner_name == "Deloitte"
        assert output.partner_overlaps[2].partner_name == "Publicis Sapient"

    def test_multiple_cosell_opportunities(self) -> None:
        """PartnerOutput handles multiple co-sell opportunities."""
        cosells = [
            _make_cosell_opportunity(partner_name="Salesforce"),
            _make_cosell_opportunity(partner_name="Adobe", partner_type="technology"),
        ]
        output = PartnerOutput(**_make_partner_output(co_sell_opportunities=cosells))
        assert len(output.co_sell_opportunities) == 2

    def test_partner_play_none(self) -> None:
        """PartnerOutput allows partner_play=None."""
        output = PartnerOutput(**_make_partner_output(partner_play=None))
        assert output.partner_play is None

    def test_empty_recent_partnerships(self) -> None:
        """PartnerOutput handles empty recent_partnerships list."""
        output = PartnerOutput(**_make_partner_output(recent_partnerships=[]))
        assert output.recent_partnerships == []

    def test_nested_competitor_partner_lists(self) -> None:
        """PartnerOutput correctly handles nested lists in CompetitorPartner."""
        comps = [
            _make_competitor_partner(
                known_partners=["A", "B", "C"],
                overlap_with_prospect_partners=["A"],
            ),
        ]
        output = PartnerOutput(**_make_partner_output(competitor_partners=comps))
        assert len(output.competitor_partners[0].known_partners) == 3
        assert output.competitor_partners[0].overlap_with_prospect_partners == ["A"]


# ---------------------------------------------------------------------------
# Cross-schema validation
# ---------------------------------------------------------------------------


class TestCrossSchemaValidation:
    """Tests that validate interactions between schemas."""

    def test_cosell_references_valid_partner_types(self) -> None:
        """CoSellOpportunity partner_type values match PartnerOverlap partner_type values."""
        valid_types = {"si", "technology", "agency", "consulting", "other"}
        for pt in valid_types:
            cosell = CoSellOpportunity(**_make_cosell_opportunity(partner_type=pt))
            overlap = PartnerOverlap(**_make_partner_overlap(partner_type=pt))
            assert cosell.partner_type == overlap.partner_type

    def test_partner_play_type_matches_overlap_type(self) -> None:
        """PartnerPlay partner_type uses same literals as PartnerOverlap."""
        valid_types = {"si", "technology", "agency", "consulting", "other"}
        for pt in valid_types:
            play = PartnerPlay(**_make_partner_play(partner_type=pt))
            assert play.partner_type == pt

    def test_full_output_with_all_submodels(self) -> None:
        """PartnerOutput with diverse sub-model combinations validates."""
        output = PartnerOutput(
            domain="dell.com",
            partner_overlaps=[
                PartnerOverlap(**_make_partner_overlap(partner_type="si")),
                PartnerOverlap(
                    **_make_partner_overlap(partner_name="Shopify", partner_type="technology")
                ),
            ],
            co_sell_opportunities=[
                CoSellOpportunity(**_make_cosell_opportunity(confidence="high")),
                CoSellOpportunity(
                    **_make_cosell_opportunity(partner_name="Adobe", confidence="low")
                ),
            ],
            si_relationships=[
                SIRelationship(**_make_si_relationship()),
                SIRelationship(
                    **_make_si_relationship(si_name="Capgemini", confirmed_source="both")
                ),
            ],
            vertical_case_studies=[
                VerticalCaseStudy(**_make_vertical_case_study()),
            ],
            recent_partnerships=["Partnership A", "Partnership B"],
            competitor_partners=[
                CompetitorPartner(**_make_competitor_partner()),
            ],
            partner_play=PartnerPlay(**_make_partner_play()),
            partner_summary="Comprehensive partner intelligence for Dell.",
            crossbeam_available=True,
        )
        assert len(output.partner_overlaps) == 2
        assert len(output.co_sell_opportunities) == 2
        assert len(output.si_relationships) == 2
        assert output.crossbeam_available is True
