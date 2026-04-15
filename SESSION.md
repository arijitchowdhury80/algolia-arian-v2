# SESSION — 2026-04-14/15
## Status: COMMITTED — Context cleared, resuming next session
## Commit: a78f0cb

---

## What was built this session

### Shared Browser Infrastructure — prism_platform/browser/
- BrowserClient: httpx → Jina Reader (JS) → Playwright stub → Browserless stub
- FetchResult, FetchOptions, FetchTier (Pydantic, universal types)
- Bot-block detector: Cloudflare, WAF, CAPTCHA, login walls
- Tier 1 fully working; Tiers 2+3 stubbed with clear interfaces

### intel-company: 3-Track Pipeline
- Track 1 (WebFetch): leadership/IR/newsroom via BrowserClient. Smart homepage link discovery.
- Track 2 (Perplexity sonar-pro): playbook v2.2.0 — targeted, explicit LinkedIn search per exec
- Track 3 (Synthesis): Gemini gemini-3.1-flash-lite-preview reconciles both. WebFetch wins conflicts.
- Pipeline health log: every failure/fallback/warning captured → in report, JSON, console
- Smoke test: cache-first (checks module_executions), --refresh flag

### Schema + DB
- CompanySeedOutput: twitter_handle, youtube_url, company_linkedin_url
- CompetitorSeed: ticker, twitter_handle, youtube_url, linkedin_url
- ExecutiveSeed: linkedin_url, tenure_description, previous_company
- Migration 006 applied. Docker up, both prospects seeded in PostgreSQL.

### Results in DB
- nike.com: accounts + module_executions, cache HIT on repeat, HEALTHY
- orientaltrading.com: accounts + module_executions, cache HIT on repeat, DEGRADED (leadership page not public)

---

## What REMAINS for intel-company to be COMPLETE

### Code (incomplete)
- [ ] Wire synthesis (Track 3) into activities.py — Temporal production path only has Track 1+2 today
- [ ] Tier 2 Playwright stealth — shared with search audit module, build when that module ships

### Tests (all missing)
- [ ] Unit: BrowserClient tier escalation (mock httpx)
- [ ] Unit: PipelineHealthLog event capture + markdown render
- [ ] Unit: SynthesisClient mock Gemini, assert reconciliation
- [ ] Integration: full 3-track run with VCR cassettes
- [ ] Contract: CompanySeedOutput schema stability

### UI (not started)
- [ ] Company identity card view (nike.com / orientaltrading.com)
- [ ] Pipeline health badge (HEALTHY/DEGRADED/FAILED + event list)
- [ ] Cache freshness indicator + refresh button

---

## Key architectural decisions

1. 3-track: WebFetch (wins) + Perplexity (external lens) + Synthesis LLM (reconciles)
2. Single Perplexity call — make it better, not two calls
3. Browser infra is shared — all modules use BrowserClient not raw httpx
4. Pipeline health mandatory — no silent failures
5. Cache mandatory — module_executions, zero API calls on repeat
6. Gemini model: gemini-3.1-flash-lite-preview everywhere

---

## Environment
- Docker: running (docker compose up -d)
- Alembic: through 006
- Venv: rebuilt at current path (old one pointed to Google Drive)
  Always use: .venv/bin/python3

## Next session
1. Verify intel-company completion checklist — what's actually missing?
2. Wire Track 3 into activities.py
3. Write unit + integration tests
4. Build company identity card UI
5. Then spoke modules
