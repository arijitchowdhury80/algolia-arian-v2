# PRISM monorepo restructure — plan

**Date:** 2026-07-28
**Status:** DRAFT — awaiting Arijit's sign-off. Nothing executed.
**Directive (Arijit, verbatim intent):** one repo named `prism`; inside it `frontend/` and
`backend/`; identical structure on laptop, VPS and GitHub; drop the "PIP" name entirely;
remove Hermes completely; Cassandra becomes a Claude agent; `v2` is a branch.
Laptop = development, VPS = production, GitHub = backup.

## Target end state

```
prism/                        GitHub: arijitchowdhury80/prism   (single repo)
├── frontend/                 static site, published reports, node web+chat server, UI
├── backend/                  FastAPI services, generators, v2 modules, alembic
├── docs/                     specs, decisions, plans (spans both sides)
├── CLAUDE.md
└── README.md
```

| environment | path | role |
|---|---|---|
| laptop | `~/Dropbox/AI-Development/prism` | development |
| VPS | `/opt/prism` | production |
| GitHub | `arijitchowdhury80/prism`, default `main`, plus `v2` | backup |

`pip.git` is retired (archived, not deleted, until the merge is proven).

## Current state, measured 2026-07-28

- `prism.git main` @ `5b4d6c4` — 700 tracked files, **187 are `.bak-*` junk**, 79 root files of
  which only 9 are real. Contains: real source (`server/`, `api/`, `chat-widget.js`,
  `cassandra-live.js`, `index.html`), generated report HTML under `reports/`, and the junk.
- `pip.git main` @ `fc8d1df` — clean. `prism_platform/`, `alembic/`, `docs/`, `tests/`,
  plus a **dead Next.js app at `frontend/` (123 files)**.
- VPS: `/opt/PRISM/v1` (frontend, branch `main`), `/opt/prism-platform` (backend, branch `main`),
  `/opt/PRISM/v2` (static v2 site), `/opt/prism-executor`, `/opt/prism-deploy-hook`.
- Hermes references: **84 in frontend** (incl. the live path `server/chat-proxy.mjs`, `api/chat.js`),
  **678 in backend** (mostly docs).

## Two blockers that must be handled, not discovered later

### 1. `frontend/` name collision
`pip.git` already has a `frontend/` directory — the abandoned Next.js app (123 files, never
deployed, documented as dead in CLAUDE.md). Moving pip into `backend/` would carry it to
`backend/frontend/`, which is absurd, and deleting it is a real decision.
**Proposed:** delete it in Phase 0, recoverable from history. Confirm with Arijit.

### 2. Removing Hermes is a rebuild, not a move
Hermes is the live grounded-chat brain. `chat-proxy.mjs` calls it over loopback
(`HERMES_API_URL`) for every Cassandra answer on every report, plus the Telegram path.
Deleting it before a replacement exists **kills live chat**.
**Proposed sequencing:** build Cassandra on the Claude Agent SDK inside `backend/`, prove
grounding parity (citations, refusal-to-fabricate) against real reports, cut `chat-proxy` over,
verify live, and only then remove Hermes. This is Phase 4 and is the largest piece of work in
this plan — it is a feature build, not a directory move.

## Phases (each ends at a verification gate; no phase starts before the previous gate passes)

### Phase 0 — Hygiene (low risk, do first)
1. Delete 187 tracked `.bak-*` / `.prelegalfix` files and the 7 stray root `*-audit-data.json`
   duplicates; add the ignore patterns (backend repo already has them).
2. Delete the dead Next app at `pip.git frontend/`.
3. Delete the merged feature branches in both repos (all are now contained in `main`), keeping
   `prism-v2` until Phase 5.
**Gate:** repo root shows only real files; `git log` still resolves every deleted file; site
unaffected (no deployed path touched).

### Phase 1 — Unify the repos, preserving history
1. In `prism.git`: move all current tracked content into `frontend/`.
2. Bring `pip.git` in under `backend/` with history preserved (`git subtree add` or
   `filter-repo` path rewrite then merge — subtree is simpler and sufficient).
3. Lift shared `docs/` to the root.
4. Archive `pip.git` on GitHub (read-only), do not delete.
**Gate:** one repo; `git log --follow` works across both lineages; tracked file count equals the
sum minus deletions; nothing deployed yet.

### Phase 2 — Repoint every path reference (this is the risky one)
Everything below currently hardcodes a path that changes:

| thing | now | becomes |
|---|---|---|
| `prism-chat-proxy` unit | `/opt/PRISM/v1`, `server/chat-proxy.mjs` | `/opt/prism/frontend` |
| `STATIC_DIR` | `/opt/PRISM/v1` | `/opt/prism/frontend` |
| `prism-platform` unit | `/opt/prism-platform` | `/opt/prism/backend` |
| `prism-platform` venv | `/opt/prism-platform/.venv` | `/opt/prism/backend/.venv` |
| `prism-runner` unit | `/opt/prism-platform/.venv/bin/python3` | `/opt/prism/backend/.venv/...` |
| `prism-v2-static` unit | `/opt/PRISM/v2` | decide in Phase 5 |
| deploy hook `REPO_DIR` | `/opt/PRISM/v1` | `/opt/prism` |
| `publish.sh`, generator output paths | flat/`reports/` | `frontend/reports/` |

Caddy needs no change (it proxies to ports, not paths).
**Gate:** all 5 services active; checksum every published report before and after and prove
byte-identical; `/`, `/reports/`, a legacy flat URL and `/healthz` all verified live.

### Phase 3 — Naming standardization
1. Rename `~/Dropbox/AI-Development/PIP` → `~/Dropbox/AI-Development/prism`.
2. Purge the "PIP" name from `CLAUDE.md`, `SESSION.md`, docs and the memory index; PRISM is the
   application name.
3. Update the Claude Code project memory path (it is keyed to the old directory name).
**Gate:** no stale `PIP` path references; a fresh session resolves `SESSION.md` correctly.

### Phase 4 — Cassandra on the Claude Agent SDK; remove Hermes
1. Build the grounded chat agent in `backend/` (report retrieval already exists: `report_chunks`
   + pgvector, live as of 2026-07-28).
2. Prove parity on real reports: grounded citations, refusal to answer beyond the report.
3. Cut `chat-proxy` from `HERMES_API_URL` to the new backend endpoint.
4. Verify live chat on a real report page.
5. Only then: stop the `hermes-prism` container, strip `HERMES_*` config, remove the 84 frontend
   references and the Telegram path.
**Gate:** live chat answers from the Claude agent with citations; Hermes container stopped and the
site still fully functional.

### Phase 5 — v2 branch
Recreate `v2` from the restructured `main` (the existing `prism-v2` branch carries the old flat
layout and would conflict wholesale). Port its unique work (per-instance marketer sections,
notebook rename) forward deliberately.
**Gate:** `v2` branches cleanly from the new `main`; `main` untouched.

## Open question for Arijit (not blocking Phase 0-3)

Generated report HTML (~600 KB per audit) is committed to git. It is build output from the
backend generators. Long term it arguably belongs in a deploy artifact or published branch rather
than source control — that is what makes the repo read as a dump. Not part of this directive;
flagged for a later decision.

## Risk register

| risk | mitigation |
|---|---|
| Hermes removed before replacement → chat dead | Phase 4 ordering; parity proven before removal |
| Path repoint breaks live site | baseline checksums before, verify after, keep old dirs until proven |
| History lost merging repos | subtree merge, verify `git log --follow`; archive `pip.git` |
| Old branches conflict after restructure | delete merged branches in Phase 0; recreate `v2` in Phase 5 |
| Deleting the dead Next app loses work | recoverable from history; confirm with Arijit first |

## Deferred (Arijit, 2026-07-28)

- **Merge `ia/`, `ia1/`, `ia2/` and establish why there are three.** Kept as-is at Arijit's
  instruction. No link from the live nav, but an unlinked page may still be a URL shared
  directly with a prospect, so they were not deleted.
- **Relocate Scout out of `/opt/prism`.** That path already contained Scout's source and backups
  (598 MB) before the restructure, so the app now sits beside it. Scout runs in Docker on 8421;
  moving it during a production cutover was declined. `/opt/scout` is the tidier home.
- **Generated report HTML in git.** ~600 KB per audit of generator output, but carrying hand-edits
  made on the live server, so it is no longer reproducible from the generator. Open question.

## Lessons from execution

Two directory nestings happened for the same reason: `mv`/`git mv` into a destination that
already existed silently nests instead of replacing.
- `mv /opt/prism.new /opt/prism` nested at `/opt/prism/prism.new` because `/opt/prism` already
  held Scout.
- `git mv backend/docs docs` nested at `docs/docs` because an untracked local `docs/workspace`
  already existed.
**Heuristic:** before any move, test the destination for existence explicitly. Do not infer that
a path is free because it was not in a listing that had been filtered.
