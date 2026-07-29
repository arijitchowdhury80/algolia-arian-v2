"""Intel Partner Track-1 collector — deterministic partner table lookup.

Reads the prospect's detected tech stack from context.upstream_results
(populated by intel-techstack, which runs in Wave 1B before this module).
Cross-references against ALGOLIA_PARTNER_TABLE using substring matching.

NO LLM, NO external API, NO browser.  Pure dict lookup — always fast,
always deterministic.

The result is merged into context.upstream_results under
``partner_tech_detection`` so the playbook can inject it as
``{upstream_partner_tech_detection}`` and the Track-2 LLM can reference
the confirmed partners verbatim without re-researching them.
"""

from __future__ import annotations

from typing import Any

import structlog

from prism_platform.v2.types import ExecutionContextV2

from .partner_table import ALGOLIA_PARTNER_TABLE, PARTNER_LOOKUP_KEYS

logger = structlog.get_logger(__name__)

# intel-techstack field names we probe for platform strings.
_TECHSTACK_PROBE_FIELDS = ("ecommerce_platform", "analytics_stack", "crm_platform")


def _normalise(value: Any) -> str:
    """Return a lowercase string for fuzzy matching, or '' if not a string."""
    if isinstance(value, str):
        return value.lower().strip()
    return ""


def _match_partners(platform_str: str, detected_via: str) -> list[dict[str, str]]:
    """Return all partner records whose key appears in ``platform_str``.

    Longest-key-first ordering in PARTNER_LOOKUP_KEYS prevents a shorter alias
    (e.g. "salesforce") from shadowing a more specific one
    ("salesforce commerce cloud") when both substrings are present.
    """
    matched: list[dict[str, str]] = []
    seen_partners: set[str] = set()

    for key in PARTNER_LOOKUP_KEYS:
        if key in platform_str:
            record = ALGOLIA_PARTNER_TABLE[key]
            partner_name = record["partner_name"]
            if partner_name in seen_partners:
                # Already added via a more-specific alias; skip duplicates.
                continue
            seen_partners.add(partner_name)
            matched.append(
                {
                    "partner_name": partner_name,
                    "integration_type": record["integration_type"],
                    "integration_doc_url": record["integration_doc_url"],
                    "detected_via": detected_via,
                    "raw_detected_value": platform_str,
                }
            )

    return matched


async def intel_partner_collector(context: ExecutionContextV2) -> dict[str, Any]:
    """Cross-reference the detected tech stack against the Algolia partner table.

    Returns a dict merged into context.upstream_results under the key
    ``partner_tech_detection``.  Never raises — failures are logged and
    an empty match list is returned so Track-2 still runs.
    """
    techstack: dict[str, Any] = context.upstream_results.get("intel-techstack", {})

    matched_partners: list[dict[str, str]] = []

    for field in _TECHSTACK_PROBE_FIELDS:
        raw_value = techstack.get(field)
        if not raw_value:
            continue
        normalised = _normalise(raw_value)
        if not normalised:
            continue
        hits = _match_partners(normalised, detected_via=field)
        matched_partners.extend(hits)

    # De-duplicate by partner_name across fields (a platform may appear in
    # multiple techstack fields, e.g. "salesforce" in both ecommerce + crm).
    seen: set[str] = set()
    unique_partners: list[dict[str, str]] = []
    for p in matched_partners:
        if p["partner_name"] not in seen:
            seen.add(p["partner_name"])
            unique_partners.append(p)

    has_overlap = len(unique_partners) > 0

    logger.info(
        "[intel-partner] Track-1 partner lookup complete",
        domain=context.account_domain,
        partners_matched=len(unique_partners),
        has_overlap=has_overlap,
        matched_names=[p["partner_name"] for p in unique_partners],
    )

    return {
        "partner_tech_detection": {
            "tech_partners": unique_partners,
            "has_algolia_partner_overlap": has_overlap,
            "detection_method": "static_partner_table",
            "techstack_fields_probed": list(_TECHSTACK_PROBE_FIELDS),
        }
    }
