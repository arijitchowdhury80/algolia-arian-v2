"""Unit tests for the landing-page-intake candidate extractor.

Covers:
- Happy path: valid findings + case_studies produce the expected candidates
- No-fabrication: a missing field produces no candidates + a skipped_fields entry
- Partial-malformed: one bad item is skipped without killing the whole pool
- Caps: MAX_FINDING_CANDIDATES / MAX_CASE_STUDY_CANDIDATES are respected
- Schema contract: CandidatePool / Candidate round-trip
"""

from __future__ import annotations

from prism_platform.v2.modules.landing_page_intake.candidate_extractor import extract_candidates
from prism_platform.v2.modules.landing_page_intake.config import (
    MAX_CASE_STUDY_CANDIDATES,
    MAX_FINDING_CANDIDATES,
)
from prism_platform.v2.modules.landing_page_intake.schemas import Candidate, CandidatePool

_VALID_FINDING = {
    "id": "f1",
    "title": "Every visitor sees the same results",
    "severity": "critical",
    "category": "Personalization",
    "tested_query": "running shoes",
    "actual_behavior": "No personalization signal shapes ranking.",
    "algolia_solution": "Algolia AI Search personalizes ranking per shopper.",
    "impact_stat": "+15% conversion",
    "impact_stat_source": "https://www.algolia.com/customers/example",
    "algolia_case_study_company": "Example Co",
    "algolia_case_study_url": "https://www.algolia.com/customers/example",
    "algolia_case_study_result": "+15% conversion",
}

_VALID_CASE_STUDY = {
    "vertical": "B2B industrial tools",
    "company": "Swedol",
    "result": "+22% conversion",
    "product": "Algolia AI Search",
    "why": "Personalized B2B search across the Nordic region.",
    "url": "https://www.algolia.com/customers/swedol",
}


def test_happy_path_extracts_finding_and_case_study() -> None:
    audit_data = {"findings": [_VALID_FINDING], "case_studies": [_VALID_CASE_STUDY]}
    pool = extract_candidates("audit-1", "Dell", audit_data)

    assert isinstance(pool, CandidatePool)
    assert pool.audit_id == "audit-1"
    assert len(pool.candidates) == 2
    assert not pool.skipped_fields

    finding_candidate = next(c for c in pool.candidates if c.kind == "finding")
    assert finding_candidate.source_field == "findings[0]"
    assert finding_candidate.title == _VALID_FINDING["title"]
    assert finding_candidate.metric == "+15% conversion"
    assert finding_candidate.link_href == _VALID_FINDING["algolia_case_study_url"]

    case_study_candidate = next(c for c in pool.candidates if c.kind == "case_study")
    assert case_study_candidate.source_field == "case_studies[0]"
    assert case_study_candidate.title == "Swedol"
    assert case_study_candidate.metric == "+22% conversion"


def test_missing_fields_produce_no_candidates_and_are_skipped() -> None:
    pool = extract_candidates("audit-2", "Nike", {})

    assert pool.candidates == []
    assert "findings" in pool.skipped_fields
    assert "case_studies" in pool.skipped_fields


def test_malformed_item_is_skipped_not_fatal() -> None:
    malformed_finding = {"id": "bad", "title": "Missing required fields"}
    audit_data = {
        "findings": [_VALID_FINDING, malformed_finding],
        "case_studies": [_VALID_CASE_STUDY],
    }
    pool = extract_candidates("audit-3", "Dell", audit_data)

    finding_candidates = [c for c in pool.candidates if c.kind == "finding"]
    assert len(finding_candidates) == 1
    assert "findings[1]" in pool.skipped_fields


def test_impact_stat_without_source_is_rejected_by_finding_schema() -> None:
    # Finding.validate_finding blocks impact_stat without impact_stat_source --
    # candidate_extractor must surface this as a skip, not crash the pool.
    unsourced = {**_VALID_FINDING, "impact_stat_source": None}
    pool = extract_candidates("audit-4", "Dell", {"findings": [unsourced]})

    assert pool.candidates == []
    assert "findings[0]" in pool.skipped_fields


def test_caps_are_respected() -> None:
    findings = [
        {**_VALID_FINDING, "id": f"f{i}", "title": f"Finding {i}"}
        for i in range(MAX_FINDING_CANDIDATES + 5)
    ]
    case_studies = [
        {**_VALID_CASE_STUDY, "company": f"Company {i}"}
        for i in range(MAX_CASE_STUDY_CANDIDATES + 5)
    ]
    audit_data = {"findings": findings, "case_studies": case_studies}
    pool = extract_candidates("audit-5", "Dell", audit_data)

    finding_candidates = [c for c in pool.candidates if c.kind == "finding"]
    case_study_candidates = [c for c in pool.candidates if c.kind == "case_study"]
    assert len(finding_candidates) == MAX_FINDING_CANDIDATES
    assert len(case_study_candidates) == MAX_CASE_STUDY_CANDIDATES


def test_high_medium_low_severity_vocabulary_is_normalized() -> None:
    # Regression: real audit_data (Lululemon fixture) uses a HIGH/MEDIUM/LOW
    # risk-tier vocabulary instead of critical/moderate/positive. Before the
    # fix, this silently dropped every finding via a schema mismatch.
    for raw_severity in ("HIGH", "MEDIUM", "LOW", "high", "medium"):
        finding = {**_VALID_FINDING, "severity": raw_severity}
        pool = extract_candidates("audit-x", "Test Co", {"findings": [finding]})
        assert len(pool.candidates) == 1, f"severity={raw_severity!r} was incorrectly skipped"
        assert "findings[0]" not in pool.skipped_fields


def test_candidate_schema_forbids_extra_fields() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Candidate(
            id="x",
            kind="finding",
            source_field="findings[0]",
            title="t",
            unexpected_field="nope",
        )
