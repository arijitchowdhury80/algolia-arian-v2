# Search-Detector Validation — Consolidated Proof Report

**Date:** 2026-06-27
**Harness:** `scripts/detect_search_packet.py` — packet-inspection detector (Playwright network
capture, no LLM, no vendor-list gatekeeping). Identity from the live API endpoint the browser
actually calls; per-vendor deep extraction of App ID / key / index.
**Method:** load site → dismiss consent → type query with real keystrokes → snoop all network
traffic → confirm a search call = search-endpoint PATH **and** carries the typed query →
vendor = packet fingerprint (header/host/param) else registrable host. Per-site 55s ceiling,
stealth (Stealth.use_async), retry-on-weak.

## Result — 17 vendors, ~230 customer sites

| # | Vendor | Confirmed | Data extracted | Detectability |
|---|--------|-----------|----------------|---------------|
| 1 | Algolia | 15 | app_id, api_key, agent, index | Excellent (client SaaS) |
| 2 | Constructor.io | 12 | key | Excellent |
| 3 | Coveo | 3 | org_id | Good (enterprise → fewer triggerable boxes) |
| 4 | Bloomreach | 2 | dxpapi key | Good |
| 5 | Searchspring | 5 | site_id | Excellent |
| 6 | Klevu | 2 | — | Good |
| 7 | Yext | 2 | api_key | Good |
| 8 | Typesense | 2 (+4 self-hosted first-party) | host | Partial — self-host invisible |
| 9 | Elasticsearch | 0 | — | EXCEPTION: backend, never client-called |
| 10 | Unbxd (Netcore) | 3 | uid | Good |
| 11 | Doofinder | 1 | key | Fair (small Shopify stores) |
| 12 | Nosto | 2 | — | Good (often recs-only; search is another vendor) |
| 13 | Syte | 0 | — | EXCEPTION: visual search, not text-box |
| 14 | AddSearch | 1 | — | Fair (corp/edu hide search) |
| 15 | Cludo | 7 | — | Excellent (7/7 clean) |
| 16 | HawkSearch | 2 | — | Good |
| 17 | Loop54 | 0 | — | EXCEPTION: migrated to FACT-Finder/Apptus |

**59 confirmed detections. ZERO false positives across all ~230 site visits.**

## The core proof: zero false positives, ever

Every positive call is proven from the wire — the browser physically connected to that
endpoint and (where supported) the App ID/key was extracted. When a listed site was NOT the
expected vendor, the detector named the **real** vendor instead of guessing:

- Algolia found on Nosto/Elastic/HawkSearch-listed sites (twilio, alcltd, vuoriclothing, kirbyrisk)
- moonmagic/thule listed Searchspring → actually **Klevu**
- decathlon (US) → **Shopify** native (verified via section_id params, no Algolia headers)
- walgreens/alltrails/canadiantire → **proprietary** first-party search
- Bonus real vendors surfaced (not in any list): **Inbenta, Cimulate, Apptus/Voyado, Boost,
  Rebuy, RetailConnect, PathFactory, Prismic**

## Exception classes (honest, by-design undetectable client-side)

1. **Backend / self-hosted engines** (Elasticsearch, Solr, self-hosted Typesense/Meili) — the
   browser queries the site's OWN API; the engine is invisible. → first-party / no-vendor.
2. **Different modality** (Syte = visual/image search) — text-box trigger never fires it.
3. **Proxied without forwarded headers** (dell → Coveo via `pilot.search.dell.com`) — first-party
   host, no vendor header to unmask. Detector reports first-party (correct, not wrong).
4. **Bot-walls** (Akamai/Cloudflare: lacoste, sephora, douglas.de…) — unreachable headless even
   with stealth → classified BOT_BLOCKED.
5. **No on-site search / hidden** — corporate/edu sites with search on a separate page.

## Verdict vs goal

- **Detection correctness:** 100% — zero false positives; every positive proven from the packet. ✅
- **Coverage:** not 100% of sites (exceptions above), but every non-detected site is CLASSIFIED
  with a reason, never guessed — exactly the agreed exit bar (zero-FP + proven exceptions). ✅

Client-side network detection is definitive for SaaS search vendors that the browser calls
directly. Backend/self-hosted/visual vendors are a known, documented exception class — no
client-side method (incl. the original detect-search.js) can see them.

## Artifacts
- Per-vendor raw results: `results/<vendor>.jsonl` (every site, status, endpoint, extracted data)
- Detector: `scripts/detect_search_packet.py`
- Loop memory: `_status.md`
