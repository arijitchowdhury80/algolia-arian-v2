# Sales Leader door — the missing 4th role (parallel track, independent of Phase 2)

This is frontend work in the `~/prism` repo (the PRISM frontend/hub, separate from this PIP backend repo) — unrelated to the Phase 2 executioner rebuild running in parallel, safe to build concurrently.

## Context (read first)

- `docs/PRISM-V2/05-role-driven-ia.md` in THIS repo (PIP) — read in full. It locks the 4-role IA (AE/BDR/Sales-Leader/Marketer), the shared-core+role-lanes partition model, and has a complete ASCII wireframe for the Sales Leader door (lines ~91-110) already Arijit-directed, not a fresh design decision.
- AE (`~/prism/ae/door.html`), BDR (`~/prism/bdr/door.html`), Marketer (`~/prism/marketer/door.html`) doors already exist and are live — read all three for the established chrome/nav pattern (role switcher `[role: X ▾]`, shared visual language) before building. Sales Leader must match this pattern, not invent a new one.
- Per CLAUDE.md: **frontend work MUST invoke the `frontend-design`/`frontend-builder` skill before writing code.** Do not skip this.

## The gap

Sales Leader is the 4th locked role and the ONLY one of the 4 with no door built yet. Per the spec: Leader's view is the aggregate/portfolio dashboard — "the old 6-tab dashboard's real home" (heatmap across the whole book of accounts, ranked by $ opportunity, rollup signals like "N accounts stalled at stage X"), drilling into any account opens that account's AE door. No shared-core single-account header (Leader is aggregate, not single-account) — this is the one door that's a genuine exception to the shared-core+role-lanes pattern used by the other 3.

## Real data — NO FABRICATION (standing project rule)

Do not invent portfolio numbers. Real audited companies with real scores exist across:
- `~/prism-data/audits/{Dell,jbl,lululemon}/` (confirmed present, used by Phase 2's Task 5c this session)
- `~/Dropbox/AI-Development/Algolia Search Audit/{BritishAirways,MichaelKors,DSW,Nike,...}/`
- Published reports under `~/prism/reports/` and `~/prism/ae/data/dsw.json` / `~/prism/marketer/data/dell.json`
- The Postgres `audits` table (schema in `prism_platform/db/models.py`, `audit_data` JSONB blob) if reachable — check `GET /api/v1/audits/by-slug/{slug}/data` (added this session per git log, commit `2503493`) as a possible real data source.

Build the portfolio rollup by pulling REAL `score`/company-name/domain fields from whichever of these real sources you can actually read — do not fabricate "$340k opp" style numbers the spec's wireframe uses as ILLUSTRATIVE placeholder text, not real numbers to copy. If a real field (like a dollar opportunity estimate) doesn't exist anywhere in the real data, leave an explicit empty/TBD slot rather than inventing a number — same standing rule this project applies everywhere else (`feedback-no-mock-data-real-company-tests`, `feedback-audit-derivable-vs-sales-input-split`).

## What to build

1. `~/prism/sales-leader/door.html` (or wherever your frontend-builder run + the AE/BDR/Marketer precedent says it should live — check their exact directory pattern first).
2. Portfolio heatmap: one row per real audited company you can source data for, using their real score + domain. "Stage" (SS1/SS2/SS3) and "$ opportunity" — pull from real AE data (`ae/data/*.json`) where it exists; leave an honest empty slot where it doesn't.
3. Rollup line: a real, computed aggregate over whatever real data you have (e.g. "N accounts scored below 3.5"), not an invented insight.
4. Drill-through: clicking an account row opens that account's existing AE door (`~/prism/ae/door.html?domain=...` or whatever query-param pattern AE's door already uses — check it).
5. Same role-switcher chrome as the other 3 doors (`[role: Leader ▾]`).

## Verification (per CLAUDE.md — UI work needs a real browser check, not just "code looks right")

Load the built page in a real browser (Chrome MCP or Playwright) and confirm it renders without console errors, the heatmap shows real company names/scores (not placeholders), and the drill-through link actually navigates to a real AE door page. Screenshot it.

## Output

Report what you built, what real data source(s) you used per field, what's left as an honest empty slot, and the verification screenshot/evidence. If the real-data sourcing is messier than expected (e.g. no consistent dollar-opportunity field exists anywhere), say so plainly rather than papering over it with an invented number.
