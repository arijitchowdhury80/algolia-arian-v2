# Reports IA Workspace

Current step: implementation.

Goal: make `/reports/` the single owner of PRISM audit pages, downloadable assets, screenshots, and audit data snapshots. The repository root should stay focused on the product shell, API, shared assets, tests, and documentation.

Verification target:
- `node --test tests/reports-structure.test.mjs`
- `npm test`
- Browser checks for `/reports/` and at least one moved audit route.
