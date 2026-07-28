# Task 5b brief — wire gate()'s real LLM stages (factcheck/adversarial/quality)

Read first, in full: `docs/workspace/phase2-executioner/interface-contract.md`, `docs/workspace/phase2-executioner/task-3-gate-report.md`, `docs/workspace/phase2-executioner/task-4a-report.md` (esp. its "Concerns" #2 — this task is exactly what it flagged as still-needed), and `prism_platform/pipeline/gate.py` + `verdicts.py` + `executioner.py` (all committed, read the real code, not just the reports).

## The gap

`gate()` (Task 3) and `make_gate_fn()` (Task 4a) are both built and tested, but stages 2-4 (factcheck, adversarial, quality) take injectable callables — `factcheck_fn`, `adversarial_fn`, `quality_fn` — that currently default to stub functions raising `NotImplementedError` with a `TODO(Task 5)` marker (this task IS that follow-up, despite the stub's comment saying "Task 5" — Task 5 built the separate report-chat agent, not this). Without real implementations, `engine="v3"` cannot get past stage 1 (mechanical) for any skill — Task 6's parity run is blocked on this.

## What to build

Each is a schema-constrained `claude -p` call (E2: forced tool-use JSON against the exact Pydantic model in `verdicts.py` — never free-form prose parsed after the fact). Reuse the `claude -p` subprocess pattern already built in `prism_platform/pipeline/chat_agent.py` (Task 5) for the actual subprocess-invocation mechanics (timeout handling, stdout capture) — don't reinvent that part.

1. **`factcheck_fn(skill_output: SkillOutput, claim: str) -> FactCheckVerdict`**: the real judgment call behind `algolia-audit-factcheck`'s evidence-tier system (AUTHENTIC/WEBFETCH/WEBSEARCH/NO_SOURCE — read that skill's SKILL.md, already summarized in the Task 1 recon report §4, for the real evidence-tier definitions). Given a specific claim from the skill's output + its audit_dir, ask the model to classify the claim's evidence tier and verdict (SUPPORTED/UNSUPPORTED/CONTRADICTED), forcing tool-use output against `FactCheckVerdict`.
2. **`adversarial_fn(skill_output: SkillOutput, claim: str) -> AdversarialVerdict`**: N=3 independent voter calls (patch #1 — only invoked by `gate.py`'s stage 3 on claims already flagged risky, you're just building the callable, not re-deciding when it fires). Each voter is a separate `claude -p` call told to try to refute the claim, default `refuted=true` if uncertain, schema-constrained against `AdversarialVoterVerdict`. Aggregate into `AdversarialVerdict.survives` (majority not-refuted).
3. **`quality_fn(skill_output: SkillOutput) -> QualityScore`**: the real Dimension 3 (instruction adherence) judgment from `algolia-audit-eval` (per Task 1 recon report §4 — Dimensions 1/2/4/5 already delegate to `factcheck_mechanical.py`, only Dimension 3 needs an LLM call). Schema-constrained against `QualityScore`.

## Cost control (patch #1, already partially handled by gate.py's stage-3 risk-gating — confirm, don't re-litigate)

State the real expected `claude -p` call count for one full 16-skill audit run with these wired in (roughly: 1 factcheck call per claim per skill for stage 2, N=3 adversarial calls only for claims stage 2 flagged as risky, 1 quality call per skill for stage 4) — a rough number, not a guess dressed as precision, so Arijit can sanity-check cost before this runs in the parity test.

## Testing constraint

You likely don't have live `claude -p` billing/access confidence in this sandbox for high-volume testing — that's fine. Follow the same dependency-injection discipline as everything else in this codebase: the actual subprocess-calling function should be a thin, separately-testable wrapper (inject a fake `claude -p` response in unit tests, same pattern `chat_agent.py`/`self_heal.py` already use), so the PROMPT-CONSTRUCTION and RESPONSE-PARSING logic is fully unit tested even if you can't run hundreds of real calls.

**COMMIT AS SOON AS unit tests (fake-LLM) pass and lint/mypy are clean — before attempting any live `claude -p` proof.** The live end-to-end proof (1-2 real calls) is a nice-to-have for your report, NOT required for DONE status. A prior attempt at this task stalled for 10+ minutes on a live end-to-end call with no timeout and lost all its work because nothing had been committed yet. If you do attempt a live call: wrap it in an explicit `timeout=` (e.g. 90s) on the subprocess call so a hang fails loudly instead of hanging the whole task, and only attempt it AFTER committing the tested, stub-verified work.

## Definition of done

- All 3 functions implemented, wired as the real (non-stub) defaults... actually: per Task 4a's design, `make_gate_fn`'s stub defaults exist so that calling it with no overrides fails loud rather than silently passing. Your job is to build the REAL implementations as importable functions (e.g. in a new `prism_platform/pipeline/llm_stages.py`) that `executioner.py`'s caller (or Task 6's parity-run harness) explicitly passes in — do not silently change `make_gate_fn`'s defaults to auto-wire your new real functions without flagging that choice, since that changes "fails loud by default" into "calls a real paid API by default," which is exactly the kind of silent behavior change this project's standards forbid. State clearly in your report which choice you made and why.
- Unit tests for prompt construction + response parsing for all 3 functions (fake LLM responses).
- `ruff`/`ruff format`/`mypy --strict` clean, existing test suite unmodified/still passing — show output.
- Report real vs. estimated call-count/cost for a full audit.

## Output

Write your report to `docs/workspace/phase2-executioner/task-5b-report.md`. Return status DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED with the report path and a 3-line summary.
