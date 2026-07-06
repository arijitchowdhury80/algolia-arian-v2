# SESSION — PRISM/PIP · 2026-07-06 (huge multi-thread: V2 pivot+deploy, SimilarWeb HITL refresh, 3 audits fully completed)

## STATUS (headline)
Massive session. Four things SHIPPED + verified: (1) PRISM V2 strategic pivot + prism2.chowmes.com live; (2) all 18 companies' SimilarWeb traffic refreshed → Postgres (verified, HITL browser capture); (3) SimilarWeb marked PERMANENT HITL everywhere; (4) **Dell, Belk, Lululemon fully completed — factcheck PROCEED + fresh traffic rendered from DB + deployed live** (belk published first time). **NEXT TASK (in progress): build the DB-backed auto-render** so reports serve from the DB automatically (user explicitly requested this next).

## RESUME ACTION — do this FIRST
1. Read this file + `docs/PRISM-V2/06-v2-execution-map.md` (the V2 build spine) + `docs/PRISM-V2/08-fable5-handoff-prompt.md`.
2. **Continue the DB-backed auto-render build** (the systemic fix). Goal: the published report page reads its `audit_data` from the DB (via a `prism_platform` API endpoint) instead of static baked-in HTML, so a DB update reflects on the live site automatically. Currently reports are STATIC (re-rendered manually this session). See "REMAINING WORK" #1.
3. Standing rules still active: SimilarWeb = permanent HITL (memory `reference-similarweb-permanent-hitl`); data integrity absolute (memory `feedback-prism-data-integrity-absolute`); data house = VPS Postgres (memory `reference-prism-current-architecture-2026-07-06`).

## CURRENT ARCHITECTURE (verified this session — canonical)
- **Data:** Postgres on VPS, docker container `prism-platform-postgres-1` (db `prism`, user `prism`). Query: `ssh chowmes-vps 'sudo docker exec prism-platform-postgres-1 psql -U prism -d prism ...'`. Tables: accounts, audits (audit_data JSONB = source of truth), module_executions, etc. `audits.factcheck_score` is Numeric(3,2) — max 9.99.
- **Skills:** canonical = `arijit-skills` GH repo (github.com/arijitchowdhury80/arijit-skills), checked out VPS `/opt/prism-executor/arijit-skills`. Local `~/.claude/skills` synced from it this session.
- **Serving:** `prism.chowmes.com` (PROD) = Caddy → node prism-chat-proxy (:8651) → static `/opt/PRISM/v1` (was `/opt/prism-hub`, MOVED this session; 7 service refs updated). Git branch `feat/prism-vps-hosting`, deploy-hook pulls on push. Clerk-gated.
- **`prism2.chowmes.com` (V2)** = Caddy → `prism-v2-static.service` (python http.server :8652) → static `/opt/PRISM/v2` (git worktree of branch `prism-v2`). Basic-auth: **user `prism` / pass `AlgoliaPRISM2026`**. Serves AE/BDR/Marketer role doors + landing-page builder (Nike/Dell) + reports.
- **Caddy** = dockerized, host-network; live Caddyfile bind-mounted from `/home/chowmesadmin/lab-judge/Caddyfile` (edit THERE). Reload: `sudo docker exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile`.
- **VPS:** `chowmes-vps` (72.61.72.147, user chowmesadmin, sudo NOPASSWD). deno at /usr/local/bin/deno.
- **DEAD (never use):** SimilarWeb API key (483b77…, 401 forever, service gone — HITL only); Google Drive $ALGOLIA_AUDIT_DIR; Dropbox "Algolia Search Audit" folder + its 03-traffic-data.json files.

## WHAT SHIPPED THIS SESSION (all verified)
### A. Dell / Belk / Lululemon — FULLY DONE (factcheck PROCEED + fresh render + deployed)
- All 3: `factcheck_action=PROCEED`, `traffic.data_quality=verified-capture-full`, fresh monthly-visits in the live HTML (dell 27.38M / belk 12.48M / lululemon 39.35M), deployed to `/opt/PRISM/v1/{slug}/index.html`.
- **Belk was a WAF-blocked stub → now published first time.** Network-verified belk runs **Constructor.io** search (killer displacement angle) + full stack (SFCC/Demandware, Dynamic Yield, Certona, Tealium, Adobe Analytics, PerimeterX WAF). F05 (aggressive WAF) real-evidenced. **HONEST CAVEAT:** belk F01-F04 have NO query-specific screenshots — PerimeterX WAF blocks automated per-query testing (blocked on 2nd query). Nulled honestly; findings stand on description + verified stack.
- **How (reusable pattern):** export DB audit_data → `docs/temp/migrate_schema.py` (fixes schema drift: severity HIGH/MEDIUM→critical/moderate, abx day→str + channel enum + email_body→body + video-without-script→email, icp algolia_product→product + pain fill) → write back to DB → `deno run render-audit.ts {slug} site` (on VPS, from a dir holding {slug}-audit-data.json) → cp index.html to `/opt/PRISM/v1/{slug}/` → factcheck_mechanical.py against deployed dir. Score must match breakdown recalc (fixed lululemon 4.3→4.0).

### B. SimilarWeb traffic refresh — all 18 → Postgres (verified)
- Full schema captured per company (visits/engagement/device/channels/geo/organic/paid keywords/referrers/industries/outgoing/display/social/demographics(age+gender)/competitor_traffic/category/ranks), sum-validated, source-labeled. `data_quality=verified-capture-full`. Reference impl: `docs/temp/sw-capture/{f,d,c}{1,2,3}.json` + `sw_upsert3.py`.
- Duplicate audit rows cleaned (belk/dell/orientaltrading dupes deleted; 18 accounts/18 audits).
- **SimilarWeb = PERMANENT HITL** (no API, key dead forever). Marked in: `algolia-intel-traffic/SKILL.md` (local + arijit-skills GH `cb77604` + VPS pull) + memory `reference-similarweb-permanent-hitl`. Method: log into pro.similarweb.com, extract from Highcharts chart-data + DOM, sum-validate, completeness-gate.

### C. PRISM V2 — pivot + prism2 live
- Pivot: **standalone product first** (Algolia = first domain module), **best-of-breed stack** (Postgres+pgvector + Claude Agent SDK), 3 roles (AE/BDR/Marketer). Beta = Algolia Marketing+Sales leadership (their #1 ask = landing-page building). 2nd pitch = Spryker; domain-swap set = Spryker/Amplience/Contentful/Cloudinary. HeyGen+Telegram = Phase 2.
- Built + deployed: 3 role doors + data-driven landing builder (Nike/Dell), `prism-v2` branch pushed, VPS reorg (/opt/PRISM/v1+v2), prism2.chowmes.com live (basic-auth).
- Docs: `docs/PRISM-V2/06-v2-execution-map.md`, `07-design-system.md`, `08-fable5-handoff-prompt.md` (+ vault mirror `Projects/PRISM/wiki/V2/`).

## REMAINING WORK (in order)
1. **DB-backed auto-render (NEXT — in progress).** Reports currently STATIC (data baked at render). Build: a `prism_platform` API endpoint serving `audit_data` by slug (reads Postgres) + the report page fetches from it (or a render-on-DB-change trigger). So DB updates reflect on the live site automatically. This is the user's explicit next task.
2. Reconcile schema drift at the SOURCE (so future renders don't need `migrate_schema.py`) — align the audit pipeline's output to the current renderer Pydantic schema.
3. V2 backend (Fable-5 package): executioner POC (needs ANTHROPIC_API_KEY), Postgres schema, chat-as-operator, modular rearchitecture — per `06` §7 open research R1-R10.
4. Belk deeper: query-specific screenshots blocked by PerimeterX WAF — needs a stealth/HITL workaround if wanted.
5. Other 15 audits: only traffic refreshed; NOT re-rendered (live sites still show old traffic for the other 15). Same migrate→render→deploy pattern applies.

## WHAT HAS NOT BEEN DONE (explicit — prevent false-green)
- The other 15 audits (autozone, british-airways, brooks-running, dsw, footlocker, homedepot-mexico, jbl, labanquepostale, llbean, michaelkors, nike, oriental-trading, petsmart, savage-x-fenty, thenorthface, torrid) have fresh DB traffic but are **NOT re-rendered/redeployed** — live pages show OLD traffic. Only Dell/Belk/Lululemon were re-rendered.
- Belk F01-F04 have no query screenshots (WAF). Dell had 4 findings' screenshots nulled (WAF/missing).
- DB-backed auto-render NOT built yet (next task).
- V2 backend (executioner/chat/modular) NOT built — planning only.
- Dead SimilarWeb key still sits in `.claude.json` MCP header + PIP `.env` (commented) — harmless but stale.

## KEY FILES THIS SESSION
- `docs/PRISM-V2/06,07,08*.md` — V2 execution map + design system + Fable-5 prompt
- `docs/temp/migrate_schema.py`, `sw_upsert3.py`, `sw-capture/*` — audit migration + traffic capture reference impls
- `~/.claude/skills/algolia-intel-traffic/SKILL.md` — HITL banner (also pushed to arijit-skills GH)
- Memory: `reference-similarweb-permanent-hitl`, `reference-prism-current-architecture-2026-07-06`, `feedback-prism-data-integrity-absolute`, `project-prism-v2-standalone-pivot-2026-07-06`
