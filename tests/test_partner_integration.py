"""Integration tests for intel-partner module.

Module metadata tests do NOT require API calls.
Full pipeline tests are skipped (Perplexity quota exhausted).
"""

from __future__ import annotations

import os

import pytest

from prism_platform.modules.intel_partner.module import (
    PartnerModule,
    _extract_competitors,
    _extract_industry,
)
from prism_platform.modules.intel_partner.schemas import PartnerInput, PartnerOutput

# ---------------------------------------------------------------------------
# Module metadata tests (no API calls)
# ---------------------------------------------------------------------------


class TestPartnerModuleMetadata:
    """Tests for PartnerModule class attributes and metadata."""

    def test_module_name(self) -> None:
        """Module name is 'intel-partner'."""
        module = PartnerModule()
        assert module.name == "intel-partner"

    def test_module_version(self) -> None:
        """Module version is '0.1.0'."""
        module = PartnerModule()
        assert module.version == "0.1.0"

    def test_module_layer(self) -> None:
        """Module layer is 'intelligence'."""
        module = PartnerModule()
        assert module.layer == "intelligence"

    def test_module_dependencies(self) -> None:
        """Module depends on intel-company and intel-techstack."""
        module = PartnerModule()
        assert "intel-company" in module.dependencies
        assert "intel-techstack" in module.dependencies

    def test_module_requires_llm(self) -> None:
        """Module requires LLM."""
        module = PartnerModule()
        assert module.requires_llm is True

    def test_module_timeout(self) -> None:
        """Module timeout is 300 seconds."""
        module = PartnerModule()
        assert module.timeout_seconds == 300

    def test_module_max_retries(self) -> None:
        """Module max_retries is 2."""
        module = PartnerModule()
        assert module.max_retries == 2

    def test_input_schema(self) -> None:
        """Module input_schema is PartnerInput."""
        module = PartnerModule()
        assert module.input_schema is PartnerInput

    def test_output_schema(self) -> None:
        """Module output_schema is PartnerOutput."""
        module = PartnerModule()
        assert module.output_schema is PartnerOutput

    def test_module_description(self) -> None:
        """Module description is not empty."""
        module = PartnerModule()
        assert module.description
        assert len(module.description) > 10


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_extract_industry_present(self) -> None:
        """_extract_industry returns industry when present."""
        intelligence = {"industry": "Technology"}
        assert _extract_industry(intelligence) == "Technology"

    def test_extract_industry_from_vertical(self) -> None:
        """_extract_industry falls back to vertical key."""
        intelligence = {"vertical": "Retail"}
        assert _extract_industry(intelligence) == "Retail"

    def test_extract_industry_missing(self) -> None:
        """_extract_industry returns 'Unknown' when missing."""
        intelligence: dict = {}
        assert _extract_industry(intelligence) == "Unknown"

    def test_extract_competitors_present(self) -> None:
        """_extract_competitors returns competitors when present."""
        intelligence = {
            "competitors": [
                {"company_name": "HP", "domain": "hp.com"},
                {"company_name": "Lenovo", "domain": "lenovo.com"},
            ],
        }
        result = _extract_competitors(intelligence)
        assert len(result) == 2
        assert result[0]["company_name"] == "HP"
        assert result[0]["domain"] == "hp.com"
        assert result[1]["company_name"] == "Lenovo"

    def test_extract_competitors_empty(self) -> None:
        """_extract_competitors returns empty list when missing."""
        intelligence: dict = {}
        assert _extract_competitors(intelligence) == []

    def test_extract_competitors_missing_keys(self) -> None:
        """_extract_competitors handles competitors with missing keys."""
        intelligence = {
            "competitors": [
                {"company_name": "HP"},
                {"domain": "lenovo.com"},
            ],
        }
        result = _extract_competitors(intelligence)
        assert len(result) == 2
        assert result[0]["company_name"] == "HP"
        assert result[0]["domain"] == ""
        assert result[1]["company_name"] == ""
        assert result[1]["domain"] == "lenovo.com"


# ---------------------------------------------------------------------------
# Health check test
# ---------------------------------------------------------------------------


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_returns_bool(self) -> None:
        """health_check returns a boolean."""
        module = PartnerModule()
        result = await module.health_check()
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Registry integration test
# ---------------------------------------------------------------------------


class TestRegistryIntegration:
    """Tests that the module is registered properly."""

    def test_module_in_registry(self) -> None:
        """PartnerModule is registered in MODULE_REGISTRY."""
        from prism_platform.core.registry import MODULE_REGISTRY, register_all_modules

        register_all_modules()
        assert "intel-partner" in MODULE_REGISTRY
        assert MODULE_REGISTRY["intel-partner"].name == "intel-partner"


# ---------------------------------------------------------------------------
# Skip behavior tests (no API for partial result)
# ---------------------------------------------------------------------------


class TestSkipBehavior:
    """Tests verifying skip/degrade behavior when APIs unavailable."""

    def test_output_schema_allows_empty_lists(self) -> None:
        """PartnerOutput allows all empty lists for degraded mode."""
        output = PartnerOutput(domain="dell.com")
        assert output.partner_overlaps == []
        assert output.co_sell_opportunities == []
        assert output.si_relationships == []
        assert output.vertical_case_studies == []
        assert output.recent_partnerships == []
        assert output.competitor_partners == []
        assert output.partner_play is None
        assert output.partner_summary == ""
        assert output.crossbeam_available is False

    def test_output_schema_allows_partial_data(self) -> None:
        """PartnerOutput allows partial data (some sections populated, others empty)."""
        from prism_platform.modules.intel_partner.schemas import PartnerOverlap

        output = PartnerOutput(
            domain="dell.com",
            partner_overlaps=[PartnerOverlap(partner_name="Accenture")],
            partner_summary="Partial data collected.",
        )
        assert len(output.partner_overlaps) == 1
        assert output.co_sell_opportunities == []
        assert output.partner_summary == "Partial data collected."


# ---------------------------------------------------------------------------
# Full pipeline integration tests (SKIPPED)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("PERPLEXITY_API_KEY") or True,
    reason="Perplexity quota exhausted -- full pipeline tests require live API",
)
class TestFullPipeline:
    """Full pipeline integration tests requiring live Perplexity + Gemini APIs."""

    @pytest.mark.asyncio
    async def test_execute_dell(self) -> None:
        """Placeholder for full execute test with dell.com."""
        pass

    @pytest.mark.asyncio
    async def test_validate_after_execute(self) -> None:
        """Placeholder for validate after execute test."""
        pass
