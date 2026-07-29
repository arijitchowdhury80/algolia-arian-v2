# PRISM V2 — Execution Map & Fable-5 Handoff Spine

**Created 2026-07-06.** This is the ordered build plan for PRISM V2 — the document you hand (in pieces) to Fable 5 for e2e execution. Read `_status.md` first, then `00-manifesto.md` for the why. Companion artifacts: `07-design-system.md` (the reusable design language), `08-fable5-handoff-prompt.md` (the copy-paste kickoff prompt).

Sources feeding this map: the manifesto (all 3 phases), `04-open-gaps-before-fable5-handoff.md` (gaps #11–13), `05-role-driven-ia.md` (role IA), `docs/research/Discovery-OS-v1.md` (§9 PRISM Translation Ruleset), and two grounded sub-agent extractions run 2026-07-06 (per-role component inventory + design-system extraction).

---

## 0. The one-paragraph frame

PRISM V2 is being rebuilt as a **standalone, domain-agnostic Prospect Research Operating System** — a sellable product, not an Algolia-internal tool. Algolia is now just the **first domain module**. The stack is **best-of-breed**: Postgres + pgvector (data + grounded RAG), Claude Agent SDK (self-hosted executioner + agents), reusing PRISM's already-shipped premium design language. The near-term proof point is **all three role doors (AE / BDR / Marketer) live on prism.chowmes.com** — demoable to a real person — because they read already-published audit data and need none of the hard backend rebuild. The hard backend (executioner re-architecture, chat-as-operator, grounded RAG, modular lego rearchitecture, productization + pricing) is sequenced behind that first visible win.

---

## 1. Locked decisions (the ground truth Fable 5 builds against)

| # | Decision | Locked | Source |
|---|----------|--------|--------|
| L1 | **North star = standalone sellable product.** Algolia = first domain module, not the platform. Phase 3 productization is the thesis. | 2026-07-06 | this session |
| L2 | **Internal-Algolia-adoption is NOT the design constraint.** The "rebuild on Algolia tech for the internal sell" rationale is retired. | 2026-07-06 | this session |
| L3 | **Data + RAG backend = Postgres + pgvector.** One store for audits, research, state, and vector retrieval. | 2026-07-06 | this session (confirms SESSION.md) |
| L4 | **Executioner + agents = Claude Agent SDK, self-hosted.** Not Agent Studio, not Algolia-as-DB. (Agent Studio may later be an *optional Algolia-domain connector*, not core.) | 2026-07-06 | this session; `03-executioner-claude-agent-sdk-findings.md` |
| L5 | **6 agent roles:** Orchestrator, Researcher, Auditor, Synthesizer, Chat (standing), + Verification Pipeline (5-stage: mechanical → fact-check → 3-agent adversarial → quality score → legal gate). Zero-tolerance-for-fabrication / full-tolerance-for-omission. | prior | SESSION 2026-07-06 |
| L6 | **3 roles in V2 scope: AE, BDR, Marketer.** Sales Leader deferred (the IA doc still specs it — treat as designed-not-built, out of scope). | 2026-07-06 | this session |
| L7 | **First visible milestone = all 3 role doors live (breadth-first).** Chat/execution wired after. | 2026-07-06 | this session |
| L8 | **Design system source of truth = the SPA template** (`index-template.html` + `algolia-brand.css`), extracted into a reusable design language. Reuse-first, no fresh invention. | 2026-07-06 | this session; `07-design-system.md` |
| L9 | **Deprioritized to Phase 2:** HeyGen/LiveAvatar embodied avatar + Telegram notify. Both built + staged, parked. Base functionality first. | 2026-07-06 | this session |
| L10 | **Multi-tenant is the target from day one** (shared tables + `tenant_id` + Postgres RLS, first-pass shape). Not yet built. Auth provider open. | prior | `04-...gaps.md` #12 |

| L11 | **Beta target = Algolia Marketing + Sales leadership** (internal-friendly-first). **Marketing's #1 ask = landing-page building** (Algolia+Jahia style) → the Marketer landing-page builder is a first-class MVP feature, not a stub. | 2026-07-06 | this session |
| L12 | **Same-day demo pressure:** a live demoable slice is wanted TODAY — scoped to the 3 role doors + the Marketing landing-page capability (built in-session), NOT the backend rebuild (which stays multi-week). | 2026-07-06 | this session |
| L13 | **Second external pitch = Spryker.** Domain-swap set to design the domain-pack interface toward: **Spryker, Amplience, Contentful, Cloudinary** (Algolia-adjacent commerce/DXP/CMS/DAM). | 2026-07-06 | this session |

**Still OPEN (see §7):** self-hosted SDK vs Managed Agents API, durable-retry approach, auth provider, the 3 IA working-assumptions, the Discovery-OS gating-rule ambiguity, pricing/metering model, Jarvis STT/TTS vendor, product name. *(Beta target + deadline now resolved — L11/L12.)*

---

## 2. The build, sequenced — 8 tracks

Ordered by dependency and by "show results fast." Tracks A/B ship the first visible win with zero backend rebuild. C→D→E→F is the real product spine. G (Discovery OS) and H (commercial) run partly in parallel.

```
NOW ───────────────────────────────────────────────► PRODUCT
 A. Role doors (breadth)  ─┐
 B. Design system          ─┴─► first demo (3 doors live)
 G-schema. Discovery OS data model ─┐
 C. Executioner + Postgres/pgvector ─┴─► real backend
 D. Chat-as-operator + grounded RAG ────► the operating system
 E. Modular lego rearchitecture ────────► plug-and-play
 F. Domain-agnostic productization + multi-tenancy ─┐
 H. Prod-readiness + GTM + pricing/metering ────────┴─► sellable beta
```

### Track A — Role doors, breadth-first  ⟶ *the first visible result*
Build **AE door** and **BDR door** to match the already-built **Marketer door** (`~/prism/marketer/door.html`), reading already-published `audit-data.json` per account. Deploy all 3 live to prism.chowmes.com. No executioner/VPS dependency — this is why it ships fast.
- **Reuses:** the Marketer door pattern (proven), the design system (Track B), the per-role IA (`05-...` + §3 below).
- **AE door** carries the Discovery-OS single-page call plan (from published data where present; explicit empty-slots where not — never fabricate).
- **Blocked on Arijit:** re-confirm the 3 IA working assumptions (D4 in §7) before building AE/BDR — they change the door architecture.
- **Definition of done:** 3 doors live, real data rendering, ui-validator pass, Playwright-verified at 1280/375px, deployed and demoable.

### Track B — Design system as a reusable asset  *(parallel to A, feeds A)*
Package the extracted design language (`07-design-system.md`) as: (1) a single source-of-truth tokens file (CSS custom properties) every V2 screen imports, (2) documented component specs, (3) the **Claude Design prompt** (seeded with real tokens) for future generation. This becomes Arijit's signature system.
- **Reuses:** `index-template.html` + `algolia-brand.css` verbatim as the source.
- **Note:** the source has real inconsistencies (two `--shadow` roundings, two content max-widths, JS gauge greens ≠ CSS `--green`, no `:disabled` states, sidebar position flips). Track B's job is to *reconcile these into one clean token system* — that reconciliation IS the value-add, documented in `07`.

### Track G-schema — Discovery OS data model  *(design alongside C1, it defines the schema)*
Turn Discovery-OS-v1 §9 into the finding/behavior/feedback/branch schema (see §4). This must be designed **before** the Postgres schema is frozen, because the Finding object (13 categories, confidence, risk, evidence, archetype, persona) is the atomic unit the whole store holds.

### Track C — Executioner re-architecture  ⟶ *the hard backend, Phase 1 core*
Remove Hermes entirely. Build the executioner on Claude Agent SDK + Postgres/pgvector.
- **C1 — Data backend:** Postgres + pgvector schema for audits, research, state, and vector RAG. Migrate off the current `prism-runner` (127.0.0.1:8770) + `prism_platform` FastAPI. Finding-object schema from Track G-schema.
- **C2 — Executioner:** Claude Agent SDK — multi-step control, subagent dispatch, `SessionStore` backed by Postgres, status tracking, and **hooks-as-gates** (`decision:"block"`) running mandatory fact-check + quality-check after **every module run** (not just once at the end — the confirmed pipeline gap, `00-manifesto.md` Phase-2 task list).
- **C3 — Durable retry:** the one capability the SDK lacks vs Temporal. Decide (D2): SDK + external queue, or Temporal re-introduced (its original "redundant with Hermes" objection is void now that Hermes is gone).
- **Gate before C is trusted:** an actual e2e POC (R1) — needs a real `ANTHROPIC_API_KEY`. The executioner ADR stays unwritten until the POC runs.

### Track D — Chat-as-operator + grounded RAG  ⟶ *the "operating system" feel*
The chat agent that **guides, operates, executes, notifies, and checks status** — not a bolt-on search box (Arijit: "chat is the guider and the operator"). Grounded RAG retrieval over pgvector powers every agent's knowledge — zero ungrounded claims.
- **Reuses:** the already-designed & live-verified `run_audit` / `live_status` tool mechanism (`L2-execution-orchestration-design.md`, 2026-06-29 — proven to work tonight). Do NOT redesign the agent-to-agent protocol from scratch; it exists.
- Wires the 6 agents (L5) behind chat. Depends on C.

### Track E — Modular lego rearchitecture  *(Phase 2)*
Each module = independent, own version control, plug-and-play. A **recipe cockpit** lets the operator hand-pick which modules run; the executioner runs the recipe. Today's skill-groups become first-class agents (Researcher / Audit / Synthesizer). Per-module fact-check + QA gate on exit. Depends on C (executioner runs recipes).

### Track F — Domain-agnostic productization  *(Phase 3 — now the thesis)*
Abstract the Algolia-specific logic into a swappable **domain pack**. Define the domain-pack interface: what a "YourCMS-PRISM" or "Commerce-PRISM" plugs in to replace the algolia-search-audit module + Algolia sales angles. Multi-tenancy (L10: shared tables + `tenant_id` + RLS). This is what makes PRISM sellable.

### Track H — Production readiness + GTM + pricing/metering  *(Phase 3 commercial)*
E2E production-readiness (security gap #13 — no shape exists yet; multi-tenancy hardening; auth; observability; SLAs), GTM strategy (position as the "Prospect Research Operating System," a category Arijit believes is empty), pricing model, usage **metering instrumentation**, and a beta program. Research-heavy (R8/R9). Start research early in parallel; build after E/F.

---

## 3. Per-role IA — what's built, pending, and cullable

Full inventory in the sub-agent extraction; condensed for the plan. Status: **BUILT** (code exists) / **DNB** (designed-not-built) / **PENDING** (named, not specified).

### Shared-across-roles (build once, reuse)
| Component | Status | Note |
|---|---|---|
| Top chrome: role switcher + account switcher + settings | PARTIAL | Marketer door has static chips, not the dropdown/search UI the IA specs. No "Run new via Jarvis" entry point. |
| Shared-core strip (company + score + "framed-for-you" tag) | BUILT (score) / PENDING (killer-finding) | `killer_finding` is not yet a shared primitive; Marketer repurposes `narrative_hook`. |
| Verification made visible (citation marker + ✓/redacted badge) | PARTIAL | One hard-coded instance on Marketer; the general "render everywhere a Finding shows" rule + redacted-chip are not built. This is the front-end of the Discovery-OS evidence-grounding requirement (§4). |
| Jarvis cockpit (voice/text overlay, recipe picker, live receipts) | DNB | Full ASCII spec exists, zero code. STT/TTS vendor open (D9). |
| Data-source stub cards (✅ active vs 🔒 would-add-value) | BUILT (Marketer) | Proven pattern, flagged reusable — extend to AE/BDR. |

### AE door — all DNB (no code exists)
- Stage cockpit **corrected to 3 stages: PREP → SS1 → SS2**. **CULL: SS3 (POC/Go-Live) and SS4 (Scoping/Proposal) entirely** — "neither of us has a role there."
- 60-sec pre-call brief (= the Discovery-OS single-page call plan, §4), exit-gate checklists, Battle Card (**MODIFIED**: Golden-Angle/demo content that lived in the culled SS3 is dropped), AE Playbook (MEDDPICC gap map + SPIN), Business Case/ROI (**moved SS4→SS2** — must exist before negotiation).
- Deep-links INTO the existing 5-tab SPA rather than rebuilding it (PENDING — one of the 3 assumptions to confirm, D4).
- **Culled for AE:** portfolio/aggregate views (Leader's job), BDR outreach mechanics.

### BDR door — all DNB
- Prioritized account queue ranked by signal strength (hiring/news/social — volume-friendly, not deep financials), hero card + one-click ABX outreach, "why now" signal line, triage chat mode.
- Outreach = **micro-Exchange** (one insight + one calibrated question — the "0.1-page" call plan, §4).
- **CULL (strongest in the doc):** deep financials, MEDDPICC depth, and the entire stage cockpit — "BDR isn't running a deal, they're generating one."

### Marketer door — the one BUILT role
- BUILT: narrative-hook hero + verified badge + source citation, `[Preview landing page]`, data-source active/locked grid, per-account JSON fetch.
- DNB/stubbed: `[Review before Jahia push]`, `[Download leave-behind/ABX]` (hard-disabled), the **ABM Brief** artifact (fully specced two-zone auto-vs-Sales-input, no code), content co-pilot chat.
- **CULL for Marketer:** deep financials, MEDDPICC/deal-stage mechanics, BDR queue — **and no stage pipeline at all** ("Marketer's work isn't gated to a deal stage").

### 3 working assumptions to re-confirm before AE/BDR build (→ D4)
1. Role switcher = a toggle anyone can flip (filter, not ACL / per-login).
2. Marketer door = a **review surface** in front of the existing Figma→Jahia pipeline, NOT a second page-builder.
3. Existing 5-tab SPA = the deep-link target for all roles (and Leader's drill-through), NOT rebuilt per role.

---

## 4. Discovery OS → PRISM build requirements (Track G)

From Discovery-OS-v1 §9 (PRISM Translation Ruleset). These define the schema and the AE experience.

**Core data objects (every audit finding must carry these — not just a claim string):**
- **Finding object:** `category` (13 codes: SA/EC/TS/HS/FS/CA/BC/WB/TE/AC/BL/RG/CM), `evidence{type,payload,source_url,timestamp}`, `confidence{High/Med/Low}`, `freshness`, `archetype_fit`, `persona_fit{Merch/Product/Eng/Exec}`, `risk_if_wrong{Low/Mod/High}`.
- **Translation layer:** `translate(finding, persona, deal_context, competitive_context, confidence_threshold)` → opening move + calibrated hypothesis + exchange sequence + question stack + objection pre-map + champion narrative + next-meeting hook + outbound-email angle + disclosure timing. (This is the "diagnosis-to-action engine" v1 lacks.)
- **Behavior object:** content + type + confidence + evidence_tier{🟢🟡🔵} + archetype_fit + persona_fit + risk_if_wrong + best_use_stage + do_not_deploy_if + visual_proof + external_citation. **Hard rule:** `risk_if_wrong=High` → mandatorily attach M9 (Documented-Fallibility Disclosure).
- **Feedback object** (rep writes post-call): hypothesis_id + buyer_reaction{confirms/amends/rejects/deflects/...} + verbatim reaction language + next_move + MEDDPICC fields updated. The write-side that lets PRISM learn.
- **Branch engine:** `branch(reaction_type, role, stage, deal_state)` → next move + proof asset + stakeholder + MEDDPICC update + `escalation_flag` (true after 2 consecutive rejections; **1** for scaffolded/junior reps — make the threshold per-rep-tier configurable, not a constant).

**The single-page call plan (AE PREP hero artifact) — exactly 7 elements, no more:**
1. Opening move (F1–F6, rule-selected by detected competitor). 2. Three ranked hypotheses, ranked `(Confidence × Business Impact) ÷ Risk`. 3. Branch tree per hypothesis. 4. One competitive objection + response. 5. One cost-of-inaction cue. 6. One stakeholder to add (must be one the buyer did NOT volunteer, from hiring/LinkedIn data). 7. One calendar-able next-meeting hook. *Compression is itself a spec: >1 page = failed, not over-delivered.*

**THE gating rule (most-emphasized in the doc):** Low-Confidence × High-Risk-if-Wrong findings must never reach a rep-facing surface. → But see the ambiguity below.

**Role applicability:** AE = full. BDR = micro-Exchange only (1 insight + 1 question outbound generator). Marketer = findings/confidence subset, no call-plan/branch (no discovery motion).

**Also:** codify a reusable **`/standards-discovery-os`** skill (like the other `/standards-*`) AND bake the call-plan output into the AE door.

**⚠️ Two source-doc ambiguities Fable 5 must NOT resolve by invention — need Arijit (D5) / engineering:**
1. **Gating rule conflict:** the doc says both *hard-suppress* Low-Conf×High-Risk (L620/L1102) AND *surface-but-label-and-gate-behind-mandatory-M9* (call-plan example L975–977). Pick one.
2. **"Archetype" is overloaded:** deal-context archetype (Greenfield / Incumbent-displacement / Platform-consolidation / Composable-migration) vs move-type archetype (Teach/Test/Triage/Acknowledge/Translate/Escalate). Two distinct schema fields — never merge.

---

## 5. Modular + productization design questions (Tracks E/F) — to brainstorm, not yet designed

- **Module boundary contract:** what's the interface every lego module implements (input schema, output schema, its own exit fact-check+QA gate)?
- **Recipe format:** how the operator's module selection is expressed and how the executioner consumes it.
- **Agent grouping:** confirm Researcher / Audit / Synthesizer boundaries against today's skill-groups.
- **Domain-pack interface (F):** the swappable unit that replaces `algolia-search-audit` + Algolia sales angles for another company/vertical. This is the crux of "sellable."
- **Multi-tenancy (L10):** shared tables + `tenant_id` + RLS — validate; pick auth provider (D3).

---

## 6. Production-readiness + GTM + pricing/metering (Track H) — the commercial gap

We have: a working audit engine, 18+ published reports, a premium UI, a methodology (Discovery OS). We do NOT have: multi-tenancy, auth, a security/deployment topology (gap #13, zero shape), usage metering, a pricing model, a GTM motion, or a beta cohort. Track H turns "a tool Arijit runs" into "a product others pay for."
- **Prod-readiness plan:** security topology, tenant isolation, secrets management, observability, SLAs, cost/ops sizing (old gap #4).
- **GTM:** category creation ("Prospect Research Operating System"), ICP, beta cohort, positioning vs. status quo (manual research / point tools).
- **Pricing + metering:** decide the metering unit (per-audit? per-seat? per-domain-pack? per-account-researched?) and instrument it from day one — retrofitting metering is painful.

---

## 7. Open research (R) and blocked decisions (D)

**Research to run (each is a Fable-5 or sub-agent task):**
- **R1** Claude Agent SDK executioner e2e POC (needs `ANTHROPIC_API_KEY`) — prove multi-step control + per-module gating + Postgres SessionStore + retry. *Gates Track C.*
- **R2** Managed Agents API live-probe (the 5th candidate, never probed) — self-hosted SDK vs Anthropic-managed. *Feeds D1.*
- **R3** Postgres + pgvector as unified store — schema + RAG + migration path from current runner/`prism_platform`.
- **R4** Durable-retry: SDK+queue vs Temporal re-eval. *Feeds D2.*
- **R5** Multi-tenancy validation (shared tables + tenant_id + RLS) + auth-provider options.
- **R6** Security/deployment topology (gap #13 — no first-pass shape exists).
- **R7** Domain-pack interface design (Phase 3).
- **R8** Pricing/metering benchmarks — comparable intelligence-platform pricing + the right metering unit.
- **R9** GTM / category / beta-cohort research.
- **R10** Cost/ops sizing for Agent SDK infra at scale.

**Decisions blocked on Arijit:**
- **D1** Self-hosted Claude Agent SDK vs Managed Agents API (after R2).
- **D2** Durable-retry approach (Temporal back in, or SDK + queue).
- **D3** Auth provider for multi-tenant.
- **D4** The 3 IA working assumptions (§3) — needed before AE/BDR build.
- **D5** Discovery-OS gating-rule ambiguity (hard-suppress vs mandatory-M9).
- **D6** Pricing model + metering unit.
- **D7** Beta target — an external company (which?), or Algolia AEs as friendly-first even though not the north star?
- **D8** Deadline / pressure driving "show results soon" (still unanswered — shapes MVP scope).
- **D9** Jarvis STT/TTS vendor (separate from the deprioritized HeyGen visual layer).
- **D10** Product name / category label (PIP / EPI / other — "Prospect Research Operating System").

---

## 8. Recommended immediate sequence (my call as your partner)

1. **This week — ship the visible win.** Tracks A + B: confirm D4 (3 assumptions), finalize the design-system tokens, build AE + BDR doors to the Marketer pattern, deploy all 3 live. One demoable URL. Breaks the built-but-not-shipped pattern.
2. **In parallel — de-risk the backend.** Run R1 (executioner POC, needs the API key) and R3 (Postgres/pgvector schema, informed by the Track G-schema finding-object). These two decide whether the whole Phase-1 rebuild is sound before we pour weeks into it.
3. **Then** Track D (chat-as-operator on the proven executioner), then E (modular), then F+H (productization + commercial) — with pricing/metering research (R8) started early so metering is designed in, not bolted on.

Fable 5 gets Tracks A/B/G-schema/C as the first executable package (see `08-fable5-handoff-prompt.md`). E/F/H stay in brainstorm until C's POC lands.
