"""PRISM in-app technology detection — the BuiltWith replacement.

Deterministic, Scout-based detection of a website's search vendor and commerce
platform. No paid third-party API (BuiltWith is out — no budget).
"""

from prism_platform.v2.detection.search_vendor import (
    SearchVendorResult,
    detect_search_vendor,
)

__all__ = ["SearchVendorResult", "detect_search_vendor"]
