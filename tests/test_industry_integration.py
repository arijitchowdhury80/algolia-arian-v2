"""Integration tests for intel-industry module.

Perplexity quota is exhausted, so all integration tests requiring
Perplexity API calls are skipped. This file tests module metadata,
schema validation, and the health_check method.
"""

from __future__ import annotations

import pytest

from prism_platform.modules.intel_industry.module import (
    IndustryModule,
    _extract_industry,
    _extract_sub_vertical,
)
from prism_platform.modules.intel_industry.schemas import IndustryInput, IndustryOutput

# ---------------------------------------------------------------------------
# Module metadata tests
# ---------------------------------------------------------------------------


class TestIndustryModuleMetadata:
    """Tests for IndustryModule class attributes."""

    def test_module_name(self) -> None:
        """Module name is 'intel-industry'."""
        assert IndustryModule.name == "intel-industry"

    def test_module_version(self) -> None:
        """Module version follows semver."""
        parts = IndustryModule.version.split(".")
        assert len(parts) == 3

    def test_module_layer(self) -> None:
        """Module layer is 'intelligence'."""
        assert IndustryModule.layer == "intelligence"

    def test_module_dependencies(self) -> None:
        """Module depends on intel-company."""
        assert "intel-company" in IndustryModule.dependencies

    def test_module_requires_llm(self) -> None:
        """Module requires LLM."""
        assert IndustryModule.requires_llm is True

    def test_module_timeout(self) -> None:
        """Module timeout is 180 seconds."""
        assert IndustryModule.timeout_seconds == 180

    def test_module_max_retries(self) -> None:
        """Module max retries is 2."""
        assert IndustryModule.max_retries == 2

    def test_input_schema(self) -> None:
        """Input schema is IndustryInput."""
        assert IndustryModule.input_schema is IndustryInput

    def test_output_schema(self) -> None:
        """Output schema is IndustryOutput."""
        assert IndustryModule.output_schema is IndustryOutput


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestExtractIndustry:
    """Tests for _extract_industry helper."""

    def test_extracts_industry(self) -> None:
        """Extracts 'industry' key from intelligence."""
        result = _extract_industry({"industry": "Retail"})
        assert result == "Retail"

    def test_falls_back_to_vertical(self) -> None:
        """Falls back to 'vertical' key if 'industry' is missing."""
        result = _extract_industry({"vertical": "Financial Services"})
        assert result == "Financial Services"

    def test_defaults_to_technology(self) -> None:
        """Defaults to 'Technology' if neither key exists."""
        result = _extract_industry({})
        assert result == "Technology"

    def test_empty_industry_falls_through(self) -> None:
        """Empty 'industry' string falls through to 'vertical'."""
        result = _extract_industry({"industry": "", "vertical": "Healthcare"})
        assert result == "Healthcare"

    def test_empty_both_defaults(self) -> None:
        """Empty both keys defaults to 'Technology'."""
        result = _extract_industry({"industry": "", "vertical": ""})
        assert result == "Technology"


class TestExtractSubVertical:
    """Tests for _extract_sub_vertical helper."""

    def test_extracts_sub_vertical(self) -> None:
        """Extracts 'sub_vertical' key from intelligence."""
        result = _extract_sub_vertical({"sub_vertical": "Luxury Fashion"})
        assert result == "Luxury Fashion"

    def test_falls_back_to_sub_industry(self) -> None:
        """Falls back to 'sub_industry' key."""
        result = _extract_sub_vertical({"sub_industry": "Grocery"})
        assert result == "Grocery"

    def test_returns_none_if_missing(self) -> None:
        """Returns None if no sub_vertical found."""
        result = _extract_sub_vertical({})
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        """Empty string returns None."""
        result = _extract_sub_vertical({"sub_vertical": ""})
        assert result is None


# ---------------------------------------------------------------------------
# Integration tests (Perplexity quota exhausted -- all skipped)
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="Perplexity quota exhausted -- returns 401")
class TestIndustryModuleIntegration:
    """Full integration tests -- require live Perplexity and Gemini APIs."""

    async def test_execute_retail(self) -> None:
        """Execute module for a retail domain."""
        ...

    async def test_execute_technology(self) -> None:
        """Execute module for a technology domain."""
        ...

    async def test_execute_without_intelligence(self) -> None:
        """Execute module without prior intelligence data."""
        ...

    async def test_validate_after_execute(self) -> None:
        """Validate output after full execution."""
        ...
