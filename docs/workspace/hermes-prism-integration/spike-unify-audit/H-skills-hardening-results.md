# H — Skills Hardening Results (6-cluster workflow, 2026-06-28)

Workflow `wf_9a559d5c-d9b`: 6 cluster agents, 848K tokens, 309 tool-uses, ~14 min. All implemented + tested in the arijit-skills repo. **Verified independently before commit:** 23/23 changed/new .py py_compile OK; audit-browser.js node --check OK; 153 pass / 1 fail (pre-existing `test_generate_finding_cards`, missing fixture dir, not in change set).

## What changed, by cluster

**A — ROI & scoring math** (the #1 fabrication fix)
- Wired the orphaned `calculate-roi.py` → new `--components` mode computes all 6 ROI components × 2 scenarios deterministically; business-case SKILL.md now MANDATES the script, LLM supplies only labeled assumptions. (BUG-3)
- Wired orphaned `calculate-score.py` into report scoring (matches generate-audit-data.py formula). (BUG-3)
- BUG-5 overwrite guard in `collect-financials.py` (company_type marker, exit 2 on cross-type clobber, --force backs up).
- 33 tests pass.

**B — Search-vendor truth + partner**
- `detect-search` is now the canonical vendor oracle for techstack Layer-3 + competitor detection (new `map-detect-search.py` bridge → canonical JSON; BuiltWith demoted to secondary agreement signal). Proven live on petsmart.com (Algolia ACTIVE, indexes extracted).
- BUG-1 fixed: partner-intel SI discovery is now genuinely dynamic (candidates derived from prospect signals; removed the hardcoded EPAM/Publicis/Deloitte/Accenture/IBM query roster that made other SIs invisible).
- 12 mapper tests pass.

**C — Financial/investor grounding + industry**
- BUG-2 fixed: industry 24-month staleness gate now applies on the WebSearch fallback path (`industry_fallback_filter.py`).
- Scout embedded ONLY for industry benchmark pages, WITH the F1 empty-markdown guard → falls back to WebFetch + flags degradation (never silently accepts empty md).
- `reconcile_financials.py`: unit-aware money parse + deterministic ±20%-of-median confidence tier (HIGH/MED/LOW) + min/median/max range (gets the "within 20%" judgment out of the LLM).
- `ground_quotes.py`: exact-substring grounding gate for investor quotes + pre-Jan-2025 recency reject (same hard-gate lesson as report-QA).
- 41 tests pass.

**D — Signals collectors + company enrichment**
- Wired orphaned `collect-hiring.classify()` → deterministic tier + ICP scoring + cross-layer role dedup. (BUG-3)
- **Scout F1 fix (live bug):** company-intel's already-embedded Scout silently returned empty md on Squarespace; now requests raw_html, detects empty-md, falls back to raw_html parse, flags `scout_degraded` LOUDLY + [OBSERVED] labels.
- Standardized first-class `collection_method` + loud (non-silent) degradation flags across news (Tavily→RSS) and social (APIFY_TOKEN-missing). Fixed a stale "[FACT — Google News via Apify]" label (Apify removed long ago).
- Verified against real live sources (Google News RSS returned 9 real articles, degraded-flagged).

**E — Synthesis & campaign** (writing left on the LLM)
- Built `generate-abx-json.py` (mirrors generate-audit-data.py): replaces ~120 lines of hand-run pseudocode; extracts email/LinkedIn/Loom copy into schema-valid `abx_sequence.touches[]`. Fixed a latent bug (video_script was empty / full Loom script wrongly in body) + Source-notes leakage.
- Email-3 financials now pull from `calculate-roi.py` output, not in-LLM arithmetic.
- `check-claim-traceability.py`: mechanical gate — every talking point must trace to a finding + exec quote; every query must carry a `Tests:` marker.
- 15 tests pass.

**F — Browser, gates & orchestration**
- BUG-6 fixed: generalized `audit-browser.js` (per-site selector/url-template/mode/queries as params) → per-company forks unnecessary; **25 abandoned forks quarantined to `_archive/`** (moved, recoverable, zero live refs).
- Shipped the mechanical factcheck/eval dimensions as a real script `factcheck_mechanical.py` (completeness, source-density, cross-file money consistency, no-fabrication, money spot-check, opt-in URL liveness); judgment dims stay LLM. Caught a real undersized scratchpad on a live Brooks Running audit.
- Orchestrator public/private routing now deterministic via `classify-public-private.py` (Yahoo Finance ticker/exchange/quote validation, not LLM WebSearch guess). Live-verified Costco→public, Nike→public, private retailer→private.

## Bugs fixed: BUG-1 (partner SI), BUG-2 (industry date leak), BUG-3 (dead scripts wired ×3), BUG-5 (financial overwrite guard), BUG-6 (browser forks). BUG-4 (committed keys) fixed earlier in commit aae33af.

## Residual / follow-ups
- Enforcement of "run the script" mandates is still LLM-side (SKILL.md instructions) — no post-gen diff harness wired. The verification gates catch violations only if the LLM runs them. A true CI harness over a sample audit is the next rigor step.
- `calculate-roi.py`'s revenue parser doesn't yet match the prose-style `08-financial-profile.md` in current production audits (parses canonical `- FY2025: $X.XB`/table only) — Email-3 wiring is correct but depends on that parser; harden the parser next.
- Scout F2 (PDF extraction empty) NOT fixed — needs a real PDF parser; financial/IR PDFs stay on Yahoo MCP + SEC EDGAR.
- Live WAF-bypass + tool-name-contract correctness only provable by real browser/`/v1/responses` runs on the box.
