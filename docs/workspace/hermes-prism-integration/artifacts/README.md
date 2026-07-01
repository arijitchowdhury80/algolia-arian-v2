# Downloadable audit artifacts — generators

Build Algolia-branded downloadable deliverables from a `{slug}-audit-data.json`.

## Files
- `make_report.py` — **the lead deliverable.** Portrait A4 chaptered audit DOCUMENT (matches the
  L.L. Bean reference at `PIP/docs/example-and-context/L.L. Bean Search Audit -Algolia.pdf`).
  Emits a self-contained HTML; render to PDF with headless Chrome.
- `make_deck.py` — 16:9 slide deck (HTML on the Algolia deck-stage engine -> PDF). Built earlier;
  superseded as the lead format by the portrait doc, but kept (user may still want a presented deck).
- `inspect_tpl.py` — dumps the official PPTX template's layouts/placeholders (reference only).

## Dependencies
- python-pptx (`pip install --user python-pptx`) — only the old PPTX path needs it; the HTML
  generators do not.
- Sora TTF embedded from `Algolia-Design-System/assets/fonts/Sora.ttf` (downloaded this session;
  also installed to `~/Library/Fonts`).
- Headless Chrome at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.
- `pdftoppm` (poppler, `/opt/homebrew/bin`) for PDF -> PNG verification. No LibreOffice on this Mac.

## Run (portrait document)
```
J=/Users/arijitchowdhury/prism-hub/petsmart/petsmart-audit-data.json
python3 make_report.py "$J" /tmp/report.html
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu \
  --no-pdf-header-footer --print-to-pdf=/tmp/out.pdf --virtual-time-budget=15000 "file:///tmp/report.html"
pdftoppm -png -r 80 /tmp/out.pdf /tmp/pg   # then Read /tmp/pg-N.png to verify visually
```
Verify slides/pages visually by Reading the PNGs (the Read tool renders images). qlmanage thumbnails
only page 1; pdftoppm gives every page.

## Design system (the brand source)
`/Users/arijitchowdhury/Dropbox/AI-Development/Algolia-Design-System/` — `colors_and_type.css`
(tokens), `assets/` (logo pack: Algolia-logo-white/blue.svg, marks, fonts/Sora.ttf), `decks/`
(deck-stage.js + deck-template-2026.html, 11 layouts), `SKILL.md`/`README.md`. The official PPTX
template: `uploads/Algolia Slide Tempalte 2026.PPTX` (extracted XML in `work/pptx-xml`).

## Grounding rule (hard)
Every number comes from the audit JSON and is shown WITH its source (impact_stat_source,
intelligence_signals[].source_url, bibliography, industry_context). No invented data. No em dashes.
No financials/pricing in the deliverable (user decision).

## Known gaps to fix next
1. DONE 2026-06-30. (Root cause was NOT a sandbox block: logo.clearbit.com's free logo API is dead
   — DNS no longer resolves, shut down post-HubSpot acquisition.) Strip now shows a typographic row
   of real Algolia customers pulled from this audit's `case_studies` (prospect excluded). To upgrade
   to real SVG logos: vendor licensed logo files into the design system and build `strip` from them.
2. DONE 2026-06-30. `clip()` limits were ~half the real field lengths; raised so sentences complete.
   Verify with `grep -o '…' out.html | wc -l` == 0.
3. Pages still have a whitespace lower-third. Can fit 3 findings/page and add a capability
   before/after page like the reference's NeuralSearch page. Content decision — do not pad with
   ungrounded filler.
4. Roll out to the other 7 full-set reports + bake into the audit pipeline (arijit-skills
   `algolia-search-audit/scripts` alongside render-audit.ts / generate-pdf.sh).
