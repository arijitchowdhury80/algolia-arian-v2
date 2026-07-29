---
name: synth-sales-plays
version: 2.0.0
description: AE/BDR sales playbook synthesis — MEDDPICC, SPIN, objections, talk tracks, power map
cost_tier: pro-search
execution_strategy: prospect-only
composes: [intel-company, intel-hiring, intel-investor, intel-competitors, intel-techstack, intel-financial-public, intel-financial-private, intel-social, synth-business-case]
---

## Mission

Produce an AE/BDR **sales playbook** for **{company_name}** ({domain}).

**Pure synthesis** — do NOT research the web. Ground every element in the upstream intelligence
below. Talk tracks must mirror the prospect's OWN executive language (quote it). Never fabricate
a person, quote, or metric. Output must validate against the required schema.

---

## Upstream intelligence (your only source material)

### Company context
{upstream_intel_company}

### Hiring signals (buying-committee + tech roles)
{upstream_intel_hiring}

### Executive / investor signals (verbatim quotes)
{upstream_intel_investor}

### Competitors & their search vendors
{upstream_intel_competitors}

### Current tech / search stack
{upstream_intel_techstack}

### Financials (public)
{upstream_intel_financial_public}

### Financials (private estimate)
{upstream_intel_financial_private}

### Social signals
{upstream_intel_social}

### Business case (ROI, value levers, displacement, timing) — anchor your selling here
{upstream_synth_business_case}

If a section is empty, omit elements depending on it. If the business case is empty, still produce
the playbook from the intel modules but note the ROI is not yet available.

---

## What to produce

### Part 1 — MEDDPICC (`meddpicc`)
One row per field (metrics, economic_buyer, decision_criteria, decision_process, paper_process,
identified_pain, champion, competition). Name the `person` where known (from hiring/investor).
`evidence` cites the source module. `recommended_approach` is the AE's next move. Set `confidence`.

### Part 2 — SPIN questions (`spin_questions`)
2-3 each of situation / problem / implication / need_payoff. `context` ties each to a specific
upstream fact (e.g. a zero-result rate, an exec priority). `expected_response` is your best guess.

### Part 3 — Objection handlers (`objection_handlers`)
Anticipate the likely objections ("we're building in-house", "incumbent is fine", "no budget").
Each: `likelihood`, a data-backed `counter`, and `evidence_to_cite` (specific upstream facts).

### Part 4 — Talk tracks (`talk_tracks`)
Openers / bridges / closes. Set `mirrors_exec_language=true` and fill `source_quote` when the line
reuses the prospect's own words from intel-investor.

### Part 5 — Power map (`power_map`)
The buying committee from intel-hiring / intel-company / intel-investor. Each member: `title`,
`meddpicc_role`, predicted `attitude`, `recommended_approach`, `linkedin_url` if known. Never invent names.

### Summary
- `playbook_summary` — short paragraph.
- `top_3_actions` — the 3 highest-leverage next moves for the rep.

Set `domain` to "{domain}".
