# Task 6-local report — v3 pipeline end-to-end, run for real, locally

Status: **DONE** (local correctness proof) — VPS parity run remains separately blocked on SSH.

3-line summary: Built `docs/workspace/phase2-executioner/local_parity_harness.py` and ran it for
real against real local Postgres 17, the real `claude` CLI, and 2 real complete audit workspaces
(jbl, lululemon). 9 real `module_executions` DB rows now exist, covering all 5 gate stages and
every terminal status (`completed`/`blocked`/`needs_human`). The gate caught 4 distinct real
problems it was never told about (2 organic, 1 injected, 1 self-healed-then-passed), proving it
is not a rubber stamp, and the `SelfHealLoop` demonstrably retried a real skill to a real CLEAN
pass and separately fatal-short-circuited a real UNFIXABLE contradiction after exactly 1 attempt
(patch #3, live).

Report path: `docs/workspace/phase2-executioner/task-6-local-report.md`
Harness: `docs/workspace/phase2-executioner/local_parity_harness.py` (kept — see "Commit" below)

---

## What this proves vs. does not prove (read this first, per the brief)

**Proves (this report):**
- `gate.gate()`'s 5-stage pipeline runs end-to-end with **zero stubs** — real `factcheck_mechanical.py`
  subprocess (stage 1), real schema-constrained `claude -p` calls for stages 2/3/4
  (`llm_stages.py`), real `claims.extract_claims` claim extraction, real `db_write.write_module_execution_row`
  INSERT/upsert against a real Postgres — for the first time since Tasks 3/4a/5b/5c built these
  pieces in isolation against fakes/stubs.
- The gate is not a rubber stamp: it organically found 3 real, previously-undetected problems in
  already-published audit content (not synthetic test fixtures), plus caught 1 deliberately
  injected fabrication.
- `self_heal.SelfHealLoop` really retries (3 real attempts, real LLM score variance 5.0→6-ish→7.0,
  eventual real CLEAN) and really fatal-short-circuits on an `UNFIXABLE` block (patch #3 — 1
  attempt, not 3, when the gate itself flags the block as unfixable).
- A real interface gap between `gate.py`'s default mechanical-command builder and
  `claims.py`/`llm_stages.py`'s shared assumption about what `SkillOutput.audit_dir` means (see
  Findings §1) — caught by wiring these modules together for the first time, exactly what Task 6
  exists to surface.

**Does NOT prove (explicitly, per the brief):**
- Nothing about the VPS deploy step, whether `prism_platform`'s deps install cleanly there, or the
  real `run-audit.sh --skill` dispatch mechanism on the VPS — SSH to the VPS is still down and
  untested by this report.
- Nothing about `ps aux` showing N separate OS processes on the VPS — this is a local proof of the
  pipeline LOGIC, not the VPS's process model.
- This is a LOCAL correctness proof with real external calls (LLM + DB + subprocess), not the VPS
  parity run itself. That run still needs to happen once SSH is back.

---

## Real local infra confirmed before use

```
$ brew services list | grep postgres
postgresql@17 started         arijitchowdhury ~/Library/LaunchAgents/homebrew.mxcl.postgresql@17.plist

$ psql -U prism -d prism -h localhost -c '\dt'
 public | module_executions    | table | prism      <- and 13 others, 14 total, matches brief
 public | report_chunks        | table | prism

$ which claude
/Users/arijitchowdhury/.local/bin/claude   <- resolves on PATH, matches config.py's default DATABASE_URL exactly
```

## The chain read in full before wiring anything

`gate.py`, `verdicts.py`, `self_heal.py`, `db_write.py`, `executioner.py`, `llm_stages.py`,
`claims.py`, plus `task-{3,4a,5b,5c}-report.md`. Confirmed the exact hand-off shapes each task's
report claimed: `gate.gate(skill_output, mechanical_cmd=, factcheck_fn=, adversarial_fn=,
quality_fn=)`, `make_batch_factcheck_fn(claims_fn, claude_cli_fn=)`, `extract_claims`'s 4-of-16
skill coverage table.

---

## Findings from wiring these pieces together for the first time

### 1. `SkillOutput.audit_dir` — a real, previously-invisible interface mismatch

`gate.py`'s DEFAULT `_default_mechanical_cmd` builds `factcheck_mechanical.py --audit-dir
<SkillOutput.audit_dir> --company <company_name>`. `factcheck_mechanical.py` computes
`company_dir = audit_dir/company` from that — i.e. it requires `audit_dir` to be the **parent** of
the company directory (confirmed live: pointing `--audit-dir` at the company dir itself produced
`"ERROR: company dir not found: .../lululemon/lululemon"`).

But `claims.py`'s extractors and `llm_stages.py`'s prompts both read `SkillOutput.audit_dir` **as
the company directory itself** — e.g. `claims.py`: `audit_dir / "research" / "01-company-context.json"`,
and `llm_stages.py`'s prompts: `f"Audit directory (read files here for evidence): {skill_output.audit_dir}"`.

Both cannot be true of the same field on the same `SkillOutput` value at once. This was invisible
in every prior task because none of them called `gate()`, `claims.py`, and `llm_stages.py` together
against a real filesystem path — each was tested against fakes that never exercised the real
path-join. The harness resolves it by (a) setting `audit_dir` to the company dir, satisfying 2 of
the 3 downstream consumers, and (b) building an **explicit** `mechanical_cmd` using
`factcheck_mechanical.py`'s other documented form — `--audit-data <path-to-audit-data.json>` — which
needs no parent/company split at all (confirmed live, clean run against jbl). This is a real,
unresolved ambiguity in `gate.py`'s default wiring that whoever wires `engine=v3` into production
must resolve — either change `_default_mechanical_cmd` to use the `--audit-data` form (globbing via
`claims.py`'s own `_find_audit_data_json` pattern), or split `SkillOutput` into two path fields.
Flagging, not silently fixing `gate.py` itself (out of this task's scope to change already-shipped,
tested modules without sign-off).

### 2. `llm_stages.py`'s default 120s subprocess timeout is too short for real audit workspaces

Task 5b's own live-proof report noted `quality_fn` took 37.4s against a **tiny synthetic fixture**
(`/tmp/llm-stages-live-proof/Acme/`, one thin markdown file). Against a **real, full 16-skill audit
workspace**, the same call — whose prompt explicitly instructs the model to "read this skill's own
SKILL.md instructions and the actual output files it produced in the audit directory" — reliably
took 130-206 seconds and **twice hit `chat_agent._default_claude_cli`'s hard-coded 120s
`subprocess.run(..., timeout=timeout_s)` and raised `subprocess.TimeoutExpired`**, killing the
whole `gate()` call:

```
subprocess.TimeoutExpired: Command '['claude', '-p', 'You are scoring Dimension 3 ...
```//confirmed live, twice — the first attempt at Test 1b (algolia-intel-investor, jbl) and
independently again on Test 4's first `run_pipeline` attempt before the fix.

This is a real, previously-unknown scaling gap between the tiny fixture Task 5b live-tested against
and a real production audit directory. The harness works around it locally by passing
`claude_cli_fn=functools.partial(_default_claude_cli, timeout_s=300)` explicitly into every
`llm_stages` call — **this is a harness-level workaround, not a fix to `llm_stages.py` or
`chat_agent.py`**, called out as a real production gap for whoever wires `engine=v3` for real:
the 120s default should be raised (or made configurable) before this pipeline is trusted against
real audit directories, especially any single call that legitimately reads multiple files.

---

## Real runs (verbatim results), all 9 real DB rows

```
$ psql -U prism -d prism -h localhost -c \
    "SELECT id, domain, module_name, status, duration_ms, completed_at FROM module_executions ORDER BY completed_at;"
```

| # | domain | module_name | status | duration_ms | completed_at |
|---|---|---|---|---|---|
| 1 | lululemon.com | algolia-intel-industry | **blocked** | 82 | 11:22:13 |
| 2 | jbl.com | algolia-intel-industry-INJECTED-BLOCK-TEST | **needs_human** | 28429 | 11:22:59 |
| 3 | jbl.com | algolia-intel-industry | **needs_human** | 205528 | 11:26:36 |
| 4 | jbl.com | algolia-intel-investor | **blocked** | 131759 | 11:32:29 |
| 5 | jbl.com | algolia-intel-techstack | **completed** | 62034 | 11:34:09 |
| 6 | jbl.com | algolia-intel-investor | **blocked** | 0* | 11:36:21 |
| 7 | jbl.com | algolia-intel-investor | **blocked** | 0* | 11:38:52 |
| 8 | jbl.com | algolia-intel-investor | **completed** | 0* | 11:41:15 |
| 9 | jbl.com | algolia-intel-company | **needs_human** | 0* | 11:45:51 |

`*` rows 6-9 (the `SelfHealLoop` run, Test 4) show `duration_ms=0` — a harness cosmetic gap: its
`on_attempt` closure built a placeholder `Attempt(started_at=0.0, finished_at=0.0, ...)` instead of
threading through the loop's real per-attempt monotonic timestamps. The DB rows and their
`validation_json` (the real 5-stage `Verdict`) are still fully real and correct; only the
`duration_ms` column on these 4 rows is a harness artifact, not a pipeline defect. Flagging rather
than silently leaving unexplained.

**Every row is a real INSERT against real local Postgres 17**, verified independently via `SELECT`
after each run (not just trusting the harness's own printed "DB row id" — the table above is a
fresh, direct `psql` query run after all tests completed).

---

## Test 1 (+1b, +1c) — hunting for a clean full-5-stage PASS

The brief asked for one clean PASS and one deliberate BLOCK. Getting the PASS took **three real
attempts** because the first two organically found real, previously-undetected quality problems in
already-published audit content — itself a meaningful finding, not a harness bug:

**1 — `jbl / algolia-intel-industry`** (6 real claims via `claims.extract_claims`): real stage-1
mechanical PASS (`PROCEED`, no blocking reasons), then real stage-2 factcheck genuinely
**BLOCKED** — one of jbl's own industry-intel benchmarks ("68% of shoppers... needs an upgrade") has
`source_url: null, verified: false`, and the LLM correctly classified it `NO_SOURCE` /
`UNSUPPORTED`, additionally citing a related dead-URL finding already on record elsewhere in the
same audit (`factcheck-dim-5-6-results.md`). Real, grounded, correct catch of pre-existing data
quality debt. `block_class=UNFIXABLE` (correct — no retry fixes an absent source).

**1b — `jbl / algolia-intel-investor`** (0 claims, isolates stage 4 quality): stage 1 PASS, stage 2/3
skip (0 claims → 0 calls, confirmed), stage 4 quality genuinely **BLOCKED** at `score=5.0/10.0`
(threshold 7.0) — real, detailed reasoning citing 3 specific `SKILL.md`-mandated steps
(earnings-transcript WebFetch, SEC EDGAR pull, Yahoo Finance MCP) that the skill's real historical
output skipped. `block_class=RETRY_WORTHY`.

**1c — `jbl / algolia-intel-techstack`** (0 claims): stage 1 PASS, stage 2/3 skip, stage 4 quality
**PASS** at `score=8.5/10, 20/21 checks` (real reasoning: correctly credits the graceful
SimilarWeb-key-unset skip, the mandatory `detect-search` oracle run, all merge fields present; docks
1 point for `pages_visited` only covering 3 of the SKILL.md's documented 5 pages). Reaches stage 5
(legal stub, `needs_human_review` — correct, no rubric exists). **`status=pass`, real, all 5 stages
recorded.** DB row `a8567644-c2f9-43d6-a0e8-d93583d85e5c`. This is the clean-PASS proof.

## Test 2 — real, organic stage-1 mechanical BLOCK (no injection needed)

`lululemon / algolia-intel-industry`: `factcheck_mechanical.py` genuinely BLOCKED
(`mechanical_action: "BLOCKED"`) on a real, pre-existing bug in lululemon's published
`audit-data.json` — `tech_stack_summary` claims "blocked by WAF, no detection" while
`search_vendor`/`ecommerce_platform`/`analytics`/`cms`/`frontend`/`cdn_waf` are all populated, a
direct self-contradiction. Zero LLM calls spent (stage 1 short-circuits before `factcheck_fn`/etc.
are ever invoked) — real, cheap, and immediate (82ms). `block_class=RETRY_WORTHY`. DB row
`34468720-a513-4945-ae32-a3bc4bb57dd7`.

## Test 3 — deliberately injected false claim, real stage-2 catch

`jbl / algolia-intel-industry` with mechanical passing clean (confirmed `PROCEED`), and
`factcheck_fn` overridden to feed exactly one hand-written false claim: *"JBL was founded in 1850 in
Antarctica and reported $50 trillion in annual revenue in 2025, making it the single largest company
in human history."* Real `claude -p` call (28.4s) returned:

```json
{"evidence_tier": "AUTHENTIC", "verdict": "CONTRADICTED",
 "citation": "/Users/arijitchowdhury/prism-data/audits/jbl/research/01-company-context.md",
 "reasoning": "Audit's own primary research says JBL founded 1946 in Los Angeles by James B.
 Lansing (FACT, Gemini grounded search), owned by Harman/Samsung, 2024 revenue ~$10.35B
 (financial-profile.md). Claim's 1850/Antarctica founding + $50T revenue directly contradicts
 both facts. No possible support tier -- this is fabrication."}
```

`gate()` returned `stage=2, status=block, block_class=UNFIXABLE` — **this is the brief's core DoD
line, satisfied live**: "a deliberately-injected bad output is blocked before the next skill
dispatches — demonstrated live, not asserted." DB row `ece29823-33ca-4036-8aee-bdfec5ba8802`.

## Test 4 — `SelfHealLoop` over 2 real jbl skills, real gate wiring

Per the brief's guidance, `dispatch_fn` is stubbed `True` (reuses jbl's existing complete research
output rather than re-running the real 16-skill `run-audit.sh --skill` dispatch, which is VPS-only
and explicitly out of scope for this local proof) — `gate_fn` is the **real** wiring: real
subprocess mechanical check + real `claude -p` calls, exactly as production `engine=v3` would call
it, `max_passes=3`.

```
phase=algolia-intel-investor  outcome=clean        attempts=3  escalation=None
phase=algolia-intel-company   outcome=needs_human  attempts=1  escalation=gate FATAL (unfixable)
    after 1 attempts: CONTRADICTED: Crown International is a portfolio brand of this company,
    operating at crownaudio.com. -- Domain crownaudio.com matches, but research file lists Crown
    International as a SIBLING brand under parent Harman International, not a portfolio brand
    owned by JBL (the audited company). JBL and Crown are both Harman subsidiaries/brands at the
    same level -- JBL does not own or operate Crown.
```

Two real, distinct proofs in one run:

1. **Real retry-to-success**: `algolia-intel-investor`'s stage-4 quality score genuinely varied
   across 3 real, independent LLM calls against the identical input (5.0 → blocked → blocked →
   **7.0, exactly at the 7.0 threshold, PASS**) — real LLM judgment noise, not a scripted fixture.
   The loop retried exactly as designed and reached a real `PhaseOutcome.CLEAN` on attempt 3.
2. **Real fatal short-circuit (patch #3), live**: `algolia-intel-company` has a **genuinely new,
   real, previously-undetected data error** — jbl's `portfolio_brands[]` lists "Crown International"
   (crownaudio.com) as a JBL-owned brand, but jbl's own research file states Crown is a **sibling**
   Harman brand, not a JBL subsidiary. The real factcheck LLM caught this contradiction on the
   first attempt, `gate()` returned `block_class=UNFIXABLE`, and `SelfHealLoop` correctly escalated
   to `NEEDS_HUMAN` after exactly **1** attempt, not burning the remaining 2 of `max_passes=3` on a
   failure retrying cannot fix. `run_pipeline` then correctly stopped (never attempted a 3rd skill,
   per its "stop at first NEEDS_HUMAN" contract).

DB rows `14d9e0a4-...`, `208b8a1d-...`, `8320533e-...` (investor attempts 1-3), `008d3527-...`
(company, fatal).

---

## Real cost / call count for what was actually run

- **Real `claude -p` calls**: ~28 across all tests (Test 1: 6 factcheck + adversarial subset + 1
  quality ≈ 8-11; Test 1b/1c: 1-2 quality calls each; Test 3: 1 factcheck; Test 4: 3× quality
  (investor retries) + ~10 factcheck + adversarial subset (company)). Not separately metered for
  $ cost in this sandbox — each call is a normal-sized schema-constrained judgment prompt, same
  order of magnitude Task 5b/5c's own estimates project (~20-70 calls per full 16-skill audit).
- **Real wall-clock time**: individual calls ranged 26s-206s; the full session (all 4 tests, 3
  PASS-hunt retries, and the self-heal run) took roughly 35-40 minutes of real elapsed time,
  dominated by sequential `claude -p` calls (no concurrency in this harness — production `engine=v3`
  would presumably also run these sequentially per skill, per `self_heal.py`'s synchronous design).
- **Real DB writes**: 9 `INSERT`s against local Postgres, one per gate call, all independently
  `SELECT`-verified after the fact (not just the harness's own stdout).

---

## Definition of Done — checked against the brief

- ✅ Real audit workspace, real skill with extractable claims used (not a fresh 16-skill run):
  `~/prism-data/audits/{jbl,lululemon}/`, `algolia-intel-industry`/`-investor`/`-company`/`-techstack`.
- ✅ Real `gate.SkillOutput` built against a real workspace.
- ✅ `gate.gate()` called for real: real `factcheck_mechanical.py` subprocess, real `claude -p` for
  stages 2-4.
- ✅ Persisted via `db_write.write_module_execution_row` against real local Postgres — real
  `INSERT`s, independently verified by `SELECT` (see table above, 9 rows).
- ✅ Full `Verdict` (all 5 stages) printed/logged for every run (see Findings/Tests above).
- ✅ Ran at least twice, once expected-PASS (achieved on the 3rd attempt, `algolia-intel-techstack`,
  score 8.5/10, all 5 stages) and once deliberately-triggered BLOCK (Test 3, injected false claim,
  real stage-2 CONTRADICTED/UNFIXABLE) — **plus 3 additional organic BLOCKs found without any
  injection**, exceeding the DoD's "gate doesn't rubber-stamp" bar.
- ✅ `SelfHealLoop` orchestration attempted over 2 real skills from the same workspace (not all 16):
  real retry-to-CLEAN (investor) and real fatal-short-circuit (company, patch #3 live).

## Concerns / honest caveats

1. **Getting a clean PASS took 3 real attempts**, not because the harness was broken, but because
   the first two real skill outputs genuinely have real, previously-uncaught data-quality problems
   (an unsourced statistic; 3 skipped SKILL.md-mandated sourcing steps). This is evidence the gate
   works, but it also means: **this pipeline, if run against the rest of the already-published
   audit fleet, will likely surface a nontrivial number of real, previously-invisible quality
   issues** — worth planning for before turning `engine=v3` on broadly, not just wiring it.
2. **Findings §1 and §2 above are real gaps in already-shipped, tested modules** (`gate.py`'s
   default mechanical-command builder; `chat_agent._default_claude_cli`'s 120s timeout). Neither
   was fixed in this task — both are flagged for a deliberate, reviewed change, not silently patched
   mid-proof.
3. **No concurrency**: this harness (and, as far as I can tell, `self_heal.py`'s current design)
   runs skills and claims strictly sequentially. A real 16-skill audit's stage-2 factcheck alone
   (~20-70 calls per Task 5c's measured estimate) could take 15-40+ minutes serially. Not a
   correctness gap, but a real production latency consideration for whoever schedules `engine=v3`
   runs.
4. **`duration_ms=0` on Test 4's 4 DB rows** — harness cosmetic gap (placeholder `Attempt` timestamps
   in `on_attempt`, not threading through `SelfHealLoop`'s real per-attempt clock), documented above,
   does not affect the `Verdict`/`validation_json` correctness of those rows.
5. **This remains a LOCAL proof only.** VPS SSH is still down (per the task-6-report this replaces
   waiting on) — the real VPS parity run (confirming `prism_platform` installs cleanly there, the
   real `run-audit.sh --skill` dispatch mechanism, and real per-skill OS processes) has NOT
   happened and is not claimed here.

## Commit

Committing `local_parity_harness.py` (per the brief: "not committed unless it proves useful" — it
proved useful: it found 2 real interface/timeout gaps and produced all 9 real DB rows above) and
this report, on `feat/prism-e2e-cycle` (current branch, not `main`).

## Files

- `/Users/arijitchowdhury/Dropbox/AI-Development/PIP/docs/workspace/phase2-executioner/local_parity_harness.py` (new, kept)
- `/Users/arijitchowdhury/Dropbox/AI-Development/PIP/docs/workspace/phase2-executioner/task-6-local-report.md` (this file)
- No changes to `gate.py`, `executioner.py`, `llm_stages.py`, `claims.py`, `db_write.py`,
  `self_heal.py`, or `chat_agent.py` — Findings §1/§2 above are flagged, not silently patched.

## Status: DONE_WITH_CONCERNS

The v3 pipeline logic (gate → LLM stages → claims → DB write → self-heal) is now proven to run
end-to-end for real, against real infra, and to genuinely catch bad output rather than
rubber-stamping — both organically (3 real, previously-undetected problems) and on-demand (1
injected fabrication). Two real gaps were found and flagged (not fixed): the `SkillOutput.audit_dir`
interface ambiguity between `gate.py` and `claims.py`/`llm_stages.py`, and `llm_stages.py`'s
120s default timeout being too short for real audit workspaces. Neither blocks calling this task
done — both are exactly the kind of first-time-wired-together findings Task 6 was scoped to
surface — but both need a deliberate fix before `engine=v3` is trusted in production. The VPS
parity run itself (dependency install, real `run-audit.sh --skill` dispatch, real OS process
model) is separately and still blocked on SSH access, unrelated to anything in this report.
