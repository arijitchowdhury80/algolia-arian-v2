---
name: synth-business-case
version: 2.0.0
description: ROI business-case synthesis from upstream intelligence — Said-vs-Found, value levers, displacement cost, customer proofs, timing
cost_tier: pro-search
execution_strategy: prospect-only
composes: [intel-company, intel-investor, intel-industry, intel-competitors, intel-techstack, intel-traffic, intel-financial-public, intel-financial-private, intel-news, intel-hiring, intel-social]
---

## Mission

Build a CFO-grade ROI **business case** for adopting Algolia at **{company_name}** ({domain}).

This is a **pure synthesis** task. Do NOT research the open web. Every claim must be grounded in
the upstream intelligence provided below — quote it, cite which module it came from, and never
fabricate a statistic, quote, or customer metric. Where a number is your own estimate, label it
clearly and set `evidence_tier="ESTIMATE"`. Output must validate against the required schema.

---

## Upstream intelligence (your only source material)

### Company context
{upstream_intel_company}

### Executive / investor signals (verbatim quotes, earnings, priorities)
{upstream_intel_investor}

### Industry benchmarks & vertical trends
{upstream_intel_industry}

### Competitors & their search vendors (Golden Angle)
{upstream_intel_competitors}

### Current tech / search stack
{upstream_intel_techstack}

### Traffic & engagement
{upstream_intel_traffic}

### Financials (public)
{upstream_intel_financial_public}

### Financials (private estimate)
{upstream_intel_financial_private}

### Recent news
{upstream_intel_news}

### Hiring signals
{upstream_intel_hiring}

### Social signals
{upstream_intel_social}

If a section above is empty, omit claims that would depend on it — do not invent substitutes.

---

## What to produce

### Part 1 — Said vs Found matrix (`said_vs_found`)
For each strategic theme, a 4-column row:
- **exec_said** — a verbatim executive quote (with speaker + source) from intel-investor/news. No quote → skip the row, don't paraphrase.
- **we_found** — what the audit data shows, citing the source module (e.g. "intel-traffic: 18% bounce on search").
- **competitors_doing** — what competitors are doing, from intel-competitors (name the vendor; flag Algolia customers as proof).
- **your_move** — how Algolia closes the gap AND leapfrogs competitors.
- **category** — one of the allowed enum values. **evidence_tier** — VERIFIED if grounded in a cited upstream fact, else ESTIMATE.

### Part 2 — ROI value levers (`value_levers`)
3-6 levers (conversion uplift, zero-result recovery, latency/bounce, merchandising efficiency,
displacement savings…). For each: `conservative_estimate` + `moderate_estimate` (annual USD floats),
`calculation_method` (show the math, anchored to traffic/financial figures upstream), `assumptions`,
and `case_study_proof` only if a real Algolia customer metric supports it. Set
`total_conservative_impact` / `total_moderate_impact` to the sums. Add a `sensitivity_analysis` narrative.

### Part 3 — Displacement (`displacement`)
Use the detected incumbent search vendor from intel-techstack/intel-competitors. Model
`cost_of_staying_annual`, `cost_of_switching`, `net_benefit_3yr` with explicit `assumptions`.
If no incumbent is known, set `current_vendor` to "unknown / proprietary" and leave costs null.

### Part 4 — Customer proofs (`customer_proofs`)
Only real, citable Algolia customers (prefer ones surfaced as competitors-on-Algolia in
intel-competitors). Match each to a `matched_lever`. Never invent a metric.

### Part 5 — Timing signals (`timing_signals`)
Pull urgency from intel-news/-hiring/-investor (funding, leadership change, replatforming, hiring
search/eng roles). Each: `source_module`, `urgency`, `reason`. Add a 1-2 sentence `urgency_summary`.

### Summary
- `executive_summary` — 2-4 paragraphs tying it together.
- `one_line_pitch` — single sentence, e.g. "{company_name} can unlock ~$X annual revenue by replacing <vendor> with Algolia NeuralSearch."

Set `domain` to "{domain}".
