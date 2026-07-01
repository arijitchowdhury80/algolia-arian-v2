# Downloadable Algolia-branded Artifacts: Deep Look

**Date:** 2026-06-30. Status: investigation complete, design pending. No code written yet.

## How the deliverable pipeline works today
Claude writes one file per audit: `{slug}-audit-data.json`. A Deno renderer (`render-audit.ts`, in arijit-skills `algolia-search-audit/scripts/`) does token substitution into static HTML templates and writes output HTML. A separate shell script `generate-pdf.sh` uses headless Chrome (`--print-to-pdf`) to turn certain HTML files into PDFs. Claude never writes layout HTML.

Templates (arijit-skills `.../templates/`): `index-template.html` (the SPA), `book-template.html` (multi-page binder), `ae-action-report-template.html`, `strategic-battle-card-template.html`, `prospect-leave-behind-template.html`, `deliverables-template.html`, research pages, and `algolia-brand.css` (34KB, injected everywhere).

## What exists vs what is downloadable (the gap)

| Artifact | Template | PDF mode in generate-pdf.sh | Generated in pipeline? | On prism-hub today? |
|---|---|---|---|---|
| SPA report (index.html) | yes | n/a (web app) | yes, published | yes (all reports) |
| Leave-behind (3pg prospect) | yes | leave-behind | yes (the ONLY auto PDF) | HTML yes, PDF NO |
| AE report (1pg) | yes | ae-report | NO (mode exists, not called) | HTML yes (8 cos), PDF NO |
| Battle card (1pg landscape) | yes | battle-card | NO (mode exists, not called) | HTML yes (8 cos), PDF NO |
| Book / binder (30-36 ch) = the "McKinsey deck" | yes | binder | NO (never invoked, never validated) | NO |
| Playbook, business case, signal brief | none | none | Markdown only | NO |
| ABX campaign (10 files) | none | none | Markdown only | NO |
| Slide deck / presentation (16:9) | DOES NOT EXIST | none | never | NO |

**Bottom line:**
1. Zero PDFs are published to prism-hub. Not a single `.pdf`, `.pptx` under `~/prism-hub/`.
2. The "Download" UI exists but is dead: the SPA topbar has a "Print" button (`window.print()`, crude `@media print` that dumps all 5 tabs sequentially) and a "Downloads" dropdown driven by `abx_sequence.assets_library[]`, which is an empty array for every published report, so it is hidden.
3. The PDF infrastructure (Chrome headless, 4 modes) exists but is a manual local dev step. `render-audit.ts` literally prints "Run generate-pdf.sh to convert HTML files to PDF." It is never run during publish.
4. There is NO real presentation/slide-deck format anywhere. The "McKinsey deck" in the skill descriptions is marketing language for the book-binder HTML, which is a document, not 16:9 slides. No pptxgenjs / python-pptx / reveal.js exists.

## Branding raw material (what we have to brand with)
- Colors (canonical, Algolia-correct): `#003DFF` blue, `#5468FF` purple, `#23263B` navy text, plus status red/amber/green. Well used.
- Font: brand standard is **Sora** (300/400/600). The SPA uses Sora. BUT the three print templates (leave-behind, battle-card, ae-report) diverge to **Source Sans 3** — visible inconsistency in any PDF.
- Logo: clean blue wordmark SVG only at `PIP/frontend/public/algolia-logo.svg`. White version exists only as inline SVG (hub) or a base64 PNG copy-pasted into each print file. No self-hosted white SVG. The "Algolia Angle" badge uses a live Google favicon URL that will break in offline PDF rendering.
- `algolia-brand.css` (34KB) is the single source of truth, injected by the renderer.

## The two distinct pieces of work
**A. Make the existing deliverables real downloadable branded PDFs (infra exists, wire it up).**
- Generate leave-behind / AE report / battle card / book PDFs as part of publish (not manual).
- Put the files in each report dir; wire a real Download control (or populate assets_library) so they download from the SPA + chat.
- Brand polish: standardize Sora across print templates, self-host a white logo SVG, kill the offline-favicon dependency.

**B. Build a true Algolia-branded presentation/slide deck (does not exist, net-new).**
- A 16:9 slide deck an AE can present or send. Built from the same `audit-data.json`.
- Format fork: editable PPTX (AE edits in PowerPoint/Google Slides; needs pptxgenjs/python-pptx) vs polished fixed PDF slides (HTML 16:9 -> Chrome PDF, prettier, not editable) vs reveal.js HTML (present in browser, link not file).

## Delivery options (where generation runs)
- Pre-generate at publish: run generate-pdf.sh modes during render, ship the PDFs in each report dir (static, simple, fits the prism-hub auto-deploy). Files get committed/deployed.
- On-demand: the new Next.js frontend (Slice 1, gated) generates per-request via headless Chrome. Heavier, always fresh, gated.

## Open decisions for the user
1. Scope: wire up existing PDFs (A) first, build the new slide deck (B), or both.
2. If B: presentation format = editable PPTX vs fixed branded PDF slides vs browser reveal deck.
3. Delivery: pre-generated files in report dirs vs on-demand in the gated Next app.
4. Which reports: pilot on petsmart first, or all 10.
