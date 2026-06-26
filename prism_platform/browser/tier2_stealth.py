"""Tier 2 — Stealth browser via Scout (Crawl4AI / Playwright).

Scout wraps Crawl4AI's Playwright-based crawler with stealth patches and
anti-detection. This tier is invoked by BrowserClient when Tier 1 (httpx +
Jina) fails — JS-rendered pages, Cloudflare/WAF blocks, etc.

PRISM imports ScoutCrawler from the scout.core library directly — no HTTP
overhead. The FastAPI service is for external callers only.

interactive_session remains a stub until the search audit module is built.
"""

from __future__ import annotations

import time

import structlog

from prism_platform.browser.types import FetchOptions, FetchResult, FetchTier

logger = structlog.get_logger(__name__)


async def fetch_stealth(
    url: str,
    options: FetchOptions,
    proxy_url: str = "",
) -> FetchResult:
    """Fetch a URL via Scout (Crawl4AI Playwright stealth browser).

    Uses ScoutCrawler.scrape() with JS enabled. Handles redirects —
    the final URL after any redirect chain is recorded in FetchResult.url.

    Args:
        url: Target URL.
        options: Fetch options (screenshot, timeout, min_content_length).
        proxy_url: Unused — Scout uses Crawl4AI's built-in proxy rotation.

    Returns:
        FetchResult with tier_used=PLAYWRIGHT on success or failure.
    """
    from scout.core import ScoutCrawler
    from scout.core.types import ScrapeRequest

    start = time.monotonic()
    crawler = ScoutCrawler()

    req = ScrapeRequest(
        url=url,
        use_js=True,
        timeout_ms=int(options.timeout * 1000),
    )

    try:
        resp = await crawler.scrape(req)
    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.error("Scout scrape raised exception", url=url, error=str(exc))
        return FetchResult(
            url=url,
            text="",
            status_code=0,
            tier_used=FetchTier.PLAYWRIGHT,
            is_bot_blocked=False,
            fetch_duration_ms=duration_ms,
            error=f"scout_exception: {type(exc).__name__}",
        )

    duration_ms = int((time.monotonic() - start) * 1000)
    final_url = resp.metadata.url if resp.success else url

    if not resp.success:
        logger.info(
            "Scout scrape failed",
            url=url,
            error=resp.error,
            duration_ms=duration_ms,
        )
        return FetchResult(
            url=final_url,
            text="",
            status_code=0,
            tier_used=FetchTier.PLAYWRIGHT,
            is_bot_blocked=False,
            fetch_duration_ms=duration_ms,
            error=resp.error or "scout_scrape_failed",
        )

    content = resp.markdown
    if len(content) < options.min_content_length:
        logger.info(
            "Scout content too short — likely bot challenge",
            url=url,
            content_len=len(content),
            min_required=options.min_content_length,
            duration_ms=duration_ms,
        )
        return FetchResult(
            url=final_url,
            text=content,
            status_code=200,
            tier_used=FetchTier.PLAYWRIGHT,
            is_bot_blocked=True,
            fetch_duration_ms=duration_ms,
            error=f"content_too_short: {len(content)} < {options.min_content_length}",
        )

    logger.info(
        "Scout scrape succeeded",
        url=url,
        final_url=final_url,
        content_len=len(content),
        duration_ms=duration_ms,
    )

    return FetchResult(
        url=final_url,
        text=content,
        html=resp.raw_html or None,
        status_code=200,
        tier_used=FetchTier.PLAYWRIGHT,
        is_bot_blocked=False,
        fetch_duration_ms=duration_ms,
    )


async def interactive_session(
    url: str,
    options: FetchOptions,
    actions: list[dict[str, object]],
    proxy_url: str = "",
) -> FetchResult:
    """Run an interactive browser session — type queries, click, screenshot.

    Required for the search audit module. NOT YET IMPLEMENTED.
    """
    logger.warning(
        "Tier 2 interactive session not yet implemented",
        url=url,
        action_count=len(actions),
    )
    return FetchResult(
        url=url,
        text="",
        status_code=0,
        tier_used=FetchTier.PLAYWRIGHT,
        is_bot_blocked=False,
        fetch_duration_ms=0,
        error="tier2_interactive_not_implemented",
    )
