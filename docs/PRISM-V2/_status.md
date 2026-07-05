# PRISM V2 — Status Pointer

Read this first when resuming. Full plan: `00-manifesto.md`. Algolia-as-DB findings: `02-algolia-as-database.md`.

## Where things stand (2026-07-04)

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
