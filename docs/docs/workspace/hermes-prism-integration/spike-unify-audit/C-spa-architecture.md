# C — PRISM SPA Architecture Recon

**Scope:** `/Users/arijitchowdhury/Dropbox/AI-Development/PIP/frontend` (Next.js, app router, pnpm).
**Goal of recon:** map the SPA to plan embedding a live chat agent that talks to the Hermes-PRISM backend, shares ONE thread with the Telegram bot, and survives phone↔laptop.
**Date:** 2026-06-28

---

## TL;DR (read this first)

The SPA is **not** "an audit report renderer with no chat." It is **already a full chat application.** There is a working AI agent named **aRRIe** rendered in the right panel, with 25 grounded tool calls, tool-result cards, an SSE audit-progress stream, and a three-panel intelligence dashboard.

The catch — and the whole reason this spike exists — is **where the agent runs and how little persists:**

1. **The chat agent runs inside Next.js, not Hermes.** `app/api/chat/route.ts` calls the Vercel AI SDK (`streamText`) against OpenAI/Anthropic/Google directly, with a hard-coded "aRRIe" system prompt and a local `lib/tools.ts` toolset. Hermes-PRISM is nowhere in this path. To unify with Telegram you either (a) repoint this route at the Hermes HTTP API, or (b) keep it and make Hermes the second client of the same thread store. This is the central architectural fork.
2. **There is zero thread persistence.** The thread lives in browser memory via `useChat({ id: "prism-chat" })`. No DB, no server thread id, no user-scoped storage. Reload = blank. Phone↔laptop = impossible today. This is the single biggest gap for the cross-device requirement.
3. **The "audit report data" is NOT static JSON.** It is served at runtime by a **separate FastAPI backend** (`prism_platform/`, `localhost:8000`) over `/api/v1/*`. `public/accounts.json` is a stale mock fixture, not the live source.

So the work is less "add a chat widget" and more "swap the chat brain + give the thread a home that two clients can share."

---

## 1. Stack & design system

| Layer | What's in use |
|---|---|
| Framework | **Next.js 15.5.14**, App Router, **React 19.1**, **Turbopack** (dev + build) |
| Package mgr | **pnpm** (`pnpm-lock.yaml`) |
| Language | TypeScript 5, strict |
| Styling | **Tailwind CSS v4** (`@tailwindcss/postcss`), CSS vars in `app/globals.css` |
| UI kit | **shadcn/ui** (`components.json`, style `base-nova`, RSC on, Radix + `radix-ui` + `@base-ui/react` primitives, **lucide** icons) |
| Chat UI | **`@assistant-ui/react`** + `@assistant-ui/react-ai-sdk` + `@assistant-ui/react-markdown` |
| AI layer | **Vercel AI SDK v6** (`ai`, `@ai-sdk/react`) with `@ai-sdk/anthropic`, `@ai-sdk/openai`, `@ai-sdk/google` |
| State | **Zustand** (`lib/store.ts`) — single global store |
| Data fetching | `@tanstack/react-query` (installed; account/result fetches are hand-rolled `fetch`) |
| Auth | **Clerk** (`@clerk/nextjs`) |
| Misc | framer-motion, react-resizable-panels (3-panel shell), react-window (virtualized account list), number-flow, zod (tool schemas) |
| Font | Sora (next/font/google) |
| Brand | Algolia blue `#003DFF`, ink `#23263B`, glass-panel aesthetic |

This is a modern, opinionated stack. **assistant-ui + AI SDK are already wired** — the chat plumbing exists; we are changing what it points at, not building it.

---

## 2. App structure (routes under `app/`)

```
app/
  layout.tsx                     Root: ClerkProvider (skipped if BYPASS_AUTH), Sora font, TooltipProvider
  page.tsx                       redirect("/chat")
  globals.css                    Tailwind v4 + design tokens
  icon.svg / favicon
  (authenticated)/               Route group — wrapped by AppShell (3-panel layout)
    layout.tsx                   <AppShell>{children}</AppShell>
    page.tsx                     redirect("/chat")
    chat/page.tsx                returns null (!) — see note below
  demo/page.tsx                  Public design demo: CompanyCard with hard-coded Nike mock
  sign-in/[[...sign-in]]/page.tsx  Clerk sign-in
  api/
    chat/route.ts                THE chat backend (AI SDK streamText, aRRIe prompt, lib/tools)
```

**Important structural quirk:** `chat/page.tsx` returns `null`. The page body is empty because the layout (`AppShell`) renders everything: left panel (accounts + ROI), center panel (the tabbed dashboard = "the audit report"), right panel (aRRIe chat). So "the audit report page" and "the chat" are **the same screen**, composed by `AppShell` → `ResizableShell`, not by the route. The route only exists to trigger the layout.

### How an "audit report" is rendered today
- Center panel (`components/layout/center-panel.tsx` → `components/dashboard/*`) renders **6 tabs**: Overview, Research, Search Audit, Business Case, Competitive, Sales Actions (`DASHBOARD_TABS` in `lib/store.ts`).
- Tab content is driven by `usePrismStore().availableResults` — a `Record<moduleName, ModuleResult>` populated at runtime.
- **It is dynamic CSR, not SSG.** Data arrives two ways: (a) selecting an account in the left panel fires `loadAccountResults(domain)` → `GET {API}/api/v1/accounts/{domain}/results`; (b) aRRIe tool calls stream `ModuleResult`s into the store via `viewModuleDetails`.

---

## 3. The data contract (where audit data comes from)

**Source of truth = a separate FastAPI service**, not the SPA and not static files.

- Backend: `prism_platform/` (FastAPI, `prism_platform/main.py`, routers under `prism_platform/api/routers/`), serving `/api/v1/*` at **`http://localhost:8000`**.
- The SPA reaches it via `lib/prism-api.ts` `prismFetch()` using `process.env.PRISM_API_URL` (server side, in tools) and `NEXT_PUBLIC_PRISM_API_URL` (client side, in `left-panel.tsx`).
- **`public/accounts.json` is a stale mock fixture**, NOT the live contract. The live account list comes from `GET /api/v1/accounts/`.

### The wire shape — `ModuleResult` (the universal envelope)
Every module/tool returns this (`lib/types.ts`):
```ts
interface ModuleResult {
  module_name: string;
  module_version: string;
  status: "success" | "partial" | "failed";
  output: Record<string, unknown>;   // module-specific payload
  sources: Source[];                 // provenance per field (tier, url, confidence)
  duration_ms: number;
  errors: string[]; warnings: string[];
}
```
Per-module `output` shapes are fully typed in `lib/types.ts` (CompanyProfileResult, TrafficResult, FinancialPublicResult, InvestorResult, BusinessCaseResult, etc.). `Source` carries the evidence tier (`VERIFIED|WEBFETCH|WEBSEARCH|ESTIMATE|NO_SOURCE`) the grounding story depends on.

### Key backend endpoints the SPA already calls
- `GET /api/v1/accounts/` — account list (left panel)
- `GET /api/v1/accounts/{domain}/results` — all module results for a domain (the "report")
- `GET /api/v1/accounts/{domain}/freshness` — staleness check
- `POST /api/v1/modules/{module}/execute/` — run one intel module (per-tool)
- `POST /api/v1/audits/` + `POST /api/v1/audits/{id}/run` — create + trigger audit
- `GET /api/v1/audits/{id}` — audit status
- **`GET /api/v1/audits/{id}/stream`** — **SSE** stream of wave/module progress (`lib/use-audit-stream.ts`, EventSource)
- `GET /api/v1/evidence/*`, `/api/v1/benchmarks/*` — customer-evidence + benchmarks

---

## 4. The chat agent today (the thing we're replacing/unifying)

- **Component:** `components/chat/prism-chat.tsx` → `useChat({ id: "prism-chat" })` bridged to assistant-ui via `useAISDKRuntime`. Registers ~22 tool-UI renderers (`components/chat/tool-renderers.tsx`) so each tool result paints a card. Rendered by `right-panel.tsx`.
- **Backend:** `app/api/chat/route.ts` — `streamText({ model, system: SYSTEM_PROMPT, messages, tools, stopWhen: stepCountIs(30) })` → `toUIMessageStreamResponse()`. Model is chosen at request time (`MODEL_FACTORY`, OpenAI/Anthropic/Google), default `gpt-4o`.
- **Prompt:** a long hard-coded "aRRIe" persona with an absolute zero-hallucination / grounding policy and a baked-in Algolia customer-evidence playbook. This is the de-facto sales-coach identity living in the Next.js route — relevant to W-C (SOUL/AGENTS) because Hermes would own this instead.
- **Tools:** `lib/tools.ts` — 25 `ai` `tool()` defs (zod schemas) that call `prismFetch` against the FastAPI backend. The agent's "hands" are HTTP calls to `localhost:8000`.

**Net:** the SPA agent is a self-contained AI-SDK agent that happens to share the FastAPI data backend with the dashboard. **It does not touch Hermes-PRISM.** Telegram + SPA sharing one thread requires both to write to one thread store and (ideally) run the same brain — today they run different brains and no shared store.

---

## 5. Auth status today

- **Clerk middleware is live** (`middleware.ts`, `clerkMiddleware`).
- Public routes: `/sign-in*`, **`/api/chat*`**, `/demo*`. Everything else is `auth.protect()`.
- **`BYPASS_AUTH=true` short-circuits all auth** (middleware returns `next()`; `layout.tsx` drops `ClerkProvider`; `left-panel.tsx` shows a hard-coded "Arijit Chowdhury / AC" avatar). The app is currently developed in bypass mode.
- **Critical for the unify plan:** `/api/chat` is **public** today (so unauthenticated/Clerk-less calls work in dev). For "private chat over intel," that route must become authenticated, and Clerk's `userId` is the natural cross-device identity key — it's the same person whether on phone or laptop *web*. (Telegram identity is separate and must be mapped to the Clerk user — see §6c.)
- We can keep **public report view + private chat**: leave the dashboard/report routes public (or `/demo`-style), gate only the chat route + thread store on Clerk.

---

## 6. Build / deploy posture

- Scripts: `dev: next dev --turbopack`, `build: next build --turbopack`, `start: next start`.
- **It is a running Node server, NOT a static export.** `next.config.ts` has no `output: "export"`; the app uses route handlers (`app/api/chat/route.ts`), Clerk middleware, and SSR/RSC. **This is good news** — a Node server can proxy to the Hermes HTTP API and host new route handlers / a thread store. No static-hosting constraint blocks the integration.
- The whole `frontend/` directory is **untracked in git** (0 tracked files; `.gitignore` excludes `.next`, `node_modules`, `.env*`, `/.clerk/`). It exists in the working tree only. Worth flagging for the build owner — this UI is not yet under version control.
- Env: `.env.local` is present and **access-protected** (could not read keys). From code references, the app reads at minimum: `PRISM_API_URL`, `NEXT_PUBLIC_PRISM_API_URL`, `BYPASS_AUTH`, `NEXT_PUBLIC_BYPASS_AUTH`, `AI_MODEL`, plus Clerk + the three AI-provider keys.

---

## 7. Existing API routes (route handlers)

Only one: **`app/api/chat/route.ts`** (`POST`, `maxDuration = 60`). No other `app/api/*` handlers exist. This is both the entire current backend-call surface of the SPA *and* the obvious place to add siblings (`/api/thread`, `/api/hermes`, webhook receivers).

---

## 8. Cleanest insertion points (the deliverable)

### (a) Chat widget — already exists; swap the brain, don't rebuild the UI
The widget is `components/chat/prism-chat.tsx` (`useChat` + assistant-ui Thread) in `right-panel.tsx`. **Do not build a new widget.** Two viable moves:
- **Minimal:** keep `useChat` and the assistant-ui Thread; repoint it by changing the transport/endpoint from `/api/chat` to a new `/api/hermes` route that proxies the Hermes HTTP API. The tool-result cards still work if Hermes emits AI-SDK-compatible UI message parts (or you add a normalizer).
- **Cleaner long-term:** replace the AI-SDK runtime with a thin custom runtime that streams from Hermes. Higher effort; only needed if Hermes's stream shape diverges hard from AI-SDK's `toUIMessageStreamResponse`.
**Recommendation:** start minimal (new route handler, same component).

### (b) Backend call path to the Hermes HTTP API — new route handler
Add **`app/api/hermes/route.ts`** (sibling of `app/api/chat/route.ts`). Because this is a Node server, the route handler proxies server-side to Hermes (keeps Hermes URL/keys off the client, lets us inject the Clerk `userId` and the resolved thread id). Reuse `lib/prism-api.ts`'s logging/redirect-handling pattern. **Read the Hermes HTTP wire format (Read Receipt required) before writing this** — message shape, streaming format (SSE vs chunked), thread-id param, auth header. Do not infer it.

### (c) Session / identity for one thread across devices — the real new work
Today there is **no thread store** (`useChat` is in-memory only). To make Telegram + SPA + phone↔laptop share ONE thread:
1. **Identity:** use Clerk `userId` as the canonical user key for the web side. Map the Telegram chat/user id → Clerk userId in a small lookup (one-time link step). Hermes likely already keys threads by some id — align on a single `thread_id` derived per (user, account/domain) so the SPA, phone, and Telegram all resolve to the same thread.
2. **Thread store:** Hermes is the natural home for thread state (it already persists threads for Telegram). Preferred path = **make the SPA a thin client of Hermes's thread**: on chat open, the new `/api/hermes` route resolves `thread_id` for `(clerkUserId, currentDomain)`, asks Hermes for history, hydrates the assistant-ui Thread, then streams new turns through Hermes. That gives cross-device + cross-channel "for free" because Hermes is the single source of truth. (Fallback only if Hermes can't expose history: a small thread table in the FastAPI backend keyed by userId+domain.)
3. **Account context:** the SPA already tracks `currentDomain`/`currentCompanyName` in Zustand — pass these to Hermes so the shared thread is scoped to the account the AE is looking at (matches the existing per-account mental model).

---

## 9. Risks / things the unify plan must not miss

- **Two brains problem:** the aRRIe prompt + grounding policy + evidence playbook currently live in `app/api/chat/route.ts`. If Hermes becomes the brain, that identity/grounding logic must move to Hermes (ties to W-B grounded report-QA and W-C SOUL/AGENTS), or the two channels will behave differently.
- **Tool execution location:** SPA tools call FastAPI `localhost:8000`. Hermes runs on the VPS. Decide whether Hermes calls the same FastAPI (network reachability) or whether tools are reimplemented as Hermes skills. The grounding guarantee depends on which executes.
- **Stream-shape compatibility:** assistant-ui expects AI-SDK UI message stream parts. Hermes's stream must be normalized to that, or the tool-result cards break.
- **`/api/chat` is public** — must be gated before it carries real intel chat.
- **frontend/ is untracked** — get it into git before modifying.
- **Two SSE systems will coexist:** audit-progress SSE (`/api/v1/audits/{id}/stream`) is independent of chat streaming; don't conflate them.
