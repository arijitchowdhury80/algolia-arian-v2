# SESSION — PRISM · 2026-06-27 (search-vendor detector rebuilt + wired; Track 2 live; v1 deleted)

## Status: search-vendor detector SHIPPED (packet inspection, zero-FP, wired to intel-competitors)

> **PIPELINE REALITY (audited 2026-06-27):** Only **Wave 1 of 6** is built in v2 (13 intel modules).
> **Waves 2-6 are NOT built** — audit-browser (W2), audit-factcheck (W3), insights-engine (W4),
> synth-business-case/synth-sales-plays/campaign-abx (W5), audit-report (W6) were deleted with v1
> and never rebuilt. The orchestrator references them; `full` mode would crash. The pipeline has
> **never run end-to-end** (no Temporal worker exists). **Rebuild of Waves 2-6 started 2026-06-27.**

## CURRENT STATUS (2026-06-27) — /goal: finish full build, run end-to-end

### The 6-wave pipeline — what's actually built
| Wave | Modules | Status |
|---|---|---|
| 1 — intel | 13 intel-* modules | ✅ built (pre-session) |
| 2 — audit-browser | audit-browser | ❌ NOT rebuilt (needs Playwright + Vision LLM) |
| 3 — audit-factcheck | audit-factcheck | ❌ NOT rebuilt (collector over all modules + child-wf verdict) |
| 4 — insights-engine | insights-engine | ❌ NOT rebuilt (cross-audit DB query + vertical_benchmarks write) |
| 5 — synth | synth-business-case, synth-sales-plays, campaign-abx | ✅ REBUILT this session |
| 6 — report | audit-report | ✅ REBUILT this session |

### Rebuild progress: 4 of 7 missing modules done
- Done (pure-synthesis, playbook-only; committed, ruff-clean, 453 tests pass):
  synth-business-case, synth-sales-plays, campaign-abx, audit-report + Wave-5 sub-wave ordering (5A→5B).
- Remaining 3 (code-heavy + infra-dependent — cannot be runtime-verified until infra up):
  **audit-browser** (W2, Playwright + Vision), **audit-factcheck** (W3, DB collector + verdict),
  **insights-engine** (W4, cross-audit DB).

### Pipeline has NEVER run end-to-end
No Temporal **worker runner** exists (activities/workflows defined, but no `Worker(...)` process).
Local Postgres not running. Vision client not wired. These block a full run.

### To reach end-to-end test (today's /goal)
1. Build remaining 3 modules (audit-browser, audit-factcheck, insights-engine).
2. Write the Temporal worker runner (`Worker(...)` hosting activities + workflows).
3. Stand up local Postgres (Docker) for module_executions / cache / persistence.
4. Wire a Vision client (Claude Vision) for audit-browser scoring.
5. Run one full audit end-to-end (worker + Postgres + Temporal) and verify deliverables.

### This session's commits (newest first)
d93b39b W5 ordering · 93d348c sales-plays+campaign+report · 8044f69 playbook bugfix ·
7149d4b business-case · 932ee29 status correction · a72aea6 search detector + wiring ·
bc9bb82 .env.local fix · f4cea8f v1 deletion

### Reference
- Search detector: `prism_platform/v2/detection/search_vendor.py` (packet inspection, zero-FP,
  17 vendors/230 sites validated; evidence `docs/workspace/search-detector-validation/REPORT.md`).
- Rebuild spec (the 7 modules, v2 contract): from investigation — playbook-only vs collector vs bespoke.
- Infra ADR (Temporal + workers locked): `docs/decisions/2026-06-22-infrastructure-architecture.md`.

## What was completed this session (2026-06-22 → 2026-06-24)

### Code (commit 85b7de5)
- **5 new v2 modules** built + registered: intel-industry, intel-investor, intel-partner, intel-queries, intel-social
- **Registry** now has all 13 modules
- **SynthesisClient lazy init** fix — no longer raises ValueError when LLM key absent at import time
- **TestCollect async fix** — 13 failing tests in test_intel_queries_v2.py converted from sync `asyncio.get_event_loop().run_until_complete()` to `async def` + `await` (pytest-asyncio `asyncio_mode=auto` compat)
- **433/433 v2 tests pass**

### VPS deployment (Chowmes — 72.61.72.147)
- **Temporal** (auto-setup 1.27 + postgres + UI) — running at 127.0.0.1:7233/8088
- **Scout** (Docker, built from source) — running at 127.0.0.1:8421
- **Caddy** updated — `temporal.contentengagement.info` route added (basic_auth: prism/prism2026)
- Configs at: `/opt/prism/temporal/docker-compose.yml`, `/opt/prism/scout/docker/docker-compose.yml`
- **DNS not yet added** — temporal.contentengagement.info → 72.61.72.147 still needed

### Smoke test script
- `scripts/smoke_real.py` — standalone script, no Postgres/Temporal required, calls Track 1 + Track 2 directly

### Research
- Parallel.ai vs Perplexity comparison done — decision: keep Perplexity, add Parallel seam later if accuracy becomes an issue

### ADR
- `docs/decisions/2026-06-22-infrastructure-architecture.md` — Postgres→Supabase path, Temporal on VPS, Vercel frontend

## Decisions locked this session

| # | Decision | Choice |
|---|---|---|
| D18 | LLM provider (Track 2) | Keep Perplexity Sonar. Parallel.ai is search-only, not drop-in. |
| D19 | VPS orchestration | Temporal self-hosted on Chowmes. Workers will run as Python processes on VPS. |
| D20 | Scout deployment | Scout runs on VPS (127.0.0.1:8421). Local dev uses SSH tunnel. |

## Remaining work (priority order)

1. **[IMMEDIATE] Add PERPLEXITY_API_KEY to .env.local → re-run smoke test** — proves Track 2 end-to-end
2. **Run browser detector tests** — `pytest tests/v2/test_search_vendor_detector_integration.py -m browser -v`
3. **DNS** — add A record: `temporal.contentengagement.info → 72.61.72.147`
4. **Deploy PRISM Python workers to VPS** — Temporal activities need a worker process running on VPS; codebase + deps not yet deployed there
5. **Local Postgres** — bring up Docker Postgres to test full persistence path (hooks, module_executions)
6. **Agent Studio trial** — stand up minimal agent over PRISM_Data; lock D9 (aRRIe architecture)
7. **Postgres→Algolia sync** — new intel findings flow to PRISM_Data
8. **Waves 4–6** — insights-engine, synth trio, audit-report SPA
9. **aRRIe copilot** — grounded on PRISM_Data, 3-panel Next.js shell

## What has NOT been done

- PERPLEXITY_API_KEY not in .env.local (Track 2 never ran live)
- PRISM Python workers not deployed to VPS (Temporal infra is up but no worker process)
- Local Postgres not running (DB hooks untested)
- DNS for temporal.contentengagement.info not added
- Agent Studio trial pending
- Postgres→Algolia sync not built
- Waves 4–6 not started

## Reference files

| File | Purpose |
|---|---|
| `prism_platform/v2/registry.py` | All 13 modules registered here |
| `prism_platform/v2/modules/intel_company/` | 3-track seed module (exemplar) |
| `prism_platform/v2/modules/intel_competitors/` | 2-track exemplar with Scout detector |
| `prism_platform/orchestrator/activities.py` | F1 context hydration + F2 collector run |
| `prism_platform/orchestrator/workflows.py` | F3 sub-wave split (1A→1B→1C) |
| `prism_platform/v2/synthesis.py` | SynthesisClient (lazy init, Gemini) |
| `scripts/smoke_real.py` | Direct smoke test script (no Postgres/Temporal) |
| `docs/decisions/2026-06-22-infrastructure-architecture.md` | Infra ADR (locked) |
| `tests/v2/` | 433 tests, all pass |
| `/opt/prism/temporal/docker-compose.yml` | Temporal on VPS |
| `/opt/prism/scout/docker/docker-compose.yml` | Scout on VPS |
| `/home/chowmesadmin/lab-judge/Caddyfile` | Caddy routes on VPS |

## VPS quick reference

```bash
# SSH into VPS
ssh -i ~/.ssh/chowmes_ed25519 chowmesadmin@72.61.72.147

# Open Scout tunnel for local dev
ssh -i ~/.ssh/chowmes_ed25519 -fNL 8421:127.0.0.1:8421 chowmesadmin@72.61.72.147

# Check all services
sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
# Expected: scout (healthy), temporal, temporal-ui, temporal-db (healthy), hermes, ac2-lab-backend (healthy), caddy
```

## Fix-and-Learn log (this session)

- **Scout Dockerfile build fail**: hatchling needs `scout/` package dir before `pip install .` — Dockerfile only copied `pyproject.toml`. Fix: copy `scout/` before pip install.
- **Docker port ghost**: after Docker daemon restart, iptables NAT rules stale → container starts without network attached. Fix: `docker compose down` + `docker compose up -d` after daemon restart.
- **asyncio_mode=auto + run_until_complete**: `asyncio.get_event_loop().run_until_complete()` in sync test methods breaks when full suite runs with `asyncio_mode=auto`. Fix: convert to `async def` + `await`.
- **SynthesisClient eager init**: calling `settings.get_enricher_provider()` in `__init__` raises ValueError when no LLM key. Fix: defer to `_resolve_provider()` called inside `synthesize()`.
