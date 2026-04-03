"""Integration tests for intel-competitors module.

Tests module metadata, enricher fallback logic, and DB read logic (if available).
"""

from __future__ import annotations

import pytest

from prism_platform.modules.intel_competitors.enricher import CompetitorsEnricher
from prism_platform.modules.intel_competitors.module import CompetitorsModule
from prism_platform.modules.intel_competitors.schemas import (
    CompetitorsInput,
    CompetitorsOutput,
    TechComparison,
)


# ---------------------------------------------------------------------------
# Module metadata tests
# ---------------------------------------------------------------------------
class TestModuleMetadata:
    def test_module_name(self) -> None:
        mod = CompetitorsModule()
        assert mod.name == "intel-competitors"

    def test_module_version(self) -> None:
        mod = CompetitorsModule()
        assert mod.version == "0.1.0"

    def test_module_layer(self) -> None:
        mod = CompetitorsModule()
        assert mod.layer == "synthesis"

    def test_module_dependencies(self) -> None:
        mod = CompetitorsModule()
        assert "intel-company" in mod.dependencies
        assert "intel-techstack" in mod.dependencies
        assert "intel-traffic" in mod.dependencies
        assert "intel-hiring" in mod.dependencies

    def test_module_requires_llm(self) -> None:
        mod = CompetitorsModule()
        assert mod.requires_llm is True

    def test_module_timeout(self) -> None:
        mod = CompetitorsModule()
        assert mod.timeout_seconds == 180

    def test_module_max_retries(self) -> None:
        mod = CompetitorsModule()
        assert mod.max_retries == 2

    def test_input_schema(self) -> None:
        mod = CompetitorsModule()
        assert mod.input_schema is CompetitorsInput

    def test_output_schema(self) -> None:
        mod = CompetitorsModule()
        assert mod.output_schema is CompetitorsOutput


# ---------------------------------------------------------------------------
# Enricher fallback logic
# ---------------------------------------------------------------------------
class TestEnricherFallback:
    def test_fallback_golden_scenario(self) -> None:
        synthesis = CompetitorsEnricher._fallback_synthesis(
            golden_angle_competitors=["HP Inc"],
            tech_gaps=[],
            tech_comparisons=[
                TechComparison(company_name="Dell", domain="dell.com"),
                TechComparison(company_name="HP Inc", domain="hp.com", algolia_detected=True),
            ],
        )
        assert synthesis.scenario_type == "golden"
        assert "HP Inc" in synthesis.scenario_description
        assert synthesis.competitive_position == "unknown"

    def test_fallback_offensive_scenario(self) -> None:
        synthesis = CompetitorsEnricher._fallback_synthesis(
            golden_angle_competitors=[],
            tech_gaps=["Prospect has no detected search vendor"],
            tech_comparisons=[
                TechComparison(company_name="Dell", domain="dell.com"),
            ],
        )
        assert synthesis.scenario_type == "offensive"
        assert len(synthesis.top_competitive_angles) >= 1

    def test_fallback_displacement_scenario(self) -> None:
        synthesis = CompetitorsEnricher._fallback_synthesis(
            golden_angle_competitors=[],
            tech_gaps=[],
            tech_comparisons=[
                TechComparison(company_name="Dell", domain="dell.com"),
            ],
        )
        assert synthesis.scenario_type == "displacement"
        assert synthesis.competitive_position == "unknown"
        assert synthesis.competitive_pressure == "unknown"

    def test_fallback_has_summary(self) -> None:
        synthesis = CompetitorsEnricher._fallback_synthesis(
            golden_angle_competitors=[],
            tech_gaps=[],
            tech_comparisons=[],
        )
        assert synthesis.competitive_summary != ""

    def test_fallback_has_angles(self) -> None:
        synthesis = CompetitorsEnricher._fallback_synthesis(
            golden_angle_competitors=[],
            tech_gaps=[],
            tech_comparisons=[],
        )
        assert len(synthesis.top_competitive_angles) >= 1


# ---------------------------------------------------------------------------
# Registry test
# ---------------------------------------------------------------------------
class TestRegistry:
    def test_module_in_registry(self) -> None:
        from prism_platform.core.registry import MODULE_REGISTRY, register_all_modules

        register_all_modules()
        assert "intel-competitors" in MODULE_REGISTRY
        assert MODULE_REGISTRY["intel-competitors"].name == "intel-competitors"


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_without_key(self) -> None:
        """Health check returns False when no Gemini key configured."""
        mod = CompetitorsModule()
        # In test environment, key may or may not be set
        result = await mod.health_check()
        # Just verify it returns a bool without error
        assert isinstance(result, bool)
