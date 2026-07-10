# Audit Re-Validation SOP

*Written 2026-07-09, after the Lululemon full re-validation session (3 systemic bugs found, 6+
hours) and while starting Belk's re-validation — the first of 19 companies needing the same
forensic pass. This doc exists so the checklist is derived once and followed 19 times, not
re-derived per company.*

## MANDATORY: where this actually runs

**Every command in this SOP runs on `chowmes-vps` (`ssh chowmes-vps`), never on the local Mac.**
The audit workspace (`/opt/prism-executor/audits/{slug}/`), the skill scripts
(`/opt/prism-executor/arijit-skills/` and the live `~/.claude/skills/` on the VPS), Postgres, and
Scout all live there. The local Mac has none of this — no Postgres connection, no
`/opt/prism-executor`, no live skill environment.

**When dispatching a subagent for any step below, its prompt MUST say explicitly: "SSH into
`chowmes-vps` and run this there" — not just "run this command."** A subagent given a bare shell
command without that instruction will run it locally, find nothing, and either fail or (worse)
fabricate a plausible-looking result. This is not a style preference — a local run of these
commands does not exercise the real system at all.

Any local-machine work in this SOP is explicitly scoped and named: writing/reading this doc itself
(`PIP/docs/`), the `arijit-skills` git checkout for committing script fixes, and the `~/prism`
clone used to relay pushes when the VPS checkout lacks push credentials (see gotcha list below).
Everything else — the actual audit data, the actual skill execution, the actual Postgres reads,
the actual live-page verification — is VPS-side.

## Ground rule: the 3-step mandatory discipline (every module, every company, no exceptions)

1. **RE-VERIFY** — re-check the module's own data against a live source. Not a re-read of the
   existing file; an actual live check (re-run `detect-search`, re-query Postgres, re-scrape via
   Scout, etc., depending on the module — see the per-module list below).
2. **FACTCHECK** — run `algolia-audit-factcheck`'s mechanical check, scoped to this module's
   file(s). Record PASS/FAIL + reasons in a per-module note.
3. **QUALITY/EVAL SCORE** — run `algolia-audit-eval`'s 5-dimension score (completeness, source
   density, instruction adherence, data accuracy, no-fabrication), scoped to this module. Record
   the score.

A module isn't "done" until all three have a written result on disk. A module that fails
FACTCHECK or scores below threshold on EVAL does NOT feed downstream synthesis until re-fixed —
no silent pass-through. This is the exact discipline the factcheck-gate hardening fix (tonight,
Lululemon session) was built to enforce structurally — this SOP is the manual/subagent-driven
version of the same rule until Phase 5 of `PIPELINE-UNIFICATION-PLAN.md` (per-skill factcheck
gate) makes it automatic.

## Full module list (parameterized on `{company}` / `{domain}` / `{slug}`)

| # | Module | Skill | File(s) (`/opt/prism-executor/audits/{slug}/research/`) | What RE-VERIFY concretely means |
|---|---|---|---|---|
| 1 | Company Context | `algolia-intel-company` | `01-company-context.*` | Exec team/URLs still current; check for leadership changes since capture date |
| 2 | Tech Stack | `algolia-intel-techstack` | `02-tech-stack.*` | Re-run `detect-search --full-tech` live against `{domain}`; diff vendor/platform/CDN against file; confirm `current_vendor` and `tech_stack_summary` name the same vendor (self-consistency) |
| 3 | Traffic / SimilarWeb | `algolia-intel-traffic` | `03-traffic-data.*` | **HITL — ALWAYS ASK ARIJIT per-company** whether to re-capture (needs him logged into SimilarWeb PRO) or reuse the existing capture. Never assume either way. If reusing: verify internal sums reconcile and degraded/estimate labels are still accurate (not silently dropped) |
| 4 | Competitors | `algolia-intel-competitors` | `04-competitors.*` | Re-run `detect-search` on each named competitor; re-check any Golden-Angle (Algolia-customer) claims against the current case-study list |
| 5 | Test Query Set | `algolia-intel-queries` | `05-test-queries.md` | Confirm query mix still matches the company's actual current site structure/vertical |
| 6 | Industry Intel | `algolia-intel-industry` | `06-industry-intel.*` | Benchmark citations still live; watch for a stray unprefixed `industry-intel.*` duplicate (the exact filename bug found for both Lululemon and Belk this session — check every company for this) |
| 7 | Partner Intel / Crossbeam | `algolia-intel-partner` | `07-partner-intel.md` | **Known pipeline gap (see bug ledger):** this skill doesn't call Crossbeam MCP yet. Manually call `get_account_context` + `find_overlap_partners` for `{domain}` and diff against the file until the skill itself is fixed |
| 8 | Financial Profile | `algolia-intel-financial-public` or `-private` | `08-financial-profile.*` | Confirm correct method used (ticker present → public path; no ticker → 6-source private waterfall); spot-check 1-2 sources live |
| 9 | Browser Findings / Screenshots | `algolia-audit-browser` | `09-browser-findings.md`, `deliverables/{slug}-search-audit.md`, `deliverables/screenshots/` | Live browser re-test against `{domain}` right now — site behavior (WAF configs, layout) can change since capture |
| 10 | Social Signals | `algolia-intel-social` | `09b-social-signals.*` | Re-scrape for anything posted since the last capture date |
| 11 | News Signals | `algolia-intel-news` | `09c-news-signals.*` | Full re-run — this is a 60-day rolling window, always stale by the time a re-validation happens |
| 12 | Hiring | `algolia-intel-hiring` | `09d-hiring-*.json/md`, `roles-raw.json` | Re-run Scout against the live careers page; cross-check Layer 2 (Gemini-grounded third-party job boards) |
| 13 | Investor Intelligence | `algolia-intel-investor` | `11-investor-intelligence.*` | Public → earnings-call transcripts; private → CEO/founder interview transcripts. Spot-check 1-2 quotes against source |

**Synthesis layer** (regenerate from Phase 1's corrected inputs, same 3-step discipline applies):

| # | Output | Skill | File |
|---|---|---|---|
| 14 | Scoring Matrix | (part of `algolia-audit-report`) | `research/10-scoring-matrix.md` |
| 15 | Business Case / ROI | `algolia-synth-business-case` (`calculate-roi.py`) | `deliverables/{slug}-business-case.md` |
| 16 | Solution Map / Sales Plays / Discovery Qs / Battle Card | `algolia-synth-sales-plays` | `deliverables/{slug}-playbook.md` |
| 17 | AE Brief / Leave-behind / Signal Brief / Book | `algolia-audit-report` | `deliverables/{slug}-ae-precall-brief.md`, `-leave-behind.pdf`, `-strategic-signal-brief.md`, `-book.html` |

## Phase 0 — Preflight (on the VPS, read-only)

0.1. **CONFIRMED (2026-07-09):** `DATABASE_URL` is NOT in `/opt/PRISM/v1/server/.env` (that file
     doesn't exist). The real source is `systemd`'s `EnvironmentFile=` on the
     `prism-chat-proxy.service` unit — confirmed via `systemctl show prism-chat-proxy -p
     EnvironmentFiles` (read-only, prints the path, not the secret): **`/opt/prism-chat-proxy/.env`**.
     Run a read-only query without printing the secret:
     ```bash
     cd /opt/PRISM/v1/server && set -a && source /opt/prism-chat-proxy/.env >/dev/null 2>&1 && set +a && node <script>.mjs
     ```
     (write `<script>.mjs` into that same `server/` dir first, via scp — it needs the `pg` package
     from `node_modules` there; running from `/tmp` throws `ERR_MODULE_NOT_FOUND`.)
0.2. Confirm `accounts`/`audits` row exists for `{domain}` — `completed_at` date tells you how
     stale the current data is.
0.3. Confirm the `${slug}.com` domain-guess convention holds (`fetchAuditData` in
     `chat-proxy.mjs` assumes this) — flag any company whose real domain isn't `.com`.

## Phase 0.5 — Check the known-bugs ledger BEFORE running any module's FACTCHECK step

See the ledger at the bottom of this doc. Any bug marked "OPEN" there will produce a false
result on every company's factcheck pass until it's fixed once, in the script — fix it there,
not per-company.

## Phase 1 — Per-module execution (13 modules, dispatched as subagents, SSH-to-VPS in every prompt)

Each subagent gets the specific module row above plus the mandatory 3-step discipline, and an
explicit instruction to SSH into `chowmes-vps` for every command. Returns a structured result:
`{module, re_verify_findings, factcheck_result: PASS|FAIL + reasons, eval_scores: {...}, status: DONE|NEEDS_REFIX}`.

## Phase 2 — Downstream synthesis (4 outputs, rows 14-17, same 3-step discipline)

Regenerate from Phase 1's corrected inputs — never from the stale pre-revalidation files.

## Phase 3 — Cross-file factcheck gate (23-dimension full pass)

Full re-run across every regenerated deliverable, same rigor as Lululemon's session — produces
`{slug}-factcheck-report.md` v2, `-correction-manifest.md` v2, `FACTCHECK_GATE.md` v2 with a
PROCEED/WARN/BLOCKED verdict. Highest-judgment step — route to Opus (T3), high effort, per
model-economics severity-escalation (a wrong gate verdict here is the expensive failure mode).

## Phase 4 — Postgres correctness, field-by-field (on the VPS)

4.1. `accounts`/`audits` row for `{domain}` — `status='completed'`, `completed_at` reflects the
     re-validation date, not the original stale date.
4.2. Diff `audits.audit_data` (jsonb) against the freshly-regenerated deliverable JSON,
     field-by-field. Any mismatch means the DB write didn't happen or ran against old data —
     fix via a real migration/update, never an ad-hoc unreviewed SSH write (the Gymshark-fix rule
     from tonight applies to every company).
4.3. Check normalized tables (`algolia_case_studies`, `algolia_quotes`, etc.) have real rows
     backing any cited proof points. Populate `module_executions.validation_json`/`output_json`
     for this company's re-run — the ready-made per-module gate hook, currently null for every
     company per `PIPELINE-UNIFICATION-PLAN.md`.

## Phase 5 — Frontend live-fetch + section-by-section render verification (on the VPS)

5.1. Wire `{slug}/index.html`'s boot script with the live-fetch + 401-retry pattern (proven and
     deployed for Lululemon tonight — copy-paste per company, not a redesign each time):
     ```js
     let resp = await fetch('/api/audit-data/{slug}', { credentials: 'same-origin' });
     if (resp.status === 401) {
       // Clerk's handshake refresh lands its fresh cookie on this same 401 — retry once.
       resp = await fetch('/api/audit-data/{slug}', { credentials: 'same-origin' });
     }
     ```
5.2. Backup `{slug}/index.html` on the VPS (`.bak-preLiveFetch-{date}`) before overwriting.
     Deploy, restart `prism-chat-proxy` if the server file changed too.
5.3. With a REAL authenticated session, hit `/api/audit-data/{slug}` and get the actual payload.
5.4. **Section-by-section, not one generic diff** — confirm each of these actually renders from
     the live payload: Executive Summary, Company Snapshot, Financial Profile, Technology Stack,
     Intelligence Signals, Hiring Intelligence, Search Audit Findings (+ screenshots), Solution
     Map, Business Case/ROI, Battle Card, Discovery Questions. A section still showing the OLD
     static values after a successful live fetch is a real bug in that section's render function.
5.5. Confirm via browser console log (`[audit-data] loaded live from database`) the live path
     fired, not the fallback.
5.6. Commit + push `{slug}/index.html`'s change. **Gotcha:** the VPS checkout of the `prism` repo
     has no GitHub push credentials — relay through the local `~/prism` clone:
     ```bash
     # on the VPS: commit as usual, then on the LOCAL machine:
     cd ~/prism && git fetch chowmes-vps:/opt/PRISM/v1 {branch} && git push origin FETCH_HEAD:{branch}
     ```

## Phase 6 — Final report to Arijit (fixed shape, every company)

- Module-by-module status table (13 + 4 synthesis, each with RE-VERIFY/FACTCHECK/EVAL results)
- Phase 3 gate verdict (PROCEED/WARN/BLOCKED + reason)
- Phase 4 Postgres field-diff result
- Phase 5 section-by-section frontend-render result
- Any NEW pipeline-wide bugs found (add to the ledger below immediately)
- Explicit "what has NOT been done" section — no claim of "done" without a written, checked
  result for every item above, not a skim

## Orchestration budget formula (AIOS guardrail #8 — state explicitly before each company's dispatch)

| Stage | Agent count | Tier | Effort |
|---|---|---|---|
| Phase 1 (13 modules × RE-VERIFY+FACTCHECK+EVAL) | 13 | Sonnet (T2) | medium |
| Phase 2 (4 synthesis outputs) | 4 | Sonnet (T2) | medium |
| Phase 3 (cross-file factcheck gate) | 1 | Opus (T3) | high |
| Phase 5 (frontend wiring + verify) | 1 | Sonnet (T2) | medium |
| **Total per company** | **~19** | mostly T2, 1 T3 | — |

Ballpark ~400-500k tokens per company. Running all 19 back-to-back is a real cost — do a few,
confirm the SOP holds up in practice, then decide whether to batch the rest or space them out.

## Standing gotchas (recorded once, so they're never re-discovered per company)

1. **SimilarWeb/traffic is permanent HITL** — never auto-re-capture. Always ask Arijit per-company.
2. **VPS checkouts have no GitHub push credentials** — relay every push through the local
   machine's already-authenticated clone (`~/prism` for the `prism` repo, the local `arijit-skills`
   checkout for that repo).
3. **`DATABASE_URL` lives at `/opt/prism-chat-proxy/.env`** (confirmed via `systemctl show
   prism-chat-proxy -p EnvironmentFiles`) — NOT `/opt/PRISM/v1/server/.env` (that file doesn't
   exist). See Phase 0.1 for the exact query recipe.
4. **Everything in this SOP runs on `chowmes-vps` via SSH** — see the MANDATORY section at the
   top. Every subagent prompt must say so explicitly.
5. **`git push` to `main`/`master` triggers the mandate-guard hook** — needs Arijit's fresh
   explicit yes each time, run as two separate Bash calls (touch the unlock token, THEN push —
   combining them in one command fires the hook before the touch has run).

## Known systemic bugs ledger (living — every new company run may add to this)

| # | Bug | Found on | File | Status |
|---|---|---|---|---|
| 1 | ROI Component 1/5 unanchored-conversion bug (~5x inflation) | Lululemon | `calculate-roi.py` | FIXED (2026-07-09) |
| 2 | `industry_context` filename typo / stray unprefixed duplicate | Lululemon (also seen on Belk) | `generate-audit-data.py` and/or the industry-intel skill's write path | FIXED for Lululemon; **check every company for the stray duplicate — the root cause may not be fully closed** |
| 3 | Data-quality-flag silently dropped (e.g. SimilarWeb degraded-mode label) | Lululemon | report/render pipeline | FIXED (2026-07-09) |
| 4 | `factcheck_mechanical.py:205` reads `search_provider`/`search_vendor`, never canonical `current_vendor` → false BLOCKED | Belk (documented in Belk's own Jul-3 `belk-skill-feedback.md`, never actioned) | `algolia-audit-factcheck/scripts/factcheck_mechanical.py` | FIXED (2026-07-09) — also added a current_vendor-vs-tech_stack_summary self-consistency assert. Deployed on VPS (both the symlinked live path and the repo). Commit staged locally in `/tmp/arijit-skills-push2-20260709`, **not yet pushed to GitHub** — blocked by the mandate-guard/classifier conflict, needs Arijit to run the push himself |
| 5 | Screenshot 50KB size floor has no WAF-degraded exception → false BLOCKED on legitimate WAF-interstitial screenshots | Belk (same source doc) | `algolia-audit-factcheck/scripts/factcheck_mechanical.py` | FIXED (2026-07-09), same commit/push status as #4 |
| 6 | `algolia-intel-partner` never calls Crossbeam MCP tools despite them working | Lululemon | `algolia-intel-partner/SKILL.md` | OPEN — Crossbeam auth confirmed working, skill just doesn't call it |
| 7 | ABX touch content check (`validate-json-schema.py`) looked at `body`/`message`/`email_body` but never `video_script` → false-warned on every valid video/Loom touch | Belk (same source doc) | `algolia-search-audit/scripts/validate-json-schema.py` | FIXED (2026-07-09), same commit/push status as #4. Applied to BOTH the repo copy and the live (non-symlinked) `~/.claude/skills/algolia-search-audit` copy on VPS — this skill is explicitly not symlinked, needed a manual second apply |

*Add new rows here the moment a company's re-validation surfaces something new — don't let bug
#7 wait for a "final report" to get written down.*
