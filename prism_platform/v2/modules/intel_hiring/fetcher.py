"""Career page fetcher for intel-hiring v2 — uses Scout (Crawl4AI Playwright).

Strategy:
  1. Try common career URL paths with httpx only (cheap, no Playwright cost)
  2. Escalate to Scout (Playwright) for the first path that returned any response
  3. Detect LinkedIn redirect — if the final URL contains linkedin.com,
     the company routes its jobs to LinkedIn; flag and bail

Career pages are almost always JS-rendered so httpx rarely works. The httpx
check is a fast cheap probe — if it works, great; if not, Scout handles it.

Returns HiringFetchResult with careers page markdown + LinkedIn redirect flag.
Empty string on complete failure — Perplexity runs as fallback (Track 2 alone).
"""

from __future__ import annotations

import structlog
from pydantic import BaseModel, ConfigDict

logger = structlog.get_logger(__name__)

# Common career page URL path patterns (tried in order)
_CAREER_PATHS = [
    "/careers",
    "/jobs",
    "/job-openings",
    "/open-positions",
    "/careers/open-positions",
    "/about/careers",
    "/join-us",
    "/work-with-us",
    "/join-our-team",
]

# Career subdomain patterns
_CAREER_SUBDOMAINS = [
    "careers.{domain}",
    "jobs.{domain}",
]

# Minimum word count to consider a careers page substantive
_MIN_CONTENT_CHARS = 300


class HiringFetchResult(BaseModel):
    """Result from fetching a company's career page via Scout."""

    model_config = ConfigDict(frozen=True)

    careers_page_content: str = ""
    careers_url: str = ""
    redirected_to_linkedin: bool = False


def _is_linkedin_url(url: str) -> bool:
    return "linkedin.com" in url.lower()


async def _quick_httpx_probe(url: str) -> tuple[bool, str]:
    """Fast httpx probe — returns (success, content). No Playwright."""
    try:
        import httpx

        async with httpx.AsyncClient(follow_redirects=True, timeout=8.0) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; PRISM/1.0)"},
            )
            if resp.status_code == 200 and len(resp.text) >= _MIN_CONTENT_CHARS:
                # Check if it redirected to LinkedIn
                if _is_linkedin_url(str(resp.url)):
                    return False, str(resp.url)
                return True, resp.text
    except Exception:
        pass
    return False, ""


async def fetch_careers_page(domain: str, timeout: float = 20.0) -> HiringFetchResult:
    """Fetch the company's career page via Scout.

    Phase 1: Quick httpx-only probe on /careers and /jobs (cheap, fast).
    Phase 2: Scout (Playwright) for JS-rendered pages, trying all paths.
    Phase 3: Try career subdomains (careers.{domain}, jobs.{domain}) via Scout.

    LinkedIn redirect detection: if Scout's final URL contains linkedin.com,
    the company routes applications to LinkedIn — set redirected_to_linkedin=True.

    Returns:
        HiringFetchResult — empty careers_page_content if nothing found.
    """
    from scout.core import ScoutCrawler
    from scout.core.types import ScrapeRequest

    base = f"https://{domain}"

    # ── Phase 1: Cheap httpx probe on top 2 paths ──────────────────────────
    for path in _CAREER_PATHS[:2]:
        url = f"{base}{path}"
        success, content = await _quick_httpx_probe(url)
        if success:
            logger.info(
                "[intel-hiring] careers page found via httpx",
                domain=domain,
                url=url,
                content_len=len(content),
            )
            return HiringFetchResult(
                careers_page_content=_truncate(content),
                careers_url=url,
            )

    # ── Phase 2: Scout (Playwright) — try all career paths ─────────────────
    crawler = ScoutCrawler()
    timeout_ms = int(timeout * 1000)

    for path in _CAREER_PATHS:
        url = f"{base}{path}"
        req = ScrapeRequest(url=url, use_js=True, timeout_ms=timeout_ms)

        try:
            resp = await crawler.scrape(req)
        except Exception as exc:
            logger.debug("[intel-hiring] Scout scrape exception", url=url, error=str(exc))
            continue

        if not resp.success:
            continue

        final_url = resp.metadata.url

        # LinkedIn redirect — company routes jobs to LinkedIn
        if _is_linkedin_url(final_url):
            logger.info(
                "[intel-hiring] LinkedIn redirect detected",
                domain=domain,
                attempted_url=url,
                redirect_to=final_url,
            )
            return HiringFetchResult(redirected_to_linkedin=True)

        if len(resp.markdown) >= _MIN_CONTENT_CHARS:
            logger.info(
                "[intel-hiring] careers page found via Scout",
                domain=domain,
                url=final_url,
                content_len=len(resp.markdown),
            )
            return HiringFetchResult(
                careers_page_content=_truncate(resp.markdown),
                careers_url=final_url,
            )

    # ── Phase 3: Try career subdomains ──────────────────────────────────────
    for subdomain_pattern in _CAREER_SUBDOMAINS:
        url = f"https://{subdomain_pattern.format(domain=domain)}"
        req = ScrapeRequest(url=url, use_js=True, timeout_ms=timeout_ms)

        try:
            resp = await crawler.scrape(req)
        except Exception as exc:
            logger.debug("[intel-hiring] subdomain Scout exception", url=url, error=str(exc))
            continue

        if not resp.success:
            continue

        final_url = resp.metadata.url

        if _is_linkedin_url(final_url):
            return HiringFetchResult(redirected_to_linkedin=True)

        if len(resp.markdown) >= _MIN_CONTENT_CHARS:
            logger.info(
                "[intel-hiring] careers subdomain found",
                domain=domain,
                url=final_url,
                content_len=len(resp.markdown),
            )
            return HiringFetchResult(
                careers_page_content=_truncate(resp.markdown),
                careers_url=final_url,
            )

    logger.warning("[intel-hiring] no careers page found", domain=domain)
    return HiringFetchResult()


def _truncate(content: str, max_chars: int = 8000) -> str:
    """Truncate content to keep playbook prompt within token budget."""
    return content[:max_chars]
