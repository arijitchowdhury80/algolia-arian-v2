# Design Thinking — Dell Marketer Landing Page

## Context
First build of PRISM's Marketer-role deliverable (role-driven IA, approved 2026-07-01). A personalized landing page for one prospect (Dell), styled like Algolia's own prospect-marketing pages (real example: Ralph Lauren PDF), but auto-filled from PRISM's live Dell audit (`~/prism/reports/dell/index.html`, embedded `T` data object) instead of hand-built in Jahia.

## Step 1: Mental Model
**"Landing page" / sales one-pager**, not a dashboard and not a report. The user (a marketer or the prospect's exec reading it) expects: one scroll, narrative pitch, big claim up top, proof in the middle, ask at the bottom. Confusion risk: if it looks like the audit report (tables, scores, tabs) it breaks the metaphor — this must read as marketing copy, not analytics.

## Step 2: Information Architecture (emphasis tiers)
- **Hero (1):** the $3.2B ROI opportunity headline, tied to Dell's name + vertical ("Technology Hardware + B2B/B2C Ecommerce").
- **Primary (2-3):** 3 proof-stat cards (real Dell audit numbers, not generic Algolia customer logos — this is PRISM's actual edge over Algolia's own template); 1 golden-angle competitive callout (Dell audit has a `golden_angle` block).
- **Secondary:** 3-4 feature/finding sections (alternating image+copy, company name injected — mirrors the 6-slot pattern seen in the real Ralph Lauren render) drawn from Dell's top audit findings.
- **Supporting:** footer link block, legal, sales-rep CTA (stubbed — no real rep assigned yet, flagged not fabricated).

Tier inflation risk: audit has dozens of findings — must cut to the 3-4 highest-signal ones, not dump the whole report.

## Step 3: Interaction Flow
Top 3 actions: (1) read the ROI headline, (2) scan proof stats, (3) click primary CTA ("Talk to your rep" / "See full audit"). Happy path: hero → proof stats → findings → CTA. No dead ends: every CTA either links to the live Dell audit report or is a stubbed mailto/contact placeholder, never a broken link.
- Empty state: N/A (single company, data pre-baked at build time).
- Loading state: N/A (static HTML, no client fetch).
- Error state: if a stat field is missing from Dell's `T` data, render nothing for that slot — never fabricate a number (memory: `feedback-no-credit-no-fabrication`).

## Step 4: Cognitive Load Budget
Chunks visible per scroll-stop: hero (1), proof-stat row (1, treated as one chunk of 3 cards), each finding section (1 each × ~4), CTA band (1), footer (1) = ~8 chunks total across the whole scroll, but only 1-2 visible in viewport at once (standard landing-page pattern, not a dashboard) — acceptable, no reduction needed since it's sequential scroll not simultaneous display.

## Step 5: Emotional Journey
Curiosity (headline ROI number) → validation (proof stats are Dell's own real audit findings, not generic) → conviction (findings sections show *why*) → urgency/action (CTA). Stat cards + golden-angle callout carry the emotional weight — they're the "this is about YOU, not a template" moment.

## Step 6: Design Pre-Mortem

**Tigers:**
- Generic AI look → mitigated by using PRISM's own established tokens (Sora, #003DFF, #21243D) already proven on the live site, not a fresh palette.
- Info overload → capped at 3 proof stats + 4 findings max (Step 4).
- Key CTA ambiguous → single primary CTA color (`--blue`), repeated hero + footer, no competing buttons.
- Breaks on 375px → alternating image/copy sections must stack single-column below 768px; test explicitly (Step 10).
- Contrast → dark sections (`--navy-900`/`#21243D`) need white text at AA (4.5:1) — verify at build time.
- Dark mode → N/A, this is a public marketing artifact matching Algolia's own site (light theme only, same as their real page). Documented exception, not an oversight.

**Elephants:**
- No real user has seen this yet — flag to Arijit as review-needed before it's called "done," not just validator-passed.
- Sales-rep block: real gap, not fabricated — must render as an honest stub (e.g., generic "Talk to your Algolia rep" mailto, no fake name), matching `feedback-no-credit-no-fabrication` memory.
