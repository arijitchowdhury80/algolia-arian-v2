# Concurrency Design — Running Up to 20 Parallel Audits

**Author:** research subagent, 2026-07-02 | **For:** PART 2 multi-tenancy architecture (goal plan §5)
**Status:** decision-grade analysis, NOT yet reviewed by Arijit — feeds `docs/plans/multi-tenancy-architecture.md`

---

## 0. Bottom line up front

Twenty *truly simultaneous* audits do not fit on the current box, and — more importantly — probably do not fit on **one Claude subscription** at all, regardless of how many boxes you add. There are two independent ceilings, and the second one is the real constraint:

1. **Box ceiling (fixable with money): ~3-4 concurrent audits** on the current 2 vCPU / 8G VPS, set by Chrome + `claude -p` RAM/CPU, not by anything architectural. Scales linearly by adding worker boxes.
2. **Subscription ceiling (NOT fixable with box money): a single Claude account's rate-limit pool is shared across every session on that account** — 5-hour rolling window AND a weekly hour cap, plus an empirically-reported hard wall where bursting many session starts at once on one account gets some of them rejected outright with 529/"temporarily limiting requests" errors, independent of whether you're under your usage cap. Adding boxes does nothing here if they all authenticate as the same subscription.

**Recommendation:** build the box-side queue now (bounded worker pool + Redis/arq + Postgres state), sized to what the box can actually hold (~3 workers), with per-tenant fairness and hard job timeouts. Treat "20 parallel" as a **queue-depth/throughput problem**, not a "20 processes running at once" problem, until Arijit makes an explicit, informed call on the subscription question in §4(d) — that's a cost/ToS decision, not an infra one, and it's the actual gate on real 20-way parallelism.

---

## 1. Realistic per-box concurrency ceiling

Ground truth from the goal plan (§1.2, verified on the live VPS): 2 vCPU / 8G RAM / 96G disk (30G free), currently near-idle, also hosting Postgres, Redis, Caddy, the Hermes containers, and the `prism_platform` FastAPI service. A single audit's `claude -p` process + headless Chrome instance is verified at **≈1-2G RAM**.

- **RAM:** existing services (Postgres + Redis + Caddy + Hermes containers + FastAPI) plausibly hold ~1-2G baseline on an idle box, leaving ~6-7G headroom. At 1-2G/audit, that supports **3-6 concurrent audits before OOM risk**. I'd plan for 3, allow monitored headroom to 4-5 — not the top of that range, because…
- **CPU:** 2 vCPUs is the tighter constraint. Chrome rendering (the browser-testing phase — typing queries, waiting for autocomplete/SAYT to render, screenshotting) is CPU-bound; `claude -p` itself is mostly I/O-bound waiting on the network, so it doesn't compete much for CPU, but N simultaneous Chrome instances on 2 vCPUs will slow page-load/render time under contention. Slower renders risk **false factcheck failures** — the pipeline already has a documented class of bug where a screenshot taken before content finishes rendering produces wrong findings (goal plan §3.1c, the lululemon "no trending suggestions" false-negative). CPU contention from over-packing concurrency directly increases the odds of retriggering that bug class.

**Verdict: ~3 concurrent audits is the safe ceiling on this box today.** This is not a soft/aesthetic number — it's RAM math plus the CPU-contention link to a known correctness bug. Push it via monitoring in production (watch RSS + audit render-timing gate-pass-rate as you raise worker count), don't guess higher upfront.

---

## 2. Queueing design options

The runner today (`prism-runner.py`, read directly — see file, 269 lines) has **no queue at all**: `POST /run` slugifies the domain, writes a flat JSON job file, and fires a **daemon thread per request, unbounded**. Two callers today would both start immediately; twenty would all try to start `claude -p` + Chrome simultaneously and OOM/CPU-starve the box. This has to change regardless of which queue tech is picked — it's the actual root gap, not a config knob.

### Option A — Postgres-table queue + bounded worker pool in the runner
A `job_queue` table (`id, tenant_id, domain, phase, skill, status, priority, claimed_by, claimed_at, attempts`) with workers claiming rows via `SELECT ... FOR UPDATE SKIP LOCKED`. Natural fit because Phase 1 of the goal plan (§1.2) is *already* moving job/audit state into Postgres (`audits` + `module_executions` tables exist, currently 0 rows) — this would just be one more table in the same database, no new dependency, single language (Python) end to end.

- **Pro:** zero new infra; tenant fairness and cost ceilings are a `WHERE tenant_id` clause away; fits the "Postgres = single source of truth" decision already locked (§10.4 of the goal plan).
- **Con:** you hand-roll retry/backoff/dead-letter/heartbeat-timeout logic yourself — a real (if bounded) amount of code. Scaling to multiple boxes means every worker box needs direct Postgres access and you're reinventing a distributed work-queue's plumbing (visibility timeouts, worker-crash recovery) on top of a relational table not built for that job.

### Option B — Redis queue (rq or arq)
Redis is already deployed and healthy (`prism-platform-redis-1`) and, per the brief, "barely used" today — capacity is sitting idle. `arq` (asyncio-based) or `rq` (sync) give a worker pool, retries, priority, and dead-letter essentially for free, and — critically — **workers are location-independent**: a worker process anywhere with network access to the same Redis instance can pull jobs. That is exactly the multi-box scale-out path (§3) with no redesign, just more workers pointed at the same `REDIS_URL`.

- **Pro:** the queue mechanics (retry, timeout, dead-letter, fair dispatch) are solved by the library, not hand-rolled; this IS the path to N boxes later without rearchitecting; Redis capacity is already paid for and idle.
- **Con:** one more operational surface (a distinct worker process/service, not the current simple-threading model in `prism-runner.py`); needs care because audit jobs are long (30-90 min) — must set generous job/lock timeouts so the queue doesn't think a healthy long-running job is dead and double-dispatch it.
- **Net:** Postgres stays the system-of-record for job/audit *state* (per the already-locked Phase 1 decision); Redis is purely the transient work-queue. Clean separation, not two competing sources of truth.

### Option C — Re-introduce Temporal
Explicitly rejected already and recorded in memory: `feedback-heavy-orchestrator-overkill` — "read workflow+activity body first; if just sequencing static steps, run in-process. Built run_pipeline (Temporal-free)." Re-opening Temporal purely to get parallelism is not justified here. What's actually needed — bounded concurrency, retry, dead-letter, per-tenant fairness — is a queue, not a durable-execution workflow engine; a queue table or Redis queue delivers all of it at a fraction of the operational cost (no separate Temporal server + its own DB, no new learning curve, no walking back a considered decision).

I'd flag one honest exception: if PART 4 or later multi-tenancy work needs genuine cross-service saga-style orchestration — e.g., coordinating an audit run with billing, notification, and a compensating rollback if a paid step fails — that's a legitimate reason to revisit Temporal. That is not what "run more audits in parallel" needs, so it shouldn't be the reason to bring it back now.

### Recommendation
**Option B — Redis + arq**, with Postgres remaining the state system-of-record (already locked by the goal plan). Reasons, ranked: (1) it's the only option of the three that turns "add more boxes" into an additive change rather than a redesign, (2) Redis capacity is already deployed and idle — no new infra cost, (3) retry/backoff/dead-letter come from the library instead of being hand-rolled and under-tested. Cap the worker pool at **3** to match the RAM/CPU ceiling from §1, not at some aspirational number.

---

## 3. Multi-box scale-out path

**Trigger point (measurable, not aesthetic):** when queue wait time consistently exceeds an acceptable SLA at the 3-4-worker ceiling — e.g., audits sitting queued for hours during a normal business-day burst. Don't scale out on a hunch; scale out on observed queue depth.

**Design:** worker-pool pattern. The dispatcher (a slimmed `prism-runner.py`, or Cassandra via the Phase-1 runner routes) pushes jobs to Redis. N cheap Hostinger worker VPS boxes ($8-30/mo each, e.g. 2vCPU/4-8G) each run an `arq` worker that pulls a job, runs `run-audit.sh` + Chrome locally, and writes results back to the **shared, central** Postgres + publishes to the shared `/opt/prism-hub` target (needs a defined push path — rsync/git from worker to hub box, or workers write to a shared volume; this is a real design item, not hand-waved). Each worker box needs `claude-cli` + the 22 skills + Playwright/Chrome provisioned identically — script that provisioning once, don't hand-configure N boxes.

**Cost curve:** at ~3-4 audits/box, hitting 20 concurrent needs ~5-7 worker boxes ≈ $50-200/mo — cheap next to the $200/mo Max 20x subscription itself. **But this is the less important number** — see §4(d): box cost is not the constraint that stops you from actually running 20 in parallel.

**A specific complication this plan should carry forward:** the SimilarWeb HITL flow (goal plan §3.2) is same-IP-login-dependent — the login IP must match the replay IP to avoid the "impossible travel" session break. Spreading audits across N worker boxes with N different egress IPs breaks that assumption unless the SimilarWeb step is centralized on one designated box (or one designated egress path) regardless of which box runs the rest of that audit. Don't let this get lost when Part 2 build starts — it's a concrete integration point between this design and the already-locked SimilarWeb decision.

---

## 4. Subscription-auth constraint — the real gate on 20-way parallelism

This is the part of the brief worth the most scrutiny, because the goal plan's cost model currently assumes it away. Quoting the goal plan directly (§9): *"An audit costs ≈ subscription + a few cents of Gemini — NOT dollars"* — that's true for **one audit at a time**. It is very likely NOT true at 20-parallel, and the reason is architectural, not a pricing nuance.

**What the audit engine actually runs on:** per the goal plan (§1.2, §9), each audit is one long `claude -p` headless session (`run-audit.sh` explicitly unsets `ANTHROPIC_API_KEY` so it runs on `CLAUDE_CODE_OAUTH_TOKEN` — flat-cost subscription auth, not metered API).

**What subscription auth actually allows, per current public documentation and reported behavior (2026):**
- All Claude Code sessions on one account **share a single pooled rate-limit budget** — a 5-hour rolling window and a separate weekly cap. More concurrent sessions on the same account means hitting that shared ceiling faster, not "more capacity." ([32blog — Multiple Claude Code Instances](https://32blog.com/en/claude-code/claude-code-multiple-instances-context-guide), [TrueFoundry — Claude Code Rate Limits](https://www.truefoundry.com/blog/claude-code-limits-explained))
- Published/aggregated weekly figures (third-party estimates, not confirmed against Anthropic's own docs in this pass — verify against `support.claude.com/en/articles/14552983-models-usage-and-limits-in-claude-code` before sizing a real budget): Max 5x ≈ 140-280 Sonnet-hours/week; Max 20x ≈ 240-480 Sonnet-hours/week, up to ~40 Opus-hours/week. ([morphllm — Claude Code Usage Limits](https://www.morphllm.com/claude-code-usage-limits))
- **Separately, and more immediately relevant:** there is a reported *hard burst ceiling* independent of the hour budget — starting many parallel Claude Code sessions at once on one account causes the first 3-4 to succeed and the rest to fail outright with a 529/"Server is temporarily limiting requests" error, even while under the account's total usage cap. This is documented as a live bug/behavior, not a soft warning. ([GitHub anthropics/claude-code#53922](https://github.com/anthropics/claude-code/issues/53922), [#68502](https://github.com/anthropics/claude-code/issues/68502))

**What this means for PRISM concretely:**
- Firing off 20 `claude -p` processes at once on **one** subscription is likely to fail outright for most of them at the burst layer — before the hour-budget math even matters. Staggering starts (a few seconds/minutes apart, via the worker pool's natural claim-and-start rhythm) avoids this, but it means "20 parallel" in practice looks like "N workers steadily draining a queue," not "20 simultaneous session starts" — which is exactly the queue design already recommended in §2, so this reinforces rather than changes that call.
- Sustained volume is the bigger risk than instantaneous burst. Each audit is a long, tool-heavy session (research + browser-control loop + report generation) — realistically consuming a meaningful chunk of active compute time, not a quick prompt. Twenty audits run in reasonably close succession could plausibly consume double-digit hours of pooled compute in a single day — a significant fraction, possibly all, of even a Max 20x account's weekly Sonnet budget, leaving little headroom for the rest of the week's normal ad-hoc audit traffic. **This has not been measured yet** — the goal plan's cost model is based on one-audit-at-a-time behavior; recommend instrumenting actual active-compute-time (or token count, as a proxy) on the next several live audits before committing to a specific weekly-volume number the subscription can sustain.
- Getting real 20-way throughput without hitting either wall requires one of:
  1. **Multiple separate Claude subscriptions**, each backing a subset of workers, each staying under its own burst + weekly caps — technically straightforward (each worker/session authenticates with a different `CLAUDE_CODE_OAUTH_TOKEN`), but this is a **commercial and ToS diligence item**, not a code change: running multiple paid seats for automated/headless workloads at volume is worth checking against Anthropic's terms before scaling this way. This doc does not resolve that question — it's flagged for Arijit to decide, explicitly, before Part 2 build commits to it.
  2. **`ANTHROPIC_API_KEY` fallback for overflow capacity beyond what the subscription pool can absorb** — technically simple (the opposite of `run-audit.sh`'s current `unset ANTHROPIC_API_KEY`, gated per-job), but this breaks the "flat-cost, pennies-per-audit" model the goal plan currently states as fact. At Sonnet API pricing ($3/$15 per 1M in/out — per the user's own `claude-api` skill reference), even a token-heavy audit is probably low single-digit dollars in isolation, but 20-parallel × dozens of audits/week on pure metered pricing turns "pennies" into a real recurring line item. **Size this from real numbers, not assumption** — instrument token usage on live audits first.
  3. **Accept a lower real-concurrency ceiling** (the §1-§2 box design, ~3-4 concurrent, queue-fed) as the actual operating model, and treat "20 AEs" as "20 people whose audits complete within an acceptable queue SLA," not "20 audits running at literally the same instant." This is almost certainly the right near-term default — it costs nothing new and doesn't require a ToS or budget decision — with (1) or (2) as explicit future upgrades if queue depth becomes the real bottleneck (per the §3 trigger).

**This is the single most important finding in this doc:** infrastructure (boxes, queue tech) is not what stands between PRISM and 20 truly parallel audits. The Claude subscription's account-level pooled rate limit is. That's a decision for Arijit, not something to route around silently in the build.

---

## 5. Per-tenant fairness + cost ceilings

Once job state lives in Postgres (Phase 1, already planned) and jobs carry `tenant_id`, fairness is a dispatch-order rule, not new infrastructure: workers should prefer round-robin across tenants with pending work rather than global FIFO, so one AE queuing 10 audits back-to-back doesn't starve everyone else. A hard cap of "no more than 2 concurrent audits per tenant" regardless of total worker capacity is a cheap, effective guardrail and should ship with the queue on day one, not be added reactively after the first complaint.

Cost ceilings matter more once any traffic falls back to metered API (§4d.2): enforce per-tenant daily/weekly audit-count caps at admission time (reject or defer beyond the cap) so one runaway tenant can't consume the shared subscription's weekly hour budget, or a real API bill, alone.

## 6. Failure containment

A stuck audit must not starve the queue. Concretely:
- **Hard wall-clock timeout per job** (e.g., 2x observed p95 audit duration) that kills the subprocess and marks the job `FAILED`/`NEEDS_HUMAN` rather than letting it hold a worker slot indefinitely. **This does not exist today** — `prism-runner.py`'s `run_job()` polls `proc.poll()` in a loop with no timeout at all; a hung `claude -p` or a Chrome instance stuck on a bot-wall interstitial currently blocks that worker slot forever. This is a real, currently-live gap, not a hypothetical.
- **Per-job process isolation, already true today** — `prism-runner.py` uses one `subprocess.Popen` per job, so a stuck job doesn't block the whole process/box, only its own slot. Preserve this property when moving to the worker-pool model (each `arq` worker handles one job at a time, same isolation, just bounded in count).
- **Dead-letter / escalation** matching the Phase 1 self-heal design (goal plan §1.3): a job that times out or exhausts retries surfaces to Cassandra/Arijit as `NEEDS_HUMAN`, not silently dropped.
- **Zombie-process reaper:** if a Chrome instance leaks past its parent `claude -p` process exiting (a documented risk given the bot-wall/interstitial issues in §3.1b of the goal plan), a periodic cron sweep (`pkill` orphaned chrome processes older than N minutes) prevents slow RAM leak across cycles — cheap insurance, add it alongside the timeout fix.

---

## 7. Recommendation summary

**Build now, on the current box:**
- Fix the actual root gap: `prism-runner.py`'s unbounded per-request thread spawn → bounded worker pool (start at 3).
- Redis + `arq` for the queue (Redis idle capacity, retry/dead-letter for free, workers are location-independent so this doubles as the multi-box on-ramp). Postgres stays the state system-of-record per the already-locked Phase 1 decision — Redis is transient work-queue only.
- Per-tenant fair dispatch + concurrency cap (max 2/tenant) from day one.
- Hard per-job timeout + kill (currently absent — genuine live gap) + zombie-Chrome reaper.

**Scale-out trigger:** measured queue-wait SLA breach at the 3-4-worker ceiling, not a target headcount. Path: add worker VPS boxes running the same `arq` worker pointed at the same Redis + Postgres — additive, not a redesign, because of the Redis choice above. Watch out for the SimilarWeb same-IP-login coupling when this happens (§3).

**The gate Arijit needs to decide, not infra:** whether real 20-way parallelism is worth (a) multiple Claude subscriptions (commercial/ToS diligence needed, not resolved here) or (b) metered API-key fallback for overflow (cost needs to be sized from real instrumented token counts, not assumed pennies) — versus (c) accepting a lower true-concurrency ceiling with queue-fed throughput as the actual "20 AEs" experience. Recommend defaulting to (c) for the near-term build (§2-§3 above), with (a)/(b) as explicit, budgeted future upgrades once real queue-depth data shows they're needed.

**Sources:**
- [32blog — Multiple Claude Code Instances: Context & Rate Limits](https://32blog.com/en/claude-code/claude-code-multiple-instances-context-guide)
- [TrueFoundry — Claude Code Rate Limits & Usage Quotas Explained (2026)](https://www.truefoundry.com/blog/claude-code-limits-explained)
- [morphllm — Claude Code Usage Limits (2026)](https://www.morphllm.com/claude-code-usage-limits)
- [GitHub anthropics/claude-code#53922 — parallel sessions right after reset fail](https://github.com/anthropics/claude-code/issues/53922)
- [GitHub anthropics/claude-code#68502 — 529 overloaded rendered as rate-limited, hard-fails parallel sessions](https://github.com/anthropics/claude-code/issues/68502)
- [Claude Help Center — Models, usage, and limits in Claude Code](https://support.claude.com/en/articles/14552983-models-usage-and-limits-in-claude-code) (verify weekly-hour figures here directly before budgeting)
