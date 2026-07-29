# MyOS Storage — My Recommendation (plain)

Date: 2026-07-01. Full detail + sources: vault `Projects/MyOS/Storage-Architecture.md`.

## The question
How should MyOS store its data — markdown files, a database, or both — given it needs a live dashboard and has to go multi-tenant later?

## How Hermes stores data today (so we build on reality)
Hermes = NousResearch/hermes-agent. It uses:
- SQLite (`~/.hermes/state.db`) for chat sessions + messages.
- Flat markdown for its "memory" (frozen into the prompt at session start — that is why editing memory only affects new sessions).
- No vector store by default.
So Hermes gives us chat history, not a dashboard-grade store. MyOS has to add that.

## My recommendation (one design, not a menu)
Markdown stays the truth. A database is a copy that the dashboard reads.

1. Source of truth = your Obsidian vault (markdown, git-versioned). You keep editing it by hand. Agents write markdown first.
2. Postgres = the queryable copy the dashboard reads. Two things live here:
   - a status table (project, stage, health, last updated, tenant),
   - a progress-log table, one row per change = the data the graph plots over time.
3. pgvector in that SAME Postgres for the agent's search/RAG. No second database.
4. Multi-tenant = one shared database with a `tenant_id` column + Postgres Row-Level Security. Cheap now, no rewrite when customer #2 arrives.
5. Keeping them in sync = a small watcher program that notices when a vault file changes and updates Postgres (debounced ~1-2s). The database is disposable: wipe it and rebuild from the vault in seconds.

Flow: Obsidian markdown (git) -> watcher -> Postgres + pgvector (isolated per tenant) -> dashboard reads SQL, Hermes/Etna reads the vector search.

## Why this and not the alternatives
- Not "database is the only truth": wrong for you, because your knowledge starts in Obsidian and you edit raw files. That model (Notion/Linear) assumes nobody touches raw files.
- Not "run the dashboard straight off markdown": SQL charts + time-series over loose files are slow and fragile.
- Not a separate vector database (Qdrant/Chroma): unjustified extra service to run and secure until you are at ~100M vectors.
- Not schema-per-tenant or database-per-tenant: more work, no benefit until a regulated enterprise contract forces it.

## Fits us specifically
- Reuses PIP's existing Postgres + alembic stack — not a new toolchain.
- Vault stays your human face; the database is derived and rebuildable.
- Multi-tenant from day one for almost no cost.

## One thing to verify before writing code
Confirm the real Hermes table names on the box (docs may differ from our install):
    sqlite3 <HERMES_HOME>/state.db ".schema"      # e.g. ~/.hermes-prism/state.db
