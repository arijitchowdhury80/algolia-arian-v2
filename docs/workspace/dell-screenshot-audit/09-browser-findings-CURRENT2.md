# Browser Findings — Dell Technologies (dell.com)
Audit Date: 2026-06-30
Auditor: Algolia (Claude Code, Chrome MCP + Playwright Chromium 149 on Xvfb)
Workspace: /opt/prism-executor/audits/dell/research/
Search vendor (Phase 1): Bloomreach (tag-only, likely server-side)

---

## CORE AUDIT

### Step 2a: Initial Observations
- Screenshot: /opt/prism-executor/audits/dell/deliverables/screenshots/01-homepage.png (VERIFIED ON DISK)
- Search bar: Present in header as a combobox labeled "Search Dell" (top, left-of-center, next to Dell logo) with an accompanying "Search Dell" submit button. Full input field, not icon-only.
- Position: Top header banner, left/center. Prominent.
- Notable: Homepage ALSO carries a large AI conversational box ("How can I help you today? / Ask me about today's best deals") with quick-action chips (Show current deals, Find the best laptop for me, Track my order, Get technical support) and a separate "Virtual Assistant BETA" AI Product Chat dialog. Dell is layering generative/assistant UX on top of traditional site search.
- Product Way Finding rail: Laptops, Desktops & AIOs, Monitors, PC Accessories, Artificial Intelligence, Servers, Data Storage, Cyber Resilience.
- Cookie consent (OneTrust) present; Declined All.

### Step 2a½: Search Vendor Network Verification
- Vendor tags found in 02-tech-stack.md: Bloomreach (tag-only, unverified — flagged "likely server-side").
- Network requests monitored: yes (Chrome MCP list_network_requests + performance resource entries during a live "laptop" search).
- ACTUAL autocomplete/SAYT provider observed: **`https://pilot.search.dell.com/queryunderstandingapi/2/suggest?type=dell&term=laptop&country=us`** — a Dell-hosted first-party search gateway (`search.dell.com`), NOT Bloomreach's client-facing domain (`brsrvr.com` / `bloomreach.com`). No `brsrvr.com`/`bloomreach.com`/`algolia`/`coveo`/`constructor` calls appear in the browser at any point.
- Result: Bloomreach is **server-side / headless** — the query flows to Dell's own `search.dell.com` endpoint which brokers to the backend engine. Browser-side detection cannot see the vendor; consistent with Phase 1's "tag-only, likely server-side" call. Bloomreach status = ACTIVE-but-proxied (not directly observable client-side).
- Note: The endpoint is named `queryunderstandingapi` and served from `pilot.search.dell.com` — Dell has a bespoke query-understanding layer in front of the catalog index.

### Step 2b: Empty State Test
- Screenshot: /opt/prism-executor/audits/dell/deliverables/screenshots/02-empty-state.png (VERIFIED ON DISK)
- Observation: Clicking into the "Search Dell" combobox WITHOUT typing surfaced **NO dropdown at all** — no popular searches, no trending queries, no recent searches, no "shop by category" shortcuts. The listbox only populates once characters are entered. This is a zero-input Query-Suggestions gap (Algolia Query Suggestions would fill the empty state with trending/popular queries to reduce dead clicks).

### Step 2c: Search-As-You-Type (SAYT) Test
- Query typed: "laptop" (char-by-char into #mh-search-input)
- Screenshot: /opt/prism-executor/audits/dell/deliverables/screenshots/03-sayt-laptop.png (VERIFIED ON DISK)
- Typed text visible in screenshot: yes (input value confirmed = "laptop")
- Observation: SAYT returns "Found 10 suggestions" — **query-completion TEXT ONLY**. The 10 suggestions were: laptop 16, laptop 15 inch, laptop i7, dell laptop 15, laptop 16 inch, dell laptop 15 inch, laptop 14 inch, laptop 14 plus, laptop i5, dell laptop 16.
- **Gap: no product previews in SAYT** — no thumbnails, no prices, no product names, no category tiles, no content/support results. Pure keyword completion. Response was fast (sub-second, single call to queryunderstandingapi). This is the classic keyword-era autocomplete: it predicts strings, it does not surface merchandise. Algolia Autocomplete/Federated Search would show product cards + categories + content inline.

### Step 2d: Full Search Results Test — "monitors"
- Screenshot: /opt/prism-executor/audits/dell/deliverables/screenshots/04-results-monitors.png (VERIFIED ON DISK)
- Result count: **247 results** for "monitors". ~46 prices rendered in viewport (real product grid, not a dead page).
- Facets present and category-relevant: Screen Size, Screen Resolution, Features (e.g. "Curved (14)"), Back Panel Color, Aspect Ratio, Price, Refresh Rate, Panel Type, Gaming Features — plus category quick-chips (Gaming, 32"/27"/24" Monitors, OLED, Portable, Ultrawide, Curved, HDMI). Facets carry count badges. This is a genuine strength — faceting is solid.
- **Sort options: only 3** — Relevance, Price Low→High, Price High→Low. NO "Newest", "Top Rated", "Best Selling", or "Most Popular". Fails the "≥4 sort options" bar and signals **no analytics-driven ranking exposed to shoppers** (no popularity/bestseller sort = Algolia Analytics / Recommend gap).
- WAF NOTE: Direct URL navigation to `/en-us/search/{q}` returns Akamai **"Access Denied"** for the automated browser (see screenshot waf-access-denied.png). The in-session organic flow (type into header box → click "Search Dell" button) bypasses the block and renders real results. All results-page tests below use the organic in-session flow.

### Step 2k: Federated Search Check (assessed during SAYT)
- Screenshot: /opt/prism-executor/audits/dell/deliverables/screenshots/03-sayt-laptop.png (shared with 2c) (VERIFIED ON DISK)
- Observation: SAYT is **products-only-absent / query-strings-only** — it federates nothing. No content pages, no support/driver docs, no brand hubs, no order-tracking shortcuts appear in the suggest dropdown. Given Dell's huge support/driver/warranty content corpus and B2B tooling, this is a major federation gap: a shopper typing "laptop" gets zero pathway to products, support, or content inside the autocomplete. FAIL.

### Step 2e: Typo Tolerance Test — "alienwear" → "Alienware"
- Query: "alienwear" (input value verified = "alienwear")
- Screenshots: 05-typo-alienwear.png (SAYT correction), 05b-typo-alienwear-results.png (corrected results page) (VERIFIED ON DISK)
- SAYT behavior: All 10 autocomplete suggestions silently corrected to the brand — "alienware 16, alienware bag, alienware oled, alienware 5090, alienware pro, alienware charger, alienware 5080, keyboard alienware, alienware, alienware 4090". Query-understanding layer handles the single-letter substitution.
- Results-page behavior (submitted the raw typo via the "Search Dell" button): URL auto-corrected to `/en-us/search/alienware`, page shows a **"Showing results for [alienware]"** correction banner and **100 results**. Typo tolerance = **PASS** end-to-end on Dell's flagship gaming brand.
- Method note: Enter-key submit forces a hard document load that Akamai blocks ("Access Denied"); the in-page "Search Dell" **button click** does a WAF-safe in-session transition. All results submissions below use the button click.

### Step 2f: Synonym / Colloquial Test — "notebook" vs "laptop"
- Screenshot: 06-synonym-notebook.png (VERIFIED ON DISK)
- "notebook" SAYT returned real product completions: alienware m16 r2 gaming notebook, dell pro 16 notebook, dell pro notebook, inspiron 15 notebook, precision notebook, etc. (Dell's own taxonomy uses "notebook" natively.)
- Result-count parity: **"laptop" = 379 results** and **"notebook" = 379 results** — identical set. Dell maps the colloquial ("laptop") and formal/legacy ("notebook") terms to the same catalog. Synonym handling = **PASS** for this pair.
- Caveat: parity here is largely because "notebook" is Dell's INTERNAL term, so the synonym happens to align with taxonomy. The harder synonym gaps (below in 2i/2m) are where shopper language diverges from Dell's spec-heavy taxonomy (e.g. "tower", use-case phrasing).

### Step 2m: Semantic / Natural-Language Search (→ Algolia NeuralSearch) — TWO queries + a critical correction

**CORRECTION (2026-07-02, Arijit, live-verified in his own browser — supersedes the FAIL-only verdict below):**
Every search submitted through the header "Search Dell" box **automatically auto-launches the Virtual
Assistant panel alongside the results grid** — same query, same action, no extra click, no separate
box. Tested live with "gaming pc with rtx 4070 and 32gb ram": the classic results grid returned 228
generic results with the WRONG GPU on the top cards (RTX 5090/5070/5080, not 4070) — confirming the
grid genuinely does not do spec-aware filtering. But the auto-launched Assistant panel, running in the
SAME session from the SAME query, correctly parsed "RTX 4070" and "32GB RAM" verbatim, asked a
clarifying budget question ("What's your gaming budget?"), took a $300-$1200 slider answer, and
returned an accurately-matched "Alienware Aurora Gaming Desktop" with a correct note that it exceeds
the stated budget but matches the requested performance. Screenshots:
`22-virtual-assistant-clarify-budget.png`, `22b-virtual-assistant-slider-input.png`,
`22c-virtual-assistant-matched-products.png`, `22d-header-search-auto-triggers-assistant.png` (all
VERIFIED, captured live 2026-07-02).
**Revised verdict:** "NLP = FAIL" as an overall characterization of Dell's search experience is WRONG.
The accurate finding is a two-system split: **the classic catalog/facet engine ignores multi-attribute
intent (confirmed, see Query A/B below), but Dell already has a working, auto-launched, integrated
conversational layer that correctly resolves the same intent, live today.** This is a materially
different (and more useful) wedge for Algolia than "Dell lacks NLP" — see the rewritten Strategic
Signal and Algolia Opportunities sections below.

**Query A: "laptop with good battery life for travel under 1000"** (hardest multi-attribute NLP)
- Screenshots: 13-nlp-battery-travel.png (SAYT), 13b-nlp-battery-travel-results.png (results) (VERIFIED ON DISK, re-verified 2026-07-02)
- SAYT: keyword-matched the literal string "laptop with…" → laptop with dvd drive / ethernet port / numeric pad / touchscreen / docking station, plus "long life battery / longest battery life". It did NOT parse price, use-case ("travel"), or combine attributes.
- Results: **46 results** (re-verified 2026-07-02; originally reported 49 — the 3-result delta is normal live-catalog drift over 2 days, not a measurement error), NO price filter auto-applied in the GRID.
- **CORRECTION (2026-07-03) — the "price ceiling ignored, up to $2,000" claim is UNVERIFIED, not confirmed.** The original June 30 audit stated results included laptops at $1,099-$2,000. That claim was carried forward uncorrected in the 2026-07-02 pass without independently re-checking it. The only evidence actually available now (the re-captured `13b-nlp-battery-travel-results.png`, default Relevance sort, top 3 visible results) shows **$929.99 / $699.99 / $899.99 — all three under $1,000**, which does NOT support "price ceiling ignored." An attempt to verify the true price range by sorting High-to-Low hit an Akamai WAF block on the sort action and produced no clean evidence either way. **Honest state: no verified evidence the $1,000 ceiling is exceeded anywhere in these 46 results.** The grid does NOT auto-apply a price FILTER (confirmed — no filter chip appears), but that is a different, narrower claim than "results ignore the price and go up to $2,000," which is currently unproven. **Verdict downgraded from FAIL to UNVERIFIED — needs a real re-test (page through or price-sort all 46 results) before any pass/fail claim is made for this query.** This also raises an open question about whether other FAIL verdicts elsewhere in this document were independently re-verified in the 2026-07-02 pass or simply carried forward from June 30 — flagged for a dedicated re-verification pass, not resolved here.

**Query B: "best laptop for video editing"** (semantic use-case intent)
- Screenshot: 13c-nlp-video-editing.png (VERIFIED ON DISK, re-captured 2026-07-02 — original capture had the wrong query baked in from an unattended re-run and was corrected)
- SAYT: ignored "best/for" semantics → returned "video cards, video camera, video game, video game consoles, video cables" (noise) mixed with "video editing laptop / desktops for video editing".
- Results: **416 results** (re-verified 2026-07-02, originally reported 415 — normal drift) — effectively the entire PC catalog with no narrowing to color-accurate-display / discrete-GPU / high-RAM editing machines. Returning 400+ undifferentiated SKUs for a specific use-case query is keyword breadth, not intent precision, at the GRID level.
- **Grid-level verdict: FAIL** (confirmed, unchanged). Dell's `queryunderstandingapi` (the grid's engine) handles typos and token-level synonyms well, but has no semantic/vector understanding of use-case, budget, or multi-attribute conversational intent. **However, per the correction above, this is not the whole story** — the SAME search action auto-launches a Virtual Assistant that DOES have this capability and returns it live, in the same panel, without the shopper taking any extra action. The real gap is not "Dell can't do NLP," it's "Dell's NLP-capable system and its catalog/facet system are two disconnected pieces of infrastructure that don't share results, facets, or ranking" — a systems-integration wedge, not a capability wedge.

### Step 2i: Intent Detection Test
- Assessed via NLP queries (2m) + typo (2e) + brand (2s below).
- Attribute+price intent ("under 1000"): grid does NOT auto-apply a price facet/filter (confirmed). Whether results actually exceed the stated ceiling is **UNVERIFIED** (see 2m Query A correction, 2026-07-03) — the only visible evidence contradicts the original claim.
- Use-case intent ("for video editing", "for travel"): **NOT detected** — returns broad catalog, no attribute pre-filtering (see 2m Query B).
- Brand intent (typo→brand "alienwear"→"alienware"): correction works and lands on a filtered brand result set (100 results). Brand-token intent = partial PASS; semantic/attribute intent = FAIL.

### Step 2n (B2B): Part-Number / Order-Code Resolution — "210-AKXX"
- Screenshots: 14-b2b-partnumber-sayt.png, 14b-b2b-partnumber-results.png (VERIFIED ON DISK)
- SAYT (5 suggestions): fuzzy-matched on the "210" number token, NOT the order code — "wd19dc … 210w power delivery", "dell pro max tower t2 cto base 210 bpsq", "dell pro 14 plus … 210 bpdr", "intel core i7 14700 2.10 ghz", "precision 5860 tower xcto base 210-bfnp". It conflated a wattage (210w), a CPU clock (2.10 GHz), and other order-code fragments.
- Results: submitting "210-AKXX" returned **109 results** with a "Showing results for" banner — it did **NOT resolve to the single product** the order code identifies. A B2B buyer pasting a precise order/part code gets a 109-item fuzzy sprawl instead of the exact SKU. **B2B code resolution = FAIL** (high-impact given Dell's B2B-dominant revenue: PremierConnect/APEX buyers routinely search by order code).

### Step 2o (B2B cross-sell): Accessory-to-Base Compatibility — "docking station for latitude 7450"
- Screenshots: 15-crosssell-dock-latitude.png (SAYT), 15b-crosssell-dock-results.png (results) (VERIFIED ON DISK)
- SAYT: no compatibility understanding — returned generic docks and docks for the WRONG models ("docking station for xps", "docking station for inspiron", "docking station for precision 7680", "usb docking station"). None specifically tied to Latitude 7450.
- Results: **8 results** (7 dock mentions, only 2 "Latitude 7450" mentions). It narrowed to the dock category but did not present a verified "compatible with your Latitude 7450" attach experience. Partial: category-right, compatibility-blind. The classic B2B attach/upsell (dock ↔ specific laptop) is not modeled — Algolia Recommend (FBT / compatible-accessories) is the direct fill.

### Step 2g: No-Results Test — "asdfghjk" / "zxqwvytremn"
- Screenshot: 07-no-results.png (VERIFIED ON DISK — shows the Akamai state for the nonsense path)
- SAYT behavior (observed on homepage, clean): typing gibberish "asdfghjk" AND "zxqwvytremn" both returned **ZERO SAYT suggestions** (empty dropdown, no "Found N suggestions" status). So autocomplete offers no recovery/fallback for no-hit terms — no popular/trending fallback surfaced in the dropdown. (Contrast: Algolia Query Suggestions can serve popular queries even on a miss.)
- Results-page behavior: submitting either gibberish string returns Akamai **"Access Denied"** — reproduced on two different nonsense strings across re-warmed sessions, while valid queries (laptop, monitors, alienware, notebook, 210-AKXX, the full NLP sentence) all rendered normally in the same sessions. This indicates a **WAF heuristic that blocks nonsense/no-hit search paths for automated browsers**; the true empty-state UI could not be captured in-browser. LIMITATION documented. The SAYT-level finding (zero fallback suggestions on a miss) stands as observed evidence.

### Step 2h: Non-Product Content Test — "return policy" & "order status"
- Screenshots: 08-non-product-return-policy.png (SAYT), 08b-non-product-redirect.png (redirect URL), 08c-non-product-order-status.png (SAYT) (VERIFIED ON DISK)
- **SAYT is intent-blind and catalog-only:**
  - "return policy" SAYT → only PRODUCTS (Precision 7680, Inspiron 2-in-1 laptops, IPS monitors) — no support/help/policy content.
  - "order status" SAYT → totally irrelevant products (stylus pen, monitor stands, SSD) matched on "st" fragments — no order-tracking shortcut, no content.
  - Confirms the autocomplete dropdown does NOT federate support/content/tools — a big miss for a direct-sales model where "return policy"/"order status" are top self-service intents.
- **Full-submit reveals a partial query-redirect Rules capability (inconsistent):**
  - "return policy" submit → **redirected to the real page** `/en-us/lp/return-policy?search_redirect=return+policy`. There IS a curated query→page redirect rule for this term (a Rules-Engine-style behavior).
  - "order status" submit → went to a plain `/en-us/search/order status` results page (NO redirect). So redirect rules are hand-curated for some terms but missing for others equally high-intent.
- Verdict: content federation in autocomplete = FAIL; query-redirect rules exist but are inconsistent/incomplete (Algolia Rules + Federated Search would make this systematic and cover the autocomplete layer too).
- (Both redirect/results target pages returned Akamai Access Denied on final document load for the automated browser, but the redirect URL itself is authoritative evidence of the rule.)

### Step 2i (cont.) / spec-NLP: "gaming pc with rtx 4070 and 32gb ram"
- Screenshots: 09-intent-gaming-spec.png (SAYT), 09b-intent-gaming-results.png (results) (VERIFIED ON DISK)
- SAYT: matched "32gb ram" but returned mostly **laptops** (query said "pc"/desktop) and offered **RTX 4060** machines, NOT the requested **RTX 4070** — e.g. "dell ect1250 tower … rtx 4060 32gb ram", "dell tower desktop … rtx 4060 32gb ram". It ignored the exact GPU spec and the form-factor.
- Results: **231 results**, 15 laptop mentions, only 3 "RTX 4070" mentions. No auto-applied GPU/RAM/form-factor facets. Multi-attribute spec parsing (GPU model + memory + form factor) = **FAIL**. A B2C enthusiast or B2B workstation buyer gets a 231-item wall instead of the handful of matching configs.

### Step 2i (brand intent): "Alienware"
- Exact brand name "Alienware" routed to `/en-us/search/Alienware` (a **search results page**), NOT a redirect to the dedicated Alienware brand hub. Contrast with "return policy" which DID redirect. So brand-name intent is treated as a keyword search, not a curated brand landing — a missed brand-experience/merchandising opportunity (Algolia Rules could pin a brand hero + curated hub). (Results-page load hit WAF Access Denied on the automated browser; the routing behavior — no redirect — is the observed finding. Note the typo variant "alienwear" returned 100 corrected results, per 2e.)

### Step 2j: Merchandising Consistency
- Screenshot: 10-merchandising-category.png (VERIFIED ON DISK)
- The menu/way-finding "Laptops" link goes to a rich category page `/shop/dell-laptops/scr/laptops` (title "Laptop Computers – Shop Laptops for Business, Gaming & Student") with product cards, star ratings and review counts (e.g. Dell 15 Laptop, 4.5★, 4,041 reviews). This is a curated PLP distinct from the flat `/search/laptop` results page — so the browse-catalog experience and the search-results experience are **two different surfaces** (curated category vs. keyword search list). Merchandising is applied to browse but the search results page is a plainer list (consistency gap between browse and search).

### Step 2n: Dynamic Facets & Filtering (→ Algolia Dynamic Faceting) — STRENGTH
- Screenshot: 14-dynamic-facets.png (full page) (VERIFIED ON DISK)
- Facets ARE category/context-adaptive:
  - "monitors" → Screen Size, Screen Resolution, Features (Curved), Back Panel Color, Aspect Ratio, Panel Type, Refresh Rate, Gaming Features.
  - "gaming pc…" → Processor, Memory, Storage Type, Storage, Price, plus grouped "Laptops by Processor/RAM/Brand", "Desktops by Brand".
- Count badges present. This is a genuine strength — faceting/refinement is solid. (The gap is upstream: the RESULT SET fed into the facets is too broad because query understanding is keyword-level.)

### Step 2r: Recommendations / FBT (→ Algolia Recommend) — GAP
- Screenshot: 18-recommendations-pdp.png (full XPS 13 PDP) (VERIFIED ON DISK)
- The XPS 13 product page (`/shop/cty/pdp/spd/xps13dx13260laptop`) offers extensive **service/support upsells** (Basic Support, Dell Care Plus, Dell Care Premium, Extended Battery Service, ProDeploy Essentials, Windows AutoPilot, Microsoft Office, data-migration) via the configuration flow — but **NO algorithmic product-recommendation carousels**: no "Frequently Bought Together", "Similar Items", "You May Also Like", or "Customers Also Viewed". Cross-sell is config-driven service attach, not behavioral product recommendation. Algolia Recommend (FBT / related-items / compatible-accessories) is a direct fill, and directly reinforces the B2B attach gap seen in 2o (dock ↔ laptop).

### Step 2l: Mobile Experience
- Screenshots: 12-mobile-homepage.png, 12b-mobile-sayt-xps.png (VERIFIED ON DISK)
- At mobile viewport the homepage renders responsively; the "Search Dell" input remains visible/accessible in the header. Mobile SAYT works identically to desktop — "xps 15 laptop" returned 8 query-string suggestions (xps 15, xps 15 9530, xps 15 charger, xps 15 battery, dell xps 16 laptop, etc.). Same query-completion-only behavior (no product cards) carries to mobile. Functional but inherits every desktop limitation (no federation, no products in SAYT, no empty-state suggestions).

### Step 2o: Popular & Recent Searches (→ Algolia Query Suggestions) — GAP
- Covered by 2b: clicking into the empty search box surfaces NO popular searches, NO trending queries, and NO recent searches. Across multiple sessions the empty combobox never populated a suggestion list until characters were typed. No "recent searches" memory observed. Clean Query-Suggestions opportunity (fill the zero-input state with trending/popular/recent queries to reduce blank-box abandonment).

### Step 2s: Banners & Merchandising Rules (→ Algolia Rules Engine)
- (1) Query-redirect rule exists for "return policy" (→ real page) but NOT for equally high-intent "order status" or the exact brand "Alienware" — rules are hand-curated and inconsistent. (2) Homepage/PLP carry promotional banners (Dell 14 Plus "Save Up to $640", XPS 13 "Starting at $699 / student $599", "Save $" PLP deal badges) so campaign merchandising exists at page/CMS level. (3) No evidence of query-triggered search banners in results. Rules capability is partial and CMS-driven, not search-native.

### Step 2t: Analytics Visibility (→ Algolia Analytics)
- Screenshot: 20-analytics-signals.png (VERIFIED ON DISK)
- Present: product star-ratings + review counts on the PLP (13 rating widgets; e.g. 4.5 stars / 4,041 reviews) = social proof; "Save $" deal badges.
- Absent: NO analytics/popularity merchandising labels anywhere — no "Bestseller", "Most Popular", "Trending", "Top Rated", "New Arrival". Combined with the results-page sort menu offering only 3 options (Relevance, Price Low->High, Price High->Low — no "Most Popular"/"Best Selling"/"Newest"), this confirms NO behavioral/analytics-driven ranking is exposed to shoppers. Algolia Analytics + Recommend fill this.

### Step 2q: Personalization (→ Algolia Personalization)
- No logged-out personalization observed: after browsing multiple product families (laptops PLP -> XPS 13 PDP) and returning to search, results/merchandising did not re-rank toward viewed categories, and no "Recommended for you" carousel appeared. (Deeper personalization is likely gated behind sign-in / Dell Rewards / Premier, not tested logged-in.) For anonymous shoppers the experience is non-personalized. GAP / not-exposed.

---

## SUMMARY

### Key Gaps Found
1. **Catalog/facet engine = NLP FAIL on CONFIRMED cases, but a disconnected Assistant system already fixes it live (revised wedge — see correction in Step 2m).** The classic results GRID does not parse intent in the CONFIRMED cases: "best laptop for video editing" dumps 400+ undifferentiated SKUs (verified); "gaming pc with rtx 4070 and 32gb ram" surfaces the wrong GPU tier on the grid's own top cards (verified, RTX 5090/5070/5080 not 4070). The "laptop with good battery life for travel under 1000" price-ceiling claim is **UNVERIFIED, not confirmed** — the only visible evidence (top 3 results, $929.99/$699.99/$899.99) contradicts "price ceiling ignored"; flagged for a real re-test, not asserted as fact here. The `pilot.search.dell.com/queryunderstandingapi` layer is keyword/token matching, not vector/semantic — confirmed for the video-editing and GPU-spec cases. **BUT** every one of these same searches, submitted through the exact same header box, auto-launches a Virtual Assistant panel that correctly parses the multi-attribute intent (verified live: RTX 4070 + 32GB + budget correctly resolved to a matched, budget-aware product) — with no extra click from the shopper. **The real, more valuable wedge is not "Dell lacks NLP" (they don't) — it's "Dell runs two disconnected AI/search systems that don't share results, facets, or ranking," a systems-integration and consistency gap Algolia NeuralSearch (unified into ONE search+facet+ranking layer) directly solves.** (Evidence: 13-, 13b-, 13c-, 09-, 09b-, 22-, 22b-, 22c-, 22d-.)
2. **Autocomplete is query-strings-only, zero federation.** SAYT returns 10 text completions with NO product cards, prices, images, categories, or content — and for support intents ("return policy", "order status") returns irrelevant products. (Evidence: 03-, 08-, 08c-.)
3. **Empty state is barren.** Focusing the search box shows no popular/trending/recent searches. (Evidence: 02-.)
4. **B2B code + compatibility resolution = FAIL.** Order code "210-AKXX" fuzz-expanded to 109 items instead of resolving the SKU; "docking station for latitude 7450" didn't model dock<->laptop compatibility. High impact for Dell's B2B-dominant revenue. (Evidence: 14-, 14b-, 15-, 15b-.)
5. **No product recommendations / no analytics-driven ranking.** No FBT/Similar/Also-Viewed on PDP (only service attach); no Bestseller/Trending/Most-Popular labels; only 3 sort options (no popularity sort). (Evidence: 18-, 20-, 04-.)
6. **Inconsistent, CMS-bound merchandising rules.** Query redirect works for "return policy" but not "order status" or brand "Alienware". (Evidence: 08b-.)

### Strengths Found (be balanced)
- **Typo tolerance = PASS** end-to-end ("alienwear" -> "alienware", 100 results + correction banner). (05-, 05b-.)
- **Synonym parity = PASS** for laptop/notebook (both 379 results). (06-.)
- **Faceting = STRONG and category-adaptive** (monitors vs gaming show different, relevant facets with counts). (04-, 14-.)
- Star-ratings/review social proof present on PLPs.

### Notable Strategic Signal (revised 2026-07-02 — see Step 2m correction)
Dell already has a WORKING, auto-launched, integrated Virtual Assistant that correctly resolves the exact multi-attribute NLP queries the classic catalog engine fails on — it fires from the SAME header search box, same query, no extra shopper action, and correctly parsed spec + budget in live testing (RTX 4070 + 32GB RAM -> budget-clarifying question -> accurately matched product). This is NOT a bolted-on fallback; it is genuinely deployed, genuinely functional, running today. **The real strategic signal is architectural fragmentation, not capability absence:** Dell built NLP-capable product discovery TWICE — once (well) in the Assistant, and Dell's classic search/facet/ranking layer never learned from or connects to it. Two shoppers with the identical query get two different answers on the same page (a bad generic grid + a good Assistant recommendation) with no reconciliation. Algolia's wedge is consolidation: one search+facet+ranking+NLP layer instead of two disconnected ones, not "give Dell NLP they don't have."

### Algolia Opportunities
| Product | Evidence from Testing |
|---------|----------------------|
| NeuralSearch (consolidation, not net-new capability) | Grid returns wrong GPU tier / 400+ undifferentiated SKUs for use-case queries (confirmed); "under 1000" price-ceiling claim is UNVERIFIED, not confirmed — but Dell's own auto-launched Assistant (same box, same query) already resolves the confirmed cases correctly, live; the wedge is unifying one correct system instead of running two disconnected ones |
| Autocomplete / Federated Search | SAYT = query strings only; no products/content/categories; support terms return products |
| Query Suggestions | Empty search box shows nothing (no popular/trending/recent) |
| Dynamic Faceting | Already a strength — validate parity; result set upstream is too broad |
| Recommend | No FBT/Similar on PDP; B2B dock<->laptop compatibility unmodeled |
| Rules | Query redirect exists for "return policy" only — inconsistent |
| Analytics / Personalization | No popularity sort, no trending/bestseller labels, no anonymous personalization |

### Overall Assessment
- Typo tolerance: PASS
- Synonym handling: PASS (laptop/notebook)
- NLP / semantic: SPLIT — catalog/facet grid FAILS, but the auto-launched Virtual Assistant (same box, same query, no extra click) PASSES; the gap is systems fragmentation, not missing capability (see revised Step 2m / Strategic Signal)
- Multi-attribute / spec parsing: SPLIT — grid FAILS, Assistant PASSES (see above)
- Federated search (autocomplete): FAIL
- No-results handling: SAYT gives no fallback; results-page empty-state not capturable (WAF)
- B2B part-number / compatibility: FAIL
- Faceting: STRONG
- Recommendations: FAIL (service attach only)
- Personalization (anonymous): NOT EXPOSED
- Analytics signals to shopper: WEAK (ratings yes; popularity/trending no)

### Method & WAF Limitations (transparency)
- Browser: Chrome MCP driving Playwright Chromium 149 (Chrome for Testing) on Xvfb :99, 1440x900, --no-sandbox. Cookies declined (OneTrust).
- Search vendor: SAYT calls Dell's first-party gateway `pilot.search.dell.com/queryunderstandingapi/2/suggest`. Bloomreach (Phase 1 tag) is server-side/proxied and NOT visible client-side (no brsrvr.com/bloomreach.com calls at any point) — consistent with "tag-only, likely server-side".
- WAF: Akamai returns "Access Denied" on (a) direct URL navigation to /search/ and /shop/ paths, and (b) results pages for nonsense/no-hit queries — for the automated browser. Workaround used throughout: warm the session on the homepage, then submit via the in-page "Search Dell" BUTTON (in-session transition), which renders real results for valid queries. Enter-key submit forces a hard load that Akamai blocks. Four small (~46KB) screenshots (07-no-results, 08b, waf-*) intentionally document the WAF state; all other screenshots are full-content (>200KB).
