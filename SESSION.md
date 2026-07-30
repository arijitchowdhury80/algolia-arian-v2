# SESSION.md — Monorepo restructure, then: the v2 pipeline was dead (2026-07-28 → 29)

**Persist run 2026-07-29 (evening): resume state below is unchanged since the ~03:45–05:00 write
below — nothing further executed after that block, this is a verification/persist pass only.**

## ⏭ LATEST SESSION (2026-07-29, ~03:45–05:00) — read this block first

**Headline: the v2 backend module pipeline could not execute a single module, and had not been
able to for some time.** Asked to run one audit end-to-end, I ran it and it failed **13/13 with
0 LLM calls** — every module `401 Unauthorized` from `api.perplexity.ai`.

**Correction to the block below:** it says Perplexity is "the only working synthesis provider."
It is not working at all. The key is byte-identical on the laptop and the VPS (sha
`986f16fb4d8c`) and returns 401 **from the VPS itself**. It also says `GEMINI_API_KEY` is unset
on that box — true for `/opt/prism/backend/.env`, but `/opt/prism-executor/.run.env` **does**
carry a working Gemini key. Two separate env files.

**Why nobody noticed:** there are **two audit engines**. The 19 published reports all come from
the executor (`/opt/prism-executor`, `prism-runner` :8770, `run-audit.sh` + `claude -p`
algolia-* skills, Gemini + Scout). That engine never touches Perplexity. The v2 backend pipeline
is the half-built one, and it is the half the restructure moved.

**Root cause, and it was not just a dead key:** all six call sites constructed
`AgentAPIClient(perplexity_key)` directly. No factory. So the provider was hardcoded six times,
`ENRICHER_PROVIDER` was decorative (logs printed `provider=gemini` while every call went to
Perplexity), and `GeminiResearchClient` — a complete, tested, drop-in replacement — was wired
nowhere.

**Fixed (commits `a6b743e`, `cf7a2d5`, local only — NOT pushed):**
- `backend/prism_platform/v2/research_client.py` — `make_research_client()` /
  `resolve_research_provider()` as the single provider decision point, `ResearchClient` Protocol,
  new `RESEARCH_PROVIDER` setting kept **separate** from `ENRICHER_PROVIDER` so a synthesis-only
  provider like `anthropic` can never silently route research to Perplexity. Unsupported or
  keyless selection **raises**; no silent fallback.
- Evidence gate: `ModuleConfig.requires_citations` (default **True**). A module that must cite
  and returns none is retried once, then downgraded to **`partial`** with an explicit error.
  Output is kept, but nothing downstream can mistake unsourced data for evidenced data.
  `intel-queries` opts out (generated test queries, nothing to cite).
- Retry now covers all three intermittent provider faults — empty response, missing citations,
  unparseable JSON — and keeps the **better** of the two attempts.
- `json.loads(..., strict=False)`: Gemini emits literal newlines/tabs inside JSON strings.
- `diagnose_pipeline.py` now **exits non-zero** on failure (it reported `EXIT=0` with 13/13
  failed) and puts the repo root on `sys.path`.

**Result: 0/13 → 13/13 executing on Gemini.** Suite 903 passed / same 7 pre-existing Mac-local
Scout failures. `mypy --strict` clean on the touched v2 modules.

**Three defects found on the way:**
1. The laptop backend had **no `.env`** — left behind in retired `PIP/`. Copied over, gitignored.
2. The venv's **editable-install map is frozen at install time**, so `python scripts/foo.py`
   raised `ModuleNotFoundError` on a newly added module while `pytest` imported it fine — a
   script can silently diagnose a stale copy. Console scripts (`.venv/bin/mypy`) also still have
   shebangs pointing at the old `PIP/` path. **The venv needs recreating after the move.**
3. `prism-runner` (User=`chowmesuser`) could not publish: its target
   `/root/.hermes-prism/reports` sat inside Hermes' private data dir.

**Store permissions — partly done, blocked by design.** Added group `prismpub`, put
`chowmesuser` in it, set `reports/` to `root:prismpub 2775` + files 664 (baseline saved at
`/opt/prism-backup/store-perms-baseline-20260729-042645.txt`). Verified the service picked up the
group (MainPID groups `987 10001`) and that it can create a slug dir and write `index.json`.
**But the parent `/root/.hermes-prism` reverted 710 → 700 within ~3 minutes** — Hermes itself
re-locks its data dir (`os.chmod(parent, 0o700)` appears throughout its auth/oauth code). So
traversal is denied again and publish is still blocked. **Perms juggling cannot win here.** The
real fix is to move the publish target out of Hermes' private dir (e.g. `/srv/prism-reports`),
mount it into the container at `/opt/data/reports`, and set `PRISM_STORE_DIR`. That changes a
live container's mount, so it needs an explicit yes. Not done.

**Open quality question (needs a decision):** grounding citations are non-deterministic run to
run. The gate now flags unsourced output as `partial` rather than hiding it, but whether an audit
may ship with `partial` modules is a product call. Also unresolved: whether to force valid JSON
at the API level (Gemini `responseMimeType`/`responseSchema`) instead of retrying — that needs a
documented check on whether structured output can be combined with Google-Search grounding.

**Next actions:** (1) prospect domain for the skills-engine run — still needed from Arijit;
(2) decide on the store-dir move; (3) add `GEMINI_API_KEY` to `/opt/prism/backend/.env` before
deploying, or the deploy is a no-op that still resolves to the dead Perplexity key;
(4) the two signed-in checks below still need Arijit.

---

**Last updated: 2026-07-29 ~03:00 (handoff).**
**Repo is now `~/Dropbox/AI-Development/prism`.** `PIP` is retired — that name only ever came from a
folder name. Launch `claude` from here so this file and the memory slug resolve.

## STATUS (one line)

PRISM is now ONE repo (`frontend/` + `backend/` + `docs/`), identical on laptop, VPS (`/opt/prism`)
and GitHub, **live and verified at `3a46557`**; phases 0-3 of the restructure plan are complete, the
branch sprawl is closed, pgvector is installed and migrations are unblocked — but **the pipeline is
unproven**: no authenticated chat, no signed-in redirect test, no audit run since the change.

## ▶ RESUME ACTION (numbered, concrete)

1. **Arijit verifies the two things I could not** (both need a real signed-in session; anonymous
   requests hit the auth gate first, which is why I could not reach them):
   - Open `prism.chowmes.com/dell/` while signed in → must **301 to `/reports/dell/`**.
   - Send Cassandra a message on any report. `handleChat` was changed for ACL gating and only the
     anonymous-401 path was proven. **No authenticated chat has ever been exercised.**
2. **Run one audit end-to-end.** The least-tested surface after all of this.
3. **Phase 4** of `docs/plans/2026-07-28-prism-monorepo-restructure.md` — rebuild Cassandra on the
   Claude Agent SDK, prove grounding parity on real reports (citations, refusal to answer beyond the
   report), cut `chat-proxy` off `HERMES_API_URL`, verify live, and **only then** remove Hermes.
   Hermes is still the live chat brain for every report plus Telegram. Removing it before parity is
   proven kills chat. The retrieval layer it needs (`report_chunks` + pgvector) went live this
   session, so the foundation exists.
4. **Phase 5** — recreate `v2` from the restructured `main`. The existing `prism-v2` carries the old
   flat layout and would conflict wholesale; port its unique work (per-instance marketer sections,
   notebook rename) forward deliberately.

## ⚠️ TWO TRIPWIRES

- **`main` auto-deploys on push.** The hook (`/opt/prism-deploy-hook`) watches `main` with
  `REPO_DIR=/opt/prism`. Never push a path change before the VPS is ready for it. This is new as of
  this session and it already caught me once.
- **Do NOT flip `ACL_ENFORCEMENT_ENABLED`.** Multi-tenancy is deployed but dormant *by design*
  (spec §10, ships dark). All 18 audits are owned by `system`/`cassandra` placeholders, `users` is
  empty, and `can_user_see` is default-deny — enforcing today **404s every report for everyone**,
  Arijit included. Ownership has to map to real Clerk user IDs first.

## WHERE WE STOPPED (exact)

Committed and pushed `3a46557` (the docs-path class fix), verified it deployed to the VPS, restarted
`prism-platform`, and confirmed all three previously-broken paths resolve (`exists: True`). Then ran
`/persist` + `/handoff`. Nothing was in flight.

## WHAT LANDED

**One repo.** `github.com/arijitchowdhury80/prism` = `frontend/` (landing page, published reports,
Node web+chat server, role pages, IA prototypes) + `backend/` (FastAPI, alembic, generators, v2
modules) + `docs/`. Backend came in by **subtree merge**, so history is preserved rather than
squashed: 464 commits, `43c0c4e` a genuine ancestor, `git log --follow` works across the move.

**Production cut over.** `/opt/PRISM/v1` → `/opt/prism/frontend`; `/opt/prism-platform` →
`/opt/prism/backend`; venv, runner, and deploy hook all repointed. Five systemd units rewritten.

**Audits moved under `reports/`.** Arijit reversed the earlier keep-flat decision in favour of
consistency with `prism-v2`. Legacy flat URLs 301-redirect, driven off what exists on disk (not a
hardcoded slug list, so it cannot drift). The redirect sits **after** the auth gate deliberately —
redirecting first would confirm to an anonymous caller which companies are audited, and the slug
list is prospect-confidential. A pre-existing test encoded exactly that property.

**pgvector installed; migration chain unblocked 009 → 012.** It had been stuck since early July for
**two** reasons, not one: `postgres:16-alpine` ships no pgvector, **and** two branches each numbered
their migration `011`, so alembic refused to move at all ("Multiple head revisions"). Swapped to
`pgvector/pgvector:pg16` (same 16.14, data on a named volume, reindexed for the musl→glibc collation
change) and renumbered the ACL migration to 012.

**Branch sprawl closed.** Eight agent-created branches merged into `main` and deleted; only `main`
and `prism-v2` remain. Rollback SHAs recorded before deletion (`feat/prism-vps-hosting` = `3b13838`).

**Scout moved out to `/opt/scout`.** It was **never embedded** — separate repo, own remote, never
tracked here, reached over HTTP at `SCOUT_BASE_URL=http://127.0.0.1:8421`. It had only occupied the
`/opt/prism` path. Zero downtime; the Compose project name stays `docker` (it derives from the
`docker/` subdirectory) so `docker_scout-data` reattached with no migration.

**Cassandra's landing-page framing corrected** at Arijit's instruction: the "Cassandra Live" avatar
card misrepresented her (she is the grounded report guide, not the LiveAvatar sandbox). Her plain
portrait is restored; the live-avatar experiment stays confined to the report chat drawer.

**Hygiene:** 199 committed junk/dead files removed — 187 `.bak-*` backups, 7 duplicate root JSONs,
the dead Vercel serverless layer, the abandoned Next.js app. Root went 79 files → 7. Ignore rules
hardened. `PRISM_TRUST_SECRET` generated and shared between the proxy and FastAPI.

## FIVE DEFECTS CAUGHT THAT WOULD OTHERWISE HAVE SHIPPED

1. **Auth would have regressed to fail-open, twice.** Both `feat/ia-ab-prototype` and
   `feat/audit-acl` were written against an older auth base whose `checkAuth` returned `{ok:true}`
   when Clerk was absent, with `/api` in the public allowlist. Naive merges would have silently
   opened the reports. Production's fail-closed gate was kept and the ACL layer grafted onto it.
2. **A boot-time crash.** A duplicate `/sign-in` handler survived *outside* the conflict markers,
   referencing a `SIGN_IN_HTML` constant the resolution dropped.
3. **Live audit data would have silently stopped updating.** `serveStatic`'s DB-live injection regex
   matched a single path segment, so under `reports/<slug>/` every report would have quietly stopped
   receiving fresh data from Postgres — still rendering, just stale.
4. **Git silently 3-way-merged the generated report HTML** — no conflict, so it never surfaced for
   review — dropping a responsive CSS rule from 16 reports and an overview-tab JS block from four.
   Restored from production's content; all 19 then verified byte-identical to baseline.
5. **Lifting `docs/` to the root broke eight backend-relative paths.** 878 passing → 57 errors. The
   live site and frontend tests never touch those paths, so everything looked green; only the backend
   suite exposed it. This is the one that nearly shipped.

## DECISIONS LOCKED

- One repo, `frontend/` + `backend/`; `pip.git` retired; "PIP" name dead. PRISM is the app name.
- Audits live under `reports/<slug>/`; legacy flat URLs redirect rather than 404.
- Redirect runs **after** the auth gate (slug list is confidential).
- Laptop = development, VPS = production, GitHub = backup; `v2` is a branch.
- Hermes removal happens **only after** a Claude-Agent-SDK Cassandra proves parity.
- `ia`/`ia1`/`ia2` kept as-is for now; merging them is deferred, not dropped.
- Generated report HTML stays in git for now — it carries hand-edits so it is no longer reproducible
  from the generator. Whether that should change is an open architectural question.

## WHAT HAS **NOT** BEEN DONE (prevents false completion claims)

- **No authenticated chat has been exercised.** Only anonymous-401 was proven.
- **No signed-in redirect test.** Unreachable anonymously.
- **No audit run end-to-end** since any of this.
- **Phases 4 and 5 not started.** Phase 4 is a feature build, not a move.
- **`~/Dropbox/AI-Development/PIP` not retired** — this session's shell was rooted there, and
  renaming it mid-session breaks the remaining commands. Safe to rename/delete now; nothing at risk
  (0 unpushed, 0 commits off-remote).
- **Old rollback dirs still present:** `/opt/PRISM/v1` and `/opt/prism-platform`. Deleting them frees
  a duplicated 5.5 GB venv. Kept deliberately as the rollback path.
- **Perplexity not removed.** Still live in production, and `GEMINI_API_KEY` is unset on that box, so
  it is currently the only working synthesis provider. Replace the callers first.
- **Scout runs an unmerged branch in production** (`fix/launch-readiness-fx1-fx7`). Different app,
  recorded not acted on.
- **`ia`/`ia1`/`ia2` not merged**; the "why are there three" question is open.

## VERIFIED THIS SESSION (evidence, not assertions)

| check | result |
|---|---|
| Live site | `/` `/healthz` `/about/` 200; gated paths 302 |
| Landing checksum | `ce18d080398351e8` (matches post-fix baseline) |
| **All 19 published reports** | **byte-identical to pre-change baseline** |
| Database | 348 rows, unchanged across the image swap and 3 migrations |
| Scout | `/health` 200; `scout.db`, `hosted_accounts.sqlite`, 599 run dirs intact |
| Services | 5/5 active |
| Frontend tests | 42/42 pass |
| Backend tests | 873 pass / 7 fail / 0 errors — the 7 pre-existing (Mac-local Scout path dep) |
| Repo-relative paths | resolve on **both** laptop and `/opt/prism` |
| Deploy hook | proven end-to-end (fetched, deployed, restarted the service itself) |

## MY OWN MISTAKES THIS SESSION

- **Two directory nestings, same root cause:** `mv`/`git mv` into a destination that already exists
  silently nests. `/opt/prism` already held Scout; `docs/` already existed as local scratch. Neither
  reached production. Heuristic banked in memory `feedback-move-into-existing-dir-nests`.
- **Reopened a settled decision** (the flat-vs-`reports/` layout) after Arijit had already decided,
  which cost real time.
- **My first redirect implementation leaked the prospect slug list** by redirecting before the auth
  gate. Caught by Arijit's own pre-existing test, fixed, and a regression test added.
- **Over-restored the Cassandra section** on the first attempt, dragging back copy Arijit had not
  asked for; corrected to the minimal change.

## REFERENCE FILES

- Plan: `docs/plans/2026-07-28-prism-monorepo-restructure.md` (phases, gates, deferred items,
  lessons)
- Vault: `Projects/PRISM/index.md` (compiled truth above the divider), `log.md`, `tasks.md`
- Memory: `~/.claude/projects/-Users-arijitchowdhury-Dropbox-AI-Development-prism/memory/`
  (`reference-one-repo-frontend-backend`, `session_pointer`,
  `feedback-move-into-existing-dir-nests`)
- VPS access: `ssh chowmes-vps` (user `chowmesadmin`)
- Backups taken this session: `/opt/prism-backup/` — pre-pgvector DB dump, pre-redeploy backend
  tarball, systemd unit copies, env-file copies

## FILES WRITTEN THIS SESSION (repo)

Restructure touched ~1,150 tracked files (moves). Substantive edits:
`frontend/server/chat-proxy.mjs` (auth resolution, legacy redirect, DB-live regex, STATIC_DIR),
`frontend/index.html` (Cassandra portrait, nav, hero), `frontend/reports/index.html` (hrefs),
`frontend/README.md`, `frontend/tests/{auth-gate,liveavatar,landing-page}.test.mjs`,
`backend/prism_platform/api/routers/landing_pages.py`, `backend/scripts/render-notebook.py`,
`backend/alembic/versions/012_add_users_audit_shares_seen_assertions.py` (renumbered),
plus 8 files repointed for the `docs/` lift, new root `README.md`, `CLAUDE.md`, `.gitignore`.

Commits: `b521155` `c16029b` `08030d1` `2fb8c0f` `1d032cd` `04ecee4` `5b4d6c4` `79bde0b` `22ec767`
`00bf373` `0f1b98b` `c8d65ed` `a654dd0` `3a46557`.
