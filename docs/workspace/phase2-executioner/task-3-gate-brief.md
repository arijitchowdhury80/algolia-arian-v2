# Task 3 brief — build Track G: `gate()` 5-stage verification pipeline

Read the binding interface contract in full FIRST: `docs/workspace/phase2-executioner/interface-contract.md`. It fixes file paths, the `gate()` signature, `SkillOutput`/`Verdict`/`BlockClass` shapes, and all 5 Pydantic verdict schemas. Do not invent a different shape.

Also read: `docs/workspace/phase2-executioner/task-1-recon-report.md` sections 3 and 4 (exact `factcheck_mechanical.py` path + exit-code contract, `algolia-audit-factcheck`/`algolia-audit-eval` invocation surfaces) — these are ground truth, already verified live, do not re-verify.

Read the existing tested code you are extending/reusing, in full, before writing anything: `prism_platform/pipeline/self_heal.py` (do not weaken or remove its 20 existing tests in `tests/pipeline/test_self_heal.py`) and `prism_platform/db/models.py`'s `ModuleExecution` model (the real, live schema — confirmed column-for-column against the deployed Postgres table in the recon report).

## What to build (TDD — write failing tests first, per superpowers:test-driven-development)

1. **`prism_platform/pipeline/verdicts.py`** — the 5 Pydantic schemas exactly as specified in the interface contract (`FactCheckVerdict`, `AdversarialVoterVerdict`, `AdversarialVerdict`, `QualityScore`, `LegalVerdict`).
2. **Extend `prism_platform/pipeline/self_heal.py`**: add `fatal: bool = False` to `GateResult` (default must not change behavior for any of the 20 existing tests — run them before and after your change to prove this). Change `SelfHealLoop.run_phase` so that when the latest attempt's `gate.fatal is True`, it breaks to `NEEDS_HUMAN` immediately, without consuming remaining `max_passes` attempts. Add new tests for this fatal-early-exit path (e.g. `max_passes=5` but a fatal result on attempt 1 stops at attempt 1, not attempt 5).
3. **`prism_platform/pipeline/gate.py`** — implement `gate(skill_output: SkillOutput) -> Verdict` running the 5 stages in order, short-circuiting on first BLOCK, per the contract:
   - Stage 1 (mechanical): wrap `factcheck_mechanical.py` via `self_heal.subprocess_gate()`-style adapter (reuse the exit-code mapping pattern, exit 0=PASS, exit 2=BLOCK/RETRY_WORTHY). The real script path and CLI args are in the recon report item 3.
   - Stages 2-4 (factcheck, adversarial, quality): these call an LLM with forced schema-constrained tool-use output against the Pydantic models from `verdicts.py`. **You will not have live LLM access to test against for real** — build these stages behind an injectable `LlmCallFn` (dependency-injected, same pattern as `self_heal.py`'s `dispatch`/`gate` injection) so they are unit-testable with fake/stub LLM responses. Do not hardcode a real API call inline — that is Task 4/5's wiring concern, not this task's. Your job is the stage logic (given a verdict object, decide PASS/BLOCK/block_class), not the LLM plumbing itself.
   - Stage 5 (legal): always returns `LegalVerdict(status="needs_human_review", note=...)` per the contract — no automated judgment, this is intentional, do not "improve" it.
   - Patch #4 compliance: `Verdict.stage` field is the stage number (1-5) that produced a BLOCK — write a test proving the 3-strike kill condition (via the self_heal loop, once wired) counts "same stage" not "same claim."
4. **DB write helper**: a function that maps a `Verdict` + `Attempt` (from `self_heal.py`) into a `ModuleExecution` row (using the existing SQLAlchemy model, not raw SQL) and persists it. This becomes the `on_attempt` observer callback per the contract's `run_full_audit` sketch. Test with a real test-DB fixture if one already exists in `tests/pipeline/` or `tests/` (check `test_runner_dbwrite.py` first — it may already have the exact fixture pattern you need; reuse it, don't rebuild).

## Definition of done

- `python3 -m pytest tests/pipeline/ -q` — all existing 95 tests still pass, PLUS new tests for `verdicts.py`, the `gate.py` 5-stage logic (all 5 stages, PASS and BLOCK paths, both `block_class` values), the `self_heal.py` fatal-early-exit extension, and the DB-write helper.
- `ruff check . && ruff format --check . && mypy src/ --strict` (or the project's actual mypy target — check `pyproject.toml` if `src/` isn't right) — clean, or report which pre-existing violations are not yours to fix.
- Show the actual pytest/ruff/mypy output in your report, not a narrative claim (CLAUDE.md cardinal rule #1).

## Output

Write your full report (what you built, test counts, command output, any concerns) to `docs/workspace/phase2-executioner/task-3-gate-report.md`. Return status DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED with the report path and a 3-line summary.

If you hit a genuine ambiguity the contract doesn't resolve, return NEEDS_CONTEXT rather than guessing — this file is read by Task 4's implementer next, so an invented shape here propagates.
