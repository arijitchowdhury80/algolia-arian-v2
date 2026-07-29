# PRISM V2 Manifesto

Started: 2026-07-04. This is a living planning document — iterated across many sessions, not a one-shot spec. Read `_status.md` first when resuming.

## Why this exists

PRISM today runs on Hermes as the "executioner" (the process that runs audits, tracks status, drives the system end-to-end). Two problems with that:

1. It's not working the way Arijit needs it to, and the root cause hasn't been found despite investigation.
2. Hermes is a 3rd-party, unchecked, self-hosted-agent codebase. That's a hard security blocker — PRISM can never be brought inside Algolia's corporate VPN/IT environment while it depends on Hermes. That matters because there's a real path to get PRISM adopted inside Algolia itself, and Hermes closes that door.

So Hermes needs to come out entirely. That opens 3 questions this manifesto tracks: who runs the system (executioner), who provides the chat experience, and what holds the data. The proposed direction is to rebuild on Algolia's own tech for all of it — partly for technical fit, partly because a PRISM built on Algolia is a much easier internal sell to Algolia's own leadership.

> **⚠️ DECISION UPDATE — 2026-07-06 (supersedes the "rebuild on Algolia tech" direction above).** Arijit chose **standalone product first**: V2 optimizes to become a sellable, domain-agnostic Prospect Research Operating System, with **Algolia as merely the first domain module**. Because the product is no longer built *for* Algolia's internal environment, the "easier internal sell" rationale no longer governs the architecture. The stack is now locked **best-of-breed: Postgres+pgvector (data/RAG) + Claude Agent SDK (executioner)** — NOT Algolia-as-DB, NOT Agent Studio-as-executioner. The Algolia-as-database and Agent-Studio-as-chat research below remains useful as *optional Algolia-domain-connector* context, but is no longer the core plan. See `_status.md` (2026-07-06 block) and `06-v2-execution-map.md`.

Three phases, each a re-architecture at a different level, for a different objective:

- **Phase 1** — replace the executioner/chat/data-backend stack (Hermes → Algolia tech + something for orchestration). Most concrete, most urgent, has open technical questions with real research attached.
- **Phase 2** — make every module of PRISM genuinely plug-and-play (independent versioning, a recipe-driven cockpit, today's skill-groups become standalone agents). Brainstorm stage, builds on whatever Phase 1 lands on.
- **Phase 3** — extend Phase 2 to be organization- and domain-agnostic, so PRISM becomes a sellable product (a "Prospect Research Operating System") rather than an Algolia-only internal tool. Furthest out, most speculative.

---

## Phase 1 — Executioner re-architecture

### The problem
- Hermes as executioner isn't working as needed. ~~Root cause unknown even after investigation.~~ **CORRECTED 2026-07-05** — see `04-open-gaps-before-fable5-handoff.md` item #2: two functional bugs were in fact root-caused and patched 2026-07-01; the deeper issue is architectural (Hermes runs the whole audit as one monolithic headless-claude call, no per-skill entry points/gating/self-heal), not an undiagnosed mystery.
- Hermes is 3rd-party, unchecked, self-hosted-agent code — blocks PRISM from ever running inside Algolia's VPN/corporate IT. Must be removed entirely. **Clarified 2026-07-05:** Hermes = Hermes Agent by Nous Research, a named third-party community agent runtime — the blocker tracks to being non-Anthropic vendor code, not to self-hosting per se. See `04-open-gaps-before-fable5-handoff.md` item #2 for the implication on remaining executioner candidates.

### What removing Hermes leaves open
Three roles need a new home:
1. **The executioner** — runs audits, tracks interim status, reports updates, controls the system end-to-end, and runs mandatory factcheck + quality-check gates at the end of every skill run (non-negotiable).
2. **The chat experience** — the conversational layer for querying results.
3. **The data backend** — wherever PRISM's data (audits, research, state) actually lives.

### Proposed direction: rebuild on Algolia tech
- **Data backend**: can Algolia itself be the database *and* index layer for all of PRISM's data, not just a search index over data stored elsewhere? Arijit: "no prior research exists here — you'll have to figure this out." → Task #3 in this session, findings go in `02-algolia-as-database.md`.
- **Chat layer**: can Algolia Agent Studio be the query/chat mechanism over that data? Arijit: "there's been a lot of prior research on Agent Studio — check the Algolia-Central repos first." → See `01-agent-studio-findings.md` (imported from existing research, see below).
- **Executioner**: the one fully open question. Candidates: Temporal (workflow engine), or Agent Studio itself. Required capabilities, stated explicitly and non-negotiably: run audits, check interim status, report updates, control the system end-to-end, run mandatory factcheck + quality check after every skill run.

### Research status (as of 2026-07-04)

**Agent Studio — substantial prior research exists**, found across `Algolia-Central2` (repo) and partially in the vault (`Projects/algolia-central2/wiki/`). Key finding directly relevant to the executioner question, from `docs/research/2026-06-27-coordinator-algolia-native-findings.md` (live-probed against a real Algolia app, not speculation):

> Agent Studio natively gives a **single agent** with a multi-step tool/search loop, NeuralSearch, and an MCP toggle. Live API probes confirm `/tools`, `/teams`, `/handoffs`, `/orchestrators`, `/workflows`, `/sessions`, `/memory`, `/templates`, `/functions`, `/skills` **all 404 — do not exist** as native resources. It does **not** give multi-agent handoff, a team/orchestrator primitive, server-side memory, or workflow control. "Agent Studio's 'orchestrator' is a classifier + client-side routing" — i.e. exactly the kind of custom code layer PRISM already has to write itself.

Also settled by prior research: native Agent Studio conversation memory does **not** carry context across turns via the completions API (tested 3 ways, confirmed negative) — any Agent Studio chat layer for PRISM would need the same stateless-replay-plus-dossier pattern already validated in Algolia-Central2, not rely on native memory.

**Working read on the executioner question, pending deeper investigation:** this existing research leans against "Agent Studio as executioner" — it has no native workflow/orchestration primitives, which is exactly what an executioner needs (multi-step control, status tracking, mandatory gating). It looks like a strong fit for the **chat layer** (single agent + NeuralSearch + tool loop is legitimate for that) but not for the **executioner** role. Temporal, as a purpose-built workflow engine, is the more natural fit for "run audits, track status, enforce mandatory gates end-to-end" — but this has NOT been separately verified against Temporal's actual capabilities yet. Open item.

**Critical prior-decision context, found in the vault (`Projects/PRISM/wiki/decisions/2026-06-28-prism-is-chowmes-prism-hermes-instance.md`), that changes the calculus:** Temporal was already tried and dropped once, on 2026-06-28, when PRISM was rearchitected onto Hermes. But the STATED reason was narrow and conditional: *"Keep Temporal for orchestration → rejected: second orchestrator alongside Hermes = duplicated state, no gain."* The rejection was specifically about redundancy with Hermes (which already had `kanban` + `cron` + durable subprocess covering queue/schedule/retry) — **not** a finding that Temporal itself is unsuitable. Since this new re-architecture removes Hermes entirely, the original objection no longer applies. Temporal should be re-evaluated fresh, not treated as a closed question — this is genuinely different context, not a repeat of the same decision.

**Algolia-as-database — no prior research found**, confirmed via vault + repo search. Fresh investigation needed; a full local Algolia REST/MCP API reference already exists (`Algolia-Central2/docs/algolia-api/`, 10 files) as a starting point. See `02-algolia-as-database.md` once written.

**Vault gap found and being closed**: the two documents above (`coordinator-algolia-native-findings.md` and the full `docs/algolia-api/` reference) existed only in the `Algolia-Central2` repo, never committed to the vault — exactly the "we keep re-researching the same thing" risk Arijit flagged. Being migrated now (see task tracking).

---

## Phase 2 — Modular / plug-and-play re-architecture

**Status: approved for brainstorming, not yet designed.** Builds on whatever Phase 1 lands on for the executioner.

Vision, captured verbatim from the source conversation:
- PRISM becomes a fully independent system where each module is genuinely plug-and-play — its own version control, independently developed, a standalone "lego block."
- A dashboard/cockpit lets an operator hand-pick which modules run for a given audit — not always the full pipeline.
- The operator's selection is a **recipe**; the executioner runs the recipe.
- This modularity naturally groups today's skill-groups into 3-4 standalone **agents**: a Researcher agent (holds all research skills), an Audit agent, a Synthesizer agent — today's informal groupings become first-class agents.

Nothing designed yet — architecture, module boundaries, and agent interfaces are open for discussion once Phase 1's executioner question resolves.

### Task list (captured 2026-07-05, not yet started)
- **Mandatory factcheck + quality-check gate after EVERY module run, not just once at the end.** Confirmed gap in the current pipeline (2026-07-05): today, `validate-json-schema.py` (schema), `factcheck_mechanical.py` + `algolia-audit-factcheck` (fact-check), and `algolia-audit-eval` (quality scoring) all run once against the FINAL assembled data, not per individual skill module — and `algolia-audit-eval` doesn't reliably run at all in the normal flow. This is exactly the executioner requirement from Phase 1 ("mandatory factcheck and quality check at the end of every skill run") — when modules become independent plug-and-play lego blocks, each one's own output should get gated on exit, before the next module (or the executioner) consumes it, not just once at the very end of the whole pipeline.

---

## Phase 3 — Domain/organization-agnostic productization

**Status: vision captured, not yet designed.** Furthest out, most speculative.

Vision, captured verbatim:
- Extends Phase 2's plug-and-play architecture to be organization-agnostic and domain-agnostic, making PRISM itself sellable.
- Illustrative scenario: build "YourCMS-PRISM" for a CMS company — swap out the Algolia-search-audit module and Algolia-specific sales-signal angles for that company's own business logic; PRISM becomes theirs.

### Restated + expanded, 2026-07-06 (Arijit, verbatim intent — record before further design)

- **Product framing:** an Enterprise Prospect Intelligence Platform. Working name riff only, not a decision: "PIP" / "EPI." Core metaphor: "PRISM domain — intelligence comes in, intelligence comes out."
- **Modularity restated:** modules brought in / taken out per business, business-specific domain logic is pluggable — Algolia gets a search-experience audit, a CMS company gets CMS-relevant logic, a commerce company gets commerce-relevant logic. Same shape as the existing "YourCMS-PRISM" example above, now with a second concrete example (commerce) and framed as the core product thesis, not a speculative furthest-out case.
- **Role-based consumption, as stated this session: "three audiences" — marketers, account executives, business development reps.** ⚠️ **Conflicts with the already-locked IA decision** (`05-role-driven-ia.md`, SESSION.md 2026-07-06: "4 role-doors — AE/BDR/Sales Leader/Marketer"). Not silently reconciled — Arijit needs to confirm whether Sales Leader is dropped from V2 scope or was just an omission in speech. Open question, tracked in `04-open-gaps-before-fable5-handoff.md`.
- **Chat is the operator, not just a Q&A layer** — "chat is the sort of guider and the operator, and then we will deliver the outputs as well." Reinforces the Chat agent design in `04-open-gaps...md` gap #8, but elevates its UX role: chat drives the interaction, execution, and status-check surface, not a bolt-on search box.
- **Design-quality bar:** explicit instruction to reuse PRISM's own live VPS UI standards (prism-hub buttons, animations, templates already shipped) as the quality bar for any V2 screens — reuse-first, not a fresh design-system invention.
- **The ask:** a full engineering/execution plan for a "V2" covering chat, interactions, execution, status checks, channels, and all role-based screens, intended to be handed to Fable 5 to build. Timeline stated: hopes for a built V2 by morning. **Flagged as unrealistic tonight given open state — see SESSION.md 2026-07-06 for the direct pushback and the gaps that block a responsible handoff.**
- Business framing: this could become a new company/product for Arijit — PRISM repositioned as a **"Prospect Research Operating System,"** a category Arijit believes doesn't exist yet.

Not designed — flagged as needing real thought/research/discussion once Phase 2 has more shape.

---

## Standing rules for this manifesto

- No fabricated feasibility conclusions. Where research is inconclusive, say so plainly.
- Phase 2 and 3 stay at brainstorm/capture level until Phase 1's executioner question is resolved — don't design ahead of the foundation.
- **RULE UPDATED (Arijit, 2026-07-05): this repo (`docs/PRISM-V2/`) stays canonical/live-edited. Vault mirror now ALSO required** at `Projects/PRISM/wiki/V2/` (Arijit's explicit call — "record everything in the vault so we don't lose our decisions") — re-copy there after each working session, never edit the vault copy directly. Supersedes the original 2026-07-04 PIP-only rule, kept here for provenance: ~~all V2 research/planning documentation lives ONLY under `docs/PRISM-V2/` in this repo — never the vault, never `~/.claude/prompt-library/`, nowhere else.~~ Findings with durable cross-project reuse value (Agent Studio capabilities, the Algolia API reference) still belong in the vault under their own topic too (e.g. `Projects/algolia-central2/`).

---

## Original request (verbatim, for provenance)

Captured via prompt-shaper before this document existed. Kept here so no nuance from the original ask is ever lost.

> Take all that. Apply my prompt skill to break this down and break it down into pased plan and lets brainstorm to build this further. Under docs create a new directory called PRISM-V2, and start storing this plan there so we dont loose it and we can keep building on it. THis is the starting of the v2 manifesto we are just beginnign here. And we will be iterating through it and building on mre and more.
>
> so while that sweep is going on, here is what I would like to do. I would like to start planning on the next phase of PSISM and this phase is a huge redesign and major update, so please start recording what I am giving you and htere will be a lot and 3 distinct phases. All the 3 phases are about re-architecure, but re-architecur done at dirrent level for differnet objecives :
>
> Phase 1: Executiioner rearchitecture.
> Today I am trying to use Hermes as the executionaer. So far it does not sem to be workingg in the manner I need it to and you also cannot figure it out. I do not know the reason why. Also the fact that Hermes as an agent causes several security nighmare challenge for any corporate IT, and the code is 3rd party and unchecked, this creates a challenge for PRISM that it can never be brought into Algolua VPN. SO I need to get rid of Hermes compelte from PRISM, however that will leave with the questions as to then what will be the executioner and the manager who is runnign the system? As well as who is going to provide the chat experience? And for that we will solve the problem by using Algolia tech. So this new rearchitecure of the system will be to use Algolia as the data backend. Instead of storing in database why not we store all our data in Algolia. Algolia is stateless, so can it be the database and the index layer to house all our data? And second this is can Algolia Agent Studio become that chat layer and provide the mechanish to query the algolia data and provide the chat experience. We need to thoroughly research on this and figure out. There has been many research done on agent studio before, you can check on my Algolia-Central repos for the differnt findings about agent studio. And fo using algolia as the database to store index content, that part you will have to research on yoru own and figure out if that is possible. So this leaves us with the only unanswerd quesions that is who will be the executioner, and for that I think probably we have to go back to the temporal route, or find another solution here. The executioner is a very important task ehre, and he will need to be abel to run audits, check interim status, report back updates and control the system end to end. Also it needs to run mandatory factcheck and quality check at the end of every skill run. So can tempral do that and say if we want agent studio for this also, can agent studio become the executioner? If we are re-building it all using algolia tech, then it will be less challenge for me to convince algolia management to bring the tool inside algolia.
>
> Phase 2. In this reacchitecture i woudl liek to research and think about how PRISM can be transformed into a compelte independat solution where wach module is completely plug and play. There will be a dashboard and the operator can select a specif part of the audit torun, like a custom cockpit with a bunch of lego blocks. THe operator builds a revepie and the recepie is the selection of modules ot run and then the executionaer will run it. So each of the module will live independant and have their own version control and can even be developed indipendently and htey are all individual lego blocks. This way we can actually build 3-4 agents, a researcher agent, which will ahve all the research skills, ta audit agent, a synthsizer agent, pretty much the groups that we have they become agents. So lets think through this and lets brainstorm and disss further.
>
> Phase 3 is : extending further from phase 2, how can we make this plug and play to become organiaion agnostoc and domain agnostic. So it will make the tool sellable. Tomorrow I can goto a CMS company and say hey let me build you a "YourCMS-PRISM" module, and say that replaces the algolia search audit module and all the sales signal angles that I am doing today for Algolia, it will get replaced by that company's business. And then PRISM becomes for that cmpany. This way I can actually build a company from PRISM and sell the softwrae. This will actually open up a whole new realm for me to start a new business and PRISM actually becomes a Prospect resaerch operating system, somethign that really does not exist today. This is also a huge areas to think into and researh and discuss more.
