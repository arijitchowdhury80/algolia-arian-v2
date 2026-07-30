"""Tests for Task 5c's mechanical claim extraction (`claims.extract_claims`).

Fixtures mirror the REAL field shapes confirmed by reading real audit
workspaces (`~/prism-data/audits/{Dell,jbl,lululemon}/`,
`~/Dropbox/AI-Development/Algolia Search Audit/*/`) and
`~/.claude/skills/algolia-search-audit/scripts/validate-json-schema.py` --
not invented generic shapes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from server.pipeline.claims import extract_claims
from server.pipeline.gate import SkillOutput
from server.pipeline.llm_stages import make_batch_factcheck_fn


def _skill_output(skill_name: str, audit_dir: Path) -> SkillOutput:
    return SkillOutput(
        skill_name=skill_name,
        domain="belk.com",
        audit_dir=audit_dir,
        company_name="Belk",
    )


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# algolia-intel-investor -- media_quotes[] (11-investor-intelligence.json)
# ---------------------------------------------------------------------------


def test_investor_media_quotes_extracted_with_speaker_and_quote(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "research" / "11-investor-intelligence.json",
        {
            "media_quotes": [
                {
                    "speaker": "Heidi O'Neill",
                    "title": "CEO-Designate",
                    "quote": "lululemon is an iconic brand.",
                    "source_url": "https://example.com/article",
                },
                {
                    "speaker": "Jane Doe",
                    "quote": "We are investing in AI.",
                    "source_url": "https://example.com/other",
                },
            ]
        },
    )
    so = _skill_output("algolia-intel-investor", tmp_path)
    claims = extract_claims(so)
    assert len(claims) == 2
    assert claims[0] == 'Heidi O\'Neill (CEO-Designate) stated: "lululemon is an iconic brand."'
    # no title -> just the speaker name, no dangling "()"
    assert claims[1] == 'Jane Doe stated: "We are investing in AI."'


def test_investor_media_quotes_skips_entries_missing_speaker_or_quote(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "research" / "11-investor-intelligence.json",
        {
            "media_quotes": [
                {"speaker": "No Quote Here", "source_url": "https://example.com"},
                {"quote": "No speaker here.", "source_url": "https://example.com"},
            ]
        },
    )
    so = _skill_output("algolia-intel-investor", tmp_path)
    assert extract_claims(so) == ()


# ---------------------------------------------------------------------------
# algolia-intel-industry -- benchmarks[] (industry-intel.json, both real
# filename variants seen in the wild)
# ---------------------------------------------------------------------------


def test_industry_benchmarks_extracted_from_unprefixed_filename(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "research" / "industry-intel.json",
        {
            "benchmarks": [
                {
                    "metric": "Apparel search-users convert vs. non-searchers",
                    "value": "13% vs 6%",
                    "context": "shoppers who use site search convert higher",
                    "confidence": "FACT",
                    "source_url": "https://example.com/study",
                }
            ]
        },
    )
    so = _skill_output("algolia-intel-industry", tmp_path)
    claims = extract_claims(so)
    assert claims == (
        "Apparel search-users convert vs. non-searchers: 13% vs 6% -- "
        "shoppers who use site search convert higher",
    )


def test_industry_benchmarks_extracted_from_numbered_prefix_filename(tmp_path: Path) -> None:
    # Newer audits (e.g. lululemon) name this file 06-industry-intel.json
    # instead -- confirmed real filename drift, both must resolve.
    _write_json(
        tmp_path / "research" / "06-industry-intel.json",
        {"benchmarks": [{"metric": "M", "value": "V", "context": ""}]},
    )
    so = _skill_output("algolia-intel-industry", tmp_path)
    assert extract_claims(so) == ("M: V",)


def test_industry_prefers_unprefixed_filename_when_both_exist(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "research" / "industry-intel.json",
        {"benchmarks": [{"metric": "A", "value": "1"}]},
    )
    _write_json(
        tmp_path / "research" / "06-industry-intel.json",
        {"benchmarks": [{"metric": "B", "value": "2"}]},
    )
    so = _skill_output("algolia-intel-industry", tmp_path)
    assert extract_claims(so) == ("A: 1",)


# ---------------------------------------------------------------------------
# algolia-audit-report -- intelligence_signals[] + industry_context.
# key_benchmarks[] + executives[] ({slug}-audit-data.json)
# ---------------------------------------------------------------------------


def test_report_intelligence_signals_extracted_with_heterogeneous_content_field(
    tmp_path: Path,
) -> None:
    _write_json(
        tmp_path / "deliverables" / "belk-audit-data.json",
        {
            "intelligence_signals": [
                {
                    "title": "New CTO appointed",
                    "detail": "Company appointed a new CTO to lead AI strategy.",
                    "source_url": "https://example.com/news",
                },
                {
                    "title": "Earnings call quote",
                    "quote": "We are doubling down on search.",
                    "source_url": "https://example.com/earnings",
                },
                {
                    "title": "Body variant",
                    "body": "Some body text claim.",
                    "source_url": "https://example.com/body",
                },
            ]
        },
    )
    so = _skill_output("algolia-audit-report", tmp_path)
    claims = extract_claims(so)
    assert claims == (
        "New CTO appointed: Company appointed a new CTO to lead AI strategy.",
        "Earnings call quote: We are doubling down on search.",
        "Body variant: Some body text claim.",
    )


def test_report_industry_context_key_benchmarks_extracted(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "deliverables" / "belk-audit-data.json",
        {
            "industry_context": {
                "key_benchmarks": [
                    {
                        "metric": "Checkout UX Best Practices",
                        "value": "35%",
                        "context": "conversion rate increase from checkout changes",
                        "source_url": "https://baymard.com/blog/current-state-of-checkout-ux",
                    }
                ]
            }
        },
    )
    so = _skill_output("algolia-audit-report", tmp_path)
    claims = extract_claims(so)
    assert claims == (
        "Checkout UX Best Practices: 35% -- conversion rate increase from checkout changes",
    )


def test_report_executives_extracted_with_name_title_and_quote(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "deliverables" / "belk-audit-data.json",
        {
            "executives": [
                {
                    "name": "Richard Spencer",
                    "title": "CIO",
                    "quote": "It had been a decade since we looked at our search solution.",
                    "quote_source": "https://example.com/interview",
                },
                {"name": "No Quote Exec", "title": "VP"},
            ]
        },
    )
    so = _skill_output("algolia-audit-report", tmp_path)
    claims = extract_claims(so)
    assert claims == (
        'Richard Spencer (CIO) stated: "It had been a decade since we looked at our search '
        'solution."',
    )


def test_report_finds_audit_data_json_regardless_of_slug_shape(tmp_path: Path) -> None:
    # Real filenames aren't a predictable slugification of company_name --
    # "British Airways" -> british-airways-audit-data.json,
    # "Michael Kors" -> michaelkors-audit-data.json. Glob, don't guess.
    _write_json(
        tmp_path / "deliverables" / "british-airways-audit-data.json",
        {"executives": [{"name": "Sean Doyle", "title": "CEO", "quote": "Behind the curve."}]},
    )
    so = _skill_output("algolia-audit-report", tmp_path)
    claims = extract_claims(so)
    assert claims == ('Sean Doyle (CEO) stated: "Behind the curve."',)


def test_report_combines_all_three_structures_in_one_call(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "deliverables" / "belk-audit-data.json",
        {
            "executives": [{"name": "A", "title": "CEO", "quote": "Q1"}],
            "intelligence_signals": [{"title": "T", "detail": "D"}],
            "industry_context": {"key_benchmarks": [{"metric": "M", "value": "V"}]},
        },
    )
    so = _skill_output("algolia-audit-report", tmp_path)
    claims = extract_claims(so)
    assert claims == ('A (CEO) stated: "Q1"', "T: D", "M: V")


# ---------------------------------------------------------------------------
# algolia-intel-company -- portfolio_brands[] (01-company-context.json)
# ---------------------------------------------------------------------------


def test_company_portfolio_brands_extracted_with_name_and_domain(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "research" / "01-company-context.json",
        {
            "portfolio_brands": [
                {
                    "name": "Belk",
                    "domain": "belk.com",
                    "source": "SEC 10-K",
                    "is_audit_target": True,
                },
                {"name": "No Domain Brand"},
            ]
        },
    )
    so = _skill_output("algolia-intel-company", tmp_path)
    claims = extract_claims(so)
    assert claims == (
        "Belk is a portfolio brand of this company, operating at belk.com.",
        "No Domain Brand is a portfolio brand of this company.",
    )


# ---------------------------------------------------------------------------
# Empty-tuple path -- skills with NO claim-bearing structure per
# validate-json-schema.py, and missing/malformed files for skills that do.
# ---------------------------------------------------------------------------


def test_skill_with_no_claim_bearing_structure_returns_empty_tuple(tmp_path: Path) -> None:
    # algolia-intel-techstack has no citable quote/benchmark array anywhere
    # in validate-json-schema.py -- not an error, a legitimate zero-claims
    # skill.
    _write_json(tmp_path / "research" / "02-tech-stack.json", {"tech_stack": {"platform": "SFCC"}})
    so = _skill_output("algolia-intel-techstack", tmp_path)
    assert extract_claims(so) == ()


def test_missing_output_file_returns_empty_tuple_not_an_error(tmp_path: Path) -> None:
    # audit_dir exists but the skill's file was never written yet.
    so = _skill_output("algolia-intel-investor", tmp_path)
    assert extract_claims(so) == ()


def test_malformed_json_returns_empty_tuple_not_an_error(tmp_path: Path) -> None:
    path = tmp_path / "research" / "11-investor-intelligence.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json", encoding="utf-8")
    so = _skill_output("algolia-intel-investor", tmp_path)
    assert extract_claims(so) == ()


def test_nonexistent_audit_dir_returns_empty_tuple_not_an_error(tmp_path: Path) -> None:
    so = _skill_output("algolia-audit-report", tmp_path / "does-not-exist")
    assert extract_claims(so) == ()


# ---------------------------------------------------------------------------
# End-to-end wiring: extract_claims plugged into Task 5b's
# make_batch_factcheck_fn -- proves the real gate.FactCheckFn callable works.
# ---------------------------------------------------------------------------


def test_extract_claims_wired_into_make_batch_factcheck_fn(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "research" / "11-investor-intelligence.json",
        {
            "media_quotes": [
                {"speaker": "Jane Doe", "quote": "We invest in AI.", "source_url": "https://x.com"}
            ]
        },
    )
    so = _skill_output("algolia-intel-investor", tmp_path)

    seen_prompts: list[str] = []

    def fake_cli(prompt: str) -> str:
        seen_prompts.append(prompt)
        return (
            '{"claim": "x", "evidence_tier": "AUTHENTIC", "verdict": "SUPPORTED", '
            '"citation": "https://x.com", "reasoning": "matches source"}'
        )

    batch_fn = make_batch_factcheck_fn(extract_claims, claude_cli_fn=fake_cli)
    verdicts = batch_fn(so)

    assert len(verdicts) == 1
    assert verdicts[0].verdict == "SUPPORTED"
    assert len(seen_prompts) == 1
    assert "Jane Doe" in seen_prompts[0]


def test_extract_claims_wired_into_make_batch_factcheck_fn_zero_claims_zero_calls(
    tmp_path: Path,
) -> None:
    # algolia-intel-techstack has no claim-bearing structure -- zero claims
    # must mean zero claude -p calls, per Task 5b's existing contract.
    so = _skill_output("algolia-intel-techstack", tmp_path)
    calls: list[str] = []

    def fake_cli(prompt: str) -> str:
        calls.append(prompt)
        return "{}"

    batch_fn = make_batch_factcheck_fn(extract_claims, claude_cli_fn=fake_cli)
    verdicts = batch_fn(so)

    assert verdicts == ()
    assert calls == []
