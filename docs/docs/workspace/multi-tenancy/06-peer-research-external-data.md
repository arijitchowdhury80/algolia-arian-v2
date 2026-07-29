# Peer-session research — external data layer (browser/SimilarWeb/HITL/block-signals)

Received 2026-07-02 from a parallel Claude session's research team. Folded in here as an input to the multi-tenancy synthesis (§ browser/proxy + SimilarWeb HITL scaling) and to corroborate the C1 block-detector. All findings are WebSearch/WebFetch-sourced, access date 2026-07-02. Treat vendor bypass claims skeptically (independent benchmarks only).

## A. Stealth automation tools (for the gated bot-wall Phase 3 — $0-spend decision)
Space moved from JS-property spoofing → protocol-level CDP-leak elimination; TLS/JA3-JA4 fingerprinting is the frontier none fully solve.
Independent May 2026 benchmark (7 tools, 31 targets, 651 verdicts) ranking:
**nodriver (28 OK/3 gated/0 blocked) > CloakBrowser ≈ curl_cffi > Patchright ≈ Camoufox (25 OK/3/3) > vanilla Playwright ≈ rebrowser-playwright (24 OK/2/5).**
- **playwright-extra + stealth plugin**: STALE (no core update since ~Mar 2023; stealth plugin deprecated Feb 2026). JS-only, can't patch CDP `Runtime.enable` leak. DataDome ~20-30% on standard rules, <10% advanced. **Don't build on this.**
- **Patchright** (maintained, v1.61.1 Jun 2026): source-AST patch, avoids `Runtime.enable`, Chromium-only. Best drop-in for a Playwright codebase.
- **rebrowser-patches**: narrow `Runtime.enable` fix only; benchmarked IDENTICAL to vanilla Playwright — patch alone insufficient in 2026.
- **nodriver** (ultrafunkamsterdam, active): best performer, talks CDP WebSocket directly (no Playwright shim). TLS/canvas/font fingerprints unchanged run-to-run (known gap).
- **Camoufox** (Firefox, C++ engine-level spoofing, experimental): different attack surface, dodges Chromium-specific detectors; smaller fingerprint pool = less crowd cover.
- **Akamai shifted primary detection to TLS/JA3-JA4** (Jan 2026: checks post-quantum X25519MLKEM768 key share in ClientHello) — network-stack signal NO Playwright/Firefox tool solves; only curl_cffi-style TLS impersonation addresses it, out of scope for browser automation.
**Implication for PRISM:** the plan's decision (detect+flag, $0, honesty-over-bypass) is right. IF a free best-effort swap is wanted later, **Patchright** (Chromium drop-in) or **nodriver** are the two live options; neither beats TLS-layer detection, so the honest-flag path (C1 block-detector) remains the acceptance bar. GATED (touches live browser).

## B. SimilarWeb API + alternatives (for the gated Phase 3 SimilarWeb HITL)
- **Official SimilarWeb API**: sales-led custom quote, ~$500/mo entry → $20K+/mo enterprise; no free tier; cheap self-serve web plans ($125-542/mo) are dashboard-only, NO API.
- **DataForSEO Traffic Analytics** (resells SimilarWeb-lineage data): PAYG, $50 min deposit, ~$0.0006-0.002/req; only domains with 5,000+ monthly visits. **Cheapest true-lineage option, no monthly floor.**
- **Semrush Trends API**: needs Business $499.95/mo + credit packs.
- **Cloudflare Radar API**: FREE (CC BY-NC), but network-observed rankings only — NO bounce/device-split, coarser methodology. Keyless stopgap.
- **Playwright `storageState`**: correct mechanism for cookie-replay after a human login (captures cookies+localStorage+IndexedDB, not sessionStorage).
- **The IP-binding risk is confirmed real, not hypothetical**: DataDome's `dd` cookie is IP-bound — changing IP mid-session *invalidates* it (not a soft challenge). "Impossible travel" (login-IP ≠ replay-IP) is a standard hijack signal. SimilarWeb's specific anti-bot vendor/config is unpublished, so unconfirmed either way — but this validates the plan's **same-IP login** requirement.
**Implication:** the plan's HITL same-IP login is the right call. Lower-risk alternative to HITL entirely = DataForSEO (pennies/req, SimilarWeb-lineage, but 5k-visit floor) or Cloudflare Radar (free, coarser). All GATED.

## C. HITL pause/resume design (informs Part-1 §3.2 + Cassandra supervisor)
- No off-the-shelf Telegram "pause/resume" lib — hand-rolled: agent sends message (+inline approve/reject buttons or `/done`), bot polling/webhook loop flips a DB status row, pipeline resumes on the flip.
- Libs: `python-telegram-bot` / `aiogram` (message+callback handlers only, you build pause logic).
- **Complexity tiers**: (1) solo/low-infra = DB-row/flag-file + poll loop — cheapest, de-facto pattern, good enough at low volume; (2) Celery/RQ = no native approval primitive; (3) Temporal = gold standard (`workflow.wait_condition()` on a durable signal, suspends with no held compute, replays exactly after days) BUT real infra overhead — **PIP already judged Temporal overkill, consistent with this**.
- **Verdict**: PRISM should use **DB-row + poll** for the SimilarWeb HITL hook (matches the Postgres state-machine the plan already builds). Not Temporal.
- **Human-reuses-same-session** is a first-class feature on two vendors:
  - **Browserbase** Session Live View (embeddable iframe, human solves CAPTCHA/login on Browserbase's IP) + **Contexts API** persists cookies across future automated sessions. Pricing: Free 1hr, Dev $20/mo (100hr, $0.12/hr over), Startup $99/mo (500hr).
  - **Steel.dev** debug URL (`interactive=true`+`showControls=true`, iframe takeover). Pricing: Free $10/100hr, $29/mo (290hr), $99/mo (1238hr), $499/mo (9980hr).
  - Both strictly better than DIY noVNC (they bundle context/cookie persistence + IP consistency you'd otherwise build). At 20 tenants sharing ~1 login/fortnight, a **single Browserbase/Steel Dev tier (~$20-29/mo)** likely covers all HITL — cheaper than per-tenant noVNC ops burden.

## D. Unblocker / scraping-browser pricing (documented for the appendix — NOT in scope, $0-spend decision stands)
No vendor publishes per-anti-bot bypass rates (generic "advanced anti-bot" copy); vendor-specific evidence only in independent benchmarks.
- **Bright Data Scraping Browser**: ~$8-9.5/GB PAYG (~$7/GB annual) +$0.1/hr; native `page.screenshot()`; top independent benchmark scores (AIMultiple 95%, Scrape.do 98.44%).
- **Bright Data Web Unlocker**: pay-per-success ~$1-3/1K; HTTP endpoint (HTML, no native screenshot).
- **Oxylabs Web Unblocker**: ~$9.40/GB (promo $5.64/GB 6mo); `X-Oxylabs-Render: png` header returns screenshot.
- **ScrapingBee**: $49/mo=250K credits (JS+proxy=5cr/req, hard targets 10-75cr); screenshots included. **Cheapest pilot.**
- **Zyte API**: ~$1.01/1K easy → steep for hard; screenshot ~$0.002/shot; PAYG cap-$100.
- **Browserless.io**: unit-based, $25/mo Prototyping (20K units); now BUNDLES residential/datacenter proxy + stealth + CAPTCHA solving (no longer bare browser).
**Cheapest to pilot against real DataDome retailers:** ScrapingBee $49/mo or Browserless Prototyping $25/mo. All out of scope per the locked $0-spend decision; documented as a future option only.

## E. Block-detection signals — CORROBORATES the C1 block-detector spec
Independent confirmation of the vendor signals (confidence high for DataDome/Cloudflare/Imperva; Akamai medium — no published block-page text):
- **Cloudflare**: `cf-mitigated: challenge` header is **vendor-documented, single-purpose** — check FIRST, cheapest+most reliable. Title `"Just a moment..."`, selectors `#cf-challenge-running`/`#challenge-spinner`/`input[name=cf-turnstile-response]`, `cf-ray` present on all CF responses (not block-specific).
- **Imperva**: `X-Iinfo` header **unique to Imperva** (diagnostic on presence alone), also `X-CDN: Incapsula`, cookies `incap_ses_*`/`visid_incap_*`/`nlbi_*`. **Block page often returns HTTP 200** — status-only logic misses it; body "Request unsuccessful. Incapsula incident ID".
- **DataDome**: `x-datadome` header + `datadome`/`_dd_s` cookies + `geo.captcha-delivery.com` iframe + `var dd = {...}` object; 403 common (400-500 range); body "you have been blocked".
- **Akamai**: `_abck` + `bm_sz` cookies, `bmak.js` sensor script; 403; body "Access Denied"/"Pardon Our Interruption"/"Reference #<n>". No stable DOM id (per-deployment obfuscation).
- **Recommended priority**: header match (CF cf-mitigated, Imperva X-Iinfo) → cookie name → iframe/script src substring → title/body text; first match wins. **Require 2+ signals for DataDome/Akamai** before positive to avoid false positives (a legit 403).
**Action:** verify C1's classifier honors — (1) Imperva detection on HTTP 200 (don't gate on status), (2) `cf-mitigated` header check, (3) 2-signal threshold for DataDome/Akamai. Feed to C1 reviewer.
