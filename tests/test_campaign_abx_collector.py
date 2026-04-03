"""Tests for campaign-abx collector -- extraction functions (no DB/API calls).

These tests verify the pure extraction functions that transform raw module outputs
into structured data for the enricher. No database or API calls needed.
"""

from __future__ import annotations

from prism_platform.modules.campaign_abx.collector import (
    extract_business_case_data,
    extract_buying_committee,
    extract_competitor_context,
    extract_executive_quotes,
    extract_sales_plays_data,
)

# ---------------------------------------------------------------------------
# Fixtures: synthetic upstream module outputs
# ---------------------------------------------------------------------------
COMPANY_OUTPUT = {
    "domain": "dell.com",
    "legal_name": "Dell Technologies Inc",
    "common_name": "Dell",
    "executives": [
        {
            "full_name": "Michael Dell",
            "title": "CEO",
            "relevance": "economic_buyer",
            "linkedin_url": "https://linkedin.com/in/michaeldell",
        },
        {
            "full_name": "John Roese",
            "title": "CTO",
            "relevance": "technical_evaluator",
            "linkedin_url": "https://linkedin.com/in/johnroese",
        },
        {
            "full_name": "Jen Felch",
            "title": "CDO",
            "relevance": "champion_candidate",
            "linkedin_url": "",
        },
        {
            "full_name": "Tom Sweet",
            "title": "CFO",
            "relevance": "influencer",
            "linkedin_url": "",
        },
    ],
}

HIRING_OUTPUT = {
    "domain": "dell.com",
    "total_open_roles": 150,
    "buying_committee": [
        {
            "name": "Sarah Johnson",
            "title": "VP of Search Experience",
            "tier": "champion_candidate",
            "linkedin_url": "https://linkedin.com/in/sarahjohnson",
        },
        {
            "name": "Michael Dell",  # Duplicate -- should be deduplicated
            "title": "CEO",
            "tier": "economic_buyer",
            "linkedin_url": "",
        },
    ],
}

INVESTOR_OUTPUT = {
    "executive_quotes": [
        {
            "quote": "We are investing heavily in our digital transformation",
            "speaker": "Michael Dell, CEO",
            "source": "Q4 2024 Earnings Call",
        },
        {
            "quote": "Search and discovery is critical to our e-commerce growth",
            "speaker": "Jen Felch, CDO",
            "source": "Q3 2024 Earnings Call",
        },
    ],
    "key_quotes": [
        "AI-powered experiences are the future of customer engagement",
    ],
}

SOCIAL_OUTPUT = {
    "key_quotes": [
        "Excited about our new AI capabilities launching next quarter",
    ],
}

COMPETITORS_OUTPUT = {
    "competitive_position": "fast_follower",
    "competitive_summary": "Dell trails HP in search technology adoption.",
    "top_competitive_angles": [
        "HP uses Algolia with 37% conversion lift",
        "Lenovo deployed AI search in Q3 2024",
    ],
    "golden_angle_competitors": ["HP"],
}

TECHSTACK_OUTPUT = {
    "search_vendor": {"name": "Elasticsearch", "status": "ACTIVE"},
    "ecommerce_platform": "Salesforce Commerce Cloud",
}

BUSINESS_CASE_OUTPUT = {
    "total_conservative_impact": 1500000.0,
    "total_moderate_impact": 3200000.0,
    "one_line_pitch": (
        "Dell can unlock $1.5-3.2M annual revenue by replacing Elasticsearch with Algolia."
    ),
    "said_vs_found": [
        {
            "exec_said": "Michael Dell: We are investing heavily in digital transformation",
            "we_found": "Site search returns 0 results for 15% of queries",
            "competitors_doing": "HP uses Algolia with 37% conversion lift",
            "your_move": "Algolia NeuralSearch eliminates zero-result queries",
            "category": "search_quality",
        },
    ],
    "customer_proofs": [
        {
            "customer_name": "Shoe Carnival",
            "industry": "Retail",
            "key_metric": "3.5x conversion lift",
            "matched_lever": "Search Conversion Uplift",
        },
    ],
    "value_levers": [
        {
            "lever_name": "Search Conversion Uplift",
            "conservative_estimate": 1000000.0,
            "moderate_estimate": 2000000.0,
        },
    ],
}

SALES_PLAYS_OUTPUT = {
    "meddpicc": {
        "metrics": "Search conversion rate, zero-result rate, time-to-result",
        "economic_buyer": "Michael Dell, CEO",
        "decision_criteria": "Performance, ease of integration, total cost of ownership",
    },
    "objection_handlers": [
        {
            "objection": "We already have Elasticsearch",
            "response": "Elasticsearch requires dedicated engineering to maintain...",
        },
    ],
    "pre_call_talking_points": [
        "Dell's CDO mentioned search is critical to e-commerce growth",
    ],
}


# ---------------------------------------------------------------------------
# extract_buying_committee
# ---------------------------------------------------------------------------
class TestExtractBuyingCommittee:
    def test_combines_company_and_hiring(self) -> None:
        committee = extract_buying_committee(COMPANY_OUTPUT, HIRING_OUTPUT)
        names = [m["name"] for m in committee]
        # Should have Michael Dell, John Roese, Jen Felch from company + Sarah Johnson from hiring
        assert "Michael Dell" in names
        assert "John Roese" in names
        assert "Jen Felch" in names
        assert "Sarah Johnson" in names

    def test_deduplicates_by_name(self) -> None:
        committee = extract_buying_committee(COMPANY_OUTPUT, HIRING_OUTPUT)
        names = [m["name"] for m in committee]
        # Michael Dell appears in both -- should only appear once
        assert names.count("Michael Dell") == 1

    def test_filters_by_relevance(self) -> None:
        committee = extract_buying_committee(COMPANY_OUTPUT, HIRING_OUTPUT)
        # Tom Sweet is "influencer" -- should NOT be in the buying committee
        names = [m["name"] for m in committee]
        assert "Tom Sweet" not in names

    def test_company_only(self) -> None:
        committee = extract_buying_committee(COMPANY_OUTPUT, None)
        assert len(committee) == 3  # economic_buyer, technical_evaluator, champion_candidate

    def test_hiring_only(self) -> None:
        committee = extract_buying_committee(None, HIRING_OUTPUT)
        assert len(committee) == 2  # Sarah Johnson + Michael Dell from hiring

    def test_both_none(self) -> None:
        committee = extract_buying_committee(None, None)
        assert committee == []

    def test_empty_executives(self) -> None:
        committee = extract_buying_committee({"executives": []}, None)
        assert committee == []

    def test_malformed_exec_data(self) -> None:
        """Non-dict entries should be skipped without error."""
        committee = extract_buying_committee({"executives": ["not a dict", 42, None]}, None)
        assert committee == []


# ---------------------------------------------------------------------------
# extract_executive_quotes
# ---------------------------------------------------------------------------
class TestExtractExecutiveQuotes:
    def test_combines_investor_and_social(self) -> None:
        quotes = extract_executive_quotes(INVESTOR_OUTPUT, SOCIAL_OUTPUT)
        texts = [q["quote"] for q in quotes]
        assert any("digital transformation" in t for t in texts)
        assert any("AI capabilities" in t for t in texts)

    def test_investor_only(self) -> None:
        quotes = extract_executive_quotes(INVESTOR_OUTPUT, None)
        assert len(quotes) >= 2

    def test_social_only(self) -> None:
        quotes = extract_executive_quotes(None, SOCIAL_OUTPUT)
        assert len(quotes) == 1

    def test_both_none(self) -> None:
        quotes = extract_executive_quotes(None, None)
        assert quotes == []

    def test_deduplicates_quotes(self) -> None:
        """Same quote in key_quotes and executive_quotes should not duplicate."""
        investor = {
            "executive_quotes": [{"quote": "Same quote", "speaker": "CEO", "source": "call"}],
            "key_quotes": ["Same quote"],
        }
        quotes = extract_executive_quotes(investor, None)
        texts = [q["quote"] for q in quotes]
        assert texts.count("Same quote") == 1

    def test_handles_string_exec_quotes(self) -> None:
        """executive_quotes can contain plain strings."""
        investor = {"executive_quotes": ["Plain string quote"]}
        quotes = extract_executive_quotes(investor, None)
        assert len(quotes) == 1
        assert quotes[0]["quote"] == "Plain string quote"


# ---------------------------------------------------------------------------
# extract_competitor_context
# ---------------------------------------------------------------------------
class TestExtractCompetitorContext:
    def test_full_extraction(self) -> None:
        ctx = extract_competitor_context(COMPETITORS_OUTPUT, TECHSTACK_OUTPUT)
        assert ctx["current_vendor"] == "Elasticsearch"
        assert ctx["competitive_position"] == "fast_follower"
        assert len(ctx["top_angles"]) == 2
        assert "HP" in ctx["golden_angle_competitors"]

    def test_techstack_only(self) -> None:
        ctx = extract_competitor_context(None, TECHSTACK_OUTPUT)
        assert ctx["current_vendor"] == "Elasticsearch"
        assert ctx["competitive_position"] == "unknown"

    def test_competitors_only(self) -> None:
        ctx = extract_competitor_context(COMPETITORS_OUTPUT, None)
        assert ctx["current_vendor"] == "None/Custom"  # No techstack to detect vendor
        assert ctx["competitive_position"] == "fast_follower"

    def test_both_none(self) -> None:
        ctx = extract_competitor_context(None, None)
        assert ctx["current_vendor"] == "None/Custom"
        assert ctx["competitive_position"] == "unknown"

    def test_no_search_vendor(self) -> None:
        ctx = extract_competitor_context(None, {"search_vendor": None})
        assert ctx["current_vendor"] == "None/Custom"

    def test_empty_vendor_name(self) -> None:
        ctx = extract_competitor_context(None, {"search_vendor": {"name": ""}})
        assert ctx["current_vendor"] == "None/Custom"


# ---------------------------------------------------------------------------
# extract_business_case_data
# ---------------------------------------------------------------------------
class TestExtractBusinessCaseData:
    def test_full_extraction(self) -> None:
        data = extract_business_case_data(BUSINESS_CASE_OUTPUT)
        assert data["total_conservative_impact"] == 1500000.0
        assert data["total_moderate_impact"] == 3200000.0
        assert "Dell" in data["one_line_pitch"]
        assert len(data["said_vs_found"]) == 1
        assert len(data["customer_proofs"]) == 1

    def test_none_input(self) -> None:
        data = extract_business_case_data(None)
        assert data["total_conservative_impact"] is None
        assert data["total_moderate_impact"] is None
        assert data["one_line_pitch"] == ""
        assert data["said_vs_found"] == []
        assert data["customer_proofs"] == []

    def test_empty_output(self) -> None:
        data = extract_business_case_data({})
        assert data["total_conservative_impact"] is None


# ---------------------------------------------------------------------------
# extract_sales_plays_data
# ---------------------------------------------------------------------------
class TestExtractSalesPlaysData:
    def test_full_extraction(self) -> None:
        data = extract_sales_plays_data(SALES_PLAYS_OUTPUT)
        assert "metrics" in data["meddpicc"]
        assert len(data["objection_handlers"]) == 1
        assert len(data["pre_call_talking_points"]) == 1

    def test_none_input(self) -> None:
        data = extract_sales_plays_data(None)
        assert data["meddpicc"] == {}
        assert data["objection_handlers"] == []
        assert data["pre_call_talking_points"] == []

    def test_empty_output(self) -> None:
        data = extract_sales_plays_data({})
        assert data["meddpicc"] == {}
