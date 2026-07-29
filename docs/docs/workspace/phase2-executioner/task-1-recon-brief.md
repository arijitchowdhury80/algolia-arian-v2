# Task 1 brief — Phase 2 recon (READ-ONLY)

Source: `docs/plans/2026-07-12-prism-finishing-build-plan.md`, PHASE 2 goal-card "Input" list + critique patch #10.

You are running READ-ONLY recon against the live VPS (`chowmes-vps`, SSH) and the PIP repo. Do NOT modify anything — no writes, no `docker` mutations, no file edits. This is fact-gathering to de-risk the build that follows.

## What to verify (report each as CONFIRMED / CHANGED / MISSING, with the actual evidence — command + output snippet, not a paraphrase)

1. Read `docs/plans/2026-07-03-per-skill-subagent-architecture.md` in full (in this repo). Summarize its executioner spec (dispatch model, MCP-per-skill table) in <15 lines — this is context for later tasks, not to be re-derived by them.
2. SSH to `chowmes-vps`, read the CURRENT `/opt/prism-executor/prism-runner.py` and `run-audit.sh` in full. Confirm/contradict: does it currently dispatch one `claude -p` process per PHASE (not per skill)? Quote the actual dispatch loop.
3. Confirm `validate-json-schema.py` exists (path + confirm it runs) and confirm the `module_executions` table exists in the Postgres DB with its current schema (`\d module_executions` or equivalent). Report the exact column list.
4. Confirm current invocation surface (CLI args, expected stdin/output shape) for the `algolia-audit-factcheck` and `algolia-audit-eval` skills — read their SKILL.md files (repo path: `~/.claude/skills/algolia-search-audit/` or wherever they're symlinked from per memory `reference-skills-symlinked-to-repo`).
5. List all skills currently in the audit pipeline (should be ~16 per the plan). For each, state whether it currently has an MCP client config wired (look for `.mcp.json` or equivalent per-skill config) — confirm or correct the claim that only `algolia-audit-browser` needs a live browser client. Include Crossbeam and any others with MCP configs.
6. Run `docker ps -a` on the VPS. Report every container's name + status (`Up`/`Exited`/etc). Specifically confirm: the two `hermes`/`hermes-prism` (`nousresearch/hermes-agent`-based, per prior session) containers are still present, AND confirm the health/status of `umami`, `cios-postgres`, `ac2-lab-backend`, `scout` (unrelated live services this build must not disturb later, per critique patch #10 — just capture their current baseline status now).

## Output

Write your findings to `docs/workspace/phase2-executioner/task-1-recon-report.md`, one numbered section per item above, each with CONFIRMED/CHANGED/MISSING + evidence. End with a short "Discrepancies from the plan doc" section listing anything that differs from what `docs/plans/2026-07-12-prism-finishing-build-plan.md` assumes.

Return status: DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED, plus the report file path and a 3-line summary of the most important discrepancy (if any).
