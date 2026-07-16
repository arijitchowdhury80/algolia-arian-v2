"""PRISM Landing Pages Router — Marketer persona intake wizard backend.

Follows the audits.py CRUD-router pattern (Pydantic request/response models
+ DbSession + SQLAlchemy), not modules.py's execute-module pattern -- this is
a deterministic transform over an existing audit's data, never a
Perplexity-backed research module. See
prism_platform/v2/modules/landing_page_intake/config.py for why.
"""

from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from prism_platform.api.deps import DbSession
from prism_platform.db.models import Account, Audit, LandingPage
from prism_platform.v2.modules.landing_page_intake.candidate_extractor import extract_candidates
from prism_platform.v2.modules.landing_page_intake.content_assembler import (
    AssemblyError,
    assemble_landing_json,
)
from prism_platform.v2.modules.landing_page_intake.schemas import CandidatePool

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()

# Where prism-hub's renderer reads landing.json from + writes rendered HTML.
# Cross-repo path by design (PIP assembles, prism-hub renders/serves) -- see
# docs/workspace/custom-landing-page/00-design-system.md Architecture.
_MARKETER_DATA_DIR = Path.home() / "prism" / "marketer" / "data"
_MARKETER_RENDER_SCRIPT = Path.home() / "prism" / "marketer" / "render-landing.mjs"


class AuditSummary(BaseModel):
    """One row in the intake wizard's audit picker."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    domain: str
    status: str


class BuildSectionEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot: str
    variant: str
    source: str = "manual"
    # Per-instance content for repeatable body sections (proof.cards,
    # roi.cards, etc). Independent per instance by design -- two "ROI tiers"
    # sections each carry their own content, never a shared global key. None
    # for hero/footer, which stay single-instance and read the top-level
    # content.hero / content.cta_band instead.
    content: dict[str, Any] | None = None


class BuildLandingPageRequest(BaseModel):
    """Body for POST /api/v1/landing-pages/ -- the wizard's final submission."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    company_name: str
    audit_id: uuid.UUID | None = None
    sections: list[BuildSectionEntry]
    theme: dict[str, Any] | None = None
    content: dict[str, Any]


class BuildLandingPageResponse(BaseModel):
    id: uuid.UUID
    slug: str
    status: str


class PreviewLandingPageRequest(BaseModel):
    """Body for POST /api/v1/landing-pages/preview -- same shape as a build,
    but never persisted and never left on disk under a real slug."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    company_name: str
    audit_id: uuid.UUID | None = None
    sections: list[BuildSectionEntry]
    theme: dict[str, Any] | None = None
    content: dict[str, Any]


class PreviewLandingPageResponse(BaseModel):
    html: str | None
    error: str | None = None


class ExtractFromJsonRequest(BaseModel):
    """Body for POST /api/v1/landing-pages/extract-from-json.

    For content sourced from anywhere other than a PRISM audit_id -- another
    campaign's audit-data.json, a one-off export, etc. Reuses the exact same
    extractor as the PRISM path: candidate_extractor.extract_candidates()
    takes a plain dict, it was never actually coupled to Postgres or to
    PRISM being the source.
    """

    model_config = ConfigDict(extra="forbid")

    company_name: str
    audit_data: dict[str, Any]


@router.get("/audits", response_model=list[AuditSummary])
async def list_audits_for_intake(session: DbSession) -> list[AuditSummary]:
    """List completed audits for the intake wizard's optional audit picker.

    Deliberately scoped to status='completed' -- an in-progress audit's
    findings/case_studies may still change, and the wizard should only offer
    stable data to pre-fill from.
    """
    result = await session.execute(
        select(Audit, Account)
        .join(Account, Audit.account_id == Account.id)
        .where(Audit.status == "completed")
        .order_by(Audit.created_at.desc())
    )
    rows = result.all()
    return [
        AuditSummary(
            id=audit.id,
            company_name=account.company_name,
            domain=account.domain,
            status=audit.status,
        )
        for audit, account in rows
    ]


@router.get("/audits/{audit_id}/candidates", response_model=CandidatePool)
async def get_candidates_for_audit(audit_id: uuid.UUID, session: DbSession) -> CandidatePool:
    """Extract candidate content from one audit's stored audit_data.

    Nothing here is auto-included -- the wizard shows these for a human to
    accept/edit/reject (feedback-audit-derivable-vs-sales-input-split).
    """
    result = await session.execute(select(Audit, Account).join(Account).where(Audit.id == audit_id))
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Audit not found.")
    audit, account = row

    if not audit.audit_data:
        return CandidatePool(
            audit_id=str(audit_id), company_name=account.company_name, candidates=[]
        )

    return extract_candidates(str(audit_id), account.company_name, audit.audit_data)


@router.post("/extract-from-json", response_model=CandidatePool)
async def extract_from_external_json(body: ExtractFromJsonRequest) -> CandidatePool:
    """Extract candidates from audit-data JSON that has no PRISM audit_id.

    Same extractor, same no-fabrication guarantees, same accept/edit/reject
    review in the wizard -- the only difference from the PRISM path is where
    the audit_data dict came from (pasted by the user, not looked up by id).
    """
    return extract_candidates("external", body.company_name, body.audit_data)


@router.post("/", response_model=BuildLandingPageResponse, status_code=201)
async def build_landing_page(
    body: BuildLandingPageRequest, session: DbSession
) -> BuildLandingPageResponse:
    """Assemble + persist a landing page, then trigger the prism-hub renderer.

    audit_id is optional by design -- PRISM audit data is a pre-fill
    convenience for the wizard, never a prerequisite. A fully manual
    submission (audit_id=None) is a first-class, fully supported build.
    """
    audit_path = None
    if body.audit_id is not None:
        result = await session.execute(select(Audit).where(Audit.id == body.audit_id))
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=404, detail="audit_id does not reference an existing audit."
            )
        audit_path = f"/reports/{body.slug}/"

    try:
        landing_json = assemble_landing_json(
            slug=body.slug,
            company_name=body.company_name,
            sections=[s.model_dump() for s in body.sections],
            content=body.content,
            theme=body.theme,
            audit_path=audit_path,
        )
    except AssemblyError as exc:
        logger.warning("build_landing_page.assembly_failed", slug=body.slug, error=str(exc))
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Upsert-by-slug: rebuilding the same company's page (iterating on copy,
    # re-running after an audit refresh) is the expected common case, not an
    # error -- a raw unique-constraint violation here would be a false-green
    # "it works" until the second build of any given slug.
    existing = await session.execute(select(LandingPage).where(LandingPage.slug == body.slug))
    landing_page = existing.scalar_one_or_none()
    if landing_page is None:
        landing_page = LandingPage(slug=body.slug)
        session.add(landing_page)

    landing_page.company_name = body.company_name
    landing_page.audit_id = body.audit_id
    landing_page.content_json = landing_json
    landing_page.sections_json = [s.model_dump() for s in body.sections]
    landing_page.theme_json = body.theme
    landing_page.status = "assembled"
    await session.flush()

    render_status, _ = _render_via_node(body.slug, landing_json)
    landing_page.status = render_status
    await session.flush()

    logger.info("build_landing_page.done", slug=body.slug, status=render_status)
    return BuildLandingPageResponse(id=landing_page.id, slug=body.slug, status=render_status)


@router.post("/preview", response_model=PreviewLandingPageResponse)
async def preview_landing_page(body: PreviewLandingPageRequest) -> PreviewLandingPageResponse:
    """Render a real preview through the actual production pipeline.

    Not an approximation: same assemble_landing_json + same partials + same
    render-landing.mjs as a real build, so what this returns is exactly what
    a build with this content/sections would produce. Never persisted (no
    DB write, no audit_id validation) and the scratch render is deleted
    immediately after reading it back -- see _cleanup_scratch_render.
    """
    scratch_slug = f"__preview__-{uuid.uuid4().hex[:12]}"
    try:
        landing_json = assemble_landing_json(
            slug=scratch_slug,
            company_name=body.company_name,
            sections=[s.model_dump() for s in body.sections],
            content=body.content,
            theme=body.theme,
            audit_path=None,
        )
    except AssemblyError as exc:
        logger.info("preview_landing_page.assembly_failed", error=str(exc))
        return PreviewLandingPageResponse(html=None, error=str(exc))

    try:
        status, html = _render_via_node(scratch_slug, landing_json)
    finally:
        _cleanup_scratch_render(scratch_slug)

    if status != "built" or html is None:
        return PreviewLandingPageResponse(
            html=None, error="Preview render failed -- check server logs."
        )
    return PreviewLandingPageResponse(html=html)


def _render_via_node(slug: str, landing_json: dict[str, Any]) -> tuple[str, str | None]:
    """Write landing.json to prism-hub's data dir and invoke its renderer.

    Cross-repo call by design (see module docstring). Never raises -- a
    render failure downgrades status rather than failing the whole call,
    since the DB row + landing.json (for a real build) are still valid
    artifacts on their own. Returns (status, rendered_html_or_None).
    """
    try:
        _MARKETER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        data_path = _MARKETER_DATA_DIR / f"{slug}.landing.json"
        data_path.write_text(json.dumps(landing_json, indent=2))
    except OSError as exc:
        logger.error("render_via_node.write_failed", slug=slug, error=str(exc))
        return "assembled", None  # landing.json exists only in the DB, not on disk

    if not _MARKETER_RENDER_SCRIPT.exists():
        logger.warning("render_via_node.renderer_missing", path=str(_MARKETER_RENDER_SCRIPT))
        return "assembled", None

    try:
        subprocess.run(
            ["node", str(_MARKETER_RENDER_SCRIPT), slug],
            cwd=str(_MARKETER_RENDER_SCRIPT.parent),
            check=True,
            capture_output=True,
            timeout=30,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.error("render_via_node.render_failed", slug=slug, stderr=exc.stderr)
        return "assembled", None
    except subprocess.TimeoutExpired:
        logger.error("render_via_node.render_timeout", slug=slug)
        return "assembled", None

    out_path = _MARKETER_RENDER_SCRIPT.parent / f"{slug}.html"
    try:
        html = out_path.read_text()
    except OSError as exc:
        logger.error("render_via_node.read_back_failed", slug=slug, error=str(exc))
        return "built", None

    return "built", html


def _cleanup_scratch_render(slug: str) -> None:
    """Delete a preview's scratch landing.json + html.

    Preview renders MUST NOT be left sitting in prism-hub's marketer/
    directory -- that directory auto-deploys on push (see
    docs/workspace/custom-landing-page/00-design-system.md Architecture);
    an orphaned scratch file there is one `git add .` away from going live
    under a throwaway name.
    """
    for path in (
        _MARKETER_DATA_DIR / f"{slug}.landing.json",
        _MARKETER_RENDER_SCRIPT.parent / f"{slug}.html",
    ):
        path.unlink(missing_ok=True)
