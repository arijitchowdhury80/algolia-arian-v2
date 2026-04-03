"""Integration tests for campaign-abx enricher -- real Gemini API calls.

These tests call the actual Gemini API via Instructor to verify structured output
generation works end-to-end. They use synthetic upstream data (not real DB reads).

Requires: GEMINI_API_KEY environment variable set.
"""

from __future__ import annotations

import os

import pytest

from prism_platform.core.types import EvidenceTier, Source
from prism_platform.modules.campaign_abx.enricher import (
    CampaignEnricher,
    CampaignSummaryOutput,
    CompetitorMessagingOutput,
    EmailSequenceOutput,
    LinkedInMessagesOutput,
    LoomScriptOutput,
    ScheduleOutput,
)
from prism_platform.modules.campaign_abx.schemas import CampaignOutput
from prism_platform.modules.campaign_abx.validator import validate_output

# Skip all tests if no Gemini API key
pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set -- skipping Gemini integration tests",
)

# ---------------------------------------------------------------------------
# Synthetic data matching what collector extractors would produce
# ---------------------------------------------------------------------------
BUYING_COMMITTEE = [
    {"name": "Michael Dell", "title": "CEO", "relevance": "economic_buyer", "linkedin_url": ""},
    {"name": "John Roese", "title": "CTO", "relevance": "technical_evaluator", "linkedin_url": ""},
    {"name": "Jen Felch", "title": "CDO", "relevance": "champion_candidate", "linkedin_url": ""},
]

EXECUTIVE_QUOTES = [
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
]

COMPETITOR_CONTEXT = {
    "current_vendor": "Elasticsearch",
    "competitive_position": "fast_follower",
    "competitive_summary": "Dell trails HP in search technology adoption.",
    "top_angles": ["HP uses Algolia with 37% conversion lift"],
    "golden_angle_competitors": ["HP"],
}

BUSINESS_CASE_DATA = {
    "total_conservative_impact": 1500000.0,
    "total_moderate_impact": 3200000.0,
    "one_line_pitch": "Dell can unlock $1.5-3.2M annual revenue by replacing Elasticsearch.",
    "said_vs_found": [
        {
            "exec_said": "Michael Dell: We are investing heavily in digital transformation",
            "we_found": "Site search returns 0 results for 15% of queries",
            "competitors_doing": "HP uses Algolia with 37% conversion lift",
            "your_move": "Algolia NeuralSearch eliminates zero-result queries",
        },
    ],
    "customer_proofs": [
        {
            "customer_name": "Shoe Carnival",
            "industry": "Retail",
            "key_metric": "3.5x conversion lift",
        },
    ],
    "value_levers": [],
}

SALES_PLAYS_DATA = {
    "meddpicc": {
        "metrics": "Search conversion rate, zero-result rate",
        "economic_buyer": "Michael Dell, CEO",
    },
    "objection_handlers": [
        {
            "objection": "We already have Elasticsearch",
            "response": "Elasticsearch requires dedicated engineering to maintain.",
        },
    ],
    "pre_call_talking_points": [],
}


# ---------------------------------------------------------------------------
# Individual component tests
# ---------------------------------------------------------------------------
class TestEmailSequenceGeneration:
    """Test that Gemini can generate a valid 5-email sequence."""

    def test_generates_5_emails(self) -> None:
        enricher = CampaignEnricher()
        context_block = enricher._build_context_block(
            domain="dell.com",
            company_name="Dell Technologies",
            buying_committee=BUYING_COMMITTEE,
            executive_quotes=EXECUTIVE_QUOTES,
            competitor_context=COMPETITOR_CONTEXT,
            business_case_data=BUSINESS_CASE_DATA,
            sales_plays_data=SALES_PLAYS_DATA,
        )
        prompt = enricher._build_email_prompt(context_block, "dell.com", "Dell Technologies")
        result = enricher._call_gemini(prompt, EmailSequenceOutput)

        assert len(result.emails) == 5
        purposes = [e.purpose for e in result.emails]
        assert purposes == ["hook", "insight", "proof", "roi", "ask"]
        for email in result.emails:
            assert email.subject_line.strip() != ""
            assert email.body.strip() != ""


class TestLinkedInMessageGeneration:
    """Test that Gemini can generate valid LinkedIn messages."""

    def test_generates_linkedin_messages(self) -> None:
        enricher = CampaignEnricher()
        context_block = enricher._build_context_block(
            domain="dell.com",
            company_name="Dell Technologies",
            buying_committee=BUYING_COMMITTEE,
            executive_quotes=EXECUTIVE_QUOTES,
            competitor_context=COMPETITOR_CONTEXT,
            business_case_data=BUSINESS_CASE_DATA,
            sales_plays_data=SALES_PLAYS_DATA,
        )
        prompt = enricher._build_linkedin_prompt(
            context_block, "dell.com", "Dell Technologies", BUYING_COMMITTEE
        )
        result = enricher._call_gemini(prompt, LinkedInMessagesOutput)

        assert len(result.messages) >= 2
        for msg in result.messages:
            assert msg.target_name.strip() != ""
            assert msg.message.strip() != ""


class TestLoomScriptGeneration:
    """Test that Gemini can generate a valid Loom script."""

    def test_generates_loom_script(self) -> None:
        enricher = CampaignEnricher()
        context_block = enricher._build_context_block(
            domain="dell.com",
            company_name="Dell Technologies",
            buying_committee=BUYING_COMMITTEE,
            executive_quotes=EXECUTIVE_QUOTES,
            competitor_context=COMPETITOR_CONTEXT,
            business_case_data=BUSINESS_CASE_DATA,
            sales_plays_data=SALES_PLAYS_DATA,
        )
        prompt = enricher._build_loom_prompt(context_block, "dell.com", "Dell Technologies")
        result = enricher._call_gemini(prompt, LoomScriptOutput)

        assert result.script.opening.strip() != ""
        assert result.script.screen_1.strip() != ""
        assert result.script.screen_2.strip() != ""
        assert result.script.screen_3.strip() != ""
        assert result.script.closing.strip() != ""
        assert result.script.call_to_action.strip() != ""


class TestScheduleGeneration:
    """Test that Gemini can generate a valid collateral schedule."""

    def test_generates_schedule(self) -> None:
        enricher = CampaignEnricher()
        context_block = enricher._build_context_block(
            domain="dell.com",
            company_name="Dell Technologies",
            buying_committee=BUYING_COMMITTEE,
            executive_quotes=EXECUTIVE_QUOTES,
            competitor_context=COMPETITOR_CONTEXT,
            business_case_data=BUSINESS_CASE_DATA,
            sales_plays_data=SALES_PLAYS_DATA,
        )
        prompt = enricher._build_schedule_prompt(
            context_block, "dell.com", "Dell Technologies", BUYING_COMMITTEE
        )
        result = enricher._call_gemini(prompt, ScheduleOutput)

        assert len(result.schedule) >= 3


class TestCompetitorMessagingGeneration:
    """Test that Gemini can generate valid competitor messaging."""

    def test_generates_competitor_messaging(self) -> None:
        enricher = CampaignEnricher()
        context_block = enricher._build_context_block(
            domain="dell.com",
            company_name="Dell Technologies",
            buying_committee=BUYING_COMMITTEE,
            executive_quotes=EXECUTIVE_QUOTES,
            competitor_context=COMPETITOR_CONTEXT,
            business_case_data=BUSINESS_CASE_DATA,
            sales_plays_data=SALES_PLAYS_DATA,
        )
        prompt = enricher._build_competitor_messaging_prompt(
            context_block, "dell.com", "Dell Technologies", COMPETITOR_CONTEXT
        )
        result = enricher._call_gemini(prompt, CompetitorMessagingOutput)

        assert result.messaging.current_vendor.strip() != ""
        assert result.messaging.messaging_angle.strip() != ""


class TestCampaignSummaryGeneration:
    """Test that Gemini can generate a valid campaign summary."""

    def test_generates_summary(self) -> None:
        enricher = CampaignEnricher()
        context_block = enricher._build_context_block(
            domain="dell.com",
            company_name="Dell Technologies",
            buying_committee=BUYING_COMMITTEE,
            executive_quotes=EXECUTIVE_QUOTES,
            competitor_context=COMPETITOR_CONTEXT,
            business_case_data=BUSINESS_CASE_DATA,
            sales_plays_data=SALES_PLAYS_DATA,
        )
        prompt = enricher._build_summary_prompt(
            context_block, "dell.com", "Dell Technologies", BUYING_COMMITTEE
        )
        result = enricher._call_gemini(prompt, CampaignSummaryOutput)

        assert result.campaign_summary.strip() != ""
        assert len(result.target_contacts) >= 1


# ---------------------------------------------------------------------------
# Full pipeline integration test
# ---------------------------------------------------------------------------
class TestFullCampaignGeneration:
    """Test the full generate_campaign pipeline with Gemini."""

    @pytest.mark.asyncio
    async def test_full_campaign_pipeline(self) -> None:
        enricher = CampaignEnricher()
        output, llm_calls, llm_cost = await enricher.generate_campaign(
            domain="dell.com",
            company_name="Dell Technologies",
            buying_committee=BUYING_COMMITTEE,
            executive_quotes=EXECUTIVE_QUOTES,
            competitor_context=COMPETITOR_CONTEXT,
            business_case_data=BUSINESS_CASE_DATA,
            sales_plays_data=SALES_PLAYS_DATA,
            raw_data={},
        )

        # Verify output structure
        assert isinstance(output, CampaignOutput)
        assert output.domain == "dell.com"
        assert len(output.emails) == 5
        assert len(output.linkedin_messages) >= 2
        assert output.loom_script is not None
        assert len(output.schedule) >= 3
        assert output.competitor_messaging is not None
        assert output.campaign_summary.strip() != ""

        # Verify LLM tracking
        assert llm_calls == 6
        assert llm_cost > 0

        # Run validator
        sources = [
            Source(
                field="upstream.intel-company",
                value="Read from module_executions for dell.com",
                tier=EvidenceTier.VERIFIED,
                source_label="intel-company module output",
                method="db_read",
            ),
        ]
        validation = validate_output(output, sources)
        assert validation.passed is True, f"Validation failed: {validation.errors}"
        assert validation.checks_run == 10
        assert validation.checks_passed == 10
