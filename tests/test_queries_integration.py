"""End-to-end integration tests for intel-queries module.

These tests run the enricher pipeline (Gemini via Instructor) against
real APIs using dell.com as the test domain.

Requires: GEMINI_API_KEY set in .env.

Run with: pytest tests/test_queries_integration.py -v
"""

from __future__ import annotations

import os

import pytest

from prism_platform.core.types import EvidenceTier, Source
from prism_platform.modules.intel_queries.collector import QueriesCollector
from prism_platform.modules.intel_queries.enricher import QueriesEnricher
from prism_platform.modules.intel_queries.module import QueriesModule
from prism_platform.modules.intel_queries.schemas import (
    QueriesOutput,
    TestQuery,
)
from prism_platform.modules.intel_queries.validator import validate_output

# Marker for tests that require real Gemini API
requires_gemini = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY required for integration tests",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dell_context() -> dict:
    """Build a realistic Dell context for query generation."""
    return QueriesCollector().collect_context(
        domain="dell.com",
        company_name="Dell Technologies",
        industry="Enterprise Technology",
        sub_vertical="Consumer Electronics",
        product_categories=[
            "Laptops",
            "Desktops",
            "Monitors",
            "Servers",
            "Storage",
            "Networking",
            "Workstations",
        ],
        competitor_domains=[
            {"company_name": "HP Inc.", "domain": "hp.com"},
            {"company_name": "Lenovo", "domain": "lenovo.com"},
            {"company_name": "Apple", "domain": "apple.com"},
        ],
    )


# ---------------------------------------------------------------------------
# Module metadata tests (no API needed)
# ---------------------------------------------------------------------------


class TestQueriesModuleMetadata:
    """Test module registration and metadata."""

    def test_module_name(self) -> None:
        module = QueriesModule()
        assert module.name == "intel-queries"

    def test_module_version(self) -> None:
        module = QueriesModule()
        assert module.version == "0.1.0"

    def test_module_layer(self) -> None:
        module = QueriesModule()
        assert module.layer == "intelligence"

    def test_module_dependencies(self) -> None:
        module = QueriesModule()
        assert "intel-company" in module.dependencies
        assert "intel-techstack" in module.dependencies

    def test_module_requires_llm(self) -> None:
        module = QueriesModule()
        assert module.requires_llm is True

    def test_module_timeout(self) -> None:
        module = QueriesModule()
        assert module.timeout_seconds == 120

    def test_module_schemas(self) -> None:
        module = QueriesModule()
        assert module.input_schema.__name__ == "QueriesInput"
        assert module.output_schema.__name__ == "QueriesOutput"

    def test_module_in_registry(self) -> None:
        from prism_platform.core.registry import MODULE_REGISTRY, register_all_modules

        register_all_modules()
        assert "intel-queries" in MODULE_REGISTRY


# ---------------------------------------------------------------------------
# Enricher integration tests (real Gemini API)
# ---------------------------------------------------------------------------


class TestEnricherIntegration:
    """Tests that call real Gemini API for query generation."""

    @requires_gemini
    @pytest.mark.asyncio
    async def test_generate_prospect_queries_dell(self) -> None:
        """Generate 16 prospect queries for Dell and verify structure."""
        context = _dell_context()
        enricher = QueriesEnricher()

        queries, llm_calls, cost = await enricher.generate_prospect_queries(context)

        # Must have at least 14 queries (spec allows some tolerance)
        assert len(queries) >= 14, f"Expected >= 14 queries, got {len(queries)}"

        # Must have queries (non-zero)
        assert llm_calls >= 1

        # Check cost is reasonable
        assert cost >= 0.0
        assert cost < 1.0  # Should be well under $1

        # Verify all queries are TestQuery instances
        for q in queries:
            assert isinstance(q, TestQuery)
            assert q.target_domain == "dell.com"
            assert q.query.strip() != ""
            assert q.expected_behavior.strip() != ""
            assert q.what_good_looks_like.strip() != ""
            assert q.what_bad_looks_like.strip() != ""

        # Verify type coverage
        actual_types = {q.query_type for q in queries}
        assert len(actual_types) >= 6, (
            f"Expected >= 6 query types covered, got {len(actual_types)}: {actual_types}"
        )

    @requires_gemini
    @pytest.mark.asyncio
    async def test_generate_competitor_queries_hp(self) -> None:
        """Generate competitor queries for HP."""
        context = _dell_context()
        enricher = QueriesEnricher()

        competitor = {"company_name": "HP Inc.", "domain": "hp.com"}
        query_set, llm_calls, _cost = await enricher.generate_competitor_queries(
            context, competitor
        )

        assert query_set.company_name == "HP Inc."
        assert query_set.domain == "hp.com"
        assert len(query_set.queries) >= 4  # At least half of requested 8
        assert llm_calls >= 1

        for q in query_set.queries:
            assert q.target_domain == "hp.com"
            assert q.query.strip() != ""

    @requires_gemini
    @pytest.mark.asyncio
    async def test_difficulty_distribution_computed(self) -> None:
        """Verify difficulty distribution computation."""
        context = _dell_context()
        enricher = QueriesEnricher()

        queries, _, _ = await enricher.generate_prospect_queries(context)
        dist = enricher.compute_difficulty_distribution(queries)

        total = dist.easy_count + dist.medium_count + dist.hard_count
        assert total == len(queries)
        assert dist.easy_count >= 0
        assert dist.medium_count >= 0
        assert dist.hard_count >= 0


# ---------------------------------------------------------------------------
# Full pipeline integration test
# ---------------------------------------------------------------------------


class TestFullPipelineIntegration:
    """Full pipeline test: context -> generate -> validate."""

    @requires_gemini
    @pytest.mark.asyncio
    async def test_full_pipeline_dell(self) -> None:
        """Run the full query generation pipeline for Dell.

        Steps:
        1. Build context from known Dell data
        2. Generate prospect queries
        3. Generate one competitor query set
        4. Assemble QueriesOutput
        5. Validate output
        """
        context = _dell_context()
        enricher = QueriesEnricher()

        # Step 1-2: Generate prospect queries
        prospect_queries, llm_calls, cost = await enricher.generate_prospect_queries(context)
        total_llm_calls = llm_calls
        total_cost = cost

        # Step 3: Generate one competitor query set
        competitor = {"company_name": "HP Inc.", "domain": "hp.com"}
        comp_set, comp_calls, comp_cost = await enricher.generate_competitor_queries(
            context, competitor
        )
        total_llm_calls += comp_calls
        total_cost += comp_cost

        # Step 4: Assemble output
        dist = enricher.compute_difficulty_distribution(prospect_queries)
        types_covered = sorted({q.query_type for q in prospect_queries})

        output = QueriesOutput(
            domain="dell.com",
            industry=context["industry"],
            sub_vertical=context["sub_vertical"],
            prospect_queries=prospect_queries,
            competitor_query_sets=[comp_set],
            difficulty_distribution=dist,
            query_count=len(prospect_queries),
            types_covered=types_covered,
            generation_notes=f"Integration test: {total_llm_calls} LLM calls, ${total_cost:.4f}",
        )

        # Step 5: Validate
        sources = [
            Source(
                field="prospect_queries",
                value=f"Gemini generated {len(prospect_queries)} queries",
                tier=EvidenceTier.ESTIMATE,
                source_label="Gemini via Instructor",
                method="llm_extraction",
            ),
        ]
        validation = validate_output(output, sources)

        # Print for debugging
        print("\n--- Full Pipeline Results ---")
        print(f"Prospect queries: {len(prospect_queries)}")
        print(f"Types covered: {types_covered}")
        print(
            f"Difficulty: easy={dist.easy_count} medium={dist.medium_count} hard={dist.hard_count}"
        )
        print(f"Competitor sets: {len(output.competitor_query_sets)}")
        print(f"LLM calls: {total_llm_calls}, Cost: ${total_cost:.4f}")
        print(f"Validation passed: {validation.passed}")
        if validation.errors:
            print(f"Errors: {validation.errors}")
        if validation.warnings:
            print(f"Warnings: {validation.warnings}")

        # Assertions
        assert output.query_count >= 14
        assert len(output.competitor_query_sets) == 1
        assert total_llm_calls >= 2

        # Validation may have minor issues (LLM not always returning exact counts)
        # but core checks should pass
        assert validation.checks_run == 9
        assert validation.checks_passed >= 6, (
            f"Expected >= 6 checks passed, got {validation.checks_passed}. "
            f"Errors: {validation.errors}"
        )

    @requires_gemini
    @pytest.mark.asyncio
    async def test_queries_are_realistic_for_dell(self) -> None:
        """Verify generated queries are actually relevant to Dell's business."""
        context = _dell_context()
        enricher = QueriesEnricher()

        queries, _, _ = await enricher.generate_prospect_queries(context)

        # At least some queries should mention Dell-relevant terms
        all_query_text = " ".join(q.query.lower() for q in queries)

        # Dell sells laptops, monitors, servers -- at least one should appear
        tech_terms = [
            "laptop",
            "monitor",
            "server",
            "desktop",
            "xps",
            "latitude",
            "inspiron",
            "optiplex",
            "poweredge",
            "dell",
        ]
        matches = [t for t in tech_terms if t in all_query_text]

        assert len(matches) >= 2, (
            f"Expected at least 2 Dell-relevant terms in queries, found {matches}. "
            f"Query text: {all_query_text[:500]}"
        )
