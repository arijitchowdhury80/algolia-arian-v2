# UI/UX constraints applied — Sales Leader door

Reused the exact token set, spacing, and component conventions already validated on the AE/BDR/
Marketer doors (same source of truth: their inline CSS, copied verbatim for `:root` tokens, topbar,
btn/source-card classes). This guarantees:
- Emphasis tiers: heatmap table = hero (1), rollup stats + $ opportunity column = primary,
  stage/methodology = secondary, data-source footer = supporting. No tier inflation.
- Responsive: `.table-scroll` wrapper (same pattern BDR uses) makes the 5-column table scroll
  horizontally under 768px instead of breaking layout; `.rollup-stats` wraps at mobile widths.
- Accessibility: every drill-through is a real `<a href>` (not a div onclick only) so keyboard/
  screen-reader users can tab to and activate it; row-level click-to-navigate is a progressive
  enhancement layered on top, not a replacement. Focus-visible outline on `.btn`/`.drill-link`
  inherited from existing tokens. Color is never the sole signal — score bars are paired with the
  numeric score + critical/moderate counts in text.
- Contrast: `--color-muted` already darkened site-wide (documented inline) to pass 4.5:1 on both
  white and `--color-bg` — reused unmodified.
- No new aesthetic decision needed — consistency with the 3 live doors was the actual constraint.
