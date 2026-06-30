# STATUS: IA-Redesign-Pending

**Tag:** `IA-Redesign-Pending` (the report Information-Architecture redesign A/B prototype)
**State:** PAUSED, ready to resume. Built + reviewed + pushed to a Vercel preview. NOT promoted to production.
**Paused:** 2026-06-30. **Owner:** Arijit.
**Resume trigger:** next session say "resume IA-Redesign-Pending" (or "read docs/status/IA-Redesign-Pending.md").

---

## One-line what
Two side-by-side IA prototypes of one audit (Home Depot Mexico) so real users decide browse-vs-chat: `/ia/ia1/` browse-centric, `/ia/ia2/` chat-centric, shared core, feedback widget. Production untouched.

## Where everything lives
- **Code:** repo `prism-hub`, branch `feat/ia-ab-prototype` (PUSHED to origin, UNMERGED). All new code under `prism-hub/ia/` + `api/feedback.js` + an add-only `/api/feedback` route in `server/chat-proxy.mjs`.
- **Per-task build ledger (exact resume map):** `prism-hub/.superpowers/sdd/progress.md` — every task, commit range, review verdict, and known debt.
- **Spec:** PIP `docs/specs/2026-06-30-prism-ia-ab-prototype-design.md`.
- **Plan (10 tasks):** PIP `docs/plans/2026-06-30-prism-ia-ab-prototype.md`.
- **Memory:** `project-prism-ia-ab-prototype`, `feedback-final-review-real-data`.
- **Preview URL:** Vercel dashboard -> `prism-hub` project -> Deployments -> the `feat/ia-ab-prototype` build (a `…-git-feat-ia-ab-prototype-….vercel.app` URL).

## Exact state (what is done)
- Tasks 1-9 of the plan: BUILT, each per-task reviewed (spec + quality), fixes applied.
- Final whole-branch review (opus, on real data): found + fixed 4 session-wasters (raw-JSON rendering from wrong accessors, dead Export buttons, missing chat error guard, blank-screen-on-fetch-fail).
- Independently verified gate: `ia/verify.ts` 3/3 (isolation + A/B parity + no-em-dash), `job-model.test.js` 10/10, zero em dashes, production diff EMPTY (reports/, index.html, chat-widget.js, api/chat.js), chat-proxy add-only (18 ins / 0 del).
- One-liner blanked; `/ia1` `/ia2` redirect stubs added.
- **Pushed** -> Vercel builds a PREVIEW. Production `main` (prism.chowmes.com, /reports/) UNTOUCHED.

## Design decisions LOCKED (do not re-litigate on resume)
- Surface = the live prism-hub published report. Fix it from a flat 72-surface library toward scoped, low-overwhelm access.
- Don't pick browse vs chat by opinion: ship BOTH, A/B test, let user feedback decide. Vary ONLY the access axis (shared data, job carve, brief, CSS skin identical).
- Both shells contain a Seller cockpit + a Prospect view (mode toggle).
- Seller carve = 6 intent-verb jobs: Know the account / Prove it's broken / Make the money case / Know who decides / Run the conversation / Reach out. Exports = an action on cards + tray, NOT a job.
- Prototype scope = Home Depot Mexico only (frozen JSON); seller + prospect both. IA2 chat = text + "open full" deep-links (reuses Cassandra `/api/chat`, slug forced to homedepot-mexico).
- Feedback = in-prototype widget; durable capture only on the VPS path.

## HOW TO RESUME (next session)
1. `cd ~/prism-hub && git checkout feat/ia-ab-prototype`
2. Read this file + `prism-hub/.superpowers/sdd/progress.md` (the granular ledger).
3. Open the Vercel preview and run the manual click-through (chrome MCP was DOWN at pause):
   - `/ia/` compare landing; `/ia/ia1/` brief + 6-job rail + toggle; `/ia/ia2/` ask box + 6 chips + Enter-to-send + browse-all drawer + open-full.
4. Decide: iterate the prototypes, OR promote to production (stage 2 below).

## STAGE 2 — promote to production (user-gated, needs VPS hands)
1. Merge `feat/ia-ab-prototype` into the deploy branch (open a PR or fast-forward).
2. On the VPS: `git pull /opt/prism-hub`.
3. If `/api/feedback` 404s on prism.chowmes.com, add a Caddy `handle /api/feedback` reverse_proxy block mirroring `/api/chat`, reload Caddy.
4. Route testers to **prism.chowmes.com/ia/** (durable feedback via chat-proxy JSONL at `/opt/prism-hub-feedback.jsonl`; live grounded chat). The Vercel `/api/feedback` only logs.
5. Live-verify both shells render + chat returns a grounded answer + a feedback click appends a JSONL line.

## Accepted debt (known, not blockers)
- `verify.ts` isolation guard blind to untracked NEW files in prod dirs; `walk()` hardcodes `isFile` (dead symlink guard).
- `chat-proxy` feedback `appendFileSync` blocks the loop (negligible at tester scale).
- IA1 double-render flash on chat "open full".
- Some production content is computed in the 12k-line server template, not in the JSON (full ROI lever calc, explicit MEDDPICC, discrete discovery-Q list) -> those panels render the available JSON identically in both shells (parity preserved; it is a navigation test, not a content test).

## Sibling initiatives (the 3 we scoped together; this is #3)
1. Downloadable deliverables (render gaps) — queued; partly absorbed here (Exports surface). See SESSION.md (artifacts track) + memory `project-downloadable-audit-artifacts`.
2. Discovery-OS incorporation — confirmed NOT in the generator (still SPIN); queued. Source: PIP `docs/research/Discovery-OS-v1.md`.
3. IA overwhelm — THIS. At preview.
