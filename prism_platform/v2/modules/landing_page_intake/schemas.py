"""Landing Page Intake — candidate pool + content schemas.

Not a pipeline module: this reads an *existing, completed* audit's audit_data
JSONB on demand (given an audit_id), it never runs inside the audit pipeline
DAG. See prism_platform/v2/modules/landing_page_intake/candidate_extractor.py.

Design intent (docs/workspace/custom-landing-page/00-design-system.md +
feedback-audit-derivable-vs-sales-input-split): a Candidate is a proposal,
never an inclusion. The wizard shows candidates for a human to accept/edit/
reject; nothing here is auto-included in a rendered page.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CandidateKind = Literal["finding", "case_study", "stat"]


class Candidate(BaseModel):
    """One piece of audit-derivable content proposed to the intake wizard.

    `source_field` is the provenance trail (e.g. 'findings[2]',
    'case_studies[0]') -- required so a reviewer can trace any candidate back
    to the exact audit_data field it came from, never a synthesized guess.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Stable id within this pool, e.g. 'finding-0'")
    kind: CandidateKind
    source_field: str = Field(description="Provenance path into audit_data, e.g. 'findings[2]'")
    tag: str | None = Field(default=None, description="Short label, e.g. Finding.category")
    title: str
    body: str = ""
    metric: str | None = Field(default=None, description="A stat/number, if this candidate has one")
    link_href: str | None = None
    link_label: str | None = None


class CandidatePool(BaseModel):
    """Full set of candidates extracted from one audit, for one landing page slot set."""

    model_config = ConfigDict(extra="forbid")

    audit_id: str
    company_name: str
    candidates: list[Candidate] = Field(default_factory=list)
    skipped_fields: list[str] = Field(
        default_factory=list,
        description=(
            "audit_data fields that exist but were skipped (e.g. failed sub-validation). "
            "Surfaced for transparency, never silently dropped -- no-fabrication rule."
        ),
    )
