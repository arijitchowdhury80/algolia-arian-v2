---
name: audit-report
version: 2.0.0
description: Final audit deliverable — 10-dimension scoring, competitor benchmark, pre-call brief, leave-behind
cost_tier: pro-search
execution_strategy: prospect-only
composes: [synth-business-case, synth-sales-plays, intel-competitors, intel-company, intel-techstack, intel-traffic, intel-industry]
---

## Mission

Assemble the final **audit deliverable** for **{company_name}** ({domain}).

**Pure synthesis** — do NOT research the web. Score and summarize ONLY from the upstream data
below. Until a live browser audit exists, every dimension score is an estimate: set
`is_estimated=true` and base it on techstack + traffic signals. Never fabricate a number or quote.
Output must validate against the required schema.

---

## Upstream intelligence (your only source material)

### Business case (ROI)
{upstream_synth_business_case}

### Sales plays (angles, power map)
{upstream_synth_sales_plays}

### Competitors & their search vendors
{upstream_intel_competitors}

### Company context
{upstream_intel_company}

### Current tech / search stack
{upstream_intel_techstack}

### Traffic & engagement
{upstream_intel_traffic}

### Industry benchmarks
{upstream_intel_industry}

---

## What to produce

### Part 1 — 10-dimension scoring (`dimension_scores`)
Score all 10 dimensions (relevance, speed, typo_tolerance, nlp, autocomplete, faceting,
zero_result_handling, personalization, merchandising, analytics) 0-10. Each: `evidence` citing the
source signal, `severity` (critical/major/minor/ok by score), `is_estimated=true`. Set
`overall_score` (mean) and a short `score_methodology`.

### Part 2 — Competitor benchmark (`competitor_scores`)
For each competitor in intel-competitors, an estimated `overall_score` (and per-dimension if
inferable). Set `industry_average_score` from intel-industry benchmarks if available.

### Part 3 — Full audit data (`full_audit_data`)
A compact dict assembling the key facts pulled from each upstream module (company, vendor, ROI
headline, top signals) — the machine-readable record behind the report.

### Part 4 — Pre-call brief (`pre_call_brief`)
The AE's 60-second read: `search_score`, `top_angle`, `key_exec_to_reference` (real quote),
`most_urgent_signal`, `recommended_first_play`, optional `partner_play`.

### Part 5 — Leave-behind (`leave_behind`)
Prospect-SAFE only — NO hiring/buying-committee/internal-strategy data. `search_quality_summary`,
`competitive_benchmark` (anonymized, no competitor names), `top_3_recommendations`, `roi_summary`
(from the business case), `next_steps`.

### Summary
`audit_summary` — a short executive summary of the whole audit.

Set `domain` to "{domain}" and `company_name` to "{company_name}".
