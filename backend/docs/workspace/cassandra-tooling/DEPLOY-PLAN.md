# Cassandra Tooling — Deploy Plan (staged, NOT executed)

Built 2026-07-02. Everything under `docs/workspace/cassandra-tooling/staged/` is
**staged code only** — nothing here has touched the VPS. This doc is the exact
sequence to run LATER, attended, when Arijit is ready to cut over Part 1 of
`docs/plans/2026-07-02-cassandra-airtight-pipeline-goal.md` (§1.1, §1.2, §1.4, §3.2).

Tests proving these staged files work: `tests/pipeline/test_runner_dbwrite.py`
(16 tests, real alembic schema against an ephemeral Postgres) and
`tests/pipeline/test_runner_routes.py` (34 tests, fake subprocess). Both pass
today — `python3 -m pytest tests/pipeline/ -q` → 145 passed (includes the
parallel block-detector/self-heal/screenshot-gate work already on this branch).

**What this build does NOT include** (out of scope for this task, noted so the
next session doesn't assume it's done): `POST /render`, `POST /publish`,
`POST /validate` as real runner routes (the plugin's `validate_audit` tool is
written defensively against a future `/validate` and reports "not deployed
yet" until it exists), and wiring `prism_platform/pipeline/self_heal.py` /
`block_detector.py` / `screenshot_gate.py` into the runner or run-audit.sh —
those are separate, already-tested, already-isolated modules built by a
parallel effort on this same branch, also not yet integrated.

---

## 0. Pre-flight (read-only, no risk)

1. SSH in: `ssh -i ~/.ssh/chowmes_ed25519 chowmesadmin@72.61.72.147`
2. Confirm current state matches what this plan assumes:
   ```
   sudo systemctl status prism-runner
   cat /opt/prism-executor/prism-runner.py | md5sum   # compare to live-sources/prism-runner.py
   cat /opt/prism-executor/run-audit.sh | md5sum       # compare to live-sources/run-audit.sh
   docker exec prism-platform-postgres-1 psql -U prism -d prism -c "\dt"
   ```
3. **Back up everything this touches** (per CLAUDE.md safety rule — back up every file before editing):
   ```
   sudo cp /opt/prism-executor/prism-runner.py /opt/prism-executor/prism-runner.py.bak-cassandra-tooling-$(date +%Y%m%d)
   sudo cp /opt/prism-executor/run-audit.sh /opt/prism-executor/run-audit.sh.bak-cassandra-tooling-$(date +%Y%m%d)
   sudo cp /root/.hermes-prism/plugins/prism-report-qa/__init__.py /root/.hermes-prism/plugins/prism-report-qa/__init__.py.bak-cassandra-tooling-$(date +%Y%m%d)
   ```
4. Confirm a recent filesystem/DB backup exists per plan §0.1 (Phase 0 safety net). **If Phase 0 backups aren't done yet, do them before this deploy** — this deploy is exactly the kind of change that backup exists to protect against.

## 1. Migrate the DB (if not already at head)

**PROD-TOUCHING.** The runner's DB write path assumes the `audits.audit_data`
JSONB column and `Numeric(3,2)` score precision from migration `009`. Confirm
the live Postgres is at head before deploying the runner:
```
docker exec prism-platform-postgres-1 psql -U prism -d prism -c "SELECT version_num FROM alembic_version;"
# expect: 009
```
If not at head, run the platform's normal migration path first (not part of
this deploy — a separate, already-existing `prism_platform` operational step).
Do NOT hand-write DDL to catch up; use alembic.

Set `DATABASE_URL` in the runner's systemd unit environment (it defaults to
the LOCAL dev DSN if unset — **do not deploy without setting this**, or the
runner will try to reach `127.0.0.1:55432` on the VPS, which doesn't exist,
and every DB write will silently fail-soft with nothing written):
```
# /etc/systemd/system/prism-runner.service (or its EnvironmentFile)
Environment=DATABASE_URL=postgresql://prism:<real-password>@127.0.0.1:5432/prism
```

## 2. Deploy `run-audit.sh` v2

**PROD-TOUCHING.**
1. Copy `staged/run-audit.sh` to `/opt/prism-executor/run-audit.sh` (overwrite, backup already taken above).
2. `chmod +x /opt/prism-executor/run-audit.sh`
3. Smoke test the unchanged path first (full run, no flags) against a **scratch
   slug**, not a real prospect (per plan §7 safety rule):
   ```
   sudo -u chowmesadmin bash /opt/prism-executor/run-audit.sh scratch-test-example.com
   ```
   Confirm the prompt logged is byte-identical in intent to the old one (same
   guardrails) plus the new SimilarWeb/skill-marker instructions.
4. Smoke test a targeted run: `--phase research` and `--skill algolia-intel-traffic` against
   the same scratch slug's existing workspace; confirm the log shows the
   scoped prompt, not the full-pipeline one.

## 3. Deploy `prism-runner.py` v2

**PROD-TOUCHING — this is Cassandra's execution arm; a bad deploy here breaks
her ability to run/monitor audits until fixed.**
1. Copy `staged/prism-runner.py` to `/opt/prism-executor/prism-runner.py`.
2. `sudo systemctl restart prism-runner`
3. `sudo systemctl status prism-runner` — confirm it's up, no crash loop.
4. `curl 127.0.0.1:8770/health` → `{"ok": true, ...}`.
5. Verify auth unchanged: `curl -H "Authorization: Bearer $PRISM_RUNNER_TOKEN" 127.0.0.1:8770/jobs` still works.
6. Verify v1 compatibility: `curl -X POST -H "Authorization: Bearer $PRISM_RUNNER_TOKEN" -d '{"domain":"scratch-test-example.com"}' 127.0.0.1:8770/run` still returns the same 202 shape Cassandra's existing `run_audit` tool expects (job_id, slug, status, note) — **do this BEFORE deploying the plugin**, so Cassandra keeps working with her OLD tool schema against the NEW runner during the gap between steps 3 and 4.
7. New routes, smoke test each:
   ```
   curl -X POST ... -d '{"domain":"scratch-test-example.com","phase":"research"}' 127.0.0.1:8770/run
   curl ... 127.0.0.1:8770/status/<job_id>          # confirm "skills" + "needs_human" keys present
   curl -X POST ... -d '{"slug":"scratch-test-example","skill":"algolia-intel-traffic"}' 127.0.0.1:8770/rerun
   curl ... 127.0.0.1:8770/needs_human
   curl -X POST ... -d '{"job_id":"<a real running job>"}' 127.0.0.1:8770/kill   # only against a scratch job
   ```
8. Confirm DB writes actually land:
   ```
   docker exec prism-platform-postgres-1 psql -U prism -d prism -c \
     "SELECT id, status, score FROM audits ORDER BY created_at DESC LIMIT 5;"
   docker exec prism-platform-postgres-1 psql -U prism -d prism -c \
     "SELECT module_name, status FROM module_executions WHERE audit_id = '<id above>';"
   ```
9. **Rollback if anything above fails:** `sudo cp prism-runner.py.bak-... prism-runner.py && sudo systemctl restart prism-runner`.

## 4. Deploy the plugin additions

**PROD-TOUCHING — restarting hermes-prism drops Cassandra's active
conversations; do this in a quiet window and confirm Telegram reconnects.**
1. Open `/root/.hermes-prism/plugins/prism-report-qa/__init__.py` (and the
   container copy `/opt/data/plugins/prism-report-qa/__init__.py` — **both**,
   per the "3 non-syncing physical copies" gotcha in memory).
2. Apply the merge per `staged/prism-report-qa-plugin-additions.py`'s
   "MERGE INSTRUCTIONS" section at the bottom of that file: replace
   `RUN_AUDIT_SCHEMA`/`_handle_run_audit`, add the four new tool
   definitions, extend `_EXEC_TOOLS`.
3. Restart the hermes-prism container: `docker restart hermes-prism` (or the
   project's normal plugin-reload path if one exists — check
   `docs/workspace/hermes-prism-integration/` first).
4. `docker logs hermes-prism --tail 50` — confirm clean startup, plugin loaded,
   no import errors from the merge.
5. Confirm Telegram reconnects (send Cassandra a message, get a reply).
6. From Telegram, exercise each new tool once against the scratch slug:
   "run a targeted traffic check for scratch-test-example.com" (skill arg),
   "re-run traffic for scratch-test-example" (rerun), "how's that audit going,
   phase by phase?" (live_status), "anything waiting on my login?" (list_needs_human).
7. **Rollback if anything above fails:** restore both `__init__.py` backups,
   `docker restart hermes-prism`, confirm Telegram replies again before
   declaring rollback complete.

## 5. Post-deploy regression

Per plan §6: re-run an existing clean audit (e.g. petsmart) end-to-end after
this deploy to confirm nothing broke on a real, non-scratch case, and
browser-verify the resulting published page still renders with 0 JS errors.

## Top 3 prod-touching steps (flagged for explicit go/no-go)

1. **Restarting `prism-runner` (step 3.2)** — Cassandra loses her execution
   arm for the duration of the restart; any audit mid-run at that moment has
   its polling thread killed (the job process itself, spawned via `sudo -u
   chowmesadmin`, is NOT a child of the Python runner process and should
   survive the restart — the runner just needs to re-attach via job-file
   polling on its next `/status` call. **Verify this assumption against the
   live systemd unit's `KillMode` before relying on it** — if `KillMode=control-group`,
   the audit subprocess dies with the service).
2. **Restarting `hermes-prism` (step 4.3)** — drops Cassandra's live
   conversations and in-memory session bindings (`_BINDINGS`, `_INDEX_CACHE`);
   anyone mid-chat with her has to re-establish which report they're bound to.
3. **Setting `DATABASE_URL` in production (step 1)** — if pointed at the wrong
   DB or a stale password, every audit publish silently fail-softs on the DB
   write (by design) while the file path keeps working — meaning this
   misconfiguration could go unnoticed for a while. **Explicitly check
   `SELECT * FROM audits` after the first post-deploy run**, don't just trust
   the file-store publish succeeding.
