"""Integration tests for intel-hiring module.

Full pipeline: collect -> enrich -> validate with real API calls.
Uses dell.com as the standard test domain.
"""

from __future__ import annotations

import os

import pytest

from prism_platform.core.module import ExecutionContext
from prism_platform.core.types import ModuleResult
from prism_platform.modules.intel_hiring.module import (
    HiringModule,
    _extract_competitors,
    _extract_executives,
)
from prism_platform.modules.intel_hiring.schemas import HiringOutput
from prism_platform.modules.intel_hiring.validator import validate_output

# Skip all tests if both API keys are missing
pytestmark = pytest.mark.skipif(
    not os.environ.get("PERPLEXITY_API_KEY") or not os.environ.get("GEMINI_API_KEY"),
    reason="PERPLEXITY_API_KEY and/or GEMINI_API_KEY not set",
)


# ---------------------------------------------------------------------------
# Helper data
# ---------------------------------------------------------------------------

DELL_INTELLIGENCE = {
    "executives": [
        {
            "full_name": "Michael Dell",
            "title": "Chairman and CEO",
            "relevance": "economic_buyer",
        },
        {
            "full_name": "Jeff Clarke",
            "title": "Vice Chairman and COO",
            "relevance": "economic_buyer",
        },
        {
            "full_name": "Yvonne McGill",
            "title": "Chief Financial Officer",
            "relevance": "economic_buyer",
        },
    ],
    "competitors": [
        {"company_name": "HP Inc.", "domain": "hp.com"},
        {"company_name": "Lenovo", "domain": "lenovo.com"},
    ],
}


def _make_context() -> ExecutionContext:
    """Build a test ExecutionContext for dell.com."""
    return ExecutionContext(
        audit_id="test-audit-hiring-001",
        account_id="test-account-001",
        domain="dell.com",
        company_name="Dell Technologies",
        ticker="DELL",
        is_private=False,
    )


# ---------------------------------------------------------------------------
# Helper extraction tests (no API calls)
# ---------------------------------------------------------------------------


class TestHelperExtraction:
    """Tests for _extract_executives and _extract_competitors."""

    def test_extract_executives(self) -> None:
        """Extracts and normalizes executive list."""
        execs = _extract_executives(DELL_INTELLIGENCE)
        assert len(execs) == 3
        assert execs[0]["name"] == "Michael Dell"
        assert execs[0]["title"] == "Chairman and CEO"
        assert execs[0]["relevance"] == "economic_buyer"

    def test_extract_executives_empty(self) -> None:
        """Returns empty list when no executives in intelligence."""
        execs = _extract_executives({})
        assert execs == []

    def test_extract_executives_alt_key(self) -> None:
        """Handles 'name' key instead of 'full_name'."""
        data = {
            "executives": [{"name": "Jane Doe", "title": "CTO", "relevance": "technical_evaluator"}]
        }
        execs = _extract_executives(data)
        assert execs[0]["name"] == "Jane Doe"

    def test_extract_competitors(self) -> None:
        """Extracts competitor list."""
        comps = _extract_competitors(DELL_INTELLIGENCE)
        assert len(comps) == 2
        assert comps[0]["company_name"] == "HP Inc."
        assert comps[0]["domain"] == "hp.com"

    def test_extract_competitors_empty(self) -> None:
        """Returns empty list when no competitors in intelligence."""
        comps = _extract_competitors({})
        assert comps == []


# ---------------------------------------------------------------------------
# Enricher integration test
# ---------------------------------------------------------------------------


class TestHiringEnricherIntegration:
    """Tests that the enricher structures raw data via Gemini."""

    @pytest.mark.asyncio
    async def test_enrich_prospect_roles(self) -> None:
        """Enricher classifies roles from raw Perplexity text."""
        from prism_platform.modules.intel_hiring.enricher import HiringEnricher

        enricher = HiringEnricher()

        # Simulated raw data (realistic structure from Perplexity fallback)
        raw_data = {
            "prospect_roles": [
                (
                    "Open positions at Dell Technologies related to search and discovery:\n"
                    "1. Senior Search Engineer - Austin, TX - Posted 2026-03-10\n"
                    "   Building next-gen search platform. Elasticsearch experience required.\n"
                    "2. VP of Digital Commerce - Round Rock, TX - Posted 2026-03-01\n"
                    "   Leading digital transformation including search and personalization.\n"
                    "3. Product Manager, Search & Discovery - Remote - Posted 2026-02-28\n"
                    "   Evaluating search vendors and managing search product roadmap.\n"
                ),
            ],
            "competitor_roles": {},
            "champion_signals": {},
            "source_type": "perplexity",
        }

        executives = [
            {"name": "Michael Dell", "title": "Chairman and CEO", "relevance": "economic_buyer"},
        ]

        output, llm_calls, cost = await enricher.enrich(
            domain="dell.com",
            company_name="Dell Technologies",
            raw_data=raw_data,
            executives=executives,
        )

        assert isinstance(output, HiringOutput)
        assert output.domain == "dell.com"
        assert len(output.open_roles) >= 1
        assert llm_calls >= 1
        assert cost >= 0.0

        # Verify roles have required fields
        for role in output.open_roles:
            assert role.title.strip() != ""


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------


class TestHiringValidator:
    """Tests for the validator with realistic data."""

    def test_valid_output_passes(self) -> None:
        """A well-formed output passes validation."""
        from prism_platform.core.types import EvidenceTier, Source

        output = HiringOutput(
            domain="dell.com",
            open_roles=[
                {  # type: ignore[arg-type]
                    "title": "Senior Search Engineer",
                    "source": "perplexity",
                    "company_name": "Dell Technologies",
                }
            ],
            role_count_by_tier={"tier4_user": 1},
            search_related_count=0,
            hiring_velocity={  # type: ignore[arg-type]
                "roles_last_30d": 5,
                "roles_last_90d": 15,
                "trend": "steady",
                "interpretation": "Stable hiring pace.",
            },
            build_vs_buy={  # type: ignore[arg-type]
                "signal": "buy",
                "evidence": ["Hiring PM for search evaluation"],
                "confidence": "medium",
            },
            buying_committee={  # type: ignore[arg-type]
                "members": [
                    {"name": "Jane Doe", "title": "VP Engineering", "role": "economic_buyer"}
                ],
                "confidence": "medium",
                "methodology": "executive list",
            },
            hiring_summary="Dell is hiring search-related roles.",
        )

        sources = [
            Source(
                field="open_roles",
                value="1 roles collected",
                tier=EvidenceTier.WEBSEARCH,
                source_label="Perplexity sonar-pro",
                method="llm_extraction",
            )
        ]

        result = validate_output(output, sources)
        assert result.passed is True
        assert result.checks_run == 9
        assert result.checks_passed >= 8

    def test_empty_output_fails(self) -> None:
        """An empty output fails validation."""
        output = HiringOutput(domain="dell.com")
        result = validate_output(output, [])
        assert result.passed is False
        assert len(result.errors) >= 2  # no roles+summary, no sources

    def test_mismatched_tier_count_fails(self) -> None:
        """Mismatched role_count_by_tier triggers validation error."""
        from prism_platform.core.types import EvidenceTier, Source

        output = HiringOutput(
            domain="dell.com",
            open_roles=[
                {  # type: ignore[arg-type]
                    "title": "Search Engineer",
                    "source": "perplexity",
                    "company_name": "Dell",
                }
            ],
            role_count_by_tier={"tier3_champion": 2},  # Mismatch: 2 vs 1 role
            hiring_summary="Dell is hiring.",
        )
        sources = [
            Source(
                field="open_roles",
                value="1 roles",
                tier=EvidenceTier.WEBSEARCH,
                source_label="Perplexity",
                method="llm_extraction",
            )
        ]

        result = validate_output(output, sources)
        assert result.passed is False
        assert any("role_count_by_tier" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Full module integration test
# ---------------------------------------------------------------------------


class TestHiringModuleIntegration:
    """Full pipeline integration test with real API calls."""

    @pytest.mark.asyncio
    async def test_full_pipeline_dell(self) -> None:
        """Run the full hiring pipeline for dell.com with real APIs.

        This test makes real Perplexity and Gemini API calls.
        It verifies the complete collect -> enrich -> validate flow.
        """
        module = HiringModule()
        context = _make_context()

        result = await module.execute(context, intelligence=DELL_INTELLIGENCE)

        # Basic result checks
        assert isinstance(result, ModuleResult)
        assert result.module_name == "intel-hiring"
        assert result.status in ("success", "partial")
        assert result.duration_ms > 0
        assert result.llm_calls >= 1

        # Deserialize and check output
        output = HiringOutput.model_validate(result.output)
        assert output.domain == "dell.com"

        # Sources should be populated
        assert len(result.sources) >= 1

        # Validate
        validation = await module.validate(result)
        assert validation.checks_run >= 8

    @pytest.mark.asyncio
    async def test_full_pipeline_no_intelligence(self) -> None:
        """Run the pipeline without intel-company data (fallback mode)."""
        module = HiringModule()
        context = _make_context()

        result = await module.execute(context, intelligence=None)

        assert isinstance(result, ModuleResult)
        assert result.module_name == "intel-hiring"
        assert result.status in ("success", "partial")

        output = HiringOutput.model_validate(result.output)
        assert output.domain == "dell.com"

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        """Health check returns True when API keys are set."""
        module = HiringModule()
        is_healthy = await module.health_check()
        assert is_healthy is True
