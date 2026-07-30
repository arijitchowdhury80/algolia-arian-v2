---
name: cluster-e-buying-signals
version: 1.0.0
description: Buying Signals & Intent Inference deep research
cluster_id: E
cost_tier: deep-research
recency_bias_months: 3
feeds: [intel-hiring, intel-news, intel-social, intel-industry]
---

## Research Mission

Identify **current buying signals** for **{company_name}** ({domain}). You are looking for evidence that this company is actively evaluating, replacing, or investing in search/discovery technology RIGHT NOW. Recency matters: signals from the last 90 days are gold; signals from 12+ months ago are background context.

## Company Context
- Domain: {domain}
- Industry: {industry}
- Current search vendor (if known): check cluster C findings

## Buying Signal Categories

### Tier 1: High-Intent Signals (Act Now)
These suggest active evaluation or imminent purchase decision:

1. **Active search/discovery job postings:** Roles like "Search Relevance Engineer", "Search Platform Engineer", "Senior Elasticsearch Developer", "Site Search Manager", "Merchandising Manager" → they're investing in or struggling with current search
2. **RFP/tender signals:** Any public procurement notices for search technology
3. **Competitor displacement signals:** Job postings mentioning "migration FROM [current vendor]", or LinkedIn posts about evaluating search vendors
4. **Tech removal signals:** BuiltWith showing removal of current search vendor recently

### Tier 2: Medium-Intent Signals (Nurture)
These suggest the problem exists but no active evaluation yet:

1. **Platform migration in progress:** Replatforming to Salesforce CC, Shopify Plus, commercetools — often disrupts existing search integrations
2. **Recent funding event:** New capital typically triggers platform modernization within 12-18 months
3. **New digital leader hired:** New VP Digital/CTO/CDO typically re-evaluates stack within 6 months of joining
4. **Public complaints about search quality:** Customer reviews, social media complaints about site search
5. **Competitive pressure:** Direct competitor recently launched improved search/discovery experience

### Tier 3: Background Signals (Long-Term Awareness)
These don't indicate urgency but support the case:

1. **Growth trajectory:** Fast-growing companies outgrow their search solutions
2. **SKU expansion:** Rapidly growing catalog creates relevance challenges
3. **International expansion:** Multi-language search needs
4. **AI/personalization investments:** Companies investing here often need better search foundation

## What to Research

### Current Signal Sweep (Last 90 Days)
1. **LinkedIn job postings:** Search for {company_name} + search/discovery/relevance roles
2. **News:** Any platform migration announcements, tech investment announcements
3. **Leadership changes:** New C-suite or VP-level hires in digital/tech/product
4. **Funding/M&A:** Any capital events that free up tech investment budget
5. **Competitive events:** Did a key competitor launch a new search experience?

### Timing Intelligence
1. **Budget cycle:** When does their fiscal year end? Budgets are often set 3-6 months prior.
2. **Peak seasons:** E-commerce companies have heightened urgency before peak (holiday, back-to-school)
3. **Contract renewal window:** If they're on a 3-year deal with current vendor, when is it up?

### Intent Scoring (Your Assessment)
At the end of your research, provide a signal summary:

**HOT (act in <30 days):** [evidence]
**WARM (act in 30-90 days):** [evidence]
**COLD (nurture, 90+ days):** [evidence]
**NO SIGNAL:** [state clearly if no signals found]

## Source Priority
1. LinkedIn Jobs (last 30 days filter)
2. LinkedIn company posts
3. Google News (last 90 days)
4. BuiltWith historical data (technology removal/addition dates)
5. Crunchbase for funding events
6. G2/Trustpilot for customer complaints about search

## Output Instructions
Be direct about signal strength. A buying signal that is 18 months old is NOT a hot signal — note the date and downgrade the signal tier. The goal is to help a sales rep know: should I call this account TODAY, or should I wait and nurture? Be specific about the evidence for each signal.
