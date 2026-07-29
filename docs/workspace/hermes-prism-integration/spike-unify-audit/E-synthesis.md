# Spike Synthesis — Unify (Telegram↔SPA), Hermes Fat-Audit, Skills Determinism, Self-Learning

Date: 2026-06-28. Source recon: A (hermes-caps), B (vps-audit), C (spa-recon), D (skills-survey).

---

## THREAD 1 — Telegram ↔ SPA unified chat + cross-device state

### The reframe (from C)
The SPA is **not** a static report renderer. It is **already a full chat app**: Next.js 15 + `@assistant-ui/react` + Vercel AI SDK v6, Clerk auth, Zustand, with a working agent **"aRRIe"** (25 grounded tools, SSE progress, 6-tab dashboard). Its **persona + grounding policy are hardcoded in `app/api/chat/route.ts`**. Report data comes from a **separate FastAPI backend** (`prism_platform/`, :8000), not static JSON.

So there are **TWO agent brains today**: aRRIe (web, own FastAPI tool-plane) and Hermes-PRISM (Telegram, gemini, L1/L4 report-QA grounding). Unification = pick one brain + give it a shared thread home.

### What Hermes natively supports (from A)
- **One SQLite store** `~/.hermes/state.db` for ALL channels (Telegram/CLI/API/cron). Sessions carry `user_id` + full history + FTS search. (`llms-full.txt:5111-5127`)
- **Sessions are keyed per-source**: `agent:main:{platform}:{chat_type}:{chat_id}`. Same human on Telegram vs web ⇒ **two different keys ⇒ two threads.** No native identity merge. (`:5545-5556`)
- **The API server writes to the SAME store** (`API_SERVER_ENABLED=true`, bearer key, :8642, CORS). Exposes:
  - `/v1/responses` (server-side state via `previous_response_id`/`conversation`)
  - **Sessions REST API** `/api/sessions/*` — read/patch/messages/fork/`chat`/`chat/stream`(SSE). An SPA can drive an existing session directly. (`:27220-27248`)
  - **`X-Hermes-Session-Key`** header — client passes a stable key → stable memory scope. (`:27267-27278`)
- `/handoff` = native baton-pass (re-binds same session id to another channel) — NOT live co-presence. (`:5271-5307`)

### Verdict
- **"Keep state, pick up phone↔laptop" = ACHIEVABLE.** Both clients resolve the **same `X-Hermes-Session-Key`** (derived from a rep identity), hydrate history via `/api/sessions/{id}/messages`, continue. This is exactly the user's ask.
- **"Same live transcript on both screens simultaneously" = NOT native** (would need `/handoff` baton or custom re-bind). The user did not ask for this — pickup-continuity is enough.
- **The gap PRISM must build:** a thin **identity map** (rep → {telegram_chat_id, web_clerk_userId, account_domain}) so both channels compute the SAME session key. e.g. `agent:main:prism:dm:{rep_id}:{domain}`.

### Build (W-D) — once the brain decision is made
1. On hermes-prism: `API_SERVER_ENABLED=true` + bearer + `API_SERVER_CORS_ORIGINS=<spa origin>`; Caddy-route it (today no port is published — B).
2. SPA: new `app/api/hermes/route.ts` (server-side proxy; keeps URL/bearer/session-key/Clerk userId off the client). **Read the Hermes wire format first (Read Receipt)** — message shape, SSE vs chunked, session-key header, auth. Repoint the existing `prism-chat.tsx` transport; don't rebuild the widget.
3. Identity map + session-key derivation shared by Telegram and web.
4. Gate `/api/chat` (currently PUBLIC — C) before it carries real intel.
5. **Move aRRIe persona + grounding into Hermes** (ties W-B/W-C) so both channels share one brain. Else they diverge.

### The fork that gates this → see DECISIONS
Tool-execution location: web tools hit FastAPI :8000; Hermes is on the VPS. If Hermes is the brain, does it (a) call the same FastAPI over the network, or (b) re-implement tools as Hermes skills? The grounding guarantee depends on which executes.

---

## THREAD 2 — Hermes "fat" audit → KEEP / DISABLE / CLEANUP (not delete)

**Confirmed pushback:** Hermes is a vendored, self-updating, self-modifying framework. Do NOT delete source files — break upgrades + the Curator. Lever = **config disable + deployment cleanup**.

### Config disable (mechanisms from A 2.1)
- `agent.disabled_toolsets:` (global off), `plugins.disabled:`, `gateway.platforms.<name>.enabled: false`.
- **DISABLE:** spotify, homeassistant, image_gen/video/video_gen, moa, discord(+admin), feishu_doc/drive, yuanbao, weixin/qqbot/wecom/dingtalk/bluebubbles/sms/email channels, computer_use, acp. Kanban optional. x_search optional.
- **KEEP:** web, terminal, file, browser, vision, memory, session_search, skills, delegation, clarify, cronjob, messaging; channels = telegram + api-server only.

### Deployment cleanup (from B — ~18 GB reclaimable, hygiene not urgency)
- `docker builder prune` → ~17 GB (0 active).
- `docker rmi` stale Temporal images (auto-setup 804MB, ui 102MB, postgres 420MB) — containers already gone.
- Remove dead Caddy route `temporal.contentengagement.info → :8088` (public hostname → nothing).

---

## THREAD 3 — Skills determinism + depth/accuracy (from D + 3 children)

### The pattern
Data **collection is already deterministic** (`collect-*.py` per skill). The reducible fat is **math + JSON-assembly masquerading as LLM work**. Genuine synthesis (narrative, email copy, talking points, quote-context) is **irreducibly LLM — leave it.**

### Ranked determinism targets (highest ROI first)
1. **`business-case`: build `calculate-roi.py`.** All 6 ROI components are LLM-computed today (15% deterministic) — top fabrication + non-reproducibility risk. Script the formulas; LLM only supplies labeled assumptions.
2. **`campaign-abx`: build `generate-abx-json.py`.** JSON assembly is pseudocode (lines 342–462), done by hand. Extract to a script.
3. **`techstack` Layer-3 network inspection → reuse `detect-search`.** Already a deterministic packet-inspection skill exists; stop re-doing it LLM-side. Dedup.
4. **`hiring` (1H): add a `collect-hiring.py`.** Only research skill with NO script; careers/job-board parsing is scriptable.
5. **`factcheck` / `eval`: ship the bash/python the SKILL.md describes but doesn't include** (Dims 1,2,4,5 are pure checks).

### Ranked accuracy / fabrication risks (worst first) + fix
1. **`business-case` ROI math** — LLM arithmetic, no validation → `calculate-roi.py` (same as #1 above).
2. **`campaign-abx` Email 3 financials + all copy** — financial figures recomputed by LLM → pull from the ROI script's output; copy stays LLM but cites script numbers.
3. **`financial-private` (35%)** — 6-source waterfall + "within 20%" confidence judged by LLM → script the numeric agreement + confidence tier.
4. **`competitors` (40%)** — Algolia-customer-portfolio discovery + scenario classification LLM-driven → script the algolia.com/customers scrape + vertical-match; LLM only picks the narrative.
5. **`intel-queries`** — query generation has no validation that queries are testable on the prospect site.

### Real BUGS (not fat)
- **`partner` (1K):** SKILL says "do NOT iterate a predetermined SI list," then hardcodes 4 SI-named WebSearch queries. Contradiction — fix one way or the other.
- **`industry` (1L):** `age_months>24` staleness filter is enforced in the script but **leaks on the WebSearch fallback** (can pull 2022 articles). Apply the date gate to the fallback path too.
- **`partner`:** no recency check on SI relationships (a 2020 press release scored same as 2025).
- **`hiring`:** no role-dedup across Layer1+Layer2; ICP keyword scoring can't tell "search engineer" from "search for candidates."

### Proposed cluster grouping for the deep-dive team (pending D's formalization)
- **C1 Financial/ROI math:** financial-public, financial-private, business-case → shared numeric engine + `calculate-roi.py`.
- **C2 Web-signal collectors:** social, news, hiring, investor(media) → Apify/Tavily + WebSearch-fallback hardening, date discipline.
- **C3 Tech/competitive:** techstack(+detect-search dedup), competitors, partner → network-inspection + portfolio-scrape scripts, fix the 1K/recency bugs.
- **C4 Company/industry context:** company, industry, queries → parent-entity + benchmark scripting, query-testability validation.
- **C5 Render/campaign assembly:** report, campaign-abx → `generate-abx-json.py`, schema validation.
- **C6 Gates:** factcheck, eval → ship the described check scripts; keep judgment dims on LLM.

---

## THREAD 4 — Hermes self-learning loop (the sleeper; ~unused today)

Hermes ships a real, documented self-improvement loop. PRISM uses ~none of it.

### Mechanisms (from A 3.x)
- **MEMORY.md (2,200 char) + USER.md (1,375 char)** — agent self-edits via `memory` tool; injected at session start. Tiny → heuristics only.
- **`skill_manage`** — agent writes its own SKILL.md on triggers (5+ tool calls, error recovery, **user correction**). `write_approval` gate.
- **Curator** — lifecycle for agent-created skills (active→stale→archived, 7d LLM review consolidates overlaps). **Only touches `agent_created` skills → the algolia-* hand-authored skills are SAFE.**
- **The loop:** every **10 user prompts** → forked agent saves to memory; every **10 tool iterations** → saves skills. Background fork, own cache.
- **Cron** — skill-backed scheduled jobs with `context_from` chaining.
- **External memory providers (8)** — Hindsight (`hindsight_reflect` synthesis), Honcho (identity mapping). For per-account bulk facts (built-in memory too small).
- **Persistent Goals (`/goal`)** — Ralph-loop with LLM judge: keeps working until done.

### How PRISM exploits it
1. **Audit outcomes → memory/skill writes** (the 10-prompt fork already fires during a run): persist "which queries failed on which sites," "which objections land."
2. **AE feedback → skill refinement** (user-correction is a `skill_manage` trigger) + `write_approval` review + Curator consolidation.
3. **Per-account deal intelligence → a memory provider** (Hindsight/Honcho) scoped by the stable session key → recalled on Telegram AND web.
4. **Cron skill-backed re-audits** with `context_from` → autonomous deltas.
5. **`/goal "PROCEED-grade audit for X"`** + judge → iterate research→browser→report→factcheck until the gate passes.

---

## CROSS-CUTTING: the one product, one brain principle
The unifying realization across all four threads: **Hermes should be the single brain; the SPA and Telegram are two windows onto it; the skills are its hands; the self-learning loop is how it gets better.** Today aRRIe (web) and Hermes-PRISM (Telegram) are two brains with two tool-planes. Collapsing to one is the spine that thread 1 (shared session), thread 3 (skills as Hermes's deterministic hands), and thread 4 (one memory/learning scope) all hang off.
