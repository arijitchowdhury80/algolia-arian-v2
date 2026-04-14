---
name: intel-company
version: 2.0.0
description: Company seed intelligence — the identity card
cost_tier: pro-search
execution_strategy: per-company
composes: []
---

## Objective

Research the company that owns the website **{domain}** and produce a comprehensive company identity card. This is the SEED module — every other module in the audit pipeline depends on your output being accurate and complete.

## What to Discover

### Identity
- Official registered company name (legal name) and common marketing name
- Headquarters location (city, state/region, country)
- Year founded
- Approximate employee count (cite source: LinkedIn, company website, etc.)
- Business model: how they make money, who their customers are, key product/service categories (minimum 3 sentences)
- Company LinkedIn page URL

### Financial Snapshot
- Whether the company is publicly traded or private
- Stock ticker symbol (if public)
- Parent company (if subsidiary)
- Annual revenue estimate in USD (cite source: SEC filing, Forbes, etc.)

### Classification
- Primary industry (e.g. "Enterprise Technology", "E-commerce Retail")
- Sub-vertical (e.g. "Consumer Electronics", "Fashion Retail")
- Top-level product/service categories visible on the website

### Leadership Team
Find **8-12 named executives**. This section is critical — downstream modules depend on it.

Search these sources:
- The company website "About Us", "Leadership", or "Team" page
- LinkedIn profiles
- Companies House director filings (for UK companies)
- Press releases and recent news

Must include at minimum: CEO, CFO, CTO/VP Engineering, CMO/VP Marketing.
Also look for: VP/Director of Product, E-commerce, Digital, Search, Data/AI.
For subsidiaries: include BOTH subsidiary leaders AND parent company executives who oversee it.

For each executive, classify their MEDDPICC buyer role based on title:
- CEO, CFO, CRO, COO, President → economic_buyer
- CTO, VP Engineering, Chief Architect → technical_buyer
- VP Digital, VP E-commerce, Head of Search, VP Customer Experience → champion
- Director-level roles → influencer
- If unclear from title alone → null

### Competitors
Find **5-7 direct competitors** that sell similar products/services to similar customers in the same market. For each competitor, include their website domain and one sentence explaining why they compete with {domain}.

### Recent Activity
Find one recent headline about the company from the last 90 days.

## Output Format
Return a single valid JSON object. No markdown, no commentary before or after.

## Quality Rules
- LinkedIn URLs must be real — do NOT fabricate. Only include if you actually found them.
- Revenue must be a raw number in USD (e.g. 88400000000.0, not "$88.4B")
- Dates in YYYY-MM-DD format
- Employee count as integer (e.g. 133000, not "~133K")
- business_model must be at least 50 characters with real substance
- Executives must have at least 5 entries
- Competitors must have at least 5 entries
