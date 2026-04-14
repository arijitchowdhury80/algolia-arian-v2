---
name: cluster-c-technology
version: 1.0.0
description: Technology & Digital Experience deep research
cluster_id: C
cost_tier: deep-research
recency_bias_months: 18
feeds: [intel-techstack, intel-queries, audit-browser]
---

## Research Mission

Conduct deep technology and digital experience intelligence on **{company_name}** ({domain}). You are researching for an Algolia sales team — your primary goal is to understand their current search technology, assess search quality, and find evidence that their current solution is underperforming.

## Company Context
- Domain: {domain}
- Industry: {industry}

## What to Discover

### Search Technology Stack
1. **Current search vendor:** What search technology powers {domain}? Look for: Algolia, Elasticsearch/OpenSearch, Solr, Coveo, Bloomreach, Searchspring, Constructor.io, Typesense, in-house/custom, basic SQL LIKE queries
2. **Detection signals:** BuiltWith data, network request analysis (XHR to api.algolia.com, etc.), job postings mentioning specific tech, engineering blog posts, GitHub repos
3. **How long they've had it:** Any evidence of when they implemented current search?
4. **Search UX assessment:** Based on any available reviews (G2, Capterra, Trustpilot) — do customers complain about search quality?

### Broader Technology Stack
1. **Ecommerce platform:** Salesforce Commerce Cloud, Shopify Plus, Magento/Adobe Commerce, commercetools, SAP, custom
2. **CMS/DXP:** Contentful, Sitecore, Adobe Experience Manager, custom
3. **Analytics:** GA4, Adobe Analytics, Mixpanel, Amplitude
4. **CDN/WAF:** Cloudflare, Akamai, Fastly — relevant for browser testing approach
5. **Recent tech migrations:** Any evidence of platform changes in last 18 months?

### Digital Experience Quality Signals
1. **Page speed/Core Web Vitals:** Any public data on their site performance?
2. **Mobile experience:** Any commentary on mobile app quality?
3. **AI/personalization investments:** Are they investing in recommendation engines, personalization, AI chatbots?
4. **Engineering blog/talks:** Any engineering content about their search/discovery investments?

### Competitor Technology Comparison
For each known competitor ({competitors}):
1. What search technology do they use?
2. Any public commentary comparing their search UX to {company_name}?
3. **Golden Angle detection:** Does any competitor use Algolia? That's a displacement opportunity signal.

### Search-Related Job Postings
1. Any open roles that mention: Elasticsearch, Solr, search relevance, search engineer, merchandising
2. What level of investment are they making in search talent?

## Source Priority
1. BuiltWith technology reports
2. Engineering blogs and tech talks (YouTube, SlideShare, engineering.{domain})
3. LinkedIn job postings with technology mentions
4. G2, Capterra, Trustpilot for user experience reviews
5. GitHub for any open-source repos
6. Network analysis / developer tools inspection hints from any available sources

## Output Instructions
Be specific and evidence-based. "They use Elasticsearch" is weak. "They use Elasticsearch based on XHR requests to search.{domain}/search visible in BuiltWith data, confirmed by job posting for 'Senior Elasticsearch Engineer' posted 3 months ago" is strong. Cite everything.
