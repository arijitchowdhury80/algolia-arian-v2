# PRISM V2 — Status Pointer

Read this first when resuming. Full plan: `00-manifesto.md`. **Execution map + Fable-5 handoff: `06-v2-execution-map.md` (the build spine — read after this).** Algolia-as-DB findings: `02-algolia-as-database.md`. Claude Agent SDK executioner findings (live-probed 2026-07-05): `03-executioner-claude-agent-sdk-findings.md`.

## Where things stand (2026-07-06) — STRATEGIC PIVOT, foundation decisions CLOSED

Two foundation decisions were settled by Arijit this session. They resolve the long-standing contradiction between the manifesto's original "rebuild on Algolia tech" rationale and the later "best-of-breed" architecture lock:

1. **North star = STANDALONE PRODUCT FIRST.** V2 optimizes to become a sellable, domain-agnostic "Prospect Research Operating System." **Algolia is now just the first domain module, not the platform.** Consequence: the original Phase-1 driver — "rebuild on Algolia tech so it's an easy internal-Algolia sell" — is **RETIRED.** Internal-Algolia adoption is no longer the design constraint. (Phase 3 productization is now the thesis, not the speculative far-future.)
2. **Stack = BEST-OF-BREED, confirmed and no longer open.** Data/RAG = **Postgres + pgvector.** Executioner = **Claude Agent SDK** (self-hosted). This closes the executioner question — the 2026-07-05 "ADR still unwritten / evidence not decision" status below is now **superseded**: the decision is made, best-of-breed wins because the product is standalone, not Algolia-internal. Algolia-as-DB and Agent Studio-as-executioner are **not** the direction. (Agent Studio may still serve as an optional *domain-connector* for Algolia-flavored deployments later — not core.)

Other calls locked this session: **3 roles in scope — AE, BDR, Marketer** (Sales Leader deferred). **First visible milestone = all 3 role doors live** (breadth-first). **Design system source of truth = the SPA template** (already embeds the premium language) → extract into a reusable design-system + Claude Design prompt. **Deprioritized to Phase 2:** HeyGen/LiveAvatar embodied avatar + Telegram notify (built + staged, parked — get base functionality working first).

Full ordered build plan, workstreams, open research, and the Fable-5 handoff prompt: **`06-v2-execution-map.md`.**

## Where things stood (2026-07-05) — superseded on the executioner decision, see above

- **Executioner decision is now a live-evidence 5-way, not a 4-way guess.** `03-executioner-claude-agent-sdk-findings.md` live-probed the actual installed `claude-agent-sdk` package (v0.2.110, source-inspected, not recalled) against every non-negotiable executioner requirement from Phase 1. Verdict: real primitives exist for multi-step control, subagent dispatch, pluggable state persistence (`SessionStore`, Postgres-backable), status tracking, and mandatory gating (hooks with `decision: "block"`) — the one real gap is durable/automatic retry, which is Temporal's strength. Also surfaced a **5th candidate this session**: the Managed Agents API (`/v1/agents` + `/v1/sessions`), Anthropic-hosted rather than self-hosted, with native multiagent coordination + Outcomes (rubric-graded gate) + memory stores — found via docs only, NOT yet live-probed.
- **Not yet done:** an actual end-to-end proof-of-concept (needs a real `ANTHROPIC_API_KEY`, not available this session), and the same live-probe treatment for the Managed Agents API. The ADR is still unwritten — this is evidence, not the decision.

## Where things stood (2026-07-04, prior)

- Manifesto written, all 3 phases captured. **HARD RULE: this lives ONLY here, under `docs/PRISM-V2/` — not the vault.** An earlier vault mirror (`Projects/PRISM/wiki/2026-07-04-v2-manifesto.md`) was created before this rule existed and has been removed; do not recreate it.
- Phase 1 research:
  - **Agent Studio**: substantial prior research located in `Algolia-Central2` repo, migrated to vault (was a real gap — existed only in-repo before today). Key finding: Agent Studio has no native multi-agent/handoff/workflow/memory primitives (live-probed, confirmed 404 on `/teams`, `/handoffs`, `/orchestrators`, `/workflows`, `/sessions`, `/memory` etc.) — looks like a fit for the chat layer, not the executioner.
  - **Algolia-as-database**: fresh research done, written up in `02-algolia-as-database.md`. Mixed verdict: good fit for PRISM's content/search layer (documents, research corpus), weak fit for the executioner's own state-tracking (no transactions, no joins, async-by-design indexing).
  - **Executioner decision (Temporal vs Agent Studio vs other)**: NOT resolved, needs Arijit's explicit call. Important context found: Temporal was dropped once already (2026-06-28 ADR, `Projects/PRISM/wiki/decisions/2026-06-28-prism-is-chowmes-prism-hermes-instance.md`) but specifically because it was redundant *alongside Hermes* — that objection doesn't hold now that Hermes is being removed entirely. Temporal should be re-evaluated fresh, not treated as closed.
- Phase 2 and 3: captured as vision only, no design work started.

## Next when resuming
1. Bring the executioner question (Temporal vs Agent Studio vs other) to Arijit as an explicit decision point — cite the "Temporal objection no longer applies" finding and the Algolia-as-DB split-architecture recommendation (content layer on Algolia, state-tracking layer elsewhere).
2. Once decided, write the ADR and update this manifesto.
3. Phase 2 brainstorming can start once Phase 1's executioner question is settled.
