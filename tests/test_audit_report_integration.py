"""Integration tests for audit-report enricher with real Gemini API calls.

These tests make real API calls to Gemini for dimension scoring,
pre-call brief generation, leave-behind generation, and audit summary.
Run with: pytest tests/test_audit_report_integration.py -v
"""

from __future__ import annotations

import os

import pytest

from prism_platform.modules.audit_report.enricher import AuditReportEnricher
from prism_platform.modules.audit_report.schemas import (
    ALL_DIMENSIONS,
    AuditReportOutput,
    DimensionScore,
    LeaveBehind,
    PreCallBrief,
)

# Skip all tests if GEMINI_API_KEY is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set -- skipping Gemini integration tests",
)


# ---------------------------------------------------------------------------
# Synthetic upstream data for testing
# ---------------------------------------------------------------------------


def _make_collected_data() -> dict:
    """Build synthetic collected data representing upstream module outputs."""
    return {
        "intel-company": {
            "legal_name": "Dell Technologies Inc.",
            "common_name": "Dell",
            "domain": "dell.com",
            "headquarters": "Round Rock, Texas, USA",
            "employee_count": 133000,
            "business_model": (
                "Dell Technologies designs, develops, and sells computing hardware, "
                "software, and IT services. Revenue comes from PC sales, enterprise "
                "servers, storage, and cloud solutions."
            ),
            "industry": "Enterprise Technology",
            "is_public": True,
            "ticker": "DELL",
            "executives": [
                {
                    "full_name": "Michael Dell",
                    "title": "Chairman and CEO",
                    "relevance": "economic_buyer",
                },
                {
                    "full_name": "Yvonne McGill",
                    "title": "CFO",
                    "relevance": "economic_buyer",
                },
            ],
            "competitors": [
                {"company_name": "HP Inc.", "domain": "hp.com"},
                {"company_name": "Lenovo", "domain": "lenovo.com"},
            ],
        },
        "intel-techstack": {
            "search_vendor": {
                "name": "Elasticsearch",
                "status": "ACTIVE",
                "detection_source": "BuiltWith",
            },
            "ecommerce_platform": "Custom",
            "all_technologies": [
                {"name": "Elasticsearch", "category": "Search"},
                {"name": "React", "category": "JavaScript Framework"},
                {"name": "Akamai", "category": "CDN"},
            ],
        },
        "intel-traffic": {
            "total_visits_monthly": 85000000,
            "bounce_rate": 0.42,
            "avg_visit_duration_seconds": 312,
            "pages_per_visit": 4.2,
            "device_split": {"desktop": 0.55, "mobile": 0.40, "tablet": 0.05},
        },
        "intel-competitors": {
            "competitors": [
                {
                    "company_name": "HP Inc.",
                    "domain": "hp.com",
                    "search_vendor": "Algolia",
                },
                {
                    "company_name": "Lenovo",
                    "domain": "lenovo.com",
                    "search_vendor": "Elasticsearch",
                },
            ],
        },
        "intel-financial-public": {
            "revenue_latest": 88400000000.0,
            "revenue_growth_yoy": 0.08,
        },
        "intel-news": {
            "articles": [
                {
                    "headline": "Dell Reports Record Q4 Revenue",
                    "source": "Reuters",
                    "date": "2026-02-15",
                },
            ],
        },
        "intel-hiring": {
            "open_roles": [
                {"title": "Senior Search Engineer", "location": "Austin, TX"},
                {"title": "VP Engineering, Digital Commerce", "location": "Remote"},
            ],
        },
        "intel-investor": {
            "exec_quotes": [
                {
                    "speaker": "Yvonne McGill, CFO",
                    "quote": "Digital transformation remains our top investment priority.",
                    "source": "Q4 2025 Earnings Call",
                },
            ],
        },
        "intel-partner": {
            "partner_matches": ["Adobe Commerce", "Salesforce"],
        },
        "synth-business-case": {
            "executive_summary": (
                "Dell can unlock $2.4M annual revenue by improving search. "
                "Conservative estimate based on 12% conversion uplift."
            ),
            "total_conservative_impact": 2400000.0,
            "total_moderate_impact": 4800000.0,
        },
        "synth-sales-plays": {
            "plays": [
                {
                    "name": "Displacement Play",
                    "description": "Replace Elasticsearch with Algolia for AI search.",
                },
            ],
        },
        "modules_found": [
            "intel-company",
            "intel-techstack",
            "intel-traffic",
            "intel-competitors",
            "intel-financial-public",
            "intel-news",
            "intel-hiring",
            "intel-investor",
            "intel-partner",
            "synth-business-case",
            "synth-sales-plays",
        ],
        "modules_missing": [
            "intel-financial-private",
            "intel-social",
            "intel-industry",
            "intel-queries",
        ],
    }


# ---------------------------------------------------------------------------
# Integration tests -- real Gemini API calls
# ---------------------------------------------------------------------------


class TestAuditReportEnricherIntegration:
    """Integration tests making real Gemini API calls."""

    @pytest.fixture(scope="class")
    def enricher(self) -> AuditReportEnricher:
        """Create enricher instance (initializes Gemini client)."""
        return AuditReportEnricher()

    @pytest.mark.asyncio
    async def test_score_dimensions_real(self, enricher: AuditReportEnricher) -> None:
        """Test dimension scoring with real Gemini call."""
        collected = _make_collected_data()
        scores, calls, cost = await enricher._score_dimensions(
            "dell.com", "Dell Technologies", collected
        )

        assert calls == 1
        assert cost > 0
        assert len(scores) == 10

        # Verify all 10 dimensions present
        dims = {ds.dimension for ds in scores}
        assert dims == set(ALL_DIMENSIONS)

        # Verify score ranges
        for ds in scores:
            assert 0 <= ds.score <= 10, f"{ds.dimension} score {ds.score} out of range"
            assert ds.evidence, f"{ds.dimension} has no evidence"
            assert ds.severity in ("critical", "major", "minor", "ok")
            assert ds.is_estimated is True

    @pytest.mark.asyncio
    async def test_score_competitors_real(self, enricher: AuditReportEnricher) -> None:
        """Test competitor scoring with real Gemini call."""
        collected = _make_collected_data()
        comp_scores, calls, cost = await enricher._score_competitors(
            "dell.com", "Dell Technologies", collected
        )

        assert calls == 1
        assert cost > 0
        assert len(comp_scores) >= 1

        for cs in comp_scores:
            assert cs.company_name
            assert cs.domain

    @pytest.mark.asyncio
    async def test_generate_pre_call_brief_real(self, enricher: AuditReportEnricher) -> None:
        """Test pre-call brief generation with real Gemini call."""
        collected = _make_collected_data()
        brief, calls, cost = await enricher._generate_pre_call_brief(
            "dell.com", "Dell Technologies", 5.2, collected
        )

        assert calls == 1
        assert cost > 0
        assert isinstance(brief, PreCallBrief)
        assert brief.company_name
        assert 0 <= brief.search_score <= 10
        assert brief.top_angle
        assert brief.key_exec_to_reference
        assert brief.most_urgent_signal
        assert brief.recommended_first_play

    @pytest.mark.asyncio
    async def test_generate_leave_behind_real(self, enricher: AuditReportEnricher) -> None:
        """Test leave-behind generation with real Gemini call."""
        collected = _make_collected_data()
        dim_scores = [
            DimensionScore(
                dimension=dim,  # type: ignore[arg-type]
                score=5.0,
                evidence=f"Evidence for {dim}.",
                severity="major",
            )
            for dim in ALL_DIMENSIONS
        ]
        lb, calls, cost = await enricher._generate_leave_behind(
            "dell.com", "Dell Technologies", 5.2, dim_scores, collected
        )

        assert calls == 1
        assert cost > 0
        assert isinstance(lb, LeaveBehind)
        assert lb.search_quality_summary
        assert lb.competitive_benchmark
        assert len(lb.top_3_recommendations) >= 1
        assert lb.roi_summary

    @pytest.mark.asyncio
    async def test_generate_audit_summary_real(self, enricher: AuditReportEnricher) -> None:
        """Test audit summary generation with real Gemini call."""
        collected = _make_collected_data()
        dim_scores = [
            DimensionScore(
                dimension=dim,  # type: ignore[arg-type]
                score=5.0,
                evidence=f"Evidence for {dim}.",
                severity="major",
            )
            for dim in ALL_DIMENSIONS
        ]
        summary, calls, cost = await enricher._generate_audit_summary(
            "dell.com", "Dell Technologies", 5.2, dim_scores, collected
        )

        assert calls == 1
        assert cost > 0
        assert isinstance(summary, str)
        assert len(summary) > 50

    @pytest.mark.asyncio
    async def test_full_enrich_pipeline_real(self, enricher: AuditReportEnricher) -> None:
        """Test the full enrichment pipeline end-to-end with real Gemini calls."""
        collected = _make_collected_data()
        output, total_calls, total_cost = await enricher.enrich(
            "dell.com", "Dell Technologies", collected
        )

        assert isinstance(output, AuditReportOutput)
        assert total_calls >= 5  # 5 LLM calls minimum
        assert total_cost > 0

        # Verify output structure
        assert output.domain == "dell.com"
        assert output.company_name == "Dell Technologies"
        assert len(output.dimension_scores) == 10
        assert output.overall_score is not None
        assert 0 <= output.overall_score <= 10
        assert output.pre_call_brief is not None
        assert output.leave_behind is not None
        assert output.audit_summary
        assert output.full_audit_data

        # Verify all dimensions scored
        dims = {ds.dimension for ds in output.dimension_scores}
        assert dims == set(ALL_DIMENSIONS)
