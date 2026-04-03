"""End-to-end integration tests for intel-traffic module.

These tests run the full module pipeline (SimilarWeb + Perplexity)
against dell.com with real API calls.

Requires: SIMILARWEB_API_KEY and PERPLEXITY_API_KEY set in .env.

Run with: python3 -m pytest tests/test_traffic_integration.py -v
"""

from __future__ import annotations

import os

import pytest

from prism_platform.core.module import ExecutionContext
from prism_platform.modules.intel_traffic.collector import TrafficCollector
from prism_platform.modules.intel_traffic.enricher import TrafficEnricher
from prism_platform.modules.intel_traffic.module import TrafficModule
from prism_platform.modules.intel_traffic.schemas import TrafficOutput
from prism_platform.modules.intel_traffic.validator import validate_output

# Marker for tests that require real API calls
requires_similarweb = pytest.mark.skipif(
    not os.environ.get("SIMILARWEB_API_KEY"),
    reason="SIMILARWEB_API_KEY required",
)

requires_perplexity = pytest.mark.skipif(
    not os.environ.get("PERPLEXITY_API_KEY"),
    reason="PERPLEXITY_API_KEY required",
)

requires_all_keys = pytest.mark.skipif(
    not (os.environ.get("SIMILARWEB_API_KEY") and os.environ.get("PERPLEXITY_API_KEY")),
    reason="SIMILARWEB_API_KEY and PERPLEXITY_API_KEY required",
)


def _make_context() -> ExecutionContext:
    """Build a test ExecutionContext for dell.com."""
    return ExecutionContext(
        audit_id="test-audit-traffic-001",
        account_id="00000000-0000-0000-0000-000000000001",
        domain="dell.com",
        company_name="Dell Technologies",
        ticker="DELL",
        is_private=False,
    )


@requires_similarweb
class TestCollectorIntegration:
    """Test the SimilarWeb collector with real API calls."""

    @pytest.mark.asyncio
    async def test_collect_domain_returns_data(self) -> None:
        """Collect all SimilarWeb data for dell.com."""
        collector = TrafficCollector()
        result = await collector.collect_domain("dell.com")

        # Monthly visits should have data
        assert isinstance(result["monthly_visits"], list)
        if result["monthly_visits"]:
            mv = result["monthly_visits"][0]
            assert mv.year >= 2025
            assert 1 <= mv.month <= 12
            assert mv.visits > 0

        # Traffic sources should have data
        assert isinstance(result["traffic_sources"], list)

        # At minimum some endpoints should return data
        populated = [k for k, v in result.items() if v]
        assert len(populated) >= 2, (
            f"Expected at least 2 populated endpoints, got {populated}"
        )

    @pytest.mark.asyncio
    async def test_collect_competitor(self) -> None:
        """Collect competitor data for hp.com."""
        collector = TrafficCollector()
        comp = await collector.collect_competitor("hp.com", "HP Inc.")

        assert comp.company_name == "HP Inc."
        assert comp.domain == "hp.com"
        # Some data should be present
        has_data = (
            comp.total_visits is not None
            or len(comp.traffic_sources) > 0
            or len(comp.top_keywords) > 0
        )
        assert has_data, "No data returned for hp.com competitor"

    @pytest.mark.asyncio
    async def test_handles_unknown_domain_gracefully(self) -> None:
        """Collector should not crash on a domain SimilarWeb doesn't track."""
        collector = TrafficCollector()
        result = await collector.collect_domain("this-domain-definitely-does-not-exist-12345.com")
        # Should return empty/default values without crashing
        assert isinstance(result, dict)
        assert isinstance(result["monthly_visits"], list)


@requires_perplexity
class TestEnricherIntegration:
    """Test Google Trends enrichment with real Perplexity API calls."""

    @pytest.mark.asyncio
    async def test_assess_trends_dell(self) -> None:
        """Assess Google Trends momentum for Dell."""
        enricher = TrafficEnricher()
        momentum, calls, cost = await enricher.assess_trends(
            "Dell Technologies", "dell.com"
        )

        assert momentum is not None
        assert momentum.company_name == "Dell Technologies"
        assert momentum.direction in ("rising", "stable", "declining", "insufficient_data")
        assert calls == 1
        assert cost >= 0

    @pytest.mark.asyncio
    async def test_assess_competitor_trends(self) -> None:
        """Assess trends for multiple competitors."""
        enricher = TrafficEnricher()
        competitors = [
            {"company_name": "HP Inc.", "domain": "hp.com"},
            {"company_name": "Lenovo", "domain": "lenovo.com"},
        ]
        results, calls, cost = await enricher.assess_competitor_trends(competitors)

        assert len(results) >= 1
        assert calls >= 1
        for r in results:
            assert r.direction in ("rising", "stable", "declining", "insufficient_data")


@requires_all_keys
class TestFullPipelineIntegration:
    """Test the full collector -> enricher -> validator pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_dell(self) -> None:
        """Full pipeline: SimilarWeb + Perplexity -> TrafficOutput -> validation."""
        collector = TrafficCollector()
        enricher = TrafficEnricher()

        # Step 1: Collect prospect data
        prospect_data = await collector.collect_domain("dell.com")

        # Step 2: Assess Google Trends
        trends, _, _ = await enricher.assess_trends("Dell Technologies", "dell.com")

        # Step 3: Build output
        from prism_platform.core.types import EvidenceTier, Source

        output = TrafficOutput(
            domain="dell.com",
            monthly_visits=prospect_data.get("monthly_visits", []),
            traffic_sources=prospect_data.get("traffic_sources", []),
            engagement=prospect_data.get("engagement"),
            device_split=prospect_data.get("device_split"),
            top_countries=prospect_data.get("top_countries", []),
            organic_keywords=prospect_data.get("organic_keywords", []),
            paid_keywords=prospect_data.get("paid_keywords", []),
            google_trends=trends,
        )

        assert output.domain == "dell.com"
        assert isinstance(output, TrafficOutput)

        # Step 4: Validate
        sources = [
            Source(
                field="similarweb",
                value="SimilarWeb API data",
                tier=EvidenceTier.VERIFIED,
                source_label="SimilarWeb API",
            )
        ]
        validation = validate_output(output, sources, expected_domain="dell.com")

        # Log validation results for visibility
        if not validation.passed:
            print(f"Validation errors: {validation.errors}")
            print(f"Validation warnings: {validation.warnings}")

        # We expect at least partial pass -- SimilarWeb may not return all data
        assert validation.checks_run == 9
        assert validation.checks_passed >= 5, (
            f"Only {validation.checks_passed}/9 checks passed. "
            f"Errors: {validation.errors}, Warnings: {validation.warnings}"
        )


@requires_all_keys
class TestTrafficModuleHealthCheck:
    """Test module health check."""

    @pytest.mark.asyncio
    async def test_health_check_passes(self) -> None:
        """Health check should pass when API keys are set."""
        module = TrafficModule()
        healthy = await module.health_check()
        assert healthy is True, (
            "Health check failed -- check SIMILARWEB_API_KEY and PERPLEXITY_API_KEY in .env"
        )
