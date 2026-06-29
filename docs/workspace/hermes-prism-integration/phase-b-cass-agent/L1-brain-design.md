# Phase B — Cass Agent Evolution — L1 "Fix the Brain" Design

**Date:** 2026-06-29
**Status:** DESIGN — awaiting user spec approval before build
**Scope:** L1 only (Gaps 1, 2, 5-backend). L2/L3 and SPA UI are separate sub-builds (see Roadmap).

---

## Why (the problem, from the live Telegram thread)

Cass today is a RAG-only chatbot: she knows the list of audited company *names* but can't
read a report's contents, can't run any skill, can't spawn agents, and her "Algolia expertise"
is just Gemini's generic training. Observed failures (Telegram, 2026-06-29):
- Couldn't pull Home Depot México highlights despite holding that report.
- Couldn't run "a light audit" or any named skill.
- Talks below the level of a real Algolia sales coach.

Root causes (verified in code, not recited):
1. **Gap 1 — no real Algolia brain.** `DEPLOY-NOTES.md:8` — only `SOUL.md` is assembled into the
   system prompt. `KNOWLEDGE-algolia-full.md` (21.7KB, complete & high quality) and `MEMORY.md`
   are NOT loaded. Her product/sales knowledge is Gemini parametric only.
2. **Gap 2 — fragile binding.** `prism-report-qa/__init__.py:_match_slug` has two bugs (below) and
   the SPA session-key path is dead (`:acct:<domain>` never reaches the hook kwargs).
3. **Gap 5 — parallel brains.** Old aRRIe system prompt in SPA `app/api/chat/route.ts` (now
   bypassed by `/api/hermes` route). Need to confirm one-brain and retire dead code.
4. **Gap 3 (tool arms) and Gap 4 (execution plane)** — deferred to L2/L3.

**Key leverage:** the plugin runs server-side inside the one Hermes instance. Telegram + SPA both
hit it. Fixing the brain in the plugin fixes BOTH channels at once.

---

## Locked decisions (user, 2026-06-29)

- **Build order:** Layered, ship each — L1 (today, no keys) → L2 (Perplexity key) → L3 (after key rotation).
- **Security:** Rotate exposed BuiltWith + SimilarWeb keys (task #15) BEFORE L3. L1+L2 need none of those.
- **Grounding gate scope:** TWO allowed sources — judge verifies prospect facts vs the bound report
  AND Algolia product/case-study facts vs the knowledge pack. Invented numbers still stripped.

---

## L1 changes (concrete, code-level)

### 1. Gap 1 — load the Algolia knowledge pack
- Copy `KNOWLEDGE-algolia-full.md` → `plugins/prism-report-qa/knowledge.md` (ships with the plugin).
- New `_load_knowledge()` — read once, cache by mtime (mirror `_load_index` pattern).
- `inject_report()` prepends the knowledge pack to its `context` in BOTH branches (bound and unbound),
  so Cass is a real Algolia coach even with no report bound (hub overview, unknown prospect like Arhaus).
- Wrap it in a clear delimiter so it reads as reference knowledge, not prospect facts, e.g.
  `[Algolia knowledge base — product, competitors, ROI model, proof points. General Algolia facts;
  NOT facts about this specific prospect.]`

### 2. Gap 2 — fix binding
**Bug A (accents):** `_match_slug` compares `é`≠`e`. Add `_norm()` that NFKD-normalizes and strips
combining marks on BOTH the company string and the user message before compacting.
**Bug B (direction/tokens):** current code tests `company_compact in message_compact` (long-in-short →
never matches partials like "homedepot"). Replace with token aliasing per report:
  - alias tokens = { slug, slug-without-hyphens, domain root, each company word minus stopwords
    (the, inc, co, company, méxico→mexico kept as token) }
  - match if any alias token of length ≥4 appears in the normalized message.
  - keep exact slug/domain/company substring matches as-is (still valid).
**Bug C (SPA session key):** `_slug_from_session_key()` is correct but `:acct:<domain>` never arrives
in kwargs. Trace how Hermes passes session/gateway context into `pre_llm_call` hooks; wire the
session key through so deterministic bind works from the SPA (Cass auto-binds to the page's company).
  - Read receipt required: locate the Hermes hook-dispatch source on the VPS, quote the kwargs it
    passes, map to the fix. (Per global protocol-read-receipt — this is a wire/contract change.)

### 3. Gap 1 × L4 interaction — two-source judge
- `grounding_gate()` / `_gemini_judge()` take the knowledge pack as a SECOND allowed source.
- Update `JUDGE_PROMPT`: SOURCE_REPORT = prospect facts; SOURCE_KNOWLEDGE = Algolia product/case-study
  facts. A claim is unsupported only if absent from BOTH. Coaching/methodology still never flagged.

### 4. Gap 5-backend — one brain
- Grep SPA for any live use of the old aRRIe `SYSTEM_PROMPT` in `app/api/chat/route.ts`; confirm
  `/api/chat` is fully gated and all chat flows through `/api/hermes`. Retire dead prompt/code.
- Confirm Telegram + SPA both resolve to the same Hermes instance + plugin (knowledge now shared).

---

## Deploy (L1)

1. Edit plugin + add `knowledge.md` locally (in this repo's `chowmes-prism/plugins/prism-report-qa/`).
2. scp plugin dir → VPS `/root/.hermes-prism/plugins/prism-report-qa/` (and `knowledge.md`).
3. Restart hermes-prism (plugin reload). Confirm `plugins.enabled` still lists `prism-report-qa`.
4. NOTE: live Telegram DM sessions freeze SOUL/system context per session — knowledge inject is a
   pre_llm_call hook so it applies to NEW turns immediately, but verify; delete stale sessions if needed
   (`hermes sessions delete <id>`) per memory `feedback-hermes-soul-frozen-per-session`.

## Test plan (evidence required before "done")

- **T1 (Gap 1, unbound):** ask Cass (no company) "why is Algolia better than Constructor for apparel?"
  → expect the 5-part counter-narrative, not generic fluff.
- **T2 (Gap 2, accent/partial):** message "home depot" (no "mexico") → binds homedepot-mexico, pulls
  real highlights. Re-run the exact failing Telegram query.
- **T3 (Gap 2, SPA key):** call `/api/hermes` with `X-Hermes-Session-Key …:acct:petsmart.com`, no
  company named in the message → binds petsmart deterministically.
- **T4 (two-source judge):** Cass cites "Lacoste +37%" → passes (knowledge pack). Cass states a wrong
  PetSmart number → stripped/corrected. (Reuse the W-B PetSmart 15.98% grounding proof.)
- **T5 (both channels):** same knowledge appears in Telegram AND SPA answers.

## Out of scope for L1 (explicit)

- L2: register 17 FastAPI module endpoints as Hermes tools + Perplexity key + SSE tool-frame shim.
- L3: claude-cli executor (.mcp.json keys, Anthropic credits, playwright) + `run_audit` chat tool. Gated on #15.
- SPA UI: global floating Cass + dedicated section. Frontend sub-build (routes through frontend-design).
  Decided shape: floating widget on all pages + a dedicated section (not a standalone page) — TBD layout.

## Risks

- Free-tier Gemini 429 under bigger payloads (knowledge pack adds ~5K tokens/turn to main call; judge
  gets a second source). Mitigation: the VPS Gemini key is paid/standard tier per memory; verify live.
- Token cost: report JSON + knowledge pack every turn. Acceptable on gemini-2.5-flash (1M ctx, cheap).
