---
name: cluster-b-financial
version: 1.0.0
description: Financial & Investor Intelligence deep research
cluster_id: B
cost_tier: deep-research
recency_bias_months: 6
feeds: [intel-financial-public, intel-financial-private, intel-investor]
---

## Research Mission

Conduct deep financial and investor intelligence research on **{company_name}** ({domain}). You are researching for a sales intelligence platform — your findings help sales teams understand the prospect's financial health, investment priorities, and executive language around spending.

## Company Context
- Public: {is_public}
- Ticker: {ticker}
- Industry: {industry}

## What to Discover

### Revenue & Financial Performance
1. **Revenue:** Annual revenue (last 3 years if available). Raw numbers in USD. Cite source precisely (SEC 10-K, earnings call, Forbes, etc.)
2. **Growth trajectory:** YoY revenue growth rate. Accelerating or decelerating?
3. **Profitability:** EBITDA margin, net income, gross margin if available
4. **Revenue breakdown:** By segment, geography, product line if available
5. **Guidance:** Forward-looking revenue guidance if public company

### For Public Companies
1. **SEC filings:** 10-K risk factors relevant to digital/tech investment. MD&A section commentary on digital strategy.
2. **Analyst consensus:** Buy/Hold/Sell rating, price target consensus, key analyst commentary
3. **Earnings calls (last 4 quarters):** Verbatim executive quotes about technology investment, digital transformation, search/discovery, AI, customer experience. These are GOLD — get the exact words.
4. **Recent investor presentations:** Key themes, strategic priorities communicated to Wall Street

### For Private Companies
1. **Funding history:** Rounds, amounts, investors, valuations if disclosed
2. **Revenue estimates:** Use multiple sources — LinkedIn employee count + revenue-per-employee benchmarks, industry databases, press coverage, job posting volume as proxy
3. **Investor/board commentary:** Any public statements from investors about the company's trajectory

### Buying Signals from Financial Data
1. **Investment priorities:** What did they say they're spending money on?
2. **Cost pressures:** Any margin squeeze that would require efficiency tech?
3. **Growth investments:** Expanding into new markets, hiring aggressively — signals for spend
4. **Recent fundraising/M&A:** New capital often precedes tech investment

## Source Priority
1. SEC EDGAR filings (10-K, 10-Q, 8-K) for public companies
2. Earnings call transcripts (Seeking Alpha, Motley Fool, company IR site)
3. Yahoo Finance, Bloomberg, Reuters for financial data
4. Crunchbase, PitchBook, CB Insights for private company funding
5. Forbes, Fortune, Inc. 5000 for revenue estimates

## Output Instructions
Write a comprehensive financial intelligence document. Every financial figure must have a source citation. Distinguish verified data (SEC filing) from estimates. Include verbatim executive quotes where found — use exact words, not paraphrases.
