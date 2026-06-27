"""Packet-inspection search detector — identity from the live endpoint, no vendor list.

Logic (no LLM, no supposition, no hardcoded vendor gatekeeping):
1. Open a real browser, load the site, trigger search (typing only makes the call fire).
2. Snoop ALL network traffic (requests + response content-types).
3. Step through the API calls (xhr/fetch), skip static assets + analytics noise.
4. CONFIRM a search call by real packet data — a search-endpoint PATH that ALSO
   carries the exact query string I typed. Zero false positives by construction:
   an ad/analytics host can't carry my query to a /search endpoint by accident.
5. The confirmed call's DESTINATION HOST is the vendor — read live off the wire.
   First-party host -> proprietary/proxied. Third-party -> that domain IS the vendor.
6. Run a per-vendor deep extractor over the confirmed calls -> app_id, index, key, etc.

A tiny KNOWN_NAMES map only prettifies a domain into a label AFTER detection; it
never decides anything. Unknown host -> still detected + named by its real domain.

Usage:
    uv run python scripts/detect_search_packet.py <domain>          # one site (verbose)
    uv run python scripts/detect_search_packet.py --vendor algolia  # run customers/algolia.txt
    uv run python scripts/detect_search_packet.py                   # the 33 vendor sites
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.async_api import Request, Response, async_playwright
from playwright_stealth import Stealth

_STEALTH = Stealth()

_WS = Path(__file__).resolve().parents[1] / "docs/workspace/search-detector-validation"
_CUSTOMERS = _WS / "customers"
_RESULTS = _WS / "results"

_QUERY = "shoes"
_QTOKEN = "shoe"  # corroboration token (catches shoe/shoes, autocomplete prefixes)

# Optional, cosmetic only: registrable-domain -> pretty label. Never used to detect.
KNOWN_NAMES: dict[str, str] = {
    "algolia.net": "Algolia", "algolianet.com": "Algolia",
    "cnstrc.com": "Constructor.io", "constructor.io": "Constructor.io",
    "coveo.com": "Coveo",
    "brcloud.com": "Bloomreach", "brapi.com": "Bloomreach", "bloomreach.com": "Bloomreach",
    "dxpapi.com": "Bloomreach",
    "yext.com": "Yext", "yextapis.com": "Yext",
    "searchspring.net": "Searchspring", "searchspring.io": "Searchspring",
    "klevu.com": "Klevu", "ksearchnet.com": "Klevu",
    "typesense.net": "Typesense", "typesense.org": "Typesense",
    "elastic.co": "Elastic", "found.io": "Elastic",
    "meilisearch.com": "Meilisearch", "meilisearch.io": "Meilisearch",
    "unbxd.io": "Unbxd", "unbxdapi.com": "Unbxd", "netcoreunbxd.com": "Unbxd",
    "doofinder.com": "Doofinder", "doofinder.io": "Doofinder",
    "swiftype.com": "Swiftype",
    "googleapis.com": "Google", "hawksearch.com": "HawkSearch", "hawksearch.net": "HawkSearch",
    "groupbycloud.com": "GroupBy", "attraqt.com": "Attraqt", "attraqt.io": "Attraqt",
    "empathy.co": "Empathy", "nosto.com": "Nosto", "syte.ai": "Syte",
    "addsearch.com": "AddSearch", "lucidworks.com": "Lucidworks",
    "loop54.io": "Loop54", "loop54.com": "Loop54", "fact-finder.de": "FACT-Finder",
    "fact-finder.com": "FACT-Finder",
    "sajari.com": "Sajari", "search.io": "Sajari",
    "orama.run": "Orama", "bonsai.io": "Bonsai", "cludo.com": "Cludo",
    "fastsimon.com": "Fast Simon", "fast.co": "Fast Simon",
}

# Vendor marketing sites (default run when no --vendor and no domain).
VENDOR_SITES: list[tuple[str, str]] = [
    ("Algolia", "https://www.algolia.com"), ("Constructor.io", "https://constructor.io"),
    ("Coveo", "https://www.coveo.com"), ("Bloomreach", "https://www.bloomreach.com"),
    ("Yext", "https://www.yext.com"), ("Searchspring", "https://www.searchspring.com"),
    ("Klevu", "https://www.klevu.com"), ("Typesense", "https://typesense.org"),
    ("Elasticsearch", "https://www.elastic.co"), ("Meilisearch", "https://www.meilisearch.com"),
    ("Unbxd", "https://unbxd.com"), ("Doofinder", "https://www.doofinder.com"),
    ("Nosto", "https://www.nosto.com"), ("AddSearch", "https://www.addsearch.com"),
    ("Cludo", "https://www.cludo.com"), ("HawkSearch", "https://www.hawksearch.com"),
]

_STATIC_EXT = (
    ".js", ".mjs", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif",
    ".ico", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".webm", ".map", ".wasm",
)
_NOISE = (
    "google-analytics.com", "analytics.google.com", "googletagmanager.com",
    "google.com/pagead", "google.com/ccm", "googlesyndication.com", "doubleclick.net",
    "facebook.com", "facebook.net", "bing.com/bat", "clarity.ms", "hotjar.com",
    "hotjar.io", "newrelic.com", "nr-data.net", "sentry.io", "segment.com", "segment.io",
    "cookielaw.org", "onetrust.com", "fonts.googleapis.com", "fonts.gstatic.com",
    "gstatic.com", "googleadservices.com", "linkedin.com", "licdn.com", "tiktok.com",
    "twitter.com", "snapchat.com", "pinterest.com", "cloudflareinsights.com",
    "demdex.net", "adobedtm.com", "omtrdc.net", "6sense.com", "qualtrics.com",
    "drift.com", "intercom.io", "amplitude.com", "mixpanel.com", "fullstory.com",
    "datadoghq.com", "browser-intake", "launchdarkly.com", "optimizely.com",
    "dreamdata.cloud", "dreamdata.io", "vidyard.com", "adroll.com", "adsrvr.org",
    "bizible.com", "marketo.net", "munchkin.marketo", "pardot.com", "hubspot.com",
    "hs-analytics.net", "hs-scripts.com", "zoominfo.com", "g2crowd.com",
)
# STRONG signal: search-specific endpoint PATHS (structural, vendor-agnostic).
_STRONG_PATHS = (
    "/search", "/queries", "/query", "/autocomplete", "/suggest", "/typeahead",
    "/instantsearch", "/instant", "/indexes/", "/collections/", "/rest/search",
    "/sayt", "/multi_search", "/find", "/facet", "/_search", "/v1/search",
    "/api/search", "/discovery", "/recommend",
)


def registrable(host: str) -> str:
    host = host.lower().split(":")[0]
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    two = ".".join(parts[-2:])
    if two in {"co.uk", "com.au", "co.jp", "co.nz", "com.br", "co.in", "org.uk"}:
        return ".".join(parts[-3:])
    return two


def is_static(url: str) -> bool:
    return urlparse(url).path.lower().endswith(_STATIC_EXT)


def is_noise(url: str) -> bool:
    low = url.lower()
    return any(n in low for n in _NOISE)


def has_strong_path(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(tok in path for tok in _STRONG_PATHS)


# Vendor fingerprints — distinctive header-keys / host / param tokens in the PACKET.
# Used ONLY to unmask a vendor (incl. proxied behind a first-party host). Real data:
# these are documented vendor API contracts, not guesses. No match -> fall back to host.
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
    ("nosto.com", ("nosto.com",)),
    ("yext.com", ("yextapis.com", ".yext.com")),
    ("loop54.io", ("loop54.io", "loop54.com")),
    ("fact-finder.de", ("fact-finder.de", "fact-finder.com", "factfinder")),
    ("addsearch.com", ("addsearch.com",)),
    ("cludo.com", ("cludo.com",)),
    ("hawksearch.com", ("hawksearch.com", "hawksearch.net")),
    ("attraqt.com", ("attraqt.com", "attraqt.io", "fredhopper")),
    ("syte.ai", ("syte.ai",)),
    ("fastsimon.com", ("fastsimon.com", "fast.co/search")),
)


def fingerprint(c: Captured) -> str | None:
    """Return the canonical vendor domain if the packet carries a vendor signature."""
    blob = (c.url + " " + c.body + " " + " ".join(c.headers.keys())).lower()
    for domain, toks in _FINGERPRINTS:
        if any(t in blob for t in toks):
            return domain
    return None


def carries_query(url: str, body: str) -> bool:
    return _QTOKEN in (url + " " + body).lower()


# ── Per-vendor deep extractors (real packet data only) ─────────────────────
def _algolia(hits: list[Captured]) -> dict:
    d: dict = {}
    for h in hits:
        if not d.get("app_id"):
            m = re.search(r"https?://([a-z0-9]{8,})-?(?:dsn)?[.-]", h.url, re.I)
            if m:
                d["app_id"] = m.group(1).upper()
        for k, src in (("app_id", "x-algolia-application-id"), ("api_key", "x-algolia-api-key")):
            if not d.get(k) and h.headers.get(src):
                d[k] = h.headers[src]
        qs = parse_qs(urlparse(h.url).query)
        for k, p in (("app_id", "x-algolia-application-id"), ("api_key", "x-algolia-api-key")):
            if not d.get(k) and qs.get(p):
                d[k] = qs[p][0]
        if not d.get("agent") and qs.get("x-algolia-agent"):
            d["agent"] = qs["x-algolia-agent"][0]
        if h.body:
            try:
                b = json.loads(h.body)
                reqs = b.get("requests") if isinstance(b, dict) else None
                if reqs:
                    idx = sorted({r.get("indexName") for r in reqs if r.get("indexName")})
                    if idx:
                        d["indexes"] = idx
            except Exception:
                pass
        if d.get("app_id"):
            d["app_id"] = d["app_id"].upper()
    return d


def _constructor(hits: list[Captured]) -> dict:
    d: dict = {}
    for h in hits:
        qs = parse_qs(urlparse(h.url).query)
        if not d.get("api_key") and qs.get("key"):
            d["api_key"] = qs["key"][0]
        if not d.get("client") and qs.get("c"):
            d["client"] = qs["c"][0]
        path = urlparse(h.url).path
        for t in ("autocomplete", "search", "browse", "recommendations"):
            if f"/{t}/" in path or path.endswith(f"/{t}"):
                d["endpoint_type"] = t
    return d


def _coveo(hits: list[Captured]) -> dict:
    d: dict = {}
    for h in hits:
        m = re.search(r"https?://([^.]+)\.org\.coveo\.com", h.url, re.I)
        if m and not d.get("org_id"):
            d["org_id"] = m.group(1)
        if h.headers.get("authorization") and not d.get("token"):
            d["token"] = h.headers["authorization"].replace("Bearer ", "")[:18] + "…"
    return d


def _generic(hits: list[Captured]) -> dict:
    d: dict = {}
    for h in hits:
        qs = parse_qs(urlparse(h.url).query)
        for cand in ("key", "apiKey", "api_key", "siteId", "account_id", "domain_key",
                     "experienceKey", "ticket", "hashid", "uid", "engine_key"):
            if qs.get(cand) and not d.get("key"):
                d["key"] = qs[cand][0]
        for hk in h.headers:
            if hk.endswith("-api-key") and not d.get("header_key"):
                d["header_key"] = h.headers[hk]
        m = re.search(r"/(?:indexes|collections|engines)/([^/?]+)", urlparse(h.url).path)
        if m and not d.get("index"):
            d["index"] = m.group(1)
    return d


def _extractor_for(domain: str):
    if domain in ("algolia.net", "algolianet.com"):
        return _algolia
    if domain in ("cnstrc.com", "constructor.io"):
        return _constructor
    if domain == "coveo.com":
        return _coveo
    return _generic


@dataclass
class Captured:
    url: str
    method: str
    rtype: str
    headers: dict
    body: str


@dataclass
class Row:
    name: str
    site: str
    expected: str = ""
    status: str = "NO_ONSITE_SEARCH"
    endpoint_host: str = ""
    vendor_domain: str = ""
    vendor_label: str = ""
    app_id: str = ""
    details: dict = field(default_factory=dict)
    sample_endpoint: str = ""
    api_calls: int = 0
    confirmed_calls: int = 0
    all_vendors: list[str] = field(default_factory=list)
    proxied: bool = False
    strong: bool = False  # headline is fingerprinted or a known 3rd-party host
    note: str = ""


async def _dismiss_consent(page) -> None:
    """Click common cookie/consent accept buttons so they don't block the search box."""
    sels = (
        "#onetrust-accept-btn-handler", "#truste-consent-button",
        'button[aria-label*="accept" i]', 'button[id*="accept" i]',
        'button[class*="accept" i]', 'button[data-testid*="accept" i]',
        '[aria-label*="Accept all" i]', "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
        ".cookie-accept", ".accept-cookies", "#accept-cookies",
    )
    for sel in sels:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=600):
                await el.click(timeout=1200)
                await page.wait_for_timeout(400)
                return
        except Exception:
            continue


async def _type(page, el) -> bool:
    """Type the query with REAL keystrokes (fires as-you-type search), then submit."""
    try:
        await el.click(timeout=1500)
        await page.wait_for_timeout(250)
        await el.press_sequentially(_QUERY, delay=110)  # real key events -> autocomplete fires
        await page.wait_for_timeout(2600)                # capture as-you-type call
        await el.press("Enter")                          # full results call
        await page.wait_for_timeout(2400)
        return True
    except Exception:
        return False


async def _trigger(page) -> None:
    await _dismiss_consent(page)
    # 1) command palette (⌘K / Ctrl-K / "/") — DocSearch + many modern sites
    for combo in ("Meta+K", "Control+K", "/"):
        try:
            await page.keyboard.press(combo)
            await page.wait_for_timeout(500)
            box = page.locator(
                'input[type="search"], input[role="searchbox"], input[role="combobox"], '
                'input[placeholder*="search" i], .DocSearch-Input'
            ).first
            if await box.is_visible(timeout=700):
                if await _type(page, box):
                    return
        except Exception:
            pass
    # 2) explicit search toggle then input
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
                'input[role="combobox"]', "#searchInput", ".search-input",
                'input[autocomplete="off"]'):
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=900):
                if await _type(page, el):
                    return
        except Exception:
            continue
    # 3) conventional /search?q= URL
    try:
        b = urlparse(page.url)
        await page.goto(f"{b.scheme}://{b.netloc}/search?q={_QUERY}",
                        wait_until="domcontentloaded", timeout=10000)
        await page.wait_for_timeout(2200)
    except Exception:
        pass


async def detect(browser, name: str, site: str, expected: str = "") -> Row:
    row = Row(name=name, site=site, expected=expected)
    ctx = await browser.new_context(
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"),
        viewport={"width": 1440, "height": 900},
        locale="en-US", timezone_id="America/New_York",
    )
    page = await ctx.new_page()
    cap: list[Captured] = []

    def on_req(req: Request) -> None:
        try:
            body = req.post_data or ""
        except Exception:
            body = ""
        cap.append(Captured(req.url, req.method, req.resource_type, dict(req.headers), body))

    page.on("request", on_req)
    try:
        await page.goto(site, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)
        title = (await page.title()).lower()
        html = (await page.content())[:4000].lower()
        if ("just a moment" in title or "attention required" in html
                or "access denied" in title or "verify you are human" in html):
            row.status = "BOT_BLOCKED"
            row.note = "challenge page"
            await ctx.close()
            return row
        await _trigger(page)
    except Exception as exc:
        row.status = "ERROR"
        row.note = f"{type(exc).__name__}: {str(exc)[:70]}"
        await ctx.close()
        return row

    site_host = registrable(urlparse(page.url).netloc)
    api = [c for c in cap if c.rtype in ("xhr", "fetch")
           and not is_static(c.url) and not is_noise(c.url)]
    row.api_calls = len(api)

    # CONFIRMED search call = search-endpoint path AND carries my typed query.
    confirmed = [c for c in api if has_strong_path(c.url) and carries_query(c.url, c.body)]
    row.confirmed_calls = len(confirmed)
    if not confirmed:
        await ctx.close()
        return row  # NO_ONSITE_SEARCH

    # Aggregate confirmed calls by vendor. Vendor = packet fingerprint (unmasks proxied
    # vendors behind a first-party host) else the registrable host.
    agg: dict[str, dict] = {}
    for c in confirmed:
        host = registrable(urlparse(c.url).netloc)
        fp = fingerprint(c)
        vendor = fp or host
        a = agg.setdefault(vendor, {"hits": 0, "fp": False, "host": host, "calls": []})
        a["hits"] += 1
        a["fp"] = a["fp"] or (fp is not None)
        a["calls"].append(c)

    def tier(v: str) -> int:
        a = agg[v]
        if a["fp"]:
            return 0  # fingerprinted vendor (definitive, incl. proxied)
        if v != site_host and v in KNOWN_NAMES:
            return 1  # known third-party host
        if v != site_host:
            return 2  # unknown third-party host
        return 3      # first-party / proprietary

    ranked = sorted(agg, key=lambda v: (tier(v), -agg[v]["hits"]))
    headline = ranked[0]
    a = agg[headline]
    hits = a["calls"]

    def label(v: str) -> str:
        lab = KNOWN_NAMES.get(v, f"(unrecognised:{v})")
        if agg[v]["fp"] and agg[v]["host"] != v and registrable(agg[v]["host"]) == site_host:
            lab += " [proxied]"
        elif v == site_host:
            lab += " [first-party]"
        return lab

    row.status = "DETECTED"
    row.all_vendors = [label(v) for v in ranked]
    row.vendor_domain = headline
    row.vendor_label = label(headline)
    row.proxied = a["fp"] and registrable(a["host"]) == site_host
    row.strong = tier(headline) in (0, 1)
    row.endpoint_host = urlparse(hits[0].url).netloc
    row.details = _extractor_for(headline)(hits)
    row.app_id = row.details.get("app_id", "")
    row.sample_endpoint = hits[0].url[:140]
    await ctx.close()
    return row


async def run(targets: list[tuple[str, str, str]]) -> list[Row]:
    sem = asyncio.Semaphore(4)
    total = len(targets)
    # Stealth().use_async patches every context/page at the playwright level — far more
    # effective vs Akamai/Cloudflare than per-page application.
    async with _STEALTH.use_async(async_playwright()) as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled",
                  "--disable-features=IsolateOrigins,site-per-process"],
        )

        done = {"n": 0}

        def stream(r: Row) -> None:
            done["n"] += 1
            idkey = r.app_id or r.details.get("key") or r.details.get("org_id") or ""
            print(f"  [{done['n']:>2}/{total}] {r.name[:24]:24.24} {r.status:14.14} "
                  f"{(r.vendor_label or r.note)[:26]:26.26} {idkey}", flush=True)

        async def guarded(name, site, exp):
            async with sem:
                # Retry on a weak/failed result (flake, or first-party that may hide a
                # vendor call). A STRONG detection (fingerprinted / known 3rd-party) is
                # proven and returned immediately.
                last = Row(name=name, site=site, expected=exp)
                best = last
                result = last
                for _ in range(2):
                    try:
                        # Hard per-site ceiling so one stuck page can't stall the batch.
                        last = await asyncio.wait_for(
                            detect(browser, name, site, exp), timeout=55
                        )
                    except (asyncio.TimeoutError, Exception) as exc:
                        kind = "TIMEOUT" if isinstance(exc, asyncio.TimeoutError) else "ERROR"
                        last = Row(name=name, site=site, expected=exp, status=kind,
                                   note=f"{type(exc).__name__}: {str(exc)[:60]}")
                    if last.status == "DETECTED" and last.strong:
                        result = last
                        break
                    if last.status == "DETECTED" and best.status != "DETECTED":
                        best = last
                    elif best.status not in ("DETECTED",) and last.status != "NO_ONSITE_SEARCH":
                        best = last
                    result = best if best.status != "NO_ONSITE_SEARCH" else last
                stream(result)
                return result

        rows = await asyncio.gather(*(guarded(n, s, e) for n, s, e in targets))
        await browser.close()
    return rows


def _norm(url: str) -> tuple[str, str]:
    d = url.strip()
    if not d or d.startswith("#"):
        return "", ""
    u = d if d.startswith("http") else f"https://{d}"
    return d.replace("https://", "").replace("http://", "").rstrip("/"), u


def print_table(rows: list[Row]) -> None:
    def c(s, w):
        s = str(s or "")
        return (s[: w - 1] + "…") if len(s) > w else s.ljust(w)
    print()
    print(c("#", 3), c("Site", 26), c("Status", 15), c("Vendor (from wire)", 22),
          c("App ID / key", 16), c("endpoint host", 30), sep="  ")
    print("-" * 122)
    for i, r in enumerate(rows, 1):
        idkey = r.app_id or r.details.get("key") or r.details.get("org_id") or ""
        print(c(i, 3), c(r.site, 26), c(r.status, 15), c(r.vendor_label or r.note, 22),
              c(idkey, 16), c(r.endpoint_host, 30), sep="  ")
    print("-" * 122)
    n = len(rows)
    det = sum(1 for r in rows if r.status == "DETECTED")
    print(f"DETECTED {det}/{n} | NO_SEARCH {sum(1 for r in rows if r.status=='NO_ONSITE_SEARCH')}"
          f" | BOT {sum(1 for r in rows if r.status=='BOT_BLOCKED')}"
          f" | ERR {sum(1 for r in rows if r.status=='ERROR')}")
    if rows and rows[0].expected:
        # Expected-vendor tokens (len>=4), tolerant of file names like "_algolia_seed".
        toks = [t for t in re.split(r"[^a-z0-9]+", rows[0].expected.lower()) if len(t) >= 4]

        def is_match(r: Row) -> bool:
            lab = r.vendor_label.lower()
            return any(t in lab for t in toks)

        detected = [r for r in rows if r.status == "DETECTED"]
        match = sum(1 for r in detected if is_match(r))
        wrong = [r for r in detected if not is_match(r)]
        print(f"EXPECTED='{rows[0].expected}': matched {match}/{len(detected)} detected"
              f" | OTHER-VENDOR {len(wrong)}: {[(r.site, r.vendor_label) for r in wrong]}")


def save(vendor: str, rows: list[Row]) -> None:
    _RESULTS.mkdir(parents=True, exist_ok=True)
    out = _RESULTS / f"{vendor}.jsonl"
    with out.open("w") as f:
        for r in rows:
            f.write(json.dumps(asdict(r)) + "\n")
    print(f"saved -> {out}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--vendor":
        vendor = args[1]
        lst = _CUSTOMERS / f"{vendor}.txt"
        targets = []
        for line in lst.read_text().splitlines():
            dom, url = _norm(line)
            if dom:
                targets.append((dom, url, vendor))
        rows = asyncio.run(run(targets))
        print_table(rows)
        save(vendor, rows)
    elif args:
        dom, url = _norm(args[0])
        rows = asyncio.run(run([(dom, url, "")]))
        print_table(rows)
        r = rows[0]
        print("\nDETAIL:", json.dumps(asdict(r), indent=2)[:1200])
    else:
        rows = asyncio.run(run([(n, s, "") for n, s in VENDOR_SITES]))
        print_table(rows)
