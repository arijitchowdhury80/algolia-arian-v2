---
name: intel-queries
version: 2.0.0
description: Browser-audit test-query set — generated deterministically by Track-1 Python collector
cost_tier: pro-search
execution_strategy: prospect-only
composes: [intel-company, intel-traffic]
---

## Note: Track-1 is the full output

intel-queries is a **near-zero-LLM** module. The Track-1 pure-Python collector
generates the complete query set from structured upstream data. The LLM (Track-2)
is intentionally minimal — invoked only to polish query naturalness if needed.

In most runs, this playbook body is never reached.

## Query set (from Track-1 collector)

The deterministic collector has already produced the full query set for **{company_name}** ({domain}):

{upstream_query_set}

## Track-2 task (optional polish only)

If the query set above was produced, your ONLY job is:

1. Review the `nlp_conversational` queries for naturalness. If any sound robotic, rewrite the `text` field to sound like a real shopper.
2. Review the `synonym_colloquial` queries. If a synonym sounds forced or regional (British vs American), adjust to the prospect's primary market.
3. Do **not** add new queries, remove queries, or change query types.
4. Return the same JSON structure with any polished `text` fields updated in-place.

## Output instructions

Return a single JSON object matching the `QueryIntelOutput` schema. All fields must be present. Do not invent query types not in the schema.

**Critical rules:**
1. If the Track-1 query set is already provided above, copy it through and only polish `nlp_conversational` and `synonym_colloquial` text where genuinely needed.
2. `query_coverage` must be consistent with the `queries` list (count each type).
3. `total_queries` = sum of all `query_coverage` values.
4. Never fabricate `source` values — use only: `product_categories`, `top_organic_keywords`, `static`, `brand`.
