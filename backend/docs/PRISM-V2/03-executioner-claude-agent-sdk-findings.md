# PRISM V2 — Executioner Candidate: Claude Agent SDK (findings, live-probed)

Started: 2026-07-05. Read `_status.md` and `00-manifesto.md` first. This document applies the same rigor Phase 1 gave Agent Studio (live probe, not docs-reading) to the Claude Agent SDK, per Arijit's explicit ask this session.

## 0. Naming disambiguation (important — two different products share "agent" branding)

Anthropic ships **two** things that could be meant by "Claude Agent SDK." They are not the same product and were evaluated separately:

1. **Claude Agent SDK** (`pip install claude-agent-sdk` / `@anthropic-ai/claude-agent-sdk`) — an open-source, **self-hosted** library that wraps the Claude Code CLI subprocess. You run it on your own infrastructure (i.e. the VPS). This is the one live-probed below — it fits PRISM's existing model (VPS-hosted, `claude-cli` already invokes the algolia-* skills today).
2. **Managed Agents API** (`/v1/agents`, `/v1/sessions`, beta `managed-agents-2026-04-01`) — Anthropic-hosted: Anthropic runs the agent loop AND the container. Found via the `claude-api` skill this session, not previously in Phase 1 scope. Session status lifecycle (`idle`/`running`/`rescheduling`/`terminated`), multi-agent coordinator/subagent threads, Outcomes (rubric-graded iterate-until-pass loop), memory stores, webhooks, scheduled deployments (cron) all exist natively. This is a **second, independently viable candidate** that wasn't on Arijit's original 4-way list (Temporal / Agent Studio / Claude Agent SDK / no-engine) — flagging it as a 5th option, not folding it into the Agent SDK findings, because the two have materially different operational models (self-hosted vs Anthropic-hosted).

Both are documented here since both are real candidates. Recommendation section addresses each.

## 1. Method — how this was actually verified (not recalled from training)

`pip install claude-agent-sdk` in a clean venv (`/private/tmp/.../scratchpad/agentsdk-test`), confirmed version **0.2.110**, then read the actual installed source (`inspect.getsource`) for the classes claimed below — not the public docs, the shipped code. No `ANTHROPIC_API_KEY` was available in this session, so **no live session was actually run** — this is a capability-surface audit (what the SDK exposes and how it's documented in its own docstrings), not an end-to-end functional test. That gap is flagged explicitly in §4.

## 2. Executioner requirements (from `00-manifesto.md`, non-negotiable)

> run audits, check interim status, report updates, control the system end-to-end, and run mandatory factcheck + quality-check gates at the end of every skill run

## 3. Capability-by-capability findings

### 3.1 Multi-step workflow control — YES, real primitives found
- `ClaudeAgentOptions`: `max_turns`, `max_budget_usd` (stops the query and returns `error_max_budget_usd` on overrun), `resume` / `continue_conversation` / `session_id` / `fork_session` for session control, `permission_mode` (`default`/`acceptEdits`/`bypassPermissions`/`plan`/`dontAsk`).
- `query()` (stateless, fire-and-forget — good fit for "run one audit module") vs `ClaudeSDKClient` (stateful, bidirectional, interruptible — good fit for a long-lived orchestrator session).
- **This maps directly onto PRISM's existing per-skill claude-cli invocation pattern** — not a rebuild, an upgrade of the same mechanism.

### 3.2 Subagent dispatch — YES
- `AgentDefinition` dataclass: per-subagent `model` (alias or full ID), `tools`/`disallowedTools`, `skills`, `memory` scope (`user`/`project`/`local`), `mcpServers`, `background: bool`, `effort` level, `permissionMode`. This is a real per-subagent config surface, not a single shared config.
- `list_subagents()` / `get_subagent_messages()` — host-side introspection into what subagents ran and what they said.
- `SubagentStartHookInput` / `SubagentStopHookInput` hooks fire on subagent lifecycle boundaries with `agent_id` / `agent_type` / `agent_transcript_path`.
- Maps cleanly onto PRISM V2 Phase 2's "Researcher / Audit / Synthesizer agent" vision — each could be an `AgentDefinition`.

### 3.3 State persistence across steps — YES, and it's the standout finding
- `SessionStore` is a **Protocol** (duck-typed adapter), not a fixed backend — you implement `append()` (mirror transcript entries after each local write) and `load()` (rehydrate for resume); `list_sessions()` / `list_session_summaries()` are optional.
- Docstring confirms this is designed for exactly PRISM's situation: "adapter receives a secondary copy... implement TTL, object-storage lifecycle policies... according to your compliance requirements." Failed mirror writes retry 3x with backoff before surfacing a `MirrorErrorMessage` — durability is decoupled from the local subprocess write, which already succeeded.
- **Direct implication for PRISM**: this could be backed by the same Postgres instance PRISM already runs (`:55432`, per memory `project-prism-local-instance-persistent-db`) — no new datastore needed, and it directly answers the Phase 1 "Algolia-as-DB weak for executioner state-tracking" gap without requiring Temporal.

### 3.4 Retries — PARTIAL, real gap identified
- `RateLimitInfo` / `RateLimitEvent`: real-time signal on rate-limit status (`allowed` / `allowed_warning` / `rejected`) across 5 windows (`five_hour`/`seven_day`/`seven_day_opus`/`seven_day_sonnet`/`overage`) with `utilization` and `resets_at`. This lets an orchestrator back off *before* hitting a hard limit.
- **What's missing**: there is no durable, automatic "retry this failed task with exponential backoff across process restarts" primitive — that's Temporal's core value proposition (durable execution). The SDK gives you the *signals* (task status = `failed`, rate-limit = `rejected`) but the retry *policy engine* is something PRISM's own orchestrator code would still have to build, same as today.
- **This is the sharpest real trade-off vs Temporal** and should weigh directly on the final decision.

### 3.5 Status tracking / interim updates / reporting — YES, strong
- Task lifecycle is modeled explicitly: `TaskStartedMessage` → `TaskProgressMessage` (carries `usage`, `last_tool_name`) → terminal via **either** `TaskNotificationMessage` (`status: completed|failed|stopped`) **or** `TaskUpdatedMessage` (`patch.status`, wider set: `pending|running|paused|completed|failed|killed`). `TERMINAL_TASK_STATUSES = frozenset({'completed','failed','killed','stopped'})` is exported so consumers don't hardcode the set.
- The SDK's own docstring flags a real subtlety worth remembering if this gets built: a killed background task's terminal state can arrive **only** via `TaskUpdatedMessage` with no matching `TaskNotificationMessage` — code that only watches notifications will miss it. (Logged here so it isn't rediscovered the hard way later.)
- `background: bool` on `AgentDefinition` plus these messages = a real async job model, not just synchronous request/response.

### 3.6 Mandatory factcheck + quality-check gate after every skill run — YES, directly implementable
- Hooks (`PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `Stop`, `SubagentStart`, `SubagentStop`) are **not just observational** — `SyncHookJSONOutput` supports `decision: "block"` plus a `reason` fed back to Claude, and `hookSpecificOutput` for finer per-event control (e.g. `permissionDecision` on `PreToolUse`).
- Concretely: wire a `SubagentStop` hook on every skill-module subagent that runs `algolia-audit-factcheck` / `validate-json-schema.py` / `algolia-audit-eval` and returns `decision: "block"` if the gate fails. This is the exact mechanism the manifesto calls for ("mandatory factcheck + quality-check gate after EVERY module run, not just once at the end" — see `00-manifesto.md` Phase 2 task list) — and it's a **native hook**, not a bolted-on wrapper PRISM has to invent.

## 4. What is NOT yet verified (honest gap — no fabricated conclusions)

- **No live session was actually run.** Everything above is a static/source-level audit of a locally-installed package, not a functional test of a real multi-agent PRISM-shaped workflow end to end. Needs: `ANTHROPIC_API_KEY` (not present this session), then a small proof-of-concept — one `AgentDefinition` per PRISM skill-group, a `SessionStore` backed by the existing Postgres, a `SubagentStop` hook running the factcheck gate — run against one real company end-to-end.
- **Retry/durable-execution story is unverified beyond "the primitive isn't there."** Whether PRISM needs Temporal-grade durable execution (survives process crash mid-task, automatic resumption) or whether "orchestrator restarts + `resume=session_id`" is good enough in practice is an open empirical question, not yet tested.
- **Managed Agents API (§0, item 2) has NOT been live-probed at all this session** — found via docs only. If it stays in contention, it needs the same live-probe treatment (it also can't be tested without an API key + beta access).
- **Cost/ops model untested** — self-hosted Claude Agent SDK runs on the VPS process model PRISM already has (known ops cost); Managed Agents API shifts to Anthropic-hosted containers (new, unverified pricing/latency shape for PRISM's use case).

## 5. Where this leaves the 4-way (now effectively 5-way) decision

| Candidate | Multi-step control | Subagent dispatch | State persistence | Retries | Status tracking | Mandatory gates | Ops model |
|---|---|---|---|---|---|---|---|
| **Temporal** | Native (durable workflows) | Via activities | Native (event-sourced) | Native, durable | Native | Would build on top | Self-hosted, new infra for PRISM |
| **Agent Studio** | None (confirmed 404 on orchestration endpoints, Phase 1) | None native | N/A | N/A | N/A | N/A | Hosted, but not fit for this role |
| **Claude Agent SDK** (this doc) | Yes, real primitives | Yes, `AgentDefinition` + hooks | Yes, pluggable `SessionStore` | Signals only, no durable retry | Yes, explicit task lifecycle | Yes, native hooks with block | Self-hosted, same VPS model as today |
| **Managed Agents API** (found this session, unverified) | Yes, sessions + events | Yes, native multiagent coordinator | Yes, memory stores | Unclear — not checked | Yes, session status + webhooks | Yes, Outcomes (rubric grader) | Anthropic-hosted, new ops model |
| **No engine (in-process)** | Manual | Manual | Manual | Manual | Manual | Manual | None — status quo, effectively what Hermes was doing badly |

**Working read, not a final call (Arijit's decision per the manifesto's own rule):** the Claude Agent SDK is the first candidate that satisfies every stated requirement with a *named, inspected primitive* rather than "would have to build it" — and it does so on PRISM's existing self-hosted/VPS/Postgres model, which is the smallest operational delta from today. Its one real gap (durable retry) is exactly Temporal's strength, which raises a legitimate hybrid question: **Claude Agent SDK as the agent/subagent/gating layer, with a thin Temporal (or even just systemd + Postgres job table, which is closer to what Cassandra's `prism-runner.py` already does) layer underneath purely for durable retry/scheduling** — rather than an either/or. That composition question, and the live end-to-end proof-of-concept in §4, are the two things that should happen before writing the ADR.

## 6. Immediate next step if this thread continues

1. Get an `ANTHROPIC_API_KEY` provisioned for a throwaway test (separate from the Claude Code subscription auth already in use).
2. Build the smallest possible proof-of-concept: one real algolia-* skill wrapped as an `AgentDefinition`, a `SessionStore` backed by the existing local Postgres (`:55432`), a `SubagentStop` hook running `algolia-audit-factcheck` as the mandatory gate.
3. Only then write the ADR — this document is evidence for that decision, not the decision itself.
