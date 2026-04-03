"""Contract tests for audit-report schemas.

Validates Pydantic models accept valid data, reject invalid data,
and enforce all constraints specified in the audit report spec.
30+ test cases covering all models and edge cases.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.audit_report.schemas import (
    ALL_DIMENSIONS,
    AuditReportInput,
    AuditReportOutput,
    CompetitorScore,
    DimensionScore,
    LeaveBehind,
    PreCallBrief,
)

# ---------------------------------------------------------------------------
# Fixtures / Builders
# ---------------------------------------------------------------------------


def _make_dimension_score(**overrides: object) -> dict:
    """Build a valid DimensionScore dict with optional overrides."""
    base = {
        "dimension": "relevance",
        "score": 6.5,
        "evidence": "BuiltWith shows basic keyword search, no AI/semantic capabilities.",
        "severity": "minor",
        "is_estimated": True,
    }
    base.update(overrides)
    return base


def _make_all_dimension_scores() -> list[dict]:
    """Build a list of 10 valid DimensionScore dicts, one per dimension."""
    scores = []
    for i, dim in enumerate(ALL_DIMENSIONS):
        score_val = 3.0 + i * 0.7
        if score_val <= 3:
            severity = "critical"
        elif score_val <= 5:
            severity = "major"
        elif score_val <= 7:
            severity = "minor"
        else:
            severity = "ok"
        scores.append(
            {
                "dimension": dim,
                "score": round(score_val, 1),
                "evidence": f"Evidence for {dim} dimension scoring.",
                "severity": severity,
                "is_estimated": True,
            }
        )
    return scores


def _make_competitor_score(**overrides: object) -> dict:
    """Build a valid CompetitorScore dict with optional overrides."""
    base = {
        "company_name": "HP Inc.",
        "domain": "hp.com",
        "overall_score": 5.5,
        "dimension_scores": [_make_dimension_score()],
    }
    base.update(overrides)
    return base


def _make_pre_call_brief(**overrides: object) -> dict:
    """Build a valid PreCallBrief dict with optional overrides."""
    base = {
        "company_name": "Dell Technologies",
        "search_score": 5.2,
        "top_angle": "Search conversion gap vs competitors using Algolia",
        "key_exec_to_reference": "CFO Yvonne McGill on Q4 call: 'Digital is our growth vector'",
        "partner_play": "Adobe Commerce integration opportunity",
        "most_urgent_signal": "Hiring 3 search engineers -- active evaluation window",
        "recommended_first_play": "Lead with competitor comparison showing 37% conversion gap",
    }
    base.update(overrides)
    return base


def _make_leave_behind(**overrides: object) -> dict:
    """Build a valid LeaveBehind dict with optional overrides."""
    base = {
        "search_quality_summary": (
            "Your search experience scores 5.2/10 across 10 dimensions. "
            "Key gaps in relevance, typo tolerance, and zero-result handling."
        ),
        "competitive_benchmark": (
            "Your search scores 5.2/10 vs industry average 6.8/10. "
            "Competitor A scores 7.2/10 with AI-powered search."
        ),
        "top_3_recommendations": [
            "Implement semantic search to improve relevance from 4.5 to 7.5+",
            "Add typo tolerance to capture misspelled queries (est. 8% of searches)",
            "Deploy zero-result rescue to recover 15% of failed searches",
        ],
        "roi_summary": (
            "Conservative estimate: $2.4M annual impact from search improvements. "
            "Based on 12% conversion uplift at current traffic levels."
        ),
        "next_steps": "Schedule a 30-minute technical deep dive with your search team.",
    }
    base.update(overrides)
    return base


def _make_full_output(**overrides: object) -> dict:
    """Build a valid AuditReportOutput dict with optional overrides."""
    base = {
        "domain": "dell.com",
        "company_name": "Dell Technologies",
        "dimension_scores": _make_all_dimension_scores(),
        "overall_score": 5.2,
        "score_methodology": "Weighted average of 10 dimensions.",
        "competitor_scores": [_make_competitor_score()],
        "industry_average_score": 6.8,
        "full_audit_data": {
            "intelligence": {"intel-company": {"legal_name": "Dell Technologies Inc."}},
            "synthesis": {},
            "metadata": {"modules_found": ["intel-company"], "modules_missing": []},
        },
        "pre_call_brief": _make_pre_call_brief(),
        "leave_behind": _make_leave_behind(),
        "audit_summary": (
            "Dell Technologies scores 5.2/10 on search quality. "
            "Critical gaps in relevance and zero-result handling present "
            "a $2.4M annual opportunity for Algolia."
        ),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# AuditReportInput
# ---------------------------------------------------------------------------


class TestAuditReportInput:
    """Tests for AuditReportInput schema."""

    def test_valid_input(self) -> None:
        inp = AuditReportInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            AuditReportInput(domain="dell.com", extra_field="nope")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# DimensionScore
# ---------------------------------------------------------------------------


class TestDimensionScore:
    """Tests for DimensionScore schema."""

    def test_valid_dimension_score(self) -> None:
        ds = DimensionScore.model_validate(_make_dimension_score())
        assert ds.dimension == "relevance"
        assert ds.score == 6.5
        assert ds.severity == "minor"
        assert ds.is_estimated is True

    @pytest.mark.parametrize("dimension", ALL_DIMENSIONS)
    def test_all_dimension_values(self, dimension: str) -> None:
        ds = DimensionScore.model_validate(_make_dimension_score(dimension=dimension))
        assert ds.dimension == dimension

    def test_invalid_dimension_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionScore.model_validate(_make_dimension_score(dimension="magic"))

    @pytest.mark.parametrize("severity", ["critical", "major", "minor", "ok"])
    def test_all_severity_values(self, severity: str) -> None:
        ds = DimensionScore.model_validate(_make_dimension_score(severity=severity))
        assert ds.severity == severity

    def test_invalid_severity_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionScore.model_validate(_make_dimension_score(severity="warning"))

    def test_score_minimum_bound(self) -> None:
        ds = DimensionScore.model_validate(_make_dimension_score(score=0))
        assert ds.score == 0

    def test_score_maximum_bound(self) -> None:
        ds = DimensionScore.model_validate(_make_dimension_score(score=10))
        assert ds.score == 10

    def test_score_below_minimum_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionScore.model_validate(_make_dimension_score(score=-0.1))

    def test_score_above_maximum_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionScore.model_validate(_make_dimension_score(score=10.1))

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            DimensionScore.model_validate({**_make_dimension_score(), "bonus": 1})

    def test_is_estimated_default_true(self) -> None:
        data = {
            "dimension": "speed",
            "score": 7.0,
            "evidence": "Fast load times observed.",
            "severity": "minor",
        }
        ds = DimensionScore.model_validate(data)
        assert ds.is_estimated is True


# ---------------------------------------------------------------------------
# CompetitorScore
# ---------------------------------------------------------------------------


class TestCompetitorScore:
    """Tests for CompetitorScore schema."""

    def test_valid_competitor_score(self) -> None:
        cs = CompetitorScore.model_validate(_make_competitor_score())
        assert cs.company_name == "HP Inc."
        assert cs.domain == "hp.com"
        assert cs.overall_score == 5.5

    def test_minimal_competitor_score(self) -> None:
        cs = CompetitorScore(company_name="Lenovo", domain="lenovo.com")
        assert cs.overall_score is None
        assert cs.dimension_scores == []

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CompetitorScore.model_validate({**_make_competitor_score(), "secret": True})

    def test_nested_dimension_validation(self) -> None:
        """Bad dimension in nested list should fail."""
        bad_data = _make_competitor_score()
        bad_data["dimension_scores"] = [
            {"dimension": "INVALID", "score": 5, "evidence": "x", "severity": "ok"}
        ]
        with pytest.raises(ValidationError):
            CompetitorScore.model_validate(bad_data)


# ---------------------------------------------------------------------------
# PreCallBrief
# ---------------------------------------------------------------------------


class TestPreCallBrief:
    """Tests for PreCallBrief schema."""

    def test_valid_pre_call_brief(self) -> None:
        pcb = PreCallBrief.model_validate(_make_pre_call_brief())
        assert pcb.company_name == "Dell Technologies"
        assert pcb.search_score == 5.2
        assert pcb.partner_play is not None

    def test_partner_play_nullable(self) -> None:
        pcb = PreCallBrief.model_validate(_make_pre_call_brief(partner_play=None))
        assert pcb.partner_play is None

    def test_search_score_bounds(self) -> None:
        pcb = PreCallBrief.model_validate(_make_pre_call_brief(search_score=0))
        assert pcb.search_score == 0
        pcb = PreCallBrief.model_validate(_make_pre_call_brief(search_score=10))
        assert pcb.search_score == 10

    def test_search_score_below_minimum_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PreCallBrief.model_validate(_make_pre_call_brief(search_score=-1))

    def test_search_score_above_maximum_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PreCallBrief.model_validate(_make_pre_call_brief(search_score=11))

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            PreCallBrief.model_validate({**_make_pre_call_brief(), "hidden": "data"})


# ---------------------------------------------------------------------------
# LeaveBehind
# ---------------------------------------------------------------------------


class TestLeaveBehind:
    """Tests for LeaveBehind schema."""

    def test_valid_leave_behind(self) -> None:
        lb = LeaveBehind.model_validate(_make_leave_behind())
        assert len(lb.top_3_recommendations) == 3
        assert lb.next_steps != ""

    def test_empty_recommendations_list(self) -> None:
        lb = LeaveBehind.model_validate(_make_leave_behind(top_3_recommendations=[]))
        assert lb.top_3_recommendations == []

    def test_next_steps_default_empty(self) -> None:
        data = _make_leave_behind()
        del data["next_steps"]
        lb = LeaveBehind.model_validate(data)
        assert lb.next_steps == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            LeaveBehind.model_validate({**_make_leave_behind(), "internal_only": True})


# ---------------------------------------------------------------------------
# AuditReportOutput
# ---------------------------------------------------------------------------


class TestAuditReportOutput:
    """Tests for AuditReportOutput schema."""

    def test_valid_full_output(self) -> None:
        output = AuditReportOutput.model_validate(_make_full_output())
        assert output.domain == "dell.com"
        assert output.company_name == "Dell Technologies"
        assert len(output.dimension_scores) == 10
        assert output.overall_score == 5.2
        assert output.pre_call_brief is not None
        assert output.leave_behind is not None
        assert output.audit_summary != ""

    def test_minimal_defaults(self) -> None:
        output = AuditReportOutput(domain="test.com")
        assert output.company_name == ""
        assert output.dimension_scores == []
        assert output.overall_score is None
        assert output.competitor_scores == []
        assert output.full_audit_data == {}
        assert output.pre_call_brief is None
        assert output.leave_behind is None
        assert output.audit_summary == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            AuditReportOutput.model_validate({**_make_full_output(), "secret": "no"})

    def test_all_10_dimensions_present(self) -> None:
        output = AuditReportOutput.model_validate(_make_full_output())
        dims = {ds.dimension for ds in output.dimension_scores}
        assert dims == set(ALL_DIMENSIONS)

    def test_nested_pre_call_brief_validation(self) -> None:
        bad_data = _make_full_output()
        bad_data["pre_call_brief"]["search_score"] = -5  # invalid
        with pytest.raises(ValidationError):
            AuditReportOutput.model_validate(bad_data)

    def test_nested_leave_behind_validation(self) -> None:
        bad_data = _make_full_output()
        bad_data["leave_behind"]["extra_field"] = "nope"  # extra forbidden
        with pytest.raises(ValidationError):
            AuditReportOutput.model_validate(bad_data)

    def test_nested_dimension_score_validation(self) -> None:
        bad_data = _make_full_output()
        bad_data["dimension_scores"][0]["dimension"] = "INVALID"
        with pytest.raises(ValidationError):
            AuditReportOutput.model_validate(bad_data)

    def test_full_audit_data_accepts_nested_dicts(self) -> None:
        output = AuditReportOutput.model_validate(_make_full_output())
        assert "intelligence" in output.full_audit_data
        assert "metadata" in output.full_audit_data

    def test_overall_score_float(self) -> None:
        output = AuditReportOutput.model_validate(_make_full_output())
        assert isinstance(output.overall_score, float)

    def test_industry_average_score_nullable(self) -> None:
        output = AuditReportOutput.model_validate(_make_full_output(industry_average_score=None))
        assert output.industry_average_score is None


# ---------------------------------------------------------------------------
# ALL_DIMENSIONS constant
# ---------------------------------------------------------------------------


class TestAllDimensions:
    """Tests for the ALL_DIMENSIONS constant."""

    def test_exactly_10_dimensions(self) -> None:
        assert len(ALL_DIMENSIONS) == 10

    def test_no_duplicates(self) -> None:
        assert len(ALL_DIMENSIONS) == len(set(ALL_DIMENSIONS))

    def test_expected_dimensions_present(self) -> None:
        expected = {
            "relevance",
            "speed",
            "typo_tolerance",
            "nlp",
            "autocomplete",
            "faceting",
            "zero_result_handling",
            "personalization",
            "merchandising",
            "analytics",
        }
        assert set(ALL_DIMENSIONS) == expected
