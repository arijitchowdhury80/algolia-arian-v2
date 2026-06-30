# Slice 1 — Unify the site under the authed Next app (public landing + Google login + gated audits)

**Date:** 2026-06-30 (revised after scope change: Next owns the root)
**Status:** Design — pending user review → writing-plans
**Depends on:** nothing (foundation slice)
**Unblocks:** Slice 2 (per-user multi-tenancy / ACL) — see `2026-06-30-slice2-multitenancy-acl-design.md`

## Goal

Make the Next.js app the entire front door for `prism.chowmes.com`:
- **`/` is a public landing page** (the existing static About splash, served as-is).
- **Google login** ("Continue with Google", a Clerk dashboard toggle).
- **All audit reports + chat are behind login** (blanket gate: any logged-in user can see them; per-user ACL is Slice 2).
- Each authenticated Clerk user is persisted into a `users` table as the durable tenant key.

The static-site-at-root serving is **retired** (cutover): the Next service serves the whole domain.

## Boundary (explicit, per user's "don't put everything behind login")

| Route | Serving | Auth |
|-------|---------|------|
| `/` (landing / About splash) | existing static `index.html` copied into `public/` + a `next.config` rewrite | **Public** |
| `/assets/*`, `/chat-widget.js`, `/sign-in` | `public/` static + Clerk | **Public** |
| `/reports`, `/reports/<slug>/...` (report HTML + screenshots) | gated catch-all route handler streaming from a report-data dir, with its own `auth()` check | **Login** |
| `/api/report-chat` | new Clerk-gated handler = static `api/chat.js` logic (slug → Hermes) | **Login** |
| `/chat` + dashboard, `/api/hermes` | existing | **Login** |
| `/api/chat` (aRRIe LLM tools), `/demo` | existing | as-is (`/demo` public) |

## Three integration landmines (designed around, from the codebase map)

1. **Two different `/api/chat` collide.** The static report `chat-widget.js` POSTs `/api/chat` expecting a *Hermes grounded-proxy* (static `~/prism-hub/api/chat.js`: `slug → /v1/responses`). The Next app **already has** an `/api/chat` that is a different aRRIe LLM-tools handler. Reusing it would break report grounding. **Fix:** new gated `/api/report-chat` replicating `api/chat.js`, and repoint the widget to it.
2. **Dotted paths bypass Clerk middleware.** The middleware matcher (`middleware.ts:19`) skips any path containing a `.`. So report **screenshots (.png)** and **chat-widget.js** are *not* gated by middleware. **The report route handler MUST do its own `auth()` check** — this is load-bearing, or screenshots leak to anonymous users.
3. **Reports live at root slugs today** (`/petsmart/`, not `/reports/petsmart/`; map confirms 10 report dirs + `reports/index.html` hardcoded grid). Moving in, namespace under gated `/reports/<slug>/` to avoid colliding with app routes; build a small gated report-list; and fix the widget's slug extraction (`chat-widget.js:18` reads `pathname.split("/")[0]`, which becomes "reports").

Other notes: `audit-data.json` is read **server-side by Hermes** (`REPORTS_DIR=/opt/data/reports`), not client-side, so Next serves only report HTML + screenshots. The public landing also loads `chat-widget.js`, so its chat 401s for anonymous visitors (acceptable under blanket gate; revisit in Slice 2).

## Report serving mechanism

- Report HTML + assets are **not committed to git** (~14 MB). They are **synced at deploy time** into a directory the Next service reads, addressed by `REPORTS_HTML_DIR` (default a small local dir in dev).
- `app/reports/[[...slug]]/route.ts`: `auth()` gate → resolve the requested path **safely under `REPORTS_HTML_DIR`** (path-traversal guard) → stream the file with the right `Content-Type`. Serves `/reports/<slug>/index.html` and `/reports/<slug>/screenshots/*.png`.
- Report assets referenced at root (`/chat-widget.js`, `/assets/*`) live in `public/` (public; not sensitive). Only report HTML + screenshots are gated.
- Report list: a gated server component listing `REPORTS_HTML_DIR` subdirs → links `/reports/<slug>/`.

## Report chat (kept working)

- `app/api/report-chat/route.ts`: Clerk-gated port of `api/chat.js`. Reads `{message, slug, sid}`; builds `X-Hermes-Session-Key = agent:main:prism:web:<sid>:acct:<reportSlug>`; tags input `[Account: <slug>]`; proxies `POST $HERMES_API_URL/v1/responses` (bearer server-side); streams plain-text deltas. Uses the Web `Response`/`ReadableStream` form (like `app/api/hermes/route.ts`), not Node `res.write`.
- Copy `chat-widget.js` into `public/`, modified: endpoint `/api/chat` → `/api/report-chat`; slug extraction handles `/reports/<slug>/`.

## Identity capture (unchanged from the original slice)

- `users` table (`id` = Clerk userId PK, `email`, `name`, `org_id` nullable — org-ready seam).
- `POST /api/v1/users/upsert` (loopback-only on `127.0.0.1:8000`, idempotent).
- Server-side `syncUser()` mirrors the Clerk-verified user into the backend on authed load.
- Blanket gate now; per-user ACL is Slice 2. Identity is captured now so Slice 2 has the tenant key.

## Deployment (VPS, cutover)

- `prism-frontend.service` (systemd + `next start -H 127.0.0.1 -p 3000`). **No basePath** (app owns root).
- Caddy: `prism.chowmes.com` → `reverse_proxy 127.0.0.1:3000` for the **whole domain**. Retire the static-root node serving (`:8651`) for this domain.
- Deploy-time: sync the 10 report dirs + `/assets` + `chat-widget.js` into the app's `REPORTS_HTML_DIR` / `public/`. The report-source pipeline (prism-hub GitHub auto-deploy) must feed `REPORTS_HTML_DIR`.
- Service env: Clerk **prod** keys, the `NEXT_PUBLIC_CLERK_*` path vars, `PRISM_API_URL=http://127.0.0.1:8000`, `HERMES_API_URL` + `HERMES_API_KEY`, `REPORTS_HTML_DIR`. `BYPASS_AUTH` **unset**.

## Verified facts (carried from pre-design probes, 2026-06-30)

- FastAPI live on `127.0.0.1:8000` (`/health`=200); loopback reachable from on-box callers (proven by the report-qa plugin already calling it).
- `uvicorn` single async process; concurrency for ~10 users is a non-issue.
- Alembic head = `008`; next revision `009`.
- `create_audit` (`audits.py:113`) defaults `user_id="system"`; that becomes a real FK in Slice 2.
- Next app is a server app (no static export); `next.config.ts` currently only sets `devIndicators:false`.

## Validation risk surface

- **Dev verification proves:** the route map, the gate (anonymous blocked from `/reports/*` and `/api/report-chat`), the public landing, and report chat grounding all work locally.
- **It does NOT prove:** the production cutover (Caddy root → `:3000` replacing the static serve), prod Google OAuth, or that the report-source pipeline correctly feeds `REPORTS_HTML_DIR`. Those are only proven by the live verification on `prism.chowmes.com` after deploy.
- **Remaining risk:** the cutover is destructive to the current public serving. Keep a rollback (Caddy can re-point to `:8651` instantly). Dotted-path bypass means the handler `auth()` check is the only thing gating screenshots — test an anonymous screenshot fetch returns 401/redirect.

## Out of scope (Slice 2)
Per-user audit visibility (Rob sees only Rob's), the `can_user_see()` ACL, identity-driven Hermes binding (+ its runtime probe), per-audit reports, audit-ownership stamping.
