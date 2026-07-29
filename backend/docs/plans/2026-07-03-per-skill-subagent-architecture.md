# PLAN — Per-Skill Sub-Agent Architecture, Merged Quality Gate, MCP Elimination

**Author:** Claude Sonnet 5, 2026-07-03 (post-marathon session, written at Arijit's explicit direction)
**Status:** PLANNED — not started. Do not execute tonight; this is the definitive spec for the next build session.
**Supersedes/refines:** `docs/plans/2026-07-02-cassandra-airtight-pipeline-goal.md` §3 (architecture), §4.1 Phase 1.1-1.3 (execution model), §4.1 Phase 2.2/2.4 (delegation).

---

## 1. Why this plan exists

Tonight's session (2026-07-03) was five hours of live-production firefighting on Cassandra and the audit pipeline. Two runs (Belk, Dell) completed and published, but investigating their actual quality surfaced that the current pipeline architecture does not match what Arijit originally specified, and never has:

- **Specified:** one sub-agent per skill, each with its own isolated context, dispatched and supervised by Cassandra. No MCP — direct HTTP calls to underlying services.
- **Actual (verified tonight):** `run-audit.sh` fires ONE `claude -p` process per audit, with all 16 skills described in a single prompt, running as one shared conversation for 30-58 minutes straight (confirmed via `ps aux` — single PID, single process, for the full run). Cassandra is not in this loop at all; she only reads the finished `audit-data.json` afterward to answer chat questions. MCP servers (chrome, apify, crossbeam) are loaded for the entire session via `--mcp-config --strict-mcp-config`, regardless of which skill is currently running.

This gap explains several of tonight's real findings:
- Factcheck runs once, at the very end, over the whole assembled result — not per-skill. A bad skill output isn't caught until the entire 16-skill run is done.
- `algolia-audit-eval` (the actual quality/completeness scorer) never runs at all — nothing calls it. Belk and Dell published with a factcheck pass but zero quality-eval.
- The Belk playbook correctly identified a warm intro path to the CIO, but the generated cold-outreach email ignored that insight — a symptom of no per-skill review pass ever checking a skill's real-world usefulness before moving on.
- Every skill's context is bloated with MCP tool definitions for tools that specific skill never touches (e.g. `algolia-intel-company` doesn't need chrome/crossbeam/apify, but they're loaded into its context anyway because everything shares one session).

## 2. Target architecture

### 2.1 Orchestration layer — deterministic, not LLM-driven

Per the already-approved design in the 2026-07-02 plan (§3): *"Deterministic orchestrator (host-side, scripted, no LLM in the control loop)... this layer must be CODE, so self-heal is guaranteed, not emergent."* That principle resolves the apparent tension between "Cassandra dispatches sub-agents" and "don't depend on LLM judgment for critical control flow":

- **`prism-runner.py` (upgraded) is the actual dispatcher.** It owns the loop: for each of the 16 skills, spawn one isolated sub-agent invocation, wait for completion, run the merged gate (§2.3), and only then dispatch the next skill. This loop is plain code — no LLM decides whether to proceed.
- **Cassandra is the supervisory/reporting layer on top**, exactly as scoped in the existing plan's §3 and §4.1 Phase 2: she observes progress via `live_status`, gets asked "how's it going," escalates to Arijit on a stuck/NEEDS_HUMAN job, and can trigger a targeted re-run via `rerun`. She does not decide whether skill 7 is allowed to run — the deterministic loop already decided that.
- Open decision to resolve at build time: whether "one sub-agent per skill" means the runner directly shells out to N independent `claude -p --skill X` processes (simplest, most deterministic, no dependency on Hermes's `delegate_task`), or whether it routes through Hermes's `delegate_task` tool from within Cassandra's own agent loop (keeps everything inside Hermes, but reintroduces an LLM decision point into what should be a deterministic dispatch). **Recommendation: direct subprocess dispatch from prism-runner.py** — simpler, matches the "deterministic orchestrator" principle exactly, and doesn't require `delegation.max_spawn_depth`/`orchestrator_enabled` config changes on the Hermes side. Revisit only if a real need for Hermes-native delegation emerges.

### 2.2 Per-skill isolation

Each of the 16 skills (`algolia-intel-company`, `algolia-intel-techstack`, ... `algolia-audit-factcheck`) runs as an independent process with:
- Its own fresh context — no accumulated conversation history from the other 15 skills.
- Only the tools/MCP-equivalent HTTP clients that specific skill actually needs (see §2.4 — most skills need none).
- Its own log file, own timeout, own retry count, own DB row (`module_executions`, already exists in the schema per the 2026-07-02 plan).

This also fixes tonight's observability gap: `SKILL START`/`SKILL DONE` markers were supposed to demarcate progress inside the single shared session but were unreliably emitted (confirmed: Belk's run.log had zero such markers despite the skill work genuinely happening). Per-skill subprocesses make this moot — the runner knows a skill is running because it dispatched that specific process, and knows it's done because that process exited. Status is structural, not dependent on the agent remembering to print a marker.

### 2.3 Merged quality gate (replaces two redundant checks with one)

Tonight's finding: `algolia-audit-factcheck` and `algolia-audit-eval` overlap significantly — both check for fabrication; eval's "completeness" dimension overlaps factcheck's structural checks. Built separately, in different sessions, never reconciled.

**New design: one gate, run immediately after each skill's sub-agent completes, before the next skill dispatches.**

The gate combines:
- **Deterministic layer** (from `factcheck_mechanical.py`): required fields present, source links resolve and actually support the claim, no internal self-contradiction, no `%%`/formatting defects, no raw internal keys leaking to customer-facing text.
- **Judgment layer** (from `algolia-audit-eval`'s dimensions): completeness relative to what that skill is supposed to produce, source density, **instruction-adherence** (this is the dimension that would have caught the CIO cold-email-ignoring-the-warm-path problem — a judgment check on "does this output actually reflect its own stated strategic insight"), data accuracy.
- Single verdict: **PASS** or **BLOCK**, with itemized reasons either way, written to `module_executions`.
- **Hard rule carried over from tonight's decision on factcheck override**: an LLM judgment layer may recommend PASS on a mechanically-BLOCKED item only with an itemized, specific reason per flag (as the existing factcheck already does reasonably well — see Belk's `FACTCHECK_GATE.md` C1/warnings handling, which was genuinely good work, not rubber-stamping). This override behavior should remain visible/auditable, not silent.
- On BLOCK: the orchestrator re-dispatches that single skill (not the whole audit) up to N attempts (self-heal loop, per the 2026-07-02 plan §1.3), then marks `NEEDS_HUMAN` with the specific skill and reason.

### 2.4 No MCP — direct HTTP calls

Audit which of the 16 skills actually uses which MCP server today, then replace each with a direct HTTP/library call inside that skill's own isolated process:

| Current MCP server | Used by | Replacement |
|---|---|---|
| `chrome` (chrome-devtools-mcp, stdio) | `algolia-audit-browser` only | Direct Playwright/Chrome DevTools Protocol calls (a standalone `scripts/audit-browser.js` with Playwright+stealth already exists on disk per an earlier session's audit — use it directly, no MCP wrapper) |
| `apify` (@apify/actors-mcp-server, stdio) | `algolia-intel-social`, possibly `algolia-intel-news` | Apify's plain REST Actors API, called directly with `APIFY_TOKEN` — no MCP layer needed, Apify's API is already a normal HTTP API underneath the MCP wrapper |
| `crossbeam` (streamable-http + OAuth) | `algolia-intel-partner` only | Needs investigation: does Crossbeam expose a plain REST API with a static API key (bypassing OAuth entirely), or is MCP+OAuth the only sanctioned integration? If REST+API-key exists, use it directly. If not, this is the one case where some persistent-session mechanism is unavoidable — decide explicitly rather than defaulting to keeping MCP. |

The other 13 skills (company, techstack, financial-*, investor, news, hiring, industry, queries, competitors, report, factcheck) use no MCP tools at all today — they'll simply run without any MCP config once the shared-session pattern is broken, which is most of the win with the least new code.

### 2.5 Reports index — systematic, not manual

Separately raised tonight and folded in here since it's part of the same "make publish actually mean something" theme: on a successful publish, the runner should automatically add/update the report's card in `reports/index.html` (sorted alphabetically or by audit date — exact sort TBD, revisit index page design later per Arijit), instead of requiring a manual HTML edit per report (as was done ad-hoc for Belk tonight).

## 3. What this does NOT include (explicitly out of scope for this plan)

- Rebuilding Cassandra's personality/voice work — that was tonight's separate (already-shipped) fix set.
- Multi-tenancy (Part 2 of the 2026-07-02 plan) — unrelated, separate track.
- Bot-wall bypass tooling for Belk's PerimeterX block — Arijit's standing decision is detect-and-flag, $0 spend, not in scope here.

## 4. Build sequence (for the next session, not tonight)

1. **Design/ADR the exact per-skill dispatch mechanism** (direct subprocess vs Hermes `delegate_task` — recommendation above) and get explicit sign-off before writing code.
2. **Build the merged gate** — consolidate `factcheck_mechanical.py` and `algolia-audit-eval`'s scoring logic into one script/skill with one verdict.
3. **Upgrade `prism-runner.py`** to loop over the 16 skills individually (`--skill X` per dispatch, already partially supported), running the merged gate after each, with the self-heal retry-until-clean loop from the 2026-07-02 plan §1.3.
4. **Strip MCP skill-by-skill**, per the table in §2.4, verifying each replacement against a real API call (Read Receipt required per the protocol-read-receipt discipline before any wire-format code).
5. **Wire Cassandra's reporting layer** on top — `live_status` already reports coarse phase; extend it to report the new per-skill gate verdicts as they land.
6. **End-to-end test on a real domain** — verify: 16 independent processes/contexts (not one shared session), zero MCP server processes spawned for the 13 skills that don't need them, one merged gate verdict per skill in `module_executions`, and the reports index auto-updates on publish.

## 5. Acceptance criteria

- A fresh audit run shows 16 separate process invocations in `ps aux`/logs, not one long-running `claude -p`.
- `module_executions` has one row per skill with a single gate verdict (not two separate factcheck/eval artifacts).
- No `chrome`/`apify`/`crossbeam` MCP server process exists during any skill invocation that doesn't need it.
- A deliberately-bad skill output (inject a contradiction or missing source) gets caught and re-dispatched before the next skill runs — not discovered at the end.
- The reports index shows the new report automatically after publish, no manual HTML edit.
