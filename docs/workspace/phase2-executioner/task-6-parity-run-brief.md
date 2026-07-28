# Task 6 brief — non-prod parity run (Track C cutover-order) — HARD SEQUENCE POINT

Read first, in full: `docs/plans/2026-07-12-prism-finishing-build-plan.md` PHASE 2 goal-card output #5 + critique patches #5/#6, and every prior task report in `docs/workspace/phase2-executioner/` (1 through 5c) — you are the integration point for all of them.

**This is the hard gate before Hermes removal.** Do NOT touch Hermes/Cassandra containers. Do NOT run `docker rm` anything. Your job ends at "report parity result" — the STOP-and-report-to-Arijit step happens after you, in the controller's hands, not yours.

## What now exists (all committed, verified this session)

- `prism_platform/pipeline/{gate,verdicts,self_heal,db_write,executioner,chat_agent,llm_stages,claims}.py` — the full 5-stage verification pipeline, real LLM-backed factcheck/adversarial/quality stages, real claim extraction, all unit-tested (285 passing tests).
- `run-audit.sh` on the VPS already supports per-skill MCP-scoped dispatch (Task 4b, live-verified).
- `prism-runner.py`'s staged copy (`docs/workspace/cassandra-tooling/staged/prism-runner.py`) has an opt-in `engine="v3"` path wired to `self_heal.SelfHealLoop` + the new gate — but **this has never been deployed to the VPS**. The VPS `/opt/prism-executor/prism-runner.py` still only has the v1 dispatch loop as of Task 1's recon.

## What to build/run

1. **Deploy the updated `prism-runner.py` (with the v3 path) + the `prism_platform` package to the VPS non-prod path.** Confirm how `prism_platform` is currently made importable from `/opt/prism-executor/` on the VPS (check for a venv, a pip install, a PYTHONPATH — Task 1's recon didn't check this specifically, verify it live). This may require installing `prism_platform`'s dependencies (pgvector, sentence-transformers per Task 5, added to `pyproject.toml`) on the VPS — check what's already there before assuming a fresh install is needed.
2. **Wire real callables for `make_gate_fn`'s LLM stages** per Task 5b/5c's explicit non-default pattern:
   ```python
   from prism_platform.pipeline import llm_stages, claims
   make_gate_fn(domain, company_name, audit_dir,
       factcheck_fn=llm_stages.make_batch_factcheck_fn(claims.extract_claims),
       adversarial_fn=llm_stages.make_batch_adversarial_fn(),
       quality_fn=llm_stages.quality_fn)
   ```
3. **Run ONE real audit end-to-end through `engine="v3"`** on a non-prod path — `prism2.chowmes.com`'s basic-auth surface, or simply invoking `prism-runner.py`'s job runner directly on the VPS without going through the public URL if that's simpler and equally valid for this test. Pick a company NOT already audited recently (to get a fresh comparison) or re-run an existing one if that's more practical — your call, state which and why.
4. **Patch #5 (parity comparison)**: compare the v3 run's output against a Hermes-run (v1) baseline for the SAME company (an existing audit, if you re-ran an existing company; otherwise the closest available baseline). Diff ONLY structurally-stable fields (schema shape, citation presence, score-within-tolerance) — NOT raw scraped content (news/social/traffic numbers legitimately drift between runs, that's not a regression). State exactly which fields you compared and the result for each.
5. **Patch #6 (Clerk-auth) — SCOPED DOWN, see below.** Task 5's report found there's no per-user-slug authorization model in the live stack at all — patch #6 as literally specified (test that an unauthorized user is rejected) tests a feature that doesn't exist. Do NOT attempt to build that model as a side effect of this task. Instead: confirm the NEW chat agent (Task 5's `/api/v1/audits/{audit_id}/chat`) is reachable through whatever auth currently gates `prism.chowmes.com` chat requests TODAY (even if that gate is weak/nonexistent per Task 5's finding) — i.e. prove you haven't made auth WORSE than it already is, not that you've built auth that doesn't exist yet. State this scoping explicitly in your report; this is a known, already-flagged gap, not something to silently skip or silently over-claim as tested.

## Definition of done (per the goal-card, patch-adjusted)

- A deliberately-injected bad output (fabricated stat or broken citation, or simply a skill whose claim fails factcheck for real) is blocked by `gate()` before the next skill dispatches — shown live, actual BLOCK verdict, not asserted.
- `ps aux` on the VPS during the real run shows N separate skill subprocesses (or as many as the run reaches before any NEEDS_HUMAN stop), not one long-lived process.
- `module_executions` has real rows for the run with real verdicts (not all-PASS-by-default) — query and show them.
- Parity result stated plainly: MATCH / MATCH-WITH-EXPLAINED-DRIFT / MISMATCH, with the specific field-by-field evidence either way.
- Real `claude -p` call count and rough cost for this one real run, compared against Task 5c's ~21-32-call estimate (was this one run in that range? Higher? Why?).
- Rollback path (§7 of the plan doc) confirmed to exist — is there an archived image/compose file for Hermes already, or does this task need to create one? Check, don't assume.

## Kill condition

If the v3 pipeline fails to complete for reasons unrelated to the gate working-as-designed (a real infra/deploy problem, not a legitimate BLOCK/NEEDS_HUMAN), stop and report BLOCKED with the specific failure — do not force it through or paper over a broken deploy step.

## Output

Write your report to `docs/workspace/phase2-executioner/task-6-report.md`. Return status DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED with the report path and a clear parity verdict. **Do not proceed to any Hermes-touching step regardless of your result — that decision belongs to the controller/Arijit, not this task.**
