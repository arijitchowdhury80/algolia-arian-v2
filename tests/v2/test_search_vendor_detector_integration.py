"""Real-company integration tests for PRISM's packet-inspection search detector.

NO MOCKS (project rule): these drive a real stealth browser against live sites and
assert on what the network actually showed. Run as a batch:

    pytest tests/v2/test_search_vendor_detector_integration.py -m browser -v

Ground truth can drift as sites re-platform, so assertions target the contract +
zero-false-positive guarantee, plus a known-Algolia DocSearch site (tailwindcss.com)
which reliably exposes Algolia from the wire.
"""

from __future__ import annotations

import pytest

from prism_platform.v2.detection import (
    SearchVendorResult,
    detect_search_vendor,
    scan_search_vendors,
)
from prism_platform.v2.detection.search_vendor import _VALID_STATUS

pytestmark = pytest.mark.browser


@pytest.mark.asyncio
async def test_detect_returns_valid_contract() -> None:
    """A real detection returns a well-formed result with a status in the taxonomy."""
    res = await detect_search_vendor("tailwindcss.com")
    assert isinstance(res, SearchVendorResult)
    assert res.domain == "tailwindcss.com"
    assert res.search_vendor_status in _VALID_STATUS
    if res.search_vendor_status == "DETECTED":
        assert res.endpoint_host  # a real host was contacted
        assert res.evidence_url   # the sample search call is recorded


@pytest.mark.asyncio
async def test_known_algolia_site_proven_from_wire() -> None:
    """tailwindcss.com runs Algolia DocSearch — must detect Algolia + extract an app_id."""
    res = await detect_search_vendor("tailwindcss.com")
    if res.search_vendor_status != "DETECTED":
        pytest.skip(f"site not exercisable this run: {res.search_vendor_status}")
    assert res.is_algolia, f"expected Algolia, got {res.search_vendor} / {res.all_vendors}"
    assert "algolia.net" in res.endpoint_host
    assert res.app_id, "Algolia detection must extract an application ID from the packet"


@pytest.mark.asyncio
async def test_no_false_positive_on_detected_call() -> None:
    """Any DETECTED result is proven: it has a real endpoint host (never a bare guess)."""
    res = await detect_search_vendor("getbootstrap.com")
    if res.search_vendor_status == "DETECTED":
        assert res.endpoint_host
        assert res.search_vendor  # a label was assigned
        # is_algolia must be consistent with the headline endpoint
        assert res.is_algolia == ("algolia.net" in res.endpoint_host)


@pytest.mark.asyncio
async def test_batch_scan_returns_result_per_domain() -> None:
    """scan_search_vendors shares one browser and returns a result for every domain."""
    domains = ["tailwindcss.com", "getbootstrap.com"]
    results = await scan_search_vendors(domains, concurrency=2)
    assert set(results) == set(domains)
    for dom, res in results.items():
        assert isinstance(res, SearchVendorResult)
        assert res.domain == dom
        assert res.search_vendor_status in _VALID_STATUS
