# Task 5 report — embedded chat agent (Track C.3)

Status: **DONE_WITH_CONCERNS**

Branch: `feat/prism-e2e-cycle` (current branch at start of this task; worked in place, did not create a new branch).

3-line summary: Built the full grounding pipeline (pgvector migration, by-section
chunking, local MiniLM embeddings, cosine-similarity retrieval, a plain `claude -p`
chat agent with enforced citation discipline, and a FastAPI router) — all pure logic
is real-unit-tested and green, and the local embedding model + `claude -p` wrapper
were live-exercised against a real audit-data fixture. What's NOT live-verified:
the pgvector SQL against a real Postgres (no DB in this sandbox) and any actual
Clerk-authenticated request (no Clerk keys here, and — more importantly — no
per-user-slug authorization concept exists anywhere in the real stack today, so
patch #6's premise needs a decision from Arijit, not just a missing test).

---

## 0. Preflight (per brief instructions)

- Confirmed no pgvector infra exists yet: `grep -rn pgvector alembic/` → no matches
  before this task (exit code 1). This is a greenfield build.
- Read `prism_platform/db/models.py`: `Audit.audit_data` (JSONB) confirmed as the
  source-of-truth blob per company, per the comment on that column (added in
  migration 009).
- Read `alembic/versions/009_audit_data_and_score_precision.py` for migration style
  (docstring header, `sa.Column`, explicit `upgrade`/`downgrade`) and
  `008_add_knowledge_store.py` for raw-SQL patterns (`op.execute` for anything
  `op.add_column` can't express) — followed both conventions in migration 010.
- Read `prism_platform/pipeline/gate.py` + `verdicts.py` + `tests/pipeline/test_gate.py`
  for this codebase's dependency-injection pattern (injectable callables, fakes in
  tests, no live LLM/DB in unit tests) — used the same pattern throughout.
- Checked a **real** audit-data fixture (`docs/temp/fc/belk-audit-data.json`,
  57,742 bytes) instead of inventing a shape. Its real top-level keys: `meta, cover,
  score, hiring, traffic, findings, ae_fields, gap_pairs, executives, financials,
  next_steps, tech_stack, competitors, icp_mapping, methodology, abx_sequence,
  bibliography, case_studies, golden_angle, partner_intel, tab_subtitles,
  company_snapshot, industry_context, strategic_angles, intelligence_signals,
  competitive_synthesis, recommended_first_play`. This does **not** exactly match
  the brief's illustrative list ("company/techstack/traffic/competitors/financial/
  investor/social/news/hiring/partner/industry") — real sections use different
  names (`financials` not `financial`, no separate `investor`/`social`/`news` keys —
  those are folded into `intelligence_signals` by `type`). **Decision:** chunk
  generically over whatever the real top-level keys are, rather than hardcoding the
  brief's illustrative list — a fixed list would silently drop real sections and
  drift from `prism_platform/v2/audit_data_schema.py`'s `AuditData` model, which
  already declares `model_config = {"extra": "allow"}` for exactly this reason.

## 1. What was built

| File | Purpose |
|---|---|
| `alembic/versions/010_add_report_chunks_pgvector.py` | `CREATE EXTENSION IF NOT EXISTS vector` + `report_chunks` table (id, audit_id FK, domain, section_name, chunk_text, `embedding vector(384)`, embedding_model, created_at) + ivfflat cosine index. |
| `prism_platform/db/models.py` | Added `ReportChunk` ORM model (mirrors the migration) + `REPORT_CHUNK_EMBEDDING_DIMS = 384` constant. |
| `prism_platform/pipeline/chunking.py` | `chunk_audit_data(audit_data) -> list[Chunk]` — one chunk per non-empty top-level section, generic over real keys, deterministic order. |
| `prism_platform/pipeline/embeddings.py` | `embed_texts(texts) -> list[list[float]]` — local `sentence-transformers/all-MiniLM-L6-v2`, lazy-loaded + cached, no network call at embed time. |
| `prism_platform/pipeline/retrieval.py` | `retrieve(session, query, audit_id, k=5) -> list[RetrievedChunk]` — embeds query, pgvector cosine search via `<=>` (`Column.cosine_distance()`), filters by `SIMILARITY_THRESHOLD = 0.35` (named constant). |
| `prism_platform/pipeline/chat_agent.py` | `build_chat_prompt()`, `extract_cited_sections()`, `run_chat_agent()` — plain `claude -p` subprocess call (no Agent SDK, no MCP), forced `[SECTION: name]` → `(Source: name)` citation discipline, refuses to call the LLM at all when retrieval returns zero chunks. |
| `prism_platform/api/routers/chat.py` | `POST /api/v1/audits/{audit_id}/chat`. `authorize_audit_access` + `check_slug_authorization` — the patch #6 wire point (see §4). |
| `prism_platform/main.py` | Registered the new router. |
| `pyproject.toml` | Added `pgvector>=0.5`, `sentence-transformers>=5.0` as real dependencies (previously only present transitively via `scout`'s deps, not declared). |
| `tests/pipeline/test_chunking.py`, `test_embeddings.py`, `test_retrieval.py`, `test_chat_agent.py`, `test_chat_router.py` | 40 new tests, all passing. |

## 2. Patch #9 (grounding mechanism) — as locked, with one real evaluation

- **Embedding model**: kept `sentence-transformers/all-MiniLM-L6-v2` (384 dims). I
  tested adequacy for real (not assumed): embedded three real-flavored sentences —
  one Belk search-finding, a paraphrase of it, and an unrelated Belk-history fact —
  and confirmed cosine(finding, paraphrase) > cosine(finding, unrelated fact)
  (`tests/pipeline/test_embeddings.py::test_embed_texts_similar_texts_are_closer_than_dissimilar_ones`,
  **passed live** against the real downloaded model). MiniLM is genuinely adequate
  for this scope — no swap needed, no cost/credential decision to flag.
- **Chunking**: by report section, generic over real top-level `audit_data` keys
  (§0) — not a fixed-token window. Verified against the real Belk fixture.
- **Similarity threshold**: `SIMILARITY_THRESHOLD = 0.35`, a named constant in
  `retrieval.py`, not a magic number.
- **Retrieval**: top-k=5 default, no cross-encoder re-ranking (v1 scope, as directed).

## 3. LIVE-VERIFIED vs WRITTEN-BUT-UNVERIFIED — do not blur these

**LIVE-VERIFIED (real command run, real output shown/observed in this session):**
- Chunking logic against the real Belk audit-data fixture (6/6 tests passed).
- The local MiniLM embedding model: downloaded, loaded, and run on CPU in this
  sandbox; semantic discrimination test passed for real (not asserted) — see §2.
- `claude -p` subprocess mechanics: ran `_default_claude_cli("Reply with exactly
  the single word: PONG")` → returned `'PONG'`, exit 0. **Then ran the full,
  real pipeline end-to-end**: real Belk audit JSON → `chunk_audit_data()` →
  2 real sections selected → `build_chat_prompt()` → live `claude -p` call. The
  model's real answer:
  > "Belk vendor: Constructor.io (Source: tech_stack). Confirmed incumbent,
  > displacement target (Source: tech_stack).
  >
  > Typo-tolerance: CONTEXT no data. findings section only covers semantic/NLP
  > gap (F01, cocktail dress query) — belk.com WAF-blocked (403 PerimeterX),
  > actual_behavior "not observable" (Source: findings). No typo-tolerance test
  > result present in CONTEXT. Can't answer that part — insufficient info, not
  > guessing."

  This is real, live proof the citation-discipline design works end-to-end with a
  real model on real data: it cited both sections correctly AND refused to answer
  the part of the question its retrieved context didn't cover, instead of
  fabricating. `extract_cited_sections()` correctly parsed `{'tech_stack', 'findings'}`
  from that real response.
- Full test suite: `761 passed, 8 failed (pre-existing, unrelated), 19 skipped` —
  see §5 for the exact pre-existing-failure list and why they're unrelated.
- `ruff check`, `ruff format --check`, `mypy --strict` all clean on every new/changed
  file — see §5 for exact commands + output.
- FastAPI app boots with the new router registered:
  `app.routes` includes `/api/v1/audits/{audit_id}/chat` after importing
  `prism_platform.main`.

**WRITTEN-BUT-UNVERIFIED (no live Postgres/pgvector, no live Clerk session in this sandbox):**
- The migration (010) was never run against a real Postgres. Confirmed no DB
  reachable: `nc -z localhost 5432` → closed; `docker ps` → daemon unreachable.
  Verified instead: the migration module imports cleanly, its
  `revision`/`down_revision` chain is correct (010 → 009), and it has real
  `upgrade`/`downgrade` functions.
- `retrieve()`'s actual SQL execution against pgvector was never run against a real
  DB. Verified instead: the SQLAlchemy statement (including
  `ReportChunk.embedding.cosine_distance(...)`) **compiles to valid PostgreSQL**
  via `stmt.compile(dialect=postgresql.dialect())` — confirmed the `<=>` operator
  and `similarity` expression render correctly:
  ```sql
  SELECT report_chunks.section_name, report_chunks.chunk_text,
         %(param_1)s - (report_chunks.embedding <=> %(embedding_1)s) AS similarity
  FROM report_chunks
  WHERE report_chunks.audit_id = %(audit_id_1)s::UUID
  ORDER BY report_chunks.embedding <=> %(embedding_2)s
  LIMIT %(param_2)s
  ```
  This proves the query is syntactically correct Postgres/pgvector SQL, not that it
  returns correct results against real data — that needs a live DB with the
  migration applied and real embedded rows.
- No actual insert-then-query round trip against `report_chunks` was run.

## 4. Patch #6 (Clerk-auth test) — the real gap, stated plainly

The brief asks for "an explicit integration test proving: a request with a valid
Clerk session for a slug the user is NOT authorized for gets rejected, and a valid
session for an authorized slug gets a grounded answer." I could not build that
test as literally specified, and it's important to say **why**, not just that I
lacked keys:

1. **This backend (PIP, `prism_platform`) has zero auth middleware.** Grepped the
   whole tree — no Clerk, no auth dependency, nothing. `prism_platform/api/deps.py`
   only exposes `DbSession`/`TemporalDep`. Confirmed by reading it in full.
2. **Clerk auth lives entirely in the other repo** (`~/prism`, the frontend,
   `server/chat-proxy.mjs`). I read that file. Its real behavior:
   - Clerk (`checkAuth`) gates **page loads** only — "is this user signed in at
     all," a binary check, with `/reports/*` gated and everything in
     `PUBLIC_PREFIXES` (which **includes `/api`**) explicitly ungated.
   - There is **no per-user-to-slug authorization model anywhere in the stack**
     today. `handleChat` in `chat-proxy.mjs` takes a `slug` in the request body
     with zero check that the calling (Clerk-authenticated) user is entitled to
     that specific slug — any signed-in-or-not caller can ask about any slug.

   So "a slug the user is NOT authorized for" describes a feature that doesn't
   exist yet, not a test gap in an existing feature. Building a real test for it
   would mean inventing the authorization model itself as an unreviewed side
   quest inside a grounding-pipeline task — I didn't do that without checking
   with Arijit first, per this project's "never invent architecture" rule.

**What I did instead (the concrete, ready-to-run spec the brief asks for as the fallback):**
- Added `authorize_audit_access` + `check_slug_authorization` to `chat.py` as the
  **wire point** for this check once a real authorization model exists: a
  placeholder header `X-Prism-Authorized-Slugs` (comma-separated domains) that a
  trusted upstream proxy would set *after* validating a Clerk session and looking
  up that user's entitled slugs. If absent, the check fails **open** — deliberately
  matching today's real (unenforced) state, not a new gap this task introduces.
- **Real, ready-to-run test spec** for the day a per-user-slug model exists:
  1. `POST /api/v1/audits/{audit_id}/chat` with header
     `X-Prism-Authorized-Slugs: dell.com` (does NOT include the target audit's
     domain, e.g. `belk.com`) → expect `403`, body
     `{"detail": "not authorized for domain 'belk.com'"}`.
  2. Same request with `X-Prism-Authorized-Slugs: belk.com,dell.com` (includes the
     target domain) → expect `200`, body shaped like
     `{"answer": str, "cited_sections": list[str], "retrieved_sections": list[str]}`.
  3. Upstream integration point: `chat-proxy.mjs`'s `handleChat` would need to (a)
     call `clerk.authenticateRequest`, (b) resolve `auth.userId` → their entitled
     slugs (a lookup that doesn't exist anywhere yet — Clerk metadata? a new DB
     table? — this is the actual design decision Arijit needs to make), (c) set
     `X-Prism-Authorized-Slugs` before proxying to this backend.
  - I unit-tested steps 1–2's *backend* half for real: `test_chat_endpoint_rejects_unauthorized_slug`
    and the authorized-slug case (`test_authorize_audit_access_returns_audit_when_authorized`)
    both pass, exercising the actual FastAPI route + dependency, with a fake DB
    session (no live Postgres) standing in for real data.
  - Step 3 (the actual Clerk session → entitled-slugs lookup) is **not built** —
    that's the real gap, and it's bigger than "missing test infra." **This needs
    Arijit's decision**, not a unilateral design choice buried in this task: is
    per-user report access scoped at all today (e.g. "any signed-in user sees any
    report," which the current code implies), or should it be?

## 5. Verification commands + output

```
$ .venv/bin/ruff check prism_platform/pipeline/chunking.py prism_platform/pipeline/embeddings.py \
    prism_platform/pipeline/retrieval.py prism_platform/pipeline/chat_agent.py \
    prism_platform/api/routers/chat.py prism_platform/db/models.py prism_platform/main.py \
    alembic/versions/010_add_report_chunks_pgvector.py tests/pipeline/test_chunking.py \
    tests/pipeline/test_embeddings.py tests/pipeline/test_retrieval.py \
    tests/pipeline/test_chat_agent.py tests/pipeline/test_chat_router.py
All checks passed!

$ .venv/bin/ruff format --check <same files>
13 files already formatted

$ .venv/bin/python -m mypy <same files, minus tests> --strict
Success: no issues found in 7 source files

$ .venv/bin/python -m pytest tests/ -q
761 passed, 8 failed, 19 skipped, 24 warnings in 63.24s
```

The 8 failures are **pre-existing and unrelated** to this task:
- `tests/test_knowledge.py` (4 tests) — `OSError: Multiple exceptions` connecting
  to a live Postgres, which doesn't exist in this sandbox (same root cause as this
  task's own DB-dependent pieces).
- `tests/v2/test_search_vendor_detector_integration.py` (4 tests) — Playwright
  Chromium executable not installed in this sandbox (`playwright install` not run
  here), unrelated to grounding/chat work.

None of the 40 new tests are among the failures; all 40 pass.

## 6. Honest gaps / follow-ups for Arijit

1. **Patch #6's real premise needs a decision** (§4) — the per-user-to-slug
   authorization model doesn't exist anywhere in the stack. I built the backend
   wire point and a ready-to-run spec but did not invent the model itself.
2. **`uv.lock` was not regenerated.** I added `pgvector`/`sentence-transformers`
   to `pyproject.toml` and installed them into `.venv` via `uv pip install`
   (not `uv add`), so the lockfile is stale relative to `pyproject.toml`. Running
   `uv lock` before this ships for real would be the correct next step — I didn't
   run it here to avoid touching unrelated pinned versions as a side effect of
   this task.
3. **No live pgvector round trip.** The first real test of migration 010 +
   `retrieve()`'s actual SQL against a populated `report_chunks` table needs to
   happen against a real (or dockerized) Postgres before this is cutover-ready —
   flagged explicitly per the brief's DoD, not silently assumed to work.
4. **No indexing pipeline wired to a real audit run yet.** This task built
   chunking + embedding + retrieval + the chat agent as composable pieces; it did
   not wire "on audit completion, chunk+embed+insert into report_chunks" into the
   executioner (`prism-runner.py`) or the FastAPI audit-completion path — that's
   Task 4's/the cutover phase's integration concern, not scoped into this brief's
   "what to build" list, but worth naming so it isn't assumed done.
