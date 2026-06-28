# Pre-Mortem — intel-hiring Scout Phase 4

## Scenario

It's 30 days after Phase 4 ships. The module is failing or producing poor results in production. What went wrong?

---

## Tigers (Real Risks — Evidence-Based)

### 🔴 T1: Temporal activity timeout exceeded (Launch-Blocking)

**What**: Scout tries all career path patterns serially. 9 paths × 20s timeout = 3 minutes worst case, plus Perplexity. Temporal activity timeout is 120s.

**Evidence**: Each Scout scrape with Playwright: 10-30s measured locally. httpx probe is <2s. But JS-heavy ATS portals (Workday, SuccessFactors) run 20-30s each. If 4 paths timeout: 80s for Scout + 60s Perplexity = 140s > 120s limit.

**Impact**: Temporal activity `ACTIVITY_FAILURE_TIMEOUT`, intel-hiring silently fails for those accounts.

**Mitigation**: httpx probe first (exits in 2s if 200 OK); stop Scout after first success; cap Scout at 3 paths if no httpx hit. Temporal activity timeout raise to 180s in config.

**Owner**: This codebase
**Decision Date**: Must be verified in Step 9 (verification) — run against 3 real domains and measure p95 latency.

---

### 🔴 T2: `fetch_careers_page()` blocks the event loop if `ScoutCrawler.scrape()` is not truly async (Launch-Blocking)

**What**: If `ScoutCrawler.scrape()` internally calls `asyncio.run()` or uses `run_until_complete()` at any nesting level, calling it inside a Temporal activity (which has its own event loop) raises `RuntimeError: This event loop is already running`.

**Evidence**: Crawl4AI's `AsyncWebCrawler.arun()` is properly async. But the `ScoutCrawler` wrapper may have synchronization points. Verified by reading `ScoutCrawler.scrape()` — it uses `await` throughout. Risk is low but not zero.

**Impact**: All intel-hiring runs crash with RuntimeError on first track 1 call.

**Mitigation**: Unit tests run with pytest-asyncio which validates async behavior. Integration test (step 28) will catch this before it ships.

---

### 🟡 T3: LinkedIn redirect detection misses edge cases (Fast-Follow)

**What**: Detection logic is `linkedin.com in resp.metadata.url`. Some companies use custom LinkedIn Career Pages hosted on `careers.linkedin.com/company/...` subdomains. Others redirect through an ATS that then redirects to LinkedIn — final URL may be `/jobs/view/...` not matching the domain check.

**Evidence**: LinkedIn URL patterns: `linkedin.com/jobs/`, `linkedin.com/company/`, `careers.linkedin.com/`. All contain `linkedin.com`. The intermediate ATS redirect case is real but rare.

**Impact**: `redirected_to_linkedin=False` when it should be True — Perplexity prompt does not get the warning context.

**Mitigation**: Non-critical. The flag is informational; Perplexity still runs. Track as fast-follow: add `careers.linkedin.com` pattern check.

---

### 🟡 T4: Playbook `{upstream_careers_page}` not resolving — empty prompt injection (Fast-Follow)

**What**: `PlaybookLoader.resolve()` maps `context.upstream_results["careers_page"]` to `{upstream_careers_page}`. If `upstream_results` key name or playbook placeholder name drift, the placeholder appears literally in the Perplexity prompt.

**Evidence**: PlaybookLoader verified by code inspection (I1 assumption). The key `careers_page` → `upstream_careers_page` pattern is the established convention (used in intel-company).

**Impact**: Perplexity sees `{upstream_careers_page}` as a literal string, not as a template error — it will treat it as content and produce garbage output.

**Mitigation**: Contract test (AC-10) validates this in step 28. If it fails, the error is loud and caught before ship.

---

## Paper Tigers (Overblown Concerns)

### PT1: Cloudflare blocks Scout on Workday portals

**Why overblown**: Track 1 is non-fatal. If Scout is blocked, `HiringFetchResult` is empty, Perplexity still runs. The fail-safe was designed into the architecture from day 1. Output degrades gracefully, not catastrophically.

### PT2: `HiringFetchResult` frozen model causes issues in pipeline

**Why overblown**: Frozen Pydantic models raise `ValidationError` on mutation attempts, which would be caught immediately in tests. The model is instantiated once per run and never mutated — frozen is correct.

### PT3: crawl4ai 0.8.6 (PRISM venv) breaks Scout import

**Why overblown**: All 70 Scout unit tests pass with 0.8.6. The only warnings are Pydantic deprecation messages from crawl4ai internals — none affect `ScoutCrawler.scrape()` behavior.

---

## Elephants (Unspoken Worries)

### E1: intel-hiring latency is now non-deterministic

**What**: Track 1 can take 2s (httpx success) or 30s (Scout Playwright) or 180s (all paths timeout). `hiring_signal_score` computation downstream sees wildly different response times. The audit UI may have a client-side timeout (e.g., 90s fetch) that kills the request before the module completes.

**Investigation needed**: Check the frontend polling interval and timeout on the audit card that triggers intel-hiring. If it's less than the new worst-case latency, the UI will show a stale/failed state even when the module eventually succeeds.

### E2: Two concurrent intel-hiring runs for the same domain step on each other

**What**: Temporal deduplication is at the workflow level, not the module level. If two audit runs start simultaneously for the same company, both call `fetch_careers_page()`, both spin up Playwright, both compete for the same browser resource.

**Investigation needed**: Check if `ScoutCrawler` uses a shared resource (browser pool) or creates a new browser per call. If shared, concurrent runs may deadlock or corrupt each other's state.

---

## Launch-Blocker Summary

| Tiger | Risk | Mitigation | Owner | Decision Date |
|---|---|---|---|---|
| T1: Activity timeout | Temporal activity fails for slow portals | Cap Scout at 3 paths; raise timeout to 180s | Codebase | Step 9 verification |
| T2: Event loop conflict | All intel-hiring runs crash with RuntimeError | Integration test catches this in Step 28 | Codebase | Step 28 (TDD RED) |
