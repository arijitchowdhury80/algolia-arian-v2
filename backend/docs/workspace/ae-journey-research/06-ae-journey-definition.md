# PRISM AE Journey — Definition (synthesis of all research + FY27 Field Guide)

Synthesizes: 01 internal deliverables · 02 competitor UX · 03 discovery methodology · 04 AE workflow · 05 FY27 AE Field Guide (primary). Honors locked decisions: PRISM = AI Sales Toolkit; AE surface = full stage cockpit; calm Claude-desktop language; conversation-as-hero + artifact slide-in.

---

## The shape: a deal-centric, conversation-led STAGE COCKPIT

Not a dashboard. Not a single brief. A cockpit that always knows **which deal, which stage, which gate** — and adapts.

```
┌────────────────────────────────────────────────────────────────────────┐
│  Nike  ·  ●━━━●━━━○━━━○━━━○   SS1 Introduction · gate 4/6 clear  ⚠     │  ← deal header: stage + gate health
├──────────┬───────────────────────────────────────────┬─────────────────┤
│ DEALS    │   CONVERSATION (hero)                       │  ARTIFACT PANEL │
│ (quiet,  │                                             │  (hidden until  │
│ collapse)│   aRRIe auto-posts the STAGE BRIEF on entry │   summoned;     │
│          │   ↓                                         │   slides in,    │
│ ● Nike   │   [ 60-sec brief card — see below ]         │   dismissible)  │
│   SS1 ⚠  │                                             │                 │
│ ● Dell   │   AE asks / drills. Cards render inline.    │  Full report /  │
│   SS3 ✓  │   Audit running = Codex-style step stream.  │  ROI / Pitch /  │
│ ● Gap    │                                             │  PIE / Playbook │
│   PREP   │   [ ask aRRIe… ]                            │  + GATE checklist│
└──────────┴───────────────────────────────────────────┴─────────────────┘
   ~16%               flex (hero)                          0 → ~38% on demand
```

- **Conversation stays hero** (Claude-desktop). The stage brief is posted *into* the conversation as cards, not a separate dashboard.
- **Stage + gate live in the header** — the backbone, always visible, never a tab to hunt for.
- **Artifact panel** = the deep objects (full report, ROI model, competitive pitch, PIE, playbook) slide in on demand, dismissible (Claude Artifacts / Codex pattern). Gate checklist also opens here.

---

## Entry model: AUTO-READY (research-backed)

PRISM watches the AE's calendar/CRM. When a meeting with a prospect is set, PRISM **pre-generates the stage-appropriate brief** and nudges once (~30 min before, Slack/calendar). Brief is ready before the AE asks. Summon ("audit nike.com" / pick from deal list) = secondary on-ramp. *(Stream 2 + 4: proactive briefs get 3–5× usage; summon-only briefs get skipped.)*

---

## The PREP/SS1 brief — 3-tier, evidence-first, Algolia-native

Built on Gong's proven 3-tier hierarchy (stream 2), filled with Algolia-specific content (field guide), every claim carrying a provenance badge (PRISM moat — the field ships briefs uncited).

**TIER 1 — the 60-second narrative (what the AE reads before the call):**
1. **WHO + STAGE** — company one-liner, vertical, public/private · current deal stage.
2. **SEARCH VERDICT** — audit score /10 + the *one damning finding* (the pain hypothesis). "The score IS the sentence" (Pocus).
3. **INCUMBENT (Algospy)** — Algolia? **C.io (Constructor.io)?** other? none? → this sets the entire motion. *Assume C.io in-deal for ICP-sized prospects.*
4. **WHY NOW** — the trigger signal (~90 days): news / exec quote / hiring surge.
5. **SAY THIS FIRST** — the SS1 framing script (*"Algolia works best when tech + business teams work together…"*) + an opener tied to the trigger + 2–3 SPIN discovery questions (Problem/Implication-weighted).

**TIER 2 — one click deep:**
- **People on the call** — role, tenure, MEDDPICC candidate tag (Champion? Economic Buyer?). One-click contact timeline.
- **Customer proofs** — 2–3 relevant live implementations (Implementation Explorer + Slackbot intel).
- **Metrics that matter** — conversion-from-search gap, zero-results rate, AOV/visitor, bounce — each with citable anchor, framed Before/After.

**TIER 3 — evidence:** every number → its source + retrieval date. The provenance layer.

**Honesty rule (stream 3):** unknowable MEDDPICC fields (Decision Criteria, Process, Paper) = explicit empty capture slots, never fabricated.

---

## Stage-by-stage: what PRISM does at each gate

| Stage | PRISM surface | Exit gate it tracks (green/amber/red) | Drill artifacts |
|---|---|---|---|
| **PREP** | Auto-generates the brief on calendar trigger; assembles audit + Algospy + customer proofs + C.io brief + Value Prompter "What We Heard" | Tools run · research complete · goals defined | Full audit report |
| **SS1** Intro (30m, no slides) | Brief = call companion. Green/Yellow/Red flag tracker. Live Value Prompter capture | Both Biz+Tech POC confirmed · quantifiable pain shared · next step scheduled | Audit evidence, customer proofs |
| **SS2** Deep Discovery (60m) | 25/25/5 agenda timer · SPIN question tree · Value Prompter completion → builds **Vision-to-Value** + **Anxiety Statement** | V2V delivered · eval path confirmed · org map complete · PIE buy-in | Discovery Guides, V2V, Anxiety Statement |
| **SS3** Custom Demo (90m) | **Competitive Pitch builder** (Anxiety → 3–5 Differentiators → Customer Examples) · PIE · Impl Plan | Roles defined · integration complexity surfaced · impl review complete | Competitive Pitch deck, PIE, Impl Plan |
| **SS4** Scoping & Proposal | **ROI model** + **C.io counter-narrative table** (know cold) + proposal (tailored, not placeholder) | ROI confirmed · proposal delivered · terms anchored to impact | ROI model, C.io rebuttals, proposal |

---

## Tool absorption map (PRISM = the AI Sales Toolkit)

| Field-guide tool | PRISM component | Status |
|---|---|---|
| AI Sales Toolkit (search audit) | Audit engine + scoring | **Have** |
| Algospy (Algolia/C.io beacon) | detect-search | **Have** |
| C.io competitive brief | Competitor module + counter-narrative table | Have + build |
| Implementation Explorer + Slackbot | Customer-impl matching index | Build |
| Value Prompter ("What We Heard") | Structured capture in cockpit | Build — **needs internal schema** |
| MegGPT (merch context) | ? | **Needs clarification** |
| PIE Playbook | SS3 PIE builder | Build — **needs internal** |

---

## Build sequencing (full architecture, incremental fill)

Build the whole stage-cockpit shell day one; fill stage by stage:
1. **PREP/SS1 first** — PRISM's existing modules map ~1:1 (audit, Algospy/C.io detection, competitor brief, customer proofs, financial/news/social). This is the shippable wow.
2. **SS2** — Value Prompter capture → Vision-to-Value → Anxiety Statement (needs internal Value Prompter schema).
3. **SS3** — Competitive Pitch builder + PIE (needs internal PIE Playbook).
4. **SS4** — ROI model + C.io counter-narrative + proposal.

**Prerequisite for any live data:** rewire frontend tool calls to the v2 backend module contracts.

---

## Open questions (logged)
- Value Prompter: what does it capture/output? (blocks SS2 absorption)
- MegGPT: what is it, what does it return? (blocks merch-context absorption)
- PIE Playbook internals (blocks SS3 absorption)
- Calendar/CRM integration scope for auto-ready entry (SFDC? Google Calendar?)
- Primary AE interviews still the missing Tier-1 confirm for the workflow assumptions.
