"""Contract tests for intel-techstack schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.core.types import EvidenceTier
from prism_platform.modules.intel_techstack.schemas import (
    CompetitorTechStack,
    SearchVendor,
    TechStackInput,
    TechStackOutput,
)


class TestTechStackInput:
    def test_valid_input(self) -> None:
        inp = TechStackInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            TechStackInput(domain="dell.com", extra_field="nope")  # type: ignore[call-arg]


class TestSearchVendor:
    @pytest.mark.parametrize("status", ["ACTIVE", "TAG_ONLY", "REMOVED", "UNDETECTED"])
    def test_all_status_values(self, status: str) -> None:
        vendor = SearchVendor(
            name="Algolia",
            status=status,  # type: ignore[arg-type]
            detection_source="BuiltWith Free API",
            evidence_tier=EvidenceTier.VERIFIED,
        )
        assert vendor.status == status

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SearchVendor(
                name="Algolia",
                status="INVALID",  # type: ignore[arg-type]
                detection_source="BuiltWith",
                evidence_tier=EvidenceTier.VERIFIED,
            )


class TestTechStackOutput:
    def test_valid_full_output(self) -> None:
        output = TechStackOutput(
            search_vendor=SearchVendor(
                name="Algolia",
                status="ACTIVE",
                detection_source="BuiltWith Free API",
                evidence_tier=EvidenceTier.VERIFIED,
            ),
            ecommerce_platform="Shopify",
            cms="WordPress",
            cdn="Cloudflare",
            analytics=["Google Analytics"],
            personalization=["Optimizely"],
            bot_detection="reCAPTCHA",
            all_technologies=[{"Name": "Algolia", "Tag": "algolia", "Categories": ["search"]}],
            tech_stack_summary="example.com: Search: Algolia (ACTIVE)",
            algolia_detected=True,
        )
        assert output.algolia_detected is True
        assert output.search_vendor is not None
        assert output.search_vendor.name == "Algolia"

    def test_minimal_defaults(self) -> None:
        output = TechStackOutput()
        assert output.search_vendor is None
        assert output.analytics == []
        assert output.algolia_detected is False
        assert output.tech_stack_summary == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            TechStackOutput(bogus="no")  # type: ignore[call-arg]

    def test_new_competitor_fields_default_empty(self) -> None:
        output = TechStackOutput()
        assert output.competitor_tech_stacks == []
        assert output.comparative_summary == ""
        assert output.golden_angle_competitors == []

    def test_output_with_competitor_data(self) -> None:
        comp = CompetitorTechStack(
            company_name="HP Inc",
            domain="hp.com",
            tech_count=5,
            all_technologies=[{"Name": "Algolia", "Tag": "algolia", "Categories": []}],
            is_algolia_customer=True,
        )
        output = TechStackOutput(
            competitor_tech_stacks=[comp],
            comparative_summary="Prospect uses Elasticsearch. HP Inc uses Algolia.",
            golden_angle_competitors=["HP Inc"],
        )
        assert len(output.competitor_tech_stacks) == 1
        assert output.competitor_tech_stacks[0].is_algolia_customer is True
        assert output.golden_angle_competitors == ["HP Inc"]


class TestCompetitorTechStack:
    def test_valid_competitor(self) -> None:
        comp = CompetitorTechStack(
            company_name="HP Inc",
            domain="hp.com",
        )
        assert comp.company_name == "HP Inc"
        assert comp.domain == "hp.com"
        assert comp.tech_count == 0
        assert comp.is_algolia_customer is False
        assert comp.all_technologies == []

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CompetitorTechStack(
                company_name="HP",
                domain="hp.com",
                bogus_field="nope",  # type: ignore[call-arg]
            )

    def test_full_competitor(self) -> None:
        vendor = SearchVendor(
            name="Algolia",
            status="ACTIVE",
            detection_source="BuiltWith v22 API",
            evidence_tier=EvidenceTier.VERIFIED,
        )
        comp = CompetitorTechStack(
            company_name="HP Inc",
            domain="hp.com",
            search_vendor=vendor,
            ecommerce_platform="Shopify",
            all_technologies=[{"Name": "Algolia", "Tag": "algolia", "Categories": []}],
            tech_count=1,
            is_algolia_customer=True,
        )
        assert comp.search_vendor is not None
        assert comp.search_vendor.name == "Algolia"
        assert comp.is_algolia_customer is True
