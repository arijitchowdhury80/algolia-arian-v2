# SESSION.md — PRISM / Cass Agent Evolution

**Status:** Phase A Wave 1 COMPLETE. **Phase B L1 = DEPLOYED + VERIFIED LIVE ON PROD** (Cass is now a real
grounded Algolia coach). NEXT = L2 orchestrator brain ($0 build; flip live on Perplexity key — first action).

**Last updated:** 2026-06-29 (~5:05am EDT)

## L1 — DEPLOYED + VERIFIED LIVE (2026-06-29) ✅
Done on prod this session:
- Migration 008 applied to live `prism` DB (alembic 007→008). Backup at container /tmp/prism-predeploy-008.dump.
- Knowledge DB seeded (faithful, verify PASS): algolia_knowledge=8, case_studies=10, proofpoints=2, quotes=1.
- Plugin deployed to /root/.hermes-prism/plugins/prism-report-qa/ + hermes-prism restarted, loaded clean.
- **Live-tested via /v1/responses (curl on VPS, port 8642):**
  - T1 unbound "Algolia vs Constructor for apparel" → real coach answer (speed/synonyms/positioning), persona
    intact, self-enforced no-fabrication. input_tokens 16k = knowledge injecting.
  - T2 "what are the highlights for home depot?" → **binds homedepot-mexico** (input 50k = full report), full
    grounded brief with [FACT]/[ESTIMATE] labels (250M visits, 0.2% conv, $15-30M, new CTO/CIO, Leroy Merlin
    $28M from knowledge DB = two-source gate working). This is the EXACT Telegram failure, now fixed.
- Retrieval verified across all 4 tables (lacoste→case study, shoe carnival→case+quote, baymard/constructor→knowledge).

## RESUME ACTION (next session, do first)
1. Read this file + the 2 design docs in docs/workspace/hermes-prism-integration/phase-b-cass-agent/.
2. **L2 orchestrator brain build** (decision locked, $0 to build). FIRST sub-step = stage the fuel:
   add `PERPLEXITY_API_KEY=<value from local .env.local>` (+ optional `PERPLEXITY_MODEL=sonar`) to VPS
   `/opt/prism-platform/.env`, `sudo systemctl restart prism-platform.service` → 17 modules go healthy.
   (I could NOT do this — reading local .env.local is permission-blocked; user/next-session handles the secret.)
3. Then build L2 per L1.5 doc: capabilities manifest (she knows which module/skill does what + when) +
   Hermes tools run_audit/run_module/audit_status wired to prism_platform + monitor (SSE /audits/{id}/stream)
   + record pipeline → knowledge DB. Architecture: Cass=control plane, prism_platform=execution plane.

## LESSONS THIS SESSION (fix-and-learn)
- FastAPI POST to a collection route WITHOUT trailing slash → 307 redirect drops the body (silent no-op write).
  Always trailing-slash collection POSTs (`/api/v1/knowledge/`).
- Postgres will NOT auto-cast `text[]`→`jsonb`. JSONB columns need a JSON literal `'[...]'::jsonb`, not `ARRAY[...]::text[]`.
  Insert/seed generators must emit per the real column type.
- Hermes hooks do NOT receive the gateway session key (`:acct:`); it lives on `agent._gateway_session_key`.
  Binding works via content-match on the message instead (SPA already tags account every turn).

## L2 ORCHESTRATOR BRAIN (next build after deploy — decision locked 2026-06-29, $0)
Cass = conversational CONTROL plane; prism_platform = EXECUTION plane ("the temporal"). Build now, inert until
fuel: (a) capabilities manifest — she knows which module/skill does what + which wave + when to invoke; (b)
Hermes tools run_audit(domain,mode)/run_module(name,domain)/audit_status(id) wired to prism_platform; (c)
monitor via /audits/{id}/stream (SSE); (d) record pipeline → knowledge DB + report store. FLIP LIVE on ONE
Perplexity key (lights all 17 modules — no Anthropic credit, no BuiltWith). Uses detect-tech + Scout +
manual SimilarWeb for key-free layers. claude-cli skills path = richer but needs credit (rejected for now).

---

## RESUME ACTION (do first, in order)
1. Read this file fully, then the two design docs:
   - `docs/workspace/hermes-prism-integration/phase-b-cass-agent/L1-brain-design.md`
   - `docs/workspace/hermes-prism-integration/phase-b-cass-agent/L1.5-algolia-self-learning-loop-design.md`
     (the "ARCHITECTURE REVISION" section is authoritative — knowledge lives in Postgres, NOT MD).
2. Check the seed-loader subagent result (was running at persist): expect
   `prism_platform/scripts/seed_algolia_knowledge.py` + `docs/temp/seed-dryrun.json` + a verify report
   (every extracted number grepped back to source — any FAIL = fabrication, fix before apply).
3. Confirm with user: design approved as-is? (They reviewed the docs; get explicit go before plugin + prod deploy.)
4. Continue build at **step 3 (plugin)** — see Remaining Work.

---

## HARD CONSTRAINTS (user, this session — NON-NEGOTIABLE)
- **NO fabrication / hallucination / invented data. EVER.** Use only data we actually have. Blank fields stay
  blank ("no data / not run"), never guessed. No naked numbers.
- **NO new credit / paid builds** without explicit OK. → Gemini cron learner DEFERRED (grounding costs).
  → L3 new audits DEFERRED (Anthropic credit).
- **BuiltWith is DEAD** (key expired, NO subscription) — gone, not rotation-pending. Tech-stack routes around it:
  `detect-search` + new `detect-tech` (#21) + SimilarWeb Technologies tab (screenshotted Wave 2).
- Plain language. CAVEMAN MODE active this session (terse).

---

## PHASE A — COMPLETE ✅ (Wave 1, 10 companies)
1. VPS grounding: `bash run/sync-all.sh` → 10/10 md5 match; store 2→10 reports. Backup
   `/root/.hermes-prism/reports.bak-20260629-030829.tar.gz`.
2. Vercel: `vercel --prod` (~/prism-hub) → READY, algolia-arian-v2.vercel.app.
3. GitHub: pushed `237e6b8..fa6a34b`.
- Ledger: `docs/workspace/hermes-prism-integration/spike-unify-audit/run/state.json`.

## WAVE 2 SCREENSHOTS — CAPTURED, NOT SYNTHESIZED
- 70/70 full-page SimilarWeb shots: `docs/temp/similarweb-wave2/<slug>/00..09-*.png` for dell, footlocker,
  jbl, michaelkors, thenorthface, torrid, autozone (10 sections each).
- `docs/temp/` EPHEMERAL + gitignored (`_DELETE-ON-CLEANUP.md`). Cover **traffic** + **tech-stack** modules.
- Step 6: synthesize → audit-data.json traffic+tech fields ONLY; rest "no data". No fabrication. Then delete.

---

## PHASE B — Cass: RAG-chatbot → real Algolia agent

### THE SKINNY (design in one breath)
Cass is a dead-ish RAG bot: knows company names, can't read reports, no Algolia brain, no tools. Fix in
3 shippable layers: **L1 Brain** (real Algolia knowledge + fixed binding, $0, today) → **L2 Tool-arms**
(she can call the 17 modules + live search; needs Perplexity key) → **L3 Generation** (run full audits from
chat; needs Anthropic credit + SimilarWeb-key rotation). Knowledge lives in **Postgres** (reuse prism DB),
the plugin retrieves top-k per turn over HTTP and injects only relevant rows (no MD dump). A **self-learning
loop** logs Algolia questions Cass can't answer (free, now) and a cron fills them via Gemini+Google-search
behind a strict source+ai-judge gate (deferred — costs credit). One brain serves Telegram + SPA. SPA gets a
global floating Cass + a dedicated section.

### The 5 gaps
1. No real brain (KNOWLEDGE pack not loaded). 2. Fragile binding (accent + direction + dead SPA session-key).
3. Zero tool-calling. 4. Execution plane blocked (keys/credit/no Temporal worker). 5. Parallel brains (old
aRRIe prompt, now bypassed).

### Locked decisions
- Sequencing: **Layered, ship each** L1→L2→L3.
- Security gate before L3: **SimilarWeb key only** (BuiltWith moot).
- Grounding gate: **two sources** (prospect report + knowledge pack); invented numbers stripped.
- Self-learning (L1.5/ASL): **gap-driven now, live at L2**; **gate-on-entry** (≥1 source + ai-judge);
  learn from **logged gaps + seed curriculum**.
- **Knowledge in Postgres, NOT MD** (user). Plugin → prism_platform HTTP → DB.
- SPA: global floating Cass + dedicated section (frontend, not built; routes through frontend-design).

---

## BUILD STATUS (Phase B)

### DONE + VERIFIED — knowledge backend (step 1)  [$0]
ruff clean, 26 pure tests pass:
- `prism_platform/db/models.py` (M) — `AlgoliaKnowledge`, `AlgoliaGap`.
- `alembic/versions/008_add_knowledge_store.py` (NEW) — rev 008→007; both tables + GENERATED tsvector+GIN on
  knowledge/case_studies/proofpoints/quotes; swaps legacy-004 FTS indexes; symmetric downgrade. I verified it.
- `prism_platform/api/routers/knowledge.py` (NEW) — 3 endpoints, bound-param FTS (no string SQL — verified).
- `prism_platform/main.py` (M) — router at /api/v1/knowledge.
- `tests/test_knowledge.py` (NEW) — 26 pass; 4 `@pytest.mark.db` need live PG (`pytest tests/test_knowledge.py -m db -v`).
- `pyproject.toml` (M) — db marker.

### API CONTRACT
- `POST /api/v1/knowledge/retrieve` {query,k=8} → {results:[{kind,title,text,sources[],score}],count}
- `POST /api/v1/knowledge/gaps` {question,topic?,conversation_id?,why} → {id,status:"open",deduped}
- `POST /api/v1/knowledge` {topic,question,answer,sources[],confidence?,judge_score?,origin} → {id,created,updated}

### IN PROGRESS — seed loader (step 2) [$0]
`prism_platform/scripts/seed_algolia_knowledge.py` (faithful KNOWLEDGE-pack → rows; --dry-run + verify; --apply
emits SQL, no execute). Check agent result on resume.

### NOT STARTED
- **Step 3 plugin** [#20,$0]: `chowmes-prism/plugins/prism-report-qa/__init__.py` — HTTP retrieve+inject (httpx
  → 127.0.0.1:8000), gap-log, two-source gate, binding fixes (NFKD accents, token alias, session-key threading).
  **READ RECEIPT FIRST**: how Hermes threads session/context into pre_llm_call/transform_llm_output kwargs (read
  hermes-prism container source on VPS).
- **Step 4 deploy+test**: apply migration 008 to live `prism` (need prism_platform VPS deploy flow; restart
  prism-platform.service), seed --apply, db tests, scp plugin → /root/.hermes-prism/plugins/, restart hermes-prism,
  drop stale Telegram sessions if needed. Tests T1–T5 + loop test.
- **Step 5 detect-tech** [#21,$0]: extend detect-search → full client-side stack (~60 sigs, Wappalyzer-style).
  arijit-skills search-detector. Client-side only.
- **Step 6 Wave2 synthesis** (screenshots → traffic+tech only).
- **DEFERRED**: Gemini learner (credit), L3 audits (credit), SPA Cass UI (frontend-design).

---

## KEY INFRA FACTS (verified)
- VPS `chowmesadmin@72.61.72.147`, key `/Users/arijitchowdhury/.ssh/chowmes_ed25519`.
- DB: `prism-platform-postgres-1` PG16, db/user=`prism` (pw in /opt/prism-platform compose). FTS yes,
  **pgvector NO**. ⚠ pg on 0.0.0.0:5432 (lock to loopback later).
- prism_platform: 127.0.0.1:8000, systemd `prism-platform.service`, alembic 007 (008 pending). VPS /opt/prism-platform; local mirror prism_platform/.
- hermes-prism: network_mode host → reaches 127.0.0.1:8000 (proven). httpx+asyncpg, NO psycopg → plugin uses HTTP.
  Only prism-report-qa plugin enabled (2 hooks).
- Empty knowledge tables already existed: algolia_customers/case_studies/quotes/proofpoints/advocates, vertical_benchmarks.

## NOT DONE (no false claims)
Plugin unchanged. Migration NOT applied to live DB. Seed NOT in DB. Cass still RAG-only. detect-tech NOT built.
Wave2 NOT synthesized. Learner NOT built. L2/L3 NOT started. SPA Cass UI NOT built. SimilarWeb key NOT rotated (#15).

## FILES WRITTEN THIS SESSION
- Design: phase-b-cass-agent/{L1-brain-design.md, L1.5-algolia-self-learning-loop-design.md}
- Backend: prism_platform/db/models.py(M), alembic/versions/008_add_knowledge_store.py, api/routers/knowledge.py,
  prism_platform/main.py(M), tests/test_knowledge.py, pyproject.toml(M)
- Seed loader (pending): prism_platform/scripts/seed_algolia_knowledge.py
- Ephemeral: docs/temp/similarweb-wave2/ (70 png), .gitignore(M)
