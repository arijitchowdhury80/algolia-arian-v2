# SESSION — PIP (backend) · Claude

**This repo = PIP = the BACKEND. Worked by Claude.** (Frontend = PRISM, repo `prism.git`, worked on Codex. The old login-gate SESSION content that lived here was frontend work — it's in git history and belongs to PRISM.)

Date: 2026-07-01. Branch `feat/prism-e2e-cycle`. Remote `pip.git` (run `git remote -v` before pushing — `prism.git` is the frontend now).

## Resume action (do FIRST)
1. Read memory `session_pointer.md` (full plan) + `project-my-os-specs`, `reference-repo-naming-canon`, `feedback-modular-http-addressable-modules`.
2. `git status` — must be CLEAN before any restructure. Never run two Claude sessions on this repo at once (a two-thread collision happened 2026-07-01).
3. Then run the one waiting job below.

## The waiting job: backend consolidation
Make PIP the ONE backend codebase = web services + Hermes instance + skills. Steps:
1. Absorb the audit skills (`~/Dropbox/AI-Development/Personal/arijit-skills`) INTO PIP (skills are PIP-only). Re-point the global `~/.claude/skills` symlinks (BLAST RADIUS — do carefully, verify, show before it sticks).
2. Promote the Hermes instance from `docs/workspace/hermes-prism-integration/chowmes-prism/` (SOUL, plugins, executor) into a real `hermes/` folder.
3. Layout: `PIP/{prism_platform, hermes, skills, ...}`. Every module HTTP-addressable + packageable.
4. Tidy first, deploy button later. On a branch, verify, show before commit; don't push until Arijit is happy.

## State (2026-07-01, clean)
- Tree CLEAN, all pushed. HEAD ~`68df92e`+. Repos renamed (pip=backend, prism=frontend). Vault = Dropbox `Arijit-Second-Brain`.
- Shipped this era: editable PPTX audit deck (`make_deck_pptx.py`), Cass-as-executioner. MyOS fully specced (vault `Projects/MyOS/`).
- CLAUDE.md is canonical here; AGENTS.md symlinks to it.

## Not done (backend side)
Consolidation (above). Deploy bridge, tracker webhook + Athena, dashboard — all open, not urgent. Cross-project status: vault `Projects/ArijitOS/My-Projects.md`.
