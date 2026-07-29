# PRISM IA — A/B Prototype Design Spec

**Date:** 2026-06-30
**Status:** Approved design — ready for implementation plan
**Surface:** Live prism-hub published-reports site (static, autodeployed to prism.chowmes.com)
**Owner:** Arijit
**Origin:** Brainstorm of three initiatives (downloadable deliverables, Discovery-OS incorporation, IA overwhelm). This spec covers the IA initiative only. The other two are tracked separately (see "Relationship to the other two initiatives").

---

## 1. Problem

The live audit report presents **~42 top-level information surfaces (72 counting finding sub-tabs)** as a flat, equally-weighted library across 5 topic tabs. Every user — a BDR who wants one email hook, an AE prepping a 90-minute discovery call, a prospect sent the link — lands on identical content with no role scoping, no "start here," and no recommended path. The most time-efficient artifacts (AE pre-call brief, leave-behind, battle card) are **orphaned** (zero inbound links). The "Downloads ▾" toolbar button is a **dead shell** (reads `ae_fields.downloads[]`, never populated).

**Root cause (named):** category error. The product ships a *reference library* (here is everything, go find what you need) when the job is a *workflow tool* (give me the right thing for this deal at this moment). Reorganizing the library is not the fix; changing what the default surface *is* and how depth is accessed is the fix.

## 2. The unresolved fork → resolved by testing, not by us

Two viable answers to "how should depth be accessed":

- **Browse-primary** — the page shows a structured map; user navigates by clicking. Lower effort to act (recognition), but must render many options → fights the overwhelm directly.
- **Conversation-first** — the page asks what you need; user navigates by asking (recall). Zero visual overwhelm, but carries cold-start and capability-discovery risk (mitigated by seeded prompt chips + a browse-all escape hatch).

These are not opposites; they are a slider on *how much structure is visible by default*. We do not have enough signal to pick. **Decision: build both as isolated prototypes, instrument them, let real users decide.**

## 3. Scope & isolation

**Isolation (hard requirement):** production must be untouched.
- New top-level dirs in prism-hub: `/ia1/` (browse-centric) and `/ia2/` (chat-centric). Optional `/ia/` compare landing linking both.
- Production `/reports/` and every existing `/{slug}/` page remain byte-for-byte unchanged.
- New renderer/templates only. The existing `render-audit.ts` (which feeds production) is **not edited**. New code lives in a new renderer (e.g. `render-ia.ts`) or hand-built prototype templates.

**Data:** the `homedepot-mexico` audit data JSON, frozen. Both shells read the same file. We change the *experience*, never the *content*.

**Audiences:** each shell contains two modes via a toggle:
- **Seller cockpit** — the primary thing testers compare. Holds the 6-job carve.
- **Prospect view** — linear narrative, curated safe subset. Public-shareable. Not the jobs.

**Out of scope for this prototype:**
- Fixing the deliverable render gaps (markdown-only business case / signal brief / playbook / ABX → real downloadable files). Captured as a punch-list feeding the Exports surface; built separately.
- Discovery-OS incorporation (separate initiative).
- Rolling the new IA across all 10 audits. Prototype is `homedepot-mexico` only; graduation to other audits is a renderer swap, post-decision.
- Calendar/CRM auto-ready entry and live deal-stage awareness (belongs to the future cockpit *app*, not a static report).

## 4. A/B validity guardrail

The two prototypes must differ on **only the access axis** (browse rail vs. ask box). They share, identically:
- the frozen `homedepot-mexico` data,
- the 6-job carve and content-to-job mapping,
- the 60-second brief,
- the visual language / design tokens (reuse existing prism-hub skin).

If IA2 is also prettier, or has different content, testers will "prefer" it for the wrong reason and the result is invalid. **One variable.**

## 5. Shared core (build once)

### 5.1 The 60-second brief (default orientation layer, both shells)
One screen, no scroll. Every element is a live pointer into a job. Tier-1 content (per AE-journey doc):
- **Who + one-liner** — company, vertical, public/private.
- **Search verdict** — score /10 + verdict badge + the *one damning finding* (the pain hypothesis).
- **Incumbent** — current search vendor (none / Algolia / competitor) — sets the motion.
- **Why now** — the trigger signal (~90 days): news / exec quote / hiring surge. (Top slice; full set lives in *Make the money case*.)
- **Say this first** — opener tied to the trigger + 2-3 discovery questions. (Top slice; full set lives in *Run the conversation*.)

The brief carrying the top slice of why-now and discovery-Qs is **progressive disclosure, not duplication**: brief = the few you need now, job = the complete set.

### 5.2 Seller job carve (locked — 6 jobs, intent verbs)

Labels are *intent verbs* (what the seller is trying to do), not content topics — intent labels guide a confused user where topic labels ("Research", "Business Case") do not.

| Job | Holds | Source modules |
|---|---|---|
| **Know the account** | company, execs, financials, tech stack, traffic, hiring, social, news, partner, industry, competitive matrix | intel-company, -financial, -techstack, -traffic, -hiring, -social, -news, -partner, -industry, -competitors |
| **Prove it's broken** | 10-area score + heatmap, finding chapters (summary/deep-dive/evidence screenshots), test queries | audit-report, audit-browser, intel-queries |
| **Make the money case** | Said-vs-Found, ROI calculator, customer proof, why-now (full) | synth-business-case, intel-investor, intel-news/-hiring/-social (why-now) |
| **Know who decides** | MEDDPICC, power map / buying committee, champion signals | synth-sales-plays, intel-hiring, intel-social |
| **Run the conversation** | discovery questions (full), objection handling, battle card, talk track / pre-call cheat sheet | synth-sales-plays, intel-competitors |
| **Reach out** | ABX emails, LinkedIn per contact, Loom script, collateral schedule | campaign-abx |

**Exports is not a job.** It is a cross-cutting action: a download affordance on every artifact card, plus a small downloads tray. (In IA2 you also export by asking — "give me the leave-behind.") This is where the deliverable punch-list surfaces once those renders exist.

The split of the old overloaded "Win the deal" into **Know who decides** (qualification / the people) and **Run the conversation** (call execution / the words) balances bucket weight and matches the AE's actual two-step ("who's the buyer?" then "what do I say?").

### 5.3 Prospect view (shared, both shells)
Not the 6 jobs. A linear persuasion narrative pulling a curated, prospect-safe subset:
**Pain → Evidence (audit findings + screenshots) → Value (ROI + Said-vs-Found) → Proof (customer case studies) → one CTA.**
Internal-only surfaces (MEDDPICC, power map, battle card, objection handling, ABX, discovery Qs) are **excluded** from prospect view. Leave-behind PDF is its natural download.

### 5.4 Visual language
Reuse existing prism-hub design tokens and component styling. Both shells look native and identical; only the interaction paradigm differs.

## 6. The two shells

### 6.1 IA1 — browse-centric
- **Default:** the 60-second brief.
- **Spine:** a **jobs rail always visible** (the 6 jobs). Click a job → that panel renders; progressive disclosure inside (collapsed modules, highest-signal first).
- **Chat:** present but secondary — the existing "Ask about this audit" helper in the corner (today's chat-widget.js behavior).
- **Mode toggle:** Seller ⇄ Prospect.
- **Exports:** download button on each artifact + a downloads tray.

### 6.2 IA2 — chat-centric
- **Default:** the 60-second brief + an **ask box as the hero**.
- **Spine:** conversation. **Seeded prompt chips** (e.g. "battle card vs incumbent", "ROI at +2% conversion", "who's on the call", "what do I send after the call") solve cold-start and capability discovery.
- **Chat depth (decided):** **text answers + "open full" deep-links.** Reuse the existing grounded Cassandra chat (chat-widget.js + /api/chat). Answers return as grounded text with chips; "open full" opens the matching job panel — the *same* panels IA1 renders. No rich inline artifact-card rendering in this prototype (that is phase 2 if chat wins).
- **Browse-all drawer:** the 6-job rail collapsed into a drawer — the escape hatch for browse-people and for deep reading.
- **Mode toggle:** Seller ⇄ Prospect.
- **Exports:** by asking ("give me X") + download button on opened panels.

## 7. Feedback capture (decided: in-prototype widget)

A small feedback widget embedded in **both** shells, capturing reactions *in context* as testers use them. Minimum captured:
- a quick reaction (e.g. "this was easy / confusing to find what I needed"),
- free-text "what was missing / confusing",
- a head-to-head preference prompt (since the goal is comparison): "which approach do you prefer, and why" — surfaced after the tester has seen both (e.g. on the `/ia` compare landing or on second-shell visit).

Storage: lightweight POST to an endpoint (or a simple append store) keyed by shell (ia1/ia2), so results are attributable per approach. Exact backend pinned in the implementation plan.

## 8. How we decide the winner

The test yields a recommendation, not an auto-decision:
- **Preference split** across testers (which shell they'd choose).
- **Qualitative "why"** themes (cold-start pain? overwhelm? trust of chat?).
- **Task success signal** if instrumented (could a tester find the battle card / ROI / who's-on-the-call quickly in each).

Winner graduates: its renderer extends to all audits and (optionally) replaces `/reports/`. Loser is archived. A hybrid outcome (e.g. browse default + strong ask box) is an allowed conclusion.

## 9. Relationship to the other two initiatives

- **Deliverables (#1):** largely *absorbed* here — the dead Downloads button dies, exports become native (ask / per-card). The remaining real work is render-pipeline gaps (markdown-only deliverables → downloadable files); that is a separate build feeding the Exports surface.
- **Discovery-OS (#2):** independent content-engine upgrade to `synth_sales_plays` (replace SPIN output with the Exchange paradigm / calibrated-hypothesis call plan). Surfaces inside the *Run the conversation* and *Know who decides* jobs once built. Does not block this prototype.

## 10. Build order (high level — detailed plan via writing-plans)

1. **Shared core:** frozen `homedepot-mexico` data load + the 6-job content model + the 60-second brief component + reuse design tokens.
2. **IA1 shell:** brief + jobs rail + panels + helper chat + mode toggle + exports affordance.
3. **IA2 shell:** brief + ask box hero + seeded chips + wire existing Cassandra + "open full" deep-links into shared panels + browse-all drawer + mode toggle.
4. **Prospect view:** shared narrative subset, rendered in both shells under the toggle.
5. **Feedback widget** in both shells + `/ia` compare landing + capture endpoint.
6. **Isolated deploy** to `/ia1/`, `/ia2/`, `/ia/`; verify production paths unaffected; live-verify both shells render homedepot-mexico correctly.

## 11. Success criteria (prototype)

- Production `/reports/` and `/{slug}/` provably unchanged (byte diff / live check).
- Both shells render the full `homedepot-mexico` audit under both modes.
- A tester can complete the comparison and the widget records an attributable preference.
- The two shells differ *only* on the access axis (content/jobs/brief/skin identical).
