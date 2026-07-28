"""Task 5 (Track C.3) -- chunk `Audit.audit_data` by report section.

Per the task-5 brief's patch #9 (locked): chunking follows the audit's
existing logical structure (company/techstack/traffic/competitors/financial/
investor/social/news/hiring/partner/industry sections), one chunk per section
per company -- not a fixed-token sliding window. Audit reports are structured
JSON with real section boundaries; chunking along them keeps citations
traceable to a named section (e.g. "tech_stack", "financials"), which matters
for the grounded-not-fabricated requirement the chat agent must uphold.

This module is generic over the *actual* top-level keys of a real
`audit_data` blob (confirmed against docs/temp/fc/belk-audit-data.json --
keys like `tech_stack`, `financials`, `hiring`, `competitors`,
`intelligence_signals`, `case_studies`, etc.) rather than hardcoding a
section-name list that could drift from the real schema
(prism_platform/v2/audit_data_schema.py's `AuditData` already allows extra
fields, so a fixed list here would silently drop real sections).
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    """One retrievable, citable unit of an audit report."""

    section_name: str
    text: str


def _is_empty(value: object) -> bool:
    return value is None or value in ("", [], {})


def _section_to_text(section_name: str, value: object) -> str:
    """Render a section's value as compact, readable text for embedding.

    Plain `json.dumps` keeps every field name + value visible to the
    embedding model (helps semantic match on e.g. "latency" or "hiring
    signal") while staying more human-legible than a single-line minified
    blob when a chunk is later surfaced as a citation.
    """
    if isinstance(value, str):
        body = value
    else:
        body = json.dumps(value, indent=2, sort_keys=True, default=str)
    return f"# {section_name}\n{body}"


def chunk_audit_data(audit_data: dict[str, object]) -> list[Chunk]:
    """Split an `Audit.audit_data` JSONB blob into one Chunk per non-empty
    top-level section, in the blob's own key order (deterministic -- same
    input always yields the same chunk list/order, which matters for the
    unique `(audit_id, section_name)` constraint on `report_chunks`).
    """
    chunks: list[Chunk] = []
    for section_name, value in audit_data.items():
        if _is_empty(value):
            continue
        chunks.append(Chunk(section_name=section_name, text=_section_to_text(section_name, value)))
    return chunks
