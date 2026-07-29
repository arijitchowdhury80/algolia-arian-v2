# PRD — intel-hiring Scout Phase 4

## Summary

Add Scout-based career page fetching (Track 1) to `intel-hiring` and implement Scout as the Tier 2 stealth browser in `BrowserClient`. Scout fetches a company's live career portal before Perplexity runs; the raw job listings are injected into the playbook as `{upstream_careers_page}`, grounding Perplexity's research in today's actual postings rather than cached aggregator data.

## Background

`intel-hiring` v2 was built as a single-track Perplexity call. The module's playbook tells Perplexity to search LinkedIn/Indeed/Glassdoor for open roles. This works but has a known weakness: Perplexity's web index lags reality by days to weeks.

Scout Phase 1 is now complete and smoke-tested (2026-05-04). Scout wraps Crawl4AI's Playwright browser with stealth patches. PRISM can import `ScoutCrawler` directly as a Python library (no HTTP overhead).

BrowserClient's Tier 2 (Playwright stealth) has been a stub since it was designed (2026-04-14). Scout fills that gap.

## Objective

**Goal**: `intel-hiring` produces hiring signals grounded in live career page data, with career page fetch rate ≥60% for real company domains.

**Key Results**:
1. Career page successfully fetched for ≥60% of test domains (10 real companies)
2. LinkedIn redirect correctly detected and flagged (`redirected_to_linkedin=True`) on 100% of LinkedIn-routed domains
3. `intel-hiring` end-to-end latency ≤90 seconds (p95) including Track 1 + Track 2

## Solution

### Components

**1. `prism_platform/browser/tier2_stealth.py`** — Replace stub with Scout

`fetch_stealth(url, options, proxy_url="") -> FetchResult`

Calls `ScoutCrawler().scrape(ScrapeRequest(url=url, use_js=True, timeout_ms=...))`.
Maps `ScrapeResponse` → `FetchResult`:
- `resp.metadata.url` → `FetchResult.url` (final URL after redirects)
- `resp.markdown` → `FetchResult.text`
- `resp.raw_html` → `FetchResult.html`
- `FetchTier.PLAYWRIGHT` always
- Content shorter than `options.min_content_length` → `is_bot_blocked=True`

`interactive_session` remains a stub (search audit Phase 5+).

**2. `prism_platform/v2/modules/intel_hiring/fetcher.py`** — New career page fetcher

```python
class HiringFetchResult(BaseModel):
    careers_page_content: str = ""
    careers_url: str = ""
    redirected_to_linkedin: bool = False

async def fetch_careers_page(domain: str, timeout: float = 20.0) -> HiringFetchResult
```

Strategy:
1. httpx-only probe on `/careers`, `/jobs` (cheap, no Playwright)
2. Scout (Playwright) on all 9 career path patterns
3. Scout on career subdomain patterns (`careers.{domain}`, `jobs.{domain}`)
4. LinkedIn redirect → `redirected_to_linkedin=True`, bail immediately
5. Return empty `HiringFetchResult` if all attempts fail (non-fatal)

Content truncated at 8,000 chars before injection.

**3. `prism_platform/v2/modules/intel_hiring/playbook.md`** — Add `{upstream_careers_page}`

Live Career Page Content section added at top of playbook, above the Research Mission. Perplexity is instructed to treat this as authoritative ground truth and fall back to web search if empty.

**4. `prism_platform/orchestrator/activities.py`** — 2-track pipeline for intel-hiring

```python
async def _run_intel_hiring_pipeline(
    input: RunModuleInput,
    handle: Any,
    v2_context: ExecutionContextV2,
    start_time: float,
) -> tuple[ModuleExecutorResult, dict[str, Any]]
```

- Track 1: `fetch_careers_page(input.domain)` → inject `careers_page` into `v2_context.upstream_results`
- If `redirected_to_linkedin=True`: log warning, continue (Perplexity still runs)
- Track 2: `ModuleExecutor.execute()` with `HiringV2Output` schema
- No Track 3 (no synthesis — ground truth is injected directly into Perplexity prompt)

`run_module()` routing updated:
```python
if input.module_name == "intel-company":
    ...
elif input.module_name == "intel-hiring":
    result, result_dict = await _run_intel_hiring_pipeline(...)
else:
    # generic single-track
```

### Acceptance Criteria

- **AC-1**: `fetch_stealth()` returns `FetchResult(tier_used=PLAYWRIGHT)` when ScoutCrawler succeeds
- **AC-2**: `fetch_stealth()` returns `FetchResult(error=...)` when ScoutCrawler raises exception
- **AC-3**: `fetch_stealth()` sets `is_bot_blocked=True` when content < `min_content_length`
- **AC-4**: `fetch_stealth()` uses `resp.metadata.url` as `FetchResult.url` (redirect tracking)
- **AC-5**: `fetch_careers_page()` returns `HiringFetchResult(careers_page_content=...)` when Scout finds career page
- **AC-6**: `fetch_careers_page()` returns `HiringFetchResult(redirected_to_linkedin=True)` when final URL contains `linkedin.com`
- **AC-7**: `fetch_careers_page()` returns empty `HiringFetchResult` when all attempts fail
- **AC-8**: `_run_intel_hiring_pipeline()` injects `careers_page` into `v2_context.upstream_results`
- **AC-9**: `_run_intel_hiring_pipeline()` runs Track 2 even when Track 1 returns empty result
- **AC-10**: Playbook resolves `{upstream_careers_page}` from `context.upstream_results["careers_page"]`
- **AC-11**: `HiringFetchResult` is a frozen Pydantic model
- **AC-12**: `BrowserClient` Tier 2 escalation now calls `fetch_stealth()` which invokes Scout (integration)

### Dependencies

- `scout.core.ScoutCrawler` — installed as editable package in PRISM venv
- `crawl4ai>=0.7.7` — installed (0.8.6 present, compatible)
- Existing: `prism_platform/v2/executor.py`, `ModuleExecutor`, `AgentAPIClient`
- Existing: `prism_platform/v2/pipeline_health.py`, `PipelineHealthLog`

## Assumptions

(From 03-assumptions.md)
- F1: Scout successfully fetches most career portals — Track 1 failure is non-fatal
- F4: crawl4ai 0.8.6 compatible — confirmed by Scout unit test suite
- I1: PlaybookLoader resolves `{upstream_careers_page}` correctly — verified by code inspection

## Release Plan

**v1 (this PR)**:
- All 4 components above
- 3-layer tests for tier2_stealth, fetcher, pipeline
- No changes to `HiringV2Output` schema (schema is frozen)

**Fast-follow**:
- Cap Scout path attempts at 4 (not 9) to reduce worst-case latency — currently mitigated by timeout
- asyncio.gather for concurrent career path probing
- Career fetch rate telemetry in PipelineHealthLog

## Open Questions

1. **Playwright install on PRISM's deployment environment**: `playwright install chromium` must run in the container. Check Dockerfile.
2. **Scout venv dependency in production**: editable install works dev; production needs `scout` packaged or path-mounted.
3. **Temporal activity timeout**: current `intel-hiring` timeout is 120s (from config). With Track 1, worst case is 120s for career fetch + 60s Perplexity = 180s. May need to increase to 180s.
