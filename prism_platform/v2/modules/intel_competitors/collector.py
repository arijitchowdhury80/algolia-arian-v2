"""Intel Competitors Track-1 collector — deterministic search-vendor detection.

Runs PRISM's in-app Scout-based detector against the prospect and every
competitor (from the F1-hydrated context.competitors). NO LLM, NO paid API.

The result is merged into context.upstream_results under
``competitor_search_detection`` so the playbook can inject it as
``{upstream_competitor_search_detection}`` and the Track-2 LLM copies the
vendor facts through verbatim (it only adds case studies + narrative).
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from prism_platform.browser import BrowserClient
from prism_platform.v2.detection import SearchVendorResult, detect_search_vendor
from prism_platform.v2.types import ExecutionContextV2

logger = structlog.get_logger(__name__)

# Cap concurrent domain scans so we don't overwhelm the browser tier.
_MAX_CONCURRENCY = 4
# Hard cap on competitors scanned (matches the seed's 5-7 competitor target).
_MAX_COMPETITORS = 7


def _profile(name: str, domain: str, det: SearchVendorResult) -> dict[str, Any]:
    """Shape a SearchVendorResult into the dict the playbook/schema expect."""
    return {
        "company_name": name,
        "domain": domain,
        "search_vendor": det.search_vendor,
        "search_vendor_status": det.search_vendor_status,
        "detection_source": "scout_source_scan",
        "is_algolia_customer": det.is_algolia,
        "evidence": ", ".join(det.matched_patterns) or det.note or det.evidence_url,
        "commerce_platform": det.commerce_platform,
    }


async def collect(context: ExecutionContextV2) -> dict[str, Any]:
    """Detect search vendors for the prospect + competitors. Never raises."""
    client = BrowserClient()
    sem = asyncio.Semaphore(_MAX_CONCURRENCY)

    async def scan(name: str, domain: str) -> dict[str, Any]:
        async with sem:
            try:
                det = await detect_search_vendor(domain, browser_client=client)
            except Exception as exc:  # detector is defensive, but never let one kill the batch
                logger.warning("[intel-competitors] scan failed", domain=domain, error=str(exc))
                det = SearchVendorResult(
                    domain=domain, search_vendor_status="FETCH_FAILED", note=str(exc)
                )
            return _profile(name, domain, det)

    # Prospect first, then up to N competitors (from F1-hydrated context).
    targets: list[tuple[str, str]] = [
        (context.company_name or context.account_domain, context.account_domain)
    ]
    targets += [(c.name, c.domain) for c in context.competitors[:_MAX_COMPETITORS]]

    profiles = await asyncio.gather(*(scan(n, d) for n, d in targets))

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
            "detection_method": "scout_source_scan",
        }
    }
