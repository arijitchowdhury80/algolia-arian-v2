# SESSION — PRISM · 2026-06-27 (search-vendor detector rebuilt + wired; Track 2 live; v1 deleted)

## Status: search-vendor detector SHIPPED (packet inspection, zero-FP, wired to intel-competitors)

> **PIPELINE REALITY (audited 2026-06-27):** Only **Wave 1 of 6** is built in v2 (13 intel modules).
> **Waves 2-6 are NOT built** — audit-browser (W2), audit-factcheck (W3), insights-engine (W4),
> synth-business-case/synth-sales-plays/campaign-abx (W5), audit-report (W6) were deleted with v1
> and never rebuilt. The orchestrator references them; `full` mode would crash. The pipeline has
> **never run end-to-end** (no Temporal worker exists). **Rebuild of Waves 2-6 started 2026-06-27.**

### Latest work (2026-06-27)
- **Search-vendor detector rebuilt** → live network-packet inspection (replaces faulty substring
  source-scan). Validated 17 vendors / ~230 sites / 59 confirms / **zero false positives**.
  Wired into `intel_competitors/collector.py` (Golden Angle; fixed competitors_scanned=0). Commit **a72aea6**.
  - Module: `prism_platform/v2/detection/search_vendor.py` (`detect_search_vendor` + `scan_search_vendors`)
  - Harness: `scripts/detect_search_packet.py` · Evidence: `docs/workspace/search-detector-validation/REPORT.md`
  - Vault ADR: `Projects/PRISM/wiki/decisions/2026-06-27-search-vendor-packet-detection.md`
- **.env.local loading fixed** (commit bc9bb82) → Track 2 (Perplexity) now VERIFIED live.
- **v1 tree deleted** (commit f4cea8f) → v2 is the sole architecture.
- Verified: ruff clean · 433 non-browser v2 tests pass · 4 live browser detector tests pass.

### Resume action
1. Read this file.
2. Confirm `.env.local` has `PERPLEXITY_API_KEY` (already set). For Scout/browser work, tunnel:
   ```bash
   ssh -i ~/.ssh/chowmes_ed25519 -fNL 8421:127.0.0.1:8421 chowmesadmin@72.61.72.147
   ```
3. Smoke: `uv run python scripts/smoke_real.py nike.com`
4. Detector tests: `uv run python -m pytest tests/v2/test_search_vendor_detector_integration.py -m browser -v`
5. Next big rocks: deploy Python workers to VPS · local Postgres · DNS · Agent Studio trial · Algolia sync.

## Where we stopped (exact)

Ran `scripts/smoke_real.py nike.com`. Result:
- Track 1 (Scout browser): **PASS** — 3 pages fetched from nike.com (leadership: 8K chars, IR: 1K, newsroom: 1K)
- Track 2 (Perplexity): **SKIP** — PERPLEXITY_API_KEY not in .env.local
- intel-competitors detector: **PASS** — ran cleanly, nike.com detected as no-Algolia (correct)

Before smoke test: Parallel.ai vs Perplexity research done. Decision locked: keep Perplexity now, Parallel is search-only (not a drop-in replacement).

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
