# MEMORY — Prism (seed)

- **What PRISM is:** an internal Algolia AE/BDR prospect-intelligence tool. The package = **this
  Hermes instance (Chowmes-PRISM) + the algolia-* skill suite**. Not a custom SaaS.
- **How it works:** control/execution split. Prism (control) dispatches a **headless Claude worker**
  that runs the 22 `algolia-*` skills to produce a scored search audit + sales deliverables.
- **Deliverables per audit:** scored SPA deck, AE pre-call report, battle card, leave-behind + PDF,
  business case (ROI), sales playbook, ABX campaign, strategic signal brief.
- **Published reports** land on the hub: `algolia-arian-v2.vercel.app/<company>/`.
- **The wedge:** the *scored search audit* + the single damning finding. Constructor.io is THE
  competitor for ICP-sized ecommerce.
- **Locked decisions:** control model = `google/gemini-2.5-flash` (OpenRouter); execution = headless
  Claude (Anthropic). **Temporal dropped** — Hermes-native kanban/cron is the orchestrator.
- **Skills source of truth:** the `arijit-skills` repo (`skills/algolia-audit-skills`); it carries
  the financials-chart parser fix. Skills run on the executor, not on Prism's own model.
- **Two interaction modes:** generation (batch audit) vs consumption (chat over a finished report).

---

## Algolia Knowledge (for grounding Prism's product expertise)

*Reference material for Prism's sales-coach persona. Every number carries a source label.
[FACT] = verified from a named source. [ESTIMATE] = modeled or industry range.*

---

### What Algolia Is

Algolia is a hosted search and discovery API — companies plug it in and get fast, relevant, tunable search without running their own search infrastructure. It sits between a company's product catalog and its website, handling the query-to-result loop with AI-powered relevance, real-time indexing, and merchandising controls built in.

In plain terms: it's the search box brain-as-a-service. You configure what matters, Algolia finds and ranks it in milliseconds.

---

### The Products That Matter in a Deal

Eight capabilities come up repeatedly. Lead with the ones that match the audit gaps.

| Product | What it does | Business outcome |
|---|---|---|
| **Search (core)** | Hosted search API with typo tolerance, synonym handling, faceted filtering, and instant results | Replaces slow/dumb keyword search; baseline of any deal |
| **NeuralSearch** | Algolia's semantic / AI search — understands intent, not just keywords ("comfortable running shoes for bad knees" works) | Recovers the 20-30% of queries that fail on keyword-only systems; lifts long-tail conversion |
| **AI Personalization** | Re-ranks results per user based on behavioral signals — the order a Gold loyalty member sees is different from a first-time visitor | AOV and repeat-purchase lift; works off existing behavioral data (clicks, purchases, add-to-cart) |
| **Recommend** | "Frequently bought together," "related items," "trending" widgets — API-powered, real-time | Basket size increase; drives add-on purchases without manual curation |
| **Dynamic Re-Ranking** | Automatically promotes items that are converting and demotes ones that aren't | Reduces manual merchandising effort; keeps results fresh without rule maintenance |
| **Merchandising Studio / Rules** | GUI for non-technical teams to pin items, inject banners, boost seasonal picks, set up A/B tests | Lets the merchant control search without filing engineering tickets — big deal for retail |
| **Query Suggestions** | Autocomplete / search-as-you-type dropdown — surfaces popular and trending queries | Reduces zero-result searches; guides users to inventory that exists |
| **Analytics** | Search analytics dashboard — shows top queries, no-results rate, CTR, conversion by query | Makes search a managed channel; feeds back into Rules and Re-Ranking |

**Federated Search** (cross-index search) is often the hook for non-ecommerce deals (media, B2B, financial services): one query box that searches products, articles, help pages, and store locators simultaneously.

---

### Where Algolia Genuinely Wins

**Speed:** Sub-100ms globally via distributed edge nodes. Not a trivial advantage — Amazon's own internal research showed 100ms of latency = 1% revenue loss [ESTIMATE — Amazon 2006, widely cited; no primary public URL]. Algolia's SLA is verifiable at status.algolia.com.

**Relevance + AI without the build cost:** NeuralSearch handles semantic queries out of the box. The alternative is building and maintaining your own vector search stack on top of Elasticsearch — months of ML engineering for the same outcome.

**Merchandiser control:** The Rules + Merchandising Studio combo lets non-engineers tune relevance, inject promotional content, and run A/B tests. This matters enormously to retail teams who can't wait for engineering tickets.

**Time-to-value:** Most implementations go live in weeks, not quarters. The API-first architecture plugs into existing stacks (Shopify, SFCC, commercetools, headless React) without a platform migration.

**Scale with zero maintenance:** Algolia handles index size, replication, and uptime. The customer doesn't manage clusters.

**Where it's a harder sell:**
- Very large enterprise with existing Elasticsearch investment and strong ML team — the build vs. buy argument is real, not just objection handling.
- Pure B2B SaaS or internal tools — the ROI math is harder without ecommerce conversion data.
- Companies with extreme data sovereignty requirements (some government/finance) — even with EU infrastructure, procurement review is long.
- Price: Algolia's pricing is usage-based and can look expensive vs. Elasticsearch's apparent "free" (ignoring engineering labor to run it).

---

### Constructor.io — The Primary Competitor

**How they position:** Constructor markets itself as "AI-first product discovery" — machine learning for ranking with less manual rule configuration. They target mid-market to enterprise ecommerce, especially fashion and apparel. Their pitch is "relevance through AI, not rules."

**What they actually are in the field:** Constructor runs at companies like Under Armour, Savage X Fenty (FableticsOS group), and select apparel DTC brands. Detection: `key_Gz4VzKsXbR7b7fSh`, client 2.65.0 (from network inspection of Under Armour, now confirmed Algolia after migration). The Savage X Fenty audit found Constructor in the FableticsOS stack. [FACT — detect-search network inspection, arijit-skills skill suite]

**The counter-narrative (5 parts):**

1. **Merchandiser control is weaker.** Constructor's ML ranking means less hands-on control for the merchant. Algolia's Rules + Merchandising Studio gives non-technical teams direct manipulation. For retail teams that run weekly promotions and seasonal campaigns, this is a deal-breaker — "the algorithm decides" isn't acceptable when you need to pin the new collection at Christmas.

2. **Federated search is Algolia's.** Constructor is a single-index product search engine. Algolia federates across products, content, store locators, help articles, FAQs in one query. Any company with content + commerce needs (which is most of them) runs into this gap.

3. **Implementation ecosystem is smaller.** Algolia has first-party connectors for Shopify, SFCC, Adobe Commerce, commercetools, and a massive InstantSearch UI library. Constructor's partner ecosystem is thinner.

4. **Proof set and case studies are thinner.** Algolia has 1,000+ documented customer deployments across verticals. Constructor's public case studies are narrower.

5. **When prospect has Constructor:** lead with the FableticsOS displacement angle (platform deal opportunity) or the specific gap (NLP/federated/Recommend) that Constructor demonstrably doesn't cover. Audit finding + screenshot is the opener.

**Other competitors — brief:**

| Vendor | Who they are | Where they beat Algolia | Algolia counter |
|---|---|---|---|
| **Coveo** | B2B/enterprise AI search, strong in Salesforce ecosystem | Deep CRM integration, B2B relevance models | Coveo is slower to implement; Algolia is faster and cheaper for ecommerce |
| **Bloomreach** | Full-suite ecommerce platform (search + content + CMS + CDP) | "All in one" pitch for mid-enterprise | Algolia is best-of-breed; Bloomreach bundles lock you in and the search module is weaker |
| **Elasticsearch (self-managed)** | Open-source, "free" | Total control, no SaaS cost | Engineering cost of self-managing is 10x+ the Algolia subscription; no relevance AI out of the box |
| **Searchspring / Klevu** | SMB-focused search for Shopify/Magento | Lower price point | Algolia scales to enterprise; Searchspring/Klevu don't handle index size or global latency at scale |

---

### ROI Levers — The 6-Component Business Case

Every Algolia business case is built from these six components. Each one maps to a specific search gap found in the audit. [Source: algolia-synth-business-case skill, verified against audit deliverables across 15+ prospects]

**Component 1 — Search Conversion Lift**
Logic: Sessions that start with search convert at a higher rate when search returns relevant results. Even a 15% lift on search-initiated sessions compounds across millions of monthly visits.
Formula signal: `monthly_visits × search_usage_rate × conversion_delta × AOV × 12`
Activated by: poor intent detection, keyword-only search, high no-results rate.

**Component 2 — Average Order Value (AOV) Increase**
Logic: When search surfaces higher-value, complementary, or personalized items — basket size grows. Recommendations and personalization are the levers.
Formula signal: `monthly_search_sessions × current_conversion × AOV_delta × 12`
Activated by: no Recommend, no AI Personalization, static facets.

**Component 3 — Bounce Rate Reduction**
Logic: Users who search and immediately leave — because results are irrelevant or empty — are recoverable. Every bounce from a search session is a lost sale.
Formula signal: `monthly_visits × search_usage_rate × bounce_delta × recovery_conversion × AOV × 12`
Activated by: high site bounce rate, poor empty-state experience, zero-results rate.

**Component 4 — No-Results Recovery**
Logic: Queries that return zero results are the worst user experience in search. Each zero-result event is a purchase that didn't happen. Typo tolerance + synonym handling + NLP recovers these.
Benchmark: Baymard Institute — 34% of e-commerce sites fail basic search adequacy [FACT — Baymard, https://baymard.com]
Formula signal: `monthly_searches × no_results_rate × AOV × recovery_rate × 12`
Activated by: typo failures, synonym gaps, NLP failures.

**Component 5 — Speed / Latency Gain**
Logic: Slow search drives abandonment. Every 100ms of additional latency costs roughly 1% in revenue. Moving from 400ms to sub-100ms search is measurable.
Benchmark: Amazon internal finding — 100ms latency = 1% revenue loss [ESTIMATE — Amazon 2006, no verified public URL]
Formula signal: `monthly_visits × search_usage_rate × latency_bucket_count × 1% × AOV × 12`
Activated by: slow page-reload search, >300ms latency.

**Component 6 — Long-Tail Discovery**
Logic: 20-30% of searches at most ecommerce sites are conversational, multi-word, or synonym-dependent [ESTIMATE — industry range]. Keyword search fails these. NeuralSearch recovers them.
Formula signal: `monthly_searches × nlp_fail_rate × AOV × recovery_rate × 12`
Activated by: NLP failures, semantic search gaps, multi-word query breakdowns.

**In practice:** the AE fills in AOV and conversion rate from the prospect; the audit provides monthly visits, bounce rate, and which components are active. The calculate-roi.py script computes the numbers — Prism never invents dollar figures.

---

### Proof Points — Real Algolia Customer Case Studies

These are the six case studies with the most evidence across the audit corpus. All URLs are the Algolia customer page — verify before citing in a live conversation.

**1. Lacoste — Sport & Lifestyle Apparel**
Result: +150% sales contribution from search · +37% conversion rate · -88% bounce rate
Product: InstantSearch + Query Rules + Personalization + Analytics (replaced platform-native Solr)
Why it works in a pitch: large multi-brand catalog across footwear and accessories — maps to any multi-SKU retailer. The 37% conversion number is the most-cited benchmark in the skills.
URL: https://www.algolia.com/customers/lacoste [FACT — extracted from brooks-running, nike, dsw, savage-x-fenty audits]

**2. Under Armour — Athletic Apparel & Footwear**
Result: +35% conversion rate on search
Product: Algolia Search (replaced in-house proprietary stack, then migrated from Constructor.io)
Why it works in a pitch: Under Armour ran a custom search stack — same story as any Nike/DIY Elasticsearch prospect. Directly comparable peer proof.
URL: https://www.algolia.com/customers/under-armour [FACT — nike-audit-data.json; brooks-running-audit-data.json]

**3. Shoe Carnival — Footwear Retail**
Result: Up to 3.5x increase in conversion from search; +4.5% conversion during first Cyber Weekend; merchandising team productivity doubled
Product: Algolia AI Search + Recommend + Dynamic Re-Ranking + Merchandising Studio
Quote: "I probably sleep better with Algolia than I did with any of the technologies we either purchased or built ourselves." — Ned Moore, Director eCommerce Product & Technology, Shoe Carnival [FACT — dsw-audit-data.json golden_angle, algolia.com/customers/shoe-carnival]
URL: https://www.algolia.com/customers/shoe-carnival

**4. Gymshark — DTC Fitness Apparel**
Result: +150% order rate for new customers · +32% add-to-cart rate
Product: Algolia Recommend + AI Search + Real-time Indexing
Why it works in a pitch: DTC brand with influencer-driven traffic spikes — proves Algolia handles real-time indexing and scales with campaign burst traffic. Maps to any high-growth DTC.
URL: https://www.algolia.com/customers/gymshark-recommend [FACT — savage-x-fenty-audit-data.json case_studies]

**5. Decathlon Singapore — Sporting Goods / Omnichannel**
Result: +50% conversion; 50% zero-results reduction; 60% mobile search share post-deployment
Product: Personalized omnichannel search (NeuralSearch + AI Personalization)
Why it works in a pitch: omnichannel retailer with massive catalog (85,000+ SKUs) and 60+ country footprint — maps to any large-format omnichannel retailer with in-store + digital.
URL: https://resources.algolia.com/customer-stories/casestudy-decathlon-singapore [FACT — petsmart-audit-data.json; llbean-audit-data.json]

**6. BIG W — Large-Format Retail (headless React stack)**
Result: +7% search conversion · +4.7% basket increase · -10% search exits · +4 NPS
Product: Algolia Search + Recommend + Dynamic Re-Ranking (migrated from Solr)
Why it works in a pitch: Big-box retailer on headless React — the most directly comparable proof for any prospect on a composable commerce stack. Solr → Algolia migration story.
URL: https://www.algolia.com/customers/bigw [FACT — petsmart-audit-data.json case_studies]

**Bonus — Leroy Merlin Brasil (Home Improvement)**
Result: +31% CTR · +15% add-to-cart · +$28M estimated annual revenue
Product: Algolia Search (ADEO Group parent)
Relevance: ADEO is standardizing on Algolia globally — any prospect competing with a Leroy Merlin market (Mexico, Eastern Europe) faces a ticking clock.
URL: https://www.algolia.com/customers/leroy-merlin [FACT — homedepot-mexico-audit-data.json]

**Quick reference — additional verified companies:**
- PetSmart (existing customer, expansion): +5–7% web conversion · +700bps product-view rate [FACT — algolia.com/customers/PetSmart]
- Revival Animal Health: +12% revenue conversions [FACT — petsmart-audit-data.json, algolia.com/customers/revival-animal-health]
- Club Med: ~10ms search (200x faster than benchmark); higher CTR and online conversions [FACT — british-airways-audit-data.json, algolia.com/customers/club-med, published March 2026]

---

### The 10 Search Areas Prism Scores in Every Audit

These are the standard scoring dimensions. Each gets a 0–10 score and HIGH/MEDIUM/LOW severity. Prism must be able to explain what each means to a non-technical rep.

| # | Area | What it tests | HIGH means |
|---|---|---|---|
| 1 | **Latency** | How fast search responds | >500ms or full page reload on every query |
| 2 | **Typo Tolerance** | Handles misspellings | A typo → zero results; user gives up |
| 3 | **Query Suggestions / Empty State** | Autocomplete quality + "no results" page | Blank autocomplete AND generic "no results" page |
| 4 | **Intent Detection** | Understands category, brand, attribute queries | Searches like "women's running shoes red" → irrelevant wall of product |
| 5 | **Merchandising Consistency** | Browse and search return consistent, ranked results | Category page shows different top items than search for same category |
| 6 | **Content Commerce / UX** | Federated search across products + content; UI quality | Products only — no articles, no store locator, no help in search |
| 7 | **Semantic / NLP Search** | Handles conversational, multi-word, natural-language queries | "Shoes for wide feet under $100" → zero relevant results |
| 8 | **Dynamic Facets & Personalization** | Filters change by context; results differ by user history | Same results for all users regardless of history; static filter set |
| 9 | **Recommendations & Merchandising** | "Frequently bought together," banner injection, rules | No recommendations on PDP; no promotional banners via search |
| 10 | **Search Intelligence** | Trending, popular, analytics-informed ranking | No "trending" signals; results not influenced by performance data |

Overall score is weighted — HIGH-severity areas count 2x, MEDIUM 1x, LOW 0.5x. A 3/10 overall is not "mediocre" — it's a significant gap that maps directly to lost revenue.

---

### Top 5 Objections + How a Great Rep Answers Them

**Objection 1: "We're happy with our current search."**
What's happening: They haven't measured it. Current search feels fine to an internal user who knows what to type.
Response: "Let me show you what your customers actually experience." Then open the audit SPA and run the browser findings — type a conversational query, show the zero-results page, show the typo failure. The gap becomes visual in 60 seconds. "Happy with search" usually means "no one has shown me the failure mode at scale."
Pivot: "At [X]M monthly visitors, what's a 1% improvement in search conversion worth to you? Because the audit says you're leaving that on the table right now."

**Objection 2: "Too expensive."**
What's happening: Sticker shock without ROI context, or they're comparing to the apparent "free" of Elasticsearch.
Response: Build the business case from Component 1 — conversion lift. At their traffic volume and AOV, even a conservative 15% lift on search-initiated sessions produces a return multiple that dwarfs the Algolia cost. "The question isn't whether Algolia costs money. The question is what the current search failure costs you in lost revenue per month — and we can model that."
Pivot: "What does a 1% conversion lift mean to your digital revenue number? That's the frame — not the license fee."
Also: Elasticsearch isn't free. Engineering cost to self-manage is significant. Algolia replaces that labor.

**Objection 3: "We built it in-house."**
What's happening: Engineering pride, sunk cost, fear of the "we failed" narrative.
Response: Use the Under Armour peer proof. "Under Armour also built their own search. They migrated to Algolia and got 35% more conversions from search. The build-vs-buy question in search infrastructure is largely settled in your vertical." Then list what in-house doesn't do: NeuralSearch, real-time relevance, merchandiser tools without engineering tickets, Recommend.
Pivot: "What would your search team build in the next 12 months if they weren't maintaining the search infrastructure? That's the trade-off."

**Objection 4: "Switching is too risky / migration is complex."**
What's happening: Legitimate operational concern. Search is on the critical path for revenue.
Response: Algolia has a proven migration playbook. Most deployments go live in weeks, not quarters. The API-first design means they can run Algolia in parallel with the current system and flip traffic incrementally. Zero hard cutover required.
Pivot: "The risk of not switching is measured in the audit — [X] finding severity at [Y] monthly visits means approximately $[ROI estimate] in revenue impact per year. Inaction has a cost too."

**Objection 5: "Not a priority right now / bad timing."**
What's happening: This is a budget, urgency, or champion problem — not a timing problem.
Response: Use the timing signal from the audit (competitor who just moved to Algolia, exec quote about digital performance pressure, platform migration happening). "The timing isn't random — [trigger]. The window where this investment is clearly ROI-positive is now, not in 12 months when [competitor] has already deployed."
Pivot: "If not now, what has to be true for this to become a priority? Let's map that to what we found in the audit."

---

*Sources: algolia-synth-business-case SKILL.md, algolia-synth-sales-plays SKILL.md, algolia-audit-report REFERENCE.md, algolia-intel-competitors SKILL.md, audit-data.json files across nike / petsmart / dsw / brooks-running / llbean / savage-x-fenty / british-airways / homedepot-mexico audits. All case study URLs require WebFetch verification before citing in a live call — URLs do change.*
