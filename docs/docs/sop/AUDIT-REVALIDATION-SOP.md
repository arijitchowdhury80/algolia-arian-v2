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
| 2 | `industry_context` filename typo / stray unprefixed duplicate | Lululemon (also seen on Belk) | `generate-audit-data.py` and/or the industry-intel skill's write path | FIXED for Lululemon AND Belk (2026-07-09) — Belk's stray `industry-intel.md/.json` confirmed byte-identical to the correct `06-industry-intel.*` (dead fossil, not divergent), moved to `.bak-confirmedDeadDuplicate-20260709`, confirmed via direct file check. Also fixed on Belk: the "10% apparel-search-adoption" benchmark stat was over-confidently labeled `confidence: FACT, verified: true` when the figure isn't confirmable on Baymard's public (paywalled) page — downgraded to `ESTIMATE`/`false`, confirmed via direct JSON read. Root cause (why the duplicate gets written in the first place) still OPEN — check every future company for the same fossil |
| 3 | Data-quality-flag silently dropped (e.g. SimilarWeb degraded-mode label) | Lululemon | report/render pipeline | FIXED (2026-07-09) |
| 4 | `factcheck_mechanical.py:205` reads `search_provider`/`search_vendor`, never canonical `current_vendor` → false BLOCKED | Belk (documented in Belk's own Jul-3 `belk-skill-feedback.md`, never actioned) | `algolia-audit-factcheck/scripts/factcheck_mechanical.py` | FIXED (2026-07-09) — also added a current_vendor-vs-tech_stack_summary self-consistency assert. Deployed on VPS (both the symlinked live path and the repo). Commit staged locally in `/tmp/arijit-skills-push2-20260709`, **not yet pushed to GitHub** — blocked by the mandate-guard/classifier conflict, needs Arijit to run the push himself |
| 5 | Screenshot 50KB size floor has no WAF-degraded exception → false BLOCKED on legitimate WAF-interstitial screenshots | Belk (same source doc) | `algolia-audit-factcheck/scripts/factcheck_mechanical.py` | FIXED (2026-07-09), same commit/push status as #4 |
| 6 | `algolia-intel-partner` never calls Crossbeam MCP tools despite them working | Lululemon | `algolia-intel-partner/SKILL.md` | OPEN — Crossbeam auth confirmed working, skill just doesn't call it |
| 7 | ABX touch content check (`validate-json-schema.py`) looked at `body`/`message`/`email_body` but never `video_script` → false-warned on every valid video/Loom touch | Belk (same source doc) | `algolia-search-audit/scripts/validate-json-schema.py` | FIXED (2026-07-09), same commit/push status as #4. Applied to BOTH the repo copy and the live (non-symlinked) `~/.claude/skills/algolia-search-audit` copy on VPS — this skill is explicitly not symlinked, needed a manual second apply |
| 8 | `algolia-intel-company`'s Gemini-grounded enrichment tags every fact `[FACT — grounded search via Gemini, ...]` (a method label) but persists no real per-fact source URL — the only 2 URLs in the whole file are opaque Vertex AI grounding-redirect links, not durable/checkable citations. Facts were independently verified accurate (no fabrication), but the artifact structurally cannot pass a mechanical FACTCHECK gate that requires a real citation per claim. Same "label claims sourced, artifact doesn't deliver it" shape as bug #2 | Belk (Module 1 re-validation, 2026-07-09) | `algolia-intel-company` skill's enrichment/collection step | OPEN — needs the skill to persist a real per-fact source URL, not just a label |
| 9 | Belk's traffic module (`03-traffic-data.json`) is not a SimilarWeb-PRO HITL capture at all — it's 100% empty output from the dead `collect-traffic.py` SimilarWeb-API-v4 script hitting 401 on all 15 endpoints. `degraded_mode`/`data_quality` flags ARE present and correct (this module correctly labels its own failure, unlike Lululemon's dropped-flag bug) — but there is zero usable traffic data for Belk, meaning any downstream ROI/business-case component that depends on traffic has nothing real to draw from | Belk (Module 3 re-validation, 2026-07-09) | `algolia-intel-traffic` — this specific company's capture, not necessarily a script bug | OPEN — needs Arijit's call: does Belk get a first-time real SimilarWeb-PRO HITL capture, or does downstream synthesis explicitly mark traffic-dependent ROI components as N/A? |

| 10 | Ledger bug #6 confirmed with real, concrete magnitude (not just theoretical): a live Crossbeam pull for Belk found an active NAMED open deal ("Belk-2026-NOV-New Business-Elevate Ecomm v8.5", owner Matthew Panning) and CRM-confirmed customer relationships that appear NOWHERE in `07-partner-intel.md`. The file's own "B1 High-Confidence SI Relationships" (Google Cloud, Constructor, Criteo, Manhattan Associates, Oracle) don't match ANY real Crossbeam overlap/recommendation data — the file's confidence framing is inverted (its "high-confidence" tier is unverified web-search, while the real CRM facts are entirely absent) | Belk (Module 7 re-validation, 2026-07-09) | `algolia-intel-partner/SKILL.md` (same skill as bug #6) | FIXED for Belk's file (2026-07-09) — rewritten leading with real Crossbeam facts, old web-search speculation demoted to a clearly-labeled unconfirmed tier. **Data-quality note surfaced during the fix**: on re-verification, the commercetools "confirmed customer" claim did NOT reconfirm live (checked 2 ways) — the rewrite explicitly flags this as an unresolved discrepancy rather than silently keeping or dropping it; Contentstack customer relationship DID reconfirm. Skill-level fix (wiring Crossbeam calls into `algolia-intel-partner` itself) still OPEN for future companies |
| 11 | `algolia-intel-social`'s report-writer sorts signals into narrative score-buckets (🔴9-10/🟡7-8/🟢6) independently of the numeric `urgency_score` field — on Belk, 3 signals scored 5-6 were placed in the "7-8" bucket and 1 signal scored 7 was placed in the "score 6" bucket. Self-consistency violation of the skill's own rubric, not a one-off | Belk (Module 10 re-validation, 2026-07-09) | `algolia-intel-social` skill's section-writer | FIXED for Belk's file (2026-07-09) — buckets now match urgency_score exactly (widened the "🟢" bucket header to "5-6" rather than force-fitting a score-5 signal, plus fixed 2 additional inline "Urgency: X/10" mismatches found during the fix, independently re-verified by re-reading the live file post-write). Skill-level fix (deriving bucket FROM score at generation time, not narratively) still OPEN for future companies |
| 12 | **Most severe finding of the Belk run.** `algolia-intel-news` collected 10 articles for the WRONG entity entirely — "Belk Center," an unrelated Tuscaloosa community/senior facility, not Belk Inc. the department-store retailer (a company-name-collision bug in the search query, not staleness). 3 of those 10 articles also carry fabricated `https://www.example.com` placeholder URLs presented as live sources — an independent no-fabrication FAIL on top of the wrong-entity FAIL. Zero of Belk's real retailer news for the period is represented | Belk (Module 11 re-validation, 2026-07-09) | `algolia-intel-news` skill's search-query construction (needs entity disambiguation, e.g. exclude "Belk Center"/"Tuscaloosa", require "department store"/"belk.com") | FIXED for Belk's file (2026-07-09) — rebuilt with 5 real, live-verified Belk-retailer articles, zero wrong-entity/placeholder content (grep-confirmed). Correctly EXCLUDED a real Belk data-breach story (DragonForce ransomware) it found because it dated to May 2025, outside the 60-day window — good discipline, not over-included. Skill-level fix (entity-disambiguation in the search query itself) still OPEN for future companies |
| 13 | `algolia-intel-competitors`'s Gemini-grounded search produced 2 concrete numeric errors that slipped through ungated: Nordstrom's revenue cited as $5.603B (actual FY2025 $15.02B per SEC 8-K, off ~3x, no traceable source) and Huckberry's "9.3x Revenue Per Session / 2.5-3.0% conversion" cited as an Algolia case-study fact when those numbers actually belong to a separate Stylitics-partnership case study — a cross-vendor metric misattribution, not a typo. Distinct failure mode from the citation-format bugs (#2/#8/#10): here the number itself is wrong/misattributed, not just uncitable | Belk (Module 4 re-validation, 2026-07-09) | `algolia-intel-competitors` skill — most claims cite only "[FACT — grounded Gemini search]" with no traceable article URL, which is why these 2 errors weren't caught upstream | FIXED for Belk's file (2026-07-09) — Nordstrom corrected to $15.02B, cited to the real SEC 8-K exhibit URL (verified via SEC EDGAR full-text search + cross-source corroboration); Huckberry's Stylitics-misattributed numbers replaced with the real Algolia-sourced "+9.4% revenue increase from AI Personalization"; PetSmart URL fixed. Both files re-read post-write to confirm. Skill-level fix (a numeric spot-check step before citing) still OPEN for future companies |
| 14 | Self-caught regression in this session's own bug-#4 fix: the new `current_vendor`-vs-`tech_stack_summary` self-consistency assert false-positived when `current_vendor` carries a parenthetical qualifier (e.g. "Constructor.io (displacement target)") — the vendor name and its annotation aren't one contiguous substring even though the vendor is clearly named in the summary | Belk (Module 2 re-validation, 2026-07-09) — found within hours of deploying bug #4's fix | `algolia-audit-factcheck/scripts/factcheck_mechanical.py` | FIXED (2026-07-09) — strip trailing parenthetical from `current_vendor` before the substring check. Verified against Belk's real audit-data.json: tech_stack now PASSes. Same commit/push status as #4 (staged locally, not yet pushed) |
| 15 | `algolia-intel-financial-private`'s defined 6-source waterfall (ecdb/PitchBook/Crunchbase, LinkedIn headcount WebFetch, CEO interviews, trade press, Inc5000/Deloitte Fast500, job-posting volume) was only ~2-3 sources actually executed on Belk — LinkedIn headcount was substituted with Forbes/Owler/PitchBook aggregators (no real LinkedIn WebFetch), Inc5000/Deloitte was substituted with an NRF Top 100 check, job-posting-volume proxy was skipped entirely despite hiring-signals data existing elsewhere in the same audit. Headline revenue number still checked out independently, but the substitutions were undisclosed as deviations from spec. `revenue_sources`/`sources_succeeded`/`sources_failed` bookkeeping was also internally inconsistent (a source in neither list) | Belk (Module 8 re-validation, 2026-07-09) | `algolia-intel-financial-private` skill / `collect-financials.py` | FIXED for Belk's file (2026-07-09) — all 3 missing sources actually run (real LinkedIn headcount check: 12,831 employees, consistent with existing estimate; real Inc5000/Deloitte Fast500 check: genuine negative, documented with reasoning rather than left blank; job-posting-volume derived from the audit's own hiring-signals data). Headline revenue number unchanged (already correct). `revenue_sources`/`sources_succeeded`/`sources_failed` bookkeeping now internally consistent (6/6 sources each in exactly one list). Skill-level fix (systemic substitution pattern across other companies) still OPEN — not yet checked beyond Belk |
| 16 | **Tied most-severe finding of the Belk run, alongside #12.** `algolia-intel-hiring`'s Layer 2 Gemini-grounded fallback fabricated 2 of 3 flagged roles outright — `careers.belk.com` (the domain in all 3 cited job URLs) doesn't exist (NXDOMAIN), Belk's real careers site is `belk.wd1.myworkdayjobs.com`; querying the real Workday API for both flagged Tier-3 roles ("Digital Merchandise", "Loyalty Analytics") returns 0 results, and their cited job IDs are far below the live ID range — consistent with never having existed, not with having closed. The 3rd role's Monster.com URL 404s. All 3 were mislabeled "✅ HIGH — Direct URL, job ID" confidence by the skill's own Data Confidence Table — this is textbook ungrounded LLM hallucination presenting itself as verified | Belk (Module 12 re-validation, 2026-07-09) | `algolia-intel-hiring` skill's Layer 2 (Gemini-grounded fallback, used because Layer 1/Scout was disabled at capture time — now fixed) | OPEN — needs a live-URL-resolution gate before Layer 2 output can ever be labeled "HIGH confidence"; likely systemic (any company could hit the same hallucination mode), not Belk-specific |

*Add new rows here the moment a company's re-validation surfaces something new — don't let the
next bug wait for a "final report" to get written down.*
