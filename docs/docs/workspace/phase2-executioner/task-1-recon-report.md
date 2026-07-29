# Task 1 recon report — Phase 2 executioner (READ-ONLY)

Run 2026-07-13. All commands executed read-only via `ssh chowmes-vps` and local repo reads. No writes, no docker mutations, no file edits made anywhere.

---

## 1. `docs/plans/2026-07-03-per-skill-subagent-architecture.md` — executioner spec summary

**CONFIRMED read in full.** 15-line summary for later tasks:

- Target: `prism-runner.py` (host-side, deterministic code, NOT Cassandra/LLM) dispatches **one isolated sub-agent process per skill** (16 skills), waits for completion, runs a **merged quality gate** after each, then dispatches the next. No LLM decides control flow.
- Recommendation locked: direct `subprocess` dispatch of N independent `claude -p --skill X` processes from `prism-runner.py` — not routed through Hermes `delegate_task`.
- Merged gate = `factcheck_mechanical.py` (deterministic: required fields, links resolve, no self-contradiction, no leaked internal keys) + `algolia-audit-eval`'s judgment dims (completeness, source density, **instruction-adherence**, data accuracy). Single PASS/BLOCK verdict written to `module_executions`. LLM may override a mechanical BLOCK only with an itemized reason (visible, not silent).
- On BLOCK: re-dispatch **only that skill**, up to N attempts (self-heal), then `NEEDS_HUMAN` with skill+reason.
- MCP elimination table: `chrome` → used only by `algolia-audit-browser`, replace with direct Playwright/CDP; `apify` → used by `algolia-intel-social`/`news`, replace with plain REST; `crossbeam` → used only by `algolia-intel-partner`, investigate REST+API-key vs. OAuth-only.
- Other 13 skills use no MCP today (per the plan's original claim — see item 5, this is corrected below).
- Also in scope: auto-updating `reports/index.html` on publish (no manual HTML edit).
- Acceptance: 16 separate process invocations per run visible in `ps aux`, one `module_executions` row per skill, no MCP server spawned for skills that don't need it, a bad skill output caught+re-dispatched before the next skill runs.
- Explicitly out of scope: Cassandra personality work, multi-tenancy, PerimeterX bypass.
- Status header: "PLANNED — not started. Do not execute [that night]; definitive spec for the next build session."

---

## 2. Live `/opt/prism-executor/prism-runner.py` + `run-audit.sh` — dispatch model

**CHANGED from the plan's target, but also CHANGED from the plan's own description of "tonight's" (2026-07-03) state — this is a third, intermediate state, not yet the target.**

Evidence — both files carry a header claiming **"STAGED, NOT DEPLOYED"**, but a byte-for-byte diff proves they ARE the live deployed files:

```
$ diff docs/workspace/cassandra-tooling/staged/run-audit.sh <(ssh chowmes-vps "cat /opt/prism-executor/run-audit.sh")
IDENTICAL
```
VPS `run-audit.sh`: 9485 bytes, mtime 2026-07-02 22:18. VPS `prism-runner.py`: 34480 bytes, mtime 2026-07-03 01:10. The repo's `docs/workspace/cassandra-tooling/staged/` copies match these exactly — the "v2" build **was deployed** despite its own comment saying otherwise. This is stale documentation, not stale code — flag for correction in the header comments as a cheap follow-up.

**Actual dispatch loop** (`prism-runner.py:465-479`, `build_audit_cmd`):
```python
cmd = ["sudo", "-u", AUDIT_USER, "bash", RUN_AUDIT, job["domain"]]
if job.get("phase"): cmd += ["--phase", job["phase"]]
if job.get("skill"): cmd += ["--skill", job["skill"]]
if job.get("skip"):  cmd += ["--skip", job["skip"]]
```
And the actual spawn (`run_job`, line ~519):
```python
proc = popen_fn(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=EXEC_DIR)
```
**One `subprocess.Popen` call per job. No loop over skills inside the runner.** A default `/run` request (`{domain}` only, no phase/skill) produces exactly **one `claude -p` process for the entire 16-skill audit** — this is unchanged from what the plan called "tonight's actual" state.

What HAS changed: `run-audit.sh` now accepts `--phase <research|browser|report|factcheck>` (4 phases) or `--skill <name>` (1 of 16) to run a **single targeted subset against an existing workspace**, and the runner exposes this via `POST /rerun {slug, phase|skill}`. But this is an **operator/Cassandra-triggered manual rerun of one already-failed piece after the fact**, not the plan's automatic "dispatch skill 1 → gate → dispatch skill 2 → gate → ..." loop. The gate-and-loop control flow described in the plan's §2.1/§2.3/§4.3 does **not exist yet** — there is no code path that runs all 16 skills as 16 separate processes with a gate between each in a single `/run` call.

Skill-level visibility exists only as **log-scraping**, not process boundaries: `run-audit.sh` instructs the single `claude -p` process to print `>>> SKILL START: <name>` / `>>> SKILL DONE: <name>` markers, and `prism-runner.py`'s `detect_skill_states()` regexes the shared log tail for them. This is real, working progress-tracking (an improvement over the "unreliable markers" the plan flagged), but it is markers-inside-one-process, not 16 processes.

**Verdict: MISSING** (the per-skill-process architecture itself). **CONFIRMED** (one-process-per-phase-or-skill capability exists, but only for manual/rerun use, and the plan's automatic gate-and-loop is not built).

---

## 3. `validate-json-schema.py` + `module_executions` schema

**CONFIRMED** — exists and runs.
- Path: `/opt/prism-executor/arijit-skills/skills/algolia-audit-skills/algolia-search-audit/scripts/validate-json-schema.py`
- Confirmed executable: `python3 <path> --help` exits 1 with `❌ --help-audit-data.json not found` — i.e. it parsed `--help` as a positional path arg and ran its normal validation logic against a nonexistent file (no `argparse --help` support), proving the script executes rather than erroring on import/syntax.

**CONFIRMED** — `module_executions` table exists in Postgres. Note: the live DB connection differs from the script's hardcoded default — `prism-runner.py`'s `DEFAULT_DATABASE_URL` says `postgresql://prism:localdev@127.0.0.1:55432/prism`, but the deployed systemd unit overrides it via `/opt/prism-executor/.runner-db.env` → `DATABASE_URL=postgresql://prism:prism_dev_password@localhost:5432/prism` (confirmed via `systemctl cat prism-runner`). The real DB is the `prism-platform-postgres-1` container on port 5432, not port 55432.

Exact column list (`\d module_executions` via `docker exec prism-platform-postgres-1 psql -U prism -d prism`):
```
id uuid NOT NULL DEFAULT gen_random_uuid()   (PK)
audit_id uuid                                (FK -> audits.id ON DELETE CASCADE)
module_name text NOT NULL
module_version text NOT NULL
status text DEFAULT 'pending'
wave integer
output_json jsonb
sources_json jsonb
validation_json jsonb
duration_ms integer
llm_calls integer DEFAULT 0
llm_cost_usd numeric(8,4) DEFAULT 0
error_message text
started_at timestamptz
completed_at timestamptz
domain text NOT NULL DEFAULT ''
```
Indexes: unique `(audit_id, module_name)`, plus `(audit_id, status)` and `(domain, module_name)`.

---

## 4. `algolia-audit-factcheck` / `algolia-audit-eval` invocation surface

**CONFIRMED** — both SKILL.md files read in full from VPS runtime path (`/home/chowmesadmin/.claude/skills/<name>/SKILL.md`).

**`algolia-audit-factcheck`** (v2.0.0):
- Input: `$ARGUMENTS` = company name (workspace resolved at `$ALGOLIA_AUDIT_DIR/{CompanyName}/`); optional `--tier quick|standard|full` (default full), `--dim {1,4}`.
- Mandatory first action: read `~/.claude/skills/algolia-search-audit/AGENT-CONTEXT.md`.
- Structure: an evidence-tier system (AUTHENTIC/WEBFETCH/WEBSEARCH/NO_SOURCE) + a **blocking completeness gate** (ABX campaign, scoring matrix, discovery-question citations, strategic angles, browser findings) that must pass before scoring dimensions run at all.
- Mechanical gate is a real script, run first and treated as final: `factcheck_mechanical.py` (8 structural bug-class checks: financials, tech_stack, traffic %, hiring, partner_intel, screenshots, ...). Output is a PROCEED/WARN/BLOCKED verdict.

**`algolia-audit-eval`**:
- Input: `$ARGUMENTS` = skill name to evaluate + company slug (e.g. `algolia-audit-research Costco`).
- Output: `$ALGOLIA_AUDIT_DIR/{CompanyName}/eval/{skill-name}-eval-report.md`.
- Scoring: `SCORE = (passing_checks/total_checks) × 10`, no estimation.
- **Important discrepancy-relevant finding**: `algolia-audit-eval`'s SKILL.md explicitly says dimensions 1 (completeness), 2 (source density), 4 (data accuracy), 5 (no fabrication) are **already implemented by calling the SAME shared script** —
  ```
  python3 ~/.claude/skills/algolia-audit-factcheck/scripts/factcheck_mechanical.py --audit-dir "$AUDIT_DIR" --company "$COMPANY_NAME"
  ```
  Only Dimension 3 (instruction adherence) remains a separate LLM judgment call, done inside `algolia-audit-eval` itself. **This means the "merged gate" the 2026-07-03 plan calls for (§2.3, "built separately... never reconciled") is already partially built** — eval already delegates 4 of 5 dimensions to factcheck's mechanical script. The plan's problem statement is out of date; the remaining work is narrower than the plan assumes (mainly: wire this into the per-skill loop and write one verdict, not "reconcile two separate implementations from scratch").

---

## 5. All skills in the pipeline + MCP wiring

**16 skills confirmed** in the active pipeline (matches `SKILL_NAMES` in `prism-runner.py` exactly, and matches the ~16 the plan assumes):
`algolia-intel-company, algolia-intel-techstack, algolia-intel-traffic, algolia-intel-competitors, algolia-intel-financial-public, algolia-intel-financial-private, algolia-intel-investor, algolia-intel-social, algolia-intel-news, algolia-intel-hiring, algolia-intel-partner, algolia-intel-industry, algolia-intel-queries, algolia-audit-browser, algolia-audit-report, algolia-audit-factcheck`.

**MISSING/CORRECTED** — no skill has its own per-skill `.mcp.json` or MCP config file. Checked every skill directory on VPS (`find <skill-dir> -iname '*mcp*.json'`) — zero hits across all 16 (and all other algolia-* skills). MCP is wired **once, globally**, at `/opt/prism-executor/.mcp.json`, loaded for the entire shared `claude -p` process regardless of which skill is "currently running" (consistent with the whole-run-is-one-process finding in item 2).

**CORRECTED claim**: the brief's premise ("only `algolia-audit-browser` needs a live browser client") is wrong, and — importantly — **the 2026-07-03 plan doc itself already says this correctly** (§2.4 table). The global `.mcp.json` wires exactly 3 MCP servers:
- `chrome` (stdio, `chrome-devtools-mcp`) — used by `algolia-audit-browser` only.
- `apify` (stdio, `@apify/actors-mcp-server`, needs `APIFY_TOKEN`) — used by `algolia-intel-social` (LinkedIn/Twitter scrape) and potentially `algolia-intel-news`.
- `crossbeam` (streamable-http, OAuth) — used by `algolia-intel-partner` only. Config comment notes Crossbeam needs a one-time interactive OAuth login on this headless box that wiring alone doesn't satisfy — auth state on the VPS itself is unverified by this recon (out of scope: would require an actual call, not just reading config).

So: **3 skills need MCP** (browser, social, partner), not 1. The other 13 (company, techstack, traffic, competitors, financial-public, financial-private, investor, news, hiring, industry, queries, report, factcheck) use no MCP tool today, consistent with the plan.

---

## 6. `docker ps -a` baseline

Ran via `ssh chowmes-vps "sudo -n docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'"` (passwordless sudo works for chowmesadmin; docker group membership itself doesn't grant socket access without it).

```
NAMES                       IMAGE                                 STATUS
scout                       docker-scout                          Up 3 days (healthy)
cios-postgres               postgres:16-alpine                    Up 4 days (healthy)
umami                       ghcr.io/umami-software/umami:latest   Up 5 days
umami-db                    postgres:15-alpine                    Up 5 days
ac2-lab-backend             ac2-lab-backend:latest                Up 5 days (healthy)
hermes                      nousresearch/hermes-agent:latest      Up 4 days
prism-platform-postgres-1   postgres:16-alpine                    Up 3 days (healthy)
prism-platform-redis-1      redis:7-alpine                        Up 3 days (healthy)
hermes-prism                nousresearch/hermes-agent:latest      Up 5 days
caddy                       caddy:latest                          Up 5 days
```

**CONFIRMED**: no `Exited` containers present — `docker ps -a` returned only `Up` entries, all 10 containers healthy/running. Specifically:
- `hermes` and `hermes-prism` — both present, both `nousresearch/hermes-agent:latest`, confirming the two-instance setup from prior sessions is unchanged.
- `umami` — Up 5 days, no healthcheck configured (shows blank, not unhealthy — just no healthcheck defined).
- `cios-postgres` — Up 4 days (healthy).
- `ac2-lab-backend` — Up 5 days (healthy).
- `scout` — Up 3 days (healthy), on `127.0.0.1:8421`.
- Also present but not named in the brief: `prism-platform-postgres-1` / `prism-platform-redis-1` (the actual DB behind `module_executions`, see item 3) and `caddy` (reverse proxy) — both healthy/running.

---

## Discrepancies from `docs/plans/2026-07-12-prism-finishing-build-plan.md` / the 2026-07-03 architecture plan

1. **Biggest gap**: the per-skill dispatch-and-gate loop (plan's core deliverable) does not exist. The live system is still "one `claude -p` process runs all 16 skills," exactly as it was on 2026-07-03 when the plan was written to fix this. What's new since then is a **manual, operator-triggered** `--phase`/`--skill` rerun capability (`/rerun` endpoint) — useful, but not the automatic loop-with-gate the plan specifies. Any Phase 2 build plan that assumes "the runner already loops per skill" is building on a false premise.
2. **The merged quality gate is more built than the plan assumes.** `algolia-audit-eval` already calls `factcheck_mechanical.py` for 4 of 5 dimensions — the plan's framing ("built separately, never reconciled") is stale. Remaining work is: wire this existing mechanical+judgment combo into the per-skill loop and write one `PASS`/`BLOCK` row per skill to `module_executions`, not build the reconciliation from scratch.
3. **MCP-per-skill claim in the recon brief itself was wrong**, though the underlying architecture plan already had it right: 3 skills use MCP (browser/chrome, social/apify, partner/crossbeam), not 1. No skill has its own MCP config file — it's one global config for the whole shared process.
4. **Both live files falsely self-describe as "STAGED, NOT DEPLOYED"** — they are in fact the deployed, live code (byte-identical to the repo's `staged/` copies). This is a stale-comment / drift-tracking bug worth a one-line fix before anyone else reads these files and gets misled about what's actually running in production.
5. **DB connection string drift**: `prism-runner.py`'s hardcoded default (`127.0.0.1:55432`, password `localdev`) does not match the actual deployed connection (`localhost:5432`, password `prism_dev_password`, via `/opt/prism-executor/.runner-db.env` + systemd `EnvironmentFile`). Not a functional bug (the override works), but anyone reading only the script's docstring/default would target the wrong port/credentials.
6. **Skill symlink drift is still only partially fixed** (confirms prior memory `feedback-vps-skill-install-not-symlinked`): on the VPS, only `algolia-audit-factcheck` and `algolia-intel-traffic` are actual symlinks into `/opt/prism-executor/arijit-skills/skills/algolia-audit-skills/`. The other 14 pipeline skills (company, techstack, competitors, financial-*, investor, social, news, hiring, partner, industry, queries, browser, report) are still plain copied directories at `/home/chowmesadmin/.claude/skills/`, not symlinks — meaning a future edit to the source-of-truth `arijit-skills` repo will NOT propagate to those 14 skills' runtime copies without a manual redeploy, same class of bug flagged before.

---

**Status: DONE_WITH_CONCERNS**

Report: `docs/workspace/phase2-executioner/task-1-recon-report.md`

3-line summary of the most important discrepancy: The live VPS executor still runs all 16 skills inside one shared `claude -p` process (unchanged since 2026-07-03) — it only gained a manual, operator-triggered `--phase`/`--skill` rerun path, not the automatic per-skill dispatch-and-gate loop the plan requires. Any Phase 2 build must treat the per-skill loop as unbuilt, even though the merged-gate logic (factcheck+eval) is further along than the plan assumes. Both `prism-runner.py` and `run-audit.sh` carry false "STAGED, NOT DEPLOYED" headers despite being the actual live production code.
