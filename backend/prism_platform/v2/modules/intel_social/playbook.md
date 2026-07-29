---
name: intel-social
version: 2.0.0
description: Social intelligence — LinkedIn + Twitter/X post relevance scoring and Algolia signal extraction
cost_tier: pro-search
execution_strategy: prospect-only
composes: [intel-company]
---

## Research Mission

Score and synthesise the social media posts collected by the Track-1 Apify collector for **{company_name}** ({domain}). The raw posts are already in context — your job is to score each one for Algolia relevance, tag it, identify the high-signal posts, and write the signal summary for a sales rep.

## Posts collected by Track 1 (authoritative — DO NOT re-collect or fabricate)

**LinkedIn posts:**
{upstream_social_linkedin_posts}

**Twitter/X posts:**
{upstream_social_twitter_posts}

**Collection sources:**
{upstream_social_social_sources}

If all lists are empty (no Apify key configured, or no social URLs in intel-company), produce an output with all post lists empty and `signal_summary` as null. Do not invent posts.

## Company context (from intel-company)

- **Company:** {company_name}
- **Domain:** {domain}
- **Industry:** {industry}

## Your task — relevance scoring

For EVERY post in the lists above, set:

### `relevance_score` (0.0–1.0)

Use keyword rules as the primary filter:

| Score range | Signal type |
|---|---|
| 0.8–1.0 | Explicit search/discovery mention ("we improved search", "Algolia", "new search experience"), platform migration announcement, AI/ML-powered customer experience launch |
| 0.6–0.8 | Digital transformation, major ecommerce investment, "customer experience" as strategic priority, headcount growth in engineering/data/product, tech partnership announcement |
| 0.4–0.6 | Generic product launch, new market entry, executive hire in tech/digital roles |
| 0.1–0.4 | Brand/marketing posts, events, CSR, employee spotlights, no tech signal |
| 0.0–0.1 | Irrelevant (HR perks, charity, recycled PR) |

Use the LLM only for borderline cases (0.4–0.7 range where keyword rules are ambiguous).

### `relevance_tags`

Tag each scored post with applicable labels from:
- `search_mention` — explicitly mentions search, discovery, or findability
- `tech_investment` — platform, infrastructure, or tech investment signal
- `platform_migration` — switching or re-platforming
- `ai_ml` — artificial intelligence, machine learning, personalisation
- `cx_focus` — customer experience as a stated priority
- `scale_signal` — rapid growth, new markets, volume surge
- `exec_signal` — senior hire in digital/tech/ecommerce role
- `partnership` — tech vendor or SI partner announced

## Output fields

Produce a single JSON object matching `SocialIntelOutput`:

- `domain` — the prospect domain (from context)
- `linkedin_posts` — all LinkedIn posts with scores and tags filled in
- `twitter_posts` — all Twitter/X posts with scores and tags filled in
- `high_signal_posts` — posts where `relevance_score > 0.7` (from either platform, sorted descending by score)
- `signal_summary` — 2–4 sentence summary for a sales rep; lead with the highest-scoring post. null if no posts were collected.
- `sources` — copy from `{upstream_social_social_sources}`

## Critical rules

1. **Do not fabricate posts.** If the collector returned empty lists, produce empty lists and `signal_summary: null`.
2. **Copy post fields verbatim.** `text`, `platform`, `date`, `url` come from the Track-1 collector — do not alter them.
3. **Keyword rules first.** Run keyword matching before invoking LLM reasoning. Only use LLM judgment for scores in the 0.4–0.7 ambiguous zone.
4. **`high_signal_posts`** must be a strict subset of `linkedin_posts + twitter_posts` — same objects, not duplicated or summarised versions.
5. **Signal summary is for the sales rep.** Write it like a briefing note: specific, actionable, grounded in what the posts actually say. One sentence per key insight.
