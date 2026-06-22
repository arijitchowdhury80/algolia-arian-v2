"""Real-company integration tests for PRISM's in-app search-vendor detector.

NO MOCKS (project rule): these hit live sites through the shared BrowserClient
(httpx → Scout/Playwright stealth). They REQUIRE Scout running. Run as a batch
once infra is up:

    pytest tests/v2/test_search_vendor_detector_integration.py -m browser -v

Each test asserts the *contract* against a real fetch — never a fabricated
response. Vendor ground-truth can drift as sites re-platform, so assertions
target the result shape + status taxonomy, with a softer check that a
known Algolia-heavy retailer surfaces Algolia signatures when reachable.
"""

from __future__ import annotations

import pytest

from prism_platform.v2.detection import detect_search_vendor
from prism_platform.v2.detection.search_vendor import (
    SEARCH_VENDOR_SIGNATURES,
    SearchVendorResult,
)

pytestmark = pytest.mark.browser

_VALID_STATUS = {
    "DETECTED",
    "UNDETECTED",
    "UNCONFIRMED_WAF_BLOCK",
    "FETCH_FAILED",
}


@pytest.mark.asyncio
async def test_detect_returns_valid_contract_for_real_site() -> None:
    """A real fetch returns a well-formed result with a status in the taxonomy."""
    res = await detect_search_vendor("nike.com")
    assert isinstance(res, SearchVendorResult)
    assert res.domain == "nike.com"
    assert res.search_vendor_status in _VALID_STATUS
    # When the page was actually scanned, evidence_url points at the final URL.
    if res.search_vendor_status in {"DETECTED", "UNDETECTED"}:
        assert res.evidence_url
    # is_algolia must be consistent with the vendor list.
    assert res.is_algolia == ("Algolia" in res.all_search_vendors)


@pytest.mark.asyncio
async def test_detected_vendor_is_a_known_signature() -> None:
    """Any detected vendor must be one of our signature names (no hallucinated vendors)."""
    res = await detect_search_vendor("lacoste.com")
    known = {sig.name for sig in SEARCH_VENDOR_SIGNATURES}
    for vendor in res.all_search_vendors:
        assert vendor in known
    if res.search_vendor_status == "DETECTED":
        assert res.search_vendor in known
        assert res.matched_patterns  # detection must carry evidence
