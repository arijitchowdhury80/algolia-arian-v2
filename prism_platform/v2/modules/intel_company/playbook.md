---
name: intel-company
version: 2.2.0
description: Company seed intelligence — the identity card (Track 2 Perplexity)
cost_tier: pro-search
execution_strategy: per-company
composes: []
---

## Objective

Research the company that owns the website **{domain}** and produce a comprehensive company identity card. This is the SEED module — every other module in the audit pipeline depends on your output being accurate and complete.

You are Track 2 in a 3-track pipeline. Track 1 (WebFetch) already fetched live pages from the company's website. Track 3 (Synthesis) will reconcile your output with Track 1's data. **Your job is to be as thorough and accurate as possible — especially on fields that Track 1 cannot get from the company's website (competitors, industry, revenue for private companies, executive LinkedIn URLs).**

---

## Primary Source: Live Page Content

The following content was fetched directly from the company's website immediately before this prompt was generated. **Treat it as authoritative ground truth** for executive names, titles, and org structure. It reflects today's reality, not cached data.

### Leadership / About Page
```
{upstream_leadership_page}
```

### Investor Relations Page
```
{upstream_ir_page}
```

### Newsroom / Press Page
```
{upstream_newsroom_page}
```

If the above content is empty or minimal, fall back to your own knowledge and search capabilities. Note this clearly.

---

## PRIORITY #1 — Leadership Team

Find **8-12 CURRENT, ACTIVE executives**. This is the most critical section.

**Search strategy for each executive:**
1. Start with names from the live page content above (if available) — these are current
2. Search the web for additional executives not on the page
3. **For EVERY executive, search specifically for their personal LinkedIn profile:**
   - Search: `"{full_name}" "{company_name}" site:linkedin.com/in`
   - The URL format MUST be: `https://www.linkedin.com/in/[slug]/`
   - Only include if you actually found a real profile — do NOT fabricate
   - This is a HARD REQUIREMENT — spend the effort to find these

**Do NOT include anyone with "Former" or "Ex-" in their title.**

**Required roles — find all that exist at the company:**
- CEO / President → economic_buyer
- CFO / Chief Financial Officer → economic_buyer
- COO / Chief Operating Officer → economic_buyer
- CTO / Chief Technology Officer → technical_buyer
- CIO / Chief Information Officer → technical_buyer
- CMO / Chief Marketing Officer → influencer
- VP/SVP/EVP of Engineering or Technology → technical_buyer
- VP/SVP/EVP of Digital, E-commerce, or Customer Experience → champion
- VP/SVP/EVP of Product → champion
- Chief Digital Officer (CDO) → champion
- Head of Search, Discovery, or Personalization → champion

**MINIMUM: 5 executives. TARGET: 8-12.**

For each executive set role_classification:
- CEO, CFO, CRO, COO, President → economic_buyer
- CTO, VP Engineering, Chief Architect, CIO → technical_buyer
- VP Digital, VP E-commerce, CDO, Head of Search, VP Customer Experience → champion
- Director-level, CMO, VP Marketing → influencer
- Unclear from title → null

**For subsidiaries (e.g., {domain} owned by a parent company):** Return the SUBSIDIARY's leadership team, not the parent company's. If the subsidiary has limited public leadership, include the subsidiary CEO + any known subsidiary executives, then supplement with parent company executives who directly oversee this subsidiary.

---

## PRIORITY #2 — Competitors (Track 2 exclusive)

This data CANNOT come from the company's own website. You are the sole source.

Find **5-7 direct competitors** selling similar products to similar customers. For each include:
- Company name and primary domain
- One sentence: why they compete with {domain}
- Stock ticker if publicly traded
- **Company LinkedIn page URL** (format: `https://www.linkedin.com/company/[slug]/`) — search for it
- **Twitter/X handle** (without @ symbol) — search for it
- **YouTube channel URL** — search for it
Only include social fields if actually found — do NOT fabricate.

---

## PRIORITY #3 — Identity & Classification (Track 2 exclusive for some fields)

### Identity
- Official registered legal name and common marketing name
- Headquarters location (city, state/region, country)
- Year founded
- Employee count as integer (cite source: LinkedIn, 10-K filing, company website)
- Business model: how they make money, revenue streams, target customers — minimum 3 sentences

### Company Social Presence
Find these for the company (only include if actually found):
- LinkedIn company page URL (format: https://www.linkedin.com/company/[slug]/)
- Twitter/X handle (without @ symbol)
- YouTube channel URL

### Financial Snapshot
- Whether publicly traded or private
- Stock ticker symbol (if public)
- Parent company (if subsidiary)
- Annual revenue in USD — **use the most authoritative source available:**
  - Public companies: 10-K filing preferred, then analyst reports
  - Private companies: analyst estimates, industry reports, third-party databases
  - Always cite the specific source

### Classification (Track 2 exclusive)
- Primary industry (e.g. "Enterprise Technology", "E-commerce Retail")
- Sub-vertical (e.g. "Consumer Electronics", "Fashion Retail")
- Top-level product/service categories visible on the website

### Recent Activity
One recent headline about the company from the last 90 days.

---

## PRIORITY #4 — Company Hierarchy

### Parent Company
- If {domain} is a subsidiary or owned by a holding company, identify the parent:
  - Parent company name (e.g. "Berkshire Hathaway Inc.")
  - Parent company's primary domain (e.g. "berkshirehathaway.com")
- If the company is independent with no parent, set both to null.

### Brand Portfolio / Subsidiaries
Research what brands and subsidiaries THIS company owns. These are brands BELOW {domain} in the hierarchy — companies or brands that {domain} has acquired or operates.

Examples of what to find:
- Nike (nike.com) owns: Jordan (jordan.com), Converse (converse.com), Hurley (hurley.com)
- Oriental Trading (orientaltrading.com) owns: MindWare (mindware.com), Fun Express (funexpress.com), Smile Makers (smilemakers.com), Morris Costumes (morriscostumes.com)

For each subsidiary/brand include:
- Name of the brand or subsidiary
- Their domain if they have a separate one (None if they operate under the parent domain)
- One sentence describing what they do and their relationship to {domain}

**Return an empty list if the company owns no distinct sub-brands.**

---

## Output Format
Return a single valid JSON object. No markdown, no commentary before or after.

## Quality Rules
- **LinkedIn personal profile URLs: SEARCH SPECIFICALLY for each executive. This is critical.**
- Company social URLs: only include if verified found
- Revenue: raw float in USD (88400000000.0 not "$88.4B")
- Employee count: integer (133000 not "~133K")
- business_model: minimum 50 characters, substantive
- Executives: minimum 5 current active entries — hard requirement
- Competitors: minimum 5 entries with domains
- Prioritise the live page content above over your own knowledge for executive names/titles
- For private companies with limited public exec data: search LinkedIn, RocketReach, ZoomInfo for executives
