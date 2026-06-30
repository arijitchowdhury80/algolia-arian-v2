# Slice 1 — Google login + deploy + identity capture

**Date:** 2026-06-30
**Status:** Design — pending user review → writing-plans
**Depends on:** nothing (foundation slice)
**Unblocks:** Slice 2 (multi-tenancy / ACL) — see `2026-06-30-slice2-multitenancy-acl-design.md`

## Goal

A visitor hits the deployed Next.js app, lands on `/sign-in`, clicks **Continue with Google**,
authenticates, and lands on `/chat`. Any Google account is allowed. The authenticated Clerk
userId is captured and persisted as the **tenant key** so Slice 2's ACL has a clean foundation.

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
2. **Deploy `frontend/` to Vercel** with Clerk **production** keys, `BYPASS_AUTH` unset.
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
| 4 | Deploy `frontend/` to Vercel; set Clerk prod env; `BYPASS_AUTH` unset | User + Claude | Repo not linked to Vercel yet; Claude preps config, user authorizes deploy |
| 5 | **Verify** Google sign-in end-to-end (dev → prod URL) | Claude | Evidence, not assertion |

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

- **`BYPASS_AUTH` must never be set in the Vercel prod environment.** It is read at
  `middleware.ts:10` and `layout.tsx:18`; if set, it disables auth entirely. The deploy checklist
  must assert it is unset.
- The Clerk **secret key** and (later) the Hermes API key stay server-side only — never
  `NEXT_PUBLIC_*`.

## Validation risk surface

- **What dev verification proves:** the code path + sign-in flow are correct (Google button
  appears, OAuth round-trips, user lands on `/chat`).
- **What it does NOT prove:** production Google OAuth. That is only proven once the prod Clerk
  instance + your Google prod OAuth client + the deployed domain are live and sign-in is tested
  against the real URL.
- **Remaining risk:** prod-only OAuth redirect/origin misconfig. The only proof is a live sign-in
  on the deployed domain — steps 1–4, which are user-owned.

## Open items for the plan
- Identity upsert mechanism (webhook vs lazy).
- Whether `users` lands in this slice's migration or is created here and extended in Slice 2.
- Confirm `hermes-session.ts` carries the verified Clerk userId (not a placeholder).
