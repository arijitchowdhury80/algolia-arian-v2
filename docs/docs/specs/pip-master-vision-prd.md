# Prism — Prospect Intelligence Platform
## Master Vision & Product Requirements Document v2.0
### *Light goes in. Intelligence comes out.*

**Document status:** Living document. Research-validated. Phase 0 complete. Phase 1 in progress.
**Date:** March 31, 2026 (updated from March 30)
**Authors:** Arijit Chowdhury (Founder/Product Lead) + Claude (Chief Architect)
**Validated by:** Deep research across 500+ sources via ChatGPT, Gemini, Claude

---

## I. WHAT PRISM IS

### The One-Line Pitch
Prism is the first AI-powered platform that runs consulting-grade competitive intelligence on a prospect AND their competitors simultaneously, producing verified, evidence-graded sales intelligence and complete deal packages — what McKinsey charges $300K for, automated for $100.

### The Problem
Every B2B enterprise sales team has the same broken workflow. Before a high-value meeting, an AE spends 3-8 hours manually researching a prospect across a dozen disconnected tools — LinkedIn, ZoomInfo, BuiltWith, SimilarWeb, SEC filings, earnings calls, Glassdoor, job boards, industry reports, Google. The result is inconsistent, unverified, and stale. Worse, no existing tool answers the question executives actually care about: "How do we compare to our peers, and what does that mean for the next 12-24 months?"

### Why This Matters Now
2026 is the inflection point. Three shifts converged simultaneously:
1. **Agent infrastructure matured.** Temporal.io, LangGraph, and harness engineering patterns now make 20-step AI pipelines reliable enough for production.
2. **Structured LLM output is solved.** Instructor + Pydantic + forced tool choice reduces schema compliance failures to under 2%.
3. **No one connected the dots.** ZoomInfo does contacts. Demandbase does intent. Klue does battlecards. Gong does conversations. SimilarWeb does traffic. BuiltWith does tech stacks. Bloomberg does financials. Each exists in isolation. Nobody integrated them into a single intelligence pipeline with evidence grading and competitive benchmarking.

### The Apple Analogy
Apple didn't invent the mouse (Xerox did), the GUI (Xerox did), or the touchscreen (Motorola did). Apple integrated fragments into something that felt like magic. Prism integrates publicly available data fragments — SEC filings, API data, social signals, website behavior, job postings — into intelligence that no sales team has ever had access to. The data was always there. People were blind. Prism opens eyes.

---

## II. THE CORE DIFFERENTIATOR

### Competitive Experience Benchmarking

This is Prism's moat. It is what no other tool does.

When you trigger a Prism audit for Costco, the platform doesn't just research Costco. It identifies Costco's top 3-5 competitors (BJ's, Walmart, Target, Sam's Club), runs the EXACT same analytical methodology against ALL of them simultaneously, and produces a comparative intelligence matrix.

The output isn't "Costco needs NLP search." The output is:
- "Costco doesn't have NLP search. Neither do BJ's or Target. But Walmart does. If Costco moves now, they match Walmart and leapfrog the rest."
- "Costco's CTO said 'digital platform investment is our top priority for FY27.' BJ's CTO said the same thing last quarter, and they just deployed Algolia. Here's what BJ's got — 37% search conversion lift."
- "Costco scores 3.2/10 on search quality. Industry average is 4.8. Walmart scores 6.1. Here are the screenshots proving each finding."

That transforms a vendor pitch into a strategic briefing. The AE becomes a trusted advisor, not a salesperson. And THAT is how enterprise deals get won.

**Market validation:** Confirmed across 500+ sources in deep research. ChatGPT's gap matrix explicitly states: "Same methodology run simultaneously on prospect + competitors for a benchmark report — rare. Consulting-style benchmark is still largely services-led." Baymard UX-Ray 2.0 proves the methodology is automatable for UX. No one has pointed it at sales intelligence.

---

## III. PRODUCT ARCHITECTURE

### The Cardinal Rule
> Claude thinks. Code orchestrates. Modules execute. PostgreSQL remembers.
> Claude API is called ONLY inside modules that need intelligence.
> Claude API is NEVER called for coordination, routing, or state management.

### Technology Stack

| Layer | Technology | Research Validation |
|-------|-----------|-------------------|
| Orchestrator | **Temporal.io (Python SDK)** | OpenAI Codex and Replit agents run on Temporal. Confirmed as best-in-class for 20-90 min AI pipelines. |
| API | **FastAPI** | Native Pydantic integration. OpenAPI generation for team onboarding. |
| Data Contracts | **Pydantic v2** | Rust-powered validation. Discriminated unions for module output routing. JSON schema generation feeds Claude tool definitions. |
| LLM Extraction | **Instructor + Claude API** | Auto-retry-with-reasking on validation failure. <2% failure rate with forced tool choice. 3M+ monthly downloads. |
| Evaluator Agent | **PydanticAI** | Typed tools, observability, trace replay. The Pydantic team's official agent runtime. |
| Experience Testing | **Playwright + Claude Vision** | GAN-inspired eval: Evaluator uses Playwright MCP to interact with live pages, not static screenshots. |
| Database | **PostgreSQL 16** | JSONB for module outputs. Full provenance chain. ACID guarantees. |
| Cache/Queue | **Redis 7** | API response caching. Rate limiting. SSE pub/sub for real-time progress. |
| Voice Interface | **Retell AI + ElevenLabs** | Dual-Agent Voice RAG: Slow Thinker pre-fetches, Fast Talker responds <500ms. $0.07/min. |
| File Storage | **Cloudflare R2** | S3-compatible. Deliverables, screenshots, PDFs. Signed URLs. |
| Auth | **Clerk** | Okta SAML SSO for Algolia. RBAC built-in. |
| Frontend | **Next.js 15 + Vercel AI SDK 6 + assistant-ui + Tailwind** | AI-native conversational interface. 21st.dev components. |
| Observability | **Langfuse + Sentry** | Every Claude API call traced with cost, latency, I/O. |

### Data Source Strategy

**Perplexity is the primary intelligence engine for ALL web research.** One API covers 80% of what our modules need. Specialized APIs are used ONLY where structured data is genuinely better than what Perplexity provides.

| Source | Used For | Why Not Perplexity |
|---|---|---|
| **Perplexity** | Company intel, executives, competitors, news, quotes, social signals, industry research | PRIMARY for 80% of research |
| **BuiltWith** | Technology detection | Structured list of 3,000+ techs with categories and detection dates |
| **SimilarWeb** | Traffic analytics | Exact visit counts, source %, keyword rankings, trended |
| **Yahoo Finance** | Financial data | Structured JSON: price, revenue, margins — no LLM needed |
| **SEC EDGAR** | Official filings | Raw 10-K and earnings transcripts — we parse with our own LLM |
| **Apify** | LinkedIn scraping | Walled garden — Perplexity can't access LinkedIn |
| **Tavily** | BACKUP ONLY | If Perplexity is down or rate-limited |

### Database-First Caching

Every module result is cached in PostgreSQL. Before any API call, the system checks for a fresh cached result. API calls only happen for data we don't have or data that's expired.

| Data Type | TTL | Rationale |
|---|---|---|
| Technology stack | 7 days | Tech changes slowly |
| Traffic analytics | 24 hours | Monthly estimates update daily |
| Financial data | 1 hour | Market data moves fast |
| Hiring/jobs | 24 hours | Postings change daily |
| News | 6 hours | News cycle |
| Company profile | 7 days | Company identity is stable |

### System Architecture

```
                    ┌──────────────────────┐
                    │   React Frontend     │
                    │   (Vercel)           │
                    └──────────┬───────────┘
                               │ REST + SSE
                    ┌──────────┴───────────┐
                    │   FastAPI            │
                    │   (Railway)          │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴───────────┐
                    │   Temporal.io        │
                    │   Workflows +        │
                    │   Activities         │
                    │   (20 modules)       │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────┴────┐  ┌───────┴───────┐  ┌────┴────────┐
     │ PostgreSQL   │  │    Redis      │  │ Cloudflare  │
     │ (provenance  │  │  (cache/SSE)  │  │  R2 (files) │
     │  store)      │  │               │  │             │
     └──────────────┘  └───────────────┘  └─────────────┘
              │
     ┌────────┴──────────────────────────────────┐
     │           External APIs                    │
     │  Perplexity (primary) · BuiltWith ·        │
     │  SimilarWeb · Yahoo Finance · SEC EDGAR   │
     │  Apify · Crossbeam · Claude API           │
     └────────────────────────────────────────────┘
```

### The Module Contract

Every module — all 20 of them — implements the same interface. No exceptions.

```python
class ModuleInterface(ABC):
    name: str                       # e.g. "intel-techstack"
    version: str                    # Semantic version
    input_schema: type[BaseModel]   # Pydantic model for inputs
    output_schema: type[BaseModel]  # Pydantic model for outputs
    dependencies: list[str]         # Modules that must complete first
    requires_llm: bool              # Does this call Claude API?

    async def execute(self, input, context) -> ModuleResult
    async def validate(self, result) -> ValidationResult
    async def health_check(self) -> bool
```

### The Evidence Envelope

Every data point carries its provenance. This is non-negotiable.

```python
class EvidenceEnvelope(BaseModel):
    value: Any
    source: str                    # "builtwith_api", "sec_edgar", "llm_inference"
    source_url: Optional[str]
    retrieved_at: datetime
    as_of_date: Optional[date]     # when data was current, not when retrieved
    confidence: Literal["verified", "high", "medium", "low", "inferred"]
    method: str                    # "direct_api", "scrape", "llm_extraction"
    conflicts_with: list[str]      # source IDs of conflicting sources
```

**Conflict Resolution Hierarchy** (applied consistently):
1. Government filing (SEC EDGAR, Companies House) — highest
2. Verified third-party API (SimilarWeb, BuiltWith, Yahoo Finance)
3. Company self-reported (LinkedIn, press releases, career page)
4. Aggregator estimate (Crunchbase, PitchBook)
5. LLM inference from unstructured sources — lowest

### Harness Engineering: The Evaluator Pattern

From Anthropic's March 2026 harness engineering research: agents cannot accurately evaluate their own work. A separate Evaluator agent with access to raw evidence — not just synthesized output — is required for quality-critical pipelines.

Prism implements this via the factcheck module, which is a Temporal child workflow:
- **Generator:** Each intelligence module produces output with evidence envelopes
- **Evaluator:** A separate Claude instance reviews outputs against raw evidence, flags low-confidence claims, and produces the FACTCHECK_GATE verdict (PROCEED/WARN/BLOCKED)
- The Evaluator uses PydanticAI for typed tools and trace replay

---

## IV. THE 20 MODULES

Prism contains 20 distinct intelligence capabilities. Each is a standalone product in its own right. Together, they form an integrated intelligence platform.

### Wave 1: Intelligence Collection (11 modules, parallel)

| # | Module | What It Produces | Market Equivalent | Equivalent Cost |
|---|--------|-----------------|-------------------|----------------|
| 1 | **intel-company** | Company overview, executives, org structure, vertical classification, parent/portfolio detection | Clearbit, Crunchbase | $50K/yr |
| 2 | **intel-techstack** | Search vendor detection (3-source), ecommerce platform, full tech stack, technology change timeline | BuiltWith | $6K/yr |
| 3 | **intel-traffic** | Traffic profile (11 SimilarWeb endpoints), Google Trends momentum, SEO keyword gaps, seasonal patterns | SimilarWeb | $12K/yr |
| 4 | **intel-competitors** | Competitive landscape, Golden Angle detection, G2/TrustRadius reviews, competitor search quality testing | Klue, Crayon | $30-60K/yr |
| 5 | **intel-financial-public** | 3-year revenue trend, digital revenue from 10-K XBRL, earnings call quotes, peer comparison | Bloomberg Terminal | $25K/seat/yr |
| 6 | **intel-financial-private** | 6-source revenue waterfall with confidence scoring | PitchBook | $20K/yr |
| 7 | **intel-investor** | Verbatim exec quotes from earnings calls, SEC risk factors, sentiment trajectory, board analysis | S&P Capital IQ | $15K/yr |
| 8 | **intel-hiring** | Open roles (ICP-tiered), buying committee ID, champion signals, org structure, tenure analysis, contact enrichment | ZoomInfo + LinkedIn Sales Nav | $15-30K/yr |
| 9 | **intel-social** | Executive LinkedIn posts, company posts, Twitter/X, Reddit/HN developer sentiment | Sprout Social | $5K/yr |
| 10 | **intel-news** | 60-day news sweep, leadership changes, funding events, tech investments, product launches | Contify | $8K/yr |
| 11 | **intel-partner** | Crossbeam account overlap, tech partner co-sell opportunities, SI relationship mapping | Crossbeam + manual research | $10K/yr |

### Wave 1.5: Supplementary Intelligence (2 modules, parallel)

| # | Module | What It Produces | Market Equivalent | Equivalent Cost |
|---|--------|-----------------|-------------------|----------------|
| 12 | **intel-industry** | Vertical benchmarks (Baymard, Forrester), trend analysis, expert analyst quotes | Baymard UX-Ray | $2.4-9.5K/yr |
| 13 | **intel-queries** | Vertically-calibrated test query set for browser audit (14-18 queries across 8 types) | Manual SE expertise | N/A |

### Wave 2: Experience Audit (1 module)

| # | Module | What It Produces | Market Equivalent | Equivalent Cost |
|---|--------|-----------------|-------------------|----------------|
| 14 | **audit-browser** | 20-step live search testing, screenshot evidence, network-level analysis, mobile viewport, competitor comparison | Baymard custom audit | $200K/engagement |

### Wave 3: Synthesis (3 modules, sequential)

| # | Module | What It Produces | Market Equivalent | Equivalent Cost |
|---|--------|-----------------|-------------------|----------------|
| 15 | **synth-business-case** | 6-component ROI model with show-all-math, sensitivity analysis, competitor displacement cost model | Custom financial modeling | $50K consulting |
| 16 | **synth-sales-plays** | MEDDPICC playbook, SPIN discovery questions, exec-language talking points, objection handling, power map | Sales methodology consulting | $25K consulting |
| 17 | **audit-report** | Scored assessment (10 dimensions), comparative matrix, all deliverable assembly | Full consulting engagement | $100K+ |

### Wave 4: Activation (1 module)

| # | Module | What It Produces | Market Equivalent | Equivalent Cost |
|---|--------|-----------------|-------------------|----------------|
| 18 | **campaign-abx** | 5-email sequence, LinkedIn messages, Loom script, collateral schedule — all personalized from audit data | Agencies charge per campaign | $5-10K/campaign |

### Wave 5: Quality Gate (1 module)

| # | Module | What It Produces | Market Equivalent | Equivalent Cost |
|---|--------|-----------------|-------------------|----------------|
| 19 | **audit-factcheck** | 20-dimension verification, evidence tiering, claim registry, correction manifest, PROCEED/WARN/BLOCKED gate | No equivalent at any price | N/A |

### Wave 6: Intelligence Engine (1 module, post-audit background)

| # | Module | What It Produces | Market Equivalent | Equivalent Cost |
|---|--------|-----------------|-------------------|----------------|
| 20 | **insights-engine** | Cross-audit vertical benchmarks, pattern detection, anonymized industry intelligence | Forrester/Gartner benchmarks | $80K+/yr |

### Combined Market Equivalent Value
If a company purchased each capability separately: **$400K-$600K+ per year**
Prism delivers all 20 integrated: **~$7,200/yr** (Professional tier at $600/mo)

---

## V. THREE USER ENTRY POINTS

### 1. Quick Lookup (~10 seconds, ~$2)
AE is about to jump on a call. Types or says "tell me about Dell." Gets a summary card: company snapshot, current search vendor, last audit score if one exists, top 3 signals, recommended first play. Pulls from accumulated account intelligence in PostgreSQL. If no data exists, kicks off lightweight collection (company + techstack + traffic) in ~30 seconds.

### 2. Full Audit (~20-40 minutes, ~$100 with competitive benchmark)
AE clicks "run full audit" or says "run a deep dive on Dell." Triggers the Temporal workflow — all 20 modules, waves, gates. Progressive delivery: AE brief ready in 10 minutes, full SPA in 20, ABX campaign in 30. Real-time progress via SSE — each module lights up as it completes.

### 3. Bulk Import (CSV upload, triage + selective deep dive)
BDR uploads 500 accounts from ZoomInfo/Demandbase. System runs lightweight triage on all 500 (~30 seconds each, ~$2 each = ~$1,000). Scores and ranks: 50 hot (competitor search vendor + high traffic), 100 warm (right vertical), 350 cold. BDR selectively triggers full audits on hot accounts.

---

## VI. VOICE INTERFACE

### Architecture: Dual-Agent Voice RAG
Based on 2026 state-of-the-art from Gemini research:
- **Slow Thinker Agent:** Predicts the user's next question, pre-fetches data from PostgreSQL into an in-memory semantic cache
- **Fast Talker Agent:** Queries the cache in <1ms, responds in <500ms for human parity
- **Grounded in verified data:** Voice agent ONLY speaks from module_executions table data with evidence tiers. Never hallucinates. Can say "I don't have verified data on that."

### Use Cases
- "What search vendor does Dell use?" → Instant answer from intel-techstack output
- "How does Dell compare to HP on search quality?" → Pulls from competitive benchmark matrix
- "Give me my 60-second pre-call brief for the Dell meeting" → Synthesizes top findings into audio briefing
- "Run a full audit on dell.com" → Triggers Temporal workflow via voice command

### Cost
Retell AI at $0.07/minute. A typical 5-minute interaction = $0.35. Annual cost for a team of 50 AEs using it 3x/day: ~$9,500/year.

---

## VII. LAYERED DELIVERY FORMAT

Critical insight from ChatGPT research: "Sales teams will not consume a 30-page benchmark even if it is excellent." Delivery must be layered — 5 levels of depth from the same underlying data:

| Level | Format | Audience | Time to Consume |
|-------|--------|----------|----------------|
| 1 | **Slack notification** | BDR/AE | 5 seconds |
| 2 | **One-paragraph summary** | AE pre-meeting glance | 30 seconds |
| 3 | **One-page brief** | AE meeting prep | 2 minutes |
| 4 | **Full audit report** | SE deep dive | 15 minutes |
| 5 | **Competitive benchmark** | Strategic deal team | 30 minutes |

All five levels are generated automatically from the same module_executions data. No separate workflow per level.

---

## VIII. ARCHITECTURE FOR DUAL USE

### Core Platform (Industry-Agnostic)
All 20 modules. All data sources. The orchestrator. The evidence system. The voice interface. The UI. The API. This is the product.

### Plugin Layer (Business-Specific)
- **Algolia plugin:** Search audit methodology (20-step browser test), Algolia case study matching, Golden Angle detection, Algolia-branded deliverable templates
- **Future: CRM vendor plugin:** CRM audit methodology, Salesforce/HubSpot case studies, CRM-specific scoring
- **Future: E-commerce platform plugin:** Platform migration assessment, commerce-specific benchmarks

When Prism is sold to another B2B SaaS company, they get the core platform and build (or we build) their domain-specific plugin. The core never changes. The plugin is where vertical expertise lives.

---

## IX. UNIT ECONOMICS

### Per-Audit Cost Breakdown (Full Audit with Competitive Benchmark)

| Cost Component | Per Audit |
|---------------|-----------|
| Perplexity API (company profile + competitors + news + exec research) | $5.00 |
| BuiltWith API (prospect + 3 competitors × ~4 calls) | $2.00 |
| SimilarWeb API (prospect + 3 competitors × 15 calls) | $3.00 |
| Apify actors (LinkedIn jobs + profiles × 4 companies) | $10.00 |
| Yahoo Finance + SEC EDGAR (public company financials) | $0.00 |
| Claude API — enrichment (Sonnet, ~15 calls) | $1.50 |
| Claude API — synthesis (Opus, ~8 calls) | $4.00 |
| Claude API — factcheck evaluator (Opus, ~5 calls) | $2.50 |
| **Subtotal: raw API costs** | **$28.00** |
| Buffer for retries/failures (+30%) | $8.40 |
| Infrastructure amortization | $5.00 |
| **Total loaded cost per full audit** | **~$42** |
| **Rounded up for margin and contingency** | **$50** |

### Quick Lookup: ~$2 (company + techstack + traffic only)
### Bulk Triage: ~$3 per account (lightweight collection)

### Infrastructure Fixed Costs (Monthly)

| Component | Monthly Cost |
|-----------|-------------|
| Railway hosting (API + Worker) | $75 |
| PostgreSQL (managed) | $30 |
| Redis (managed) | $20 |
| Temporal Cloud | $200 |
| Cloudflare R2 storage | $10 |
| Langfuse (observability) | $50 |
| Clerk (auth) | $0 (free tier) |
| Vercel (frontend) | $0 (free tier) |
| **Total infrastructure** | **~$385/month** |

### API Subscriptions (Monthly)

| Service | Monthly Cost |
|---------|-------------|
| Perplexity API | $200 |
| BuiltWith Pro | $500 |
| SimilarWeb API | $400 |
| Apify | $150 |
| Claude API | Usage-based (~$400/mo at 50 audits) |
| **Total API subscriptions** | **~$1,650/month** |

### Total Annual Run Rate
Infrastructure: $4,620/year
API subscriptions: $19,800/year
**Total: ~$24,500/year** (at 50 audits/month)

---

## X. PRODUCTIZED PRICING

Based on deep research market comps (Clay at $149-$800/mo, 11x at $900-$5,000/mo, ZoomInfo at $15-40K/yr):

| Tier | Price | Includes | Target Buyer |
|------|-------|---------|-------------|
| **Starter** | $200/seat/mo | Unlimited quick lookups, 5 full audits/mo, basic deliverables | Individual BDR |
| **Professional** | $600/seat/mo | 25 full audits/mo with competitive benchmark, all deliverables, voice interface, CRM integration | AE team |
| **Enterprise** | $1,200/seat/mo | Unlimited audits, custom methodology, dedicated support, custom benchmarking, API access | Sales org |

**Gross margin at Professional tier:** ~85% ($600/mo revenue, ~$90/mo cost at 25 audits)

**Revenue projections:**
- 10 customers × Pro tier = $72K ARR
- 50 customers × Pro tier = $360K ARR
- 100 customers × mixed tiers = $600K-$1M ARR

---

## XI. THE DATA MOAT

Every audit Prism runs makes the platform smarter. After 100 audits across footwear companies, Prism knows:
- Average search quality score in footwear: 4.2/10
- Most common search vendor in footwear: Elasticsearch DIY (43%)
- Average digital revenue share: 22%
- Most common missing capability: NLP search (87% of companies)

These vertical benchmarks — derived from real data, not surveys — become a competitive advantage no new entrant can replicate without running hundreds of audits. They also become a sellable asset: "What does the typical B2B manufacturing tech stack look like?" is a question Forrester charges $80K+/year to answer from survey data. Prism has real data.

---

## XII. CONNECTION TO COE

### Prism Is Not One POC — It Is 20 Products

When presenting the CoE business case, Prism should be presented as 20 distinct AI-powered capabilities:

| # | Capability | What It Replaces | Annual Cost Replaced |
|---|-----------|-----------------|---------------------|
| 1 | Company intelligence engine | Clearbit + Crunchbase subscriptions | $50K |
| 2 | Technology detection platform | BuiltWith subscription | $6K |
| 3 | Traffic intelligence system | SimilarWeb subscription | $12K |
| 4 | Competitive intelligence platform | Klue/Crayon subscription | $45K |
| 5 | Financial intelligence (public) | Bloomberg/Capital IQ seat | $25K |
| 6 | Financial intelligence (private) | PitchBook subscription | $20K |
| 7 | Executive intelligence system | Manual analyst work | $15K |
| 8 | People intelligence & buying committee mapper | ZoomInfo + LinkedIn Sales Nav | $25K |
| 9 | Social signal monitoring | Sprout Social | $5K |
| 10 | News intelligence | Contify | $8K |
| 11 | Partner intelligence | Manual + Crossbeam | $10K |
| 12 | Industry benchmarking | Baymard/Forrester subscription | $10K |
| 13 | Test methodology engine | SE expertise (time cost) | $15K |
| 14 | Digital experience auditor | Baymard custom audit | $200K |
| 15 | ROI modeling engine | Financial consulting | $50K |
| 16 | Sales methodology generator | Sales consulting | $25K |
| 17 | Report & deliverable engine | Agency work | $30K |
| 18 | ABX campaign generator | Agency campaigns | $10K |
| 19 | 20-dimension verification system | No equivalent | Priceless |
| 20 | Vertical insights engine | Forrester/Gartner benchmarks | $80K |
| | **TOTAL REPLACED** | | **$640K+/year** |

**The CoE pitch:** "In three months, with no budget and no dedicated team, the CoE prototype built 20 AI-powered intelligence capabilities that would cost $640K+ per year if purchased separately. The total investment to run them: $24K per year. That's a 26:1 return before counting a single closed deal."

### How Prism Feeds Every CoE Use Case

The same module architecture powers all 7 CoE departments:
- **Sales/BDR:** Full Prism audit → meeting prep, competitive benchmark, ABX campaigns
- **Marketing:** intel-company + intel-traffic + intel-industry → micro-personas, whale account activation
- **Partnerships:** intel-partner + intel-techstack → co-sell packages for SI partners
- **Customer Success:** intel-hiring + intel-news + intel-financial → churn signal detection
- **Product:** intel-industry + audit-browser → Gong transcript analysis by vertical
- **Competitive Intel:** intel-competitors + insights-engine → always-on competitive monitoring
- **Support:** intel-techstack + audit-browser → Zendesk pattern analysis by tech stack

The architecture is one. The applications are seven. The budget ask is one.

---

## XIII. BUILD PLAN

### Phase 0: Foundation (Week 1-2)
Infrastructure + first module. Docker Compose, PostgreSQL, Redis, Temporal, FastAPI, core contracts, intel-techstack module, integration test.

### Phase 1: Intelligence Modules (Week 3-6)
All 13 intelligence modules converted from existing Python scripts. Each with Pydantic schemas, Instructor-powered enrichment, validators, tests.

### Phase 2: Synthesis + Deliverables (Week 7-8)
Business case, sales plays, report assembly, ABX campaign, deliverable renderer, S3 storage.

### Phase 3: Browser Audit (Week 9-10)
Visual agent (Playwright + Claude Vision), 20-step protocol as config, WAF handling, competitor comparison testing.

### Phase 4: Factcheck (Week 11-12)
Temporal child workflow, claim registry, parallel verification, GAN-inspired Evaluator pattern with PydanticAI.

### Phase 5: Frontend (Week 13-16)
React dashboard, Clerk auth, audit list/detail, real-time progress (SSE), account intelligence view, admin panel.

### Phase 6: Voice + Polish (Week 17-18)
Retell AI integration, Dual-Agent Voice RAG, Slack integration, CRM write-back.

### Phase 7: Production (Week 19-20)
Rate limiting, RBAC, Langfuse tracing, Sentry monitoring, CI/CD, Temporal Cloud migration.

---

## XIV. COMPETITIVE LANDSCAPE SUMMARY

Based on deep research across 500+ sources (March 2026):

| Capability | Prism | Clay | ZoomInfo | 6sense | Klue | Gong | Baymard |
|-----------|-----|------|----------|--------|------|------|---------|
| Multi-source data aggregation | ✅ | ✅ | ✅ | Partial | ❌ | ❌ | ❌ |
| Evidence grading per claim | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Competitive experience benchmark | ✅ | ❌ | ❌ | ❌ | Partial | ❌ | ✅ (UX only) |
| Live website search audit | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Earnings call intelligence | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ (own calls) | ❌ |
| Buying committee mapping | ✅ | Partial | ✅ | ✅ | ❌ | ❌ | ❌ |
| ROI model generation | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| MEDDPICC playbook generation | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| ABX campaign from research | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Verification/factcheck gate | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Voice-native interface | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Vertical benchmarking engine | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (UX only) |
| **Price** | **$600/mo** | **$800/mo** | **$25K+/yr** | **$60K+/yr** | **$30K+/yr** | **$50K+/yr** | **$9.5K/yr** |

**Prism's positioning:** More comprehensive than any single tool. More affordable than the sum of parts. The only platform with comparative benchmarking + evidence grading + full package generation.

---

## XV. LONG-TERM STRATEGY

### Year 1 (2026): Build at Algolia
Build Prism under the CoE. Prove ROI with 500 whale account audits. Document everything. Accumulate vertical benchmarks. Build the team (2 people).

### Year 2 (2027): Expand or Launch
Three paths, each viable:
- **Path A:** Expand CoE into profit center. License Prism methodology to Algolia customers and partners.
- **Path B:** Leave Algolia. Launch Prism as standalone SaaS. First customers: mid-market B2B SaaS companies (500-2,000 employees) with 50+ person sales teams.
- **Path C:** Become fractional Chief AI Officer. Consult for companies building AI CoEs, using Prism as the reference implementation.

### The Career Thesis
Every tool the CoE builds at Algolia, every module that ships, every audit that proves ROI — it all compounds. After 18 months, the portfolio is: 20 AI-powered products built and proven, quantified ROI across 7 departments, a productizable platform architecture, and deep expertise in AI CoE methodology. That portfolio is worth multiples of any salary, whether deployed as a company, a consulting practice, or a senior executive role.

---

*This document is the single source of truth for Prism. It incorporates all architectural decisions, all research findings, all strategic planning from March 29-30, 2026. It should be referenced by every Claude Code session, every pitch document, and every future planning conversation.*
