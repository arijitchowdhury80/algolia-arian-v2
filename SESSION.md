# SESSION — PRISM/PIP · Claude (2026-07-01, Crossbeam partner-refresh thread)

**This repo = PIP = BACKEND** (github `pip.git`). Frontend = PRISM (`prism.git`, local `~/prism`, VPS `/opt/prism-hub`). Deploy = push to `prism.git` → webhook → prism.chowmes.com live. VPS can't push; publish from laptop.

## ▶ STATUS (headline)
Big job APPROVED + planned, NOT started: **portfolio-wide Partner-Intelligence refresh via live Crossbeam + full cascade.** Plan on disk: `~/.claude/plans/of-course-re-run-first-jiggly-pelican.md`. Ready to execute P0 in this fresh session. User wants AUTO mode + ultracode (/goal + /loop + Workflow). Pilot-first (Dell+Nike) → human review → portfolio.

## ▶ RESUME ACTION (do in order)
1. Read `~/.claude/plans/of-course-re-run-first-jiggly-pelican.md` (the approved plan — full detail).
2. Read memory `reference-crossbeam-mcp-live.md` (Crossbeam is live; the ACCOUNT-RESOLUTION crux; the corrected Dell finding).
3. **Verify Crossbeam still authed** — call a cheap tool (e.g. `get_account_context` name=Dell). If tools gone / 401 → re-auth: call `mcp__crossbeam__authenticate`, give user the URL, they authorize in browser (allow cookies / drop Brave shields, one clean pass).
4. Execute **P0 prerequisites** (before any prospect loop): P0-A rebuild `algolia-intel-partner` Crossbeam logic (account resolution + 4-tool recipe) · P0-B fix deploy path (publish-audit.sh targets DEAD `~/algolia-arian-v2`; real = `~/prism/reports/{slug}/` + `prism.git` push; root-cause the `reports/dell/` 404) · P0-C schema seam (`partner_intel` unmodeled in audit_data_schema.py; parse_partner_extended lifts only B2/C; wire migrate-audit-data.py) + pinpoint where partner-dependent strategic_angles are authored.
5. **Pilot**: full per-prospect pipeline on Dell + Nike → stage into `~/prism/reports/` (DO NOT push) → STOP, get user eyeball on both live-preview.
6. On sign-off → portfolio loop (13 remaining) via resumable ledger (state.json) → stage all → single batch review → one push.

## Crossbeam recipe per prospect (the corrected method — see plan)
Resolve OWNED SFDC record (`owner != null` + non-empty `populations`, prefer high-intent) FIRST, then: `find_overlap_partners`(owned id) + `find_partner_recommendations`(deal/account name) + `find_partner_contacts`(owned id). Naive domain lookup = dead legacy records = false zeros (this is what made all prior audits fall back to WebSearch). Label `[FACT — Crossbeam MCP, date]`.

## DONE + VERIFIED this session
- **Drift merge SHIPPED** (RESUME #1 from prior session): grafted signal-synthesis (`synthesize_signals` + 10 helpers) into canonical arijit-skills `generate-audit-data.py`. Commit **8ec80a1** on `feat/gemini-grounded-search`, unpushed. All gates passed (py_compile, Dell synthesis 24→11 merges, British Airways full render, schema+completeness, 212 pytest pass/1 pre-existing fail). Caught + fixed a real bug: canonical `lift_media_quotes` dropped `speaker` → `dedupe_merge_signals` was inert. The Attempt-1 style-token blocker was STALE (both templates already pass the gate). `resynth-signals.py` already in both copies.
- **Crossbeam MCP LIVE** — OAuth authed (was never used before; all ~15 audits ran on WebSearch fallback, 0 FACT labels). Verified real data: Dell owned record = 64 overlaps + 7 EI recs; ecosystem = 130,776 records.
- **Corrected a wrong conclusion I made mid-session**: "Dell = zero overlap / retail-only" was a wrong-record artifact. Fixed in memory `reference-crossbeam-mcp-live.md` + MEMORY.md index + noted observation 8713 was wrong.
- **Red ticker restored to bright red** (`#FF0000`, was softened `#FF4444`) in canonical `index-template.html` line 262. Source-of-truth fixed; live reports get it on the re-render sweep (offered immediate one-off patch+push if wanted).
- **MEMORY.md compacted** 20.7KB→14.5KB (was near read limit), all 80 entries preserved as one-liners.
- Emailed-update content drafted for Gerard/Crossbeam (in-thread, not sent by me).

## ⚠ NOT DONE (no false completion)
- Partner refresh NOT started (P0 not begun). publish-audit.sh NOT fixed. `reports/dell/` 404 NOT root-caused. Schema seam NOT done. No ledger/state.json exists yet.
- Nothing pushed (drift merge commit 8ec80a1 unpushed; 3 render-contract SKILL.md still dirty in arijit-skills — leave them).
- Live reports still show old `#FF4444` ticker until re-render sweep.

## Other open threads (parked)
- **Clerk login** — blocked on user: run the `!` one-liner (keys → VPS `/opt/prism-chat-proxy/.env` + restart + verify reports gated). Static prod proxy `~/prism/server/chat-proxy.mjs` already has the gate; fail-open until keys set.
- **Tech-stack badge rename** — "BuiltWith" hardcoded (template ~5043/7445/4508/8943) but we use detect-search; user to confirm name (my pick "NETWORK SCAN").
- Network/VPN security architecture (own thread, ADR first). 6 Wave-2 audits not run. Scout-on-VPS. Cassandra single-skill invocation.

## Reference files
- Plan (authoritative): `~/.claude/plans/of-course-re-run-first-jiggly-pelican.md`
- Memory: `reference-crossbeam-mcp-live.md` (Crossbeam + crux), `feedback-audit-pipeline-reconciliation-gotchas.md`, `feedback-audit-financials-render-not-data.md`
- Canonical skills: `~/.claude/skills/algolia-*` → symlink to `~/Dropbox/AI-Development/Personal/arijit-skills/skills/algolia-audit-skills/`
- Portfolio audits: `~/Dropbox/AI-Development/Algolia Search Audit/{Company}/research/`
- Lessons this session: `docs/sop/lessons-log.md` (merge lessons appended)

## git remote -v before push (prism.git = FRONTEND, pip.git = BACKEND). Branch feat/prism-e2e-cycle (PIP), feat/gemini-grounded-search (arijit-skills, has 8ec80a1 unpushed).
