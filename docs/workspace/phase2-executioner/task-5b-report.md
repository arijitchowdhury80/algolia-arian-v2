# Task 5b report — wiring gate()'s real LLM stages (factcheck/adversarial/quality)

Status: **DONE**

3-line summary: Built `prism_platform/pipeline/llm_stages.py` — real, schema-constrained `claude -p` implementations of the atomic per-claim `factcheck_fn(skill_output, claim)`/`adversarial_fn(skill_output, claim)`/`quality_fn(skill_output)` calls, plus `make_batch_factcheck_fn`/`make_batch_adversarial_fn` adapters matching `gate.py`'s actual batch-shaped injection types (`gate.FactCheckFn`/`gate.AdversarialFn`) so they're directly pluggable into `make_gate_fn`. 23 new unit tests against a fake `claude -p` pass, zero regressions (245 → 268 passing in `tests/pipeline/`), `ruff`/`ruff format`/`mypy --strict` clean; committed BEFORE attempting any live call, then verified 2 real `claude -p` calls (quality + factcheck) each under a 90s timeout, both returning valid schema-conforming verdicts.

Report path: `docs/workspace/phase2-executioner/task-5b-report.md`

---

## What was built

### `prism_platform/pipeline/llm_stages.py` (new file)

**Atomic, per-claim functions** — matching the brief's literal signatures exactly:
- `factcheck_fn(skill_output, claim, *, claude_cli_fn=_default_claude_cli) -> FactCheckVerdict` — the real judgment call behind `algolia-audit-factcheck`'s evidence-tier system.
- `adversarial_voter_fn(skill_output, claim, voter_id, *, n_voters=3, claude_cli_fn=...) -> AdversarialVoterVerdict` — one voter's ballot.
- `adversarial_fn(skill_output, claim, *, n_voters=3, claude_cli_fn=...) -> AdversarialVerdict` — N=3 independent voter calls, aggregated (`survives` = strict majority NOT refuted; a tie does NOT save the claim).
- `quality_fn(skill_output, *, claude_cli_fn=...) -> QualityScore` — the real Dimension 3 (instruction adherence) judgment from `algolia-audit-eval`.

**Batch adapters** — matching `gate.py`'s *actual* injection types (confirmed by reading `gate.py`'s real code, not just the brief's prose): `gate.FactCheckFn = Callable[[SkillOutput], tuple[FactCheckVerdict, ...]]` and `gate.AdversarialFn = Callable[[SkillOutput, tuple[str, ...]], tuple[AdversarialVerdict, ...]]` operate on a whole skill's claim set in one call, not one claim at a time like the brief's literal signatures describe:
- `make_batch_factcheck_fn(claims_fn, *, claude_cli_fn=...) -> gate.FactCheckFn`
- `make_batch_adversarial_fn(*, n_voters=3, claude_cli_fn=...) -> gate.AdversarialFn`
- `quality_fn` needs **no** adapter — its atomic signature already matches `gate.QualityFn` (`SkillOutput -> QualityScore`) exactly, so it's directly pluggable as-is (bind `claude_cli_fn` via `functools.partial` if a non-default is needed).

**Shared E2 plumbing** (schema-constrained, not free-form-prose-then-parse):
- `_schema_instruction(model)` renders the Pydantic model's `model_json_schema()` directly into the prompt with an explicit "respond with ONLY this JSON, no prose, no fences" instruction.
- `_parse_schema_response(raw, model, *, context)` extracts a JSON object from the response (tolerating a markdown code-fence wrapper, which `claude -p` produces even when told not to) and validates it via `model.model_validate_json(...)`, raising `ValueError` loudly — never silently defaulting/guessing a verdict — on malformed or schema-non-conforming output.
- The atomic subprocess mechanics (timeout handling, `subprocess.run(..., capture_output=True, text=True, timeout=...)`) are reused directly: every function's default `claude_cli_fn` is `chat_agent._default_claude_cli`, imported, not reimplemented, per the brief's explicit instruction.

## A design decision flagged explicitly (not a silent guess)

**E2 vs. true forced tool-use.** Bare `claude -p` (this project's locked no-Agent-SDK, no-raw-Messages-API decision) has no equivalent of the Anthropic Messages API's `tool_choice`-forced JSON schema — there is no mechanism to make the CLI structurally incapable of returning anything but valid schema JSON. E2 compliance here is *approximated*: the prompt renders the exact Pydantic JSON Schema and instructs the model to emit only that; the response is then validated against the same Pydantic model, and a non-conforming response raises loudly rather than being coerced or defaulted. This is weaker than true API-level tool-use forcing but is the best available approximation without reintroducing the Agent SDK or a raw API client into a subprocess-CLI-only codebase. Flagging this rather than silently claiming full E2 equivalence — someone should confirm this tradeoff is acceptable before Task 6's parity run leans on it at scale.

**The `make_gate_fn` default-wiring choice.** Per the brief's explicit instruction: I did **not** change `executioner.py`'s `make_gate_fn` defaults (`_stub_factcheck_fn`/`_stub_adversarial_fn`/`_stub_quality_fn`) to auto-wire these real functions. `make_gate_fn()` called with no overrides still fails loud with `NotImplementedError` on any skill that reaches stage 2+. This module's functions are built as *importable, explicitly-passed-in* replacements — Task 6's parity-run harness (or whoever wires `engine="v3"` into production) must explicitly do:
```python
make_gate_fn(
    domain, company_name, audit_dir,
    factcheck_fn=make_batch_factcheck_fn(claims_fn),
    adversarial_fn=make_batch_adversarial_fn(),
    quality_fn=quality_fn,
)
```
Changing the default would turn "fails loud" into "silently calls a real paid API by default" — exactly the class of silent behavior change this project's standards (and the brief itself) forbid.

## Concern flagged for Task 6 — the claim-extraction gap

`gate.FactCheckFn` takes **only** `SkillOutput` (no claim list) — `gate()` calls it once per skill and expects back every claim's verdict for that skill. There is no established mechanism anywhere in this codebase (Task 1 recon report, the interface contract, `gate.py`, or `executioner.py`) for turning "a skill's output directory" into "the concrete list of discrete factual claims to check." That extraction step is genuinely a different problem from the judgment call this task was scoped to build (the brief's three signatures are judgment calls, not claim extractors), so I did **not** invent a guessed heuristic (e.g. naive sentence-splitting a markdown file) to paper over it. Instead, `make_batch_factcheck_fn(claims_fn, ...)` requires `claims_fn` as a mandatory argument with no default — Task 6's parity harness must supply a real claim source (most plausibly whatever claim list `algolia-audit-factcheck`'s own skill logic already produces when it runs standalone) before stage 2 can run end-to-end across a real 16-skill audit. This is not a blocker for this task (the callable contract is complete and tested), but it IS a real gap standing between "this task is DONE" and "stage 2 actually runs in Task 6's parity test" — flagging loudly rather than silently assuming Task 6 will figure it out.

By contrast, stage 3 (`gate.AdversarialFn`) has **no such gap** — `gate()` itself already computes and hands over the `risky_claims` tuple (patch #1, claims stage 2 flagged with a weaker-than-`AUTHENTIC` evidence tier), so `make_batch_adversarial_fn()` needs no external claim source.

## Cost control — real expected call count for one full 16-skill audit run

Rough, stated as an order-of-magnitude estimate, not false precision:

- **Stage 4 (quality):** exactly **1 call per skill** → **16 calls** per audit (one `quality_fn` call per skill, always runs once mechanical + factcheck + adversarial pass).
- **Stage 2 (factcheck):** **1 call per claim per skill**. Claim count per skill is currently unknown (the claim-extraction gap above) — as an order-of-magnitude guess, a research-heavy skill's output (a few hundred lines of markdown) plausibly yields somewhere in the **5-20 checkable claims** range; across 16 skills that's roughly **80-320 calls** per audit. This is the dominant cost driver and the actual number should be measured empirically once Task 6 wires a real `claims_fn` and runs one real audit, not assumed from this guess.
- **Stage 3 (adversarial):** **N=3 calls per risky claim**, and (per patch #1, confirmed already implemented in `gate.py`) only fires for claims stage 2 flagged `WEBSEARCH`/`NO_SOURCE` evidence tier — i.e. a strict subset of stage 2's claims, likely a minority in a well-sourced audit. As a rough guess, if ~20% of stage 2's claims are risky, that's roughly **(80-320) × 0.2 × 3 ≈ 48-192 calls** per audit.
- **Total estimate for one full 16-skill audit, first pass, no retries:** roughly **150-500 `claude -p` calls**. Retries (self-heal's `max_passes=3` on `RETRY_WORTHY` blocks) could multiply the mechanical/quality-stage share of this by up to 3× in the worst case, but do NOT re-run stages that already produced a fatal `UNFIXABLE` block (patch #3 short-circuits those to `NEEDS_HUMAN` on first occurrence). This is a rough sanity-check number for Arijit, not a bid — the real number depends entirely on the (currently unbuilt) claim-extraction step's actual claim density per skill.

## Test results (verbatim)

```
$ python3 -m pytest tests/pipeline/test_llm_stages.py -v
======================= test session starts =======================
collected 23 items
... (all 23 PASSED, see full list below)
======================= 23 passed in 0.42s =======================
```

Full test list (23): prompt-construction tests for all 3 stages (claim/audit_dir/schema/skill-name/company-name presence, refuted-default-on-uncertainty instruction), response-parsing tests (valid JSON, markdown-fenced JSON, malformed JSON raises, missing required field raises, invalid Literal value raises), adversarial aggregation tests (majority-survives, majority-blocked, tie-does-not-survive, exact N-voter call count, loop-voter_id-wins-over-model-echo), quality-score tests (valid parse, wrong-dimension-literal raises, pluggable with a single positional arg matching `gate.QualityFn`), batch-adapter tests (`make_batch_factcheck_fn` calls `claims_fn` then one call per claim, zero claims → zero CLI calls; `make_batch_adversarial_fn` calls `adversarial_fn` per risky claim with the right total call count, zero risky claims → zero CLI calls), and one full `gate()` end-to-end wiring proof with all three real functions plugged in against fakes.

Full suite, before vs. after (via `git stash -u` on the same tree, confirming baseline independently rather than trusting a remembered number):

```
$ git stash -u && python3 -m pytest tests/pipeline/ -q   # BEFORE
245 passed, 18 skipped in 20.57s

$ git stash pop && python3 -m pytest tests/pipeline/ -q  # AFTER
268 passed, 18 skipped in 33.31s
```
268 = 245 baseline + 23 new (`test_llm_stages.py`). Zero regressions, 18 skipped identical to baseline (pre-existing docker/DB-gated tests, untouched).

```
$ python3 -m ruff check prism_platform/pipeline/llm_stages.py tests/pipeline/test_llm_stages.py
All checks passed!

$ python3 -m ruff format --check prism_platform/pipeline/llm_stages.py tests/pipeline/test_llm_stages.py
2 files already formatted

$ python3 -m mypy prism_platform/pipeline/llm_stages.py
Success: no issues found in 1 source file

$ python3 -m mypy prism_platform/
Found 28 errors in 10 files (checked 124 source files)
```
The 28 errors are the same pre-existing baseline files documented in Task 3/4a's reports (`v2/modules/intel_investor/collector.py`, `browser/tier2_stealth.py`, `v2/modules/intel_company/fetcher.py`, `integrations/scout.py`, `v2/synthesis.py`, `api/routers/knowledge.py`, `api/routers/audits.py`) — none of them is `llm_stages.py`, confirmed by the targeted run above being clean.

## Live proof (nice-to-have, attempted AFTER committing the tested core)

Per the brief's explicit instruction (a prior attempt lost all work by attempting a live call before committing), the tested/lint/mypy-clean core was committed first (`git log` shows commit `197adce`), THEN 2 real `claude -p` calls were attempted, each wrapped in an explicit `timeout=90` on the subprocess call:

1. **`quality_fn` against a real (fictional smoke-test) audit dir** — `/tmp/llm-stages-live-proof/Acme/01-company-context.md`, a deliberately thin/incomplete file. Real call, 37.4s elapsed, well under the 90s timeout. Returned a valid `QualityScore`: `score=0.5`, `passing_checks=1/10`, with reasoning correctly identifying every missing required output (no JSON file, no executives, no citation labels, no verification-gate handling) — i.e. the model did real, grounded, critical judgment against the actual file on disk, not a rubber-stamp pass.
2. **`factcheck_fn` against the same fixture, claim "Acme Corp is headquartered in Springfield."** — Real call, 26.9s elapsed. Returned `evidence_tier="AUTHENTIC"`, `verdict="SUPPORTED"`, `citation` pointing at the exact fixture file, reasoning quoting the matching line ("HQ: Springfield") — correct, grounded, and schema-valid.

Both calls parsed cleanly through `_parse_schema_response` with zero manual intervention, confirming the JSON-Schema-in-prompt + Pydantic-validate approach works against the real `claude` CLI, not just fakes. No adversarial-panel live call was attempted (would need 3x the calls for one claim) — the quality + factcheck proofs already demonstrate the shared parsing/prompt machinery end-to-end, and `adversarial_voter_fn`/`adversarial_fn` share that exact same `_parse_schema_response` path, already covered by 6 fake-LLM unit tests.

## Files

- `/Users/arijitchowdhury/Dropbox/AI-Development/PIP/prism_platform/pipeline/llm_stages.py` (new)
- `/Users/arijitchowdhury/Dropbox/AI-Development/PIP/tests/pipeline/test_llm_stages.py` (new)
- Committed as `197adce` on branch `feat/prism-e2e-cycle` (no changes to `gate.py`, `executioner.py`, `verdicts.py`, or `chat_agent.py` — pure addition).
