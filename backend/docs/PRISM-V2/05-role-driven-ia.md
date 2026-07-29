# PRISM V2 — Role-Driven IA (4 personas)

Started 2026-07-05. Extends locked decisions from memory `project-prism-ui-persona-journeys` (AE/BDR/Sales-Leader, build order, design language) and `project-prism-role-driven-ia` (shared-core + role-lanes model). Adding **Marketer** as the 4th persona per Arijit's explicit direction this session — note: an earlier memory (`project-prism-role-driven-ia`, 2026-07-01) had briefly used Marketer/AE/BDR as the 3-role set with no Sales Leader; treating Arijit's current statement (AE/BDR/Sales-Leader as original 3, Marketer newly added as 4th) as authoritative and current.

## Locked, not re-litigated
- **Model: shared core + role lanes.** One audit, one engine. Every role sees the same underlying score + killer finding (small "framed for you" chip changes), then a role-specific slice on top. Not full partition — don't triplicate findings 4 times.
- **6-tab dashboard was already rejected as the universal front door** (2026-06-27 ADR: "functionally wrong... assumed one UI for all users"). It still exists as a real thing — just relocated to where it actually belongs (Sales Leader's aggregate view).
- **Design language:** Claude-Desktop-calm resting state (warm-neutral, low chrome, content-first, artifact panel slides in on demand) + Codex-Desktop-style streaming step receipts while an audit is actively running. Conversation-as-hero, not chrome-as-hero.
- **Stack:** static vanilla JS/CSS (prism-hub), no React, no build step. This IA must be buildable in that stack — no component-tree assumptions that need a framework.

## The 4 doors — front door, hero, and what's de-prioritized

| Persona | Front door / hero (what they see FIRST) | De-prioritized / hidden by default | Chat mode |
|---|---|---|---|
| **AE** | 5-stage cockpit (PREP→SS1→SS2→SS3→SS4), exit-gate checklists (green/amber/red). Hero card = 60-sec pre-call brief + business-case artifact for whichever account they're prepping right now. | Aggregate/portfolio views (that's the Leader's job), BDR's outreach sequencing mechanics | Drill co-pilot — "why does this account matter, what's the counter to Constructor.io here" |
| **BDR** | Prioritized account queue, ranked by signal strength (hiring/news/social — the volume-friendly signals, not deep financials). Hero card = the account at the top of the queue + its personalized outreach (ABX) package, one-click to send. | Deep financials, MEDDPICC depth, the 5-stage cockpit (BDR isn't running a deal, they're generating one) | Triage command — "which 5 accounts should I hit today, why these" |
| **Sales Leader** | Portfolio dashboard — this is where the old 6-tab view actually lives now. Heatmap across the whole book, ranked accounts by $ opportunity, aggregate win-rate signal. | Nothing hidden — Leader is the one persona who legitimately wants everything, aggregated. This is the superset view, not a stripped one. | Rollup query — "which reps are stalled at SS2, why" |
| **Marketer (new)** | Content/campaign angle, not deal-stage. Hero = the audit's marketing-usable findings surfaced first: traffic/industry/competitor positioning, the landing-page-ready narrative, ABX/leave-behind assets. Financials and deal-stage mechanics are irrelevant to this role. | Deep financials (AE's job), MEDDPICC/deal-stage (not their motion at all), BDR's queue mechanics | Content co-pilot — "what's the one narrative hook this audit gives me for a landing page/campaign" |

Existing artifact→role map (from `project-prism-role-driven-ia`) already had Marketer partially defined — reused here: **Marketer ← traffic / industry / competitors / investor → landing page, ABX, leave-behind.**

## Access model: filter, not lockdown — recommendation, your call still open

You raised this as open: full ACL vs. "everyone can see everything, just filter by role." Recommendation: **filter, not ACL.** This is an internal Algolia GTM tool (not a multi-tenant product with real security boundaries between customers) — the risk a hard permission wall protects against (one customer seeing another customer's data) doesn't apply here; everyone in this tool is on the same team looking at the same prospect. A role filter that reshapes what's foregrounded, with a "see everything" escape hatch for power users (e.g. a Leader who wants to peek at a specific AE's cockpit view), is simpler to build in a no-framework static stack and matches what's already been decided (shared core + role lanes, not partition). Full ACL only becomes worth the complexity if this becomes the sellable multi-tenant product (Phase 3) serving actual competing customers — worth revisiting at that point, not now.

## ASCII wireframe — login/role-select, then one example door (AE)

```
┌─────────────────────────────────────────────────────────────┐
│  PRISM                                    [role: AE ▾]  [⚙] │  <- role switcher, top-right, always visible
├─────────────────────────────────────────────────────────────┤
│                                                                │
│   SHARED CORE (same for every role, small framing changes)   │
│   ┌───────────────────────────────────────────────────────┐  │
│   │  Costco.com — Score 3.7/5           "framed for you:"  │  │
│   │  Killer finding: zero-results rate 8.2% on branded qs  │  │
│   └───────────────────────────────────────────────────────┘  │
│                                                                │
│   AE LANE (role-specific, everything below this line changes)│
│   ┌───────────────────────────────────────────────────────┐  │
│   │  PREP ●──○──○──○──○ SS1  SS2  SS3  SS4                │  │
│   │  (green/amber/red exit-gate per stage)                 │  │
│   │                                                          │  │
│   │  ┌─ 60-sec pre-call brief ─────────────────────────┐   │  │
│   │  │ Champion: unknown (empty slot, not fabricated)   │   │  │
│   │  │ Anxiety Q: "why now, why us vs Constructor.io"   │   │  │
│   │  │ [Open business case]  [Open playbook]            │   │  │
│   │  └───────────────────────────────────────────────────┘  │  │
│   └───────────────────────────────────────────────────────┘  │
│                                                                │
│   [ 💬 drill co-pilot — slides in on demand, not always-on ] │
└─────────────────────────────────────────────────────────────┘

Loading state: streaming step receipts (Codex-style) while an audit
is actively running — "Researching competitors... Running browser
tests... Generating business case..." — not a blank spinner.

Empty state (MEDDPICC slot unknown): shown as an explicit empty
chip, never inferred/fabricated — ties directly to the zero-
fabrication rule from the Verification Pipeline (gap #8).
```

## ASCII wireframe — BDR door

```
┌─────────────────────────────────────────────────────────────┐
│  PRISM                                   [role: BDR ▾]  [⚙] │
├─────────────────────────────────────────────────────────────┤
│   SHARED CORE                                                 │
│   ┌───────────────────────────────────────────────────────┐  │
│   │  Costco.com — Score 3.7/5           "framed for you:"  │  │
│   │  Killer finding: zero-results rate 8.2% on branded qs  │  │
│   └───────────────────────────────────────────────────────┘  │
│                                                                │
│   BDR LANE — queue, not single-account depth                  │
│   ┌───────────────────────────────────────────────────────┐  │
│   │  Prioritized queue (ranked by signal strength):        │  │
│   │  1. Costco.com    [hiring+news+social signal: HIGH]    │  │
│   │  2. Target.com    [signal: MEDIUM]                     │  │
│   │  3. Wayfair.com   [signal: MEDIUM]                     │  │
│   │                                                          │  │
│   │  ┌─ Top of queue: Costco.com ──────────────────────┐   │  │
│   │  │ Why now: 3 open search-eng roles posted last wk  │   │  │
│   │  │ [Send outreach package]  [Battle card]           │   │  │
│   │  └───────────────────────────────────────────────────┘  │  │
│   └───────────────────────────────────────────────────────┘  │
│   [ 💬 triage command — "which 5 accounts today, why" ]      │
└─────────────────────────────────────────────────────────────┘
```

## ASCII wireframe — Sales Leader door

```
┌─────────────────────────────────────────────────────────────┐
│  PRISM                                [role: Leader ▾]  [⚙] │
├─────────────────────────────────────────────────────────────┤
│   NO SHARED-CORE SINGLE-ACCOUNT HEADER — Leader is aggregate  │
│   ┌───────────────────────────────────────────────────────┐  │
│   │  Portfolio heatmap (this is the old 6-tab dashboard's  │  │
│   │  real home):                                            │  │
│   │  ▓▓▓░░ Costco    SS2   $340k opp   score 3.7           │  │
│   │  ▓▓░░░ Target    SS1   $210k opp   score 2.9           │  │
│   │  ▓▓▓▓░ Wayfair   SS3   $180k opp   score 4.1           │  │
│   │                                                          │  │
│   │  Rollup: 3 accounts stalled at SS2 (>14 days)          │  │
│   │  [Drill into any account → opens THAT account's AE view]│  │
│   └───────────────────────────────────────────────────────┘  │
│   [ 💬 rollup query — "which reps are stalled at SS2, why" ] │
└─────────────────────────────────────────────────────────────┘
```

## ASCII wireframe — Marketer door (updated with global chrome, 2026-07-05)

```
┌─────────────────────────────────────────────────────────────────┐
│  PRISM  [role: Marketer ▾]  [account: Costco.com ▾]  🎙 ◉  [⚙]│
├─────────────────────────────────────────────────────────────────┤
│   SHARED CORE                                                     │
│   ┌───────────────────────────────────────────────────────────┐  │
│   │  Costco.com — Score 3.7/5           "framed for you:"      │  │
│   │  Killer finding: zero-results rate 8.2% on branded qs  ✓   │  │
│   └───────────────────────────────────────────────────────────┘  │
│                                                                     │
│   MARKETER LANE — content angle, no deal-stage mechanics           │
│   ┌───────────────────────────────────────────────────────────┐  │
│   │  Narrative hook: "Costco loses 8% of branded searches  ✓   │  │
│   │  to zero results — direct revenue leak"                     │  │
│   │  Sourced from: traffic + industry + competitor findings     │  │
│   │                                                              │  │
│   │  [Preview landing page]  [Review before Jahia push]         │  │
│   │  [Download leave-behind]  [Download ABX assets]             │  │
│   └───────────────────────────────────────────────────────────┘  │
│   [ 💬 content co-pilot — "what's the one hook for this?" ]      │
└─────────────────────────────────────────────────────────────────┘
```

No stage pipeline here (unlike AE) — Marketer's work isn't gated to a deal stage, it's tied to whenever the audit's findings are fresh enough to be campaign-worthy.

## Open items — resolved with a recommendation, not yet Arijit-confirmed

- **Role switcher: toggle, not fixed-per-login.** Confirmed as the working assumption (matches "filter not lockdown" above) — anyone can flip roles to preview another door, no separate account-per-role needed. Simpler in a no-build static stack.
- **Marketer ↔ Jahia pipeline: PRISM's Marketer door is the review/approve surface, not a second builder.** The existing pipeline (Figma → design system → PRISM fills components with audit data → push to Jahia) stays as-is. The Marketer door's "[Preview landing page] / [Review before Jahia push]" buttons sit in front of that same pipeline — one builder, PRISM adds a review step, doesn't duplicate it.
- **Existing 5-tab report SPA (Overview/Research/Search Audit/Business Case/Sales Actions): becomes the Sales Leader's drill-through, not retired.** Leader's persona is explicitly the "wants everything, aggregated" superset — the existing SPA already IS that superset view. AE/BDR/Marketer doors deep-link INTO specific tabs contextually (e.g. AE's "[Open business case]" button opens the Business Case tab of the same SPA) instead of each role getting its own rebuilt version of that content.

All three above are working assumptions, not locked — flag if wrong before more gets built on top.

## Jarvis cockpit — the operator/run layer, added 2026-07-05

Arijit's vision: "PRISM Central OS," Iron-Man-style — voice + text, enter a domain, pick agents/skills, watch it run, chat with results. This is the recipe/cockpit system from Phase 2's manifesto text ("operator hand-picks which modules run; the selection is a recipe; the executioner runs the recipe") given a real face — closes gap #9.

**Confirmed: not operator-only, every persona gets it. Reconciled with the 4 role-doors as a persistent global element, not a 5th separate surface** — the role-tailored front doors stay (AE still opens into their pre-call brief, BDR into their queue), and the Jarvis command bar/recipe-builder is present on every door, triggered on demand, overlaying whichever door you're already in. One component, reused across all 4 doors, not rebuilt per role.

**Recipe mechanics = Agent × Skill, two-step:** pick an agent (Researcher/Auditor/Synthesizer/Chat — Gate/QA is automatic, never manually selected, it always runs), then within that agent pick specific skills to run (e.g. Researcher → company-intel + competitor-intel, cherry-picked from the 12 intel-* skills, not always the full set). Submits as a recipe, executioner runs it, live execution view streams status (Codex-style step receipts, already the decided pattern for audit-running moments), results land in Postgres automatically, chat picks up immediately after grounded in what just ran.

**Voice — CONFIRMED REAL, not just visual/animated feel.** Checked for reuse first: none exists (only a static avatar image for Cassandra's chat widget, no audio pipeline anywhere in the current system) — this is new build, not a swap-in.
- **STT (input):** browser-native `SpeechRecognition` Web API. Free, zero new backend infra, fits the existing no-build vanilla-JS/CSS stack directly. Known gap: Safari/iOS support is patchy vs. Chrome/Edge — flagged, not a blocker.
- **TTS (output):** browser-native `SpeechSynthesis` exists but sounds robotic — wrong fit for "premium, no sacrifice to look and feel." A real Jarvis voice needs a dedicated TTS vendor (ElevenLabs-class quality). **Open item, not decided:** which vendor, at what cost — this deserves its own vendor pass, same shape as the earlier Claude-vs-Google-vs-OpenAI executioner challenge, just for voice synthesis specifically. Not resolving it inline here.

### ASCII — Jarvis overlay on an existing door (AE shown, same pattern applies to all 4)

```
┌───────────────────────────────────────────────────────────────────┐
│  PRISM                          [role: AE ▾]     🎙 ◉ Jarvis  [⚙]│  <- global, present on every door
├─────────────────────────────────────────────────────────────────┤
│   (role-door content underneath, unchanged from earlier wireframe) │
├─────────────────────────────────────────────────────────────────┤
│  ▼ Jarvis expanded (voice or click-triggered overlay)              │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  🎙 listening... "run competitor intel on torrid.com"        │  │
│  │  ┌─ AGENTS ──────────┐  ┌─ RECIPE ───────────────────────┐  │  │
│  │  │ ● Researcher       │  │ ☑ company-intel                 │  │  │
│  │  │   Auditor          │  │ ☑ competitor-intel               │  │  │
│  │  │   Synthesizer       │  │ ☐ financial-public / hiring...  │  │  │
│  │  │   Chat              │  │ [ Run recipe ]                   │  │  │
│  │  └─────────────────────┘  └───────────────────────────────┘  │  │
│  │  LIVE: ● company-intel done (2.1s)  ● competitor-intel ▓▓░░  │  │
│  │  RESULTS + CHAT: [output cards]  💬 "biggest exposure vs C.io?"│ │
│  └─────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

### Open items from this pass
- **TTS vendor decision** (ElevenLabs-class) — deferred, cosmetic per Arijit 2026-07-05, own pass later.
- Per-role default recipe suggestions when Jarvis is invoked — resolved below (2026-07-05 pass).
- Mic permission / privacy UX — deferred alongside TTS, cosmetic for now.

## Company/account switcher — closed gap, 2026-07-05

Every wireframe so far showed one company (Costco.com) as if permanently active — no mechanism existed for switching context or for a freshly-run Jarvis recipe to become the active audit on a role-door. Fixed: switcher lives in the header, next to the role switcher, on every door.

```
┌───────────────────────────────────────────────────────────────────┐
│  PRISM     [role: AE ▾]   [account: Costco.com ▾]   🎙 ◉  [⚙]   │
│                            ┌──────────────────────┐               │
│                            │ 🔍 search accounts...  │               │
│                            │ Costco.com  (active)  │               │
│                            │ Target.com            │               │
│                            │ Wayfair.com           │               │
│                            │ ────────────────      │               │
│                            │ + Run new via Jarvis  │  <- ties directly
│                            └──────────────────────┘     into the cockpit
└───────────────────────────────────────────────────────────────────┘
```

When a Jarvis recipe finishes for a new domain, that domain is auto-added to the account switcher and becomes the active context — no separate "import" step. Same switcher, same list, powers the "previous audits" browsing you originally described — it's not a separate history panel, it's this dropdown.

**Per-role default recipe, resolved:** when a role invokes Jarvis without specifying skills, it defaults to that role's artifact→skill map already established (Marketer defaults to traffic/industry/competitor/investor skills, BDR to hiring/news/social, AE to the full deep set, Leader to whatever's already run — aggregate, doesn't trigger new runs by default). User can always override the default checklist manually; the default just saves a step for the common case.

## Trust/provenance visibility — the Verification Pipeline made visible, 2026-07-05

Real gap: the 5-stage Verification Pipeline (gap #8) was designed entirely backend. Nothing in any wireframe showed the user what got checked or what got stripped. Given zero-tolerance-for-fabrication is the stated business risk, invisible verification is a missed opportunity, not just an oversight — visible trust signals double as a sales asset (an AE can show a prospect "every number here passed 3 independent checks").

**Every claim/stat/quote rendered anywhere in the UI carries two things:**
1. A **citation marker** — hover/click reveals `source_url`, `captured_at`, `method` (the same provenance shape already required by the "no naked numbers" rule).
2. A **verification badge** — ✓ passed all 5 pipeline stages, or a visible **redacted chip** where a claim was stripped for insufficient verification. Redaction is shown, not hidden — "1 claim removed here (unverifiable)" is a trust signal, not a defect.

```
┌───────────────────────────────────────────────────────────────┐
│  Killer finding: zero-results rate 8.2% on branded queries  ✓  │  <- ✓ = passed all 5 stages
│  [hover: source=algolia-search-audit run 2026-07-05,           │
│   captured_at=14:22Z, method=browser-test]                     │
│                                                                  │
│  ⊘ 1 claim redacted here — competitor revenue estimate         │  <- visible, not silent
│    could not be independently verified by 2 of 3 auditors      │
└─────────────────────────────────────────────────────────────────┘
```

This one design decision touches every door (AE/BDR/Leader/Marketer) and the Jarvis results panel — it's not a separate screen, it's a rendering rule applied everywhere a `Finding`/`Evidence` gets shown.

### Open items from this pass
- Exact badge visual language (icon set, color, whether redaction chips are collapsible/expandable) — not designed, needs actual visual craft pass once IA is locked.
- Whether Leader's aggregate/portfolio view shows per-account verification-badge rollup (e.g. "3 accounts have 0 redactions, 1 has 2") — not yet decided, plausible and cheap given the data already exists per-claim.

## AE door corrected: stage-aware collateral, not static buttons — 2026-07-05

Real research already answers this (`docs/workspace/ae-journey-research/05-algolia-ae-sales-process.md`, sourced from the actual FY27 Field Guide, Tier-1) and `01-internal-audit-deliverables.md` — pulled from there, not invented. Original mapping covered all 5 stages; **scope locked down 2026-07-05 to PREP+SS1+SS2 only** — Arijit's call: SS3 (POC/Go-Live) and SS4 (Scoping & Proposal) are execution/negotiation territory where "neither of us has a role" — PRISM doesn't prep collateral for those, full stop.

| Stage | Primary focus | Collateral surfaced |
|---|---|---|
| PREP | Score + critical-gap count, Playbook BLUF | 60-sec brief |
| SS1 (intro, no slides) | Green/yellow/red qualification | 60-sec brief + Battle Card C.io check |
| SS2 (deep discovery) | Vision-to-Value, Anxiety Statement, ROI justification | **AE Playbook** (MEDDPICC Gap Map, SPIN discovery, talking points) + **Business Case/ROI model** |

**Corrected 2026-07-05 (Arijit):** original research mapped Business Case/ROI to SS4 — wrong. SS4 is closing/legal/procurement; the business case has to already exist in full, excruciating detail well before the deal reaches the negotiation table, or the deal never gets there. ROI/business-case work belongs in SS2, built alongside the Playbook off the same discovery conversation — not deferred to a stage that's now out of scope anyway.

**Dropped from scope: SS3, SS4.** Battle Card's Golden Angle/differentiator content (originally SS3) stays out — that was pitch/demo material for the now-out-of-scope stage.

**Not stage-locked, still relevant within PREP-SS2:** Strategic Signal Brief (spine), Leave-Behind (usable after any meeting), ABX Campaign (outreach can start early).

**Correction this forces:** the AE door's collateral buttons are NOT static — they change based on which of the 3 in-scope stages is currently selected.

```
┌─────────────────────────────────────────────────────────────┐
│   PREP ○──●──○  SS1  SS2         <- only 3 stages, not 5     │
│         (currently viewing: SS2 Deep Discovery)               │
│   ┌─ SS2 exit gate: Vision-to-Value delivered? ─────────┐    │
│   │  ☐ eval path confirmed   ☐ PIE buy-in secured        │    │
│   └─────────────────────────────────────────────────────┘    │
│   ┌─ Stage-relevant collateral (changes per stage) ──────┐    │
│   │  [Open AE Playbook — MEDDPICC + SPIN discovery]      │    │
│   │  [Open Business Case — ROI model, fill-in-the-blank] │    │
│   │  (PREP/SS1 would show: [60-sec brief] [Battle Card]) │    │
│   └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## ABM Brief artifact — Marketer's real hero artifact, 2026-07-06

Grounded in a real whale-account playbook already in the repo (`docs/example-and-context/Belk Whale1_1 Pipeline Acceleration Marketing Playbook v2.md` — an actual human-built ABM doc, not a template). Arijit confirmed this table + reasoning as exactly right (2026-07-06) — treat this split as a **general design principle for every PRISM deliverable, not just the ABM Brief**: never let an artifact guess at content that only exists in a human's head, a sales conversation, or a CRM — auto-generate only what the audit can actually verify, and show an explicit, honest empty slot for the rest. This is the same rule the Verification Pipeline (gap #8) already enforces for individual claims, now applied at the artifact-design level.

| Section | Can PRISM auto-generate this from an audit? |
|---|---|
| Account Overview (revenue, employees, industry, competitive intel) | **Yes** — already covered by existing skills (company/financial/competitors) |
| Business Goals / Pain Points | **Yes** — synthesizable from company-intel + industry + investor quotes, same pattern as AE's Vision-to-Value |
| Event engagement | **No** — real gap, no existing skill catches this at all |
| Key Players (named individuals, who-directs-to-whom internally) | **No** — this level of detail comes from actual sales conversations, not public research. PRISM can surface named execs from earnings calls/LinkedIn, but not internal reporting relationships |
| Decision-Making Process / Decision Criteria / Pricing / Open Opportunity $ | **No, and shouldn't try** — this is CRM/Salesforce data. The doc's own label ("Sales Input") admits this is manually provided, not automated |
| Phase 1/2/Events tactics tables | **Not per-company** — this is a **static, reusable tactic menu** (same options for any whale account), not something regenerated per audit. PRISM's real job here is recommending *which* tactics fit *this* company's profile, not writing the tactic descriptions fresh each time |

**Design consequence:** the ABM Brief has two visually distinct zones — an **auto-filled zone** (Account Overview, Business Goals/Pain Points, recommended tactics from the fixed menu) and a **Sales-input zone** with explicit empty slots (Key Players, Decision Process/Criteria/Pricing, Open Opportunity), styled the same as AE's "empty MEDDPICC slot, not fabricated" pattern. The tactics menu itself (Phase 1 digital/paid media, Phase 2 custom creative, Events) is stored once as PRISM reference data, not regenerated — the audit only decides which entries to recommend.

**Open items:** CRM/Salesforce integration (does PRISM ever pull deal-stage/$ value automatically, or does Sales always paste it in manually?) — not decided, real scope question. Event-engagement signal — confirmed gap, no skill covers it yet, would need a new intel module if this is worth building.

## Marketer — data-source stub modules, 2026-07-06

Arijit's ask: show marketing execs which extra data sources would add value if available, what function each unlocks, and what specific data it needs — Salesforce explicitly excluded from consideration (not deprioritized, dropped).

**Gong (call/meeting recordings + transcripts):**
- Function: "Verbatim Objection & Signal Miner" — extracts real spoken language from actual meetings: objections raised, competitor names the prospect brought up themselves, budget/timeline hints, urgency signals.
- Data needed: Gong call transcripts for the account.
- Value: sharpens Business Goals/Pain Points beyond public-signal inference, AND partially closes the "Key Players" gap from the ABM Brief split (meeting attendee names + what they personally raised — real/derivable; their internal reporting structure still isn't, stays a gap).

**Account-history doc (informal notes — "who do we know, what's already happened"):**
- Function: "Account Memory" — ingested before a fresh audit runs, surfaces prior deals (won/lost), past contacts, messaging already tried, as a pre-existing-context panel.
- Data needed: whatever informal notes a rep already has — no new system required.
- Value: continuity (don't re-pitch a failed angle), partially informs Decision-Making Process without any CRM integration.

**Salesforce/CRM: explicitly dropped, not a stub candidate.** Per direct instruction.

### UI — active vs. locked data sources, visible to the exec reviewing the view

```
┌───────────────────────────────────────────────────────────────────┐
│  DATA SOURCES POWERING THIS VIEW                                     │
│  ✅ ACTIVE                          🔒 WOULD ADD VALUE IF AVAILABLE  │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐  │
│  │ Company/financial/competitor │  │ 🔒 Gong call recordings       │  │
│  │ Traffic, news, social, hiring│  │   → real objections + who     │  │
│  │ Techstack, industry, partner │  │     said what in the room     │  │
│  └─────────────────────────────┘  │ 🔒 Account history doc         │  │
│                                     │   → don't repeat a failed pitch│  │
│                                     │ 🔒 Event engagement feed       │  │
│                                     │   → conference/booth touches   │  │
│                                     └─────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

Every locked card names: the function it unlocks, the exact data required, and the specific marketing gain — not a vague "more data would help." Reusable pattern: same stub-card mechanism likely applies to AE/BDR doors too (different data sources, same "active vs locked, name the function" structure) — not yet extended there, flag if wanted.
