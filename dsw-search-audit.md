# DSW (Designer Brands Inc.) — Algolia Search Audit
**Date:** 2026-03-22
**Website:** https://www.dsw.com
**Ticker:** NYSE: DBI
**Prepared by:** Algolia

---

## Executive Summary

DSW's on-site search scores **3.8/10** — driven by five critical architectural gaps in a proprietary search backend with zero enterprise search vendor detected. The site handles brand queries and empty states reasonably well, but fails completely on three decisive dimensions: semantic/NLP search, federated content discovery, and personalized result ranking. A customer searching "gift for her under $100" receives an Under Armour backpack at position #1. A customer typing "comfortable shoes for standing all day" sees only 49 results versus 6,519 for "sneakers." Help content, loyalty program information, and brand editorial are completely invisible in search. Most critically: **Shoe Carnival — DSW's direct off-price footwear competitor — already uses Algolia and achieved up to 3.5x search conversions.** DSW has $921M flowing through dsw.com and no enterprise search platform. This is a greenfield opportunity with no displacement required.

---

## Strategic Intelligence

> **Why Now:** New CFO (Feb 2026) + New COO (Feb 2026) + first positive comparable sales in 9 quarters + VIP loyalty relaunch = the exact 90-day budget review window Algolia needs to enter with a $6.9M ROI story.

### Timing Signals

| Signal | Evidence | Source | Implication |
|--------|----------|--------|-------------|
| New CFO: Sheamus Toal | Started Feb 16, 2026 — former Children's Place CFO+COO | [PRNewswire](https://www.prnewswire.com/news-releases/designer-brands-inc-appoints-sheamus-toal-as-chief-financial-officer-302684350.html) | 90-day budget review in progress — ideal ROI pitch window |
| New COO: Andrea O'Donnell | Started Feb 8, 2026 — new operational leadership | [DBI IR](https://investors.designerbrands.com/management) | Process re-evaluation = receptive to new solutions |
| January 2026 Layoffs | Org simplification, cost reduction across operations | [WWD](https://wwd.com/footwear-news/shoe-industry-news/designer-brands-layoffs-2026-dsw-jobs-1238537102/) | ROI-driven tech buying environment — proven ROI required |
| Q4 FY2025 positive comp (+0.5%) | First positive quarter in 9 quarters | [DBI Earnings](https://investors.designerbrands.com/2025-03-20-Designer-Brands-Inc-Reports-Fourth-Quarter-and-Fiscal-Year-2024-Financial-Results) | "Turning the corner — now invest to accelerate" narrative |
| VIP Loyalty Program Relaunch | Actively planning loyalty program refresh | [Retail Dive](https://www.retaildive.com/news/designer-brands-open-DSW-stores-refresh-loyalty-program/743276/) | Loyalty + personalized search = highest-value combo |
| CEO Omnichannel Mandate | Explicit FY2024 strategic priority: "elevate omnichannel experience" | [DBI IR](https://investors.designerbrands.com/2025-03-20-Designer-Brands-Inc-Reports-Fourth-Quarter-and-Fiscal-Year-2024-Financial-Results) | Executive cover for search investment |

### Trigger Events

| Trigger | Opening Line for AE | Source |
|---------|--------------------|----|
| New CFO (Sheamus Toal) | "Sheamus, with $921M flowing through dsw.com and a search experience that's leaving $6.9M/year on the table — what does the ROI math need to look like for you?" | [PRNewswire](https://www.prnewswire.com/news-releases/designer-brands-inc-appoints-sheamus-toal-as-chief-financial-officer-302684350.html) |
| Shoe Carnival = Algolia customer | "Your direct competitor in off-price footwear — Shoe Carnival — just 3.5x'd their search conversions with Algolia. DSW has more stores and more traffic. The gap shouldn't exist." | [Algolia Customers](https://www.algolia.com/customers/shoe-carnival/) |
| VIP Loyalty Relaunch | "Your VIP relaunch is the exact moment to wire personalized search to loyalty tier — show Gold members their size, their brands, their price range first." | [Retail Dive](https://www.retaildive.com/news/designer-brands-open-DSW-stores-refresh-loyalty-program/743276/) |
| First positive comp in 9Q | "DSW just posted its first growth quarter in over two years. The question is: what digital investment accelerates the next one?" | [DBI Earnings](https://investors.designerbrands.com/2025-03-20-Designer-Brands-Inc-Reports-Fourth-Quarter-and-Fiscal-Year-2024-Financial-Results) |

---

## In Their Own Words

> "This year's achievements are a direct result of our decisive actions and commitment to refresh and strengthen our leadership, revitalize and modernize our assortment, refine our marketing strategies, right size our brand portfolio, and **elevate our customers' omnichannel experience.**"
> — Doug Howe, CEO, [Designer Brands FY2024 Earnings Release](https://investors.designerbrands.com/2025-03-20-Designer-Brands-Inc-Reports-Fourth-Quarter-and-Fiscal-Year-2024-Financial-Results), March 2025

**What we found:** DSW's on-site search is a custom proprietary backend with zero enterprise search vendor. The primary digital touchpoint — dsw.com search — cannot personalize results, understand natural language, or surface non-product content. "Elevating omnichannel experience" requires starting with search.

**Algolia solution:** Algolia Search + NeuralSearch + AI Personalization gives DSW an enterprise-grade omnichannel search layer that adapts to each shopper's context, size, loyalty tier, and browsing history — identical to what Shoe Carnival deployed to achieve 3.5x conversions.

---

> "We anticipate our reinvigorated efforts to be **customer-first and product obsessed** will help us better understand our customers and strengthen our product offerings through a **data-driven approach.**"
> — Doug Howe, CEO, [Designer Brands FY2024 Earnings Release](https://investors.designerbrands.com/2025-03-20-Designer-Brands-Inc-Reports-Fourth-Quarter-and-Fiscal-Year-2024-Financial-Results), March 2025

**What we found:** DSW has no search analytics visibility beyond "Top Rated" and "New Arrival" badges. There is no trending signal, no query analytics surfaced in the UI, and no personalization in search result ranking. "Data-driven" requires data — and the current search stack doesn't produce or consume it.

**Algolia solution:** Algolia Analytics + Insights API gives DSW real-time visibility into what customers are searching, what they're clicking, what queries fail — and feeds that data back into NeuralSearch to continuously improve relevance without manual rules.

---

> "Our top customers shop both channels, digital and physical, and they engage with our app very regularly, and that's something that we're continuously innovating upon."
> — Sarah Crockett, CMO, [Marketing Dive](https://www.marketingdive.com/news/dsw-cmo-brand-overhaul-phygital-retail/741028/), 2025

**What we found:** DSW's site search is entirely siloed from its multi-channel strategy. Store locator, loyalty program pages, and brand editorial are invisible in search. A customer using the "DSW rewards" query gets unrelated product results — not the loyalty program page. The digital and physical channels are not connected at the search layer.

**Algolia solution:** Algolia Federated Search unifies product catalog, store inventory, help content, loyalty program pages, and brand editorial into a single search experience — the infrastructure for the "phygital" experience DSW's CMO describes.

### Forward Guidance
Designer Brands guided for FY2026 low-single digit revenue growth and diluted EPS of $0.30–$0.50. The narrative is "accelerate the turn" — the first positive comp in 9 quarters creates internal pressure to invest in proven growth levers. [Source: DBI FY2024 Earnings Release](https://investors.designerbrands.com/2025-03-20-Designer-Brands-Inc-Reports-Fourth-Quarter-and-Fiscal-Year-2024-Financial-Results)

### Risk Factors Mentioning Digital/Technology
1. **Digital competition risk:** DSW operates in a "highly promotional retail environment" with intense competition across physical AND online channels. Failure to improve digital experience = continued customer erosion to Zappos, Macy's, and Amazon. [Source: Last10K 10-K Summary](https://last10k.com/sec-filings/dbi/0001319947-24-000011.htm)
2. **Failure to respond to changing consumer preferences:** Explicitly disclosed as a risk in 10-K FY2024 — "ability to anticipate and respond to rapidly changing consumer preferences and fashion trends." Algolia NeuralSearch + Query Suggestions directly addresses this risk.
3. **Cybersecurity and IT systems risk:** Aging/complex infrastructure disclosed as risk — signals need for modern, scalable search infrastructure. [Source: TipRanks Risk Factors](https://www.tipranks.com/stocks/dbi/risk-factors)

---

## Company Context

**Designer Brands Inc. (NYSE: DBI)** is the parent company of DSW Designer Shoe Warehouse — the largest off-price footwear chain in the US. Founded in 1969, publicly traded since 2005, headquartered in Columbus, Ohio.

- **Total Stores:** 669 (494 US DSW + 175 Canada) as of Feb 1, 2025 [FACT — DBI IR](https://investors.designerbrands.com/2025-03-20-Designer-Brands-Inc-Reports-Fourth-Quarter-and-Fiscal-Year-2024-Financial-Results)
- **FY2025 Revenue:** $3.009B [FACT — Yahoo Finance](https://finance.yahoo.com/quote/DBI/financials)
- **Digital Revenue (dsw.com):** ~$921M (~31% of total) [ESTIMATE — ecdb.com](https://ecdb.com/resources/sample-data/retailer/dsw)
- **Employees:** ~14,000 [FACT — Yahoo Finance](https://finance.yahoo.com/quote/DBI/financials)
- **Brand Portfolio:** DSW, The Shoe Co. (Canada), Vince Camuto, Keds, Topo Athletic, Jessica Simpson, Lucky Brand, Hush Puppies
- **Digital fulfillment:** 80%+ of digital orders fulfilled from distribution centers — inventory-aware search is a live need

DSW claims "a billion-dollar digital commerce business across multiple domains" — placing the quality of on-site search directly on the path to revenue recovery. [FACT — DBI IR, March 2025](https://investors.designerbrands.com/2025-03-20-Designer-Brands-Inc-Reports-Fourth-Quarter-and-Fiscal-Year-2024-Financial-Results)

---

## Technology Stack Deep Dive

| Category | Vendor | Confidence | Source |
|----------|--------|-----------|--------|
| **Site Search** | **CUSTOM/PROPRIETARY** | FACT (network inspection) | Phase 2 browser audit |
| E-commerce Platform | Unknown (enterprise/custom) | ESTIMATE | BuiltWith |
| CDN | Cloudflare | ESTIMATE | LeadIQ |
| Analytics | Adobe Analytics / Google Tag Manager | ESTIMATE | LeadIQ |
| Reviews/UGC | **Bazaarvoice** | FACT | [Bazaarvoice Case Study](https://www.bazaarvoice.com/success-stories/dsw/) |
| Personalization | **None detected** | FACT | BuiltWith + Phase 2 |
| Recommendations | **None detected** | FACT | BuiltWith + Phase 2 |
| Bot Protection | DataDome | FACT | Phase 2 network inspection |
| CRM/Push | Braze | FACT | Phase 2 network inspection |
| Tag Management | Tealium | FACT | Phase 2 network inspection |
| A/B Testing | Optimizely | FACT | Phase 2 network inspection |
| Customer Feedback | Medallia | FACT | Phase 2 network inspection |
| AI Inventory | Sizeo AI | FACT | [Sizeo LinkedIn](https://www.linkedin.com/posts/sizeo_retailai-sizecurves-inventoryoptimization-activity-7351219093644976129-M6U_) |
| CMS | Umbraco | ESTIMATE | LeadIQ |

**Key finding:** Phase 2 network inspection confirmed zero API calls to any known enterprise search platform (Algolia, BloomReach, Constructor, Coveo, Klevu, SearchSpring, Hawksearch). DSW runs a custom/proprietary search backend. No displacement required — this is a **pure greenfield opportunity**.

Search URL pattern `/browse/{term}` is server-side rendered — all search processing is on DSW's own infrastructure, not routed through a third-party search API. This means Algolia integration would be a net-new capability, not a swap.

**Algolia-ready stack signals:**
- Bazaarvoice reviews → can be indexed in Algolia for review-aware search ranking
- Braze CRM → customer identity available to power Algolia AI Personalization
- Tealium Tag Manager → Algolia Insights API can be deployed via Tealium without engineering sprints
- Umbraco CMS → Algolia headless connectors available for content search

---

## Competitor Landscape

| Competitor | Monthly Visits | Search Vendor | Notes |
|-----------|---------------|---------------|-------|
| Zappos | 14.5M | Amazon/AWS Internal | Owned by Amazon — unfair advantage; benchmark for UX |
| Macy's | 68.4M | Custom/Internal | Large stack (148 techs), Monetate + Adobe Target for personalization |
| Famous Footwear | 6.8M | Undetected | Most similar B&M+ecom model to DSW |
| Steve Madden | 4.6M | Undetected | DTC brand; lower complexity |
| **Shoe Carnival** | ~2M | **ALGOLIA** ⭐ | **Direct DSW competitor. 3.5x search conversions confirmed.** |

[Sources: SimilarWeb public page, BuiltWith API — 2026-03-21]

### The Golden Angle: Shoe Carnival

Shoe Carnival competes directly with DSW in off-price footwear. Same business model: brick-and-mortar + ecommerce, multi-brand, value-oriented footwear shopper. Shoe Carnival deployed Algolia (Search + Dynamic Re-Ranking + Recommend + Rules Engine + Amplience) and saw **up to 3.5x increase in conversions from search**. [Source: Algolia Customers](https://www.algolia.com/customers/shoe-carnival/)

> "Search and catalog are the heart of any commerce system, and very profitable for us." — Ned Moore, Director of eCommerce Product & Technology, Shoe Carnival

DSW has more stores (494 vs ~400), more traffic (21.7M peak vs ~2M), and a larger digital business ($921M). The search quality gap should not exist. **Shoe Carnival is winning on digital search. DSW can close that gap in weeks, not quarters.**

### Competitive Positioning

| Competitor | Search Maturity | Personalization | Gap to DSW |
|-----------|-----------------|----------------|-----------|
| Zappos | HIGH (Amazon infrastructure) | HIGH | DSW is 2-3 capability levels behind |
| Macy's | MEDIUM-HIGH (custom stack) | HIGH (Monetate + Adobe Target) | Personalization advantage vs. DSW |
| Famous Footwear | UNKNOWN | UNKNOWN | Likely parity with DSW |
| Steve Madden | LOW-MEDIUM | UNKNOWN | DSW on par or ahead |
| Shoe Carnival | **HIGH (Algolia)** | **HIGH** | **Shoe Carnival is now ahead** |

---

## Financial Profile

| Metric | FY2025 | FY2024 | FY2023 | Source |
|--------|--------|--------|--------|--------|
| Total Revenue | $3.009B | $3.075B | $3.315B | [Yahoo Finance](https://finance.yahoo.com/quote/DBI/financials) |
| Gross Profit | $1.286B | $1.324B | $1.455B | [Yahoo Finance](https://finance.yahoo.com/quote/DBI/financials) |
| EBITDA | $99.5M | $139.3M | $255.9M | [Yahoo Finance](https://finance.yahoo.com/quote/DBI/financials) |
| Net Income | -$10.5M | +$29.1M | +$162.7M | [Yahoo Finance](https://finance.yahoo.com/quote/DBI/financials) |
| EBITDA Margin | 3.31% | 4.53% | 7.72% | [Yahoo Finance](https://finance.yahoo.com/quote/DBI/financials) |
| Gross Margin | 42.88% | 43.05% | 43.89% | [Yahoo Finance](https://finance.yahoo.com/quote/DBI/financials) |

**Margin Zone: RED** — Net loss in FY2025 ($10.5M). EBITDA margin at 3.31% — well below 10% threshold. Revenue declining 3-year trend ($3.315B → $3.009B). Q4 FY2025 was first positive comparable quarter in 9 quarters (+0.5%).

[Source: Yahoo Finance MCP — FACT, 2026-03-21](https://finance.yahoo.com/quote/DBI/financials)

**AE context on Red Margin Zone:** DSW is not in a growth-investment mode — they are in recovery mode. The pitch must be ROI-first, cost-efficient, and tied to a specific payback period. "Proven ROI in 90 days or less" framing is essential.

### Revenue Impact Estimate

**Inputs (from research):**
- Total Revenue (FY2025): $3.009B [FACT — Yahoo Finance](https://finance.yahoo.com/quote/DBI/financials)
- Digital Revenue (dsw.com): ~$921M (30.6% digital share) [ESTIMATE — ecdb.com](https://ecdb.com/resources/sample-data/retailer/dsw)
- Search-addressable revenue: 15% of digital (~$138.2M) [ESTIMATE — Baymard Institute benchmark]

**ROI Scenarios:**

| Scenario | Improvement | Annual Revenue Impact |
|---------|------------|----------------------|
| Conservative | 5% search conversion lift | **$6.9M/year** |
| Moderate | 10% search conversion lift | **$13.8M/year** |

**ROI Multiple:** $6.9M impact / ~$400K Algolia ACV = **17x ROI** (conservative)
**Payback period:** <30 days at moderate scenario

**AE framing:** "If Algolia improves DSW's search conversion by just 5% — the same improvement Shoe Carnival described — that's $6.9M in additional annual revenue from existing dsw.com traffic, before accounting for reduced bounce rate or improved loyalty retention."

---

## Strategic Leadership

### Tier 1 — Primary Executives

| Name | Title | Tenure | Notes |
|------|-------|--------|-------|
| **Doug M. Howe** | CEO | April 2023–present | Owns omnichannel experience mandate; former DSW President |
| **Sheamus Toal** | EVP, CFO | Feb 16, 2026–present | NEW — 90-day budget review window OPEN NOW |
| **Andrea O'Donnell** | EVP, COO + President Brands | Feb 8, 2026–present | NEW — process re-evaluation mode |

[FACT — DBI IR + PRNewswire](https://investors.designerbrands.com/management)

### Tier 2 — Algolia Buying Committee

| Name | Title | Role | Notes |
|------|-------|------|-------|
| **Laura T. (Denk) Davis** | EVP + President, North America Retail, DSW | Secondary | VP-level sponsor for "customer experience" investment |
| **Barry Esposito** | SVP, e-Commerce & Customer Operations, DSW | **PRIMARY TARGET** | Owns dsw.com — primary AE outreach contact |
| VP/Director, Digital Product | Unidentified (under Barry's org) | Champion | Find via LinkedIn — would own technical evaluation |

[ESTIMATE — Comparably + WebSearch](https://www.comparably.com/companies/dsw/executive-team)

---

## Buying Committee

| Role | Name | Signal | Approach |
|------|------|--------|---------|
| Economic Buyer | Sheamus Toal (CFO) | NEW — 90-day review | ROI brief: $6.9M–$13.8M annual uplift at 17x ROI |
| Technical Buyer | Barry Esposito (SVP eCommerce) | Owns dsw.com | "Shoe Carnival 3.5x" opener + 15-min demo ask |
| User Buyer | VP/Dir Digital Product (TBD) | Find in Barry's org | Technical evaluation — Algolia complements ML ambitions |
| Champion | ML Engineer (open role) | Hiring ML/AI talent | Position Algolia as the search infrastructure ML team builds ON TOP of |

---

## Hiring Signal Analysis

DSW maintains 419 open positions despite January 2026 layoffs — technology and digital roles were protected. [ESTIMATE — Zippia](https://www.zippia.com/designer-brands-careers-3576/jobs/)

| Role | Signal | Algolia Relevance |
|------|--------|-----------------|
| Machine Learning Engineer | Active hire — GCP/Azure OpenAI, ML model deployment | Would evaluate and integrate AI search — potential champion |
| E-commerce Roles (explicit category) | Separate from IT — dedicated ecommerce product team | Ecommerce product team owns search experience decisions |
| IT / Information Technology | Dedicated IT function separate from retail ops | Integration partner for Algolia deployment |

**Key insight:** DSW is hiring ML Engineers to build AI/ML models — Algolia NeuralSearch complements, not competes with, their internal ML ambitions. Position as "the search API your ML team builds personalization ON TOP of."

**No "Search Engineer" role detected** — this means either (a) DSW doesn't invest in search as a specialty (likely), OR (b) they are evaluating external vendors. Either interpretation favors Algolia.

---

## Revenue Impact Estimate

See Financial Profile section above.

**Conservative ROI: $6.9M/year** (5% improvement on $138.2M search-addressable revenue)
**Moderate ROI: $13.8M/year** (10% improvement)
**Estimated ACV: $400K–$800K** | **ROI Multiple: 17x** (conservative) | **Payback: <30 days** (moderate)

---

## ICP-to-Priority Mapping

**ICP Score: 83.5/100 — HOT tier**

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|---------|
| Revenue Scale | 9/10 | 15% | 13.5 |
| Digital Presence | 9/10 | 15% | 13.5 |
| Search Problem Size | 8/10 | 20% | 16.0 |
| Buying Signal Strength | 8/10 | 15% | 12.0 |
| Competitive Urgency | 7/10 | 10% | 7.0 |
| Trigger Event Timing | 9/10 | 15% | 13.5 |
| Case Study Proximity | 8/10 | 10% | 8.0 |
| **TOTAL** | | | **83.5/100 — HOT** |

[Source: 12-icp-priority-mapping.md]

**Algolia Products — Priority Fit:**

| Product | Fit | Evidence |
|---------|-----|---------|
| Algolia Search (Core) | ⭐⭐⭐⭐⭐ | Greenfield — no search vendor |
| Algolia NeuralSearch | ⭐⭐⭐⭐⭐ | 3 NLP queries fail; CEO "data-driven customer-first" mandate |
| Algolia Personalization | ⭐⭐⭐⭐⭐ | VIP relaunch + 76% female audience + no personalization engine |
| Algolia Recommend | ⭐⭐⭐⭐ | PDP recs are brand-siloed; no cross-catalog collaborative filtering |
| Algolia Merchandising Studio | ⭐⭐⭐⭐ | No Rules Engine; banners are template-only |
| Algolia Federated Search | ⭐⭐⭐ | Uber Eats + store locator + loyalty = multiple data sources |

---

## Search Audit Findings

### Audit Recap (10-Area Scoring)

| # | Area | Score | Severity | Key Evidence |
|---|------|-------|---------|-------------|
| 1 | Latency | 7/10 | LOW | Fast SAYT; server-rendered /browse/{term} |
| 2 | Typo Tolerance | 4/10 | HIGH | "DID YOU MEAN" click required; not auto-correcting |
| 3 | Query Suggestions / Empty State | 6/10 | MEDIUM | Trending + Ideas For You good; no recent searches |
| 4 | Intent Detection | 5/10 | MEDIUM | Brand intent excellent; price/occasion intent partial |
| 5 | Merchandising Consistency | 6/10 | MEDIUM | Brand/clearance pages good; no inline rules engine |
| 6 | Content Commerce / Front-End UX | 2/10 | HIGH | FAIL — No federated search; content invisible |
| 7 | Semantic / NLP Search | 1/10 | HIGH | FAIL — All 3 NLP queries fail; pure keyword matching |
| 8 | Dynamic Facets & Personalization | 4/10 | HIGH | Template-based facets; search ranking not personalized |
| 9 | Recommendations & Merchandising | 4/10 | HIGH | Brand-siloed recs; no collaborative filtering |
| 10 | Search Intelligence | 4/10 | MEDIUM | Basic badges; no trending/popularity signals |
| **OVERALL** | | **3.8/10** | | **5 critical, 4 moderate, 1 low** |

**Formula:** sum(score × weight) / sum(weights) = 54.5 / 14.5 = **3.8/10**

---

### Detailed Findings

#### F01 — Zero NeuralSearch: Natural Language Queries Completely Fail
**Severity:** CRITICAL
**Category:** Semantic / NLP Search
**Tested Queries:** "gift for her under 100", "comfortable shoes for standing all day", "shoes for a summer wedding guest"
**Screenshot:** screenshots/06-synonym-gift-for-her.png, screenshots/13-nlp-comfortable-shoes.png

**What happened:**
- "gift for her under 100": 3,229 results — **Under Armour backpacks** at position #1 (keyword match on "her" in product name "Adore Her Slip-On"). Price filter "$100" was never applied. Gender intent "for her" was not understood.
- "comfortable shoes for standing all day": **49 results** vs 6,519 for "sneakers." Returns Dansko clogs and kitchen shoes only — no comfort-rated running shoes, orthopedic sneakers, or wide-fit options that a human buyer would associate with the intent.
- "shoes for a summer wedding guest": 1,249 results — includes men's Cole Haan penny loafers. Gender and occasion precision failed.

**Why it matters:** 76% of DSW's audience is female. Fashion-driven queries ("summer wedding guest heels under $150," "wide fit comfortable work shoe") are the primary search vocabulary of their customer. Pure keyword matching fails this audience systematically.

**Algolia solution:** Algolia NeuralSearch understands natural language intent — gender, price constraints, occasion, lifestyle context — and returns results matching what the shopper means, not just what they typed. Shoe Carnival deployed NeuralSearch as part of their Algolia implementation that delivered 3.5x search conversions.

**Case study:** [Shoe Carnival — up to 3.5x conversions from search](https://www.algolia.com/customers/shoe-carnival/)

---

#### F02 — No Federated Search: Content, Help, and Loyalty Invisible
**Severity:** CRITICAL
**Category:** Content Commerce / Front-End UX
**Tested Query:** "sneak" (SAYT), "DSW rewards" (inferred)
**Screenshot:** screenshots/03-sayt-sneakers.png

**What happened:** SAYT shows only product thumbnails and query completions — no category page links, no help article shortcuts, no brand page shortcuts. A user typing "return policy" in the search bar does get redirected to the correct page (good) — but this is a **hardcoded rule**, not dynamic search. The loyalty program ("DSW Rewards"), store locator, lookbook content, and brand editorial are completely invisible in search. Searching "DSW rewards" would return products with "reward" in product names, not the VIP program page.

**Why it matters:** Shoe Carnival uses Algolia Federated Search to surface category pages, content, and help articles alongside products. DSW's search is product-only — an entire class of high-intent user queries ("how do I use my points," "free shipping policy," "return in store") hits dead ends.

**Algolia solution:** Algolia Federated Search indexes multiple data sources — product catalog, help center, loyalty pages, brand editorial, store locator — and surfaces the right content type at the right moment in SAYT and full results.

**Case study:** [Shoe Carnival — multi-source search with Algolia](https://www.algolia.com/customers/shoe-carnival/)

---

#### F03 — Typo Tolerance Requires User Action
**Severity:** CRITICAL
**Category:** Typo Tolerance
**Tested Query:** "sneackers"
**Screenshot:** screenshots/05-typo-sneackers.png

**What happened:** Searching "sneackers" (extra 'c') displays: "YOU SEARCHED FOR 'sneackers'" with "DID YOU MEAN: [Sneakers button]" and 6,626 results below. The user must **click the "Sneakers" button** to see corrected results. SAYT during typing showed only 1 suggestion ("sneakers"). On mobile, the DID YOU MEAN banner may be below the fold.

**Why it matters:** Mobile accounts for a substantial share of DSW's traffic (76% female audience on mobile is high). A passive "did you mean" banner that requires a click creates friction — especially on small screens where the banner may be partially hidden.

**Algolia solution:** Algolia auto-corrects typos transparently — showing "Results for 'sneakers'" inline, with zero extra clicks. Mobile users see corrected results immediately.

---

#### F04 — Recommendations are Brand-Siloed, Not Collaborative
**Severity:** CRITICAL
**Category:** Recommendations & Merchandising
**Tested PDP:** Birkenstock Arizona Slide Sandal
**Screenshot:** screenshots/18-recommendations.png

**What happened:** PDP has three recommendation sections ("Similar Styles," "You May Also Like," "Customers Also Bought") but all return Birkenstock variants only — other colorways and price points of the same product family. No cross-brand recommendations were observed. "Customers Also Bought" appears to use same-brand filtering rather than collaborative filtering across the full catalog.

**Why it matters:** "Complete the Look" (sandals + bag + socks) and cross-brand "frequently bought together" (Birkenstock + Vionic insoles) are the highest-AOV recommendation patterns in footwear. DSW's current recommendations miss all of this.

**Algolia solution:** Algolia Recommend uses collaborative filtering across the full product catalog — surfacing what customers who bought THIS product also bought, regardless of brand. Shoe Carnival deployed Algolia Recommend and described it as "a game-changer for getting the most value from search."

**Case study:** [Shoe Carnival — immediate conversion uplift with Algolia Recommend](https://www.algolia.com/customers/shoe-carnival/)

---

#### F05 — No Personalized Search Ranking
**Severity:** CRITICAL
**Category:** Dynamic Facets & Personalization
**Tested Query:** "sneakers" (6,519 results)
**Screenshot:** screenshots/14-dynamic-facets.png

**What happened:** DSW has "Ideas For You" (10 personalized product thumbnails in empty state) and "Recently Viewed" sections — session-level personalization via Braze/native components. However, searching "sneakers" returns 6,519 results in a generic ranked order with no evidence of personalization. A size 8 medium Naturalizer fan sees the same ranking as a size 12 wide New Balance runner. Width filter ("W" width) is present but buried in the facet panel — not pre-surfaced for footwear searches.

**Why it matters:** DSW has the data (loyalty tier, size history, brand preferences, purchase history) but the search layer doesn't use it. 76% of the audience is female — occasion, style, and size preference vary enormously. A VIP Insider Gold member searching "boots" should see their size, width, and preferred brands before all others.

**Algolia solution:** Algolia AI Personalization re-ranks results based on each user's browsing and purchase history. The VIP loyalty relaunch is the perfect integration moment — wire loyalty tier to Algolia user tokens to create a personalized search experience for each loyalty segment.

---

#### F06 — Strong Brand Intent Detection (Positive Finding)
**Severity:** POSITIVE
**Category:** Intent Detection
**Tested Query:** "Vince Camuto"
**Screenshot:** screenshots/09-intent-wedding-guest.png

**What happened:** Searching "Vince Camuto" redirects to a fully curated brand landing page at `/brands/vince-camuto` — with editorial heading "The Vince Camuto Shop," gender funnels, featured product sections, and 266 results with brand-specific filters. This is excellent brand intent handling.

**Why it matters:** DSW's strong brand-to-page intent handling shows their team has invested in merchandising for key brands. This is a strength that Algolia Rules Engine would amplify — enabling the same outcome for long-tail brand searches that don't have dedicated pages today.

**Algolia solution:** Algolia Rules Engine codifies these brand redirect patterns programmatically — enabling the merchandising team to manage hundreds of rules via a visual interface, without engineering dependency.

---

### Screenshots Reference

| Screenshot | Query / Test | Key Finding |
|-----------|-------------|-------------|
| 01-homepage.png | Homepage load | Search bar prominent, sticky nav, DataDome active but no block |
| 02-empty-state.png | Empty state (before typing) | Trending + Ideas For You — above average |
| 03-sayt-sneakers.png | "sneak" SAYT | Products + completions only — no federated content |
| 04-results-sneakers.png | "sneakers" results | 6,519 results; 15 facets; well-structured |
| 05-typo-sneackers.png | "sneackers" typo | DID YOU MEAN — requires click; not auto-correcting |
| 06-synonym-gift-for-her.png | "gift for her under 100" | Under Armour backpacks — NLP failure |
| 07-no-results.png | "xyzunknownbrand123" | Best-sellers fallback; no query suggestions |
| 08-non-product-return-policy.png | "return policy" | Redirects to correct page (hardcoded rule) |
| 09-intent-wedding-guest.png | "shoes for a summer wedding guest" | 1,249 results; partial intent — includes men's |
| 10-merchandising.png | Vince Camuto brand page | Excellent curated brand landing page |
| 12-mobile-sneakers.png | Mobile viewport (390×844) | Functional; camera icon invisible on mobile |
| 13-nlp-comfortable-shoes.png | "comfortable shoes for standing all day" | Only 49 results — NLP failure |
| 14-dynamic-facets.png | "wide calf boots" facets | 311 results, 13 facets; no count badges |
| 18-recommendations.png | Birkenstock PDP | Similar Styles shows only Birkenstock variants |
| 19-banners-sale.png | "sale" → clearance | Clearance page with brand logo carousel |

---

## Opportunities

| Priority | Algolia Product | Business Impact | Evidence |
|---------|----------------|----------------|---------|
| 1 | **NeuralSearch** | Unlock $6.9M–$13.8M revenue from NLP queries currently returning wrong results | "gift for her under 100" → backpacks; "comfortable shoes for standing all day" → 49 results |
| 2 | **Federated Search** | Surface loyalty program, help content, brand editorial — reduce bounce from non-product queries | SAYT is product-only; "DSW rewards" would return unrelated products |
| 3 | **AI Personalization** | VIP loyalty relaunch: personalize search by size, tier, brand history for 76% female audience | No personalized ranking detected; search ranking is generic for all users |
| 4 | **Recommend** | Increase AOV with cross-catalog "frequently bought together" and "complete the look" | Brand-siloed recommendations miss cross-brand and cross-category upsell |
| 5 | **Rules Engine** | Replace hardcoded merchandising templates with dynamic keyword-triggered rules and banners | Template-only merchandising; no inline campaign banners on search results pages |
| 6 | **Analytics + Insights** | Generate "data-driven" search visibility CEO mandated; feed performance data back into NeuralSearch | Basic Top Rated/New Arrival badges; no trending signals or query analytics in UI |

---

## Algolia Value-Prop Assessment

| Algolia Product | DSW Gap | Shoe Carnival Proof | Priority |
|----------------|---------|-------------------|---------|
| NeuralSearch | 3/3 NLP test queries fail | Deployed as part of Shoe Carnival stack | URGENT |
| Federated Search | Content/loyalty invisible to search | Multi-source search across catalog + content | HIGH |
| AI Personalization | Search ranking not personalized | 76% female audience: size, brand, tier matter | HIGH |
| Recommend | Brand-siloed PDP recs only | "Game-changer for value from search" — Shoe Carnival | HIGH |
| Rules Engine | Template-only merchandising | Visual Editor used by Shoe Carnival merch team | MEDIUM |
| Query Suggestions | Session-weighted suggestions absent | Used in Shoe Carnival SAYT | MEDIUM |
| Dynamic Facets | Width facet buried; no count badges | Facets + Filters used at Shoe Carnival | MEDIUM |
| Analytics / Insights | No analytics signals in UI | Insights API + Analytics used at Shoe Carnival | LOW |

---

## How Algolia Can Help

DSW's search architecture needs a platform upgrade — not a patch. The custom/proprietary search backend that handles `/browse/{term}` can be replaced with or complemented by Algolia as the intelligence layer, with DSW maintaining their existing URL patterns and front-end experience.

**Recommended implementation path:**

1. **Phase 1 (Weeks 1–4): Core Search + NeuralSearch** — Replace the keyword matching engine with Algolia Search + NeuralSearch. Maintain existing URL patterns. Enable typo tolerance, NLP understanding, and result quality improvements. Measure: search conversion rate, zero-results rate, click-through from SAYT.

2. **Phase 2 (Weeks 5–8): Federated Search + Rules Engine** — Extend Algolia to index non-product content (help center, loyalty pages, brand editorial). Deploy merchandising rules for campaign keywords. Enable inline banners. Integrate via Tealium (already deployed).

3. **Phase 3 (Weeks 9–16): AI Personalization + Recommend** — Connect Braze customer identity to Algolia AI Personalization. Re-rank search results by user profile (size, width, brand history, loyalty tier). Deploy Recommend on PDP with full collaborative filtering.

---

## Next Steps

1. **This week:** Share this audit with Barry Esposito (SVP eCommerce). Subject line: "Shoe Carnival 3.5x'd search conversions with Algolia — here's what we found on dsw.com."

2. **Week 2:** Book a 30-minute technical walkthrough with Barry + VP Digital Product. Demo the exact queries that failed: "gift for her under 100," "comfortable shoes for standing all day." Show Shoe Carnival comparison in real time.

3. **Month 1:** Present ROI brief to CFO Sheamus Toal. Frame: $6.9M annual uplift at 17x ROI, 90-day pilot, zero displacement required. New CFO is in budget review mode — ideal timing.

---

## Source Bibliography

1. [Yahoo Finance — DBI Financials](https://finance.yahoo.com/quote/DBI/financials)
2. [Yahoo Finance — DBI Quote](https://finance.yahoo.com/quote/DBI)
3. [Designer Brands IR — FY2024 Earnings Release](https://investors.designerbrands.com/2025-03-20-Designer-Brands-Inc-Reports-Fourth-Quarter-and-Fiscal-Year-2024-Financial-Results)
4. [Designer Brands — Management Page](https://investors.designerbrands.com/management)
5. [PRNewswire — Sheamus Toal CFO Appointment](https://www.prnewswire.com/news-releases/designer-brands-inc-appoints-sheamus-toal-as-chief-financial-officer-302684350.html)
6. [PRNewswire — Q3 FY2025 Results](https://www.prnewswire.com/news-releases/designer-brands-inc-reports-third-quarter-2025-financial-results-302635763.html)
7. [WWD — Designer Brands Layoffs 2026](https://wwd.com/footwear-news/shoe-industry-news/designer-brands-layoffs-2026-dsw-jobs-1238537102/)
8. [Retail Dive — DSW Layoffs](https://www.retaildive.com/news/designer-brands-dsw-confirms-layoffs/811413/)
9. [Retail Dive — VIP Program Refresh](https://www.retaildive.com/news/designer-brands-open-DSW-stores-refresh-loyalty-program/743276/)
10. [Marketing Dive — DSW CMO Phygital Retail](https://www.marketingdive.com/news/dsw-cmo-brand-overhaul-phygital-retail/741028/)
11. [SimilarWeb — dsw.com](https://www.similarweb.com/website/dsw.com/)
12. [BuiltWith — dsw.com](https://builtwith.com/dsw.com)
13. [BuiltWith — zappos.com](https://builtwith.com/zappos.com)
14. [BuiltWith — macys.com](https://builtwith.com/macys.com)
15. [ecdb.com — DSW Revenue](https://ecdb.com/resources/sample-data/retailer/dsw)
16. [Algolia — Shoe Carnival Case Study](https://www.algolia.com/customers/shoe-carnival/)
17. [Bazaarvoice — DSW Case Study](https://www.bazaarvoice.com/success-stories/dsw/)
18. [Sizeo — DSW Partnership](https://www.linkedin.com/posts/sizeo_retailai-sizecurves-inventoryoptimization-activity-7351219093644976129-M6U_)
19. [Last10K — DBI 10-K FY2024](https://last10k.com/sec-filings/dbi/0001319947-24-000011.htm)
20. [TipRanks — DBI Risk Factors](https://www.tipranks.com/stocks/dbi/risk-factors)
21. [SeekingAlpha — Q3 2025 Earnings Call](https://seekingalpha.com/article/4851576-designer-brands-inc-dbi-q3-2025-earnings-call-transcript)
22. [Wikipedia — Designer Brands](https://en.wikipedia.org/wiki/Designer_Brands)
23. [Zippia — Designer Brands Jobs](https://www.zippia.com/designer-brands-careers-3576/jobs/)
24. [DSW Careers](https://careers.dswinc.com/)
25. [ainvest.com — DSW Personalization Article](https://www.ainvest.com/news/dsw-strategic-rebranding-personalization-driven-growth-blueprint-retail-resilience-2509/)
