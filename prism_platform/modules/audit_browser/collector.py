"""Audit Browser collector -- Playwright browser automation for live search testing.

Drives a real browser to:
1. Navigate to a prospect's website
2. Find the search bar via CSS selectors (with fallbacks)
3. Execute test queries from intel-queries output
4. Capture screenshots, response times, result counts, NLP features
5. Run mobile viewport tests for 3 key queries
6. Intercept network requests to detect search API providers
7. Test competitor sites with a subset of queries

Since Playwright may not be available in all environments, all Playwright
imports are wrapped in try/except for graceful degradation.
"""

from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Any

import structlog

from prism_platform.modules.audit_browser.schemas import (
    COMMON_SEARCH_SELECTORS,
    MOBILE_VIEWPORT,
)

logger = structlog.get_logger(__name__)

# Try to import Playwright -- graceful degradation if not installed
try:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Page,
        async_playwright,
    )

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("[BrowserCollector] playwright not installed -- browser tests disabled")

# Search provider detection patterns in network URLs
PROVIDER_PATTERNS: dict[str, list[str]] = {
    "Algolia": ["algolia.net", "algolianet.com", "algolia.io"],
    "Elasticsearch": ["elastic", "_search", "elasticsearch"],
    "Coveo": ["coveo.com", "cloud.coveo"],
    "Bloomreach": ["bloomreach", "brx.io"],
    "SearchSpring": ["searchspring.net", "searchspring.io"],
    "Klevu": ["klevu.com", "klarnaservices"],
    "Constructor.io": ["constructor.io", "cnstrc.com"],
    "Lucidworks": ["lucidworks", "fusion.lucidworks"],
    "Yext": ["yextpages.net", "answers.yext"],
    "Google CSE": ["googleapis.com/customsearch", "cse.google"],
    "Swiftype": ["swiftype.com"],
    "Typesense": ["typesense"],
    "Meilisearch": ["meilisearch"],
}

# User agent string for stealth browsing
STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# Timeouts
QUERY_TIMEOUT_MS = 30_000  # 30 seconds per query
TOTAL_TIMEOUT_SECONDS = 600  # 10 minutes total
NAVIGATION_TIMEOUT_MS = 30_000  # 30 seconds for page load
SCREENSHOT_QUALITY = 80  # JPEG quality for screenshots


def detect_provider_from_url(url: str) -> str | None:
    """Detect a search provider from a network request URL.

    Args:
        url: The full URL of the intercepted request.

    Returns:
        Provider name if detected, None otherwise.
    """
    url_lower = url.lower()
    for provider, patterns in PROVIDER_PATTERNS.items():
        for pattern in patterns:
            if pattern in url_lower:
                return provider
    return None


def is_search_api_request(url: str, method: str) -> bool:
    """Determine if a network request is likely a search API call.

    Args:
        url: The full URL of the request.
        method: HTTP method (GET, POST, etc.).

    Returns:
        True if the request looks like a search API call.
    """
    url_lower = url.lower()
    search_indicators = [
        "search",
        "query",
        "suggest",
        "autocomplete",
        "typeahead",
        "instant",
        "find",
        "/s?",
        "/s/",
    ]
    # Check for known provider patterns
    if detect_provider_from_url(url) is not None:
        return True
    # Check for search-related URL patterns
    return any(indicator in url_lower for indicator in search_indicators)


class BrowserCollector:
    """Drives a real browser to test search experiences on prospect and competitor sites."""

    def __init__(self) -> None:
        self._intercepted_requests: list[dict[str, Any]] = []

    async def collect_all(
        self,
        domain: str,
        audit_id: str,
        queries: list[dict[str, str]],
        competitor_domains: list[dict[str, str]] | None = None,
        search_bar_selector_hint: str | None = None,
    ) -> dict[str, Any]:
        """Run full browser-based search testing.

        Args:
            domain: Prospect website domain to test.
            audit_id: Audit ID for screenshot storage.
            queries: List of query dicts with 'query' and 'query_type' keys.
            competitor_domains: Optional list of dicts with 'domain' and 'company_name'.
            search_bar_selector_hint: Optional CSS selector hint from intel-company.

        Returns:
            Dict with keys: prospect_query_results, mobile_test_results,
            network_interceptions, search_bar_found, search_bar_selector,
            detected_search_provider, was_blocked, block_details,
            competitor_results, total_queries_executed, total_screenshots.
        """
        logger.info(
            "[BrowserCollector] collect_all started",
            domain=domain,
            audit_id=audit_id,
            query_count=len(queries),
            competitor_count=len(competitor_domains or []),
        )

        if not PLAYWRIGHT_AVAILABLE:
            logger.error("[BrowserCollector] Playwright not available -- returning empty results")
            return self._empty_result(domain)

        start_time = time.monotonic()
        screenshot_dir = self._ensure_screenshot_dir(audit_id)

        results: dict[str, Any] = {
            "prospect_query_results": [],
            "mobile_test_results": [],
            "network_interceptions": [],
            "search_bar_found": False,
            "search_bar_selector": None,
            "detected_search_provider": None,
            "was_blocked": False,
            "block_details": None,
            "competitor_results": [],
            "total_queries_executed": 0,
            "total_screenshots": 0,
        }

        try:
            async with async_playwright() as pw:
                logger.info("[BrowserCollector] launching Chromium browser", headless=True)
                browser = await pw.chromium.launch(headless=True)
                logger.info("[BrowserCollector] browser launched successfully")
                try:
                    # Test the prospect
                    prospect_results = await self._test_site(
                        browser=browser,
                        domain=domain,
                        queries=queries,
                        screenshot_dir=screenshot_dir,
                        prefix="prospect",
                        search_bar_hint=search_bar_selector_hint,
                        start_time=start_time,
                    )
                    results.update(prospect_results)

                    # Test competitors (top 3, 5 queries each)
                    if competitor_domains and not self._time_exceeded(start_time):
                        comp_results = await self._test_competitors(
                            browser=browser,
                            competitors=competitor_domains[:3],
                            queries=queries[:5],
                            screenshot_dir=screenshot_dir,
                            start_time=start_time,
                        )
                        results["competitor_results"] = comp_results

                    # Aggregate counts
                    results["total_queries_executed"] = (
                        len(results["prospect_query_results"])
                        + len(results["mobile_test_results"])
                        + sum(
                            len(c.get("query_results", [])) for c in results["competitor_results"]
                        )
                    )
                    results["total_screenshots"] = self._count_screenshots(results)

                    # Detect primary provider from network interceptions
                    results["detected_search_provider"] = self._detect_primary_provider(
                        results["network_interceptions"]
                    )

                finally:
                    logger.info("[BrowserCollector] closing browser")
                    await browser.close()
                    logger.info("[BrowserCollector] browser closed")

        except Exception as exc:
            logger.exception(
                "[BrowserCollector] browser automation failed",
                domain=domain,
                error=str(exc),
            )
            results["was_blocked"] = True
            results["block_details"] = f"Browser automation error: {type(exc).__name__}: {exc}"

        elapsed_s = round(time.monotonic() - start_time, 2)
        logger.info(
            "[BrowserCollector] collect_all completed",
            domain=domain,
            total_queries=results["total_queries_executed"],
            total_screenshots=results["total_screenshots"],
            search_bar_found=results["search_bar_found"],
            provider=results["detected_search_provider"],
            was_blocked=results["was_blocked"],
            competitor_count=len(results["competitor_results"]),
            network_interceptions=len(results["network_interceptions"]),
            elapsed_seconds=elapsed_s,
        )

        return results

    async def _test_site(
        self,
        browser: Browser,
        domain: str,
        queries: list[dict[str, str]],
        screenshot_dir: Path,
        prefix: str,
        search_bar_hint: str | None,
        start_time: float,
    ) -> dict[str, Any]:
        """Test a single site with queries.

        Args:
            browser: Playwright browser instance.
            domain: Domain to test.
            queries: List of query dicts.
            screenshot_dir: Directory for screenshots.
            prefix: Filename prefix for screenshots.
            search_bar_hint: Optional CSS selector hint.
            start_time: Start time for total timeout check.

        Returns:
            Dict with prospect results.
        """
        results: dict[str, Any] = {
            "prospect_query_results": [],
            "mobile_test_results": [],
            "network_interceptions": [],
            "search_bar_found": False,
            "search_bar_selector": None,
            "was_blocked": False,
            "block_details": None,
        }

        try:
            context = await self._create_stealth_context(browser)
            try:
                page = await context.new_page()

                # Set up network interception
                intercepted: list[dict[str, Any]] = []
                page.on("request", lambda req: self._on_request(req, intercepted))

                # Navigate to the site
                blocked = await self._navigate_to_site(page, domain)
                if blocked:
                    results["was_blocked"] = True
                    results["block_details"] = f"Site blocked access: {domain}"
                    return results

                # Find the search bar
                selector = await self._find_search_bar(page, search_bar_hint)
                if selector:
                    results["search_bar_found"] = True
                    results["search_bar_selector"] = selector
                    logger.info(
                        "[BrowserCollector] search bar found",
                        domain=domain,
                        selector=selector,
                    )
                else:
                    logger.warning(
                        "[BrowserCollector] no search bar found",
                        domain=domain,
                    )
                    results["search_bar_found"] = False
                    return results

                # Execute queries
                for i, query_data in enumerate(queries):
                    if self._time_exceeded(start_time):
                        logger.warning(
                            "[BrowserCollector] total timeout exceeded, stopping queries",
                            domain=domain,
                            queries_completed=i,
                        )
                        break

                    query_result = await self._execute_query(
                        page=page,
                        domain=domain,
                        query_text=query_data.get("query", ""),
                        query_type=query_data.get("query_type", "unknown"),
                        selector=selector,
                        screenshot_dir=screenshot_dir,
                        screenshot_name=f"{prefix}_query_{i:02d}",
                    )
                    results["prospect_query_results"].append(query_result)

                # Mobile viewport tests (first 3 queries)
                mobile_queries = queries[:3]
                for i, query_data in enumerate(mobile_queries):
                    if self._time_exceeded(start_time):
                        break

                    mobile_result = await self._execute_mobile_query(
                        browser=browser,
                        domain=domain,
                        query_text=query_data.get("query", ""),
                        screenshot_dir=screenshot_dir,
                        screenshot_name=f"{prefix}_mobile_{i:02d}",
                        search_bar_hint=selector,
                    )
                    results["mobile_test_results"].append(mobile_result)

                # Convert intercepted requests to NetworkInterception dicts
                results["network_interceptions"] = [
                    {
                        "url": req["url"],
                        "method": req["method"],
                        "provider_detected": detect_provider_from_url(req["url"]),
                        "is_search_api": is_search_api_request(req["url"], req["method"]),
                    }
                    for req in intercepted
                    if is_search_api_request(req["url"], req["method"])
                ]

            finally:
                await context.close()

        except Exception as exc:
            logger.exception(
                "[BrowserCollector] site test failed",
                domain=domain,
                error=str(exc),
            )
            results["was_blocked"] = True
            results["block_details"] = f"Test error: {type(exc).__name__}: {exc}"

        return results

    async def _test_competitors(
        self,
        browser: Browser,
        competitors: list[dict[str, str]],
        queries: list[dict[str, str]],
        screenshot_dir: Path,
        start_time: float,
    ) -> list[dict[str, Any]]:
        """Test competitor sites with a subset of queries.

        Args:
            browser: Playwright browser instance.
            competitors: List of competitor dicts with 'domain' and 'company_name'.
            queries: Queries to run (typically first 5).
            screenshot_dir: Directory for screenshots.
            start_time: Start time for total timeout.

        Returns:
            List of competitor result dicts.
        """
        competitor_results: list[dict[str, Any]] = []
        logger.info(
            "[BrowserCollector] starting competitor testing",
            competitor_count=len(competitors),
            queries_per_competitor=min(5, len(queries)),
        )

        for comp in competitors:
            if self._time_exceeded(start_time):
                logger.warning("[BrowserCollector] timeout -- skipping remaining competitors")
                break

            comp_domain = comp.get("domain", "")
            comp_name = comp.get("company_name", comp_domain)

            logger.info(
                "[BrowserCollector] testing competitor",
                competitor=comp_name,
                domain=comp_domain,
            )

            try:
                context = await self._create_stealth_context(browser)
                try:
                    page = await context.new_page()
                    intercepted: list[dict[str, Any]] = []
                    _intercepted = intercepted  # bind for closure
                    page.on("request", lambda req, s=_intercepted: self._on_request(req, s))

                    blocked = await self._navigate_to_site(page, comp_domain)
                    if blocked:
                        logger.warning(
                            "[BrowserCollector] competitor blocked",
                            domain=comp_domain,
                        )
                        continue

                    selector = await self._find_search_bar(page, None)
                    if not selector:
                        logger.warning(
                            "[BrowserCollector] no search bar on competitor",
                            domain=comp_domain,
                        )
                        continue

                    query_results: list[dict[str, Any]] = []
                    for i, q in enumerate(queries[:5]):
                        if self._time_exceeded(start_time):
                            break
                        qr = await self._execute_query(
                            page=page,
                            domain=comp_domain,
                            query_text=q.get("query", ""),
                            query_type=q.get("query_type", "unknown"),
                            selector=selector,
                            screenshot_dir=screenshot_dir,
                            screenshot_name=f"comp_{comp_domain.replace('.', '_')}_{i:02d}",
                        )
                        query_results.append(qr)

                    competitor_results.append(
                        {
                            "company_name": comp_name,
                            "domain": comp_domain,
                            "query_results": query_results,
                            "dimension_scores": [],  # Populated by enricher
                        }
                    )
                    logger.info(
                        "[BrowserCollector] competitor test completed",
                        competitor=comp_name,
                        domain=comp_domain,
                        queries_executed=len(query_results),
                    )

                finally:
                    await context.close()

            except Exception as exc:
                logger.error(
                    "[BrowserCollector] competitor test failed",
                    domain=comp_domain,
                    error=str(exc),
                )

        return competitor_results

    async def _create_stealth_context(self, browser: Browser) -> BrowserContext:
        """Create a browser context with stealth settings.

        Args:
            browser: Playwright browser instance.

        Returns:
            Configured BrowserContext with stealth user-agent and webdriver disabled.
        """
        context = await browser.new_context(
            user_agent=STEALTH_USER_AGENT,
            viewport={"width": 1440, "height": 900},
            java_script_enabled=True,
            bypass_csp=True,
        )
        # Disable webdriver detection
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return context

    async def _navigate_to_site(self, page: Page, domain: str) -> bool:
        """Navigate to a site and check if blocked.

        Args:
            page: Playwright page instance.
            domain: Domain to navigate to.

        Returns:
            True if the site appears to have blocked the browser.
        """
        url = f"https://{domain}"
        logger.info(
            "[BrowserCollector] navigating to site", url=url, timeout_ms=NAVIGATION_TIMEOUT_MS
        )
        nav_start = time.monotonic()
        try:
            response = await page.goto(
                url, timeout=NAVIGATION_TIMEOUT_MS, wait_until="domcontentloaded"
            )
            nav_ms = round((time.monotonic() - nav_start) * 1000)
            logger.info(
                "[BrowserCollector] navigation completed",
                url=url,
                status=response.status if response else None,
                duration_ms=nav_ms,
            )
            if response and response.status in (403, 429, 503):
                logger.warning(
                    "[BrowserCollector] possible block detected",
                    domain=domain,
                    status=response.status,
                )
                # Check for common WAF challenge pages
                content = await page.content()
                block_indicators = [
                    "captcha",
                    "challenge",
                    "blocked",
                    "access denied",
                    "cloudflare",
                    "rate limit",
                    "bot detection",
                ]
                content_lower = content.lower()
                if any(indicator in content_lower for indicator in block_indicators):
                    matched = [i for i in block_indicators if i in content_lower]
                    logger.warning(
                        "[BrowserCollector] WAF/bot detection triggered",
                        domain=domain,
                        status=response.status,
                        matched_indicators=matched,
                    )
                    return True
            return False

        except Exception as exc:
            logger.error(
                "[BrowserCollector] navigation failed",
                domain=domain,
                error=str(exc),
            )
            return True

    async def _find_search_bar(
        self,
        page: Page,
        hint: str | None,
    ) -> str | None:
        """Locate the search bar on the page.

        Tries the hint selector first, then falls back to common selectors,
        then tries clicking search icons, then navigates to /search.

        Args:
            page: Playwright page instance.
            hint: Optional CSS selector hint from intel-company.

        Returns:
            CSS selector that matched, or None if not found.
        """
        # Try the hint first
        if hint:
            try:
                element = await page.query_selector(hint)
                if element and await element.is_visible():
                    return hint
            except Exception:
                pass

        # Try common selectors
        for selector in COMMON_SEARCH_SELECTORS:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    return selector
            except Exception:
                continue

        # Try clicking a search icon to reveal the input
        search_icon_selectors = [
            'button[aria-label*="search" i]',
            'a[aria-label*="search" i]',
            ".search-icon",
            ".search-toggle",
            '[data-action="search"]',
            'svg[class*="search"]',
        ]
        for icon_selector in search_icon_selectors:
            try:
                icon = await page.query_selector(icon_selector)
                if icon and await icon.is_visible():
                    await icon.click()
                    await page.wait_for_timeout(1000)
                    # Re-check common selectors after click
                    for selector in COMMON_SEARCH_SELECTORS:
                        try:
                            element = await page.query_selector(selector)
                            if element and await element.is_visible():
                                return selector
                        except Exception:
                            continue
            except Exception:
                continue

        # Try navigating to /search
        try:
            current_url = page.url
            for search_path in ["/search", "/s"]:
                try:
                    await page.goto(
                        f"{current_url.rstrip('/')}{search_path}",
                        timeout=10_000,
                        wait_until="domcontentloaded",
                    )
                    for selector in COMMON_SEARCH_SELECTORS:
                        try:
                            element = await page.query_selector(selector)
                            if element and await element.is_visible():
                                return selector
                        except Exception:
                            continue
                except Exception:
                    continue
        except Exception:
            pass

        return None

    async def _execute_query(
        self,
        page: Page,
        domain: str,
        query_text: str,
        query_type: str,
        selector: str,
        screenshot_dir: Path,
        screenshot_name: str,
    ) -> dict[str, Any]:
        """Execute a single search query and capture results.

        Args:
            page: Playwright page instance.
            domain: Domain being tested.
            query_text: The search query to type.
            query_type: Classification of the query.
            selector: CSS selector for the search bar.
            screenshot_dir: Directory for screenshot storage.
            screenshot_name: Base name for the screenshot file.

        Returns:
            Dict matching QueryResult fields.
        """
        result: dict[str, Any] = {
            "query": query_text,
            "query_type": query_type,
            "response_time_ms": 0,
            "result_count": 0,
            "screenshot_path": None,
            "has_autocomplete": False,
            "has_did_you_mean": False,
            "has_facets": False,
            "has_zero_result_page": False,
            "detected_search_provider": None,
            "notes": "",
        }

        logger.debug(
            "[BrowserCollector] executing query",
            domain=domain,
            query=query_text,
            query_type=query_type,
        )

        try:
            # Clear and focus the search bar
            search_input = await page.query_selector(selector)
            if not search_input:
                result["notes"] = "Search bar not found on page"
                return result

            await search_input.click()
            await search_input.fill("")

            # Type the query character by character to trigger autocomplete
            start_ms = time.monotonic_ns() // 1_000_000
            await page.type(selector, query_text, delay=50)

            # Wait a moment for autocomplete suggestions
            await page.wait_for_timeout(1500)

            # Check for autocomplete
            autocomplete_selectors = [
                '[role="listbox"]',
                '[role="option"]',
                ".autocomplete",
                ".suggestions",
                ".search-suggestions",
                ".tt-menu",
                ".aa-Panel",
                ".ais-Hits",
            ]
            for ac_sel in autocomplete_selectors:
                try:
                    ac_element = await page.query_selector(ac_sel)
                    if ac_element and await ac_element.is_visible():
                        result["has_autocomplete"] = True
                        break
                except Exception:
                    continue

            # Press Enter to submit
            await page.press(selector, "Enter")

            # Wait for results
            try:
                await page.wait_for_load_state("networkidle", timeout=QUERY_TIMEOUT_MS)
            except Exception:
                # Timeout waiting for network idle -- continue anyway
                await page.wait_for_timeout(3000)

            end_ms = time.monotonic_ns() // 1_000_000
            result["response_time_ms"] = end_ms - start_ms

            # Detect NLP features on the results page
            result["has_did_you_mean"] = await self._detect_did_you_mean(page)
            result["has_facets"] = await self._detect_facets(page)
            result["result_count"] = await self._count_results(page)
            result["has_zero_result_page"] = result["result_count"] == 0

            # Capture screenshot
            screenshot_path = screenshot_dir / f"{screenshot_name}.png"
            try:
                await page.screenshot(path=str(screenshot_path), full_page=False)
                result["screenshot_path"] = str(screenshot_path)
                file_size = (
                    os.path.getsize(str(screenshot_path))
                    if os.path.exists(str(screenshot_path))
                    else 0
                )
                logger.debug(
                    "[BrowserCollector] screenshot captured",
                    path=str(screenshot_path),
                    size_bytes=file_size,
                    domain=domain,
                    query=query_text,
                )
            except Exception as exc:
                logger.warning(
                    "[BrowserCollector] screenshot failed",
                    domain=domain,
                    query=query_text,
                    error=str(exc),
                )

            logger.info(
                "[BrowserCollector] query executed",
                domain=domain,
                query=query_text,
                response_time_ms=result["response_time_ms"],
                result_count=result["result_count"],
                has_autocomplete=result["has_autocomplete"],
            )

        except Exception as exc:
            logger.error(
                "[BrowserCollector] query execution failed",
                domain=domain,
                query=query_text,
                error=str(exc),
            )
            result["notes"] = f"Query failed: {type(exc).__name__}: {exc}"

        return result

    async def _execute_mobile_query(
        self,
        browser: Browser,
        domain: str,
        query_text: str,
        screenshot_dir: Path,
        screenshot_name: str,
        search_bar_hint: str | None,
    ) -> dict[str, Any]:
        """Execute a query in a mobile viewport.

        Args:
            browser: Playwright browser instance.
            domain: Domain to test.
            query_text: The search query.
            screenshot_dir: Directory for screenshots.
            screenshot_name: Base name for screenshot.
            search_bar_hint: CSS selector for the search bar.

        Returns:
            Dict matching MobileTestResult fields.
        """
        result: dict[str, Any] = {
            "query": query_text,
            "viewport": f"{MOBILE_VIEWPORT['width']}x{MOBILE_VIEWPORT['height']}",
            "screenshot_path": None,
            "response_time_ms": 0,
            "notes": "",
        }

        logger.info(
            "[BrowserCollector] switching to mobile viewport",
            domain=domain,
            viewport=f"{MOBILE_VIEWPORT['width']}x{MOBILE_VIEWPORT['height']}",
            query=query_text,
        )

        try:
            context = await browser.new_context(
                user_agent=STEALTH_USER_AGENT.replace(
                    "Macintosh; Intel Mac OS X", "iPhone; CPU iPhone OS 17_0 like Mac OS X"
                ),
                viewport=MOBILE_VIEWPORT,
                is_mobile=True,
                has_touch=True,
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            try:
                page = await context.new_page()
                await page.goto(
                    f"https://{domain}",
                    timeout=NAVIGATION_TIMEOUT_MS,
                    wait_until="domcontentloaded",
                )

                selector = await self._find_search_bar(page, search_bar_hint)
                if not selector:
                    result["notes"] = "Search bar not found on mobile viewport"
                    return result

                search_input = await page.query_selector(selector)
                if not search_input:
                    result["notes"] = "Search input element not accessible on mobile"
                    return result

                await search_input.click()
                start_ms = time.monotonic_ns() // 1_000_000
                await page.type(selector, query_text, delay=50)
                await page.press(selector, "Enter")

                try:
                    await page.wait_for_load_state("networkidle", timeout=QUERY_TIMEOUT_MS)
                except Exception:
                    await page.wait_for_timeout(3000)

                end_ms = time.monotonic_ns() // 1_000_000
                result["response_time_ms"] = end_ms - start_ms

                # Screenshot
                screenshot_path = screenshot_dir / f"{screenshot_name}.png"
                try:
                    await page.screenshot(path=str(screenshot_path), full_page=False)
                    result["screenshot_path"] = str(screenshot_path)
                except Exception as exc:
                    logger.warning(
                        "[BrowserCollector] mobile screenshot failed",
                        error=str(exc),
                    )

            finally:
                await context.close()

        except Exception as exc:
            logger.error(
                "[BrowserCollector] mobile query failed",
                domain=domain,
                query=query_text,
                error=str(exc),
            )
            result["notes"] = f"Mobile test failed: {type(exc).__name__}: {exc}"

        return result

    async def _detect_did_you_mean(self, page: Page) -> bool:
        """Check if a 'did you mean' correction is shown on the results page.

        Args:
            page: Playwright page instance on the results page.

        Returns:
            True if a did-you-mean suggestion is detected.
        """
        try:
            selectors = [
                ".did-you-mean",
                ".spell-correction",
                ".search-correction",
                '[data-testid="did-you-mean"]',
            ]
            for sel in selectors:
                element = await page.query_selector(sel)
                if element and await element.is_visible():
                    return True

            # Check text content for common patterns
            content = await page.content()
            content_lower = content.lower()
            patterns = ["did you mean", "showing results for", "search instead for"]
            return any(p in content_lower for p in patterns)

        except Exception:
            return False

    async def _detect_facets(self, page: Page) -> bool:
        """Check if faceted navigation / filters are shown.

        Args:
            page: Playwright page instance on the results page.

        Returns:
            True if facets/filters are detected.
        """
        try:
            selectors = [
                ".facets",
                ".filters",
                ".refinements",
                '[role="navigation"]',
                ".ais-RefinementList",
                ".ais-HierarchicalMenu",
                '[data-testid="facets"]',
                '[data-testid="filters"]',
                ".filter-panel",
                ".sidebar-filters",
            ]
            for sel in selectors:
                element = await page.query_selector(sel)
                if element and await element.is_visible():
                    return True
            return False

        except Exception:
            return False

    async def _count_results(self, page: Page) -> int:
        """Count the number of search results on the page.

        Args:
            page: Playwright page instance on the results page.

        Returns:
            Number of results detected, 0 if none found.
        """
        try:
            result_selectors = [
                ".search-result",
                ".product-card",
                ".result-item",
                '[data-testid="search-result"]',
                ".ais-Hits-item",
                ".product-tile",
                ".search-results-item",
                "article.product",
                ".grid-item",
            ]
            for sel in result_selectors:
                elements = await page.query_selector_all(sel)
                if elements:
                    return len(elements)

            # Fallback: look for a result count text
            count_selectors = [
                ".result-count",
                ".search-count",
                ".total-results",
                '[data-testid="result-count"]',
            ]
            for sel in count_selectors:
                element = await page.query_selector(sel)
                if element:
                    text = await element.text_content()
                    if text:
                        import re

                        numbers = re.findall(r"\d+", text)
                        if numbers:
                            return int(numbers[0])

            return 0

        except Exception:
            return 0

    def _on_request(self, request: Any, storage: list[dict[str, Any]]) -> None:
        """Callback for network request interception.

        Args:
            request: Playwright request object.
            storage: List to append intercepted request data to.
        """
        try:
            url = request.url
            method = request.method
            resource_type = request.resource_type
            if resource_type in ("xhr", "fetch"):
                storage.append(
                    {
                        "url": url,
                        "method": method,
                        "resource_type": resource_type,
                    }
                )
                provider = detect_provider_from_url(url)
                if provider:
                    logger.info(
                        "[BrowserCollector] search provider detected via network",
                        provider=provider,
                        url_pattern=url[:120],
                        method=method,
                    )
        except Exception:
            pass

    def _detect_primary_provider(self, interceptions: list[dict[str, Any]]) -> str | None:
        """Detect the primary search provider from all interceptions.

        Args:
            interceptions: List of NetworkInterception dicts.

        Returns:
            Most frequently detected provider name, or None.
        """
        providers: dict[str, int] = {}
        for interception in interceptions:
            provider = interception.get("provider_detected")
            if provider:
                providers[provider] = providers.get(provider, 0) + 1

        if not providers:
            return None

        return max(providers, key=providers.get)  # type: ignore[arg-type]

    def _count_screenshots(self, results: dict[str, Any]) -> int:
        """Count total screenshots in results.

        Args:
            results: The full results dict.

        Returns:
            Total number of non-None screenshot paths.
        """
        count = 0
        for qr in results.get("prospect_query_results", []):
            if qr.get("screenshot_path"):
                count += 1
        for mr in results.get("mobile_test_results", []):
            if mr.get("screenshot_path"):
                count += 1
        for cr in results.get("competitor_results", []):
            for qr in cr.get("query_results", []):
                if qr.get("screenshot_path"):
                    count += 1
        return count

    def _time_exceeded(self, start_time: float) -> bool:
        """Check if total timeout has been exceeded.

        Args:
            start_time: Monotonic start time.

        Returns:
            True if elapsed time exceeds TOTAL_TIMEOUT_SECONDS.
        """
        return (time.monotonic() - start_time) > TOTAL_TIMEOUT_SECONDS

    def _ensure_screenshot_dir(self, audit_id: str) -> Path:
        """Ensure the screenshot directory exists.

        Args:
            audit_id: Audit ID for directory naming.

        Returns:
            Path to the screenshot directory.
        """
        screenshot_dir = Path("data/screenshots") / audit_id
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        return screenshot_dir

    def _empty_result(self, domain: str) -> dict[str, Any]:
        """Return an empty result dict when Playwright is unavailable.

        Args:
            domain: Domain that was supposed to be tested.

        Returns:
            Empty result dict with all expected keys.
        """
        return {
            "prospect_query_results": [],
            "mobile_test_results": [],
            "network_interceptions": [],
            "search_bar_found": False,
            "search_bar_selector": None,
            "detected_search_provider": None,
            "was_blocked": True,
            "block_details": "Playwright not available in this environment",
            "competitor_results": [],
            "total_queries_executed": 0,
            "total_screenshots": 0,
        }


def load_screenshots_as_base64(screenshot_paths: list[str]) -> list[dict[str, str]]:
    """Load screenshot files and encode as base64 for LLM consumption.

    Args:
        screenshot_paths: List of filesystem paths to PNG screenshots.

    Returns:
        List of dicts with 'path' and 'base64' keys.
    """
    encoded: list[dict[str, str]] = []
    for path in screenshot_paths:
        try:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                encoded.append({"path": path, "base64": data})
            else:
                logger.warning(
                    "[BrowserCollector] screenshot file not found",
                    path=path,
                )
        except Exception as exc:
            logger.error(
                "[BrowserCollector] failed to read screenshot",
                path=path,
                error=str(exc),
            )
    return encoded
