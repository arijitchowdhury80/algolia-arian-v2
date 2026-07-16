# PRISM Finishing Build Plan — the Fable-5 loop package

**Written:** 2026-07-12, by Claude Sonnet 5, after live VPS + GitHub + local ground-truth verification (not from stale docs). **Status:** DRAFT — awaiting Arijit's sign-off before handoff to Fable 5.

**Why this doc exists:** the 2026-07-06 `docs/PRISM-V2/` package was handed off toward Fable 5 but never fully executed — some of it (role doors, landing-page builder) shipped same-day, then all attention moved to the Belk/Dell/Lululemon audit-revalidation effort (2026-07-09/10) and the V2 architecture work (Hermes removal, executioner rebuild, chat-as-operator) never started. This doc supersedes `06-v2-execution-map.md` / `08-fable5-handoff-prompt.md` / `09-fable5-autonomous-build.md` as the current source of truth — those docs contain real design value (reused below) but their "what's built" status is six days stale and in two places wrong.

---

## 0. Ground truth (verified live, 2026-07-12 — not doc-derived)

| Area | Real state |
|---|---|
| **Hermes/Cassandra** | Still running in prod. Two `nousresearch/hermes-agent` containers live on the VPS. Zero Claude Agent SDK code anywhere (`grep` confirmed). |
| **Orchestration** | A real controller exists and is live: systemd `prism-runner.service` → `/opt/prism-executor/run-audit.sh` → one `claude -p` per audit **phase** (not per skill). No per-module fact-check/QA gate — factcheck is a manual final phase. |
| **V2 role doors** | AE, BDR, Marketer, plus an IA A/B prototype — all four exist as real code, live on `prism2.chowmes.com` (Basic Auth). Built in one push 2026-07-06, untouched for 6 days since — including while the Belk/Lululemon Postgres payloads they read were being corrected underneath them. **Unverified against current data.** |
| **Landing-page builder** | Real, working, zero-dependency (`marketer/render-landing.mjs` + template). Dell and Nike are rendered. Belk/Lululemon are not. No Figma/Jahia wiring exists anywhere (Jahia MCP not installed). |
| **Skills** | `~/.claude/skills/algolia-*` (local, 36) vs `arijit-skills` GitHub repo (canonical, 42 incl. non-algolia) — 99% in sync, zero automated sync mechanism. Two known drifts (§6.5). |
| **Verification pipeline** | No automated per-module gate anywhere. Only a JSON-schema validator (`validate-json-schema.py`) + pytest gate tests + a manually-invoked factcheck skill at the end. The 5-stage Verification Pipeline design (mechanical → factcheck → adversarial panel → quality → legal gate) from `06-v2-execution-map.md` §gap-8 is doc-only, never built. |
| **Live security gap** (found this session, unrelated to everything above) | `POST /api/chat` on `prism.chowmes.com` is unauthenticated — dispatches before the auth gate in `chat-proxy.mjs`. Anyone who knows/guesses a slug gets grounded chat answers with no login. **Fix immediately, independent of this plan's sequencing.** |
| **Multi-tenancy design** | A decision-grade doc exists (`docs/plans/multi-tenancy-architecture.md`, 2026-07-02) but is written assuming Hermes/Cassandra stays as the shared daemon. Needs a rewrite pass once Hermes is removed (data-isolation + auth + queue design carry over; the "one shared Hermes daemon" section does not). Also flags a **never-run empirical test**: whether the Claude subscription's pooled rate limit sustains 3+ concurrent `claude -p` audits — this gates any real concurrency number and has been open since 07-02. |

---

## 1. Locked decisions (this session, 2026-07-12)

| # | Decision | Reasoning |
|---|---|---|
| E1 | **Executioner = upgrade `prism-runner.py`**, not a Claude Agent SDK rewrite. Build it behind a clean `dispatch(skill) → result` / `gate(result) → pass\|fail\|retry` interface so an SDK migration later is additive, not a rewrite. | The SDK's real benefits (native hooks, unified executioner+chat framework) only pay off once Track D/F actually need them. Stacking an unproven, never-POC'd framework onto a full Hermes removal + Figma/Jahia integration + full productization in one loop is the overreach that causes stalls. Ship the proven pattern now; keep the door open. |
| H1 | **Full Hermes/Cassandra rip-and-replace, this pass.** Not staged. | Arijit's explicit call. Real risk: live chat on `prism.chowmes.com` can break mid-build — mitigated by §4's sequencing (new executioner proven on a non-prod path before Hermes is pulled) and a rollback plan (§7). |
| L1 | **Build the real Figma → Jahia integration**, not just the static-template reuse. | Arijit's explicit call. Real risk: Jahia MCP isn't installed, Figma today is "wireframe-only" per prior research — this is greenfield, not a small lift. Scoped explicitly in Track F below with its own research spike. |
| S1 | **Scope = Tracks A–H, full productization.** | Arijit's explicit call — this is now a sellable-product build, not just an internal-tool finish. |
| SEC1 | **Patch the unauthenticated `/api/chat` hole immediately**, ahead of and independent of the rest of this plan. | Live prod security gap, unrelated to sequencing above. |
| E2 | **LLM calls are scoped to synthesis + judgment only, never to mechanical work — and every synthesis/judgment call must emit schema-constrained structured output (forced JSON via tool-use, validated against a Pydantic model at the call site), not free-form prose that a downstream step tries to parse.** | Arijit's explicit call, 2026-07-13, in response to reviewing Phase 2's goal-card. Reasoning: "software, not a Claude experience" doesn't mean removing LLM calls — most of what skills do (writing prose synthesis, fact-checking a claim against a source, scoring quality, adversarial refutation) is irreducibly LLM judgment, not mechanizable into deterministic Python. What CAN and must change is where "LLM randomness" is allowed to leak into the pipeline: constraining every judgment call to a fixed schema at generation time removes format drift as a failure mode entirely, instead of catching it after the fact in the Mechanical Validator. This is CLAUDE.md cardinal rule #7 ("Pydantic on every boundary") applied specifically to LLM output, not just data handoffs between modules. |

**Carried forward, unchanged, from `06-v2-execution-map.md` §1:** L3 (Postgres+pgvector), L5 (6 agent roles + 5-stage verification pipeline design), L6 (AE/BDR/Marketer in scope, Sales Leader deferred), L8 (SPA template = design-system source of truth), L10 (multi-tenant shared-tables + tenant_id + RLS, first-pass shape), L13 (Spryker/Amplience/Contentful/Cloudinary as the domain-swap set).

**Still genuinely open — Fable 5 must surface these, not invent them (§8):** auth provider for multi-tenant (D3), pricing/metering model (D6), product name (D10), and the two Discovery-OS ambiguities (D5 — gating rule; the archetype-field overload).

---

## 2. The anti-handwaving Verification Pipeline (build this before/alongside Track C — it's the answer to your biggest concern)

This is the direct fix for "Claude handwaves, doesn't finish modules, fabricates data, skips factcheck." It must be **code that enforces itself**, not a skill Claude remembers to invoke.

**Structured-output enforcement (E2, applies to every stage below that calls an LLM — this is a generation-time constraint, not just a post-hoc check):** stages 2, 3, and 4 don't ask the model to "write a fact-check report" or "score this module" in prose. Each defines a Pydantic schema for its verdict shape (e.g. `FactCheckVerdict{claim: str, source_url: str, verdict: Literal["verified","unverified","contradicted"], confidence: float}`) and forces the LLM call through tool-use/structured-output so the model can only fill those fields — it cannot drift into a different format, skip a required field, or return free text where a literal/enum is required. The Mechanical Validator (stage 1) still runs after, but its job shifts from "parse whatever the LLM wrote and hope it's checkable" to "confirm the already-schema-valid output also passes content rules (URLs resolve, citations present)." Skills' *synthesis* outputs (the actual audit report prose, deck copy, etc.) are the one exception — those are meant to be prose for a human reader — but even there, structural elements (citation tags, required sections, scores) are schema-constrained fields embedded in an otherwise-free document, not left to the model's formatting instincts.

**5 stages, run automatically after every module, wired into the upgraded `prism-runner.py`'s `gate()` function — no module's output is accepted until it passes:**

1. **Mechanical Validator** (pure script, zero LLM calls) — schema validation, every citation URL resolves, every `[FACT]` tag has a source, required fields present. This already exists as `validate-json-schema.py` — extend it to run automatically per-module instead of being invoked manually.
2. **Fact-Check Agent** (existing `algolia-audit-factcheck` skill) — verify claims against cited sources, quote-verbatim check, cross-file consistency. Already exists; the fix is *automatic per-module invocation*, plus converting its verdict output to the schema-constrained shape above — not a new skill.
3. **Adversarial Verifier Panel** (new) — 3 independent agents, different lens each, run in parallel, **none sees the others' verdicts**: Numbers Auditor (every stat traces to a cited source), Quote Auditor (verbatim, not paraphrased), Skeptic (actively tries to refute — job is to find any unsupported claim). Default-to-strip-on-doubt: consensus required to KEEP a claim, not to reject one. Each verifier's verdict is schema-constrained (pass/fail + reason + the specific claim it's judging), so consensus-counting is a code-level tally over structured fields, not a re-read of 3 paragraphs of prose.
4. **Quality/Completeness Agent** (existing `algolia-audit-eval` skill) — depth, coverage, instruction-adherence. Lower stakes than fabrication (a "good enough" check, not a "true" check) — but per the 2026-07-03 findings, this skill **currently never runs at all** in the live pipeline. Wiring it in is itself a real fix, not just a nice-to-have. Its score output also converts to a schema-constrained shape (per-dimension numeric scores + rationale), not a prose review.
5. **Final Legal/Liability Gate** — runs once on the fully-assembled deliverable, after 1–4 pass per-module. Cross-file consistency check across all deliverable files. "Would this survive a lawyer's review before reaching a prospect."

**Model tier:** stages 1/2/4 = Sonnet (bulk work, per the routing table). **Stage 3 (adversarial panel) + stage 5 (legal gate) = Opus** — severity escalates a tier, per standing policy.

**Enforcement mechanism (concrete, not aspirational):** `prism-runner.py`'s per-skill dispatch loop calls `gate(skill_output)` immediately after each skill's subprocess exits, *before* dispatching the next skill. `gate()` returns `PASS` or `BLOCK` with itemized reasons written to the DB (`module_executions` table, already exists). On `BLOCK`: re-dispatch that one skill (not the whole audit) up to N retries, then mark `NEEDS_HUMAN` with the specific skill + reason — never silently proceed with unvalidated output.

**Definition of done for this section specifically:**
- A deliberately-injected bad output (a fabricated stat, a broken citation) gets caught and blocks progression before the next skill dispatches — demonstrated live, not asserted.
- `module_executions` shows one row per skill with a real verdict, for every skill in a real audit run.
- `algolia-audit-eval` actually executes and its score is recorded — verified by checking the DB, not by reading a claim that it ran.
- **E2 check:** every stage-2/3/4 LLM call is demonstrated to reject/retry on a malformed-schema response (e.g. force one deliberately, confirm the harness catches it before it reaches `gate()`'s content logic) — proving the constraint is enforced at the call site, not just documented as an intention.

---

## 3. Definition of Done / Test Plan — applies to every track below

No track is "done" on Fable 5's say-so. Every track's completion claim must show:

1. **Verification command output**, not a description of what was run. (`ruff check . && ruff format --check . && mypy src/ --strict && pytest -v` for Python; `ui-validator` + Playwright screenshot at 1280px/375px for UI; the actual `gate()` verdict for pipeline changes.)
2. **Done-means-live**: the real served surface (`prism2.chowmes.com`, or the relevant endpoint) checked *after* the final change, not before it. "Changed, not yet verified" is the only allowed status otherwise.
3. **A before/after artifact** where the claim is "this is now different/fixed" — a screenshot diff, a DB row diff, a curl response diff. Not a narrative claim.

**Global success criteria for the whole plan:** a reviewer can open `prism2.chowmes.com`, use each of the 3 role cockpits + a working chat-as-operator, watch a real audit run with visible per-module gate verdicts, generate a Belk and a Lululemon landing page through the real pipeline, and see zero fabricated data anywhere — with Hermes fully removed from the stack.

**Global failure criteria (any one of these = the run failed, regardless of what else shipped):** any module's output reaches a rep-facing surface without passing the Verification Pipeline; any screen is indistinguishable from V1 (the §2 "new-experience" test from `09-fable5-autonomous-build.md` still applies); Hermes is left partially removed (some traffic still routes through it, undocumented); a "done" claim exists anywhere without the verification command output attached.

---

## 4. Execution model — 6 phases, one Fable-5 goal each, hard review gate between phases

**Decided 2026-07-12: this is NOT a single autonomous run.** The 2026-07-06 attempt at exactly that framing (`09-fable5-autonomous-build.md`'s "run this loop yourself, don't stop unless a Mandate Boundary" model) is the same shape of ask that produced a half-finished, silently-diverged result — some tracks shipped, the highest-risk ones (Hermes removal, executioner) never started, and nobody caught it until this session's recon, days later. This plan's tracks also mix genuinely irreversible steps (Hermes container removal, prod cutover) with genuine unknown-unknowns (Figma/Jahia — unconfirmed what exists; the concurrency ceiling — untested since 07-02). Compounding all of that in one unsupervised loop means a wrong turn isn't caught until the end, when it's expensive to unwind.

**Rule: each phase below is issued to Fable 5 as its own goal, with its own definition of done. Fable 5 stops at the end of the phase and reports. Arijit reviews. The next phase's prompt is issued only after that review — never chained automatically.**

```
PHASE 1 ──► PHASE 2 ──► PHASE 3 ──► PHASE 3.5 ──► PHASE 4 ──► PHASE 5 ──► PHASE 6
Foundation   Executioner+ Landing     The Notebook     Modular      Multi-      Prod-
(SEC0+A+B)   Verification  pages (L)  (Track I,      rearch (E)   tenancy (F) readiness+
             +Hermes                  notebook.chowmes.                       GTM (H)
             removal (G+C)            com — added
                                       2026-07-13)
   │              │            │           │             │            │           │
   ▼              ▼            ▼           ▼             ▼            ▼           ▼
[REVIEW GATE]  [REVIEW GATE] [REVIEW GATE][REVIEW GATE] [REVIEW GATE][REVIEW GATE][ship]
```

**Why Phase 1 = SEC0+A+B merged, not 3 separate phases:** the auth patch (SEC0) and the door/design-system re-verify (A+B) are both low-risk, non-irreversible, don't depend on each other, and don't block or get blocked by anything in Phase 2+. No reason to burn a separate review gate on two safe, fast checks — merge them, keep the gate for what actually needs it (Phase 2 onward, where irreversible/unknown-unknown work starts).

### Phase-by-phase tracks

## PHASE 1 — Foundation (SEC0 + A + B)
**Goal handed to Fable 5:** patch the live auth hole, then confirm the 3 existing role doors are correct against current data, then reconcile the design-system tokens. **Review gate before Phase 2:** Arijit confirms all 3 DoDs below are met with evidence, and personally spot-checks at least one door live.

**SEC0 result (2026-07-13, verified live):** Step 0 re-verify found the hole ALREADY FIXED — `handleChat()` in the current `chat-proxy.mjs` (branch `feat/prism-vps-hosting`) calls `requireAuth()` as its first line. Confirmed live: `curl -X POST https://prism.chowmes.com/api/chat` (no session) → `401`. Fixed somewhere in the 07-09/10 auth-hardening commits, before this plan existed. No patch needed — this is exactly why Step 0 was added; patching a non-existent hole would have been wasted (and risky) work. SEC0 CLOSED.

**Track A result (2026-07-13, verified live):** Reality diverged from the planned "9 pairs" (3 doors × 3 accounts) matrix, recorded as found rather than forced:
- **AE** (Belk, Dell, Lululemon — all 3): all render clean, zero console errors, real cited data, honest empty slots. **Real bug found + fixed:** `ae/build-ae-data.py` hardcoded `"scale": 5` with no source lookup — the one fabricated field in a script whose own docstring bans fabrication — which made Belk's real 5.3 score display as an impossible "5.3/5". Confirmed true scale is 10 via `algolia-audit-report` SKILL.md's scoring convention (0-10, e.g. "0/10 — keyword-only") before picking the fix. Same bug, different mechanism, in `marketer/door.html` (hardcoded `/5` directly in JS). Fixed both (commit `3061d2f` on `prism-v2`), regenerated all 3 AE JSON files via the corrected script, verified `scale: 10` live on Belk/Dell/Lululemon + Marketer's Dell view. Bonus: the regeneration also picked up Belk's already-corrected data from the 07-10 revalidation (fabricated "Digital Merchandise manager" finding is gone, replaced with the real corrected note).
- **BDR**: not a per-account selector like AE — one shared cross-account signal-ranked queue (10 different companies: La Banque Postale, Home Depot México, Oriental Trading, DSW, Savage X Fenty, Nike, L.L.Bean, Brooks Running, PetSmart, British Airways — not Belk/Dell/Lululemon). Renders clean, transparent scoring formula shown in the page itself, honest "not yet generated for this account" states instead of fabricated battle cards for the 2 accounts missing one.
- **Marketer**: only has data for Dell today (score now correctly 3.6/10). No Belk/Lululemon marketer views exist — no account switcher even offers them. Expected, not a Phase 1 gap — generating those is Phase 3's landing-page work.

**Track B result (2026-07-13, verified live):** Re-verified before acting — all 5 of `07-design-system.md`'s documented inconsistencies belong to the OLD V1 SPA template and never propagated into the V2 doors, which independently built their own clean, WCAG-AA-checked token+button system (the `:disabled` state the doc claimed missing was already built, consistently, in all 3 doors). Real finding instead: the 3 doors had byte-for-byte-identical-at-creation inline `<style>` blocks with live drift already starting (AE's `overflow-wrap:anywhere` bug fix, BDR's more detailed version of the same fix, Marketer missing it; BDR's extra `.btn-ghost-white` variant). Extracted `shared/prism-tokens.css` + `shared/prism-components.css` (commit `40d169c`), retrofitted all 3 doors to link them instead of inlining duplicates. Verified live: all 3 doors + both shared CSS files return 200, links wired correctly, zero visual regression.

**Process lesson caught mid-phase, recorded (feedback-class, not just this incident):** regenerating `ae/data/*.json` via `build-ae-data.py` directly on the VPS (for the scale fix) produced an uncommitted local change. The next deploy's `git reset --hard origin/prism-v2` (routine, for the CSS-extraction pull) silently reverted it back to the broken `scale:5` state — caught immediately because Track A's own live-verification discipline re-checked after the CSS push, not because anyone remembered the earlier fix was fragile. Fixed by committing the regenerated JSON files (`ae0fb66`). **Prevention heuristic:** any script that regenerates deploy-served files on the VPS must have its output committed in the same breath as the fix — an uncommitted VPS-side-effect is invisible until the next unrelated `git reset --hard` erases it, and it will erase it, not might.

**PHASE 1 — COMPLETE**, pending Arijit's review-gate sign-off per §4 before Phase 2 starts.

### Track SEC0 — Patch the live auth hole (do this first, standalone)
- **Step 0 — re-verify before patching.** The hole was documented 2026-07-02, but `feat/prism-vps-hosting` (the branch that deploys this file) has since shipped an auth-related commit (07-09/10: "API auth 401-not-redirect + client retry"). Read the CURRENT `handleChat()` in `chat-proxy.mjs` on that branch and reproduce the unauthenticated-POST hole live (`curl -X POST` with no session) before assuming the 07-02 description still matches the code. If it's already fixed, or fixed differently, report that — don't patch a hole that's gone.
- Add `checkAuth(req)` + `authorizeReport(auth, reportSlug)` inside `handleChat()` in `chat-proxy.mjs`, before the upstream Hermes/executioner fetch — same two functions the page-serving path already uses.
- Also tighten/remove the dev-mode "fail open if Clerk unconfigured" behavior for prod; apply the same slug-scoped check to `/reports/data/<slug>-audit-data.json` sidecars.
- **DoD:** `curl -s -o /dev/null -w "%{http_code}" -X POST https://prism.chowmes.com/api/chat -d '{"slug":"<real-slug>","message":"test"}'` returns 401 without a valid session, 200 with one. Verified live, post-change.
- **Failure:** any code path where an unauthenticated POST still returns report-grounded content.

### Track A — Re-verify + finish the role doors
The doors exist but haven't been touched in 6 days while the underlying data was being corrected. Do not build anything new on top until this is confirmed.
1. For each of AE/BDR/Marketer doors, load them live against Belk and Lululemon's **current, corrected** `audit_data` (post-revalidation) and diff against what the door renders. Fix any field-name mismatches or stale-schema assumptions (the render-audit.ts bugs already flagged in `SESSION.md` — `lift_traffic_json()` wrong rank-field keys, demographics gender-fallback overwriting age-bucket data — are exactly this failure class; fix them here, not just for Belk).
2. Finish the stubbed pieces per `06-v2-execution-map.md` §3: Marketer's ABM Brief artifact, disabled download buttons; the general "render everywhere a Finding shows" verification-badge primitive (currently one hard-coded instance).
3. Re-confirm the 3 IA working assumptions before extending AE/BDR further (role switcher = toggle not ACL; Marketer door = review surface in front of the Figma/Jahia pipeline, not a second builder — though note L1 above now makes that pipeline real, not aspirational; existing 5-tab SPA = deep-link target, not rebuilt per role).
- **DoD:** all 3 doors render correctly against live, current DB data for at least Belk + Lululemon + one more account; `ui-validator` pass; Playwright-verified at 1280px/375px on the actually-served `prism2.chowmes.com` surface (not local files).
- **Failure:** any door showing a JS error, a blank slot where real data exists, or data that doesn't match the current Postgres `audit_data` row.

### Track B — Design-system reconciliation
- **Step 0 — re-verify before reconciling.** `07-design-system.md`'s 4 documented inconsistencies were captured 2026-07-06; `prism-v2` and V1's rendering both shipped changes since (07-09/10 "JS-rendering/data-resync fixes"). Re-read the current `index-template.html` + `algolia-brand.css` and confirm each of the 4 inconsistencies still exists as described before building the reconciliation around it — some may have already shifted or been fixed incidentally.
Package `07-design-system.md`'s extracted tokens into `prism-tokens.css` + `prism-components.css`, fixing the source inconsistencies confirmed still present in Step 0 (originally documented as: two `--shadow` roundings, two content max-widths, JS-gauge greens ≠ CSS `--green`, missing `:disabled` states). Retrofit all 3 doors onto these files.
- **DoD:** one tokens file, imported by every V2 screen; no visual regression on the 3 doors (screenshot diff).

## PHASE 2 — Executioner + Verification Pipeline + Hermes removal
**Goal handed to Fable 5:** build the anti-handwaving gate, upgrade the executioner behind it, prove parity on a non-prod path, only then remove Hermes. **This is the highest-risk phase — irreversible steps live here.** **Review gate before Phase 3:** Arijit explicitly approves the actual Hermes container removal (per §6 mandate boundary) before it happens, and independently verifies live chat still works post-cutover.

**Status (2026-07-13): APPROVED to start. Arijit signed off on Phase 1 and pre-approved the Hermes-removal action inside this phase (still confirm at the actual `docker rm` step, per §6, but no separate ask needed to begin the phase).**

### Phase 2 goal-card (input / output / DoD / loop / kill-condition — the Phase-1 pattern, applied)

**Input (what must exist/be readable before starting):**
- `docs/plans/2026-07-03-per-skill-subagent-architecture.md` (the executioner spec Track C builds from) — read in full.
- Current `prism-runner.py` + `run-audit.sh` on the VPS (`/opt/prism-executor/`) — read live, not from memory of what they used to do.
- `validate-json-schema.py` (existing mechanical validator) and the `module_executions` DB table schema — confirm both exist as described in §2 before building on top of them.
- `algolia-audit-factcheck` and `algolia-audit-eval` skills — confirm current invocation surface (CLI args, expected input shape).
- List of all ~16 skills in the current audit pipeline + which one (only `algolia-audit-browser`) needs a live browser client, per `2026-07-03-per-skill-subagent-architecture.md` §2.4 — re-verify this table against the CURRENT skill list, don't assume it's unchanged.
- Hermes/Cassandra container inventory on VPS (`docker ps -a`, compose files) — confirm the "two `nousresearch/hermes-agent` containers" ground-truth from §0 is still accurate before planning removal.

**Output (artifacts that must exist at the end):**
1. `gate()` function wired into an upgraded `prism-runner.py`, implementing all 5 verification stages from §2 (mechanical → factcheck → adversarial panel → quality → legal gate), writing one verdict row per skill to `module_executions`. **Per E2: stages 2/3/4's LLM calls are schema-constrained (forced tool-use JSON against a Pydantic model), not free-form prose parsed after the fact.** Define the actual Pydantic verdict models (`FactCheckVerdict`, `AdversarialVerdict`, `QualityScore`) as part of this output, not left implicit.
2. Per-skill subprocess dispatch (`dispatch(skill) → result`) replacing the current per-phase dispatch — N isolated `claude -p` processes per audit, not one.
3. MCP config stripped from all skills except `algolia-audit-browser` (direct Playwright client for that one).
4. A lightweight embedded chat agent (plain `claude -p` + Postgres/pgvector grounding) running on the non-prod path (`prism2.chowmes.com`'s basic-auth surface), replacing Hermes/Cassandra's chat-facing role there first.
5. A real audit run completed end-to-end through the new executioner on the non-prod path, with a side-by-side parity comparison against a Hermes-run audit (same company or a close proxy).
6. Hermes/Cassandra containers archived (image + compose file backed up to a named location) BEFORE removal, then removed from the VPS — only after step 5's parity is confirmed AND Arijit's explicit go at the actual `docker rm` step.
7. `prism.chowmes.com` prod traffic cut over to the new executioner + chat agent, verified live post-cutover.

**Definition of done (concrete, testable — not narrative):**
- A deliberately-injected bad output (fabricated stat or broken citation) is blocked by `gate()` before the next skill dispatches — demonstrated live with the actual `BLOCK` verdict shown, not asserted.
- `ps aux` on the VPS during a real audit run shows N separate skill subprocesses, not one long-lived `claude -p`.
- `docker ps -a` shows zero MCP processes for the 15 skills that don't need one.
- `module_executions` has one row per skill per real audit run, each with a real verdict (not all-PASS-by-default).
- `algolia-audit-eval`'s score is present in the DB for a real run (previously never ran at all — this is the regression test for that specific gap).
- `docker ps -a` confirms Hermes containers gone from the VPS.
- `curl`/browser-verified: chat on `prism.chowmes.com` answers a real question grounded in Postgres, post-cutover, with no Hermes process in the path.
- Rollback path (§7) verified to exist — archived image + compose file present at a named path — BEFORE the `docker rm`, not assumed after.

**Loop structure:** per-skill retry-until-clean on `gate()` BLOCK (re-dispatch that one skill, not the whole audit, up to N retries — N=3 suggested, confirm with Arijit if it needs to differ). Track G (pipeline) and Track C (executioner) build in parallel since Track C's dispatch loop calls Track G's `gate()` — but the non-prod parity run (output #5) is a hard sequence point: it must pass before output #6 (Hermes removal) starts.

**Kill condition:** if the same skill fails `gate()` 3 times in a row on the SAME check, stop retrying that skill, mark `NEEDS_HUMAN` with the specific skill + reason in the DB, and report — do not grind silently or fall back to accepting unvalidated output. If the non-prod parity run (output #5) fails to match the Hermes-run baseline on any factual field, stop before touching Hermes — that's a gate failure on the whole cutover, not a per-skill retry.

**Mandate-boundary re-confirmation inside this phase (per §6, standing rule — restated here so it's not missed mid-execution):** the actual `docker rm`/`rm -rf /opt/hermes-agent` step (output #6) still needs Arijit to say go at that specific moment, even though the phase itself and the removal-in-principle are both pre-approved (2026-07-13). Everything else in this phase (goal-card outputs 1-5, 7) can proceed without a further check-in.

### Phase 2 critique patches (2026-07-13 — 10 failure modes found by adversarial self-review, all folded in before execution)

The goal-card above passed initial review but was then deliberately attacked for hand-waving/downstream-headache risk. 10 real gaps found; all patched here as binding additions to the goal-card, not optional nice-to-haves:

1. **Adversarial-panel cost blowup, unsized.** 16 skills × 3 voters (stage 3) × up to 3 retries = up to 144 extra LLM calls per audit, mostly Opus. **Patch:** only run the stage-3 adversarial panel on claims the mechanical validator (stage 1) or fact-check agent (stage 2) flagged as risky — not every claim in every skill. State the real expected call-count/cost estimate for one full audit run before building, not a guess.
2. **No fixed interface contract between subagents building Track G (gate) and Track C (dispatch).** Prose-only specs → mismatched interfaces when built in parallel (matches the known failure class in `feedback-workflow-shared-repo-verify`). **Patch:** write the exact contract FIRST — file path (`prism_platform/pipeline/gate.py`), function signature (`gate(skill_output: SkillOutput) -> Verdict`), the `Verdict`/`FactCheckVerdict`/`AdversarialVerdict`/`QualityScore` Pydantic schemas — as its own artifact, both subagents read it, neither invents their own shape.
3. **Retry loop can't distinguish flaky-worth-retrying from genuinely-unfixable.** Retrying 3x on "source doesn't exist" gets the same failure 3x, wastes cost, delays escalation every time. **Patch:** classify BLOCK reasons — retry-worthy (schema/format drift, transient) vs not (data genuinely absent, contradicted-by-source) — route the second class straight to `NEEDS_HUMAN` on first occurrence.
4. **"Same check" (the 3-strike kill condition) is undefined at the claim level.** 3 different claims failing stage 2 on 3 different attempts never trips 3-strikes if counted per-claim — could retry indefinitely. **Patch:** "same check" = same STAGE, not same specific claim/reason. 3 BLOCKs from the same stage (any reason) trips `NEEDS_HUMAN`.
5. **Parity run can't separate "pipeline broke" from "the world changed between runs."** News/social data drifts between a Hermes-run baseline and a fresh non-prod run — a content diff on live-changing fields will look like a false regression. **Patch:** parity run uses frozen/cached input data for both runs where possible, or diffs only structurally-stable fields (schema shape, citation presence, score-within-tolerance) — not raw scraped content.
6. **Non-prod (`prism2.chowmes.com`, Basic-Auth) ≠ prod (`prism.chowmes.com`, Clerk) auth surface.** "Proven on non-prod" proves chat-agent logic, not its Clerk session/slug-authorization integration — exactly the bug class SEC0 just fixed. **Patch:** add an explicit Clerk-auth integration test as its own pre-cutover step, not assumed covered by the parity run.
7. **MCP-strip subagents have nothing real to check against if `gate()` isn't built/deployed yet** — falls back to eyeballing, the exact hand-waving this phase exists to kill. **Patch:** hard sequence dependency — `gate()` must be built, tested, and callable BEFORE any MCP-strip subagent starts. State this ordering explicitly; don't let Track G and the MCP-strip work run blind-parallel.
8. **Stage 5 (legal/liability gate) has no rubric** — "would this survive a lawyer's review" is the most hand-wavy line in the whole design, ironic given E2 exists to kill hand-waving elsewhere. **Patch:** either write a real checklist/schema for this stage now, or explicitly mark it manual-Arijit-review-only until a rubric exists — never ship it as "automated" when it's actually vibes.
9. **Chat agent's "Postgres/pgvector grounding" names no embedding model, chunking strategy, or similarity threshold** — asserting "grounded" without a mechanism is the same failure class this whole plan exists to eliminate. **Patch:** name the embedding model + retrieval params explicitly before a subagent is dispatched to build it, or scope that naming as its own research subtask first, not folded silently into "build the chat agent."
10. **VPS blast radius understated** — the recon/deploy subagent's DB migration + systemd swap runs on a host also serving `umami`, `cios-postgres`, `ac2-lab-backend`, `scout` (unrelated live services). **Patch:** recon subagent's DoD must explicitly confirm those unrelated services are unaffected post-deploy (still `Up`/healthy in `docker ps -a`), not just check PRISM's own surface.

### Phase 2 dispatch prompt (verbatim, consolidated — this is the actual text to hand the executor, all 10 patches verified present)

> Build Phase 2 of `docs/plans/2026-07-12-prism-finishing-build-plan.md`. Read the PHASE 2 section + goal-card + "Phase 2 critique patches" (10 items) in full, plus `docs/plans/2026-07-03-per-skill-subagent-architecture.md` — its MCP table is stale (no Apify in this picture; Crossbeam is live/verified per `reference-crossbeam-mcp-live.md`, strip it same as the others, not an open question).
>
> **Sub-agent driven, always** — no inline main-loop work. Sequence: recon → interface contract → gate-build → (only then, patch #7) dispatch-rewrite + MCP-strip in parallel → chat-agent → parity-run → STOP/report → (fresh yes) → Hermes removal → cutover.
>
> **Patch #2:** before any parallel dispatch, write the fixed interface contract as its own artifact — `gate()`'s exact file path/signature + the `Verdict`/`FactCheckVerdict`/`AdversarialVerdict`/`QualityScore` Pydantic schemas. Every subagent reads this contract; none invents its own shape.
>
> **Patch #1 (cost control):** stage-3 adversarial panel runs ONLY on claims stages 1/2 already flagged as risky, not every claim in every skill. State a real call-count/cost estimate for one full audit run, sized against 16 skills × up-to-3-voters × up-to-3-retries, before building — not a guess.
>
> **Patch #3 (retry discipline):** classify `gate()` BLOCK reasons before retrying — schema/format drift retries up to 3x; "data genuinely absent/contradicted-by-source" skips straight to `NEEDS_HUMAN` on first occurrence, no wasted retries.
>
> **Patch #4 (kill condition):** "same check" for the 3-strike rule = same STAGE (1-5), not same specific claim/reason — 3 BLOCKs from one stage, any reason, trips `NEEDS_HUMAN`.
>
> **Patch #5 (parity run):** diff against a Hermes-run baseline using frozen/cached input data where possible, or diff only structurally-stable fields (schema shape, citation presence, score-within-tolerance) — not raw live-changing content (news/social drift between runs is not a regression).
>
> **Patch #6 (auth):** non-prod (`prism2.chowmes.com`, Basic-Auth) proves chat-agent logic, not Clerk integration. Add an explicit Clerk session/slug-authorization test as its own pre-cutover step before flipping `prism.chowmes.com`.
>
> **Patch #7 (sequencing):** `gate()` must be built, tested, and callable before any MCP-strip subagent starts — MCP-strip subagents check each skill's output against the real gate, not eyeballing.
>
> **Patch #8 (legal gate):** Stage 5 ships as manual-Arijit-review-only until a real rubric exists — do not mark it automated with no rubric behind it.
>
> **Patch #9 (grounding):** name the embedding model, chunking strategy, and similarity threshold explicitly before building the chat agent — "grounded via pgvector" with no named mechanism is not acceptable.
>
> **Patch #10 (blast radius):** recon subagent's DoD includes confirming `umami`, `cios-postgres`, `ac2-lab-backend`, `scout` stay `Up`/healthy in `docker ps -a` post-deploy, not just PRISM's own surface.
>
> **Hard requirements, every deliverable:** Read-Receipt (`protocol-read-receipt.md`) before any wire-protocol/external-API code. `ruff check . && ruff format --check . && mypy src/ --strict && pytest -v` output shown, not described, before anything is marked done. Report done/deferred/blocked per numbered deliverable. `docker rm`/Hermes removal needs a fresh explicit yes from Arijit at that exact step — nothing else in this phase does.

### Track G — Verification Pipeline
See §2 in full, plus the 10 patches above (especially #1, #2, #3, #4, #7, #8 — all directly modify Track G's build). Build this alongside Track C, since the pipeline's `gate()` calls are what the new executioner's dispatch loop calls — but per patch #7, `gate()` must be usable before MCP-strip work starts, so it is not fully symmetric parallelism.

### Track C — Executioner rebuild + Hermes rip-and-replace
1. **Upgrade `prism-runner.py`** to dispatch one `claude -p --skill X` subprocess per skill (not one process per phase), each behind the `dispatch()`/`gate()` interface from E1 and the fixed contract from patch #2. Per-skill isolated context, own log, own timeout/retry, own DB row.
2. **Strip MCP per-skill, sequenced after `gate()` exists (patch #7)** — re-verify the current MCP-per-skill table live first (the 07-03 doc's Apify reference is stale/wrong — no Apify in this picture; Crossbeam is live/verified per `reference-crossbeam-mcp-live.md`, not an open question). Only `algolia-audit-browser` needs a browser client (direct Playwright, no MCP wrapper); confirm the rest live, don't assume the doc's list is current. Per-skill verify loop (patch: strip → re-run that skill standalone → confirm valid output against `gate()` → next skill; not a batch strip-then-test-all).
3. **Build the embedded chat agent** (item 1's actual ask): a lightweight process that invokes `claude -p` directly, grounded against Postgres/pgvector — name the embedding model + chunking/retrieval params explicitly (patch #9) before building. Plain, not SDK-based, consistent with E1. Add the Clerk-auth integration test (patch #6) before this is considered cutover-ready.
4. **Remove Hermes**: stop + remove both `hermes-prism` and `hermes` containers, remove `/opt/chowmes-prism`, `/opt/hermes-agent` (archive first, don't delete blind — this is a destructive op, confirm with Arijit before the actual `docker rm`/`rm -rf` per the standing destructive-ops rule).
5. **Cutover order** (de-risks H1's "no staging" call): stand up the new executioner + chat agent on a non-prod path first (e.g. `prism2.chowmes.com`'s existing basic-auth surface), run a real audit end-to-end through it, verify parity with a Hermes-run audit using patch #5's frozen-input-diff method, *then* flip `prism.chowmes.com` traffic and pull Hermes. This is sequencing inside a "full rip-and-replace," not a staged rollout of the decision itself.
- **DoD:** `ps aux` on the VPS shows N separate skill subprocesses during a real audit run, not one long `claude -p`; zero MCP processes for skills that don't need them; Hermes containers gone (`docker ps -a` confirms); unrelated services (`umami`, `cios-postgres`, `ac2-lab-backend`, `scout`) still healthy post-deploy (patch #10); chat on `prism.chowmes.com` answers a real question grounded in Postgres, verified live post-cutover, through the Clerk auth path (patch #6).
- **Failure:** any point where Hermes is "removed" but still receiving traffic, or the new chat agent returns an ungrounded/fabricated answer.

## PHASE 3 — Landing pages
**Goal handed to Fable 5:** ship Belk + Lululemon via the existing static builder first (fast, low-risk floor), then run the Figma/Jahia spike as its own checkpoint, then build the integration only once the spike's findings are reviewed. **Review gate before Phase 4:** Arijit reviews the spike's findings before the integration build starts (the spike may change scope significantly), and confirms both landing pages live-verified with zero fabricated data.

### Track L — Landing-page pipeline: Belk + Lululemon + real Figma→Jahia integration
1. **Extend the existing pipeline first** (don't rebuild `render-landing.mjs` — reuse it): write `belk.landing.json` / `lululemon.landing.json` from the corrected Postgres `audit_data` (same pattern as `build-ae-data.py`), run the renderer, get `belk.html` / `lululemon.html` alongside the existing Dell/Nike ones. This is the fast, low-risk floor — do this even if the Figma/Jahia integration below takes longer.
2. **Figma → Jahia integration research spike (Track F/L1 proper):** confirm what actually exists — is there a real Figma file this maps to, or is "wireframe-only" (per `2026-07-02-cassandra-airtight-pipeline-goal.md`) still accurate? Does a Jahia API/MCP exist to install, or does "push" mean a manual content-entry step? This must be answered with live evidence before building — do not assume a Figma API connection exists.
3. **Build the integration** once the spike answers what's real: likely shape = Figma design tokens/components extracted once (not per-audit) into the same design-system tokens from Track B, PRISM's renderer fills them with per-account data (extending `render-landing.mjs`'s pattern), output pushed to Jahia via whatever real mechanism the spike found (API, MCP, or a documented manual step if no API exists — say so, don't invent one).
- **DoD:** Belk and Lululemon landing pages exist and render correctly (screenshot-verified) using real, current audit data — zero fabricated proof-stats (the `01-design-thinking.md` rule: missing field renders empty, never guessed). The Figma→Jahia path is either working end-to-end with a live-verified push, or explicitly reported as blocked with the specific missing piece (e.g. "no Jahia API access token provisioned") — not silently skipped.
- **Failure:** a landing page with any invented number, or a "Figma integration done" claim with no live push demonstrated.

## PHASE 3.5 — The Notebook (external single-source-of-truth site)
**Added 2026-07-13, by Arijit — not in the original 6-phase model, inserted between Phase 3 and Phase 4.** **Goal handed to Fable 5:** build `notebook.chowmes.com/PRISM` — the external-facing counterpart to the internal vault. Where the vault is PRISM's internal single source of truth (Arijit + Claude, all raw detail), the Notebook is the **external** single source of truth: a due-diligence-grade site an outside technical reviewer (e.g. an Algolia CSO evaluating whether to bring PRISM in) can read to fully understand the project — objectives, technical design, security posture, architecture, technology choices, decisions made and why, current execution status — without needing anyone in the room. **Review gate before Phase 4:** Arijit reviews the live site end-to-end as if he were that outside reviewer, confirms no internal-only/sensitive content leaked through, and approves the actual DNS/subdomain go-live (mandate boundary — new public URL, per §6).

### Track I — The Notebook

**Input:**
- Vault `Projects/PRISM/` in full — `index.md`, `log.md`, `tasks.md`, `wiki/decisions/*`, `wiki/log.md`, `wiki/hot.md` — the internal source of truth this externalizes.
- `docs/PRISM-V2/*`, `docs/plans/2026-07-12-prism-finishing-build-plan.md` (this doc), `docs/decisions/*`, `docs/specs/*` — the PIP-repo-side documentation.
- Existing frontend patterns to reuse: `prism-hub`'s static-site approach (vanilla JS/CSS, no build step — per standing decision, [[feedback-port-react-to-vanilla]]) and the V2 doors' shared token/component CSS from Phase 1 Track B.
- A content classification pass BEFORE anything is published: every vault/docs item must be tagged externally-safe vs internal-only (credentials, VPS paths, live security-gap details, unresolved-decision debates, anything Arijit wouldn't want an outside evaluator reading) — this classification is itself a deliverable, not a build detail to skip.

**Output:**
1. A content sync/render pipeline: reads vault + docs sources, applies the safe/internal classification filter, renders to static pages — NOT a live read-through of the raw vault (raw vault stays internal-only, ever).
2. Site structure covering: Project Objective, Technical Design, Architecture (with the actual diagrams/schemas, not just prose), Security Documentation (posture + how known gaps were handled — factually, not defensively), Technology Stack + why each choice was made, Decision Log (the real ADR-style history, e.g. E1/H1/L1/S1 from §1), Execution Status (what phase we're actually on, what's done vs not — this must stay in sync with reality, not go stale like `06`/`08`/`09` did).
3. `notebook.chowmes.com` DNS/subdomain provisioned and the site deployed there.
4. A defined update mechanism so the Notebook doesn't rot: either re-run the sync pipeline on a schedule/on-demand, or wire it into the existing `record-knowledge`/`project-tracker` skill flow so vault updates propagate — decide which, don't leave it as a one-time snapshot.

**Definition of done:**
- `notebook.chowmes.com/PRISM` is live, publicly reachable, and Arijit personally walks it end-to-end as an outside reviewer would and confirms nothing internal-only leaked (no credentials, no VPS paths/IPs, no raw unresolved-debate content).
- Every major section (objective/design/security/architecture/tech/decisions/execution) has real content, not a placeholder — sourced from and traceable back to the vault/docs, not freshly invented prose.
- The execution-status section matches this plan doc's actual phase state at publish time (cross-checked, not assumed).
- The update mechanism is demonstrated once: a real vault/docs change propagates to the live site through the defined path.

**Loop structure:** per-section build-then-classify-then-render — don't publish any section until its content has passed the safe/internal filter. Iterate section by section rather than one big draft-then-scrub pass (a scrub pass after full drafting is exactly the shape of mistake that leaks something).

**Kill condition:** if the classification pass surfaces genuine ambiguity about whether something is safe to publish (e.g. does documenting a *fixed* historical security gap count as safe, or does describing it at all create risk) — stop and ask Arijit on that specific item, don't guess toward "publish" by default. Default-to-withhold on doubt, same posture as the Verification Pipeline's "default-to-strip-on-doubt" rule in §2.

**Mandate boundary (per §6, restated):** `notebook.chowmes.com` is a new public subdomain — needs Arijit's explicit yes before DNS/hosting provisioning goes live, and again before the "no internal content leaked" review passes and it's actually announced/linked anywhere.

## PHASE 4 — Modular rearchitecture
**Goal handed to Fable 5:** define and build the module boundary contract + recipe format on top of Phase 2's executioner. **Review gate before Phase 5:** Arijit confirms a real recipe run (fewer than the full module set) works live.

### Track E — Modular lego rearchitecture
Per `06-v2-execution-map.md` §5: define the module boundary contract (input/output schema + its own exit gate), the recipe format, confirm Researcher/Auditor/Synthesizer agent groupings against the actual skill list. Depends on Track C's executioner being real.
- **DoD:** an operator can hand-pick a subset of modules for an audit (a "recipe"), and the executioner runs exactly that subset — demonstrated on a real run with fewer than the full module set.

## PHASE 5 — Multi-tenancy + domain-pack
**Goal handed to Fable 5:** run the concurrency test FIRST (it's a decision input, not busywork to fit in later), rewrite the multi-tenancy doc's Hermes-specific section, design the domain-pack interface. **Review gate before Phase 6:** Arijit sees the real concurrency number and makes the cost/architecture call it implies (2nd subscription vs API overflow, if needed) before Phase 6's commercial work assumes any specific scale.

### Track F — Multi-tenancy + domain-pack productization
1. **Rewrite `multi-tenancy-architecture.md`'s Axis (a)** for the post-Hermes world — the "one shared Hermes daemon" model is moot; the new chat-as-operator agent needs its own tenancy/session model. Data isolation (tenant_id column + app-layer filtering, RLS as the triggered upgrade), auth (Clerk + ACL table), and the queue design (bounded worker pool, Postgres state) carry over largely unchanged — reuse, don't re-derive.
2. **Run the concurrency test that's been open since 2026-07-02**: fire 2–3 concurrent `claude -p` audit sessions on the real subscription, measure throttling. This number gates the worker-pool depth and the real cost model — do not finalize either without it.
3. **Domain-pack interface** (Track F proper): define the swappable unit that replaces `algolia-search-audit` + Algolia sales angles, designed toward the concrete swap set (Spryker, Amplience, Contentful, Cloudinary).
- **DoD:** the concurrency test has a real number, not an assumption; a tenant_id-scoped query returns only that tenant's data even when another tenant's data exists in the same tables (a real cross-tenant leak test, not just a design review).

## PHASE 6 — Production readiness + GTM + pricing/metering
**Goal handed to Fable 5:** security/deployment topology, observability, GTM positioning, pricing/metering decided and instrumented. **Final gate:** Arijit signs off before this is called a sellable beta.

### Track H — Production readiness + GTM + pricing/metering
Security/deployment topology, observability, SLAs, GTM positioning ("Prospect Research Operating System"), pricing + metering unit decided and instrumented from day one. Research-heavy — start early, build after E/F land.
- **DoD:** a pricing/metering unit is decided and at least one usage event is actually recorded against it (not just designed).

---

## 5. Guardrails for the Fable-5 loop (non-negotiable)

- **Evidence before assertions.** Every done/fixed/verified claim ships with the command output or the live-checked artifact. No exceptions.
- **Done-means-live.** Check the real served surface after the final change, not before.
- **No silent scope-narrowing.** Report every item done/deferred/blocked explicitly — a dropped item that isn't flagged is a false-green.
- **Zero fabrication, full tolerance for omission.** An empty slot beats a guessed value, always. SimilarWeb stays permanent HITL — never assume a script fetches it.
- **Reuse-first.** Track A/L above are explicit reuse tracks, not rebuilds — enumerate what exists before writing new code.
- **Loop-until-done, not first-pass-accept.** Build → gate (§2/§3) → fix → re-verify. A track isn't done because it ran once.
- **Orchestration budget stated up front.** Any fan-out of >2 agents states agent count, tier, rough token estimate before dispatch.

## 6. Mandate boundaries — stop and get Arijit's explicit yes

- Deploying to `prism.chowmes.com` prod, or the actual Hermes-container removal (`docker rm`, `rm -rf /opt/hermes-agent` etc.) — confirm immediately before this specific destructive step, even though H1 already authorizes the rip-and-replace in principle.
- Auth/visibility/network-exposure changes (new public URL, new open port, Jahia credentials/access provisioning).
- Any of the still-open decisions in §1 (D3 auth provider, D5 gating-rule ambiguity, D6 pricing/metering, D10 product name) — decide with best judgment on everything else, but these need a human call.
- If the Track F concurrency test shows the subscription can't sustain the needed parallelism — that's a real cost/architecture decision (2nd subscription vs API overflow), not Fable 5's to make alone.

## 7. Rollback plan (for the Hermes cutover specifically)
Before removing Hermes containers: confirm the new executioner + chat agent have run a real audit end-to-end on the non-prod path (§Track C step 5) and the images/configs for `hermes-prism` and `hermes` are archived (image tag + compose file backed up), not just deleted. If the new chat agent fails post-cutover, the archived containers + compose file are the rollback path — verify this path exists before pulling the trigger, don't assume it.

## 8. Fable-5 handoff — read-first list
1. This document (supersedes `06`/`08`/`09` on "what's built").
2. `docs/PRISM-V2/07-design-system.md` (design language, still accurate).
3. `docs/PRISM-V2/05-role-driven-ia.md` (role IA, still accurate).
4. `docs/research/Discovery-OS-v1.md` §9 (Finding/Behavior/Feedback/Branch schema, still accurate).
5. `docs/plans/2026-07-03-per-skill-subagent-architecture.md` (the executioner upgrade this plan's Track C builds — read in full, it's the detailed spec).
6. `docs/plans/multi-tenancy-architecture.md` (reuse for Track F, minus the Hermes-daemon-specific section per §4 Track F.1).
7. `docs/sop/AUDIT-REVALIDATION-SOP.md` (context on why 07-06→07-10 diverged from this plan — not part of this build, but explains recent history).

**First move:** Phase 1 only (SEC0 + A + B). Stop and report at Phase 1's review gate — do not proceed into Phase 2 without Arijit's explicit go-ahead on the next phase's prompt. Each subsequent phase is issued as its own fresh goal after review, per §4.

---

## 9. Phase 2 — skill logic review (separate effort, not in this loop)

Deferred per Arijit's framing: a full pass over every one of the ~36-42 `algolia-*` skills' internal logic — checking for incorrect assumptions, illogical steps, or scope creep baked into a skill's own instructions (distinct from the pipeline/orchestration issues this plan fixes). Scope this as its own plan once Tracks A–D above are live; do not fold it into the Fable-5 loop above. Placeholder only — no content authored yet.
