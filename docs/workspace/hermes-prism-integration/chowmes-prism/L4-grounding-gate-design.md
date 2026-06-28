# L4 — Grounding Gate Design (W-B B3)

## Why this exists (proven, not theoretical)
Test 2026-06-28: with the full PetSmart report injected (L1) + strict "answer only from it"
instructions (L3), gemini-2.5-flash still answered "no-results rate = **12.5%** [FACT]" — the real
value is **15.98%** (`no_results_rate`). Injection + instructions LEAK. A hard post-generation gate
is required. (Hermes hooks can't gate output → a source patch is the only place; decided: Option A.)

## What it does (one sentence)
After Hermes finalizes the assistant's answer, if the conversation is bound to an audit report,
verify every **factual claim about the prospect** in that answer against the report; block/rewrite
any claim the report doesn't support — before the message is sent.

## Scope (the decided rule: facts grounded, coaching allowed)
- **Verified (must be report-supported):** factual claims about the prospect — numbers, scores,
  search vendor, findings, financials, competitor facts, quotes.
- **NOT policed:** coaching/reasoning (calibrated hypotheses, F1–F6/M1–M10 moves, objection
  handling, call plans, methodology) — allowed, as long as the *facts* they cite are supported.
- The judge is told this split explicitly, so it flags a fabricated *number* but not a *hypothesis*.

## Where (the chokepoint)
`agent/turn_finalizer.py` — the single point where the turn's final assistant text is assembled
(where `post_llm_call` emits). Insert the gate immediately before the finalized response is returned
for delivery. Covers BOTH Telegram and the API/SPA path (same turn loop).

## The judge (runs on Gemini, not the ai-judge Claude skill)
The grounding check is a **direct Gemini call** (the working control-plane model) — NOT the
`ai-judge` Claude skill, because Anthropic auth is exactly what's unavailable on the box.
- Input: the SOURCE = the bound report's `audit-data.json`; the ANSWER = the drafted assistant text.
- Prompt: "Extract each FACTUAL claim about the prospect in ANSWER. For each, is it directly
  supported by SOURCE? Return JSON: `{verdict: PASS|FAIL, unsupported:[{claim, why}], ...}`. Treat
  coaching/hypotheses/advice as NOT factual claims — ignore them."
- Cheap, deterministic-enough, same key already wired.

## Decision logic
- `verdict == PASS` → send the answer unchanged.
- `verdict == FAIL` (≥1 unsupported factual claim) → **do not send the raw answer.** Options (pick at
  build): (a) **rewrite** — strip/replace the unsupported claims and append "(other details aren't in
  the audit report)"; or (b) **safe-replace** — return "Parts of that aren't in the audit report —
  here's what the report supports: …" with only verified facts. Default: **rewrite**, fail-closed on
  facts.
- Judge call errors/timeout → **fail-closed for facts**: append a visible "(could not verify against
  the report — treat factual details with caution)" rather than silently passing. Never fail-open
  silently.
- No report bound to the session → gate is a no-op (normal Hermes behavior).

## How the gate knows the bound report
The `prism-report-qa` plugin already resolves the binding per `session_id`. Make it **persist the
binding** to a small file (e.g. `/opt/data/report-bindings/<session_id>.txt` = slug). The
turn_finalizer patch reads that file by `session_id` to load the same report. (Shared state across
the plugin + the patch; survives within the container.)

## Packaging (no live edits)
Build a **pinned derived Docker image**:
```
FROM nousresearch/hermes-agent:<pinned-digest>
COPY turn_finalizer.patched.py <path-in-image>/agent/turn_finalizer.py
```
- First locate the file's path inside the published image (it's in the image, not the mounted
  volume).
- Point `/opt/chowmes-prism/docker-compose.yml` at the derived image tag.
- Pin the base by digest so an upstream `:latest` change can't silently break the patch.
- Keep the patch as a small unified diff in the repo so it's reappliable on Hermes upgrades.

## Verification (must pass before W-B is "done")
1. "PetSmart no-results rate?" → **15.98%** (or a refusal), NEVER 12.5%.
2. Inject a deliberately ungrounded claim into a draft (test harness) → gate blocks/rewrites it.
3. "Give me an opening move for the PetSmart call" → coaching answer ALLOWED, but every fact it
   cites (e.g. the 15.98%) is correct/supported.
4. Ask something genuinely absent → "That's not in the audit report."
5. Latency: measure the added judge round-trip; acceptable for chat.

## Open choices for you
- Rewrite vs safe-replace on FAIL (default: rewrite).
- Judge model: gemini-2.5-flash (same as chat) vs a cheaper/faster gemini for the check.
- Whether the gate also runs in *generation* answers or only report-QA (recommend: only when a
  report is bound).
