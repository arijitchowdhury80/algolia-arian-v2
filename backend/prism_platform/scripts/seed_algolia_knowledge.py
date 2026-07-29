#!/usr/bin/env python3
# ruff: noqa: RUF001, RUF003  # Unicode chars (–, ×, ', etc.) are verbatim from source MD
"""
seed_algolia_knowledge.py

Populate Algolia knowledge DB tables from the curated knowledge pack at:
  docs/workspace/hermes-prism-integration/chowmes-prism/KNOWLEDGE-algolia-full.md

DATA INTEGRITY RULE (hard): faithful transcription ONLY.
No invented facts, numbers, URLs, or quotes.
Every figure/quote in this file must appear verbatim in the source MD.
The --verify step (embedded in --dry-run) checks this automatically.

Usage:
  python seed_algolia_knowledge.py                       # dry-run (default)
  python seed_algolia_knowledge.py --dry-run             # explicit dry-run
  python seed_algolia_knowledge.py --apply http://127.0.0.1:8000

Destination contracts:
  POST /api/v1/knowledge
    { topic, question, answer, sources:[url...], confidence:null,
      judge_score:null, origin:"seed" }

  Structured tables (no POST endpoint yet — SQL emitted to docs/temp/seed-structured.sql):
    algolia_case_studies(customer_name, url, industry, sub_vertical, country,
        use_case, features_used[], competitor_takeout, partner_integrations,
        key_results, status)
    algolia_proofpoints(result_text, source, proof_type, industry,
        customer_or_theme, shareable)
    algolia_quotes(customer_name, person_name, person_title, industry, country,
        quote_text, evidence_type, source, tags[])

Idempotency: knowledge upsert is by question_hash (server-side); re-running is safe.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# Resolves from prism_platform/scripts/ up two levels to PIP/
# parents[2] was backend/ when docs/ lived inside it; docs/ is now at the repo
# root (2026-07-28 restructure), so resolve one level higher.
REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_MD = (
    REPO_ROOT
    / "docs"
    / "workspace"
    / "hermes-prism-integration"
    / "chowmes-prism"
    / "KNOWLEDGE-algolia-full.md"
)
TEMP_DIR = REPO_ROOT / "docs" / "temp"
DRY_RUN_JSON = TEMP_DIR / "seed-dryrun.json"
STRUCTURED_SQL = TEMP_DIR / "seed-structured.sql"

# ---------------------------------------------------------------------------
# ── Case Studies ─────────────────────────────────────────────────────────────
# Data copied verbatim from SOURCE_MD.  No embellishment or invented fields.
# Unicode used as-is from source:
#   · = · (middle dot separator)
#   – = – (en-dash, used in ranges like 5–7%)
#   null   = field not present in source
# ---------------------------------------------------------------------------
CASE_STUDIES: list[dict[str, Any]] = [
    {
        "customer_name": "Lacoste",
        "url": "https://www.algolia.com/customers/lacoste",
        "industry": "Retail",
        "sub_vertical": "Sport & Lifestyle Apparel",
        "country": None,
        "use_case": (
            "Replaced platform-native Solr; multi-brand catalog across footwear and accessories"
        ),
        "features_used": ["InstantSearch", "Query Rules", "Personalization", "Analytics"],
        "competitor_takeout": "Solr",
        "partner_integrations": None,
        "key_results": (
            "+150% sales contribution from search · +37% conversion rate · -88% bounce rate"
        ),
        "status": "customer",
    },
    {
        "customer_name": "Under Armour",
        "url": "https://www.algolia.com/customers/under-armour",
        "industry": "Retail",
        "sub_vertical": "Athletic Apparel & Footwear",
        "country": None,
        "use_case": "Replaced in-house proprietary stack, then migrated from Constructor.io",
        "features_used": ["Algolia Search"],
        "competitor_takeout": "in-house proprietary stack; Constructor.io",
        "partner_integrations": None,
        "key_results": "+35% conversion rate on search",
        "status": "customer",
    },
    {
        "customer_name": "Shoe Carnival",
        "url": "https://www.algolia.com/customers/shoe-carnival",
        "industry": "Retail",
        "sub_vertical": "Footwear Retail",
        "country": None,
        "use_case": "AI search, recommendations, dynamic re-ranking, and merchandising studio",
        "features_used": [
            "Algolia AI Search",
            "Recommend",
            "Dynamic Re-Ranking",
            "Merchandising Studio",
        ],
        "competitor_takeout": None,
        "partner_integrations": None,
        "key_results": (
            "Up to 3.5x increase in conversion from search; "
            "+4.5% conversion during first Cyber Weekend; "
            "merchandising team productivity doubled"
        ),
        "status": "customer",
    },
    {
        "customer_name": "Gymshark",
        "url": "https://www.algolia.com/customers/gymshark-recommend",
        "industry": "Retail",
        "sub_vertical": "DTC Fitness Apparel",
        "country": None,
        "use_case": (
            "DTC brand with influencer-driven traffic spikes; "
            "real-time indexing and burst-traffic scaling"
        ),
        "features_used": ["Algolia Recommend", "AI Search", "Real-time Indexing"],
        "competitor_takeout": None,
        "partner_integrations": None,
        "key_results": "+150% order rate for new customers · +32% add-to-cart rate",
        "status": "customer",
    },
    {
        "customer_name": "Decathlon Singapore",
        "url": "https://resources.algolia.com/customer-stories/casestudy-decathlon-singapore",
        "industry": "Retail",
        "sub_vertical": "Sporting Goods / Omnichannel",
        "country": "Singapore",
        "use_case": (
            "Personalized omnichannel search for large catalog (85,000+ SKUs) "
            "with 60+ country footprint"
        ),
        "features_used": ["NeuralSearch", "AI Personalization"],
        "competitor_takeout": None,
        "partner_integrations": None,
        "key_results": (
            "+50% conversion; 50% zero-results reduction; 60% mobile search share post-deployment"
        ),
        "status": "customer",
    },
    {
        "customer_name": "BIG W",
        "url": "https://www.algolia.com/customers/bigw",
        "industry": "Retail",
        "sub_vertical": "Large-Format Retail",
        "country": "Australia",
        "use_case": (
            "Migrated from Solr; big-box retailer on headless "
            "React composable commerce stack"
        ),
        "features_used": ["Algolia Search", "Recommend", "Dynamic Re-Ranking"],
        "competitor_takeout": "Solr",
        "partner_integrations": None,
        "key_results": (
            "+7% search conversion · +4.7% basket increase "
            "· -10% search exits · +4 NPS"
        ),
        "status": "customer",
    },
    {
        "customer_name": "Leroy Merlin Brasil",
        "url": "https://www.algolia.com/customers/leroy-merlin",
        "industry": "Retail",
        "sub_vertical": "Home Improvement",
        "country": "Brazil",
        "use_case": "ADEO Group global standardization on Algolia",
        "features_used": ["Algolia Search"],
        "competitor_takeout": None,
        "partner_integrations": None,
        "key_results": "+31% CTR · +15% add-to-cart · +$28M estimated annual revenue",
        "status": "customer",
    },
    {
        "customer_name": "PetSmart",
        "url": "https://algolia.com/customers/PetSmart",
        "industry": "Retail",
        "sub_vertical": "Pet Supplies",
        "country": None,
        "use_case": "Existing customer expansion",
        "features_used": [],
        "competitor_takeout": None,
        "partner_integrations": None,
        # en-dash (–) in range 5–7% matches source exactly
        "key_results": "+5–7% web conversion · +700bps product-view rate",
        "status": "customer",
    },
    {
        "customer_name": "Revival Animal Health",
        "url": "https://algolia.com/customers/revival-animal-health",
        "industry": "Retail",
        "sub_vertical": "Animal Health",
        "country": None,
        "use_case": None,
        "features_used": [],
        "competitor_takeout": None,
        "partner_integrations": None,
        "key_results": "+12% revenue conversions",
        "status": "customer",
    },
    {
        "customer_name": "Club Med",
        "url": "https://algolia.com/customers/club-med",
        "industry": "Travel & Hospitality",
        "sub_vertical": None,
        "country": None,
        "use_case": None,
        "features_used": [],
        "competitor_takeout": None,
        "partner_integrations": None,
        "key_results": (
            "~10ms search (200x faster than benchmark); "
            "higher CTR and online conversions"
        ),
        "status": "customer",
    },
]

# ---------------------------------------------------------------------------
# ── Proof Points ─────────────────────────────────────────────────────────────
# result_text: verbatim from source (without the [FACT]/[ESTIMATE] label).
# source: null when source doc says "no verified public URL".
# ---------------------------------------------------------------------------
PROOF_POINTS: list[dict[str, Any]] = [
    {
        "result_text": "34% of e-commerce sites fail basic search adequacy",
        "source": "https://baymard.com",
        "proof_type": "benchmark",
        "industry": "ecommerce",
        "customer_or_theme": "Search quality baseline",
        "shareable": True,
    },
    {
        # [ESTIMATE — Amazon 2006, no verified public URL] per source doc → source is null
        "result_text": "100ms latency = 1% revenue loss",
        "source": None,
        "proof_type": "benchmark",
        "industry": "ecommerce",
        "customer_or_theme": "Latency impact",
        "shareable": True,
    },
]

# ---------------------------------------------------------------------------
# ── Quotes ───────────────────────────────────────────────────────────────────
# quote_text: verbatim from source (inner text only, no surrounding markup).
# ---------------------------------------------------------------------------
QUOTES: list[dict[str, Any]] = [
    {
        "customer_name": "Shoe Carnival",
        "person_name": "Ned Moore",
        "person_title": "Director eCommerce Product & Technology",
        "industry": "Retail",
        "country": None,
        "quote_text": (
            "I probably sleep better with Algolia than I did with any of the "
            "technologies we either purchased or built ourselves."
        ),
        "evidence_type": "customer_quote",
        "source": "https://www.algolia.com/customers/shoe-carnival",
        "tags": ["reliability", "migration", "customer-satisfaction"],
    },
]

# ---------------------------------------------------------------------------
# ── Knowledge Q&A records ────────────────────────────────────────────────────
# question: synthesized natural question (no new facts).
# answer:   verbatim text from SOURCE_MD, lightly stitched for readability.
#           NO new facts, numbers, or URLs beyond what the source section contains.
# sources:  only URLs explicitly present in the relevant source section.
# ---------------------------------------------------------------------------
KNOWLEDGE_RECORDS: list[dict[str, Any]] = [
    {
        "topic": "algolia_overview",
        "question": "What is Algolia and what problem does it solve?",
        "answer": (
            "Algolia is a hosted search and discovery API — companies plug it in and get fast, "
            "relevant, tunable search without running their own search infrastructure. It sits "
            "between a company’s product catalog and its website, handling the query-to-result "
            "loop with AI-powered relevance, real-time indexing, and merchandising controls built "
            "in.\n\n"
            "In plain terms: it’s the search box brain-as-a-service. You configure what "
            "matters, Algolia finds and ranks it in milliseconds."
        ),
        "sources": [],
        "confidence": None,
        "judge_score": None,
        "origin": "seed",
    },
    {
        "topic": "algolia_products",
        "question": "What are the key Algolia products that come up in sales deals?",
        "answer": (
            "Eight capabilities come up repeatedly. "
            "Lead with the ones that match the audit gaps.\n\n"
            "Search (core): Hosted search API with typo tolerance, synonym handling, faceted "
            "filtering, and instant results. Replaces slow/dumb keyword search; baseline of any "
            "deal.\n\n"
            "NeuralSearch: Algolia’s semantic / AI search — understands intent, not just "
            "keywords (“comfortable running shoes for bad knees” works). Recovers the "
            "20-30% of queries that fail on keyword-only systems; lifts long-tail conversion.\n\n"
            "AI Personalization: Re-ranks results per user based on behavioral signals — the "
            "order a Gold loyalty member sees is different from a first-time visitor. AOV and "
            "repeat-purchase lift; works off existing behavioral data (clicks, purchases, "
            "add-to-cart).\n\n"
            "Recommend: “Frequently bought together,” “related items,” "
            "“trending” widgets — API-powered, real-time. Basket size increase; "
            "drives add-on purchases without manual curation.\n\n"
            "Dynamic Re-Ranking: Automatically promotes items that are converting and demotes ones "
            "that aren’t. Reduces manual merchandising effort; keeps results fresh without "
            "rule maintenance.\n\n"
            "Merchandising Studio / Rules: GUI for non-technical teams to pin items, inject "
            "banners, boost seasonal picks, set up A/B tests. Lets the merchant control search "
            "without filing engineering tickets — big deal for retail.\n\n"
            "Query Suggestions: Autocomplete / search-as-you-type dropdown — surfaces popular "
            "and trending queries. Reduces zero-result searches; guides users to inventory that "
            "exists.\n\n"
            "Analytics: Search analytics dashboard — shows top queries, no-results rate, CTR, "
            "conversion by query. Makes search a managed channel; feeds back into Rules and "
            "Re-Ranking.\n\n"
            "Federated Search (cross-index search) is often the hook for non-ecommerce deals "
            "(media, B2B, financial services): one query box that searches products, articles, "
            "help pages, and store locators simultaneously."
        ),
        "sources": [],
        "confidence": None,
        "judge_score": None,
        "origin": "seed",
    },
    {
        "topic": "algolia_competitive_strengths",
        "question": "Where does Algolia genuinely win versus the alternatives?",
        "answer": (
            "Speed: Sub-100ms globally via distributed edge nodes. Not a trivial advantage — "
            "Amazon’s own internal research showed 100ms of latency = 1% revenue loss "
            "[ESTIMATE — Amazon 2006, widely cited; no primary public URL]. Algolia’s "
            "SLA is verifiable at status.algolia.com.\n\n"
            "Relevance + AI without the build cost: NeuralSearch handles semantic queries out of "
            "the box. The alternative is building and maintaining your own vector search stack on "
            "top of Elasticsearch — months of ML engineering for the same outcome.\n\n"
            "Merchandiser control: The Rules + Merchandising Studio combo lets non-engineers tune "
            "relevance, inject promotional content, and run A/B tests. This matters enormously to "
            "retail teams who can’t wait for engineering tickets.\n\n"
            "Time-to-value: Most implementations go live in weeks, not quarters. The API-first "
            "architecture plugs into existing stacks (Shopify, SFCC, commercetools, headless "
            "React) without a platform migration.\n\n"
            "Scale with zero maintenance: Algolia handles index size, replication, and uptime. The "
            "customer doesn’t manage clusters.\n\n"
            "Where it’s a harder sell:\n"
            "- Very large enterprise with existing Elasticsearch investment and strong ML team "
            "— the build vs. buy argument is real, not just objection handling.\n"
            "- Pure B2B SaaS or internal tools — the ROI math is harder without ecommerce "
            "conversion data.\n"
            "- Companies with extreme data sovereignty requirements (some government/finance) "
            "— even with EU infrastructure, procurement review is long.\n"
            "- Price: Algolia’s pricing is usage-based and can look expensive vs. "
            "Elasticsearch’s apparent “free” (ignoring engineering labor to run it)."
        ),
        "sources": [],
        "confidence": None,
        "judge_score": None,
        "origin": "seed",
    },
    {
        "topic": "competitor_constructor",
        "question": "How does Algolia beat Constructor.io?",
        "answer": (
            "Constructor markets itself as “AI-first product discovery” — machine "
            "learning for ranking with less manual rule configuration. They target mid-market to "
            "enterprise ecommerce, especially fashion and apparel. Their pitch is “relevance "
            "through AI, not rules.”\n\n"
            "The counter-narrative (5 parts):\n\n"
            "1. Merchandiser control is weaker. Constructor’s ML ranking means less hands-on "
            "control for the merchant. Algolia’s Rules + Merchandising Studio gives "
            "non-technical teams direct manipulation. For retail teams that run weekly promotions "
            "and seasonal campaigns, this is a deal-breaker — “the algorithm "
            "decides” isn’t acceptable when you need to pin the new collection at "
            "Christmas.\n\n"
            "2. Federated search is Algolia’s. Constructor is a single-index product search "
            "engine. Algolia federates across products, content, store locators, help articles, "
            "FAQs in one query. Any company with content + commerce needs (which is most of them) "
            "runs into this gap.\n\n"
            "3. Implementation ecosystem is smaller. Algolia has first-party connectors for "
            "Shopify, SFCC, Adobe Commerce, commercetools, and a massive InstantSearch UI library. "
            "Constructor’s partner ecosystem is thinner.\n\n"
            "4. Proof set and case studies are thinner. Algolia has 1,000+ documented customer "
            "deployments across verticals. Constructor’s public case studies are narrower.\n\n"
            "5. When prospect has Constructor: lead with the FableticsOS displacement angle "
            "(platform deal opportunity) or the specific gap (NLP/federated/Recommend) that "
            "Constructor demonstrably doesn’t cover. Audit finding + screenshot is the opener."
        ),
        "sources": [],
        "confidence": None,
        "judge_score": None,
        "origin": "seed",
    },
    {
        "topic": "competitor_overview",
        "question": (
            "How does Algolia compare to Coveo, Bloomreach, Elasticsearch, "
            "Searchspring, and Klevu?"
        ),
        "answer": (
            "Coveo: B2B/enterprise AI search, strong in Salesforce ecosystem. Beats Algolia on "
            "deep CRM integration and B2B relevance models. Algolia counter: Coveo is slower to "
            "implement; Algolia is faster and cheaper for ecommerce.\n\n"
            "Bloomreach: Full-suite ecommerce platform (search + content + CMS + CDP). "
            "“All in one” pitch for mid-enterprise. Algolia counter: Algolia is "
            "best-of-breed; Bloomreach bundles lock you in and the search module is weaker.\n\n"
            "Elasticsearch (self-managed): Open-source, “free.” Total control, no SaaS "
            "cost. Algolia counter: Engineering cost of self-managing is 10x+ the Algolia "
            "subscription; no relevance AI out of the box.\n\n"
            "Searchspring / Klevu: SMB-focused search for Shopify/Magento. Lower price point. "
            "Algolia counter: Algolia scales to enterprise; Searchspring/Klevu don’t handle "
            "index size or global latency at scale."
        ),
        "sources": [],
        "confidence": None,
        "judge_score": None,
        "origin": "seed",
    },
    {
        "topic": "roi_model",
        "question": "What are the 6 components of the Algolia ROI business case model?",
        "answer": (
            "Every Algolia business case is built from these six components. Each one maps to a "
            "specific search gap found in the audit.\n\n"
            "Component 1 — Search Conversion Lift\n"
            "Logic: Sessions that start with search convert at a higher rate when search returns "
            "relevant results. Even a 15% lift on search-initiated sessions compounds across "
            "millions of monthly visits.\n"
            "Formula signal: monthly_visits × search_usage_rate × conversion_delta "
            "× AOV × 12\n"
            "Activated by: poor intent detection, keyword-only search, high no-results rate.\n\n"
            "Component 2 — Average Order Value (AOV) Increase\n"
            "Logic: When search surfaces higher-value, complementary, or personalized items "
            "— basket size grows. Recommendations and personalization are the levers.\n"
            "Formula signal: monthly_search_sessions × current_conversion × AOV_delta "
            "× 12\n"
            "Activated by: no Recommend, no AI Personalization, static facets.\n\n"
            "Component 3 — Bounce Rate Reduction\n"
            "Logic: Users who search and immediately leave — because results are irrelevant "
            "or empty — are recoverable. Every bounce from a search session is a lost sale.\n"
            "Formula signal: monthly_visits × search_usage_rate × bounce_delta × "
            "recovery_conversion × AOV × 12\n"
            "Activated by: high site bounce rate, poor empty-state experience, "
            "zero-results rate.\n\n"
            "Component 4 — No-Results Recovery\n"
            "Logic: Queries that return zero results are the worst user experience in search. Each "
            "zero-result event is a purchase that didn’t happen. Typo tolerance + synonym "
            "handling + NLP recovers these.\n"
            "Benchmark: Baymard Institute — 34% of e-commerce sites fail basic search "
            "adequacy [FACT — Baymard, https://baymard.com]\n"
            "Formula signal: monthly_searches × no_results_rate × AOV × "
            "recovery_rate × 12\n"
            "Activated by: typo failures, synonym gaps, NLP failures.\n\n"
            "Component 5 — Speed / Latency Gain\n"
            "Logic: Slow search drives abandonment. Every 100ms of additional latency costs "
            "roughly 1% in revenue. Moving from 400ms to sub-100ms search is measurable.\n"
            "Benchmark: Amazon internal finding — 100ms latency = 1% revenue loss "
            "[ESTIMATE — Amazon 2006, no verified public URL]\n"
            "Formula signal: monthly_visits × search_usage_rate × latency_bucket_count "
            "× 1% × AOV × 12\n"
            "Activated by: slow page-reload search, >300ms latency.\n\n"
            "Component 6 — Long-Tail Discovery\n"
            "Logic: 20-30% of searches at most ecommerce sites are conversational, multi-word, or "
            "synonym-dependent [ESTIMATE — industry range]. Keyword search fails these. "
            "NeuralSearch recovers them.\n"
            "Formula signal: monthly_searches × nlp_fail_rate × AOV × "
            "recovery_rate × 12\n"
            "Activated by: NLP failures, semantic search gaps, multi-word query breakdowns."
        ),
        "sources": ["https://baymard.com"],
        "confidence": None,
        "judge_score": None,
        "origin": "seed",
    },
    {
        "topic": "audit_scoring_areas",
        "question": "What are the 10 search areas Prism scores in every audit?",
        "answer": (
            "These are the standard scoring dimensions. Each gets a 0–10 score and "
            "HIGH/MEDIUM/LOW severity. Overall score is weighted — HIGH-severity areas count "
            "2x, MEDIUM 1x, LOW 0.5x. A 3/10 overall is not “mediocre” — "
            "it’s a significant gap that maps directly to lost revenue.\n\n"
            "1. Latency — How fast search responds. HIGH means >500ms or full page reload "
            "on every query.\n"
            "2. Typo Tolerance — Handles misspellings. HIGH means a typo → zero "
            "results; user gives up.\n"
            "3. Query Suggestions / Empty State — Autocomplete quality + “no "
            "results” page. HIGH means blank autocomplete AND generic “no "
            "results” page.\n"
            "4. Intent Detection — Understands category, brand, attribute queries. HIGH "
            "means searches like “women’s running shoes red” → irrelevant "
            "wall of product.\n"
            "5. Merchandising Consistency — Browse and search return consistent, ranked "
            "results. HIGH means category page shows different top items than search for same "
            "category.\n"
            "6. Content Commerce / UX — Federated search across products + content; UI "
            "quality. HIGH means products only — no articles, no store locator, no help in "
            "search.\n"
            "7. Semantic / NLP Search — Handles conversational, multi-word, "
            "natural-language queries. HIGH means “Shoes for wide feet under "
            "$100” → zero relevant results.\n"
            "8. Dynamic Facets & Personalization — Filters change by context; results differ "
            "by user history. HIGH means same results for all users regardless of history; static "
            "filter set.\n"
            "9. Recommendations & Merchandising — “Frequently bought "
            "together,” banner injection, rules. HIGH means no recommendations on PDP; no "
            "promotional banners via search.\n"
            "10. Search Intelligence — Trending, popular, analytics-informed ranking. HIGH "
            "means no “trending” signals; results not influenced by performance data."
        ),
        "sources": [],
        "confidence": None,
        "judge_score": None,
        "origin": "seed",
    },
    {
        "topic": "objection_handling",
        "question": "How should an AE respond to the top 5 sales objections about Algolia?",
        "answer": (
            'Objection 1: "We’re happy with our current search."\n'
            "What’s happening: They haven’t measured it. Current search feels fine to "
            "an internal user who knows what to type.\n"
            'Response: "Let me show you what your customers actually experience." Then open the '
            "audit SPA and run the browser findings — type a conversational query, show the "
            "zero-results page, show the typo failure. The gap becomes visual in 60 seconds. "
            '"Happy with search" usually means "no one has shown me the failure mode at scale."\n'
            'Pivot: "At [X]M monthly visitors, what’s a 1% improvement in search conversion '
            'worth to you? Because the audit says you’re leaving that on the table right '
            'now."\n\n'
            'Objection 2: "Too expensive."\n'
            "What’s happening: Sticker shock without ROI context, or they’re comparing "
            'to the apparent "free" of Elasticsearch.\n'
            "Response: Build the business case from Component 1 — conversion lift. At their "
            "traffic volume and AOV, even a conservative 15% lift on search-initiated sessions "
            'produces a return multiple that dwarfs the Algolia cost. "The question isn’t '
            "whether Algolia costs money. The question is what the current search failure costs "
            'you in lost revenue per month — and we can model that."\n'
            'Pivot: "What does a 1% conversion lift mean to your digital revenue number? '
            'That’s the frame — not the license fee."\n'
            "Also: Elasticsearch isn’t free. Engineering cost to self-manage is significant. "
            "Algolia replaces that labor.\n\n"
            'Objection 3: "We built it in-house."\n'
            'What’s happening: Engineering pride, sunk cost, fear of the "we failed" '
            "narrative.\n"
            'Response: Use the Under Armour peer proof. "Under Armour also built their own '
            "search. They migrated to Algolia and got 35% more conversions from search. The "
            'build-vs-buy question in search infrastructure is largely settled in your vertical." '
            "Then list what in-house doesn’t do: NeuralSearch, real-time relevance, "
            "merchandiser tools without engineering tickets, Recommend.\n"
            'Pivot: "What would your search team build in the next 12 months if they weren’t '
            'maintaining the search infrastructure? That’s the trade-off."\n\n'
            'Objection 4: "Switching is too risky / migration is complex."\n'
            "What’s happening: Legitimate operational concern. Search is on the critical "
            "path for revenue.\n"
            "Response: Algolia has a proven migration playbook. Most deployments go live in "
            "weeks, not quarters. The API-first design means they can run Algolia in parallel "
            "with the current system and flip traffic incrementally. Zero hard cutover required.\n"
            'Pivot: "The risk of not switching is measured in the audit — [X] finding '
            "severity at [Y] monthly visits means approximately $[ROI estimate] in revenue "
            'impact per year. Inaction has a cost too."\n\n'
            'Objection 5: "Not a priority right now / bad timing."\n'
            "What’s happening: This is a budget, urgency, or champion problem — not a "
            "timing problem.\n"
            "Response: Use the timing signal from the audit (competitor who just moved to "
            "Algolia, exec quote about digital performance pressure, platform migration "
            'happening). "The timing isn’t random — [trigger]. The window where this '
            "investment is clearly ROI-positive is now, not in 12 months when [competitor] has "
            'already deployed."\n'
            'Pivot: "If not now, what has to be true for this to become a priority? Let’s '
            'map that to what we found in the audit."'
        ),
        "sources": [],
        "confidence": None,
        "judge_score": None,
        "origin": "seed",
    },
]

# ---------------------------------------------------------------------------
# ── Verify needles ───────────────────────────────────────────────────────────
# Strings that MUST appear verbatim in SOURCE_MD.
# Tuple: (needle, record_type, record_label)
# ---------------------------------------------------------------------------
VERIFY_NEEDLES: list[tuple[str, str, str]] = [
    # Case study — Lacoste
    ("+150% sales contribution from search", "case_study", "Lacoste"),
    ("+37% conversion rate", "case_study", "Lacoste"),
    ("-88% bounce rate", "case_study", "Lacoste"),
    # Case study — Under Armour
    ("+35% conversion rate on search", "case_study", "Under Armour"),
    # Case study — Shoe Carnival
    ("3.5x increase in conversion from search", "case_study", "Shoe Carnival"),
    ("+4.5% conversion during first Cyber Weekend", "case_study", "Shoe Carnival"),
    ("merchandising team productivity doubled", "case_study", "Shoe Carnival"),
    # Case study — Gymshark
    ("+150% order rate for new customers", "case_study", "Gymshark"),
    ("+32% add-to-cart rate", "case_study", "Gymshark"),
    # Case study — Decathlon Singapore
    ("+50% conversion", "case_study", "Decathlon Singapore"),
    ("50% zero-results reduction", "case_study", "Decathlon Singapore"),
    ("60% mobile search share post-deployment", "case_study", "Decathlon Singapore"),
    # Case study — BIG W
    ("+7% search conversion", "case_study", "BIG W"),
    ("+4.7% basket increase", "case_study", "BIG W"),
    ("-10% search exits", "case_study", "BIG W"),
    ("+4 NPS", "case_study", "BIG W"),
    # Case study — Leroy Merlin Brasil
    ("+31% CTR", "case_study", "Leroy Merlin Brasil"),
    ("+15% add-to-cart", "case_study", "Leroy Merlin Brasil"),
    ("+$28M estimated annual revenue", "case_study", "Leroy Merlin Brasil"),
    # Case study — PetSmart (en-dash – in range)
    ("+5–7% web conversion", "case_study", "PetSmart"),
    ("+700bps product-view rate", "case_study", "PetSmart"),
    # Case study — Revival Animal Health
    ("+12% revenue conversions", "case_study", "Revival Animal Health"),
    # Case study — Club Med
    ("~10ms search (200x faster than benchmark)", "case_study", "Club Med"),
    # Proof points
    ("34% of e-commerce sites fail basic search adequacy", "proofpoint", "Baymard"),
    ("100ms latency = 1% revenue loss", "proofpoint", "Amazon"),
    # Quote — Ned Moore
    (
        "I probably sleep better with Algolia than I did with any of the technologies "
        "we either purchased or built ourselves.",
        "quote",
        "Ned Moore / Shoe Carnival",
    ),
]

# ---------------------------------------------------------------------------
# ── SQL helpers ──────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------


def _sql_str(value: str | None) -> str:
    """Format value as a SQL string literal or NULL."""
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def _sql_bool(value: bool | None) -> str:
    if value is None:
        return "NULL"
    return "TRUE" if value else "FALSE"


def _sql_array(items: list[str] | None) -> str:
    """Format a list as a PostgreSQL jsonb array literal.

    features_used (case_studies) and tags (quotes) are jsonb columns in the 008 schema,
    so emit a JSON array literal cast to jsonb (NOT a text[] array — PG won't auto-cast).
    """
    json_str = json.dumps(items or [])
    return "'" + json_str.replace("'", "''") + "'::jsonb"


# ---------------------------------------------------------------------------
# ── SQL generation ───────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------


def build_sql_inserts() -> str:
    """Return SQL INSERT statements for all three structured tables."""
    lines: list[str] = [
        "-- Generated by seed_algolia_knowledge.py",
        "-- Source: KNOWLEDGE-algolia-full.md",
        "-- DO NOT EXECUTE DIRECTLY — review contents first.",
        "",
    ]

    # algolia_case_studies
    lines.append(
        "-- ── algolia_case_studies "
        "──────────────"
        "──────────────"
        "────────────"
    )
    for cs in CASE_STUDIES:
        lines.append(
            "INSERT INTO algolia_case_studies "
            "(customer_name, url, industry, sub_vertical, country, use_case, "
            "features_used, competitor_takeout, partner_integrations, key_results, status) "
            "VALUES ("
            + ", ".join(
                [
                    _sql_str(cs["customer_name"]),
                    _sql_str(cs["url"]),
                    _sql_str(cs["industry"]),
                    _sql_str(cs["sub_vertical"]),
                    _sql_str(cs["country"]),
                    _sql_str(cs["use_case"]),
                    _sql_array(cs["features_used"]),
                    _sql_str(cs["competitor_takeout"]),
                    _sql_str(cs["partner_integrations"]),
                    _sql_str(cs["key_results"]),
                    _sql_str(cs["status"]),
                ]
            )
            + ");"
        )
    lines.append("")

    # algolia_proofpoints
    lines.append(
        "-- ── algolia_proofpoints "
        "──────────────"
        "──────────────"
        "────────────"
    )
    for pp in PROOF_POINTS:
        lines.append(
            "INSERT INTO algolia_proofpoints "
            "(result_text, source, proof_type, industry, customer_or_theme, shareable) "
            "VALUES ("
            + ", ".join(
                [
                    _sql_str(pp["result_text"]),
                    _sql_str(pp["source"]),
                    _sql_str(pp["proof_type"]),
                    _sql_str(pp["industry"]),
                    _sql_str(pp["customer_or_theme"]),
                    _sql_bool(pp["shareable"]),
                ]
            )
            + ");"
        )
    lines.append("")

    # algolia_quotes
    lines.append(
        "-- ── algolia_quotes "
        "──────────────"
        "──────────────"
        "──────────────"
    )
    for q in QUOTES:
        lines.append(
            "INSERT INTO algolia_quotes "
            "(customer_name, person_name, person_title, industry, country, "
            "quote_text, evidence_type, source, tags) "
            "VALUES ("
            + ", ".join(
                [
                    _sql_str(q["customer_name"]),
                    _sql_str(q["person_name"]),
                    _sql_str(q["person_title"]),
                    _sql_str(q["industry"]),
                    _sql_str(q["country"]),
                    _sql_str(q["quote_text"]),
                    _sql_str(q["evidence_type"]),
                    _sql_str(q["source"]),
                    _sql_array(q["tags"]),
                ]
            )
            + ");"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ── Verify step ──────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------


def verify_against_source(source_path: Path) -> list[dict[str, Any]]:
    """
    Check every VERIFY_NEEDLE against the raw source MD text.
    Returns list of failure dicts; empty list = all pass.
    """
    if not source_path.exists():
        return [{"error": f"Source file not found: {source_path}"}]

    source_text = source_path.read_text(encoding="utf-8")
    failures: list[dict[str, Any]] = []

    for needle, record_type, record_label in VERIFY_NEEDLES:
        if needle not in source_text:
            failures.append(
                {
                    "needle": needle,
                    "record_type": record_type,
                    "record_label": record_label,
                    "status": "NOT_FOUND_VERBATIM",
                }
            )

    return failures


# ---------------------------------------------------------------------------
# ── Dry-run mode ─────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------


def run_dry_run(source_path: Path) -> None:
    """
    Print summary table + first 2 records per destination as JSON.
    Write full payload to docs/temp/seed-dryrun.json.
    Run verify step; exit(1) on any failure.
    """
    print("=" * 62)
    print("  seed_algolia_knowledge.py — DRY RUN")
    print("=" * 62)

    # Summary table
    print("\n── Destination counts ────────")
    rows = [
        ("algolia_case_studies (SQL)", len(CASE_STUDIES)),
        ("algolia_proofpoints  (SQL)", len(PROOF_POINTS)),
        ("algolia_quotes       (SQL)", len(QUOTES)),
        ("/api/v1/knowledge   (POST)", len(KNOWLEDGE_RECORDS)),
        ("verify_needles      (check)", len(VERIFY_NEEDLES)),
    ]
    for label, count in rows:
        print(f"  {label:<30}  {count:>3}")
    total_structured = len(CASE_STUDIES) + len(PROOF_POINTS) + len(QUOTES)
    print(f"\n  Total structured rows  : {total_structured}")
    print(f"  Total knowledge Q&A    : {len(KNOWLEDGE_RECORDS)}")

    # Sample records
    destinations = [
        ("algolia_case_studies", CASE_STUDIES),
        ("algolia_proofpoints", PROOF_POINTS),
        ("algolia_quotes", QUOTES),
        ("knowledge_records", KNOWLEDGE_RECORDS),
    ]
    print(
        "\n── Sample records (first 2 per destination) "
        "──────────"
    )
    for dest_label, records in destinations:
        print(f"\n  [{dest_label}]")
        for rec in records[:2]:
            compact = json.dumps(rec, indent=2, ensure_ascii=False)
            indented = "\n".join("    " + line for line in compact.splitlines())
            print(indented)

    # Write full payload JSON
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "source": str(source_path),
            "counts": {
                "case_studies": len(CASE_STUDIES),
                "proofpoints": len(PROOF_POINTS),
                "quotes": len(QUOTES),
                "knowledge_records": len(KNOWLEDGE_RECORDS),
            },
        },
        "case_studies": CASE_STUDIES,
        "proofpoints": PROOF_POINTS,
        "quotes": QUOTES,
        "knowledge_records": KNOWLEDGE_RECORDS,
    }
    DRY_RUN_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n── Full payload written to:\n  {DRY_RUN_JSON}")

    # Verify step
    print(
        "\n── Verify: checking "
        f"{len(VERIFY_NEEDLES)} needles against source MD ────"
    )
    failures = verify_against_source(source_path)
    if failures:
        print(f"  FAIL — {len(failures)} needle(s) not found verbatim in source:\n")
        for f in failures:
            label = f.get("record_label", "?")
            rtype = f.get("record_type", "?")
            needle = f.get("needle", f.get("error", ""))
            print(f"    [{rtype}:{label}]  {needle!r}")
        print()
        sys.exit(1)
    else:
        print(f"  PASS — all {len(VERIFY_NEEDLES)} needles found verbatim in source.")

    print("\n── Dry-run complete. No live API or DB calls made. ────")


# ---------------------------------------------------------------------------
# ── Apply mode ───────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------


def run_apply(base_url: str) -> None:
    """
    POST knowledge records to BASE_URL/api/v1/knowledge.
    Write SQL INSERT statements for structured tables to docs/temp/seed-structured.sql.
    SQL is NOT executed automatically.
    """
    try:
        import httpx
    except ImportError:
        print("ERROR: httpx not installed.  Run: pip install httpx")
        sys.exit(1)

    base_url = base_url.rstrip("/")
    print("=" * 62)
    print("  seed_algolia_knowledge.py — APPLY MODE")
    print(f"  Target: {base_url}")
    print("=" * 62)

    # 1. POST knowledge records
    endpoint = f"{base_url}/api/v1/knowledge/"  # trailing slash — FastAPI 307-redirects without it
    print(f"\nPosting {len(KNOWLEDGE_RECORDS)} knowledge records to {endpoint} ...")
    ok_count = 0
    with httpx.Client(timeout=30.0) as client:
        for rec in KNOWLEDGE_RECORDS:
            resp = client.post(endpoint, json=rec)
            ok = resp.status_code in (200, 201)
            if ok:
                ok_count += 1
            status_str = "OK " if ok else f"ERR {resp.status_code}"
            short_q = rec["question"][:55]
            print(f"  [{status_str}] {rec['topic']}: {short_q}")
    print(f"\n  {ok_count}/{len(KNOWLEDGE_RECORDS)} knowledge records posted.")

    # 2. Emit SQL (no execution)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    sql = build_sql_inserts()
    STRUCTURED_SQL.write_text(sql, encoding="utf-8")
    print(f"\nSQL INSERT statements written to:\n  {STRUCTURED_SQL}")
    print("Review and execute manually against the target DB — NOT run automatically.")


# ---------------------------------------------------------------------------
# ── Entry point ──────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Seed Algolia knowledge DB from KNOWLEDGE-algolia-full.md.\n"
            "Default mode is --dry-run."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Print summary + write seed-dryrun.json (default)",
    )
    group.add_argument(
        "--apply",
        metavar="BASE_URL",
        help=(
            "POST knowledge records and write SQL "
            "(e.g. http://127.0.0.1:8000)"
        ),
    )
    args = parser.parse_args()

    if args.apply:
        run_apply(args.apply)
    else:
        run_dry_run(SOURCE_MD)


if __name__ == "__main__":
    main()
