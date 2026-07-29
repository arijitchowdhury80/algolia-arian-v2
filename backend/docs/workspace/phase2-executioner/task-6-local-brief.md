# Task 6-local brief — run the v3 pipeline end-to-end LOCALLY (VPS SSH is down, don't wait on it)

VPS SSH is unreachable (local network issue, confirmed — see `task-6-report.md`). Rather than sit idle, prove the ENTIRE v3 pipeline works end-to-end on THIS machine, against real local infra, so the result is ready to push to the VPS the moment SSH comes back. This replaces waiting; it does not replace the eventual real VPS parity run (a local run proves the CODE works, not the VPS deploy — say this plainly in your report, don't conflate the two).

## Local infra now available (set up this session, confirm each still works before relying on it)

- **Real local Postgres 17 + pgvector**, full schema migrated: `DATABASE_URL=postgresql+asyncpg://prism:prism_dev_password@localhost:5432/prism` (matches `prism_platform/config.py`'s default exactly — no override needed). Verify: `psql -U prism -d prism -c '\dt'` should show 14 tables including `module_executions` and `report_chunks`.
- **Real local `claude` CLI**: `/Users/arijitchowdhury/.local/bin/claude`, confirmed working this session (Tasks 5b/5c both made real live calls with it).
- **Real algolia-* skills installed locally**: `~/.claude/skills/algolia-search-audit/` (confirmed present, used by Tasks 1/4b/5c this session for real script reads).
- **Real existing audit workspaces**: `/Users/arijitchowdhury/prism-data/audits/{Dell,jbl,lululemon}/` — pick ONE of these (already has real research output for all 16 skills) rather than running a full fresh 16-skill research audit (too slow/costly for this proof) — you're proving the GATE + DISPATCH mechanism against real existing output, not re-running discovery.

## What to build/run

1. **Read the full chain first**: `prism_platform/pipeline/{gate,verdicts,self_heal,db_write,executioner,llm_stages,claims}.py` and all of `docs/workspace/phase2-executioner/task-{3,4a,5b,5c}-report.md` — you are wiring pieces that 4 prior tasks each built and unit-tested in isolation; this is the first time they run together for real.
2. **Write a small local harness script** (`docs/workspace/phase2-executioner/local_parity_harness.py`, throwaway/scratch, not committed unless it proves useful) that:
   - Picks one real audit workspace (e.g. `lululemon`) and one real skill from it that HAS extractable claims per Task 5c's table (`algolia-intel-company`, `algolia-intel-investor`, `algolia-intel-industry`, or `algolia-audit-report` — NOT one of the 12 that return zero claims, that wouldn't exercise stage 2).
   - Builds a real `gate.SkillOutput` pointing at that real workspace.
   - Calls `gate.gate(skill_output, mechanical_cmd=..., factcheck_fn=llm_stages.make_batch_factcheck_fn(claims.extract_claims), adversarial_fn=llm_stages.make_batch_adversarial_fn(), quality_fn=llm_stages.quality_fn)` for real — real `factcheck_mechanical.py` subprocess call, real `claude -p` calls for stages 2-4.
   - Persists the result via `db_write.write_module_execution_row` against the REAL local Postgres (a real `INSERT`, not a fake).
   - Prints/logs the full `Verdict` (all 5 stages) and confirms the DB row exists afterward (`SELECT * FROM module_executions WHERE ...`).
3. **Run it for real**, at least twice: once against a skill you expect to PASS cleanly, once against a skill/claim you can perturb to deliberately trigger a BLOCK (e.g. temporarily feed a claim you know is false, or point at a workspace file with a broken citation) — this proves the gate actually catches bad output, not just rubber-stamps everything, per the original plan's core DoD ("a deliberately-injected bad output is blocked before the next skill dispatches — demonstrated live, not asserted").
4. **If you have time**: attempt the actual `self_heal.SelfHealLoop` orchestration over 2-3 skills from the same real workspace (not all 16 — that's real cost/time, use judgment on how many to prove the loop itself, not just the single-gate call), to prove the retry/escalation logic runs for real against real local calls, not just fakes.

## What this does NOT prove (say so explicitly, don't overclaim)

- Nothing about the actual VPS deploy step, its Python environment, whether `prism_platform`'s deps install cleanly there, or the real `run-audit.sh --skill` dispatch mechanism (that's still VPS-only and still blocked).
- Nothing about `ps aux` showing N separate OS processes on the VPS specifically (this local proof can show the LOGIC dispatches per-skill correctly, not the VPS's actual process model).
- This is a LOCAL correctness proof of the pipeline logic end-to-end with real external calls (LLM + DB + subprocess), not the VPS parity run itself.

## Output

Write your report to `docs/workspace/phase2-executioner/task-6-local-report.md` — real command output, real Verdict contents, real DB query results, real cost/call count for what you ran. Commit any harness script + report that's worth keeping (check branch first, don't touch main). Return status DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED with a clear statement of what's now proven vs. what still needs the VPS.
