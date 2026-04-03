"""Tests for audit-factcheck collector extraction logic.

Tests the pure extraction functions with synthetic data. No DB or API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from prism_platform.modules.audit_factcheck.collector import (
    MODULE_CATEGORY_MAP,
    FactcheckCollector,
    extract_claims_from_output,
)
from prism_platform.modules.audit_factcheck.schemas import VerificationCategory

# ---------------------------------------------------------------------------
# Sample upstream data fixtures
# ---------------------------------------------------------------------------

SAMPLE_COMPANY_OUTPUT: dict = {
    "domain": "dell.com",
    "legal_name": "Dell Technologies Inc.",
    "common_name": "Dell",
    "industry": "Technology Hardware",
    "is_public": True,
    "description": (
        "Dell Technologies is a multinational technology company"
        " that develops and sells computers and IT infrastructure."
    ),
    "headquarters": "Round Rock, Texas, United States",
    "employee_count": 120000,
    "founded_year": 1984,
}

SAMPLE_FINANCIAL_PUBLIC_OUTPUT: dict = {
    "domain": "dell.com",
    "revenue": 102300000000.0,
    "revenue_growth_pct": 12.5,
    "market_cap": 95000000000.0,
    "ebitda_margin": 18.2,
    "digital_revenue_pct": 35.0,
    "fiscal_year": "FY2024",
}

SAMPLE_TECHSTACK_OUTPUT: dict = {
    "domain": "dell.com",
    "search_vendor": {"name": "Elasticsearch", "status": "ACTIVE"},
    "ecommerce_platform": "Salesforce Commerce Cloud",
    "all_technologies": [
        {"Name": "Elasticsearch", "Tag": "elasticsearch"},
        {"Name": "React", "Tag": "react"},
    ],
    "algolia_detected": False,
}

SAMPLE_TRAFFIC_OUTPUT: dict = {
    "domain": "dell.com",
    "total_visits": 250000000,
    "bounce_rate": 0.35,
    "pages_per_visit": 4.2,
    "organic_search_pct": 0.42,
}

SAMPLE_HIRING_OUTPUT: dict = {
    "domain": "dell.com",
    "total_open_roles": 450,
    "search_related_roles": 12,
    "build_vs_buy": "buy",
    "hiring_trend": "stable",
    "key_roles": [
        {"title": "Senior Search Engineer", "department": "Engineering"},
    ],
}


# ---------------------------------------------------------------------------
# extract_claims_from_output tests
# ---------------------------------------------------------------------------
class TestExtractClaimsFromOutput:
    def test_company_output_extracts_claims(self) -> None:
        claims = extract_claims_from_output(
            "intel-company", VerificationCategory.COMPANY_FACTS, SAMPLE_COMPANY_OUTPUT
        )
        assert len(claims) > 0
        assert all(c.source_module == "intel-company" for c in claims)
        assert all(c.category == VerificationCategory.COMPANY_FACTS for c in claims)

    def test_financial_output_extracts_numeric_claims(self) -> None:
        claims = extract_claims_from_output(
            "intel-financial-public",
            VerificationCategory.FINANCIAL_CLAIMS,
            SAMPLE_FINANCIAL_PUBLIC_OUTPUT,
        )
        # Should extract numeric fields like revenue, market_cap, etc.
        numeric_claims = [c for c in claims if "=" in c.claim_text]
        assert len(numeric_claims) > 0

    def test_techstack_output_extracts_claims(self) -> None:
        claims = extract_claims_from_output(
            "intel-techstack",
            VerificationCategory.TECHNOLOGY_CLAIMS,
            SAMPLE_TECHSTACK_OUTPUT,
        )
        assert len(claims) > 0

    def test_traffic_output_extracts_claims(self) -> None:
        claims = extract_claims_from_output(
            "intel-traffic",
            VerificationCategory.TRAFFIC_CLAIMS,
            SAMPLE_TRAFFIC_OUTPUT,
        )
        assert len(claims) > 0
        # Should have numeric claims for visits, bounce_rate, etc.
        numeric_claims = [c for c in claims if "=" in c.claim_text]
        assert len(numeric_claims) > 0

    def test_hiring_output_extracts_claims(self) -> None:
        claims = extract_claims_from_output(
            "intel-hiring",
            VerificationCategory.HIRING_CLAIMS,
            SAMPLE_HIRING_OUTPUT,
        )
        assert len(claims) > 0

    def test_empty_output_returns_no_claims(self) -> None:
        claims = extract_claims_from_output("intel-company", VerificationCategory.COMPANY_FACTS, {})
        assert claims == []

    def test_short_strings_skipped(self) -> None:
        """Strings <= 10 chars should not be extracted as claims."""
        claims = extract_claims_from_output(
            "intel-company",
            VerificationCategory.COMPANY_FACTS,
            {"short": "abc", "also_short": "1234567890"},
        )
        assert len(claims) == 0

    def test_nested_dict_extraction(self) -> None:
        """Should traverse nested dicts and extract claims."""
        data = {
            "outer": {
                "inner_text": "This is a nested factual claim about the company",
                "inner_num": 42,
            },
        }
        claims = extract_claims_from_output(
            "intel-company", VerificationCategory.COMPANY_FACTS, data
        )
        text_claims = [c for c in claims if "nested factual claim" in c.claim_text]
        assert len(text_claims) == 1

    def test_list_extraction(self) -> None:
        """Should traverse lists and extract claims."""
        data = {
            "items": [
                "First factual claim about company operations",
                "Second factual claim about company strategy",
            ],
        }
        claims = extract_claims_from_output(
            "intel-company", VerificationCategory.COMPANY_FACTS, data
        )
        assert len(claims) == 2


# ---------------------------------------------------------------------------
# MODULE_CATEGORY_MAP tests
# ---------------------------------------------------------------------------
class TestModuleCategoryMap:
    def test_company_maps_to_company_facts(self) -> None:
        assert MODULE_CATEGORY_MAP["intel-company"] == VerificationCategory.COMPANY_FACTS

    def test_financial_public_maps_to_financial(self) -> None:
        assert (
            MODULE_CATEGORY_MAP["intel-financial-public"] == VerificationCategory.FINANCIAL_CLAIMS
        )

    def test_financial_private_maps_to_financial(self) -> None:
        assert (
            MODULE_CATEGORY_MAP["intel-financial-private"] == VerificationCategory.FINANCIAL_CLAIMS
        )

    def test_techstack_maps_to_technology(self) -> None:
        assert MODULE_CATEGORY_MAP["intel-techstack"] == VerificationCategory.TECHNOLOGY_CLAIMS

    def test_traffic_maps_to_traffic(self) -> None:
        assert MODULE_CATEGORY_MAP["intel-traffic"] == VerificationCategory.TRAFFIC_CLAIMS

    def test_competitors_maps_to_competitive(self) -> None:
        assert MODULE_CATEGORY_MAP["intel-competitors"] == VerificationCategory.COMPETITIVE_CLAIMS

    def test_synth_business_case_maps_to_synthesis(self) -> None:
        assert MODULE_CATEGORY_MAP["synth-business-case"] == VerificationCategory.SYNTHESIS_CLAIMS

    def test_synth_sales_plays_maps_to_synthesis(self) -> None:
        assert MODULE_CATEGORY_MAP["synth-sales-plays"] == VerificationCategory.SYNTHESIS_CLAIMS

    def test_hiring_maps_to_hiring(self) -> None:
        assert MODULE_CATEGORY_MAP["intel-hiring"] == VerificationCategory.HIRING_CLAIMS

    def test_investor_maps_to_quotes(self) -> None:
        assert MODULE_CATEGORY_MAP["intel-investor"] == VerificationCategory.QUOTE_CLAIMS

    def test_social_maps_to_quotes(self) -> None:
        assert MODULE_CATEGORY_MAP["intel-social"] == VerificationCategory.QUOTE_CLAIMS

    def test_news_maps_to_quotes(self) -> None:
        assert MODULE_CATEGORY_MAP["intel-news"] == VerificationCategory.QUOTE_CLAIMS


# ---------------------------------------------------------------------------
# FactcheckCollector tests (mocking DB)
# ---------------------------------------------------------------------------
class TestFactcheckCollector:
    @pytest.mark.asyncio
    async def test_collect_all_with_empty_db(self) -> None:
        """Should return empty claims when no module_executions exist."""
        collector = FactcheckCollector()

        with patch.object(
            collector, "_read_all_module_outputs", new_callable=AsyncMock
        ) as mock_read:
            mock_read.return_value = {}
            claims, sources = await collector.collect_all("audit-123", "dell.com")

            assert sum(len(v) for v in claims.values()) == 0
            assert len(sources) == 0

    @pytest.mark.asyncio
    async def test_collect_all_with_company_data(self) -> None:
        """Should extract claims from intel-company output."""
        collector = FactcheckCollector()

        with patch.object(
            collector, "_read_all_module_outputs", new_callable=AsyncMock
        ) as mock_read:
            mock_read.return_value = {"intel-company": SAMPLE_COMPANY_OUTPUT}
            claims, sources = await collector.collect_all("audit-123", "dell.com")

            assert len(claims[VerificationCategory.COMPANY_FACTS]) > 0
            assert len(sources) == 1

    @pytest.mark.asyncio
    async def test_collect_all_with_none_output(self) -> None:
        """Should skip modules with None output_json."""
        collector = FactcheckCollector()

        with patch.object(
            collector, "_read_all_module_outputs", new_callable=AsyncMock
        ) as mock_read:
            mock_read.return_value = {"intel-company": None}
            claims, sources = await collector.collect_all("audit-123", "dell.com")

            assert sum(len(v) for v in claims.values()) == 0
            assert len(sources) == 0

    @pytest.mark.asyncio
    async def test_collect_all_with_unknown_module(self) -> None:
        """Should skip modules not in the category map."""
        collector = FactcheckCollector()

        with patch.object(
            collector, "_read_all_module_outputs", new_callable=AsyncMock
        ) as mock_read:
            mock_read.return_value = {
                "unknown-module": {"some": "data that should be ignored by the collector"},
            }
            claims, _sources = await collector.collect_all("audit-123", "dell.com")

            assert sum(len(v) for v in claims.values()) == 0

    @pytest.mark.asyncio
    async def test_collect_all_multiple_modules(self) -> None:
        """Should extract claims from multiple upstream modules."""
        collector = FactcheckCollector()

        with patch.object(
            collector, "_read_all_module_outputs", new_callable=AsyncMock
        ) as mock_read:
            mock_read.return_value = {
                "intel-company": SAMPLE_COMPANY_OUTPUT,
                "intel-financial-public": SAMPLE_FINANCIAL_PUBLIC_OUTPUT,
                "intel-techstack": SAMPLE_TECHSTACK_OUTPUT,
            }
            claims, sources = await collector.collect_all("audit-123", "dell.com")

            total = sum(len(v) for v in claims.values())
            assert total > 0
            assert len(claims[VerificationCategory.COMPANY_FACTS]) > 0
            assert len(claims[VerificationCategory.FINANCIAL_CLAIMS]) > 0
            assert len(claims[VerificationCategory.TECHNOLOGY_CLAIMS]) > 0
            assert len(sources) == 3

    @pytest.mark.asyncio
    async def test_collect_all_db_error_returns_empty(self) -> None:
        """Should return empty claims when DB read fails."""
        collector = FactcheckCollector()

        with patch.object(
            collector, "_read_all_module_outputs", new_callable=AsyncMock
        ) as mock_read:
            mock_read.side_effect = Exception("DB connection failed")
            claims, sources = await collector.collect_all("audit-123", "dell.com")

            assert sum(len(v) for v in claims.values()) == 0
            assert len(sources) == 0
