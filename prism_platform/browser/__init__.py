"""PRISM shared browser infrastructure — tiered web fetch for all modules.

Usage:
    from prism_platform.browser import BrowserClient, FetchOptions, FetchResult

    client = BrowserClient(jina_api_key="optional")
    result = await client.fetch("https://nike.com/about/leadership")

Tiers:
    1. httpx + Jina Reader (free, fast, handles 60% of sites)
    2. Playwright stealth (JS + WAF bypass, handles 90%) — STUB
    3. Commercial service (Browserless/ScrapingBee, handles 99%) — STUB
"""

from prism_platform.browser.client import BrowserClient
from prism_platform.browser.types import FetchOptions, FetchResult, FetchTier

__all__ = [
    "BrowserClient",
    "FetchOptions",
    "FetchResult",
    "FetchTier",
]
