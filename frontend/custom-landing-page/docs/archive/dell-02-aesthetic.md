# Aesthetic Selection

**Chosen: `brand: algolia`** (not one of the 5 generic frontend-builder themes).

Why: the frontend-design system already ships a dedicated Algolia brand theme (Sora font, `#003DFF` primary, exact hero gradient `#0D1240 → #21243D → #001A8A`). PRISM's own live site (`~/prism/index.html`, `~/prism/reports/dell/index.html`) already uses this exact palette in production (`--blue: #003DFF`, Sora, dark `#21243D` header). Using the canned generic themes (dashboard/enterprise/clean/professional/report-designer) would fork the visual language from what's already shipped. Consistency with the existing PRISM system outranks picking a "better fit" generic theme.

Token source: vault `Standards/UIUXDesignSOP/algolia.md` (verbatim CSS block, see 03-uiux-constraints.md).

Component picks (from Decision Matrix, `Standards/UIUXDesignSOP/index.md`):
- Hero ROI number → **Bounce Card** (Dollar Amount / ROI, Hero tier)
- 3 proof stats → **Finding Card Gradient** (Primary tier)
- Findings/features sections → **Finding Spread (70/30)** (Image / Screenshot, Primary tier) or **Gap Pair** if framed as before/after
- Vertical tag ("Technology Hardware...") → **Eyebrow** (Supporting, Navigation/Wayfinding row)
- Golden-angle competitive callout → **Quote Card** or **Signal Card** depending on final copy shape
