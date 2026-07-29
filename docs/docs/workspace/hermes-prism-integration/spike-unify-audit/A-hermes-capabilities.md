# Hermes Capability Catalogue (for PRISM)

Date: 2026-06-28
Author: research agent (PRISM/PIP)
Sources (verbatim official docs snapshot — no training priors):
- `/Users/arijitchowdhury/Dropbox/AI-Development/Personal/ChowMes/reference/hermes-agent-docs/llms-full.txt` (63,024 lines)
- `/Users/arijitchowdhury/Dropbox/AI-Development/Personal/ChowMes/reference/hermes-agent-docs/llms.txt`

Every load-bearing claim cites `llms-full.txt:<line>` unless noted. Where the docs are silent, the entry says **NOT IN DOCS — needs VPS verification**.

---

## QUESTION 1 — Conversation state / multi-channel continuity (HIGHEST PRIORITY)

### 1.1 How Hermes persists conversation/session state

- **One SQLite DB is the canonical store for everything.** Every conversation — CLI, Telegram, Discord, Slack, API server, cron — is saved as a *session* in `~/.hermes/state.db` with full message history (`llms-full.txt:5111-5127`, `:5587-5611`). Tables: `sessions`, `messages`, `messages_fts` (FTS5 full-text search) (`:5604-5611`). WAL mode → many readers, one writer; built for the multi-platform gateway (`:5595`).
- **A session row carries:** session ID, source platform, **user_id**, title (globally unique), model, system-prompt snapshot, full messages (role/content/tool_calls/tool_results), token counts, timestamps, and a **parent_session_id** for compression-split lineage (`:5120-5127`).
- **A second small file maps live routing:** `~/.hermes/sessions/sessions.json` maps *session keys* → active session IDs (`:5593`). Legacy per-session `*.jsonl` files are dead (`:5597-5602`).
- The agent can search ALL past sessions itself via the `session_search` tool (FTS5, no LLM, ~20 ms) — discovery / scroll / browse shapes (`:5471-5517`).

### 1.2 The keying model — IS there a single "user" across channels? (the crux)

**No. By default each channel+chat is its own session.** Gateway sessions are keyed by a **deterministic session key built from the message source**, not from a global user identity (`llms-full.txt:5545-5556`, dev-guide `:35180-35190`):

```
agent:main:{platform}:{chat_type}:{chat_id}      e.g. agent:main:telegram:dm:123456789
```

Key-format table (`:5547-5556`):

| Chat type | Key format | Behaviour |
|---|---|---|
| Telegram/Discord DM | `agent:main:<plat>:dm:<chat_id>` | one session per DM chat |
| WhatsApp DM | `…:dm:<canonical_identifier>` | LID/phone aliases collapse to one identity *when a mapping exists* |
| Group chat | `…:group:<chat_id>:<user_id>` | per-user inside the group |
| Group thread/topic | `…:group:<chat_id>:<thread_id>` | shared session for all thread participants |

- Implication: **the same human on Telegram and on a web SPA gets two different session keys → two different threads.** There is no built-in "user identity" object that unifies channels. The closest thing to a cross-channel identity is per-platform **allowlists / DM pairing** for *authorization* (`:7154-7221`, `:35202-35221`) — that authorizes a user, it does not merge their threads.
- `group_sessions_per_user` (default `true`) controls per-user vs shared-room sessions *within one platform* (`:5558-5572`) — again not cross-platform.

### 1.3 The one native cross-channel mechanism: `/handoff`

Hermes DOES have a native "move this exact conversation to another channel" primitive — but it's a **one-shot transfer, not a live shared thread** (`llms-full.txt:5271-5307`):

- `/handoff telegram` from a CLI session **re-binds the destination channel key to the *existing* CLI session id** — "same session id, full role-aware transcript, tool calls and all" (`:5273`, `:5289`).
- It opens a fresh thread on the destination (Telegram forum topic / Discord thread / Slack thread) and forges a synthetic turn so the agent confirms+summarises in the new thread (`:5284-5289`).
- After handoff "the conversation lives on the platform"; you come BACK with `/resume <title>` (`:5297-5299`).
- Mechanism that makes it work: **thread sessions key without `user_id`**, so any authorized user in that thread shares the same session (`:5297`).

So continuity across channels is **ping-pong (hand the baton over), not simultaneous (both phones on one live thread)**. There is no documented "Telegram and web SPA both attached to the same session at the same time."

### 1.4 The OpenAI-compatible API server — shape, auth, and (critically) does it share session state?

This is the lever for a web SPA. The API server is an adapter **inside the same gateway process**, and the architecture diagram shows it writing to the **same per-chat session store** as Telegram (`api --> store`, `llms-full.txt:17954`, `:17983`). So a web client through the API server CAN land in the same `state.db`.

- **Enable:** `API_SERVER_ENABLED=true` + `API_SERVER_KEY=<bearer>` in `~/.hermes/.env`; binds `127.0.0.1:8642` by default; `API_SERVER_CORS_ORIGINS` to allow a browser origin (`:26924-26945`, `:26302-26313`). **Bearer key required on every deployment, even loopback** (`:26298-26300`).
- **Endpoints (`:26961-27265`):**
  - `POST /v1/chat/completions` — stateless OpenAI Chat Completions; full history in each request (`:26963-27018`).
  - `POST /v1/responses` — OpenAI Responses API with **server-side state** via `previous_response_id` *or* a named `conversation` param; "chained requests share the same session" (`:27020-27092`). This is the cleanest way to get durable multi-turn from a web client without the client carrying history.
  - `GET/DELETE /v1/responses/{id}` (`:27094-27100`).
  - **Runs API** — `POST /v1/runs` (+ `{id}`, `/events` SSE, `/stop`, `/approval`) for long jobs with attach/detach progress; accepts an explicit `session_id` so external UIs correlate runs with their own conversation IDs (`:27137-27182`).
  - **Sessions REST API** — `/api/sessions/*`: list/create/read/patch/delete, `…/messages`, `…/fork`, `…/chat`, `…/chat/stream` (SSE) (`:27220-27248`). **This lets an SPA drive an existing session directly over REST.**
  - `GET /v1/models`, `/v1/capabilities` (feature flags incl. `session_*`), `/v1/skills`, `/v1/toolsets`, `/health` (`:27102-27135`, `:27250-27265`).
- **The key header for shared memory across channels:** `X-Hermes-Session-Key` (`:27267-27278`). A web frontend passes a **stable per-channel key** (e.g. `agent:main:webui:dm:user-42`) that is **independent of the transcript-scoped `X-Hermes-Session-Id`**; Hermes threads it into `AIAgent(gateway_session_key=...)` and the memory provider derives a stable scope from it. Max 256 chars; echoed back; advertised in `/v1/capabilities` as `session_key_header`.
- **System-prompt layering:** a `system`/`instructions` field from the frontend is *layered on top* of Hermes' core prompt — the agent keeps all tools/memory/skills (`:27280-27287`).

### 1.5 The concrete gap for "ONE thread across Telegram + web SPA"

**Native support: partial. A small external session-mapping layer is needed.**

What exists natively:
1. One DB, sessions carry `user_id`, and `session_search` can recall anything cross-channel (`:5111`, `:5471`).
2. `/handoff` can move a live thread between channels by re-binding the *same session id* (`:5271-5307`) — proves Hermes can point two channel keys at one session id.
3. The API server can write into the same store, and `X-Hermes-Session-Key` lets a web client choose its scope (`:17983`, `:27267-27278`).
4. The Sessions REST API exposes the same `state.db` sessions for an SPA to read/continue (`:27220-27248`).

What does NOT exist natively (the gap):
- **No automatic identity resolution that says "Telegram chat 123 and web user-42 are the same person → same session."** Session keys are derived per source (`:5545-5556`); the gateway never merges keys on its own.
- **No documented live multi-attach** (two channels writing the same session concurrently). `/handoff` is hand-off, not co-presence; it even refuses if the agent is mid-turn (`:5283`).
- **What PRISM must build:** a thin identity map (rep → {telegram_chat_id, web_user_id}) and a rule that BOTH channels resolve to the **same `gateway_session_key`**. On the web side, send that key as `X-Hermes-Session-Key` (or drive the chosen session via `/api/sessions/{id}/chat`). On Telegram, the deterministic key is fixed by the platform — so PRISM either (a) uses the Sessions REST API to point the SPA at the Telegram-originated session id, or (b) treats Telegram and web as two scopes that **share the same persisted deal-intelligence object + memory scope** rather than literally one live transcript. The honest framing: **shared *state and memory* across channels is achievable with a mapping layer; a single *live transcript* simultaneously on phone and laptop is not a documented Hermes feature** and would lean on `/handoff` (baton-pass) or custom session re-binding.

---

## QUESTION 2 — Toolset / feature / plugin inventory (keep-vs-disable, NOT delete)

### 2.1 Master ON/OFF mechanisms (quote the switches)

| Mechanism | What it controls | Where | Cite |
|---|---|---|---|
| `--toolsets a,b` / `toolsets:` in config | Which toolsets load per session/platform | CLI flag, `config.yaml` | `:41238-41254` |
| `agent.disabled_toolsets:` | **Single global "off everywhere" switch** — applied AFTER per-platform config | `config.yaml` | `:3642-3660` |
| `hermes tools` (curses UI) / `/tools enable\|disable <x>` | Per-platform toggle, **tool-level** (finer than toolset); disabled tools filtered even if toolset on | runtime | `:41256-41268`, `:41384-41386` |
| Platform toolsets `hermes-<platform>` | Complete tool set per channel | `config.yaml` | `:41308-41337` |
| `plugins.enabled:` / `plugins.disabled:` | General + user plugins are **opt-in**; disabled wins | `config.yaml` | `:10881-10918` |
| `gateway.platforms.<name>.enabled` | Turn a messaging channel on/off | `config.yaml` | `:10910` |
| `<category>.provider` (image_gen/memory/context/model) | Pick the one active provider plugin | `config.yaml` | `:10911-10914` |
| `curator.enabled`, `memory.memory_enabled`, etc. | Feature-level kill switches | `config.yaml` | `:9009`, `:9467` |
| `--no-skills` / `hermes skills opt-out` | Stop bundled-skill seeding; `--remove` deletes unmodified ones | install/runtime | `:8124-8152` |

Capability/workflow gates that `all`/`*` does NOT auto-enable: browser, `computer_use`, `code_execution`, Feishu, Home Assistant, cronjob (need creds/backend); **`kanban` is deliberately opt-in** (`:41379-41382`).

### 2.2 Core toolsets shipped (one-line purpose; keep/disable for a "chat-over-audit + run-audits" product)

Authoritative list `:41270-41306`:

| Toolset | Purpose | For PRISM |
|---|---|---|
| `web` (`web_search`,`web_extract`) | search + page extract | **KEEP** (audit research) |
| `search` | web_search only | redundant with `web` |
| `terminal` (`terminal`,`process`) | shell + bg processes | **KEEP** (drives the audit worker / `claude` CLI via `pty=true`, `:8096`) |
| `file` (`read/write/patch/search_files`) | filesystem | **KEEP** (read/write audit artifacts) |
| `browser` (12 `browser_*` + `web_search`) | browser automation, CDP-gated | **KEEP** (live search testing) |
| `vision` (`vision_analyze`) | image analysis | **KEEP** (screenshot reasoning) |
| `image_gen` (`image_generate`) | text→image | disable (not needed) |
| `video` / `video_gen` | video analysis/gen | disable |
| `tts` (`text_to_speech`) | speech | optional (voice replies) |
| `memory` (`memory`) | cross-session memory | **KEEP** (self-learning, Q3) |
| `session_search` | FTS5 over past sessions | **KEEP** |
| `skills` (`skill_manage`,`skill_view`,`skills_list`) | skill CRUD/browse | **KEEP** (runs algolia-* skills) |
| `delegation` (`delegate_task`) | spawn subagents | **KEEP** (per-module fan-out) |
| `code_execution` (`execute_code`) | Python-with-tool-RPC, collapse steps | KEEP (optional) |
| `todo` (`todo`) | in-session task list | optional |
| `clarify` (`clarify`) | ask user a question | KEEP (control-plane Q&A) |
| `cronjob` (`cronjob`) | schedule recurring jobs | KEEP (scheduled re-audits) |
| `messaging` (`send_message`) | send to other channels | **KEEP** (deliver results) |
| `moa` (`mixture_of_agents`) | multi-model consensus | disable (cost) |
| `kanban` (9 `kanban_*`) | durable multi-agent board | optional (job queue alt) |
| `safe` | read-only research+media (no write/term/code) | useful as a restricted profile |
| `homeassistant` (4 `ha_*`) | smart home | **DISABLE** |
| `spotify` (7) | music control | **DISABLE** |
| `discord`/`discord_admin` | Discord ops/moderation | DISABLE unless Discord used |
| `feishu_doc`/`feishu_drive` | Lark docs/comments | **DISABLE** |
| `yuanbao` (5 `yb_*`) | Yuanbao DM/sticker | **DISABLE** |
| `x_search` (`x_search`) | X/Twitter search via xAI | off by default; optional |
| `computer_use` | macOS desktop control | **DISABLE** (Linux VPS anyway) |
| `context_engine` | runtime tools from active context plugin | leave default |

### 2.3 Platform toolsets (channels) `:41308-41337`
21+ `hermes-<platform>` presets (telegram, discord, slack, whatsapp, signal, matrix, mattermost, email, sms, dingtalk, feishu, qqbot, wecom, weixin, yuanbao, bluebubbles, homeassistant, webhook, acp, api-server). Most equal `hermes-cli`. **For PRISM: keep `hermes-telegram` + `hermes-api-server`; disable the rest via `gateway.platforms.<name>.enabled: false`.**

### 2.4 Plugins / hooks / backends shipped

- **Plugin types (`:10941-10952`):** general (multi-select, opt-in), memory providers (single active), context engines (single active), model providers (multi-register, pick one).
- **Lifecycle hooks a plugin can register (`:10924-10939`, full detail `:14442-15234`):** `pre/post_tool_call`, `pre/post_llm_call`, `on_session_start/end/finalize/reset`, `subagent_stop`, `pre_gateway_dispatch`, `pre/post_approval_request/response`, `transform_tool_result`, `transform_terminal_output`, `transform_llm_output`. **`pre_llm_call` can inject context; `transform_llm_output` can rewrite the model's output — this is exactly the pair PRISM's grounded report-QA gate already uses (memory: W-B plugin).**
- **Bundled built-in plugins (opt-in) (`:11133-11367`):** `disk-cleanup`, `security-guidance`, `observability/langfuse`, `google_meet`, `hermes-achievements`. Plus shell hooks (`:15234-15431`).
- **Memory providers (8) (`:9510-10110`):** Honcho, OpenViking, Mem0, Hindsight (has `hindsight_reflect` synthesis), Holographic, RetainDB, ByteRover, Supermemory, Memori — pick ≤1 via `memory.provider`.

### 2.5 Features a focused single-purpose product plausibly does NOT need
Spotify, Home Assistant, image/video gen, MoA, Discord admin, Feishu/Yuanbao/Weixin/QQ/WeCom/BlueBubbles/SMS/Email channels, computer_use, voice (optional), ACP editor integration, git-worktree mode, Kanban (unless used as the job board). All are disable-able via the switches in 2.1 — **disable, don't delete** (bundled skills/plugins are opt-in or archive-only anyway).

---

## QUESTION 3 — Self-learning / self-improving machinery (STRATEGIC)

Hermes markets as "the self-improving AI agent" (`llms.txt:2`). The actual mechanisms:

### 3.1 Persistent memory (`MEMORY.md` + `USER.md`)
- Two bounded files in `~/.hermes/memories/`: **MEMORY.md** (agent notes, 2,200 char ≈ 800 tok) and **USER.md** (user profile, 1,375 char ≈ 500 tok), injected as a frozen system-prompt snapshot at session start (`:9247-9254`, `:9266-9287`).
- Agent self-manages via the `memory` tool: `add` / `replace` / `remove` (substring match); **no `read`** (it's already in the prompt) (`:9289-9310`). When full, the tool errors and forces consolidation in-turn (`:9364-9383`). Duplicate-rejection + injection/exfil security scan (`:9407-9413`).
- Gate: `memory.write_approval: true` stages every save (incl. background ones) for `/memory pending` review (`:9455-9480`).
- **PRISM lever:** after every audit, the agent writes durable facts (which queries failed on which sites, which objections land, AE corrections) to MEMORY.md so they ride in every future session prompt. Capacity is tiny — use it for *heuristics*, push bulk facts to a memory provider (3.5) or the persisted deal object.

### 3.2 Agent-created skills (`skill_manage`) + the Curator
- **Procedural memory:** when the agent solves a non-trivial workflow it writes a SKILL.md via `skill_manage` — actions `create` / `patch` (preferred) / `edit` / `delete` / `write_file` / `remove_file` (`:8482-8506`). Triggers: after a complex task (5+ tool calls), after recovering from errors, after a user correction, on discovering a non-trivial workflow (`:8486-8491`).
- Gate: `skills.write_approval: true` stages writes for `/skills pending` + `/skills diff` review (`:8508-8543`).
- **Curator** = background maintenance for *agent-created* skills (`:8961-9235`): deterministic `active → stale(30d) → archived(90d)` transitions + a periodic aux-model LLM review (every 7d, after 2h idle, `max_iterations=8`) that keeps/patches/**consolidates** overlapping skills/archives (`:8973-8993`, `:8999-9007`). Never auto-deletes (worst case = recoverable `.archive/`) (`:8969`); pre-run tar.gz snapshots + `hermes curator rollback` (`:9062-9085`); pin protection (`:9133-9153`); usage telemetry sidecar `.usage.json` (`:9155-9182`); per-run `REPORT.md` (`:9184-9204`).
- **Important scoping caveat:** the Curator's LLM review only manages skills marked `agent_created`, and **currently ONLY the background self-improvement review fork sets that marker** — foreground/user-directed skills and hand-written/external skills are left alone (`:9091-9121`). So the algolia-* skills (external/hand-authored) are SAFE from curator mutation by default.

### 3.3 The background self-improvement review fork (the actual "learning loop")
The engine behind 3.1/3.2 (`:51547-51568`, also `:8980`, `:9101-9105`):
- **Every 10 user prompts** → a forked `AIAgent` reviews the conversation and decides what to save to **memory**.
- **Every 10 tool iterations within a turn** → same idea for **skills** (`skill_manage`).
- Runs as a background fork in its own prompt cache, never touches the live conversation (`:8980`). It's the only path that marks skills `agent_created` (→ curator-managed) (`:9101-9105`).

### 3.4 Cron / scheduled autonomy
- `cronjob` tool + `/cron` + `hermes cron`: NL schedules, relative/interval/cron-expr/ISO; **skill-backed jobs** (attach one+ skills), run-in-project-dir, delivery routing to home channel, **`context_from` to chain a job's output into the next** (`:11388-12048`). Gateway scheduler ticks every 60 s (`:17989`). Jobs are also CRUD-able over REST (`/api/jobs`) (`:27184-27218`).
- Note one entry: cron job deliveries are NOT mirrored into gateway session history (own cron session) (`:35304`).

### 3.5 Deeper learning: external memory providers + persistent goals
- 8 pluggable providers run *alongside* built-in memory adding knowledge graphs, semantic search, auto fact-extraction, cross-session user modelling (`:9510-9524`). **Hindsight** notably ships `hindsight_reflect` for cross-memory synthesis (`:9862-9873`). Honcho is the AI-native one with gateway identity mapping (`:9726`).
- **Persistent Goals (`/goal`)** — a standing goal with an LLM judge that keeps the agent working across turns until done (Ralph-loop) (`llms.txt:51`, `:13619-13798`).

### 3.6 How PRISM exploits the self-learning loop (tie to mechanisms that exist)
1. **Every audit outcome → memory/skill writes.** The 10-prompt / 10-iteration review fork (3.3) already fires during an audit run; let it persist "what worked" heuristics to MEMORY.md (3.1) and crystallise repeatable sub-workflows as agent-created skills (3.2) that the Curator then de-dupes (3.3/3.2).
2. **AE feedback refines skills.** A user correction is an explicit `skill_manage` trigger (`:8490`); turn on `skills.write_approval` so each refinement is reviewed before it lands (`:8508`). The Curator consolidates the accumulating variants instead of letting them sprawl (`:8991`).
3. **Cross-session deal intelligence → a memory provider.** Built-in memory is too small (2,200 chars) for per-account facts; route those to Hindsight/Honcho (3.5) scoped by the stable `X-Hermes-Session-Key` (Q1.4) so the same scope is recalled whether the rep is on Telegram or the SPA.
4. **Scheduled re-audits + chaining.** Cron skill-backed jobs with `context_from` (3.4) run periodic re-audits and feed deltas forward — autonomy without a human kicking each run.
5. **Goal-mode for end-to-end runs.** `/goal "produce a PROCEED-grade audit for X"` + judge (3.5) keeps the agent iterating through research→browser→report→factcheck until the gate passes.

---

## Confidence & gaps
- HIGH on session keying, `/handoff`, API server shape+headers, toolset/plugin switches, and the self-learning mechanisms — all from the verbatim docs with line cites.
- The **biggest documented gap** is cross-channel *live* continuity (Q1.5): Hermes gives shared **state + memory + recall** across channels but no automatic identity-merge and no live multi-attach — PRISM must add the identity→session-key mapping layer.
- NOT verified on the VPS (no SSH this run): the live `config.yaml` (which toolsets/plugins/channels are actually enabled on Chowmes-PRISM), whether `API_SERVER_ENABLED` is on, and whether any memory provider is configured. All checkable on the box; none change the above.
