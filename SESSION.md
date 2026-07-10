# SESSION — PRISM/PIP · 2026-07-09 night (Lululemon full re-validation → pipeline reliability crisis → unification plan)

## Status
Lululemon's audit is now correct and verified end-to-end (23-dimension factcheck, live external verification). Three systemic bugs that were silently affecting every audit in this pipeline are fixed. The real root cause — a GitHub repo and a live VPS execution path that have drifted apart across ~40 skills — is named and partially fixed. A real live-fetch-from-Postgres architecture was started but is not finished (blocked on a real auth bug, correctly left unresolved rather than patched insecurely). A full plan to finish the cleanup is written and ready for a fresh session.

## Resume action (do this first, in order)
1. Read `arijit-skills/docs/PIPELINE-UNIFICATION-PLAN.md` on the VPS (`/opt/prism-executor/arijit-skills/docs/`) — it has the full phased plan and a "Corrections from the first draft" section you must read before touching anything (3 things I assumed were broken turned out to already work).
2. Push the pending GitHub commits: `cd /tmp/arijit-skills-push2-20260709 && git push origin main` (3 commits: `sync-live-page.py`, the plan doc x2). If that directory no longer exists (fresh machine/session), re-clone `arijit-skills` and re-apply from the VPS copies at `/opt/prism-executor/arijit-skills/`.
3. Get Arijit's answer on Phase 0's 2 open decisions (SPA rendering model: live-fetch vs. deploy-time bake; and who reviews the `algolia-search-audit` script reconciliation) before starting Phase 1.
4. Fix the Clerk-handshake bug blocking `/api/audit-data/{slug}` on `/opt/PRISM/v1/server/chat-proxy.mjs` (see "What has NOT been done" below) — this is the single highest-value next fix, it's what actually answers "why doesn't the page just read the database."

## Where we stopped (exact)
Mid-way through wiring Lululemon's live page to fetch from the new Postgres-backed API. The API endpoint works (verified via direct query — returns real, current data). The page's boot JS was patched to call it, but the auth check (`checkAuth`/`requireAuth` in `chat-proxy.mjs`) hits Clerk's "handshake" session-refresh flow for this route, which issues an HTTP redirect — `fetch()` follows it to an HTML page and fails to parse it as JSON. My first fix attempt (trust any cookie *named* like a session cookie without validating it) was correctly blocked by the safety classifier as a real auth-security weakening. The page currently falls back to its static baked-in data blob when the live fetch fails, so nothing is broken for users — it's just not doing the live fetch yet.

## Decisions locked (verified live this session, not left as design questions)
- **Postgres already has a real 13-table relational schema** (`accounts`, `audits`, `deliverables`, `module_executions`, `algolia_case_studies`, `algolia_quotes`, `algolia_gaps`, `algolia_proofpoints`, `algolia_advocates`, `algolia_customers`, `vertical_benchmarks`, `alembic_version`). `audits.audit_data` is a jsonb blob by current design — the open item is migrating module content out of it into the already-existing normalized tables, not designing a schema from scratch.
- **Crossbeam MCP is authenticated and works** — tested live this session (`get_account_context`, `find_overlap_partners` for lululemon.com), returned real data: an assigned Algolia owner (Erik Metke) and 60 partner overlaps including a CRM-confirmed commercetools customer relationship. The bug was never auth — `algolia-intel-partner`'s SKILL.md simply never calls any Crossbeam MCP tool.
- **Scout's local scrape is now enabled.** Was disabled via `SCOUT_PUBLIC_HOSTED_ONLY=true` in `/opt/prism/scout/.env`. Flipped to `false`, container recreated with `docker compose up -d --force-recreate` (plain `docker restart` does NOT reload `.env`), confirmed still `127.0.0.1`-only, verified working with a real authenticated scrape.
- **2 skills symlinked, repo↔live, cannot drift apart again**: `algolia-audit-factcheck`, `algolia-intel-traffic` (confirmed byte-identical first). Live path backups: `~/.claude/skills/{name}.bak-preSymlink-20260709`.
- **`algolia-search-audit` (the biggest skill) is correctly NOT symlinked** — confirmed real divergence in both directions (repo has 9 scripts + a `tests/` dir the live path lacks; live path has ~25 company-specific one-off `.js` scratch scripts the repo lacks). Needs manual pair-by-pair human review before any merge.
- **Gymshark's case-study proof was pointing at the wrong URL centrally** (Postgres `algolia_case_studies` table has it at `gymshark-recommend`, which doesn't carry the 6.2%→10% conversion stat — that's on a different page, `gymshark-headless`). A corrected INSERT is drafted (see Reference files) but was correctly blocked from running ad-hoc via SSH — needs a real migration, not a one-off write to a shared production table.

## Remaining work
- Fix the Clerk-handshake/fetch bug (highest priority — see "Where we stopped").
- Once fixed, roll the live-fetch page wiring to belk/dell/jbl/nike (currently Lululemon only).
- Run the Gymshark case-study migration properly.
- Wire `algolia-intel-partner` to actually call Crossbeam MCP tools instead of Gemini-grounded search.
- Investigate whether Scout can do interactive site-search (form fill + submit) — needed to verify specific job-posting claims on hiring; Scout's basic `/scrape` couldn't do it in this session's testing.
- Execute `PIPELINE-UNIFICATION-PLAN.md` Phases 1 (finish skill symlinking) through 7 (full re-validation of every existing company).
- `algolia-search-audit` manual script reconciliation (Phase 0.2 in the plan) — needs Arijit or a human reviewer, not something to automate blind.

## Reference files
- VPS: `arijit-skills/docs/PIPELINE-UNIFICATION-PLAN.md` — the full plan, read this first.
- VPS: `algolia-search-audit/scripts/sync-live-page.py` — the interim data-sync tool (repo + live path, both have it).
- VPS: `/opt/PRISM/v1/server/chat-proxy.mjs` — the live-fetch API route lives here (backup: `chat-proxy.mjs.bak-preLiveFetch-20260709`).
- VPS: `/opt/prism-executor/audits/lululemon/deliverables/lululemon-factcheck-report.md`, `-correction-manifest.md`, `-skill-feedback.md`, `research/FACTCHECK_GATE.md` — the full 23-dimension re-validation writeup (score 9.8/10, PROCEED).
- Local: `/tmp/arijit-skills-push2-20260709` — pending GitHub push (3 commits, not yet pushed at persist time).
- Gymshark migration SQL (drafted, not run):
  ```sql
  INSERT INTO algolia_case_studies (customer_name, url, industry, sub_vertical, use_case, features_used, key_results, status)
  VALUES ('Gymshark', 'https://www.algolia.com/customers/gymshark-headless', 'Retail', 'Athletic Apparel',
  'Headless commerce migration; AI-based merchandising replacing manual process',
  '["AI Synonyms", "AI-based Merchandising", "Dynamic Re-Ranking"]',
  'Search conversion 6.2% to over 10% · revenue from search users up 400%+ YoY · search usage +20%', 'customer');
  ```
- Vault: `Projects/PRISM/index.md` (compiled truth, updated this session), `log.md` (full narrative entry), `tasks.md` (updated task ledger).
- Memory: `project-prism-lululemon-fullrevalidation-2026-07-09`, `feedback-verify-before-assuming-infra-broken`, `two-copies-architecture-antipattern`.

## What has NOT been done (read this before claiming anything is finished)
- The live-fetch API works at the query level but is NOT actually serving live data to any page yet — the auth bug blocks it, and every page (including Lululemon) is still running on its static baked-in data blob as a fallback.
- Only Lululemon's data was fully re-validated this session. Belk/dell/jbl/nike got the earlier JS-rendering-bug fixes (from a prior thread this same night) but did NOT get the same deep citation/ROI/industry-context/Crossbeam-level re-validation Lululemon got.
- The `algolia_case_studies` Gymshark fix is drafted, not applied to the database.
- Crossbeam is verified working but NOT wired into the actual `algolia-intel-partner` skill instructions — the next real audit run will still show "Crossbeam unavailable" until that skill file is edited.
- `~/.claude/skills` still has ~40 skills never diff-checked against the repo — only 2 are confirmed safe and symlinked.
- No Pydantic schema enforcement exists anywhere in the pipeline yet (Phase 3 of the plan, not started).
- No per-skill factcheck gate exists yet — `module_executions.validation_json` is identified as the right hook but is not populated by anything (Phase 5 of the plan, not started).
- The pending GitHub push (`/tmp/arijit-skills-push2-20260709`, 3 commits) may or may not have been pushed by the time you read this — check `git log origin/main` before assuming either way.

## Files written this session
VPS: `algolia-audit-factcheck/scripts/factcheck_mechanical.py`, `algolia-search-audit/scripts/generate-audit-data.py`, `calculate-roi.py`, `sync-live-page.py` (new), `algolia-intel-traffic/README.md` (both repo+live), `algolia-intel-traffic/SKILL.md` (live path, deployed from repo's already-correct version), `/opt/prism-executor/audits/lululemon/{research,deliverables}/*` (traffic, tech_stack, executives, case studies, industry_context, partner_intel, solution map, factcheck report/manifest/gate/feedback), `/opt/PRISM/v1/lululemon/index.html` + `/opt/PRISM/v1/{belk,dell,jbl,nike}/index.html` (JS fixes + data resync), `/opt/PRISM/v1/server/chat-proxy.mjs` (new API route, WIP), `/opt/prism-chat-proxy/.env`, `/opt/prism/scout/.env`. Local: `docs/PIPELINE-UNIFICATION-PLAN.md`, this file, vault `Projects/PRISM/{index.md,log.md,tasks.md}`, memory files listed above.
