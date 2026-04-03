"""Collector and validator tests for synth-sales-plays -- no DB or API calls.

Tests the extract_* functions and validate_output with synthetic data.
"""

from __future__ import annotations

from prism_platform.core.types import EvidenceTier, Source
from prism_platform.modules.synth_sales_plays.collector import (
    extract_business_case_context,
    extract_buying_committee,
    extract_company_context,
    extract_competitive_context,
    extract_exec_quotes,
    extract_financial_context,
)
from prism_platform.modules.synth_sales_plays.schemas import (
    MEDDPICCField,
    ObjectionHandler,
    PowerMapMember,
    SalesPlaysOutput,
    SPINQuestion,
    TalkTrack,
)
from prism_platform.modules.synth_sales_plays.validator import validate_output


# ---------------------------------------------------------------------------
# extract_buying_committee
# ---------------------------------------------------------------------------
class TestExtractBuyingCommittee:
    def test_returns_empty_for_none(self) -> None:
        assert extract_buying_committee(None) == []

    def test_returns_empty_for_empty_dict(self) -> None:
        assert extract_buying_committee({}) == []

    def test_extracts_from_buying_committee(self) -> None:
        hiring_output = {
            "buying_committee": [
                {"name": "Jane Doe", "title": "VP Eng", "tier": "Economic Buyer"},
                {"name": "Bob Smith", "title": "Dir Search", "tier": "Champion"},
            ]
        }
        members = extract_buying_committee(hiring_output)
        assert len(members) == 2
        assert members[0]["name"] == "Jane Doe"
        assert members[1]["tier"] == "Champion"

    def test_extracts_from_key_contacts(self) -> None:
        hiring_output = {
            "key_contacts": [
                {"name": "Alice", "title": "CTO", "tier": "Technical Buyer"},
            ]
        }
        members = extract_buying_committee(hiring_output)
        assert len(members) == 1
        assert members[0]["name"] == "Alice"

    def test_deduplicates_across_sources(self) -> None:
        hiring_output = {
            "buying_committee": [
                {"name": "Jane Doe", "title": "VP Eng", "tier": "Economic Buyer"},
            ],
            "key_contacts": [
                {"name": "Jane Doe", "title": "VP Eng", "tier": "Economic Buyer"},
                {"name": "Bob", "title": "Manager", "tier": "Influencer"},
            ],
        }
        members = extract_buying_committee(hiring_output)
        assert len(members) == 2  # Jane Doe not duplicated

    def test_handles_malformed_data(self) -> None:
        hiring_output = {
            "buying_committee": "not a list",
        }
        members = extract_buying_committee(hiring_output)
        assert members == []

    def test_includes_linkedin_url(self) -> None:
        hiring_output = {
            "buying_committee": [
                {
                    "name": "Jane",
                    "title": "VP",
                    "tier": "EB",
                    "linkedin_url": "https://linkedin.com/in/jane",
                },
            ]
        }
        members = extract_buying_committee(hiring_output)
        assert members[0]["linkedin_url"] == "https://linkedin.com/in/jane"


# ---------------------------------------------------------------------------
# extract_exec_quotes
# ---------------------------------------------------------------------------
class TestExtractExecQuotes:
    def test_returns_empty_for_none(self) -> None:
        assert extract_exec_quotes(None, None) == []

    def test_extracts_from_investor_quotes(self) -> None:
        investor = {
            "executive_quotes": [
                {"quote": "Search is our priority", "speaker": "CEO"},
            ]
        }
        quotes = extract_exec_quotes(investor, None)
        assert len(quotes) == 1
        assert quotes[0]["quote"] == "Search is our priority"
        assert quotes[0]["speaker"] == "CEO"

    def test_extracts_from_key_quotes(self) -> None:
        investor = {
            "key_quotes": ["Digital is the future"],
        }
        quotes = extract_exec_quotes(investor, None)
        assert len(quotes) == 1
        assert quotes[0]["quote"] == "Digital is the future"

    def test_extracts_from_social(self) -> None:
        social = {
            "key_quotes": ["Excited about our new search experience"],
        }
        quotes = extract_exec_quotes(None, social)
        assert len(quotes) == 1
        assert quotes[0]["source"] == "social_signals"

    def test_deduplicates_quotes(self) -> None:
        investor = {
            "executive_quotes": [
                {"quote": "Search matters", "speaker": "CEO"},
            ],
            "key_quotes": ["Search matters"],
        }
        quotes = extract_exec_quotes(investor, None)
        assert len(quotes) == 1

    def test_handles_string_quotes_in_executive_quotes(self) -> None:
        investor = {
            "executive_quotes": ["A plain string quote"],
        }
        quotes = extract_exec_quotes(investor, None)
        assert len(quotes) == 1
        assert quotes[0]["quote"] == "A plain string quote"


# ---------------------------------------------------------------------------
# extract_competitive_context
# ---------------------------------------------------------------------------
class TestExtractCompetitiveContext:
    def test_returns_defaults_for_none(self) -> None:
        ctx = extract_competitive_context(None, None)
        assert ctx["current_vendor"] is None
        assert ctx["golden_angle_competitors"] == []

    def test_extracts_current_vendor_dict(self) -> None:
        techstack = {"search_vendor": {"name": "Elasticsearch"}}
        ctx = extract_competitive_context(None, techstack)
        assert ctx["current_vendor"] == "Elasticsearch"

    def test_extracts_current_vendor_string(self) -> None:
        techstack = {"search_vendor": "Coveo"}
        ctx = extract_competitive_context(None, techstack)
        assert ctx["current_vendor"] == "Coveo"

    def test_extracts_from_competitors(self) -> None:
        competitors = {
            "golden_angle_competitors": ["Amazon", "Walmart"],
            "tech_gaps": ["No AI search"],
            "competitive_summary": "Lagging behind peers",
        }
        ctx = extract_competitive_context(competitors, None)
        assert ctx["golden_angle_competitors"] == ["Amazon", "Walmart"]
        assert ctx["tech_gaps"] == ["No AI search"]
        assert ctx["competitive_summary"] == "Lagging behind peers"


# ---------------------------------------------------------------------------
# extract_financial_context
# ---------------------------------------------------------------------------
class TestExtractFinancialContext:
    def test_returns_defaults_for_none(self) -> None:
        ctx = extract_financial_context(None, None)
        assert ctx["revenue"] is None

    def test_extracts_from_public(self) -> None:
        public = {
            "revenue": 5000000000,
            "revenue_growth_pct": 12.5,
            "digital_revenue_pct": 35.0,
            "market_cap": 80000000000,
        }
        ctx = extract_financial_context(public, None)
        assert ctx["revenue"] == 5000000000.0
        assert ctx["revenue_growth_pct"] == 12.5
        assert ctx["digital_revenue_pct"] == 35.0
        assert ctx["market_cap"] == 80000000000.0

    def test_extracts_alternate_field_names(self) -> None:
        public = {"annual_revenue": 1000000, "ecommerce_revenue_pct": 20.0}
        ctx = extract_financial_context(public, None)
        assert ctx["revenue"] == 1000000.0
        assert ctx["digital_revenue_pct"] == 20.0

    def test_fallback_to_private(self) -> None:
        private = {"revenue": 500000}
        ctx = extract_financial_context(None, private)
        assert ctx["revenue"] == 500000.0

    def test_handles_string_values(self) -> None:
        public = {"revenue": "not a number"}
        ctx = extract_financial_context(public, None)
        assert ctx["revenue"] is None


# ---------------------------------------------------------------------------
# extract_company_context
# ---------------------------------------------------------------------------
class TestExtractCompanyContext:
    def test_returns_defaults_for_none(self) -> None:
        ctx = extract_company_context(None)
        assert ctx["company_name"] == ""

    def test_extracts_company_data(self) -> None:
        company = {
            "company_name": "Dell Technologies",
            "vertical": "Technology",
            "description": "Global tech company",
            "employee_count": 130000,
        }
        ctx = extract_company_context(company)
        assert ctx["company_name"] == "Dell Technologies"
        assert ctx["vertical"] == "Technology"
        assert ctx["employee_count"] == 130000


# ---------------------------------------------------------------------------
# extract_business_case_context
# ---------------------------------------------------------------------------
class TestExtractBusinessCaseContext:
    def test_returns_defaults_for_none(self) -> None:
        ctx = extract_business_case_context(None)
        assert ctx["total_roi_usd"] is None

    def test_extracts_roi_data(self) -> None:
        bc = {
            "total_roi_usd": 2500000.0,
            "roi_summary": "Strong ROI driven by conversion improvements",
            "value_drivers": ["Search relevance", "Personalization"],
        }
        ctx = extract_business_case_context(bc)
        assert ctx["total_roi_usd"] == 2500000.0
        assert ctx["roi_summary"] == "Strong ROI driven by conversion improvements"
        assert len(ctx["value_drivers"]) == 2


# ---------------------------------------------------------------------------
# validate_output
# ---------------------------------------------------------------------------
def _make_valid_output() -> SalesPlaysOutput:
    """Build a fully valid SalesPlaysOutput for testing."""
    meddpicc_fields = [
        MEDDPICCField(
            field_name=name,  # type: ignore[arg-type]
            evidence=f"Evidence for {name}",
            recommended_approach=f"Approach for {name}",
        )
        for name in [
            "metrics",
            "economic_buyer",
            "decision_criteria",
            "identified_pain",
            "champion",
        ]
    ]

    spin_questions = []
    for cat in ["situation", "problem", "implication", "need_payoff"]:
        for i in range(2):
            spin_questions.append(
                SPINQuestion(
                    category=cat,  # type: ignore[arg-type]
                    question=f"Question {i + 1} for {cat}",
                    context=f"Context for {cat} {i + 1}",
                )
            )

    objection_handlers = [
        ObjectionHandler(objection="Building in-house", counter="Your hiring data shows..."),
        ObjectionHandler(objection="Happy with current", counter="Competitor benchmark shows..."),
    ]

    talk_tracks = [
        TalkTrack(line_type="opener", text="I noticed your CEO said..."),
        TalkTrack(line_type="bridge", text="That connects to what Algolia does..."),
        TalkTrack(line_type="close", text="Let's schedule a technical deep-dive..."),
    ]

    power_map = [
        PowerMapMember(name="Jane Doe", title="VP Engineering", meddpicc_role="economic_buyer"),
    ]

    return SalesPlaysOutput(
        domain="dell.com",
        meddpicc=meddpicc_fields,
        spin_questions=spin_questions,
        objection_handlers=objection_handlers,
        talk_tracks=talk_tracks,
        power_map=power_map,
        playbook_summary="Strong opportunity driven by digital transformation initiative.",
        top_3_actions=[
            "Book meeting with VP Eng Jane Doe",
            "Send ROI analysis showing $2.5M impact",
            "Reference Amazon case study for social proof",
        ],
    )


def _make_source() -> Source:
    return Source(
        field="upstream.intel-company",
        value="Read from module_executions",
        tier=EvidenceTier.VERIFIED,
        source_label="intel-company module output",
        method="db_read",
    )


class TestValidateOutput:
    def test_valid_output_passes(self) -> None:
        output = _make_valid_output()
        result = validate_output(output, [_make_source()])
        assert result.passed is True
        assert result.checks_run == 10
        assert result.checks_passed == 10
        assert result.errors == []

    def test_empty_domain_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"domain": ""})
        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert "domain is empty" in result.errors

    def test_insufficient_meddpicc_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"meddpicc": output.meddpicc[:3]})
        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("meddpicc" in e for e in result.errors)

    def test_insufficient_spin_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"spin_questions": output.spin_questions[:5]})
        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("spin_questions" in e for e in result.errors)

    def test_missing_spin_category_fails(self) -> None:
        output = _make_valid_output()
        # Remove all need_payoff questions
        filtered = [q for q in output.spin_questions if q.category != "need_payoff"]
        # Ensure we still have 8+ but missing a category
        while len(filtered) < 8:
            filtered.append(
                SPINQuestion(
                    category="situation",
                    question="Extra question",
                    context="Extra context",
                )
            )
        output = output.model_copy(update={"spin_questions": filtered})
        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("SPIN categories missing" in e for e in result.errors)

    def test_insufficient_objections_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"objection_handlers": output.objection_handlers[:1]})
        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("objection_handlers" in e for e in result.errors)

    def test_insufficient_talk_tracks_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"talk_tracks": output.talk_tracks[:2]})
        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("talk_tracks" in e for e in result.errors)

    def test_empty_power_map_warns(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"power_map": []})
        result = validate_output(output, [_make_source()])
        # Power map empty is a WARNING not error
        assert any("power_map" in w for w in result.warnings)

    def test_empty_summary_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"playbook_summary": ""})
        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("playbook_summary" in e for e in result.errors)

    def test_wrong_action_count_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"top_3_actions": ["one", "two"]})
        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("top_3_actions" in e for e in result.errors)

    def test_no_sources_fails(self) -> None:
        output = _make_valid_output()
        result = validate_output(output, [])
        assert result.passed is False
        assert any("sources" in e.lower() or "provenance" in e.lower() for e in result.errors)

    def test_exactly_5_meddpicc_passes(self) -> None:
        output = _make_valid_output()
        assert len(output.meddpicc) == 5  # Exactly 5
        result = validate_output(output, [_make_source()])
        assert result.passed is True

    def test_exactly_8_spin_passes(self) -> None:
        output = _make_valid_output()
        assert len(output.spin_questions) == 8  # Exactly 8
        result = validate_output(output, [_make_source()])
        assert result.passed is True

    def test_exactly_3_actions_passes(self) -> None:
        output = _make_valid_output()
        assert len(output.top_3_actions) == 3
        result = validate_output(output, [_make_source()])
        assert result.passed is True

    def test_four_actions_fails(self) -> None:
        output = _make_valid_output()
        output = output.model_copy(update={"top_3_actions": ["a", "b", "c", "d"]})
        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("top_3_actions" in e for e in result.errors)
