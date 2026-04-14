"""Citation validator — Tier 1 URL existence checks.

Tier 1: async HEAD request to verify a URL returns a non-404 response.
        Fast and cheap. Catches hallucinated URLs immediately.

Tier 2 (Phase 3): fetch page content, verify claim appears on page.
                  Reserved for revenue figures and exec quotes.

Every ClaimRegistryEntry gets citation_status from this module.
"""

from __future__ import annotations

from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict

# Status literals for citation validation results
CitationStatus = Literal["live", "dead", "unchecked"]

# HTTP status codes that mean "URL exists, content may have moved"
_LIVE_STATUS_CODES = frozenset(range(100, 400))  # 1xx, 2xx, 3xx

_HEAD_TIMEOUT_SECONDS = 10.0
_USER_AGENT = "PRISM/2.0 citation-validator (HEAD request)"


class CitationValidationResult(BaseModel):
    """Result of a Tier 1 citation validation check.

    Immutable — created once per URL, consumed by audit-factcheck.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str
    citation_status: CitationStatus
    http_status_code: int | None = None


async def validate_citations_tier1(
    citations: list[str],
) -> list[CitationValidationResult]:
    """Validate all citation URLs via async HEAD requests.

    Each URL gets a HEAD request with a 10-second timeout. The result is:
    - "live"      → HTTP 1xx / 2xx / 3xx (URL exists)
    - "dead"      → HTTP 4xx / 5xx (URL returned an error)
    - "unchecked" → Network error, timeout, or other exception

    Results are returned in the same order as the input list.

    Args:
        citations: List of URL strings to validate.

    Returns:
        List of CitationValidationResult, one per input URL, in order.
    """
    if not citations:
        return []

    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=_HEAD_TIMEOUT_SECONDS,
        headers={"User-Agent": _USER_AGENT},
    ) as client:
        tasks = [_check_url(client, url) for url in citations]

        # Run all checks concurrently
        import asyncio

        results = await asyncio.gather(*tasks)

    return list(results)


async def _check_url(
    client: httpx.AsyncClient,
    url: str,
) -> CitationValidationResult:
    """Check a single URL via HEAD request.

    Args:
        client: Shared httpx AsyncClient.
        url: URL to check.

    Returns:
        CitationValidationResult for the URL.
    """
    try:
        response = await client.head(url)
        status_code = response.status_code

        if status_code in _LIVE_STATUS_CODES:
            return CitationValidationResult(
                url=url,
                citation_status="live",
                http_status_code=status_code,
            )
        else:
            return CitationValidationResult(
                url=url,
                citation_status="dead",
                http_status_code=status_code,
            )

    except (httpx.HTTPError, httpx.InvalidURL, OSError):
        return CitationValidationResult(
            url=url,
            citation_status="unchecked",
            http_status_code=None,
        )
