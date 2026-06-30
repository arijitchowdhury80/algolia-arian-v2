# Slice 1 — Google login + deploy + identity capture

**Date:** 2026-06-30
**Status:** Design — pending user review → writing-plans
**Depends on:** nothing (foundation slice)
**Unblocks:** Slice 2 (multi-tenancy / ACL) — see `2026-06-30-slice2-multitenancy-acl-design.md`

## Goal

A visitor hits the deployed Next.js app at **`prism.chowmes.com/app`**, lands on `/app/sign-in`,
clicks **Continue with Google**, authenticates, and lands on `/app/chat`. Any Google account is
allowed. The authenticated Clerk userId is captured and persisted as the **tenant key** so Slice 2's
ACL has a clean foundation.

## Deployment model: VPS + Caddy + systemd (NOT Vercel)

The whole stack runs on the Chowmes VPS behind Caddy — there is no Vercel. Verified on the box
(2026-06-30):
- `prism-platform` = `uvicorn prism_platform.main:app` on `127.0.0.1:8000`, systemd service.
- static `prism-hub` = node server on `127.0.0.1:8651`, fronted by Caddy (TLS, :80/:443).
- **Node 22.23.1 + npm present**; `/opt/prism-hub` and `/opt/prism-platform` exist; **no Next.js app
  deployed** (`/opt/prism-frontend` absent).

The Next.js app cannot be a static export — Clerk middleware + the `/api/hermes` server route need a
Node runtime. So:
- Deploy to `/opt/prism-frontend`, build (`next build`), run `next start` as a **systemd service**
  (`prism-frontend.service`) on `127.0.0.1:3000` — mirrors `prism-platform.service`.
- **Same-origin path route** at `prism.chowmes.com/app` (chosen over a subdomain): when Slice 2 gates
  the reports, app + reports share the origin so the Clerk session cookie covers both — no
  cross-origin/satellite-domain dance.
- Three concrete requirements of the path route (all standard, no blockers):
  1. `next.config` → `basePath: '/app'` (routes/assets become `/app/...`).
  2. Caddy → `handle_path /app/*` reverse_proxy `127.0.0.1:3000`; the static prism-hub node server
     (`:8651`) keeps everything else. Order so the static server never claims `/app`.
  3. Clerk path env: `NEXT_PUBLIC_CLERK_SIGN_IN_URL=/app/sign-in` (and siblings); prod redirect URLs
     point at `/app/*`. Clerk binds to the domain `prism.chowmes.com` and handles custom paths.
- Service env: Clerk **prod** keys, `PRISM_API_URL=http://127.0.0.1:8000`, `HERMES_API_URL/KEY`,
  `BYPASS_AUTH` **unset**.

## The core truth: this is config + deploy, not building auth

The Clerk wiring already exists and works end-to-end in dev:

- `frontend/app/layout.tsx:41` — `<ClerkProvider>` wraps the app.
- `frontend/middleware.ts:8-16` — `clerkMiddleware` protects everything except `/sign-in` and
  `/demo`; `BYPASS_AUTH=true` short-circuits for local dev.
- `frontend/app/sign-in/[[...sign-in]]/page.tsx:14` — Clerk `<SignIn>` component. **It
  auto-renders whatever social connections are enabled in the Clerk dashboard** — so "Sign in
  with Google" is a dashboard toggle, not code.
- Flow: `/` → redirect `/chat` (`app/page.tsx:4`) → `/chat` is in the `(authenticated)` group →
  middleware bounces unauthenticated users to `/sign-in` → after login → `/chat`.
- `frontend/.env.local` exists (Clerk dev keys present). No `vercel.json` / `.vercel` → the app
  has never been deployed.

## Scope

### In scope
1. **Enable Google** as a Clerk social connection (dashboard). Dev works on Clerk's shared Google
   credentials instantly; prod needs your own Google Cloud OAuth client.
2. **Deploy `frontend/` to the VPS** as `prism-frontend.service` (systemd + `next start`,
   `127.0.0.1:3000`) behind a Caddy `/app` route, with Clerk **production** keys, `BYPASS_AUTH` unset.
3. **Identity capture hook** — persist the authenticated Clerk userId as the tenant key (a real
   `users` row, not `"system"`), so Slice 2 can build ACL without re-plumbing identity.
4. **Verify** Google sign-in end-to-end (dev, then the live prod URL).

### Out of scope (Slice 2)
Gating the reports, migrating reports into the app, multi-tenant org model, ACL,
retiring/repurposing the static prism-hub site.

## Task split (most steps are human/browser-gated, not code)

| # | Step | Owner | Why |
|---|------|-------|-----|
| 1 | Confirm/create Clerk **production** instance | User (Clerk dashboard) | Dev keys can't serve prod |
| 2 | Enable **Google** social connection | User (Clerk dashboard) | A toggle, not code |
| 3 | Create **Google Cloud OAuth client** (prod), paste client ID/secret into Clerk | User (Google Cloud + Clerk) | Console actions Claude can't perform |
| 4 | Add the `prism.chowmes.com/app` **DNS/Clerk prod domain** binding + prod redirect URLs | User (Clerk dashboard) | Clerk prod binds to the domain; OAuth redirects must list `/app/*` |
| 5 | Build + deploy to `/opt/prism-frontend`; write `prism-frontend.service`; add Caddy `/app` route; set service env | Claude (on VPS) + User (authorize) | Mirrors `prism-platform.service`; Claude has VPS admin for service/Caddy work |
| 6 | **Verify** Google sign-in end-to-end (dev → live `prism.chowmes.com/app`) | Claude | Evidence, not assertion |

## Identity capture hook (the one piece of real code)

When a user is authenticated, mirror their Clerk identity into a local `users` row and derive the
tenant key from it. This is the seam Slice 2 builds ACL on.

- `users` table: `id` (text PK = Clerk userId), `email`, `name`, `org_id` (nullable — org-ready seam).
- On first authenticated request (or a Clerk webhook), upsert the `users` row.
- The Hermes session key derived in `frontend/lib/hermes-session.ts` must carry this userId in its
  identity segment (already maps Clerk userId → session key; confirm it threads the verified id).

> Detail deferred to the plan: webhook-driven upsert vs lazy upsert-on-request. Either works;
> pick in writing-plans.

## Security

- **`BYPASS_AUTH` must never be set in the `prism-frontend.service` env.** It is read at
  `middleware.ts:10` and `layout.tsx:18`; if set, it disables auth entirely. The deploy checklist
  must assert it is unset in the systemd unit.
- **Caddy route isolation:** the `/app` reverse_proxy must not let the static prism-hub server claim
  `/app/*`, and the Next app must not shadow the public report routes. Verify route precedence post-deploy.
- The Clerk **secret key** and (later) the Hermes API key stay server-side only — never
  `NEXT_PUBLIC_*`.

## Validation risk surface

- **What dev verification proves:** the code path + sign-in flow are correct (Google button
  appears, OAuth round-trips, user lands on `/chat`).
- **What it does NOT prove:** production Google OAuth. That is only proven once the prod Clerk
  instance + your Google prod OAuth client + the deployed domain are live and sign-in is tested
  against the real URL.
- **Remaining risk:** prod-only OAuth redirect/origin misconfig **plus** the `/app` basePath +
  Caddy route interaction (the redirect could resolve to `/sign-in` instead of `/app/sign-in`, or
  the static server could intercept `/app`). The only proof is a live sign-in on
  `prism.chowmes.com/app` after deploy.

## Open items for the plan
- Identity upsert mechanism (webhook vs lazy).
- Whether `users` lands in this slice's migration or is created here and extended in Slice 2.
- Confirm `hermes-session.ts` carries the verified Clerk userId (not a placeholder).
- `basePath: '/app'` rollout — verify it doesn't break dev asset/route paths; test the full sign-in
  flow in dev with basePath set before deploying.
- Caddy route precedence vs the static prism-hub node server (`:8651`) — confirm `/app/*` reaches the
  Next service and nothing else does.
- `npm` vs `pnpm` on the VPS — package.json implies pnpm; only `npm` confirmed present. Decide
  install path (use npm, or install pnpm) in the plan.
