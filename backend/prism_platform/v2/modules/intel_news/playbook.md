---
name: intel-news
version: 2.0.0
description: Recent news intelligence — company news, competitor news, urgency signals for sales outreach
cost_tier: pro-search
execution_strategy: prospect-only
composes: []
---

## Research Mission

Find recent news (last 90 days) about **{company_name}** ({domain}) and its competitors that is relevant to an Algolia sales pitch. Classify each article by urgency and sell signal status.

## Company Context
- Domain: {domain}
- Company: {company_name}
- Industry: {industry}
- Key executives: {executives}
- Competitors:
{competitors}

## What to Research

### 1. Company News (Last 90 Days)

Search Google News, Reuters, TechCrunch, and industry publications for:
1. **Leadership changes:** New CEO, CTO, VP Digital/Ecommerce, CDO hired in last 6 months
2. **Platform migration announcements:** Re-platforming to new ecommerce platform, cloud migration, tech stack overhaul
3. **Technology investments:** Press releases about AI investment, digital transformation, search improvement, customer experience
4. **Financial events:** Funding round, IPO filing, M&A activity, cost-cutting announcements
5. **Digital product launches:** New website, new app, new digital channel
6. **Customer experience commentary:** Any public discussion of site search quality, conversion issues

**Search queries to try:**
- "{company_name} digital transformation 2025"
- "{company_name} technology investment 2025"
- "{company_name} search platform"
- "{company_name} ecommerce replatform"
- "{company_name} new CTO" or "new VP Digital" or "new CDO"

### 2. Competitor News That Creates Urgency

For each competitor listed above, look for:
- Has any competitor recently launched improved search/discovery experience?
- Has any competitor announced Algolia or similar technology adoption?
- Has any competitor won an award for digital experience?

A competitor using Algolia or launching a notable search upgrade creates urgency for the prospect.

### 3. Executive-Specific News

For key executives (especially VP Digital, CTO, CEO):
- Any public statements about technology priorities?
- Conference keynote appearances?
- LinkedIn posts about digital investment?

## Urgency Classification

**High urgency (act within days):**
- New VP Digital/CTO/CDO hired in last 30 days (new leaders evaluate tech stack in first 6 months)
- Active platform migration announced
- Company just announced major digital transformation initiative with specific timeline
- Competitor just launched Algolia or new search experience

**Medium urgency (act within weeks):**
- New leader hired 30-90 days ago
- Digital investment announced without specific timeline
- M&A activity that typically triggers tech stack review

**Low urgency (background context):**
- General company news with no direct technology signal
- Older news (90+ days)

## Output Instructions

Return a single JSON object matching the NewsV2Output schema.

**Critical rules:**
1. Only include news from the last 90 days as "high" or "medium" urgency
2. Set is_sell_signal=True only for news directly relevant to search/discovery technology decisions
3. outreach_angle must be a single specific, actionable sentence for a sales rep
4. URL field: use the actual article URL — do not fabricate URLs
5. news_narrative written for a sales rep before an outreach call
