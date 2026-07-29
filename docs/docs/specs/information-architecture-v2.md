# PRISM Intelligence Dashboard — Information Architecture v2
**Date:** 2026-04-02
**Status:** Draft — Pending Review
**Context:** Session 11 brainstorm. Replaces the zoom-parallax and chat-centric approaches.

---

## Design Decision

**Layout:** SPA-style intelligence dashboard in center panel, aRRIe chat in right panel.
**Navigation:** 6 tabbed sections with direct access (no linear scroll dependency).
**Rationale:** AEs need random access to specific intelligence (competitive data before a call, email sequence for outreach). Scroll-heavy experiences cause fatigue and context loss. The SPA template already has proven IA.

---

## Layout Structure

```
┌───────────────────────────────────────────────────────────┐
│ Algolia  │  PRISM  │  [Account: Jewson · jewson.co.uk]  AC│
├──────┬───┴─────────────────────────────────┬──────────────┤
│ Left │  Overview│Research│Audit│Case│Comp│Sales           │
│ 240px│─────────────────────────────────────│  Right 340px │
│      │                                     │              │
│ Acct │   [Active tab content]              │  aRRIe Chat  │
│ List │                                     │              │
│      │                                     │              │
│ A-Z  │                                     │              │
│      │                                     │              │
│ ROI  │                                     │              │
├──────┴─────────────────────────────────────┴──────────────┤
│ ⚠ AI disclaimer                                           │
└───────────────────────────────────────────────────────────┘
```

---

## Section 1: OVERVIEW

**Purpose:** 60-second pre-call brief. Everything the AE needs before walking into a meeting.

**Source modules:** intel-company, audit-report (pre-call brief), synth-business-case (one-line pitch), audit-factcheck (verdict)

**Framework:** Executive Dashboard / Pre-Call Brief

**Cards:**

| Card | Content | Visual |
|------|---------|--------|
| Who Is This | Company name, industry, HQ, revenue, employees, website | Glassmorphism bento tile, icon badges |
| Search Score | Overall score /10, verdict, top 3 critical gaps | 72px animated number, severity bars |
| Top Signals | 3 most urgent signals from news/hiring/investor | Signal timeline with urgency colors |
| Pre-Call Brief | 60-second AE read from audit-report | Compact text block, structured bullets |
| One-Line Pitch | From synth-business-case | Large quote-style text |
| Factcheck Verdict | PROCEED / WARN / BLOCKED badge | Traffic light indicator |
| Module Status | Which of 20 modules ran, which are missing, dates | Progress bar + checklist |

**Downloads available:** Pre-call brief PDF, Leave-behind PDF, Full audit JSON

---

## Section 2: RESEARCH

**Purpose:** Deep intelligence on the prospect company and its market. All about understanding WHO they are.

**Source modules:** intel-company, intel-techstack, intel-traffic, intel-financial-public/private, intel-industry, intel-news, intel-hiring, intel-social, intel-investor, intel-partner

**Framework:** Collapsible section groups, each with a summary header and expandable detail

**Sub-sections:**

### 2a. Company Profile
- **Source:** intel-company
- **Framework:** Company identity card
- **Shows:** Name, legal name, industry, HQ, founded, employee count, revenue, website snapshot, business model description
- **Key execs table:** Name, title, tenure, LinkedIn URL

### 2b. Technology Stack
- **Source:** intel-techstack
- **Framework:** Tech Stack Map — visual inventory grouped by category
- **Shows:** Search vendor (with ACTIVE/TAG_ONLY/REMOVED status badge), ecommerce platform, CMS, CDN, analytics tools, personalization tools, bot detection
- **Competitor tech comparison table:** Side-by-side (who uses what)
- **Golden Angle callout:** If competitor uses Algolia

### 2c. Traffic & Engagement
- **Source:** intel-traffic
- **Framework:** KPI Dashboard — metric tiles + trend visualization
- **Shows:** Monthly visits (6-month trend), traffic sources (SVG donut chart), device split bar, top countries, top keywords, bounce rate, pages/visit
- **Google Trends momentum indicator**
- **Competitor traffic comparison table**

### 2d. Financial Profile
- **Source:** intel-financial-public OR intel-financial-private
- **Framework:** Trend Analysis — 3-year chart + key ratios
- **Public:** Revenue trend (3yr bar chart), margins, market cap, P/E, analyst consensus, SEC insights, investor presentation highlights
- **Private:** Revenue waterfall (6 estimates with confidence), funding data, employee revenue model
- **Competitor financial comparison table**

### 2e. Industry Context
- **Source:** intel-industry
- **Framework:** Benchmark Comparison — prospect vs vertical average
- **Shows:** Vertical benchmarks (conversion rate, AOV, digital revenue share), industry trends with relevance to search, pain points mapped to Algolia capabilities, vendor landscape market share, case studies in vertical

### 2f. News & Signals
- **Source:** intel-news
- **Framework:** Signal Timeline — chronological with urgency color coding
- **Shows:** 90-day news sweep (headline, source, date, category), urgency signals (red/amber/gray tiers), executive media quotes, sell signals flagged
- **Competitor news section**

### 2g. Hiring Intelligence
- **Source:** intel-hiring
- **Framework:** Hiring Signal Dashboard
- **Shows:** Open roles by ICP tier (economic buyer / technical / champion / user), search-related roles highlighted, hiring velocity trend, build-vs-buy signal (with evidence), buying committee mapping
- **Competitor hiring comparison**

### 2h. Executive & Social Intelligence
- **Source:** intel-social + intel-investor
- **Framework:** Power Map + Quote Library
- **Shows:** Executive social posts (platform, topic, relevance), quotable statements, earnings call quotes (verbatim), Said vs Found mappings, YouTube/media appearances, board composition (tech background flags), 10-K risk factors
- **Sales angles derived from investor intel**

### 2i. Partner Ecosystem
- **Source:** intel-partner
- **Framework:** Ecosystem Map
- **Shows:** SI relationships, co-sell opportunities, partner overlaps (Crossbeam if available), vertical case studies, recent partnership announcements, competitor partners
- **Partner play recommendation card**

---

## Section 3: SEARCH AUDIT

**Purpose:** How good is their search experience today? Evidence-based scoring.

**Source modules:** audit-browser, intel-queries, audit-report (dimension scores)

**Framework:** Scorecard with Evidence (TOC pattern from SPA)

**Components:**

| Component | Framework | Content |
|-----------|-----------|---------|
| Score Summary | Large animated number + verdict | Overall score /10, severity badge |
| Quick Stats | 3-card row | Critical gaps count, total dimensions, detected provider |
| 10-Dimension Table | TOC severity table (from SPA) | ID, area, score bar, severity, evidence link |
| Query Results | Expandable query-by-query detail | Query text, type, response time, result count, screenshot |
| Mobile Results | Separate section for mobile viewport | Same structure as desktop |
| Provider Detection | Badge + network evidence | Detected search API from network interceptions |
| Competitor Comparison | Side-by-side radar/spider chart | 10 dimensions overlaid for prospect vs each competitor |

---

## Section 4: BUSINESS CASE

**Purpose:** Why should they buy Algolia? ROI justification with evidence.

**Source modules:** synth-business-case, intel-investor (Said vs Found), customer evidence DB

**Frameworks:**

| Component | Framework | Content |
|-----------|-----------|---------|
| Said vs Found | Evidence Matrix (PRISM original) | 4-column table: exec_said → we_found → competitors_doing → your_move. Color-coded headers. |
| ROI Calculator | Value Engineering Calculator | Interactive 4-6 levers, each backed by case study proof. Two-panel: builder + dark summary. Conservative/Moderate toggle. |
| SWOT | Data-Backed SWOT | 4-quadrant grid. Every item cites source module. Strengths from what's working, Weaknesses from audit gaps, Opportunities from competitor gaps + signals, Threats from competitor moves + market trends. |
| Urgency Matrix | 2×2 Impact × Urgency | Plots timing signals. Top-right = "act now." |
| Customer Proof | Social Proof Stack | Matched customers (logo rights only), case studies with URLs, verbatim quotes with attribution, proof points with metrics. |
| Displacement Model | Cost comparison table | Current vendor cost, switching cost, 3-year net benefit. |

---

## Section 5: COMPETITIVE INTEL ★

**Purpose:** THE differentiator. How the prospect compares to competitors across every dimension.

**Source modules:** intel-competitors (synthesis), intel-techstack, intel-traffic, intel-financial, intel-hiring, intel-news, intel-social, intel-investor, audit-browser, customer evidence DB

**Frameworks:**

| Component | Framework | Content |
|-----------|-----------|---------|
| Golden Angle Banner | Hero callout (conditional) | Full-width amber/gold banner if any competitor is Algolia customer. Company name, result achieved, case study link. |
| Competitive Matrix | Comparison table (Crayon/Klue style) | Rows = dimensions (search quality, tech, traffic, financial, hiring, sentiment). Columns = prospect + each competitor. Color-coded cells: green (winning), amber (par), red (losing). |
| Battle Cards | 1 card per competitor (industry standard) | Per competitor: overview, their strengths, our strengths, landmines to set, objection counters, killer quote, scenario classification. Collapsible accordion. |
| Scenario Classification | GOLDEN / OFFENSIVE / DEFENSIVE / DISPLACEMENT | PRISM's own framework. Each competitor labeled with scenario + evidence + play recommendation. |
| Search Quality Radar | Spider/radar chart | 10 dimensions overlaid — prospect vs competitors. Instantly shows gap areas. |
| Competitive Signal Feed | Chronological activity stream | Merged from news + hiring + social + investor: what competitors are doing RIGHT NOW. "Walmart hired 5 search engineers this month." "Target's CTO mentioned AI search investment." |
| Competitive Ammunition | Quotable talk tracks | From intel-investor competitive ammunition. Specific quotes and data points the AE can use in conversation. Copy-to-clipboard. |
| Customer Evidence Cross-Reference | Evidence matches | From algolia_customers: which of the prospect's competitors are Algolia customers? Case studies, quotes, proof points. |

---

## Section 6: SALES ACTIONS

**Purpose:** What does the AE do with all this intelligence? Ready-to-use collateral.

**Source modules:** synth-sales-plays, campaign-abx, audit-report (leave-behind + pre-call brief)

**Frameworks:**

| Component | Framework | Content |
|-----------|-----------|---------|
| MEDDPICC | 8-field qualification framework | Each field: evidence from PRISM data, recommended approach, confidence level. Accordion expandable per field. 73% of enterprise SaaS uses this. |
| SPIN Discovery | Question framework (Situation → Problem → Implication → Need-Payoff) | Generated from PRISM data, not templates. Each question has context and expected response. Copy-to-clipboard. |
| Objection Handlers | Objection → Counter → Evidence format | Anticipated objections with likelihood. Each paired with data-backed counter: "They say X → Show Y." Battle-tested format from Klue/Gong. |
| Power Map | Buying Committee visualization | Org-chart style. Each person: name, title, MEDDPICC role, attitude (Champion/Supportive/Neutral/Skeptical/Blocker), approach recommendation. Color-coded. |
| ABX Email Sequence | 5-step horizontal stepper | Hook → Insight → Proof → ROI → Ask. Each email: subject, body, personalization tokens, target role. Expand to see full email. |
| LinkedIn Messages | Per buying committee member | Connection request + 2 follow-ups per person. Blue LinkedIn styling. |
| Loom Script | 2-minute video outline | Opening hook, 3 screens (what to show + what to say), closing CTA. Violet styling. |
| Collateral Schedule | Week-by-week action plan | Table: week, actions, target contacts, notes. |
| Leave-Behind | Prospect-safe 3-pager | Search quality summary, anonymized competitive benchmark, top 3 recommendations, ROI summary, next steps. Download as PDF. |

---

## Synthesis Module Distribution

These modules don't have their own sections — their outputs are distributed:

| Module | Where its data goes |
|--------|-------------------|
| intel-competitors | Section 5 (Competitive Intel) — the entire section is built from this + cross-module competitive data |
| intel-queries | Section 3 (Search Audit) — feeds the test queries |
| synth-business-case | Section 1 (Overview: one-line pitch) + Section 4 (Business Case: Said vs Found, ROI, timing) |
| synth-sales-plays | Section 6 (Sales Actions: MEDDPICC, SPIN, objections, power map) |
| audit-report | Section 1 (Overview: score, pre-call brief) + Section 3 (Search Audit: dimension scores) + Section 6 (Sales Actions: leave-behind) |
| campaign-abx | Section 6 (Sales Actions: emails, LinkedIn, Loom, schedule) |
| audit-factcheck | Section 1 (Overview: verdict badge) — banner on any section if WARN/BLOCKED |
| insights-engine | Section 2 > Industry (vertical benchmarks) — anonymized cross-audit data |

---

## Customer Evidence Integration (Session 10)

Customer evidence from the evidence DB appears in:

| Section | How evidence is used |
|---------|---------------------|
| Section 1 Overview | "N customers in your vertical" count |
| Section 4 Business Case | Customer proof stack: matched case studies, quotes, proof points per ROI lever |
| Section 5 Competitive Intel | Golden Angle amplification: competitor is Algolia customer with case study |
| Section 6 Sales Actions | Email sequences reference specific case studies by name and URL |

---

## Navigation & Interaction

- **Tab switching:** Click tab or use keyboard (Cmd+1 through Cmd+6)
- **Cross-section links:** Any data point can link to its detailed view in another tab (e.g., "See full competitive analysis →" in Overview links to Section 5)
- **aRRIe integration:** Clicking "Ask aRRIe about this" on any card sends a contextual message to the chat panel
- **Copy-to-clipboard:** Every quote, talk track, email, and stat has a copy button
- **Expandable detail:** Sections use accordion pattern — summary visible, detail on click
- **URL hash routing:** Each tab and sub-section has a URL hash for direct linking and browser back button

---

## Open Questions

1. Should the Competitive Matrix show ALL dimensions or only the ones where the prospect is losing? (Risk of overwhelming with a 6×4 table)
2. Should Battle Cards be auto-generated or curated by the AE? (Auto + editable?)
3. The SWOT in Business Case — is it redundant with the Competitive Intel section? Or does SWOT serve a different audience (executive summary vs detailed analysis)?
4. How many case studies / quotes should we show inline vs behind a "see all" link? (Risk of overwhelming vs risk of hiding proof)
5. Should the Power Map be editable by the AE (add notes, change attitudes as they learn more)?
