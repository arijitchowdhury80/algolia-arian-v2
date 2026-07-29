# Task 5c brief — build `claims_fn` (mechanical claim extraction, closes Task 5b's flagged gap)

Read first: `docs/workspace/phase2-executioner/task-5b-report.md` §"Concern flagged for Task 6 — the claim-extraction gap" (states the exact problem this task solves) and `prism_platform/pipeline/llm_stages.py`'s `make_batch_factcheck_fn(claims_fn, ...)` (the exact interface you're implementing `claims_fn` for — signature: `claims_fn(skill_output: gate.SkillOutput) -> tuple[str, ...]`, called once per skill, returns the claim strings to fact-check).

## Ground truth (read in full before writing anything — do not invent a generic walker)

`~/.claude/skills/algolia-search-audit/scripts/validate-json-schema.py` is the authoritative source for which fields in each skill's output JSON carry a checkable claim. It is heterogeneous, NOT one uniform schema across all 16 skills — different skills use different field names for the same concept:
- `media_quotes[i]` → `speaker`, `quote_source` (a URL)
- `intelligence_signals[i]` → `detail`/`quote`/`body`/`title`, `source_url`
- `industry-intel.json benchmarks[i]` → `confidence` (`"FACT"` requires `source_url`)
- `audit-data.json industry_context.key_benchmarks[i]` → `source_url`

Read the WHOLE file (not just the grep hits above — those are a starting pointer, not the full list) to build the real, complete field-name table per skill/section before writing extraction code. Also check `algolia-search-audit/scripts/check-claim-traceability.py` for the playbook/queries pattern (narrower scope, Cluster E only, but shows the project's existing convention for what counts as "a claim" — a factual assertion paired with a citation).

## What to build

`prism_platform/pipeline/claims.py` — `extract_claims(skill_output: gate.SkillOutput) -> tuple[str, ...]`:
- For a given `skill_output.skill_name`, locate that skill's real output file(s) under `skill_output.audit_dir` (confirm the real file-naming convention per skill — read a couple of the JSON schema checks above for the actual filenames like `industry-intel.json`, `audit-data.json`; don't guess).
- Walk the known claim-bearing structures for that skill (per the table you built from `validate-json-schema.py`), extracting each as a plain claim string: prefer the actual assertion text (`detail`/`quote`/`body`/whatever the field's real content is) combined with enough context to be checkable standalone (e.g. "benchmarks[2]: <text>" isn't a checkable claim by itself — render the real sentence).
- Skills with NO claim-bearing structure in the schema (if any exist) should return an empty tuple, not an error — `make_batch_factcheck_fn` already handles zero claims as zero CLI calls (per Task 5b's tests).
- This is MECHANICAL, deterministic code — no LLM call here. The judgment ("is this claim true") is `factcheck_fn`'s job (already built); this task's job is purely "which strings need judging."

## Definition of done

- Unit tests using real or realistic fixture JSON per skill family (media_quotes, intelligence_signals, benchmarks, key_benchmarks — cover each pattern you find) proving claims are extracted with the right count and the right combined text.
- Test the empty-tuple path for a skill/section with no claims.
- Wire one example end-to-end: `make_batch_factcheck_fn(claims.extract_claims)` produces a real `gate.FactCheckFn` callable (reuse Task 5b's existing test pattern for this, don't rebuild the batch-adapter tests — those already pass).
- `ruff`/`ruff format`/`mypy --strict` clean, full existing suite unmodified/still passing — show output.
- Update the cost estimate from Task 5b's report (§"Cost control") with a REAL claim count from at least one real audit's JSON files if you have access to one (check `docs/temp/fc/belk-audit-data.json`, used by Task 5, or find another real audit workspace) — replace the "5-20 claims per skill" guess with an actual measured number where you can.

## Output

Write your report to `docs/workspace/phase2-executioner/task-5c-report.md`. Return status DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED with the report path and a 3-line summary. Commit as soon as tests/lint/mypy pass — this task has no live-LLM-call risk, but commit early anyway per this session's standing practice.
