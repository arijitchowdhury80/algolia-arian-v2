# Plan (v2): 6 Stub Intel Modules — Scriptify-First, Two-Track

**Date:** 2026-06-21 (rewritten after architecture review)
**Status:** DRAFT v2 — awaiting review before build
**Supersedes:** the v1 "pure-LLM playbook" plan (archived below in §10)

---

## 0. Why this was rewritten

The v1 plan would have added 6 more **pure-LLM** modules — each a single Perplexity call driven by a playbook. A code trace showed that is exactly the wrong pattern for PRISM's goal ("codify and scriptify as much as possible; use the LLM only when needed"). Three foundational gaps in the current v2 system make the naive approach worse than it looks:

| Gap | Evidence | Consequence |
|-----|----------|-------------|
| **G1 — `api_clients` is dead metadata** | `grep` across `prism_platform/` finds nothing that *reads* `config.api_clients`. The executor (`executor.py:98-170`) does: load playbook → one Perplexity call → parse. | BuiltWith/SimilarWeb/Yahoo/Apify are never called. "Use BuiltWith data" is just prompt text the LLM web-searches. We pay an LLM for facts a structured API returns for free. |
| **G2 — `composes` is dead** | `run_module` (`activities.py:98-103`) builds `v2_context` with only domain/company/ticker. It never loads `competitors`, `executives`, or any upstream module output. Only the bespoke intel-company / intel-hiring paths inject `upstream_results`. | `{competitors}`, `{executives}`, `{upstream_intel_*}` resolve to **empty** for every generic module. A "composing" module composes nothing. |
| **G3 — Wave 1 has no real ordering** | `workflows.py:372` runs all 13 modules via one `asyncio.gather`; the intel-company "gate" is checked *after* the wave. | intel-company runs concurrently with its dependents, so its output is never available to them during the wave. (You chose to split into sub-waves — but the split only helps once G2 is fixed.) |

**The good pattern already exists** in two modules and is what we copy:
- **`intel-hiring`** — 2-track: Track 1 = `fetcher.py` does a cheap httpx probe then **Scout** (Playwright) crawl of the careers page, *no LLM*; Track 2 = Perplexity only as fallback, with the crawled page injected into context.
- **`intel-company`** — 3-track: Scout crawl → Perplexity → synthesis LLM.

So this plan does foundation-first, then builds the 6 modules on the hiring pattern.

---

## 1. Decisions locked in this review

- **D14 — Search/LLM provider: keep Perplexity for the residual fuzzy layer.** It's the only wired provider, returns citations (Cardinal Rule 5), and hiring/company already use it. The win is *removing* LLM calls via scriptification, not swapping engines. Parallel.ai is **not** in the codebase (no client, no key) — revisit later as a drop-in behind the `AgentAPIClient` seam if the shrunken residual is still costly. SerpApi/Tavily keys exist in `config.py` but are unused.
- **D15 — Scriptify-first, two-track per module.** Every module gets a deterministic **Track 1 collector** (Scout / BuiltWith / Yahoo / Apify / static tables / pure Python) and an optional **Track 2 LLM** call only for the irreducibly fuzzy residual (narrative, quote extraction, relevance scoring). LLM is the exception, not the default.
- **D16 — Sub-wave split (your call).** Wave 1 splits into ordered sub-waves so upstream data is guaranteed available. Requires G2 fixed first to mean anything.
- **D17 — Revive `composes` and `api_clients` generically**, not with per-module if/elif branches in `activities.py` (won't scale to 13+ modules).

---

## 2. Foundation work (MUST land before the 6 modules)

### F1 — Hydrate context from `composes` (fixes G2)

In `run_module`, after building `v2_context` and before executing:
1. Load `competitors` and `executives` from intel-company's persisted output (accounts table or its cached `module_executions` row) → populate `v2_context.competitors` / `.executives`. This makes the **existing** `{competitors}` / `{executives}` template vars work for *all* modules.
2. For each name in `handle.config.composes`, fetch that module's cached output via `get_cached_result(name, domain)` and set `v2_context.upstream_results[name] = output`. This makes `{upstream_intel_company}` / `{upstream_intel_techstack}` resolve.

Failure to load an upstream is non-fatal (module degrades to independent research) — preserves current resilience.

### F2 — Generic collector seam (fixes G1)

Add an optional deterministic pre-fetch step, wired once, used by any module:
- Add `collector: CollectorFn | None = None` to `ModuleHandle` (mirrors the existing `post_execute` pattern).
- `CollectorFn = Callable[[ExecutionContextV2], Awaitable[dict[str, Any]]]` — returns structured data to merge into `context.upstream_results`.
- In `run_module`, after F1 hydration: `if handle.collector: v2_context.upstream_results.update(await handle.collector(v2_context))`. Wrap in try/except — collector failure is non-fatal, Track 2 still runs.
- Modules with no collector (pure-LLM, e.g. intel-industry) simply pass `collector=None`.
- This also lets us later fold the hiring/company bespoke branches into the generic seam (out of scope here, but the seam makes it possible).

`api_clients` becomes documentation of what a collector uses (still useful for health checks); the *real* call lives in the module's `collector.py`.

### F3 — Sub-wave split (fixes G3, implements D16)

In `workflows.py`, replace the single `(1, WAVE_1_INTEL)` entry with ordered sub-waves (each sub-wave runs its members in parallel; sub-waves run sequentially so prior outputs are in the DB for F1 to load):

```
WAVE_1A_SEED   = ["intel-company"]                              # seed — gate still aborts on failure
WAVE_1B_BASE   = ["intel-techstack", "intel-traffic",           # need only company
                  "intel-financial-public", "intel-financial-private",
                  "intel-news", "intel-hiring", "intel-social",
                  "intel-investor", "intel-industry", "intel-queries"]
WAVE_1C_DERIVED= ["intel-competitors", "intel-partner"]         # need techstack (from 1B)
```

- intel-queries composes intel-traffic → if we want its top-keywords input guaranteed, move it to 1C too. **Open decision Q1 (§9).**
- Keep the existing intel-company gate between 1A and 1B.

---

## 3. Per-module designs (scriptify-first)

Legend: **T1** = deterministic Track 1 (no LLM). **T2** = LLM residual (Perplexity), only the fuzzy part.

### 3.1 intel-competitors — ~80% scripted
- **T1 collector:** for each competitor (from `intel-company.competitors`), call **BuiltWith `domain-api`** → search vendor, ecommerce platform. Classify vendor against a known-vendor table (Algolia, Elasticsearch, Coveo, Bloomreach, Constructor, Searchspring, Klevu, Lucidworks, …). Set `is_algolia_customer`, `search_vendor_status`, `detection_source="builtwith"`. Compute `competitive_scenario` by rules (any competitor on Algolia → `golden`; prospect on Algolia → `defensive`; none → `offensive`; else `mixed`).
- **T2 LLM (small):** match Algolia case studies to the prospect's vertical (fuzzy) + write `competitive_landscape_narrative`. Case studies can come from a Scout crawl of `algolia.com/customers` filtered by vertical, falling back to Perplexity.
- **Strategy:** `comparative` (single T2 call with all competitor profiles in context). T1 loops BuiltWith per domain, then **one** LLM call.
- **Composes:** intel-company, intel-techstack. **Cost tier:** pro-search.

### 3.2 intel-industry — mostly LLM (justified)
- **T1:** none reliable. Vertical benchmarks + named analyst quotes + 2025-26 trends are open-web research with no structured API. (Optional: maintain a small URL list for Baymard/NRF and Scout-crawl them — deferred.)
- **T2 LLM:** Perplexity `pro-search` for benchmarks/trends/quotes with citations.
- This is the **one** module where LLM-by-default is correct. We accept it and say so.
- **Composes:** intel-company. **Cost tier:** pro-search.

### 3.3 intel-investor — collector-heavy + LLM extraction
- **T1 collector:** **Yahoo Finance MCP** (`get_stock_info`, `get_yahoo_finance_news`, `get_financial_statement`) for public companies → deterministic signals + financials + news feed. SEC EDGAR full-text search (deterministic API) → 10-K/10-Q filing URLs; Scout-crawl the MD&A / Risk Factors sections.
- **T2 LLM:** extract **verbatim** executive quotes from earnings transcripts + 10-K MD&A (fuzzy, needs reading long text), tag each with Algolia themes. Private companies: Perplexity for CEO/founder interviews.
- **Strategy:** `prospect-only`. **Cost tier:** `deep-research` (transcript reading). **Composes:** intel-company.

### 3.4 intel-partner — mostly scripted + small LLM
- **T1 collector:** cross-reference the prospect's detected stack (`intel-techstack` upstream) against a **static Algolia partner table** (Adobe, Salesforce Commerce Cloud, Shopify, SAP, commercetools, BigCommerce, … with integration-doc URLs). Pure dict lookup → `tech_partners` list. No LLM, no external API.
- **T2 LLM (small):** SI/agency relationships (e.g. "Accenture built their SFCC site") via Perplexity/Scout + `actionable_motions` narrative.
- **Strategy:** `prospect-only`. **Cost tier:** pro-search. **Composes:** intel-company, intel-techstack.

### 3.5 intel-social — collector via Apify + LLM scoring
- **T1 collector:** **Apify** actors scrape LinkedIn company posts + Twitter/X posts (deterministic retrieval). Read `company_linkedin_url` / `twitter_handle` from `intel-company` upstream JSON (these are **not** template vars — the collector reads `upstream_results`, see note below).
- **T2 LLM (cheap):** score each post for Algolia relevance + tag signals. First pass can be keyword rules; LLM only to refine borderline posts.
- **Strategy:** `prospect-only`. **Cost tier:** pro-search. **Composes:** intel-company.

### 3.6 intel-queries — near-zero LLM
- **T1 (pure Python):** generate the test-query set from product categories (intel-company) + top keywords (intel-traffic). Programmatic generation per query type: broad_category, specific_product, nlp_conversational, **typo_variant (algorithmic typo injection)**, synonym_colloquial, non_product_content, brand_subbrand, zero_results_gibberish (static). Compute `query_coverage` by counting.
- **T2 LLM (optional, tiny):** polish queries for naturalness only. Can ship without it.
- **Strategy:** `prospect-only`. **Cost tier:** pro-search (only if T2 used). **Composes:** intel-company, intel-traffic.

> **Template-var correction (carried from v1):** the playbook loader resolves a *fixed* set — `{domain}`, `{company_name}`, `{industry}`, `{ticker}`, `{is_public}`, `{competitors}`, `{executives}`, `{upstream_<module>}`. Variables like `{product_categories}`, `{sub_vertical}`, `{company_linkedin_url}`, `{twitter_handle}` **do not exist** and would survive as literal text. Modules read those from `{upstream_intel_company}` (full JSON) or from `upstream_results` inside their collector — never as bare placeholders.

---

## 4. Files per module

```
intel_<name>/
  __init__.py
  config.py        # ModuleConfig (api_clients now documents collector deps)
  schemas.py       # Pydantic output models (extra="forbid", frozen nested, *_narrative + domain)
  collector.py     # NEW — deterministic Track 1 (skip for intel-industry)
  playbook.md      # Track 2 LLM instructions (references {upstream_*} from collector + composes)
```

Plus shared: a small `partner_table.py` (static Algolia partner map) for intel-partner, and a vendor-classification table for intel-competitors (can live in their collectors).

---

## 5. Registry wiring

Add 6 blocks to `register_all_v2_modules()`. Modules with a collector pass `collector=<fn>`. Count goes 7 → 13.

---

## 6. Build order

1. **Foundation (sequential, tested):** F1 (composes hydration) → F2 (collector seam) → F3 (sub-wave split). Each with unit tests; F1/F2 verified against an existing composing case.
2. **Modules (parallel fan-out):** 6 agents, one per module, each writing config + schemas + collector + playbook on the locked pattern.
3. **Registry pass:** add 6 blocks.
4. **Verify:** `register_all_v2_modules()` → 13; each schema `model_validate` on a sample; each playbook resolves; collectors unit-tested with mocked clients.
5. **Regression:** existing 7 modules + workflow tests still pass.

---

## 7. What this does NOT cover
- Agent Studio trial (separate, browser-based).
- Postgres→Algolia sync.
- Waves 4–6 (insights, synthesis, report).
- audit-browser Temporal wiring.
- Folding hiring/company bespoke branches into the F2 collector seam (possible later, not now).

---

## 8. Acceptance criteria
- [ ] F1: a composing module receives populated `competitors`/`executives` and `upstream_results` (test with intel-company → a dependent).
- [ ] F2: `ModuleHandle.collector` runs before T2 and merges into `upstream_results`; failure is non-fatal.
- [ ] F3: Wave 1 executes 1A→1B→1C in order; intel-company gate preserved.
- [ ] All 6 modules: config + schemas + playbook (+ collector where designed).
- [ ] Each module's T1 collector has a real-company integration test (live calls, no mocks); pure-logic helpers have fast unit tests.
- [ ] intel-queries runs in Wave 1C (after traffic).
- [ ] `register_all_v2_modules()` reports 13.
- [ ] D14 recorded as an ADR (provider decision).
- [ ] No regressions in existing 7 modules or workflow tests.

---

## 9. Decisions resolved in review
- **Q1 — intel-queries → Wave 1C.** Runs after intel-traffic so top-keyword input is guaranteed. 1C = [intel-competitors, intel-partner, intel-queries].
- **Q2 — NO MOCKS.** Tests use **real companies with live API/Scout calls**, never fabricated data (see memory `feedback-no-mock-data-real-company-tests`). Data-gathering collectors → integration tests against a real domain. Pure-logic functions (vendor table, typo injection, partner-table lookup, rules, schema validation) → fast unit tests, no fabricated intelligence involved.

---

## 10. Archived: v1 plan summary (superseded)
v1 proposed 6 pure-LLM modules (3 files each, one Perplexity call per module, `api_clients` as inert metadata) with an "accept the parallel race" stance on Wave 1. Rejected because it (a) pays an LLM for structured facts, (b) leaves `composes` non-functional, and (c) the parallel race makes "composes" meaningless. Retained only as a record of the schema/field designs, which carry forward into §3 largely unchanged.
