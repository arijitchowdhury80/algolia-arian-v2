# SESSION.md — PRISM (PIP)

**Last updated:** 2026-06-27
**Status:** FORK RESOLVED → **HYBRID**. Primary = orchestrate via Hermes (run existing skills →
report + chat/mobile UX, fastest to a working product). Secondary = the deterministic PRISM modules
(keep + swap in over time as token-free drop-in replacements).

## UPDATE — this session (deterministic-build track, now SECONDARY)
Built/realigned the deterministic modules against the **skills as source of truth** (corrected an
earlier mistake of porting from deleted v1 code). Committed, ruff-clean, 453 tests pass:
- Vendored canonical **AuditData** contract (`prism_platform/v2/audit_data_schema.py`) from the
  skill; audit-report now outputs it (commit 77fdfe7).
- Realigned synth-business-case / sales-plays / campaign-abx schemas to the skills (signal_tier,
  source_notes, BLUF, talking-points, partner-angles, AE fill-in, assumption inventory) (a38536e).
- Earlier: search-vendor packet detector shipped + wired (a72aea6); 4 synth/report modules rebuilt.
These are the **drop-in-replacement track** — NOT the urgent path. STILL pending on this track:
audit-report assembler, audit-browser+Vision, audit-factcheck, render, full e2e run.

**Primary next (per Hybrid):** the Hermes-as-PRISM orchestrate fork below — run the algolia-* skill
suite via the Hermes harness → SPA report → chat/mobile UX. Founder parked this for a FRESH session.

---

## RESUME ACTION (do this first, next session)

1. Read this file, then memory `[[session_pointer]]` and `[[project-prism-hermes-direction]]`.
2. **Do NOT resume the UX mockup thread.** The founder explicitly pivoted.
3. Start exploring the new fork (see "THE NEW DIRECTION" below): can the **Hermes harness run the existing Claude skill suite** to generate the SPA, and how does a user (esp. **mobile**) chat with / interact with the result?
4. Likely first steps: understand Hermes (VPS `72.61.72.147`, workspace Google Drive `AI-Projects/Hermes`, `hostinger-vps-ssh` skill); inventory the `algolia-*` skill suite as the "engine"; sketch build-vs-orchestrate options.

---

## THE NEW DIRECTION (the actual next task) — Hermes-as-PRISM

Founder's framing, verbatim intent:
- PRISM/PIP today is an **idea, not a full build**. What IS fully built = the **manually-run Claude skills** (`algolia-*` audit/intel/synth/campaign suite).
- Question: **Do we even need to build PRISM fully?** Or give **Hermes** the existing skills and have the **Hermes harness run the skills** → research a company → generate the SPA report.
- Flow: give Hermes a company → it runs each skill → generates the report.
- **Open UX problem:** how does the *user* still use the tool — chat with it, interact with the report? Could we integrate Hermes so the user **chats from their phone** and interacts with the report conversationally?

This is a **build-vs-orchestrate** decision. The "build PRISM custom" path is far from done (only Wave 1 exists). The "Hermes runs the skills" path may reach a working product faster, since the skills already produce every deliverable.

---

## DATA-ENGINE GROUND TRUTH (established this session — important context)

Corrects an earlier over-rosy belief. Authoritative state:
- **Built = Wave 1 ONLY: the 13 intel modules** (`prism_platform/v2/registry.py`). They gather company intelligence.
- **NOT built: Waves 2-6** — audit-browser (the SCORED search audit = the core Algolia wedge), audit-factcheck, insights-engine, synth-business-case, synth-sales-plays, campaign-abx, audit-report. Deleted with v1; rebuild only started.
- **Pipeline has NEVER run end-to-end.** No Temporal worker running. No local Postgres.
- Smoke tests verified *individual pieces* only (Scout fetch, packet detection, one Perplexity call) — NOT a full audit.

**Data gathering — how (Track 1 deterministic / Track 2 Perplexity LLM):**
- 7 modules have Track-1 collectors. Strongest asset = **search-vendor packet detection** (`v2/detection/search_vendor.py`): 17 vendors, zero false-positives, detects Algolia/**C.io**. Blind to proxied/self-hosted/bot-walled.
- Track 2 = Perplexity Sonar research for techstack/traffic/financial/news/industry.
- Yahoo Finance (public financials), Apify (LinkedIn+Twitter), Scout (page fetch on VPS), static partner table, Python query gen.

**Gatherable TODAY (Wave 1):** company profile, incumbent search vendor (incl. C.io), tech stack, traffic, financials (public), news/hiring/social signals, partner overlap, query set.
**NOT gatherable today (unbuilt):** scored search audit + the "damning finding", ROI/business case, sales playbook, ABX campaign, report package.
→ ~60% of the designed brief is real today; the most important 40% (the audit score + deliverables) is not.
**Crucially:** the Claude SKILLS already produce all of that manually — which is what makes the Hermes fork attractive.

---

## DECISIONS LOCKED THIS SESSION (UX/journey track — paused, not dead)

All recorded as ADRs in vault `Projects/PRISM/wiki/decisions/`:
1. **Persona-journey UI architecture** (`2026-06-27-persona-journey-ui-architecture.md`) — UI = three role-shaped doors over one intel engine. Build order **AE → BDR → Sales Leader**. AE = depth/brief+business-case; BDR = volume/queue+outreach; Leader = aggregate/dashboard (the old 6-tab dashboard belongs to the Leader, not the AE).
2. **PRISM = AI Sales Toolkit + stage cockpit** (`2026-06-27-prism-as-ai-sales-toolkit-stage-cockpit.md`) — PRISM absorbs the internal AE toolset (Algospy=detect-search, Value Prompter, etc.). AE surface = the real **5-stage gated motion PREP→SS1→SS2→SS3→SS4** with exit-gate checklists as backbone. NOTE: this assumes building PRISM — the new Hermes fork may change the whole frame.
3. Design language: **calm Claude-Desktop** (conversation-as-hero, artifact slides in) + Codex working-state for audit-running. Entry model = **auto-ready** (pre-generate on calendar trigger), summon secondary.

**Key learning — the FY27 AE Field Guide** (`docs/Algolia/AE Sales Process - FY27 Field Guide.PDF`, primary source) defines the real Algolia motion: 5 gated stages, never skip; **C.io (Constructor.io) = THE competitor** (assume in-deal for ICP size; know the counter-narrative cold); PRISM is literally the "AI Sales Toolkit" the guide tells AEs to run in PREP/SS1. Full extraction: `docs/workspace/ae-journey-research/05-algolia-ae-sales-process.md`.

---

## REFERENCE FILES (next session should read as needed)

- `docs/workspace/ae-journey-research/_status.md` — research index (6 docs)
- `docs/workspace/ae-journey-research/05-algolia-ae-sales-process.md` — FY27 AE motion extraction (primary source)
- `docs/workspace/ae-journey-research/06-ae-journey-definition.md` — full synthesized AE journey (the paused design)
- `docs/workspace/ae-journey-research/01..04` — internal deliverables / competitor UX / discovery methodology / AE workflow research
- Vault `Projects/PRISM/wiki/decisions/` — the 3 ADRs above
- `prism_platform/v2/registry.py` — the 13 built modules (source of truth for what exists)
- Memory `[[project-prism-hermes-direction]]`, `[[project-prism-state]]`, `[[project-prism-ui-persona-journeys]]`

---

## FILES WRITTEN/TOUCHED THIS SESSION

- Vault ADRs: `2026-06-27-persona-journey-ui-architecture.md`, `2026-06-27-prism-as-ai-sales-toolkit-stage-cockpit.md`; updated vault `index.md` + `log.md`.
- Workspace: `docs/workspace/ae-journey-research/_status.md`, `01`–`06` research docs.
- Memory: `project-prism-ui-persona-journeys.md`, `project-prism-hermes-direction.md`, `session_pointer.md`; MEMORY.md pointers.
- (Note: founder/linter updated `MEMORY.md` line 3 + `project-prism-state.md` to the corrected Wave-1-only build state.)

---

## WHAT HAS NOT BEEN DONE (no false completion)

- No code written. No mockups rendered. No UI built this session.
- Wave-1 pipeline NOT run end-to-end (was the pending ask; superseded by the tangent).
- audit-browser + synth deliverables NOT built.
- Hermes-as-PRISM fork NOT yet explored — that's next session's job.
- Open questions still unanswered: Value Prompter / MegGPT / PIE Playbook internals; calendar/CRM integration scope; primary AE interviews.
