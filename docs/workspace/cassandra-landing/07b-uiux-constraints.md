# UI/UX Constraints - Cassandra Landing Refresh

## Emphasis Rules
- One hero per section. In the Cassandra section, Cassandra's profile block is the hero element.
- Primary elements: three concrete capability cards and channel actions.
- Secondary elements: supporting section lead and flow statement.
- Supporting elements: status labels, small chips, captions.

## Component Constraints
- Profile image must have stable dimensions and `object-fit: cover`.
- Cards must not be nested inside other cards except the profile panel itself as a single framed feature.
- Buttons/links must keep clear labels and visible focus states.
- No visible instructional copy about how the UI is designed.

## Breakpoints
- 375px: Cassandra section becomes one column; portrait remains legible and text wraps without overlap.
- 768px: one-column or balanced stacked layout is acceptable.
- 1024px: two-column profile/capabilities layout.
- 1280px: full-width composed section with portrait and cards.

## Accessibility
- Portrait uses descriptive alt text.
- Contrast must remain AA against the dark background.
- Interactive elements keep keyboard focus outlines.
- Touch targets remain at least 44px where clickable.

## Conflict Check
The existing page uses raw CSS variables and inline SVGs. For this static HTML page, keep that pattern rather than adding a framework dependency. The new work should reuse existing tokens and introduce only Cassandra-specific variables where the current token set lacks warmth.
