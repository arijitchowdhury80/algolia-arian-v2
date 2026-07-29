"""Intel Competitors Track-1 collector — deterministic search-vendor detection.

Runs PRISM's packet-inspection detector against the prospect and every competitor
(from the F1-hydrated context.competitors) on ONE shared stealth browser. NO LLM,
NO paid API — vendor identity is read live off each site's search API call, with
App ID / endpoint extracted from the packet.

The result is merged into context.upstream_results under ``competitor_search_detection``
so the playbook can inject it as ``{upstream_competitor_search_detection}`` and the
Track-2 LLM copies the vendor facts through verbatim (adds case studies + narrative only).
"""

from __future__ import annotations

from typing import Any

import structlog

from prism_platform.v2.detection import SearchVendorResult, scan_search_vendors
from prism_platform.v2.types import ExecutionContextV2

logger = structlog.get_logger(__name__)

# Hard cap on competitors scanned (matches the seed's 5-7 competitor target).
_MAX_COMPETITORS = 7


def _profile(name: str, domain: str, det: SearchVendorResult) -> dict[str, Any]:
    """Shape a SearchVendorResult into the dict the playbook/schema expect."""
    return {
        "company_name": name,
        "domain": domain,
        "search_vendor": det.search_vendor,
        "search_vendor_status": det.search_vendor_status,
        "detection_source": "network_capture",
        "is_algolia_customer": det.is_algolia,
        "app_id": det.app_id,
        "endpoint_host": det.endpoint_host,
        "all_vendors": det.all_vendors,
        "proxied": det.proxied,
        "evidence": det.evidence_url or ", ".join(det.matched_patterns) or det.note,
    }


async def collect(context: ExecutionContextV2) -> dict[str, Any]:
    """Detect search vendors for the prospect + competitors. Never raises."""
    # Prospect first, then up to N competitors (from F1-hydrated context).
    targets: list[tuple[str, str]] = [
        (context.company_name or context.account_domain, context.account_domain)
    ]
    targets += [(c.name, c.domain) for c in context.competitors[:_MAX_COMPETITORS]]

    domains = [d for _, d in targets]
    try:
        results = await scan_search_vendors(domains)
    except Exception as exc:  # batch is defensive, but never let detection kill the module
        logger.warning("[intel-competitors] scan batch failed", error=str(exc))
        results = {}

    profiles: list[dict[str, Any]] = []
    for name, domain in targets:
        det = results.get(domain) or SearchVendorResult(
            domain=domain, search_vendor_status="ERROR", note="no result returned"
        )
        profiles.append(_profile(name, domain, det))

    prospect_profile = profiles[0]
    competitor_profiles = profiles[1:]
    golden = [p["domain"] for p in competitor_profiles if p["is_algolia_customer"]]

    logger.info(
        "[intel-competitors] Track-1 detection complete",
        domain=context.account_domain,
        competitors_scanned=len(competitor_profiles),
        golden_angle_count=len(golden),
        prospect_vendor=prospect_profile["search_vendor"],
    )

    return {
        "competitor_search_detection": {
            "prospect": prospect_profile,
            "competitors": competitor_profiles,
            "golden_angle_domains": golden,
            "detection_method": "network_capture",
        }
    }
