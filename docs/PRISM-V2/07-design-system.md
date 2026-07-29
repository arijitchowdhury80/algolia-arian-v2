# PRISM Design System — "Signature" (v1)

**Created 2026-07-06.** Extracted verbatim from the canonical SPA generator template and reconciled into one reusable system. This is Arijit's signature design language — every V2 screen imports from here; nothing gets re-invented.

**Source of truth (do not edit these to change the system — edit this doc + the tokens file):**
- `~/.claude/skills/algolia-search-audit/templates/index-template.html` (SPA template, 13,027 lines — the canonical layout + components)
- `~/.claude/skills/algolia-search-audit/templates/algolia-brand.css` (brand CSS injected into every deliverable, 1,140 lines)
- `~/.claude/skills/algolia-search-audit/scripts/render-audit.ts` (the renderer that stamps them out)

> **This is a single fixed LIGHT theme** — no dark-mode / `prefers-color-scheme` in source. Two components are deliberately dark *within* the light page (the topbar and the "Company Snapshot" navy panel). If V2 wants a dark mode, that is a NEW decision, not an extraction.

---

## 1. Design tokens (the reconciled single source)

Ship this as `prism-tokens.css` and import it into every V2 screen. This reconciles the source's real inconsistencies (noted inline) into one clean set.

```css
:root {
  /* ---- Brand ---- */
  --blue:      #003DFF;   /* primary brand (Algolia blue) */
  --purple:    #5468FF;   /* secondary brand */
  --gray:      #23263B;   /* primary text / dark surfaces (topbar) */
  --mid:       #6B7280;   /* secondary / muted text */
  --light:     #F5F5F7;   /* light surface tint */
  --border:    #E5E7EB;   /* hairline borders */
  --white:     #FFFFFF;
  --page-bg:   #F8F9FB;   /* body background */

  /* ---- Semantic status ---- */
  --red:       #DC2626;   /* danger / critical */
  --amber:     #D97706;   /* warning / moderate */
  --green:     #059669;   /* success / positive */
  --teal:      #0891B2;   /* info accent */
  --violet:    #7C3AED;   /* secondary accent */

  /* ---- Signal / brand-mark colors ---- */
  --linkedin:  #0A66C2;
  --competitor:#EF4444;
  --partner:   #0D9488;
  --social-x:  #000000;

  /* ---- Tint + border pairs (soft-bg + subtle border per status) ---- */
  --blue-tint:  #EEF2FF;  --blue-border:  #C7D2FE;
  --red-tint:   #FEF2F2;  --red-border:   #FECACA;
  --amber-tint: #FFFBEB;  --amber-border: #FDE68A;
  --green-tint: #F0FDF4;  --green-border: #BBF7D0;
  --violet-tint:#F5F3FF;  --violet-border:#DDD6FE;
  --teal-tint:  #F0FDFA;  --teal-border:  #99F6E4;
  --hover-tint: #F0F4FF;  /* link/row hover bg */
  --near-white: #FAFAFA;  /* alternating rows */

  /* ---- Type ---- */
  --font: 'Sora', sans-serif;   /* weights 300 / 400 / 600 only */

  /* ---- Radius / shadow (reconciled) ---- */
  --radius:    8px;                          /* default; cards use 12px, tiles/bento 16–20px, pills 100px */
  --shadow:    0 2px 8px rgba(33,36,61,0.10);/* base elevation — was rounded 2 ways in source, use this */
  --shadow-hover: 0 6px 24px rgba(33,36,61,0.11);

  /* ---- Layout ---- */
  --topbar-h:  52px;
  --tabrail-h: 80px;
  --drawer-w:  480px;
  --content-max: 1040px;   /* source had both 1040 and 960 — standardize on 1040 for content */
}
```

**Reconciliations Track B must apply (source bugs → clean system):**
- Gauge/bar JS colors (`#16A34A` green, `#2563EB` blue) differ from CSS `--green`/`--blue`. → Use the CSS tokens everywhere; retire the JS-only hexes.
- `--shadow` was rounded two ways (`rgba(33,36,61…)` vs `rgba(35,38,59…)`). → One value (above).
- Two content max-widths (1040 / 960). → Standardize 1040.
- No `:disabled` button state exists. → **Add one** (see §5) — V2 doors need it (Marketer's disabled buttons currently rely on ad-hoc styling).
- Section sidebar position flips left/right between the two source files. → Pick one (recommend left rail).

---

## 2. Color usage
Primary text `--gray` on `--page-bg`. Brand blue `--blue` for links/primary actions (links: underline-on-hover only, **no** color change, **no** arrows/icons — this is a stated non-negotiable). Status colors always as a **tint + border + text** triad (e.g. critical = `--red-tint` bg / `--red-border` / `--red` text). Dark accent panels use the navy gradient `linear-gradient(135deg,#0d1b38,#1a2d52 55%,#13244a)`.

## 3. Typography — Sora
Google Fonts, weights **300 / 400 / 600 only**, `display=swap`.

| Element | Size | Weight | Line-height | Tracking |
|---|---|---|---|---|
| h1 | 56px | 300 | 1.10 | -2px |
| h2 | 36px | 300 | 1.40 | -2px |
| h3 | 28px | 400 | 1.40 | -1px |
| h4 | 22px | 600 | 1.40 | — |
| h5 | 18px | 600 | 1.40 | — |
| body | 16px | 400 | 1.6 | — |
| label/eyebrow | 14px | 600 | — | uppercase, 0.12em |

Signature move: **light-weight (300) large headlines** with negative tracking — the elegant, editorial feel. Eyebrows are 14px/600 uppercase in `--blue`.

## 4. Motion
Three easing curves, used consistently:
- **Spring/bounce:** `cubic-bezier(0.34, 1.3, 0.64, 1)` — card hovers, animated highlights.
- **Standard ease-out:** `cubic-bezier(0.4, 0, 0.2, 1)` — drawers, accordions, bar fills.
- **Slow organic:** `cubic-bezier(0.445, 0.05, 0.55, 0.95)` — background blobs.

Durations: `0.12s` hover color, `0.15s` button bg, `0.18–0.25s` card lift, `0.35–0.45s` drawer/accordion, `0.6–1s` progress fills. Signature effects: 4-layer "3D shadow" card lift, mouse-tracking conic-gradient glow border (`.glow-card`), floating stat-bar (`float-bob`), animated gradient blobs behind the snapshot panel.

## 5. Components (canonical CSS in the source; key ones)
**Base card** (`--radius`? no — cards use 12px), hover lift `translateY(-2px)` + `--shadow-hover`. **Metric tile** (label uppercase 14/600 + 1.35rem value, `--red`/`--green` variants). **3D shadow card** (4-layer shadow stack). **Bounce card** (case-study stat, red/amber/green gradients, `scale(0.95) rotate(-1deg)` on hover). **Data table** (`--gray` header, white, uppercase 0.06em th, row hover `#FAFBFF`, horizontal-scroll on mobile). **Feature/capability table** (red-vs-blue vendor columns, `.cap-yes/-no/-part`). **Bento tiles** (glassmorphism, `backdrop-filter: blur(20px)`, mouse-tracked radial spotlight). **Score gauge** (SVG, circumference 283, color thresholds <4 red / 4–6 amber / ≥6 green/blue). **Cmd+K palette**, **right slide-in drawer**, **signal cards** (4px left color-bar by type), **severity badges** (tint+border+text triad).

**Buttons — NOTE:** the source has **no generic `.btn` system** — every control is bespoke (`.tb-btn`, `.tab-btn`, `.filter-btn`, `.cs-read-link`, `.proof-pill`, etc.). **Track B should define ONE button system** (primary / secondary / ghost / pill + hover/active/focus/**disabled**) distilled from these, so V2 doors stop re-authoring buttons. The `--disabled` state is missing entirely in source and must be added.

Full per-component CSS lives in the source files above and in the sub-agent extraction transcript; Track B lifts it into `prism-components.css`.

---

## 6. The Claude Design prompt (seeded with real tokens)

Paste this into a Claude / Claude Design session to generate on-brand screens. It is **seeded with the actual extracted values** so output matches the live system — far higher fidelity than pointing a tool at the login-gated `prism.chowmes.com`.

> **You are generating a UI screen in the PRISM design system.** PRISM is a premium enterprise prospect-intelligence product. Match this design language exactly — it is a fixed light theme, elegant and editorial, never generic-SaaS.
>
> **Font:** Sora (Google Fonts, weights 300/400/600 only). Large headlines use weight **300** with negative letter-spacing (h1 56px/−2px, h2 36px/−2px). Body 16px/400, line-height 1.6. Eyebrows: 14px/600, uppercase, letter-spacing 0.12em, colored `#003DFF`.
>
> **Palette:** brand blue `#003DFF`, secondary purple `#5468FF`, primary text `#23263B`, muted text `#6B7280`, page background `#F8F9FB`, surfaces white, hairline borders `#E5E7EB`, radius 8px. Status colors as tint+border+text triads: critical `#FEF2F2`/`#FECACA`/`#DC2626`, moderate `#FFFBEB`/`#FDE68A`/`#D97706`, positive `#F0FDF4`/`#BBF7D0`/`#059669`. Dark accent panels use `linear-gradient(135deg,#0d1b38,#1a2d52,#13244a)`.
>
> **Links:** blue, underline on hover only — no color change, no arrows/icons.
>
> **Elevation:** base shadow `0 2px 8px rgba(33,36,61,0.10)`; cards lift on hover with `translateY(-2px)` and a deeper shadow. Use the signature 4-layer "3D shadow" for hero cards.
>
> **Motion:** hover transitions 0.12–0.18s; card lifts with `cubic-bezier(0.34,1.3,0.64,1)`; drawers/accordions with `cubic-bezier(0.4,0,0.2,1)` over 0.35–0.45s. Restrained, premium — never bouncy-everywhere.
>
> **Components to reuse:** metric tiles (uppercase 14/600 label + 1.35rem value), data tables (dark `#23263B` header, uppercase 0.06em, row-hover `#FAFBFF`, horizontal-scroll on mobile), pill tab-rail (active = filled `#23263B` white text), Cmd+K palette, right slide-in drawer (480px), signal cards with a 4px left color-bar, severity badges as tint+border+text.
>
> **Buttons:** primary = solid `#003DFF` white text; secondary = white with `#E5E7EB` border, hovers to blue border+text; ghost = text-only, blue on hover; pill = fully rounded. Always include hover/active/focus/**disabled** states (disabled = 0.5 opacity, `not-allowed`).
>
> **Layout:** max content width 1040px, generous section rhythm (~96px between sections), fixed 52px topbar (dark `#23263B`), responsive down to 375px with tables scrolling and grids collapsing to one column.
>
> **Never:** generic Bootstrap/Material look, drop shadows everywhere, gradients on text, emoji as UI icons, or any color change on link hover. Output self-contained HTML+CSS using the tokens above as CSS custom properties.

---

## 7. Next for Track B
1. Emit `prism-tokens.css` (§1) + `prism-components.css` (distilled buttons/cards/tables with the added `:disabled`).
2. Apply the §1 reconciliations (kill source inconsistencies).
3. Retrofit the Marketer door onto the tokens file; build AE/BDR doors on it from the start.
4. Keep this doc as the living spec; the SPA template stays the reference implementation.
