# B — VPS Live-State Audit (Hermes-PRISM)

**Date:** 2026-06-28
**Auditor:** vps-audit agent (read-only SSH, ground truth)
**Box:** chowmes / 72.61.72.147 / Ubuntu 24.04, 2 vCPU, 7.8 GiB RAM, 96 GB disk (33% used)
**Access:** SSH key auth as `chowmesadmin` (sudo). Connection succeeded. All findings below are
from live `sudo docker` / `ss` / `cat` output, not inference. Secrets redacted.

---

## ENABLED & USED (the live PRISM surface)

### Containers (all 5 running, `docker ps -a`)
| Container | Status | Image | Role | Ports |
|---|---|---|---|---|
| **hermes-prism** | Up 42 min (s6) | nousresearch/hermes-agent:latest | **PRISM instance** | none published |
| hermes | Up 5 days | nousresearch/hermes-agent:latest | personal Hermes | none published |
| scout | Up 12h (healthy) | docker-scout | PRISM web-intel | 127.0.0.1:8421 |
| ac2-lab-backend | Up 5d (healthy) | ac2-lab-backend:latest | AC2 lab (judge) | 127.0.0.1:8787 |
| caddy | Up 5 days | caddy:latest | reverse proxy | 80, 443 (public) |

No dead/stopped containers exist. Temporal containers are **already gone** (only stale images linger — see DEAD WEIGHT).

### hermes-prism config (`/root/.hermes-prism/config.yaml`, redacted)
- **Model:** `provider: gemini`, `default: gemini-2.5-flash`, `api_mode: chat_completions`, ctx 131072, max_tokens 4096. (Note: gemini direct, via `GEMINI_API_KEY`; NOT OpenRouter for the primary — OpenRouter is only used by the `auxiliary.*` helper models + `model_aliases`.)
- **CLI toolset:** `toolsets: [hermes-cli]` (the default).
- **Telegram toolset (what the bot actually exposes):** `platform_toolsets.telegram = [clarify, cronjob, file, kanban, memory, skills, terminal, todo, vision, web]`. So over Telegram the agent HAS terminal + file + skills + web + vision enabled.
- **`mcp_servers`: ABSENT** — no MCP block in config at all. No algolia/apify/builtwith/yahoo MCP servers attached.
- **`skills.external_dirs: []`** — EMPTY. The algolia skill suite is NOT wired into this instance.
- `agent.max_turns: 6`, `reasoning_effort: medium`, compression enabled.
- `plugins.enabled: [prism-report-qa]`, `plugins.disabled: []`.
- `platforms.telegram.enabled: true`.

### Plugins (opt-in) — `hermes plugins list` in container
- **`prism-report-qa` → ENABLED** (version 0.1, source: user). CONFIRMED live.
  - plugin.yaml desc: "Binds a chat to ONE audit report and injects it as the sole source of facts (grounded report-QA)."
  - `__init__.py` implements **two hooks**: L1 `pre_llm_call` injects the bound company's `audit-data.json` each turn; L4 `transform_llm_output` runs a **Gemini grounding judge** (`gemini-2.5-flash`) that verifies factual claims and rewrites unsupported ones before send (the hard gate). Coaching (F1-F6/M1-M10) is allowed, facts must be report-cited.
  - Reads from `PRISM_REPORTS_DIR=/opt/data/reports`, env `/opt/data/.env`.
- All other plugins (`browser-browser-use`, `browser-browserbase`, etc.) → **not enabled** (bundled, dormant).

### Processes inside hermes-prism (`docker exec ps aux`)
s6-supervised. Two real Python processes:
1. `hermes dashboard --host 127.0.0.1 --port 9120 --no-open` (PID 118)
2. `hermes gateway run` (PID 137) — Telegram polling + cron scheduler.

`gateway_state.json`: `desired_state: running`, **telegram: connected**, pid 137, active_agents 0.

### Skills the container sees (`/opt/data/skills/`)
Hermes's **own bundled skill catalogue only**: apple, autonomous-ai-agents, creative, data-science,
devops, dogfood, email, github, media, mlops, note-taking, productivity, research, smart-home,
social-media, software-development, yuanbao. **The algolia-* suite is NOT present** and
`external_dirs` is empty → **execution plane (algolia skills) is NOT wired in.** This matches
_status.md "P2 not yet done."

### Data layer (`/root/.hermes-prism/reports/` = `/opt/data/reports` in container)
`index.json` (schema "chowmes-prism report store v1") + 2 imported corpora:
- **petsmart** (score 5.8, EXPANSION) — `petsmart/audit-data.json`
- **homedepot-mexico** (score 2.6, displacement) — `homedepot-mexico/audit-data.json`
Both sourced from algolia-arian-v2 (Vercel hub), imported 2026-06-28. This is the grounding corpus.

### Secrets present (`/root/.hermes-prism/.env`, names only)
`OPENROUTER_API_KEY`, `TELEGRAM_ALLOWED_USERS`, `TELEGRAM_HOME_CHANNEL`, `TELEGRAM_BOT_TOKEN`,
`GEMINI_API_KEY`. (Anthropic key NOT present here — consistent with "blocked on Anthropic credits
for generation" in memory; gemini is the live driver.)

---

## DEAD WEIGHT / STRIPPABLE

1. **Temporal image triad — ~1.3 GB, containers already deleted.** Images still on disk with no
   running containers:
   - `temporalio/auto-setup:1.27` (804 MB)
   - `temporalio/ui:latest` (102 MB)
   - `postgres:16-alpine` (420 MB) — was the temporal-db.
   Safe to `docker rmi` (Temporal stack is dead per _status.md; nothing references these).
2. **Docker build cache — 17.43 GB total, 16.98 GB reclaimable (0 active).** Single largest
   reclaim. `docker builder prune` frees ~17 GB.
3. **Stale Caddy route to a dead service.** Caddyfile still serves
   `temporal.contentengagement.info` (basic-auth) → `reverse_proxy localhost:8088`, but **:8088 is
   DEAD** (`curl` → connection refused; temporal-ui container gone). This route should be removed —
   it's a public hostname pointing at nothing.
4. **`docker system df`:** Images 22.63 GB total, **21.31 GB (94%) reclaimable.** Most of that is
   the two hermes-agent layers (kept, both in use) + the temporal triad (strippable) + dangling.

Total quick reclaim ≈ **18 GB** (build cache 17 GB + temporal images 1.3 GB) without touching
anything live. Disk is only 33% used, so this is hygiene, not urgent pressure.

---

## API / CADDY for SPA integration

### Public exposure (Caddyfile — only TWO routes)
```
judge.contentengagement.info     -> reverse_proxy localhost:8787   (ac2-lab-backend, LIVE)
temporal.contentengagement.info  -> reverse_proxy localhost:8088   (DEAD — :8088 refused)
```
Public ports: only **80/443 (caddy)** and **22 (ssh)**. UFW posture intact.

### Localhost-only listeners (`ss -tlnp`)
- 127.0.0.1:9119 — personal hermes dashboard
- 127.0.0.1:9120 — **hermes-prism dashboard**
- 127.0.0.1:8421 — scout
- 127.0.0.1:8787 — ac2-lab
- 127.0.0.1:2019 — caddy admin

### Is an HTTP API reachable for the SPA today? **NO.**
- **hermes-prism publishes no ports** and runs **only** the gateway (Telegram) + the dashboard
  (127.0.0.1:9120, not proxied by Caddy). There is **no OpenAI-compatible / HTTP API server
  running** for it, and **no Caddy route to it.** The SPA cannot reach the PRISM agent today.
- **But the capability exists in the binary.** `hermes --help` shows:
  - `hermes proxy` — "Local OpenAI-compatible proxy to OAuth providers" (an OpenAI-compatible HTTP
    endpoint).
  - `hermes mcp` — "Manage MCP servers and run Hermes as an MCP server" (run Hermes itself as an
    MCP/HTTP server).
  There is **no `hermes api` subcommand** (confirmed — invalid choice).
- **Path to SPA integration (not yet built):** run `hermes proxy` (or the MCP server mode) inside
  hermes-prism on a localhost port, publish/expose it, add a Caddy route
  (e.g. `prism.contentengagement.info` → that port) **with auth** (public SPA, private intel).
  This is exactly the W-D "Hermes API behind Caddy + auth" task — currently **pending/unbuilt.**

---

## Bottom line
- **Running & healthy:** hermes-prism (gemini-2.5-flash, Telegram connected), report store (petsmart
  + homedepot-mexico), **prism-report-qa plugin ENABLED** with the inject + grounding-gate hooks.
- **Not wired (by design, P2 pending):** algolia execution plane — `external_dirs` empty, no MCP
  servers, only Hermes's bundled skills present. PRISM today = grounded report-QA chat, not a
  generator.
- **SPA integration:** no HTTP API exposed today; `hermes proxy`/`hermes mcp` is the supported
  mechanism but must be started + Caddy-routed + auth'd (W-D, unbuilt).
- **Dead weight:** ~18 GB reclaimable (17 GB build cache + 1.3 GB stale Temporal images) and a dead
  Caddy `temporal.*` route to remove. No live container is wasted.

---

## APPLIED CHANGES — 2026-06-28 (vps-ops agent, live, authorized by user via team-lead)

Connected as `chowmesadmin` (key auth, `sudo docker`). Each step verified with real output.

### Thread 2 — cleanup (APPLIED)

**Step 1 — `docker builder prune -f` — DONE.**
- Before: `Build Cache 86 entries / 17.43GB / 16.98GB reclaimable`; `Images 22.63GB`.
- After: `Build Cache 12 / 448.1MB / 0B reclaimable`; `Images 10.16GB`.
- **Reclaimed ≈ 16.98 GB** of build cache. No active build cache touched (0 active before).

**Step 2 — `docker rmi` stale Temporal triad — DONE.**
- Pre-check: `docker ps -a | grep -Ei 'temporal|postgres'` → NONE (no container, running or stopped, references these images).
- Removed: `temporalio/auto-setup:1.27`, `temporalio/ui:latest`, `postgres:16-alpine` (all `Untagged` + `Deleted`).
- After: 4 images remain, all in use by running containers (docker-scout, ac2-lab-backend, nousresearch/hermes-agent [shared by hermes + hermes-prism], caddy). `docker system df` Images now 8.83 GB.
- **Reclaimed ≈ 1.3 GB.** Combined Thread-2 cleanup reclaim ≈ **18.3 GB**.

**Step 3 — Caddy: remove dead `temporal.contentengagement.info` route — BACKUP DONE, EDIT BLOCKED.**
- Caddyfile location found: bind-mount `/home/chowmesadmin/lab-judge/Caddyfile` → `/etc/caddy/Caddyfile`.
- **Backup made:** `Caddyfile.bak-2026-06-28` (`cp -a`, verified present, 234 bytes).
- Pre-state verified: `:8088` → HTTP 000 / connection refused (DEAD); judge backend `localhost:8787/health` → HTTP 200 (LIVE); `https://judge.contentengagement.info` → HTTP 404 (app responding at `/`, route works).
- **BLOCKED:** overwriting the live Caddyfile via SSH was denied by the Claude Code auto-mode write classifier (production config write needs user review outside auto mode). The trimmed file (judge-only) was NOT written. Backup is in place; original Caddyfile unchanged and still serving.

### Thread 2 — disable unused Hermes surface (PREPARED, EDIT BLOCKED)

Read-only inspection of `/root/.hermes-prism/config.yaml` (sudo):
- `agent.disabled_toolsets: []` (line 29) — needs the disable list. **NOTE:** several names in the request are *platform* names, not toolsets (discord, homeassistant, yuanbao have `platform_toolsets.*` / `known_plugin_toolsets` entries, not agent toolsets). Must validate each against `hermes`'s real toolset registry before writing, to avoid an invalid-config restart failure. Real candidate agent toolsets to disable: spotify, image_gen, video, video_gen, moa, computer_use, feishu_doc, feishu_drive, x_search — pending name validation.
- `platforms:` block (line 639) lists **only** `telegram: enabled: true`. No other platform is enabled → nothing to set `false`. Telegram tool exposure is governed by `platform_toolsets.telegram` (clarify, cronjob, file, kanban, memory, skills, terminal, todo, vision, web) — all on the keep-list; no change needed there.
- **BLOCKED:** config.yaml write gated same as Caddyfile. No edit applied.

### Thread 4 — self-learning (ALREADY SATISFIED, NO EDIT NEEDED)

Read-only confirmation in config.yaml:
- `memory.memory_enabled: true` (line 391) ✓
- `memory.write_approval: true` (line 393) ✓ — self-writes are STAGED for review, exactly as requested.
- `memory.user_profile_enabled: true`, `memory.provider: ''` (no external provider) ✓
- `curator.enabled: true`, `interval_hours: 168` (line ~426) — background self-improvement/curation review is ON (default). ✓
- **No config change required for Thread 4.** Target state already in place.

### Step 6 — restart / recovery

- **Not performed.** No config write succeeded, so no restart was warranted. hermes-prism, Telegram, and the prism-report-qa plugin remain in their pre-existing healthy state (untouched). No backup needed restoring.

### Memory-provider recommendation (Thread 4 report-only)

- **Recommend Hindsight over Honcho** for this box. Rationale: PRISM's value is *grounded, auditable* QA; Hindsight's reflective-memory model (periodic distillation of session history into reviewable lessons) maps cleanly onto the existing `write_approval: true` + `curator` staging discipline and stays self-hosted/local (no extra outbound data plane for private intel). Honcho is a hosted user-modeling/personalization service — stronger for consumer personalization, weaker fit for a single-operator internal sales tool and adds a third-party data dependency.
- **Enabling requires:** set `memory.provider` to the provider id, supply its connection env (host/key) in `/root/.hermes-prism/.env`, run its store/migration, restart hermes-prism, and verify `hermes` picks up the provider. Keep `write_approval: true` so provider-suggested memories stay staged. Deferred — not installed, per instruction.

### Net result
- **GB reclaimed: ≈18.3 GB** (16.98 build cache + 1.3 stale images), verified by `docker system df` before/after.
- **Toolsets/channels disabled:** 0 applied (write blocked); platforms already minimal (telegram-only).
- **Memory settings:** already at target (`memory_enabled`+`write_approval`+`curator` on) — no edit needed.
- **Recovery verified:** N/A — no restart performed; live surface untouched and still healthy.
- **BLOCKER:** all live-config writes (Caddyfile trim, config.yaml toolset disable) denied by auto-mode write classifier. Caddyfile backup is in place. Need the write step run outside auto mode (or a Bash permission rule) to finish Thread-2 config + Caddy steps.
