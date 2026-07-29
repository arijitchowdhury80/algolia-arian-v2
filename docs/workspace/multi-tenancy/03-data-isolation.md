# Data Isolation Model for PRISM Postgres — 20 Tenants

**Scope:** which isolation model PRISM's Postgres should use once tenancy = "one Algolia AE/BDR user." Written 2026-07-02 against alembic head 008, `prism_platform/db/models.py`, `prism_platform/db/session.py`, `docker-compose.yml`.

## Ground truth verified locally (not re-derived from the goal-plan doc)

- **Single DB role for everything.** `docker-compose.yml` creates one Postgres role, `prism`, which both owns every table (it ran the alembic migrations) and is the app's connection role (`prism_platform/config.py:43`, `postgresql+asyncpg://prism:...`). This one fact kills naive RLS — see §2.
- **NullPool, not a pooler.** `prism_platform/db/session.py:15-18` uses SQLAlchemy's `NullPool` explicitly, with a comment saying it's to dodge event-loop/connection-reuse issues under uvicorn. This means **there is no PgBouncer, no asyncpg statement-cache/prepared-statement trap, and no cross-request GUC leakage risk today** — each logical request gets its own real connection, used once, then closed. That removes the single scariest RLS footgun (see §2) as a non-issue *for this deployment as it stands*. It also means connection cost is a non-issue at 20 tenants (a handful of req/s, tops) but would need revisiting before real concurrency.
- **The isolation column already exists and is unpopulated.** `Audit.user_id: Text, nullable=False, default="system"` (`models.py:87`, migrated in `001_initial_schema.py:48` with `server_default='system'`). Every one of the 0 existing rows would carry `"system"`. This is effectively a pre-built tenant column nobody has wired up yet.
- **`accounts.domain` is globally unique** (`models.py:36`, `unique=True`). One row per company domain, full stop — there is no per-tenant company research today, and the schema doesn't support two tenants having independent "versions" of the same company's Account row.
- **The shared Algolia knowledge tables already establish the pattern of deliberately-global data**: `algolia_customers`, `algolia_case_studies`, `algolia_quotes`, `algolia_proofpoints`, `algolia_advocates`, `algolia_knowledge`, `algolia_gaps`, `vertical_benchmarks` — none of these are tenant data, all read by every tenant's chat/RAG regardless of who's asking. This is a precedent to extend, not fight.
- `audits.account_id` FKs to `accounts.id` (CASCADE), `module_executions.audit_id` and `deliverables.audit_id` both FK to `audits.id` (CASCADE). Tenant scoping, if added, only needs to land on one table if the others are always reached through `audit_id`.

## The four options, evaluated honestly at this scale

**(a) Shared schema + `tenant_id` + Postgres RLS.**
Textbook answer for SaaS multi-tenancy, and it *would* work here — but only after real setup cost this deployment doesn't have yet:
1. RLS policies are enforced against ordinary roles. **Table owners bypass RLS by default**, and superusers/`BYPASSRLS` roles bypass it unconditionally, `FORCE ROW LEVEL SECURITY` or not ([Postgres docs](https://www.postgresql.org/docs/current/ddl-rowsecurity.html); [Bytebase RLS footguns](https://www.bytebase.com/blog/postgres-row-level-security-footguns/)). Since `prism` is both owner and app role, turning on RLS today is a **silent no-op** unless you either (i) create a second, non-owner, non-`BYPASSRLS` role for the app and re-point `database_url` at it, or (ii) run `ALTER TABLE audits FORCE ROW LEVEL SECURITY` and accept the owner is now also policy-bound (workable, but means one role change touches every query path, migrations included — migrations would need to run as a role that bypasses, or connect differently).
2. RLS needs the tenant id present in the session, standard pattern is `SET LOCAL app.tenant_id = '<id>'` at the top of every transaction, with the policy `USING (tenant_id = current_setting('app.tenant_id')::uuid)`. In SQLAlchemy the idiomatic hook is a `before_cursor_execute`/session-begin event listener that issues the `SET LOCAL` from a contextvar populated by FastAPI's auth dependency ([Atlas SQLAlchemy RLS guide](https://atlasgo.io/guides/orms/sqlalchemy/row-level-security); [döb: RLS with SQLAlchemy](https://dobken.nl/posts/rls-postgres/)). This is real code (a middleware/event listener + a policy per table + an integration test that tries to read cross-tenant and asserts it fails) — call it 1-2 focused sessions, not a config flag.
3. **The one genuine gotcha that usually kills this pattern doesn't apply here.** The classic failure is PgBouncer transaction-mode pooling reassigning a physical backend to a different client mid-session, so a `SET LOCAL` (or a cached prepared statement) from tenant A's transaction can leak into tenant B's next transaction on the same backend ([asyncpg+PgBouncer prepared statement trap](https://goldlapel.com/grounds/connection-pooling/asyncpg-pgbouncer-prepared-statement-trap)). PRISM has **no pooler** — `NullPool` means one physical connection per request, closed after. `SET LOCAL` is scoped to a transaction on a connection nobody else will ever touch. This removes the scariest part of RLS's operational risk *as currently deployed*. It reappears the moment `NullPool` is swapped for a real pool or a managed-PG proxy (see §Managed-PG below) — flag it then, not now.
4. Bottom line: RLS is *correct in spirit* but net-new plumbing (new role, event listener, policies, tests) for a threat model — 20 trusted internal Algolia employees seeing each other's *own company's sales-prospecting research* — that isn't adversarial. It's the right answer once PRISM data becomes customer-facing or the tenant count/trust model changes; it's not the right first move for V1.

**(b) Schema-per-tenant.**
20 schemas, each migrated independently. Alembic doesn't support per-schema migrations out of the box — you'd hand-roll a loop that runs the same migration N times with a `search_path` swap, and every new migration now has to be verified against 20 schemas instead of 1. For a dataset that's currently *zero rows* and, per audit, a few MB of JSONB, this multiplies operational surface for no isolation benefit over (a) or (d) — worse, actually, because the shared Algolia knowledge tables would need to live somewhere every schema can reach (a 21st "public" schema), which just re-invents (a)'s cross-cutting-table problem with extra ceremony. Rejected.

**(c) Database-per-tenant.**
20 Postgres databases on one small VPS. Cross-database queries in Postgres require `postgres_fdw` or `dblink` — but the shared Algolia knowledge tables need to be read by every tenant's chat, constantly. That's 20x the FDW wiring of (a), 20x the connection overhead (defeats the point of `NullPool` being cheap-per-request), and 20x the backup/migration operations for a workload that's currently under 1MB total. This is the option that would make sense if tenants needed hard resource isolation (noisy-neighbor CPU/IO) or regulatory data-residency separation — neither applies to 20 internal AEs on a shared VPS. Rejected for this stage; revisit only if a specific tenant ever needs contractual data residency.

**(d) `tenant_id` column, app-layer enforced, no RLS.**
The honest option for 20 trusted internal users, and what I'm recommending for V1. Every query that returns tenant-scoped rows goes through one shared FastAPI dependency/repository function that always filters `WHERE audits.user_id = :current_user`. No new Postgres role, no `SET LOCAL`, no policy DDL — ships fast, matches the actual trust model, and reuses the column that's already sitting there unused.

## Recommendation: (d) now, (a) as the named upgrade path — not silently skipped

Given: 20 *internal, trusted* tenants; data that is Algolia's own competitive/sales research on prospects (not a customer's private data — leaking AE-Y's Belk audit to AE-X inside Algolia is an annoyance, not a breach); a schema that already carries the exact column needed; and a `NullPool` deployment that has no pooler-based RLS trap today but also isn't purpose-built for RLS —

**Ship app-layer `tenant_id` filtering now. Do not silently skip RLS — write down the trigger condition for revisiting it:** the day PRISM audit data becomes visible to anyone outside Algolia (a prospect-facing portal, a partner integration, or a change in trust model), or the day the DB moves behind a real connection pooler, re-open this doc and build (a) properly (new low-privilege app role + `SET LOCAL` + policies + cross-tenant read test). That's a half-day of work sitting on top of the same `tenant_id` column — (d) is not a dead end, it's RLS's precondition.

### Concrete schema change

1. **`audits.user_id` becomes the tenant key immediately — no migration needed for the column itself.** It already exists (`Text, nullable=False`, currently defaulted to `"system"`). Change: populate it with the real tenant identity instead of the default, and add an index:
   ```python
   # alembic/versions/009_index_audits_tenant.py
   op.create_index("idx_audits_user_id", "audits", ["user_id"])
   ```
2. **Tenant identity = Clerk user id (string), not a new `tenants` table, for V1.** Memory `project-prism-login-multitenancy` confirms Clerk is already the auth layer in flight. Store the Clerk `user.id` (or `org.id` if/when AEs are grouped into teams — Clerk supports both) directly in `audits.user_id`. Skip building a `tenants` table until there's an actual second attribute to hang off it (plan, seat count, team roster) — right now it would be a table with one column (id) FK'd from one place, pure ceremony.
3. **`accounts` stays global, unscoped — do not add `tenant_id` there.** `domain` is already globally unique; this is deliberate-by-existing-design, not an oversight to fix. Two AEs auditing Belk should hit the *same* `accounts` row and its already-researched company context — that's a feature (dedup work, faster second audit of the same prospect), consistent with how the shared Algolia knowledge tables already work. Tenant-scope the *audit* (the work product: score, findings, deliverables — "AE Jane's read on Belk today"), not the *company* (the facts: Belk's HQ, employee count, exec team — true regardless of who's asking).
4. **`module_executions` and `deliverables` need no `tenant_id` column of their own.** Both already FK to `audit_id` with `ondelete="CASCADE"`. Enforce tenant scoping by joining through `audits.user_id` in the one shared repository function, e.g.:
   ```python
   async def get_module_executions_for_tenant(session, audit_id: UUID, tenant: str):
       stmt = (
           select(ModuleExecution)
           .join(Audit, Audit.id == ModuleExecution.audit_id)
           .where(ModuleExecution.audit_id == audit_id, Audit.user_id == tenant)
       )
   ```
   Trade-off acknowledged: a join on every scoped query vs. a denormalized `tenant_id` copy on each child table. At current/projected row counts (dozens of audits/year × 20 tenants = hundreds of rows/year total) the join costs nothing measurable; denormalizing would just create a second place `tenant_id` can drift out of sync if an audit is ever reassigned. Don't denormalize until profiling says otherwise.
5. **One shared enforcement point, not per-route filtering.** Whatever ships this needs the `WHERE ... = tenant` clause in exactly one place (a repository/service layer function each FastAPI route calls), not copy-pasted into every endpoint — that's the actual mitigation for app-layer blast radius (see below), and it's a cheap code-review-time check: "does this query go through the shared scoped-query helper?"

### Migration path from today's single-tenant rows

There are currently **0 rows** in `audits`/`module_executions`/`deliverables` (per the goal-plan's audit, confirmed structurally here — the schema exists, nothing has been written to it yet since the audit engine doesn't persist to Postgres at all currently). So there is no backfill problem: turn on the `user_id` population *before* Part 1's DB-write path goes live (goal-plan §1.4), and every row is born tenant-correct. This is the cheapest possible migration story — don't build a backfill script for zero rows.

### Backup story

Current plan (goal-plan §Phase 0.1): nightly `pg_dump` → git repo → private GitHub. A single-database `pg_dump` naturally captures all tenants' data in one file — this is unaffected by choosing (d) over (a)/(b)/(c); RLS, if added later, doesn't change what `pg_dump` captures (it dumps as the backup role, typically bypassing RLS by design so the restore is complete). No special per-tenant backup/restore consideration needed at this scale; a full-DB restore is the correct and only granularity worth building for 20 tenants and sub-1MB data.

### Blast radius of app-layer bugs

Real risk, not hand-waved: a missed `WHERE user_id = :tenant` in a new route lets AE-X list AE-Y's audits. Mitigations that make this an acceptable trade for the speed gained:
- Single shared scoped-query helper (above) — one place to get right, one place to unit-test with a "tenant A cannot see tenant B's audit" integration test (this test should exist regardless of (a) vs (d) — RLS doesn't remove the need for it, since (a) can just as easily be misconfigured, per the Bytebase RLS-footguns piece above).
- The blast radius, if hit, is "an internal Algolia employee sees another internal Algolia employee's sales research on a public company" — not customer PII, not a compliance event. This is the actual reason (d) is defensible for V1 in a way it wouldn't be for a customer-facing product.
- `code-validator`/`code-review` should flag any new query against `audits`/`module_executions`/`deliverables` that doesn't route through the shared helper — worth a lint rule or grep-based pre-commit check once the helper exists.

### What the managed-PG move changes

Moving off the local Docker Postgres to a managed provider (RDS, Neon, Supabase, Crunchy) typically means:
- A connection pooler (RDS Proxy, Neon's built-in pooler, PgBouncer-as-a-service) often gets inserted **by the provider**, which is exactly the trigger condition that reopens the asyncpg-prepared-statement/`SET LOCAL` risk described in §(a).3. If/when that migration happens, revisit `NullPool` (it may need `statement_cache_size=0` on the asyncpg connection args, or a switch to session-mode pooling) *before* also layering RLS on top — doing both changes blind at once would make a regression hard to attribute.
- Managed providers make automated `pg_dump`-equivalent backups turnkey (point-in-time recovery), which is strictly additive to the git-versioned dump already planned — keep the git-versioned dump too, since it's the only *off-provider* copy (protects against provider account issues, not just disk failure).
- None of this changes the (d)-now/(a)-later recommendation; it just narrows exactly when (a) becomes worth doing (bundle it with the pooler-safety work, not before).

## Summary of the concrete change to make

- Add index `idx_audits_user_id` on `audits.user_id` (migration 009).
- Start populating `audits.user_id` with the real Clerk user id (or org id) instead of the `"system"` default, as part of Part 1's DB-write path.
- Write one shared tenant-scoped query helper/repository function; route every `audits`/`module_executions`/`deliverables` read/write through it.
- Leave `accounts` and all `algolia_*`/`vertical_benchmarks` tables global/unscoped — they are reference data, not tenant data, by design.
- Do not build RLS, schema-per-tenant, or DB-per-tenant now. Document the RLS upgrade path (this doc) so it isn't rediscovered from scratch when the trust model or pooling setup changes.

Sources cited inline above: [Postgres RLS docs](https://www.postgresql.org/docs/current/ddl-rowsecurity.html), [Bytebase — Postgres RLS footguns](https://www.bytebase.com/blog/postgres-row-level-security-footguns/), [Atlas — RLS with SQLAlchemy](https://atlasgo.io/guides/orms/sqlalchemy/row-level-security), [döb — RLS with SQLAlchemy](https://dobken.nl/posts/rls-postgres/), [Gold Lapel — asyncpg + PgBouncer prepared statement trap](https://goldlapel.com/grounds/connection-pooling/asyncpg-pgbouncer-prepared-statement-trap).
