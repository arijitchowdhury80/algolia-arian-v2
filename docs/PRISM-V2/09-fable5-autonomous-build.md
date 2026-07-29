# PRISM V2 — Autonomous Full-Build Mission (paste into a fresh Fable 5 session)

You are **Fable 5**, executing the PRISM V2 build **to completion, autonomously**. You own this end-to-end: decompose the work, spawn agent teams, monitor them, quality-gate every deliverable, iterate until the definition of done is met, and ship. Run the loop yourself — do not stop to ask unless you hit a genuine Mandate Boundary (listed below).

---

## 0. READ FIRST (in this order) — do not build until you have
- `docs/PRISM-V2/06-v2-execution-map.md` — the build spine (8 tracks, per-role IA, Discovery-OS build reqs, open research R1–R10, blocked decisions D1–D10).
- `docs/PRISM-V2/05-role-driven-ia.md` — the role IA (AE/BDR/Marketer doors + Jarvis cockpit).
- `docs/PRISM-V2/07-design-system.md` — the design language (Sora, Algolia `#003DFF`, tokens).
- `docs/PRISM-V2/00-manifesto.md`, `_status.md`, `04-open-gaps-before-fable5-handoff.md` — decisions + gaps.
- `SESSION.md` (repo root) — current state.
- **Current architecture (verified 2026-07-06):** data = **Postgres on the VPS** (`prism-platform-postgres-1`, db `prism`, table `audits.audit_data` JSONB = source of truth). Skills canonical = **`arijit-skills` GH repo** (VPS `/opt/prism-executor/arijit-skills`). Serving: `prism.chowmes.com` (V1, Clerk-gated, `/opt/PRISM/v1`) is now **DB-backed auto-render** (chat-proxy injects fresh `audit_data` from `GET /api/v1/audits/by-slug/{slug}/data`). **`prism2.chowmes.com`** (V2, basic-auth `prism`/`AlgoliaPRISM2026`) serves `/opt/PRISM/v2` = git worktree of branch `prism-v2`. VPS = `chowmes-vps` (72.61.72.147, sudo NOPASSWD), deno at `/usr/local/bin/deno`.

## 1. THE PRODUCT (what you are building)
PRISM V2 = a **standalone, domain-agnostic Prospect Research Operating System** — a sellable product, Algolia is just the first domain module. Stack: Postgres+pgvector + Claude Agent SDK (self-hosted). Beta = Algolia Marketing + Sales leadership (Marketing's #1 ask = landing-page building). 3 roles: AE, BDR, Marketer.

## 2. ⛔ THE #1 CONSTRAINT — V2 MUST BE A GENUINELY NEW EXPERIENCE (this is why the last attempt failed)
The first V2 attempt **FAILED the real test**: the screens looked **identical to V1** — it reused the V1 report SPA and put thin "door" pages in front that linked back to the *same* report. Arijit could not tell what was built. **V2 is NOT a re-skin of V1's audit report.** It is a different PRODUCT. Concretely, V2 must deliver experiences that do not exist in V1:
- **Role cockpits that are DISTINCT per role** — the AE deal cockpit (3-stage PREP→SS1→SS2 + Discovery-OS single-page call plan) ≠ the BDR signal-ranked queue + one-click micro-Exchange outreach ≠ the Marketer content studio (narrative hooks + landing-page builder + ABM brief). Not one report behind three labels.
- **Chat-as-operator cockpit** — chat is the primary surface that **drives** the system: guides the user, runs audits, checks status, streams live receipts, notifies. Not a search box bolted onto a report.
- **Recipe / module selection (lego cockpit)** — the operator hand-picks which modules run for an audit; the executioner runs the recipe.
- **Live execution + monitoring** — watch an audit run in real time (per-module status, gates passing).
- **Grounded RAG chat** over the Postgres/pgvector store — every answer source-backed.
- **The Marketing landing-page builder** as a first-class feature (their explicit ask) — generate on-brand landing pages per account from DB audit data.

**Acceptance rule for every screen:** if a reviewer opening it side-by-side with the V1 report cannot *instantly* tell it is a new product with a new job, it is **not done**. Screenshot V1 and your screen; the difference must be obvious.

## 3. AUTONOMOUS ORCHESTRATION PROTOCOL (run this loop yourself)
1. **Decompose** the mission into workstreams from `06` §2 (role cockpits, chat-as-operator + grounded RAG, executioner/data backend, modular recipe cockpit, productization). Order by dependency; ship visible surfaces first (role cockpits + chat) so difference-from-V1 is provable early.
2. **Spawn agent teams per workstream** — a builder + an independent QA/adversarial-verifier per deliverable. Route model tiers by the economics table (bulk build → cheaper tier; judgment/verify → higher). Declare agent count + tier + rough token estimate before any fan-out >2.
3. **Self-monitor** — track each workstream's state. If an agent stalls, errors, or returns a self-report without evidence, re-dispatch or escalate. Never relay a subagent "done" without independently checking the real artifact.
4. **Quality-gate every deliverable BEFORE accepting it:**
   - UI/screens → `ui-validator` + the "new-experience" acceptance rule (§2) + Playwright-verify at 1280/375px on the actually-served surface.
   - Code → `code-validator` + tests ship with every module (`ruff/mypy/pytest` green, output shown).
   - Data → data-integrity gate: every number source-backed, zero fabrication; SimilarWeb is **permanent HITL** (no API — never assume the script runs).
   - Done → **done-means-live**: load the real served surface (prism2.chowmes.com) AFTER the final change and observe it. No false-green.
5. **Loop-until-done** — do not declare a workstream done on first pass. Iterate: build → QA → fix → re-verify, until it meets the definition of done. Use a loop-until-dry / adversarial-verify pattern for correctness.
6. **Persist + report** at each milestone (SESSION.md + memory). Show a status board of workstreams (done/in-progress/blocked).

## 4. DEFINITION OF DONE
- **Per screen:** distinct, functional, real DB data, role-specific, deployed to prism2.chowmes.com, **visibly ≠ V1** (§2 acceptance), quality-gated (ui-validator + Playwright on served surface).
- **Chat-as-operator:** actually drives a real audit + returns live status (not a mock).
- **Grounded RAG:** answers cite DB sources; no ungrounded claims.
- **Overall:** a reviewer can open prism2.chowmes.com, use each role cockpit + the chat operator, and see a coherent NEW product — not the V1 report.

## 5. GUARDRAILS (non-negotiable — from the project's operating rules)
- **Data integrity absolute:** verified, source-backed, exact data only — never estimates/ranges/fabrication. Empty slot > guessed value. SimilarWeb = HITL (Arijit logs in; capture from browser).
- **Done-means-live:** verify the real user-facing surface after the final change; the only allowed status otherwise is "changed, not yet verified."
- **No re-skin:** the §2 new-experience test gates every screen.
- **No silent scope-narrowing / no false-green:** report each item done/deferred/blocked honestly.
- **Reuse-first:** enumerate what exists (arijit-skills, prism_platform, the current repo, the design system) before building new.

## 6. MANDATE BOUNDARIES — stop and get Arijit's explicit yes for these ONLY
- Deploying to **V1 prod** (`prism.chowmes.com`) or merging to its branch.
- Destructive ops (dropping data, `rm -rf`, deleting a project).
- Auth/visibility/network-exposure changes (new public URL, opening a port).
- Model/provider switch, or changing model IDs in application code.
- The still-open decisions in `06` §7 that need a human call: D1 (self-hosted SDK vs Managed Agents API), D2 (durable retry), D3 (auth provider), D5 (Discovery-OS gating-rule ambiguity), D6 (pricing/metering), D8 (deadline), D10 (product name). For everything else, decide with best judgment and record the decision.
- **R1 executioner POC needs a real `ANTHROPIC_API_KEY`** — request it if you reach that track and it's absent; do not stub around it.

## 7. FIRST MOVE
Read §0. Then build **one role cockpit end-to-end (AE) as the proof it's a NEW experience** — real DB data via the by-slug endpoint, distinct cockpit UI, quality-gated, deployed to prism2, screenshotted next to V1 to prove the difference. Only after that vertical slice is verified-live do you fan out the other cockpits + chat-operator. Report + persist after the AE slice.
