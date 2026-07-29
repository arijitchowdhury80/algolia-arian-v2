---
name: intel-industry
version: 2.0.0
description: Vertical intelligence — benchmarks, trends, analyst quotes, and Algolia relevance narrative
cost_tier: pro-search
execution_strategy: prospect-only
composes: [intel-company]
---

## Research Mission

Produce vertical intelligence for **{company_name}** ({domain}), which operates in the **{industry}** vertical.

Your output will be used by a sales rep before a discovery call. It must answer: *what is actually happening in this vertical right now, and why is Algolia the right solution?*

This is the one module where LLM-by-default is correct — vertical benchmarks, analyst quotes, and 2025-26 trend data exist on the open web but have no structured API. Use Perplexity pro-search with citations. Do not fabricate statistics or quotes.

---

## Context from intel-company

{upstream_intel_company}

Use the `vertical`, `sub_vertical`, `company_description`, and `product_categories` fields from the above to calibrate your research. If the upstream is empty, infer the vertical from the domain and company name.

---

## What to research

### 1. Vertical identification

Classify the prospect into a canonical vertical label. Examples:
- B2C Fashion & Apparel
- B2B Industrial Distribution
- Online Marketplace
- Luxury Retail
- Home & Garden / DIY
- Health & Beauty
- Consumer Electronics
- Grocery & Food Delivery
- Media & Publishing

Use the company context above. Be specific (prefer "B2C Fashion & Apparel" over "Retail").

### 2. Benchmark statistics (3-6)

Search for published benchmark statistics from **named authoritative sources** in this vertical:
- **Baymard Institute** — search UX, site search abandonment, autocomplete quality
- **Forrester** — digital commerce search, personalization ROI
- **NRF / National Retail Federation** — retail consumer behaviour
- **Nielsen / NielsenIQ** — consumer trends
- **ECDB / eMarketer** — ecommerce market sizing
- **Gartner** — technology adoption

Requirements:
- Each stat must include: the number, the source name, and a URL if you found one
- Do not include stats you cannot attribute to a named source
- Prefer 2024-2026 data where available
- Focus on stats that connect to **search, discovery, conversion, or personalisation** — not general retail stats

### 3. Trend summary (2025-26)

Identify the 2-3 most important trends shaping search and discovery in this vertical right now. Write a 3-5 sentence narrative with:
- Named trends (not vague "AI is changing things")
- Numbers where you have them
- Written for a sales rep who needs to open a discovery conversation

Example strong trend: "72% of B2B buyers now start product discovery via search rather than browsing (Forrester, 2025), driven by catalogue complexity exceeding 100K SKUs at leading distributors..."

### 4. Analyst quotes (2-4)

Find verbatim or close-paraphrase quotes from:
- Named industry analysts (Gartner, Forrester, IDC, eMarketer)
- Industry executives (NRF, trade associations)
- Academic researchers published in credible outlets

Requirements:
- Real quotes only — never fabricate
- Include: the quote, the person's name + title, the publication, and a URL if available
- Tag each quote with the Algolia sales theme it supports: `search-as-conversion-driver`, `personalization`, `ai-search`, `speed`, `zero-results-cost`, or `null` if none fits

### 5. Algolia relevance narrative

Write 3-4 sentences for a sales rep explaining **why Algolia is the right solution for this vertical right now**. Ground it in the benchmarks and trends you found above. Do not use generic Algolia marketing copy. The narrative should feel like it was written specifically for this vertical, not copy-pasted from a product page.

---

## Output instructions

Return a single JSON object matching the `IndustryIntelOutput` schema exactly.

**Critical rules:**
1. `benchmark_stats` — every entry must have a `stat` (with a number), a named `source`, and a `relevance` sentence. Include a `url` only if you actually found one. Null is correct for `url` if you did not find a URL.
2. `analyst_quotes` — every entry must be a real quote from a named person. If you cannot find real quotes with attributions, return an empty list. Empty is correct; fabricated quotes are not.
3. `sources` — collect all URLs from `benchmark_stats` and `analyst_quotes`. Deduplicate. Perplexity will populate citations automatically — copy them here.
4. `algolia_relevance_narrative` — specific to this vertical, grounded in what you found. Not generic.
5. `vertical` — a canonical label from the examples above, or your own if none fits — but be specific.
