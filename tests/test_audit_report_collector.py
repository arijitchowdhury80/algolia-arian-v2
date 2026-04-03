"""Tests for audit-report collector (DB reader) and validator.

Tests the collector logic using synthetic data and the validator
with both passing and failing outputs. No database connection needed
for validator tests. Collector tests verify the module list and
data assembly logic.
"""

from __future__ import annotations

from prism_platform.core.types import EvidenceTier, Source
from prism_platform.modules.audit_report.collector import (
    UPSTREAM_MODULES,
    AuditReportCollector,
)
from prism_platform.modules.audit_report.enricher import AuditReportEnricher
from prism_platform.modules.audit_report.schemas import (
    ALL_DIMENSIONS,
    AuditReportOutput,
    CompetitorScore,
    DimensionScore,
    LeaveBehind,
    PreCallBrief,
)
from prism_platform.modules.audit_report.validator import validate_output

# ---------------------------------------------------------------------------
# Collector unit tests
# ---------------------------------------------------------------------------


class TestAuditReportCollector:
    """Tests for AuditReportCollector configuration and constants."""

    def test_upstream_modules_list_complete(self) -> None:
        """Verify all expected upstream modules are in the UPSTREAM_MODULES list."""
        expected = {
            "intel-company",
            "intel-techstack",
            "intel-traffic",
            "intel-financial-public",
            "intel-financial-private",
            "intel-news",
            "intel-hiring",
            "intel-social",
            "intel-investor",
            "intel-partner",
            "intel-industry",
            "intel-competitors",
            "intel-queries",
            "synth-business-case",
            "synth-sales-plays",
        }
        assert set(UPSTREAM_MODULES) == expected

    def test_upstream_modules_count(self) -> None:
        assert len(UPSTREAM_MODULES) == 15

    def test_collector_instantiation(self) -> None:
        collector = AuditReportCollector()
        assert collector is not None


# ---------------------------------------------------------------------------
# Enricher unit tests (non-LLM methods)
# ---------------------------------------------------------------------------


class TestAuditReportEnricherHelpers:
    """Tests for AuditReportEnricher static/helper methods that don't require LLM."""

    def test_calculate_overall_score_weighted(self) -> None:
        """High-weight dimensions (relevance, speed, zero_result_handling) count 1.5x."""
        high = [("relevance", 10.0), ("speed", 10.0), ("zero_result_handling", 10.0)]
        low = [
            ("typo_tolerance", 0.0),
            ("nlp", 0.0),
            ("autocomplete", 0.0),
            ("faceting", 0.0),
            ("personalization", 0.0),
            ("merchandising", 0.0),
            ("analytics", 0.0),
        ]
        scores = [
            DimensionScore(
                dimension=d,
                score=s,
                evidence="e",
                severity="ok" if s > 0 else "critical",
            )
            for d, s in high + low
        ]
        result = AuditReportEnricher._calculate_overall_score(scores)
        assert result is not None
        # 3 high-weight dims at 10 * 1.5 = 45, 7 low-weight at 0 = 0
        # total weight = 3*1.5 + 7*1.0 = 11.5
        # score = 45 / 11.5 = 3.913...
        assert abs(result - 3.9) < 0.1

    def test_calculate_overall_score_empty(self) -> None:
        result = AuditReportEnricher._calculate_overall_score([])
        assert result is None

    def test_calculate_overall_score_uniform(self) -> None:
        """All dimensions at 5.0 should give exactly 5.0."""
        scores = [
            DimensionScore(dimension=dim, score=5.0, evidence="e", severity="major")
            for dim in ALL_DIMENSIONS
        ]
        result = AuditReportEnricher._calculate_overall_score(scores)
        assert result == 5.0

    def test_calculate_industry_average(self) -> None:
        competitors = [
            CompetitorScore(company_name="A", domain="a.com", overall_score=6.0),
            CompetitorScore(company_name="B", domain="b.com", overall_score=8.0),
        ]
        result = AuditReportEnricher._calculate_industry_average(competitors)
        assert result == 7.0

    def test_calculate_industry_average_empty(self) -> None:
        result = AuditReportEnricher._calculate_industry_average([])
        assert result is None

    def test_calculate_industry_average_with_nulls(self) -> None:
        competitors = [
            CompetitorScore(company_name="A", domain="a.com", overall_score=6.0),
            CompetitorScore(company_name="B", domain="b.com", overall_score=None),
        ]
        result = AuditReportEnricher._calculate_industry_average(competitors)
        assert result == 6.0

    def test_estimate_cost(self) -> None:
        cost = AuditReportEnricher._estimate_cost("a" * 4000, "b" * 4000)
        # 4000 chars / 4 = 1000 tokens
        # Input: 1000/1M * 0.10 = 0.0001
        # Output: 1000/1M * 0.40 = 0.0004
        assert abs(cost - 0.0005) < 0.0001

    def test_assemble_full_audit_data(self) -> None:
        """Test that full_audit_data is organized by section."""
        # Need to instantiate but avoid __init__ Gemini client
        # Test the static-ish logic by calling on a mock instance
        collected = {
            "intel-company": {"legal_name": "Test Corp"},
            "intel-techstack": {"search_vendor": "elasticsearch"},
            "synth-business-case": {"executive_summary": "Good opportunity"},
            "modules_found": ["intel-company", "intel-techstack", "synth-business-case"],
            "modules_missing": ["intel-traffic"],
        }
        # Call the method directly (it's essentially a pure function)
        enricher = object.__new__(AuditReportEnricher)
        result = enricher._assemble_full_audit_data(collected)

        assert "intelligence" in result
        assert "synthesis" in result
        assert "metadata" in result
        intel = result["intelligence"]
        assert "intel-company" in intel  # type: ignore[operator]
        assert "intel-techstack" in intel  # type: ignore[operator]
        synth = result["synthesis"]
        assert "synth-business-case" in synth  # type: ignore[operator]


# ---------------------------------------------------------------------------
# Validator tests with synthetic data
# ---------------------------------------------------------------------------


def _make_valid_output() -> AuditReportOutput:
    """Build a valid AuditReportOutput for validator testing."""
    dimension_scores = [
        DimensionScore(
            dimension=dim,  # type: ignore[arg-type]
            score=5.0 + i * 0.3,
            evidence=f"Evidence for {dim}.",
            severity="major" if 5.0 + i * 0.3 <= 5 else "minor",
            is_estimated=True,
        )
        for i, dim in enumerate(ALL_DIMENSIONS)
    ]
    return AuditReportOutput(
        domain="dell.com",
        company_name="Dell Technologies",
        dimension_scores=dimension_scores,
        overall_score=5.2,
        score_methodology="Weighted average.",
        competitor_scores=[
            CompetitorScore(company_name="HP", domain="hp.com", overall_score=6.0),
        ],
        industry_average_score=6.5,
        full_audit_data={
            "intelligence": {"intel-company": {}},
            "metadata": {"modules_found": ["intel-company"]},
        },
        pre_call_brief=PreCallBrief(
            company_name="Dell Technologies",
            search_score=5.2,
            top_angle="Search conversion gap",
            key_exec_to_reference="CFO said digital is priority",
            partner_play=None,
            most_urgent_signal="Hiring 3 search engineers",
            recommended_first_play="Lead with competitor comparison",
        ),
        leave_behind=LeaveBehind(
            search_quality_summary="Your search scores 5.2/10.",
            competitive_benchmark="Industry avg is 6.8/10.",
            top_3_recommendations=[
                "Implement semantic search",
                "Add typo tolerance",
                "Deploy zero-result rescue",
            ],
            roi_summary="$2.4M annual impact.",
            next_steps="Schedule technical deep dive.",
        ),
        audit_summary="Dell scores 5.2/10 on search quality with significant gaps.",
    )


def _make_valid_sources() -> list[Source]:
    """Build valid Source list for validator testing."""
    return [
        Source(
            field="collected_modules",
            value="Loaded 12 module outputs",
            tier=EvidenceTier.VERIFIED,
            source_label="PRISM DB",
            method="direct_api",
        ),
    ]


class TestAuditReportValidator:
    """Tests for audit-report validator with synthetic data."""

    def test_valid_output_passes(self) -> None:
        output = _make_valid_output()
        sources = _make_valid_sources()
        result = validate_output(output, sources)
        assert result.passed is True
        assert result.checks_run == 10
        assert result.checks_passed == 10
        assert result.errors == []

    def test_empty_domain_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"domain": ""})
        result = validate_output(output, _make_valid_sources())
        assert result.passed is False
        assert any("domain is empty" in e for e in result.errors)

    def test_wrong_dimension_count_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"dimension_scores": output.dimension_scores[:5]})
        result = validate_output(output, _make_valid_sources())
        assert result.passed is False
        assert any("expected exactly 10" in e for e in result.errors)

    def test_missing_dimensions_fails(self) -> None:
        output = _make_valid_output()
        # Replace last dimension with duplicate of first
        scores = list(output.dimension_scores[:9])
        scores.append(
            DimensionScore(
                dimension="relevance",
                score=5.0,
                evidence="Duplicate",
                severity="major",
            )
        )
        output = output.model_copy(update={"dimension_scores": scores})
        result = validate_output(output, _make_valid_sources())
        assert result.passed is False
        assert any("Missing dimensions" in e for e in result.errors)

    def test_null_overall_score_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"overall_score": None})
        result = validate_output(output, _make_valid_sources())
        assert result.passed is False
        assert any("overall_score is None" in e for e in result.errors)

    def test_overall_score_out_of_range_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"overall_score": 11.0})
        result = validate_output(output, _make_valid_sources())
        assert result.passed is False
        assert any("must be between 0 and 10" in e for e in result.errors)

    def test_null_pre_call_brief_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"pre_call_brief": None})
        result = validate_output(output, _make_valid_sources())
        assert result.passed is False
        assert any("pre_call_brief is None" in e for e in result.errors)

    def test_null_leave_behind_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"leave_behind": None})
        result = validate_output(output, _make_valid_sources())
        assert result.passed is False
        assert any("leave_behind is None" in e for e in result.errors)

    def test_wrong_recommendation_count_fails(self) -> None:
        output = _make_valid_output()
        lb = output.leave_behind
        assert lb is not None
        new_lb = lb.model_copy(update={"top_3_recommendations": ["only one"]})
        output = output.model_copy(update={"leave_behind": new_lb})
        result = validate_output(output, _make_valid_sources())
        assert result.passed is False
        assert any("expected exactly 3" in e for e in result.errors)

    def test_empty_audit_summary_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"audit_summary": ""})
        result = validate_output(output, _make_valid_sources())
        assert result.passed is False
        assert any("audit_summary is empty" in e for e in result.errors)

    def test_no_sources_fails(self) -> None:
        output = _make_valid_output()
        result = validate_output(output, [])
        assert result.passed is False
        assert any("No source provenance" in e for e in result.errors)

    def test_empty_full_audit_data_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"full_audit_data": {}})
        result = validate_output(output, _make_valid_sources())
        assert result.passed is False
        assert any("full_audit_data is empty" in e for e in result.errors)

    def test_multiple_failures_all_reported(self) -> None:
        """An output with many issues should report all of them."""
        output = AuditReportOutput(
            domain="",
            company_name="",
            dimension_scores=[],
            overall_score=None,
            pre_call_brief=None,
            leave_behind=None,
            audit_summary="",
            full_audit_data={},
        )
        result = validate_output(output, [])
        assert result.passed is False
        # Should have many errors
        assert len(result.errors) >= 7
