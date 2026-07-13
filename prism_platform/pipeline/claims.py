"""Task 5c -- mechanical claim extraction, closing Task 5b's flagged gap.

Task 5b built `make_batch_factcheck_fn(claims_fn, ...)` matching
`gate.FactCheckFn`'s real shape (`SkillOutput -> tuple[FactCheckVerdict, ...]`)
but deliberately left `claims_fn` as a mandatory, no-default argument: turning
"a skill's output directory" into "the concrete list of discrete claims to
check" is a different problem than the judgment call `factcheck_fn` makes,
and Task 5b's brief did not scope building it. This module is that follow-up.

`extract_claims` is purely mechanical (no LLM call) -- it walks each skill's
real output JSON file(s) and pulls out the fields that are actually a factual
assertion paired with (or at least eligible for) a citation. Ground truth for
"which fields carry a checkable claim" is
`~/.claude/skills/algolia-search-audit/scripts/validate-json-schema.py`
(read in full, not just grepped) plus live inspection of real audit
workspaces (`~/prism-data/audits/{Dell,jbl,lululemon}/`, and
`~/Dropbox/AI-Development/Algolia Search Audit/*/`) to confirm actual field
names and the real, drifted file-naming convention (e.g. some audits have
`research/industry-intel.json`, newer ones have `research/06-industry-intel.json`
-- both are tried).

The 16 pipeline skills (`docs/workspace/phase2-executioner/task-1-recon-report.md`
item 5) are heterogeneous -- most of them (tech stack, traffic, competitors,
financial profile, social signals, news signals, hiring, partner intel, test
queries, browser findings, factcheck's own report) have NO field that
`validate-json-schema.py` treats as a citable claim (a single value with a
free-text "_source" label is not the same shape as an array of quotes/
benchmarks each carrying its own citation). Only 4 skills own a real
claim-bearing structure:

  - `algolia-intel-company`  -> research/01-company-context.json
                                 `portfolio_brands[]` (name/domain/source --
                                 validate-json-schema.py CHECK 7).
  - `algolia-intel-investor` -> research/11-investor-intelligence.json
                                 `media_quotes[]` (speaker/title/quote/
                                 source_url).
  - `algolia-intel-industry` -> research/{industry-intel,06-industry-intel}.json
                                 `benchmarks[]` (metric/value/context/
                                 source_url/confidence).
  - `algolia-audit-report`   -> deliverables/{slug}-audit-data.json (the
                                 lifted/merged deliverable) --
                                 `executives[]` (name/title/quote/
                                 quote_source -- CITATION BASELINE RULE,
                                 BLOCKING), `intelligence_signals[]`
                                 (detail/quote/body/title, source_url),
                                 `industry_context.key_benchmarks[]`
                                 (same shape as industry benchmarks).

Every other skill returns an empty tuple -- not an error, not a guessed
generic walker over arbitrary JSON. `make_batch_factcheck_fn` already treats
zero claims as zero `claude -p` calls (Task 5b's tests), so this is a
legitimate, cheap no-op for those skills rather than a gap.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from prism_platform.pipeline import gate as gate_module

# ---------------------------------------------------------------------------
# File loading -- tolerant of missing/malformed files (return None, not raise)
# ---------------------------------------------------------------------------


def _load_json_object(path: Path) -> dict[str, Any] | None:
    """Load `path` as a JSON object. Returns None (not an exception) for a
    missing file, unreadable file, malformed JSON, or a JSON value that
    isn't an object -- a skill that hasn't produced its output yet (or
    produced something unexpected) yields zero claims, it does not crash
    claim extraction for the whole audit."""
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _first_existing(candidates: list[Path]) -> Path | None:
    """Return the first candidate path that actually exists. Handles the
    real, confirmed filename drift across audit workspaces (e.g.
    `industry-intel.json` vs `06-industry-intel.json`) without guessing a
    single canonical name."""
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


# `_find_audit_data_json` used to duplicate this glob logic locally. Task 6d
# extracted it to `gate.find_audit_data_json` (gate.py's default mechanical
# command builder needs the exact same resolution) so both modules share one
# implementation instead of two that could drift.
_find_audit_data_json = gate_module.find_audit_data_json


# ---------------------------------------------------------------------------
# Per-structure claim rendering -- combine the assertion with enough context
# to be checkable standalone (never just "benchmarks[2]").
# ---------------------------------------------------------------------------


def _benchmark_claim(benchmark: dict[str, Any]) -> str | None:
    """`benchmarks[]` (industry-intel.json) / `key_benchmarks[]`
    (audit-data.json industry_context) -- same shape: metric + value,
    optionally with context."""
    metric = str(benchmark.get("metric") or "").strip()
    value = str(benchmark.get("value") or "").strip()
    if not metric or not value:
        return None
    context = str(benchmark.get("context") or "").strip()
    base = f"{metric}: {value}"
    return f"{base} -- {context}" if context else base


def _media_quote_claim(media_quote: dict[str, Any]) -> str | None:
    """`media_quotes[]` (11-investor-intelligence.json) -- speaker + quote."""
    speaker = str(media_quote.get("speaker") or "").strip()
    quote = str(media_quote.get("quote") or "").strip()
    if not speaker or not quote:
        return None
    title = str(media_quote.get("title") or "").strip()
    who = f"{speaker} ({title})" if title else speaker
    return f'{who} stated: "{quote}"'


def _executive_claim(executive: dict[str, Any]) -> str | None:
    """`executives[]` (audit-data.json) -- name + quote. Per
    validate-json-schema.py's CITATION BASELINE RULE, every executive with a
    quote must carry a `quote_source` -- that requirement is factcheck_fn's
    concern (evidence_tier judgment), not this extractor's; this just
    surfaces the claim to be judged."""
    name = str(executive.get("name") or "").strip()
    quote = str(executive.get("quote") or "").strip()
    if not name or not quote:
        return None
    title = str(executive.get("title") or "").strip()
    who = f"{name} ({title})" if title else name
    return f'{who} stated: "{quote}"'


def _intelligence_signal_claim(signal: dict[str, Any]) -> str | None:
    """`intelligence_signals[]` (audit-data.json) -- heterogeneous content
    field name across signal types (`detail`/`quote`/`body`), per the
    brief's ground truth."""
    content = str(signal.get("detail") or signal.get("quote") or signal.get("body") or "").strip()
    if not content:
        return None
    title = str(signal.get("title") or signal.get("badge_label") or "").strip()
    return f"{title}: {content}" if title else content


def _portfolio_brand_claim(brand: dict[str, Any]) -> str | None:
    """`portfolio_brands[]` (01-company-context.json) -- brand + domain
    (validate-json-schema.py CHECK 7)."""
    name = str(brand.get("name") or "").strip()
    if not name:
        return None
    domain = str(brand.get("domain") or "").strip()
    if domain:
        return f"{name} is a portfolio brand of this company, operating at {domain}."
    return f"{name} is a portfolio brand of this company."


# ---------------------------------------------------------------------------
# Per-skill extractors -- locate the real file(s), walk the real structures.
# ---------------------------------------------------------------------------


def _extract_company_claims(audit_dir: Path) -> tuple[str, ...]:
    data = _load_json_object(audit_dir / "research" / "01-company-context.json")
    if data is None:
        return ()
    brands = data.get("portfolio_brands") or []
    return tuple(
        claim
        for brand in brands
        if isinstance(brand, dict) and (claim := _portfolio_brand_claim(brand)) is not None
    )


def _extract_investor_claims(audit_dir: Path) -> tuple[str, ...]:
    data = _load_json_object(audit_dir / "research" / "11-investor-intelligence.json")
    if data is None:
        return ()
    media_quotes = data.get("media_quotes") or []
    return tuple(
        claim
        for media_quote in media_quotes
        if isinstance(media_quote, dict) and (claim := _media_quote_claim(media_quote)) is not None
    )


def _extract_industry_claims(audit_dir: Path) -> tuple[str, ...]:
    research_dir = audit_dir / "research"
    path = _first_existing(
        [research_dir / "industry-intel.json", research_dir / "06-industry-intel.json"]
    )
    data = _load_json_object(path) if path is not None else None
    if data is None:
        return ()
    benchmarks = data.get("benchmarks") or []
    return tuple(
        claim
        for benchmark in benchmarks
        if isinstance(benchmark, dict) and (claim := _benchmark_claim(benchmark)) is not None
    )


def _extract_report_claims(audit_dir: Path) -> tuple[str, ...]:
    path = _find_audit_data_json(audit_dir)
    data = _load_json_object(path) if path is not None else None
    if data is None:
        return ()

    claims: list[str] = []

    for executive in data.get("executives") or []:
        if isinstance(executive, dict) and (claim := _executive_claim(executive)) is not None:
            claims.append(claim)

    for signal in data.get("intelligence_signals") or []:
        if isinstance(signal, dict) and (claim := _intelligence_signal_claim(signal)) is not None:
            claims.append(claim)

    industry_context = data.get("industry_context") or {}
    for key_benchmark in industry_context.get("key_benchmarks") or []:
        if (
            isinstance(key_benchmark, dict)
            and (claim := _benchmark_claim(key_benchmark)) is not None
        ):
            claims.append(claim)

    return tuple(claims)


# skill_name -> extractor. Every other skill_name (the 12 without a
# claim-bearing structure per validate-json-schema.py) is absent from this
# table on purpose -- `extract_claims` treats an absent key as "zero claims",
# not an error.
_EXTRACTORS: dict[str, Callable[[Path], tuple[str, ...]]] = {
    "algolia-intel-company": _extract_company_claims,
    "algolia-intel-investor": _extract_investor_claims,
    "algolia-intel-industry": _extract_industry_claims,
    "algolia-audit-report": _extract_report_claims,
}


def extract_claims(skill_output: gate_module.SkillOutput) -> tuple[str, ...]:
    """`claims_fn` for `make_batch_factcheck_fn` (Task 5b's
    `llm_stages.py`). Mechanical, deterministic -- no LLM call. Returns the
    claim strings that need `factcheck_fn`'s judgment for
    `skill_output.skill_name`'s real output file(s) under
    `skill_output.audit_dir`. A skill with no established claim-bearing
    structure, or whose output file is missing/malformed, returns an empty
    tuple rather than raising -- `make_batch_factcheck_fn` already turns zero
    claims into zero `claude -p` calls."""
    extractor = _EXTRACTORS.get(skill_output.skill_name)
    if extractor is None:
        return ()
    return extractor(skill_output.audit_dir)
