"""Tests for intel-competitors collector extraction logic and validator.

Tests the pure extraction functions with synthetic data. No DB or API calls.
"""

from __future__ import annotations

from prism_platform.core.types import EvidenceTier, Source
from prism_platform.modules.intel_competitors.collector import (
    extract_executive_sentiments,
    extract_financial_comparisons,
    extract_hiring_comparisons,
    extract_tech_comparisons,
    extract_traffic_comparisons,
)
from prism_platform.modules.intel_competitors.schemas import (
    CompetitiveScenario,
    CompetitorsOutput,
    TechComparison,
)
from prism_platform.modules.intel_competitors.validator import validate_output

# ---------------------------------------------------------------------------
# Sample upstream data fixtures
# ---------------------------------------------------------------------------

SAMPLE_TECHSTACK_OUTPUT: dict = {
    "search_vendor": {
        "name": "Elasticsearch",
        "status": "ACTIVE",
        "detection_source": "BuiltWith v22 API",
        "evidence_tier": "VERIFIED",
    },
    "ecommerce_platform": "Salesforce Commerce Cloud",
    "all_technologies": [
        {"Name": "Elasticsearch", "Tag": "elasticsearch", "Categories": ["search"]},
        {"Name": "React", "Tag": "react", "Categories": ["javascript"]},
        {"Name": "Salesforce Commerce Cloud", "Tag": "sfcc", "Categories": ["ecommerce"]},
        {"Name": "Google Analytics", "Tag": "ga", "Categories": ["analytics"]},
    ],
    "algolia_detected": False,
    "competitor_tech_stacks": [
        {
            "company_name": "HP Inc",
            "domain": "hp.com",
            "search_vendor": {
                "name": "Algolia",
                "status": "ACTIVE",
                "detection_source": "BuiltWith v22 API",
                "evidence_tier": "VERIFIED",
            },
            "ecommerce_platform": "Magento",
            "all_technologies": [
                {"Name": "Algolia", "Tag": "algolia", "Categories": ["search"]},
                {"Name": "Magento", "Tag": "magento", "Categories": ["ecommerce"]},
            ],
            "tech_count": 2,
            "is_algolia_customer": True,
        },
        {
            "company_name": "Lenovo",
            "domain": "lenovo.com",
            "search_vendor": {
                "name": "Coveo",
                "status": "ACTIVE",
                "detection_source": "BuiltWith v22 API",
                "evidence_tier": "VERIFIED",
            },
            "ecommerce_platform": None,
            "all_technologies": [
                {"Name": "Coveo", "Tag": "coveo", "Categories": ["search"]},
            ],
            "tech_count": 1,
            "is_algolia_customer": False,
        },
    ],
    "golden_angle_competitors": ["HP Inc"],
}

SAMPLE_TRAFFIC_OUTPUT: dict = {
    "total_visits": 50_000_000,
    "bounce_rate": 0.35,
    "pages_per_visit": 4.2,
    "traffic_sources": {
        "organic_search": 0.45,
        "paid_search": 0.15,
        "direct": 0.25,
        "referral": 0.10,
        "social": 0.05,
    },
    "visit_history": [
        {"month": "2024-01", "visits": 45_000_000},
        {"month": "2024-02", "visits": 50_000_000},
    ],
}

SAMPLE_FINANCIAL_PUBLIC_OUTPUT: dict = {
    "revenue": 102_300_000_000.0,
    "revenue_growth_pct": 8.5,
    "digital_revenue_pct": 45.0,
    "market_cap": 85_000_000_000.0,
}

SAMPLE_FINANCIAL_PRIVATE_OUTPUT: dict = {
    "annual_revenue": 500_000_000.0,
    "revenue_growth": 12.0,
    "ecommerce_revenue_pct": 60.0,
}

SAMPLE_HIRING_OUTPUT: dict = {
    "total_open_roles": 450,
    "search_related_roles": 12,
    "build_vs_buy": "buy",
    "hiring_trend": "accelerating",
}

SAMPLE_INVESTOR_OUTPUT: dict = {
    "key_quotes": ["We are doubling down on digital transformation."],
    "executive_quotes": [
        {"quote": "Search is critical to our ecommerce strategy.", "source": "Q4 earnings"},
    ],
    "search_mentions": 5,
    "digital_commitment_level": "high",
}

SAMPLE_SOCIAL_OUTPUT: dict = {
    "key_quotes": ["Excited to announce our new AI-powered search."],
    "search_mentions": 3,
    "digital_commitment_level": "medium",
}


# ---------------------------------------------------------------------------
# extract_tech_comparisons
# ---------------------------------------------------------------------------
class TestExtractTechComparisons:
    def test_full_extraction(self) -> None:
        comps, golden, _gaps = extract_tech_comparisons(
            SAMPLE_TECHSTACK_OUTPUT, "dell.com", "Dell Inc"
        )
        assert len(comps) == 3  # prospect + 2 competitors
        assert comps[0].company_name == "Dell Inc"
        assert comps[0].domain == "dell.com"
        assert comps[0].search_vendor == "Elasticsearch"
        assert comps[0].algolia_detected is False
        assert comps[1].company_name == "HP Inc"
        assert comps[1].algolia_detected is True
        assert "HP Inc" in golden

    def test_none_input(self) -> None:
        comps, golden, gaps = extract_tech_comparisons(None, "dell.com", "Dell Inc")
        assert comps == []
        assert golden == []
        assert gaps == []

    def test_empty_dict(self) -> None:
        """Empty dict is falsy in Python, so treated same as None."""
        comps, _golden, _gaps = extract_tech_comparisons({}, "dell.com", "Dell Inc")
        assert comps == []

    def test_minimal_data(self) -> None:
        """Dict with at least one key produces a prospect entry."""
        data = {"search_vendor": None, "all_technologies": []}
        comps, _golden, _gaps = extract_tech_comparisons(data, "dell.com", "Dell Inc")
        assert len(comps) == 1
        assert comps[0].search_vendor is None

    def test_golden_angle_detected(self) -> None:
        _, golden, _ = extract_tech_comparisons(SAMPLE_TECHSTACK_OUTPUT, "dell.com", "Dell Inc")
        assert "HP Inc" in golden
        assert "Lenovo" not in golden

    def test_tech_gaps_detected(self) -> None:
        """Test tech gap detection when prospect has no search vendor but competitors do."""
        data = {
            "search_vendor": None,
            "all_technologies": [],
            "competitor_tech_stacks": [
                {
                    "company_name": "Competitor A",
                    "domain": "a.com",
                    "search_vendor": {
                        "name": "Algolia",
                        "status": "ACTIVE",
                        "detection_source": "BW",
                        "evidence_tier": "VERIFIED",
                    },
                    "all_technologies": [],
                    "is_algolia_customer": True,
                }
            ],
            "golden_angle_competitors": ["Competitor A"],
        }
        _, _, gaps = extract_tech_comparisons(data, "test.com", "Test Co")
        assert any("no detected search vendor" in g.lower() for g in gaps)

    def test_key_technologies_capped_at_20(self) -> None:
        data = {
            "search_vendor": None,
            "all_technologies": [
                {"Name": f"Tech{i}", "Tag": f"t{i}", "Categories": []} for i in range(30)
            ],
            "competitor_tech_stacks": [],
        }
        comps, _, _ = extract_tech_comparisons(data, "test.com", "Test Co")
        assert len(comps[0].key_technologies) == 20


# ---------------------------------------------------------------------------
# extract_traffic_comparisons
# ---------------------------------------------------------------------------
class TestExtractTrafficComparisons:
    def test_full_extraction(self) -> None:
        comps = extract_traffic_comparisons(SAMPLE_TRAFFIC_OUTPUT, "dell.com", "Dell Inc")
        assert len(comps) == 1
        assert comps[0].monthly_visits == 50_000_000
        assert comps[0].bounce_rate == 0.35
        assert comps[0].pages_per_visit == 4.2
        assert comps[0].organic_search_pct == 0.45
        assert comps[0].growth_trend == "growing"

    def test_none_input(self) -> None:
        comps = extract_traffic_comparisons(None, "dell.com", "Dell Inc")
        assert comps == []

    def test_empty_dict(self) -> None:
        """Empty dict is falsy in Python, treated same as None."""
        comps = extract_traffic_comparisons({}, "dell.com", "Dell Inc")
        assert comps == []

    def test_minimal_data(self) -> None:
        """Dict with at least one key produces a prospect entry."""
        comps = extract_traffic_comparisons({"total_visits": None}, "dell.com", "Dell Inc")
        assert len(comps) == 1
        assert comps[0].monthly_visits is None

    def test_declining_trend(self) -> None:
        data = {
            "visit_history": [
                {"month": "2024-01", "visits": 50_000_000},
                {"month": "2024-02", "visits": 40_000_000},
            ]
        }
        comps = extract_traffic_comparisons(data, "test.com", "Test")
        assert comps[0].growth_trend == "declining"

    def test_stable_trend(self) -> None:
        data = {
            "visit_history": [
                {"month": "2024-01", "visits": 50_000_000},
                {"month": "2024-02", "visits": 50_500_000},
            ]
        }
        comps = extract_traffic_comparisons(data, "test.com", "Test")
        assert comps[0].growth_trend == "stable"


# ---------------------------------------------------------------------------
# extract_financial_comparisons
# ---------------------------------------------------------------------------
class TestExtractFinancialComparisons:
    def test_public_company(self) -> None:
        comps = extract_financial_comparisons(
            SAMPLE_FINANCIAL_PUBLIC_OUTPUT, None, "dell.com", "Dell Inc", is_private=False
        )
        assert len(comps) == 1
        assert comps[0].revenue == 102_300_000_000.0
        assert comps[0].revenue_growth_pct == 8.5
        assert comps[0].market_cap == 85_000_000_000.0

    def test_private_company(self) -> None:
        comps = extract_financial_comparisons(
            None, SAMPLE_FINANCIAL_PRIVATE_OUTPUT, "private.com", "Private Co", is_private=True
        )
        assert len(comps) == 1
        assert comps[0].revenue == 500_000_000.0
        assert comps[0].revenue_growth_pct == 12.0

    def test_none_inputs(self) -> None:
        comps = extract_financial_comparisons(None, None, "test.com", "Test", is_private=False)
        assert comps == []

    def test_fallback_to_available(self) -> None:
        """If marked private but no private output, fall back to public."""
        comps = extract_financial_comparisons(
            SAMPLE_FINANCIAL_PUBLIC_OUTPUT, None, "test.com", "Test", is_private=True
        )
        assert len(comps) == 1
        assert comps[0].revenue == 102_300_000_000.0


# ---------------------------------------------------------------------------
# extract_hiring_comparisons
# ---------------------------------------------------------------------------
class TestExtractHiringComparisons:
    def test_full_extraction(self) -> None:
        comps = extract_hiring_comparisons(SAMPLE_HIRING_OUTPUT, "dell.com", "Dell Inc")
        assert len(comps) == 1
        assert comps[0].total_open_roles == 450
        assert comps[0].search_related_roles == 12
        assert comps[0].build_vs_buy == "buy"
        assert comps[0].hiring_trend == "accelerating"

    def test_none_input(self) -> None:
        comps = extract_hiring_comparisons(None, "dell.com", "Dell Inc")
        assert comps == []

    def test_empty_dict(self) -> None:
        """Empty dict is falsy in Python, treated same as None."""
        comps = extract_hiring_comparisons({}, "dell.com", "Dell Inc")
        assert comps == []

    def test_minimal_data(self) -> None:
        """Dict with at least one key produces a prospect entry."""
        comps = extract_hiring_comparisons({"total_open_roles": 0}, "dell.com", "Dell Inc")
        assert len(comps) == 1
        assert comps[0].total_open_roles == 0


# ---------------------------------------------------------------------------
# extract_executive_sentiments
# ---------------------------------------------------------------------------
class TestExtractExecutiveSentiments:
    def test_full_extraction(self) -> None:
        sentiments = extract_executive_sentiments(
            SAMPLE_INVESTOR_OUTPUT, SAMPLE_SOCIAL_OUTPUT, "dell.com", "Dell Inc"
        )
        assert len(sentiments) == 1
        assert sentiments[0].digital_commitment_level == "high"
        assert sentiments[0].search_mentions == 8  # 5 + 3
        assert len(sentiments[0].key_quotes) >= 2

    def test_investor_only(self) -> None:
        sentiments = extract_executive_sentiments(
            SAMPLE_INVESTOR_OUTPUT, None, "dell.com", "Dell Inc"
        )
        assert len(sentiments) == 1
        assert sentiments[0].digital_commitment_level == "high"

    def test_social_only(self) -> None:
        sentiments = extract_executive_sentiments(
            None, SAMPLE_SOCIAL_OUTPUT, "dell.com", "Dell Inc"
        )
        assert len(sentiments) == 1
        assert sentiments[0].digital_commitment_level == "medium"

    def test_both_none(self) -> None:
        sentiments = extract_executive_sentiments(None, None, "dell.com", "Dell Inc")
        assert sentiments == []

    def test_no_useful_data(self) -> None:
        sentiments = extract_executive_sentiments(
            {"search_mentions": 0}, {"search_mentions": 0}, "dell.com", "Dell Inc"
        )
        assert sentiments == []


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------
class TestValidator:
    def _make_sources(self, count: int = 1) -> list[Source]:
        return [
            Source(
                field="upstream.intel-techstack",
                value="test",
                tier=EvidenceTier.VERIFIED,
                source_label="test",
                method="db_read",
            )
            for _ in range(count)
        ]

    def test_valid_full_output(self) -> None:
        output = CompetitorsOutput(
            domain="dell.com",
            tech_comparisons=[
                TechComparison(company_name="Dell", domain="dell.com"),
                TechComparison(company_name="HP", domain="hp.com"),
            ],
            golden_angle_competitors=["HP"],
            competitive_position="fast_follower",
            competitive_pressure="increasing",
            competitive_scenario=CompetitiveScenario(
                scenario_type="golden",
                description="HP uses Algolia.",
            ),
            competitive_summary="Dell faces competitive pressure.",
            top_competitive_angles=["Golden Angle: HP uses Algolia"],
        )
        result = validate_output(output, self._make_sources())
        assert result.passed is True
        assert result.checks_run == 9
        assert result.checks_passed == 9
        assert result.errors == []

    def test_empty_domain_fails(self) -> None:
        output = CompetitorsOutput(
            domain="",
            competitive_summary="Test",
            top_competitive_angles=["Angle"],
            tech_comparisons=[TechComparison(company_name="A", domain="a.com")],
        )
        result = validate_output(output, self._make_sources())
        assert result.passed is False
        assert any("domain is empty" in e for e in result.errors)

    def test_no_comparisons_fails(self) -> None:
        output = CompetitorsOutput(
            domain="test.com",
            competitive_summary="Test",
            top_competitive_angles=["Angle"],
        )
        result = validate_output(output, self._make_sources())
        assert result.passed is False
        assert any("No comparison data" in e for e in result.errors)

    def test_empty_summary_fails(self) -> None:
        output = CompetitorsOutput(
            domain="test.com",
            tech_comparisons=[TechComparison(company_name="A", domain="a.com")],
            competitive_summary="",
            top_competitive_angles=["Angle"],
        )
        result = validate_output(output, self._make_sources())
        assert result.passed is False
        assert any("competitive_summary is empty" in e for e in result.errors)

    def test_no_angles_fails(self) -> None:
        output = CompetitorsOutput(
            domain="test.com",
            tech_comparisons=[TechComparison(company_name="A", domain="a.com")],
            competitive_summary="Summary",
            top_competitive_angles=[],
        )
        result = validate_output(output, self._make_sources())
        assert result.passed is False
        assert any("top_competitive_angles is empty" in e for e in result.errors)

    def test_no_sources_fails(self) -> None:
        output = CompetitorsOutput(
            domain="test.com",
            tech_comparisons=[TechComparison(company_name="A", domain="a.com")],
            competitive_summary="Summary",
            top_competitive_angles=["Angle"],
        )
        result = validate_output(output, [])
        assert result.passed is False
        assert any("No sources" in e for e in result.errors)

    def test_empty_company_name_fails(self) -> None:
        output = CompetitorsOutput(
            domain="test.com",
            tech_comparisons=[TechComparison(company_name="", domain="a.com")],
            competitive_summary="Summary",
            top_competitive_angles=["Angle"],
        )
        result = validate_output(output, self._make_sources())
        assert result.passed is False
        assert any("empty company_name" in e for e in result.errors)

    def test_golden_not_in_tech_fails(self) -> None:
        output = CompetitorsOutput(
            domain="test.com",
            tech_comparisons=[TechComparison(company_name="A", domain="a.com")],
            golden_angle_competitors=["B"],
            competitive_summary="Summary",
            top_competitive_angles=["Angle"],
        )
        result = validate_output(output, self._make_sources())
        assert result.passed is False
        assert any("golden_angle_competitors" in e for e in result.errors)

    def test_unknown_position_is_warning(self) -> None:
        output = CompetitorsOutput(
            domain="test.com",
            tech_comparisons=[TechComparison(company_name="A", domain="a.com")],
            competitive_position="unknown",
            competitive_summary="Summary",
            top_competitive_angles=["Angle"],
        )
        result = validate_output(output, self._make_sources())
        # Warning, not error -- should still pass
        assert result.passed is True
        assert any("unknown" in w for w in result.warnings)

    def test_none_scenario_is_warning(self) -> None:
        output = CompetitorsOutput(
            domain="test.com",
            tech_comparisons=[TechComparison(company_name="A", domain="a.com")],
            competitive_scenario=None,
            competitive_summary="Summary",
            top_competitive_angles=["Angle"],
        )
        result = validate_output(output, self._make_sources())
        assert result.passed is True
        assert any("scenario" in w.lower() for w in result.warnings)
