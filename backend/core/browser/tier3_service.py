"""Tier 3 — Commercial browser-as-a-service (Browserless / ScrapingBee).

Nuclear option for sites that defeat Tier 2. These services manage the
anti-detection arms race full-time — they update when detection methods change.

Supports:
  - Browserless.io — Playwright-compatible API, stealth mode, proxy rotation
  - ScrapingBee — REST API, JS rendering, CAPTCHA solving, proxy rotation

Cost: ~$0.005-0.01 per page. Only used when Tiers 1 and 2 fail.

Current status: STUB — interface defined, implementation pending.
When implemented, add to .env:
  - BROWSERLESS_API_KEY=your_key  (for Browserless.io)
  - SCRAPINGBEE_API_KEY=your_key  (for ScrapingBee)
"""

from __future__ import annotations

import structlog

from core.browser.types import FetchOptions, FetchResult, FetchTier

logger = structlog.get_logger(__name__)


async def fetch_browserless(
    url: str,
    options: FetchOptions,
    api_key: str = "",
) -> FetchResult:
    """Fetch via Browserless.io — managed headless Chrome with stealth.

    NOT YET IMPLEMENTED.

    Args:
        url: Target URL.
        options: Fetch options.
        api_key: Browserless API key.

    Returns:
        FetchResult with error indicating Tier 3 is not yet available.
    """
    logger.warning(
        "Tier 3 Browserless not yet implemented",
        url=url,
    )
    return FetchResult(
        url=url,
        text="",
        html=None,
        status_code=0,
        tier_used=FetchTier.BROWSERLESS,
        is_bot_blocked=False,
        fetch_duration_ms=0,
        error="tier3_browserless_not_implemented",
    )


async def fetch_scrapingbee(
    url: str,
    options: FetchOptions,
    api_key: str = "",
) -> FetchResult:
    """Fetch via ScrapingBee — REST API with JS rendering and CAPTCHA solving.

    NOT YET IMPLEMENTED.

    Args:
        url: Target URL.
        options: Fetch options.
        api_key: ScrapingBee API key.

    Returns:
        FetchResult with error indicating Tier 3 is not yet available.
    """
    logger.warning(
        "Tier 3 ScrapingBee not yet implemented",
        url=url,
    )
    return FetchResult(
        url=url,
        text="",
        html=None,
        status_code=0,
        tier_used=FetchTier.SCRAPINGBEE,
        is_bot_blocked=False,
        fetch_duration_ms=0,
        error="tier3_scrapingbee_not_implemented",
    )
