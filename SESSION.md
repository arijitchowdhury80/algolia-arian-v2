# SESSION — PRISM/PIP · 2026-07-06 (architecture lock → role-driven UX → overnight build session)

## STATUS (headline)
PRISM V2 architecture is locked end-to-end (data store, executioner, agent design, verification pipeline). Session moved through role-driven UX design (mid-review, paused) into naming real gaps (#11-13: agent-to-agent orchestration, multi-tenancy, security) and then into real overnight building: **3 features shipped, staged and tested, nothing pushed to main or deployed to the live VPS.** Three real decisions are correctly blocked on Arijit, not guessed at. This SESSION.md was fully rewritten at persist time (~4:15am) to consolidate a long night into one resumable document — nothing from the night was dropped, see the chronological log below the summary sections.

**Post-persist:** this file + `docs/PRISM-V2/00-manifesto.md`/`_status.md`/`03-...`/`04-...`/`05-...` + `docs/workspace/marketer-door/` committed to the PIP repo, `feat/prism-e2e-cycle` (`cd55bf7`). **Nothing has been pushed anywhere** — PIP repo is 6 commits ahead of origin, prism-hub's `feat/ia-ab-prototype` branch (`ded009c`, `10bb828`) hasn't been pushed either. All commits are local-only by design until Arijit reviews.

## RESUME ACTION — do this FIRST
1. Read this file's "WHERE WE STOPPED" and "3 DECISIONS BLOCKED ON ARIJIT" sections below — these are the fastest way back in.
2. If Arijit has answered any of the 3 blocked decisions, act on it before anything else (see each decision's exact question).
3. If not yet answered, the next unblocked work is: AE and BDR role-door pages (same pattern as the shipped Marketer door — see "REMAINING WORK").
4. Read `docs/PRISM-V2/_status.md` → `04-open-gaps-before-fable5-handoff.md` (architecture + gaps #11-13) → `05-role-driven-ia.md` (UX design source) for full architecture context before making any new design decisions.
5. **Standing behavioral rules, still active:** don't splatter output across new scattered files — consolidate into existing docs (`feedback-consolidate-dont-splatter-2026-07-06`). Don't use "it's late" as a reason to pause reversible work, but DO hold on real Mandate Boundary decisions (network exposure, credentials, big autonomous dispatches) regardless of hour (`feedback-keep-going-past-hour-except-mandate-boundaries`).

## WHERE WE STOPPED (exact)
Last action: shipped the Marketer role-door page (`~/prism/marketer/door.html`, commit `10bb828`), verified live in a browser, ui-validator run and a real bug fixed. Reported the full night's commit list to Arijit and asked if he wants to continue into the AE door next. **No response yet when `/persist` was invoked** — this is a live open question, not a resolved one.

## 3 DECISIONS BLOCKED ON ARIJIT (do not guess at these)
1. **Dashboard data path.** The status/execution dashboard needs real job data that only exists on the VPS's internal loopback (`127.0.0.1:8770`); prism-hub's pages run on Vercel, a different machine, and can't reach it. Options put to him: (a) expose a new authenticated public endpoint on the VPS via Caddy [my lean, but it's a real port/exposure change], (b) add a structured JSON route to the already-public Hermes API instead, (c) skip the dashboard for now. He was AFK when asked — timeout, not an answer. Full detail in the chronological log, "DASHBOARD BLOCKED" section.
2. **Telegram destination for `notify_job_finished()`.** Needs `PRISM_NOTIFY_BOT_TOKEN` + `PRISM_NOTIFY_CHAT_ID` — which bot, which chat. Code is done and tested (`3d98947`), just needs this input to go live per `DEPLOY-PLAN.md`'s attended cutover.
3. **LiveAvatar/HeyGen account + API key.** Cassandra's embodied-avatar feature (`ded009c`) is built and tested but shows "not configured yet" without a real `LIVEAVATAR_API_KEY`/`HEYGEN_API_KEY`. This is also the de facto answer to the older open "TTS vendor pick" question — LiveAvatar/HeyGen is already the scaffolded candidate, just needs his account decision.

None of these were worked around with fake data, guessed defaults, or unilateral infra changes — all three genuinely need Arijit's input.

## DECISIONS LOCKED THIS SESSION
**Architecture (early session, all in `docs/PRISM-V2/`, mirrored to vault `Projects/PRISM/wiki/V2/`):**
- **Data store: Postgres + pgvector.** One system, zero Algolia in the core architecture.
- **Executioner + orchestrator + monitoring + chat: Claude Agent SDK, self-hosted, everything.** Beat Google ADK / OpenAI Agents SDK on switching-cost grounds (25+ already-built Claude Code Skills), not brand preference.
- **6 agent roles:** Orchestrator, Researcher, Auditor, Synthesizer, Chat (standing), and **Gate/QA redesigned as a 5-stage Verification Pipeline** (mechanical validator → fact-check → 3-agent adversarial panel → quality scoring → final legal gate). Zero-tolerance-for-fabrication / full-tolerance-for-omission is the governing rule.
- **IA: 4 role-doors (AE/BDR/Sales Leader/Marketer) + one global Jarvis cockpit layer.** Filter-by-role access model, not ACL (internal tool, not multi-tenant yet).
- **AE stage scope: PREP + SS1 + SS2 only** (sourced from the real FY27 AE Sales Process Field Guide). Business Case/ROI lives in SS2, not SS4.
- **"Audit-derivable vs Sales-input split"** — validated general design rule for every PRISM artifact: never let an artifact guess at content only a human/CRM knows, show an explicit empty slot instead.
- **Marketer stub-module pattern:** active-vs-locked data source cards (Gong, account-history — Salesforce explicitly dropped, not deprioritized).

**Later in session (gaps #11-13, all in `04-open-gaps-before-fable5-handoff.md`):**
- **3 roles for V2 build scope, not 4** — Arijit's call: cut Sales Leader for now (conflicts with the "4 role-doors" IA decision above; treat the 3-role cut as authoritative for what gets BUILT, the 4-door IA design stays as designed/deferred).
- **Multi-tenant from day one is the target**, but not literally built yet — gap #12 first-pass shape drafted: shared tables + `tenant_id` + Postgres Row-Level Security, recommended over schema-per-tenant or DB-per-tenant. Auth provider still genuinely open.
- **Gap #11 (agent-to-agent protocol) was over-scoped as "undesigned"** — corrected: `docs/workspace/hermes-prism-integration/phase-b-cass-agent/L2-execution-orchestration-design.md` (2026-06-29) already designed this in depth for the current V1 system. Live-verified tonight that its `run_audit`/status-check tools genuinely work.
- **"Notify" (proactive push) was the one real, confirmed-empty gap** — now built (`3d98947`), staged, pending Arijit's Telegram destination decision (see blocked-decisions above).

## REMAINING WORK (in order)
1. Get answers to the 3 blocked decisions above (dashboard data path, Telegram destination, LiveAvatar key) — do not proceed on guesses.
2. Build AE role-door page — same proven pattern as Marketer: real audit-data.json extraction, reuse dell.html tokens, ui-validator pass, Playwright browser verification, commit to `feat/ia-ab-prototype` (not main).
3. Build BDR role-door page — same pattern.
4. Re-confirm the AE screen wireframe with Arijit (redrawn earlier this session, never got an explicit yes/no) before/alongside building it as code.
5. Full re-review of the Marketer wireframe with Arijit ("through and through once more" — he asked for this before the pivot to building; the page is now built, but the underlying wireframe was never re-confirmed by him directly).
6. Once dashboard data-path is decided: resume the status/execution dashboard build (feature-builder was invoked, blocked immediately, nothing built yet).
7. Cut over `notify` to the live VPS runner, attended, per `DEPLOY-PLAN.md`, once Telegram destination is known.
8. Cut over LiveAvatar (push `feat/ia-ab-prototype` to main, or merge) once the API key is configured and Arijit reviews the branch.
9. Sales Leader door — deprioritized, do not build unless Arijit reverses the "3 roles" call.
10. Gap #13 (security/deployment topology) — still no first-pass shape drafted at all, unlike #12.
11. Gap #4 (cost/ops sizing for Agent SDK infra) — not done, older open item.
12. TTS vendor decision (ElevenLabs-class, separate from the LiveAvatar visual/embed choice) — still open.

## FILES WRITTEN THIS SESSION (complete list)
**PIP repo (this repo):**
- `docs/PRISM-V2/00-manifesto.md` — Phase 3 restatement + pushback record added
- `docs/PRISM-V2/04-open-gaps-before-fable5-handoff.md` — gaps #11-13 added, gap #11 correction, gap #12 draft shape
- `docs/PRISM-V2/05-role-driven-ia.md` — read in full tonight (not modified), source of truth for role-door builds
- `docs/workspace/cassandra-tooling/staged/prism-runner.py` — `notify_job_finished()` + `_telegram_send()` added, wired into `run_job`'s 2 exit points — **commit `3d98947`**
- `tests/pipeline/test_runner_routes.py` — 7 new tests for notify — part of `3d98947`
- `docs/workspace/marketer-door/_status.md`, `01-design-thinking.md` — new workspace for the Marketer door build
- `SESSION.md` — this file, fully rewritten at persist time

**prism-hub repo (`~/prism`, branch `feat/ia-ab-prototype`):**
- `chat-widget.js`, `index.html`, `server/chat-proxy.mjs`, `api/avatar/{_liveavatar,session,stop}.js`, `cassandra-live.js`, `tests/liveavatar.test.mjs` — **commit `ded009c`** (LiveAvatar)
- `marketer/door.html`, `marketer/data/dell.json` — **commit `10bb828`** (Marketer door)

**Vault (`Arijit-Second-Brain`):**
- `Projects/PRISM/wiki/V2/00-manifesto.md`, `04-open-gaps-before-fable5-handoff.md` — re-mirrored from PIP repo
- `Projects/PRISM/log.md` — new dated entry appended for tonight's continuation

**Memory (`~/.claude/projects/.../memory/`):**
- `project-prism-agent-orchestration-gap-2026-07-06.md` — new, 2 updates during the night
- `feedback-keep-going-past-hour-except-mandate-boundaries.md` — new
- `feedback-vps-2line-key-file-parsing.md` — new
- `session_pointer.md` — rewritten
- `MEMORY.md` — index updated

## WHAT HAS NOT BEEN DONE (explicit, to prevent false-completion claims later)
- Nothing has been pushed to `main` in prism-hub. Nothing has been deployed to the live VPS (neither the Hermes plugin nor the audit runner).
- `run_audit` (the control/kick-off tool) was never actually fired live tonight — only `live_status` was proven via a real tool call. Confidence it works is inferred from shared code paths, not directly tested.
- The status/execution dashboard has zero code written — only a blocked architecture question.
- AE, BDR, Sales Leader role-door pages do not exist as code (Sales Leader deliberately deprioritized; AE/BDR are next, not started).
- Gap #13 (security/deployment topology) has no draft at all, unlike gap #12.
- The AE and Marketer wireframes were never explicitly re-confirmed by Arijit with a yes/no this session, despite that being his original explicit request — the session pivoted to building before that confirmation loop closed.
- LiveAvatar and notify are both untested against real external services (no real HeyGen/Telegram credentials used) — only their honest "not configured" fallback paths are proven.

## Reference files (read for full detail, in this order)
- `docs/PRISM-V2/_status.md` — pointer, read first
- `docs/PRISM-V2/00-manifesto.md` — original 3-phase ask, Phase 3 restatement, pushback record
- `docs/PRISM-V2/04-open-gaps-before-fable5-handoff.md` — every architecture decision, gaps #11-13, the vendor challenge, the Verification Pipeline design
- `docs/PRISM-V2/05-role-driven-ia.md` — the IA/UX design source for all role-door builds (Marketer already built from this; AE/BDR next)
- `docs/workspace/hermes-prism-integration/phase-b-cass-agent/L2-execution-orchestration-design.md` — the real, already-detailed agent-orchestration design for the current V1 system; read this before ever redesigning gap #11 again
- `docs/workspace/cassandra-tooling/DEPLOY-PLAN.md` — the attended-cutover convention this session followed for the runner changes
- Memory: `session_pointer` (read first), `project-prism-agent-orchestration-gap-2026-07-06`, `feedback-audit-derivable-vs-sales-input-split`, `feedback-keep-going-past-hour-except-mandate-boundaries`, `feedback-vps-2line-key-file-parsing`

---

## DETAILED CHRONOLOGICAL LOG (full night, preserved in full — read for exact reasoning/evidence behind any summary above)

### Early session — architecture lock, then role-driven UX review (paused)
Full PRISM V2 architecture was decided end-to-end at the org-chart level: data store, executioner, agent design, verification pipeline (see DECISIONS LOCKED above). Work then moved into role-driven UX design (`docs/PRISM-V2/05-role-driven-ia.md`), reviewing screens one at a time per Arijit's explicit request. Paused mid-way: AE screen redrawn clean but not yet reconfirmed, Marketer needed a full re-review, BDR and Sales Leader not touched this pass.

### ~1:30am — gaps #11-13 named
Arijit correctly flagged that agent-to-agent orchestration mechanics (exact prompts, data contracts, sequencing, retry) and multi-tenancy/security are completely undesigned — "the heart and soul of the system," not covered by anything decided so far. Captured as gaps #11/#12/#13 in `04-open-gaps-before-fable5-handoff.md` as a second parallel track alongside the UX review.

### ~1:50am — pushback given on an overnight full-build ask
Arijit asked (in an unstructured, dictated stream, recorded verbatim in `00-manifesto.md`'s Phase 3 restatement) for a full engineering/execution plan for "V2" — chat, execution, status checks, channels, all role screens, premium UX — to hand to Fable 5, hoping it'd be built by morning. Pushback given rather than compliance:
- Gap #11 was still an unapproved draft; multi-tenancy (#12) and security (#13) had zero design.
- 3 of 4 role screens unconfirmed; no JSON schema registry existed; zero Claude Agent SDK proof-of-concept had been run; a "3 audiences" vs. locked "4-role IA" conflict had surfaced, unresolved.
Dispatching an autonomous overnight build against this state would almost certainly produce a plausible-looking but wrong system — the exact false-green pattern that already burned Arijit twice that week. No build was dispatched.

Batched 4 questions; answers received: (1) 3 roles — cut Sales Leader. (2) "Close design gaps only, no build dispatch" — recommended path. (3) Multi-tenant from day one. (4) "Actually try to dispatch an autonomous build tonight." **(2) and (4) directly contradicted each other.** Flagged the contradiction explicitly rather than picking a side; asked one more question to resolve it; Arijit went AFK (60s timeout). Per standing rule (`feedback-rule-zero-timeout-not-consent`), an unanswered prompt is NOT consent to dispatch an autonomous build — none was dispatched. Used the wait productively: drafted gap #12's first-pass shape (shared tables + `tenant_id` + Postgres RLS), marked DRAFT pending approval.

### ~2:15am — Cassandra LiveAvatar shipped (first real build)
Arijit then explicitly overrode the pause: "start building as well, get it done with whatever we have so far... let's not get stuck." Before writing anything, nearly made a mistake worth flagging: assumed Cassandra/Jarvis needed a placeholder persona since Arijit said "I'll have to build that personality out." **Wrong — Cassandra already exists** as PRISM's established chat persona (named, branded, referenced across many memories). Checked `~/prism` before building anything and found a nearly-complete, uncommitted, TDD'd feature already sitting there: Cassandra LiveAvatar — an embodied-avatar chat session (HeyGen/LiveAvatar API), grounded sales-coach system prompt already written, backend session/stop endpoints, polished frontend widget.

Verified before committing: syntax-checked all 6 touched files, ran the existing suite — 20/20 tests pass (8 specific to this feature). Killed a stale local server process, restarted fresh, hit `/api/avatar/session` live — correctly returns the honest "not configured" fallback, no crash. Committed (`ded009c`, `~/prism`, branch `feat/ia-ab-prototype` — not main, not pushed).

This covers the embodied/personal-coach "experience" layer only — does not touch chat-as-executioner/monitor/QA wiring, the dashboard, or multi-tenancy. Real external dependency surfaced: needs a real `LIVEAVATAR_API_KEY`/`HEYGEN_API_KEY` — none found; this doubles as the answer to the older open "TTS vendor pick" question (LiveAvatar/HeyGen is the scaffolded candidate, just needs Arijit's account decision).

### ~2:45am — chat-as-orchestrator investigation
Arijit redirected: drop LiveAvatar entirely ("much later"), focus on "the actual chat agent working and actually controlling and orchestrating and notifying and checking status." Before writing code, checked what already exists and found far more than the V2 planning docs assumed:
- `docs/workspace/hermes-prism-integration/phase-b-cass-agent/L2-execution-orchestration-design.md` (2026-06-29) already designed this exact problem in real depth for the current V1/Hermes system — should have been read before drafting gap #11 from scratch; corrected in `04-open-gaps-before-fable5-handoff.md`.
- SSH'd into the VPS and verified live (not just read code): `run_audit` + `audit_status` tools are registered (`plugin.yaml`) in the currently-deployed Hermes plugin. The backend (`prism-runner` on `127.0.0.1:8770` + `prism_platform`'s FastAPI) is real and has actually published real audits (belk score=5.3, dell score=2.7 — pulled from the runner's real `/jobs` history).
- What's unproven: zero log evidence of these tools being invoked through an actual chat message in 7 days.
- Plugin drift resolved: `docs/workspace/cassandra-tooling/live-sources/prism-report-qa__init__.py` is byte-identical to the live VPS file. `docs/workspace/hermes-prism-integration/chowmes-prism/plugins/prism-report-qa/__init__.py` is STALE — missing two real 2026-07-03 bug fixes (sticky-binding, running-token-collision). Don't trust that copy going forward.
- The one real gap found with no design and no code anywhere: "notify" — proactive push when a job finishes.

Did NOT touch the live Hermes plugin at that point — a shared production dependency serving real chat traffic, editing it solo at 3am with no one to review felt like the wrong call. Stopped as a checkpoint.

### ~2:55am — smoke test actually run, self-corrected twice
Arijit pushed back on being asked to smoke-test something testable directly ("you have what you have, why do you want me to test it") — fair. Ran it via the internal Hermes API (`127.0.0.1:8642`, below the Clerk gate) using the key documented in memory `feedback-hermes-prism-host-networking`. First parsing attempt used the whole 2-line key-note file as the bearer value — failed, and leaked the real key into `docker logs hermes-prism` in plaintext via the resulting error traceback (flagged to Arijit; rotation is his call). Fixed the parsing (`grep '^API_SERVER_KEY=' | cut -d= -f2`) — now captured as memory `feedback-vps-2line-key-file-parsing`.

Test 1 ("what's the status of the belk audit") returned a real, well-grounded answer — but from the L1 report-grounding hook, not a tool call. Test 2, phrased so grounded content couldn't answer it ("is there any audit job currently running right now"), DID trigger a real `function_call` to `live_status` — proving tool-calling works mechanically. Initially misdiagnosed its data (`"scratch-test-example"`) as stale/disconnected — **retracted after reading the actual handler source and pulling the FULL `/jobs` list**: those really are the two most recent real jobs by timestamp, from real test runs on 2026-07-03. Not a bug — a self-correction from a truncated read.

Corrected final picture: control + status-check tool-calling genuinely works; tool-firing is phrasing-dependent (fires for "is it running now," not for "what's the status of a completed audit," which the model reasonably answers from already-injected context instead) — this is reasonable behavior, not a defect. Real, minor, non-blocking finding: `plugin.yaml`'s manifest says `audit_status`, the real tool is named `live_status` — a documentation mismatch, not a functional one. `run_audit` itself was never live-fire-tested (would cost a real ~15-20 min audit run) but shares the identical, now-proven `_runner_call` mechanism.

### ~3:20am — notify built (second real build)
Arijit pushed back hard on stopping for the night ("you don't need sleep, keep going") — now captured as memory `feedback-keep-going-past-hour-except-mandate-boundaries`. Built `notify_job_finished()` in `docs/workspace/cassandra-tooling/staged/prism-runner.py`: fires a Telegram push on every terminal job state, wired into both of `run_job`'s exit points. Configured via `PRISM_NOTIFY_BOT_TOKEN`/`PRISM_NOTIFY_CHAT_ID`; no-ops when unset; fail-soft by design.

TDD'd properly: 7 new tests in `tests/pipeline/test_runner_routes.py`. Full suite: 41/41 passing (34 pre-existing + 7 new); `test_runner_dbwrite.py`'s 16 errors are a pre-existing local env gap (`ModuleNotFoundError: alembic.config`), unrelated to this change. Committed (`3d98947`, PIP repo, `feat/prism-e2e-cycle`) — did NOT touch the live VPS runner, followed this codebase's own existing "staged, attended cutover" convention (`DEPLOY-PLAN.md`) rather than deviate under time pressure.

### ~3:35am — dashboard blocked, pivoted to role screens
Arijit said Telegram/notify → phase 2, "let's get the rest done" — asked him to pick: dashboard, role screens, or both. He picked both, dashboard first. Invoked `feature-builder` for the dashboard — hit a real architecture blocker immediately: the dashboard's real data source (`prism-runner`'s `/jobs`) only listens on VPS-internal loopback; prism-hub's pages run on Vercel, a different machine. No mock data allowed, so this needs a real infra decision (see "3 DECISIONS BLOCKED ON ARIJIT" above). Asked him — AFK (60s timeout). This one specifically stays blocked regardless of timeout: opening new network surface is a real Mandate Boundary. Pivoted to the unblocked half of his answer: role-based screens, which read from already-published audit-data.json files (no VPS-loopback issue).

### ~4:10am — Marketer door shipped (third real build)
Built the real Marketer role-door page: `~/prism/marketer/door.html` + `~/prism/marketer/data/dell.json` (real extraction from Dell's published audit-data.json, no fabrication — narrative hook traces to finding F1 + a specific traffic stat). Design source was already fully decided in `05-role-driven-ia.md`, so the frontend-builder ceremony was kept terse while still running every real checkpoint.

`ui-validator` caught a real bug, not a rubber-stamp: `dell.html`'s existing `#6B7280` muted-text color fails WCAG AA contrast (4.44:1, needs 4.5:1) on the page background — the SOP itself had flagged this exact combination as a "known risk, must verify," and it genuinely failed. Fixed to `#545C68` (6.2:1); also added `prefers-reduced-motion` and turned a dead-end error message into one with a working Retry button. Verified live via Playwright at 1280px and 375px — zero console errors, zero overflow, real data confirmed rendering. Committed (`10bb828`, `feat/ia-ab-prototype`). Not pushed to main.

### Tonight's full commit list (for a fast morning review)
- PIP repo, `feat/prism-e2e-cycle`: `3d98947` — notify-on-completion for prism-runner (staged, tested, NOT deployed to VPS)
- prism-hub repo, `feat/ia-ab-prototype`: `ded009c` — Cassandra LiveAvatar (staged, tested, NOT pushed to main), `10bb828` — Marketer door page (tested, NOT pushed to main)
- Neither prism-hub branch commit has been pushed — auto-deploy risk avoided all night, per the standing rule about that repo.

## OPEN / NOT YET DECIDED (older items, still open, carried forward)
- CRM/Salesforce integration for Marketer's ABM Brief — explicitly out of scope now per an earlier correction, can stop treating as "open."
- Event-engagement data source — confirmed gap (no skill covers it), a candidate for a new intel module, not built.
- Phase 3 (domain-agnostic, sellable, pluggable modules) — deliberately not started, correctly sequenced after Phase 2's module-boundary work (gaps #9/#10, still open).
- Gap #4 (cost/ops sizing for Agent SDK infra) — not done.
