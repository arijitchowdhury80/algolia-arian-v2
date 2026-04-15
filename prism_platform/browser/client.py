"""BrowserClient — unified interface for all web fetch operations.

Every module that needs web data calls BrowserClient.fetch().
It tries tiers in order, escalating on failure:

  Tier 1: httpx direct → Jina Reader (free, fast, 60% of sites)
  Tier 2: Playwright stealth (JS + WAF bypass, 90% of sites)
  Tier 3: Commercial service (Browserless/ScrapingBee, 99% of sites)

The module doesn't know or care which tier served the response.
It gets a FetchResult back with the content.

Usage:
    from prism_platform.browser import BrowserClient

    client = BrowserClient()
    result = await client.fetch("https://nike.com/about/leadership")
    if result.success:
        print(result.text)
    else:
        print(f"Failed: {result.error}, tier: {result.tier_used}")
"""

from __future__ import annotations

import structlog

from prism_platform.browser.tier1_direct import fetch_direct, fetch_jina
from prism_platform.browser.tier2_stealth import fetch_stealth
from prism_platform.browser.tier3_service import fetch_browserless, fetch_scrapingbee
from prism_platform.browser.types import FetchOptions, FetchResult

logger = structlog.get_logger(__name__)


class BrowserClient:
    """Tiered web fetch client for PRISM modules.

    Tries tiers in order, escalating when a tier fails (blocked, JS needed,
    error). Stops at the tier configured in FetchOptions.max_tier.

    Args:
        jina_api_key: Optional Jina Reader API key (higher rate limits).
        browserless_api_key: Optional Browserless.io API key (Tier 3).
        scrapingbee_api_key: Optional ScrapingBee API key (Tier 3).
        residential_proxy_url: Optional proxy for Tier 2 stealth browser.
    """

    def __init__(
        self,
        jina_api_key: str = "",
        browserless_api_key: str = "",
        scrapingbee_api_key: str = "",
        residential_proxy_url: str = "",
    ) -> None:
        self._jina_api_key = jina_api_key
        self._browserless_api_key = browserless_api_key
        self._scrapingbee_api_key = scrapingbee_api_key
        self._residential_proxy_url = residential_proxy_url

    async def fetch(
        self,
        url: str,
        options: FetchOptions | None = None,
    ) -> FetchResult:
        """Fetch a URL, trying tiers in order until success.

        Args:
            url: Target URL.
            options: Fetch options. Defaults to standard content extraction settings.

        Returns:
            FetchResult from whichever tier succeeded (or last tier's failure).
        """
        if options is None:
            options = FetchOptions()

        # If caller needs interactive browser, skip straight to Tier 2
        if options.interactive:
            return await self._try_tier2(url, options)

        # If caller explicitly wants JS rendering, skip httpx
        if options.render_js:
            result = await self._try_jina(url, options)
            if result.success:
                return result
            # Jina failed — escalate
            if options.max_tier >= 2:
                return await self._try_tier2(url, options)
            return result

        # Standard flow: httpx → Jina → Tier 2 → Tier 3
        result = await self._try_httpx(url, options)
        if result.success:
            return result

        # httpx failed (blocked, JS-required, error) — try Jina
        logger.info(
            "Tier 1 httpx failed, trying Jina Reader",
            url=url,
            httpx_error=result.error,
            httpx_blocked=result.is_bot_blocked,
        )
        result = await self._try_jina(url, options)
        if result.success:
            return result

        # Jina failed — escalate to Tier 2 if allowed
        if options.max_tier >= 2:
            logger.info(
                "Tier 1 Jina failed, trying Tier 2 stealth browser",
                url=url,
                jina_error=result.error,
            )
            result = await self._try_tier2(url, options)
            if result.success:
                return result

            # Tier 2 failed — escalate to Tier 3 if allowed
            if options.max_tier >= 3:
                logger.info(
                    "Tier 2 failed, trying Tier 3 commercial service",
                    url=url,
                    tier2_error=result.error,
                )
                return await self._try_tier3(url, options)

        return result

    async def fetch_multiple(
        self,
        urls: list[str],
        options: FetchOptions | None = None,
    ) -> list[FetchResult]:
        """Fetch multiple URLs. Returns results in same order as urls.

        Runs sequentially to be polite to target servers.
        For parallel fetching across different domains, use asyncio.gather()
        with individual fetch() calls.
        """
        results = []
        for url in urls:
            result = await self.fetch(url, options)
            results.append(result)
        return results

    # --- Tier dispatch methods ---

    async def _try_httpx(self, url: str, options: FetchOptions) -> FetchResult:
        """Tier 1a: Plain httpx fetch."""
        return await fetch_direct(url, options)

    async def _try_jina(self, url: str, options: FetchOptions) -> FetchResult:
        """Tier 1b: Jina Reader API (JS rendering, basic anti-bot)."""
        return await fetch_jina(url, options, api_key=self._jina_api_key)

    async def _try_tier2(self, url: str, options: FetchOptions) -> FetchResult:
        """Tier 2: Stealth browser (Playwright/Camoufox)."""
        return await fetch_stealth(
            url, options, proxy_url=self._residential_proxy_url
        )

    async def _try_tier3(self, url: str, options: FetchOptions) -> FetchResult:
        """Tier 3: Commercial browser service."""
        # Try Browserless first if key is available
        if self._browserless_api_key:
            result = await fetch_browserless(
                url, options, api_key=self._browserless_api_key
            )
            if result.success:
                return result

        # Fall back to ScrapingBee
        if self._scrapingbee_api_key:
            return await fetch_scrapingbee(
                url, options, api_key=self._scrapingbee_api_key
            )

        # No Tier 3 API keys configured
        logger.warning("No Tier 3 API keys configured — cannot escalate further", url=url)
        from prism_platform.browser.types import FetchTier

        return FetchResult(
            url=url,
            text="",
            html=None,
            status_code=0,
            tier_used=FetchTier.BROWSERLESS,
            is_bot_blocked=False,
            fetch_duration_ms=0,
            error="no_tier3_api_keys_configured",
        )
