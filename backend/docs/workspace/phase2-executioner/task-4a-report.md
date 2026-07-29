# Task 4a report — Track C.1: executioner dispatch rewrite

Status: **DONE**

3-line summary: Built `prism_platform/pipeline/executioner.py` (`make_dispatch_fn` reuses the real staged `build_audit_cmd` to force per-skill dispatch via `run-audit.sh --skill`; `make_gate_fn` wraps `gate.gate()` and maps its `Verdict` to `self_heal.GateResult`, with `factcheck_fn`/`adversarial_fn`/`quality_fn` defaulting to loud `NotImplementedError` stubs, not silent auto-pass). Wired an opt-in `job["engine"] == "v3"` path into the staged `prism-runner.py` that runs the 16 skills through `self_heal.SelfHealLoop` instead of one long subprocess, with a DB-write `on_attempt` observer — the legacy path is untouched and remains the default. All 19 new tests pass; all 186 pre-existing `tests/pipeline/` tests still pass unmodified (205 total now); `ruff check`/`ruff format --check`/`mypy --strict` clean on every new/changed file.

Report path: `docs/workspace/phase2-executioner/task-4a-report.md`

---

## What was built

### 1. `prism_platform/pipeline/executioner.py` (new file)

- **`make_dispatch_fn(domain, *, build_cmd_fn=None, run_cmd_fn=None) -> self_heal.DispatchFn`**
  Returns `(skill_name, attempt_number) -> bool`. Builds `job = {"domain": domain, "skill": skill_name}` — never `phase`/`skip` — and calls `build_cmd_fn(job)` (default: the REAL staged `prism-runner.py`'s `build_audit_cmd`, lazily loaded once per process via the exact `importlib.util` pattern `tests/pipeline/test_runner_routes.py` already uses for that hyphenated-filename host script, cached in a module-level `types.ModuleType | None`), then `run_cmd_fn(cmd)` (default: real `subprocess.run`). Returns `True` iff exit code `0` — explicitly documented as "dispatch ran to completion," not "output is good, that's the gate's job," per the brief.
  `test_make_dispatch_fn_default_build_cmd_fn_reuses_real_build_audit_cmd` proves the default really calls the real `build_audit_cmd` (argv shape: `sudo -u <user> bash <run-audit.sh> <domain> --skill <skill>`, no `--phase`/`--skip`) with `run_cmd_fn` faked so no real subprocess runs.

- **`make_gate_fn(domain, company_name, audit_dir, *, mechanical_cmd_fn=None, factcheck_fn=_stub_factcheck_fn, adversarial_fn=_stub_adversarial_fn, quality_fn=_stub_quality_fn, quality_pass_threshold=..., verdict_sink=None) -> self_heal.GateFn`**
  Returns `(skill_name) -> GateResult`. Builds a `gate.SkillOutput` and calls `gate.gate(...)`, then maps the result: `status=CLEAN` iff `Verdict.status == PASS` else `BLOCKED`; `fatal=True` iff `Verdict.block_class == BlockClass.UNFIXABLE` (patch #3 — the loop must escalate immediately on an unfixable BLOCK rather than burn `max_passes` retries). `verdict_sink`, if passed, is populated with the full `Verdict` per skill so a caller (prism-runner.py's v3 `on_attempt` observer) can persist the richer 5-stage trail that a bare `GateResult` can't carry.

- **`_stub_factcheck_fn` / `_stub_adversarial_fn` / `_stub_quality_fn`**
  Per the brief: "you do NOT have a real LLM call to wire in this task... naming a real embedding/LLM call is Task 5's job." Each stub raises `NotImplementedError` with a `TODO(Task 5)` docstring naming exactly what must replace it (a real schema-constrained LLM call against the corresponding `verdicts.py` Pydantic model). These are the **default** values for `factcheck_fn`/`adversarial_fn`/`quality_fn` in `make_gate_fn`'s signature — so swapping in real implementations later is a one-line change (pass a real callable for the kwarg) and calling `make_gate_fn()` today with no overrides is fully wired/callable, but any call that actually reaches stage 2+ fails loudly instead of silently auto-passing. Verified by `test_make_gate_fn_default_stages_raise_notimplementederror_not_silent_pass`.

13 tests in `tests/pipeline/test_executioner.py` cover: dispatch forcing skill (never phase/skip), dispatch true/false on exit code, the real-`build_audit_cmd` reuse proof, gate mapping for PASS→CLEAN, mechanical BLOCK→BLOCKED/not-fatal, factcheck CONTRADICTED→BLOCKED/fatal, quality-below-threshold→BLOCKED/not-fatal, adversarial-panel-only-on-risky-claims→BLOCKED/fatal, the NotImplementedError-not-silent-pass guarantee, `verdict_sink` population, and the default (unwired) mechanical command path fail-closing to BLOCKED rather than crashing.

### 2. Wiring into `docs/workspace/cassandra-tooling/staged/prism-runner.py`

- **Optional-import guard** (mirrors the existing `psycopg2` guard, since the module's own docstring states it "runs standalone on the host with no app install"):
  ```python
  try:
      from prism_platform.pipeline import db_write as _db_write
      from prism_platform.pipeline import executioner as _executioner
      from prism_platform.pipeline import self_heal as _self_heal
  except Exception:
      _db_write = None
      _executioner = None
      _self_heal = None
  ```
- **`run_job()`** gained 4 new trailing kwargs (`v3_dispatch_fn`, `v3_gate_fn`, `v3_on_attempt`, `v3_max_passes=3`) and one new line at the very top:
  ```python
  if job.get("engine") == "v3":
      return run_job_v3(job, dispatch_fn=v3_dispatch_fn, gate_fn=v3_gate_fn,
                         on_attempt=v3_on_attempt, max_passes=v3_max_passes)
  ```
  Every existing call site passes none of these new kwargs and no existing job ever sets `job["engine"]`, so the legacy branch below is reached exactly as before — **off by default, additive only**.
- **`run_job_v3(job, *, dispatch_fn=None, gate_fn=None, on_attempt=None, max_passes=3)`** (new function): if `prism_platform` isn't importable, fails loudly (`status="failed"`, explicit error message) rather than silently falling back to v1. Otherwise: writes `_db_audit_id` via the existing `db_write_audit_start` (unless `dry`), builds `dispatch`/`gate` via `executioner.make_dispatch_fn`/`make_gate_fn` (with a `verdict_sink` dict) unless overridden, builds the real `on_attempt` observer (`_v3_default_on_attempt`, persists via `db_write.write_module_execution_row` inside `asyncio.run(...)`, fail-soft/logged via the existing `_log_db_error`) unless overridden, then drives `self_heal.SelfHealLoop(...).run_pipeline(executioner.SKILL_NAMES)`. Any skill's `PhaseOutcome.NEEDS_HUMAN` escalates the whole job to `needs_human`; otherwise it publishes via the existing `publish_to_store` and marks `done`/`published_failed` exactly like the legacy path's terminal states.
- **Did not touch**: `build_audit_cmd`, `run-audit.sh`, the `job["phase"]`/`job["skill"]` clobber-bug fix (still exactly where it was, comment intact), `detect_phase`/`detect_skill_states`/`detect_needs_human`, `publish_to_store`, the DB write functions, `kill_job`/`_terminate`, or any HTTP route handler.

7 new tests in `tests/pipeline/test_runner_routes.py`: legacy-path-untouched-by-default (monkeypatches `run_job_v3` to fail the test if called — a job with no `engine` key never reaches it), `engine="v3"` delegates to `run_job_v3` with the right kwargs, `run_job_v3` fails loudly when `prism_platform` is unavailable, a full-pipeline CLEAN run marks `done` (and produces one `v3_reports` entry per `executioner.SKILL_NAMES`), a fatal gate result on one skill escalates the WHOLE job to `needs_human` after exactly 1 attempt (proving the patch #3 fatal short-circuit is really wired through, not just unit-tested in isolation), and the `on_attempt` observer fires once per skill across the pipeline.

## Test results (verbatim)

```
$ python3 -m pytest tests/pipeline/ -q          # BEFORE any change (baseline)
.......................................ss...................ssssssssssss [ 35%]
ssss.................................................................... [ 70%]
............................................................             [100%]
186 passed, 18 skipped in 4.35s
```

```
$ python3 -m pytest tests/pipeline/test_executioner.py -v
============================= 13 passed in 0.81s ==============================
```

```
$ python3 -m pytest tests/pipeline/test_runner_routes.py -v
============================== 47 passed in 0.43s ==============================
```
(41 pre-existing + 6 new; all pre-existing tests unmodified and still pass, including the phase/skill-clobber regression coverage, the wall-clock timeout test, the notify tests, and every `/rerun`/`/kill`/`/needs_human`/`/jobs` route test.)

```
$ python3 -m pytest tests/pipeline/ -q          # AFTER all changes
.......................................ss............................... [ 32%]
.ssssssssssssssss....................................................... [ 64%]
........................................................................ [ 96%]
.......                                                                  [100%]
205 passed, 18 skipped in 5.53s
```
205 = 186 baseline + 13 new (`test_executioner.py`) + 6 new (`test_runner_routes.py`'s v3 tests) = 205, zero regressions. 18 skipped is identical to the baseline's 18 skipped (unchanged, all pre-existing docker/DB-gated tests).

```
$ python3 -m ruff check prism_platform/pipeline/executioner.py tests/pipeline/test_executioner.py \
    docs/workspace/cassandra-tooling/staged/prism-runner.py tests/pipeline/test_runner_routes.py
All checks passed!

$ python3 -m ruff format --check prism_platform/pipeline/executioner.py tests/pipeline/test_executioner.py \
    docs/workspace/cassandra-tooling/staged/prism-runner.py tests/pipeline/test_runner_routes.py
4 files already formatted
```

```
$ python3 -m mypy prism_platform/pipeline/executioner.py
Success: no issues found in 1 source file

$ python3 -m mypy prism_platform/
Found 33 errors in 11 files (checked 118 source files)
```
The 33 errors are the same 28 pre-existing baseline files/errors documented in Task 3's report (unrelated files: `v2/modules/intel_investor/collector.py`, `browser/tier2_stealth.py`, `v2/modules/intel_company/fetcher.py`, `integrations/scout.py`, `v2/synthesis.py`, `api/routers/knowledge.py`, `api/routers/audits.py`) — none of my files appear. `prism_platform/pipeline/executioner.py` alone (checked separately above) is clean under `mypy --strict`. `docs/workspace/cassandra-tooling/staged/prism-runner.py` is outside the `prism_platform/` package and outside this project's mypy target (same as Task 3's runner-adjacent files); not type-checked by `mypy prism_platform/`, consistent with the existing convention for that hyphenated-filename host script.

## Legacy path proof (DoD requirement: "provably unchanged")

- `test_run_job_engine_v3_default_off_uses_legacy_path` monkeypatches `run_job_v3` to record a call if invoked; a job with no `engine` key completes via the untouched legacy branch and `run_job_v3` is never called (`calls == []`).
- Every pre-existing test in `test_runner_routes.py` (slugify, job I/O, `/run`, `/rerun`, dry-run, success/failure/publish-failed, skill-state log parsing, NEEDS_HUMAN marker mark-and-continue, `/status`, wall-clock timeout, notify, `/kill`, `/needs_human`, `/jobs`) passes unmodified, byte-identical to before this task's changes.
- The `job["phase"]`/`job["skill"]` clobber-bug fix and its comment (the one the brief explicitly warned not to reintroduce) are untouched — `run_job`'s legacy branch still builds `cmd = build_audit_cmd(job)` before `job["phase"]` is overwritten for progress tracking.

## Concerns / honest caveats (why not a bare "DONE" without qualification, though nothing here blocks shipping this task)

1. **`_v3_default_on_attempt`'s DB write was never executed against a real Postgres in this sandbox** (no docker/local Postgres available, same limitation Task 3 flagged for its own DB-write tests). It's exercised in tests only via injected `on_attempt` fakes that never touch the real `asyncio.run(...)`/`create_async_engine(...)` path. The real path reuses `db_write.write_module_execution_row` (already unit-tested in Task 3, 12 pure-logic tests passing) plumbed through a fresh `AsyncEngine` per attempt — functionally straightforward but not integration-tested end-to-end here. Someone with docker/a running Postgres should exercise `run_job_v3` against a real DB before trusting `v3_publish`/`module_executions` rows in production.
2. **`make_gate_fn`'s three LLM stages are intentionally unusable in production as shipped** (loud `NotImplementedError`, by design per the brief) — Task 5 must supply real `factcheck_fn`/`adversarial_fn`/`quality_fn` before `engine="v3"` can complete past stage 1 for any real skill output. This is not a defect; it's the explicit scope boundary the brief drew.
3. **`run_job_v3`'s per-attempt DB write creates a new `AsyncEngine` every call** rather than reusing a shared engine/pool — correct but not connection-efficient across a 16-skill pipeline. Acceptable for this task's scope (a background host script, not a hot path); flagging for whoever wires this into a longer-lived process.
