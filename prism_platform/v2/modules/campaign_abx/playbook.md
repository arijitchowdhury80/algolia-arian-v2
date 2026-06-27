---
name: campaign-abx
version: 2.0.0
description: Multi-touch ABX campaign — 5 emails, LinkedIn messages, Loom script, schedule, competitor messaging
cost_tier: pro-search
execution_strategy: prospect-only
composes: [synth-business-case, synth-sales-plays, intel-hiring, intel-company, intel-investor, intel-competitors, intel-techstack, intel-social]
---

## Mission

Produce a personalized multi-touch **ABX outreach campaign** for **{company_name}** ({domain}).

**Pure synthesis** — do NOT research the web. Every email, message, and script line must reference
real audit data (exec quotes, competitive intel, ROI, case studies). No generic templates. Never
invent a person, quote, or metric. Output must validate against the required schema.

---

## Upstream intelligence (your only source material)

### Business case (ROI, value levers, displacement, timing)
{upstream_synth_business_case}

### Sales plays (MEDDPICC, power map, objections, talk tracks)
{upstream_synth_sales_plays}

### Hiring signals (buying committee)
{upstream_intel_hiring}

### Company context
{upstream_intel_company}

### Executive / investor signals (verbatim quotes)
{upstream_intel_investor}

### Competitors & their search vendors
{upstream_intel_competitors}

### Current tech / search stack
{upstream_intel_techstack}

### Social signals
{upstream_intel_social}

If the synth modules are empty, build a lighter campaign from the intel modules and note ROI is pending.

---

## What to produce

### Part 1 — Email sequence (`emails`)
Exactly 5 emails, one per `purpose` in order: hook → insight → proof → roi → ask. Each `body`
references specific audit data; list the `personalization_tokens` used; set `target_role` and
`recommended_send_day`. Subject lines < 80 chars.

### Part 2 — LinkedIn messages (`linkedin_messages`)
For the top buying-committee members (from sales-plays power map / intel-hiring): a
connection_request + follow_up. Use real `target_name`/`target_title`; never invent names. Note the
`personalization_context`.

### Part 3 — Loom script (`loom_script`)
A 2-minute script: `opening` (name the prospect), `screen_1/2/3` (the 3 most compelling findings,
each "show X / say Y"), `closing`, `call_to_action`.

### Part 4 — Collateral schedule (`schedule`)
Week-by-week (1-5): `actions`, `target_contacts`, `notes`.

### Part 5 — Competitor messaging (`competitor_messaging`)
Set `current_vendor` from intel-techstack/intel-competitors; pick `messaging_angle`
(displacement / performance / greenfield); list `key_points` + `differentiators`.

### Summary
- `campaign_summary` — short paragraph on the strategy.
- `target_contacts` — names from the buying committee to target.

Set `domain` to "{domain}".
