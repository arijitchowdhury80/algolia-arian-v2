# SESSION.md — PRISM (= Chowmes-PRISM)

**Last updated:** 2026-06-28 (unify+audit spike)
**Status:** **Chowmes-PRISM LIVE; grounded report-QA VERIFIED.** This session: 4-thread spike done —
skills HARDENED+committed+pushed (arijit-skills a9db07a; dead scripts wired, 5 bugs fixed, Scout
only-in-industry), public-repo key leak SCRUBBED from history, Hermes fat-audit (18.3 GB reclaimed),
self-learning loop confirmed ON+staged, W-A executor synced + browser-plane proven + scaffold ready,
W-D fully designed. **Full spike record: `docs/workspace/hermes-prism-integration/spike-unify-audit/`
(A–J). The finish runbook is `spike-unify-audit/J-RESUME-RUNBOOK.md` — start there.**

> ⚠️ Headless work hit the permission gate (file deletes/commit/push) + missing secrets. The PIP
> cleanup is PREPARED (.gitignore fixed) but the deletes+commit+push must be RUN by the user (J §1–2).

> **NAMING CANON:** "PRISM"/"prism" = **Chowmes-PRISM** only — the dedicated Hermes agent instance on
> the VPS. NOT the old custom-SaaS idea, NOT the personal Chowmes/Athena agent.

---

## RESUME ACTION (do this first, next session)
1. Read this file fully, then memory `MEMORY.md` (esp. `[[reference-prism-means-chowmes-prism]]`,
   `[[project-prism-hermes-direction]]`, `[[reference-skills-symlinked-to-repo]]`, and the 5 feedback
   findings).
2. Read the project plan: `docs/workspace/hermes-prism-integration/03-plan.md` (workstreams W-A..W-F)
   and `_status.md` in that folder.
3. Check the two pending USER actions (below) — they gate the next build.
4. Continue from "REMAINING WORK".

## PENDING USER ACTIONS (gate progress) — all in J-RESUME-RUNBOOK.md
- **🚨 (0) ROTATE the exposed keys.** arijit-skills is PUBLIC; old BuiltWith+SimilarWeb keys were in
  history (scrubbed+force-pushed, but assume scraped). Rotate at both dashboards NOW. (task #15)
- **(1) Run the PIP cleanup + clean push** — gated headless. J §1–2 (deletes restore canonical docs,
  drop TEMP/junk, `git rm CHECKPOINT.md`, then commit+push the private `prism` repo, latest-only).
- **(A) Anthropic account credits.** Executor key loaded+valid on VPS but balance low. Generation
  (W-A) can't run until topped up at console.anthropic.com.
- **(2) W-A finish:** fill `/opt/prism-executor/.mcp.json` (algolia/builtwith/yahoo) + `.mcp.env` keys
  (ALGOLIA_APP_ID/KEY, BUILTWITH, APIFY) → `cd /opt/prism-executor && ./run-audit.sh petsmart.com`. (J §3)
- **(3) W-D build:** deploy FastAPI on VPS (R1) → enable Hermes API → SPA proxy → identity map → e2e.
  Full checklist in `spike-unify-audit/G-wd-design.md`; sequence in J §4.
- **(B) Try the live bot.** DM `prism_bot` (id 8870557089), e.g. "For PetSmart, what's their
  no-results rate?" — should answer grounded.

---

## WHAT IS BUILT + LIVE (verified this session)
- **Chowmes-PRISM instance**: separate Hermes Docker container `hermes-prism` on the VPS
  (72.61.72.147). Volume `/root/.hermes-prism` → container `/opt/data`. Dashboard 127.0.0.1:9120.
  Telegram connected (bot id 8870557089). Model = **gemini-2.5-flash direct** (paid Gemini key, in
  `/root/.hermes-prism/.env`). Compose: `/opt/chowmes-prism/docker-compose.yml`. Personal `hermes`
  container untouched (its dashboard 9119).
- **Identity files** (`/root/.hermes-prism/`): SOUL.md, USER.md, AGENTS.md, MEMORY.md = a
  sales-research orchestrator (local copies in `docs/workspace/hermes-prism-integration/chowmes-prism/`).
- **Data layer**: `/root/.hermes-prism/reports/` (= `/opt/data/reports`) with `index.json` +
  `petsmart/audit-data.json` + `homedepot-mexico/audit-data.json` (imported from the algolia-arian-v2
  hub). 8 more companies importable.
- **prism-report-qa plugin** (`/root/.hermes-prism/plugins/prism-report-qa/`, ENABLED): `pre_llm_call`
  injects the bound report (L1) + `transform_llm_output` runs a Gemini grounding judge that
  rewrites/blocks unsupported FACTUAL claims (L4). **No Hermes fork** (the transform_llm_output hook
  can rewrite output). VERIFIED over PetSmart: grounded fact (15.98%, cited real field), absent fact
  → "That's not in the audit report", coaching allowed + anchored to cited facts.
- **W-A executor** (`/opt/prism-executor`, by teammate `wa-executor`): node22 / deno2.9 / Claude Code
  CLI / Playwright+Chromium+stealth / arijit-skills cloned (35 algolia skills) / chrome MCP wired.
  Anthropic key loaded. **Blocked on Anthropic credits + 3 MCP keys (apify/similarweb/builtwith).**

## DECISIONS LOCKED THIS SESSION (full rationale in vault ADRs)
1. **PRISM = Chowmes-PRISM**, a dedicated Hermes instance (not custom SaaS, not a profile); execution
   on VPS (standalone). Vault ADR `2026-06-28-prism-is-chowmes-prism-hermes-instance`.
2. **Temporal DROPPED** for PRISM — Hermes-native kanban/cron orchestrate. VPS Temporal stack deleted.
   (Org-wide Temporal decision in vault DecisionLog left intact — PRISM-only cleanup.)
3. **Two model planes:** control = Gemini-direct (cheap chat); execution = headless Claude/Anthropic
   (skills tuned for Claude).
4. **Grounding gate** = Hermes plugin (`transform_llm_output`), NOT a source fork. Scope =
   **facts grounded, coaching allowed**. Vault ADR `2026-06-28-grounded-report-qa-gate`.
5. (earlier this session) financials-chart parser bug fixed (`pvB`), skills backed up to `arijit-skills`
   repo + symlinked, hub `index.html` PetSmart card + logo fixed.

## REMAINING WORK (order)
- **W-A generation** (blocked on Anthropic credits + MCP keys): once unblocked, hand `wa-executor`
  the go → wire keys, run an end-to-end audit on a new company → deliverables to `/opt/data/reports`.
  Risk gate: browser/WAF on datacenter IP (residential runner or degrade).
- **W-B hardening** (non-blocking): force-a-fabrication stress test of the gate; QA-mode tool/
  delegation lockdown (L2 — agent sometimes delegates instead of answering); persist report-binding
  to a file (currently in-memory per session).
- **W-C** sales-coach identity refine (SOUL/AGENTS). **W-D** SPA chat + cross-channel (Hermes
  Responses API named-conversations + Caddy auth — NO fork). **W-E** Discovery-OS (finding metadata +
  translation layer → call plans). **W-F** skill review / determinism (ongoing).

## REFERENCE FILES (read as needed)
- Plan + recon: `docs/workspace/hermes-prism-integration/{03-plan.md,_status.md,01-skill-engine-map.md,02-hermes-architecture-truth.md}`
- Chowmes-PRISM artifacts (local copies): `docs/workspace/hermes-prism-integration/chowmes-prism/`
  (SOUL/USER/AGENTS/MEMORY, L4-grounding-gate-design.md, plugins/prism-report-qa/)
- Vault: `Projects/PRISM/` — overview (rewritten), open-questions (refreshed), wiki/decisions/ (2 new
  ADRs + 2 marked superseded), dev-log.
- GitHub: `arijitchowdhury80/prism` (commit 87342f6). Skills repo: `arijitchowdhury80/arijit-skills`.
- VPS access: skill `hostinger-vps-ssh`; helper `~/.claude/skills/hostinger-vps-ssh/scripts/ssh-hermes-vps`;
  temp env `/tmp/chowmes-prism.env` (SSH_HOST/USER/KEY — recreate if gone: host 72.61.72.147, user
  chowmesadmin, key ~/.ssh/chowmes_ed25519). `sudo -n` is passwordless. Run SSH with
  Bash `dangerouslyDisableSandbox: true`.

## WHAT HAS NOT BEEN DONE (no false completion)
- Generation has NEVER run end-to-end on the VPS (blocked on Anthropic credits). No new audit
  produced by Chowmes-PRISM yet.
- The grounding gate's HARD backstop wasn't stress-tested with a forced fabrication (the model
  answered correctly once the report was injected; the judge's block-path is unproven in a live run).
- L2 (tool/delegation lockdown) NOT done — the agent can still try to delegate for some phrasings.
- SPA chat (W-D), Discovery-OS (W-E), skill determinism (W-F): not started.
- MCP keys (apify/similarweb/builtwith) not on the box; BuiltWith-vs-SimilarWeb "dropped vs required"
  discrepancy unresolved.

## KEY LEARNINGS THIS SESSION (also in memory)
- Injection + "answer only from it" instructions do NOT stop fabrication (gemini said 12.5%, real
  15.98%) → a hard post-gen verifier gate is mandatory. [[feedback-injection-insufficient-need-hard-gate]]
- Hermes plugins are OPT-IN (`hermes plugins enable` + restart) — deploying files does nothing.
  [[feedback-hermes-plugins-opt-in]]
- Hermes has a `transform_llm_output` hook that CAN rewrite output (docs hook-table was incomplete —
  read the source). LLM "no final response" can mask a provider 402. [[feedback-llm-402-no-final-response]]
- Cross-channel continuity needs NO fork (Hermes Responses API named-conversations).
- Verify a subagent's "already built/proven" claims vs the primary source. [[feedback-verify-subagent-overclaims]]

## FILES WRITTEN/TOUCHED THIS SESSION (so nothing is lost)
- VPS: `/root/.hermes-prism/{config.yaml,.env,SOUL.md,USER.md,AGENTS.md,MEMORY.md,reports/*,plugins/prism-report-qa/*}`;
  `/opt/chowmes-prism/docker-compose.yml`; `/opt/prism-executor/*` (teammate); deleted `/opt/prism/temporal`.
- Repo PIP: `docs/workspace/hermes-prism-integration/*` (recon, plan, status, chowmes-prism/ staging,
  plugin, L4 design); `CLAUDE.md` (naming canon). Committed 87342f6 + pushed.
- Hub repo algolia-arian-v2 (earlier): index.html PetSmart card + clearbit logo; 3 financials fixes.
- Skills repo arijit-skills (earlier): audit skill sync + detect skills handling.
- Vault Projects/PRISM: overview.md (rewritten), open-questions.md (refreshed), 2 new ADRs, 2 ADRs
  superseded, index.md/log.md/dev-log.md; Architecture/DecisionLog.md (+1 PRISM note).
- Memory: reference-prism-means-chowmes-prism, reference-skills-symlinked-to-repo, feedback-*
  (verify-subagent-overclaims, strip-parsefloat-unit-blind, llm-402, injection-insufficient,
  hermes-plugins-opt-in), project-prism-hermes-direction (updated), MEMORY.md index, session_pointer.

## TEAMMATE
`wa-executor` (background agent) — finished W-A A1+A2 (executor install + skills), reported, now idle.
Resume it via SendMessage(to:'wa-executor') once Anthropic credits + MCP keys are available, to
finish A3 wiring + e2e.
