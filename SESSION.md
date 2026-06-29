# SESSION.md — PRISM (= Chowmes-PRISM)

**Last updated:** 2026-06-28 (autonomous-standardization PILOT complete; loop prompt ready, NOT launched)

## STATUS (one line)
**Pilot for the autonomous report-standardization run is COMPLETE.** Render pipeline unblocked + proven, model-routing economics standardized, petsmart canary ran end-to-end (staged-sync model), and a copy-paste `/loop` prompt is ready. **Next action = launch the loop** (or eyeball `run/` first).

> **NAMING CANON:** "PRISM" = Chowmes-PRISM (Hermes instance on the VPS). Published reports site = `prism-hub` (GH repo; live `algolia-arian-v2.vercel.app`; local `~/prism-hub`). Internal app = `PIP/frontend` (NOT the chat target).

---

## RESUME ACTION (do FIRST next session)
1. Read this file + `MEMORY.md` (esp. `[[feedback-model-routing-by-tier]]`, `[[project-prism-hub-chat-live]]`).
2. Read the disk-truth ledger: `docs/workspace/hermes-prism-integration/spike-unify-audit/run/state.json` — every company × step, prereqs (DONE), gates, findings.
3. **Launch the autonomous loop:** type `/loop`, paste THE LOOP PROMPT below, send (no interval = self-paced). OR review `run/sync-all.sh` + `run/state.json` first if not yet confident.

### THE LOOP PROMPT (paste after `/loop`)
```
ultracode. Autonomous report standardization, hands-off. Disk truth =
docs/workspace/hermes-prism-integration/spike-unify-audit/run/state.json — read
it FIRST every tick; source of truth, survives compaction.

DONE (do NOT redo): prereqs (render path fix, template tokenization — committed
314d045 in arijit-skills); petsmart canary (RENDER/SPA done, SYNC staged, COMMIT
db32cad). Start at the next PENDING units.

ONE-TIME before first gap company: move homedepot-mexico JSON from nested
~/prism-hub/homedepot-mexico/homedepot-mexico-audit-data.json to root
~/prism-hub/homedepot-mexico-audit-data.json (render + index scan read root path).

MODEL ROUTING (per global CLAUDE.md MODEL ECONOMICS — every subagent declares a
tier): collectors/validators/renders/file-ops → model:haiku (low). gap-fill
grounded-synthesis/edits → model:sonnet (medium). orchestration (you) + adversarial
verify of a critical report claim → model:opus (high). All-opus = cost bug.

LOOP each tick: read state.json → pick next PENDING unit (steps_order) → dispatch a
FRESH SUBAGENT at the right tier returning ONLY {status, artifact_path, note}
(heavy output stays in the subagent) → run the gate → write result to ledger →
persist → advance.

PER-STEP GATES (DONE only if gate passes): GAPCHECK/FIX_DATA = audit_data_schema.py
PASS; SKILL_PATCH = pytest PASS (only if a skill bug found); RENDER = {slug}/index
.html written AND hub-root index.html md5 unchanged; SYNC = APPEND slug to run/sync
-all.sh (LOCAL write — never write the live VPS store); COMMIT = git commit LOCAL
only, no push. DEPLOY is global/staged in run/DEPLOY.txt — never deploy.

RULES: two failures same unit → BLOCKED + skip + continue. 429/quota = retry-later
(re-queue, not BLOCKED). compromised-key auth-fail = BLOCKED + surface. Wave 2 (7
dataless full re-audits: dell, footlocker, jbl, michaelkors, thenorthface, torrid,
autozone) needs MCP keys — if BuiltWith/SimilarWeb keys 401, BLOCK that audit +
surface (keys may be compromised). Don't ask me anything with a sane default — log
to ledger assumptions_log + continue. STOP only for: destructive/irreversible op,
secret rotation, or all-remaining BLOCKED. When all units DONE/BLOCKED: write
run/FINAL-REPORT.md and stop.

When you stop: tell me to review run/sync-all.sh then run `! bash <path>/run/sync
-all.sh` and `! vercel --prod` to publish.
```

---

## WHERE WE STOPPED (exact)
Pilot done; loop NOT launched. petsmart canary fully proven under the staged-sync model. Both repos have LOCAL commits (no push): `~/.claude/skills/algolia-search-audit` @ `314d045` (render fix + template tokenization + migrate tool); `~/prism-hub` @ `db32cad` (gitignore + homepage regen + petsmart render). Awaiting user to launch `/loop` or eyeball `run/`.

## DECISIONS LOCKED THIS SESSION
- **Autonomy mechanism:** `/loop` (NOT `/goal` — doesn't exist) + `ultracode` keyword (flips to Workflow orchestration) + disk-truth `state.json` ledger + per-unit subagents (context firewall) + validator gates + two-strikes-then-BLOCK. Context rot solved by: heavy work never enters main context (subagents return thin), state lives on disk.
- **MODEL ECONOMICS & ROUTING** standardized GLOBALLY (`~/.claude/CLAUDE.md` new section + memory `feedback-model-routing-by-tier`): T1 haiku / T2 sonnet / T3 opus / T4 fable; orchestrator stays high, workers route down; severity escalates a tier. Pricing verified via `claude-api` skill (Opus out = 5× Haiku).
- **Prod writes are STAGED, not executed by the loop** (user chose "stage, run once"): SYNC appends to `run/sync-all.sh`; DEPLOY in `run/DEPLOY.txt`. User runs `! bash run/sync-all.sh` + `! vercel --prod` on return. Loop never writes the live VPS store or deploys (auto-mode permission guard blocks it anyway — correctly).
- **Style gate = template-hygiene linter** (doesn't change output). Chose to TOKENIZE all 108 violations (design SOP stays strict) over warn/bypass. Zero visual change PROVEN by resolved-CSS diff.
- **Commits: LOCAL only, no push** (held for user).

## PILOT FINDINGS (all fixed/handled)
1. `render-audit.ts` site mode wrote to cwd → clobbered hub homepage. FIXED (`join(cwd, slug)`), verified, committed.
2. Render hard-blocked by 108 template style violations (would BLOCK all 17). Tokenized (96 font-size + 12 raw-color), gate EXIT=0, zero-visual-change proven (`scratchpad/verify_tokenization.py`), committed.
3. Wrong agent-type (no Bash → can't verify) + subagent over-scoped (added :root vars). Caught by independent verify, proved benign.
4. SSH to VPS: use `chowmesadmin` + `~/.ssh/chowmes_ed25519` (root login DISABLED), passwordless sudo. NOT root.
5. Prod SYNC overwrite BLOCKED by auto-mode permission guard → solved via staged `sync-all.sh`.
6. Missing DEPLOY step (rendered pages need `vercel --prod`/push) → added, staged in `run/DEPLOY.txt`.
7. homedepot-mexico JSON at NESTED path `homedepot-mexico/homedepot-mexico-audit-data.json` (no root file) → loop must move to root before GAPCHECK/RENDER.
8. Homepage finds 8/10 (homedepot-mexico + oriental-trading lack rendered `<slug>/index.html`) → loop RENDER fills.

## REMAINING WORK (order)
1. **Launch the loop** (paste prompt above after `/loop`).
2. Loop processes: 6 with-data gaps (nike, savage-x-fenty, oriental-trading, llbean, dsw, homedepot-mexico) — FIX_DATA→RENDER→SPA→SYNC-stage→COMMIT; + render the already-clean british-airways/labanquepostale/brooks-running; then Wave 2 = 7 dataless full re-audits (dell, footlocker, jbl, michaelkors, thenorthface, torrid, autozone).
3. **USER actions on loop completion:** review `run/sync-all.sh` → `! bash …/run/sync-all.sh` (prod grounding) → `! vercel --prod` (publish pages) → `git push` both repos if desired.
4. **USER (still pending from before):** rotate BuiltWith + SimilarWeb keys (Wave 2 audits 401 until done); rotate free-tier grounding-gate Gemini key (Nike chat 429s); Vercel project rename→prism-hub.

## WHAT HAS NOT BEEN DONE (no false claims)
- Loop NOT launched. Only petsmart (canary) processed; 16 companies PENDING.
- `run/sync-all.sh` NOT executed (prod VPS store untouched this session). `vercel --prod` NOT run (pages not republished).
- Commits NOT pushed (both repos local-only).
- Keys NOT rotated. Vercel project NOT renamed.
- 6 with-data gap reports still fail schema (genuine content gaps); 7 dataless have no audit data.

## REFERENCE FILES
- **Ledger (resume here):** `docs/workspace/hermes-prism-integration/spike-unify-audit/run/state.json` (17×8 + prereqs + gates + findings). Staging: `run/sync-all.sh`, `run/DEPLOY.txt`.
- Lessons: `docs/sop/lessons-log.md` (render clobber, gate display-cap, agent-type/Bash, byte-diff-wrong-test, subagent over-scope).
- Spike docs A–L: `docs/workspace/hermes-prism-integration/spike-unify-audit/` (L = standardization status).
- Verifier: `<scratchpad>/verify_tokenization.py` (resolved-CSS zero-visual-change proof).
- Global routing rule: `~/.claude/CLAUDE.md` "MODEL ECONOMICS & ROUTING".
- Tools: render `render-audit.ts <slug> site`; hub homepage `generate-index.ts`; migrate `migrate-audit-data.py`; validators `audit_data_schema.py` + `template_contract.py` (in `~/.claude/skills/algolia-search-audit/scripts/`).

## FILES WRITTEN THIS SESSION (key)
- **arijit-skills** (committed `314d045`, NOT pushed): `scripts/render-audit.ts` (site path fix), `templates/index-template.html` (108 tokenized), `scripts/migrate-audit-data.py`.
- **prism-hub** (committed `db32cad`, NOT pushed): `.gitignore`, `index.html` (homepage regen), `petsmart/index.html` (re-render).
- **PIP** (uncommitted): `docs/workspace/.../run/{state.json,sync-all.sh,DEPLOY.txt}`, this SESSION.md, `docs/sop/lessons-log.md` (+4 entries).
- **Global** `~/.claude/CLAUDE.md`: MODEL ECONOMICS & ROUTING section.
- **Memory:** `feedback-model-routing-by-tier.md` + MEMORY.md index line.
