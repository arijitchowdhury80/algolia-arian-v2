"""Landing Page Intake — assemble a wizard submission into landing.json.

Merges the wizard's chosen sections + content (PRISM-approved candidates
and/or manual entries, already merged client-side by the wizard) into the
canonical landing.json shape, then validates against the shared JSON Schema
(docs/workspace/custom-landing-page/schema/landing-page.schema.json).

Deliberately does not decide what content is "good" -- that decision already
happened in the wizard (accept/edit/reject). This function's only job is
structural: does the submission produce a schema-valid landing.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

_SCHEMA_PATH = (
    # docs/ is at the repo root since the 2026-07-28 restructure, one level above
    # backend/, so this walks up one more than before.
    Path(__file__).resolve().parents[5]
    / "docs"
    / "workspace"
    / "custom-landing-page"
    / "schema"
    / "landing-page.schema.json"
)


class AssemblyError(ValueError):
    """Raised when a wizard submission does not produce a schema-valid landing.json."""


def _load_schema() -> dict[str, Any]:
    with _SCHEMA_PATH.open() as f:
        schema: dict[str, Any] = json.load(f)
        return schema


def assemble_landing_json(
    *,
    slug: str,
    company_name: str,
    sections: list[dict[str, Any]],
    content: dict[str, Any],
    theme: dict[str, Any] | None,
    audit_path: str | None,
) -> dict[str, Any]:
    """Build + validate the full landing.json for one landing page.

    `content` is whatever the wizard collected for meta/hero/findings/proof/
    cta_band/etc -- passed through largely as-is; this function's value-add is
    ensuring `meta` is complete and the whole document is schema-valid before
    it ever reaches the renderer.
    """
    meta = {
        "company": company_name,
        "slug": slug,
        "title": content.get("meta", {}).get("title") or f"Algolia for {company_name}",
        "description": content.get("meta", {}).get("description", ""),
        "audit_path": audit_path,
    }

    landing_json: dict[str, Any] = {
        **content,
        "meta": meta,
        "sections": sections,
    }
    if theme:
        landing_json["theme"] = theme

    # footer is required by the schema; the wizard always renders one, but
    # guard here too so a malformed submission fails loudly, not silently.
    landing_json.setdefault("footer", {})
    landing_json.setdefault("hero", {})

    schema = _load_schema()
    try:
        jsonschema.validate(landing_json, schema)
    except jsonschema.ValidationError as exc:
        raise AssemblyError(f"landing.json failed schema validation: {exc.message}") from exc

    return landing_json
