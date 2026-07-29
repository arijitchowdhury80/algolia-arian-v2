# G — W-D: Unified Chat Design (Telegram + Web SPA on one Hermes brain)

**Date:** 2026-06-28
**Author:** W-D design agent (PRISM/PIP)
**Status:** DESIGN ONLY — no code this pass.
**Decision already locked (by team lead):** Hermes is the single brain. The SPA chat route proxies to the Hermes HTTP API. Hermes reuses the existing FastAPI:8000 tools. This doc designs *how*, with a Protocol Read Receipt, the session-key scheme, the reachability finding, and an ordered build checklist.

Sources read for this design:
- Hermes API server docs — `/Users/arijitchowdhury/Dropbox/AI-Development/Personal/ChowMes/reference/hermes-agent-docs/llms-full.txt` (lines 26909–27328 read verbatim).
- Capability catalogue Q1 — `docs/workspace/hermes-prism-integration/spike-unify-audit/A-hermes-capabilities.md`.
- SPA recon — `docs/workspace/hermes-prism-integration/spike-unify-audit/C-spa-architecture.md`.
- SPA code — `frontend/app/api/chat/route.ts`, `frontend/components/chat/prism-chat.tsx`, `frontend/middleware.ts` (per recon C §5).
- Backend code — `prism_platform/main.py`, `prism_platform/config.py`, repo `docker-compose.yml`, `scaffold-project.sh`.

---

## 0. THE REACHABILITY FINDING (load-bearing — read first)

**Question:** Hermes runs on the VPS. Can the VPS `hermes-prism` container reach the FastAPI tool backend (`prism_platform`, :8000) — the premise of "Hermes reuses FastAPI tools"?

**Finding: NO, not today. The FastAPI backend is not deployed anywhere reachable by the VPS.** Evidence:

1. **No container artifact for `prism_platform`.** Repo `docker-compose.yml` defines only `postgres` and `redis` — there is no `prism_platform`/FastAPI/uvicorn service (`docker-compose.yml:1-30`). The only Dockerfile-class artifacts in the repo are that compose file; there is no `Dockerfile` for the API.
2. **No process entrypoint that binds a public host.** `prism_platform/main.py` only constructs the `FastAPI()` app and routers (`main.py:21-41`); it has no `uvicorn.run(...)` and no `host=0.0.0.0`. It is started ad-hoc (`uvicorn prism_platform.main:app`) on the dev Mac, defaulting to `127.0.0.1:8000`.
3. **No VPS route to it.** The VPS deployment record lists only Temporal (7233/8088) and Scout (8421) behind Caddy — **no :8000 / `prism_platform` service and no Caddy host for it** (memory `reference-vps-deployment`, lines 12-26). The SPA reaches it via `localhost:8000` (recon C §3) — i.e. same-machine only.
4. **Backend assumes localhost infra.** `config.py` defaults: Postgres `localhost:5432`, Redis `localhost:6379`, Temporal `localhost:7233` (`config.py:43-51`). It is wired for a single-host (the Mac) topology.

**Consequence for the design:** "Hermes (on the VPS) reuses FastAPI:8000 tools" has a **prerequisite that is not yet met** — the tool backend must first be made reachable from the VPS Hermes process. Three ways, in preference order:

- **(R1) Co-locate (preferred).** Deploy `prism_platform` as a service *on the VPS* next to Hermes (it already needs Postgres+Redis which the VPS can run via the existing compose). Then Hermes calls `http://127.0.0.1:8000/api/v1/*` locally. Cleanest, lowest latency, no public exposure. Requires: a Dockerfile/systemd unit for the API + porting the local Postgres/Redis/Temporal to the VPS (or pointing at the VPS Temporal already there).
- **(R2) Expose over Caddy with auth.** Add a Caddy host (e.g. `api.contentengagement.info → localhost:8000`) with bearer/basic auth, and have Hermes call the public URL. Simpler to stand up; widens attack surface; the API currently has no auth of its own (no auth router in `main.py`), so the gate must be at Caddy.
- **(R3) Reverse SSH tunnel from VPS → Mac.** Mirror of the existing Scout tunnel pattern (`reference-vps-deployment` lines 27-31) but reversed, so VPS Hermes hits the Mac's :8000. Dev-only; not a production posture (depends on the Mac being up).

**What to check on the box to confirm before building:** `ssh` to the VPS and run `curl -s http://127.0.0.1:8000/health` (expect connection refused today) and `docker ps | grep -i prism` (expect no FastAPI container). If both confirm absence, R1 is the build path.

> This finding does NOT block the SPA-side design below (the proxy, transport repoint, session scheme are all independent of *where* the tools run). It DOES gate the "tool execution plan" in §4 — Hermes cannot call tools it cannot reach.

---

## 1. PROTOCOL READ RECEIPT — Hermes API server

### 1(a) Endpoint choice for the SPA's streaming multi-turn chat

**Candidates** (both quoted from the docs):

- `/v1/responses` with server-side state:
  > "**POST /v1/responses** — OpenAI Responses API format. Supports server-side conversation state via `previous_response_id` — the server stores full conversation history (including tool calls and results) so multi-turn context is preserved without the client managing it." (`llms-full.txt:27020-27022`)
  > "Chained requests also share the same session, so multi-turn conversations appear as a single entry in the dashboard and session history." (`:27080`)
  > Named-conversation variant: "Use the `conversation` parameter instead of tracking response IDs … The server automatically chains to the latest response in that conversation." (`:27082-27092`)

- `/api/sessions/{id}/chat/stream`:
  > "| `POST` | `/api/sessions/{id}/chat/stream` | SSE wrapper over a single turn — emits `assistant.delta`, `tool.started`, `tool.completed`, `run.completed` events |" (`:27234`)

**CHOSEN: `POST /v1/responses` with `stream: true`, keyed by a stable `conversation` name + `X-Hermes-Session-Key` header.** Justification, each point mapped to a quoted rule:

1. **It is OpenAI-Responses-shaped, which the SPA's stack already speaks.** The SPA is AI-SDK v6 + assistant-ui (recon C §1); the Responses event types are spec-native (`response.output_text.delta`, `response.output_item.*`, `response.completed`, quoted at `:27014`), so the normalization shim (§2) maps a *standard* event family rather than Hermes-proprietary `assistant.delta` events.
2. **Server-side multi-turn state with zero client history management** — the cross-device requirement. The doc rule "the server stores full conversation history (including tool calls and results) so multi-turn context is preserved without the client managing it" (`:27022`) maps directly to: phone and laptop both POST the same `conversation`; neither carries the transcript; Hermes reconstructs it. With `/api/sessions/{id}/chat/stream` the SPA would have to first create/resolve a session id and manage it — more moving parts for the same outcome.
3. **One dashboard entry across turns/channels** — "multi-turn conversations appear as a single entry in the dashboard and session history" (`:27080`) is exactly the "one thread" UX goal.
4. **Tool UI is emitted inline in the stream** — "For **Responses**, the stream uses OpenAI Responses event types …" and "Hermes emits spec-native `function_call` and `function_call_output` output items during the SSE stream, so clients can render structured tool UI in real time" (`:27014`, `:27018`). This is what feeds the existing tool-result cards (§2).

*Why not `/api/sessions/{id}/chat/stream`:* it is the right tool for an SPA that wants to *drive a specific pre-existing session id* (e.g. resume a Telegram-originated session by id). We keep it as the **fallback/secondary** path for the "attach SPA to the exact Telegram session id" case (§3), but the primary chat loop uses `/v1/responses` for its no-client-state ergonomics.

### 1(b) Request / response JSON shape

Request (mapped to our proxy):
> ```json
> {"model": "hermes-agent", "input": "What files are in my project?", "instructions": "...", "store": true}
> ```
> (`:27024-27033`). Multi-turn chaining: `{"input": "...", "conversation": "my-project"}` (`:27086-27090`) or `{"input": "...", "previous_response_id": "resp_abc123"}` (`:27073-27078`).

→ **Our proxy sends:** `{"model":"hermes-agent","input":<latest user text>,"conversation":<resolved conversation name, see §3>,"stream":true,"store":true}`. We use `conversation` (stable, derived) rather than tracking `previous_response_id` so the server does the chaining — matches rule `:27090`.

Response (non-stream shape, for reference / `GET /v1/responses/{id}`):
> ```json
> {"id":"resp_abc123","object":"response","status":"completed","model":"hermes-agent",
>  "output":[
>    {"type":"function_call","name":"terminal","arguments":"{...}","call_id":"call_1"},
>    {"type":"function_call_output","call_id":"call_1","output":"..."},
>    {"type":"message","role":"assistant","content":[{"type":"output_text","text":"..."}]}],
>  "usage":{...}}
> ```
> (`:27036-27047`).

→ **Mapping:** `output[]` items of type `function_call` / `function_call_output` are the tool calls/results that must become assistant-ui tool-result cards; `message.content[].output_text` is the assistant text.

### 1(c) SSE / stream event format

> "**Streaming** (`"stream": true`): Returns Server-Sent Events (SSE) … For **Responses**, the stream uses OpenAI Responses event types such as `response.created`, `response.output_text.delta`, `response.output_item.added`, `response.output_item.done`, and `response.completed`." (`:27014`)
> "Responses: Hermes emits spec-native `function_call` and `function_call_output` output items during the SSE stream, so clients can render structured tool UI in real time." (`:27018`)

→ **Mapping:** the proxy consumes these SSE events and re-emits AI-SDK UI-message-stream parts (§2). `response.output_text.delta` → text deltas; `response.output_item.added/done` carrying `function_call` / `function_call_output` → tool-call / tool-result parts.

### 1(d) Auth + session headers — exact and what each scopes

**Auth header:**
> "Bearer token auth via the `Authorization` header: `Authorization: Bearer ***`. Configure the key via `API_SERVER_KEY` env var." (`:27288-27294`)
> Security: "`API_SERVER_KEY` is **required for every deployment**, including the default loopback bind on `127.0.0.1`." (`:27298-27299`)

→ **Mapping:** the proxy (server-side only) sends `Authorization: Bearer <API_SERVER_KEY>`. This key NEVER reaches the browser (§5).

**`X-Hermes-Session-Key`** (long-term memory scope):
> "Pass `X-Hermes-Session-Key` on `/v1/chat/completions`, `/v1/responses`, or `/v1/runs` and Hermes threads it through to `AIAgent(gateway_session_key=...)`, where the Honcho memory provider uses it to derive a stable scope." (`:27269`)
> "a **stable per-channel identifier for long-term memory** … that is **independent** of the transcript-scoped `X-Hermes-Session-Id` (which rotates on `/new`)." (`:27267-27268`)
> Rules: "max 256 chars, control characters (`\r`, `\n`, `\x00`) are rejected, and the value is echoed back on responses (JSON + SSE)." (`:27278`)
> Example value: `agent:main:webui:dm:user-42` (`:27275`).

→ **Scopes: long-term *memory*** (the deal-intelligence the agent remembers), stable across `/new`. This is the lever for "Telegram and web share the same remembered context." Mapping in §3.

**`X-Hermes-Session-Id`** (transcript scope):
> "the transcript-scoped `X-Hermes-Session-Id` (which rotates on `/new`)." (`:27268`); example header `X-Hermes-Session-Id: transcript-alpha` (`:27274`).

→ **Scopes: the *transcript*** (which message thread). Rotates when the user starts a new chat. We do NOT need to set this when using `/v1/responses` + `conversation` (the server manages the transcript via the conversation chain); we set `X-Hermes-Session-Key` for memory scope.

**Net of 1(d):** three identifiers, three scopes — `Authorization` = *who may call the API* (one shared service key), `X-Hermes-Session-Key` = *whose long-term memory scope* (stable per rep+account), `X-Hermes-Session-Id` = *which transcript* (rotates per "new chat"; left to the server under the `conversation` model).

---

## 2. STREAM-SHAPE GAP + normalization shim

**The gap.** assistant-ui consumes the AI-SDK **UI message stream** — the format produced today by `route.ts`'s `streamText(...).toUIMessageStreamResponse()` (recon C §4). Its parts include `text-delta` and, crucially, **tool parts** (`tool-input-*` / `tool-output-available`) that drive the ~22 registered tool-result cards in `prism-chat.tsx` / `tool-renderers.tsx`. Hermes emits **OpenAI Responses SSE** (`response.output_text.delta`, `response.output_item.*` with `function_call` / `function_call_output`) — a *different* event family. Point the component straight at Hermes and the cards break.

**Where the shim lives: server-side, inside the new `app/api/hermes/route.ts` proxy.** It reads Hermes's Responses SSE and writes an AI-SDK UI-message stream (the same shape `toUIMessageStreamResponse()` would). Mapping table:

| Hermes Responses SSE event (`:27014-27018`) | AI-SDK UI-message-stream part | Drives |
|---|---|---|
| `response.created` | stream start / message id | message bootstrap |
| `response.output_text.delta` | `text-delta` | streaming assistant text |
| `response.output_item.added` (type `function_call`) | `tool-input-start` + `tool-input-available` (tool name + args) | shows "running <tool>" card |
| `response.output_item.done` (type `function_call_output`) | `tool-output-available` (call_id + output) | fills the tool-result card |
| `response.completed` | stream finish | finalize |

**Tool-name contract risk (must verify on the box):** the cards key on PRISM tool names (`get_company_profile`, `get_tech_stack`, … — 25 of them in `lib/tools.ts`). The shim must surface the **same** `name`/`call_id` Hermes emits in `function_call`. This only lines up if Hermes invokes tools whose names match the SPA's renderer keys (i.e. the FastAPI module tools are registered in Hermes under those names). If Hermes names them differently, the shim needs a name-map, OR the cards fall back to a generic tool renderer. **Verification:** once R1 (§0) is done, run a real audit turn through `/v1/responses` and inspect the `function_call.name` values vs the renderer registry. Until then this is the single biggest stream-compat unknown.

**Minimal vs clean (recon C §8a):** start minimal — keep `useChat` + assistant-ui `Thread`, repoint transport to `/api/hermes`, do the SSE→UI-stream mapping in the proxy. Only build a bespoke assistant-ui runtime if the mapping proves lossy.

---

## 3. IDENTITY + SESSION-KEY SCHEME

**Goal:** one rep, working an account, gets the *same remembered context* whether on Telegram or the web SPA (and phone↔laptop on web). Per A-Q1.5 the honest framing: **shared state+memory across channels is achievable with a small mapping layer; a single live transcript simultaneously on two devices is not a native Hermes feature** — we get cross-device continuity on web (same `conversation` + same memory key), and cross-*channel* shared *memory* (same `X-Hermes-Session-Key`), not a literal co-attached transcript with Telegram.

### 3.1 The key format (concrete)

Web identity anchor = Clerk `userId` (the same person on phone or laptop web — recon C §5). Account scope = `currentDomain` from Zustand (recon C §8c). The audit subject scopes memory so context doesn't bleed across accounts.

**`X-Hermes-Session-Key` (long-term memory scope) — exact string:**

```
agent:main:prism:rep:<repId>:acct:<domain>
```

e.g. `agent:main:prism:rep:user_2abc...:acct:petsmart.com`

- Follows Hermes's own `agent:main:<channel>:<...>` convention (A-Q1.2, key-format table) and the doc's `webui:dm:user-42` example shape (`:27275`); ≤256 chars (rule `:27278`).
- `<repId>` = a stable rep id mapped from Clerk `userId` (web) AND from the Telegram chat id (Telegram) — see 3.3.
- Parameterized by `<domain>` = the account the rep is viewing → per-account memory scope.

**`conversation` name (transcript chain for `/v1/responses`) — exact string:**

```
prism:<repId>:<domain>
```

e.g. `prism:user_2abc...:petsmart.com`. Same value from phone and laptop → server chains both into one transcript (rule `:27090`), giving cross-device web continuity for free.

### 3.2 Web side (the clean path)

On chat open, the proxy resolves `(clerkUserId, currentDomain)` → `repId` → builds both strings above, then for each turn POSTs `/v1/responses` with `conversation = prism:<repId>:<domain>`, header `X-Hermes-Session-Key: agent:main:prism:rep:<repId>:acct:<domain>`, `Authorization: Bearer <API_SERVER_KEY>`. Phone and laptop send identical values → one thread, one memory scope.

### 3.3 Reconciling Telegram (the constraint, cited)

Telegram's session key is **platform-derived and fixed by Hermes** — `agent:main:telegram:dm:<chat_id>` (A-Q1.2, key-format table; `llms-full.txt:5547-5556`). Hermes "never merges keys on its own" (A-Q1.5). So we cannot make Telegram natively emit our `agent:main:prism:...` key. Two concrete reconciliation options (pick per effort budget):

- **(I1) Shared *memory* scope (recommended, low-effort).** Map Telegram chat_id → the same `repId` (a one-time `/link` step in the bot: rep sends a code shown in the SPA). Both channels then resolve to the **same per-account deal-intelligence object + memory scope** even though their *transcripts* differ. This is exactly A-Q1.5's option (b): "treat Telegram and web as two scopes that share the same persisted deal-intelligence object + memory scope rather than literally one live transcript." Honcho-style memory keyed by `X-Hermes-Session-Key` is the carrier; the web side already sends our key; for Telegram we accept its native transcript but ensure the *memory provider scope* resolves to the same rep+account (requires the memory provider's scope to be derivable from the linked rep, not only the raw telegram key — verify against the chosen provider on the box).
- **(I2) Re-bind to one session id via Sessions REST (higher-effort, true single transcript).** Use `POST /api/sessions/{id}/fork` / drive `/api/sessions/{id}/chat` (`:27232-27234`) to point the SPA at the *Telegram-originated session id*, mirroring `/handoff`'s "re-bind the destination channel key to the existing session id" mechanism (A-Q1.3, `:5273`). This yields a literal shared transcript but is baton-pass-shaped (A-Q1.3: "ping-pong, not simultaneous") and refuses mid-turn (`:5283`). Use only if a single literal transcript across Telegram+web is a hard requirement.

**Recommendation: ship I1.** It satisfies the real user need (the agent *remembers* the same deal regardless of channel) without fighting Hermes's per-platform keying. Revisit I2 only if a literal shared transcript is demanded.

**The mapping layer PRISM must build (per A-Q1.5):** a thin `rep ↔ {clerk_user_id, telegram_chat_id}` table (lives in the FastAPI backend, or Hermes memory) + the deterministic key/conversation builders above. That is the only net-new identity infrastructure.

---

## 4. TOOL-EXECUTION PLAN

**How Hermes invokes the FastAPI:8000 tools.** Hermes's native tool for hitting an HTTP service is its `web`/`terminal` toolset, but the durable, typed way is to register the 25 PRISM module calls as **Hermes skills/tools that issue HTTP calls to the FastAPI `/api/v1/*` endpoints** (the same endpoints `lib/tools.ts` calls today — recon C §4). Concretely: each algolia-* / intel module becomes a Hermes tool whose body is an HTTP request to `http://127.0.0.1:8000/api/v1/modules/{module}/execute/` (and the read endpoints `/accounts/{domain}/results`, etc., recon C §3). This is **HTTP calls, not MCP** — the FastAPI backend already exposes REST; wrapping it in MCP would add a layer for no gain. (Hermes *can* speak MCP, but the existing contract is REST, so HTTP tools are the lower-friction map.)

**Gated entirely on the §0 reachability fix.** "Hermes calls `http://127.0.0.1:8000`" is only true after R1 (co-locate the FastAPI backend on the VPS). Until then Hermes has no tools to call. **This is the critical-path prerequisite for the whole "one brain" story.**

**Where zero-hallucination grounding runs — today vs target.**
- **Today it lives in TWO disconnected places:** (1) the SPA's `app/api/chat/route.ts` hard-coded aRRIe `SYSTEM_PROMPT` with its "ZERO HALLUCINATION POLICY (ABSOLUTE)" (read verbatim, `route.ts:15-57`); and (2) the proven Hermes-side **`prism-report-qa` plugin** — a `pre_llm_call` source-injection + `transform_llm_output` Gemini grounding gate, verified over PetSmart (memory: W-B grounded report-QA WORKING; plugin src in `docs/workspace/hermes-prism-integration/chowmes-prism/plugins/`). A-Q2.4 confirms `pre_llm_call` can inject context and `transform_llm_output` can rewrite output — "exactly the pair PRISM's grounded report-QA gate already uses."
- **Target: grounding must live in Hermes, once, so BOTH channels inherit it.** When Hermes becomes the brain, the aRRIe identity + grounding policy moves OUT of `route.ts` (it would otherwise only protect web, leaving Telegram ungrounded — recon C §9 "two brains problem") and into Hermes as: (a) the system/`instructions` layer (the aRRIe persona, layered per `:27280-27287`), plus (b) the existing `prism-report-qa` plugin as the **hard post-gen gate** — because injection alone is insufficient (memory: "injection insufficient, need hard gate" — PROVEN: source-injection + "answer only from it" still fabricated; a post-gen verifier is mandatory). So: persona via `instructions`, **enforcement via the plugin's `transform_llm_output` gate**. Both Telegram and the SPA then get identical grounding.

---

## 5. THE SPA CHANGES (described, not coded)

**PREREQUISITE (blocking): `frontend/` is UNTRACKED in git.** Recon C §6: 0 tracked files in `frontend/`. It must be committed before any edits, or changes are unrecoverable and unreviewable. First build step, no exceptions.

1. **New `app/api/hermes/route.ts` proxy (server-side).** Sibling of `app/api/chat/route.ts` (the only existing route handler — recon C §7). Responsibilities: read Clerk `userId` (server-side), resolve `repId` + `currentDomain`, build the `conversation` name and `X-Hermes-Session-Key` (§3.1), POST `/v1/responses` (`stream:true`) to the Hermes API with `Authorization: Bearer <API_SERVER_KEY>`, run the SSE→UI-message-stream shim (§2), return the UI stream. Keeps **bearer key, Hermes URL, and session key entirely off the client.** Reuse `lib/prism-api.ts`'s logging/redirect pattern (recon C §8b).
2. **Repoint the chat transport.** In `prism-chat.tsx`, `useChat({ id: "prism-chat" })` uses the default transport (POSTs `/api/chat`). Change it to target `/api/hermes` (set `transport`/`api` to the new route). The assistant-ui `Thread` and all ~22 tool-renderer registrations stay as-is — they consume the UI-message stream the shim produces (recon C §8a "swap the brain, don't rebuild the UI").
3. **Gate the currently-PUBLIC `/api/chat`.** `middleware.ts` lists `/api/chat*` as public (recon C §5). Once chat carries real intel: either remove `/api/chat` from the public matcher and require Clerk, or retire `/api/chat` entirely in favour of `/api/hermes` (which must itself be Clerk-gated). Either way, **no unauthenticated path may reach a brain that holds account intel.**
4. **(Deferred) thread hydration on open.** For history-on-reload, optionally `GET /v1/responses/{id}` or list via the conversation to hydrate the assistant-ui Thread. Not required for v1 if we accept that reload starts a fresh view of the same server-side conversation (the *memory* persists regardless via the session key).

**Out of scope / don't conflate:** the audit-progress SSE (`/api/v1/audits/{id}/stream`) is a separate stream from chat (recon C §9) — leave it alone.

---

## 6. BUILD CHECKLIST (ordered, verifiable)

Each step has an explicit verification — no step is "done" without its check passing.

1. **Commit `frontend/` to git.** ✅ when `git ls-files frontend/ | wc -l` > 0 and `.env*`/`node_modules`/`.next` remain ignored.
2. **Confirm the reachability gap on the VPS.** `curl -s http://127.0.0.1:8000/health` on the box → expect refused; `docker ps | grep -i prism` → expect no FastAPI container. ✅ when the absence is confirmed (or, if already present, R1 is moot).
3. **R1 — co-locate the FastAPI backend on the VPS.** Add a Dockerfile/systemd unit for `prism_platform` (uvicorn, bind `127.0.0.1:8000`); bring up Postgres/Redis (existing compose) on the VPS; point `temporal_host` at the VPS Temporal already running (`reference-vps-deployment`). ✅ when `curl http://127.0.0.1:8000/health` on the VPS returns `{"status":"ok"}`.
4. **Enable + verify the Hermes API server.** Set `API_SERVER_ENABLED=true`, `API_SERVER_KEY=<secret>` in `~/.hermes/.env` (`:26924-26945`); `hermes gateway`. ✅ when `curl -H "Authorization: Bearer <key>" http://127.0.0.1:8642/v1/capabilities` shows `"responses_api": true` and `"session_key_header": "X-Hermes-Session-Key"` (`:27108-27127`, `:27278`).
5. **Register the 25 PRISM module tools in Hermes** as HTTP tools → `http://127.0.0.1:8000/api/v1/*` (§4). ✅ when `GET /v1/toolsets` lists them (`:27259-27265`) and a manual `/v1/responses` turn ("run intel-company on petsmart.com") emits a `function_call` to the right endpoint and returns real data.
6. **Move grounding into Hermes.** aRRIe persona → `instructions` layer; enable the `prism-report-qa` plugin as the `transform_llm_output` gate (memory: hermes plugins are opt-in — `hermes plugins enable prism-report-qa` + restart). ✅ when a known-absent fact is *refused* and a known fact is grounded (re-run the PetSmart 15.98% check from W-B).
7. **Build `app/api/hermes/route.ts` proxy + SSE→UI-stream shim** (§2, §5.1). ✅ when a curl through the proxy returns a valid AI-SDK UI-message stream (text-delta + tool parts) for one turn.
8. **Verify tool-name contract** (§2 risk). Inspect `function_call.name` values vs the renderer registry; add a name-map if they diverge. ✅ when a real audit turn paints the correct tool-result cards (not the generic fallback).
9. **Repoint `prism-chat.tsx` transport** to `/api/hermes` (§5.2). ✅ when the SPA chat streams from Hermes and existing cards render.
10. **Identity + session scheme** (§3): build the `rep ↔ {clerk_user_id, telegram_chat_id}` map + key/conversation builders; Telegram `/link` step (I1). ✅ when phone and laptop web continue one conversation, and a fact taught on Telegram is recalled in the SPA (shared memory scope).
11. **Gate `/api/chat`** (§5.3). ✅ when an unauthenticated request to the chat path is rejected by Clerk middleware.
12. **End-to-end:** one rep, one account, ask the same question on Telegram then SPA → consistent, grounded answers from the same remembered context. ✅ when both channels agree and both refuse the same absent fact.

---

## Validation risk surface (per global SOP)

- **What this design proves:** the endpoint/header/stream contract is grounded in verbatim Hermes docs (§1 read receipt); the SPA insertion points are grounded in the actual code (recon C + files read).
- **What it does NOT prove:** (a) that the VPS Hermes can reach FastAPI:8000 — it cannot today (§0), this is a build prerequisite, not a verified state; (b) that Hermes's `function_call.name` values match the SPA renderer keys (§2 — unverified until a real turn runs on the box); (c) that the chosen memory provider's scope is derivable from a linked rep id for the Telegram I1 path (§3.3 — verify on the box).
- **Remaining risk:** runtime stream-shape and tool-name mismatches are only disprovable by running a real `/v1/responses` turn end-to-end on the VPS (checklist steps 5, 7, 8). No amount of doc-reading discharges that — it is the runtime proof.
