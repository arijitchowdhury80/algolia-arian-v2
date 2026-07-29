---
title: Unified Module Architecture v2.0 — The Agentic Pattern
date: 2026-04-09
status: decided
supersedes: v1.0 (2026-04-08 runtime-agnostic adapter pattern)
---

# Unified Module Architecture v2.0

## Core Insight
Every PRISM module IS an agent. Not metaphorically — structurally identical to the Anthropic-recommended agentic AI pattern.

## The Agentic Mapping

| Agentic AI Pattern | PRISM Component | File | What It Does |
|---|---|---|---|
| System Prompt + Tool Definitions | ModuleConfig | config.py | WHO the agent is, WHAT tools it can access, constraints (cache TTL, timeout, priority, retry) |
| User Prompt | Playbook | playbook.md | WHAT to do, HOW to do it, dynamic variables, merge strategy, citation requirements, execution strategy |
| Output Schema | Pydantic Models | schemas.py | WHAT SHAPE the answer takes. extra="forbid", Literal types, field descriptions = LLM instructions |
| Tools | DataSourceClients | Shared clients | APIs the agent can call: BuiltWithClient, SimilarWebClient, AgentAPIClient, ApifyClient, etc. |
| Harness | ModuleExecutor | core/executor.py | Runs the agent. Same for every module. Loads playbook, calls tools, validates, caches. Generic. |
| Guardrails | Citation Validation + Evidence Tiers | Executor post-processing | 3-tier: URL existence → content verification → cross-source confirmation |
| Evaluation | Golden Fixtures + Rubric | evals/ directory | CI for playbooks. Known-good outputs, scoring rubric, eval runner. |

## Module File Structure

```
modules/{module-name}/
├── config.py              # ModuleConfig — ~15 lines
├── playbook.md            # Research/structuring instructions
├── schemas.py             # Pydantic input + output models
└── tests/
    ├── test_schemas.py
    └── test_playbook.py
```

To create a new module: write 3 files. Never touch the executor.

## The Complete Pipeline

### PHASE 1: SEED (intel-company — thin, fast, ~30 seconds)
One Agent API pro-search call. Produces the identity card:
- Legal name, domain, HQ, employee count
- Business model / revenue model
- Industry / vertical classification
- Ticker + public/private flag
- Key URLs (website, careers, blog, newsroom, investor relations)
- Company LinkedIn URL
- Top 3-5 competitors (name, domain, LinkedIn URL)
- Executive team top 5-8 (name, title, personal LinkedIn URL, role classification)
- Recent headline

### PHASE 2: DEEP RESEARCH (5 clusters × 2 providers = 10 calls, parallel)
PURE research — no structured APIs, just web research.

**Cluster A: Company & Competitive Landscape**
Sources: company websites, Wikipedia, Crunchbase, industry reports, news
Covers: business model depth, competitive positioning, industry trends, partner ecosystem

**Cluster B: Financial & Investor Intelligence**
Sources: earnings call transcripts, SEC filings, Yahoo Finance, analyst reports
Covers: revenue/margins/growth, analyst consensus, 10-K risk factors, M&A

**Cluster C: Technology & Digital Experience**
Sources: tech blogs, developer forums, job postings, G2/Capterra reviews, app store reviews
Covers: search technology, tech stack, migrations, digital UX quality, architecture

**Cluster D: People & Signals**
Sources: LinkedIn posts, Twitter/X, conference talks, podcasts, interviews, news
Covers: exec statements, social sentiment, leadership changes, news, conferences

**Cluster E: Buying Signals & Intent Inference**
Sources: job postings, BuiltWith changes, funding news, conference talks, vendor comparison articles
Covers: hiring for search/ML, tech removals, budget signals, evaluation signals, competitive pressure

**Dual provider:** Perplexity Agent API + OpenAI deep research. Different search engines surface different sources. Cross-validation: if both find same data point → high confidence.

**Asymmetric depth:** Prospect gets 60% of research effort (deep dive). Competitors get 40% (comparison-focused).

### PHASE 3: EXTRACT + MERGE (Map-Reduce)
**Extract (map):** 10 parallel calls using fast model (Sonnet/Haiku). Each 70-page research document → structured Finding objects.

```
Finding = {
  company: str,
  category: str,
  statement: str,
  source_url: str (REQUIRED),
  source_date: Optional[date],
  confidence: "high" | "medium" | "low",
  raw_quote: Optional[str]
}
```

Findings are IMMUTABLE — once extracted, they flow through the pipeline unchanged. Citation chain is traceable.

**Merge (reduce):** 5 parallel calls (one per cluster). Merge Perplexity + OpenAI findings. Deduplicate, flag agreements (high confidence) and conflicts (needs investigation).

### PHASE 4: DOMAIN MODULES (parallel)
Each module:
1. Receives merged cluster findings (from research)
2. Calls its OWN structured APIs (BuiltWith, SimilarWeb, Yahoo Finance, etc.)
3. Cross-validates research findings against authority data
4. Draws domain-specific inferences
5. May make playbook-authorized supplementary call for predefined gaps
6. Produces Pydantic-validated output + evidence chain + claim registry

**Module → Cluster + API ownership:**
- intel-company: Cluster A + (enrichment of seed)
- intel-techstack: Cluster C + BuiltWith + SimilarWeb tech
- intel-traffic: Cluster C + SimilarWeb (all 11 endpoints)
- intel-financials: Cluster B + Yahoo Finance + SEC EDGAR (public) OR research waterfall (private)
- intel-investor: Cluster B + Cluster D + SEC EDGAR transcripts
- intel-hiring: Cluster E + Apify LinkedIn Jobs + careers page WebFetch
- intel-social: Cluster D + Apify LinkedIn/Twitter posts
- intel-news: Cluster D + Cluster A
- intel-partner: Cluster A + Crossbeam (when available)
- intel-industry: Cluster A + Cluster C
- intel-competitors: ALL clusters (competitive synthesis)
- intel-queries: generates test queries from all above

### PHASE 5: SYNTHESIS
- synth-business-case (reads all domain outputs, produces ROI model + Said vs Found)
- synth-sales-plays (reads all domain outputs, produces MEDDPICC + SPIN + objection handling)
- audit-report (assembles all findings into scored report)

### PHASE 6: DELIVERY
- campaign-abx (personalized outreach from all findings)

### PHASE 7: QUALITY GATE
- audit-factcheck (adversarial evaluator — stays custom, NOT a playbook)
- Consumes auto-generated ClaimRegistry from all upstream modules

### PHASE 8: BACKGROUND
- insights-engine (vertical benchmarking, fire-and-forget)

### SEPARATE TRACK
- audit-browser (completely independent, launches after seed + queries)
- Browser-tests prospect (Playwright + Claude Vision)
- Research-tests competitors (Agent API)
- Does NOT consume from research clusters

## Public vs Private Company Branching

**Public companies:**
- Cluster B research + Yahoo Finance (VERIFIED) + SEC EDGAR (VERIFIED)
- Cross-validate research against structured data
- High confidence output

**Private companies:**
- Cluster B research (dual provider) is PRIMARY source
- Supplementary: Apify LinkedIn headcount, job posting volume
- All figures labeled [ESTIMATE] with confidence scoring
- Waterfall: research findings → Crunchbase/Tracxn (Phase 2) → headcount proxy → job volume proxy

## Evidence Tier Hierarchy

1. Government filing (SEC EDGAR, Companies House) → VERIFIED
2. Verified third-party API (BuiltWith, SimilarWeb, Yahoo Finance) → VERIFIED
3. Agent API research with verified citation (URL exists + content confirmed) → WEBFETCH
4. Agent API research with live URL (URL exists, content not verified) → WEBSEARCH
5. Company self-reported (LinkedIn, press releases) → WEBSEARCH
6. Aggregator estimate (Crunchbase, PitchBook) → ESTIMATE
7. Agent API research without URL → NO_SOURCE (rejected, dropped)

## Buying Signals (Cluster E) — Source Methodology

Detectable from public sources:
- Job postings for search/relevance/ML roles (Apify + research)
- Technology changes on BuiltWith (removals, additions)
- Funding announcements (research + SEC EDGAR Form D)
- New executive hires (research + Apify LinkedIn)
- Conference/podcast statements about search/digital strategy
- Competitor adopted Algolia (BuiltWith Golden Angle detection)

NOT detectable (requires paid intent platforms):
- Website visit tracking (ZoomInfo/Bombora/6sense — $30-100K/year)
- Content download tracking (requires Algolia's marketing automation)
- Private RFP processes

Future Phase 2: Crunchbase Pro API or Tracxn for structured funding data.

## Key Design Principles

1. The playbook IS the module's identity — everything unique lives in playbook + schema
2. The executor never changes — adding a module = adding files
3. Pydantic is the contract enforcer — passed directly to Agent API as response_format
4. Conflicts are intelligence — preserved as structured data, not silently resolved
5. Every claim has a citation — no source URL = NO_SOURCE tier = dropped
6. Playbooks compose — modules read upstream cache via composes field
7. Research and APIs are independent — research first, APIs in modules, cross-validate

## Relationship to Orchestration

- Temporal manages WHEN (wave ordering, dependencies, parallelism, retries)
- ModuleExecutor manages HOW (load playbook, call APIs, validate, cache)
- Playbook manages WHAT (research methodology, quality rules)
- Clean separation — none knows about the others' internals
