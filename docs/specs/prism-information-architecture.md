# PRISM — Information Architecture Specification
## Center Panel: Intelligence Dashboard
### For CoE Pitch and Claude Code Implementation

---

## LAYOUT (FINAL — LOCKED)

| Panel | Content | Width |
|---|---|---|
| Left | Accounts list + ROI Calculator | ~280px fixed |
| Center | Intelligence Dashboard (tabbed) | Remaining space (the hero) |
| Right | aRRIe chat (orchestrator + navigator) | ~340px fixed |

The center panel has a **tab rail** across the top — 6 tabs. Clicking a tab shows that section. aRRIe's chat is also a navigation controller: when the user asks a question, the center panel can navigate to the relevant section automatically.

---

## TAB STRUCTURE — 6 TABS

### Tab 1: OVERVIEW
### Tab 2: RESEARCH  
### Tab 3: SEARCH AUDIT
### Tab 4: BUSINESS CASE
### Tab 5: COMPETITIVE
### Tab 6: SALES ACTIONS

---

## TAB 1: OVERVIEW

**Purpose:** 60-second pre-call brief. The AE glances at this in the elevator. Everything they need to know on one screen, no scrolling.

**Layout:** Bento grid — 4 tiles in a 2x2 (or 6-column grid like the SPA).

| Tile | Question it Answers | Content | Source Modules |
|---|---|---|---|
| WHO IS THIS? | "What company am I about to meet?" | Company name, revenue, search vendor + Target badge, ecommerce platform, vertical badge | intel-company, intel-techstack |
| HOW BAD IS THEIR SEARCH? | "What's the headline finding?" | Score (large number /10), verdict badge (CRITICAL/MODERATE/OK), top 3 critical gaps as bullet points | audit-report (or audit-browser if available) |
| WHY ACT NOW? | "Why should I call this week?" | Top 3 urgency signals — exec statement, competitor move, industry risk. Color-coded by urgency. Clickable to source. | intel-news, intel-investor, intel-hiring, intel-social |
| WHAT DO I DO NEXT? | "What's my first move?" | Urgency label (HIGH/MEDIUM), recommended action ("Share audit + book 15-min call with SVP Digital"), owner, due date | synth-sales-plays |

**Below the bento:** Customer Proof teaser — if a matched case study exists from the evidence database, show the proof card: "Shoe Carnival — similar challenge, proven with Algolia. Up to 3.5x increase in conversions. See case study →"

**Framework used:** Pre-Call Brief (AE-optimized dashboard tile). NOT a traditional framework — it's a purpose-built summary card.

**Framework decision:** No analytical framework here. This is a dashboard, not an analysis. Every element is a pointer to deeper sections.

---

## TAB 2: RESEARCH

**Purpose:** Deep company intelligence. The SE or AE digs in before a strategic call. This is reference material — comprehensive, well-organized, scannable.

**Layout:** Vertical scroll with section dividers. Each section has: eyebrow label, title, content. Sections are individually collapsible.

### Section 2.1: Company Snapshot
**Source:** intel-company
**Display pattern:** Profile card with structured data
- Company name, logo placeholder, vertical, HQ, founded, employee count
- Business model description (2-3 sentences)
- Executive list: name, title, LinkedIn link (table format, not org chart)
- Key competitors identified (clickable — jumps to Competitive tab)

**Framework:** None needed. This is structured data display.

### Section 2.2: Financial Profile
**Source:** intel-financial-public OR intel-financial-private
**Display pattern:** Trend analysis — 3-year data

For public companies:
- Revenue headline (large number, NumberFlow animated)
- 3-year data table: Revenue, Gross Profit, Operating Margin, Net Income, Growth Rate
- Market cap, P/E ratio, analyst consensus in metric tiles
- Digital revenue share if available from 10-K analysis

For private companies:
- Revenue estimate range (low — high) with confidence indicator
- 6-source waterfall visualization: which sources agree, which diverge
- Funding stage, last known round

**Framework:** Trend Analysis — shows trajectory, not just a snapshot. "Revenue declined from $3.5B to $3.07B over 3 years — that's a headwind. Position Algolia as an efficiency play, not a growth play."

### Section 2.3: Technology Stack
**Source:** intel-techstack
**Display pattern:** Categorized inventory

- Search vendor callout at top (large, prominent): "Search: Coveo (ACTIVE, Verified)" with source badge
- Category groups: Analytics, Personalization, Ecommerce Platform, CMS, CDN, Tag Management
- Each tech: name + first detected date + source badge
- Golden Angle alert banner if competitor uses Algolia
- Competitor tech comparison: prospect vs top 3 competitors side by side (which search vendor does each use?)

**Framework:** Tech Stack Map — visual inventory grouped by category. Standard pattern from BuiltWith and Crayon.

### Section 2.4: Traffic & Digital Presence
**Source:** intel-traffic
**Display pattern:** KPI dashboard with chart

- Top metrics row: Monthly Visits, Bounce Rate, Pages/Visit, Avg Visit Duration in metric tiles
- Traffic source donut chart (interactive — Direct, Organic, Social, Referral, Paid, Other)
- Geographic breakdown: top 5 countries with traffic share
- Device split: Desktop / Mobile / Tablet percentages
- Trend: monthly visits sparkline (6-month trend if available)
- Competitor traffic comparison row: prospect vs top 3 competitors

**Framework:** KPI Dashboard — standard analytics presentation. Same layout SimilarWeb uses in their own product.

### Section 2.5: Hiring Signals
**Source:** intel-hiring
**Display pattern:** Grouped role table + signal badges

- Build vs Buy signal: prominent badge at top (BUILD SIGNAL or BUY SIGNAL) with reasoning
- Open roles grouped by ICP tier:
  - Tier 1 (Economic Buyer): VP/Director titles
  - Tier 2 (Technical): Engineering/Architect titles
  - Tier 3 (Champion): Manager/Lead titles  
  - Tier 4 (User): Analyst/Specialist titles
- Each role: title, department, location, date posted, ICP tier badge
- Champion signals highlighted: "New hire in search role — 30-day window to engage"
- Buying committee summary: table with name, title, tier, approach

**Framework:** Role-based classification. Standard sales intelligence pattern. The ICP tier grouping is PRISM's own addition — no other tool does this.

### Section 2.6: News & Signals
**Source:** intel-news
**Display pattern:** Signal timeline — chronological, color-coded

- Filter bar at top: pill buttons (All, Digital Investment, Technology, AI, Competitive, Leadership)
- Signal cards in reverse chronological order, each with:
  - Left color bar by category
  - Severity dot + type badge + headline
  - Detail text (1-2 sentences)
  - Source link
  - Urgency badge if HIGH
- Executive media quotes highlighted with quote styling and attribution

**Framework:** Signal Timeline — shows recency and velocity. Red = urgent (leadership change in last 30 days), amber = watch (tech investment), green = positive (growth signal). This is Crayon's core format and it works because it answers "what's happening NOW?"

### Section 2.7: Social Intelligence
**Source:** intel-social
**Display pattern:** Activity feed

- Executive LinkedIn activity: post summaries with topic classification badges
- Quotable statements (top 5): styled as pull quotes with "Copy" button — AE can paste into emails
- Twitter/X presence if available
- Algolia relevance scoring: HIGH/MEDIUM/LOW per item

**Framework:** Activity Feed — standard social monitoring format. No analytical framework needed. The value is the raw signal, not the framework.

### Section 2.8: Investor Intelligence
**Source:** intel-investor
**Display pattern:** Quote-first analysis

- Said vs Found preview: top 3 rows (teaser — full version in Business Case tab). Clickable link: "See full Said vs Found →"
- Earnings call quotes: verbatim quotes from last 4 quarters, attributed to speaker with title. Sales angle badge next to each quote.
- Board composition: table with name, title, background badge (Tech Background = buying signal)
- 10-K risk factors: collapsible chips (Technology Risk, Digital Disruption, Legacy Systems)
- Top 5 sales angles: numbered list with evidence citation

**Framework:** The Said vs Found preview is PRISM's own framework. The rest is structured data display. The sales angle generation is unique to PRISM — no other tool maps earnings quotes to sales approaches.

### Section 2.9: Partner Intelligence
**Source:** intel-partner
**Display pattern:** Relationship table

- SI relationships: partner name, relationship type, engagement level
- Co-sell opportunities: where warm introductions exist
- Vertical case studies from partners
- Partner play recommendation badge
- Crossbeam overlap count if available

**Framework:** Ecosystem table. Keep it simple. A network diagram (ecosystem map) looks cool but is hard to read and harder to act on. A table with "who, what relationship, what opportunity" is more actionable for an AE.

### Section 2.10: Industry Benchmarks
**Source:** intel-industry
**Display pattern:** Comparison bars

- "You vs Industry Average" horizontal bars for key metrics: conversion rate, AOV, digital revenue share, search quality score
- Industry trends: bullet list with trend direction icons (↑ growing, → stable, ↓ declining)
- Pain points mapped to Algolia capabilities: two-column table (Industry Pain → Algolia Solution)
- Algolia case studies in this vertical (from evidence database): company name + result + link

**Framework:** Benchmark Comparison — horizontal bars showing prospect position vs industry average. This is the standard Forrester/Baymard format and it works because the comparison instantly shows "you're behind" or "you're ahead."

---

## TAB 3: SEARCH AUDIT

**Purpose:** The technical evidence. How bad is their search, proven with screenshots and scores. This is what SEs use to build POC proposals.

**Layout:** Table of contents at top, then per-finding chapters below.

### Section 3.1: Score Summary
**Source:** audit-report (10-dimension scoring)
- Overall score: large number, colored by severity, verdict badge
- Quick stats: X critical gaps, Y moderate, Z positive strengths
- 3 large stat cards in a row: Critical count (red), Total findings, Overall score

### Section 3.2: Score by Dimension
**Source:** audit-report
- Table with 10 rows, one per dimension
- Columns: Dimension name, Score bar (filled, colored by severity), Score number, Severity badge
- Dimensions: Relevance, Speed, Typo Tolerance, NLP/Semantic, Autocomplete, Faceting, Zero-Results, Personalization, Merchandising, Analytics
- Competitor scores side-by-side if audit-browser ran on competitors

### Section 3.3: Per-Finding Chapters
**Source:** audit-browser + audit-report
- Each finding is a chapter with:
  - Finding ID badge (G01, G02 for gaps; S01, S02 for strengths)
  - Title + severity badge
  - Tested query / Expected result / Found result (side by side)
  - Screenshot thumbnails (clickable to expand to full size)
  - "How Algolia Fixes It" section: green-tint background, green left border, solution text with feature names
  - Industry proof point: "In footwear retail, 87% of sites with NLP search see higher conversion rates"

**Framework:** Scorecard with Evidence. This is PRISM's SPA pattern and it works. Don't change it. The TOC at top with severity bars, the per-finding chapters with visual evidence — this is the pattern that proves the audit isn't just an opinion.

---

## TAB 4: BUSINESS CASE

**Purpose:** The money slide. Why should the prospect spend money on this? Executive-ready evidence.

**Layout:** Vertical sections, each building on the last. This tab tells a story: what leaders said → what we found → what it's worth → who else did this → why act now.

### Section 4.1: Said vs Found (THE HOOK)
**Source:** synth-business-case + intel-investor
**Display pattern:** 3-column colored table (from SPA)

- Column headers: "They Said" (green), "We Found" (red), "Algolia Solution" (blue)
- 5-7 rows mapping executive statements to audit findings to Algolia capabilities
- Each "They Said" cell: italic quote, attribution, source badge
- Each "We Found" cell: bold problem statement with evidence
- Each "Algolia Solution" cell: capability description with cross-link to search audit finding

**Framework:** Evidence Matrix — PRISM's own creation. No other tool has this. This is the single most powerful slide in any AE's deck because it takes the prospect's OWN words and connects them to YOUR evidence. It's unarguable.

**Framework decision: KEEP. This is the crown jewel. Front and center.**

### Section 4.2: Revenue & ROI Calculator
**Source:** synth-business-case + algolia_proofpoints
**Display pattern:** Two-panel interactive calculator (from SPA)

- Left (builder): 3 baseline inputs + 4 lever sliders with case study proof
- Right (summary): total annual impact (large, animated), breakdown per lever, formula note
- Proof badges on every lever: "CASE STUDY: Decathlon saw +50% lift"
- Below: Revenue at Risk bounce cards (Conservative / Moderate / Optimistic) with glow shadows

**Framework:** Value Engineering Calculator — industry standard (Forrester TEI format). Each lever backed by a real customer metric from the evidence database. This is NOT a theoretical model — it's grounded in actual Algolia customer results.

**Framework decision: KEEP. The interactive calculator with proof points is genuinely useful. AEs can adjust sliders live during a meeting.**

### Section 4.3: Customer Proof
**Source:** algolia_case_studies + algolia_quotes + algolia_proofpoints (from Session 10 evidence database)
**Display pattern:** Proof stack

- Matched case study cards: gradient cards with company name, vertical match, key result, case study link
- Customer quotes: pull quotes with name, title, company, source
- Proof metrics: "15 customers in your vertical. Average conversion lift: +35%."

**Framework:** Social Proof Stack — logos, quotes, metrics. Standard persuasion pattern. But PRISM's version is uniquely powerful because the matching is automated — the system finds the most relevant proof from 1,300+ customers based on the prospect's vertical and tech stack.

**Framework decision: KEEP. Proof beats promises every time.**

### Section 4.4: Why Act Now
**Source:** intel-news + intel-hiring + intel-investor + intel-social
**Display pattern:** Urgency signal cards

- Top urgency signals sorted by severity
- Each signal: icon, type badge, headline, detail, source link, severity dot
- Timing context: "Leadership change 3 weeks ago — 30-day window", "Competitor deployed Algolia last quarter — urgency rising"

**Framework decision:** This is a filtered view of signals from Research, focused on timing. It earns its place here because the Business Case tab tells a story: what they said → what we found → what it's worth → what others did → why NOW. The "why now" is the closer.

**WHAT I DROPPED FROM CLAUDE CODE'S RECOMMENDATION:**

**SWOT — DROPPED.** The same data appears in better formats: strengths = positive audit findings (Tab 3), weaknesses = critical gaps (Tab 3), opportunities = Said vs Found (Tab 4), threats = competitive signals (Tab 5). SWOT is redundant with the data already presented. It also carries "generic consultant deck" connotations that undermine PRISM's premium positioning.

**Urgency Matrix (2x2 impact × urgency) — DROPPED.** The Why Act Now section with severity-coded signal cards is more actionable than a 2x2 quadrant. A quadrant says "this is high impact high urgency." A signal card says "CEO said digital transformation is priority Q3 — here's the quote, here's the link." Specificity beats abstraction.

---

## TAB 5: COMPETITIVE

**Purpose:** How does the prospect compare to their peers? This is PRISM's differentiator — simultaneous benchmarking.

**Layout:** Two main components, stacked.

### Section 5.1: Comparison Matrix
**Source:** intel-competitors
**Display pattern:** Data table with color-coded cells

- Columns: dimension name, prospect, competitor 1, competitor 2, competitor 3
- Rows: Search Vendor, Search Quality Score, Monthly Traffic, Revenue, Employee Count, Digital Investment Signal, Hiring Signal (Build/Buy), Social Sentiment
- Cells: color-coded by relative position (green = leader in this dimension, amber = middle, red = lagging)
- Column headers: prospect name on blue background, competitor names on neutral

**Framework:** Competitive Matrix — the Klue/Crayon standard. This works because it's instantly scannable. The AE can point at a cell and say "You're here, your competitor is there. Let me show you how to close that gap."

### Section 5.2: Battle Cards
**Source:** intel-competitors + synth-sales-plays + algolia_case_studies
**Display pattern:** One expandable card per competitor

Each battle card contains:
- Competitor name + scenario badge: GOLDEN (competitor is Algolia customer), OFFENSIVE (prospect is stronger — expand), DEFENSIVE (competitor is stronger — protect), DISPLACEMENT (prospect uses competitor's product — replace)
- Their strengths: 3-4 bullet points from the competitive analysis
- Our advantages: 3-4 Algolia strengths against this specific competitor
- Landmines to set: questions that expose the competitor's weaknesses
- Killer quote: a customer quote about switching FROM this competitor to Algolia (from evidence database)
- Talk track: 2-3 sentences in the prospect's language

**Framework:** Battle Cards — industry standard for sales enablement. 71% of companies report higher win rates using them. The scenario classification (GOLDEN/OFFENSIVE/DEFENSIVE/DISPLACEMENT) is PRISM's own addition and should be a prominent badge, not a separate view.

### Section 5.3: Golden Angle Banner (conditional)
**Source:** intel-competitors + algolia_customers (evidence database)
**Display pattern:** Full-width highlighted banner. ONLY shows when a competitor is an Algolia customer.

- "GOLDEN ANGLE: [Competitor] is an Algolia customer"
- Key result from their case study
- Case study link
- Talk track: how to use this in the conversation

**Framework decision:** Not a framework — it's a conditional callout. It only appears when the data triggers it. When it does appear, it should be impossible to miss.

**WHAT I DROPPED:**

**Spider/Radar Chart — DROPPED from its own section.** The 10-dimension spider chart is visually appealing but practically hard to read. The Score by Dimension bar chart in Tab 3 shows the same data more clearly. If you want the spider chart, put it in the Overview tile as a small visual — not as a standalone section.

**Competitive Signal Feed — DROPPED as separate section.** This is already covered in Research Tab 2.6 (News & Signals). Adding a duplicate feed in the Competitive tab creates redundancy. The battle cards already cite the most relevant competitive signals.

---

## TAB 6: SALES ACTIONS

**Purpose:** Ready-to-use sales tools. The AE walks out of this tab with everything they need to run the deal.

**Layout:** Vertical sections, each a distinct deliverable.

### Section 6.1: Deal Qualification — MEDDPICC
**Source:** synth-sales-plays
**Display pattern:** Accordion — 8 sections, one per letter

- M — Metrics: measurable outcomes that matter + evidence (from ROI calculator)
- E — Economic Buyer: who signs the check (from intel-hiring buying committee)
- D — Decision Criteria: what they'll evaluate on (from intel-investor + intel-company)
- D — Decision Process: how they decide (inferred from company size + industry norms)
- P — Paper Process: procurement requirements (inferred)
- I — Identified Pain: what hurts today (from audit findings)
- C — Champion: internal advocate (from intel-hiring champion signals)
- C — Competition: who else they're looking at (from intel-competitors)

Each section: populated field + evidence citation + confidence badge (Verified / Inferred / Unknown). "Unknown" fields explicitly marked — the AE knows what they still need to discover.

**Framework:** MEDDPICC — the enterprise SaaS qualification standard. 73% of companies selling >$100K use it. The power here is that PRISM pre-populates it with real data instead of the AE filling it from memory.

**Framework decision: KEEP. Industry standard, universally understood, pre-populated with data.**

### Section 6.2: Discovery Prep — SPIN Questions
**Source:** synth-sales-plays
**Display pattern:** Grouped question list with copy buttons

- Situation (3-4 questions): "What search platform do you use today?" — contextualized with what PRISM already knows, so the AE doesn't ask questions they already have answers to
- Problem (3-4 questions): "How often do customers see zero search results?" — referencing actual audit data
- Implication (3-4 questions): "What does that cost you in lost revenue per month?" — tied to ROI model
- Need-payoff (3-4 questions): "If you could eliminate zero results, what would that mean for Q4?"

Each question has a "Copy" button and a note explaining why this question matters based on the audit data.

**Framework:** SPIN Selling — from 35,000+ sales call analyses. The four question types move the buyer from "I have a situation" to "I need a solution." PRISM's version generates these from REAL data, not templates.

**Framework decision: KEEP. The data-backed questions are genuinely differentiated from generic SPIN templates.**

### Section 6.3: Objection Handling
**Source:** synth-sales-plays + algolia_proofpoints
**Display pattern:** Expandable cards — one per common objection

- "We can build it ourselves" → counter with TCO analysis + "Dell has 3 search engineers costing $600K/yr vs Algolia at $X/yr" + hiring data evidence
- "We're happy with our current vendor" → counter with competitive gaps + benchmark comparison
- "Budget is tight" → counter with ROI model + payback period + customer proof
- "We tried Algolia before" → counter with what's changed (NeuralSearch, AI features)

Each objection: the objection text, the counter argument, the specific evidence from PRISM data, and a customer proof point.

**Framework:** Battle-tested counters — standard from Klue/Crayon battle card format. Each objection paired with data-backed counter, not generic responses.

**Framework decision: KEEP. Data-backed objection counters are one of the highest-value deliverables for AEs.**

### Section 6.4: Buying Committee & Power Map
**Source:** intel-hiring + intel-social + synth-sales-plays
**Display pattern:** Table with attitude badges

- Each row: name, title, ICP tier, attitude badge (Champion / Supportive / Neutral / Skeptical / Blocker / Unknown), recommended approach, evidence
- Attitude inferred from: LinkedIn posts (intel-social), hiring activity (intel-hiring), earnings call quotes (intel-investor)
- Champion row highlighted in green

**Framework decision:** Start with a table. A visual org chart / power map looks impressive but is fragile — it requires accurate reporting relationships that PRISM doesn't have. A table with attitude badges is honest about what we know and what we don't.

### Section 6.5: Outreach Sequence — ABX Campaign
**Source:** campaign-abx
**Display pattern:** Horizontal stepper + expandable emails

- 5-step visual stepper: Hook → Insight → Proof → ROI → Ask
- Click each step to see full email: subject line, body, CTA
- All emails reference specific audit data — not templates
- LinkedIn messages section: per buying committee member
- Loom video script: collapsible, violet-tint background
- Collateral schedule: week-by-week timeline

**Framework:** ABX sequence — standard multi-touch campaign format. Personalized from PRISM data, not generic templates.

**Framework decision: KEEP. Ready-to-send emails are the highest-leverage deliverable after the audit.**

---

## MODULE-TO-TAB MAPPING (all 20 modules accounted for)

| Module | Primary Tab | Secondary Tab |
|---|---|---|
| intel-company | Research (2.1) | Overview |
| intel-techstack | Research (2.3) | Overview, Competitive |
| intel-traffic | Research (2.4) | Competitive (matrix) |
| intel-financial-public | Research (2.2) | Business Case (ROI baseline) |
| intel-financial-private | Research (2.2) | Business Case (ROI baseline) |
| intel-news | Research (2.6) | Business Case (Why Act Now) |
| intel-hiring | Research (2.5) | Sales Actions (MEDDPICC, Power Map) |
| intel-social | Research (2.7) | Sales Actions (Power Map) |
| intel-investor | Research (2.8) | Business Case (Said vs Found) |
| intel-partner | Research (2.9) | — |
| intel-industry | Research (2.10) | Business Case (proof points) |
| intel-competitors | Competitive (5.1, 5.2) | Overview |
| intel-queries | Search Audit (input) | — |
| audit-browser | Search Audit (3.3) | Overview (score tile) |
| audit-report | Search Audit (3.1, 3.2) | Overview (score tile) |
| synth-business-case | Business Case (4.1, 4.2) | Overview (next step) |
| synth-sales-plays | Sales Actions (6.1-6.4) | Overview (next step) |
| campaign-abx | Sales Actions (6.5) | — |
| audit-factcheck | Internal (quality gate) | Shown as confidence badge on all data |
| insights-engine | Research (2.10 benchmarks) | — |

## FRAMEWORKS USED (FINAL — 8 total)

| Framework | Where Used | Why It Earns Its Place |
|---|---|---|
| Pre-Call Brief | Overview | AE needs 60-second summary. No other format works. |
| Benchmark Comparison | Research (Industry) | "You vs average" instantly shows position. |
| Signal Timeline | Research (News) | Shows recency and velocity of signals. |
| Scorecard with Evidence | Search Audit | Proves findings with screenshots, not opinions. |
| Evidence Matrix (Said vs Found) | Business Case | PRISM's crown jewel. Connects their words to our evidence. |
| Value Engineering Calculator | Business Case (ROI) | Interactive, proof-backed, usable in live meetings. |
| MEDDPICC | Sales Actions | Industry standard qualification. Pre-populated with data. |
| SPIN | Sales Actions | Data-backed discovery questions, not templates. |

## FRAMEWORKS DROPPED (4 killed)

| Framework | Why Dropped |
|---|---|
| SWOT | Redundant. Same data in better formats (Said vs Found, competitive matrix, signal timeline). "Consultant deck" connotations. |
| Urgency Matrix (2x2) | Abstraction adds no value over the specific signal cards. |
| Spider/Radar Chart | Hard to read in practice. Score bars show same data more clearly. |
| Ecosystem Map (network diagram) | Looks cool, hard to act on. Simple relationship table is more actionable. |

---

## NAVIGATION BEHAVIOR

When aRRIe mentions a finding in chat, it should include a navigation hint that the center panel can act on:

- aRRIe says "The tech stack shows Coveo" → center navigates to Research > Tech Stack (2.3)
- aRRIe says "Check the Said vs Found" → center navigates to Business Case > Said vs Found (4.1)
- aRRIe says "The competitive matrix shows Dell lagging" → center navigates to Competitive > Matrix (5.1)
- aRRIe says "I've generated the email sequence" → center navigates to Sales Actions > Outreach (6.5)

Implementation: aRRIe's tool results include a `navigate_to` field with the section ID. The frontend uses this to auto-navigate the center panel tab and scroll to the section.
