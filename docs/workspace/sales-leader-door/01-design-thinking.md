# Sales Leader door — design thinking (condensed)

This is the 4th of 4 role doors. AE/BDR/Marketer are already built and live in ~/prism with an
established visual system (dark topchrome, white card sections, Sora font, blue accent #003DFF,
fetch-JSON-and-render pattern, active/locked data-source footer cards). The job here is
**consistency with precedent**, not a fresh aesthetic decision — Leader must look like the same
product, not a different one. Aesthetic = same family already in use (closest named aesthetic:
`theme-professional` — polished, business-ready, Sora/Inter-class sans, restrained color). No new
theme skill invoked; tokens copied verbatim from ae/door.html to guarantee visual identity.

## 1. Mental model
"Dashboard" — portfolio heatmap, at-a-glance status across a book of accounts, ranked. The Leader
does NOT think in terms of one account (unlike AE/BDR/Marketer) — they think in terms of the whole
book. Per the locked spec (docs/PRISM-V2/05-role-driven-ia.md line ~97): NO shared-core
single-account header. This is the one door that's a genuine structural exception.

## 2. Information architecture
- Hero (1): the portfolio heatmap table itself — ranked rows, one per real audited company.
- Primary (2-3): the rollup line (computed aggregate insight), the $ opportunity column, the score column.
- Secondary: stage column (mostly empty — only 1/10 accounts has real AE-stage data), methodology note.
- Supporting: data-source footer cards (active/locked), same pattern as other 3 doors.

## 3. Interaction flow
- Common actions: (1) scan heatmap for weakest/highest-opportunity accounts, (2) click a row to
  drill into that account's AE door, (3) read the rollup line for a one-glance takeaway.
- Happy path: load page -> table renders -> click a company name -> new tab opens
  ae/door.html?account=<slug> (real navigation, same query-param contract AE already reads).
- Empty/error state: if the JSON source can't be fetched, same retry-button pattern as the other
  3 doors (already proven, reused verbatim).

## 4. Cognitive load budget
Chunks: 1 heatmap table + 1 rollup banner + 1 methodology note + 1 data-sources section = 4. Under
the 5-chunk budget, no accordion/tab split needed.

## 5. Emotional journey
Scan (which accounts need attention) -> orient (where's the $ opportunity concentrated) ->
confidence (numbers are real/cited, not a mystery score) -> action (click through to the account
that matters most right now).

## 6. Pre-mortem
Tigers:
- Generic-AI look: mitigated by reusing the exact CSS tokens/typography already proven distinctive
  across 3 live doors (Sora, dark topbar, blue accent, tinted score badges).
- Overload: heatmap capped at 10 real rows (all we have real data for), no pagination needed yet.
- Mobile 375px: table needs horizontal scroll wrapper (`.table-scroll`), same fix BDR already uses.
- Fabricated numbers: hard-blocked by design — every cell either renders a real JSON field or an
  explicit empty-slot chip; no interpolated/invented values anywhere in the render code.
Elephants:
- Real AE-stage data only exists for 1 of 10 companies (dsw) — drill-through to the other 9 will
  land on a real AE door page that then fails to load account data (no JSON file for that slug).
  This is an honest, disclosed gap (documented in output), not something this task can silently fix
  since it requires building 9 more ae/data/*.json files, out of scope for this door.
