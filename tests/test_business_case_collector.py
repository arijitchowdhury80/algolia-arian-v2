"""Tests for synth-business-case collector extraction logic and validator.

Tests the pure extraction functions with synthetic data. No DB or API calls.
"""

from __future__ import annotations

from prism_platform.core.types import EvidenceTier, Source
from prism_platform.modules.synth_business_case.collector import (
    extract_executive_quotes,
    extract_financial_data,
    extract_search_vendor,
    extract_timing_signals_from_modules,
    extract_traffic_data,
)
from prism_platform.modules.synth_business_case.schemas import (
    BusinessCaseOutput,
    CustomerProof,
    DisplacementCost,
    SaidVsFoundRow,
    TimingSignal,
    ValueLever,
)
from prism_platform.modules.synth_business_case.validator import validate_output

# ---------------------------------------------------------------------------
# Sample upstream data fixtures
# ---------------------------------------------------------------------------

SAMPLE_INVESTOR_OUTPUT: dict = {
    "key_quotes": ["We are doubling down on digital transformation."],
    "executive_quotes": [
        {
            "quote": "Search is critical to our ecommerce strategy.",
            "speaker": "CFO Jane Smith",
            "source": "Q4 earnings call",
        },
        {
            "quote": "We need to improve the online experience.",
            "speaker": "CEO John Doe",
            "source": "Annual shareholder meeting",
        },
    ],
    "search_mentions": 5,
    "digital_commitment_level": "high",
}

SAMPLE_SOCIAL_OUTPUT: dict = {
    "key_quotes": ["Excited to announce our new AI-powered search."],
    "search_mentions": 3,
    "digital_commitment_level": "medium",
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

SAMPLE_TECHSTACK_OUTPUT: dict = {
    "search_vendor": {
        "name": "Elasticsearch",
        "status": "ACTIVE",
        "detection_source": "BuiltWith v22 API",
        "evidence_tier": "VERIFIED",
    },
    "ecommerce_platform": "Salesforce Commerce Cloud",
}

SAMPLE_TRAFFIC_OUTPUT: dict = {
    "total_visits": 50_000_000,
    "bounce_rate": 0.35,
    "pages_per_visit": 4.2,
    "traffic_sources": {
        "organic_search": 0.45,
        "paid_search": 0.15,
        "direct": 0.25,
    },
}

SAMPLE_NEWS_OUTPUT: dict = {
    "articles": [
        {"title": "Dell announces digital transformation initiative", "summary": "Big push"},
        {"title": "Dell hires new CTO", "summary": "Leadership change"},
    ],
}

SAMPLE_HIRING_OUTPUT: dict = {
    "total_open_roles": 450,
    "search_related_roles": 12,
    "build_vs_buy": "buy",
    "hiring_trend": "accelerating",
}

SAMPLE_COMPETITORS_OUTPUT: dict = {
    "golden_angle_competitors": ["HP Inc"],
    "competitive_summary": "Dell faces increasing competitive pressure.",
    "top_competitive_angles": ["Golden Angle: HP trusts Algolia"],
}


# ---------------------------------------------------------------------------
# extract_executive_quotes
# ---------------------------------------------------------------------------
class TestExtractExecutiveQuotes:
    def test_full_extraction(self) -> None:
        quotes = extract_executive_quotes(SAMPLE_INVESTOR_OUTPUT, SAMPLE_SOCIAL_OUTPUT)
        assert len(quotes) >= 3
        assert any("Search is critical" in q for q in quotes)
        assert any("AI-powered search" in q for q in quotes)

    def test_investor_only(self) -> None:
        quotes = extract_executive_quotes(SAMPLE_INVESTOR_OUTPUT, None)
        assert len(quotes) >= 2

    def test_social_only(self) -> None:
        quotes = extract_executive_quotes(None, SAMPLE_SOCIAL_OUTPUT)
        assert len(quotes) == 1

    def test_both_none(self) -> None:
        quotes = extract_executive_quotes(None, None)
        assert quotes == []

    def test_empty_dicts(self) -> None:
        quotes = extract_executive_quotes({}, {})
        assert quotes == []

    def test_deduplication(self) -> None:
        """Same quote in both sources should not appear twice."""
        investor = {
            "key_quotes": ["Excited to announce our new AI-powered search."],
        }
        social = {
            "key_quotes": ["Excited to announce our new AI-powered search."],
        }
        quotes = extract_executive_quotes(investor, social)
        assert quotes.count("Excited to announce our new AI-powered search.") == 1

    def test_speaker_attribution(self) -> None:
        quotes = extract_executive_quotes(SAMPLE_INVESTOR_OUTPUT, None)
        assert any("CFO Jane Smith" in q for q in quotes)


# ---------------------------------------------------------------------------
# extract_financial_data
# ---------------------------------------------------------------------------
class TestExtractFinancialData:
    def test_public_company(self) -> None:
        data = extract_financial_data(SAMPLE_FINANCIAL_PUBLIC_OUTPUT, None)
        assert data["revenue"] == 102_300_000_000.0
        assert data["revenue_growth_pct"] == 8.5
        assert data["digital_revenue_pct"] == 45.0
        assert data["market_cap"] == 85_000_000_000.0

    def test_ecommerce_revenue_calculated(self) -> None:
        data = extract_financial_data(SAMPLE_FINANCIAL_PUBLIC_OUTPUT, None)
        expected = 102_300_000_000.0 * 45.0 / 100.0
        assert data["ecommerce_revenue"] == expected

    def test_private_company(self) -> None:
        data = extract_financial_data(None, SAMPLE_FINANCIAL_PRIVATE_OUTPUT)
        assert data["revenue"] == 500_000_000.0
        assert data["revenue_growth_pct"] == 12.0

    def test_both_none(self) -> None:
        data = extract_financial_data(None, None)
        assert data["revenue"] is None
        assert data["revenue_growth_pct"] is None

    def test_public_preferred(self) -> None:
        """When both available, public is used (it's first in the or expression)."""
        data = extract_financial_data(
            SAMPLE_FINANCIAL_PUBLIC_OUTPUT, SAMPLE_FINANCIAL_PRIVATE_OUTPUT
        )
        assert data["revenue"] == 102_300_000_000.0

    def test_invalid_revenue_type(self) -> None:
        data = extract_financial_data({"revenue": "not a number"}, None)
        assert data["revenue"] is None


# ---------------------------------------------------------------------------
# extract_search_vendor
# ---------------------------------------------------------------------------
class TestExtractSearchVendor:
    def test_dict_vendor(self) -> None:
        vendor = extract_search_vendor(SAMPLE_TECHSTACK_OUTPUT)
        assert vendor == "Elasticsearch"

    def test_string_vendor(self) -> None:
        vendor = extract_search_vendor({"search_vendor": "Algolia"})
        assert vendor == "Algolia"

    def test_none_input(self) -> None:
        vendor = extract_search_vendor(None)
        assert vendor is None

    def test_empty_dict(self) -> None:
        vendor = extract_search_vendor({})
        assert vendor is None

    def test_no_vendor_key(self) -> None:
        vendor = extract_search_vendor({"other_key": "value"})
        assert vendor is None

    def test_null_vendor(self) -> None:
        vendor = extract_search_vendor({"search_vendor": None})
        assert vendor is None


# ---------------------------------------------------------------------------
# extract_traffic_data
# ---------------------------------------------------------------------------
class TestExtractTrafficData:
    def test_full_extraction(self) -> None:
        data = extract_traffic_data(SAMPLE_TRAFFIC_OUTPUT)
        assert data["monthly_visits"] == 50_000_000
        assert data["bounce_rate"] == 0.35
        assert data["pages_per_visit"] == 4.2
        assert data["organic_search_pct"] == 0.45

    def test_none_input(self) -> None:
        data = extract_traffic_data(None)
        assert data["monthly_visits"] is None
        assert data["bounce_rate"] is None

    def test_empty_dict(self) -> None:
        data = extract_traffic_data({})
        assert data["monthly_visits"] is None

    def test_partial_data(self) -> None:
        data = extract_traffic_data({"total_visits": 1_000_000})
        assert data["monthly_visits"] == 1_000_000
        assert data["bounce_rate"] is None

    def test_invalid_visits_type(self) -> None:
        data = extract_traffic_data({"total_visits": "not a number"})
        assert data["monthly_visits"] is None


# ---------------------------------------------------------------------------
# extract_timing_signals_from_modules
# ---------------------------------------------------------------------------
class TestExtractTimingSignals:
    def test_full_extraction(self) -> None:
        signals = extract_timing_signals_from_modules(
            SAMPLE_NEWS_OUTPUT,
            SAMPLE_HIRING_OUTPUT,
            SAMPLE_INVESTOR_OUTPUT,
            SAMPLE_COMPETITORS_OUTPUT,
        )
        assert len(signals) >= 4
        sources = [s["source_module"] for s in signals]
        assert "intel-news" in sources
        assert "intel-hiring" in sources
        assert "intel-investor" in sources
        assert "intel-competitors" in sources

    def test_news_only(self) -> None:
        signals = extract_timing_signals_from_modules(SAMPLE_NEWS_OUTPUT, None, None, None)
        assert len(signals) >= 1
        assert all(s["source_module"] == "intel-news" for s in signals)

    def test_hiring_signals(self) -> None:
        signals = extract_timing_signals_from_modules(None, SAMPLE_HIRING_OUTPUT, None, None)
        assert len(signals) >= 1
        assert any("search-related" in s["signal"] for s in signals)

    def test_all_none(self) -> None:
        signals = extract_timing_signals_from_modules(None, None, None, None)
        assert signals == []

    def test_golden_angle_signal(self) -> None:
        signals = extract_timing_signals_from_modules(None, None, None, SAMPLE_COMPETITORS_OUTPUT)
        assert len(signals) >= 1
        assert any("HP Inc" in s["signal"] for s in signals)

    def test_no_hiring_signal_when_zero_roles(self) -> None:
        signals = extract_timing_signals_from_modules(
            None, {"search_related_roles": 0, "hiring_trend": "stable"}, None, None
        )
        assert not any("search-related" in s.get("signal", "") for s in signals)


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------
class TestValidator:
    def _make_sources(self, count: int = 1) -> list[Source]:
        return [
            Source(
                field="upstream.intel-company",
                value="test",
                tier=EvidenceTier.VERIFIED,
                source_label="test",
                method="db_read",
            )
            for _ in range(count)
        ]

    def _make_valid_output(self) -> BusinessCaseOutput:
        return BusinessCaseOutput(
            domain="dell.com",
            said_vs_found=[
                SaidVsFoundRow(
                    exec_said=f"Quote {i}",
                    we_found=f"Finding {i}",
                    competitors_doing=f"Action {i}",
                    your_move=f"Move {i}",
                    category="search_quality",
                )
                for i in range(5)
            ],
            value_levers=[
                ValueLever(
                    lever_name=f"Lever {i}",
                    description=f"Desc {i}",
                    conservative_estimate=float(i * 100_000),
                    moderate_estimate=float(i * 200_000),
                )
                for i in range(1, 5)
            ],
            total_conservative_impact=1_000_000.0,
            total_moderate_impact=2_000_000.0,
            displacement=DisplacementCost(
                current_vendor="Elasticsearch",
                net_benefit_3yr=500_000.0,
            ),
            customer_proofs=[
                CustomerProof(
                    customer_name="Lacoste",
                    industry="Retail",
                    key_metric="37% lift",
                ),
            ],
            timing_signals=[
                TimingSignal(
                    signal="Digital initiative announced",
                    source_module="intel-investor",
                    urgency="high",
                    reason="Budget allocated",
                ),
            ],
            urgency_summary="Act now.",
            executive_summary="Dell has a massive opportunity.",
            one_line_pitch="Dell can unlock $1M by switching to Algolia.",
        )

    def test_valid_full_output(self) -> None:
        result = validate_output(self._make_valid_output(), self._make_sources())
        assert result.passed is True
        assert result.checks_run == 10
        assert result.checks_passed == 10
        assert result.errors == []

    def test_empty_domain_fails(self) -> None:
        output = self._make_valid_output()
        output = output.model_copy(update={"domain": ""})
        result = validate_output(output, self._make_sources())
        assert result.passed is False
        assert any("domain is empty" in e for e in result.errors)

    def test_too_few_said_vs_found_fails(self) -> None:
        output = self._make_valid_output()
        output = output.model_copy(update={"said_vs_found": output.said_vs_found[:2]})
        result = validate_output(output, self._make_sources())
        assert result.passed is False
        assert any("said_vs_found" in e for e in result.errors)

    def test_empty_said_vs_found_column_fails(self) -> None:
        output = self._make_valid_output()
        bad_rows = list(output.said_vs_found)
        bad_rows[0] = bad_rows[0].model_copy(update={"exec_said": ""})
        output = output.model_copy(update={"said_vs_found": bad_rows})
        result = validate_output(output, self._make_sources())
        assert result.passed is False
        assert any("empty columns" in e for e in result.errors)

    def test_too_few_value_levers_fails(self) -> None:
        output = self._make_valid_output()
        output = output.model_copy(update={"value_levers": output.value_levers[:2]})
        result = validate_output(output, self._make_sources())
        assert result.passed is False
        assert any("value_levers" in e for e in result.errors)

    def test_missing_conservative_total_fails(self) -> None:
        output = self._make_valid_output()
        output = output.model_copy(update={"total_conservative_impact": None})
        result = validate_output(output, self._make_sources())
        assert result.passed is False
        assert any("total_conservative_impact" in e for e in result.errors)

    def test_empty_executive_summary_fails(self) -> None:
        output = self._make_valid_output()
        output = output.model_copy(update={"executive_summary": ""})
        result = validate_output(output, self._make_sources())
        assert result.passed is False
        assert any("executive_summary" in e for e in result.errors)

    def test_no_sources_fails(self) -> None:
        result = validate_output(self._make_valid_output(), [])
        assert result.passed is False
        assert any("No sources" in e for e in result.errors)

    def test_no_timing_signals_fails(self) -> None:
        output = self._make_valid_output()
        output = output.model_copy(update={"timing_signals": []})
        result = validate_output(output, self._make_sources())
        assert result.passed is False
        assert any("timing_signals" in e for e in result.errors)

    def test_empty_one_line_pitch_fails(self) -> None:
        output = self._make_valid_output()
        output = output.model_copy(update={"one_line_pitch": ""})
        result = validate_output(output, self._make_sources())
        assert result.passed is False
        assert any("one_line_pitch" in e for e in result.errors)

    def test_no_customer_proofs_fails(self) -> None:
        output = self._make_valid_output()
        output = output.model_copy(update={"customer_proofs": []})
        result = validate_output(output, self._make_sources())
        assert result.passed is False
        assert any("customer_proofs" in e for e in result.errors)

    def test_no_levers_conservative_warning(self) -> None:
        """When no levers at all, check 5 passes with a warning."""
        output = self._make_valid_output()
        output = output.model_copy(
            update={
                "value_levers": [],
                "total_conservative_impact": None,
                "total_moderate_impact": None,
            }
        )
        result = validate_output(output, self._make_sources())
        # Will fail on check 4 (too few levers), but check 5 should just warn
        assert any("cannot be calculated" in w for w in result.warnings)
