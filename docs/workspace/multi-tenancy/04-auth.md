# Multi-Tenant Auth + Report-Access Design (Clerk)

Status: RESEARCH — input to `docs/plans/multi-tenancy-architecture.md`, not yet built.
Scope: §5 of `docs/plans/2026-07-02-cassandra-airtight-pipeline-goal.md` — "auth (Clerk is already
in flight per memory)". This doc covers the auth/ACL slice only (concurrency, browser scaling,
per-tenant Cassandra sizing are out of scope — see the other `05-*` research files).

## 0. Ground truth read (don't re-derive)

- **Live gate today:** `~/prism/server/chat-proxy.mjs` (plain `node:http` server, systemd
  `prism-chat-proxy`, fronted by Caddy — NOT Next.js). Uses `@clerk/backend`'s
  `createClerkClient({ secretKey, publishableKey })` + `clerk.authenticateRequest(webRequest, {})`.
  `PUBLIC_EXACT` / `PUBLIC_PREFIXES` allowlist (`/`, `/about`, `/assets`, `/ia*`, `/api`) — anything
  else requires a signed-in session (fail-closed by default, fail-*open* only if `@clerk/backend`
  isn't installed or `CLERK_SECRET_KEY` is unset — a dev safety valve, not a prod stance).
- **Reports live at `/reports/<slug>/{index,ae-report,battle-card,leave-behind}.html` +
  `/reports/<slug>/screenshots/*`** (confirmed via `ls ~/prism/reports/`). Slug = single path
  segment after `/reports/`. `/reports/data/<slug>-audit-data.json` sidecar files also exist there.
- **Today's model is binary, not multi-tenant:** any signed-in user sees every report. There is no
  per-slug ACL anywhere in the stack.
- **A prior custom `User` table was built AND REVERTED** (commit `855000c`, memory + claude-mem
  observation 7751: deleted `alembic/versions/009_add_users.py`, `api/routers/users.py`,
  `tests/test_users.py`). Read as a decision, not an accident: **identity lives in Clerk, Postgres
  never re-implements a Users table.** Any ACL table this design adds stores Clerk's `user_id` as an
  opaque `text` foreign key — it does not mirror Clerk user records.
- **`prism_platform` Postgres already tracks audit ownership.** `db/models.py:87` —
  `Audit.user_id: Mapped[str]` (default `"system"`) — the rep who ran/owns a given audit is *already
  a column on an existing table*. Report-access default-grants should derive from this, not invent a
  parallel ownership concept.
- **claude-mem observation 9870 (2026-07-02, agent `R4-auth`)** independently surfaced a Hermes
  framework reference pattern — multiple Telegram bots per user via `(user_id, bot_token)` session
  routing — flagged as applicable to per-AE Cassandra binding. Relevant to §(d) below, but see the
  recommendation: it's more machinery than this problem needs right now.

## 1. The tenancy shape is NOT classic multi-org SaaS — say so explicitly

The plan doc (§5) frames this as "how does each of 20 AEs get their own Cassandra" and lists
"per-tenant Postgres schema/RLS vs per-tenant DB" as an open question. That framing assumes
**tenant = customer company**, the classic B2B SaaS shape Clerk Organizations is built for (Slack,
Linear: each customer gets an isolated workspace with its own membership).

That's not this problem. PRISM has **one vendor (Algolia), ~20 internal reps, and ~1 admin**, and the
resource being access-controlled is a *report* (one per prospect company), not a workspace. Two
reps at Algolia might both want visibility into the same account. This is an **internal tool with
row-level ACL on resources**, not multi-org SaaS. Recommending Clerk Organizations here would mean
standing up org-creation UI, membership management, and role/permission plumbing to solve a problem
that's really just "which of these 20 report slugs can this one user see" — a join table.

**Recommendation: skip Clerk Organizations for the internal AE/BDR/admin case.** Use one Clerk
application, a `role` field in `publicMetadata` (`admin` | `rep`), and a thin Postgres ACL table.
Keep this call revisitable: if PRISM is ever sold as external multi-org SaaS (a different company's
sales team using their own PRISM instance), Organizations become the right primitive then — this
doc's model does not block that pivot, it just doesn't build it before it's needed.

## 2. Recommended model

### 2.1 Identity + role (Clerk)
- One Clerk application (already provisioned). Each of the 20 AE/BDR users + Arijit is a normal
  Clerk user — no Organizations.
- `publicMetadata: { role: "admin" | "rep" }` set via Clerk Dashboard or a small admin script.
  `admin` (Arijit, maybe 1-2 sales leaders) sees every report; `rep` sees only what's granted.
- **Session token customization** (Clerk feature: Dashboard → Sessions → customize the JWT template)
  adds `role` as a claim on the session token itself, so `auth.sessionClaims.role` is readable from
  `authenticateRequest()`'s result with **zero extra Clerk API round-trips per request** — this
  matters because the gate runs on every GET to a report page and every chat POST.

### 2.2 Resource ACL (Postgres, on `prism_platform`)
New table, additive only — no changes to `Audit`/`Account`:

```sql
CREATE TABLE report_access (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    report_slug   text NOT NULL,          -- matches /reports/<slug>/ on prism-hub
    clerk_user_id text NOT NULL,          -- Clerk user_id, opaque FK (no Users table)
    granted_by    text,                   -- clerk_user_id of the admin who granted it, NULL if auto
    source        text NOT NULL DEFAULT 'manual',  -- 'audit_owner' | 'manual'
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (report_slug, clerk_user_id)
);
CREATE INDEX idx_report_access_user ON report_access (clerk_user_id);
```

- **Default grant, automatic:** when an audit completes for account X, insert a `source='audit_owner'`
  row from `audits.user_id` (already exists, `db/models.py:87`) mapped to the matching Clerk user
  (map by email or a small `AE ↔ Clerk user_id` static config — 20 people, doesn't need a dynamic
  sync). One rep runs the audit → that rep can see it, day one, no manual step.
- **Extra grants, manual:** admin adds rows for co-ownership, hand-offs, or "let the whole team see
  this one" — a single INSERT, or a 5-line admin CLI/endpoint. Not worth a UI at 20 users.
- **Admin bypass:** `role === "admin"` skips the table entirely (sees all slugs). Enforced in code,
  not by pre-populating every row for the admin.

### 2.3 Enforcement point — extend the existing gate, don't build a second one
`chat-proxy.mjs` already intercepts every request. Two additions to the *same* file:

```js
// after clerk.authenticateRequest() succeeds and auth.sessionClaims.role is known
async function authorizeReport(auth, reportSlug) {
  if (auth.role === "admin") return true;
  // internal loopback call to prism_platform (same pattern as the existing Hermes loopback
  // call in handleChat — one DB client, owned by prism_platform, not a second pg connection
  // bolted onto chat-proxy)
  const r = await fetch(`${PRISM_PLATFORM_URL}/internal/authz?slug=${reportSlug}&user_id=${auth.userId}`,
    { headers: { Authorization: `Bearer ${PRISM_PLATFORM_INTERNAL_KEY}` } });
  return r.ok && (await r.json()).allowed === true;
}

function reportSlugFromPath(url) {
  const m = /^\/reports\/([^/]+)\//.exec(url);
  return m ? m[1] : null;
}
```

- **GET/HEAD path** (existing block, `chat-proxy.mjs` bottom): after `checkAuth(req)` returns `ok`,
  additionally resolve `reportSlugFromPath(url)` — if it's a report path, call `authorizeReport`;
  on `false`, return **404** (not 403 — don't confirm the slug exists to an unauthorized viewer).
- **`POST /api/chat` — CONCRETE GAP FOUND, must fix regardless of Orgs-vs-metadata:** in the current
  dispatcher, `POST /api/chat` is matched and routed to `handleChat()` **before** the
  `if (req.method === "GET" || req.method === "HEAD")` gate block runs. `checkAuth()` is never called
  on the chat path at all — `/api` is also in `PUBLIC_PREFIXES`. Today, anyone who knows (or guesses)
  a report slug can `POST /api/chat` and get grounded answers about that report **with no Clerk
  session, no cookie check, nothing.** This is a real hole in the *current* single-tenant deployment,
  not just a multi-tenant gap — flag for a fix independent of this design's timeline. Fix: call
  `checkAuth(req)` + `authorizeReport(auth, reportSlug)` inside `handleChat()` before the upstream
  Hermes fetch, using the same two functions as the GET path (one gate, two entry points — don't let
  chat and page-serving diverge again).
- **`/reports/` index page stays static** (memory: PRISM hub is vanilla JS, no build step,
  `feedback-port-react-to-vanilla`) — it must NOT server-render a per-user filtered list, since that
  breaks the static-site model. Instead: add `GET /api/my-reports` (new gated JSON endpoint, calls
  the same `/internal/authz`-adjacent list query) and have `index.html`'s existing inline JS fetch it
  client-side to filter which report cards render. Unauthorized slugs are simply never sent to the
  browser, not hidden by CSS.

## 3. Prospect-facing external shares — signed URLs, not Clerk invitations

Checked Clerk's invitation model directly: **Clerk invitations require the invitee to end up with a
Clerk account** — `createOrganizationMembership()` still needs an existing Clerk user id, and the
standard invite flow redirects to Clerk's sign-up. There's no "guest, no account" primitive. Forcing
a prospect (a buyer at the audited company) to create a Clerk account just to view one report is the
wrong friction for an AE sending a link mid-deal — that's a DocSend/Loom-link UX, not a login UX.

**Recommendation: revocable, time-limited signed URLs, layered in front of the Clerk gate, not
replacing it.**

```sql
CREATE TABLE share_links (
    token         text PRIMARY KEY,       -- random, url-safe, 32+ bytes
    report_slug   text NOT NULL,
    created_by    text NOT NULL,          -- clerk_user_id of the AE who shared it
    expires_at    timestamptz NOT NULL,
    revoked_at    timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now()
);
```

- Use a **DB-backed token, not a stateless HMAC**. A pure HMAC(`slug + expiry`, secret) link can't be
  revoked before its expiry if a deal falls through or the link leaks — a DB row can, with one
  `UPDATE ... SET revoked_at = now()`. At this scale (dozens of shares, not millions), the DB lookup
  cost is irrelevant and revocability is worth it.
- Gate check order in `chat-proxy.mjs`: for a `/reports/<slug>/` request carrying `?share=<token>`,
  check `share_links` FIRST (valid, unexpired, unrevoked, slug matches) — if it passes, **serve
  read-only, no chat widget** (the chat widget POSTs to `/api/chat`, which still requires a real Clerk
  session under the fix in §2.3 — a share link should not grant grounded-chat access, only the static
  report view, to keep the blast radius of a leaked link small). If no valid share token, fall through
  to the normal Clerk `checkAuth` + `authorizeReport` path.
- AE-facing UX: a "Share with prospect" action (small admin/AE endpoint, `POST /internal/share-links`)
  that mints a token with a default 14-day expiry — no new AE-facing surface needed beyond copying a
  URL.

## 4. Telegram → tenant identity (no Clerk session exists there)

Telegram has no cookie/session — Cassandra needs another way to resolve "which rep is this" before
applying the same `report_access` check used on the web gate.

- **Do NOT reach for the Hermes multi-bot-per-user `(user_id, bot_token)` pattern found in claude-mem
  observation 9870.** That solves "give each AE their own bot," which is more infrastructure
  (20 bot tokens, gateway routing changes) than this problem needs. The actual requirement is just
  identity resolution + the same ACL check — one shared bot is fine.
- **Recommended: one-time `/link` flow.** Cassandra's Telegram handler supports a `/link <code>`
  command. The AE requests a short-lived code from a small web page (already behind the Clerk gate —
  reuses existing auth, no new login surface), pastes it into Telegram, and Cassandra writes a row to:

```sql
CREATE TABLE telegram_links (
    telegram_user_id bigint PRIMARY KEY,
    clerk_user_id     text NOT NULL,
    linked_at         timestamptz NOT NULL DEFAULT now()
);
```

- On every Telegram message, Cassandra looks up `telegram_user_id → clerk_user_id`, then calls the
  **same** `authorizeReport(auth, reportSlug)` logic the web gate uses (via the `/internal/authz`
  endpoint on `prism_platform` — one authorization function, two callers, matching the "one gate, two
  entry points" principle from §2.3). Unlinked Telegram users get a "message me `/link` first" reply,
  never a report answer.

## 5. Migration from today's single-tenant gate

1. Ship `report_access` + `share_links` + `telegram_links` tables via alembic migration on
   `prism_platform` (additive, no existing table touched).
2. Add `/internal/authz`, `/internal/my-reports`, `/internal/share-links` endpoints to
   `prism_platform` FastAPI (internal-only, bearer-keyed, loopback — same trust boundary as the
   existing Hermes 8642 / Scout 8421 loopback services per memory `project-prism-vps-executor`).
3. Backfill `report_access` for every existing published report from `audits.user_id` (defaulting
   unmapped/`"system"`-owned audits to admin-only until manually assigned — **fail closed**, the
   opposite of today's dev-mode fail-open-if-Clerk-unconfigured behavior, which should also be
   tightened or removed for the prod deployment as part of this change).
4. Set `publicMetadata.role` for all 20 users + configure the Clerk session-token JWT template to
   include `role`.
5. Patch `chat-proxy.mjs`: add `reportSlugFromPath`, `authorizeReport`, call both from the GET/HEAD
   gate AND from `handleChat()` (closing the gap in §2.3) AND from the new `/api/my-reports` handler.
6. Update `~/prism/index.html` / `/reports/index.html` inline JS to fetch `/api/my-reports` and render
   only visible cards (no server-rendered filtering — stays a static site).
7. Wire Cassandra's Telegram handler to the `/link` flow + the shared `authorizeReport` call.
8. Verification: Playwright test as two distinct Clerk test users (`rep-a`, `rep-b`) each granted a
   different single report — confirm `rep-a` gets 404 on `rep-b`'s slug via both the page GET and the
   `POST /api/chat` path, and that a `share_links` token serves the static page but the chat widget
   still 401s without a real session.

## 6. Cost

Clerk's 2026 Hobby/free plan covers 50,000 Monthly Retained Users and 100 Monthly Active
Organizations for $0/mo — 20 internal users plus a handful of time-boxed prospect shares (which don't
even touch Clerk, per §3) is nowhere near either ceiling. **Cost is not a factor in the
Organizations-vs-flat-role decision** — the recommendation in §1 is purely about matching the
architecture to the actual access-control shape, not about avoiding Clerk's org pricing.

## 7. Open questions for the gated design review

- Static AE↔Clerk-user-id mapping for the audit-owner auto-grant (§2.2): hand-maintained config file,
  or pull from an existing roster (SFDC?) — 20 people, either is fine, pick the one with less upkeep.
- Should `share_links` also log access (who/when opened) for AE follow-up visibility? Cheap add
  (`share_link_views` table) if wanted — not required for v1.
- **Resolved, not open (verified by running `isPublicPath` from `chat-proxy.mjs` directly):**
  `/reports/data/<slug>-audit-data.json` is already caught by today's binary gate (`isPublicPath(...)`
  returns `false` for it — it matches none of `PUBLIC_EXACT`/`PUBLIC_PREFIXES`). It needs the *same*
  slug-scoped `authorizeReport` upgrade as every other `/reports/<slug>/...` path (§2.3), but there is
  no separate pre-existing leak to fix here — just extend the one check to cover it too.
