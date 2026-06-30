# SESSION.md — PRISM marathon (gemini migration · prism.chowmes.com hosting · BuiltWith→detect-search · techstack rebuild)

**Status:** Continuation session. #5 demo page LIVE; detect-search verified+versioned; **all 3 branches
PUSHED**; Cass portraits generated (awaiting user pick to deploy avatar). Branch `feat/prism-e2e-cycle`
(PIP); skills `feat/gemini-grounded-search` (== origin/main); hub `feat/prism-vps-hosting`.

**Last updated:** 2026-06-30 ~12:00am EDT

## THIS CONTINUATION SESSION (2026-06-30)
- **#5 about page LIVE** — reviewed, deployed `scp → /opt/prism-hub/about/`; https://prism.chowmes.com/about/
  HTTP 200, MD5 verified. Branded, reuses audit design system, 7 sections, content accurate.
- **detect-search DONE** — VPS `npm install` + chromium were cached; **live-verified** `--full-tech` on
  petsmart (Algolia detected, 14 categories, exit 0). **Versioned**: vendored into arijit-skills at
  `skills/detect-search/` (committed `80e3245`, pushed to main); `~/.claude/skills/detect-search` now a
  **symlink** into the repo (backup `~/.claude/skills/detect-search.prelink-bak-20260629`). node_modules +
  runtime workspace gitignored.
- **Branches PUSHED** — skills feature pushed + **main fast-forwarded** (`80ae128..80e3245`, main==feature,
  reconcile DONE). hub `feat/prism-vps-hosting` pushed (about page, Cassandra rename, 4 audit-data.json).
  PIP `feat/prism-e2e-cycle` pushed.
- **Cass portrait** — read SOUL (`/root/.hermes-prism/SOUL.md`, sudo). VPS key supports Imagen 4 /
  gemini-3-pro-image. Generated 4 candidates via `imagen-4.0-generate-001`, pulled to
  `~/prism-hub/assets/cass-candidates/cass-{0..3}.png` (gitignored). **AWAITING user pick** → then deploy as
  SPA chat avatar (chat-widget.js) + Telegram avatar. Recommendation: cass-3 (dry knowing smile), cass-1 2nd.
- ⚠️ **Concurrent process active** — kept committing to arijit-skills (`1598f39`,`80ae128`) AND modifying
  ~10 hub report `index.html` (re-render). Left those hub edits UNSTAGED/uncommitted (not mine to commit).

---

## RESUME ACTION (next session — do in order)
1. Read this file + MEMORY.md. Use `dangerouslyDisableSandbox:true` on EVERY VPS bash (raw-TCP egress is
   sandbox-blocked; `ssh chowmes-vps ...` works unsandboxed). Don't storm the VPS — batch commands.
2. **Check the in-flight #5 demo page**: subagent built `/Users/arijitchowdhury/prism-hub/about/index.html`
   (the "what is PRISM" branded one-pager for the Friday demo to 200 people). Open it, review sections +
   branding match, show the user, then deploy: `scp ~/prism-hub/about/index.html chowmes-vps:/opt/prism-hub/about/index.html`
   (mkdir the dir) → live at `https://prism.chowmes.com/about/`. (Subagent id was `afe8900f3f03893b5`.)
3. Continue the open thread (the user's 6-item list — see THREAD below) + the global pending queue (PENDING).

---

## ENVIRONMENT / ACCESS (verified this session)
- VPS alias `ssh chowmes-vps` = chowmesadmin@72.61.72.147, key `~/.ssh/chowmes_ed25519`. ControlPersist on.
- **Skills repo**: `/Users/arijitchowdhury/Dropbox/AI-Development/Personal/arijit-skills` (GH:
  github.com/arijitchowdhury80/arijit-skills). `~/.claude/skills/algolia-*` symlink into
  `skills/algolia-audit-skills/`. Edit→commit. On VPS the skills live at `/home/chowmesadmin/.claude/skills/`.
- **detect-search** = `~/.claude/skills/detect-search/` — STANDALONE, **NOT a git repo** (unversioned!).
- **Hub repo** = `~/prism-hub` (GH renamed → prism-hub). Static reports SPA + chat. Served on the VPS at
  `/opt/prism-hub` (NOT Vercel anymore — see Thread-B history below).
- Keys on VPS: `GEMINI_API_KEY` in `/root/.hermes-prism/.env` (paid, works); `SCOUT_API_KEY` in
  `/opt/prism-platform/.env`; Hermes bearer `API_SERVER_KEY` in `/root/.hermes-prism/.env`. Executor OAuth
  token (Claude subscription) at `/opt/prism-executor/.claude-oauth.env` (CLAUDE_CODE_OAUTH_TOKEN); GEMINI+SCOUT
  for skill runs at `/opt/prism-executor/.run.env`.

## OPERATIONAL GOTCHAS that bit me (avoid re-hitting)
- **zsh does NOT word-split unquoted `$VAR`** → `for x in $LIST` runs ONCE. Use arrays: `ARR=(a b c); for x in $ARR`.
- **macOS has no `timeout`** (exit 127). Use Python `subprocess(timeout=)` or `gtimeout`, not `timeout`.
- **rsync silently skipped dirs** ("cannot delete non-empty directory") → files NOT synced. Verify per-file
  on the VPS after sync (grep), or scp each file explicitly. Don't trust rsync exit 0.
- Subagents make mistakes (a blanket-gemini mis-route; a blind-sed broke pages). VERIFY their work independently.

---

## WHAT LANDED + COMMITTED THIS SESSION

### Commits (NONE pushed)
- arijit-skills `feat/gemini-grounded-search`: `864f8c6` gemini migration · `9966d8b` BuiltWith removal ·
  `ef458f8` techstack rebuild.
- prism-hub `feat/prism-vps-hosting`: `072564b` on-VPS chat proxy · `4db8be2` landing logo fix.
- PIP `feat/prism-e2e-cycle`: `c19cfec` SESSION checkpoint (this file supersedes it).
- ⚠️ A PARALLEL process pushed arijit-skills **main → v2.0.0** (READMEs added; see MEMORY
  "feedback-parallel-user-commit-mid-session"). My feature branch needs reconciling/merging with main.

### Thread 1 — Gemini-grounded research migration ✅
Right-tool rule (USER'S REPEATED CORRECTION — internalize): **Scout** = acquire the TARGET's own data
(company, execs, careers/jobs, IR). **Gemini-grounded Google search** = OPEN-WEB research (benchmarks,
analyst quotes, news, competitor tech). **detect-search** = keyless tech/search-vendor. **yfinance** = public
financials. NO WebSearch, NO fabrication (ungrounded → blank).
- `scripts/gemini_search.py` (CLI helper, 6 tests, live grounded) + `platform_utils.gemini_search_results()`
  (Tavily drop-in — returns grounded PROSE as result content since google_search can't emit JSON; single
  result; ungrounded→[]; 6 tests). 16 SKILL.md migrated. `collect-industry.py` + `collect-exec-media.py`
  swapped off Tavily (collect-news=Apify, collect-investor=WebFetch/Yahoo never used Tavily). intel-hiring
  re-routed: Layer1=Scout careers page, Layer2=gemini third-party boards.

### Thread 2 — BuiltWith removed; no paid MCP keys anywhere ✅
"Blocker B" is DEAD. BuiltWith (no key, no role) GONE; Yahoo = **yfinance** public (collect-financials.py
already used it — fixed the SKILL wording, no code change); **Algolia MCP has no role** in a prospect audit.
Only MCP the pipeline needs = **chrome** (browser) + apify (news). `collect-techstack.py`/`collect-company.py`
de-BuiltWithed; ~12 docs cleaned. `run-audit.sh` + `.mcp.json` on VPS stripped to chrome+apify.

### Thread 3 — Tech-stack rebuilt on detect-search --full-tech (keyless) ✅ (code) / ⚠️ (VPS deploy)
`detect-search.js` ALREADY had a `--full-tech` mode; extended it: **multi-page** capture (home/PLP/PDP/search/
cart), +5 curated categories (payment, CDP, frontend_framework, marketing_automation, hosting), + a pluggable
**open-DB fallback** (`tech-fingerprint-db.js` + `fingerprints/` — seed only; drop the full webappanalyzer DB
in to upgrade). NEW bridge `scripts/map-detect-tech.py` (--full-tech JSON → `02-tech-stack.json` schema; 47
tests). `collect-techstack.py` rewired to invoke engine+bridge (resolves detect-search at
`~/.claude/skills/detect-search`). **Live-verified locally on petsmart: 14 techs, Algolia detected, 4 pages.**
Fixed a bridge bug: `algolia_detected` read `platform_id` but engine uses `id` → now checks both.
⚠️ **detect-search on the VPS is NOT runnable yet**: `package.json` was just synced but `npm install` +
`npx playwright install chromium` in `/home/chowmesadmin/.claude/skills/detect-search/` STILL NEEDS to run
(first attempt failed — package.json hadn't synced). Until then techstack runs locally only.

### Thread B (history) — PRISM self-hosted under prism.chowmes.com on the VPS ✅
chowmes.com bought (Hostinger DNS). `prism` A → VPS, `scout` A → VPS. **Everything under prism, on the VPS**
(user decision; not Vercel). Caddy `/home/chowmesadmin/lab-judge/Caddyfile`: `prism.chowmes.com` →
`reverse_proxy 127.0.0.1:8651` = `prism-chat-proxy.service` (Node, serves static `/opt/prism-hub` + `/api/chat`
→ Hermes loopback 8642). `scout.chowmes.com` → 8421. **judge.contentengagement.info DECOUPLED**: removed its
`/scout` + `/hermes-api` path blocks (now 404). Chat verified grounded over HTTPS. Proxy src =
`~/prism-hub/server/chat-proxy.mjs`. (Vercel front retired; apex chowmes.com still lingers in Vercel account, harmless.)

---

## THE OPEN THREAD (user's 6-item message, last turn) — status
1. **Landing-page chat absent** — ANSWERED: by design (grounded RAG binds to one audit; landing has none).
   Open option: add a general (non-audit) PRISM Q&A mode to the landing if wanted.
2. **Chat said "PRISM", she's Cassandra** — rename DONE + LIVE (chat-widget.js header → "Cassandra", deployed).
   STILL TODO: give Cassandra a **personality** (read her Hermes SOUL) + **generate a portrait** based on it,
   use SAME image as SPA chat avatar AND Telegram avatar. NEEDS image-gen (Gemini Imagen / OpenAI key on VPS) — not yet done.
3. **Index cards alphabetical** (quick: JS sort-on-load over the static cards) + **tile UI won't scale to
   hundreds** (future redesign). TRACKED, not priority.
4. **Was the report-standardization run done?** — ANSWERED: Wave-1 (10 with-data) DONE+committed; Wave-2
   (7 dataless) BLOCKED (missing data source + flagged keys). Ledger:
   `docs/workspace/hermes-prism-integration/spike-unify-audit/run/FINAL-REPORT.md`.
5. **PRISM one-page branded demo deck (HTML)** — TOP PRIORITY, **IN FLIGHT** (opus subagent building
   `~/prism-hub/about/index.html`). For Friday demo to 200 AI enthusiasts. Content + branding spec given (what/
   who/produces/how/skills+GH-grouping/Hermes-as-execution-layer). REVIEW its output + deploy to /about/.
6. **Unify the background animation** across landing + audit pages into ONE shared design library. QUEUED
   (relates to #5's output — the demo page reuses the audit background; extend that into a common include).

---

## PENDING QUEUE (global — beyond the 6-item thread)
1. **detect-search**: (a) put it under version control (git-init or fold into arijit-skills) — currently
   UNVERSIONED; (b) finish VPS `npm install` + `playwright install chromium` so techstack runs on the executor;
   (c) then live-verify `collect-techstack.py` on the VPS.
2. **Chat-trigger** — Cass starts an audit from a chat message (Thread C; not built). Path: plugin intent →
   prism_platform endpoint → spawn `/opt/prism-executor/run-audit.sh <domain>`.
3. **Full e2e audit run** on a real domain with the new keyless muscle (NEVER run end-to-end). The real proof.
4. **SimilarWeb dead key** (traffic module) — separate blocker; traffic stays blank until resolved.
5. **Push branches** + reconcile arijit-skills feature branch with the parallel `main` v2.0.0.
6. **Rotate the leaked OAuth token** (it appeared in chat earlier) — user re-runs `claude setup-token`, I swap
   `/opt/prism-executor/.claude-oauth.env`.
7. Cassandra portrait (#2) + landing alpha-sort (#3) + unified background (#6).

---

## HARD CONSTRAINTS (user)
- **Right tool for the job** — Scout vs Gemini-grounded vs detect-search vs yfinance; do NOT blanket-route.
- **NO fabrication** — blank stays blank; ungrounded → null.
- **PRISM orchestrates skills, never rebuilds research/synth.** No paid data-MCP keys (none needed).
- **Everything under prism.chowmes.com** (VPS-hosted). judge.contentengagement.info is SEPARATE.
- **Frontend builds route through the frontend-design skill.** Plain language. Don't storm the VPS.

## NOT DONE / NOT TRUE (no false claims)
- #5 demo page NOT reviewed/deployed (subagent still running). detect-search NOT runnable on VPS yet, NOT
  version-controlled. Chat-trigger NOT built. Full e2e audit NEVER run. Branches NOT pushed. OAuth token NOT
  rotated. Cassandra portrait NOT generated. Landing NOT alpha-sorted. Background NOT unified. Wave-2 (7) audits NOT done.

## FILES WRITTEN THIS SESSION (key)
- Skills: `scripts/gemini_search.py`, `scripts/platform_utils.py` (+gemini_search_results), `scripts/map-detect-tech.py`,
  `scripts/collect-techstack.py`, `scripts/collect-company.py`, `scripts/collect-industry.py`, `scripts/collect-exec-media.py`,
  `scripts/tests/test_gemini_search*.py`, `scripts/tests/test_map_detect_tech.py`, 17+ SKILL.md/REFERENCE/AGENT-CONTEXT/platform.config.
- detect-search: `detect-search.js` (multi-page+categories+opendb hook), `tech-fingerprint-db.js`, `fingerprints/{technologies.json,README.md}`.
- Hub: `server/chat-proxy.mjs`, `index.html` (logos), `chat-widget.js` (Cassandra), `about/index.html` (IN FLIGHT).
- VPS: `/opt/prism-executor/run-audit.sh` (rewired), `.run.env`, `.claude-oauth.env`; `.mcp.json` (chrome+apify);
  `/opt/prism-chat-proxy/` service; Caddyfile prism block + judge paths removed; `/opt/prism-hub` static.
- Memory: `feedback-claude-cli-setup-token-headless.md` (+ this session's new ones).
