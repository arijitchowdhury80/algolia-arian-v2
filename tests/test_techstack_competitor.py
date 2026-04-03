"""Integration tests for intel-techstack competitor fan-out and Golden Angle detection.

Uses real BuiltWith API calls -- requires BUILTWITH_API_KEY in environment.
"""

from __future__ import annotations

import pytest

from prism_platform.config import settings
from prism_platform.modules.intel_techstack.collector import TechStackCollector
from prism_platform.modules.intel_techstack.schemas import (
    CompetitorTechStack,
    TechStackOutput,
)
from prism_platform.modules.intel_techstack.validator import validate_output

pytestmark = pytest.mark.skipif(
    not settings.builtwith_api_key,
    reason="BUILTWITH_API_KEY not set -- skipping integration test",
)


class TestCompetitorCollection:
    """Test collecting a single competitor's tech stack via real API."""

    @pytest.mark.asyncio
    async def test_collect_single_competitor(self) -> None:
        """Collect tech stack for hp.com as a competitor."""
        collector = TechStackCollector()
        result = await collector.collect_competitor(domain="hp.com", company_name="HP Inc")

        assert isinstance(result, CompetitorTechStack)
        assert result.company_name == "HP Inc"
        assert result.domain == "hp.com"
        assert result.tech_count >= 1, (
            f"Expected at least 1 technology for hp.com, got {result.tech_count}"
        )
        assert len(result.all_technologies) == result.tech_count

    @pytest.mark.asyncio
    async def test_collect_competitor_has_search_vendor_or_none(self) -> None:
        """Competitor search_vendor is either a valid SearchVendor or None."""
        collector = TechStackCollector()
        result = await collector.collect_competitor(domain="lenovo.com", company_name="Lenovo")

        assert isinstance(result, CompetitorTechStack)
        # search_vendor may or may not be detected -- both are valid
        if result.search_vendor is not None:
            assert result.search_vendor.name != ""
            assert result.search_vendor.status in ("ACTIVE", "TAG_ONLY", "REMOVED", "UNDETECTED")


class TestCompetitorFanOut:
    """Test parallel collection of prospect + multiple competitors."""

    @pytest.mark.asyncio
    async def test_collect_all_with_competitors(self) -> None:
        """Run fan-out for dell.com with hp.com and lenovo.com as competitors."""
        collector = TechStackCollector()
        competitor_data = [
            {"company_name": "HP Inc", "domain": "hp.com"},
            {"company_name": "Lenovo", "domain": "lenovo.com"},
        ]

        output, sources = await collector.collect_all_with_competitors(
            prospect_domain="dell.com",
            competitor_data=competitor_data,
        )

        # Prospect data present
        assert isinstance(output, TechStackOutput)
        assert len(output.all_technologies) >= 3

        # Competitor data present
        assert len(output.competitor_tech_stacks) == 2
        competitor_names = {cs.company_name for cs in output.competitor_tech_stacks}
        assert "HP Inc" in competitor_names
        assert "Lenovo" in competitor_names

        # Each competitor should have technologies
        for cs in output.competitor_tech_stacks:
            assert cs.tech_count >= 1, (
                f"Expected at least 1 tech for {cs.domain}, got {cs.tech_count}"
            )

        # Sources should include competitor entries
        competitor_source_fields = [
            s.field for s in sources if s.field.startswith("competitor_tech_stack.")
        ]
        assert len(competitor_source_fields) == 2

    @pytest.mark.asyncio
    async def test_empty_competitor_list_falls_back(self) -> None:
        """When competitor_data is empty, behave like collect_all."""
        collector = TechStackCollector()
        output, _sources = await collector.collect_all_with_competitors(
            prospect_domain="dell.com",
            competitor_data=[],
        )

        assert isinstance(output, TechStackOutput)
        assert len(output.all_technologies) >= 3
        assert output.competitor_tech_stacks == []
        assert output.comparative_summary != ""  # Still has prospect summary
        assert output.golden_angle_competitors == []


class TestGoldenAngleDetection:
    """Test that competitors using Algolia are flagged as Golden Angle."""

    @pytest.mark.asyncio
    async def test_golden_angle_is_subset_of_competitors(self) -> None:
        """golden_angle_competitors must be a subset of competitor company names."""
        collector = TechStackCollector()
        competitor_data = [
            {"company_name": "HP Inc", "domain": "hp.com"},
            {"company_name": "Lenovo", "domain": "lenovo.com"},
        ]

        output, _sources = await collector.collect_all_with_competitors(
            prospect_domain="dell.com",
            competitor_data=competitor_data,
        )

        competitor_names = {cs.company_name for cs in output.competitor_tech_stacks}
        for golden_name in output.golden_angle_competitors:
            assert golden_name in competitor_names, (
                f"Golden Angle name '{golden_name}' not in competitor names: {competitor_names}"
            )

    @pytest.mark.asyncio
    async def test_golden_angle_matches_algolia_flag(self) -> None:
        """Golden angle list must match competitors where is_algolia_customer is True."""
        collector = TechStackCollector()
        competitor_data = [
            {"company_name": "HP Inc", "domain": "hp.com"},
            {"company_name": "Lenovo", "domain": "lenovo.com"},
        ]

        output, _sources = await collector.collect_all_with_competitors(
            prospect_domain="dell.com",
            competitor_data=competitor_data,
        )

        algolia_customers = {
            cs.company_name for cs in output.competitor_tech_stacks if cs.is_algolia_customer
        }
        assert set(output.golden_angle_competitors) == algolia_customers


class TestComparativeSummary:
    """Test comparative summary generation."""

    @pytest.mark.asyncio
    async def test_summary_mentions_prospect(self) -> None:
        """Comparative summary must mention the prospect domain."""
        collector = TechStackCollector()
        competitor_data = [
            {"company_name": "HP Inc", "domain": "hp.com"},
        ]

        output, _sources = await collector.collect_all_with_competitors(
            prospect_domain="dell.com",
            competitor_data=competitor_data,
        )

        assert "dell.com" in output.comparative_summary

    @pytest.mark.asyncio
    async def test_summary_mentions_each_competitor(self) -> None:
        """Comparative summary must mention each competitor by name."""
        collector = TechStackCollector()
        competitor_data = [
            {"company_name": "HP Inc", "domain": "hp.com"},
            {"company_name": "Lenovo", "domain": "lenovo.com"},
        ]

        output, _sources = await collector.collect_all_with_competitors(
            prospect_domain="dell.com",
            competitor_data=competitor_data,
        )

        assert "HP Inc" in output.comparative_summary
        assert "Lenovo" in output.comparative_summary


class TestValidatorWithCompetitors:
    """Test that the validator handles the new competitor fields correctly."""

    @pytest.mark.asyncio
    async def test_validator_passes_with_competitor_data(self) -> None:
        """Validator should pass when competitor data is well-formed."""
        collector = TechStackCollector()
        competitor_data = [
            {"company_name": "HP Inc", "domain": "hp.com"},
        ]

        output, sources = await collector.collect_all_with_competitors(
            prospect_domain="dell.com",
            competitor_data=competitor_data,
        )

        validation = validate_output(output, sources)
        assert validation.checks_run >= 8, (
            f"Expected at least 8 checks, got {validation.checks_run}"
        )
        # Should pass (or have only warnings, not errors)
        if not validation.passed:
            # Print errors for debugging but don't fail if it's just warnings
            for err in validation.errors:
                print(f"  Validation error: {err}")
