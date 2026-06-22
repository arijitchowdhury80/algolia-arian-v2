---
name: intel-competitors
version: 2.0.0
description: Competitive search-landscape — vendor detection (deterministic) + golden angle + Algolia case-study matching
cost_tier: pro-search
execution_strategy: comparative
composes: [intel-company, intel-techstack]
---

## Research Mission

Build the competitive search-landscape for **{company_name}** ({domain}) in the **{industry}** vertical. The hard part — *which search vendor each competitor runs* — has ALREADY been determined deterministically by PRISM's in-app detector. Your job is to (1) pass those facts through faithfully, and (2) add the parts that need reasoning: Algolia case-study matching and the sales narrative.

## Deterministic detection (authoritative — DO NOT re-research)

The Track-1 Scout source-scan already detected each company's search vendor:

{upstream_competitor_search_detection}

**Rules for using this data:**
1. Copy `search_vendor`, `search_vendor_status`, `is_algolia_customer`, and `evidence` into each `competitor_profiles` entry **verbatim**. Do not change them, do not "verify" them with your own web search, do not invent vendors not listed.
2. `detection_source` is always `"scout_source_scan"` for these.
3. `golden_angle_competitors` = the `golden_angle_domains` list from the detection above.
4. If a competitor's status is `UNCONFIRMED_WAF_BLOCK` or `FETCH_FAILED`, keep it as-is — a block is itself a finding, not a reason to guess.

## Competitor set (from intel-company)

{competitors}

## What you DO research

### 1. Algolia case studies (2-4)
Search `algolia.com/customers` and Algolia's blog for customer stories in or adjacent to the **{industry}** vertical. For each, capture the title, real URL (no fabrication), the vertical, and one sentence on why it's relevant to {company_name}.

### 2. Competitive scenario
Classify the overall picture from the deterministic detection:
- `golden` — at least one competitor runs Algolia (lead with "your competitor already switched")
- `defensive` — the prospect ({domain}) itself runs Algolia (retention / expansion play)
- `offensive` — neither prospect nor competitors run Algolia (greenfield displacement)
- `mixed` — varies across the set

### 3. Narrative
Write `competitive_landscape_narrative` (3-5 sentences) for a sales rep: who competes, how they compare on search technology, and the single sharpest angle. **Lead with any golden-angle finding** (a competitor on Algolia is the strongest opener).

## Output Instructions

Return a single JSON object matching the `CompetitorsV2Output` schema.

**Critical rules:**
1. Search-vendor fields come from the deterministic detection above — verbatim. Everything else (case studies, narrative) is yours.
2. Every case study URL must be one you actually found on algolia.com — never fabricate URLs.
3. `competitive_scenario` must be consistent with the detection (e.g. don't say `offensive` if a competitor `is_algolia_customer` is true).
4. The narrative is written for a sales rep about to make a call — make it specific and actionable.
