# Fable-5 Handoff Prompt

Copy-paste the block below to kick off Fable 5 on PRISM V2. It scopes the **first executable package only** (Tracks A/B/G-schema/C) — E/F/H stay in brainstorm until the executioner POC lands.

**Inputs now resolved (2026-07-06):**
- **DEADLINE (D8):** same-day demo pressure — Arijit wants a live, demoable slice *today* for Algolia Marketing + Sales leadership. The full backend rebuild is NOT same-day; the demoable slice = the 3 role doors + the Marketing landing-page capability, shipped live. Fable 5's package remains the multi-week backend; the same-day slice is being built directly in-session, not by Fable 5.
- **BETA TARGET (D7):** **Algolia Marketing + Sales leadership** (internal-friendly-first, even though the north star is standalone). **Marketing's #1 ask = the ability to BUILD LANDING PAGES** (the Algolia+Jahia landing-page style — see `docs/example-and-context/algolia-jahia-landing-COMPRESSED.pdf`; Dell semi-test-run exists at `~/prism/marketer/dell.html`). This elevates the Marketer landing-page builder from a stub to a **first-class MVP feature**.
- **Second pitch target + domain-swap thesis:** **Spryker** is the next big external pitch. The swappable domain module (replacing `algolia-search-audit` + Algolia sales angles) should target a set of Algolia-adjacent commerce/DXP/CMS/DAM vendors: **Spryker, Amplience, Contentful, Cloudinary**, etc. Design the domain-pack interface (R7/Track F) with these concrete first swaps in mind.

---

> **You are Fable 5, executing the PRISM V2 build. PRISM is being rebuilt as a standalone, domain-agnostic "Prospect Research Operating System" — a sellable product, not an Algolia-internal tool. Algolia is just the first domain module.**
>
> **Read first, in order:** `docs/PRISM-V2/_status.md` → `06-v2-execution-map.md` (your build spine) → `07-design-system.md` (the design language you build every screen against) → `05-role-driven-ia.md` (role IA) → `docs/research/Discovery-OS-v1.md` §9 (the finding/call-plan schema). Do not re-derive decisions already locked in `06` §1.
>
> **Ground rules (non-negotiable, from the project CLAUDE.md):** best-of-breed stack — Postgres+pgvector + Claude Agent SDK, NOT Algolia-as-DB, NOT Agent Studio. Pydantic on every boundary. Tests ship with every module (unit + integration + contract). Never claim done without running `ruff check . && ruff format --check . && mypy src/ --strict && pytest -v` and showing output. Evidence + source on every data point — zero fabrication; where data is unknown, render an explicit empty slot, never a guess. Nothing deploys to prism.chowmes.com or main without an attended review.
>
> **Do NOT resolve these by invention — stop and flag them** (they are `06` §7 blocked decisions): the 3 IA working assumptions (D4), the Discovery-OS gating-rule ambiguity (D5, hard-suppress vs mandatory-M9), executioner self-hosted-vs-managed (D1), durable-retry approach (D2). Also honor: HeyGen/LiveAvatar + Telegram are Phase-2, do not build them.
>
> **Your work package, in order:**
>
> **1 — Design system (Track B).** From `07-design-system.md`, emit `prism-tokens.css` (the reconciled §1 tokens) and `prism-components.css` (ONE button system with primary/secondary/ghost/pill + hover/active/focus/disabled, plus cards/tables/tiles), applying the §1 reconciliations that fix the source's inconsistencies. Retrofit the existing Marketer door (`~/prism/marketer/door.html`) onto these files.
>
> **2 — Role doors, breadth-first (Track A).** Build the **AE door** and **BDR door** to match the shipped Marketer-door pattern, reading already-published `audit-data.json` per account — no executioner/VPS dependency. Per-role scope, culls, and components are in `06` §3: AE = 3-stage cockpit (PREP→SS1→SS2, SS3/SS4 culled) + the Discovery-OS single-page call plan as the PREP hero; BDR = signal-ranked queue + micro-Exchange outreach (deep financials/MEDDPICC/stages culled); Marketer already built (finish its stubbed ABM Brief + disabled buttons). ui-validator pass + Playwright verify at 1280/375px. **Goal: all 3 doors live and demoable.**
>
> **3 — Discovery OS schema (Track G-schema).** From Discovery-OS-v1 §9 (spec condensed in `06` §4), define the Pydantic Finding / Behavior / Feedback / Branch objects (13 finding categories, confidence, risk_if_wrong, evidence-grounding, the two DISTINCT archetype fields, persona_fit). This schema must be settled before the Postgres schema freezes. Also scaffold the `/standards-discovery-os` skill.
>
> **4 — Executioner + data backend (Track C), POC FIRST.** Before building the full executioner, run the e2e POC (R1): prove Claude Agent SDK can do multi-step audit control + subagent dispatch + Postgres-backed `SessionStore` + status tracking + hooks-as-gates running fact-check+QA after EVERY module run. This needs a real `ANTHROPIC_API_KEY` — request it if absent, do not stub around it. Only after the POC passes, design the Postgres+pgvector schema (audits/research/state/vectors, using the Track G-schema Finding object) and the migration off the current `prism-runner` + `prism_platform`. Reuse the already-proven `run_audit`/`live_status` tool mechanism from `docs/workspace/hermes-prism-integration/phase-b-cass-agent/L2-execution-orchestration-design.md` — do not redesign the agent protocol from scratch.
>
> **Context for scoping:** deadline = same-day demo for **Algolia Marketing + Sales leadership** (the beta cohort). **Marketing's #1 ask is landing-page building** (Algolia+Jahia style) — treat the Marketer landing-page builder as a first-class MVP feature, not a stub. Second external pitch = **Spryker**; the domain-swap set to design toward is Spryker / Amplience / Contentful / Cloudinary.
>
> **Report format:** for each of the 4 items, report done/deferred/blocked with the verification command output. Surface every blocked decision back to Arijit rather than guessing. Chat-as-operator (Track D), modular rearchitecture (E), and productization+GTM+pricing (F/H) are the NEXT package — do not start them in this run.

---

**Before you send it:** answer D7 (beta target) and D8 (deadline) so the two brackets are filled — otherwise Fable 5 scopes the MVP blind.
