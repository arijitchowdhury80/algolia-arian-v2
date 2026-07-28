"""Landing Page Intake — candidate extraction from an existing audit.

Reads a completed audit's `audit_data` JSONB and proposes candidate content
for the intake wizard's Step 2 (per-section content). Every candidate is
tagged with its exact provenance (source_field) and nothing is auto-included
-- the wizard shows these for a human to accept/edit/reject
(feedback-audit-derivable-vs-sales-input-split).

No fabrication: a field that is missing or fails to parse produces no
candidate and is recorded in `skipped_fields`, never a placeholder.

Deliberately does NOT force the raw dict through the strict `AuditData`
pydantic model (prism_platform/v2/audit_data_schema.py) -- that model's
completion gate can raise on an audit that hasn't finished ABX sequencing,
even though its `findings`/`case_studies` are already good candidate
material. Sub-models (Finding, CaseStudy) are parsed individually instead,
so one malformed item never kills the whole pool.
"""

from __future__ import annotations

from typing import Any

import structlog

from prism_platform.v2.audit_data_schema import CaseStudy, Finding
from prism_platform.v2.modules.landing_page_intake.config import (
    MAX_CASE_STUDY_CANDIDATES,
    MAX_FINDING_CANDIDATES,
)
from prism_platform.v2.modules.landing_page_intake.schemas import Candidate, CandidatePool

logger = structlog.get_logger(__name__)

# Some audit generators emit HIGH/MEDIUM/LOW severity (a risk-tier vocabulary)
# instead of the Finding schema's critical/moderate/positive (an audit-verdict
# vocabulary) -- both real, both seen in production audit_data (see Lululemon
# fixture, docs/temp/fc/lululemon-audit-data.json). Normalizing here is a
# label canonicalization, not a fabrication: the underlying finding content is
# untouched, only its severity string is mapped to the schema's vocabulary so
# real findings aren't silently dropped by a vocabulary mismatch.
_SEVERITY_ALIASES = {
    "HIGH": "critical",
    "MEDIUM": "moderate",
    "LOW": "moderate",
}


def _normalize_severity(raw: dict[str, Any]) -> dict[str, Any]:
    severity = raw.get("severity")
    if isinstance(severity, str) and severity.upper() in _SEVERITY_ALIASES:
        raw = {**raw, "severity": _SEVERITY_ALIASES[severity.upper()]}
    return raw


def _findings_to_candidates(raw_findings: list[Any]) -> tuple[list[Candidate], list[str]]:
    candidates: list[Candidate] = []
    skipped: list[str] = []
    for i, raw in enumerate(raw_findings[:MAX_FINDING_CANDIDATES]):
        source_field = f"findings[{i}]"
        try:
            finding = Finding.model_validate(_normalize_severity(raw))
        except Exception as exc:
            logger.warning(
                "candidate_extractor.finding_skipped", source_field=source_field, error=str(exc)
            )
            skipped.append(source_field)
            continue
        body = finding.actual_behavior
        if finding.algolia_solution:
            body = f"{body} {finding.algolia_solution}"
        candidates.append(
            Candidate(
                id=f"finding-{i}",
                kind="finding",
                source_field=source_field,
                tag=finding.category,
                title=finding.title,
                body=body,
                metric=finding.impact_stat,
                link_href=finding.algolia_case_study_url,
                link_label=(
                    "Read their story" if finding.algolia_case_study_url else None
                ),
            )
        )
    return candidates, skipped


def _case_studies_to_candidates(raw_case_studies: list[Any]) -> tuple[list[Candidate], list[str]]:
    candidates: list[Candidate] = []
    skipped: list[str] = []
    for i, raw in enumerate(raw_case_studies[:MAX_CASE_STUDY_CANDIDATES]):
        source_field = f"case_studies[{i}]"
        try:
            case_study = CaseStudy.model_validate(raw)
        except Exception as exc:
            logger.warning(
                "candidate_extractor.case_study_skipped",
                source_field=source_field,
                error=str(exc),
            )
            skipped.append(source_field)
            continue
        candidates.append(
            Candidate(
                id=f"case-study-{i}",
                kind="case_study",
                source_field=source_field,
                tag=case_study.vertical,
                title=case_study.company,
                body=case_study.why,
                metric=case_study.result,
                link_href=case_study.url,
                link_label="Read their story",
            )
        )
    return candidates, skipped


def extract_candidates(
    audit_id: str, company_name: str, audit_data: dict[str, Any]
) -> CandidatePool:
    """Build a CandidatePool from one audit's stored audit_data JSON.

    `audit_data` is the raw dict from `Audit.audit_data` (Postgres JSONB) --
    never re-fetched or re-derived here, so this function has no DB/network
    dependency and is trivially unit-testable with a plain dict.
    """
    all_candidates: list[Candidate] = []
    all_skipped: list[str] = []

    raw_findings = audit_data.get("findings")
    if isinstance(raw_findings, list):
        findings_candidates, findings_skipped = _findings_to_candidates(raw_findings)
        all_candidates.extend(findings_candidates)
        all_skipped.extend(findings_skipped)
    else:
        all_skipped.append("findings")

    raw_case_studies = audit_data.get("case_studies")
    if isinstance(raw_case_studies, list):
        case_study_candidates, case_study_skipped = _case_studies_to_candidates(raw_case_studies)
        all_candidates.extend(case_study_candidates)
        all_skipped.extend(case_study_skipped)
    else:
        all_skipped.append("case_studies")

    logger.info(
        "candidate_extractor.done",
        audit_id=audit_id,
        candidate_count=len(all_candidates),
        skipped_count=len(all_skipped),
    )

    return CandidatePool(
        audit_id=audit_id,
        company_name=company_name,
        candidates=all_candidates,
        skipped_fields=all_skipped,
    )
