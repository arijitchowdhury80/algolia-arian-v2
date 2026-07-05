# GOAL PLAN — Make PRISM Airtight: Cassandra-as-Supervisor + Self-Healing Pipeline

**Author:** Claude (Opus 4.8), 2026-07-02
**For:** hand to Fable 5 (or Opus 4.8) via `/goal` for autonomous execution
**Status:** ✅ REVIEWED + APPROVED by Arijit 2026-07-02. **Execute PART 1 ONLY via this /goal run** (Phases 0→4, gated). Parts 2/3/4 are documented here for continuity but are NOT in scope for this run — they are separate later sessions.

---

## 0. READ THIS FIRST (for the executing model)

You are the **orchestrator**. You do NOT do all the work yourself — you decompose into tasks, dispatch **doer sub-agents** at the cheapest model tier that fits, verify their output against a concrete acceptance test, and only then move on. You keep judgment; workers keep grunt-work.

**Non-negotiable execution rules (from Arijit's operating constitution):**
1. **Never claim done without running the verification command and showing its output.** "It should work" is a failure.
2. **Every change is verified on the REAL VPS** (`ssh -i ~/.ssh/chowmes_ed25519 chowmesadmin@72.61.72.147`), not just locally. The runtime is the truth; source-read ≠ runtime.
3. **Protocol Read-Receipt** before writing any Hermes-plugin / runner-API / wire-format code: quote the exact governing code (file+lines) you are conforming to, then map it to your change. No phantom formats.
4. **Two-strikes-then-stop:** if the same approach fails twice, STOP, write a failure report, surface to Arijit. Do not blindly try a third variant.
5. **Hard gates between phases.** Do not start Phase N+1 until Phase N's acceptance test passes with shown evidence.
6. **Token discipline:** route every sub-task to the tier in the Model Routing table (§9). A loop that dispatches grunt-work at Opus/Fable is a cost bug.
7. **No fabrication, ever.** Blank data stays blank + flagged. This whole project exists because the pipeline was lying (fake screenshots, guessed traffic, emergent-not-real self-heal).

**The one-line problem statement:** *PRISM's self-healing is currently luck, not architecture; Cassandra is a 512-token chat bot with two buttons, not the supervisor she needs to be; and the real system-of-record is an unbacked-up filesystem on one disk.* This goal fixes all three, then proves it with a fresh Belk audit Arijit launches from his phone.

---

## 1. CURRENT STATE — ground truth (audited 2026-07-02, don't re-discover)

All facts below are verified against the live VPS. File paths are real. Use them.

### 1.1 Cassandra (Hermes agent, `hermes-prism` container)
- **Model:** `gemini-2.5-flash`, `temperature 1.05`, **`max_tokens: 512`**, context 131072. Config: `/root/.hermes-prism/config.yaml → model.default`. The grounding judge also uses `gemini-2.5-flash`.
- **Plugins enabled:** exactly ONE — `prism-report-qa` v0.1 (`/root/.hermes-prism/plugins/prism-report-qa/__init__.py`, 588 lines; container copy `/opt/data/plugins/prism-report-qa/__init__.py`). Dozens of bundled Hermes plugins exist under `/opt/hermes/plugins/` but are disabled.
- **Her 2 audit tools** (registered `toolset="prism_audit"`):
  - `run_audit(domain)` — fire-and-forget `POST /run {domain}` to the host runner. Whole-pipeline only, no phase/skill arg.
  - `audit_status(job_id?)` — `GET /jobs` then `GET /status/<id>`; surfaces status/phase + on failure the runner reason + last 8 log lines (this is the observability fix that shipped 2026-07-01).
- **2 hooks (load-bearing):** `inject_report` (pre_llm_call — injects the bound `audit-data.json` + a KB block from `POST 127.0.0.1:8000/api/v1/knowledge/retrieve`), `grounding_gate` (transform_llm_output — Gemini PASS/correct judge, fail-closed).
- **Sub-agent capability:** Hermes ships `delegate_task` (`/opt/hermes/tools/delegate_tool.py`, 2956 lines) — spawns isolated child agents, single or batch/parallel. It's in `_HERMES_CORE_TOOLS`, reachable on `cli` + `telegram` channels. **Config-capped:** `config.yaml → delegation: {orchestrator_enabled: false, max_spawn_depth: 1}` = one flat layer of leaf children, no recursion. **Unused by PRISM.**
- **Channel gap:** `platform_toolsets` gives `prism_audit` to `cli` + `telegram` but NOT `api_server` (the public web SPA). So audits can be triggered from Telegram + CLI, NOT web chat. (Telegram = Arijit's phone path — that works.)

### 1.2 The pipeline (host, `/opt/prism-executor/`)
- **`run-audit.sh`** (82 lines): takes ONE positional arg = domain. Fires ONE hardcoded `claude -p` running the `algolia-search-audit` skill end-to-end. `--allowed-tools` includes `Task` (so the audit session CAN spawn sub-agents). **No `--phase`/`--skill` parsing** — but the orchestrator SKILL.md already understands `--phase {research|browser|report|factcheck}` / `--skill` at the prompt level (a "Recovery Commands" convention). Enabling granular runs = swap the hardcoded prompt string + thread a param through (~10-20 lines).
- **`prism-runner.py`** (269 lines, systemd `prism-runner`, `127.0.0.1:8770`, bearer `PRISM_RUNNER_TOKEN`): exactly 4 routes — `GET /health`, `POST /run {domain,dry}`, `GET /status/<job_id>` (+15-line log tail), `GET /jobs` (last 20). `POST /run` reads ONLY `domain`. **Job tracking = flat JSON files** (`jobs/<id>.json` + `.log`), NOT a DB. Phase detection = `detect_phase()` regex tail-scan for 5 markers (`wave1|browser|report|factcheck|done`) — coarse, not per-skill, not a real state machine. Publish = glob largest `*audit-data.json` → copy to `/root/.hermes-prism/reports/<slug>/`.
- **The self-heal loop DOES NOT EXIST IN CODE.** `factcheck_mechanical.py` (`~/.claude/skills/algolia-audit-factcheck/scripts/`, 721 lines) is a genuine deterministic blocking gate (8 structural + corpus checks, exit 2 = BLOCKED). But the BLOCKED→fix→re-run cycle that "self-corrected" JBL was **emergent LLM behavior** in one long `claude -p` session — there is NO scripted retry anywhere. A differently-behaving run stops at BLOCKED and exits non-zero. **This is finding #1 to fix.**
- **Runtime skill copy** `claude -p` actually loads: `/home/chowmesadmin/.claude/skills/` (plain copied dirs, NOT symlinks; separately deployed from the git source at `/opt/prism-executor/arijit-skills/`). Beware the "3 non-syncing physical copies" gotcha — a fix in one copy is not live until in this one.

### 1.3 Browser / bot-walls
- VPS IP `72.61.72.147` is **permanently DataDome-flagged**. JBL's `09-browser-findings.md` correctly opened with a "WAF NOTICE — DataDome Hard Block" and labeled inferred steps honestly (good — it flags, doesn't fake). But: DataDome CAPTCHA screenshots are 46-47KB, just under the gate's 50KB size heuristic — a blocked run can slip the mechanical size check. No proxy/residential layer exists.
- Tooling is inconsistent: SKILL.md mentions both Playwright+stealth and Chrome MCP; `run-audit.sh` only wires `mcp__chrome__*`. A standalone `scripts/audit-browser.js` (Playwright+stealth) exists on disk.

### 1.4 SimilarWeb / traffic
- SKILL.md says "SimilarWeb MCP" — STALE. Reality: `collect-traffic.py` makes direct REST to `api.similarweb.com` with a **dead key** (env `SIMILARWEB_API_KEY` or hardcoded fallback `483b77d48d254810b4caf3d376b28ce7`). All 401.
- **Dell shipped with ZERO traffic data** (401s, no fallback ran). JBL/lululemon fell back to Gemini-grounded estimates labeled `[ESTIMATE]`. **No screenshot/vision path exists on the VPS.** No HITL hook — it 401s and guesses, unattended.

### 1.5 Data storage + health
- **No DB in the audit loop.** Postgres `prism-platform-postgres-1` (alembic head 008) has a real `audits/accounts/deliverables/module_executions` schema and **0 rows**. Only 5 tables are seeded — static Algolia *sales knowledge* (case studies, gaps, quotes), read fail-open by the chat plugin via `127.0.0.1:8000/api/v1/knowledge/retrieve`. The audit engine never writes to Postgres (grep-confirmed across run-audit.sh + runner + plugin).
- **Real system-of-record = filesystem, 3 un-versioned trees on one disk:** `/opt/prism-executor/audits/<slug>/` (raw research + screenshots — NOT a git repo), `/root/.hermes-prism/reports/<slug>/` (chat-grounding store + sqlite state), `/opt/prism-hub/<slug>/` (published site — the ONLY git-backed/off-host copy).
- **Zero backups.** No pg_dump, no cron, no off-host copy of the research trail or Cassandra's sqlite memory. Disk failure or `docker volume rm` = permanent total loss of audit history + Cassandra's memory.
- Operationally healthy: 7 containers, 0 failed systemd units, disk 70% (30G free), no restart loops. **The fragility is architectural, not operational.**

---

## 2. TARGET STATE — definition of "airtight"

When this goal is DONE, all of the following are true and PROVEN by evidence.

**Cassandra is built like a living being (Arijit's framing — she is the heart and soul of PRISM):**
- **Eyes = vision** (reads screenshots, dashboards, rendered pages).
- **Brain = `gemini-2.5-flash-lite`** for the high-volume thinking + chat (cheap), escalating to `gemini-2.5-pro` only for the hard supervisor calls.
- **Memory = her own conversational memory + the audit DATABASE** (the system-of-record for all audit data).
- **Muscles = all the skills** (the full algolia-* pipeline she can invoke whole, per-phase, or per-skill).
- **Self-improving + learning** — she captures what fails, feeds fixes downstream, and gets sharper over time.
She is a **30-year senior sales exec, a human sales coach, AND the supervisor/manager of PRISM** — not a bot, not a passive tool.

**Cassandra can, from Telegram (Arijit's phone):**
1. Launch a full audit for any domain.
2. Re-run a single phase OR a single skill of an existing audit (e.g. "re-run just traffic for belk").
3. Report status at **phase AND skill** granularity — including **LIVE, while an audit is still running**: what's done, what's running now, what's next, what's pending, as a detailed report.
4. Proactively validate each module's data completeness + run factcheck + **random-sample spot-check** finished data, and tell Arijit exactly what's incomplete or unverified.
5. **Point-check a specific module** or **random-sample-test** an audit on demand, like a manager auditing a rep's work.
6. On a detected gap/failure, re-dispatch that specific part downstream to fix, and confirm the fix — without redoing the whole audit.
7. Flag human-required blockers (bot-walled site, SimilarWeb login needed) and pause cleanly for them.
8. Spawn parallel sub-agents for independent per-skill work when it speeds things up.
9. Do ALL of the above **in her real human voice** — witty, sarcastic, dry-humoured, philosophical, speaks her mind from the data — never sounding like AI.

**The pipeline itself:**
8. Has a **scripted, deterministic self-heal loop** — the mechanical gate runs after each phase; a BLOCKED phase/skill is auto-re-dispatched up to N times; still-failing escalates to human. No dependence on an LLM "remembering" to retry.
9. **Postgres is the single source of truth** — every audit (new AND all historical) persisted there; the DB is authoritative, filesystem/HTML are projections. All existing completed audits are **migrated in** with nothing left behind and nothing fabricated.
10. **Durable + git-versioned** — pg_dump cron writes to a `/data` git repo pushed to a private GitHub repo (off-host DB backup), plus off-host copies of the research trail + Cassandra's sqlite.
11. **Migration proven safe** — a full regression run confirms every currently-live report still renders identically (0 JS errors) after the DB becomes source of truth.
12. **Never lies + shows its provenance** — every section renders a source badge with a ✓ ONLY when the data came authentically from that real source (Crossbeam ✓ only if Crossbeam ran, Website ✓ only if scraped, SimilarWeb ✓ only if logged in); estimates/fallbacks get an amber "unverified" flag, never a ✓. Bot-walled sites flagged UNAVAILABLE (not faked); a guess is never shown as fact; every data gap is visible; formatting is clean (no `%%`, no range-mash, no empty "Data as of —").

**Proof:** Arijit launches a **fresh Belk audit from his phone**; it runs end-to-end with self-heal, HITL hooks fire correctly, blocks are flagged not faked, it persists to DB, publishes clean, and Cassandra reports granular status + validation the whole way.

---

## 3. ARCHITECTURE — the core decision

**Split the supervisor into two layers. This is the central design insight; build to it.**

- **Deterministic orchestrator (host-side, scripted, no LLM in the control loop).** Upgrade `prism-runner.py` into a real state machine that: runs phases, runs the mechanical gate after each, **auto-re-dispatches** a failed phase/skill up to N times, persists all state to Postgres, and exposes granular per-skill status. This layer must be CODE, so self-heal is guaranteed, not emergent. *This fixes finding #1.*
- **Cassandra (Hermes agent, tiered model) as the human-facing supervisor ON TOP.** She triggers + observes the orchestrator at skill granularity, runs the *judgment* validation (LLM factcheck/verify layered on the mechanical gate) via an Opus-tier delegate, decides when to escalate to human, flags HITL blockers, and reports in plain language. She is the brain and the voice; the orchestrator is the reliable hands.

**Why this split:** deterministic loops must never depend on an LLM's mood. But "is this data actually good / is this finding real / should we bother the human" is judgment that deserves a strong model. Mechanical gate = code (always runs, always blocks). Judgment gate = Cassandra/Opus (adds the 200% verify + human comms). Cassandra *drives* the deterministic loop; she doesn't *replace* it.

**Sub-agents:** enable `delegate_task` (bump `max_spawn_depth`, wire it into the plugin) so Cassandra can fan out independent per-skill re-runs in parallel and isolate heavy validation into child contexts. Use it for parallelizable work only; the deterministic loop stays in the orchestrator.

---

## 4. EXECUTION — FOUR PARTS (Arijit, ordering locked 2026-07-02)

**Do PART 1 first and fully — it is the point of this project.** The others follow in order.

- **PART 1 — Make the single-tenant pipeline airtight, then prove it on Belk.** Scripted self-heal + granular runner + Cassandra-as-supervisor + DB-as-source-of-truth *for new audits* + backups + block-detector + SimilarWeb HITL + context-efficiency (caching). (§4.1, Phases 0–4.)
- **PART 2 — Multi-tenancy & scalability.** (Order set by Arijit — matters more than backfilling old data.) Design the architecture first (gated review), then build: how 20 AEs each get their own Cassandra, how 20 parallel audits run, tenant isolation + scaling. (§5.) DESIGN stage may run in parallel with Part 1.
- **PART 3 — Backfill history + prove nothing broke.** Migrate all existing completed audits into the DB + full regression. (§4.2.) Heavy, risky (touches live reports); old audits keep serving fine from their current HTML until then.
- **PART 4 — Role-driven IA re-architecture + customer-facing Jahia landing page.** (§5b.) A near-complete re-architecture of the report IA around 3 roles (Marketer/AE/BDR) + a real Marketer landing page pushed to Algolia's Jahia CMS. **Needs its own dedicated, focused, high-attention session WITH Arijit — NOT an autonomous /goal blast.** Documented here so it isn't lost.

Execution model within each part: **Phased + gated** ✅ LOCKED. fable5 completes a phase, runs its acceptance test, shows evidence, then STOPS for Arijit's go/no-go before the next. We've gone in circles; slow + verified beats fast + broken.

---

## 4.1 PART 1 — Airtight single-tenant pipeline + Belk proof (PRIORITY)

### PHASE 0 — Safety net + free wins (do first, low-risk, high-value)
**Goal:** stop the data-loss bleeding and kill the "pipeline lies" class before touching anything fragile.
- **0.1 Backups + git-versioned DB** (Arijit: "the data is our heart and soul — don't fear losing it"): pg_dump nightly cron (Postgres) → write the dump to a `/data/` folder that is a **git repo pushed to a dedicated PRIVATE GitHub repo** `[DEFAULT: new private repo `prism-data`, NOT prism-hub — committing to prism-hub would trigger its live-deploy webhook; alt = a `/data` folder in the PIP backend repo]`. So the DB is versioned + off-host on every backup. Also nightly rsync/git of `/opt/prism-executor/audits/` (raw research + screenshots) and `/root/.hermes-prism/` (Cassandra's sqlite memory + report store) to the same off-host target. **Verify a restore works** (restore the dump into a scratch Postgres, diff row counts).
- **0.2 Deterministic block-detector** (the highest-ROI free item): a pure-code module that runs on every page load BEFORE screenshotting and returns `OK | BLOCKED_BY=<vendor> | SOFT_BLOCK`. Signals (from research §Appendix A): DataDome (`x-datadome` header, `datadome` cookie, `geo.captcha-delivery.com`), Akamai (`_abck` cookie, "Access Denied"/"Pardon Our Interruption"), Cloudflare (`cf-mitigated: challenge` header, "Just a moment", `#challenge-running`), Imperva (`x-iinfo`, `incap_ses_*`, "Incapsula incident ID"). Wire into the browser skill + fix the 50KB gate to also image/DOM-classify, not just size.
- **Acceptance:** trigger a backup + restore it (show output); run the detector against a known DataDome site (jbl.com) and a clean site, show it correctly labels each.
- **Model routing:** doer = sonnet (bounded scripting); verify = sonnet.

### PHASE 1 — Granular + durable + self-healing pipeline (the foundation)
**Goal:** the pipeline can run/re-run any phase or skill, persists to DB, and self-heals deterministically.
- **1.1 `run-audit.sh`:** add `--phase <name>` and `--skill <name>` (swap the hardcoded prompt for a targeted one). Keep the full-run default. **Read-receipt required** (quote the current prompt block + allowed-tools before editing).
- **1.2 `prism-runner.py` → state machine:** new routes — `POST /run {domain, phase?, skill?}`, `POST /rerun {job_id, phase|skill}`, `POST /render {slug}`, `POST /publish {slug}`, `POST /validate {slug}` (runs mechanical gate, returns structured findings), `GET /status/<id>` with per-skill detail, `POST /kill {job_id}`. Move job state from flat files → Postgres (`audits` + `module_executions` tables — they already exist).
- **1.3 Scripted self-heal loop — loop until CLEAN, not a fixed count** (Arijit: "cannot afford wrong data anywhere; run factcheck multiple times if needed"): after each phase, orchestrator runs `factcheck_mechanical.py`; on BLOCKED, auto-re-dispatch that phase/skill and re-run the gate — **repeat until it passes clean**, up to a sane safety cap (e.g. 4 passes) then mark `NEEDS_HUMAN` + escalate to Cassandra/Arijit. Factcheck genuinely runs multiple times when needed. Log every attempt + gate result to `module_executions`. **This is the emergent→scripted fix.**
- **1.3b Extend the gate to RENDER + SOURCE correctness** (the lululemon-axis class): the mechanical gate today checks DATA presence, not RENDERING or source-validity. Add: (a) **chart/render sanity** — for any dual-axis or plotted series, assert the axis max ≥ data max and every series plots inside the plot bounds (the lululemon EBITDA-margin line rendered OFF the axis: axis capped 0-20%, data 24-28% → floating line; a data-only gate passed it because the numbers were valid — the RENDER was broken). (b) **source-validation** — every numeric/factual data point must carry a live source link that RESOLVES and SUPPORTS the claim; a number with a dead or non-supporting citation BLOCKS. No unsourced, un-validated data ships, period.
- **1.4 Postgres = SINGLE SOURCE OF TRUTH for NEW audits** (Arijit's decision): every audit run *from now on* writes to `audits` (status, score, factcheck_score, config + full audit-data JSON in a jsonb column) + per-module rows to `module_executions` + `deliverables`. The DB is authoritative for new audits; the filesystem/rendered-HTML become projections derived from it. **Existing live reports are NOT touched here** — they keep serving their current frozen HTML until PART 3 backfills them (§4.2 — deliberately out of PART 1).
- **1.5 Context efficiency — prompt caching + section-scoped injection** (Arijit approved — build it into Part 1): the `inject_report` hook today injects the WHOLE `audit-data.json` into every chat turn (the main cost driver). Two builds: (a) **Gemini prompt caching** on the injected report + KB block so repeat turns in a session read from cache (~75% cheaper) — verify `prompt_caching` is actually on and hitting; (b) **section-scoped retrieval injection** — instead of the whole report, inject only the report section(s) relevant to the question (retrieved from the DB's per-section rows now that Postgres is source-of-truth). Fall back to whole-report only when the question is broad. Cuts Cassandra's per-turn token cost hard. **No regression to grounding** — the grounding gate must still have the facts it needs; if a needed section wasn't injected, widen and retry, never answer ungrounded.
- **1.6 Provenance-badge system + template honesty + formatting hardening** (Arijit's lululemon feedback — fix the TEMPLATE so every future run is honest by construction): the pipeline must **record real provenance per module** (a field: actual source + collection method + timestamp + `verified` bool = "came authentically from that real source" vs estimate/fallback) and the template renders THAT truth:
  1. **Provenance badge + checkmark per section** — each section shows its ACTUAL source as a badge with a ✓ ONLY when the data came authentically from that real source: `Crossbeam ✓` only if Crossbeam MCP actually ran (today it never has — falls back to WebSearch, so it must show `Web research`, NOT a false `Crossbeam ✓`); `Website ✓` only if the careers/site scrape succeeded; `SimilarWeb ✓` only if the same-IP login happened; `Yahoo Finance ✓`/`SEC ✓` for financials; an **estimate/fallback gets an amber `Estimate — unverified` flag, never a ✓.** Badge is DATA-DRIVEN from the provenance field, never hardcoded. Fix the current mislabels (tech-stack shows `BuiltWith` but is actually `detect-search`).
  2. **No fabrication-as-fact in render** — if a source wasn't run (e.g. no SimilarWeb login → traffic is a Gemini estimate), the section shows the estimate flag OR blanks with an honest "not collected" note. NEVER a guess shown as authoritative (the lululemon traffic case: 30.7%/41.23%/device-split shown as fact when no login ever happened).
  3. **Formatting bugs** (all seen live on lululemon): double `%%` signs, range-concatenation ("70.9–74.43%%"), empty "Data as of —" dates, empty section boxes (Audience Profile blank). Fix the render + add these to the gate (1.3b) so they can't recur.
  3b. **NO internal identifiers in the customer-facing UI** (Arijit caught this live: finding headers rendered raw internal `category` keys — `semantic_nlp_search`, `content_commerce_ux`, `intent_detection` — next to the gap number "G03", where previously only the gap number showed). The template must NEVER print a raw internal key (snake_case category IDs, `f.id`, module names, filenames, slugs). Any label shown to the prospect must be a human string — either humanize the key (snake_case → Title Case with acronym fixes: nlp→NLP, ux→UX, roi→ROI, ai→AI) or omit it. Add a gate check: fail the render if any visible text node matches `/[a-z]+_[a-z_]+/` (a snake_case internal token leaking into UI). Fix at the source template (`index-template.html`), not per-report.
  4. **Fix the TEMPLATE** (`index-template.html` + `render-audit.ts`), not just lululemon's one page — so all future renders are correct by design.
- **Acceptance:** (a) re-run ONLY `algolia-intel-traffic` for an existing slug, show it updates just that module in the DB; (b) inject a known gate failure, watch the scripted loop auto-re-dispatch and recover (show `module_executions` rows); (c) after a fresh run, `SELECT * FROM audits` shows the new row with its jsonb data; (d) a chat turn shows a cache hit + a section-scoped injection, grounding still passing; (e) render a report where Crossbeam did NOT run + traffic is an estimate → the page shows `Web research` (no ✓) for partner and an amber `Estimate` flag for traffic, zero `%%`/range/empty-date defects. All shown as evidence.
- **Model routing:** doer = sonnet per route/script + the caching/retrieval wiring; the self-heal-loop design review = opus (critical correctness piece); tests = sonnet.

### PHASE 2 — Cassandra as supervisor
**Goal:** Cassandra can drive + validate + report + self-heal + delegate, from Telegram.
- **2.1 Tiered model routing** `[Arijit: brain = flash-lite for cost]`: her default brain = **`gemini-2.5-flash-lite`** ($0.10/$0.40 per 1M) for chat Q&A AND routine supervisor ops (status, point-checks, per-module completeness reads) — high volume, cheap. Escalate to **`gemini-2.5-pro`** ($1.25/$10) ONLY for the genuinely hard calls (final validation synthesis, ambiguous self-heal decisions, the "speak my mind" strategic read) — a handful per audit. Opus NOT used. **Raise `max_tokens`** off the current 512 (far too small for a detailed status report or a validation synthesis) — set generous on the supervisor path, keep chat modest. Keep the model STABLE within a session (prompt cache). Enable `prompt_caching` for the injected report so repeat chat turns are cache-cheap.
- **2.2 New plugin tools** (map to Phase-1 routes): `run_audit(domain, phase?, skill?)`, `rerun(slug, phase|skill)`, `audit_status(slug)` (granular), `live_status(job_id)` — **mid-run introspection while an audit is RUNNING: what's DONE, what's running NOW, what's NEXT, what's PENDING, per phase AND per skill, as a detailed report** (Arijit's explicit ask — "even when an existing audit is running and I ask for status, she should look into the pipeline and come back with a detailed report"); `validate_audit(slug)` (mechanical + LLM factcheck → structured gaps); `sample_check(slug, n?)` — **random-sample test: pull N random data points/citations from a finished audit and verify them live** (spot-check for confidence, like a manager auditing a rep's work); `point_check(slug, module)` — **targeted spot-check of one named module** on demand; `render_publish(slug)`, `list_reports()`, `get_audit_field(slug, path)`. **Read-receipt** against the existing `register_tool` calls + `_runner_call` before adding. (`live_status` needs the Phase-1 state machine to expose per-skill live state — not just the coarse log-regex it has today.)
- **2.3 Fix the web-channel gap:** add `prism_audit` to the `api_server` platform_toolset so the web SPA can also trigger/monitor (Telegram already works).
- **2.4 Enable delegation:** bump `delegation.max_spawn_depth` (and `orchestrator_enabled` if parallel-of-parallel is wanted), wire a plugin path that fans out independent per-skill re-runs as `delegate_task` batch children.
- **2.5 Proactive validation + self-heal from her side — E2E, every element** (Arijit, non-negotiable: "check and validate e2e every single element of the report... cannot afford wrong data anywhere that is not source-linked and source-validated"): after a run, Cassandra auto-runs the full validation stack and re-dispatches until clean:
  1. **Mechanical gate** (data completeness + render/source checks from 1.3/1.3b).
  2. **VISION check (her eyes)** — she actually LOADS the rendered report and LOOKS at every element (charts, tables, sections), catching visual breakage a field-check can't: the lululemon EBITDA-line-floating-off-the-axis case, overlapping labels, empty/placeholder visuals, a chart whose numbers don't match its bars. This is why she has vision — a data gate alone would have passed that broken chart.
  3. **Source-validation** — every data point traces to a live source that actually supports it (spot-check citations resolve + back the claim).
  4. **Random-sample test** (`sample_check`) — pull N random facts and re-verify live.
  On ANY failure she re-dispatches the specific part (`rerun`) and re-validates — **looping until clean or escalating to Arijit**, running factcheck as many times as it takes. She does this proactively (baked into her instructions, not left to chance) and **speaks her mind** on what the data says, like a 30-year sales exec reviewing a rep's work. **Nothing wrong, unsourced, or visually broken ships.**
- **2.6 VOICE / SOUL — she must sound like a real human, never like AI** (Arijit, non-negotiable): Cassandra keeps her carefully-designed SOUL voice in EVERY channel and every message — emotion, witty sarcasm, dry humor, banter + tease (banter matters), philosophical (draws parallels from philosophy and life), a 30-year senior sales exec who speaks her mind from data + observation. She is the human sales coach AND the supervisor/manager of PRISM. Guardrails: (a) load the RICH SOUL, never a trimmed one — a prior trim made her robotic (see memory `feedback-soul-trim-killed-personality`); verify the live SOUL is the full version. (b) The `grounding_gate` (Gemini judge that rewrites her output for factual grounding) MUST preserve voice — it may correct FACTS, never flatten personality; re-prompt the judge to keep her tone, or run grounding on facts-only and re-voice after. (c) Status/validation reports are still in HER voice — a detailed pipeline status should read like a sharp exec briefing a colleague, not a system log.
- **2.7 Grounding-fetch integrity — never return a login page (or any unvalidated fetch) as an answer** (diagnosed live 2026-07-02: Cassandra answered a lululemon question with the PRISM **Clerk sign-in HTML** — `<title>Sign in · PRISM</title>`, Clerk key, `mountSignIn` — because her report-grounding fetch hit a Clerk-gated PUBLIC report URL, got the login wall back, and passed it straight through. Same systemic failure as every other bug today: trust + forward whatever was fetched without checking it's real). Four fixes:
  1. **Internal data path bypasses the public Clerk gate.** Cassandra reads report data from the DB (source of truth, once Part 1 lands) or the internal loopback store (`/root/.hermes-prism/reports/<slug>/audit-data.json`) — NEVER the public Clerk-gated URL. Internal grounding must not traverse the public auth wall. (Ties to the known memory issue "Clerk gate 302s all report pages for anon.")
  2. **Validate fetched grounding content BEFORE using it.** Assert the payload is real audit JSON (expected keys / `AUDIT_DATA`). If it's HTML or a login gate (detect `<!doctype html>`, `<title>Sign in`, Clerk markers), treat it as a FETCH FAILURE — do not inject it, do not echo it; retry via the internal path or surface an honest error.
  3. **Never emit raw markup as a chat answer.** The output transform (`grounding_gate`) must guarantee natural-language replies; a raw `<!doctype html>…` reaching the user is a HARD failure the gate blocks.
  4. **Report-binding correctness + confirmation.** The session must bind to the correct report (slug/content match) and CONFIRM the bound report actually loaded before answering. On binding failure, say so — don't silently fall back to fetching a gated URL.
- **Acceptance:** from Telegram — (a) she runs an audit and, WHILE it's running, answers "status?" with a detailed done/now/next/pending breakdown; (b) she catches an incomplete module, re-dispatches just that skill, confirms the fix; (c) she random-sample-checks a finished audit and reports what she verified; (d) every message reads as a witty, human, philosophical sales exec — NOT a bot; (e) **ask her a lululemon question → she answers from the real bound report in her own voice; she NEVER returns HTML, a login page, or an unvalidated fetch** (this exact failure, reproduced and killed as a named case). Show the Telegram transcript as proof of function AND voice.
- **Model routing:** plugin/tool coding = sonnet; SOUL/voice + validation-judgment design = opus (voice is high-stakes, get it right); delegation wiring = sonnet.

### PHASE 3 — External data (browser bot-walls + SimilarWeb HITL)
**Goal:** the two chronic data-quality holes are fixed or honestly flagged.
- **3.1 Bot-walls — detect + flag only, $0 spend** (Arijit's decision): NO paid unblocker, NO proxy spend. The Phase-0 deterministic block-detector gates every capture; walled sites are honestly marked `UNAVAILABLE(BLOCKED_BY=<vendor>)` and the search audit says "couldn't live-test, bot-walled" for them. A free Patchright/Camoufox swap (better fingerprint hygiene than the current setup, no recurring cost) is allowed as a best-effort first try, but the acceptance bar is **honesty, not bypass** — never fake a screenshot. (Paid scraping-browser tier is documented in the research appendix as a future option if Arijit later wants real screenshots from walled sites; NOT in scope now.)
- **3.1b Screenshot quality + interstitial dismissal** (Arijit's lululemon search-audit screenshots were all black / all stuck on a "summer sale" promo modal — useless, and they PASSED because the gate only checks file size, and a black/popup PNG is still >50KB): the browser phase must (a) **dismiss interstitials before every capture** — cookie banners, promo/"summer sale" modals, newsletter popups, age gates (wait-for + close common overlay selectors + press Escape); (b) **quality-gate every screenshot by CONTENT, not size** — detect all-black/blank frames (pixel-variance/histogram check) and detect "this is a popup/overlay, not the search UI" (expected search selectors absent) → mark the shot BAD and re-capture or flag `SCREENSHOT_UNUSABLE`, never ship it; (c) **Cassandra vision-QA** — she LOOKS at each search screenshot and flags "these are black / all show a promo, not search results" (a data/size gate is blind to this). A search audit with no usable screenshots must say so honestly, not present garbage.
- **3.1c Screenshot TIMING — wait for the tested behavior to actually render, and never let a pre-load capture drive a finding** (Arijit's lululemon search-audit: the shots were captured BEFORE search-as-you-type suggestions loaded, so EVERY query looked empty ["only a Trending Searches label"] — and the analyst then wrote FALSE findings + a low score concluding lululemon has "no trending, no scoped suggestions," when in reality keyword search, autocomplete, trending, and recent searches all work; only natural-language/intent + federated content genuinely fail). This is worse than a bad image — **a mistimed screenshot produced wrong findings and a wrong score.** Fix in the `algolia-audit-browser` skill: (a) after typing a query, **wait for the actual result to render** — `waitForSelector` on real suggestion/product/result elements (not a fixed sleep, not just the container label), with a generous timeout + settle delay; if nothing renders, RETRY, then flag `NO_RESULTS_CONFIRMED` — never assume "empty" on first look; (b) **assert the captured frame contains the query + real content** before saving (the search term is in the box AND ≥1 result/suggestion element exists, or it's a genuine confirmed zero-result); (c) **a finding may NOT be written from an unconfirmed-empty capture** — "no suggestions" requires a waited, retried, confirmed-empty result, distinguished from "suggestions hadn't loaded yet"; (d) each screenshot must MATCH the exact query/behavior its finding claims (no reusing one query's shot for another's finding). This whole class = the "took the picture before the thing happened, then described the blank" bug Arijit flagged.
- **3.2 SimilarWeb HITL hook** `[DEFAULT: HITL, same-IP login]`: state machine — pipeline hits the traffic step → writes `WAITING_FOR_HUMAN(similarweb_login)` → Cassandra Telegrams Arijit a live browser link → he logs in ONCE through a shared cloud browser (Browserbase/Steel live-view, ~$20-50/mo) OR a noVNC session on the VPS itself, so **login IP == replay IP** (this is the specific fix for the impossible-travel session break) → agent captures `storageState`, screenshots the dashboard, resumes; re-fires the hook only when the session dies (days-2wks). Vision-extract the screenshots as today. If Arijit prefers zero human touch, fall back to DataForSEO programmatic estimates labeled `[ESTIMATE]`.
- **Acceptance:** on the Belk run (Phase 4) — the SimilarWeb hook fires, Arijit logs in from his phone, real traffic screenshots are captured + extracted; any bot-walled Belk sub-page is flagged UNAVAILABLE, not faked.
- **Model routing:** browser/detector/HITL-state-machine coding = sonnet; vision-extraction prompt = sonnet; the overall design = opus.

### PHASE 4 — THE BELK ACCEPTANCE TEST (definition of done)
**Arijit launches a fresh Belk audit from his phone, via Telegram, to Cassandra.** fable5 does NOT trigger it — Arijit does, live, as the real-world proof. fable5's job is to make sure that when he does, ALL of this holds and to observe + report:
- Full pipeline runs; scripted self-heal recovers any gate failure (show `module_executions`).
- Per-skill status is reportable throughout; Cassandra narrates it.
- SimilarWeb HITL hook fires; Arijit logs in from phone; traffic captured.
- Any bot-walled page flagged, not faked.
- Audit persists to Postgres (`SELECT` proof); publishes clean; browser-verified 0 JS errors.
- Cassandra proactively validates + reports completeness + confirms no fabrication.
- **If ANY of these fail, the goal is NOT done** — diagnose, fix, re-prove.

**← PART 1 COMPLETE when Belk passes. STOP. Get Arijit's sign-off before starting PART 2.**

---

## 4.2 PART 3 — Backfill history into the DB + prove nothing broke (do LAST)

Deferred deliberately to last: heavy + the riskiest work (it touches live production reports). Only start after Part 1's Belk proof AND Part 2 (multi-tenancy) are done.

- **P3.1 MIGRATE ALL EXISTING AUDITS into the DB** (nothing left behind): enumerate every completed/published audit across the three current stores (`/opt/prism-hub/<slug>/` published sites, `/root/.hermes-prism/reports/<slug>/audit-data.json`, `/opt/prism-executor/audits/<slug>/`), reconcile duplicates (prefer the live-served inline `window.AUDIT_DATA` as truth for what's public), load each into `audits`/`module_executions`/`deliverables`. Handle schema drift: older JSONs predate current Pydantic tightening (see lessons-log "Stale base audit-data JSON blocks re-render"); migrate WITHOUT fabricating missing fields — mark gaps explicitly. Deliverable: migration report (N found, N migrated, per-audit field-gap list).
- **P3.2 POST-MIGRATION REGRESSION — prove nothing broke:** every currently-live report on `prism.chowmes.com/<slug>/` must still render identically and work — real Playwright load per report, `page.on("pageerror")`, 0 JS errors, key facts present. Diff DB-sourced data vs live inline data per report; any divergence is a BLOCKER to investigate, not paper over. Deliverable: pass/fail table across all live reports.
- **P3.3 Cut the read path over to the DB** (optional, only if P3.2 is clean): switch the render/serve path to read from Postgres instead of the frozen inline HTML, so the DB is truly authoritative end to end. Guarded by the same regression bar.
- **Acceptance:** migration report shows every historical audit loaded; regression table shows every live report still 0-error; (if P2.3) a report re-rendered from the DB is byte-equivalent in rendered content to the prior live one.
- **Model routing:** migration ETL + regression browser-verify = sonnet; reconciliation judgment on schema-drift conflicts = opus.

---

## 5. PART 2 — Multi-Tenancy & Scalability (design → gated review → build)

**Elevated per Arijit — this is important, and it comes before the history backfill.** Two stages: (1) **DESIGN** a decision-grade architecture doc (`docs/plans/multi-tenancy-architecture.md`), gate on Arijit's review, THEN (2) **BUILD** to the approved design. The DESIGN stage can start in parallel with Part 1 (pure research, no prod code); the BUILD stage starts only after Part 1's Belk proof + design sign-off. The doc answers:
- How does each of 20 AEs/BDRs get "their own Cassandra"? (one Hermes instance per tenant vs one instance multi-session vs per-tenant containers) — trade-offs on cost, isolation, memory separation.
- How do 20 parallel audits run? (the runner is single-box, sequential-ish today) — concurrency model, queue, per-tenant rate limits, worker pool, cost ceilings.
- Tenant data isolation (per-tenant Postgres schema/row-level-security vs per-tenant DB), auth (Clerk is already in flight per memory), per-tenant report stores.
- Scaling the browser/proxy + SimilarWeb HITL across tenants (shared vs per-tenant sessions).
- What breaks first at 20 tenants; the migration path single-tenant → multi-tenant; rough infra cost curve.
- **Deliverable:** `docs/plans/multi-tenancy-architecture.md` + a recommendation. Dispatch as a research sub-agent (sonnet + web research) reporting to an opus synthesis.

---

## 5b. PART 4 — Role-driven IA re-architecture + customer-facing Jahia landing page

**Needs its OWN dedicated, focused, high-craft session WITH Arijit — NOT an autonomous /goal blast.** A prior attempt was rejected (shallow browse-vs-chat A/B, "useless and rubbish"); Arijit then gave his own direction. Use HIS model below — do not re-invent. Documented here so it isn't lost. Full prior state: memory `project-prism-role-driven-ia`, `project-marketer-landing-dell-shipped`, `reference-figma-mcp-jahia-landing`, `project-prism-ui-persona-journeys`.

**The role model (Arijit's decision):** the report IA is **role-driven** — 3 role doors: **Marketer · AE · BDR** (Algolia's own GTM roles consuming the audit). Each door re-sorts the SAME audit into that job's view. Partition = **shared core + role lanes** (do NOT triplicate the findings).

**Each role door = 3 zones:** (1) **shared audit core** (score + killer finding + a small "framed for you" chip); (2) **Your Intelligence** (research sliced for that role); (3) **Your Deliverables** (actions/outputs for that role).

**Scope of work:**
- **P4.1 Audit + re-slot every section:** review ALL current report sections and slot each under a role. Starting map (validate + refine): Marketer ← traffic / industry / competitors / investor; AE ← tech-stack / financial / investor / partner / competitors; BDR ← news / social / hiring; shared core = company-context / test-queries / browser-findings / scoring.
- **P4.2 VALIDATE the data in every section** (the near-rearchitecture part): for each section, is the data actually correct, complete, and sourced? Should sections be added, modified, or dropped? This is a content-integrity pass, not just a layout reshuffle — tie it to the Part-1 DB (data is now queryable + validated) so this rides on real, checked data.
- **P4.3 Customer-facing Marketer landing page → Jahia:** build a real customer-facing landing page (Marketer role, channel #1) and **push it to Jahia (Algolia's CMS) → Jahia publishes it live.** Significant build. Prereqs/known gaps: **Jahia MCP is NOT installed** (needs instance URL + creds + a community MCP server — real setup); Figma design source is wireframe-only; a Dell marketer landing-page prototype already exists (the "whale-ac" pattern, `~/prism/marketer/dell.html`) — reuse as the reference, don't start from zero.
- **P4.4 OPEN decision** to settle in that session: personalization depth — light (name+vertical+rep) vs deep (inject findings/ROI/Golden-Angle) vs hybrid (Arijit's rec: ship light + one PRISM audit-insight block).

**Craft bar:** prior verdict was "directionally right, you can be a lot better" — this phase is where craft matters most; give it real attention.

---

## 6. TESTING & VALIDATION (every phase)
- **Unit/integration** for each new runner route + plugin tool (pytest; the repo convention is 3-layer tests).
- **Real-VPS integration:** every route hit live with `curl` + bearer token; every plugin tool exercised through a real Hermes session.
- **The scripted self-heal loop** gets an explicit forced-failure test (inject bad data → assert auto-re-dispatch → assert recovery).
- **Browser-verify** every published page with Playwright `page.on("pageerror")` (HTTP-200 + grep is NOT proof — this bit us repeatedly).
- **No phase passes on source-read alone** — show runtime evidence.
- **Regression:** re-run an existing clean audit (e.g. petsmart) end-to-end after each phase to confirm nothing broke.

---

## 7. SAFETY / ROLLBACK
- Back up every file before editing (`*.bak-<goal>-<date>`), as prior sessions did.
- The VPS runs LIVE production (`prism.chowmes.com`). Test on a scratch slug, not a real prospect, until a phase is proven.
- `prism-runner.py` + the plugin restart affects Cassandra — restart in a window, verify `docker logs` clean + Telegram reconnect after each deploy.
- Never push to `prism-hub` (auto-deploys live) without a browser-verify first.

---

## 8. KEY FILES (all on VPS unless noted)
- `/opt/prism-executor/run-audit.sh`, `/opt/prism-executor/prism-runner.py`
- `/root/.hermes-prism/plugins/prism-report-qa/__init__.py` (+ container copy `/opt/data/plugins/...`)
- `/root/.hermes-prism/config.yaml` (model, plugins, delegation, platform_toolsets), `/root/.hermes-prism/SOUL.md`
- `/opt/hermes/tools/delegate_tool.py`, `/opt/hermes/.../toolsets.py`
- `/home/chowmesadmin/.claude/skills/algolia-*/` (RUNTIME skill copy — the one `claude -p` loads), `.../algolia-audit-factcheck/scripts/factcheck_mechanical.py`
- Postgres: `docker exec prism-platform-postgres-1 psql -U prism -d prism`; FastAPI `prism_platform` (`127.0.0.1:8000`), source under `/opt/prism-platform/`
- SSH: `ssh -i ~/.ssh/chowmes_ed25519 chowmesadmin@72.61.72.147`; runner token `PRISM_RUNNER_TOKEN` (systemd env), value known to Arijit.

## 9. MODEL ROUTING TABLE (token discipline)
| Work | Tier | Model |
|---|---|---|
| Orchestration / this goal's main loop | T3/T4 | fable5 (or opus-4.8) |
| The self-heal-loop + supervisor-split design & review | T3 | opus-4.8 |
| Bounded coding (one runner route, one plugin tool, one script) | T2 | sonnet |
| Writing tests, running gates, VPS grep/curl checks | T1/T2 | haiku / sonnet |
| Multi-tenancy research sweep | T2 | sonnet |
| Multi-tenancy synthesis + adversarial verify of Belk acceptance | T3 | opus-4.8 |
| Cassandra's runtime supervisor reasoning — HARD calls only (in production) | T3 | **gemini-2.5-pro** (already available — NO new API spend; Opus not used) |
| Cassandra's runtime chat Q&A + routine supervisor ops (in production) | T1 | **gemini-2.5-flash-lite** |
Severity override: escalate one tier for anything touching the live prod site or irreversible data.

**COST — two separate things, do not conflate:**
- **BUILD cost (one-time):** the tokens fable5/opus/sonnet spend BUILDING this upgrade. The `~$X/phase` numbers below are THIS — a one-time dev spend across Part 1's phases, not recurring.
- **RUNTIME cost per audit (recurring):** VERIFIED tiny. The audit engine runs on the **Claude subscription** via `CLAUDE_CODE_OAUTH_TOKEN` (`run-audit.sh` unsets `ANTHROPIC_API_KEY` — flat cost, not per-token). Cassandra = gemini-2.5-flash. Gemini grounding + SimilarWeb vision = gemini, pennies. **An audit costs ≈ subscription + a few cents of Gemini — NOT dollars.** The supervisor upgrade stays on gemini-2.5-pro, so it adds no meaningful recurring cost.

## 10. DECISIONS — LOCKED by Arijit 2026-07-02 (unless noted)
1. Execution model → **phased + gated** ✅ LOCKED
2. SimilarWeb → **HITL, same-IP login** ✅ LOCKED
3. Bot-walls → **detect + flag only, $0 spend** ✅ LOCKED (no paid unblocker, no proxy spend; honesty over bypass)
4. Data layer → **Postgres = single source of truth + migrate ALL historical audits + git-versioned `/data` on GitHub + post-migration regression** ✅ LOCKED (upgraded from the original "DB as index" default)
5. Cassandra model → **tiered, gemini-only: flash-lite brain (chat + routine ops) / gemini-2.5-pro for hard supervisor calls; Opus not used** ✅ LOCKED
6. Multi-tenancy → **PART 2: design → gated review → build** (elevated above history-migration) ✅ LOCKED
8. IA re-architecture (role-driven Marketer/AE/BDR) + Jahia landing page → **PART 4, dedicated focused session with Arijit, NOT autonomous** ✅ LOCKED
7. **Sub-decisions — defaults applied 2026-07-02 (Arijit away; override on return):**
   - (a) `/data` DB dumps → **new private repo `prism-data`**, and it also holds the rsync'd `/opt/prism-executor/audits` raw research + screenshots — everything versioned off-host in one place `[DEFAULT]`. NOT prism-hub (its push webhook auto-deploys the live site).
   - (b) SimilarWeb same-IP login → **free noVNC into the VPS browser first**; pay for a live-view service only if too clunky `[DEFAULT]`.
   - (c) **BUILD** cost ceiling (one-time dev spend, NOT per-audit) → **Moderate** with §9 routing: sonnet5 doers, opus/fable only for design + critical-verify. Sonnet-heavy keeps it modest. `[DEFAULT — bump for the self-heal-loop + Belk phases where correctness is worth it]`. **Per-audit RUNTIME cost is separate + tiny** (subscription + pennies of Gemini — verified 2026-07-02); the running system adds no new recurring API bill.
