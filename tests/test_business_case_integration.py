"""Integration tests for synth-business-case module.

Tests module metadata, enricher helper logic, and Gemini-based synthesis (if API key available).
"""

from __future__ import annotations

import os

import pytest

from prism_platform.modules.synth_business_case.enricher import BusinessCaseEnricher
from prism_platform.modules.synth_business_case.module import BusinessCaseModule
from prism_platform.modules.synth_business_case.schemas import (
    BusinessCaseInput,
    BusinessCaseOutput,
    ValueLever,
)


# ---------------------------------------------------------------------------
# Module metadata tests
# ---------------------------------------------------------------------------
class TestModuleMetadata:
    def test_module_name(self) -> None:
        mod = BusinessCaseModule()
        assert mod.name == "synth-business-case"

    def test_module_version(self) -> None:
        mod = BusinessCaseModule()
        assert mod.version == "0.1.0"

    def test_module_layer(self) -> None:
        mod = BusinessCaseModule()
        assert mod.layer == "synthesis"

    def test_module_dependencies(self) -> None:
        mod = BusinessCaseModule()
        assert "intel-company" in mod.dependencies
        assert "intel-investor" in mod.dependencies
        assert "intel-industry" in mod.dependencies
        assert "intel-competitors" in mod.dependencies

    def test_module_requires_llm(self) -> None:
        mod = BusinessCaseModule()
        assert mod.requires_llm is True

    def test_module_timeout(self) -> None:
        mod = BusinessCaseModule()
        assert mod.timeout_seconds == 300

    def test_module_max_retries(self) -> None:
        mod = BusinessCaseModule()
        assert mod.max_retries == 2

    def test_input_schema(self) -> None:
        mod = BusinessCaseModule()
        assert mod.input_schema is BusinessCaseInput

    def test_output_schema(self) -> None:
        mod = BusinessCaseModule()
        assert mod.output_schema is BusinessCaseOutput


# ---------------------------------------------------------------------------
# Enricher helper logic
# ---------------------------------------------------------------------------
class TestEnricherHelpers:
    def test_sum_estimates_conservative(self) -> None:
        levers = [
            ValueLever(lever_name="A", description="D", conservative_estimate=100.0),
            ValueLever(lever_name="B", description="D", conservative_estimate=200.0),
            ValueLever(lever_name="C", description="D", conservative_estimate=None),
        ]
        total = BusinessCaseEnricher._sum_estimates(levers, "conservative_estimate")
        assert total == 300.0

    def test_sum_estimates_moderate(self) -> None:
        levers = [
            ValueLever(lever_name="A", description="D", moderate_estimate=500.0),
            ValueLever(lever_name="B", description="D", moderate_estimate=700.0),
        ]
        total = BusinessCaseEnricher._sum_estimates(levers, "moderate_estimate")
        assert total == 1200.0

    def test_sum_estimates_all_none(self) -> None:
        levers = [
            ValueLever(lever_name="A", description="D"),
            ValueLever(lever_name="B", description="D"),
        ]
        total = BusinessCaseEnricher._sum_estimates(levers, "conservative_estimate")
        assert total is None

    def test_sum_estimates_empty_list(self) -> None:
        total = BusinessCaseEnricher._sum_estimates([], "conservative_estimate")
        assert total is None

    def test_build_context_string(self) -> None:
        enricher = BusinessCaseEnricher()
        context = enricher._build_context_string(
            domain="dell.com",
            company_name="Dell Inc",
            raw_data={
                "intel-company": {"description": "Dell makes computers", "employee_count": 165000},
                "intel-competitors": {
                    "competitive_summary": "Dell faces competition",
                    "golden_angle_competitors": ["HP Inc"],
                    "top_competitive_angles": ["HP uses Algolia"],
                },
            },
            executive_quotes=["We are investing in digital."],
            financial_data={
                "revenue": 102_300_000_000.0,
                "revenue_growth_pct": 8.5,
                "digital_revenue_pct": 45.0,
                "ecommerce_revenue": 46_035_000_000.0,
            },
            search_vendor="Elasticsearch",
            traffic_data={
                "monthly_visits": 50_000_000,
                "bounce_rate": 0.35,
                "organic_search_pct": 0.45,
            },
        )
        assert "Dell Inc" in context
        assert "dell.com" in context
        assert "Elasticsearch" in context
        assert "$102,300,000,000" in context
        assert "HP Inc" in context

    def test_build_said_vs_found_prompt(self) -> None:
        prompt = BusinessCaseEnricher._build_said_vs_found_prompt(
            context_str="Context here",
            executive_quotes=["We are doubling down on digital."],
        )
        assert "Said vs Found" in prompt
        assert "doubling down" in prompt
        assert "exec_said" in prompt

    def test_build_roi_prompt(self) -> None:
        prompt = BusinessCaseEnricher._build_roi_prompt(
            context_str="Context here",
            financial_data={"revenue": 1_000_000.0},
            traffic_data={"monthly_visits": 500_000},
        )
        assert "ROI" in prompt
        assert "conservative_estimate" in prompt

    def test_build_displacement_prompt(self) -> None:
        prompt = BusinessCaseEnricher._build_displacement_prompt(
            context_str="Context here",
            search_vendor="Elasticsearch",
            financial_data={"revenue": 1_000_000.0},
        )
        assert "Elasticsearch" in prompt
        assert "displacement" in prompt.lower()

    def test_build_customer_proof_prompt(self) -> None:
        levers = [
            ValueLever(lever_name="Conversion Uplift", description="Better search"),
        ]
        prompt = BusinessCaseEnricher._build_customer_proof_prompt(
            context_str="Context here",
            value_levers=levers,
            industry_output=None,
        )
        assert "Conversion Uplift" in prompt
        assert "Algolia" in prompt

    def test_build_timing_prompt(self) -> None:
        signals = [{"signal": "Test signal", "source_module": "intel-news"}]
        prompt = BusinessCaseEnricher._build_timing_prompt(
            context_str="Context here",
            raw_timing_signals=signals,
        )
        assert "Test signal" in prompt
        assert "urgency" in prompt.lower()

    def test_build_executive_summary_prompt(self) -> None:
        from prism_platform.modules.synth_business_case.schemas import (
            CustomerProof,
            SaidVsFoundRow,
            TimingSignal,
        )

        prompt = BusinessCaseEnricher._build_executive_summary_prompt(
            context_str="Context here",
            said_vs_found=[
                SaidVsFoundRow(
                    exec_said="Q",
                    we_found="F",
                    competitors_doing="C",
                    your_move="M",
                    category="search_quality",
                )
            ],
            value_levers=[
                ValueLever(lever_name="Test Lever", description="D", conservative_estimate=100.0),
            ],
            total_conservative=100.0,
            total_moderate=200.0,
            customer_proofs=[
                CustomerProof(customer_name="Lacoste", industry="Retail", key_metric="37% lift"),
            ],
            timing_signals=[
                TimingSignal(signal="S", source_module="intel-news", urgency="high", reason="R"),
            ],
            displacement=None,
        )
        assert "executive summary" in prompt.lower()
        assert "Test Lever" in prompt
        assert "$100" in prompt
        assert "Lacoste" in prompt


# ---------------------------------------------------------------------------
# Registry test
# ---------------------------------------------------------------------------
class TestRegistry:
    def test_module_in_registry(self) -> None:
        from prism_platform.core.registry import MODULE_REGISTRY, register_all_modules

        register_all_modules()
        assert "synth-business-case" in MODULE_REGISTRY
        assert MODULE_REGISTRY["synth-business-case"].name == "synth-business-case"


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_returns_bool(self) -> None:
        mod = BusinessCaseModule()
        result = await mod.health_check()
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Gemini enricher integration test (requires GEMINI_API_KEY)
# ---------------------------------------------------------------------------
HAS_GEMINI_KEY = bool(os.environ.get("GEMINI_API_KEY", ""))


@pytest.mark.skipif(not HAS_GEMINI_KEY, reason="GEMINI_API_KEY not set")
class TestEnricherWithGemini:
    """Integration tests that call real Gemini API. Skipped if no key."""

    @pytest.mark.asyncio
    async def test_full_synthesis(self) -> None:
        enricher = BusinessCaseEnricher()

        raw_data = {
            "intel-company": {
                "description": "Dell Technologies is a multinational technology company",
                "employee_count": 165000,
                "headquarters": "Round Rock, TX",
            },
            "intel-financial-public": {
                "revenue": 102_300_000_000.0,
                "revenue_growth_pct": 8.5,
                "digital_revenue_pct": 45.0,
                "market_cap": 85_000_000_000.0,
            },
            "intel-traffic": {
                "total_visits": 50_000_000,
                "bounce_rate": 0.35,
                "pages_per_visit": 4.2,
                "traffic_sources": {"organic_search": 0.45},
            },
            "intel-techstack": {
                "search_vendor": {"name": "Elasticsearch", "status": "ACTIVE"},
            },
            "intel-competitors": {
                "competitive_summary": (
                    "Dell faces increasing competitive pressure from HP and Lenovo."
                ),
                "golden_angle_competitors": ["HP Inc"],
                "top_competitive_angles": ["HP uses Algolia for product search"],
            },
            "intel-investor": {
                "key_quotes": ["We are investing heavily in digital transformation."],
                "executive_quotes": [
                    {
                        "quote": "Our ecommerce channel is growing 2x the rate of retail.",
                        "speaker": "CFO",
                        "source": "Q4 2024 earnings",
                    }
                ],
                "digital_commitment_level": "high",
                "search_mentions": 3,
            },
            "intel-industry": {
                "vertical": "Technology / PC Manufacturing",
                "case_studies": [
                    {
                        "customer": "Lacoste",
                        "metric": "37% conversion lift",
                        "industry": "Retail",
                    },
                ],
            },
            "intel-hiring": {
                "search_related_roles": 8,
                "hiring_trend": "accelerating",
                "build_vs_buy": "buy",
            },
            "intel-news": {
                "articles": [
                    {"title": "Dell launches new AI PC lineup", "summary": "AI push"},
                ],
            },
            "intel-social": None,
            "intel-financial-private": None,
        }

        output, llm_calls, llm_cost = await enricher.synthesize(
            domain="dell.com",
            company_name="Dell Inc",
            raw_data=raw_data,
            executive_quotes=[
                "We are investing heavily in digital transformation.",
                "CFO: Our ecommerce channel is growing 2x the rate of retail. (Q4 2024 earnings)",
            ],
            financial_data={
                "revenue": 102_300_000_000.0,
                "revenue_growth_pct": 8.5,
                "digital_revenue_pct": 45.0,
                "ecommerce_revenue": 46_035_000_000.0,
            },
            search_vendor="Elasticsearch",
            traffic_data={
                "monthly_visits": 50_000_000,
                "bounce_rate": 0.35,
                "organic_search_pct": 0.45,
            },
            raw_timing_signals=[
                {"signal": "8 search-related roles open", "source_module": "intel-hiring"},
                {"signal": "HP Inc uses Algolia", "source_module": "intel-competitors"},
            ],
        )

        # Verify structured output
        assert isinstance(output, BusinessCaseOutput)
        assert output.domain == "dell.com"
        assert llm_calls >= 5  # At least 5 Gemini calls (skipping displacement if no vendor)
        assert llm_cost > 0

        # Said vs Found
        assert len(output.said_vs_found) >= 3

        # Value levers
        assert len(output.value_levers) >= 3

        # Totals
        if output.value_levers:
            assert output.total_conservative_impact is not None or all(
                lv.conservative_estimate is None for lv in output.value_levers
            )

        # Customer proofs
        assert len(output.customer_proofs) >= 1

        # Timing signals
        assert len(output.timing_signals) >= 1

        # Executive summary
        assert len(output.executive_summary) > 50
        assert len(output.one_line_pitch) > 10
