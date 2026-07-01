# FIX SPEC — financial + traffic render (Dell audit, 2026-07-01)

Two DIFFERENT bugs that both surface as "financial section broken." They are NOT the same recurring error — which is why patching one never fixed the other. Fix each at the root + patch the skill + add a QA reject-gate so neither recurs.

## Bug 1 — Financial chart/table: RENDER bug (data is complete)
- **Symptom:** chart shows only Revenue bars; table shows Revenue values but Gross Profit / EBITDA / Op Income / Net Income / all margins render "—". "Data as of —" empty.
- **Root cause (verified):** the DATA is complete in `dell-audit-data.json` → `financials`: `gross_profit_fy2026`=$22.7B, `ebitda_fy2026`=$11.9B, `net_income_fy2026`=$5.9B, `gross_margin_pct`=19.21, `ebitda_margin_pct`=10.5, `net_margin_pct`=6.28, `operating_margin_pct`=8.86, `market_cap`, `balance_sheet`, `total_assets/debt`, `cash`. The RENDERER only wires up revenue: `render-audit.ts:buildRevenue3yRows` (line 640) and `buildAppendixFinancialData` (1039) map `revenue_3y` only. The main Financial-Profile chart+table component (bars + EBITDA-margin line + metric table) reads only revenue and never reads the gross_profit/ebitda/net_income/margin fields that exist.
- **Fix:**
  1. Locate the Financial-Profile chart+table component (NOT in `render-audit.ts` main builders, NOT in `docs-dark.html` — find the SPA template/component that draws "Financial Profile / 4-year trajectory ... EBITDA Margin %").
  2. Wire it to read `gross_profit_fy2026`, `ebitda_fy2026`, `net_income_fy2026`, `operating_margin_pct`, `gross_margin_pct`, `ebitda_margin_pct`, `net_margin_pct`, and the "data as of" date.
  3. **Data-shape gap:** gross_profit/ebitda/net_income exist for FY2026 ONLY (revenue has 3 years). For a fully-populated 3-year table, extend `collect-financials.py` (algolia-intel-financial-public) to extract gross_profit/ebitda/op_income/net_income for all 3 years from yfinance `income_stmt` (it has them). Until then, render FY2026 and leave prior years blank (not the whole table "—").
  4. Also fix the YoY/trend arrow: Revenue 88.4→95.6→113.5 is UP, but the render showed "↓ 8%" — trend direction logic is inverted/misordered.

## Bug 2 — Traffic/SimilarWeb: DATA-acquisition bug (opposite problem)
- **Symptom:** entire traffic section empty (monthly_visits/bounce/etc. all null).
- **Root cause (verified):** `traffic.source` = "SimilarWeb API v4 — all endpoints returned 401 Unauthorized". The SimilarWeb API key is dead. AND the manually-captured logged-in SimilarWeb screenshots for Dell (`PIP/docs/temp/similarweb-wave2/dell/`) were NOT used — the audit ran on the VPS (no screenshots there) and the traffic skill fell back to the dead API instead of vision-extracting from screenshots.
- **Fix:**
  1. Patch `algolia-intel-traffic` to vision-extract from the logged-in SimilarWeb screenshots (the resolved Wave-2 method) as the PRIMARY path; the REST API is dead (401), do not depend on it.
  2. Ensure the screenshots reach the audit runtime (get `similarweb-wave2/<slug>/` onto the VPS executor, or make the skill accept a screenshots dir).
  3. Skill must FAIL LOUD (not silently null) when neither API nor screenshots yield data.

## Bug 3 (meta) — QA gate blind spot
- Factcheck passed this **9.6 PROCEED** because it only checks JSON grounding, never the RENDERED output. Empty chart series, all-dashes table, and 401'd traffic sailed through.
- **Fix:** the acceptance gate (Athena / Definition-of-Done) must verify the RENDERED deliverable: reject if a chart series is empty, a table is >X% dashes, or a section's `source` contains "401"/"Unauthorized"/"error". This is the gate that stops incomplete audits from publishing.

## Recurrence prevention
- Patch the financial + traffic SKILL.md files to state the exact data shape the renderer expects (field names, 3-year metrics), so script and template agree.
- Add the render-completeness checks to the acceptance gate so a regression is caught before publish, not by Arijit's eyes.
