# ADR: MyOS Storage Architecture

- **Date:** 2026-07-01
- **Status:** ACCEPTED (core), with one OPEN sub-decision (sync mechanism)
- **Source:** `docs/workspace/myos-storage-recommendation.md` (plain) + vault `Projects/MyOS/Storage-Architecture.md` (full)

## Decision (accepted, locked)

MyOS stores data as **markdown-as-truth, Postgres-as-derived-index**:

1. **Source of truth = the Obsidian vault (markdown).** Agents write markdown first; Arijit keeps editing raw files by hand.
2. **Postgres = the queryable, disposable copy the dashboard reads.** Two tables: a `status` table (project, stage, health, last_updated, tenant) and a `progress_log` table (one row per change = the graph's time series). Wipe and rebuild from the vault at any time.
3. **pgvector lives in the SAME Postgres** for agent search/RAG. No separate vector database until ~100M vectors force it.
4. **Multi-tenant = one shared database + `tenant_id` column + Postgres Row-Level Security.** No schema-per-tenant / db-per-tenant until a regulated contract forces it.
5. **Reuse PIP's existing Postgres + alembic stack.** No new datastore toolchain.

Rejected alternatives (and why) are in the source doc: DB-as-only-truth (Arijit edits raw files), dashboard-straight-off-markdown (slow/fragile SQL over loose files), separate vector DB (unjustified service), schema/db-per-tenant (premature).

## OPEN sub-decision: the sync mechanism (markdown -> Postgres)

The source doc proposes a **filesystem watcher**. Investigation on 2026-07-01 found the doc's premise is inaccurate: **the vault is NOT git-versioned today** (it is Google-Drive-synced only, no git repo, no remote). A watcher on a Drive-synced folder is fragile (async/partial-write sync) and can only run on the laptop (the VPS cannot see the Drive mount), forcing network writes to VPS Postgres with the laptop always on.

**Recommended amendment (pending Arijit's call):** git-back the vault (at least `Projects/`), push to a private GitHub repo, and drive the sync with the **`/persist` -> webhook** pipeline (already specified in vault `Projects/ArijitOS/My-OS-Specs.md`) instead of a file-watcher:

> edit markdown -> `/persist` commits it -> webhook fires -> VPS pulls committed markdown -> updates Postgres.

Benefits: real version history (which the source doc assumed already existed), reuses tonight's proven `prism-deploy-hook` (webhook->pull) + `prism-runner` (event->headless run) substrate, and honors the "version everything in GitHub" principle. One GitOps spine for both code and knowledge. The file-watcher becomes optional local-dev convenience, not the backbone.

**The choice:** (A, recommended) git-back the vault + persist-webhook sync; or (B) keep the vault Drive-only with a laptop file-watcher.

## Verify before writing code

- Confirm real Hermes table names on the box: `sqlite3 <HERMES_HOME>/state.db ".schema"` (e.g. `/root/.hermes-prism/state.db`). Docs may differ from the install.
- Resolve the OPEN sync sub-decision above.
