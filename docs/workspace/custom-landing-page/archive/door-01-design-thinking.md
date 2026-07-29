# Marketer Door — design thinking (terse, IA already decided)

**Mental model:** "Report" — narrative flow with evidence, not a dashboard. The marketer opens this to
understand ONE campaign angle for ONE account, backed by cited findings, then acts (preview/download/review).

**Tiers:**
- Hero: the narrative hook (one sentence, the single most important thing on the page).
- Primary: shared-core score/killer-finding strip, action buttons (preview/review/download x2).
- Secondary: data-source stub cards (active vs locked).
- Supporting: citation markers, verification badges, methodology footer.

**3 most common actions:** (1) read the hook, (2) open/preview the landing page or leave-behind,
(3) scan which data sources are active vs locked. All 1 click, no dead ends — buttons link to real
existing pages (`~/prism/marketer/dell.html` if it's the account, `reports/<slug>/` otherwise) or are
visibly disabled/labeled "not yet built" rather than fake-linking anywhere.

**Cognitive load:** 4 chunks (shared-core strip, hook card, action row, stub-cards grid) — under the
5-chunk budget, no accordion/tab split needed.

**Emotional journey:** confidence (real, cited data) → clarity (one hook, not a data dump) → agency
(clear next action + visible "here's what more you could unlock").

**Pre-mortem tigers:** generic-AI look (mitigated: reuse dell.html's real shipped tokens, not a fresh
palette) · fabricated-sounding hook (mitigated: hook text must trace to a specific findings/traffic
field, cited inline) · mobile breakage (mitigated: single-column stack under 768px, checked in browser).

**Aesthetic decision:** NOT invoking a generic theme skill (theme-dashboard/enterprise/clean/professional).
PRISM already has a real, shipped, production design system in `~/prism/marketer/dell.html` (Sora font,
`--color-primary:#003DFF`, 44px buttons, `--radius`/`--shadow` tokens) — reusing those tokens directly is
the correct "reuse before building new" call, not a shortcut around Step 7.
