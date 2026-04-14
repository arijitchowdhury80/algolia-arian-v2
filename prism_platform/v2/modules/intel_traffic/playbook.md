---
name: intel-traffic
version: 2.0.0
description: Traffic intelligence — comparative analysis of prospect and competitor traffic patterns
cost_tier: pro-search
execution_strategy: comparative
composes: []
---

## Research Mission

Conduct comparative traffic intelligence for **{company_name}** ({domain}) and its competitors. You are producing a single report covering the prospect and all competitors in one research pass.

## Company Context
- Prospect: {company_name} ({domain})
- Industry: {industry}
- Competitors:
{competitors}

## What to Research

### 1. Prospect Traffic Profile

For **{domain}**:

1. **Monthly visits:** Use SimilarWeb, Semrush, or similar tools. Report as a range: "5M-10M visits/month". Cite source.
2. **Traffic trend:** Is traffic growing, stable, or declining? Look for YoY or QoQ data.
3. **Traffic sources:** Breakdown by channel (direct, organic search, paid search, social, referral). Which channel dominates?
4. **Top organic keywords:** What are the top 5 organic keywords driving traffic? Are they branded (company name) or product/category terms?
5. **Bounce rate:** If available. Compare to industry average.
6. **Google Trends:** Search for "{company_name}" trends over the last 12 months. Rising, stable, or declining?
7. **Seasonal pattern:** Any clear seasonal peaks or troughs? Relevant for retail, travel, etc.

### 2. Competitor Traffic Comparison

For each competitor listed above, provide:
1. Estimated monthly visits (range)
2. Traffic trend (growing/stable/declining)
3. Primary traffic source
4. Any notable traffic data points

### 3. Comparative Analysis

After gathering data for all companies:
1. **Who has the most traffic?** Rank the companies.
2. **Who is growing fastest?** Any outliers?
3. **Search traffic dependency:** Which companies are most dependent on organic search? High organic dependency = SEO-driven growth model, often correlates with search quality investment.
4. **Paid search spend signals:** Heavy paid search = budget-conscious about digital acquisition.

## Source Priority
1. SimilarWeb (most reliable for traffic estimates)
2. Semrush traffic analytics
3. Ahrefs site traffic reports
4. SimilarWeb public data (when API not available, use public pages)
5. Alexa Archive / other traffic estimators

## Output Instructions

Return a single JSON object matching the TrafficV2Output schema.

**Critical rules:**
1. Report monthly_visits_estimate as a STRING range: "5M-10M", "50M+", "< 1M", "data_unavailable"
2. Do NOT invent traffic numbers — if data is unavailable, say so
3. competitor_summaries must cover ALL competitors listed in the context
4. comparative_narrative is written for a sales rep — make it actionable
5. Cite all data sources in data_freshness field
