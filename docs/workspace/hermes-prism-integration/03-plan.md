# Plan — PRISM as Hermes (orchestrate, don't build)

**Date:** 2026-06-27
**Status:** ACTIVE plan. Supersedes "build PRISM custom SaaS."
**Source recon:** `01-skill-engine-map.md`, `02-hermes-architecture-truth.md`, vault harvest (see `_status.md`).

---

## THE DECISION (locked)

PRISM is **no longer a custom SaaS build**. PRISM = **Hermes agent + the algolia-* skill suite + supporting infra**, packaged. That package *is* "PRISM v1".

- **Architecture: CONTROL / EXECUTION split** (DESIGNED 2026-06-19, NOT yet built — ChowMes notes
  say "refine 'Hermes spawns Claude' → queue + workers" and "Do NOT jump to building"). What IS
  proven: the skills produce a real, published, factchecked, 10/10-eval audit (**PetSmart**, run
  **manually in Claude Code**; Hermes/Athena only did the exec verdict). Hermes orchestrating the
  skills end-to-end is UNPROVEN — that is what this plan builds.
  - **Control plane = Hermes** (Nous Research agent on the VPS): chat, identity, gating, cron, memory, delivery, mobile (Telegram).
  - **Execution plane = headless Claude** (`claude` CLI / Agent SDK) that Hermes shells out to, running the 22 algolia skills + MCP **unchanged**.
  - Hermes does NOT reimplement the Claude `Skill` tool. Skills run verbatim under headless Claude.
- **Category: internal Algolia AE/BDR enablement tool, NOT a sellable SaaS.** This is *why* "agent + skills + keys + VPS" is a legitimate package.

## TWO-MODE PRODUCT MODEL (do not fuse)

| Mode | What | Speed | Cost | Frequency |
|---|---|---|---|---|
| **Generation** | Hermes → headless Claude → runs skill pipeline → report + deliverables | minutes (batch) | full LLM cost | once per prospect (on-demand / calendar) |
| **Consumption** | AE/BDR chats over the *finished* report on mobile (= **aRRIe**, grounded RAG) | seconds | cheap | many turns |

Mobile chat = grounded Q&A over a pre-built artifact. **NOT** live full-audit per turn.

---

## CONSTRAINTS

- **Demo: 2-4 weeks.** Shows BOTH: live skill generation + Hermes mobile chat over the report.
- Two tracks run in parallel (A presentation, B integration).
- Demo generation may be **attended** (operator drives, solves CAPTCHA manually). Unattended is a product goal, not a demo gate.

---

## TRACK A — Presentation (cohort demo)

- **A1 — Narrative deck.** Source: `01-skill-engine-map.md` (the suite, grouped + the 6-wave pipeline) + `docs/specs/pip-master-vision-prd.md` (the $640K/yr → ~$24K story, 20-module catalog) + `docs/specs/cognitive-stack-architecture.md` (Layer-5 framing). Provenance/anti-hallucination gets its own slide (`arrie-zero-hallucination-policy.md`).
- **A2 — Live skills demo.** Run the algolia skills in Claude Code on a real prospect; show real deliverables. Zero build risk — works today.
- **A3 — Hermes mobile chat demo.** Chat over the generated report from a phone. **Depends on B4.** This is the "wow."

**A is dual-purpose:** the skill-engine map is simultaneously the presentation preamble AND the B integration spec.

## TRACK B — Hermes integration (the product)

- **B0 — VPS ground-truth.** SSH the box. Confirm: is algolia MCP attached to the `hermes` container? Does the control/execution split still run? Inventory live state (Scout, Temporal, secrets path). *Recon could not SSH — this is unverified.*
- **B1 — Architecture ADR.** Record control/execution split in vault `Projects/PRISM/wiki/decisions/`.
- **B2 — Browser/WAF de-risk spike** *(product #1 risk — FIRST on product path).* Prove `audit-browser` can beat WAF/CAPTCHA **unattended** via a residential-IP runner. Pass/fail gate. If fail → audit-browser stays human-assisted (graceful degrade); know before building the queue.
- **B3 — Orchestration hardening.** Job queue, gating (confidence/evidence/human-review), persisted deal-intel store, secrets path off Telegram.
- **B4 — Chat-over-report on mobile** *(DEMO-CRITICAL — parallel to B2).* aRRIe answering over an existing report via Telegram. Grounded RAG, zero-hallucination policy.
- **B5 — e2e via Hermes.** Real prospect, full run through the control/execution split.

---

## CRITICAL PATHS

- **Demo path (2-4 wks):** A1 + A2 + **B0 → B4** + attended generation. (Browser WAF NOT a blocker — operator drives.)
- **Product path:** **B0 → B1 → B2 (gate)** → B3 → B5. Unattended generation depends on B2 passing.

## RISKS (named, not waved away)

1. **Browser WAF on datacenter IPs** — breaks unattended generation = the core wedge. Mitigation: residential-IP runner (B2). #1 risk.
2. **Cost** — every generation is full LLM tokens; deterministic modules parked. Acceptable at demo/small-team scale; watch at "every AE daily."
3. **Silent degradation** — unset keys (Apify/Tavily/SimilarWeb/BuiltWith) downgrade to WebSearch; **Yahoo MCP outage hard-stops** financial-public. Operational hardening before any live demo.
4. **Secrets via Telegram** — current path is a stopgap; needs a real secrets path (B3).
5. **Centralized scripts** — collectors live in `~/.claude/skills/algolia-search-audit/scripts/` (not per-skill). Any port must carry that dir + `$ALGOLIA_AUDIT_DIR` + the `AGENT-CONTEXT.md` pre-read.

## IMMEDIATE NEXT ACTIONS

1. **B0** — SSH VPS, verify live state (unblocks everything; resolves recon's one gap).
2. **A1** — start the deck from the skill-engine map (parallel, no dependency).
3. Kick **B2** (browser spike) and **B4** (mobile chat) once B0 confirms the runtime.
