"""Search-vendor + commerce-platform detector — PRISM's in-app BuiltWith replacement.

Why this exists
---------------
BuiltWith is out of PRISM (no budget / credits). The only thing we actually
need from it — *which search vendor a site runs* — is detectable for free by
crawling the rendered homepage and scanning the HTML/JS for known vendor
signatures. This is also *more* reliable than BuiltWith for our purpose:
BuiltWith reports installed tags from a stale database, while we read what the
live, JS-rendered application actually ships.

How it works (deterministic Track-1 source-scan, NO LLM)
--------------------------------------------------------
1. Fetch the rendered homepage through the shared tiered ``BrowserClient``
   (httpx → Scout/Playwright stealth), which bypasses most WAFs and runs JS so
   vendor bundles (e.g. ``algoliasearch``) appear in the HTML.
2. Lower-case the HTML + discovered links and test each vendor's signature
   patterns against it.
3. Classify the result (DETECTED / UNDETECTED / UNCONFIRMED_WAF_BLOCK /
   FETCH_FAILED) with the matched evidence.

Known limit (planned follow-up)
-------------------------------
Scout's response exposes ``html``/``text``/``links`` but NOT network requests,
so this is a *source scan*. The gold-standard "live network confirmation"
(type a query, observe the firing search API) needs a network-capture path
Scout does not yet expose. ``detection_method`` records which layer ran so the
classification is never overstated.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from pydantic import BaseModel, ConfigDict, Field

from prism_platform.browser import BrowserClient, FetchOptions

logger = structlog.get_logger(__name__)


class VendorSignature(BaseModel):
    """A vendor and the case-insensitive substrings that betray its presence."""

    model_config = ConfigDict(frozen=True)

    name: str
    category: str  # "search" | "commerce"
    patterns: tuple[str, ...]


# Ordered by specificity — the first matching search vendor wins as `search_vendor`.
# Patterns are matched case-insensitively against rendered HTML + links.
SEARCH_VENDOR_SIGNATURES: tuple[VendorSignature, ...] = (
    VendorSignature(
        name="Algolia",
        category="search",
        patterns=("algolia.net", "algolianet.com", "algoliasearch", "/1/indexes/", "algolia.com"),
    ),
    VendorSignature(
        name="Constructor.io", category="search", patterns=("cnstrc.com", "constructor.io")
    ),
    VendorSignature(
        name="Coveo",
        category="search",
        patterns=("cloud.coveo.com", "coveo.com", "platform.cloud.coveo"),
    ),
    VendorSignature(name="Bloomreach", category="search", patterns=("brcloud.com", "bloomreach")),
    VendorSignature(
        name="Searchspring",
        category="search",
        patterns=("searchspring.net", "searchspring.io", "searchspring"),
    ),
    VendorSignature(name="Klevu", category="search", patterns=("klevu.com", "klevu")),
    VendorSignature(name="Unbxd", category="search", patterns=("unbxd.com", "unbxd")),
    VendorSignature(name="Attraqt", category="search", patterns=("attraqt", "fredhopper")),
    VendorSignature(name="Yext", category="search", patterns=("yext.com", "yextapis")),
    VendorSignature(name="Lucidworks", category="search", patterns=("lucidworks",)),
    VendorSignature(name="Solr", category="search", patterns=("/solr/",)),
    VendorSignature(
        name="Elasticsearch",
        category="search",
        patterns=("elasticsearch", "opensearch", "/_search?"),
    ),
)

COMMERCE_SIGNATURES: tuple[VendorSignature, ...] = (
    VendorSignature(
        name="Shopify",
        category="commerce",
        patterns=("cdn.shopify.com", "myshopify.com", "shopify"),
    ),
    VendorSignature(
        name="Salesforce Commerce Cloud",
        category="commerce",
        patterns=("demandware.net", "demandware", "salesforce commerce"),
    ),
    VendorSignature(
        name="Adobe Commerce (Magento)",
        category="commerce",
        patterns=("/static/version", "magento", "adobe commerce"),
    ),
    VendorSignature(
        name="BigCommerce", category="commerce", patterns=("bigcommerce.com", "bigcommerce")
    ),
    VendorSignature(name="commercetools", category="commerce", patterns=("commercetools",)),
    VendorSignature(name="SAP Hybris", category="commerce", patterns=("hybris",)),
    VendorSignature(name="VTEX", category="commerce", patterns=("vtexcommercestable", "vtex")),
)

# Status taxonomy mirrors the audit skill's classification vocabulary.
SearchVendorStatus = str  # "DETECTED" | "UNDETECTED" | "UNCONFIRMED_WAF_BLOCK" | "FETCH_FAILED"


class SearchVendorResult(BaseModel):
    """Deterministic detection result for one domain (BuiltWith replacement)."""

    model_config = ConfigDict(extra="forbid")

    domain: str
    search_vendor: str | None = Field(
        default=None, description="Highest-priority search vendor detected, or None"
    )
    search_vendor_status: SearchVendorStatus = Field(
        default="UNDETECTED",
        description="DETECTED | UNDETECTED | UNCONFIRMED_WAF_BLOCK | FETCH_FAILED",
    )
    all_search_vendors: list[str] = Field(
        default_factory=list, description="Every search vendor whose signature matched"
    )
    commerce_platform: str | None = Field(
        default=None, description="Detected ecommerce platform, or None"
    )
    is_algolia: bool = Field(default=False, description="True if Algolia was detected")
    matched_patterns: list[str] = Field(
        default_factory=list, description="The exact signature substrings that matched (evidence)"
    )
    detection_method: str = Field(
        default="source_scan",
        description="Which detection layer produced this (source_scan; network_confirm is TODO)",
    )
    evidence_url: str = Field(default="", description="Final URL that was scanned")
    checked_at: str = Field(default="", description="ISO timestamp of the scan")
    note: str = Field(default="", description="Human-readable detail (e.g. WAF block reason)")


def _scan(haystack: str, signatures: tuple[VendorSignature, ...]) -> list[tuple[str, list[str]]]:
    """Return [(vendor_name, [matched_patterns]), ...] in signature priority order."""
    hits: list[tuple[str, list[str]]] = []
    for sig in signatures:
        matched = [p for p in sig.patterns if p.lower() in haystack]
        if matched:
            hits.append((sig.name, matched))
    return hits


async def detect_search_vendor(
    domain: str,
    browser_client: BrowserClient | None = None,
    timeout: float = 30.0,
) -> SearchVendorResult:
    """Detect the search vendor + commerce platform for a domain via source scan.

    Args:
        domain: Bare domain (e.g. "nike.com") or full URL.
        browser_client: Optional shared BrowserClient; one is created if omitted.
        timeout: Per-fetch timeout in seconds.

    Returns:
        SearchVendorResult — never raises; failures are encoded in the status.
    """
    now = datetime.now(UTC).isoformat()
    url = domain if domain.startswith("http") else f"https://{domain}"
    client = browser_client or BrowserClient()

    try:
        result = await client.fetch(
            url,
            FetchOptions(render_js=True, max_tier=2, timeout=timeout),
        )
    except Exception as exc:
        logger.warning("[detect] fetch raised", domain=domain, error=str(exc))
        return SearchVendorResult(
            domain=domain,
            search_vendor_status="FETCH_FAILED",
            checked_at=now,
            note=f"fetch exception: {type(exc).__name__}",
        )

    if result.is_bot_blocked:
        return SearchVendorResult(
            domain=domain,
            search_vendor_status="UNCONFIRMED_WAF_BLOCK",
            evidence_url=result.url,
            checked_at=now,
            note=f"Bot/WAF block at tier {result.tier_used}; needs stealth escalation",
        )

    haystack = (
        (result.html or "") + " " + result.text + " " + " ".join(getattr(result, "links", []) or [])
    ).lower()
    if not haystack.strip() or result.status_code == 0:
        return SearchVendorResult(
            domain=domain,
            search_vendor_status="FETCH_FAILED",
            evidence_url=result.url,
            checked_at=now,
            note=result.error or "empty content returned",
        )

    search_hits = _scan(haystack, SEARCH_VENDOR_SIGNATURES)
    commerce_hits = _scan(haystack, COMMERCE_SIGNATURES)

    all_vendors = [name for name, _ in search_hits]
    matched_patterns = [p for _, pats in search_hits for p in pats]
    primary = all_vendors[0] if all_vendors else None

    res = SearchVendorResult(
        domain=domain,
        search_vendor=primary,
        search_vendor_status="DETECTED" if primary else "UNDETECTED",
        all_search_vendors=all_vendors,
        commerce_platform=commerce_hits[0][0] if commerce_hits else None,
        is_algolia=any(v == "Algolia" for v in all_vendors),
        matched_patterns=matched_patterns,
        evidence_url=result.url,
        checked_at=now,
    )
    logger.info(
        "[detect] source scan complete",
        domain=domain,
        search_vendor=res.search_vendor,
        status=res.search_vendor_status,
        commerce=res.commerce_platform,
    )
    return res
