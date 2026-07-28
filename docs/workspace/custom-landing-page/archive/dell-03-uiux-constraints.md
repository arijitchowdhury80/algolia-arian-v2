# UIUX Constraints — Dell Marketer Landing Page

Source: vault `Standards/UIUXDesignSOP/index.md` + `algolia.md`.

## Emphasis Tiers (Step 2 cross-check)
- Hero: 1 max per section — the $3.2B ROI headline only. Do not also hero the vertical tag or company name in the same visual weight.
- Primary: 2-3 max — 3 proof-stat cards is at the ceiling, do not add a 4th.
- Secondary/Supporting: no limit, but Step 4 budget caps findings sections at ~4.

## Component Constraints
- Hero ROI number → Bounce Card. Dollar amounts: use Dell's real audit figure ($3.2B), cite it's from PRISM's own audit, never round/embellish beyond what's in `T` data.
- Cards: `1px solid var(--color-border)`, `border-radius: var(--radius)` (8px), subtle shadow `0 2px 8px rgba(35,38,59,0.10)`.
- Dark hero section: exact gradient `linear-gradient(135deg, #0D1240 0%, #21243D 45%, #001A8A 100%)`.

## Responsive Breakpoints (mandatory test)
375px / 768px / 1024px / 1280px. Alternating image+copy sections must stack to single column below 768px — this is the highest-risk layout (4 instances on the page).

## Accessibility (WCAG 2.2 AA)
- Contrast: white text on the navy gradient hero must hit 4.5:1 — verify with `--color-white` (#FFFFFF) on `#0D1240`/`#21243D` (both pass by default, confirm post-build).
- Every CTA button has an accessible label (not just an icon).
- Touch targets ≥44px on mobile CTA buttons.
- Color never the sole indicator — the golden-angle callout can't rely on color alone to signal "advantage."

## Brand Rules (from algolia.md — hard constraints)
- Font: Sora only. Never Inter/Roboto/DM Sans/Arial/system/serif.
- Sentence case headings, not Title Case. AP style, Oxford comma.
- **Approved Algolia stats are locked** (17,000+ customers / 1.7T searches/year / 30B records) — only if Algolia's own stats appear anywhere on this page (likely not needed here, page is about Dell's numbers, not Algolia's).
- **Never name competitors** (Elasticsearch, Typesense, Meilisearch, Coveo, Bloomreach, Lucidworks) in customer-facing copy. ACTION: must check Dell's tech-stack audit data for their current search vendor before writing findings copy — if it's a listed competitor, refer to it generically ("your current search experience"), never by name.
- Product names capitalized correctly if mentioned (Algolia Search, Algolia AI Search, etc.)

## Conflicts flagged before coding
None — the pre-existing `brand: algolia` theme (Step 7/02-aesthetic.md) already satisfies all of the above; no tension with Steps 1-6 decisions.
