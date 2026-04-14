---
name: intel-techstack
version: 2.0.0
description: Technology stack detection for a single domain — search vendor, ecommerce platform, and golden angle detection
cost_tier: pro-search
execution_strategy: per-company
composes: []
---

## Research Mission

Identify the **complete technology stack** for **{domain}** ({company_name}). Your primary goal is to detect the **search vendor** — the technology powering site search and product discovery on this domain.

This playbook runs once per company (prospect + each competitor). The results for all companies are aggregated by the orchestrator.

## Company Context
- Domain: {domain}
- Company: {company_name}
- Industry: {industry}

## What to Research

### 1. Search Vendor Detection (Primary Target)

Search for evidence of which technology powers search on {domain}:

**Detection signals in priority order:**
1. **BuiltWith data** — search for "{domain} BuiltWith" or check builtwith.com/{domain}
   - Look for: Algolia, Elasticsearch, OpenSearch, Solr, Coveo, Bloomreach, Searchspring, Constructor.io, Typesense
2. **Network analysis hints** — any public references to XHR calls, API endpoints visible in dev tools screenshots, or network traces
   - Algolia: requests to `*.algolia.net`, `*.algolianet.com`, or `algolia.io`
   - Elasticsearch: requests to `/_search`, `/search.json`, internal search endpoints
3. **Engineering blog** — search for "{company_name} engineering search" or "engineering.{domain}"
4. **Job postings** — search for "{company_name} search engineer elasticsearch algolia" on LinkedIn
5. **GitHub** — public repos mentioning the domain's search implementation
6. **G2/Capterra reviews** — any customer reviews mentioning site search quality

**Evidence quality standard:** "They use Elasticsearch" is weak. "BuiltWith reports Elasticsearch 8.x for {domain}; confirmed by a Senior Elasticsearch Engineer job posting (Oct 2025, LinkedIn)" is strong. Always cite the source URL.

### 2. Ecommerce Platform (if applicable)

For retail and commerce domains, detect the ecommerce platform:
- Salesforce Commerce Cloud (SFCC): look for `demandware.net` references, SFCC-specific URLs
- Shopify Plus: `myshopify.com` in source, Shopify CDN
- Magento/Adobe Commerce: `/catalog/product/`, Adobe Commerce job postings
- commercetools: `api.commercetools.co` references, CT-specific docs
- Custom: large enterprises often build in-house

### 3. Analytics Stack

Detect analytics/tracking tools. Look for:
- Google Analytics 4 (GA4), Adobe Analytics, Mixpanel, Amplitude
- These are less critical but complete the tech profile

### 4. All Detected Technologies

List all major technologies detected for {domain}:
- CDN/WAF: Cloudflare, Akamai, Fastly
- Frontend: React, Vue, Next.js, Angular
- Ecommerce platform (see above)
- Search (see above)
- Analytics (see above)

## Output Instructions

Return a single JSON object matching the TechStackV2Output schema.

**Critical rules:**
1. `search_vendor` must be null if you cannot find evidence — do not guess
2. `is_algolia_customer` must be false unless you have direct evidence (BuiltWith Algolia detection, confirmed `*.algolia.net` calls, or official Algolia case study)
3. `evidence_url` in SearchVendorV2 must be a real URL you found — not a made-up URL
4. `tech_stack_narrative` should lead with the search vendor finding and be written for a sales rep to read

**For `golden_angle_competitors`:** This field is ONLY relevant when this playbook runs for a competitor domain. If {domain} is a competitor using Algolia, the orchestrator will populate the prospect's golden_angle_competitors. For now, set golden_angle_competitors to an empty list unless you have specific evidence that a different competitor uses Algolia.

**Minimum acceptable research:** At least check BuiltWith, one job posting source, and one engineering blog search. A response with search_vendor null is acceptable if no evidence found — an invented vendor is not.
