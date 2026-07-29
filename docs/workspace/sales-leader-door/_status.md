# Sales Leader door — status: SHIPPED

Built ~/prism/sales-leader/door.html + ~/prism/sales-leader/data/portfolio.json (generated from
real reports/data/*.json + ae/data/dsw.json). Matches AE/BDR/Marketer chrome exactly. Verified
in a real Playwright-driven Chromium browser: 10 real rows render, 0 console errors, drill-through
click-through confirmed to a real, loading AE door page (dsw), touch targets fixed to 44px min
after first pass found a 16px violation, mobile/tablet/desktop screenshots captured to /tmp/.

Known real-data gap surfaced honestly, not fabricated around: Brooks Running's
financials.roi_scenarios annual_impact strings in the SOURCE audit-data.json are malformed
("$9.75M" -> renders as ".75M") — a pre-existing upstream data defect in
reports/data/brooks-running-audit-data.json, not something this task introduced or silently
patched. Flagged in the final report to Arijit rather than guessing the missing digit.
