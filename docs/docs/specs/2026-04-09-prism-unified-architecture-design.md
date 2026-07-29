# PRISM Unified Architecture Design Spec

**Date:** 2026-04-09
**Status:** Approved — ready for implementation planning
**Authors:** Arijit Chowdhury, Claude (Architect)
**Supersedes:** Original 20-module architecture with per-module Sonar + Gemini collectors

---

## 1. Executive Summary

This spec redesigns PRISM's entire module architecture around three core insights:

1. **Every module is an agent.** The config is the system prompt, the playbook is the user prompt, the Pydantic schema is the output contract, the structured APIs are the tools, and the ModuleExecutor is the harness. To create a new capability, write three files — never touch the executor.

2. **Research is separated from structuring.** Five research clusters powered by dual-provider deep research (Perplexity Agent API + OpenAI) conduct comprehensive investigation. Domain modules then consume that research, call their own structured APIs, cross-validate, and produce typed intelligence.

3. **Every data point has a citation or it doesn't exist.** The zero-hallucination principle is enforced at every layer: structured APIs provide VERIFIED-tier evidence, research findings carry source URLs, citation validation checks that URLs are real and contain the claimed information, and the factcheck evaluator adversarially verifies all claims.

**Budget:** $25/audit ceiling. Expected landing: $8-15 per full audit.

---

## 2. The Agentic Module Pattern

### 2.1 The Mapping

| Agentic AI Pattern | PRISM Component | File | Purpose |
|---|---|---|---|
| System Prompt + Tool Definitions | ModuleConfig | `config.py` | WHO the module is, WHAT tools it can access, constraints (cache TTL, timeout, priority, retry) |
| User Prompt | Playbook | `playbook.md` | WHAT to do, HOW to do it, dynamic variables (`{domain}`, `{competitors}`), merge strategy, citation requirements |
| Output Schema | Pydantic Models | `schemas.py` | WHAT SHAPE the answer takes. `extra="forbid"`, `Literal` types, field descriptions as LLM instructions |
| Tools | DataSourceClients | Shared clients | APIs: BuiltWithClient, SimilarWebClient, AgentAPIClient, ApifyClient, YahooFinanceClient, SECEdgarClient |
| Harness | ModuleExecutor | `core/executor.py` | Runs the agent. Same for every module. Loads playbook, calls tools, validates, caches. Generic, never changes. |
| Guardrails | Citation Validation | Executor post-processing | 3-tier: URL existence check, content verification (high-value claims), cross-source confirmation |
| Evaluation | Golden Fixtures + Rubric | `evals/` directory | CI for playbooks. Known-good outputs, scoring rubric, eval runner |

### 2.2 Module File Structure

```
modules/{module-name}/
├── config.py              # ModuleConfig — ~15 lines
├── playbook.md            # Research/structuring instructions — the intelligence
├── schemas.py             # Pydantic input + output models — the contract
└── tests/
    ├── test_schemas.py    # Schema validation tests
    └── test_playbook.py   # Playbook execution tests with fixtures
```

To create a new research capability: write these 3 files. Never touch the executor.

### 2.3 The Generic Executor

The ModuleExecutor is a Python class (~200-300 lines) at `core/executor.py`. It runs inside Temporal activities. The execution flow:

1. Check cache (module_executions table, TTL from config)
2. Load and resolve playbook (replace `{domain}`, `{competitors}`, `{upstream_data}`)
3. Read merged cluster findings (from research phase)
4. Call structured APIs as declared in config (BuiltWith, SimilarWeb, etc.)
5. Cross-validate research findings against structured API data
6. Merge multi-source data using playbook's merge strategy
7. Validate against Pydantic output schema
8. Run citation validation (3-tier)
9. Generate ClaimRegistry (for factcheck consumption)
10. Cache result in module_executions table
11. Return ModuleResult with output + evidence + cost metadata

The executor does not know what any module researches. It follows config (which clients), playbook (what instructions), and schema (what shape). Pure plumbing.

### 2.4 Playbook Format

```markdown
---
name: {module-name}
version: x.y.z
description: One-line description
cost_tier: pro-search | deep-research
execution_strategy: per-company | comparative | hybrid
composes: [upstream modules whose cache to read]
---

## Objective
What this module discovers and why it matters.

## Cluster Consumption
Which clusters to read, which Finding categories to filter on.

## Data Collection
### PRIMARY: {APIName}
What to query and what to extract from structured APIs.

## Structuring Instructions
How to merge cluster findings with structured API data.
Domain-specific inference rules.

## Merge Strategy
Per-field source priority and conflict resolution.

## Validation Rules
Cross-reference checks, required fields, evidence tier assignment.

## Supplementary Research (Gap-Filling)
Predefined gaps that authorize a targeted Agent API pro-search call.
```

### 2.5 ExecutionContext — Data Flow Between Modules

```python
class ExecutionContext(BaseModel):
    audit_id: UUID
    account_domain: str
    company_name: str                      # from seed
    industry: str                          # from seed
    is_public: bool                        # from seed (has ticker)
    competitors: list[CompetitorRef]       # from seed
    executives: list[ExecutiveRef]         # from seed
    cluster_findings: dict[str, list[Finding]]  # from extract+merge phase
    upstream_results: dict[str, ModuleResult]    # populated as modules complete
```

Temporal populates the context as phases complete. The executor resolves playbook template variables from the context.

---

## 3. Research Architecture

### 3.1 Five Research Clusters

Research is separated from domain modules. Five clusters run in parallel, each with two providers (Perplexity Agent API + OpenAI deep research) for cross-validation.

| Cluster | Domain | Key Sources | Recency Bias | Feeds |
|---|---|---|---|---|
| **A: Company & Competitive Landscape** | Business model, competitive positioning, industry trends, partner ecosystem, market position | Company websites, Wikipedia, Crunchbase, industry reports, news articles, analyst pieces | 12 months | intel-company, intel-industry, intel-partner, intel-competitors |
| **B: Financial & Investor Intelligence** | Revenue/margins/growth, earnings call quotes, 10-K insights, analyst consensus, M&A activity | Earnings transcripts, SEC filings, Yahoo Finance, analyst reports, financial news, investor presentations | 6 months | intel-financials, intel-investor |
| **C: Technology & Digital Experience** | Search technology, tech stack, migrations, UX quality, user reviews, architecture decisions | Tech blogs, developer forums, job postings, G2/Capterra reviews, app store reviews, conference talks | 12 months | intel-techstack, intel-traffic, intel-hiring (partial) |
| **D: People & Signals** | Exec statements, social sentiment, leadership changes, news, conference talks, podcast appearances | LinkedIn posts, Twitter/X, conference talks, podcasts, interviews, careers pages, Glassdoor, press releases | 3 months | intel-social, intel-hiring (partial), intel-news, intel-investor (exec quotes) |
| **E: Buying Signals & Intent Inference** | Hiring for search/ML, tech removals, budget signals, evaluation signals, competitive pressure, funding | Job postings, BuiltWith changes, funding news, conference talks, vendor comparison articles, RFP databases | 3 months | intel-hiring, intel-techstack (migration), synth-sales-plays (timing) |

### 3.2 Dual-Provider Strategy

Each cluster runs as two independent deep-research calls:
- **Perplexity Agent API** (`deep-research` preset) — Perplexity's own search index
- **OpenAI deep research** — Bing search

Different search engines surface different sources. The union of findings is richer than either alone. When both providers independently find the same data point, confidence is HIGH. When they conflict, the data point is flagged for domain module investigation.

**Asymmetric depth:** Research instructions specify 60% effort on the prospect (deep dive) and 40% on competitors (comparison-focused key data points).

### 3.3 Map-Reduce Synthesis

Raw deep research produces 40-70 pages per document (10 documents total = 300-400 pages). Direct consumption is impractical. The map-reduce pipeline:

**Step 1 — Extract (Map):** 10 parallel calls using a fast model (Claude Sonnet or Haiku). Each call extracts structured Findings from one research document.

```python
class Finding(BaseModel):
    id: str                                    # unique, traceable
    company: str                               # which company this applies to
    category: str                              # e.g., "revenue", "search_tech", "exec_quote"
    statement: str                             # the actual finding
    source_url: str                            # citation — REQUIRED, no URL = rejected
    source_date: Optional[date]                # when the source was published
    confidence: Literal["high", "medium", "low"]
    raw_quote: Optional[str]                   # verbatim quote if applicable
    provider: str                              # "perplexity" or "openai"
```

Findings are **immutable objects**. Once extracted, they flow through the pipeline unchanged. The citation chain from final output back to original source URL is always traceable.

**Step 2 — Merge (Reduce):** 5 parallel calls (one per cluster). Merge the two providers' findings:
- Deduplicate semantically equivalent findings
- Tag agreements: both providers found it → `confidence: "high"`
- Flag conflicts: providers disagree → `confidence: "low"`, flagged for module investigation
- Preserve all source URLs from both providers

**Output:** 5 merged cluster intelligence packages, each containing structured Findings with confidence scores.

### 3.4 Research Cost Estimate

| Component | Calls | Est. Cost |
|---|---|---|
| Seed (intel-company, pro-search) | 1 | $0.05 |
| Deep research (5 clusters × 2 providers) | 10 | $1.50-3.00 |
| Extraction (10 documents, fast model) | 10 | $0.30-0.50 |
| Merge (5 clusters) | 5 | $0.15-0.25 |
| **Research subtotal** | **26** | **$2.00-3.80** |
| Domain module API calls (BuiltWith, SimilarWeb, etc.) | ~15 | Subscription-based |
| Domain module structuring (Pydantic validation) | 12 | $0.50-1.00 |
| Synthesis + delivery | 4 | $1.00-2.00 |
| Factcheck | 1 | $0.50-1.00 |
| **Total per audit** | **~58** | **$4.00-7.80** |

Well within $25 budget ceiling. Structured API costs are subscription-based (BuiltWith, SimilarWeb) and not per-call.

---

## 4. Domain Module Architecture

### 4.1 Module Responsibilities

In the new architecture, domain modules do NOT conduct research. Their role:

1. **Consume** merged cluster findings (filtered by domain relevance)
2. **Call** structured APIs for VERIFIED-tier data (their own API calls)
3. **Cross-validate** research findings against structured data
4. **Draw domain-specific inferences** (the "so what" for their domain)
5. **Produce** Pydantic-validated output with evidence chain and claim registry
6. **Gap-fill** via playbook-authorized supplementary Agent API call if needed

### 4.2 Module-to-Cluster-and-API Ownership

| Module | Primary Cluster(s) | Structured APIs | Inference Domain |
|---|---|---|---|
| intel-company | A | (enriches seed) | Company identity and competitive landscape |
| intel-techstack | C | BuiltWith, SimilarWeb tech | Search vendor detection, tech comparison, migration signals |
| intel-traffic | C | SimilarWeb (all 11 endpoints) | Digital presence, engagement, SEO gaps |
| intel-financials | B | Yahoo Finance + SEC EDGAR (public) OR waterfall (private) | Financial health, growth trajectory, investment capacity |
| intel-investor | B, D | SEC EDGAR transcripts | Executive priorities, strategic direction, Said vs Found |
| intel-hiring | E | Apify LinkedIn Jobs + careers page WebFetch | Buying committee, org structure, build-vs-buy signals |
| intel-social | D | Apify LinkedIn/Twitter posts | Exec voice, sentiment, strategic priorities |
| intel-news | D, A | (cluster research is primary) | Urgency signals, leadership changes, recent events |
| intel-partner | A | Crossbeam (when available) | Partner ecosystem, co-sell opportunities |
| intel-industry | A, C | (cluster research is primary) | Vertical benchmarks, industry trends, whitespace |
| intel-competitors | ALL | (synthesis of all upstream) | Competitive positioning matrix, battle cards |
| intel-queries | (reads all above) | (none) | Test query generation for browser audit |

### 4.3 Public vs Private Company Branching

The intel-financials module branches based on `context.is_public`:

**Public companies:**
- Cluster B research + Yahoo Finance (VERIFIED) + SEC EDGAR (VERIFIED)
- Cross-validate research findings against structured financial data
- High confidence output with exact revenue, margins, analyst consensus

**Private companies:**
- Cluster B research (dual-provider) is the PRIMARY source
- Supplementary: Apify LinkedIn headcount (proxy), job posting volume (growth proxy)
- Future Phase 2: Crunchbase Pro API or Tracxn for structured funding data
- All figures labeled [ESTIMATE] with confidence scoring
- Revenue waterfall: research findings → funding data → headcount proxy → job volume proxy

### 4.4 Hiring Intelligence (Three-Source Cross-Validation)

The intel-hiring module exemplifies the cross-validation pattern:

- **Apify LinkedIn Jobs** → exact job listings with titles, descriptions, dates (VERIFIED tier)
- **Careers page WebFetch** → positions Apify missed (VERIFIED tier)
- **Cluster E research** → context for WHY they're hiring, org changes, budget signals (WEBSEARCH tier)
- Cross-validate: if Apify shows "Search Engineer" AND cluster research found "CTO announced search rebuild," that's a HIGH CONFIDENCE buying signal

### 4.5 Buying Signals & Intent (Cluster E)

**Detectable from public sources:**
- Job postings for search/relevance/ML roles (Apify + research)
- Technology removals/additions on BuiltWith
- Funding announcements (research + SEC EDGAR Form D)
- New executive hires — VP Digital, CTO, Chief Experience Officer (research + Apify)
- Conference/podcast statements about search/digital strategy
- Competitor adopted Algolia (BuiltWith Golden Angle detection)

**Not detectable without paid intent platforms ($30-100K/year):**
- Website visit tracking (ZoomInfo/Bombora/6sense)
- Content download tracking (marketing automation)
- Private RFP processes

**Each signal gets a timing score:**
- ACTIVE: evidence of current evaluation or investment
- EMERGING: early signals suggesting future investment
- LATENT: conditions are right but no active signal

---

## 5. Evidence & Citation System

### 5.1 Evidence Tier Hierarchy

| Tier | Sources | Confidence |
|---|---|---|
| VERIFIED | Government filings (SEC EDGAR), structured APIs (BuiltWith, SimilarWeb, Yahoo Finance), Apify direct scrape | Highest — authoritative, structured data |
| WEBFETCH | Agent API research where cited URL was fetched and claim was confirmed on the page | High — verified citation |
| WEBSEARCH | Agent API research with live URL (exists but content not verified) | Medium — plausible but unverified |
| ESTIMATE | Revenue proxies, headcount-based calculations, aggregator data | Low — labeled as estimate |
| NO_SOURCE | Any claim without a source URL | Rejected — does not enter the system |

### 5.2 Three-Tier Citation Validation

Built into the executor's post-processing, runs on every module output:

**Tier 1 — URL existence (all citations):** HEAD request to check URL is live. Dead URL → evidence drops to NO_SOURCE. Cost: near zero.

**Tier 2 — Content verification (high-value claims only):** Fetch the page, ask a fast model "Does this page contain evidence for this claim?" Verified → upgrade to WEBFETCH tier. Not found → drop to NO_SOURCE. Cost: ~$0.001 per check. Run on: revenue figures, executive quotes, technology detections, migration claims.

**Tier 3 — Cross-source confirmation (where structured API data exists):** Compare Agent API claim against BuiltWith/SimilarWeb/Yahoo Finance. Agreement → upgrade to VERIFIED. Conflict → flag, preserve both. Cost: zero (data already fetched).

### 5.3 Claim Registry

Every module auto-generates a ClaimRegistry as part of its output:

```python
class Claim(BaseModel):
    statement: str
    source_url: str
    evidence_tier: EvidenceTier
    module_origin: str
    field_path: str  # e.g., "competitor_scores.walmart.search_vendor"
```

The factcheck evaluator (Phase 7) consumes all claim registries for adversarial verification.

---

## 6. Synthesis & Inference Layers

### 6.1 Where Inferences Happen

**Domain modules** draw domain-specific inferences:
- "Revenue grew 18% but digital revenue grew 32% — digital acceleration makes search investment timely"
- "Walmart has NLP search, Costco does not — competitive gap that Algolia closes"

**Synthesis modules** draw cross-domain narratives:
- "Your CTO said customer experience is priority #1 (intel-investor), but your search scores 3/10 (audit-browser), while Walmart invested in NLP search last quarter (intel-techstack). Here's how Algolia bridges that gap."
- "Three of your four competitors have invested in search personalization. You risk falling behind."

### 6.2 Synthesis Modules as Playbooks

synth-business-case and synth-sales-plays follow the same pattern: config + playbook + schema. Their data source is the module cache (`FROM CACHE` pattern). The playbook instructions tell Claude how to synthesize cross-domain findings into narratives, ROI models, and sales plays.

---

## 7. Excluded from This Spec (Separate Design Sessions)

### 7.1 audit-browser
Completely independent from the research cluster architecture. Browser-tests the prospect with Playwright + Claude Vision. Research-tests competitors via Agent API. Launches after seed + queries. Requires its own design session for competitive benchmarking expansion.

### 7.2 audit-factcheck
Stays as custom code. Adversarial evaluator pattern — separate agent with raw evidence access. Not a playbook. Consumes ClaimRegistries from all upstream modules.

### 7.3 Eight Parked Gaps
See `Decisions/2026-04-08-gap-findings.md` in vault. Each requires dedicated design time:
1. Merge strategy implementation details
2. Rate limiter / priority queue for Agent API
3. Call strategy per cluster (resolved: clusters)
4. Citation validation implementation
5. audit-browser hybrid approach
6. Synthesis modules migration (resolved: yes, as playbooks)
7. Factcheck input standardization (resolved: ClaimRegistry)
8. Playbook evaluation framework (Phase 3)

---

## 8. Implementation Phases

### Phase 1: Prove the Pattern
- Build the generic ModuleExecutor
- Build the AgentAPIClient (thin wrapper)
- Build intel-company v2.0 using the new pattern (config + playbook + schema)
- Prove it produces equal or better results than the current implementation
- Validate: executor works, playbook resolves, Pydantic validates, citations check out

### Phase 2: Research Clusters + Domain Migration
- Implement the 5 research clusters with dual-provider calls
- Implement map-reduce extraction and merge pipeline
- Migrate existing intel modules to new pattern one at a time
- Each migration: replace collector/enricher/parser with playbook + cluster consumption
- Add structured API cross-validation to each module

### Phase 3: New Capabilities
- Add the 7 new research capabilities identified in brainstorming:
  1. Live competitive search benchmarking
  2. Executive intelligence mining
  3. Industry gap analysis
  4. Prospect pain signal detection
  5. Technology migration intelligence
  6. Partner ecosystem deep mapping
  7. Custom competitive battlecard generation
- Build playbook evaluation framework (golden fixtures + rubrics)

### Phase 4: Software Building Engine
- Build Developer Agent (follows CodingSOPs + module pattern template)
- Build QA Agent (follows TestingSOPs + schema contracts)
- Build Dispatcher Agent (reads TODO, assigns tasks, tracks progress)
- Automate module creation from playbook + schema specs

### Phase 5: Delivery Enhancements
- NotebookLM integration (delivery channel for AE consumption)
- Crunchbase/Tracxn integration (structured funding data)
- ZoomInfo/Bombora integration (first-party intent data, if budget allows)

---

## 9. Decisions Log

| # | Decision | Rationale |
|---|---|---|
| 1 | Unified module pattern: config + playbook + schema | Eliminates per-module boilerplate. Adding a capability = 3 files. |
| 2 | Perplexity Agent API as primary research engine | Managed runtime, 19+ models, built-in web search, structured output, $0.005/search |
| 3 | Dual provider (Perplexity + OpenAI) | Cross-validation, different search indices, provider resilience |
| 4 | 5 research clusters | Organized by research methodology/source type, not by module |
| 5 | Map-reduce synthesis | Research documents too large (70 pages) for direct consumption |
| 6 | Research-first, APIs-in-modules | Clean separation: clusters find intelligence, modules validate with authority sources |
| 7 | Keep BuiltWith, SimilarWeb, Yahoo Finance, SEC EDGAR, Apify | VERIFIED-tier evidence. Zero-hallucination principle requires authoritative validation. |
| 8 | Asymmetric competitor depth (60/40) | Prospect needs deep dive, competitors need comparison points |
| 9 | Playbook-authorized supplementary calls | Bounded gap-filling, not open-ended research |
| 10 | Private company waterfall | No structured API for private financials. Research + proxies + confidence scoring. |
| 11 | Buying signals from public sources | Intent platforms ($30-100K/year) are Phase 5. Public signals are actionable now. |
| 12 | Factcheck stays custom | Adversarial pattern can't be a playbook — that's the defendant judging themselves |
| 13 | Skills deprecated | PRISM absorbs all skill capabilities. Skills = read-only methodology reference. |
| 14 | $25/audit budget ceiling | Even at ceiling, orders of magnitude cheaper than manual research |
| 15 | Software building engine after proof of concept | Prove the pattern by hand before automating the factory |
| 16 | Immutable Finding objects | Citation chain integrity — every data point traceable to source URL |

---

## 10. Open Questions for Next Session

1. Specific playbook content for each of the 5 research clusters
2. Pydantic schema design for each domain module's output
3. Finding model field details and category taxonomy
4. Merge strategy implementation per module
5. Private company financial waterfall — does dual-provider research simplify the 6-source waterfall?
6. AgentAPIClient detailed design (streaming, error handling, retry logic)
7. Rate limiter implementation for parallel Agent API calls
8. intel-company v2.0 detailed design (the proof of concept)
