# Assumptions — intel-hiring Scout Phase 4

## Value Assumptions

| # | Assumption | Confidence | If Wrong |
|---|---|---|---|
| V1 | Career page content injected into Perplexity's prompt materially improves hiring signal quality | Medium | Perplexity already finds the same data via web search; Track 1 adds latency with no quality gain. Mitigation: A/B test 20 accounts with/without Track 1 injection |
| V2 | Sales reps value live job posting citations in `hiring_narrative` | High | User research confirmed MEDDPICC tier mapping is the highest-value field; job titles are a close second |

## Feasibility Assumptions

| # | Assumption | Confidence | If Wrong |
|---|---|---|---|
| F1 | Scout (Crawl4AI Playwright) can successfully fetch most enterprise career portals (Workday, Greenhouse, Lever, custom portals) | Medium | Many career portals are Cloudflare-protected; Scout's stealth Playwright may not bypass all. Mitigation: Track 1 failure is non-fatal; fallback to Track 2 alone |
| F2 | `/careers` or `/jobs` path pattern covers >60% of company career portals | Medium | Some companies use entirely custom URL schemes (e.g., `apply.{domain}`, `hire.{domain}`). Mitigation: subdomain patterns + httpx probe with redirect-following cover most cases |
| F3 | LinkedIn redirect detection works reliably (final URL contains `linkedin.com`) | High | Scout returns `resp.metadata.url` as the final URL after all redirects. This is the canonical way to detect LinkedIn redirect. |
| F4 | crawl4ai 0.8.6 (installed) is compatible with Scout's 0.7.7-tested API surface | High | Scout unit tests all pass with 0.8.6. Pydantic deprecation warnings from crawl4ai internals only, not our code. |

## Viability Assumptions

| # | Assumption | Confidence | If Wrong |
|---|---|---|---|
| Vi1 | Track 1 Scout fetch adds acceptable latency (<30s per domain) | Medium | Career portals on heavy JS frameworks can take 20-40s to render fully. Timeout set to 20s per URL. If all 9 paths are tried and fail, total timeout could be 3+ minutes. Mitigation: cap at 3 path attempts before giving up; httpx probe first (fast) |
| Vi2 | Adding Scout as PRISM dependency doesn't create version conflict issues | High | Scout installed as editable package (`pip install -e`) in PRISM's uv venv. crawl4ai 0.8.6 co-exists cleanly with existing PRISM deps |

## Integration Assumptions

| # | Assumption | Confidence | If Wrong |
|---|---|---|---|
| I1 | `PlaybookLoader.resolve()` correctly substitutes `{upstream_careers_page}` when `context.upstream_results["careers_page"]` is set | High | PlaybookLoader uses `upstream_{key.replace('-','_')}` pattern — key `careers_page` → `upstream_careers_page`. Verified by reading PlaybookLoader code. |
| I2 | `run_module()` routing addition (`elif input.module_name == "intel-hiring"`) doesn't break existing modules | High | Existing `if "intel-company"` branch is unchanged; new `elif` branch catches `intel-hiring` before the generic fallback |
| I3 | `_run_intel_hiring_pipeline()` can reuse `ModuleExecutor` and `AgentAPIClient` without changes | High | Pattern is identical to `_run_intel_company_pipeline()` — same executor, same API, different playbook and context injection |

## Top 3 Riskiest Assumptions

### 🔴 Risk 1 (F1): Career portal JS render success rate
**What**: Scout may not bypass Cloudflare/Akamai protection on major enterprise career portals (Workday, SuccessFactors, Taleo).
**Evidence**: Enterprise HR platforms are known anti-bot targets. Crawl4AI's stealth mode handles most, but hardened Cloudflare Enterprise deployments remain a problem.
**Impact**: If >50% of enterprise career portals block Scout, Track 1 becomes noise rather than signal.
**Mitigation**: Track 1 failure is non-fatal — Perplexity still runs. Flag in pipeline health log so we can track fetch rate over time and tune.

### 🟡 Risk 2 (Vi1): Latency from exhaustive path probing
**What**: If Scout tries all 9 career paths and fails on each, total latency could exceed 3 minutes per account.
**Evidence**: Each Scout scrape with Playwright takes 10-30s. 9 attempts × 20s = 3 minutes worst case.
**Impact**: Temporal activity timeout exceeded; intel-hiring module fails.
**Mitigation**: (1) httpx probe first (fast, <2s each); (2) cap Scout attempts at 4 paths before giving up; (3) run paths concurrently with asyncio.gather with a semaphore.

### 🟡 Risk 3 (V1): Track 1 content improves signal quality
**What**: Perplexity's web search already indexes career portals. Injecting the same content via Track 1 may produce identical output.
**Evidence**: Perplexity sonar-pro has strong job search coverage. For high-traffic companies (Dell, Nike), Perplexity likely already has current data.
**Impact**: Track 1 latency with no quality improvement for high-profile accounts.
**Mitigation**: Risk is accepted for Phase 4. The real value shows for mid-market companies with lower web search index coverage.
