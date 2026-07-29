# Phase B — L2 Execution Orchestration Design (multi-agent)

**Date:** 2026-06-29
**Status:** DESIGN — runtime model LOCKED (hybrid routing, user 2026-06-29). Roster + lifecycle below.
**Supersedes:** the "Cass gets Hermes tools / gemini tool-calling" framing in `L1-brain-design.md`
(line 103) and SESSION's L2 sketch. That was the wrong plane — see §0.

---

## §0 — Reframe: two planes, gemini tool-calling is NOT the execution model

The earlier plan said "register run_audit/run_module as Hermes tools so the gemini agent calls them."
**Wrong lens.** PRISM execution is **multi-agent orchestration**, not one LLM emitting tool calls.

- **Conversational plane (Cass):** a human says "run an audit on petsmart.com." Cass only needs to
  *kick off* a run and narrate it. That trigger is tiny — the plugin already does content-detection
  (it binds reports that way) and can POST to the orchestrator the same way. **No gemini tool-calling
  needed.** Cass is a thin front, not the orchestrator.
- **Execution plane (this doc):** a deterministic controller spawns purpose-built agents, each owning
  a task + its skill(s), then dispatches / monitors / finishes / QA-gates / sequences them. Gemini is
  absent. Most agents aren't LLMs at all.

The existing `run_pipeline` (committed `c54fc3e`) is the **orchestrator skeleton** (dispatch + monitor
hook + finish + intel-company abort gate). Its weakness: today every "worker" is a single Perplexity
call (`run_module`) — NOT a purpose-built agent executing its own skill. Closing that is L2's core.

---

## §1 — Locked decision: hybrid runtime routing

Each task runs on the **cheapest runtime that can actually do it** (the model-economics rule applied
to the audit pipeline). Three tiers:

| Tier | Runtime | What it is | Cost |
|---|---|---|---|
| **Script** | pure Python function (collector) | deterministic — Playwright packet scan, API/MCP pull, template. No LLM. | $0 |
| **Research** | playbook → Perplexity (`AgentAPIClient`) | one grounded web-research+synthesis call. | cheap (Perplexity key) |
| **Heavy** | `claude-cli` subprocess running the real skill | full agentic — executes the skill's scripts + reasoning + MCP + Playwright. | Anthropic credit |

**Payoff:** waves 1 + 3–5 (minus browser) run on Script + Research only → **zero Anthropic credit**.
Only browser-testing and the rendered report need Heavy. So a "data + research" audit ships on the
Perplexity key alone; Heavy agents bolt on when credit is approved. → a `--no-heavy` audit mode.

---

## §2 — Worker-agent roster (grounded in the registry — 17 handles + 3 unbuilt)

Registry has **17 module handles**. 5 have deterministic collectors today: intel-competitors,
intel-partner, intel-queries, intel-investor, intel-social. **`audit-browser`, `audit-factcheck`,
`insights-engine` are in the wave plan but have NO handle** → they'd fail as "Unknown module." Roster:

### Script tier ($0) — convert these from LLM-playbook to script-first
| Agent | Task | Skill / source | Has collector? | Key needed |
|---|---|---|---|---|
| tech-stack | detect client-side stack | `detect-tech` (Playwright packet) | no — build | none |
| traffic | visits/engagement | SimilarWeb API + screenshot | no — build | SimilarWeb (#15) |
| financial-public | revenue/EBITDA | Yahoo Finance MCP | no — build | none |
| news | recent signals | Apify Google-News | no — build | Apify |
| social | LinkedIn/X posts | Apify | yes | Apify |
| partner | co-sell overlap | Crossbeam | yes | Crossbeam |
| queries | test query set | template from traffic keywords | yes | none |

### Research tier (Perplexity, cheap)
| Agent | Task | Notes | Has collector? |
|---|---|---|---|
| company-context | seed (competitors/execs/industry) | 3-track: WebFetch + Perplexity + synthesis (already special) | no (justified pure-LLM seed) |
| industry | vertical benchmarks | synthesis | no |
| competitors | who + what search vendor | `detect-search` on rivals (collector) + synthesis | yes |
| investor | exec quotes | transcript fetch (collector) + extraction | yes |
| hiring | ICP roles | careers fetch (`fetcher.py`) + classify | via fetcher |
| financial-private | revenue estimate | 6-source waterfall | no |

### Heavy tier (claude-cli, credit) — incl. the 3 unbuilt
| Agent | Task | Skill | State |
|---|---|---|---|
| browser-test | live SAYT/NLP/typo testing + screenshots | `algolia-audit-browser` (Playwright stealth) | **unbuilt handle** |
| factcheck | QA gate over collected data | `algolia-audit-factcheck` | **unbuilt handle** |
| insights | patterns/benchmarks from validated data | `insights-engine` | **unbuilt handle** |
| report | render deck + landing + PDF | `algolia-audit-report` | handle exists; rendering heavy |
| business-case | ROI model | mostly deterministic calc + light LLM | handle exists |
| sales-plays | AE/BDR playbook | LLM synthesis (Perplexity ok) | handle exists |
| campaign-abx | email/LinkedIn/Loom | LLM synthesis | handle exists |

---

## §3 — Runtime routing mechanism (the key new piece)

The orchestrator picks a runner per module from a **declared runtime tier**. My injectable `runner`
in `run_pipeline` is already the extension point — instead of one global runner, route per module.

1. **Declare tier in the registry** — add `runtime: Literal["script","research","heavy"]` to
   `ModuleHandle` (default `"research"` to preserve today's behavior). Script-tier modules also
   declare their `collector` as the *whole* job (no playbook call).
2. **A runner per tier** (each satisfies the `ModuleRunner` protocol — `async (RunModuleInput) -> dict`):
   - `script_runner` — run the collector only; validate + return. No `AgentAPIClient`.
   - `research_runner` — today's `run_module` (collector optional + playbook→Perplexity). Default.
   - `heavy_runner` — spawn `claude-cli` with the skill + inputs; capture structured stdout; validate.
3. **Dispatch** — `run_pipeline` looks up `handle.runtime` → picks the runner. One-line change to the
   per-module call; the wave/gate/monitor logic is untouched.
4. **`check_fn` per runner** — script needs its key (e.g. SimilarWeb) or it returns `no_data` (never
   fabricates); research needs Perplexity; heavy needs Anthropic credit + claude-cli present. Missing
   prerequisite → module returns `skipped`/`no_data`, audit degrades gracefully (not crash).

---

## §4 — Lifecycle services ("build all of that")

| Concern | Mechanism | State |
|---|---|---|
| **Dispatch** | orchestrator routes task → runner by tier (§3) | skeleton exists; routing new |
| **Monitor** | `on_progress` callback → SSE on `/audits/{id}/stream` (`audit_stream.py`) + heartbeat per heavy agent | hook exists; SSE wiring new |
| **Finish** | collect output → Pydantic-validate (`output_schema`) → `persist_result` | exists |
| **QA-check** | factcheck (wave 3) returns PROCEED/WARN/BLOCKED → **gate**: BLOCKED stops deliverable waves 5–6 | wave runs; gate not wired |
| **Orchestrate** | wave dependency order + sub-waves + intel-company abort gate | exists (`run_pipeline`) |
| **Retry/abort** | per-module try/except → `failed` (non-fatal except intel-company); heavy agents get N retries | partial |
| **Capabilities manifest** | per-module: what it does, when to invoke, runtime tier, cost, key dep — for Cass + the router | new (derive from registry + this doc) |

---

## §5 — How Cass triggers a run (conversational → execution bridge)

No gemini tool-calling. When the message intent is "run an audit / refresh X":
- The plugin detects intent + domain (same content-match it already uses for report binding) and
  `POST /api/v1/audits/{id}/run-local` (creating the audit first if needed).
- Returns immediately (202). Cass says "started — I'll track it." She polls `GET /audits/{id}` (or
  the SSE stream) and narrates progress / surfaces the finished report.
- This keeps Cass a thin conversational front over the deterministic orchestrator.

---

## §6 — Build order (incremental, $0 until Heavy)

1. **Runtime routing layer** ($0, now): add `runtime` to `ModuleHandle`; build `script_runner` +
   `heavy_runner` (research = existing); route in `run_pipeline`. TDD the router (which tier → which
   runner, check_fn gating). *No live keys needed to unit-test.*
2. **Convert script-tier modules** (incremental): wire collectors as the whole job for tech-stack,
   traffic, financial-public, news (the obvious deterministic ones). Each = one collector + test.
3. **Build the 3 missing handles** — factcheck (QA gate), insights, browser — as heavy agents.
   Factcheck first (it's the QA gate everything downstream trusts).
4. **QA gate wiring** — factcheck verdict BLOCKED → skip waves 5–6.
5. **SSE monitor** — per-agent progress events on the existing stream.
6. **Capabilities manifest** — generate from registry + tiers; expose for Cass + router.
7. **Cass trigger** — plugin intent-detection → `/run-local`.
8. **Flip live** — Perplexity key (research tier) → then claude-cli credit (heavy tier, deferred).

---

## §7 — Open questions / decisions still needed
- **Heavy runtime = claude-cli subprocess on the VPS executor** (`/opt/prism-executor`, per memory
  `project-prism-vps-executor`) vs Hermes-native sub-agent spawn? claude-cli is proven (skills run
  there); Hermes sub-agents unverified. → default claude-cli; revisit if Hermes spawn is cleaner.
- **Per-heavy-agent isolation** — each claude-cli run in its own workdir; concurrency cap (don't
  spawn 13 at once). Wave parallelism already bounds this somewhat.
- **factcheck/insights/browser** skills exist in arijit-skills — the heavy_runner invokes them by
  name; need the input/output contract per skill (read receipt before wiring each).
- **Cost guard** — heavy agents are the only credit spend; a per-audit budget cap + `--no-heavy` mode.
