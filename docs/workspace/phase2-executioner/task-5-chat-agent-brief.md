# Task 5 brief — embedded chat agent (Track C.3)

Read first: `docs/plans/2026-07-12-prism-finishing-build-plan.md` PHASE 2 §Track C item 3 + critique patches #6 and #9. Read `prism_platform/db/models.py` (the real `Audit`/`ModuleExecution` models — `Audit.audit_data` is the JSONB source-of-truth blob per-company, per existing code comments) and confirm current Postgres has no pgvector table yet (`grep -rn pgvector alembic/` returned nothing — confirm this yourself, don't just trust this brief).

## Patch #9 (grounding mechanism) — LOCKED so this isn't hand-wavy

No pgvector infra exists yet in this repo — this is a real greenfield build, not wiring. Per "no credit, no fabrication" and this project's standing preference for keyless/local infra over new paid API dependencies (`reference-no-paid-mcp-keys-needed`, `detect-search` keyless pattern), use:
- **Embedding model: `sentence-transformers/all-MiniLM-L6-v2`** (384 dims, runs locally on CPU, no API key, no per-call cost). If you determine this is genuinely inadequate for retrieval quality on real audit content (test it, don't assume), name a specific alternative with the same no-new-credential property and justify the switch in your report — do not silently swap to a paid provider (OpenAI/Voyage) without flagging that as a cost/credential decision for Arijit.
- **Chunking: by report section** (the audit's existing logical structure — company/techstack/traffic/competitors/financial/investor/social/news/hiring/partner/industry sections, one chunk per section per company, not a fixed-token sliding window) — audit reports are structured JSON/markdown with real section boundaries; chunking along them keeps citations traceable to a named section, which matters for the "grounded, not fabricated" requirement this whole project is built around.
- **Similarity threshold: cosine similarity >= 0.35** via pgvector's `<=>` operator (typical usable threshold for MiniLM-class models) — treat as a starting default, tunable, but state it explicitly in code (a named constant, not a magic number scattered inline).
- **Retrieval**: top-k=5 chunks per query, re-ranked by nothing fancy (no cross-encoder) for this task's scope — keep it simple, this is v1.

## What to build

1. **Alembic migration**: enable the `pgvector` Postgres extension (`CREATE EXTENSION IF NOT EXISTS vector`) and a new table, e.g. `report_chunks (id, audit_id FK, domain, section_name, chunk_text, embedding vector(384), created_at)`. Follow the existing migration style in `alembic/versions/` (read a recent one, e.g. migration 009, for the project's conventions before writing yours).
2. **Embedding + chunking pipeline**: a function that, given an `Audit.audit_data` blob, splits it into per-section chunks and computes embeddings (local model, batched, no network call). Test with a real (or realistic fixture) audit_data shape — check an existing published audit's JSON structure first (e.g. via the DB or a fixture file already in `tests/` if one exists) rather than inventing a shape.
3. **Retrieval function**: `retrieve(query: str, audit_id: UUID, k: int = 5) -> list[RetrievedChunk]` — embeds the query with the same local model, runs the pgvector similarity query, filters by threshold, returns chunks with their section name (for citation).
4. **The chat agent itself**: a plain `claude -p` invocation (NOT Claude Agent SDK — this project's locked decision, see plan doc §1) that takes a user question + `audit_id`, calls `retrieve()`, injects the retrieved chunks into the prompt with explicit citation markers (section name), and requires the model to cite which section backed each claim in its answer — same `[FACT]`-citation discipline as the existing prism-hub chat (see memory `project-prism-hub-chat-live.md` for the pattern this replaces). This can be a new small module, e.g. `prism_platform/pipeline/chat_agent.py` or wherever fits the existing FastAPI router structure (`prism_platform/api/routers/`) — check the existing routers for the right home before creating a new top-level location.
5. **Patch #6 (Clerk-auth test)**: this chat agent will eventually sit behind `prism.chowmes.com`'s Clerk-gated session (per SESSION.md — Clerk auth was already verified/fixed in Phase 1's SEC0 work). Write an explicit integration test (or, if Clerk test infra doesn't exist in this repo yet, a clearly-scoped test PLAN with the exact request/response shape to verify) proving: a request with a valid Clerk session for a slug the user is NOT authorized for gets rejected, and a valid session for an authorized slug gets a grounded answer. If you cannot execute a real Clerk-authenticated request from this sandbox (no live Clerk dev keys here), say so plainly and hand back a concrete, ready-to-run test spec rather than skipping this silently — this is a named patch, not optional.

## Definition of done

- Migration applies cleanly against a real or dockerized Postgres if available; if not available in this sandbox, the migration file must be syntactically valid and reviewed against the existing migration style, with this limitation stated explicitly (same honesty standard as Tasks 3/4a's DB-write concerns).
- Retrieval + chunking logic has real unit tests with fixture data (no live DB needed for the pure logic).
- Chat agent's citation-discipline is testable: given a fake `retrieve()` returning known chunks, the agent's prompt-construction step provably includes section-name citations and instructs the model not to answer beyond what's retrieved.
- `ruff check . && ruff format --check . && mypy` clean on new files (same standard as prior tasks — show output).
- Report which parts are LIVE-VERIFIED vs. WRITTEN-BUT-UNVERIFIED (docker/Clerk-dependent pieces) — do not blur the two.

## Output

Write your report to `docs/workspace/phase2-executioner/task-5-report.md`. Return status DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED with the report path and a 3-line summary.
