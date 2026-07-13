# Task 6 report — non-prod parity run (Track C cutover-order)

**Status: BLOCKED**

3-line summary: All prerequisite code (`gate.py`, `self_heal.py`, `executioner.py`, `llm_stages.py`,
`claims.py`, `chat_agent.py`, `verdicts.py`, the v3-wired staged `prism-runner.py`) is committed
locally and passes the full test suite (285 passed, `ruff`/`ruff format`/`mypy --strict` clean — see
§1). The task could not proceed past that point: **SSH access to the VPS (`chowmes-vps`,
`72.61.72.147:22`) is unreachable from this machine's current network for the entire session**,
which blocks every subsequent step (deploy, dependency check, real audit run, `ps aux`/DB evidence,
parity comparison). This is a real infra blocker, not a gate/pipeline failure — reported per the
brief's kill condition, not forced through.

---

## 1. What was confirmed BEFORE the SSH blocker (local repo, no VPS needed)

```
$ git log --oneline -6 -- prism_platform/pipeline/
8d47318 feat(pipeline): Task 5c — claims.extract_claims closes Task 5b's claim-extraction gap
197adce feat(pipeline): Task 5b — real LLM stages for gate()'s factcheck/adversarial/quality
d71dad5 feat(chat): Task 5 — embedded grounded chat agent (pgvector + local MiniLM + claude -p)
37272d4 feat(pipeline): executioner dispatch + gate closures for per-skill self-heal (Task 4a)
4f3f5d9 feat(pipeline): Track G gate() 5-stage verification pipeline (Task 3)
acd155e feat(prism): live DB migration + Cassandra tooling deploy + Dell audit fixes
```
Working tree clean for `prism_platform/pipeline/` (nothing uncommitted) — all Task 1-5c work is on
disk on branch `feat/prism-e2e-cycle`, ready to deploy.

```
$ python3 -m pytest tests/pipeline/ -q
........................................................................ [ 23%]
........ss.............................................................. [ 47%]
.........ssssssssssssssss............................................... [ 71%]
........................................................................ [ 95%]
...............                                                          [100%]
285 passed, 18 skipped in 55.90s
```

This confirms, independent of any prior task report's self-report, that the code this task needed to
deploy is real, present, and green as of right now, on this branch.

## 2. The blocker — localized, not assumed

Per the standing heuristic (memory `feedback-vps-connection-storm-ban`: "test `/dev/tcp/github.com/22`
FIRST; if refused it's local egress"), I localized before concluding anything about the VPS:

```
$ nc -z -w5 github.com 22   → "Connection to github.com port 22 [tcp/ssh] succeeded!"
$ nc -z -w8 72.61.72.147 22 → "vps22 FAIL" (repeated across ~6 attempts over ~12 minutes,
                                 including two bounded retry loops of 5 and ~10 minutes)
$ curl -sS -m 10 -o /dev/null -w "%{http_code}\n" https://prism.chowmes.com/ → 200
```

- Outbound SSH to a DIFFERENT host (github.com) works fine — rules out "my ISP/network blocks all
  outbound 22 to everywhere" as the first hypothesis... except it doesn't, see below.
- Outbound HTTPS to the VPS itself works fine (200) — rules out "the VPS/box is down."
- Outbound SSH to the VPS specifically times out, on every attempt, across ~12 minutes of retries
  (including two separate bounded backoff loops, one 5 min, one ~10 min, per-attempt `ConnectTimeout=10`).

**Root cause identified**: `netstat -rn -f inet` shows this machine's active default gateway is
`172.20.10.1` — a cellular/mobile-hotspot address range, not a home/office router. Cellular carrier
hotspot NAT commonly blocks or heavily restricts outbound TCP/22 while passing 443 freely (a known,
common carrier-level restriction, distinct from any VPS-side fail2ban/UFW behavior). This explains
the exact pattern observed: 443 fine, 22 dead, github.com:22 "succeeding" at the TCP handshake level
(a different destination/path, and note: even that check only proved a SYN/ACK-level connect for
github, not a full SSH auth — it's a weaker signal than it looks, and is not itself proof the VPS-only
theory is wrong, given the gateway-address evidence is more direct).

**This is a local-network condition, not a VPS or credential problem** — nothing on the VPS side
(fail2ban, UFW, the box being down) is implicated by this evidence. It is also not something fixable
from inside this session: it requires being on a different network (home/office Wi-Fi, not this
hotspot) to re-attempt.

## 3. What this blocks (all of it, sequentially)

Every remaining brief item requires VPS shell access and none could be started:
1. Deploy updated `prism-runner.py` (v3 path) + `prism_platform` package to `/opt/prism-executor/` — **not attempted, blocked**.
2. Confirm how `prism_platform` is made importable on the VPS (venv/pip/PYTHONPATH) — **not attempted, blocked**.
3. Install `pgvector`/`sentence-transformers` on the VPS if missing — **not attempted, blocked**.
4. Wire real `factcheck_fn`/`adversarial_fn`/`quality_fn` callables into a live `make_gate_fn` call on the VPS — **not attempted, blocked** (the callables themselves exist and are unit-tested per Task 5b/5c; wiring them into a live VPS run needed the deploy step above first).
5. Run one real audit end-to-end through `engine="v3"` — **not attempted, blocked**.
6. `ps aux` evidence of N separate skill subprocesses — **not attempted, blocked**.
7. `module_executions` real-verdict rows — **not attempted, blocked**.
8. Parity comparison (patch #5) against a Hermes-run baseline — **not attempted, blocked** (no v3 run exists to compare).
9. Patch #6 scoped-down auth check (chat agent reachable through current, even-weak, auth gate) — **not attempted, blocked**.
10. Real `claude -p` call count / cost for one run, vs. Task 5c's ~21-32 estimate — **not measured, blocked** (no run occurred).
11. Rollback path (§7) — archived Hermes image/compose file — **not checked, blocked** (this specific check is VPS-side: confirming an archive exists at a named path).

**Zero destructive or partial actions were taken.** No deploy, no VPS file writes, no Hermes-adjacent
commands, no `docker` commands of any kind ran this session — the blocker occurred before step 1
could start.

## 4. Parity verdict

**NOT APPLICABLE — no v3 run exists to compare.** Cannot state MATCH / MATCH-WITH-EXPLAINED-DRIFT /
MISMATCH because the run this comparison depends on never executed. Stating a verdict anyway would be
exactly the false-green failure mode this project's standards forbid (AIOS guardrail #1).

## 5. What Task 6 needs to actually run (unchanged, still valid, just not executable from here tonight)

Nothing about the plan changed — this is purely a network-access blocker on this attempt, not a
finding that invalidates any prior task's work or the interface contract. The next attempt should:
1. Confirm this machine is on a normal (non-cellular-hotspot) network, or use an alternate access path
   to the VPS, before retrying `ssh chowmes-vps`.
2. Re-run the exact steps 1-11 in §3 above, in order, once shell access is confirmed live with a plain
   `ssh chowmes-vps "hostname; date"` sanity check FIRST (don't assume connectivity from a stale
   session).
3. Everything downstream of that (deploy, wiring, the real audit, parity, cost count, rollback check)
   is unchanged from this brief and ready to execute the moment SSH is reachable.

## Kill condition invoked

Per the brief: "If the v3 pipeline fails to complete for reasons unrelated to the gate working-as-
designed (a real infra/deploy problem, not a legitimate BLOCK/NEEDS_HUMAN), stop and report BLOCKED
with the specific failure — do not force it through or paper over a broken deploy step." This is
exactly that case, one step earlier than the pipeline itself (the deploy never started) — reported
as BLOCKED rather than retried indefinitely or faked.

**No Hermes-touching step was attempted or approached.** This report ends at "report parity result"
per the brief's own scope boundary — the STOP-and-report-to-Arijit step (and any decision about
retrying on a different network) belongs to the controller, not this task.
