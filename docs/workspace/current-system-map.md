# Current System Map — PRISM

> Living boundary doc. Read this BEFORE building another slice, so nobody builds on dead code.
> Last verified: 2026-07-01 (much of the LIVE column probed directly on the VPS this night).
> Legend: 🟢 LIVE (in use, verified) · 🧪 EXPERIMENTAL (built, not the trusted path) · 🟡 STALE (superseded, keep for reference) · ⛔ DO-NOT-USE (dead / reverted / deleted).
> Scope: this spans three surfaces — the **PIP repo** (backend), the **prism-hub repo** (frontend, separate), and the **VPS runtime**. PRISM is not one repo.

## 🟢 LIVE — the trusted path

**The audit engine (this is the real product):**
- `arijit-skills` 22 `algolia-*` skills + `detect-search` — the actual audit engine. Symlinked into `~/.claude/skills`, and installed on the VPS. Verified: full Dell audit ran end to end tonight.
- VPS `/opt/prism-executor/` — `run-audit.sh` (headless `claude -p` runs the skills) + `prism-runner.py` (systemd `prism-runner.service`, loopback `8770`). Verified live.
- **Cassandra** = `hermes-prism` container (Hermes) — the executioner. Plugin `prism-report-qa` (grounding hooks + the new `run_audit`/`audit_status` tools). Reachable via web SPA (`/v1/responses`) + Telegram. Verified live.
- Repo source of both: `docs/workspace/hermes-prism-integration/chowmes-prism/` (plugin + `executor/`). Committed 2026-07-01 (`c789672`).
- Cass report store: VPS `/root/.hermes-prism/reports/<slug>/audit-data.json` + `index.json`. 10 Wave-1 audits + Dell.

**Supporting runtime (VPS, verified up):** Scout (`8421`), `prism-deploy-hook` (webhook to `git pull /opt/prism-hub`, `9099`), caddy, postgres, redis.

**The live site (frontend = `prism`):** repo `github.com/arijitchowdhury80/prism` (renamed from `prism-hub` on 2026-07-01), served from `/opt/prism-hub`, local `~/prism-hub`. Human-facing UI at prism.chowmes.com. Deploy branch the VPS pulls: `feat/prism-vps-hosting`. (Local folder still named `prism-hub`; rename to `~/prism` is a pending follow-up.)

**This repo (PIP = backend):** remote `github.com/arijitchowdhury80/pip.git` (renamed from `prism` on 2026-07-01), active branch `feat/prism-e2e-cycle`. NOTE: `prism.git` is now the FRONTEND, not this repo.

## 🧪 EXPERIMENTAL — built, not the trusted path (do not assume these are "the system")
- `prism_platform/` (FastAPI, VPS `:8000`, health OK) — a real running service, but it is NOT the audit engine. The audit runs through the skills + executor above, not through `prism_platform`'s own `run_pipeline`. Storage/chat scaffolding; confirm intent before extending.
- `frontend/` (Next.js app in this repo) — NOT the live site (prism-hub is). **Clerk login IS wired and active here** (`@clerk/nextjs`, `clerkMiddleware` protecting all non-public routes, `sign-in` + `(authenticated)` dirs). What was dropped was only the *backend per-user data layer* (see DO-NOT-USE), not login. Whether this app ships separately from prism-hub is the open question. Confirm before building on it.
- IA A/B prototype — lives in `prism-hub` on branch `feat/ia-ab-prototype` (`/ia/ia1` browse vs `/ia/ia2` chat). Paused.
- Downloadable artifacts (`docs/workspace/hermes-prism-integration/artifacts/` — `make_report.py`, `make_deck_pptx.py`) — recent, pilots rendered; active but evolving.

## 🟡 STALE — superseded, keep only for reference
- `docs/workspace/6-stub-modules/`, `phase2-standards-skills/`, `phase3-thinking-skills/`, `ae-journey-research/`, `intel-hiring-scout-phase4/`, `search-detector-validation/` — older build-phase and research workspaces. History, not current wiring.
- Google Drive vault (`ArijitOS-Brain`) — migrated to the Dropbox vault (`Arijit-Second-Brain`) 2026-07-01; kept only as backup. Canonical vault is now Dropbox.
- Branch `feature/v2-core-infrastructure` — old line.

## ⛔ DO-NOT-USE — dead / reverted / deleted
- **Vercel** — being retired. Hosting is the VPS (prism.chowmes.com). NOTE: a Vercel project `prism` (`algolia-arian-v2.vercel.app`) was still live as of 2026-07-01 and is being deleted (after repointing 23 in-repo refs first). Any "deploy to Vercel" instruction is wrong.
- `algolia-arian-v2` — on GitHub this is NOT a separate repo; it is prism-hub (renamed, old name redirects). **Never delete the GitHub `algolia-arian-v2` repo — it IS the live site's repo.** The stale local dup checkout `~/Dropbox/AI-Development/algolia-arian-v2` is being removed.
- Backend per-user multi-tenancy (`prism_platform` users table + `/api/v1/users/upsert` + migration 009) — reverted (`20f8467`), never deployed to the VPS DB. **Clerk LOGIN itself is LIVE, not reverted** (see below); only the PIP-backend per-user data layer was dropped. Login is gated at the prism-hub/frontend layer, not the PIP backend.
- v1 build (deterministic-module / custom-SaaS) — deleted long ago; only Wave-1 intel modules survived into v2. Naming canon: "PRISM" = Chowmes-PRISM only.
- Waves 2–6 of the original module plan — never built.

## Open questions to confirm (so this map hardens)
- `prism_platform/` — is it kept as the storage/chat/API layer, or is it dead weight now that skills+Cass do the audit? (Memory leans "peripheral.")
- `frontend/` Next.js — retire it, or is there a plan that revives it separately from prism-hub?
