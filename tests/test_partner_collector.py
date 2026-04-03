"""Tests for intel-partner collector -- prompt builders and validator.

Prompt builder tests do NOT require API calls.
Perplexity integration tests are skipped (quota exhausted).
Crossbeam integration tests are skipped (no API key).
"""

from __future__ import annotations

import os

import pytest

from prism_platform.core.types import EvidenceTier, Source
from prism_platform.modules.intel_partner.collector import (
    build_competitor_partners_prompt,
    build_partnership_news_prompt,
    build_si_relationships_prompt,
    build_tech_partners_prompt,
    build_vertical_case_studies_prompt,
)
from prism_platform.modules.intel_partner.schemas import (
    CompetitorPartner,
    CoSellOpportunity,
    PartnerOutput,
    PartnerOverlap,
    PartnerPlay,
    SIRelationship,
    VerticalCaseStudy,
)
from prism_platform.modules.intel_partner.validator import validate_output

# ---------------------------------------------------------------------------
# Prompt builder tests (no API calls)
# ---------------------------------------------------------------------------


class TestPromptBuilders:
    """Tests for prompt builder functions."""

    def test_si_relationships_prompt_contains_company(self) -> None:
        """SI relationships prompt includes company name and domain."""
        prompt = build_si_relationships_prompt("Dell Technologies", "dell.com")
        assert "Dell Technologies" in prompt
        assert "dell.com" in prompt
        assert "system integrator" in prompt.lower()

    def test_si_relationships_prompt_mentions_algolia(self) -> None:
        """SI relationships prompt asks about Algolia partners."""
        prompt = build_si_relationships_prompt("Dell Technologies", "dell.com")
        assert "Algolia" in prompt

    def test_tech_partners_prompt_contains_company(self) -> None:
        """Tech partners prompt includes company name and domain."""
        prompt = build_tech_partners_prompt("Dell Technologies", "dell.com")
        assert "Dell Technologies" in prompt
        assert "dell.com" in prompt

    def test_tech_partners_prompt_mentions_platforms(self) -> None:
        """Tech partners prompt mentions key e-commerce platforms."""
        prompt = build_tech_partners_prompt("Dell Technologies", "dell.com")
        assert "Salesforce Commerce Cloud" in prompt
        assert "Adobe Commerce" in prompt or "Magento" in prompt
        assert "Shopify" in prompt

    def test_vertical_case_studies_prompt_contains_industry(self) -> None:
        """Vertical case studies prompt includes industry."""
        prompt = build_vertical_case_studies_prompt("Dell Technologies", "dell.com", "Technology")
        assert "Technology" in prompt
        assert "Algolia" in prompt
        assert "case stud" in prompt.lower()

    def test_partnership_news_prompt_contains_company(self) -> None:
        """Partnership news prompt includes company name."""
        prompt = build_partnership_news_prompt("Dell Technologies", "dell.com")
        assert "Dell Technologies" in prompt
        assert "dell.com" in prompt
        assert "partnership" in prompt.lower() or "partner" in prompt.lower()

    def test_competitor_partners_prompt_lists_competitors(self) -> None:
        """Competitor partners prompt includes competitor list."""
        competitors = [
            {"company_name": "HP", "domain": "hp.com"},
            {"company_name": "Lenovo", "domain": "lenovo.com"},
        ]
        prompt = build_competitor_partners_prompt("Dell Technologies", "dell.com", competitors)
        assert "HP" in prompt
        assert "hp.com" in prompt
        assert "Lenovo" in prompt
        assert "lenovo.com" in prompt

    def test_competitor_partners_prompt_empty_competitors(self) -> None:
        """Competitor partners prompt handles empty competitor list."""
        prompt = build_competitor_partners_prompt("Dell Technologies", "dell.com", [])
        assert "Dell Technologies" in prompt

    def test_competitor_partners_prompt_limits_to_5(self) -> None:
        """Competitor partners prompt limits to 5 competitors."""
        competitors = [{"company_name": f"Comp{i}", "domain": f"comp{i}.com"} for i in range(10)]
        prompt = build_competitor_partners_prompt("Dell Technologies", "dell.com", competitors)
        # Only first 5 should be included
        assert "Comp4" in prompt
        assert "Comp5" not in prompt


# ---------------------------------------------------------------------------
# Validator unit tests (no API calls)
# ---------------------------------------------------------------------------


def _make_valid_output(**overrides: object) -> PartnerOutput:
    """Build a valid PartnerOutput for validator testing."""
    defaults: dict = {
        "domain": "dell.com",
        "partner_overlaps": [
            PartnerOverlap(partner_name="Accenture", partner_type="si"),
        ],
        "co_sell_opportunities": [
            CoSellOpportunity(partner_name="Salesforce", partner_type="technology"),
        ],
        "si_relationships": [
            SIRelationship(si_name="Slalom"),
        ],
        "vertical_case_studies": [
            VerticalCaseStudy(customer_name="Gymshark"),
        ],
        "recent_partnerships": ["Dell announced SAP migration"],
        "competitor_partners": [
            CompetitorPartner(company_name="HP", domain="hp.com"),
        ],
        "partner_play": PartnerPlay(
            recommended_partner="Accenture",
            partner_type="si",
            approach_reason="Strong relationship",
            pitch_message="Let's co-sell",
        ),
        "partner_summary": "Dell has strong partner ecosystem for co-sell.",
        "crossbeam_available": False,
    }
    defaults.update(overrides)
    return PartnerOutput(**defaults)


def _make_sources() -> list[Source]:
    """Build a minimal list of sources for validator testing."""
    return [
        Source(
            field="partner_overlaps",
            value="3 overlaps",
            tier=EvidenceTier.WEBSEARCH,
            source_label="Perplexity sonar-pro",
            method="llm_extraction",
        ),
    ]


class TestValidator:
    """Tests for the validate_output function."""

    def test_valid_output_passes(self) -> None:
        """Fully valid output passes all checks."""
        output = _make_valid_output()
        result = validate_output(output, _make_sources())
        assert result.passed is True
        assert result.checks_run == 8
        assert result.checks_passed == 8
        assert result.errors == []

    def test_empty_domain_fails(self) -> None:
        """Empty domain fails check 1."""
        output = _make_valid_output(domain="")
        result = validate_output(output, _make_sources())
        assert result.passed is False
        assert "domain is empty" in result.errors

    def test_empty_summary_warns(self) -> None:
        """Empty partner_summary produces a warning, not error."""
        output = _make_valid_output(partner_summary="")
        result = validate_output(output, _make_sources())
        # This is a warning, not error, so should still pass
        assert result.passed is True
        assert any("partner_summary" in w for w in result.warnings)

    def test_no_sources_fails(self) -> None:
        """No sources fails check 3."""
        output = _make_valid_output()
        result = validate_output(output, [])
        assert result.passed is False
        assert any("No sources" in e for e in result.errors)

    def test_empty_partner_name_in_overlaps_fails(self) -> None:
        """Empty partner_name in overlaps fails check 4."""
        output = _make_valid_output(partner_overlaps=[PartnerOverlap(partner_name="")])
        result = validate_output(output, _make_sources())
        assert result.passed is False
        assert any("partner_name" in e and "overlap" in e.lower() for e in result.errors)

    def test_empty_partner_name_in_cosell_fails(self) -> None:
        """Empty partner_name in co-sell fails check 5."""
        output = _make_valid_output(co_sell_opportunities=[CoSellOpportunity(partner_name="")])
        result = validate_output(output, _make_sources())
        assert result.passed is False
        assert any("partner_name" in e and "Co-sell" in e for e in result.errors)

    def test_empty_si_name_fails(self) -> None:
        """Empty si_name in SI relationships fails check 6."""
        output = _make_valid_output(si_relationships=[SIRelationship(si_name="")])
        result = validate_output(output, _make_sources())
        assert result.passed is False
        assert any("si_name" in e for e in result.errors)

    def test_no_partner_play_warns(self) -> None:
        """Missing partner_play produces a warning, not error."""
        output = _make_valid_output(partner_play=None)
        result = validate_output(output, _make_sources())
        assert result.passed is True
        assert any("partner_play" in w for w in result.warnings)

    def test_crossbeam_flag_inconsistency_warns(self) -> None:
        """crossbeam_available=True with empty overlaps produces warning."""
        output = _make_valid_output(crossbeam_available=True, partner_overlaps=[])
        result = validate_output(output, _make_sources())
        # This is a warning, not error
        assert result.passed is True
        assert any("crossbeam_available" in w for w in result.warnings)

    def test_multiple_errors_accumulated(self) -> None:
        """Multiple validation errors are all reported."""
        output = _make_valid_output(
            domain="",
            partner_overlaps=[PartnerOverlap(partner_name="")],
            co_sell_opportunities=[CoSellOpportunity(partner_name="")],
            si_relationships=[SIRelationship(si_name="")],
        )
        result = validate_output(output, [])
        assert result.passed is False
        assert len(result.errors) >= 4  # domain, sources, overlap name, cosell name, si name

    def test_valid_with_crossbeam_true_and_overlaps(self) -> None:
        """crossbeam_available=True with overlaps is valid."""
        output = _make_valid_output(
            crossbeam_available=True,
            partner_overlaps=[PartnerOverlap(partner_name="Accenture")],
        )
        result = validate_output(output, _make_sources())
        assert result.passed is True

    def test_empty_lists_pass(self) -> None:
        """Empty lists for optional sections still pass validation."""
        output = _make_valid_output(
            partner_overlaps=[],
            co_sell_opportunities=[],
            si_relationships=[],
            vertical_case_studies=[],
            recent_partnerships=[],
            competitor_partners=[],
        )
        result = validate_output(output, _make_sources())
        assert result.passed is True


# ---------------------------------------------------------------------------
# Perplexity integration tests (SKIPPED -- quota exhausted)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("PERPLEXITY_API_KEY") or True,
    reason="Perplexity quota exhausted",
)
class TestPerplexityIntegration:
    """Integration tests requiring live Perplexity API. Currently skipped."""

    @pytest.mark.asyncio
    async def test_si_query(self) -> None:
        """Placeholder for live SI relationship query test."""
        pass

    @pytest.mark.asyncio
    async def test_tech_partners_query(self) -> None:
        """Placeholder for live tech partners query test."""
        pass


# ---------------------------------------------------------------------------
# Crossbeam integration tests (SKIPPED -- no API key)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("CROSSBEAM_API_KEY"),
    reason="CROSSBEAM_API_KEY not configured",
)
class TestCrossbeamIntegration:
    """Integration tests requiring live Crossbeam API. Currently skipped."""

    @pytest.mark.asyncio
    async def test_overlaps_query(self) -> None:
        """Placeholder for live Crossbeam overlaps query test."""
        pass
