"""Leadership page fetcher for intel-company v2 — uses shared browser infrastructure.

Strategy (fast, smart path discovery):
  1. Fetch homepage → extract about/leadership/team links from navigation
  2. Also try common subdomain patterns (about.{domain}, corp.{domain})
  3. Follow discovered links through the tiered BrowserClient
  4. Check for leadership content signals before accepting

This replaces the old brute-force approach (14 paths × 2 tiers = 28 requests, 3+ min)
with a 2-4 request strategy that handles non-standard URL structures.
"""

from __future__ import annotations

import re

import structlog

from core.browser import BrowserClient, FetchOptions, FetchResult
from core.config import settings

logger = structlog.get_logger(__name__)

# High-priority paths tried directly (before link discovery)
_FAST_PATHS = [
    "/about/leadership",
    "/about-us/leadership",
    "/company/leadership",
    "/leadership",
    "/about/team",
]

# Subdomain patterns to try
_SUBDOMAIN_PATTERNS = [
    "about.{domain}",
    "corp.{domain}",
    "corporate.{domain}",
    "ir.{domain}",
]

# Generic href extractor
_HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)

# Keywords for about/leadership pages (matched against the URL path)
_ABOUT_KEYWORDS = {"about", "leadership", "people", "executive", "management", "corporate", "corp"}

# Keywords to EXCLUDE (product pages, shopping)
_SKIP_KEYWORDS = {"/w/", "/t/", "shopping", "cart", "product", "blog", "tiktok", "instagram", "facebook"}

# IR keywords (matched against URL path)
_IR_KEYWORDS = {"investor", "/ir", "annual-report", "10-k", "sec-filing"}

# Newsroom keywords (matched against URL path)
_NEWS_KEYWORDS = {"newsroom", "press-release", "/media", "/news"}

# Keywords that indicate we found a people/leadership page
_LEADERSHIP_SIGNALS = [
    "chief executive",
    "ceo",
    "cfo",
    "cto",
    "chief operating",
    "vice president",
    "executive",
    "president",
    "linkedin.com/in/",
    "leadership team",
    "our team",
    "management team",
    "executive team",
    "board of directors",
]


def _looks_like_leadership_page(text: str) -> bool:
    """True if the page content appears to contain executive/leadership info."""
    text_lower = text.lower()
    # Require at least 2 signals (reduces false positives from generic pages)
    matches = sum(1 for signal in _LEADERSHIP_SIGNALS if signal in text_lower)
    return matches >= 2


def _extract_links(html: str, keywords: set[str], base_url: str) -> list[str]:
    """Extract links from HTML matching keyword patterns in URL path.

    Smarter than regex-on-full-href: filters out product pages,
    social media links, and other noise.
    """
    all_hrefs = _HREF_RE.findall(html)
    resolved = []
    seen = set()

    for href in all_hrefs:
        lower = href.lower()

        # Must match at least one keyword in the URL
        if not any(kw in lower for kw in keywords):
            continue

        # Skip product/noise pages
        if any(skip in lower for skip in _SKIP_KEYWORDS):
            continue

        # Resolve relative URLs
        link = href
        if link.startswith("//"):
            link = f"https:{link}"
        elif link.startswith("/"):
            link = f"{base_url}{link}"
        elif not link.startswith("http"):
            link = f"{base_url}/{link}"

        # Deduplicate
        if link not in seen:
            seen.add(link)
            resolved.append(link)

    return resolved[:5]


def _get_browser_client() -> BrowserClient:
    """Create a BrowserClient from current settings."""
    return BrowserClient(
        jina_api_key=settings.jina_api_key,
        browserless_api_key=settings.browserless_api_key,
        scrapingbee_api_key=settings.scrapingbee_api_key,
        residential_proxy_url=settings.residential_proxy_url,
    )


async def _try_url(
    client: BrowserClient,
    url: str,
    options: FetchOptions,
    content_check: callable | None = None,
) -> FetchResult | None:
    """Try a single URL, return result if successful and content check passes."""
    result = await client.fetch(url, options)
    if not result.success:
        return None
    if content_check and not content_check(result.text):
        return None
    return result


async def _try_httpx_only(url: str, timeout: float = 10.0) -> FetchResult:
    """Quick httpx-only fetch — no Jina fallback, no escalation."""
    from core.browser.tier1_direct import fetch_direct

    return await fetch_direct(url, FetchOptions(timeout=timeout, min_content_length=300))


def _prioritize_links(links: list[str]) -> list[str]:
    """Sort discovered links by likelihood of containing leadership content.

    Prioritizes:
      1. Links with 'leadership', 'people', 'team', 'executive' in path
      2. About subdomain links (about.{domain})
      3. Generic about links
      4. Corporate links
    """
    def _score(url: str) -> int:
        lower = url.lower()
        if any(kw in lower for kw in ["leadership", "people", "executive", "management"]):
            return 0  # Highest priority
        if "about." in lower and "/en" in lower:
            return 1  # About subdomain (e.g., about.nike.com/en)
        if any(kw in lower for kw in ["/about", "about."]):
            return 2
        if any(kw in lower for kw in ["corp.", "corporate"]):
            return 3
        return 4

    return sorted(links, key=_score)


async def fetch_leadership_page(domain: str, timeout: float = 15.0) -> str:
    """Fetch the company's About/Leadership page via smart link discovery.

    Strategy:
      Phase 1: Try 5 high-priority paths with httpx ONLY (no Jina, <2 seconds each)
      Phase 2: Fetch homepage → discover about/leadership/team links
      Phase 3: Follow top discovered links + subdomain patterns via full tier system
      Phase 4: One-hop-deep: if about page found but no leadership content,
               discover leadership sub-links from the about page

    Returns empty string if all attempts fail — the module continues
    without this data (Perplexity still runs as Track 2).
    """
    client = _get_browser_client()
    base = f"https://{domain}"
    full_options = FetchOptions(timeout=timeout, min_content_length=500)

    # --- Phase 1: Quick httpx-only scan (no Jina, fast) ---
    for path in _FAST_PATHS:
        url = f"{base}{path}"
        result = await _try_httpx_only(url, timeout=8.0)
        if result.success and _looks_like_leadership_page(result.text):
            logger.info(
                "[intel-company] leadership page found (fast path)",
                domain=domain,
                url=result.url,
            )
            return _format_result(result)

    # --- Phase 2: Fetch homepage, discover links ---
    homepage_result = await client.fetch(base, FetchOptions(timeout=timeout, min_content_length=200))
    discovered_links: list[str] = []

    if homepage_result.success:
        html = homepage_result.html or homepage_result.text
        raw_links = _extract_links(html, _ABOUT_KEYWORDS, base)
        discovered_links = _prioritize_links(raw_links)
        logger.info(
            "[intel-company] discovered about/leadership links from homepage",
            domain=domain,
            link_count=len(discovered_links),
            links=discovered_links[:5],
        )

    # Add subdomain patterns after discovered links
    subdomain_urls = [
        f"https://{pattern.format(domain=domain)}"
        for pattern in _SUBDOMAIN_PATTERNS
    ]
    candidate_urls = discovered_links + subdomain_urls

    # --- Phase 3: Try candidates via full tier system ---
    about_page_result: FetchResult | None = None

    for url in candidate_urls[:6]:  # Cap at 6 to limit total time
        result = await _try_url(client, url, full_options, content_check=None)
        if not result:
            continue

        # If it has leadership content, we're done
        if _looks_like_leadership_page(result.text):
            logger.info(
                "[intel-company] leadership page found (discovery)",
                domain=domain,
                url=result.url,
                tier=result.tier_used.value,
            )
            return _format_result(result)

        # Save the first about-ish page for Phase 4 one-hop-deep crawling
        if about_page_result is None:
            about_page_result = result

    # --- Phase 4: One-hop-deep — crawl about page for leadership sub-link ---
    if about_page_result and about_page_result.html:
        sub_links = _extract_links(
            about_page_result.html, {"leadership", "people", "executive", "team"}, about_page_result.url
        )
        logger.info(
            "[intel-company] one-hop-deep: sub-links from about page",
            domain=domain,
            about_url=about_page_result.url,
            sub_links=sub_links[:3],
        )
        for url in sub_links[:3]:
            result = await _try_url(client, url, full_options, _looks_like_leadership_page)
            if result:
                logger.info(
                    "[intel-company] leadership page found (one-hop-deep)",
                    domain=domain,
                    url=result.url,
                    tier=result.tier_used.value,
                )
                return _format_result(result)

    # --- Phase 5: Last resort — homepage content itself ---
    if homepage_result.success and _looks_like_leadership_page(homepage_result.text):
        logger.info("[intel-company] using homepage as leadership source", domain=domain)
        return _format_result(homepage_result)

    logger.warning("[intel-company] no leadership page found", domain=domain)
    return ""


async def fetch_ir_page(domain: str, timeout: float = 15.0) -> str:
    """Fetch the company's Investor Relations page.

    Returns empty string for private companies or if IR page not found.
    Used to get authoritative employee count, revenue, and financial data.
    """
    client = _get_browser_client()
    base = f"https://{domain}"
    options = FetchOptions(timeout=timeout, min_content_length=300)

    # Try direct IR paths first
    for path in ["/investor-relations", "/investors", "/ir"]:
        result = await _try_url(client, f"{base}{path}", options)
        if result:
            return _format_result(result, max_chars=5000)

    # Try IR subdomain
    result = await _try_url(client, f"https://ir.{domain}", options)
    if result:
        return _format_result(result, max_chars=5000)

    # Try discovering IR links from homepage
    homepage = await client.fetch(base, FetchOptions(timeout=timeout, max_tier=1))
    if homepage.success and homepage.html:
        ir_links = _extract_links(homepage.html, _IR_KEYWORDS, base)
        for url in ir_links[:3]:
            result = await _try_url(client, url, options)
            if result:
                return _format_result(result, max_chars=5000)

    return ""


async def fetch_newsroom_page(domain: str, timeout: float = 15.0) -> str:
    """Fetch the company's Newsroom/Press page.

    Used to get recent press releases and detect leadership changes
    that may not yet be reflected on the about page.
    """
    client = _get_browser_client()
    base = f"https://{domain}"
    options = FetchOptions(timeout=timeout, min_content_length=300)

    for path in ["/newsroom", "/news", "/press", "/media"]:
        result = await _try_url(client, f"{base}{path}", options)
        if result:
            return _format_result(result, max_chars=5000)

    # Try discovering newsroom links from homepage
    homepage = await client.fetch(base, FetchOptions(timeout=timeout, max_tier=1))
    if homepage.success and homepage.html:
        news_links = _extract_links(homepage.html, _NEWS_KEYWORDS, base)
        for url in news_links[:3]:
            result = await _try_url(client, url, options)
            if result:
                return _format_result(result, max_chars=5000)

    return ""


async def fetch_all_company_pages(domain: str, timeout: float = 15.0) -> dict[str, str]:
    """Fetch all relevant company pages for Track 1 (WebFetch).

    Returns a dict of page_type -> content for injection into the
    synthesis pipeline. Empty string for pages that weren't found.
    """
    leadership = await fetch_leadership_page(domain, timeout)
    ir = await fetch_ir_page(domain, timeout)
    newsroom = await fetch_newsroom_page(domain, timeout)

    pages_found = sum(1 for v in [leadership, ir, newsroom] if v)
    logger.info(
        "[intel-company] company page fetch complete",
        domain=domain,
        pages_found=pages_found,
        has_leadership=bool(leadership),
        has_ir=bool(ir),
        has_newsroom=bool(newsroom),
    )

    return {
        "leadership_page": leadership,
        "ir_page": ir,
        "newsroom_page": newsroom,
    }


def _format_result(result: FetchResult, max_chars: int = 8000) -> str:
    """Format a FetchResult into the text blob injected into playbook context."""
    truncated = result.text[:max_chars]
    return f"[Fetched from {result.url} via {result.tier_used.value}]\n\n{truncated}"
