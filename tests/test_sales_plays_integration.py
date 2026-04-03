"""Integration tests for synth-sales-plays -- tests enricher with real Gemini API calls.

These tests call the real Gemini API. They are NOT mocked.
Requires GEMINI_API_KEY to be set in the environment.
"""

from __future__ import annotations

import os

import pytest

from prism_platform.modules.synth_sales_plays.enricher import (
    MEDDPICCSynthesis,
    ObjectionSynthesis,
    PowerMapSynthesis,
    SalesPlaysEnricher,
    SPINSynthesis,
    SummarySynthesis,
    TalkTrackSynthesis,
)

# Skip the entire module if no Gemini API key is configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set -- skipping Gemini integration tests",
)


@pytest.fixture
def enricher() -> SalesPlaysEnricher:
    """Create an enricher instance for testing."""
    return SalesPlaysEnricher()


@pytest.fixture
def sample_base_context() -> str:
    """Build a realistic base context for LLM calls."""
    return (
        "# Prospect: Dell Technologies (dell.com)\n"
        "Vertical: Technology / Enterprise Hardware\n"
        "Description: Global technology company providing servers, storage, and PCs\n"
        "Employee Count: 130,000\n\n"
        "## Financial Context\n"
        "Revenue: $90,000,000,000\n"
        "Revenue Growth: 8.2%\n"
        "Digital Revenue %: 35.0%\n\n"
        "## Competitive Context\n"
        "Current Search Vendor: Coveo\n"
        "Competitors Using Algolia: HP, Lenovo\n"
        "Tech Gaps: No AI-powered search; legacy autocomplete\n"
        "Summary: Dell lags HP and Lenovo in search technology adoption\n\n"
        "## Executive Quotes\n"
        '- "Our digital transformation is accelerating" -- Michael Dell (investor_intelligence)\n'
        '- "Search and discovery are critical to our B2B commerce strategy" '
        "-- CFO (investor_intelligence)\n\n"
        "## Buying Committee\n"
        "- Sarah Johnson | VP of Digital Commerce | Tier: Economic Buyer\n"
        "- Mike Chen | Director of Search & Discovery | Tier: Champion\n"
        "- Lisa Park | Head of Procurement | Tier: Paper Process\n"
        "- David Kim | Principal Engineer, Search Team | Tier: Technical Evaluator\n\n"
        "## Business Case\n"
        "Estimated ROI: $2,500,000\n"
        "Summary: Strong ROI driven by search conversion and operational efficiency\n"
        "Value Drivers:\n"
        "  - Search conversion improvement: +25%\n"
        "  - Reduced search bounce rate: -40%\n"
        "  - Engineering time saved: 2 FTEs\n"
    )


class TestMEDDPICCSynthesis:
    def test_generates_meddpicc_fields(
        self, enricher: SalesPlaysEnricher, sample_base_context: str
    ) -> None:
        prompt = enricher._build_meddpicc_prompt(sample_base_context)
        result = enricher._call_llm(
            prompt=prompt,
            response_model=MEDDPICCSynthesis,
            call_label="test_meddpicc",
            domain="dell.com",
        )
        assert isinstance(result, MEDDPICCSynthesis)
        assert len(result.fields) >= 3
        field_names = {f.field_name for f in result.fields}
        # Should have at least some of the key fields
        assert len(field_names) >= 3

    def test_meddpicc_fields_have_evidence(
        self, enricher: SalesPlaysEnricher, sample_base_context: str
    ) -> None:
        prompt = enricher._build_meddpicc_prompt(sample_base_context)
        result = enricher._call_llm(
            prompt=prompt,
            response_model=MEDDPICCSynthesis,
            call_label="test_meddpicc_evidence",
            domain="dell.com",
        )
        for field in result.fields:
            assert field.evidence.strip() != ""
            assert field.recommended_approach.strip() != ""


class TestSPINSynthesis:
    def test_generates_spin_questions(
        self, enricher: SalesPlaysEnricher, sample_base_context: str
    ) -> None:
        prompt = enricher._build_spin_prompt(sample_base_context)
        result = enricher._call_llm(
            prompt=prompt,
            response_model=SPINSynthesis,
            call_label="test_spin",
            domain="dell.com",
        )
        assert isinstance(result, SPINSynthesis)
        assert len(result.questions) >= 6

    def test_spin_covers_categories(
        self, enricher: SalesPlaysEnricher, sample_base_context: str
    ) -> None:
        prompt = enricher._build_spin_prompt(sample_base_context)
        result = enricher._call_llm(
            prompt=prompt,
            response_model=SPINSynthesis,
            call_label="test_spin_categories",
            domain="dell.com",
        )
        categories = {q.category for q in result.questions}
        # Should cover at least 3 of 4 categories
        assert len(categories) >= 3


class TestObjectionSynthesis:
    def test_generates_objections(
        self, enricher: SalesPlaysEnricher, sample_base_context: str
    ) -> None:
        prompt = enricher._build_objection_prompt(sample_base_context)
        result = enricher._call_llm(
            prompt=prompt,
            response_model=ObjectionSynthesis,
            call_label="test_objections",
            domain="dell.com",
        )
        assert isinstance(result, ObjectionSynthesis)
        assert len(result.handlers) >= 2

    def test_objections_have_counters(
        self, enricher: SalesPlaysEnricher, sample_base_context: str
    ) -> None:
        prompt = enricher._build_objection_prompt(sample_base_context)
        result = enricher._call_llm(
            prompt=prompt,
            response_model=ObjectionSynthesis,
            call_label="test_objection_counters",
            domain="dell.com",
        )
        for handler in result.handlers:
            assert handler.objection.strip() != ""
            assert handler.counter.strip() != ""


class TestTalkTrackSynthesis:
    def test_generates_talk_tracks(
        self, enricher: SalesPlaysEnricher, sample_base_context: str
    ) -> None:
        prompt = enricher._build_talk_track_prompt(sample_base_context)
        result = enricher._call_llm(
            prompt=prompt,
            response_model=TalkTrackSynthesis,
            call_label="test_talk_tracks",
            domain="dell.com",
        )
        assert isinstance(result, TalkTrackSynthesis)
        assert len(result.tracks) >= 2


class TestPowerMapSynthesis:
    def test_generates_power_map(
        self, enricher: SalesPlaysEnricher, sample_base_context: str
    ) -> None:
        prompt = enricher._build_power_map_prompt(sample_base_context)
        result = enricher._call_llm(
            prompt=prompt,
            response_model=PowerMapSynthesis,
            call_label="test_power_map",
            domain="dell.com",
        )
        assert isinstance(result, PowerMapSynthesis)
        assert len(result.members) >= 1

    def test_power_map_has_roles(
        self, enricher: SalesPlaysEnricher, sample_base_context: str
    ) -> None:
        prompt = enricher._build_power_map_prompt(sample_base_context)
        result = enricher._call_llm(
            prompt=prompt,
            response_model=PowerMapSynthesis,
            call_label="test_power_map_roles",
            domain="dell.com",
        )
        for member in result.members:
            assert member.name.strip() != ""
            assert member.title.strip() != ""


class TestSummarySynthesis:
    def test_generates_summary(
        self, enricher: SalesPlaysEnricher, sample_base_context: str
    ) -> None:
        prompt = enricher._build_summary_prompt(
            base_context=sample_base_context,
            meddpicc_count=6,
            spin_count=10,
            objection_count=4,
            power_map_count=4,
        )
        result = enricher._call_llm(
            prompt=prompt,
            response_model=SummarySynthesis,
            call_label="test_summary",
            domain="dell.com",
        )
        assert isinstance(result, SummarySynthesis)
        assert result.playbook_summary.strip() != ""
        assert len(result.top_3_actions) == 3

    def test_actions_are_specific(
        self, enricher: SalesPlaysEnricher, sample_base_context: str
    ) -> None:
        prompt = enricher._build_summary_prompt(
            base_context=sample_base_context,
            meddpicc_count=6,
            spin_count=10,
            objection_count=4,
            power_map_count=4,
        )
        result = enricher._call_llm(
            prompt=prompt,
            response_model=SummarySynthesis,
            call_label="test_actions_specific",
            domain="dell.com",
        )
        for action in result.top_3_actions:
            assert action.strip() != ""
            assert len(action) > 10  # Actions should be substantive


class TestFullSynthesis:
    @pytest.mark.asyncio
    async def test_full_synthesize(self, enricher: SalesPlaysEnricher) -> None:
        """End-to-end test: run all 6 LLM calls and verify output structure."""
        output, llm_calls, llm_cost = await enricher.synthesize(
            domain="dell.com",
            company_name="Dell Technologies",
            company_context={
                "company_name": "Dell Technologies",
                "vertical": "Technology",
                "description": "Global technology company",
                "employee_count": 130000,
            },
            buying_committee=[
                {"name": "Sarah Johnson", "title": "VP Digital Commerce", "tier": "Economic Buyer"},
                {"name": "Mike Chen", "title": "Dir Search", "tier": "Champion"},
            ],
            exec_quotes=[
                {
                    "quote": "Digital transformation is our top priority",
                    "speaker": "Michael Dell",
                    "source": "investor_intelligence",
                },
            ],
            competitive_context={
                "current_vendor": "Coveo",
                "golden_angle_competitors": ["HP"],
                "tech_gaps": ["No AI search"],
                "competitive_summary": "Lagging behind peers",
            },
            financial_context={
                "revenue": 90000000000,
                "revenue_growth_pct": 8.2,
                "digital_revenue_pct": 35.0,
            },
            business_case_context={
                "total_roi_usd": 2500000,
                "roi_summary": "Strong ROI",
                "value_drivers": ["Search conversion", "Bounce rate reduction"],
            },
            raw_data={},
        )

        assert output.domain == "dell.com"
        assert llm_calls >= 4
        assert llm_cost > 0

        # Verify structure populated
        assert len(output.meddpicc) > 0
        assert len(output.spin_questions) > 0
        assert len(output.objection_handlers) > 0
        assert len(output.talk_tracks) > 0
        assert len(output.power_map) > 0
        assert output.playbook_summary.strip() != ""
        assert len(output.top_3_actions) > 0
