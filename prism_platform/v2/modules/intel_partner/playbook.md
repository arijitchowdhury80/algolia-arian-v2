---
name: intel-partner
version: 2.0.0
description: Partner ecosystem — tech partner detection (deterministic) + SI/agency relationships + actionable co-sell motions
cost_tier: pro-search
execution_strategy: prospect-only
composes: [intel-company, intel-techstack]
---

## Research Mission

Map the partner ecosystem for **{company_name}** ({domain}) in the **{industry}** vertical. The hard part — *which Algolia technology partners the prospect already uses* — has ALREADY been determined deterministically by PRISM's static partner table lookup. Your job is to (1) pass those partner facts through faithfully, and (2) add the parts that need open-web reasoning: SI/agency relationships and actionable sales motions.

## Deterministic partner detection (authoritative — DO NOT re-research)

The Track-1 static table lookup already matched the prospect's tech stack against Algolia's partner ecosystem:

{upstream_partner_tech_detection}

**Rules for using this data:**
1. Copy every entry in `tech_partners` verbatim into the output `tech_partners` list. Do NOT add, remove, or modify these entries.
2. Set `has_algolia_partner_overlap` exactly as provided above — do NOT recompute it.
3. If `tech_partners` is empty, the prospect uses no detected Algolia tech partner. Do not invent one.

## Company context (from intel-company)

{upstream_intel_company}

## Tech stack context (from intel-techstack)

{upstream_intel_techstack}

## What you DO research

### 1. SI / agency relationships (2-4)

Search for system integrators or digital agencies known to have built or maintained **{company_name}**'s commerce or digital experience platform. Examples: Accenture, EPAM, Deloitte Digital, Publicis Sapient, Razorfish, Slalom, Dept Agency, WPP agencies.

For each firm found:
- `firm_name`: the SI/agency name
- `relationship_type`: e.g. "implementation partner", "AOR", "managed services partner"
- `evidence`: one sentence citing the source (press release, case study, LinkedIn, job posting)
- `confidence`: confirmed / likely / possible
- `algolia_relevance`: one sentence — why this SI relationship matters for an Algolia sales motion (e.g. "Accenture has a dedicated SFCC/Algolia connector practice that could accelerate the deal")

Only include relationships you found evidence for. Do not fabricate SI relationships.

### 2. Partner narrative

Write `partner_narrative` (3-5 sentences) for a sales rep:
- Which Algolia tech partners the prospect already runs (from Track-1 detection)
- Key SI/agency leverage points found
- The single sharpest co-sell or partner-led angle

### 3. Actionable motions (2-4)

Write 2-4 specific, actionable sales motions that the partner landscape enables. Each motion should be one sentence starting with an action verb. Examples:
- "Engage [SI firm]'s [platform] practice to co-sell the Algolia connector and reduce prospect's implementation risk"
- "Leverage Shopify's Algolia app listing as a warm entry point — prospect is already in the Shopify ecosystem"
- "Contact Algolia's [partner] partner manager to request a co-sell introduction"

## Output Instructions

Return a single JSON object matching the `PartnerV2Output` schema.

**Critical rules:**
1. `tech_partners` and `has_algolia_partner_overlap` MUST be copied verbatim from the Track-1 detection above. Do NOT alter these.
2. `si_relationships` comes entirely from your research — do NOT invent relationships not evidenced.
3. Every `evidence` field in `si_relationships` must cite a real source you found. No fabrication.
4. `actionable_motions` should be specific to **{company_name}** — not generic Algolia sales copy.
5. `partner_narrative` is written for a sales rep about to make a call — make it specific and actionable.
