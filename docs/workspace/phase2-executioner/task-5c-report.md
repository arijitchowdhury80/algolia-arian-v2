# Task 5c report — `claims.extract_claims` (mechanical claim extraction, closes Task 5b's flagged gap)

Status: **DONE**

3-line summary: Built `prism_platform/pipeline/claims.py` — `extract_claims(skill_output) -> tuple[str, ...]`, the `claims_fn` Task 5b's `make_batch_factcheck_fn` required with no default. Ground-truthed against `validate-json-schema.py` plus live inspection of 3 real complete audit workspaces: only 4 of the 16 pipeline skills (`algolia-intel-company`, `algolia-intel-investor`, `algolia-intel-industry`, `algolia-audit-report`) actually own a claim-bearing structure — the other 12 correctly return an empty tuple, not a guessed heuristic. 17 new unit tests pass (285 total in `tests/pipeline/`, up from 268, zero regressions), `ruff`/`ruff format`/`mypy --strict` clean on both new files. Measured real claim counts across 3 real audits (Dell/jbl/lululemon) and used them to correct Task 5b's cost-control estimate downward (~21-32 factcheck calls per audit, not the original 80-320 guess).

Report path: `docs/workspace/phase2-executioner/task-5c-report.md`

---

## What was built

### `prism_platform/pipeline/claims.py` (new file)

`extract_claims(skill_output: gate.SkillOutput) -> tuple[str, ...]` — purely mechanical, no LLM call. For a given `skill_output.skill_name`, looks up a per-skill extractor function in a table; skills with no entry return `()` immediately.

**Ground truth used** (per the brief's explicit instruction — read in full, not just grepped):
- `~/.claude/skills/algolia-search-audit/scripts/validate-json-schema.py` (478 lines, read in full) — the authoritative list of which JSON fields carry a checkable claim+citation pair.
- `~/.claude/skills/algolia-search-audit/scripts/check-claim-traceability.py` — confirmed the project's existing convention for "what counts as a claim" (a factual assertion paired with a citation), used for Cluster E (playbook/queries), not directly reused here since it operates on markdown, not JSON.
- **Live inspection of 3 real, complete audit workspaces** (not synthetic guesses): `/Users/arijitchowdhury/prism-data/audits/{Dell,jbl,lululemon}/` and several more in `~/Dropbox/AI-Development/Algolia Search Audit/{BritishAirways,Michael Kors,DSW,Nike,...}/` — used to confirm real field names, real (drifted) file-naming conventions, and real slug-to-filename mapping.

**The real, complete field-name table** (confirmed by reading actual JSON, not assumed from the brief's 4 example bullets):

| Skill | File | Structure | Fields used |
|---|---|---|---|
| `algolia-intel-company` | `research/01-company-context.json` | `portfolio_brands[]` | `name`, `domain` |
| `algolia-intel-investor` | `research/11-investor-intelligence.json` | `media_quotes[]` | `speaker`, `title`, `quote` |
| `algolia-intel-industry` | `research/industry-intel.json` **or** `research/06-industry-intel.json` | `benchmarks[]` | `metric`, `value`, `context` |
| `algolia-audit-report` | `deliverables/*-audit-data.json` (globbed, not slug-computed) | `executives[]` | `name`, `title`, `quote` |
| `algolia-audit-report` | (same file) | `intelligence_signals[]` | `title`/`badge_label` + `detail`/`quote`/`body` |
| `algolia-audit-report` | (same file) | `industry_context.key_benchmarks[]` | same shape as industry benchmarks |
| all other 12 skills | — | none | `()` |

**Two confirmed real drift/naming facts that shaped the code** (not assumed):
1. **`industry-intel.json` filename drift**: older audits (Dell, all of `~/Dropbox/AI-Development/Algolia Search Audit/*`) name this file `research/industry-intel.json`; newer audits (lululemon, jbl) name it `research/06-industry-intel.json`. `_first_existing()` tries both rather than picking one and guessing.
2. **`{slug}-audit-data.json` filename is NOT a predictable slugification of `company_name`**: confirmed real examples — `"British Airways"` → `british-airways-audit-data.json` (hyphenated), `"Michael Kors"` → `michaelkors-audit-data.json` (no hyphen at all). `_find_audit_data_json()` globs `deliverables/*-audit-data.json` instead of computing a guessed slug from `skill_output.company_name`.

**Why only 4 skills, not 16 with a generic walker**: `algolia-intel-techstack`, `-traffic`, `-competitors`, `-financial-public`, `-financial-private`, `-social`, `-news`, `-hiring`, `-partner`, `-queries`, `algolia-audit-browser`, `algolia-audit-factcheck` were all inspected (their real research-file field lists are in the recon transcript, e.g. `02-tech-stack.json`'s `search_vendor_*` fields, `09b-social-signals.json`'s `signals[]`, `08-financial-profile.json`'s `executive_quotes[]`). None of them is checked by `validate-json-schema.py` for a citable array shape — a single value with a free-text `_source` sibling field (e.g. `monthly_visits_source`) is a different shape than an array of quotes/benchmarks each carrying its own citation, and inventing a generic "any array with a `source`-ish key is a claim" walker would silently manufacture claims the ground truth file never asked anyone to check. Per the brief's explicit instruction, these correctly return `()`.

Note: `08-financial-profile.json`'s `executive_quotes[]` (has `quote` + `source_url`, structurally identical to `media_quotes[]`) and `04-competitors.json`'s `sources_used` are real candidate claim structures that `validate-json-schema.py` does **not** check — flagging this rather than silently including or silently omitting it without comment. Left out of scope here because the brief's ground truth (`validate-json-schema.py`) doesn't validate them; if Task 6's parity run wants factcheck coverage on financial executive quotes, that's a real, cheap follow-up (same `_media_quote_claim`/`_executive_claim` shape already built) but is new scope beyond this task's ground-truth instruction, not silently smuggled in.

## Definition of done

- ✅ Unit tests using real-shaped fixture JSON per skill family (media_quotes, intelligence_signals, benchmarks, key_benchmarks, portfolio_brands, executives) — 17 tests in `tests/pipeline/test_claims.py`, covering each pattern plus the file-naming-drift cases (both `industry-intel.json` filenames, both present at once, slug-independent audit-data.json globbing).
- ✅ Empty-tuple path tested 4 ways: a skill with no claim-bearing structure at all (`algolia-intel-techstack`), a missing output file, malformed JSON, and a nonexistent `audit_dir`.
- ✅ End-to-end wiring: `make_batch_factcheck_fn(claims.extract_claims)` produces a real `gate.FactCheckFn` callable, proven against a fake `claude -p` (one call per real claim, zero claims → zero calls) — reusing Task 5b's existing adapter, not rebuilt.
- ✅ `ruff check` / `ruff format --check` / `mypy --strict` clean on both new files (stricter than Task 5b's own bar, which ran plain `mypy` not `--strict` on its test file).
- ✅ Full existing suite passes unmodified: 268 → 285 (268 baseline + 17 new), zero regressions, 18 skipped identical to baseline.
- ✅ Cost estimate updated in Task 5b's report with real measured claim counts from 3 real audits (see below) — replaces the "5-20 claims per skill" guess.

## Test results (verbatim)

```
$ python3 -m pytest tests/pipeline/test_claims.py -v
======================= test session starts =======================
collected 17 items
tests/pipeline/test_claims.py::test_investor_media_quotes_extracted_with_speaker_and_quote PASSED
tests/pipeline/test_claims.py::test_investor_media_quotes_skips_entries_missing_speaker_or_quote PASSED
tests/pipeline/test_claims.py::test_industry_benchmarks_extracted_from_unprefixed_filename PASSED
tests/pipeline/test_claims.py::test_industry_benchmarks_extracted_from_numbered_prefix_filename PASSED
tests/pipeline/test_claims.py::test_industry_prefers_unprefixed_filename_when_both_exist PASSED
tests/pipeline/test_claims.py::test_report_intelligence_signals_extracted_with_heterogeneous_content_field PASSED
tests/pipeline/test_claims.py::test_report_industry_context_key_benchmarks_extracted PASSED
tests/pipeline/test_claims.py::test_report_executives_extracted_with_name_title_and_quote PASSED
tests/pipeline/test_claims.py::test_report_finds_audit_data_json_regardless_of_slug_shape PASSED
tests/pipeline/test_claims.py::test_report_combines_all_three_structures_in_one_call PASSED
tests/pipeline/test_claims.py::test_company_portfolio_brands_extracted_with_name_and_domain PASSED
tests/pipeline/test_claims.py::test_skill_with_no_claim_bearing_structure_returns_empty_tuple PASSED
tests/pipeline/test_claims.py::test_missing_output_file_returns_empty_tuple_not_an_error PASSED
tests/pipeline/test_claims.py::test_malformed_json_returns_empty_tuple_not_an_error PASSED
tests/pipeline/test_claims.py::test_nonexistent_audit_dir_returns_empty_tuple_not_an_error PASSED
tests/pipeline/test_claims.py::test_extract_claims_wired_into_make_batch_factcheck_fn PASSED
tests/pipeline/test_claims.py::test_extract_claims_wired_into_make_batch_factcheck_fn_zero_claims_zero_calls PASSED
======================= 17 passed in 0.35s =======================
```

Full suite, before vs. after (via `git stash -u` on the same tree, confirming baseline independently rather than trusting a remembered number):

```
$ git stash -u && python3 -m pytest tests/pipeline/ -q   # BEFORE
268 passed, 18 skipped in 29.72s

$ git stash pop && python3 -m pytest tests/pipeline/ -q  # AFTER
285 passed, 18 skipped in 21.57s
```
285 = 268 baseline + 17 new (`test_claims.py`). Zero regressions, 18 skipped identical to baseline.

```
$ python3 -m ruff check prism_platform/pipeline/claims.py tests/pipeline/test_claims.py
All checks passed!

$ python3 -m ruff format --check prism_platform/pipeline/claims.py tests/pipeline/test_claims.py
2 files already formatted

$ python3 -m mypy --strict prism_platform/pipeline/claims.py tests/pipeline/test_claims.py
Success: no issues found in 2 source files

$ python3 -m mypy prism_platform/
Found 28 errors in 10 files (checked 125 source files)
```
The 28 errors are the same pre-existing baseline files documented in Task 3/4a/5b's reports (`v2/modules/intel_investor/collector.py`, `browser/tier2_stealth.py`, `v2/modules/intel_company/fetcher.py`, `integrations/scout.py`, `v2/synthesis.py`, `api/routers/knowledge.py`, `api/routers/audits.py`) — none of them is `claims.py`, confirmed by the targeted `mypy --strict` run above being clean (a stricter bar than Task 5b's own `mypy` (non-strict) pass on its own test file, which does NOT pass `--strict` — checked, 10 pre-existing errors — but that's Task 5b's test file, not something this task touched or is claiming credit for).

## Real claim counts — cost estimate update

Measured `extract_claims` against 3 real, complete 16-skill audit workspaces on disk (`/Users/arijitchowdhury/prism-data/audits/{Dell,jbl,lululemon}/`), one `SkillOutput` per skill, all 16 skill names:

| Audit | `algolia-intel-company` | `algolia-intel-investor` | `algolia-intel-industry` | `algolia-audit-report` | **total (all 16 skills)** |
|---|---|---|---|---|---|
| Dell | 4 | 3 | 1 | 13 | **21** |
| jbl | 10 | 0 | 6 | 16 | **32** |
| lululemon | 3 | 2 | 7 | 11 | **23** |

The other 12 skills contributed 0 in every audit, every time (correctly — no claim-bearing structure exists for them per the ground truth).

**This replaces Task 5b's "5-20 claims per skill x 16 skills = 80-320 calls" guess** — the real number is **~21-32 total stage-2 (factcheck) calls per audit**, not per skill. Full correction (with the revised total-call estimate) written into `docs/workspace/phase2-executioner/task-5b-report.md`'s "Cost control" section, dated as a Task 5c update rather than silently overwriting Task 5b's original numbers (which are kept, struck through in spirit but left visible, so the record of what was guessed vs. measured stays intact).

## Files

- `/Users/arijitchowdhury/Dropbox/AI-Development/PIP/prism_platform/pipeline/claims.py` (new)
- `/Users/arijitchowdhury/Dropbox/AI-Development/PIP/tests/pipeline/test_claims.py` (new)
- `/Users/arijitchowdhury/Dropbox/AI-Development/PIP/docs/workspace/phase2-executioner/task-5b-report.md` (updated — Cost control section, real measured numbers appended)
- No changes to `gate.py`, `executioner.py`, `verdicts.py`, `llm_stages.py`, or `chat_agent.py` — pure addition, `claims_fn` is now a real importable function Task 6's parity harness can pass to `make_batch_factcheck_fn` with no further guessing.
