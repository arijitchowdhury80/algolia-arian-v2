# SESSION — Login gate on prism.chowmes.com/reports (Clerk Google)

**Status:** Login gate DONE + working locally + pushed (feature branches, NOT deployed). This session's task was: gate `prism.chowmes.com/reports` behind Google login, keep `/` public. Done at the EXISTING prism-hub server (a wrong Next.js rebuild was tried, then abandoned + deleted).

Date: 2026-06-30 (late). Full detail: memory `project-prism-login-multitenancy`. Other open tracks (artifacts, IA prototype) live in memory `session_pointer`.

## RESUME ACTION (next session, do FIRST)
1. Read memory `project-prism-login-multitenancy` (the whole state) + `feedback-gate-existing-dont-rebuild` (the lesson).
2. The remaining work is the **VPS deploy** of the gate (deferred, user-approved as a future step). Steps in the memory file: `npm install @clerk/backend` on `/opt/prism-hub`; set Clerk keys in the chat-proxy service env; restart it; create a Clerk **PRODUCTION** instance for `prism.chowmes.com` + point clerk-js at it; get the code onto `/opt/prism-hub` (auto-deploy branch is `feat/prism-vps-hosting`, current work is on `feat/ia-ab-prototype`); verify live.
3. Do NOT rebuild anything. The gate is ~80 lines in `~/prism-hub/server/chat-proxy.mjs`.

## WHAT WAS DONE
- **Gate:** `~/prism-hub/server/chat-proxy.mjs` — public allowlist (`/`, `/about`, `/assets`, `/ia*`, `/api`, `/chat-widget.js`, `/sign-in`, `/healthz`); everything else (`/reports` + report slugs) requires a Clerk session (`@clerk/backend`, resilient/fail-open import). `/sign-in` page = clerk-js `<SignIn>`.
- **Auth control:** `~/prism-hub/index.html` topbar — Sign in link / avatar+Sign out (clerk-js).
- **Clerk:** Algolia-account app `app_3Frh5zKzvYMFRRkn94e0J7ylX3y`; dev keys in `PIP/.env.local` (consolidated; `frontend/.env.local` is a SYMLINK to it); `BYPASS_AUTH`/`NEXT_PUBLIC_BYPASS_AUTH`=false.
- **Verified local:** server on `localhost:8651` (run: `STATIC_DIR=~/prism-hub PORT=8651 CLERK_SECRET_KEY=.. CLERK_PUBLISHABLE_KEY=.. node server/chat-proxy.mjs`). Gate proven (curl `/`=200, `/reports/`=302→/sign-in). User confirmed Google login + avatar/Sign-out in browser.
- **TOC bug fixed:** removed the `@media(max-width:1200px){#section-sidebar{display:none}}` rule AND the JS `if(activeTabId==='overview'){hide}` special-case, in 17 reports + templates.
- **Cleanup:** deleted the abandoned Next.js site-rebuild + the unused `prism_platform` users table/migration/endpoint (design docs kept).
- **Pushed:** prism-hub `feat/ia-ab-prototype`; arijit-skills `feat/gemini-grounded-search`; PIP `feat/prism-e2e-cycle`.

## WHAT HAS NOT BEEN DONE (no false claims)
- The gate is **NOT live** on prism.chowmes.com (pushed to a non-deploy branch; VPS not prepped). Live site unchanged.
- Clerk **production** instance for prism.chowmes.com: NOT created (dev keys only work on Clerk's dev domain).
- Local **chat** is unavailable (public Hermes endpoint 404s; no loopback locally) — works on the VPS, not a regression.
- Per-user multi-tenancy/ACL: NOT built (design docs only).
- A local prism-hub server may still be running (nohup) on :8651.

## KEY FILES
- `~/prism-hub/server/chat-proxy.mjs` (the gate), `~/prism-hub/index.html` (auth control)
- `PIP/.env.local` (Clerk + other keys; frontend/.env.local symlinks here)
- Templates: `~/.claude/skills/algolia-search-audit/templates/{index-template.html,algolia-brand.css}`
- Lesson: memory `feedback-gate-existing-dont-rebuild`. Standing rule: no em dashes.
