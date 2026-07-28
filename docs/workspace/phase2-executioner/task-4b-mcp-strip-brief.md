# Task 4b brief — MCP-strip per skill (Track C.2)

Read first, in full: `docs/workspace/phase2-executioner/task-1-recon-report.md` section 5 (ground truth on MCP wiring — already corrected once, trust this over the original plan doc's premise) and `docs/plans/2026-07-12-prism-finishing-build-plan.md` PHASE 2 section (patch #7, Track C item 2).

## Ground truth (confirmed live by recon, do not re-derive)

- MCP is wired ONCE, globally, at `/opt/prism-executor/.mcp.json` on the VPS — loaded for the entire shared `claude -p` process regardless of which skill is "currently running." No skill has its own per-skill MCP config file.
- Exactly 3 of the 16 skills need MCP: `algolia-audit-browser` (chrome/chrome-devtools-mcp), `algolia-intel-social` (apify), `algolia-intel-partner` (crossbeam, streamable-http, OAuth — confirmed live/verified per memory `reference-crossbeam-mcp-live.md`, not an open OAuth question).
- `algolia-intel-news` was flagged by the 2026-07-03 plan doc as a possible apify user too — CONFIRM or RULE OUT this specific skill's actual MCP tool usage before touching anything (read its SKILL.md + any script it calls; don't assume the plan doc's hedge is correct).
- The other 13 skills use no MCP tool today.
- **Patch #7 (hard sequence dependency, already satisfied)**: `prism_platform/pipeline/gate.py` is now built, tested, and committed (Task 3, commit `4f3f5d9`) — you may check MCP-stripped skill output against the real gate, not eyeballing. `factcheck_mechanical.py` in particular is real and runnable.

## What to build

For each of the 13 MCP-free skills, one at a time (per-skill verify loop — strip, re-run that skill standalone via `run-audit.sh --skill <name>` against a real existing workspace, confirm output is still valid via `factcheck_mechanical.py` / `gate.py`'s stage 1, THEN move to the next skill — not a batch strip-then-test-all):

1. Confirm the skill genuinely has zero MCP dependency by reading its SKILL.md + scripts (not just trusting the recon's grep-for-config-file finding — a skill could call an MCP tool without a dedicated config file if it's using the global one; verify by reading what tools the skill's SKILL.md actually invokes).
2. Design and build a **per-skill scoped MCP config** replacing the global one — likely one of: (a) a per-skill `--mcp-config` flag passed to `claude -p` when `run-audit.sh` dispatches with `--skill <name>` (check if the CLI supports this — `claude -p --help` on the VPS or locally), pointing to an empty/minimal config for the 13 skills and the real 3-server config only for browser/social/partner, or (b) confirm whether Claude Code's `claude -p` supports disabling MCP entirely via a flag for a given invocation. Pick whichever mechanism is real and verifiable — do not assume a flag exists without checking `claude -p --help` or the docs first.
3. This step depends on Task 4a's per-skill dispatch existing to be meaningful at scale (stripping MCP only matters once skills run as separate processes) — but you CAN and SHOULD verify the mechanism works for a single skill standalone via the EXISTING `--skill` flag (confirmed live today) without waiting for Task 4a's automatic loop. Do not block on Task 4a.
4. Access: use the `hostinger-vps-ssh` skill / SSH to `chowmes-vps` for VPS-side config reads/writes. This modifies live VPS config files (`.mcp.json` or new per-skill configs under `/opt/prism-executor/`) — back up the current `.mcp.json` to a timestamped copy in the same directory BEFORE changing anything (non-destructive precaution, not a mandate-boundary item, but do it anyway).

## Definition of done

- For each of the 13 MCP-free skills: re-run standalone via `--skill <name>` against a real (existing, already-audited) company workspace with the new scoped/stripped config, show the actual command + exit code + confirm `factcheck_mechanical.py` still returns exit 0 (or the same exit code it returned before your change — capture BEFORE and AFTER for at least 3 representative skills as your evidence, not all 13 if that's too slow, but state clearly which ones you spot-checked vs. which you changed but didn't individually re-verify).
- `docker ps -a` / `ps aux` on the VPS during your test runs shows no `chrome-devtools-mcp`/`apify`/`crossbeam` MCP process spawned for the 13 non-MCP skills.
- The 3 MCP-needing skills (browser, social, partner — confirm/correct `news`) are untouched or explicitly still get their real MCP config — do not accidentally strip a skill that needs one.
- Per critique patch #10: confirm `umami`, `cios-postgres`, `ac2-lab-backend`, `scout` are still `Up`/healthy in `docker ps -a` after your changes — this VPS serves unrelated live services, your changes must not disturb them.

## Output

Write your report to `docs/workspace/phase2-executioner/task-4b-report.md`. Return status DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED with the report path and a 3-line summary. If `claude -p` has no clean per-invocation MCP-scoping mechanism, say so plainly (BLOCKED or NEEDS_CONTEXT) rather than inventing a workaround that weakens the global config for everyone.
