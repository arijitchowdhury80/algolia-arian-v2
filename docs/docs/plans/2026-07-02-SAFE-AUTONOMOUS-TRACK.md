# SAFE AUTONOMOUS TRACK — work while Arijit is away (demo tomorrow)

**Set 2026-07-02.** Arijit is away (at school) and has a **LIVE DEMO TOMORROW** on the running PRISM system. This track defines the ONLY work permitted autonomously. It is scoped to be **100% non-destructive to the live system.**

## RULE ZERO — DO NOT TOUCH THE LIVE WORKING SYSTEM
The demo runs on live prod. Breaking it is unacceptable. **You may NOT, under any circumstance, without Arijit present to gate it:**
- Deploy anything to the VPS live serving path, or push to `feat/prism-vps-hosting` (that branch auto-deploys + hard-resets the box).
- Restart or reconfigure any live service: `hermes-prism`, `prism-runner`, `prism-chat-proxy`, `prism-platform`, `caddy`, `scout`.
- Change auth / Clerk / the chat-proxy gate.
- Migrate audit data, write to the live Postgres in any way that affects serving, or re-point `run-audit.sh` / the runner.
- Touch the lululemon report (it is DONE + live + correct — leave it alone).
- Run a live audit or anything that consumes prod resources during demo prep.

**If any task would touch live prod → STOP, write it to the "GATED — needs Arijit" list at the bottom, and move on.** When in doubt, treat it as gated.

**After ANY read-only VPS action, re-verify the live system is healthy:** `curl -s -o /dev/null -w "%{http_code}" https://prism.chowmes.com/` (expect 200), `systemctl is-active hermes-prism prism-runner prism-chat-proxy` (all active). If anything changed, STOP and report.

## CONTEXT TO READ FIRST
- `docs/plans/2026-07-02-cassandra-airtight-pipeline-goal.md` — the full airtight-pipeline plan (4 parts). You are doing ONLY the safe slices below.
- `MEMORY.md` + memory `project-prism-airtight-pipeline-plan`, `project-cassandra-observability-gap`, `reference-two-repos-prism-vs-pip`.
- VPS access (READ-ONLY use only): `ssh -i ~/.ssh/chowmes_ed25519 chowmesadmin@72.61.72.147`. Runner token in systemd env. You may READ/inspect freely; you may NOT modify live services/config/deploys.

## THE SAFE WORK (do these, in order)

### A. Backups — protect the data (highest value, non-destructive)
Set up durable backups WITHOUT modifying the running system. All read-only + additive:
1. `pg_dump` of the prism-platform Postgres (read-only) → write the dump to a new local/off-box location.
2. Create a NEW PRIVATE GitHub repo `prism-data` (do NOT use prism-hub — its push webhook deploys). Commit the pg_dump + an rsync'd copy of `/opt/prism-executor/audits/` (raw research + screenshots) + `/root/.hermes-prism/reports/` there. This is the "heart and soul" off-host backup Arijit asked for.
3. Add a nightly cron (additive — a new cron entry only) that repeats the dump + push. Do NOT restart anything.
4. **Verify a restore works** into a SCRATCH throwaway Postgres (NOT the live one) — dump → restore → diff row counts.
5. Prove it: show the repo exists + has the data, and the restore diff.
**Guardrail:** dumping + copying + a new repo + a cron entry do not alter the running system. After each step, run the health check above.

### B. Multi-tenancy & scalability architecture DESIGN doc (pure research/writing — zero prod risk)
Produce `docs/plans/multi-tenancy-architecture.md` answering Part 2 of the main plan: how 20 AEs each get their own Cassandra (one Hermes instance/tenant vs multi-session vs per-tenant containers), how 20 parallel audits run (concurrency/queue/worker pool), tenant data isolation (per-tenant schema/RLS vs per-tenant DB), auth (Clerk multi-tenant), scaling browser/proxy + SimilarWeb HITL across tenants, what breaks first at 20 tenants, migration path, rough infra cost curve. Dispatch parallel research sub-agents (sonnet) → opus synthesis. Decision-grade, with a recommendation.

### C. Build the isolated code (NEW files + tests, NOT wired into live)
Write these as standalone, tested code in the repo — do NOT deploy or integrate into the live pipeline (that's gated):
1. **Deterministic block-detector** (plan §0.2): pure-code module + tests. Given a page's headers/DOM/status, returns `OK | BLOCKED_BY=<vendor> | SOFT_BLOCK` using the per-vendor signals (DataDome/Akamai/Cloudflare/Imperva). Unit tests with fixture pages.
2. **Scripted self-heal loop** (plan §1.3) as a standalone module + tests: after each phase run the mechanical gate, on BLOCKED re-dispatch up to N, escalate. Write it so it CAN later wrap the runner, but do NOT wire it into the live runner now.
3. **Screenshot timing/quality gate** (plan §3.1b/§3.1c): a checker that verifies a capture has real content (waited for load, query present, not black/popup) + tests.
Each ships with tests you run and show passing. These are drop-in modules for the gated integration later.

## MODEL ROUTING / COST
Orchestrate on the session model. Route bulk sub-agents DOWN: research sweeps + bounded coding + tests = sonnet; grunt/inspection = haiku; only design synthesis + critical review = opus. Don't run grunt work on opus.

## DELIVERABLES FOR ARIJIT'S RETURN
- Backups live + restore-proven (repo link + evidence).
- `multi-tenancy-architecture.md` with a recommendation.
- Block-detector + self-heal-loop + screenshot-gate modules, tested (show test output).
- A concise status report + the "GATED — needs Arijit" list (everything that touched, or would touch, live prod and is waiting for his sign-off).

## GATED — needs Arijit present (DO NOT do autonomously)
(Append here anything you hit that requires touching live prod. Starter list:)
- Wiring the block-detector / self-heal loop / new runner routes into the LIVE runner + restarting it.
- The granular per-skill runner routes + plugin tools deploy.
- Cassandra model/tooling changes + hermes-prism restart.
- DB-as-source-of-truth cutover + historical migration.
- Any prod deploy or service restart.
