# Task 3 report — Track G: `gate()` 5-stage verification pipeline

Status: **DONE_WITH_CONCERNS**

3-line summary: Built `verdicts.py` (5 Pydantic schemas, verbatim to contract), extended `self_heal.GateResult`/`SelfHealLoop` with the `fatal` early-exit (20 original tests untouched and still pass, +5 new), and built `gate.py`'s 5-stage pipeline with dependency-injected LLM stages plus a DB-write helper (`db_write.py`) using the real `ModuleExecution` ORM model with upsert semantics. All 186 runnable tests pass (up from a 136-passing/152-collected baseline, zero regressions); the two real Postgres integration tests for the DB-write helper are written but could not be executed in this sandbox (no docker daemon available) — see "Concerns" below.

Report path: `docs/workspace/phase2-executioner/task-3-gate-report.md`

---

## What was built

### 1. `prism_platform/pipeline/verdicts.py`
The 5 Pydantic schemas (`FactCheckVerdict`, `AdversarialVoterVerdict`, `AdversarialVerdict`, `QualityScore`, `LegalVerdict`) copied verbatim from the interface contract — same field names, same `Literal` value sets, same optionality. 14 tests in `tests/pipeline/test_verdicts.py` cover valid construction, rejection of invalid literals, JSON round-trip, and (for `LegalVerdict`) that `PASS`/`BLOCK` status values are rejected — the stub can only ever produce `needs_human_review`.

### 2. `prism_platform/pipeline/self_heal.py` extension (patch #3 fatal early-exit)
- Added `fatal: bool = False` to `GateResult` (default preserves every pre-existing call site).
- `SelfHealLoop.run_phase` now checks `gate_result.fatal` on every attempt (after the CLEAN check) and breaks to `NEEDS_HUMAN` immediately if true, without consuming remaining `max_passes`.
- `_escalation_reason` now reports `"gate FATAL (unfixable) after N attempts: ..."` when the terminal attempt was fatal.
- **Verified the 20 original tests were run and passed BEFORE any change** (`pytest tests/pipeline/test_self_heal.py -q` → `20 passed`), then again after (`25 passed` — the 20 originals + 5 new). No existing test was modified.
- 5 new tests in `TestFatalGateResultShortCircuitsRetry`: fatal-on-attempt-1 with `max_passes=5` stops at 1 attempt; fatal-on-attempt-2 stops at 2; `GateResult.fatal` defaults to `False`; non-fatal BLOCKED still exhausts `max_passes` as before (regression guard); dispatch-failure attempts (where `gate` is `None`) never crash the new fatal check.

### 3. `prism_platform/pipeline/gate.py`
Implements `gate(skill_output, *, mechanical_cmd=None, factcheck_fn=None, adversarial_fn=None, quality_fn=None, quality_pass_threshold=7.0) -> Verdict`, running the 5 stages in order with short-circuit on first BLOCK:

- **Stage 1 (mechanical)**: reuses `self_heal.subprocess_gate()` directly (no reimplementation of the exit-code mapping). Exit 0 → PASS; exit 2 → BLOCK/RETRY_WORTHY; any other exit code → BLOCK/RETRY_WORTHY as well (documented as a deliberate fail-closed choice consistent with `subprocess_gate`'s own ERROR handling — an ERROR isn't evidence the data is wrong, just that the mechanical check didn't come back clean, so it's still worth a retry).
- **Stage 2 (factcheck)**: `CONTRADICTED`/`UNSUPPORTED` → BLOCK/UNFIXABLE; all `SUPPORTED` → advance.
- **Stage 3 (adversarial)**: patch #1 — only runs on claims stage 2 flagged with a weaker-than-`AUTHENTIC` evidence tier (`WEBSEARCH`/`NO_SOURCE`). If there are no risky claims, the stage auto-passes without even requiring `adversarial_fn` to be supplied. Majority-not-refuted → advance; majority-refuted → BLOCK/UNFIXABLE.
- **Stage 4 (quality)**: score below `quality_pass_threshold` (default 7.0) → BLOCK/RETRY_WORTHY; else advance.
- **Stage 5 (legal)**: always returns `LegalVerdict(status="needs_human_review", ...)`. Documented in code as intentionally never auto-judging — reaching stage 5 always yields an overall `Verdict.status == PASS` at the automated-gate level (there's no PASS/BLOCK value on `LegalVerdict` itself), with the human review happening out-of-band against the persisted `legal` field. **Did not "improve" this per the brief's explicit instruction not to.**

19 tests in `tests/pipeline/test_gate.py` cover all 5 stages, both PASS and BLOCK paths, both `BlockClass` values, the "missing injected fn raises `NotImplementedError`" behavior for stages 2-4, the risky-claim gating for stage 3, custom quality thresholds, and skill-name propagation through every stage. A dedicated test class, `TestPatchFourStageNotClaimScopedStrikeCounting`, wires `gate()`'s `Verdict` into a real `SelfHealLoop` (via a small `Verdict → GateResult` adapter) and proves that 3 attempts whose quality-stage BLOCK reasoning text differs every single time (`"missing pricing section"`, `"missing hiring section"`, `"missing news section"`) still exhaust `max_passes=3` and escalate — i.e. the strike counter tracks stage identity (all 3 blocked at stage 4), not exact claim/finding wording.

### 4. `prism_platform/pipeline/db_write.py`
`write_module_execution_row(session, *, audit_id, domain, verdict, attempt, module_version="gate-v1", now=None) -> ModuleExecution` — maps a `gate.Verdict` + `self_heal.Attempt` into one `ModuleExecution` row via the real SQLAlchemy ORM model (no raw SQL), upserting on `(audit_id, module_name)` so re-dispatch attempts update in place instead of duplicating (matching the behavior already proven for the staged runner's raw-SQL writes in `test_runner_dbwrite.py`).

Pure helper functions (all independently unit tested, no DB needed):
- `verdict_to_status`: dispatch failure or no verdict → `"failed"`; PASS → `"completed"`; BLOCK/UNFIXABLE → `"needs_human"`; BLOCK/RETRY_WORTHY → `"blocked"`.
- `verdict_to_validation_json`: full stage trail (factcheck/adversarial/quality/legal sub-verdicts, findings, mechanical raw output) serialized into the JSONB shape for `validation_json`.
- `attempt_duration_ms`: elapsed time from `Attempt.started_at`/`finished_at`, clamped to non-negative.

**Bug caught and fixed before it shipped** (documented in the module docstring as a standing gotcha): `Attempt.started_at`/`finished_at` are `time.monotonic()` readings (or a fake clock in tests), NOT epoch/wall-clock time — `self_heal.py`'s `ClockFn` default is `time.monotonic`. An earlier draft would have called `datetime.fromtimestamp()` directly on these values, which would silently write nonsense dates (e.g. `1970-01-01T00:00:10Z`) into the `timestamptz` columns. Fixed by stamping `completed_at` with real wall-clock time at persist-time and deriving `started_at` by subtracting the attempt's own (monotonic-delta) duration — the delta between two monotonic readings is a valid real-time interval even though neither reading alone is a real timestamp. Regression-guarded by `TestDurationDoesNotLeakMonotonicReadingsAsTimestamps` in `test_db_write.py`.

12 pure-logic tests pass with no DB. 2 real Postgres integration tests (`test_write_module_execution_row_inserts_a_new_row`, `test_write_module_execution_row_upserts_on_retry_not_duplicate`) are written reusing the exact ephemeral-docker + real-alembic-migrations pattern from `tests/pipeline/test_runner_dbwrite.py` (not rebuilt from scratch), gated behind `@pytest.mark.db` + a per-test (not module-level) `skipif(docker unavailable)` guard.

**Bug caught while wiring the skip guard**: my first draft used a module-level `pytestmark = pytest.mark.skipif(...)`, which — because `test_db_write.py` mixes pure-logic and DB tests in one file, unlike `test_runner_dbwrite.py` which is DB-only — was silently skipping all 14 tests in the file, including the 12 that need no DB at all. Caught by actually running the file and seeing `14 skipped` instead of `12 passed, 2 skipped`. Fixed by moving the skip to a named marker (`_skip_if_no_docker`) applied only to the two DB-integration test functions.

## A documented interpretation (not a guess — flagging for Task 4/5)

The contract's code sketch shows `gate(skill_output: SkillOutput) -> Verdict` with no dependency-injection parameters, while also requiring stages 2-4 to be "behind an injectable `LlmCallFn`" and explicitly forbidding a live API call inline in this task. Those two requirements are in tension for a single-argument function. Resolved by keeping `gate()`'s required signature exactly as specified (`skill_output` is the only positional/required argument) and adding **optional keyword-only** injection parameters (`mechanical_cmd`, `factcheck_fn`, `adversarial_fn`, `quality_fn`, `quality_pass_threshold`) that default to `None`/a sane default. When a required stage's callable is `None`, `gate()` raises `NotImplementedError` rather than silently auto-passing. Task 4a's `make_gate_fn(domain, company_name, audit_dir) -> GateFn` (per the contract, not built in this task) is expected to close over real callables and call `gate(skill_output, factcheck_fn=real_llm_factcheck, ...)` — i.e. `gate()` itself doesn't change shape, but nobody may call it in production without supplying the real stage functions. Flagging this explicitly per the brief's own instruction ("if you hit a genuine ambiguity... return NEEDS_CONTEXT rather than guessing") — I judged this resolvable within the contract's stated intent rather than a genuine blocker, but Task 4/5's implementer should confirm this reading before wiring real LLM calls.

## Test results (verbatim output)

```
$ python3 -m pytest tests/pipeline/ -q
...........................ssssssssssssss...................ssssssssssss [ 35%]
ssss.................................................................... [ 70%]
............................................................             [100%]
186 passed, 18 skipped in 5.38s
```

Per-file breakdown of new/changed files:
```
tests/pipeline/test_self_heal.py  : 25 passed   (20 original, unmodified + 5 new)
tests/pipeline/test_verdicts.py   : 14 passed   (new)
tests/pipeline/test_gate.py       : 19 passed   (new)
tests/pipeline/test_db_write.py   : 12 passed, 2 skipped (new; the 2 skipped are the
                                     real-Postgres integration tests -- see Concerns)
```

Baseline (before this task, confirmed via `git stash -u` on the same tree): `tests/pipeline/` collected 152 tests, 136 passed / 16 skipped. The brief's DoD says "all existing 95 tests still pass" — that figure doesn't match the actual baseline in this repo (136 passing / 152 collected); reporting the real number rather than reconciling to the brief's stated count. All 136 originally-passing tests still pass; zero regressions.

```
$ python3 -m pytest tests/pipeline/test_self_heal.py -q   # BEFORE the fatal extension
....................
20 passed in 0.29s

$ python3 -m pytest tests/pipeline/test_self_heal.py -q   # AFTER
.........................
25 passed in 0.29s
```

```
$ ruff check prism_platform/pipeline/gate.py prism_platform/pipeline/verdicts.py \
    prism_platform/pipeline/db_write.py prism_platform/pipeline/self_heal.py \
    tests/pipeline/test_gate.py tests/pipeline/test_verdicts.py \
    tests/pipeline/test_db_write.py tests/pipeline/test_self_heal.py
UP042 Class VerdictStatus inherits from both `str` and `enum.Enum`
UP042 Class BlockClass inherits from both `str` and `enum.Enum`
Found 2 errors.
```
Both are the exact `class VerdictStatus(str, Enum)` / `class BlockClass(str, Enum)` shapes the interface contract specifies verbatim (line-for-line copy from `interface-contract.md`). This is also the pre-existing convention elsewhere in the codebase (`prism_platform/v2/pipeline_health.py`'s `EventSeverity`/`EventCategory`, `prism_platform/browser/types.py`'s `FetchTier` all trigger the same UP042 today, unfixed). Not fixing this: changing to `enum.StrEnum` would deviate from the contract's literal shape, which the brief explicitly forbids ("do not invent a different shape"). Flagging as accepted, not silently ignored.

```
$ ruff format --check prism_platform/pipeline/gate.py prism_platform/pipeline/verdicts.py \
    prism_platform/pipeline/db_write.py prism_platform/pipeline/self_heal.py \
    tests/pipeline/test_gate.py tests/pipeline/test_verdicts.py \
    tests/pipeline/test_db_write.py tests/pipeline/test_self_heal.py
8 files already formatted
```

```
$ mypy prism_platform/pipeline/gate.py prism_platform/pipeline/verdicts.py \
    prism_platform/pipeline/db_write.py prism_platform/pipeline/self_heal.py
Success: no issues found in 4 source files
```

```
$ mypy prism_platform/   # full project target per pyproject.toml/Makefile
Found 28 errors in 10 files (checked 117 source files)
```
All 28 errors are in files I did not touch (`v2/modules/intel_investor/collector.py`, `browser/tier2_stealth.py`, `v2/modules/intel_company/fetcher.py`, `integrations/scout.py`, `v2/synthesis.py`, `api/routers/knowledge.py`, `api/routers/audits.py`) — none of my 4 new/changed pipeline files appear in the error list. Confirmed pre-existing by re-running `mypy prism_platform/pipeline/{gate,verdicts,db_write,self_heal}.py` alone → clean.

Also confirmed pre-existing, unrelated failure elsewhere in the suite: `tests/v2/test_intel_hiring_phase4.py::TestHiringFetcher::test_linkedin_redirect_detected` (a live-network test hitting `dell.com`) fails identically on a clean `git stash`'d tree, before any of my changes. Not caused by this task, not fixed by this task (out of scope).

## Concerns (DONE_WITH_CONCERNS, not DONE)

1. **The 2 real-Postgres DB-write integration tests were never executed.** No docker daemon is available in this sandbox (`docker info` fails: `dial unix .../docker.sock: connect: no such file or directory`), and the local dev Postgres on `localhost:5432` (the app's default `database_url`) is also not running here (`pg_isready` → no response). The tests are written, reuse the exact proven ephemeral-docker + real-alembic-migration pattern from `test_runner_dbwrite.py`, and are correctly gated to skip (not error) when docker is unavailable — but per CLAUDE.md cardinal rule #1, I am not claiming they pass; only that the 12 pure-logic tests around the same helper functions (`verdict_to_status`, `verdict_to_validation_json`, `attempt_duration_ms`) do pass, and that the ORM statement construction (`pg_insert(...).on_conflict_do_update(...).returning(...)`) type-checks cleanly under `mypy --strict`. Someone with docker (or a running local Postgres with migrations applied) should run `pytest tests/pipeline/test_db_write.py -m db -v` before this helper is trusted in production wiring.
2. **The Task 3→Task 4 signature interpretation** documented above (optional keyword-injection on an otherwise-fixed `gate(skill_output)` signature) is my judgment call, not literally spelled out in the contract. Flagging for Task 4/5's implementer to confirm rather than silently assume.
3. **Stage 4's quality-pass threshold (7.0) is a single global default**, not a per-skill threshold table — the contract says "below the skill's pass threshold" (singular possessive, implying per-skill values may exist eventually) but no per-skill rubric exists yet in any document I read. `quality_pass_threshold` is an overridable parameter, so Task 4/5 can supply per-skill values once/if that rubric exists; until then every skill uses the same default.
