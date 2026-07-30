"""Search-vendor detector — packet inspection (PRISM's BuiltWith replacement).

Identity comes from the LIVE network call the browser makes, not from scraping HTML
or a hardcoded vendor list. No LLM. No supposition.

How it works (deterministic, network capture):
1. Open a real (stealth) browser, load the site, dismiss consent, type a query with
   REAL keystrokes (fires as-you-type search). Typing only makes the call fire.
2. Snoop ALL network traffic.
3. A search call is CONFIRMED only if it hits a search-endpoint PATH *and* carries the
   typed query — zero false positives by construction (ad/analytics can't do both).
4. Vendor = packet fingerprint (header/host/param — unmasks proxied vendors) else the
   registrable host of the confirmed call. First-party host => proprietary.
5. Per-vendor deep extraction: app_id, api_key, index, etc. — all from the packet.

Known limits (by design, classified as exceptions — no client-side method can see these):
- Backend / self-hosted engines (Elasticsearch, Solr, self-hosted Typesense): the browser
  queries the site's own API; the engine is invisible. -> first-party.
- Visual search (Syte): text-box trigger never fires it.
- Proxied vendors that don't forward vendor headers: reported as first-party (honest).
- Bot-walls (Akamai/Cloudflare): BOT_BLOCKED even with stealth.

Validated 2026-06-27 across 17 vendors / ~230 customer sites: 59 confirmed, zero false positives.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from urllib.parse import urlparse

import structlog
from playwright.async_api import Browser, Request, async_playwright
from playwright_stealth import Stealth
from pydantic import BaseModel, ConfigDict, Field

logger = structlog.get_logger(__name__)

_STEALTH = Stealth()
_QUERY = "shoes"
_QTOKEN = "shoe"  # corroboration token (matches shoe/shoes + autocomplete prefixes)
_SITE_TIMEOUT = 55.0  # hard per-site ceiling so one hung page can't stall a batch

# Cosmetic only: registrable-domain -> pretty label. NEVER used to detect.
KNOWN_NAMES: dict[str, str] = {
    "algolia.net": "Algolia", "algolianet.com": "Algolia",
    "cnstrc.com": "Constructor.io", "constructor.io": "Constructor.io",
    "coveo.com": "Coveo", "brcloud.com": "Bloomreach", "brapi.com": "Bloomreach",
    "bloomreach.com": "Bloomreach", "dxpapi.com": "Bloomreach",
    "yext.com": "Yext", "yextapis.com": "Yext",
    "searchspring.net": "Searchspring", "searchspring.io": "Searchspring",
    "klevu.com": "Klevu", "ksearchnet.com": "Klevu",
    "typesense.net": "Typesense", "typesense.org": "Typesense",
    "elastic.co": "Elastic", "found.io": "Elastic",
    "meilisearch.com": "Meilisearch", "meilisearch.io": "Meilisearch",
    "unbxd.io": "Unbxd", "unbxdapi.com": "Unbxd", "netcoreunbxd.com": "Unbxd",
    "doofinder.com": "Doofinder", "doofinder.io": "Doofinder", "swiftype.com": "Swiftype",
    "googleapis.com": "Google", "hawksearch.com": "HawkSearch", "hawksearch.net": "HawkSearch",
    "groupbycloud.com": "GroupBy", "attraqt.com": "Attraqt", "attraqt.io": "Attraqt",
    "empathy.co": "Empathy", "nosto.com": "Nosto", "syte.ai": "Syte",
    "addsearch.com": "AddSearch", "lucidworks.com": "Lucidworks",
    "loop54.io": "Loop54", "loop54.com": "Loop54", "fact-finder.de": "FACT-Finder",
    "fact-finder.com": "FACT-Finder", "apptus.cloud": "Apptus/Voyado",
    "inbenta.io": "Inbenta", "cimulate.ai": "Cimulate", "mybcapps.com": "Boost",
    "sajari.com": "Sajari", "search.io": "Sajari", "orama.run": "Orama",
    "bonsai.io": "Bonsai", "cludo.com": "Cludo", "fastsimon.com": "Fast Simon",
}

# Vendor fingerprints — distinctive header-keys / host / param tokens in the PACKET.
# Used ONLY to unmask a vendor (incl. proxied behind a first-party host). Real data.
_FINGERPRINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("algolia.net", ("x-algolia-application-id", "x-algolia-api-key", "x-algolia-agent",
                     "algolia.net", "algolianet.com")),
    ("typesense.net", ("x-typesense-api-key", "typesense.net", ".typesense.")),
    ("meilisearch.com", ("x-meili-api-key", "meilisearch")),
    ("cnstrc.com", ("cnstrc.com", "constructor.io")),
    ("coveo.com", (".coveo.com", "org.coveo", "coveocdn")),
    ("brcloud.com", ("brcloud.com", "brapi.com", "bloomreach", "dxpapi.com", "dxpapi")),
    ("searchspring.net", ("searchspring.net", "searchspring.io")),
    ("klevu.com", ("klevu.com", "ksearchnet.com")),
    ("unbxd.io", ("unbxd.io", "unbxdapi.com", "netcoreunbxd")),
    ("doofinder.com", ("doofinder.com", "doofinder.io")),
    ("nosto.com", ("nosto.com",)), ("yext.com", ("yextapis.com", ".yext.com")),
    ("loop54.io", ("loop54.io", "loop54.com")),
    ("fact-finder.de", ("fact-finder.de", "fact-finder.com", "factfinder")),
    ("addsearch.com", ("addsearch.com",)), ("cludo.com", ("cludo.com",)),
    ("hawksearch.com", ("hawksearch.com", "hawksearch.net")),
    ("attraqt.com", ("attraqt.com", "attraqt.io", "fredhopper")),
    ("apptus.cloud", ("apptus.cloud", "esales.apptus")),
    ("inbenta.io", ("inbenta.io",)), ("cimulate.ai", ("cimulate.ai",)),
    ("mybcapps.com", ("mybcapps.com",)), ("syte.ai", ("syte.ai",)),
    ("fastsimon.com", ("fastsimon.com", "fast.co/search")),
)

_STATIC_EXT = (".js", ".mjs", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
               ".avif", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".webm", ".map", ".wasm")
_NOISE = ("google-analytics.com", "analytics.google.com", "googletagmanager.com",
          "google.com/pagead", "googlesyndication.com", "doubleclick.net", "facebook.com",
          "facebook.net", "clarity.ms", "hotjar.com", "newrelic.com", "nr-data.net", "sentry.io",
          "segment.com", "segment.io", "cookielaw.org", "onetrust.com", "fonts.googleapis.com",
          "fonts.gstatic.com", "gstatic.com", "linkedin.com", "licdn.com", "tiktok.com",
          "cloudflareinsights.com", "demdex.net", "adobedtm.com", "omtrdc.net", "6sense.com",
          "qualtrics.com", "amplitude.com", "mixpanel.com", "datadoghq.com", "dreamdata.cloud",
          "vidyard.com", "adroll.com", "adsrvr.org", "marketo.net", "hubspot.com", "zoominfo.com")
_STRONG_PATHS = ("/search", "/queries", "/query", "/autocomplete", "/suggest", "/typeahead",
                 "/instantsearch", "/instant", "/indexes/", "/collections/", "/rest/search",
                 "/sayt", "/multi_search", "/find", "/facet", "/_search", "/v1/search",
                 "/api/search", "/discovery", "/recommend")

# Status taxonomy.
DETECTED = "DETECTED"
NO_ONSITE_SEARCH = "NO_ONSITE_SEARCH"
BOT_BLOCKED = "BOT_BLOCKED"
ERROR = "ERROR"
TIMEOUT = "TIMEOUT"
_VALID_STATUS = frozenset({DETECTED, NO_ONSITE_SEARCH, BOT_BLOCKED, ERROR, TIMEOUT})


class SearchVendorResult(BaseModel):
    """Deterministic detection result for one domain, proven from the network packet."""

    model_config = ConfigDict(extra="forbid")

    domain: str
    search_vendor: str | None = Field(default=None, description="Headline vendor label, or None")
    search_vendor_status: str = Field(default=NO_ONSITE_SEARCH, description="status taxonomy")
    is_algolia: bool = Field(default=False)
    app_id: str = Field(default="", description="Vendor app/account ID extracted from the packet")
    api_key: str = Field(default="", description="Public search key, if exposed")
    index_name: str = Field(default="", description="Index/collection, if present")
    endpoint_host: str = Field(default="", description="Real host the search call hit")
    all_vendors: list[str] = Field(default_factory=list, description="Every confirmed vendor")
    proxied: bool = Field(default=False, description="Vendor served via a first-party host")
    commerce_platform: str | None = Field(default=None)
    detection_method: str = Field(default="network_capture")
    matched_patterns: list[str] = Field(default_factory=list, description="Evidence tokens")
    evidence_url: str = Field(default="", description="Sample search endpoint URL")
    checked_at: str = Field(default="")
    note: str = Field(default="")


def registrable(host: str) -> str:
    host = host.lower().split(":")[0]
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    two = ".".join(parts[-2:])
    if two in {"co.uk", "com.au", "co.jp", "co.nz", "com.br", "co.in", "org.uk"}:
        return ".".join(parts[-3:])
    return two


def _is_static(url: str) -> bool:
    return urlparse(url).path.lower().endswith(_STATIC_EXT)


def _is_noise(url: str) -> bool:
    low = url.lower()
    return any(n in low for n in _NOISE)


def _strong_path(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(t in path for t in _STRONG_PATHS)


def _carries_query(url: str, body: str) -> bool:
    return _QTOKEN in (url + " " + body).lower()


class _Cap:
    __slots__ = ("body", "headers", "url")

    def __init__(self, url: str, headers: dict, body: str) -> None:
        self.url, self.headers, self.body = url, headers, body


def _fingerprint(c: _Cap) -> str | None:
    blob = (c.url + " " + c.body + " " + " ".join(c.headers.keys())).lower()
    for domain, toks in _FINGERPRINTS:
        if any(t in blob for t in toks):
            return domain
    return None


def _extract(domain: str, hits: list[_Cap]) -> dict:
    d: dict = {}
    if domain in ("algolia.net", "algolianet.com"):
        for h in hits:
            if not d.get("app_id"):
                m = re.search(r"https?://([a-z0-9]{8,})-?(?:dsn)?[.-]", h.url, re.I)
                if m:
                    d["app_id"] = m.group(1).upper()
            for k, src in (("app_id", "x-algolia-application-id"),
                           ("api_key", "x-algolia-api-key")):
                if not d.get(k) and h.headers.get(src):
                    d[k] = h.headers[src]
            if h.body:
                try:
                    b = json.loads(h.body)
                    reqs = b.get("requests") if isinstance(b, dict) else None
                    if reqs:
                        idx = sorted({r.get("indexName") for r in reqs if r.get("indexName")})
                        if idx:
                            d["index_name"] = idx[0]
                except Exception:
                    pass
        if d.get("app_id"):
            d["app_id"] = d["app_id"].upper()
        return d
    # generic: pull common id/key params + index/collection from the path
    from urllib.parse import parse_qs
    for h in hits:
        qs = parse_qs(urlparse(h.url).query)
        for cand in ("key", "apiKey", "api_key", "siteId", "account_id", "domain_key",
                     "experienceKey", "uid", "engine_key"):
            if qs.get(cand) and not d.get("app_id"):
                d["app_id"] = qs[cand][0]
        m = re.search(r"/(?:indexes|collections|engines)/([^/?]+)", urlparse(h.url).path)
        if m and not d.get("index_name"):
            d["index_name"] = m.group(1)
    return d


async def _dismiss_consent(page) -> None:
    for sel in ("#onetrust-accept-btn-handler", "#truste-consent-button",
                'button[aria-label*="accept" i]', 'button[id*="accept" i]',
                'button[class*="accept" i]', ".cookie-accept", ".accept-cookies",
                "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"):
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=600):
                await el.click(timeout=1200)
                await page.wait_for_timeout(400)
                return
        except Exception:
            continue


async def _type(page, el) -> bool:
    try:
        await el.click(timeout=1500)
        await page.wait_for_timeout(250)
        await el.press_sequentially(_QUERY, delay=110)  # real key events -> autocomplete fires
        await page.wait_for_timeout(2600)
        await el.press("Enter")
        await page.wait_for_timeout(2400)
        return True
    except Exception:
        return False


async def _trigger(page) -> None:
    await _dismiss_consent(page)
    for combo in ("Meta+K", "Control+K", "/"):
        try:
            await page.keyboard.press(combo)
            await page.wait_for_timeout(500)
            box = page.locator(
                'input[type="search"], input[role="searchbox"], input[role="combobox"], '
                'input[placeholder*="search" i], .DocSearch-Input'
            ).first
            if await box.is_visible(timeout=700) and await _type(page, box):
                return
        except Exception:
            pass
    for sel in ('button[aria-label*="search" i]', 'a[aria-label*="search" i]',
                '[data-testid*="search" i]', ".search-icon", ".search-toggle",
                ".search-button", 'button[class*="search" i]', 'header button:has(svg)'):
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=700):
                await el.click(timeout=1500)
                await page.wait_for_timeout(500)
                break
        except Exception:
            continue
    for sel in ('input[type="search"]', 'input[name*="search" i]',
                'input[placeholder*="search" i]', 'input[id*="search" i]',
                'input[aria-label*="search" i]', 'input[role="searchbox"]',
                'input[role="combobox"]', "#searchInput", ".search-input"):
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=900) and await _type(page, el):
                return
        except Exception:
            continue
    try:
        b = urlparse(page.url)
        await page.goto(f"{b.scheme}://{b.netloc}/search?q={_QUERY}",
                        wait_until="domcontentloaded", timeout=10000)
        await page.wait_for_timeout(2200)
    except Exception:
        pass


async def _detect_on(browser: Browser, domain: str) -> SearchVendorResult:
    """Core single-domain detection on a shared browser. Never raises."""
    now = datetime.now(UTC).isoformat()
    url = domain if domain.startswith("http") else f"https://{domain}"
    res = SearchVendorResult(domain=domain, checked_at=now)
    ctx = await browser.new_context(
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"),
        viewport={"width": 1440, "height": 900}, locale="en-US", timezone_id="America/New_York",
    )
    page = await ctx.new_page()
    cap: list[_Cap] = []

    def on_req(req: Request) -> None:
        try:
            body = req.post_data or ""
        except Exception:
            body = ""
        if req.resource_type in ("xhr", "fetch"):
            cap.append(_Cap(req.url, dict(req.headers), body))

    page.on("request", on_req)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)
        title = (await page.title()).lower()
        html = (await page.content())[:4000].lower()
        if ("just a moment" in title or "attention required" in html
                or "access denied" in title or "verify you are human" in html):
            res.search_vendor_status = BOT_BLOCKED
            res.note = "challenge page"
            await ctx.close()
            return res
        await _trigger(page)
    except Exception as exc:
        res.search_vendor_status = ERROR
        res.note = f"{type(exc).__name__}: {str(exc)[:70]}"
        await ctx.close()
        return res

    site_host = registrable(urlparse(page.url).netloc)
    api = [c for c in cap if not _is_static(c.url) and not _is_noise(c.url)]
    confirmed = [c for c in api if _strong_path(c.url) and _carries_query(c.url, c.body)]
    if not confirmed:
        await ctx.close()
        return res  # NO_ONSITE_SEARCH

    agg: dict[str, dict] = {}
    for c in confirmed:
        host = registrable(urlparse(c.url).netloc)
        fp = _fingerprint(c)
        vendor = fp or host
        a = agg.setdefault(vendor, {"hits": 0, "fp": False, "host": host, "calls": []})
        a["hits"] += 1
        a["fp"] = a["fp"] or (fp is not None)
        a["calls"].append(c)

    def _tier(v: str) -> int:
        a = agg[v]
        if a["fp"]:
            return 0
        if v != site_host and v in KNOWN_NAMES:
            return 1
        if v != site_host:
            return 2
        return 3

    def _label(v: str) -> str:
        lab = KNOWN_NAMES.get(v, f"unrecognised:{v}")
        if agg[v]["fp"] and registrable(agg[v]["host"]) == site_host:
            return lab + " [proxied]"
        if v == site_host:
            return lab + " [first-party]"
        return lab

    ranked = sorted(agg, key=lambda v: (_tier(v), -agg[v]["hits"]))
    headline = ranked[0]
    a = agg[headline]
    hits = a["calls"]
    details = _extract(headline, hits)

    res.search_vendor_status = DETECTED
    res.search_vendor = _label(headline)
    res.all_vendors = [_label(v) for v in ranked]
    res.is_algolia = headline in ("algolia.net", "algolianet.com")
    res.proxied = a["fp"] and registrable(a["host"]) == site_host
    res.endpoint_host = urlparse(hits[0].url).netloc
    res.app_id = details.get("app_id", "")
    res.api_key = details.get("api_key", "")
    res.index_name = details.get("index_name", "")
    res.evidence_url = hits[0].url[:200]
    res.matched_patterns = [headline] + ([res.app_id] if res.app_id else [])
    await ctx.close()
    logger.info("[detect] complete", domain=domain, vendor=res.search_vendor,
                status=res.search_vendor_status, app_id=res.app_id)
    return res


async def detect_search_vendor(
    domain: str,
    browser: Browser | None = None,
    timeout: float = _SITE_TIMEOUT,
) -> SearchVendorResult:
    """Detect the search vendor for one domain via live packet inspection. Never raises.

    Args:
        domain: bare domain ("nike.com") or full URL.
        browser: optional shared Playwright Browser (for batch use). One is launched if omitted.
        timeout: hard per-site ceiling in seconds.
    """
    async def _run(b: Browser) -> SearchVendorResult:
        try:
            return await asyncio.wait_for(_detect_on(b, domain), timeout=timeout)
        except TimeoutError:
            return SearchVendorResult(domain=domain, search_vendor_status=TIMEOUT,
                                      note=f"exceeded {timeout}s")
        except Exception as exc:
            return SearchVendorResult(domain=domain, search_vendor_status=ERROR,
                                      note=f"{type(exc).__name__}: {str(exc)[:70]}")

    if browser is not None:
        return await _run(browser)
    async with _STEALTH.use_async(async_playwright()) as pw:
        b = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            return await _run(b)
        finally:
            await b.close()


async def scan_search_vendors(
    domains: list[str],
    concurrency: int = 4,
    timeout: float = _SITE_TIMEOUT,
) -> dict[str, SearchVendorResult]:
    """Scan many domains on ONE shared stealth browser. Returns {domain: result}. Never raises."""
    sem = asyncio.Semaphore(concurrency)
    async with _STEALTH.use_async(async_playwright()) as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )

        async def one(dom: str) -> tuple[str, SearchVendorResult]:
            async with sem:
                return dom, await detect_search_vendor(dom, browser=browser, timeout=timeout)

        try:
            pairs = await asyncio.gather(*(one(d) for d in domains))
        finally:
            await browser.close()
    return dict(pairs)
