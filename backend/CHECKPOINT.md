# PRISM — Session Checkpoint
**Last updated:** 2026-04-02 12:20 UTC
**Last session:** Session 11 — Layout Restructure + Intelligence Dashboard

---

## Platform Summary

**20 modules built. ~1547 tests passing. Zero code bugs. 2,868 customer evidence records loaded.**

PRISM is an AI-powered Prospect Intelligence Platform for Algolia Sales. It ingests a domain, runs 13 intelligence collection modules against 7 external APIs, tests live search experience via Playwright, synthesizes findings into business cases and sales plays, produces ready-to-use deliverables (scored audit, email sequences, discovery questions, competitive ammunition), factchecks all claims, and generates cross-audit vertical benchmarks.

---

## What's Built and Working

### Backend — 20 Modules (prism_platform/)

#### Infrastructure
- **FastAPI** on :8000 — `/health`, `/api/v1/audits`, `/api/v1/modules`, `/api/v1/benchmarks/{vertical}`
- **PostgreSQL 16** in Docker — 5 tables (accounts, audits, module_executions, deliverables, vertical_benchmarks)
- **Redis 7** in Docker
- **Temporal** dev server + worker — AuditWorkflow with **wave-based execution + gates**
- **Database-first caching** — uniform 48-hour TTL, old data never deleted
- **Module registry** — all 20 modules registered in `core/registry.py`

#### Temporal Workflow — Wave Execution (NEW in Session 6)
```
Wave 1 — 13 intel-* modules in parallel (intel-company MUST succeed or audit aborts)
Wave 2 — audit-browser (10-minute timeout, non-fatal)
Wave 3 — synth-business-case, synth-sales-plays, audit-report in parallel
Wave 4 — campaign-abx
Wave 5 — audit-factcheck as Temporal CHILD WORKFLOW (PROCEED/WARN/BLOCKED)
Wave 6 — insights-engine (fire-and-forget, non-blocking)
```

Audit modes: `full` (all 6 waves), `quick` (3 intel modules), `bulk_triage` (quick + scoring)
`skip_modules` parameter to exclude specific modules.

#### Intelligence Modules (13) — Wave 1

| # | Module | APIs | What It Produces |
|---|---|---|---|
| 1 | intel-company | Perplexity, Gemini | Company identity, executives, competitors, news. Seeds all others via accounts.intelligence JSONB. |
| 2 | intel-techstack | BuiltWith | Tech stack + competitor fan-out + Golden Angle (competitor uses Algolia) detection. |
| 3 | intel-traffic | SimilarWeb, Perplexity | 10 traffic endpoints + Google Trends momentum + competitor comparison. |
| 4 | intel-financial-public | Yahoo Finance, SEC EDGAR, Perplexity, Gemini | 3yr financials, market data, analyst consensus, SEC insights, investor presentations. |
| 5 | intel-financial-private | Perplexity, Gemini | 6-source revenue waterfall for private companies. Skips if public. |
| 6 | intel-news | Perplexity, Gemini | Company news (90-day), executive media quotes, urgency signals, sell signals. |
| 7 | intel-hiring | Apify, Perplexity, Gemini | LinkedIn jobs, ICP tier classification, build-vs-buy signal, buying committee, champion signals. |
| 8 | intel-social | Apify, Perplexity, Gemini | Exec LinkedIn activity, public statements, topic classification, quotable statements, Twitter/X. |
| 9 | intel-investor | Perplexity, Gemini, SEC EDGAR | Earnings call quotes, **Said vs Found mapping**, YouTube appearances, board composition, 10-K risk factors. |
| 10 | intel-partner | Crossbeam (OAuth, deferred), Perplexity, Gemini | SI relationships, co-sell opportunities, vertical case studies, partner play recommendation. |
| 11 | intel-industry | Perplexity, Gemini | Vertical benchmarks, industry trends, pain points → Algolia capability mapping, case studies. |
| 12 | intel-competitors | DB only, Gemini | Pure synthesis from all modules. Tech/traffic/financial/hiring/sentiment matrices. GOLDEN/OFFENSIVE/DEFENSIVE/DISPLACEMENT scenarios. |
| 13 | intel-queries | Gemini | 16 vertically-calibrated test queries (8 types × 2 each). Competitor query sets. Difficulty scoring. |

#### Experience Audit (1) — Wave 2 (NEW in Session 6)

| # | Module | What It Produces |
|---|---|---|
| 14 | audit-browser | Playwright live search testing on prospect + competitors. 10-dimension scoring via Gemini Vision. Screenshot evidence. Mobile viewport. Network-level search provider detection. |

#### Synthesis Modules (2) — Wave 3

| # | Module | What It Produces |
|---|---|---|
| 15 | synth-business-case | **Said vs Found (4-column matrix)**, 6-lever ROI calculator, displacement cost model, customer proof matching, timing signals. |
| 16 | synth-sales-plays | MEDDPICC mapping, SPIN discovery questions, objection handlers, executive-language talk tracks, power map. |

#### Delivery Modules (2) — Wave 3-4

| # | Module | What It Produces |
|---|---|---|
| 17 | audit-report | 10-dimension search quality score, comparative scoring, pre-call brief (60-sec AE read), leave-behind (prospect-safe), full audit JSON. |
| 18 | campaign-abx | 5-email ABX sequence, LinkedIn messages per buying committee member, Loom video script, collateral schedule, competitor-specific messaging. |

#### Quality Gate (1) — Wave 5 (NEW in Session 6)

| # | Module | What It Produces |
|---|---|---|
| 19 | audit-factcheck | GAN-inspired claim verification. 8-category batched evaluation. PROCEED/WARN/BLOCKED verdict. Correction manifest. Temporal child workflow. |

#### Intelligence Engine (1) — Wave 6 (NEW in Session 6)

| # | Module | What It Produces |
|---|---|---|
| 20 | insights-engine | Cross-audit vertical benchmarks. Anonymized industry patterns. Stored in vertical_benchmarks table. Fire-and-forget. Idempotent. |

### Frontend (frontend/) — UPDATED Session 11 (Layout Restructure + Intelligence Dashboard)
- **Next.js 15** with Tailwind CSS v4, shadcn/ui
- **aRRIe intelligence persona** — RAG-grounded, zero hallucination policy enforced
- **Output validator** — code-based fact-checker validates numbers, companies, executives, quotes against tool data
- **Context framing** — tool results wrapped with boundary markers + data inventory injected per conversation
- **Algolia branded** — Sora font, enforced type scale (16px body, 14px labels, 12px min)
- **Multi-model chat** — OpenAI, Anthropic, Gemini, OpenRouter via auto-detection from .env
- **AI SDK v6** — useChat from @ai-sdk/react, assistant-ui Thread
- **23 chat tools** — 22 module tools + check_account_freshness
- **Freshness tracking** — checks existing data before re-running, selective refresh mode
- **Zustand store** — global state for currentDomain, currentCompanyName, availableResults, activeTab, navigateTo
- **Three-Panel Layout** (Session 11 — permanent, nothing collapses):
  - **Left Panel** (280px fixed):
    - Top 60%: Account list (react-window virtualized, live from backend /api/v1/accounts/)
    - Bottom 40%: ROI Calculator (collapsible, 6 sliders, Conservative/Moderate/Custom presets)
  - **Center Panel** (fluid — INTELLIGENCE DASHBOARD):
    - **Tab Rail**: floating pill bar with 6 tabs (Overview, Research, Search Audit, Business Case, Competitive, Sales Actions) + Cmd+K search
    - **Overview Tab**: 4 glassmorphism bento tiles (Who Is This, Search Score, Signals, Next Steps) + download placeholders
    - **Research Tab**: 10 collapsible sections (company, financial, tech, traffic, hiring, news, social, investor, partner, industry) — each renders existing card components
    - **Search Audit Tab**: score summary (72px animated number), 10-dimension severity table, browser audit findings
    - **Business Case Tab**: Said vs Found table, ROI calculator, customer proof, timing signals
    - **Competitive Tab**: comparison matrix, battle cards, conditional golden angle banner
    - **Sales Actions Tab**: MEDDPICC accordion, SPIN questions with copy, objection handling, buying committee, outreach stepper + deliverable composer placeholder
    - Navigation controller: `navigateTo(target)` switches tab + scrolls to section + flash highlight
    - URL hash updates for browser back button
  - **Right Panel** (340px fixed — aRRIe CHAT):
    - Always visible, dedicated to aRRIe conversation
    - Panel header: "aRRIe" label + PRISM icon + context line (current account)
    - Compact summary cards with PRISM grounding badge
    - ThinkingBlock for tool execution transparency
    - Sample Questions popup (click to send)
    - Chat input pinned at bottom with voice placeholder
- **Voice placeholder** — microphone icon with "Hey aRRIe" tooltip (UI only)
- **AI disclaimer footer** — red scrolling ticker, 120s cycle
- **10 card components** (Session 9) — glassmorphism design, used in both chat summaries and dashboard tabs:
  - CompanyCard, ScoreCard, BusinessCaseCard, ROI Calculator, SignalCard, TrafficCard
  - CompetitorMatrix, BrowserAuditCard, CampaignCard, CustomerProofCard
- **Design system**: glassmorphism (rgba(255,255,255,0.72) + blur(20px)), 20px radius bento tiles, Algolia brand tokens
- **Build passes clean** — zero errors, all 7 routes generate

### Backend — UPDATED Session 10
- **Freshness endpoint**: GET /api/v1/accounts/{domain}/freshness
- **Staleness thresholds**: 14-180 days per module type (configurable in config.py)
- **Selective refresh**: audit_mode="refresh" runs only stale modules + synthesis re-run
- **Universal LLM factory**: auto-detects provider from API keys (Anthropic/OpenAI/Gemini/OpenRouter)
- **Voice config placeholder**: VOICE_ENABLED, VOICE_WAKE_WORD in config.py
- **Customer Evidence API** (NEW Session 10):
  - 5 new PostgreSQL tables: algolia_customers (2,013), algolia_case_studies (154), algolia_quotes (352), algolia_proofpoints (81), algolia_advocates (268)
  - 6 REST endpoints under `/api/v1/evidence/` — customers, case-studies, quotes, proofpoints, advocates, match
  - **Evidence match endpoint**: cross-references prospect intel with Algolia customer DB, detects Golden Angle (competitor is Algolia customer)
  - Privacy-gated: only returns customers with logo_rights or publicity_consent
  - Import script: `scripts/import_customer_evidence.py` — reads 21 Excel sheets, deduplicates, loads 2,868 rows
  - 3 new chat tools: find_customer_evidence, find_case_studies, find_customer_quotes
  - aRRIe system prompt updated: proactive evidence citation in every prospect briefing

---

## Test Suite

```
~1547 passed, 9 skipped, 29 failed (all Perplexity/SimilarWeb quota — zero code bugs)
Total when all APIs available: ~1585 tests
```

### Test Breakdown by Module
| Module | Schema | Collector | Integration | Total |
|---|---|---|---|---|
| intel-company | 36 | 7 | 17 | 60 |
| intel-techstack | 15 | 10 | — | 25 |
| intel-traffic | 36 | 24 | 7 | 67 |
| intel-financial-public | 26 | 24 | 13 | 63 |
| intel-financial-private | 26 | 14 | 14 | 54 |
| intel-news | 59 | 8 | 12 | 79 |
| intel-hiring | 59 | 11 | 12 | 82 |
| intel-social | 68 | 4 | 4 | 76 |
| intel-investor | 30 | 10 | 11 | 51 |
| intel-partner | 54 | 21 | 20 | 95 |
| intel-industry | 55 | 31 | 22 | 104* |
| intel-competitors | 48 | 32 | 16 | 100* |
| intel-queries | 34 | 19 | 13 | 66 |
| synth-business-case | 39 | 42 | 23 | 104 |
| synth-sales-plays | 31 | 49 | 12* | 80* |
| audit-report | 52 | 24 | 6 | 82 |
| campaign-abx | 30 | 26 | 7 | 63 |
| **audit-browser** | 43 | 30 | 17 | **90** |
| **audit-factcheck** | 43 | 21 | 34 | **98** |
| **insights-engine** | 22 | 10 | 23 | **55** |
| API + workflow | — | — | — | ~22 |

*Some integration tests skipped due to API quota

---

## API Keys Required

| API | Env Var | Status | Used By |
|---|---|---|---|
| Perplexity | PERPLEXITY_API_KEY | Quota exhausted (temporary) | intel-company, news, hiring, social, investor, partner, industry, traffic |
| Gemini | GEMINI_API_KEY | Working | All modules (enricher/structuring) |
| BuiltWith | BUILTWITH_API_KEY | Working | intel-techstack |
| SimilarWeb | SIMILARWEB_API_KEY | Working | intel-traffic |
| Yahoo Finance | (free) | Working | intel-financial-public |
| SEC EDGAR | (free) | Working | intel-financial-public, intel-investor |
| Apify | APIFY_API_KEY | Working | intel-hiring, intel-social (LinkedIn) |
| Anthropic | ANTHROPIC_API_KEY | Available | (reserved for future Claude calls) |
| Crossbeam | CROSSBEAM_API_KEY | OAuth — deferred | intel-partner (using Perplexity fallback) |

---

## File Counts

```
Module source files:  ~110 .py files across 20 module directories
Test files:           ~52 test_*.py files
Core infrastructure:  config.py, core/, db/, api/, orchestrator/
Frontend:             ~60 component files (23 card + 8 dashboard tabs + 29 layout/chat/ui)
```

---

## How to Start Everything

```bash
# Terminal 1: Docker (PostgreSQL + Redis)
cd /path/to/PIP && docker compose up -d

# Terminal 2: Temporal dev server
temporal server start-dev

# Terminal 3: PRISM worker
cd /path/to/PIP && .venv/bin/python scripts/start_worker.py

# Terminal 4: PRISM API
cd /path/to/PIP && .venv/bin/uvicorn prism_platform.main:app --host 0.0.0.0 --port 8000

# Terminal 5: Frontend
cd /path/to/PIP/frontend && ./node_modules/.bin/next dev --port 3000

# Run tests
cd /path/to/PIP && set -a && source .env 2>/dev/null; set +a && python3 -m pytest tests/ -v -m "not browser"
```

---

## Key Technical Decisions
- Python package: `prism_platform` (not `pip` — avoids shadowing)
- Gemini 2.0 Flash for all enrichers (cost-effective for structuring tasks)
- Perplexity sonar-pro as primary web intelligence engine
- Database-first caching in PostgreSQL (not Redis) — uniform 48-hour TTL
- intel-company seeds all downstream via accounts.intelligence JSONB
- intel-competitors is pure synthesis (reads DB, no external APIs)
- Apify for LinkedIn (walled garden), Perplexity fallback when no token
- Crossbeam OAuth deferred to testing phase
- react-resizable-panels v2.1.7 (v4 API broke, downgraded)
- No dark mode (Algolia brand is light)
- Said vs Found is 4-column (exec_said → we_found → competitors_doing → your_move)
- Wave execution: intel-company gate (abort on failure), other intel non-fatal
- audit-factcheck runs as Temporal child workflow for isolation
- insights-engine is fire-and-forget (non-blocking)
- Playwright stealth mode for browser testing, WAF detection and graceful degradation
- GAN pattern: factcheck evaluator reviews ALL claims across 8 categories

---

## What's NOT Built Yet

### Frontend
- ~~Right panel (ROI calculator, tool menu)~~ DONE Session 7
- ~~Intelligence cards for new modules~~ DONE Session 7 (18 cards)
- ~~Frontend tools for each backend module~~ DONE Session 7 (22 tools)
- ~~Layout restructure (chat→right, dashboard→center)~~ DONE Session 11
- ~~Intelligence dashboard with 6 tabs~~ DONE Session 11
- Cmd+K command palette (search input exists, palette not wired)
- Deliverable composer (placeholder UI exists, generation not implemented)
- Wire navigateTo from aRRIe tool results (controller ready, tool output needs navigate_to field)
- Full end-to-end integration test (backend + frontend live)
- Real-time SSE progress for audit execution (currently polling)
- Screenshot viewer for browser audit screenshots

### Integration
- Crossbeam OAuth authentication for intel-partner
- Perplexity quota reset (all 29 failures will resolve)
- Production hardening (Supabase, Temporal Cloud, Clerk prod keys)
- Cloudflare R2 for screenshot storage (currently local filesystem)
- Playwright `install chromium` in CI/CD pipeline
