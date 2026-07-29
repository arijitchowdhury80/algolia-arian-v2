---
name: intel-financial-private
version: 2.0.0
description: Revenue estimation for private companies — multi-source waterfall approach
cost_tier: pro-search
execution_strategy: prospect-only
composes: []
---

## Research Mission

Estimate the annual revenue of **{company_name}** ({domain}), a **private company**.

**SKIP IMMEDIATELY** if {is_public} is "True" — return skipped=True.

This is a private company. There is no 10-K. You must triangulate revenue from indirect evidence. Use the waterfall approach below: try each source in order, record what you find (or don't find), and produce a best estimate with confidence.

## Company Context
- Domain: {domain}
- Company: {company_name}
- Industry: {industry}

## Revenue Estimation Waterfall

Work through these sources in order. Record each source even if it yields no data.

### Source 1: Press Releases and Company Announcements
Search "{company_name} revenue" and "{company_name} annual revenue":
- Has the company ever disclosed revenue publicly?
- Any press releases, CEO interviews, or official announcements with revenue figures?
- Company website "About Us" or "Investor" page?
- Highest confidence if found.

### Source 2: Industry Reports and Rankings
- Is {company_name} mentioned in any industry revenue rankings?
- Inc 5000 list? Deloitte Technology Fast 500? Fortune rankings?
- Any analyst reports (Forrester, Gartner, IDC) mentioning this company's revenue?
- Search: "{company_name} revenue estimate analyst" or "{domain} annual revenue"

### Source 3: Crunchbase / PitchBook Funding Data
Search Crunchbase or PitchBook for {company_name}:
- Total funding raised (as a revenue proxy)
- Last funding round: name, amount, date, lead investor
- Valuation if disclosed
- Note: funding amount ≠ revenue, but last round size and valuation are useful context

### Source 4: Employee Count × Revenue-per-Employee Model
1. Find employee count from LinkedIn company page (search "{company_name} LinkedIn employees")
2. Apply industry benchmark revenue per employee:
   - SaaS / Software: $200K-$300K per employee
   - Ecommerce: $800K-$2M per employee
   - Professional Services: $150K-$250K per employee
   - Retail: $300K-$600K per employee
3. Calculate range: employee_count × low_benchmark to employee_count × high_benchmark

### Source 5: Competitor Comparison
- Find a similar-sized competitor with known revenue
- Use their revenue-per-employee ratio as a benchmark for {company_name}
- Note: this is lowest-confidence, report clearly as estimate

## Funding Intelligence
While researching, capture funding history if available (see FundingDataV2 schema).

## Output Instructions

Return a single JSON object matching the FinancialPrivateV2Output schema.

**Critical rules:**
1. If {is_public} is "True": set skipped=true, skip_reason, stop
2. Revenue figures must be raw floats: 50000000.0 NOT "$50M"
3. Record EVERY source tried in revenue_estimates, even those with no result
4. estimate_range must be a human-readable string: "$50M-$100M", "Under $10M", "Insufficient data"
5. confidence = "insufficient_data" if fewer than 2 corroborating sources
6. financial_narrative written for a sales rep
