# F — Scout vs WebFetch: Empirical A/B Evidence

**Question:** Should the algolia-* skills embed Scout (PRISM's crawler) in place of raw WebFetch/WebSearch for data-gathering?
**Method:** Real targets, both methods run on the *same URL*, scored on usable-data / quality / completeness / JS-WAF-PDF handling / signal. No mock data.
**Date:** 2026-06-28 · **Run by:** scout-eval agent
**Scout:** http://localhost:8421 (crawl4ai 0.7.7, scout 0.1.0), auth `X-API-Key: dev-key`. Confirmed healthy before testing.
**Raw outputs:** `./scout-ab-raw/*.json` (Scout responses). WebFetch answers quoted inline below.

---

## VERDICT TABLE (per data-type)

| # | Data-type | Target | Scout result | WebFetch result | Winner | Recommendation |
|---|-----------|--------|--------------|-----------------|--------|----------------|
| 1 | Company About / Leadership | petsmartcorporate.com/our-leaders (Squarespace) | md **EMPTY (4 chars)** on every page of site; raw_html (304K) HAS all 6 C-suite names+titles but needs custom parse | Clean **17-person table**, names+titles, zero effort | **WebFetch** | KEEP CURRENT for Squarespace/JS bio-card sites |
| 2 | Careers behind ATS | careers.chewy.com (Workday API) | Landing page clean (4.6K, depts only); job listings = unresolved `${pageStateData}` placeholders, **0 jobs** | "**NO JOB LISTINGS FOUND**" | **Tie (both lose on jobs)**; Scout wins landing-page context | HYBRID — neither gets ATS jobs; use `detect-search`/Apify job board, not page scrape |
| 3a | Investor Relations page | investor.chewy.com (Q4 .aspx) | **EMPTY (1 char)**, even w/ 9s wait + magic | "**NO PRESS RELEASES FOUND**" | **Tie (both lose)** | KEEP CURRENT — Q4 .aspx defeats both; use Yahoo/SEC MCP instead |
| 3b | PDF extraction | Amazon AR + Apple 10-K PDFs (both HTTP 200, app/pdf) | **EMPTY (1 char)** on BOTH PDFs — PDF extraction broken in this deploy | "**CANNOT EXTRACT PDF**" (can't decode binary) | **Tie (both lose)** | NEITHER — real PDF parser needed regardless of skill doc's claim |
| 4 | Industry benchmark | baymard.com/research/ecommerce-search | **11,608 chars clean structured md** (108×"search", 19×"benchmark") | Got data too (NOT blocked as skill assumed); tighter pre-summary | **Scout** (fuller raw extraction) | **EMBED SCOUT** for industry benchmark pages |
| 5 | Competitor search page | chewy.com/s?query=dog+food (Akamai WAF) | **EMPTY (1 char)**, stealth+simulate_user didn't beat WAF | **HTTP 429** Too Many Requests | **Tie (both lose)** | KEEP CURRENT path — use `detect-search` (Playwright) for competitor search-tech, not raw scrape |
| 6 | Newsroom / press | petsmartcorporate.com/press-releases (Squarespace) | md EMPTY (4 chars) — same Squarespace md bug; raw_html 113K shell, thin release content | "NO PRESS RELEASES FOUND" (page genuinely sparse) | **Tie / inconclusive** (thin source) | KEEP CURRENT; revisit if Squarespace md bug fixed |

**Net:** Scout decisively wins **1 of 6** (industry benchmark). WebFetch wins **1 of 6** (leadership). The other **4 are ties where BOTH fail** (ATS jobs, Q4 IR, PDF, WAF e-commerce). Scout did NOT broadly beat WebFetch. The audit's hardest data-types are unmet by *either* tool.

---

## CRITICAL FINDINGS (the load-bearing ones)

### F1 — Scout markdown conversion is BROKEN on Squarespace sites (reproducible)
Every page on petsmartcorporate.com (Squarespace) returns **4-char empty markdown** — leadership, about, press — even with `use_js:true`, `wait_for:"img"`, `wait_for_timeout:6000`, `formats:["markdown"]`. The `raw_html` is fetched correctly (304K chars, all 6 exec names + titles present in `alt` attributes). So Scout *retrieves* the page but its HTML→markdown step yields nothing for this CMS.
- **Impact:** This is the **company-intel leadership use case where Scout is ALREADY embedded** (collect-company.py → scout_company.py). For Squarespace-hosted corporate sites, that embedded path is silently returning empty markdown today. The skill doc's own fallback ("use formats:['raw_html'] and parse cards") is the only thing that works — but that requires bespoke parsing, which WebFetch does for free.
- **Evidence:** `scout-ab-raw/t1_scout2.json` (md=4, html=303861, names Hicks/Schnaid/Duarte/Goldberg/Redfield/Bundy all in html). Extracted titles via regex on `alt=`:
  - Alan Schnaid — EVP and Chief Financial Officer
  - Jesica Duarte — EVP and Chief Commercial Officer
  - David Redfield — EVP and Chief Operating Officer
  - Erick Goldberg — EVP and Chief Human Resources Officer
  - Lacey Bundy — EVP, Chief Legal Officer and Secretary

### F2 — Scout PDF extraction returns empty (skill doc claims native support)
Two real, reachable PDFs (Amazon 2023 AR via q4cdn 1.3MB app/pdf HTTP 200; Apple 10-K via cloudfront) both returned **1-char markdown** from `/scrape`. The skill doc explicitly says "Scout's /scrape handles PDFs natively." In this deployment it does not.
- **Evidence:** `scout-ab-raw/t3b_scout.json`, `t3b_apple.json` (both md=1, no error field).
- WebFetch also can't read PDFs (returns raw binary). **So PDF extraction is unmet by both** — the investor/financial PDF need requires a dedicated PDF parser (pdfplumber/pymupdf), not either of these.

### F3 — Scout WON on the JS-heavy content page WebFetch was assumed to fail (Baymard)
Baymard returned **11.6K chars of clean structured markdown** from Scout — the single clearest win. (Notably WebFetch was *not* blocked on Baymard this run, contradicting the skill's documented "Baymard blocks WebFetch" assumption — but Scout still returned more complete raw content for multi-stat extraction.)
- **Evidence:** `scout-ab-raw/t4_scout.json` (md=11608).

### F4 — ATS jobs and WAF e-commerce defeat BOTH tools
- careers.chewy.com: Scout gets landing page but jobs are a JS/ATS API call → unresolved `${pageStateData.searchKeyword}` template literals, 0 jobs. WebFetch: "NO JOB LISTINGS FOUND". (`t2b_scout.json`)
- chewy.com search (Akamai): Scout 1 char even with `magic:true, simulate_user:true`; WebFetch HTTP 429. (`t5_scout2.json`)
- **Implication:** For competitor search-tech and live job listings, the right tool is the Playwright-based `detect-search` skill / Apify job-board actors — neither raw Scout nor WebFetch.

### F5 — Q4 .aspx investor platforms defeat BOTH
investor.chewy.com (Q4 Inc) returned 1 char from Scout (9s wait + magic) and "NO PRESS RELEASES FOUND" from WebFetch. Financial/investor data should come from Yahoo Finance MCP + SEC EDGAR (already the skill path), not page scraping.

---

## MEASUREMENTS (Scout, exact)

| Test | Scout md chars | Scout html chars | dur_ms | got-usable-data |
|------|---------------:|-----------------:|-------:|:---------------:|
| T1 leadership | 4 | 303,861 | 1,794 | only via raw_html |
| T2 careers (landing) | 4,595 | 0 | 3,295 | partial (no jobs) |
| T3a IR | 1 | 0 | 3,268 | NO |
| T3b PDF | 1 | 0 | 2,383 | NO |
| T4 baymard | 11,608 | 0 | 2,684 | **YES** |
| T5 competitor | 1 | 0 | 6,010 | NO |
| T6 newsroom | 4 | 113,549 | 2,638 | NO (thin src) |

Scout speed is good (1.7–6s). The failure mode is content, not latency.

---

## PER-SKILL EMBED RECOMMENDATION

| Skill | Fetch step | Switch to Scout? | Why |
|-------|-----------|:----------------:|-----|
| algolia-intel-industry | Baymard / benchmark pages | **YES — EMBED** | Only decisive Scout win; 11.6K clean md vs WebFetch summary. Best ROI. |
| algolia-intel-company | leadership/about (Squarespace) | **NO (until F1 fixed)** | Scout md empty on Squarespace; already-embedded path is degraded. Add raw_html fallback parser OR keep WebFetch. |
| algolia-intel-hiring | ATS job listings | **NO** | Scout can't render ATS jobs; keep WebSearch/job-board path. |
| algolia-intel-investor / -financial-* | IR pages + PDFs | **NO** | Both fail Q4 .aspx + PDF. Stay on Yahoo MCP + SEC EDGAR; add real PDF parser. |
| algolia-intel-competitors | competitor search page | **NO** | WAF defeats Scout; use `detect-search` (Playwright). |
| algolia-intel-news | newsroom/press | **NO (inconclusive)** | Tie; revisit after F1 Squarespace fix. |

---

## BOTTOM LINE
Evidence does **not** support broadly embedding Scout. Embed it for **industry-benchmark pages only** (clear win). For everything else, current methods tie or win, and the genuinely hard cases (ATS jobs, WAF e-commerce, Q4 IR, PDFs) are unsolved by both — those need the right specialized tool (`detect-search` / Apify / Yahoo+SEC MCP / a real PDF parser), not a fetch-tool swap. Fix F1 (Scout Squarespace markdown) and F2 (Scout PDF) before reconsidering the company/news/investor steps.
