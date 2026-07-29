---
name: intel-hiring
version: 2.0.0
description: Hiring intelligence — open roles, ICP tier mapping, build-vs-buy signal, hiring velocity
cost_tier: pro-search
execution_strategy: prospect-only
composes: []
---

## Live Career Page Content

The following content was fetched directly from **{company_name}**'s career page immediately before this prompt. **Treat job titles and descriptions as authoritative** — they reflect currently open positions.

```
{upstream_careers_page}
```

If the above is empty, a LinkedIn redirect was detected, or content is minimal, fall back to web search on LinkedIn Jobs, Indeed, and Glassdoor.

---

## Research Mission

Analyse the current hiring activity of **{company_name}** ({domain}) to detect buying signals. You are looking for: open roles that suggest search investment, leadership hires that trigger tech evaluation, and build-vs-buy signals from job posting language.

## Company Context
- Domain: {domain}
- Company: {company_name}
- Industry: {industry}
- Key executives: {executives}
- Competitors:
{competitors}

## What to Research

### 1. Search and Discovery Roles (Primary Target)

Search LinkedIn Jobs, Indeed, and Glassdoor for {company_name} open roles. Focus on:
- "Search Engineer" / "Search Platform Engineer" / "Search Relevance Engineer"
- "Site Search" / "Product Discovery" / "Discovery Platform"
- "Elasticsearch Developer" / "Solr Engineer" / "OpenSearch"
- "Search Architect" / "Search Lead" / "Head of Search"
- "Merchandising Manager" / "Digital Merchandiser" (often controls search configuration)
- "Senior Software Engineer" with description mentioning search

**Why this matters:** Companies hiring for search roles are either building in-house or implementing a vendor solution. The job description language tells you which.

**Build signal:** "Design and build our search infrastructure from scratch", "Lucene expertise required", "Build search relevance models"
**Buy signal:** "Implement Algolia/Elastic/Coveo", "Evaluate search vendor solutions", "Own vendor relationship"

### 2. Digital Leadership Hires (Buying Committee)

Search for new hires in the last 12 months:
- VP / Director of Digital Commerce / Digital Experience
- CTO / VP Engineering
- Chief Digital Officer (CDO)
- VP / Director of Product (for digital products)
- VP / Director of Customer Experience

These are economic buyers and champions for Algolia. New leaders re-evaluate tech stack within 6 months.

### 3. ICP Tier Mapping

For each relevant role, classify by MEDDPICC tier:
- **Tier 1 (Economic buyer):** VP/Director with budget (VP Digital Commerce, VP Engineering, CTO)
- **Tier 2 (Technical evaluator):** Architect, Tech Lead, Platform Lead who will evaluate solutions
- **Tier 3 (Champion):** Search Engineer, Relevance Engineer who will advocate internally
- **Tier 4 (User):** Individual contributors who use the search platform

### 4. Hiring Velocity Signal

Are they hiring aggressively in search/digital? Count of search-related roles in the last 30 days.
- 3+ search roles = high investment signal
- 1-2 search roles = moderate investment
- 0 search roles = no current signal

### 5. Competitor Hiring Context

For the top 2 competitors, are they also hiring for search?
This validates that search investment is a market-wide trend.

## Output Instructions

Return a single JSON object matching the HiringV2Output schema.

**Critical rules:**
1. Limit open_roles to top 10 most relevant roles
2. Set search_related=True only for roles directly related to search/discovery/relevance
3. hiring_signal_score: 0.8-1.0 for strong buy signal (evaluation roles + executive hires), 0.4-0.7 for moderate, 0.0-0.3 for weak
4. build_vs_buy: base this on language in actual job descriptions, not inference
5. hiring_narrative written for a sales rep — lead with the strongest signal
