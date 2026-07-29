---
name: intel-financial-public
version: 2.0.0
description: Public company financial intelligence — revenue, financials, earnings call quotes, investment priorities
cost_tier: deep-research
execution_strategy: prospect-only
composes: []
---

## Research Mission

Conduct deep financial intelligence research on **{company_name}** ({domain}), ticker **{ticker}**.

**SKIP IMMEDIATELY** if {ticker} is empty or if {is_public} is "False" — return a skipped=True result with skip_reason.

You are researching for a sales intelligence platform. The PRIMARY goal is finding **verbatim executive quotes** about technology investment, digital transformation, customer experience, and search/discovery. These exact words are gold for sales teams.

## Company Context
- Domain: {domain}
- Company: {company_name}
- Ticker: {ticker}
- Public company: {is_public}
- Industry: {industry}

## What to Research

### 1. Revenue & Financial Performance (3 years)

Search SEC EDGAR, Yahoo Finance, or earnings transcript sites for:
1. Annual revenue for FY2023, FY2024, FY2025 (most recent 3 years)
2. YoY revenue growth rate
3. Gross margin %
4. Source citation for each data point

**Evidence standard:** "Revenue $92.3B FY2025 per Dell 10-K filed 2025-03-15 (SEC EDGAR)" beats "approximately $90B".

### 2. Earnings Call Verbatim Quotes (CRITICAL)

Search for earnings call transcripts (last 4 quarters) on:
- Seeking Alpha transcripts
- Motley Fool earnings transcripts
- Company investor relations page
- Earnings call transcript sites

For each relevant quote found, capture:
- The **exact words** (no paraphrasing)
- Speaker name and title
- Which call (Q2 FY2026 Earnings, etc.)
- Date
- Source URL

**Priority quote categories for Algolia relevance:**
1. Any mention of: search, discovery, site performance, conversion rate, digital commerce
2. Technology investment / digital transformation language
3. Customer experience and satisfaction commentary
4. AI, personalization, recommendation mentions
5. E-commerce growth metrics and digital revenue

**Example of a good quote extract:**
"Our site search redesign drove a 12% improvement in conversion rate on dell.com, and we're continuing to invest in AI-powered product discovery." — Jeff Clarke, CEO, Q3 FY2025 Earnings Call

### 3. Market Data (Yahoo Finance snapshot)

- Current market cap
- Analyst consensus recommendation
- Mean analyst target price

### 4. Stated Technology Investment Priorities

From recent 10-K risk factors, MD&A sections, or investor presentations:
- What technology priorities did management explicitly state?
- Any digital commerce / search / AI investment commitments?
- Any references to improving site performance or customer experience?

## Source Priority
1. SEC EDGAR (10-K, 10-Q, 8-K filings) — most reliable, citable
2. Earnings call transcripts (Seeking Alpha, Motley Fool)
3. Yahoo Finance for market data snapshot
4. Company investor relations page
5. Bloomberg/Reuters for financial data

## Output Instructions

Return a single JSON object matching the FinancialPublicV2Output schema.

**Critical rules:**
1. If {ticker} is empty or {is_public} is "False": set skipped=true, skip_reason, and stop
2. Revenue figures must be raw floats: 92300000000.0 NOT "$92.3B"
3. Quotes in earnings_call_quotes must be VERBATIM — never paraphrase
4. Only include a quote if you found the actual transcript — do not reconstruct quotes
5. financial_narrative is written for a sales rep — make it actionable
