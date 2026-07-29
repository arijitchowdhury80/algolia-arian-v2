# Workspace status — hermes-prism-integration

**Goal:** Make Hermes the PRISM engine (orchestrate the algolia-* skills via control/execution split). Two tracks: A presentation (cohort demo 2-4 wks), B Hermes integration (the product).

## Files
- `01-skill-engine-map.md` — the 22 skills: categories, dependency DAG, deliverables, headless-readiness risks. DUAL-PURPOSE (presentation + integration spec).
- `02-hermes-architecture-truth.md` — what Hermes is (Nous Research agent), control/execution split, the load-bearing "can it run skills" answer.
- `03-plan.md` — THE plan. Decision, two-mode model, Track A, Track B, critical paths, risks, next actions.

## Decisions locked
- PRISM = Hermes + skills, packaged. NOT a custom SaaS. Internal AE/BDR enablement tool.
- Control/execution split: Hermes orchestrates headless Claude that runs skills unchanged.
- Two-mode: Generation (batch) vs Consumption (chat-over-report = aRRIe).
- Demo in 2-4 wks shows BOTH live generation + Hermes mobile chat. Track B starts with browser/WAF spike.

## NAMING CANON (2026-06-28)
"PRISM"/"prism" = **Chowmes-PRISM** only (the VPS Hermes instance). Execution runs ON THE VPS
(standalone). See memory `reference-prism-means-chowmes-prism`.

## P1 DONE — Chowmes-PRISM is LIVE (2026-06-28)
Container `hermes-prism` up (s6-supervised), Telegram connected (polling, bot id 8870557089),
model gemini-2.5-flash, dashboard 127.0.0.1:9120 (personal hermes on 9119, no collision). Identity
files loaded as `default` profile. Data layer present. **NOT yet:** algolia skills (execution P2),
grounding patch (task #7), report-binding. So today it chats as a general Hermes agent with Prism's
persona — exclusive report-grounding is the NEXT task.
Bot token lives ONLY in `/root/.hermes-prism/.env` (never in repo/docs).

## (history) P1 build steps
B0 done (VPS recon). P1 in progress: created `/root/.hermes-prism/` (config.yaml → gemini-2.5-flash,
SOUL/USER/AGENTS/MEMORY authored — local copies in `chowmes-prism/`), `.env` (keys + placeholder
bot token), `/opt/chowmes-prism/docker-compose.yml` (hermes-prism, dashboard :9120, VALID, NOT
started). **Blocked on:** the `prism_bot` Telegram token from Arijit (@BotFather) → drop in .env →
`docker compose up -d`.

## Two new core challenges (from 2026-06-28)
1. **Exclusively-grounded report-QA RAG** — the bot answers ONLY from the audit report, never
   outside/parametric. Approach: closed-book-over-document (inject full report) + disable
   outside tools (config) + grounding-judge output gate (ai-judge) + Hermes hooks; fork only if
   hooks can't intercept output. This is the immediate design focus.
2. **SPA chat integration + cross-channel continuity** — embed the same agent in the (today static)
   SPA so a conversation continues across Telegram ↔ desktop. Needs Hermes API behind Caddy + auth
   (public SPA, private intel) + a channel-agnostic shared conversation thread. Later phase.

## Data layer (created 2026-06-28)
Report store at `/root/.hermes-prism/reports/` (= `/opt/data/reports` in container): `index.json`
(discovery) + `<slug>/audit-data.json`. Imported **petsmart** (5.8) + **homedepot-mexico** (2.6)
from the algolia-arian-v2 hub. 8 more companies importable (nike, brooks-running, dsw, llbean,
savage-x-fenty, oriental-trading, british-airways, labanquepostale). This is the grounding corpus
for report-QA; new VPS-generated audits write here too. Temporal stack DELETED from VPS (stale).

## Open / unverified
- Executor-on-VPS: needs Claude CLI + skills + MCP installed on the box (P2) — not yet done.
- Browser/WAF unattended feasibility unknown until the de-risk spike (P5).
- Whether Hermes hooks can intercept outbound messages (decides config-vs-fork for the grounding gate).
