# Crawl4AI — PRISM Fit Analysis
# Written: 2026-05-03

## What We're Replacing / Enhancing

### Current intel_company (working)
- Custom `BrowserClient`: httpx → Jina Reader → Playwright stub → Browserless stub
- Fetches leadership, IR, newsroom pages via regex link extraction
- Output is raw text blobs injected into Perplexity + Gemini synthesis prompts
- **Pain point**: text blobs → LLM must infer structure. No structured extraction.

### Current intel_hiring (stub — no fetcher yet)
- Has schemas (OpenRoleV2, HiringSignalSummary, HiringV2Output) ✅
- Has config ✅
- **Missing**: fetcher.py, executor.py — not built yet
- Was going to use Apify for job listing scraping
- **Apify cost**: ~$0.003/run + volume pricing = expensive at scale

## What Crawl4AI Gives Us

| Need | Crawl4AI Solution | Notes |
|------|-------------------|-------|
| Corporate website → executive team | LLMExtractionStrategy + ExecutiveTeam Pydantic | Handles unstructured layout |
| Careers page → job listings | JsonCssExtractionStrategy | Fast, no LLM cost |
| Paginated job boards (50+ listings) | BFSDeepCrawlStrategy + max_pages | Follows pagination |
| Investor Relations → 10K/10Q | Link extraction + PDF URL discovery | Get PDF URLs, fetch separately |
| Anti-bot protection | 3-tier anti-bot + proxy escalation | Better than raw httpx |
| JavaScript-rendered pages | JS execution + dynamic scroll | Handles React/Angular job boards |
| PRISM's Pydantic contract | LLMExtractionStrategy schema= | Already Pydantic-native |
| Async-first architecture | AsyncWebCrawler | Matches PRISM's async design |

## Cost Model

### Apify (planned for hiring)
- $0.003 per actor run
- 500 companies/month = 500 runs = $1.50 just to scrape
- More complex actors (pagination) = more runs
- Plus: Apify API key management, actor versioning, their infra costs

### Crawl4AI (proposed)
- Library: free
- LLM extraction: Gemini flash-lite (~$0.0001/1K tokens) — PRISM standard
- 500 companies: ~$0.05-0.15 total for LLM extraction calls
- **Estimated 90%+ cost reduction vs Apify for hiring intel**

## Architecture Decision Points

### Decision 1: Integration path for intel_company
**Option A**: Add Crawl4AI as Tier 4 of existing BrowserClient
- Pro: backward compatible, low risk
- Con: adds complexity to already multi-tier client

**Option B**: Add Crawl4AIFetcher as a parallel fetcher alongside BrowserClient
- Pro: clean separation, can A/B test quality
- Con: more code to maintain

**Option C**: Build Crawl4AIFetcher as a standalone service, gradually migrate
- Pro: cleanest long-term architecture
- Con: scope creep if we do it all at once

**Recommendation**: Option B for now — `Crawl4AIFetcher` as a parallel class
that `intel_hiring` uses natively (clean slate) and `intel_company` optionally uses.

### Decision 2: Deployment mode
**Option A**: Python library (pip install crawl4ai + crawl4ai-setup)
- Playwright browsers installed in the PRISM container
- Direct import, no network overhead
- Recommended — Docker is experimental in v0.8.x

**Option B**: Docker sidecar
- Crawl4AI docs say "not stable, may break with future releases"
- Skip for now

**Option C**: Crawl4AI Cloud API
- Beta, external dependency, cost
- Skip for now

**Recommendation**: Python library directly. Add to requirements.txt.

### Decision 3: Data storage for large crawl results
- Hiring intel = potentially 50-200 job listings per company
- Job listings change weekly → cache_ttl_days=7 (already in config)
- **Use existing PostgreSQL**: store as JSONB in module_executions.output
- No new storage layer needed — PRISM already has this pattern
- The `CacheMode.ENABLED` in Crawl4AI will also cache raw fetches in-memory/disk

### Decision 4: Which modules to build first
1. **intel_hiring fetcher** — clean slate, immediate value (Apify killer)
2. **intel_company enhancement** — add structured executive extraction on top of existing text blob
3. **intel_investor** — PDF/10K discovery via Crawl4AI link extraction

### Decision 5: Perplexity's new role
- **Before**: Perplexity = primary source for executive names/titles
- **After**: Perplexity = validation layer
  - Crawl4AI extracts structured data directly from source (authoritative)
  - Perplexity cross-checks/fills gaps (LinkedIn profiles, dates Crawl4AI missed)
  - Gemini synthesis reconciles both (same as today)
- Net: Perplexity call becomes more targeted, probably cheaper

## What We Need to Build

### Phase 1: Crawl4AI Foundation (1 session)
1. Add `crawl4ai` to requirements.txt
2. Create `prism_platform/crawl4ai/` package:
   - `client.py` — Crawl4AIFetcher wrapping AsyncWebCrawler
   - `types.py` — CrawlOptions, CrawlResult (PRISM-native types)
   - `schemas/` — Pydantic extraction schemas per use case
3. Unit tests with VCR cassettes

### Phase 2: intel_hiring Fetcher (1 session)
1. `prism_platform/v2/modules/intel_hiring/fetcher.py` using Crawl4AIFetcher
2. CSS schema for job listings
3. LLM extraction for executive-level roles
4. Tests

### Phase 3: intel_company Enhancement (1 session)
1. Add Crawl4AIFetcher as structured extraction layer
2. Replace text blob with `ExecutiveTeam` Pydantic object
3. Tests + migration

### Phase 4: intel_investor PDF Discovery (future)
1. Link extraction for IR pages → 10K/10Q PDF URLs
2. PDF text extraction
