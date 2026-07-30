# PRISM Handoff — aRRIe + Algolia datastore + finish-the-platform plan

**Date:** 2026-06-21
**Author:** Arijit (vision) + Claude (mechanics), handed off from a ChowMes-dir session into PIP (PRISM's real home).
**Read order for the new session:** this doc → `SESSION.md` → `CLAUDE.md` → the architecture specs it points to.
**Status:** Planning/design locked. One live blocker (Algolia write key). Nothing built this session — by design.

---

## 0. Why this handoff exists

The prior session ran in `/Users/arijitchowdhury/Dropbox/AI-Development/Personal/ChowMes` and drafted an "IPRS engine" design before realizing **PRISM already exists here in PIP and is a Phase-2 platform.** That ChowMes design (`ChowMes/docs/superpowers/specs/2026-06-20-iprs-engine-mechanics-design.md`) **largely reinvented what PIP already has** — treat it as historical context only. **PIP is the source of truth.** This doc reconciles everything to PIP's reality.

**Lesson captured:** before designing a "new" system, check for an existing implementation first. PRISM/PIP (Temporal + the Finding model + a Next.js frontend) already existed; the queue/data-model/gates were partly built.

---

## 1. The vision (owner: Arijit) — what we're finishing

**PRISM is the product; the Algolia-search-audit *skills* are just Arijit running each step by hand.** The skills don't scale to 50 reps/BDRs and produce a static, all-or-nothing report nobody can interrogate. PRISM is the always-on, multi-rep, conversational version.

- **aRRIe** = the grounded RAG **sales-coach agent** (Arijit's DJ name) in the middle of the product. Fully grounded on PRISM's data; suggests strategies/approaches; an AI sales coach for an Algolia AE/BDR.
- **UX = Claude-Desktop layout** (3 panels): **left** = customers list with alphabetical grouping; **center** = working area / chat; **right** = artifact preview that opens whatever aRRIe generates.
- **"Uber-premium" aesthetic** of the existing SPA audit reports must be carried forward into PRISM's deliverables and preview panel.
- **Two consumer sides:** internal (AEs/BDRs) now; external (bracketed, not precluded — `tenant_id` scoping) later.
- **All four of these are REQUIRED** (not either/or): finish the audit pipeline, build aRRIe, the Algolia dogfood datastore, and the premium aesthetics. Sequencing is by dependency (see §5).

---

## 2. PRISM's actual current state (as explored 2026-06-21)

**PIP = Prospect Intelligence Platform** (parent). **PRISM v2** = the agentic engine inside. Stack: Python 3.12 / FastAPI / **PostgreSQL 16** / **Temporal.io** / Redis; **Next.js 15 + Clerk + Vercel AI SDK + @assistant-ui/react** frontend (already chat-first, Claude-Desktop artifact model).

**Orchestration = Temporal**, 6 waves defined in `prism_platform/orchestrator/workflows.py`:
- Wave 1 Intel (13 modules) → W2 Browser → W3 Factcheck → W4 Insights → W5 Synthesis (business-case, sales-plays, campaign) → W6 Report.

**Data model already exists** (`prism_platform/v2/types.py`): immutable `Finding` (id, company, category[enum], statement, source_url REQUIRED, source_date, confidence[high/medium/low], raw_quote, provider) + `ModuleConfig` + `ExecutionContextV2`. DB tables: `accounts`, `audits`, `module_executions`, `findings_cache`, `deliverables`, `vertical_benchmarks`. **This is the "deal-intelligence object."**

**Module pattern is generic:** each module = `config.py` + `playbook.md` + `schemas.py`; the executor (`v2/executor.py`) is shared. **To add a module = write 3 files.**

### Built vs missing (the finish line)
- ✅ **Built:** infra (Temporal/Postgres/Redis/FastAPI/Next.js+Clerk), the module pattern, **7 intel modules** (company, techstack, traffic, financial-public, financial-private, news, hiring), caching, 3-tier citation validation, evidence tiers.
- ❌ **Missing — this is the work:**
  1. **6 stub intel modules** (competitors, industry, investor, partner, social, queries) — scaffolded, empty `__init__.py`, not registered. Each is "write 3 files." **Ideal first parallel workflow.**
  2. **audit-browser** exists in `prism_platform/browser/` (Playwright) but is **not wired into Temporal**.
  3. **Waves 4–6 do not exist:** insights-engine, the synth trio (business-case, sales-plays, campaign-abx), **audit-report** (the premium SPA). *A full audit currently dies after factcheck.*
  4. **aRRIe** — the grounded copilot over audit state + editable artifacts, on the existing frontend shell.

### Architecture docs (read before building)
- `docs/specs/cognitive-stack-architecture.md`
- vault `Projects/PRISM/Architecture/unified-module-architecture.md` (THE core design spec)
- vault `Projects/PRISM/Specs/2026-04-09-prism-unified-architecture-design.md`
- `docs/plans/2026-04-09-prism-v2-implementation-plan.md`
- vault `Projects/PRISM/Wiki/Feature-Inventory-And-Build-Plan.md` (5-phase sequencing; "baseline reliable first")

---

## 3. Algolia-as-datastore + Agent Studio — VERDICT

Researched + partially tested this session (empirical seed blocked on a bad write key — see §4).

### Verdict: YES to both, as a hybrid
- **Algolia as datastore → YES, as the retrieval/grounding layer, NOT a Postgres replacement.** Store each finding/deliverable as an Algolia record; retrieve by keyword + **vector (NeuralSearch)** + facet/filter (company, category, confidence, persona_fit, archetype). That is exactly aRRIe's grounding layer, and it dogfoods Algolia.
  - **Keep Postgres + Temporal** as the system of record + operational state (workflow state, audit/job status, `module_executions`, editable-artifact versions, the `accounts` master). **Algolia is the search index OVER the findings, synced from Postgres.** The one trap to avoid: do not try to make Algolia your transactional DB.
- **Agent Studio as aRRIe → YES, strong fit.** Purpose-built: grounded retrieval over your index, **bring-your-own-LLM** (OpenAI / Gemini / Azure / OpenAI-compatible — use a cheaper model), configurable agent **role/style/constraints** (sales-coach persona), multi-turn, tool use, embeddable via **React InstantSearch chat widget** OR **REST API**. Algolia's own "AI Assist" (reads context, surfaces suggestions, cheaper model, permissioned) ≈ aRRIe — proof it's doable. 4-step build: define role → add tools+indices → choose model → publish/integrate. Dashboard at `dashboard.algolia.com/generativeAi/agent-studio/agents`.
  - **Caveats:** public **beta** (GA later 2026 — fine for internal pilot; flag before external productizing); the prebuilt React chat widget is a **constrained UI** → for the full 3-panel artifact-generating experience, drive Agent Studio via its **REST API and render your own UI**; usage is metered (completions cached).
  - **Honest alternative:** the frontend already has the **Vercel AI SDK** — aRRIe could be built directly on it with Algolia search as the RAG tool, skipping Agent Studio. Agent Studio buys managed grounding/governance/caching + the dogfood story; rolling your own buys full control. **Decide after the hands-on Agent Studio trial (part of finishing the spike).**

Sources: algolia.com/products/ai/agent-studio · algolia.com/doc/guides/algolia-ai/agent-studio · algolia.com/blog/product/three-tools-built-with-agent-studio

---

## 4. Spike state — datastore DONE ✅ (Agent Studio trial pending)

**Index:** `PRISM_Data` (created + seeded). **App:** `FLAGSHIP_Accelerator_Program_APP` = **`0EXRPAXB56`** (us region). Creds in **`PIP/.env.local`**: `ALGOLIA_APP_ID`, `ALGOLIA_SEARCH_API_KEY` (read-only), `ALGOLIA_WRITE_API_KEY` (full admin ACLs — fixed 2026-06-21; the earlier 403 was a newline-wrapped key in the env file).

**Proven this session:**
- ✅ `PRISM_Data` created with settings (searchable: statement/company/category/raw_quote; faceting: company/category/confidence/persona_fit/archetype/domain).
- ✅ Seeded 6 sample `Finding` records (PetSmart ×3, Home Depot ×3).
- ✅ Retrieval works: keyword search ("no results") + facets + filter `confidence:high` → correct hit; filter `company:PetSmart` → its 3 findings. Faceting/filtering confirmed.
- ⏳ **NeuralSearch/vector NOT enabled yet** — put the index in `neuralSearch` mode (Algolia must enable NeuralSearch for the app/index) and re-test for the vector-RAG path aRRIe wants.
- ⏳ **Agent Studio trial NOT done** — stand up a minimal agent over `PRISM_Data` (sales-coach role, cheaper model) and ask one grounded question → locks D9.

**Verdict stands:** the Algolia-as-findings-datastore answer is **YES** (empirically confirmed). Remaining is the agent-layer trial + enabling vector mode.

### Seed script (run once the write key is fixed — creates + proves `PRISM_Data`)
```bash
PIP=/Users/arijitchowdhury/Dropbox/AI-Development/PIP
set -a; source "$PIP/.env.local"; set +a
APP="$ALGOLIA_APP_ID"; WK="$ALGOLIA_WRITE_API_KEY"; SK="$ALGOLIA_SEARCH_API_KEY"

# 0) verify write key ACLs (expect addObject/editSettings present)
curl -sS "https://$APP-dsn.algolia.net/1/keys/$WK" -H "X-Algolia-API-Key: $WK" -H "X-Algolia-Application-Id: $APP"

# 1) settings (faceting + searchable)
curl -sS -X PUT "https://$APP.algolia.net/1/indexes/PRISM_Data/settings" \
  -H "X-Algolia-API-Key: $WK" -H "X-Algolia-Application-Id: $APP" \
  --data-binary '{"searchableAttributes":["statement","company","category","raw_quote"],"attributesForFaceting":["searchable(company)","category","confidence","persona_fit","archetype","domain"]}'

# 2) seed sample findings
curl -sS -X POST "https://$APP.algolia.net/1/indexes/PRISM_Data/batch" \
  -H "X-Algolia-API-Key: $WK" -H "X-Algolia-Application-Id: $APP" \
  --data-binary @/tmp/prism_seed.json   # 6 sample Finding records (see below)

# 3) prove retrieval: keyword search + facet filter
curl -sS -X POST "https://$APP-dsn.algolia.net/1/indexes/PRISM_Data/query" \
  -H "X-Algolia-API-Key: $SK" -H "X-Algolia-Application-Id: $APP" \
  --data-binary '{"query":"no-results search","facets":["company","category","confidence"],"filters":"confidence:high"}'
```
Sample seed records (write to `/tmp/prism_seed.json` as `{"requests":[{"action":"addObject","body":{...}}, ...]}`): 6 Findings across PetSmart (search_audit/exec_commentary/tech_stack) and Home Depot (financial_signal/hiring_signal/competitive_action), each with `objectID, company, domain, category, statement, source_url, source_date, confidence, risk_if_wrong, persona_fit[], archetype, provider`. (Mirror the real `Finding` schema in `prism_platform/v2/types.py`.)

**Then:** stand up a minimal Agent Studio agent over `PRISM_Data` (sales-coach role, cheaper model) and ask it one grounded question → validates aRRIe end-to-end. This closes the spike and locks the datastore + agent decision.

---

## 5. The integrated build sequence (all four, by dependency)

- **0 · Finish the spike** (blocked only on the write key): seed `PRISM_Data`, prove keyword+facet+vector retrieval, run the Agent Studio trial → lock datastore + aRRIe-engine decision.
- **1 · Finish the pipeline so findings are reliable:** the **6 stub intel modules** (first parallel **workflow** fan-out — each is "write 3 files" against the existing pattern) → wire **audit-browser** into Temporal → build **Waves 4–6** (insights, synth trio, **premium audit-report SPA**). Add a **sync step** that indexes each finding from Postgres into `PRISM_Data`.
- **2 · aRRIe copilot:** grounded on `PRISM_Data` (Agent Studio or Vercel AI SDK — decide post-trial), embedded in the existing Next.js 3-panel shell (customers left / work center / artifact preview right), editable artifacts.
- **Premium aesthetics:** not a phase — the quality bar carried through the Wave-6 report and the preview panel (carry forward the SPA `renderSections` design).
- **Scout** fixes run in parallel (see §6) but do NOT block the baseline (per the vault's "baseline reliable first" guidance).

### Orchestration (how to break up the work — Arijit asked)
- **Manual / interactive (Arijit + Claude):** design, ambiguity, taste. Do NOT put design in an autonomous loop.
- **Workflow (one bounded parallel fan-out, then review):** the 6 stub modules is the first fan-out; each Wave-4–6 module gets a spec then a build pass with review between.
- **Autonomous loop / `/goal`:** only for airtight mechanical grind (e.g. regenerating N deliverables to a locked template). Never for design.
- Pattern: **plan it (manual) → build it (workflows per chunk) → grind it (loop only when airtight).**

---

## 6. Scout — assessment + issues (Arijit asked to flag problems)

Scout (`/Users/arijitchowdhury/Dropbox/AI-Development/Scout`) is PRISM's intended crawl/data-fetch layer (Crawl4AI + Playwright stealth; FastAPI on port 8421; CLI; Python import).

- ✅ **Crawl engine is solid:** scrape / crawl / map / **products**, plus a real anti-bot escalation ladder (beats Cloudflare/Akamai). Already wired into `intel-company` and `intel-investor` for WAF bypass.
- ❌ **Intelligence modes are STUBS:** `company`, `prism`, `investor`, `careers`, `news` return **fake seed records at 0.35 confidence** ("live acquisition pending"). `scout run company` returns fake data. Today Scout is safe only as a **raw fetch / anti-bot layer**, NOT the company-intelligence engine.
- ⚠️ **Fix-before-trust:** default API key is `"dev-key"`; no rate limiting on the HTTP API; `crawl4ai>=0.7.7` has **no upper pin** (0.8 will silently break it); runs lost on restart (no SQLite persistence yet); proxy creds may leak into logs.
- **Use Scout now as the stealth fetch layer feeding modules; don't rely on its intelligence modes until that rebuild ("Phase C") lands.**

---

## 7. Decisions locked (this + prior session)

| # | Decision |
|---|----------|
| D1 | Browser wave → **always-on residential runner** (the Mac), not proxies. #1 risk, isolated bottleneck. |
| D2 | Scope = **pilot pod** (AEs/BDRs): per-rep identity + cost caps; not single-user, not all-AEs governance. |
| D3 | Engine **branches on archetype** (existing-customer golden-telemetry vs net-new SPIN); secrets-vault path core. |
| D4 | **Temporal** is the orchestration backbone (supersedes the ChowMes "Postgres-queue" idea). Browser wave pinned to the residential Mac; research/synthesis in cloud. |
| D5 | Primary interface = **web portal / 3-panel app** (customers left / work center / artifact preview right). Telegram → optional later channel. |
| D6 | External side **bracketed, not precluded** (`tenant_id`+`rep_id` scoping, default Algolia-internal). |
| D7 | **Gates are enforced code, not notes** ("notes ≠ prevention"); design-verify gate = the PetSmart wrong-template regression as a test. |
| D8 | **Datastore = hybrid:** Postgres+Temporal (operational) + **Algolia `PRISM_Data`** (retrieval/grounding for aRRIe). |
| D9 | **aRRIe engine:** Agent Studio (strong fit) vs Vercel AI SDK — decide after the spike trial. |

---

## 8. Open questions
- Fix + verify the Algolia write key (blocker).
- Agent Studio vs Vercel-AI-SDK for aRRIe (decide post-trial).
- External-consumer shape (defer).
- Concrete numbers: Temporal concurrency, per-run cost ceiling, finding-freshness/staleness window, Postgres→Algolia sync trigger.
- The residential-runner wiring for audit-browser under Temporal.

---

## 9. Key file pointers
- **PRISM data model:** `prism_platform/v2/types.py` (the `Finding` schema to mirror in `PRISM_Data`).
- **Executor / module pattern:** `prism_platform/v2/executor.py`, `prism_platform/v2/registry.py`.
- **Temporal:** `prism_platform/orchestrator/workflows.py`, `activities.py`.
- **Stub modules to build:** `prism_platform/v2/modules/intel_{competitors,industry,investor,partner,social,queries}/`.
- **Frontend (aRRIe home):** `frontend/` (Next.js 15, Vercel AI SDK, @assistant-ui/react, Clerk).
- **Scout:** `Scout/scout/core/acquisition.py`, `Scout/scout/api/main.py`, `Scout/scout/core/use_cases/intelligence_runner.py` (the stubs).
- **Prior-session reference (historical, not source of truth):** `ChowMes/docs/superpowers/specs/2026-06-20-iprs-engine-mechanics-design.md`; Discovery-OS at `~/Dropbox/AI-Development/Discovery/Discovery-OS-v1.md` (the future sales-methodology synthesis layer; Phase 5 — do NOT bring in before baseline is reliable).

---

## 10. IMMEDIATE NEXT ACTIONS (new session, in order)
1. Read this doc + `SESSION.md` + `CLAUDE.md` + the architecture specs (§2).
2. ✅ DONE — write key fixed, `PRISM_Data` created + seeded + retrieval proven (§4).
3. **Finish the spike's last piece:** stand up a minimal **Agent Studio** agent over `PRISM_Data` (sales-coach role, cheaper model), ask one grounded question → lock **D9** (Agent Studio vs Vercel AI SDK). Optionally enable `neuralSearch` mode and re-test vector retrieval.
4. Decide orchestration for slice 1 and **plan the 6 stub modules** (the first workflow fan-out). Do NOT build before the plan is reviewed.
5. Build the **Postgres→Algolia `PRISM_Data` sync** as part of the pipeline work so findings flow to the dogfood datastore.
6. Keep the premium SPA aesthetic as the bar for the eventual audit-report (Wave 6).
