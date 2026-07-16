# SESSION.md — Custom Landing Page system built end-to-end (2026-07-15 evening)

**Last updated: 2026-07-15 evening (persist/handoff).**

## STATUS (one line)

New per-prospect Custom Landing Page system (Marketer persona deliverable) built end-to-end and proven with a real Lululemon audit, then significantly reworked after Arijit's own live testing — everything is uncommitted on both repos, and the wizard has not had a full hands-on pass yet (session ended mid-demo, on Arijit's explicit instruction not to disrupt it).

## RESUME ACTION (numbered, concrete)

1. Ask Arijit whether his demo has ended, and whether he wants the latest batch committed on both repos (PIP + prism-hub `prism-v2`). Do NOT auto-commit — he's explicit that commits need his ask.
2. If committing: PIP side is `alembic/versions/011_add_landing_pages.py`, `prism_platform/db/models.py`, `prism_platform/main.py`, `prism_platform/api/routers/landing_pages.py`, `prism_platform/v2/modules/landing_page_intake/`, `prism_platform/static/landing_intake/`, `pyproject.toml`, `docs/workspace/custom-landing-page/`, `tests/v2/test_landing_page_intake_v2.py`. prism-hub side is `marketer/render-landing.mjs`, `marketer/partials/*.html` (incl. new `body-custom.html`), `marketer/schema/landing-page.schema.json`. Do NOT commit the unrelated pre-existing noise sitting in `git status` (`.development-loop/`, `CHECKPOINT.md`, `migration-dryrun` backups, `phase2-executioner/`, `sales-leader-door/`, etc.) — none of that is this session's work.
3. Get Arijit's full hands-on pass on the rebuilt wizard at `http://localhost:8123/admin/landing-intake/` (or wherever the server is running) — specifically the Step 1 add/remove section-instance flow, Step 2's per-instance content, and Step 3's real preview.
4. Reconcile `~/prism/marketer/lululemon.html` on `prism-v2` — it was pushed to GitHub BEFORE the section-instance rework, so the live pushed version is stale relative to local. Re-render and re-push once Arijit confirms.
5. Phase 2 (explicitly deferred, unscoped): map `sections[]`/`content` to real Algolia Jahia components, push via Jahia's API instead of static HTML.

## WHERE WE STOPPED (exact)

Arijit was mid-demo on `localhost:8123` when the session ended. The last code change was the full section-instance rework (Step 1 body-section picker rebuilt from checkbox-toggle to an ordered add/remove list; `render-landing.mjs` rewritten so each body section instance gets its own independent mustache scope). This was verified working on a separate test port (8124, closed after testing) without touching Arijit's live 8123 session. `/persist` + `/handoff` was then run to close the session cleanly.

## DECISIONS LOCKED

- **Repo split:** PIP (backend) owns intake/curation/data-transform. prism-hub (frontend) owns rendering + serving. Matches the existing backend/frontend split (`reference-repo-naming-canon`).
- **PRISM is optional, never a prerequisite:** enforced at the DB level — `landing_pages.audit_id` is a **nullable** FK with `ondelete="SET NULL"`, not just a UI affordance.
- **Intake surface:** a real Algolia-branded wizard (not a CLI/JSON file), built via the `frontend-design` skill.
- **Variant scope:** a curated subset of the Figma section library, not the full ~17 variants, not the single original fixed flow. Documented in `docs/workspace/custom-landing-page/00-design-system.md`.
- **Section model (locked after Arijit's live testing):** body sections are an ordered, independently addable/removable list of *instances* — the same variant can appear more than once, each with fully independent content. Hero and footer stay single-instance (a page has exactly one of each). Reordering is add/remove only, no drag-and-drop (explicit choice, deferred).
- **Preview must be real:** Step 3 calls the actual production render pipeline (same partials, same `render-landing.mjs`) via a scratch-file `/preview` endpoint, never a hand-rolled approximation.
- **External content:** three concrete asks, all built — (1) manual fields for every pickable section type (ROI, Capabilities, not just Findings/Proof), (2) a free-form custom HTML/text section variant, (3) paste-JSON import from any audit-data-shaped external source, reusing the same extractor as the PRISM path (it was never actually coupled to Postgres).

## REMAINING WORK

- Commit decision + actual commit (both repos) — pending Arijit.
- Full Arijit hands-on pass on the rebuilt wizard — not done yet.
- Reconcile the stale pushed `lululemon.html`.
- Phase 2 (Jahia push) — fully unscoped, deferred.
- Minor: accessibility label warnings in the wizard's console (`No label associated with a form field`) — not blocking, not fixed this session.
- Minor: the `sales-leader/` directory and `deno.lock` sitting untracked in prism-hub are NOT this session's work — flagged, not touched, not explained (unknown origin).

## REFERENCE FILES

- Design system: `docs/workspace/custom-landing-page/00-design-system.md` (tokens, section inventory, component mapping, visual refs from the PDF/Figma Arijit provided).
- Schema: `docs/workspace/custom-landing-page/schema/landing-page.schema.json` (mirrored to `~/prism/marketer/schema/`).
- PIP module: `prism_platform/v2/modules/landing_page_intake/` (`candidate_extractor.py`, `content_assembler.py`, `schemas.py`, `config.py`).
- API: `prism_platform/api/routers/landing_pages.py` (audits list, candidates, preview, extract-from-json, build).
- Wizard: `prism_platform/static/landing_intake/index.html`.
- Renderer: `~/prism/marketer/render-landing.mjs` + `~/prism/marketer/partials/*.html`.
- Tests: `tests/v2/test_landing_page_intake_v2.py` (7 passing — candidate extraction, no-fabrication, severity-vocabulary normalization regression).
- Vault: `Projects/PRISM/index.md` (new compiled-truth entry), `log.md`, `tasks.md`.
- Memory: `project-custom-landing-page-system-built.md`, `feedback-preview-must-use-real-pipeline-not-approximation.md`, `feedback-section-picker-needs-independent-instances-not-type-toggle.md`, `feedback-dont-disrupt-live-demo-separate-port.md`.

## WHAT HAS NOT BEEN DONE (prevents false completion claims)

- **Nothing is committed** on PIP. On prism-hub, only the ORIGINAL `lululemon.html` + first-pass renderer/partials were committed and pushed (`e4fd896` on `prism-v2`) — the section-instance rework that came after is NOT pushed, so the live GitHub state is stale relative to local disk.
- **No Arijit hands-on verification of the rebuilt wizard.** Everything in this session was verified by Claude via Chrome DevTools MCP on a separate test port — real evidence, but not the same as Arijit's own usage, which is exactly what surfaced the last 3 rounds of real bugs. Assume more gaps exist until he's tested it himself.
- **No Jahia integration** (Phase 2) — explicitly out of scope this session, zero code exists for it.
- **No accessibility fixes** on the wizard's form fields (missing `<label>` associations) — flagged by Chrome DevTools, not fixed.
- **Drag-to-reorder** for body sections — explicitly deferred, add/remove-only was the locked decision.

## FILES WRITTEN THIS SESSION

**PIP (new):** `alembic/versions/011_add_landing_pages.py`, `prism_platform/api/routers/landing_pages.py`, `prism_platform/v2/modules/landing_page_intake/{__init__,config,schemas,candidate_extractor,content_assembler}.py`, `prism_platform/static/landing_intake/{index.html,assets/algolia-mark-blue.svg}`, `tests/v2/test_landing_page_intake_v2.py`, `docs/workspace/custom-landing-page/{00-design-system.md,schema/landing-page.schema.json,figma-refs/*,pdf-pages/*,reference-ralph-lauren.pdf,archive/*}`.

**PIP (modified):** `prism_platform/db/models.py` (added `LandingPage`), `prism_platform/main.py` (router + no-cache wizard route), `pyproject.toml` (added `jsonschema`).

**PIP (deleted, consolidated into `docs/workspace/custom-landing-page/archive/`):** `docs/workspace/marketer-door/*`, `docs/workspace/marketer-landing-dell/*`.

**prism-hub (new):** `marketer/partials/{shell-open,shell-close,hero-image-2cta,hero-single-column,hero-kelly-personalized,body-proof-stats,body-roi,body-left-right,body-accordion,body-grid,body-custom,footer-plain-cta,footer-alt-gradient}.html`, `marketer/schema/landing-page.schema.json`, `marketer/lululemon.html`, `marketer/data/lululemon.landing.json`.

**prism-hub (modified):** `marketer/render-landing.mjs` (variant-aware assembly, per-instance scoping, theme override injection).

**Vault:** `Projects/PRISM/{index.md,log.md,tasks.md}`, `wiki/hot.md`, `wiki/log.md`, `Projects/AI-OS/My-Projects.md`.

**Memory:** `session_pointer.md` (rewritten), `MEMORY.md` (updated), `project-custom-landing-page-system-built.md` (new), `feedback-preview-must-use-real-pipeline-not-approximation.md` (new), `feedback-section-picker-needs-independent-instances-not-type-toggle.md` (new), `feedback-dont-disrupt-live-demo-separate-port.md` (new), `project-tracker-status.md` (updated).

## UNRELATED, STILL-PENDING THREAD (not touched this session)

Notebook doc effort + `feat/audit-acl` auth-fix merge — both exactly where 2026-07-14 left them. See vault `Projects/PRISM/index.md`'s "Next resume action" block for both options. Do not restart the development-loop ceremony for either.
