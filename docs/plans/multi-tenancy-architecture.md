# PRISM Multi-Tenancy Architecture — Decision-Grade Design

**Part 2 of the airtight-pipeline goal** (`docs/plans/2026-07-02-cassandra-airtight-pipeline-goal.md` §5). This is the DESIGN artifact for Arijit's gated review. Nothing here is built yet. It synthesizes six research passes (`docs/workspace/multi-tenancy/01–06`); every load-bearing claim cites its source doc, and every source doc carries its own external citations.

**Author:** synthesis agent (Opus tier), 2026-07-02
**Status:** DRAFT for gated review. BUILD does not start until (1) Arijit signs off on this doc AND (2) Part 1's Belk proof passes AND (3) the one empirical test in the boxed callout below has run.

---

## BLUF — the recommended architecture in six bullets

1. **One shared Hermes daemon, not 20 containers.** Cassandra stays a single process; tenancy is enforced in *code and data*, never by spinning up per-tenant infrastructure. Container-per-tenant is disqualified by arithmetic — 20 × ~1G baseline blows an 8G box that already runs 7 containers (`01-hermes-tenancy` §2–3). The "hybrid" tax is entirely code, not hardware.
2. **A single hard `tenant_id`, derived once at session start, is the spine of the whole design.** The report-binding bug, the data-isolation model, and the auth layer are not three problems — they are one. All three want the same tenant key, resolved at session start and carried through every hook, query, and tool call. This is the central unifying decision (see "The one decision" below).
3. **Data isolation = a `tenant_id` column filtered in the app layer, not Postgres RLS — yet.** The column already exists (`Audit.user_id`, defaulted `"system"`, 0 rows today). Ship app-layer filtering through one shared query helper now; RLS is the documented, triggered upgrade for when the data goes customer-facing or a real connection pooler appears (`03-data-isolation` §32–37).
4. **Auth = one Clerk app + a role claim + a thin ACL table, not Clerk Organizations.** This is an internal tool with row-level ACL on report resources, not multi-org SaaS. Prospect shares use revocable signed URLs, not forced Clerk accounts. Telegram identity resolves via a one-time `/link` flow (`04-auth` §1–4).
5. **"20 parallel audits" is a queue-depth problem, not a 20-processes-at-once problem.** Build a bounded Redis/`arq` worker pool (start at 3) with Postgres as state-of-record, per-tenant fairness (max 2/tenant), and a hard per-job timeout that does not exist today. Real parallelism is gated by the Claude subscription, not the box (`02-concurrency`, `05-breakpoints-cost`).
6. **External data (SimilarWeb HITL, bot-walls) does NOT scale with tenant count.** One shared same-IP login, serialized behind a queue, covers 1 through 20 tenants — the session is time-lived, not query-lived. Bot-wall detect+flag is $0 per-audit data (`05-breakpoints-cost` §1, `06-peer-research` §B–C).

**The single biggest open risk:** the Claude subscription's account-level pooled rate limit is the real ceiling on parallelism, and the goal plan's cost model (§9: "an audit costs ≈ subscription + pennies") is **unverified at concurrency**. If one Max 20x subscription cannot sustain 3+ concurrent `claude -p` audits, the cost curve stops being "$10–120/mo" and starts being "$400–800/mo in subscription seats." This must be tested empirically before Part 2 build commits to any concurrency number (`02-concurrency` §4, `05-breakpoints-cost` §2 Rank 1).

---

> ## ⚠️ FIX THIS REGARDLESS OF MULTI-TENANCY — live security gap
>
> **`POST /api/chat` is unauthenticated today.** In `~/prism/server/chat-proxy.mjs`, the chat route is matched and dispatched to `handleChat()` *before* the GET/HEAD auth gate runs, and `/api` is in `PUBLIC_PREFIXES`. Anyone who knows or guesses a report slug can POST to `/api/chat` and get grounded answers about that report with **no Clerk session, no cookie, nothing** (`04-auth` §2.3).
>
> This is a hole in the *current single-tenant* production deployment. It is independent of everything else in this doc and should be patched now, not waited on behind the Part 2 build. **Fix:** call `checkAuth(req)` + `authorizeReport(auth, reportSlug)` inside `handleChat()` before the upstream Hermes fetch — the same two functions the page-serving path will use (one gate, two entry points).
>
> Related, same file, same spirit: the dev-mode "fail open if Clerk unconfigured" behavior should be tightened or removed for prod, and `/reports/data/<slug>-audit-data.json` sidecars need the same slug-scoped check as report pages (`04-auth` §0, §7).

---

> ## 🔬 RUN THIS TEST BEFORE BUILDING PART 2 — the concurrency unknown
>
> **The #1 thing gated on evidence.** The goal plan states runtime cost ≈ subscription + pennies (§9). That is true for *one audit at a time*. It is very likely NOT true at concurrency, and the reason is architectural, not a pricing nuance: every `claude -p` session on one account **shares a single pooled rate-limit budget**, plus there is a reported hard *burst* wall where firing many session-starts at once on one account rejects the excess with 529 errors even under the usage cap (`02-concurrency` §4, sources: GitHub anthropics/claude-code#53922, #68502).
>
> **Exact test:** on the real Max 20x subscription, fire **2–3 concurrent `claude -p` audit sessions** (staggered by a few seconds, then simultaneous) and watch for throttling / 529 / "temporarily limiting requests." Measure how many run cleanly in parallel, and instrument active-compute-time (or token count as a proxy) per audit to size a sustainable weekly volume.
>
> **Why it gates the build:** the answer sets the worker-pool depth (§ Concurrency below), decides whether a 2nd subscription / API-overflow path is needed, and determines whether the cost curve is the cheap one or the expensive one. Do not finalize the concurrency design or the cost model until this number is real.

---

## The one decision that ties three research threads together

Three of the six research passes independently converged on the **same** missing primitive. Presented separately they look like three tickets; they are one.

| Thread (source doc) | How it shows up | What it actually needs |
|---|---|---|
| **Report-binding bug** (`01-hermes-tenancy` §crux) | Cassandra binds a chat session to a report by *content-matching the user's message* (`_BINDINGS[session_id]`), not by a hard key. At N=1 it's a UX nuisance; at N=20 sharing one Cassandra it's a **data-leakage bug** — AE Alice could get AE Bob's audit if her message content-matches his bound report. | A hard tenant key on every session, resolved at session start, never re-derived mid-conversation by content. |
| **Data isolation** (`03-data-isolation`) | `Audit.user_id` exists but is unpopulated (defaults `"system"`). Every tenant-scoped query needs a `WHERE user_id = :tenant` filter that nothing enforces yet. | The same tenant key, populated into `audits.user_id` and filtered through one shared query helper. |
| **Auth** (`04-auth`) | Web sessions have a Clerk `user_id`; Telegram sessions have none; today any signed-in user sees every report. The gate needs to know *who* is asking to decide *what* they may see. | The same tenant key — Clerk `user_id` on web, resolved via `/link` on Telegram — feeding an ACL check. |

**The unifying decision:** define **one tenant identity — the Clerk `user_id` (string)** — and thread it through every layer:

- **Session start** resolves it once: web = Clerk session claim; Telegram = `telegram_user_id → clerk_user_id` via the `/link` table; CLI = configured. It is carried on the session object, **never re-derived by message content** (this is the direct kill for the binding bug).
- **Data layer** stores it in `audits.user_id` (already the column) and every scoped read/write goes through **one shared repository helper** that filters on it (`03-data-isolation` §57).
- **Auth layer** uses it as the ACL subject: `report_access.clerk_user_id` decides which slugs this tenant may see (`04-auth` §2.2).

Fixing the binding bug is therefore not a separate chore — it is step one of the data-isolation build, and the precondition for auth. Do it **before** onboarding a second tenant, and it pays off even at N=1 (it's a latent correctness bug today). One key, three payoffs.

---

## Axis (a) — How 20 AEs each get "their own Cassandra"

**Recommendation: Model C — one shared Hermes daemon, hard per-tenant partitions in code + DB, one Telegram bot with forum-topic routing per tenant.** (`01-hermes-tenancy` §6.)

Not a compromise pick. An unrelated open-source multi-agent Telegram framework (`NousResearch/hermes-agent`, issues #9514 and #8287) independently converged on the same design — one gateway daemon, per-topic workspace isolation, `10x resource savings vs. one-process-per-agent` — which is external validation, not just first-principles reasoning (`01-hermes-tenancy` §5).

| Model | Verdict | Why |
|---|---|---|
| **A — container per tenant** | Rejected | 20 × ~1G baseline = **8–15G+** of idle agent processes on an 8G box already running 7 containers. Fails at deploy time, not gracefully. Also hits BotFather's 20-bot ceiling (40 w/ Premium) with zero headroom. Reconsider only if a future requirement demands genuinely divergent per-tenant SOULs or contractual physical isolation — neither is true today. |
| **B — shared instance, session-only isolation** | Rejected | Closest to today, and cheapest to bolt on — but it scales the binding bug by 20×. "Isolation" here is hope, not architecture; Part 1's whole point was to replace hope with architecture. |
| **C — hybrid: shared daemon, hard tenant partitions** | **Recommended** | Keeps B's RAM/CPU/ops profile (~2–4G at 20 tenants, one thing to operate) while enforcing tenancy as a first-class key in code + data. Gets "one voice, N data scopes" exactly right — Arijit's spec is one Cassandra personality, not 20 (`01-hermes-tenancy` §2, §4C). |

**Concretely, Model C means:**
- **Hard tenant key** on every session (the unifying decision above).
- **Per-tenant memory/state:** per-tenant sqlite directories `/root/.hermes-prism/tenants/<slug>/*.db` — a small, mechanical change from today's flat layout. sqlite files are cheap; disk is not the constraint (30G free).
- **One shared knowledge base:** the Algolia sales-knowledge tables (case studies, quotes, gaps) stay global, read by every tenant — extend the existing pattern, don't partition it (`03-data-isolation` §11).
- **One Telegram bot, forum-topic routing** (`(chat_id, topic_id) → tenant_id`) instead of 20 bot tokens — avoids the BotFather ceiling, gives each AE a distinct thread that reads like "my Cassandra." Keep per-bot-token routing (`01` §5, issue #8287) as a documented fallback only if topic-routing feels insufficiently "theirs" — don't build it preemptively.

**Trade-off stated honestly:** Model C does **not** give OS-level crash isolation. One bad deploy or one runaway tool call can degrade all 20 tenants at once (a real SPOF). Mitigate with a hot-reload / per-tenant-workspace-reload path (the NousResearch Phase-4 pattern), not by re-introducing 20 processes. This matches today's N=1 reality (one Cassandra, one failure domain), so it is an accepted risk to carry, not a regression — revisit only if uptime SLAs or compliance change (`01-hermes-tenancy` §6.6). **What we are NOT solving here:** crash isolation, and per-tenant CPU contention (that's the concurrency axis, below — don't conflate a memory/data-isolation problem with a CPU-scheduling one).

---

## Axis (b) — How 20 parallel audits run

**Recommendation: a bounded Redis + `arq` worker pool (start at 3 workers), with Postgres as the state system-of-record.** (`02-concurrency` §2, §7.)

The runner today has **no queue at all**: `POST /run` fires an *unbounded daemon thread per request*. Two callers both start immediately; twenty would all launch `claude -p` + Chrome simultaneously and OOM/CPU-starve the box (`02-concurrency` §2). This must change regardless of tenancy model — it is the actual root gap.

**Two independent ceilings — the second is the real one:**

1. **Box ceiling (fixable with money): ~3 concurrent audits** on the current 2 vCPU / 8G VPS. Set by Chrome + `claude -p` RAM (~1–2G/audit) and CPU contention, not by anything architectural. Critically, over-packing CPU *increases the odds of the known screenshot-timing bug class* (goal plan §3.1c) — slow renders under contention produce false factcheck failures. So ~3 is a correctness number, not just a resource one (`02-concurrency` §1).
2. **Subscription ceiling (NOT fixable with box money):** one Claude account's pooled rate limit is shared across every session — see the boxed test above. Adding boxes does nothing if they all authenticate as the same subscription.

**Queue tech — why Redis/`arq` over the alternatives:**

| Option | Verdict | Reason |
|---|---|---|
| A — Postgres-table queue | Viable, not chosen | Zero new infra (Part 1 already puts job state in Postgres), but you hand-roll retry/backoff/dead-letter/heartbeat, and multi-box scale-out means reinventing distributed-queue plumbing on a relational table. |
| **B — Redis + `arq`** | **Recommended** | Redis is already deployed and idle. Retry/timeout/dead-letter come from the library. Workers are location-independent → this IS the multi-box on-ramp with no redesign, just more workers pointed at the same `REDIS_URL`. Postgres stays state-of-record; Redis is transient work-queue only — clean separation, not two sources of truth. |
| C — Temporal | Rejected | Already judged overkill and recorded in memory (`feedback-heavy-orchestrator-overkill`). What's needed — bounded concurrency, retry, fairness — is a queue, not a durable-execution engine. Honest exception: revisit only if a later phase needs cross-service saga orchestration (audit + billing + compensating rollback), which "run more audits in parallel" does not. |

**Ship with the queue on day one (not reactively):**
- **Per-tenant fair dispatch** — round-robin across tenants with pending work, not global FIFO, so one AE queuing 10 audits doesn't starve everyone (`02-concurrency` §5).
- **Hard cap: max 2 concurrent audits per tenant**, regardless of total worker capacity.
- **Hard per-job wall-clock timeout** (e.g., 2× observed p95) that kills the subprocess and marks `NEEDS_HUMAN`. **This does not exist today** — `run_job()` polls `proc.poll()` with no timeout; a hung `claude -p` or a Chrome stuck on a bot-wall interstitial blocks that worker slot *forever*. Genuine live gap (`02-concurrency` §6).
- **Zombie-Chrome reaper** — periodic `pkill` of orphaned Chrome older than N minutes, cheap insurance against RAM leak across cycles.

**Multi-box scale-out** (only when measured queue-wait breaches SLA at the 3–4-worker ceiling, not on a hunch): add cheap Hostinger worker boxes each running an `arq` worker pointed at the same Redis + Postgres. **Carry-forward complication:** the SimilarWeb same-IP-login flow breaks if audits spread across N egress IPs — centralize the SimilarWeb step on one designated box/egress regardless of which box runs the rest of that audit (`02-concurrency` §3).

---

## Axis (c) — Tenant data isolation

**Recommendation: a `tenant_id` column enforced in the app layer through one shared query helper. NOT Postgres RLS yet — but RLS is a documented, triggered upgrade, not a silent skip.** (`03-data-isolation` §32.)

The four options, evaluated at *this* scale (20 internal, trusted Algolia reps; data = Algolia's own sales research on public prospects; leaking AE-Y's Belk audit to AE-X is an annoyance, not a breach):

| Option | Verdict |
|---|---|
| (a) shared schema + `tenant_id` + **RLS** | Correct in spirit, wrong first move. RLS is net-new plumbing (a new non-owner app role — because `prism` currently both owns tables and is the app role, so RLS is a **silent no-op** as deployed — plus `SET LOCAL` event listeners, per-table policies, cross-tenant tests) for a non-adversarial threat model. The scariest RLS footgun (pooler reassigning a backend mid-`SET LOCAL`) doesn't apply today because there's **no pooler** (`NullPool`, one connection per request) — but that also means the setup isn't RLS-ready. |
| (b) schema-per-tenant | Rejected — Alembic doesn't do per-schema migrations cleanly; 20× migration surface for zero isolation benefit; shared Algolia tables would need a 21st "public" schema anyway. |
| (c) database-per-tenant | Rejected — cross-DB reads of the shared knowledge tables need `postgres_fdw`/`dblink` × 20; 20× backup/connection overhead for sub-1MB data. Revisit only for contractual data-residency, which no tenant needs. |
| **(d) `tenant_id` column, app-layer enforced** | **Recommended for V1** — reuses the column already sitting there, ships fast, matches the actual trust model. |

**The concrete change (`03-data-isolation` §38–57):**
- `audits.user_id` **becomes the tenant key immediately** — it already exists (`Text, NOT NULL`, default `"system"`). Add index `idx_audits_user_id` (migration 009). No column migration needed.
- Tenant identity = **Clerk `user_id` string** stored directly in `audits.user_id` — no separate `tenants` table until there's a real second attribute to hang off it (plan, seat count, team roster).
- **`accounts` stays global, unscoped.** `domain` is already globally unique by design — two AEs auditing Belk hit the *same* company-facts row (dedup, faster second audit). Tenant-scope the *work product* (the audit: score, findings, deliverables), not the *facts* (Belk's HQ, headcount — true regardless of who asks).
- **`module_executions` / `deliverables` need no `tenant_id` of their own** — both FK to `audit_id` (CASCADE); scope them by **joining through `audits.user_id`** in the one shared helper.
- **One shared enforcement point**, not per-route filtering — the `WHERE ... = tenant` clause lives in exactly one repository function every route calls. That's the mitigation for app-layer blast radius, plus one integration test ("tenant A cannot read tenant B's audit") that must exist regardless of (a) vs (d) — RLS can be misconfigured just as easily.

**The trade-off, stated:** a missed `WHERE user_id = :tenant` in a new route lets one AE list another's audits. Mitigated by the single shared helper + the cross-tenant test + a `code-review`/grep check that any new query against `audits`/`module_executions`/`deliverables` routes through the helper. The blast radius if hit is "an internal employee sees another internal employee's research on a public company" — not customer PII, not a compliance event. That is precisely why (d) is defensible for V1 in a way it would not be for a customer-facing product.

**The RLS trigger — written down so it isn't rediscovered from scratch:** build (a) properly (new low-privilege app role + `SET LOCAL` + policies + cross-tenant read test — roughly a half-day on top of the same `tenant_id` column) the day **either** PRISM audit data becomes visible outside Algolia (prospect portal, partner integration, trust-model change) **or** the DB moves behind a real connection pooler (e.g., a managed-PG migration to RDS/Neon/Supabase, which also reopens the asyncpg `SET LOCAL` / prepared-statement risk). Bundle the RLS work with the pooler-safety work; don't do both blind at once (`03-data-isolation` §74–79).

---

## Axis (d) — Clerk multi-tenant auth

**Recommendation: one Clerk application + a `role` claim in `publicMetadata` + a thin Postgres ACL table. Skip Clerk Organizations.** (`04-auth` §1–2.)

**Why not Organizations:** the plan framed this as "tenant = customer company," the classic multi-org SaaS shape Orgs are built for. That's not this problem. PRISM is **one vendor (Algolia), ~20 internal reps, ~1 admin**, and the access-controlled resource is a *report*, not a workspace. Two reps may both want the same account. This is an **internal tool with row-level ACL on resources** — a join table, not org-creation UI + membership management + permission plumbing. Keep the call revisitable: if PRISM is ever sold as external multi-org SaaS, Orgs become right *then*; this model doesn't block that pivot (`04-auth` §1). Note also a prior custom `User` table was built AND reverted (commit `855000c`) — **identity lives in Clerk; Postgres never re-implements Users.** Any ACL table stores Clerk's `user_id` as an opaque text FK (`04-auth` §0).

**The model (`04-auth` §2):**
- **Identity + role:** each of 20 reps + Arijit is a normal Clerk user. `publicMetadata: { role: "admin" | "rep" }`. Customize the Clerk session-token JWT template to carry `role` as a claim → readable from `authenticateRequest()` with **zero extra Clerk API round-trips per request** (matters — the gate runs on every report GET and chat POST).
- **Resource ACL table** `report_access (report_slug, clerk_user_id, source, granted_by, ...)`, additive, no changes to `Audit`/`Account`. **Auto-grant** on audit completion from `audits.user_id` (`source='audit_owner'`) → the rep who ran it sees it day one, no manual step. **Manual grants** (co-ownership, hand-off, "whole team") = one INSERT. **Admin bypass** in code (`role === "admin"` skips the table).
- **One gate, two entry points:** extend the existing `chat-proxy.mjs` gate — add `reportSlugFromPath()` + `authorizeReport()`, call from the GET/HEAD path (return **404** not 403 on deny — don't confirm the slug exists) AND from `handleChat()` (this closes the live security gap in the boxed callout). The `/reports/` index stays static — add a gated `GET /api/my-reports` JSON endpoint that the inline JS fetches to render only visible cards (no server-rendered filtering — keeps the vanilla static-site model).
- **Prospect shares = revocable signed URLs, not Clerk invitations.** Clerk invites force the invitee to create a Clerk account — wrong friction for an AE sending a link mid-deal (that's a DocSend UX, not a login UX). Use a **DB-backed token** (`share_links` table, not stateless HMAC, so it's revocable before expiry), default 14-day expiry, serves the **static report read-only with no chat widget** — a leaked link never grants grounded-chat access (`04-auth` §3).
- **Telegram identity = one-time `/link` flow.** No cookie/session exists on Telegram. AE requests a short code from a Clerk-gated web page, pastes `/link <code>` to Cassandra, who writes `telegram_links (telegram_user_id → clerk_user_id)`. Every Telegram message then resolves identity and calls the **same** `authorizeReport` logic as the web gate. Do NOT reach for the multi-bot-per-user pattern — one shared bot is fine (`04-auth` §4).

**Cost:** Clerk's free tier (50K Monthly Retained Users) covers 20 internal users plus time-boxed prospect shares (which don't touch Clerk) with enormous margin. Cost is not a factor in the Orgs-vs-flat-role decision — that call is purely about matching architecture to the actual access shape (`04-auth` §6).

---

## Axis (e) — Scaling browser/proxy + SimilarWeb HITL across tenants

**Recommendation: share ONE SimilarWeb login behind a serialized queue; it does not scale with tenant count. Keep bot-wall detect+flag at $0. Move off noVNC to Browserbase Developer ($20/mo) for the HITL login UX when noVNC friction shows — not because of scale.** (`05-breakpoints-cost` §1, `06-peer-research` §B–D.)

**SimilarWeb HITL is a non-problem at scale — state it plainly.** The fragility is a *session-identity* problem (login-IP ≠ replay-IP triggers "impossible travel" session kill — confirmed real: DataDome's `dd` cookie is IP-bound, `06-peer-research` §B), not a *query-volume* problem. Same-IP login (the locked fix) solves it once for one shared session regardless of tenant count. Session lifespan is **time-based (days to ~2 weeks), not query-count-based**, so login cadence stays ~1 login/fortnight whether 1 or 20 tenants are behind it. Buying 20 SimilarWeb seats would be needless (Pro/Team seats run hundreds/mo). What *does* serialize is the capture queue — only one browser context holds the authenticated session — but at 20 tenants' peak that's ~20–60 min/day of serialized capture, a non-bottleneck **as long as the traffic step is async, not blocking the rest of an audit's pipeline** (`05-breakpoints-cost` §1.1).

- **noVNC ($0) vs Browserbase Developer ($20/mo):** noVNC works but is clunky (VNC/SSH-tunnel from phone) and ties up a ~300–500MB desktop Chrome+X11 session on a constrained box. Browserbase Developer gives a tappable live-view URL — dramatically better for "Cassandra Telegrams a link, Arijit taps it on his phone" — and its Contexts API persists cookies across future automated sessions. Since only **one** concurrent HITL session is ever needed, $20/mo Developer tier is sufficient from 1 through 20 tenants. Switch on first sign of noVNC friction, independent of tenant count (`06-peer-research` §C, `05-breakpoints-cost` §1.1). Steel.dev ($29/mo) is an equivalent alternative.
- **HITL pause/resume mechanism:** DB-row + poll loop (matches the Postgres state-machine Part 1 already builds), NOT Temporal — consistent with the prior overkill judgment (`06-peer-research` §C).
- **Bot-walls stay detect+flag, $0.** Cost doesn't change with scale — only the *volume* of honestly-reported `UNAVAILABLE(BLOCKED_BY=...)` flags does. If a free best-effort stealth swap is ever wanted, the two live 2026 options are **Patchright** (Chromium drop-in) or **nodriver** — but neither beats TLS/JA3-JA4-layer detection (Akamai's Jan-2026 frontier), so the honest-flag path remains the acceptance bar (`06-peer-research` §A). Paid unblockers (ScrapingBee $49/mo, Browserless $25/mo cheapest to pilot) are documented as a future option only — out of scope per the locked $0-spend decision (`06-peer-research` §D).
- **Browser concurrency is the real shared-resource constraint**, and it's the same CPU ceiling as Axis (b): headless Chrome is CPU-hungry, genuine parallelism collapses around 2–3 concurrent full pipeline runs before system-wide response times (including Cassandra's own chat) degrade (`05-breakpoints-cost` §1.3).

---

## Axis (f) — What breaks first, migration path, and cost curve

### What breaks first — ranked, with the tenant-count trigger

| Rank | Breakpoint | Bites around | Why it's first | Mitigation | Incremental cost |
|---|---|---|---|---|---|
| **1** | **Claude subscription concurrency** (flat-rate `claude -p`) | **~3–5 tenants** | A **policy/architecture** ceiling, not hardware — hits even with spare VPS capacity the moment 2+ AEs' audits overlap. **UNVERIFIED** — Anthropic publishes no concurrent-session cap; run the boxed test before treating as fact. | Hard-cap the queue to N concurrent `claude -p` slots (test to find real N); add a 2nd subscription or API-overflow path when queue depth demands. | 2nd Max 20x ≈ **$200/mo** if needed; API overflow ≈ low single-$/audit at Sonnet rates (size from real instrumented tokens, not assumption) |
| **2** | **VPS CPU (2 vCPU)** | ~5–8 tenants | Chrome + `claude -p` both CPU-bound; the hard physical ceiling on queue depth. Horizontal small boxes beat one big box for CPU-bound Chrome. | Move browser+`claude -p` execution to 1–3 separate worker boxes so contention doesn't degrade the always-on DB/Caddy/Hermes-chat box. | +1 Hostinger box ≈ **$7–15/mo** |
| **3** | **RAM (8G shared)** | ~8–15 tenants | Background services + a deeper worker queue get tight. **Arrives much earlier (~5–8) if the design lands on per-tenant Hermes containers** — which is exactly why Model C (shared instance) is recommended in Axis (a). | Prefer shared Hermes + per-tenant session state (Axis a); bump DB box to 4 vCPU/16G only if that's not adopted. | KVM4 ≈ **$13–15/mo** (only if Model C is NOT adopted) |
| **4** | **Disk (screenshots)** | ~15–20+ tenants, slow | ~20MB/audit → ~12GB/mo at sustained peak against 30G free; months of runway. | Archive screenshots >90 days to object storage (Backblaze B2) — already part of Phase-0 backup work. | ≈ **$1–3/mo** |
| — | Postgres | not near-term | Hundreds of JSONB rows/year is trivial. | Self-hosted stays fine. | $0 |
| — | SimilarWeb HITL human | never at this scale | Session-lifespan-based, not query-count-based (Axis e). | N/A — don't over-engineer. | $0 |
| — | Single Telegram bot | never at this scale | ~30 msg/s Bot API limit vs occasional status pings. Real risk here is a *correctness* leak (per-tenant session keying), not a rate wall — covered by the unifying tenant-key decision. | Per-tenant session keying (already the plan). | $0 |

**The ranking's punchline:** the business-model ceiling (subscription concurrency) bites *before* the hardware ceiling (CPU), and both bite well before "20 tenants is a lot of data" (Postgres/disk barely register). Prioritize the concurrency queue + the subscription test first — it's the actual constraint, not the box.

### Migration path: single → 20 tenants (additive, isolation-verified per onboard)

**Postgres has 0 audit rows today**, so this is *additive, not a risky data migration* — there is no backfill (`01` §6, `03` §60). Order, each step independently testable and reversible:

1. **Fix the tenant-key binding bug** (the unifying decision) — valuable at N=1, precondition for everything. Replace content-match binding with a hard `tenant_id` resolved at session start.
2. **Patch the live security gap** (`POST /api/chat` auth — boxed callout) — do this now, independent of the rest.
3. **`tenant_id` in Postgres** — index `audits.user_id`, populate it as Part 1's DB-write path goes live so every row is born tenant-correct. Ship the ACL tables (`report_access`, `share_links`, `telegram_links`) + `/internal/authz` endpoints.
4. **Per-tenant directory layout** for sqlite/memory under `/root/.hermes-prism/tenants/<slug>/`.
5. **Topic-routing** on the existing single Telegram bot; `/link` flow live.
6. **Bounded worker queue** (Redis/`arq`, start at 3) + per-tenant fairness + job timeout.
7. **Onboard tenants one at a time behind a feature flag**, verifying isolation (tenant A genuinely cannot retrieve tenant B's bound report — the cross-tenant integration test) **before** each next onboard. No big-bang cutover.

### Cost curve (subscription seat shown as the wildcard range)

| Item | 1 tenant | 5 tenants | 10 tenants | 20 tenants |
|---|---|---|---|---|
| Primary VPS (DB/Caddy/Hermes-chat) | $7–15/mo | same | same | same |
| Audit-worker VPS(es) | shares primary | not yet needed | +1 box $7–15/mo | +2–3 boxes $20–45/mo |
| SimilarWeb HITL live-view | noVNC $0 | Browserbase Dev $20/mo | $20/mo | $20/mo |
| Bot-wall detect+flag | $0 | $0 | $0 | $0 |
| Clerk auth | free | free | free | free (20 ≪ 50K MRU) |
| Postgres | $0 | $0 | $0 | $0 |
| Backups (git `/data` + object storage) | $0 | ~pennies | ~pennies | ~$1–3/mo |
| **Infra subtotal (excl. Claude seats)** | **~$10–15/mo** | **~$30–40/mo** | **~$50–80/mo** | **~$80–120/mo** |
| **Claude subscription seats (the wildcard)** | 1 (owned), flat | 1 *if queue-cap holds* | **1–2** ($0–200/mo) | **1–4** ($0–800/mo) |
| **All-in, realistic** | ~$10–15/mo | ~$30–40/mo | ~$50–280/mo | ~$80–800/mo |

Every infra row is vendor-quoted and solid. **The Claude-seat row is the one genuine unknown** — resolve it with the boxed test. If Max 20x handles 3–4 concurrent cleanly, the whole curve stays in **$10–120/mo** through 20 tenants (genuinely cheap). If it doesn't, subscription seats dominate, and the cheaper fix is likely queue-depth discipline + metered API overflow rather than buying more $200/mo seats (`05-breakpoints-cost` §2–3).

---

## What this design explicitly does NOT solve

- **Crash isolation.** Model C is one process — a daemon crash or runaway tool call degrades all tenants. Accepted risk (matches N=1 today); mitigate with hot-reload, not more containers.
- **CPU contention as a tenancy feature.** The 2-vCPU concurrency ceiling is a queue problem (Axis b), deliberately kept separate from the tenancy model. Conflating them produces a worse design for both.
- **TLS/JA3-JA4-layer bot detection.** No browser-automation tool solves Akamai's network-stack fingerprinting; the honest detect+flag path is the acceptance bar, not bypass.
- **The subscription-concurrency question itself.** This doc flags it, sizes both branches, and specifies the test — but does not resolve it. That's Arijit's informed call after the empirical result, because it's a cost/ToS decision, not an infra one.

---

## Top items gated on Arijit (for the design-review gate)

1. **Run the concurrency test** (boxed callout) — the single most important input; it decides the worker-pool depth and whether the cost curve is the cheap one or the expensive one.
2. **Approve Model C** (shared Hermes daemon + hard tenant partitions + topic-routed bot) over container-per-tenant, and accept the crash-isolation trade-off it carries.
3. **Approve app-layer `tenant_id` isolation now, RLS as a documented triggered upgrade** — vs. building RLS up front.
4. **Approve skipping Clerk Organizations** for the internal model (flat role + ACL table + signed-URL prospect shares), and greenlight the **immediate** `POST /api/chat` security-gap fix independent of the Part 2 timeline.
5. **Confirm the real-parallelism strategy** if the test shows one subscription can't sustain 3+: (a) multiple subscriptions (ToS diligence needed), (b) metered API overflow (size from real tokens), or (c) accept queue-fed throughput as the actual "20 AEs" experience — the recommended near-term default.
