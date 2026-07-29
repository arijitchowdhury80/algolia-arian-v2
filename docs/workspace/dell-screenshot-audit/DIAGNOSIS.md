# Dell Screenshot Audit — Diagnosis (2026-07-02, before re-run)

Arijit's ask: check Dell's search-audit screenshots (run June 30, before today's screenshot-quality
lessons existed), re-run, fix all the screenshots.

## Method
Pulled all 29 screenshots from `/opt/prism-executor/audits/dell/deliverables/screenshots/` read-only,
viewed every one directly (not grep, not file size alone). Cross-read `research/09-browser-findings.md`
(26KB, the claims built on these screenshots) and the prior factcheck pass
(`deliverables/dell-correction-manifest.md`, `deliverables/dell-skill-feedback.md`, June 30 22:10 —
already fixed 4 real data bugs: dead Algolia case-study slugs, scoring denominator math, count
derivation, competitors[] degradation — but that pass was DATA-ONLY, never looked at images).

## Finding 1 — 5 files are honest, intentional WAF-block documentation, NOT a bug
`07-no-results.png`, `08b-non-product-redirect.png`, `08c-non-product-order-status.png`,
`waf-access-denied.png`, `waf-zero-results-attempt.png` (all 45-46KB) are genuine Akamai
"Access Denied" pages. **This is correctly and transparently documented** in
`09-browser-findings.md`'s "Method & WAF Limitations" section — the auditor found the WAF
pattern (blocks direct URL nav + Enter-key submit, allows in-page button-click submit), used a
working workaround for all subsequent tests, and explicitly labeled these 5 small files as
intentional evidence of the block state, never claiming them as real "no results" UI. This is
NOT the lululemon-class bug (mistimed capture silently treated as a false negative finding).
Verdict: **no fix needed**, this class is fine as-is.

## Finding 2 — REAL, previously-uncaught bug: 12 of 29 screenshots (≈40%) have an undismissed
## promotional popup covering most of the frame

Dell.com shows a "Sign Up and Save" lead-gen modal (dark blue panel, ~left half of viewport, 10%-off
email signup, close-X top-right) on results/category/product pages. The June 30 run correctly
declined the OneTrust cookie banner but never detected/dismissed this SEPARATE modal. It is NOT
caught by the site's file-size gate (all compromised files are >200KB, comfortably over the old
50KB heuristic) — this is exactly the "size passes, content is broken" class from
`docs/plans/2026-07-02-cassandra-airtight-pipeline-goal.md` §3.1b, and exactly what today's
(built-but-not-wired) `screenshot_gate.py` popup/overlay-marker check targets.

**Compromised files (verified by direct visual inspection):**
| File | What's hidden |
|---|---|
| `04-results-monitors.png` | monitors results grid, facets, sort options |
| `05b-typo-alienwear-results.png` | alienware corrected results grid |
| `09b-intent-gaming-results.png` | gaming-pc-spec results grid |
| `10-merchandising-category.png` | Laptop Computers category page |
| `13b-nlp-battery-travel-results.png` | NLP battery/travel results grid |
| `13c-nlp-video-editing.png` | NLP video-editing results grid |
| `14-dynamic-facets.png` | facet panel (looks like a near-duplicate of 09b — same query/state) |
| `14b-b2b-partnumber-results.png` | B2B part-number results grid |
| `15b-crosssell-dock-results.png` | docking-station cross-sell results |
| `18-recommendations-pdp.png` | XPS 13 PDP recommendations/cross-sell area |
| `20-analytics-signals.png` | rating/review/analytics signals on PLP |
| `21-annotated-nlp-fail.png` | annotation built ON TOP of the compromised 13b |

**Clean (verified, no popup):** `01-homepage`, `02-empty-state`, `03-sayt-laptop`, `05-typo-alienwear`,
`06-synonym-notebook`, `08-non-product-return-policy`, `09-intent-gaming-spec`, `12-mobile-homepage`,
`12b-mobile-sayt-xps`, `13-nlp-battery-travel`, `14-b2b-partnumber-sayt`, `15-crosssell-dock-latitude`.
Pattern: SAYT/dropdown captures are clean; RESULTS-page captures are the ones the popup hits.

## Why the findings TEXT is probably still accurate even though the screenshots are bad
The auditor was live in a real browser session and could read result counts/banners/facet text
directly from the DOM at capture time (before the popup fully rendered, or via non-screenshot
observation) — most claims in `09-browser-findings.md` read as genuinely observed, not guessed.
This is different from the lululemon bug (screenshot WAS the sole evidence, and was wrong). Here
the screenshots are POOR EVIDENCE for otherwise-plausible claims, not proof the claims are false.
**Action:** fix the screenshots; re-verify (not blindly trust) the claims once evidence is clean;
change a verdict only if new clean evidence contradicts it.

## Fix in flight
Re-running ONLY the browser/search-testing phase (not research/financial/scoring/factcheck — those
are already factchecked and out of scope) via a targeted `claude -p` invocation that names the exact
defect (popup-not-cookie-banner), lists the 11 files to overwrite, and requires dismissing the modal
(click close-X or Escape, wait 1-2s, then capture) before every results/category/product screenshot.
Uses the SAME proven WAF workaround (warm session, type + click "Search Dell" button, never Enter/
direct-nav) already documented and working in the original run. Backup of all 29 originals kept at
`docs/workspace/dell-screenshot-audit/original/` (local, read-only pull, untouched by the re-run).
Launched 2026-07-02 ~22:49 EDT, log at `/opt/prism-executor/audits/dell/dell-screenshot-fix-rerun.log`.

## Verification checklist (post-run)
- [ ] All 11 target files re-captured, none still show the Sign Up and Save modal
- [ ] No new WAF blocks introduced (compare against the 5 known-honest WAF files, should stay 5)
- [ ] `09-browser-findings.md` claims re-verified against clean screenshots; any correction explained
- [ ] `10-scoring-matrix.md` untouched unless a verdict genuinely changed (explain if so)
- [ ] No regression to the previously-factchecked research/financial/deliverable files (June 30 pass)
- [ ] Final site health check on prism.chowmes.com (unrelated live services, standard discipline)
