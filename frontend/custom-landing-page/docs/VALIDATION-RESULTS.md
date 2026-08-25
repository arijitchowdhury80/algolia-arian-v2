# Whale Builder — Phase 1 Validation Results
_2026-08-25 · Build-view preview, prod app :8799 · harness = browser automation, no Jahia writes_

Method: for each module, the harness clicked through **every rendition** (hashing the preview block to prove
each renders distinctly), then reset to a slot-bearing variant and **applied every element** (typed text →
appears; browsed a real Jahia asset → real `<img>/<video>` renders; toggled a pick item → appears).

| Module | Renditions (distinct/total) | Text | Asset(s) render real | Pick applies |
|---|---|---|---|---|
| Hero | 5/5 ✓ | 2/2 ✓ | video ✓ + background ✓ | — |
| Proven Impact | 8/8 ✓ | — | logos ✓ | ✓ |
| Customer Quotes | 8/8 ✓ | — | logos ✓ | ✓ |
| Features / Solutions | 8/8 ✓ | — | icons ✓ | ✓ (12 items) |
| Built Around Priorities | 8/8 ✓ | — | image ✓ | ✓ (7 items) |
| Recommended Resources | 8/8 ✓ | — | thumb ✓ | ✓ |
| Parting Shot / CTA | 2/2 ✓ | 3/3 ✓ | bg ✓ | — |
| Search (standard) | fixed ✓ | — | — | — |
| Awards (standard) | fixed ✓ | — | — | — |

**Totals:** 47 change-module renditions (all distinct) + 2 standard; every element (text / asset / pick)
applies and previews with a real Jahia asset streamed through the proxy. **No Jahia writes.**

## Fixes made to reach green (this pass)
- Hero manifest corrected to ground truth: dropped spurious `lockup` (logo), added real `background` (image).
  Hero now renders a real background image (cover, dark overlay) + real video.
- Removed dead per-module renderers (proven/quotes/features/priorities/resources) — all body modules render
  via `bodyLayoutHTML` across the 8 real Figma body layouts.
- Hero/module video autoplays muted+loop inline (was static first frame).
- Asset render across all module layouts + parting background (prior commits).

## N/A-by-design (validated as correctly absent, not failures)
- Hero video slot exists only in variants 0 (image+2CTAs) and 1 (single column); variants 2/3 (forms) and
  4 (kelly solid) intentionally have no video slot. The harness's first run flagged these as false positives
  until it was corrected to test each element on a slot-bearing rendition.

## Not covered by Phase 1 (by design)
- **Save to Jahia** — no writes. Deferred to Phase 2 (publish / draft persistence, governance-gated).
- **Jahia-fidelity of edited page** — Build view is the faithful configurator preview with real assets; the
  "True preview (Jahia)" tab shows the real *published* page. Editing reflected in Jahia's *own* render is the
  Phase 2 edit-reflection build.
