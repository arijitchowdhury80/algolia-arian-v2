"""Tier 1 — Direct HTTP fetch + Jina Reader fallback.

Strategy:
  1. Try httpx direct fetch (free, fast, no JS rendering)
  2. If blocked or JS-required: fall back to Jina Reader API
     (handles JS rendering + basic anti-bot, free tier available)

This tier handles ~60% of corporate websites. The remaining 40%
(JS-heavy sites behind Cloudflare) escalate to Tier 2.
"""

from __future__ import annotations

import re
import time

import httpx
import structlog

from core.browser.detector import detect_bot_block, detect_content_quality
from core.browser.types import FetchOptions, FetchResult, FetchTier

logger = structlog.get_logger(__name__)

# Default user agent — looks like a real Chrome browser
_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# HTML tag stripping
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")

JINA_READER_BASE = "https://r.jina.ai"


def _strip_html(html: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    text = _TAG_RE.sub(" ", html)
    text = _SPACE_RE.sub(" ", text)
    return text.strip()


async def fetch_direct(url: str, options: FetchOptions) -> FetchResult:
    """Fetch a URL via plain httpx. No JS rendering.

    Args:
        url: Target URL.
        options: Fetch options (timeout, user_agent, etc.)

    Returns:
        FetchResult — check .success to see if it worked.
    """
    start = time.monotonic()
    ua = options.user_agent or _DEFAULT_UA

    try:
        async with httpx.AsyncClient(
            timeout=options.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        ) as client:
            response = await client.get(url)
            duration_ms = int((time.monotonic() - start) * 1000)

            raw_html = response.text
            text = _strip_html(raw_html)
            is_blocked = detect_bot_block(text, response.status_code)

            if not is_blocked and not detect_content_quality(text, options.min_content_length):
                # Got a 200 but content is empty/garbage — likely JS app that didn't render
                logger.info(
                    "Tier 1 httpx: page content too thin (likely JS-rendered)",
                    url=url,
                    text_length=len(text),
                )
                return FetchResult(
                    url=str(response.url),
                    text=text,
                    html=raw_html,
                    status_code=response.status_code,
                    tier_used=FetchTier.HTTPX,
                    is_bot_blocked=False,
                    fetch_duration_ms=duration_ms,
                    error="content_too_thin",
                )

            return FetchResult(
                url=str(response.url),
                text=text,
                html=raw_html,
                status_code=response.status_code,
                tier_used=FetchTier.HTTPX,
                is_bot_blocked=is_blocked,
                fetch_duration_ms=duration_ms,
                error=None if not is_blocked else "bot_blocked",
            )

    except (httpx.RequestError, httpx.TimeoutException) as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.warning("Tier 1 httpx: request failed", url=url, error=str(exc))
        return FetchResult(
            url=url,
            text="",
            html=None,
            status_code=0,
            tier_used=FetchTier.HTTPX,
            is_bot_blocked=False,
            fetch_duration_ms=duration_ms,
            error=str(exc),
        )


async def fetch_jina(url: str, options: FetchOptions, api_key: str = "") -> FetchResult:
    """Fetch a URL via Jina Reader API — handles JS rendering + basic anti-bot.

    Jina Reader renders the page server-side and returns clean markdown/text.
    Free tier available (no API key required, rate-limited).
    With API key: higher rate limits.

    Args:
        url: Target URL.
        options: Fetch options.
        api_key: Optional Jina API key for higher rate limits.

    Returns:
        FetchResult with rendered text content.
    """
    start = time.monotonic()
    jina_url = f"{JINA_READER_BASE}/{url}"

    headers: dict[str, str] = {
        "Accept": "text/plain",
        "X-Return-Format": "text",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(
            timeout=max(options.timeout, 30.0),  # Jina needs more time for JS rendering
            follow_redirects=True,
            headers=headers,
        ) as client:
            response = await client.get(jina_url)
            duration_ms = int((time.monotonic() - start) * 1000)

            text = response.text.strip()

            # Jina returns plain text — no HTML stripping needed
            # But check for Jina-level errors
            if response.status_code != 200:
                logger.warning(
                    "Tier 1 Jina: non-200 response",
                    url=url,
                    jina_status=response.status_code,
                )
                return FetchResult(
                    url=url,
                    text=text,
                    html=None,
                    status_code=response.status_code,
                    tier_used=FetchTier.JINA,
                    is_bot_blocked=False,
                    fetch_duration_ms=duration_ms,
                    error=f"jina_status_{response.status_code}",
                )

            # Check if Jina itself hit a bot block
            is_blocked = detect_bot_block(text, 200)

            return FetchResult(
                url=url,
                text=text,
                html=None,
                status_code=200,
                tier_used=FetchTier.JINA,
                is_bot_blocked=is_blocked,
                fetch_duration_ms=duration_ms,
                error=None if not is_blocked else "bot_blocked_via_jina",
            )

    except (httpx.RequestError, httpx.TimeoutException) as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.warning("Tier 1 Jina: request failed", url=url, error=str(exc))
        return FetchResult(
            url=url,
            text="",
            html=None,
            status_code=0,
            tier_used=FetchTier.JINA,
            is_bot_blocked=False,
            fetch_duration_ms=duration_ms,
            error=str(exc),
        )
