---
title: Custom Landing Page — Design System
status: active
created: 2026-07-15
---

# Custom Landing Page Design System

Source of truth for the "Marketer persona" custom landing page system. Read this before adding a
section variant, changing a token, or building the intake wizard's section picker — it is what
the wizard's Step 1 (section selection) and Step 4a implementation read from. If a variant moves
from "defer" to "ship," edit this table, not code comments.

Derived from two references, both archived in this workspace:
- `reference-ralph-lauren.pdf` (+ page renders in `pdf-pages/`) — a real, fully-assembled Algolia/Jahia
  landing page for Ralph Lauren. This is the "what a finished page looks like" exemplar.
- Figma file `5DkPHASwX5HwFgG0WFEDhS` ("Landing Page options") (+ renders in `figma-refs/`) — Algolia's
  own modular section-library: named, swappable hero/body/footer variants with background-color rules.
  This is the "what pieces exist and how they combine" catalog.

Both point at the same underlying system: one component library, assembled per-prospect.

---

## Brand Tokens

Canonical source: vault `Standards/UIUXDesignSOP/algolia.md` (`brand: algolia` theme). Restated here
so this workspace is self-contained — if the two ever disagree, the vault file wins; update this copy.

**These are defaults, not a hard lock.** The intake wizard has an optional "Brand override" panel
(primary color, accent color, font family, logo) for campaigns that need a different look. Leaving it
untouched renders with the tokens below exactly as-is. See `landing.json`'s `theme{}` key (plan Step 2).

```css
:root {
  /* Brand colors */
  --color-primary:    #003DFF;   /* Nebula Blue — primary CTA, links */
  --color-accent:     #5468FF;   /* Accent Purple */
  --color-text:       #23263B;   /* Space Gray — headings, body */
  --color-muted:      #6B7280;
  --color-bg:         #F5F5F7;
  --color-border:     #E5E7EB;
  --color-white:      #FFFFFF;
  --topbar-bg:        #23263B;

  /* Typography */
  --font-family:    'Sora', sans-serif;   /* Never: Inter, Roboto, DM Sans, Arial, system fonts, serif */
  --font-h1: 56px; --font-h2: 36px; --font-h3: 28px; --font-h4: 22px; --font-h5: 18px; --font-body: 16px;
  --weight-light: 300; --weight-regular: 400; --weight-semibold: 600;

  /* Layout */
  --radius: 8px;
  --shadow: 0 2px 8px rgba(35, 38, 59, 0.10);
}

.hero-section {
  background: linear-gradient(135deg, #0D1240 0%, #21243D 45%, #001A8A 100%);
  color: var(--color-white);
}
```

**Buttons**: pill-shaped. Primary = filled `--color-primary`. Secondary = white/outline. Never more
than one visually-competing primary CTA per screen (repeat the same primary color in hero + footer,
don't introduce a second color for "importance").

**Voice**: confident, clear, technically credible, never arrogant. Sentence case headings. Only use
Algolia's approved stats verbatim (17,000+ customers, 1.7 trillion searches/year, 30 billion records
indexed) — no rounding, no embellishment. Never name competitors in prospect-facing material.

**No-fabrication rule** (`feedback-no-credit-no-fabrication`): any section whose backing data (PRISM
audit field, manual input) is absent must be omitted entirely — never rendered with a placeholder
number, a fake rep name, or invented copy.

---

## Section Inventory

The curated set this spike ships, plus what's deferred. Figma node IDs (file `5DkPHASwX5HwFgG0WFEDhS`)
given for traceability back to the source frames: `12:17` Banners, `12:25` Body, `12:74` Footer.

| Slot | Variant | Background rule | Status | Existing impl. |
|---|---|---|---|---|
| Hero | Hero + image, 2 CTAs | hero gradient | **Ship** | net-new |
| Hero | Single-column title/subtitle | hero gradient or solid | **Ship** | close match to current `hero` section in `landing-template.html` |
| Hero | Solid kelly-blue, personalized headline ("...FOR {Company}") | solid brand blue | **Ship** | net-new — best fit for "personalized for X" framing |
| Hero | Form in hero (single/two-col) | hero gradient | Defer | lead-gen focused, not needed for a sales-collateral one-pager |
| Body | Left/right alternating, image+copy | navy / kelly / white / gray | **Ship** | maps to existing `findings` section |
| Body | 2/3/4-column icon grid | white | **Ship** | maps to existing `capabilities` section |
| Body | Stat/proof cards (3-up) | white | **Ship** | maps to existing `proof` + `roi` sections |
| Body | Accordion (plain) | white | **Ship** | net-new |
| Body | Single column w/ bullets | white | Defer | |
| Body | People cards | white | Defer | |
| Body | Accordion (image swaps on click) | white | Defer | interaction complexity not worth it for spike |
| Body | Video/interactive demo embed | white/gray | Defer | |
| Body | Custom (free-form HTML/text block) | inherits page bg | **Ship** | net-new; user-controlled raw content, not a curated Algolia component |
| Footer | Plain CTA footer | brand blue band + dark footer | **Ship** | maps to existing `cta_band` + `footer` |
| Footer | Alt gradient CTA footer | hero gradient band | **Ship** | net-new, reuses hero gradient token |
| Footer | Full mega-footer w/ nav | dark | Defer | existing footer is intentionally minimal (sales one-pager, not the main site) |

**Shipped count**: 3 hero / 4 body (proof+roi counted together since they already coexist as one visual
rhythm) + accordion + grid + left-right = effectively 5 distinct body variants / 2 footer.

**Assembly rule** (from Figma annotations): nav and footer are both explicitly removable. Left/right
body sections may sit on navy, kelly-blue, white, or gray — but two adjacent sections should not repeat
the same background, to preserve the alternating visual rhythm visible in the Ralph Lauren exemplar.

---

## Component Mapping (UIUX SOP Decision Matrix)

From `docs/workspace/custom-landing-page/archive/dell-02-aesthetic.md` — the component picks already
made for the first prototype, which this design system inherits rather than re-derives:

| Content | Component |
|---|---|
| Hero ROI/big number | Bounce Card (Dollar Amount / ROI, Hero tier) |
| Proof stats (3-up) | Finding Card Gradient (Primary tier) |
| Findings / features | Finding Spread (70/30) or Gap Pair (before/after framing) |
| Vertical tag ("Technology Hardware...") | Eyebrow (Supporting, Navigation/Wayfinding row) |
| Competitive callout (golden angle) | Quote Card or Signal Card, depending on copy shape |

---

## Visual References

- `reference-ralph-lauren.pdf` / `pdf-pages/page-{1..7}.png` — full real exemplar page, in order: nav →
  hero → proof-stat cards → logo wall → testimonial carousel → 3-icon feature row → dark CTA banner →
  alternating left/right sections → 8-icon capability grid → recommended-reading cards → awards strip →
  final CTA → mega-footer.
- `figma-refs/banners.png`, `figma-refs/body.png`, `figma-refs/footer.png` — the modular section
  catalog screenshots, annotated with each variant's name and background-color rule.

## Existing Prototype (validated 2026-07-15, see plan Step 0)

`~/prism/marketer/landing-template.html` + `render-landing.mjs` already implement one fixed flow using
these exact tokens (hero → proof → roi → findings → capabilities → cta_band → footer), confirmed by
rendering `dell.landing.json` and `nike.landing.json` and screenshotting the output. This design system
formalizes what that prototype already got right, and defines the additional variants needed for the
section-picker wizard (plan Steps 4/6/7).
