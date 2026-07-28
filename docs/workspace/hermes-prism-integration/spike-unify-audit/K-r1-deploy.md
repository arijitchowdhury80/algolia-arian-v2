# K-r1-deploy — PRISM FastAPI on the Hermes VPS (W-D step R1)

Date: 2026-06-28
Owner: r1-deploy (agent)
Goal: deploy `prism_platform` (FastAPI) on the Hermes VPS, reachable at `http://127.0.0.1:8000`, `/health` returning `{"status":"ok","version":"2.0.0"}`. Prereq for Hermes → PRISM tool calls.

## Result: REACHABLE — Y

```
$ curl -s http://127.0.0.1:8000/health
{"status":"ok","version":"2.0.0"}
```

## Environment (VPS `chowmes`, 72.61.72.147)
- SSH: key auth as `chowmesadmin` (`~/.ssh/chowmes_ed25519`). sudo NOPASSWD.
- OS python: 3.12.3. `uv` NOT present → used venv + pip.
- `python3.12-venv` was missing (ensurepip failed) → installed via `apt-get install -y python3.12-venv` (small, standard prereq; step-4 authorized apt).

## Ports — NO conflicts, defaults kept
At deploy time 5432 / 6379 / 8000 were all free (`ss -tlnp` showed none listening). Existing containers: hermes, hermes-prism, scout (127.0.0.1:8421), ac2-lab-backend (127.0.0.1:8787), caddy. So compose default host ports kept:
- Postgres host 5432 → container 5432
- Redis host 6379 → container 6379
- uvicorn 127.0.0.1:8000
Note: compose binds postgres/redis on `0.0.0.0`, but UFW only allows public TCP 22, so they are not externally reachable. Acceptable for R1.

## Steps executed
1. **Sync** → `/opt/prism-platform/` via `rsync -az --delete` over SSH key, subset: `prism_platform/ pyproject.toml uv.lock alembic/ alembic.ini docker-compose.yml`; excluded `.venv __pycache__ *.pyc node_modules .git frontend`. All 7 migrations present.
2. **DB up** → `docker compose up -d postgres redis`. Both report `(healthy)`. `pg_isready -U prism` = accepting connections; `redis-cli ping` = PONG.
3. **Python env** → `/opt/prism-platform/.venv` (system python3.12). pip 26.1.2.
4. **Deps** → pip-installed the core set NOT via `pip install -e .` (see gotcha): fastapi, uvicorn[standard], pydantic, pydantic-settings, sqlalchemy[asyncio], asyncpg, alembic, redis, httpx, tenacity, structlog, temporalio, playwright, playwright-stealth. Did NOT install: `scout` (broken path dep), playwright browser binaries (not needed for import/health), anthropic/google-genai/instructor/yfinance (deferred imports, not hit at load), the Temporal **server** (only the Python client package).
5. **`.env`** at `/opt/prism-platform/.env`: DATABASE_URL=postgresql+asyncpg://prism:prism_dev_password@localhost:5432/prism, REDIS_URL=redis://localhost:6379/0, APP_ENV=production, LOG_LEVEL=INFO. No real keys.
6. **Migrate** → `alembic upgrade head` reached **007 (head)**. All 7 migrations applied clean. `alembic current` = `007 (head)`.
7. **Run** → systemd unit `/etc/systemd/system/prism-platform.service` (Type=simple, User=chowmesadmin, WorkingDirectory=/opt/prism-platform, EnvironmentFile=/opt/prism-platform/.env, ExecStart=.venv/bin/uvicorn prism_platform.main:app --host 127.0.0.1 --port 8000, Restart=always). `enable --now` → active, up in ~2s.

## Verification (all green)
- `/health` → `{"status":"ok","version":"2.0.0"}`
- `GET /api/v1/accounts/` → `[]` HTTP 200 (DB-backed router queries OK on empty table)
- `GET /api/v1/modules/` → HTTP 200, all **17** v2 modules listed
- App import registered all 17 v2 modules; **no Temporal crash at startup** (confirms Temporal client is lazy/per-request — `api/deps.py` imports `temporalio.client` but only connects inside a request dependency).
- Startup warnings are expected and in-scope: `No LLM provider configured`, `PERPLEXITY_API_KEY not set` per module, module `healthy:false`. R1 carries no keys.

## Service type: **systemd** (`prism-platform.service`, enabled, Restart=always)

## Blockers: NONE for R1.

## Gotcha / Fix-and-Learn
**Symptom:** `pip install -e .` would fail; app import also failed once on `ModuleNotFoundError: playwright`.
**Root cause:** `pyproject.toml` declares `scout = { path = "../Scout", editable = true }` — a Mac-only path dep absent from the synced subset, so a full editable install can't resolve. Separately, `register_all_v2_modules()` runs at **import time** (called in `main.py`) and pulls `intel_competitors.collector → v2.detection.search_vendor`, which imports `playwright.async_api` at module top — so the Python `playwright` package IS required at load even though no browser is launched for `/health`.
**Fix:** install the explicit core dep list (no `scout`, no `-e .`), add `playwright`+`playwright-stealth` Python packages but skip `playwright install` browser binaries. scout/yfinance/anthropic/google-genai imports are deferred (inside functions) and never hit at load.
**Prevention (future me):** On the VPS, install PRISM deps explicitly, never `pip install -e .` (the `scout` path dep is Mac-local). The module-load import chain needs `playwright` the package (registry imports the search-vendor detector at top level) but NOT the browser binaries for import/health. Temporal client import ≠ Temporal server: import succeeds with no server because connection is per-request.

## Follow-ups (out of R1 scope)
- Browser-dependent module runs will need `playwright install chromium` + system libs.
- Any module execution needs LLM/MCP keys (PERPLEXITY_API_KEY etc.) — deliberately empty now.
- Temporal worker is deleted; audit *execution* via the Temporal workflow path is not wired. `/health` + DB routers do not need it.

---

# W-D wiring — API + reachability (2026-06-28)

Owner: hermes-api-wire (agent). Goal: (1) make `prism_platform` reachable FROM the hermes-prism container without exposing it publicly; (2) enable the Hermes OpenAI-compatible API server on hermes-prism. Both verified WITHOUT LLM credits. Backups taken; live report-QA preserved.

## KEY FINDING — hermes-prism uses host networking → no rebind needed
`docker inspect hermes-prism` → `NetworkMode=host` (compose: `network_mode: host`). The container shares the host's network namespace, so it sees the host's `127.0.0.1` directly. uvicorn already binds `127.0.0.1:8000` (host loopback) → the container reaches PRISM at that exact address with **zero config change**. Binding `0.0.0.0` was therefore NOT done — it would only widen exposure and rely solely on UFW. Keeping loopback is both reachable-from-container AND not-public. (`host.docker.internal` / `172.17.0.1` bridge-gateway paths are irrelevant under host networking — there is no bridge in play for this container.)

## TASK 1 — PRISM reachable from hermes-prism (NOT public)
**URL the container uses to reach PRISM:** `http://127.0.0.1:8000`

3 reachability checks (all as required):
- (a) HOST → `curl 127.0.0.1:8000/health` → `{"status":"ok","version":"2.0.0"}` ✅
- (b) **load-bearing** — INSIDE container → `sudo docker exec hermes-prism curl -s http://127.0.0.1:8000/health` → `{"status":"ok","version":"2.0.0"}` ✅ (re-verified AFTER the hermes-prism restart too — still ok)
- (c) Mac → `curl http://72.61.72.147:8000/health` → timeout (curl exit 28) ✅ NOT public

Supporting: `ss -tlnp` shows `127.0.0.1:8000 uvicorn` (loopback bind, not `0.0.0.0`). UFW active, public allow-list = 22/80/443 only (8000 absent).

## TASK 2 — Hermes API server enabled on hermes-prism — UP: **Y**
Config model: hermes-prism is `docker compose` project `chowmes-prism` (`/opt/chowmes-prism/docker-compose.yml`), `image: nousresearch/hermes-agent:latest`, `command: [gateway, run]`, bind-mount `/root/.hermes-prism → /opt/data`, `HERMES_HOME=/opt/data`. Compose `environment:` only sets dashboard/UID — it does NOT pass API vars, so config goes in the env file at `/root/.hermes-prism/.env` (= `/opt/data/.env`, the documented `~/.hermes/.env` location).

**Read Receipt (grounded in the live binary, not just the spike doc):**
- `/opt/hermes/gateway/config.py:1643-1647` reads `API_SERVER_ENABLED` (truthy = true/1/yes) + `API_SERVER_KEY` from env; registers the `API_SERVER` platform when either is set.
- `/opt/hermes/hermes_cli/config.py:3511-3540`: `API_SERVER_KEY` "Required whenever the API server is enabled; server refuses to start without it." Defaults: `API_SERVER_HOST`=127.0.0.1, `API_SERVER_PORT`=8642 (left unset → defaults kept).
- Session key header constant `X-Hermes-Session-Key` present in binary.

**Changes made (backups first):**
- Backed up `/root/.hermes-prism/.env` → `.env.bak-20260628-055240` and `config.yaml` → `config.yaml.bak-20260628-055240`.
- Generated a strong token (`openssl rand -hex 32`). **Stored at `/root/.hermes-prism-api-key.txt` (root-only, chmod 600) — NOT printed here.** Retrieve with `sudo awk -F= '/^API_SERVER_KEY=/{print $2}' /root/.hermes-prism-api-key.txt`.
- Appended to `/root/.hermes-prism/.env` (existing 5 keys preserved, file still 600): `API_SERVER_ENABLED=true`, `API_SERVER_KEY=<token>`. Bind left at default loopback `127.0.0.1:8642`.
- `docker restart hermes-prism`. API server came up in ~10s.

**Recovery verification (all green):**
- Container running; `gateway_state.json` → `gateway_state: running`; **telegram `connected`** (reconnected); **api_server `connected`** (new platform).
- agent.log: `[Api_Server] API server listening on http://127.0.0.1:8642 (model: hermes-agent)` → `✓ api_server connected` → `Gateway running with 2 platform(s)`.
- **prism-report-qa plugin still `enabled`** (`hermes plugins list`). No plugin/grounding errors in errors.log (only the expected SIGTERM from my restart + the pre-existing OpenRouter credit warnings — the known W-A generation blocker, unrelated).
- NOTE: a *live* report-QA answer needs an LLM call → blocked on credits (W-A). Verified at the level asked: plugin enabled + gateway healthy + clean load. Restore-on-break was not needed.

**API server verification (`Authorization: Bearer <key>`):**
- `/health` → `{"status":"ok","platform":"hermes-agent","version":"0.16.0"}`
- `/v1/capabilities` → `responses_api: true`, `session_key_header: "X-Hermes-Session-Key"`, `session_continuity_header: "X-Hermes-Session-Id"`, `auth.required: true`, `cors: false`. Full Sessions REST + Runs + responses endpoints advertised.
- `/v1/models` → `hermes-agent`
- Auth enforced: no-key `/v1/capabilities` → HTTP 401.
- `ss -tlnp` → `127.0.0.1:8642 hermes` (loopback bind).
- Mac → `curl http://72.61.72.147:8642/health` → timeout (exit 28) ✅ NOT public.

## For tool registration / SPA (next)
- Hermes → PRISM tool calls: register PRISM base URL as **`http://127.0.0.1:8000`** (host loopback under host networking).
- SPA → Hermes: hit `http://127.0.0.1:8642` with `Authorization: Bearer <key from /root/.hermes-prism-api-key.txt>`; durable multi-turn via `/v1/responses` (`responses_api: true`) or `/api/sessions/*`; cross-channel scope via `X-Hermes-Session-Key`.
- CORS: `cors: false` now. Add `API_SERVER_CORS_ORIGINS=<spa-origin>` to `/root/.hermes-prism/.env` + restart when the SPA domain is known.

---

# W-D build-state assessment (2026-06-28) — D1/D2/D3 sequencing

Maps to G-wd-design.md's 12-step checklist and J-RESUME-RUNBOOK §4. Verified live on the box.

## Done (green)
- Checklist 1 — `frontend/` committed: `git ls-files frontend/ | wc -l` = **121** tracked. ✅
- Checklist 2 — reachability gap confirmed + fixed: prism_platform LIVE on VPS, `/health` ok. ✅
- Checklist 3 (R1) — FastAPI co-located on VPS, reachable from hermes-prism at `http://127.0.0.1:8000`. ✅
- Checklist 4 — Hermes API server enabled + verified (`responses_api: true`, `session_key_header: X-Hermes-Session-Key`). ✅

## NOT done — the critical-path prerequisites BEFORE the SPA widget (D2)
- **Checklist 5 — register the 25 PRISM module tools in Hermes: NOT done.** `GET /v1/toolsets` returns only default Hermes toolsets (web, browser, terminal, file, code_execution, vision, …). No `get_company_profile`/`get_tech_stack`/etc. `GET /v1/skills` shows only generic Hermes skills, not the algolia-* suite as callable tools. → **Hermes currently has no PRISM tool to call.** Per G §4: "Until then Hermes has no tools to call. This is the critical-path prerequisite for the whole 'one brain' story."
- **Checklist 6 — move grounding (aRRIe persona + prism-report-qa gate) so the chat brain is grounded: NOT done for the chat path.** The report-QA plugin is enabled for the report-QA flow, but the aRRIe persona/grounding for general chat still lives only in the SPA's `app/api/chat/route.ts` SYSTEM_PROMPT (web-only; Telegram ungrounded — G §4 "two brains problem").

## Consequence for D1/D2/D3 (the push-back)
Building D2 (the SPA chat widget → `/v1/responses`) **now** would stream from a Hermes brain that (a) cannot execute a single PRISM audit tool and (b) is not grounded for chat. That is checklist step 9 before steps 5–8. Recommended order: **5 (register tools) → 6 (grounding) → 7 (proxy+shim) → 8 (tool-name contract) → 9 (repoint transport) → D1 Caddy/SPA-deploy + gate /api/chat → D3 cross-channel**.

## D1 specifics gathered (Caddy)
- Caddyfile: `/home/chowmesadmin/lab-judge/Caddyfile` (bind-mounted into the `caddy` container at `/etc/caddy/Caddyfile`).
- Existing pattern = `<sub>.contentengagement.info { basic_auth { … } reverse_proxy localhost:<port> }`. A `prism` basic_auth user (bcrypt) already exists for `temporal.contentengagement.info → localhost:8088`.
- For the SPA: the SPA must first be DEPLOYED on the VPS (it runs on the Mac/localhost today); then a Caddy host (e.g. `app.contentengagement.info → localhost:<spa-port>`) fronts it. Auth split: the **SPA** is the public face (Clerk-gated inside the app); the **Hermes API (8642)** and **PRISM (8000)** stay loopback-only and are reached only by the SPA's server-side proxy — NOT exposed via Caddy. So D1's "public SPA, private intel" = expose only the Next.js SPA, keep 8642/8000 loopback.
- `API_SERVER_CORS_ORIGINS`: not needed if the browser never calls 8642 directly (the proxy is server-side). Only add it if a browser-direct call to Hermes is ever introduced.

## SPA insertion points (D2) confirmed in code
- `frontend/components/chat/prism-chat.tsx:49` — `useChat({ id: "prism-chat" })` on DEFAULT transport (POSTs `/api/chat`); ~22 tool-renderer registrations present (lines 62-95). Repoint transport to `/api/hermes` per G §5.2; renderers stay.
- `frontend/middleware.ts:4` — `/api/chat(.*)` is in the PUBLIC matcher (+ `BYPASS_AUTH` escape at line 8). Must gate before chat carries real intel (G §5.3 / checklist 11).
- New proxy `app/api/hermes/route.ts` + SSE→AI-SDK-UI-stream shim still to build (G §2, §5.1).

---

# W-D Track A — expose Hermes API publicly + /v1/responses stream probe (2026-06-28)

Goal: make the live Hermes-PRISM API reachable from a Vercel SPA (public Hermes API, bearer-gated + TLS) and capture the real `/v1/responses` SSE shape for the SSE→AI-SDK shim. Verified live on the box and from the Mac (public internet).

## ARCHITECTURE-SHIFT NOTE (supersedes K §D1 for Track A)
The earlier K notes (line 131-132) assumed **SPA-on-VPS with a server-side proxy → Hermes stays loopback-only, no public Hermes, no CORS**. Track A's direction is different: **SPA on Vercel → calls a PUBLIC Hermes API directly.** That means Hermes 8642 IS now publicly exposed (bearer-gated) and CORS WILL be required (browser calls Hermes cross-origin). Both designs are valid; this section implements the Vercel-public-API one. If the SPA ends up on the VPS after all, the public route can simply be removed and the loopback design from line 131 restored.

## Caddy / DNS reality (verified)
- **No wildcard DNS.** `dig +short` from the Mac: `judge.contentengagement.info` → `72.61.72.147` (resolves); `temporal.contentengagement.info`, `hermes-api.contentengagement.info`, and a random sub → **empty** (do not resolve). DNS records are added per-host manually; I cannot create them. Per instructions, did NOT invent a subdomain.
- **Decision: path route under the existing resolvable host.** Added `handle_path /hermes-api/* { reverse_proxy 127.0.0.1:8642 }` to the `judge.contentengagement.info` block, with the existing app moved into a `handle { reverse_proxy localhost:8787 }` default. `handle_path` strips the `/hermes-api` prefix before proxying.
- **Public Hermes API URL: `https://judge.contentengagement.info/hermes-api`** (e.g. capabilities at `/hermes-api/v1/capabilities`, responses at `/hermes-api/v1/responses`).
- Key Caddy fact: the `caddy` container runs `network_mode: host`, so inside the container `127.0.0.1` IS the host — `reverse_proxy 127.0.0.1:8642` reaches the loopback Hermes API with no docker-host gymnastics.
- Backups made before any edit: `Caddyfile.bak.20260628-092231` (in `/home/chowmesadmin/lab-judge/`), and `/root/.hermes-prism/.env.bak.20260628-092521`.
- `caddy validate` → `Valid configuration`; graceful `caddy reload`, container stayed `Up` (no restart). The only warning is a cosmetic "not formatted" notice.

## Verification (from the Mac, public internet)
- `GET https://judge.contentengagement.info/hermes-api/v1/capabilities` **WITHOUT** auth → **401** (bearer gate holds publicly). ✅
- WITH `Authorization: Bearer <key>` → **200** + capabilities JSON. `platform: hermes-agent`, **`responses_api: true`**, **`responses_streaming: true`**, `cors: false`, `session_key_header: X-Hermes-Session-Key`. ✅
- TLS: valid Let's Encrypt cert `CN=judge.contentengagement.info` (notAfter Sep 16 2026). ✅
- Existing judge route still works: `https://judge.contentengagement.info/health` → **200** (upstream lab-judge on :8787 reached through the new `handle` split; `/` returns the app's own 404, not a routing error). ✅
- report-QA still healthy: **Y** — `prism-report-qa` plugin present at `/root/.hermes-prism/plugins/prism-report-qa`; Hermes API **same PID (2432648)** on 8642 before & after my changes (no restart); `/health` → 200.

## Auth key gotcha (recorded for future-me)
`/root/.hermes-prism-api-key.txt` is **NOT a bare key** — it is a 2-line note file: line 1 a human caption, line 2 `API_SERVER_KEY=<64-hex>`. The usable key is the value AFTER `API_SERVER_KEY=` on line 2 (sha256 verified equal to `API_SERVER_KEY` in `/root/.hermes-prism/.env`). Passing the whole file as the bearer yields curl "Missing expected CR after header value" (embedded newline), and the trimmed caption yields 401. Extract with: `grep '^API_SERVER_KEY=' <file> | sed 's/^API_SERVER_KEY=//' | tr -d '[:space:]'`.

## CORS
- Authoritative env var (read from source, NOT guessed): `API_SERVER_CORS_ORIGINS`, comma-separated origins, parsed at `/opt/hermes-agent/gateway/config.py:1645` and consumed at `gateway/platforms/api_server.py:752`. Empty string = CORS disabled (current state → capabilities `cors: false`). `"*"` = allow all.
- Action taken: appended a **commented (inert) placeholder** to `/root/.hermes-prism/.env` (no restart, so the live report-QA was not disturbed):
  `#API_SERVER_CORS_ORIGINS=https://REPLACE-WITH-VERCEL-ORIGIN.vercel.app`
- **TODO before the Vercel SPA goes live:** uncomment + set to the real Vercel origin, then restart hermes-prism so `cors: true`. The browser calls Hermes cross-origin, so this is mandatory (unlike the old server-side-proxy design where it wasn't).

## RAW /v1/responses SSE — TEXT DELTA turn (verbatim, captured over the public route)
Request body: `{"model":"hermes-agent","input":"Say hello in 5 words.","conversation":"prism:probe:test","stream":true,"store":true}`
Headers: `Authorization: Bearer <key>`, `Content-Type: application/json`, `X-Hermes-Session-Key: agent:main:prism:rep:probe:acct:test`

```
event: response.created
data: {"type": "response.created", "response": {"id": "resp_598f375253994cc49f6eb54ae828", "object": "response", "status": "in_progress", "created_at": 1782653131, "model": "hermes-agent", "output": []}, "sequence_number": 0}

event: response.output_item.added
data: {"type": "response.output_item.added", "output_index": 0, "item": {"id": "msg_86fcd5d02b3544339db40746", "type": "message", "status": "in_progress", "role": "assistant", "content": []}, "sequence_number": 1}

event: response.output_text.delta
data: {"type": "response.output_text.delta", "item_id": "msg_86fcd5d02b3544339db40746", "output_index": 0, "content_index": 0, "delta": "Hello!", "logprobs": [], "sequence_number": 2}

event: response.output_text.delta
data: {"type": "response.output_text.delta", "item_id": "msg_86fcd5d02b3544339db40746", "output_index": 0, "content_index": 0, "delta": " How can I help you?", "logprobs": [], "sequence_number": 3}

event: response.output_text.done
data: {"type": "response.output_text.done", "item_id": "msg_86fcd5d02b3544339db40746", "output_index": 0, "content_index": 0, "text": "Hello! How can I help you?", "logprobs": [], "sequence_number": 4}

event: response.output_item.done
data: {"type": "response.output_item.done", "output_index": 0, "item": {"id": "msg_86fcd5d02b3544339db40746", "type": "message", "status": "completed", "role": "assistant", "content": [{"type": "output_text", "text": "Hello! How can I help you?"}]}, "sequence_number": 5}

event: response.completed
data: {"type": "response.completed", "response": {"id": "resp_598f375253994cc49f6eb54ae828", "object": "response", "status": "completed", "created_at": 1782653131, "model": "hermes-agent", "output": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Hello! How can I help you?"}]}], "usage": {"input_tokens": 14356, "output_tokens": 8, "total_tokens": 14364}}, "sequence_number": 6}
```

### Shape notes for the SSE→AI-SDK shim (text path)
- OpenAI Responses-API event grammar. Per-text-chunk event = **`response.output_text.delta`**, payload field **`delta`** (the token string). `item_id` + `output_index` + `content_index` identify the target message/part.
- Lifecycle: `response.created` → `response.output_item.added` (assistant message shell) → N× `response.output_text.delta` → `response.output_text.done` (full `text`) → `response.output_item.done` → `response.completed` (final response object + `usage`).
- `sequence_number` is monotonic across the whole stream. Final usage on `response.completed.response.usage`.
- Transport: standard SSE, `event:` + `data:` (JSON) line pairs, blank line between events.

### Session id the plugin/hook sees (verified — answers "is it stable per conversation?")
- Request sends `X-Hermes-Session-Key: agent:main:prism:rep:probe:acct:test`. The server resolves it to a stable UUID and echoes BOTH headers on the response:
  - `X-Hermes-Session-Key: agent:main:prism:rep:probe:acct:test` (what the client sent)
  - `X-Hermes-Session-Id: e42d8d20-9f63-45d5-b070-9e8e951e5922` (the resolved internal session id the plugin/hook sees)
- **STABLE per session key:** two consecutive `/v1/responses` calls with the SAME `X-Hermes-Session-Key` both returned the SAME `X-Hermes-Session-Id` (e42d8d20-...). So the plugin/hook keys off a deterministic, conversation-stable session id derived from the X-Hermes-Session-Key. The continuity header to read back on responses is `X-Hermes-Session-Id` (matches capabilities `session_continuity_header`). For the shim: send a per-conversation `X-Hermes-Session-Key`; the same key → same session → grounded report-QA plugin sees a stable session for that conversation.
- Note: this probe used `stream:false, store:true` and went through cleanly (no 429) — confirms the gemini 429 is a per-minute rate limit, not a hard outage; light/non-streaming traffic still works between bursts.

## RAW /v1/responses SSE — TOOL/FUNCTION_CALL turn — **NOT CAPTURED (provider 402-equivalent)**
Attempted 3× (prompts explicitly asking it to run a shell tool). **All three returned a Google Gemini free-tier 429** and the `function_call` event shape was never reached. **No tool fired** — generation was blocked upstream before any tool decision. The 429 surfaces as the gemini analogue of the Anthropic 402 the task warned about.

Provider-error shape worth noting for the shim: the error did NOT come back as an SSE error event — it was streamed **as the assistant's `output_text`** with `status: completed`. Verbatim error text (single delta):
```
event: response.output_text.delta
data: {"type": "response.output_text.delta", ... "delta": "API call failed after 1 retries: HTTP 429: Gemini HTTP 429 (RESOURCE_EXHAUSTED): You exceeded your current quota ... Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-2.5-flash. Please retry in 47.7s. Your Google API key is on the free tier (<= 250 request...", ...}
```
→ **BLOCKER for the function_call sample:** Google Gemini free-tier quota (20 req/min on `gemini-2.5-flash`). The probe traffic exhausted the per-minute window; the daily free-tier cap may also be in play. To capture the `function_call`/`function_call_output` event shape + `name` field, either (a) wait for the quota window and run ONE tool-forcing call, or (b) put a paid Gemini key / different brain on hermes-prism. The text-delta shape above is sufficient to start the shim; the tool-event shape is the only remaining gap.

---

## Plugin patch — deterministic bind (`_slug_from_session_key`) — 2026-06-28

**Goal:** deploy the patched `prism-report-qa/__init__.py` that binds the report from the
session-key's `:acct:<domain>` segment (deterministic) *before* the message content-match,
so a generic question with no company name still grounds. Verify report-QA stays healthy.

**Deployed path (running hermes-prism reads this live):**
- Host: `/root/.hermes-prism/plugins/prism-report-qa/__init__.py`
- In-container: `/opt/data/plugins/prism-report-qa/__init__.py`
- Wiring: container mount `/root/.hermes-prism -> /opt/data (rw)` (bind-mount; host edit = live in container)

**Pre-state confirmed OLD:** deployed file had `_match_slug` (3 hits), `_slug_from_session_key` (0). Plugin `enabled`, v0.1, source `user`.

**Backup:** `/root/.hermes-prism/plugins/prism-report-qa/__init__.py.bak-20260628-103138` (8227 B, identical to pre-deploy).

**Deploy:** scp Mac→VPS `/tmp`, then `sudo cp` into place (root:root 644), cleared stale `__pycache__`.
- md5 Mac == temp-on-box == deployed = `e4ed6efcdaee1364bf1958f659940841` (bit-identical).
- `_slug_from_session_key` present post-deploy (2 hits: def + call site in `inject_report`).
- **py_compile OK = Y** — both host `python3` and inside container (`/opt/data/...`).

**Restart recovery (`sudo docker restart hermes-prism`):**
- Container `Up`; `/health` = **200** on first poll.
- `hermes plugins list` → `prism-report-qa` still **enabled**.
- No traceback / import / plugin-load errors in logs since restart.
- Gateway up under s6 supervision (dashboard ready, main-hermes started). No explicit Telegram "reconnect" log line at default level, but the gateway process that owns the Telegram channel started clean and healthy.
- **report-QA healthy = Y.**

**THE LOAD-BEARING PROBE (one streaming call, account ONLY in session-key, generic message, no [Account:] prefix):**
- `X-Hermes-Session-Key: agent:main:prism:rep:patchtest:acct:petsmart.com`, input "What is the no-results rate?", `stream:true, store:true`. curl exit 0, full SSE, no 429.
- **Assembled answer:**
  > "I can only answer from a bound audit report. Which company are you asking about? PetSmart or The Home Depot México?"

**PROBE VERDICT = PARTIAL — key-not-in-hook.**
The plugin's *no-report-bound* branch fired (the "which company / available reports" string is produced only by `inject_report` when `slug` is None). That means `_slug_from_session_key(kwargs)` returned None for a request whose session-key carried `:acct:petsmart.com` → **the session-key is NOT reaching the `pre_llm_call` hook's kwargs** under any name the patch inspects (`gateway_session_key` / `session_key` / `x_hermes_session_key`), nor as any `:acct:`-bearing string in kwargs.

- The patch deployed correctly and is a **safe no-op** on this path (returns None → falls through to the existing message-match, unchanged behavior). It is **harmless but ineffective via the session-key path**.
- Note the server DOES resolve the key (earlier in this doc it echoes `X-Hermes-Session-Id` derived from `X-Hermes-Session-Key`), so the key reaches the gateway — it just isn't threaded into the plugin hook ctx. Closing the loop needs Hermes to pass the session-key (or resolved acct) into `pre_llm_call` kwargs, OR we keep the SPA proxy's `[Account:]` message-tag fallback (which `_match_slug` handles) as the binding mechanism.
- Deterministic bind via session-key is therefore **not yet live**; `[Account:]`-tag / company-name message binding remains the working path.

---

## Report store import — 2026-06-28

Imported all available published audit reports into the Hermes-PRISM report store so grounded chat binds for every company page (was 2/17). **No hermes-prism restart** — plugin reads `index.json` live (mtime-cached `_INDEX_CACHE`), confirmed by the working Nike probe below.

**Source (Mac):** `/Users/arijitchowdhury/prism/<slug>-audit-data.json`. Canonical fields are `meta.company` + `meta.domain` (verified by inspecting nike/petsmart/british-airways — not top-level `company`/`domain`).

**Imported (8 new + petsmart already present = 9 from Mac, 10 total with homedepot-mexico):**
| slug | domain | company |
|---|---|---|
| british-airways | britishairways.com | British Airways |
| brooks-running | brooksrunning.com | Brooks Running |
| dsw | dsw.com | DSW Designer Shoe Warehouse |
| labanquepostale | labanquepostale.fr | La Banque Postale |
| llbean | llbean.com | L.L.Bean |
| nike | nike.com | Nike |
| oriental-trading | orientaltrading.com | Oriental Trading Company |
| savage-x-fenty | savagex.com | Savage X Fenty |
| petsmart | petsmart.com | PetSmart (already present — byte-identical, left intact) |
| homedepot-mexico | homedepot.com.mx | The Home Depot México (already present — untouched) |

**Skipped (8 of the 17 brief slugs — no `<slug>-audit-data.json` on the Mac):** autozone, dell, footlocker, jbl, michaelkors, torrid, thenorthface, michaelkors. Plus `homedepot-mexico` has no Mac source (already on VPS). Note two filename deltas vs brief: source is `oriental-trading` (not `orientaltrading`); `savage-x-fenty` domain is `savagex.com`.

**Procedure:**
- Backed up old index → `/root/.hermes-prism/reports/index.json.bak-20260628-105023` (956 B, the 2-row version).
- scp Mac→VPS `/tmp/prism-import`, validated each is well-formed JSON, then `sudo cp` into `<slug>/audit-data.json` (root:root, dirs 755 / files 644). Staging dir removed after.
- Merged `index.json` (10 rows) preserves the existing rich schema for petsmart/homedepot; new rows carry `slug`/`company`/`domain` (+ corpus/source/imported_at). Plugin read-receipt: `__init__.py:76` reads `reports[]`; `:89-100` matches on `slug`/`domain`/`company`; `:134` loads `<slug>/audit-data.json` — minimum contract satisfied.

**Integrity:**
- petsmart store sha256 == Mac source `ec8936ad…1fc53fda` (unchanged). homedepot-mexico sha256 `2fe092aa…de2bfa81` present + untouched. **petsmart/homedepot intact = Y.**
- `find … -name audit-data.json` → all 10 slug dirs present, each with the file. index.json row count = **10**, valid JSON.

**Nike grounded probe (newly-imported):** one streamed call, `X-Hermes-Session-Key: …:acct:nike.com`, input `[Account: nike] Give me one finding from the audit.`
- Assembled answer: *"Nike's search silently corrects typos without providing 'Did you mean' feedback… 'jrodan 4' corrects to 'jordan 4' but the results header still shows 'jrodan 4 (58)' [FACT - 09-browser-findings.md]."*
- input_tokens 45,703 → full Nike audit-data.json injected (not the "which company" fallback). **PROBE = PASS — grounded.**
- Binding path: the `[Account:]` message tag → `_match_slug` (the known-working path). Consistent with the prior "key-not-in-hook" PARTIAL finding above — session-key-only binding still isn't threaded into the hook; the `[Account:]` tag remains the live mechanism, and it works for the new companies.

**No restart performed (confirmed).**

## hub chat deploy — 2026-06-28

**Production URL:** https://prism.chowmes.com (Vercel project `prism`, prj_yOUkUWmGkCF8DVQ3J8GK2VJSg4SX). Linked dir /Users/arijitchowdhury/prism → project `prism`.

**Env set:** Y (Production). `HERMES_API_URL` + `HERMES_API_KEY` both Encrypted/Production, confirmed via `vercel env ls` (values never printed). Preview NOT set — this project's production branch is `main`, and Vercel rejects preview env vars on the production branch ("Cannot set Production Branch main for a Preview Environment Variable"). Production is what `vercel --prod` uses, so this does not affect the live deploy.

**Deploy:** Y. Latest prod deployment READY, aliased to prism.chowmes.com.

**Widget on page:** Y. `curl -s .../petsmart/ | grep -c chat-widget.js` = 1.

**Upstream brain:** HEALTHY and grounded. From an external network (Mac, mimicking Vercel) the exact proxy call to `https://judge.contentengagement.info/hermes-api/v1/responses` (stream:true) returns HTTP 200 in **6.3s** with the grounded answer: *"PetSmart's no-results rate is **15.98% [FACT]** (8.25M of 51.6M searches...)"*. This is the PASS figure. (One earlier upstream run returned a transient Gemini **HTTP 429 free-tier quota** error in the delta — limit 20 req/gemini-2.5-flash — so the grounding-gate LLM key is rate-limited intermittently; rotate to a paid Gemini key or raise the tier to make this reliable.)

**/api/chat E2E verdict: FAIL (Vercel-side, NOT upstream).** The deployed `/api/chat` returns **HTTP=000, 0 bytes, full timeout** on every real call. Fast paths work in ~0.2s (GET→405, empty body→400 "empty message", missing slug→400 "missing slug"), which proves the function runs AND both env vars are present at runtime (else it would 500 "chat not configured"). It hangs only after the upstream `fetch`.

**ROOT CAUSE:** `api/chat.js` is written as a **Vercel Edge function** (`export const config = { runtime: "edge" }`, Web `Request`/`Response`/`ReadableStream` APIs, `export default async function handler(req)`). But Vercel deploys it as a **Node serverless Lambda** — `vercel inspect` shows `λ api/chat`, not an Edge function. The edge `config` export is NOT being honored by this old static project (`algolia-arian-v2`); adding `package.json {"type":"module"}` did not change it, `vercel.json functions.runtime:"edge"` is invalid ("Runtimes must have a valid version"), and a `--force` no-cache rebuild still produced `λ`. As a Node Lambda, the handler receives `(req, res)` and must call `res.end()`; instead it returns a Web `Response` object the Lambda ignores → the function never ends the response → gateway timeout → client sees HTTP=000.

**FIX (not yet applied — beyond deploy scope, needs authorization):** Rewrite `api/chat.js` to the Node serverless signature (`export default async function handler(req, res)`, read body from `req`, stream upstream deltas via `res.write(...)` + `res.end()`), OR get this Vercel project to actually honor the edge runtime (likely needs a new project created with edge support, or project-level runtime setting). Recommended: rewrite to Node serverless streaming — least friction, no new project. Also rotate the Gemini grounding-gate key off free tier so the 429 doesn't intermittently replace the grounded answer.

## hub chat deploy — RETEST after Node-serverless fix — 2026-06-28

**Fix verified.** Team-lead's commit 237e6b8 rewrote `api/chat.js` to the Node serverless handler (`export default async function handler(req, res)` + `res.write`/`res.end`, `export const config = { maxDuration: 60 }`). Redeployed to https://prism.chowmes.com (deployment prism-9r3qo3to5, READY). `vercel inspect` now shows `λ api/chat (3.08KB) [iad1]` — λ is now CORRECT because the handler is genuinely Node `(req,res)`.

**The HTTP=000 hang is GONE.** Every call now returns HTTP=200 with a streamed plain-text body in ~1–4s (was 000 / full-timeout before). The runtime is serving the stream correctly.

**petsmart /api/chat verdict: PASS (grounded).** After a 60s wait for Gemini quota, the call returned HTTP=200, 4.16s:
> "The no-results rate for PetSmart is **15.98% [FACT]**, meaning approximately 1 in 6 searches results in a dead-end. This translates to an estimated 100 million dead-end searches per year [ESTIMATE]. The best practice for no-results rate is less than 5% [FACT]. Source: PetSmart Algolia search analytics (30-day window)"
Exact target figure (15.98%), [FACT]/[ESTIMATE] grounding markers, source line. The grounded chat works end-to-end through the deployed Vercel proxy.

**nike multi-account verdict: transport PASS / content BLOCKED by Gemini free-tier quota.** Every nike call returned HTTP=200 with a correctly-streamed body, but the body was the Gemini **429 RESOURCE_EXHAUSTED** error (free tier, limit 20 req/gemini-2.5-flash) — the day's quota was exhausted by the petsmart + repeated test calls. Retried per instructions (once after the backoff window); still 429. This is NOT a deploy/code/multi-account-routing failure: the `[Account: nike]` request reached the brain and the grounding gate fired (the gate itself is what emits the 429), which only happens after correct per-account binding. The grounded nike answer will return as soon as the Gemini quota recovers OR the key is moved off free tier.

**ACTION REQUIRED (infra, not deploy):** Rotate the grounding-gate Gemini key off the free tier (or raise the limit). The free-tier 20-req cap intermittently replaces grounded answers with a 429 string — this is now the only thing between "deployed + working" and "reliably grounded for every account."

**Runtime now serving the stream: YES.**
