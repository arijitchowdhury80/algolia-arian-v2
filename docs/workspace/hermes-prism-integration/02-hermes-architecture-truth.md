# Hermes Architecture Truth — Can it run Claude skills?

Date: 2026-06-27
Author: research agent (PRISM/PIP)
Question driving this: **Can the Hermes agent execute Claude skills (SKILL.md + the Skill tool) — natively, or only if re-plumbed?**

---

## TL;DR verdict

**Hermes is NOT a custom build. It is [Hermes Agent by Nous Research](https://github.com/NousResearch/hermes-agent) — a third-party, terminal-native Python agent runtime.** "Chowmes" is just Arijit's deployment of it on a Hostinger VPS, fronted by Telegram. "Mallory/Athena" are personas (SOUL.md), not code.

On the load-bearing question, the answer has two layers:

1. **Hermes has its own native skills system that uses the SAME `SKILL.md` format** as Claude Code, and it is explicitly **agentskills.io-compatible**. It can be pointed at the Claude skills directory via `external_dirs`. So Hermes can *load and follow* a SKILL.md natively.
2. **BUT Hermes's skill engine is NOT the Claude `Skill` tool.** It is a different mechanism (`skills_list` / `skill_view` / slash commands / `skill_manage`). The algolia skills are not just instructions — they orchestrate **sub-agents via the Claude `Agent`/`Task` tool**, call **named `mcp__*` tools**, and run **Deno/Playwright scripts**. Those are Claude-Code-runtime-specific. Hermes loading the SKILL.md text does not give it those tools.

**Bottom-line gap: MODERATE.** The clean path is NOT "make Hermes natively re-implement the Skill tool." It is the **CONTROL/EXECUTION split**: Hermes is the control plane (Telegram chat, identity, queue, gating, delivery); it shells out to a **headless Claude (`claude` CLI / Agent SDK)** as the execution plane that runs the 22 algolia-* skills with their MCP + browser tooling. Hermes officially supports driving Claude Code as a child process, so the mechanism is *available*. What's missing is building it (queue, gates, residential-IP browser runner, data store).

> ⚠️ **CORRECTION (2026-06-27, verified by reading `../ChowMes/SESSION.md` directly).** An earlier draft of this line said the split was "already prototyped — Arijit ran a full PetSmart audit this exact way." **That was an overclaim.** The truth: the PetSmart audit is real, published (`algolia-arian-v2.vercel.app/petsmart/`), factchecked PROCEED 9.2, eval 10/10 — but it was run **MANUALLY in Claude Code** (skills executed by hand); Hermes/Athena only produced the executive verdict at the end. The control/execution split is **DESIGNED (decided 2026-06-19), NOT BUILT** — that SESSION explicitly says "Do NOT jump to building" and flags "refine 'Hermes spawns Claude' → queue + workers." So: the *skills* are proven; *Hermes orchestrating them end-to-end* is unproven.

---

## What Hermes actually IS (evidence)

Source: local docs snapshot at `/Users/arijitchowdhury/Dropbox/AI-Development/Personal/ChowMes/reference/hermes-agent-docs/` (llms.txt, llms-full.txt — a verbatim copy of https://hermes-agent.nousresearch.com/docs).

- **Product / vendor:** `reference/hermes-agent-docs/llms.txt:1-3` —
  > "# Hermes Agent > The self-improving AI agent built by Nous Research. A terminal-native autonomous coding and task agent with persistent memory, agent-created skills, and a messaging gateway... Runs on local, Docker, SSH, Daytona, Modal, or Singularity backends. Works with Nous Portal, OpenRouter, OpenAI, Anthropic, Google, or any OpenAI-compatible endpoint."
  Repo: `github.com/NousResearch/hermes-agent`. Install via curl script. **It is an off-the-shelf agent framework, not a bespoke loop.**
- **Language / runtime:** Python (`uv pip install -e ".[mcp]"`, `AIAgent` Python class, "Use Hermes as a Python Library"). Not LangGraph, not a hand-rolled loop. (`llms.txt` Developer Guide → Agent Loop / Architecture; `llms-full.txt` MCP section.)
- **"Chowmes" = the deployment.** `../ChowMes/README.md:1-5` calls it "Arijit's private Hermes Agent workspace." `../ChowMes/CHOWMES.md:1-3`: "Chowmes is the Hostinger VPS running Hermes Agent for Telegram and agent work."
- **The Dropbox "Hermes" workspace has NO source code** — it is markdown source-of-truth (SOUL/USER/MEMORY/WORK_OS/PROJECTS) plus two SKILL.md skills. The runtime lives on the VPS in Docker.
  - NOTE: the path in the task prompt (`GoogleDrive-arijit.chowdhury@gmail.com/My Drive/AI-Projects/Hermes`) is **not mounted on this machine** — only the algolia.com Drive is. The actual local copies are `/Users/arijitchowdhury/Dropbox/AI-Development/Personal/Hermes` and `.../Personal/ChowMes`. I did NOT SSH the VPS; all findings are from local docs + runbooks.

---

## Answers to the six questions

### 1. What is Hermes built on?
**Hermes Agent (Nous Research), a Python agent framework.** Not Claude Agent SDK, not Claude Code, not a custom LangGraph loop. Evidence: `reference/hermes-agent-docs/llms.txt:1-7`; Developer Guide entries for "Agent Loop (AIAgent execution)", "Architecture", "Use Hermes as a Python Library (embed AIAgent)". It is provider-agnostic and currently wired to **OpenRouter** (see Q3).

### 2. Does it have a concept of "skills" / a Skill tool / dynamic instruction-loading?
**Yes — a full, mature skills system. This is the single most important finding.**
- Same `SKILL.md` format as Claude Code: YAML frontmatter (`name`, `description`, optional `metadata.hermes.*`) + markdown body, with `references/`, `scripts/`, `templates/`, `assets/` subdirs. (`llms-full.txt` "SKILL.md Format", "Skill Directory Structure".)
- **Explicitly agentskills.io-compatible** (the open skill standard): `llms-full.txt:7888`, `:8113` — "compatible with the agentskills.io open standard."
- **Progressive disclosure** via tools `skills_list()` → `skill_view(name)` → `skill_view(name, path)` (`llms-full.txt:8183-8185`). This is Hermes's analogue of Claude's `Skill` tool — **different tool names, same idea.**
- **Each skill is auto-exposed as a `/slash-command`** and is also reachable through natural conversation.
- **External skill directories:** `skills.external_dirs` in `config.yaml` lets Hermes scan folders outside `~/.hermes/skills/` — the docs explicitly mention "a shared `~/.agents/skills/` directory used by multiple AI tools." External skills get "full integration… no different from local skills." (`llms-full.txt:8330-8376`.) **This is the hook for pointing Hermes at the Claude skills.**
- It also has `skill_manage` (agent writes/edits its own skills) and a Curator for lifecycle. (`llms-full.txt:8482+`, `:8967+`.)
- **It also loads `CLAUDE.md` as a context file** (`llms-full.txt:4817`, `:4823`: priority `.hermes.md` → `AGENTS.md` → `CLAUDE.md` → `.cursorrules`).

**The catch (do not gloss over this):** Hermes loading a SKILL.md ≠ Hermes having the tools that skill calls. The Claude `Skill` tool and Hermes's `skill_view` are different runtimes. The algolia skills depend on:
  - the Claude **`Agent`/`Task` tool** for sub-agent fan-out (the orchestrator `algolia-search-audit/SKILL.md` says: "spawns agents — one per module… Every module runs in its own isolated Agent… using the Skill tool internally");
  - **named `mcp__*` tools** (algolia, apify, builtwith, yahoo-finance, chrome) bound by name in the Claude harness;
  - **Deno + Playwright scripts** (`scripts/render-audit.ts`, browser stealth).
  Hermes has equivalents (delegation, MCP, browser, terminal) but **not the same tool names/contract**, so the skills would not run verbatim under Hermes's own engine without rework.

### 3. What LLM/provider, and how are tools/MCP wired in?
- **Provider: OpenRouter** (default). Live model `deepseek/deepseek-v4-pro`, context `131072`, web backend `parallel`. Frontier escalation `anthropic/claude-sonnet-4.6`; boardroom `anthropic/claude-opus-4.8`. (`../ChowMes/CHOWMES.md` "Current live snapshot" + "Current model setup", verified 2026-06-26.) DeepSeek V4 Pro is **text-only on OpenRouter** → Gemini 2.5 Flash is the vision fallback.
- **MCP: fully supported.** `mcp_servers:` block in `~/.hermes/config.yaml`, stdio + remote HTTP, auto-discovery at startup, per-server tool filtering, plus a curated `hermes mcp` catalog. (`llms-full.txt` MCP section.) **So the algolia MCP backends (algolia, apify, etc.) can be attached to Hermes** — but they'd appear as `mcp-<server>` tools with Hermes naming, not the `mcp__algolia__*` names the skills hardcode.
- **Native tools (toolsets):** web (`web_search`, `web_extract`), Terminal & Files (`terminal`, `process`, `read_file`, `patch`), **Browser (`browser_navigate`, `browser_snapshot`, `browser_vision`)**, Agent orchestration (`todo`, `clarify`, `execute_code`, `delegate_task`). (`llms-full.txt` Tools & Toolsets.) Terminal backend can be a **persistent Docker container** or SSH/Modal/Singularity.
- **Crucially, terminal supports `pty=true` for "interactive CLI tools like Codex and Claude Code"** (`llms-full.txt:8096`, also `:3126`, `:5941` list `Claude Code` and `Codex` as external CLIs Hermes drives). **This is the official, supported way Hermes runs Claude Code as a child process** — i.e., the EXECUTION plane.

### 4. Chat interface? Mobile access?
**Yes, and this is Hermes's strongest card.** Messaging gateway on 21+ platforms; **Telegram is live and configured** (`../ChowMes/CHOWMES.md`: "Default Athena gateway running"). Telegram is mobile-native → Arijit already has a phone chat surface to Mallory/Athena with no UI to build. Operator tools enabled on Telegram: web, terminal, file, vision, skills, todo, memory, clarify, cronjob (approved 2026-06-16, `max_turns: 12`). Also CLI/TUI, voice mode, and an OpenAI-compatible API server.

### 5. What runs on the VPS vs locally?
On the VPS (`chowmes`, verified 2026-06-26, `../ChowMes/CHOWMES.md`):
- Docker containers: **`hermes`, `caddy`, `scout`, `temporal`, `temporal-ui`, `temporal-db`, `ac2-lab-backend`.**
- Public ports 22/80/443; local-only: Hermes dashboard `127.0.0.1:9119`, **Temporal `7233`**, Temporal UI `8088`, **Scout `8421`**, AC2 lab `8787`.
- **PRISM's own infra (Scout + Temporal) is ALREADY co-located on the same box as Hermes.** That is a strong integration argument.
Locally (Mac): the markdown source-of-truth, the Claude skills (`~/.claude/skills/algolia-*`), the algolia hub repo, and — per SESSION.md — the **residential-IP browser runs** (the only place stealth Playwright currently survives WAFs).
Browser/Playwright: Hermes has its own browser toolset (Tool Gateway or local); the algolia audit's Playwright stealth currently runs from Arijit's Mac (datacenter-IP blocking is the #1 risk, see below).

### 6. Bottom-line gap to "Hermes runs the algolia-* skills and generates the report"
**MODERATE, not large, not trivial — and a working prototype already exists.**

The decisive evidence is `../ChowMes/SESSION.md` ("DONE THIS RUN — PetSmart Algolia Search Audit: COMPLETE & PUBLISHED"). It documents:
- The intended architecture, verbatim:
  > "CONTROL = Hermes: per-rep identity, intent parse, job queue, progress msgs, gating verdicts, delivery. EXECUTION = headless Claude (`claude` CLI / Agent SDK) + 22 algolia skills + MCP, as disposable context-isolated workers. DATA = persisted deal-intelligence object."
- A real run: a full PetSmart audit (score 5.8, factcheck PROCEED 9.2, eval 10.0) was produced and published to Vercel, with Athena (Hermes `default` profile) doing the boardroom verdict, invoked via:
  `ssh ... 'sudo docker exec -u 10000 -i hermes hermes -p default -z "..."'`.

So the integration is **not a from-scratch skill-execution build**. It is a **plumbing + productization** job:

What's required (moderate):
1. **Execution plane:** run headless Claude (`claude` CLI / Agent SDK) as the worker that actually executes the algolia skills with their `mcp__*` tools + Playwright. Hermes drives it via `terminal pty=true` / `docker exec` / SSH. (Already proven manually.)
2. **MCP plumbing:** the worker needs the algolia MCP servers + keys wired into its environment (whether that worker runs on the Mac or the VPS).
3. **Browser/WAF:** solve the #1 risk — datacenter-IP browser runs get blocked (Akamai/Cloudflare); stealth only worked from Arijit's residential Mac. Needs a residential-IP runner or proxies, or a "degraded-and-flagged" mode. (SESSION.md "Top holes #1".)
4. **Control plane:** Telegram intent parse → job queue → progress messages → **gating verdicts** (Discovery-OS hard preconditions: confidence scoring, evidence URLs, human-review queue, design-verify gate) → delivery. Telegram can't carry secrets (Algolia analytics keys) — needs a vault/non-chat path.
5. **Data store:** the persisted deal-intelligence object reused across reps/roles.

What is explicitly NOT needed:
- Building a skill-execution engine from scratch (Hermes has one; and the proven path uses Claude's engine as the worker anyway).
- Replacing Hermes (it is the right control/chat/mobile layer — Telegram + personas + cron + memory).
- A new UI (Telegram is the surface).

The honest framing: **the hard, novel work left is gates + residential browser + queue/data store**, not "can Hermes run a skill." Per SESSION.md's own closing line: *"The engine/gates/Discovery-module/Telegram architecture is DESIGN-ONLY (brainstorm). Nothing built."* The PetSmart run was a **manual, hand-driven** proof, not an automated pipeline.

---

## Two candidate architectures (for the decision this drives)

**A. Hermes-native (port skills to Hermes's engine).** Point Hermes `external_dirs` at the Claude skills, or rewrite them as Hermes skills; attach algolia MCP servers; use Hermes's own browser/delegation. *Cost:* rewrite ~22 skills' tool calls (`Agent`/`Task` → `delegate_task`, `mcp__algolia__*` → Hermes MCP names, Deno render scripts via terminal). High rework, loses the maturity already baked into the Claude skills, re-tests everything. **Not recommended.**

**B. Control/Execution split (proven).** Hermes = control plane on Telegram; headless Claude = execution plane running the algolia skills unchanged. *Cost:* queue + gates + browser-IP + data store + secret handling. Skills run **as-is**; all the audit-quality engineering is preserved. **This is what Arijit already prototyped and what the design notes assume.**

Recommendation for the downstream architecture decision: **B.** The load-bearing question "can Hermes execute Claude skills natively" is technically *yes-ish* (same format, agentskills.io, external_dirs), but the **pragmatically correct answer is to NOT make Hermes execute them itself** — let it orchestrate a headless Claude that does. Hermes's job is the parts it's uniquely good at: mobile chat, identity, scheduling, memory, gating, delivery.

---

## Confidence & gaps

- HIGH confidence on what Hermes is, its skills/MCP/tool model, provider, and Telegram surface — all from the verbatim official docs snapshot.
- HIGH confidence on live VPS state and the PetSmart prototype — from dated, "verified live" runbooks (`CHOWMES.md` 2026-06-26, `SESSION.md`).
- NOT verified by me (did not SSH): exact current `config.yaml`, whether any algolia MCP servers are presently attached to the Hermes container, and whether the PetSmart worker ran on the Mac or VPS. These are checkable on the box but do not change the verdict.
- The gmail-Drive "Hermes" path from the task prompt is not mounted here; I used the Dropbox `Personal/Hermes` + `Personal/ChowMes` copies, which the handoff doc names as the sibling source-of-truth.
