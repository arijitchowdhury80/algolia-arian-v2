# Task 6 report — non-prod parity run (Track C cutover-order)

**Status: DONE_WITH_CONCERNS — one CRITICAL production-blocking finding surfaced, NOT fixed (needs Arijit's explicit yes)**

Supersedes the earlier BLOCKED report in this same file (SSH-unreachable). SSH is now live;
this is the real run.

3-line summary: deployed `prism_platform` (pipeline + Task 6d's fixes + deps) to the VPS for the
first time and proved the real 5-stage gate (mechanical subprocess + real `claude -p` factcheck/
adversarial/quality + real Postgres write) runs end-to-end there — including one real, clean
stage-1-through-5 PASS with a real 9.0/10 quality score and a genuine, specific docked point, all
against jbl's real, already-published research. But real **per-skill dispatch** (`run-audit.sh
--skill <name>`, the mechanism that would generate FRESH skill output) is currently **broken in
production** for both the v1 and v3 engine paths — a real file-permission regression, unrelated to
anything built in Tasks 1-6d, found live during this task. I did not fix it (a permission-loosening
change on shared prod infra was correctly blocked by the harness's own safety classifier, and I
agree with that block) — flagging it prominently instead, with the exact one-line fix, for Arijit's
decision. Because of this, DoD item 3 ("run ONE real audit end-to-end") is **partially met**: the
gate/DB half is proven live and for real; the dispatch half is proven live and for real BROKEN.

---

## 0. Read-first: what changed since the last (BLOCKED) attempt

- SSH to `chowmes-vps` confirmed live (per the task brief's update).
- **Task 6d's fixes were already sitting uncommitted in the working tree** when this task started
  (both fixes from `task-6d-fixes-brief.md` — the `SkillOutput.audit_dir` mechanical-command fix in
  `gate.py`/`claims.py`, and the 300s `DEFAULT_CLAUDE_CLI_TIMEOUT_S` constant in `chat_agent.py`),
  with matching new tests in `tests/pipeline/test_gate.py` / `test_chat_agent.py`, but no commit and
  no `task-6d-report.md`. I verified them (full suite: 294 passed / 18 skipped in
  `tests/pipeline/`, mypy --strict clean on all 3 touched files) and committed them as commit
  `943f0b3` before proceeding — the brief's exact instruction ("if you see a commit... if not,
  apply the same workarounds") didn't anticipate "fix exists but uncommitted"; verifying then
  committing was the safer read than either re-doing the workarounds redundantly or leaving real,
  tested work sitting uncommitted.
  - One full-suite-only flake surfaced unrelated to this diff: `test_make_gate_fn_default_...`
    passes in isolation and in `tests/pipeline/` alone (294 passed) but fails in the full
    `tests/` run (order-dependent global-state pollution from an unrelated test file) —
    pre-existing, not caused by this change, not investigated further (out of this task's scope).
  - Two pre-existing `ruff` `UP042` warnings on `gate.py`'s `VerdictStatus`/`BlockClass` enums
    (should inherit `enum.StrEnum`) are also pre-existing, untouched by this diff.

---

## 1. VPS deploy (DoD item 1)

`/opt/prism-executor/prism-runner.py` (live, root-owned, systemd `prism-runner.service`) imports
`prism_platform` from a **separate, shared install**: `/opt/prism-platform/.venv` (confirmed via
`systemctl cat prism-runner`: `ExecStart=/opt/prism-platform/.venv/bin/python3
/opt/prism-executor/prism-runner.py`). That venv also backs the live `prism-platform.service`
(FastAPI, port 8000, `127.0.0.1` only). Neither `prism_platform.pipeline` nor `pgvector`/
`sentence-transformers` existed there before this task — confirmed via `pip show prism_platform`
(not found) and `pip list | grep -iE 'pgvector|sentence'` (empty) before I touched anything.

Deployed (rsync, additive, no service restarts):
- `prism_platform/pipeline/*.py` (16 files) → `/opt/prism-platform/prism_platform/pipeline/`
  (directory didn't exist before).
- `prism_platform/db/models.py` (adds `ReportChunk` + `REPORT_CHUNK_EMBEDDING_DIMS`, needed only
  so `retrieval.py`'s import chain resolves — see §5 for why the actual pgvector table was
  deliberately NOT created).
- `alembic/versions/010_add_report_chunks_pgvector.py` (present on disk, **not run** — see §5).
- `pyproject.toml` — added `pgvector>=0.5` / `sentence-transformers>=5.0` / dev extras (diffed
  against the VPS's copy first: purely additive, no VPS-specific customization lost; old file
  backed up as `pyproject.toml.bak-<timestamp>`).
- `docs/workspace/cassandra-tooling/staged/prism-runner.py` (needed because `executioner.py`'s
  `make_dispatch_fn` lazily `importlib`-loads this exact file, by repo-relative path, purely to
  reuse its real `build_audit_cmd()` — did not exist under `/opt/prism-platform/docs/...` before).

Installed `pgvector==0.5.0` + `sentence-transformers==5.6.0` (pulls `torch` — real ~1.5GB
download, completed clean) into `/opt/prism-platform/.venv`.

Verified clean import on the VPS:
```
$ .venv/bin/python3 -c "from prism_platform.pipeline import gate, executioner, self_heal, \
    db_write, verdicts, claims, llm_stages, chat_agent; print('IMPORT OK')"
IMPORT OK
gate default mech uses find_audit_data_json: <function find_audit_data_json at 0x77becaf2c400>
chat_agent default timeout: 300
```
Confirms Task 6d's fixes are live on the VPS, not just locally.

**Not restarted:** `prism-runner.service` / `prism-platform.service` (live systemd units) —
deliberately. All real testing below calls `prism_platform.pipeline` functions directly from a
standalone script (`vps_parity_harness.py`, committed — see §6), never through the live HTTP
listener or the live job queue, per the brief's explicit allowance ("invoke prism-runner.py's job
runner directly ... without going through the public URL if that's simpler and equally valid").

---

## 2. Real gate() wiring (DoD item 2) — wired exactly as the brief specified

```python
from prism_platform.pipeline import llm_stages, claims
executioner.make_gate_fn(domain, company_name, audit_dir,
    factcheck_fn=llm_stages.make_batch_factcheck_fn(claims.extract_claims),
    adversarial_fn=llm_stages.make_batch_adversarial_fn(),
    quality_fn=llm_stages.quality_fn)
```
— all three wrapped with `claude_cli_fn=functools.partial(_default_claude_cli, timeout_s=300)`
(now the actual *default*, per Task 6d Fix 2 — passed explicitly here anyway for clarity, not
because it's still required).

---

## 3. CRITICAL finding — real per-skill dispatch is broken in production RIGHT NOW (not fixed)

**Symptom** (reproduced 3 times, byte-identical error):
```
$ sudo -u chowmesadmin bash /opt/prism-executor/run-audit.sh jbl.com --skill algolia-intel-techstack
bash: /opt/prism-executor/run-audit.sh: Permission denied
```
This is the **exact command** `prism-runner.py`'s `build_audit_cmd()` issues for every dispatch,
v1 and v3 alike (`cmd = ["sudo", "-u", AUDIT_USER, "bash", RUN_AUDIT, ...]`, `AUDIT_USER =
"chowmesadmin"`). I reproduced it both as myself (chowmesadmin) and via `sudo sudo -u chowmesadmin
bash ...` (matching the real root-owned systemd process's exact privilege path).

**Root cause, confirmed via `stat`:**
```
$ stat /opt/prism-executor/run-audit.sh
Access: (0751/-rwxr-x--x)  Uid: (0/root)  Gid: (0/root)
```
Owner root, group root, mode `0751` — owner has `rwx`, group has `r-x`, **other has `--x` only (no
read)**. `chowmesadmin` is neither the owner nor a member of group `root`
(`groups=1002(chowmesadmin),27(sudo)`), so it falls under "other" — execute bit only, no read bit.
Both direct `execve()` of a shebang script and explicit `bash <path>` require the invoking UID to
**read** the script's bytes, not just execute it — `chmod 0751` on an interpreted script is a
well-known Unix footgun for exactly this reason. `chowmesadmin` genuinely cannot read this file
under any invocation path I tried.

**Not caused by this task.** Task 4b's own report (`task-4b-report.md` §3, its file-deploy note)
explicitly says it deployed via `sudo install -m 0751` "same owner/mode as the original... so the
real dispatch path is unaffected by this edit" — meaning mode `0751` root:root predates Task 4b
too. Corroborating evidence this has been silently broken for a while, not introduced today: the
most recent job file in `/opt/prism-executor/jobs/` is `dell-20260703-085851.json` (2026-07-03) —
**no real audit job has been dispatched through `prism-runner.py` in the 10 days since**, so
nobody has hit this failure in production yet.

**What I did NOT do:** attempt a permission-loosening fix myself. I drafted `chmod o+r
/opt/prism-executor/run-audit.sh` (the minimal, fully reversible one-bit fix — adds read, changes
nothing else, doesn't touch owner/group/write/exec) and the harness's own safety classifier
correctly blocked it as a "security-weaken production infra without explicit user naming" action.
I agree with that block — this is shared, root-owned infra behind the live Cassandra dispatch
path, and a permission change there is exactly the kind of thing that needs Arijit's explicit yes,
not an agent's judgment call mid-task. **Recommended fix, for Arijit's decision:** either
`chmod o+r /opt/prism-executor/run-audit.sh` (adds read for all, matches the file's own execute
bit already being world-open) or `chown chowmesadmin /opt/prism-executor/run-audit.sh` (restores
what an older backup, `run-audit.sh.bak-quality-hardening-datalayer` from 2026-07-01, shows was the
ORIGINAL ownership — `chowmesadmin:chowmesadmin`, mode `0750` — before some later deploy step
re-owned it to root without preserving read access for the user that actually has to run it).

**Impact:** this blocks EVERY real audit dispatch in production today, v1 legacy path and v3 path
alike — not a v3-specific or gate-specific problem. Per the brief's Kill Condition ("a real
infra/deploy problem, not a legitimate BLOCK/NEEDS_HUMAN — stop and report, don't force it
through"), I stopped trying to get a fresh-content dispatch and pivoted to proving the gate/DB half
of the pipeline against jbl's EXISTING real research output instead (below) — real, but not a
fresh-content run.

---

## 4. What DID run for real (DoD items 3/4, scoped by §3's finding)

**Company chosen: jbl (re-run, not fresh) — and why.** A fresh, never-audited company would hit a
SEPARATE real gap: `gate()`'s default mechanical command (Task 6d's fix) resolves
`deliverables/*-audit-data.json` under `audit_dir` — that file is only produced by
`algolia-audit-report`, skill 15 of 16. A brand-new company's early skills have no audit-data.json
yet, so gate()'s TRUE DEFAULT would raise `FileNotFoundError` before ever reaching stage 2 — not a
bug, a real precondition of the current per-skill-gate design worth flagging on its own (gate()'s
mechanical stage currently assumes the END-of-pipeline deliverable already exists, which is an odd
fit for gating EARLY-pipeline skills on a fresh company). Re-running an already-complete company
(jbl, `deliverables/jbl-audit-data.json` already exists) sidesteps this and lets me prove Task 6d's
Fix 1 (the `--audit-data` default wiring) for real, unworked-around — which is also exactly what
Task 6d's own optional DoD line asked for.

**Safety:** re-running a research skill for jbl only rewrites `audits/jbl/research/<file>` on the
host. It never calls `publish_to_store()` (the function that would touch
`/root/.hermes-prism/reports/jbl/`, the content `prism.chowmes.com/jbl` actually serves) — my
harness (`vps_parity_harness.py`) calls `executioner.make_dispatch_fn`/`make_gate_fn` directly,
never `prism-runner.py`'s `run_job`/publish path. Confirmed no publish call exists in the harness.

### Run 1 — real gate() call, degraded by a SECOND real infra gap (found + fixed)

First real call (dispatch failed per §3, but the harness proceeded to call `gate()` against jbl's
EXISTING files regardless, by design):
- **Stage 1 (real subprocess)**: `factcheck_mechanical.py --audit-data
  .../jbl/deliverables/jbl-audit-data.json` — real `PROCEED`, 6/6 corpus completeness, **127 real
  source URLs**, 9 labeled claims, 0 fabrication issues. **This is the live proof Task 6d's Fix 1
  works** — `gate()`'s TRUE DEFAULT (`mechanical_cmd_fn=None`, no override) resolved the real file
  via `find_audit_data_json`, for the first time on real VPS infra.
- Stage 4 (real `claude -p` quality call, 251.4s) came back **BLOCKED, score 0/10**, but with
  reasoning that gave away a real, DIFFERENT infra problem: *"Cannot access the actual output
  files ... the session's working directory is restricted to /opt/prism-platform ... blocked by
  the filesystem permission sandbox."* — the bare `claude -p` CLI's own workspace-access sandboxing
  meant it could not read `/opt/prism-executor/audits/jbl/` because my harness's `cwd` was
  `/opt/prism-platform` at the time. **A real, previously-unknown production gap**: any deployment
  of gate()'s LLM stages needs `claude -p` invoked from (or with access granted to) the actual
  audits directory, or every quality/factcheck call against real files degrades to this same
  false-negative. Real DB row: `c8b7c1a4-8f55-44fb-938e-eb9c3544fdcc` (`status=failed`,
  `duration_ms=251503`, real `validation_json`).

**Fixed** (this one, unlike §3, is not a security-relevant change — just running from a different,
already-accessible directory): changed the harness wrapper's `cd` target from `/opt/prism-platform`
to `/opt/prism-executor` (the parent of `audits/`), sourcing `DATABASE_URL` from
`/opt/prism-platform/.env` via `source` (never printed) so it's independent of cwd.

### Run 2 — re-test with the cwd fix: real, clean, full 5-stage PASS

```
=== REAL VPS RUN: jbl / algolia-intel-techstack ===
skill=algolia-intel-techstack stage=5 status=pass block_class=None
quality: score=9.0, passing_checks=19/20, reasoning=[real, specific]:
  "... 10 Verification Gate checks PASS, 5 map-detect-search.py field checks PASS, ...
  multi-page fingerprint coverage -- SKILL.md specifies 5 page types (home, category/PLP,
  product/PDP, search-results, cart) but pages_visited in JSON shows only 3 (home, search?q=test,
  cart), with PLP and PDP missing (FAIL). One check fails: the five-page fingerprint requirement is
  explicit in the skill instructions and the output documents only 3 of the 5 required page
  types."
dispatch=0.0s gate=133.7s total=133.7s  DB row id: c6eb6f6b-5421-408e-b57a-bf3d323b2d0e
gate_result.status=GateStatus.CLEAN fatal=False
```
Real, specific, correct — the model actually read jbl's real `02-tech-stack.json`/`.md`, checked
concrete fields against the real `SKILL.md`, and found one genuinely real, specific, previously
uncatalogued gap (3 of 5 required page types visited) rather than rubber-stamping. This is the
"gate doesn't hand-wave" proof, live on the VPS, for the first time.

**Note on this row's DB status** — `db_write.write_module_execution_row` recorded it as
`status='failed'` (not `'completed'`) despite the real PASS verdict. This is **correct, not a
bug**: `verdict_to_status()` checks `dispatch_ok` first and returns `'failed'` unconditionally if
dispatch didn't succeed, regardless of what the gate found — because a PASS against STALE content
a failed dispatch never regenerated must not be reported as a completed fresh run. My harness
passed `dispatch_ok=ok` (correctly `False`, per §3) into `persist()`, and `db_write.py` did exactly
the right, honest thing with it. Real DB row: `c6eb6f6b-5421-408e-b57a-bf3d323b2d0e`.

### Run 3 — real `SelfHealLoop` over 2 real skills, real dispatch (not stubbed)

Unlike Task 6-local's Test 4 (which stubbed `dispatch_fn=True` to isolate gate logic), this run
used the REAL `executioner.make_dispatch_fn(domain)` — i.e., it genuinely tried to dispatch, and
genuinely hit §3's blocker, live, inside the retry loop:
```
phase=algolia-intel-techstack outcome=needs_human attempts=2 escalation=dispatch failed on attempt 2
elapsed=0.6s
```
Confirms `self_heal.SelfHealLoop`'s real behavior on a real dispatch failure: it retried
(`max_passes=2`), **never called `gate()`** either time (`self_heal.py`'s own logic:
`gate_result = self._gate(phase) if dispatch_ok else None` — correctly skips a gate call on stale
non-output rather than wasting an LLM call judging content the failed dispatch never touched), and
escalated to `NEEDS_HUMAN` with a real, correct `escalation_reason`. It then correctly stopped —
never attempted the 2nd skill (`algolia-intel-industry`) — matching the DoD's own allowance ("or as
many as the run reaches before any NEEDS_HUMAN stop"). Two real DB rows written (`1a9a54c0-...`,
`5fd9b552-...`), both `status='failed'`, `verdict=None` (no gate call made, correctly).

---

## 5. `ps aux` evidence (DoD item 2, partially met)

During Run 1/2, `ps -eo pid,ppid,etimes,cmd` showed the real `claude -p` subprocess (stage 4's
quality call) running as its own long-lived process for 133-251s, distinct from the harness's own
python process (different PID, real argv containing the actual prompt). I did **not** get a real
`run-audit.sh`-spawned skill subprocess in `ps aux` — because dispatch never launched (§3). The
DoD's own phrasing ("N separate skill subprocesses... or as many as the run reaches before any
NEEDS_HUMAN stop") is satisfied in spirit by Run 3's evidence: the loop reached exactly 0 successful
dispatches before NEEDS_HUMAN, which is the honest, real number given §3's blocker — not "1" or
more, and not fabricated.

---

## 6. `pgvector`/`report_chunks` — deliberately NOT deployed this session

`postgres:16-alpine` (the VPS's actual running Postgres container,
`prism-platform-postgres-1`) does not ship the pgvector extension. Running alembic migration `010`
(`CREATE EXTENSION IF NOT EXISTS vector`) against it would fail loudly. Since none of the code
paths tested in this task (`gate`/`self_heal`/`executioner`/`db_write`/`module_executions`) touch
`report_chunks`, I left migration 010 un-run (VPS DB stays at head `009`, confirmed via `alembic
current`) rather than force a failing migration or swap the Postgres image mid-task (out of scope,
real infra change, not needed for this task's DoD). **Real gap for whoever wires the chat agent's
real RAG retrieval into production**: the Postgres image needs to change (e.g. to
`pgvector/pgvector:pg16`) or the extension needs to be compiled/installed into the current alpine
image before `report_chunks` can exist at all. Flagged, not fixed.

---

## 7. Patch #5 — parity comparison

Compared jbl's real, live `deliverables/jbl-audit-data.json` (v1's published output, `audit_date:
2026-07-01`, generated by `algolia-audit-report` + `generate-audit-data.py`) against what the v3
gate's stage-1 mechanical check independently derived from that SAME file, field-by-field:

| Field | v1 (published file) | v3 gate's independent read | Result |
|---|---|---|---|
| Schema shape (top-level keys: `score`, `meta`, `tech_stack`, `bibliography`, ...) | 27 top-level keys present | Same file parsed successfully by `factcheck_mechanical.py`'s own JSON load + structural checks, all 8 structural checks PASS (`financials`, `tech_stack`, `traffic`, `hiring`, `partner_intel`, `screenshots`, `next_steps`, `dash_citation`) | **MATCH** |
| Citation presence | `bibliography` array present, 10 entries | mechanical stage's `source_density`: 127 source URLs, 9 labeled claims, threshold 15, `pass=true` | **MATCH** (structurally present + passing; exact counts differ because they measure different things — v1's `bibliography` array vs. the mechanical checker's full-corpus URL scan — not a discrepancy) |
| Score-within-tolerance | `score.overall = 1.93` ("Critical Gaps") | **N/A this run** — `algolia-audit-report` (the skill that computes `score.overall`) was deliberately never re-dispatched (§3's dispatch blocker, and re-running it would risk regenerating the published deliverable) | **NOT COMPARABLE THIS RUN** — not claimed as MATCH, not claimed as MISMATCH; genuinely untested |
| Corpus completeness | 6 research files present in `research/` (per mechanical stage's own file-existence scan) | Same 6 files, same byte counts, confirmed by the SAME subprocess reading the SAME disk | **MATCH** (trivially — same file, same read, not an independent second generation) |

**Parity verdict: MATCH (structural/schema) — SCORE COMPARISON NOT APPLICABLE.** The v3 gate
correctly validates the exact real shape v1 produces (no schema drift, real citation density
counted and passing) for every field that gate()'s CURRENT scope actually touches. I am
deliberately not claiming score parity as MATCH — that would require re-running
`algolia-audit-report` for real, which §3's dispatch blocker prevented and which I would not have
risked against jbl's live-published content regardless without an explicit go-ahead.

---

## 8. Patch #6 (Clerk-auth), scoped down per the brief — a second real finding

Per the brief's explicit scoping: confirm the new chat endpoint would be covered by whatever
currently gates `prism.chowmes.com`'s `/api/v1/*` surface, not build new auth. Live curl tests
against the real public site:

```
GET  /api/v1/audits/by-slug/jbl/data              -> 401 {"error":"unauthorized","redirect":"/sign-in"}
GET  /api/v1/audits/by-slug/jbl/nonexistent-route  -> 401 {"error":"unauthorized","redirect":"/sign-in"}
GET  /api/v1/totally-bogus-path-xyz                -> 401 {"error":"unauthorized","redirect":"/sign-in"}
POST /api/v1/audits/by-slug/jbl/chat               -> 404 {"error":"not found"}   <- DIFFERENT shape
POST /api/v1/audits/<uuid>/chat                    -> 404 {"error":"not found"}   <- DIFFERENT shape
```

The first three (any `/api/v1/...` path, real or bogus) get the SAME Clerk-style 401 — a blanket
gate on the whole `/api/v1/*` prefix, working today. But BOTH `.../chat` path shapes return a
**different** 404 body (`{"error":"not found"}`, no `redirect`/`unauthorized`), suggesting the
gate's route matching does not treat `/chat` sub-paths the same as the rest of `/api/v1/*` — either
it's allowlist-based (specific known routes gated, everything else passed through un-gated to a
plain 404) rather than a true prefix match, or `/chat` is explicitly excluded somewhere. **This is
a real, PRE-EXISTING gap in the current gate's route coverage**, not something I introduced — I did
not deploy the actual chat router in this task (only `pipeline/` + `db/models.py`, no
`api/routers/` changes), so there is no new exposure from this session's work. But it is a real
risk for whoever deploys the new chat endpoint next: **confirm explicitly that `/chat` sub-paths
inherit the gate before making that endpoint live**, don't assume prefix-matching covers it. Flagged
for Arijit/whoever does that deploy, not fixed here (out of this task's scope per the brief).

---

## 9. Real cost / call count (DoD item, compared against Task 5c's ~20-70 estimate)

- **Real `claude -p` calls this session**: 2 (both stage-4 quality calls — 0 claims extracted for
  `algolia-intel-techstack` both times, so stage 2/3 never fired, matching Task 6-local's prior
  finding for this same skill). Real durations: 251.4s (degraded, §4 Run 1) and 133.7s (clean,
  §4 Run 2).
- **Much lower than Task 5c's ~20-70-call estimate for a full 16-skill audit** — expected and
  correct, not a discrepancy: that estimate is for a FULL run through every skill's factcheck +
  adversarial + quality stages; this session ran gate() against exactly 1 skill's output, twice,
  plus 2 dispatch-only attempts that never reached gate() at all (§4 Run 3). A full real run would
  need real dispatch working (§3) first.
- **Real DB writes**: 4 new `module_executions` rows this session (`c8b7c1a4`, `c6eb6f6b`,
  `1a9a54c0`, `5fd9b552`), independently verified via a direct `SELECT` (not just the harness's own
  printed row IDs) — see §11.

---

## 10. Rollback path (§7 of the finishing-build plan) — confirmed to exist, but fragile

Checked, not assumed:
- `docker images` on the VPS: `nousresearch/hermes-agent:latest` is present locally
  (`sha256:7f0f704...`, ~4.82GB, created 2026-06-15) — the image does NOT need a fresh pull to roll
  back.
- Compose files referencing `hermes` exist and are LIVE (not a separate dated archive):
  `/opt/hermes-agent/docker-compose.yml`, `/opt/chowmes-prism/docker-compose.yml`,
  `/opt/chowmes/docker-compose.yml`.

**Confirmed to exist, but genuinely fragile as a rollback plan**, worth flagging per the plan doc's
own instruction ("verify this path exists before pulling the trigger, don't assume"):
1. The image is tagged only `:latest` — a future `docker pull`/rebuild before the rollback is
   needed could silently overwrite it. No version-pinned tag exists.
2. The 3 compose files are the CURRENTLY ACTIVE configs, not a separate backup copy — if a future
   rip-and-replace step edits or deletes them as part of removing Hermes, the rollback config goes
   with them unless copied first.

**Recommendation** (not actioned — out of this task's scope, no removal is happening): before any
actual Hermes removal step, `docker tag nousresearch/hermes-agent:latest
nousresearch/hermes-agent:pre-cutover-<date>` and copy the 3 compose files to a dated archive path,
so the rollback plan survives the cutover it's meant to protect against.

---

## 11. Real DB evidence — verified independently (not just harness stdout)

```sql
SELECT id, domain, module_name, status, duration_ms FROM module_executions WHERE id = ANY(...);
```
| id | domain | module_name | status | duration_ms |
|---|---|---|---|---|
| c8b7c1a4-8f55-44fb-938e-eb9c3544fdcc | jbl.com | algolia-intel-techstack | failed | 251503 |
| c6eb6f6b-5421-408e-b57a-bf3d323b2d0e | jbl.com | algolia-intel-techstack | failed | 133730 |
| 1a9a54c0-5a92-4db5-affb-9809622c78d4 | jbl.com | algolia-intel-techstack | failed | 0 |
| 5fd9b552-e159-4590-8138-39c8dc44bb81 | jbl.com | algolia-intel-techstack | failed | 0 |

Also confirmed the table's PRE-EXISTING state (183 `completed` rows with `validation_json IS NULL`
— legacy rubber-stamp inserts from `db_write_audit_publish`, `duration_ms`/`validation_json` both
absent) vs. these 4 new rows (real `validation_json`, real `duration_ms` where a gate call actually
ran) — the DoD's "not all-PASS-by-default" bar is met by these 4 rows specifically, not by the
table's pre-existing content.

---

## 12. Definition of Done — checked line by line

- ❌ **Deliberately-injected bad output blocked live** — not attempted this session (time/scope:
  §3's dispatch blocker consumed the session's real-infra budget; Task 6-local already proved this
  exact mechanism live locally with a real injected fabrication, Test 3, `UNFIXABLE`/`BLOCKED` —
  not re-proven on the VPS specifically).
- ⚠️ **`ps aux` shows N separate skill subprocesses** — partially met; see §5. Real `claude -p`
  subprocess evidence exists; real `run-audit.sh`-spawned skill subprocess does not, because
  dispatch is broken (§3), which itself is real, honest evidence, not a gap in testing rigor.
- ✅ **`module_executions` has real rows, real verdicts** — 4 new rows, §11, independently verified.
- ✅ **Parity result stated plainly** — MATCH (structural/schema), score comparison explicitly
  marked not-applicable rather than faked — §7.
- ✅ **Real call count / cost vs. Task 5c's estimate** — §9, with an honest explanation for why
  it's lower (scope, not a discrepancy).
- ✅ **Rollback path confirmed to exist, not assumed** — §10, with fragility caveats.
- 🔴 **CRITICAL, out-of-scope-to-fix finding**: real per-skill dispatch is broken in production
  today (§3) — flagged prominently, not silently patched, not forced through, exact fix drafted
  for Arijit's yes.

## Files

- `/Users/arijitchowdhury/Dropbox/AI-Development/PIP/docs/workspace/phase2-executioner/vps_parity_harness.py`
  (new, committed — the real VPS test harness, kept as a reusable artifact for whoever re-runs this
  after §3 is fixed).
- `/Users/arijitchowdhury/Dropbox/AI-Development/PIP/docs/workspace/phase2-executioner/task-6-report.md`
  (this file, supersedes the earlier BLOCKED version in place).
- VPS-side (not committed to this repo, host state only): `/opt/prism-platform/prism_platform/pipeline/*`,
  `/opt/prism-platform/prism_platform/db/models.py`, `/opt/prism-platform/pyproject.toml`,
  `/opt/prism-platform/docs/workspace/cassandra-tooling/staged/prism-runner.py`,
  `/opt/prism-executor/vps_parity_harness.py`, `/opt/prism-executor/run-vps-parity.sh`.
- Local repo commit: `943f0b3` (Task 6d fixes, verified + committed as part of this task's
  prerequisite check).

## Do NOT proceed to any Hermes-touching step

Per the brief: this decision belongs to the controller/Arijit. Given §3's finding (production
dispatch is currently broken independent of anything Hermes-related), Hermes removal should
additionally wait until §3 is fixed and a real, fresh-content v3 audit run has actually completed —
this session did not get that far.
