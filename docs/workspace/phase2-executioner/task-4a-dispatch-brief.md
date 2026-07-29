# Task 4a brief — executioner dispatch rewrite (Track C.1)

Read first, in full: `docs/workspace/phase2-executioner/interface-contract.md` (binding shapes) and `docs/workspace/phase2-executioner/task-3-gate-report.md` (what Task 3 actually built — `gate()`'s real signature has optional keyword-injection params: `mechanical_cmd`, `factcheck_fn`, `adversarial_fn`, `quality_fn`, `quality_pass_threshold`; missing required stage callables raise `NotImplementedError`, they do NOT silently auto-pass).

Ground truth (do not re-derive): the canonical source-of-truth for the deployed executioner is `docs/workspace/cassandra-tooling/staged/prism-runner.py` + `run-audit.sh` in THIS repo (confirmed byte-identical to the live VPS `/opt/prism-executor/` files in the Task 1 recon report, item 2 — this repo's copy is what gets deployed, not a stale draft). Read both files in full before changing anything. Also read `prism_platform/pipeline/self_heal.py` and `prism_platform/pipeline/gate.py`/`db_write.py` (Task 3's output, already committed) in full.

## What exists today (confirmed, per recon)

- A default `/run` request (domain only) → `build_audit_cmd()` builds ONE subprocess invoking `run-audit.sh <domain>` with no `--phase`/`--skill` flag → one `claude -p` process runs all 16 skills internally, with only log-marker-based progress tracking (`detect_skill_states()` regexing `>>> SKILL START/DONE`). This is what must change.
- `run-audit.sh` ALREADY supports `--skill <name>` to run exactly one skill standalone against an existing workspace (confirmed live, used today for manual reruns via `/rerun`). **This already does the per-skill dispatch mechanism — you are not building a new subprocess mechanism, you are calling the existing one in a new automatic loop.**

## What to build

1. **`prism_platform/pipeline/executioner.py`** (new file, per interface contract): `make_dispatch_fn(domain: str) -> DispatchFn` and `make_gate_fn(domain: str, company_name: str, audit_dir: Path) -> GateFn`, matching `self_heal.py`'s `DispatchFn`/`GateFn` shapes exactly.
   - `make_dispatch_fn`'s returned callable, given `(skill_name, attempt_number)`, must invoke the SAME command-building logic as `build_audit_cmd()` but with `job["skill"] = skill_name` forced — reuse `build_audit_cmd`, don't duplicate its argv-building logic. Returns `True`/`False` based on subprocess exit code (0 = dispatch succeeded, i.e. the process ran to completion without crashing — this is NOT the same as the skill's output being good, that's the gate's job).
   - `make_gate_fn`'s returned callable, given `(skill_name)`, must call `gate.gate(SkillOutput(skill_name=skill_name, domain=domain, audit_dir=audit_dir, company_name=company_name), mechanical_cmd=..., factcheck_fn=..., adversarial_fn=..., quality_fn=...)` and map the result to `self_heal.GateResult(status=CLEAN|BLOCKED, fatal=(block_class==UNFIXABLE), findings=...)`.
   - **For factcheck_fn/adversarial_fn/quality_fn**: you do NOT have a real LLM call to wire in this task (that's out of scope — flagged by Task 3 as a Task 4/5 concern, and confirmed here: naming a real embedding/LLM call is Task 5's job per patch #9, not this one). Wire these three params to a clearly-labeled `NotImplementedError`-raising stub for now if you cannot call a real LLM from your sandbox — but structure `make_gate_fn` so swapping in real implementations later is a one-line change (a `TODO(Task 5)` comment naming exactly what needs to replace the stub). Do NOT silently make stages 2-4 always pass — that would defeat the entire point of this gate.
2. **Wire into `prism-runner.py`**: add a new code path (behind a feature flag / job field, e.g. `job.get("engine") == "v3"` or similar — your call, but it must be OFF by default so this change is safe to land without affecting the currently-live single-process behavior) that, when set, calls `self_heal.SelfHealLoop(dispatch=make_dispatch_fn(domain), gate=make_gate_fn(...), max_passes=3, on_attempt=<writes to module_executions via db_write.write_module_execution_row>).run_pipeline(SKILL_NAMES)` instead of the current `build_audit_cmd`+single-`Popen` path. **The existing v1/legacy single-process path must remain fully intact and be the default** — this is an additive capability, not a replacement, until the parity run (a later task) proves the new path works. Do not remove or weaken the existing path, tests, or the `job["phase"]`/`job["skill"]` clobber-bug fix already committed (see the file's own comments around line ~536 — do not reintroduce that bug).
3. **Tests**: unit tests for `make_dispatch_fn`/`make_gate_fn` (dependency-injected, no real subprocess/VPS calls — same DI pattern as everything else in this codebase) and for the new feature-flagged code path in `prism-runner.py`'s test file (find it — likely `tests/pipeline/test_runner_routes.py` or similar, check first). Do not weaken any existing test.

## Definition of done

- New tests pass; ALL existing tests in `tests/pipeline/` and any `prism-runner.py`-specific test file still pass (run them before and after, show both outputs).
- `ruff check . && ruff format --check .` clean on your new/changed files (pre-existing unrelated violations elsewhere are not your concern, same standard as Task 3's report).
- The legacy single-process path is provably unchanged — run its existing tests, confirm no diff in behavior for a job without the new flag set.
- Show all command output verbatim in your report.

## Output

Write your report to `docs/workspace/phase2-executioner/task-4a-report.md`. Return status DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED with the report path and a 3-line summary. If the real LLM-stage wiring genuinely can't be stubbed cleanly per the contract, say so as a concern — don't invent a fake LLM call to make tests "pass" hollow.
