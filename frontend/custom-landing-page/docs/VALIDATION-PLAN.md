# Whale Builder — Recursive Validation Plan
_2026-08-25 · goal: prove every module × every element × every rendition applies, previews, and composes correctly_

## What we are validating (the matrix, from the real manifest)
Every **cell** = (module, rendition/variant, element). Grounded in `src/manifest.ts`, not guessed.

| Module | Elements (from manifest) | Renditions | Cells |
|---|---|---|---|
| hero | headline, subhead, media(video), **backgroundImage(image)** | 5 (HERO_VARIANTS) | 20 |
| proven | logos(asset), proof-points(pick 1–6) | 8 (BODY_VARIANTS) | 16 |
| quotes | logos(asset), quotes(pick 1–5) | 8 | 16 |
| features | icons(asset), features(pick 8–10) | 8 | 16 |
| priorities | image(asset), priorities(pick 1–7 grouped) | 8 | 16 |
| resources | thumb(asset), resources(pick 0–5) | 8 | 16 |
| parting | message, cta, ae, bg(asset) | 2 (FOOTER_VARIANTS) | 8 |
| search, awards | standard (fixed) | 1 each | 2 |
| **Total** | | | **~110** |

### N/A-by-design (critical — do NOT fail these)
Not every element renders in every rendition; some cells are intentionally absent:
- **hero media (video/image):** shown in v0 (image+2CTAs), v1 (single-col). In v2/v3 the form replaces the media; in v4 (kelly solid) there is no media slot → media = **N/A** in v2,v3,v4.
- **hero lockup:** eyebrow text vs logo image — see open question on the lockup field.
- **body asset banner:** renders in the head for all 8 layouts (universal), so applies in every body cell.
- A cell marked N/A must be asserted as **correctly absent**, not broken.

## Three things each cell must prove
1. **Applies** — setting the element (type text / browse asset / pick item) updates the module's state (`field.v` / `field.assetPath` / `pick.chosen`).
2. **Previews (Build view)** — the change renders in the schematic preview, in the correct rendition layout, distinct from other renditions, with NO fabricated content (empty → explicit empty state).
3. **Composes (True preview / page)** — the element appears in the **real page**. Phase-gated (see below), because true-preview edit-reflection is not built yet.

## Two-phase scope (honest)
- **Phase 1 — Build view (now).** Validate all ~110 cells against the React schematic preview. This is fully automatable today. Surfaces real bugs (e.g. the body-module dead-code below).
- **Phase 2 — Jahia page (after edit-reflection is wired).** The True preview currently renders only the PUBLISHED page; it does not yet reflect operator edits (needs the draft-write step). "The page is created correctly with every component" can only be validated end-to-end AFTER that build. Until then Phase-2 cells = **BLOCKED**, reported as such (not passed).

## Known bugs the matrix will formalize (already spotted in code)
- **Body-module dead code:** `previewInner` routes proven/quotes/features/priorities/resources through the generic `bodyLayoutHTML`; the dedicated rich renderers (proven statistic cards, quotes carousel, feature grid) at App.tsx ~L81–111 are **never reached**. So e.g. Proven renders as a generic column list, not `statisticCardTeaser` stat cards. Root-cause fix, not per-instance.
- **Body renditions are generic**, not module-specific — each body module offers all 8 BODY_VARIANTS but the layouts don't specialize per module. Decide intended behavior per module before asserting "correct."

## Manifest corrections from ground truth (do these BEFORE validating hero)
Verified live against the real banners (`.../algoliabanner` properties):
- **RL banner:** `sourceVideo` (internalVideo) + `backgroundImage`. No logo/lockup.
- **Belk banner:** `sourceVideo` only. No backgroundImage, no logo/lockup.
Therefore:
- **DROP hero `lockup` (logo)** — no such asset exists on either real page; the "Brand + Algolia" eyebrow is template text, not an image. The field is spurious.
- **ADD hero `backgroundImage` (image asset)** — RL uses one; the configurator is missing it.
- Net hero elements = headline, subhead, media(video), backgroundImage(image). Still 4 → 20 cells, but the right 4.

## The recursive harness (Phase 1, automatable now)
A browser-driven script (runs against the prod app on :8799), pseudo:
```
for module in modules:
  if module.kind == standard: assert one fixed block renders; continue
  for variant in module.variants:
     select variant
     for element in module.elements:
        if cell is N/A-by-design(module,variant,element): assert absent; mark N/A; continue
        apply element:
           text field  -> set a sentinel value
           asset field -> browse, pick a real Jahia file (skip folders)
           pick-list   -> select up to max, incl. min/max cap + add-custom
        assert in Build-view preview DOM:
           - sentinel/asset/picks present in THIS module's block
           - layout matches the variant (distinct class/structure vs other variants)
           - no fabricated values; empty -> explicit empty state
        record PASS / FAIL / N/A  (+ reason, + screenshot on FAIL)
reset module between variants
```
Output = a **matrix report** (module × variant × element → PASS/FAIL/N/A) + failure screenshots. Deterministic, re-runnable.

## Fix loop
For every FAIL: root-cause (fix the generator/renderer, not the one cell), re-run the harness, confirm green. Log recurring classes (e.g. dead-code routing) so they can't regress.

## Acceptance
- Phase 1: 100% of applicable cells PASS in Build view; every N/A asserted as correctly absent; the body dead-code + generic-rendition issues resolved or explicitly accepted.
- Phase 2 (post edit-reflection): the **whole page** renders in True preview with every operator-chosen component present and correct, diffed against the real published RL/Belk pages.

## Execution order
1. Build the harness + run it → produce the Phase-1 matrix (baseline, expect reds).
2. Triage reds → fix by class → re-run to green.
3. Wire true-preview edit-reflection (separate build; needs the draft-write decision) → run Phase-2 whole-page validation.
