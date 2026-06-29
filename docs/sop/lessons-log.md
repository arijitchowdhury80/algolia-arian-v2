# Lessons Log — PRISM

### Vercel: in-file `runtime:"edge"` silently ignored → deploys as Node Lambda → streaming handler hangs (HTTP=000) — 2026-06-28
- **Symptom:** Deployed `/api/chat` returned HTTP=000, 0 bytes, full gateway timeout on every real request; fast validation paths (405/400) worked in 0.2s and env vars were present (no "not configured" 500).
- **Root cause:** `api/chat.js` was an Edge function (`export const config={runtime:"edge"}`, Web `Response`/`ReadableStream`, `handler(req)`), but the old static Vercel project `algolia-arian-v2`/`prism` deployed it as a **Node serverless Lambda** (`vercel inspect` shows `λ api/chat`, not Edge). A Node Lambda handler is `(req,res)` and must call `res.end()`; returning a Web `Response` does nothing → response never ends → 000.
- **Fix:** (a) verify the runtime with `vercel inspect <url> | grep api/` — `λ`=Node Lambda, Edge shows as an Edge fn; (b) if it must be Node, write the handler as `(req,res)` with `res.write/res.end`; if it must be Edge, ensure the project actually honors edge (adding `package.json{"type":"module"}` did NOT fix it; `vercel.json functions.runtime:"edge"` is INVALID — that field needs a versioned 3rd-party runtime; `--force` rebuild didn't change it). Likely needs a fresh project with edge support.
- **Evidence:** External Mac curl to the same upstream returned the grounded answer (15.98% [FACT]) in 6.3s/HTTP200, proving upstream+wiring are correct and the hang is purely Vercel-runtime.
- **Prevention (future me):** After deploying any Vercel function that uses Web `Response`/streaming, IMMEDIATELY run `vercel inspect <url> | grep api/` and confirm it is NOT `λ`. The `λ` symbol on a Web-API handler = guaranteed hang. Don't trust the in-file edge `config` export on old/static projects — verify the deployed runtime, not the source intent.

### RESOLVED: Vercel Web-API handler hang → fixed by Node `(req,res)` rewrite — 2026-06-28
- **Resolution of the prior λ-hang lesson:** the static `prism` project will NOT honor the in-file edge `config` export — it always deploys `/api/*` as a Node Lambda (λ). Trying to force Edge (package.json type:module, vercel.json functions.runtime:"edge", --force rebuild) all failed. The working fix was to STOP fighting it and write the handler to the runtime Vercel actually uses: `export default async function handler(req, res)`, read `req.body`, stream upstream deltas via `res.write(...)`, end with `res.end()`, and set `export const config = { maxDuration: 60 }` for the streaming duration.
- **Evidence:** post-fix `/api/chat` returns HTTP=200 in 1–4s with streamed text (was HTTP=000 / 90s timeout). petsmart grounded answer "15.98% [FACT]" came through the deployed proxy. `vercel inspect` shows `λ api/chat (3.08KB)` — λ is correct for a Node handler.
- **Prevention (future me):** On an old/static Vercel project, don't assume `config={runtime:"edge"}` opts you into Edge — verify with `vercel inspect`. If it deploys as λ, write the function for the Node serverless contract (`(req,res)` + `res.end()`), NOT the Web `Response` contract. Pick the contract that matches the deployed runtime, not the one you wish you had.

### render-audit.ts `site` mode wrote to cwd, clobbering the hub homepage `index.html` — 2026-06-28
- **Symptom:** `deno run render-audit.ts <slug> site` from `~/prism-hub` overwrote the hub's ROOT `index.html` (homepage) instead of `<slug>/index.html`; had to `git checkout index.html` to restore.
- **Root cause:** `renderSite(data, _slug, cwd)` ignored the slug (`_slug`) and wrote `join(cwd, "index.html")`. Every OTHER mode uses `join(cwd, slug, …)` (`inSlugDir:true`). The `site` mode was the lone offender — and the screenshot-path logic (`screenshots/x.png` resolving from `{slug}/index.html`) was already written assuming the slug-dir output, so root-write broke screenshots too.
- **Fix:** `const outDir = join(cwd, slug)` in `renderSite`; renamed `_slug`→`slug`. Verified: render writes `petsmart/index.html` (589.5KB), root `index.html` md5 unchanged.
- **Prevention (future me):** A renderer that takes both `slug` and `cwd` but writes to `cwd` directly is a clobber waiting to happen. Any per-entity output path must include the entity dir. Before batch-rendering into a shared dir, render ONE and assert the shared root file's md5 is unchanged.

### `check-style-tokens.py` (and similar gates) print a DISPLAY CAP, not the true count — read the headline, not the lines — 2026-06-28
- **Symptom:** Eyeballed the gate output, counted 25 `[FONT-SIZE]` lines, scoped a fix to "25 violations in one region." A subagent pushed back: real total was 108, file-wide (lines 6621→11628). I had under-scoped by 4×.
- **Root cause:** The gate prints `deduped[:25]` then `… and N more`, and the headline `DESIGN SYSTEM VIOLATIONS (108)`. `grep -c "Line"` returns 25 (the cap), NOT the total. The "… and 83 more" line doesn't contain "Line".
- **Fix:** Read the parenthesized headline count (`(108)`) or `grep -E "and [0-9]+ more"`, never the count of printed detail lines.
- **Prevention (future me):** Any linter/gate that truncates output has a headline total — trust THAT, not a `grep -c` of the visible rows. When a subagent contradicts my count, verify against the source before proceeding (it was right, I was wrong).

### Delegation: verification-required tasks need an agent that HAS the verify tool — 2026-06-28
- **Symptom:** Dispatched `cavecrew-builder` to fix a gate "and run check-style-tokens.py to confirm EXIT=0" — but cavecrew-builder has no Bash tool, so it physically could not verify and returned blocked.
- **Root cause:** Agent-type tool sets differ. Picked a tightly-scoped edit agent for a task whose acceptance criterion required running a command.
- **Prevention (future me):** Match agent capability to the task's acceptance test. If the task says "run X and confirm output," the agent MUST have Bash. cavecrew-builder = pure edits; general-purpose / claude = edits + verify. Check tools before dispatching.

### "Zero visual change" of a client-rendered template ≠ byte-identical output — resolve tokens, don't diff bytes — 2026-06-28
- **Symptom:** Tokenized 108 template style violations, then byte-diffed petsmart's rendered HTML before/after to prove no visual change. It DIFFERED — looked like a regression.
- **Root cause:** The report template is client-rendered: the rendered `index.html` embeds the template's JS (`const T = {…}`) and `:root` CSS verbatim, and `${T.x}` expands in the *browser*. Adding token/var DEFINITIONS changes the file bytes without changing any rendered element. A byte-diff measures source, not pixels.
- **Fix:** Proved equivalence by *resolution*: expand every `${T.x}` (from the T map) and `var(--c)` (from `:root`) in both old and new templates, normalize case-insensitive hex, then diff. Zero use-site differences (only definitions/comments) ⇒ zero visual change. Script: scratchpad `verify_tokenization.py`.
- **Prevention (future me):** To prove a tokenization/refactor of a client-rendered template is visually inert, diff the *resolved* CSS (or computed styles via browser), never the raw file. And remember CSS hex is case-insensitive — `#abc123`==`#ABC123`, normalize before diffing.

### Subagent over-scoped (added :root vars I fenced off, uppercased hex) — independent verify caught it benign — 2026-06-28
- **Symptom:** Delegated "tokenize font-sizes, don't touch :root." Agent reported success but had added 5 `:root` vars and uppercased hex on unrelated lines — beyond the stated scope.
- **Root cause:** The pass condition (gate EXIT=0) required clearing 12 raw-color violations the task had mis-scoped as font-size; the agent honored the hard "EXIT=0 + preserve visuals" goal over the narrower "don't touch :root" rule, and flagged it.
- **Fix:** Didn't accept the self-report — ran the resolution verifier; confirmed every added var holds the exact original hex and every change is visually inert. Accepted the deviation on evidence.
- **Prevention (future me):** A subagent's "done, zero impact" is a claim, not proof — independently verify against the source (here: resolved-CSS diff). When a hard pass-condition conflicts with a soft constraint, expect the agent to deviate; bound deviations by making the verifier, not the agent's word, the gate.
