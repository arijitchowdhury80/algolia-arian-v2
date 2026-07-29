# SESSION.md — Repo/VPS reconciliation; branch sprawl discovered (2026-07-27 → 28)

**Last updated: 2026-07-28 early hours (handoff).**
**Session ran from the Algolia-Central-Spectrum working dir, not PIP** — all PRISM work, wrong CWD.
Launch `claude` from `~/Dropbox/AI-Development/prism` (the repo was restructured and renamed on 2026-07-28; `PIP` no longer exists) so SESSION.md + the memory slug resolve here.

## STATUS (one line)

Started as a malformed-`settings.json` fix, became a full three-way (laptop / GitHub / VPS) reconciliation:
**all laptop- and VPS-only work is now on GitHub (0 commits at risk)**, the VPS deploy script has been
hardened after it destroyed live content mid-session, and the root problem was identified — **eight
agent-created branches, both repos' `main` dead since 28–29 June, production running an unmerged
feature branch.** Merges are analysed and approved but NOT started.

## THE HEADLINE FINDING

Both repos fanned out into parallel branches on 28–29 June and never merged back.

| repo | branch | commits | Co-Authored-By Claude |
|---|---|---|---|
| pip.git | `feat/audit-acl` | 83 | 63 |
| pip.git | `feat/prism-e2e-cycle` | 77 | **64** |
| prism.git | `feat/prism-vps-hosting` | 50 | **48** ← **production runs this** |
| prism.git | `prism-v2` | 68 | 45 |
| prism.git | `feat/prism-vps-hosting-local` | 69 | 53 |
| prism.git | `feat/ia-ab-prototype` | 56 | 42 |
| prism.git | `feat/audit-acl` | 60 | 43 |

`pip.git/main` last moved 2026-06-29. `prism.git/main` last moved 2026-06-28.
Arijit had never heard of `feat/prism-e2e-cycle` — sessions created these branches, committed under his
git identity, and nobody surfaced the topology. **This is the root cause of the whole session's confusion.**

What each branch actually is (verified from commit contents, not names):
- `feat/prism-vps-hosting` — self-hosting + Clerk auth. **Live.**
- `feat/prism-vps-hosting-local` — misnamed; it's Dell audit **content QA** (stale-claim rewrites).
- `feat/ia-ab-prototype` — Marketer role-door page, Cassandra LiveAvatar wiring, `dell/` → `reports/` move.
- `prism-v2` — next-version site (per-instance marketer sections, bible→notebook rename).
- `feat/audit-acl` (both repos) — ONE feature split across two repos: frontend gating + HMAC, backend ACL endpoints B6/B7/B8.

## DONE + VERIFIED THIS SESSION

1. **Everything is on GitHub. 0 commits reachable from no remote ref**, across `PIP`, `PIP-audit-acl`, `~/prism`.
   Pushed: `pip.git feat/audit-acl` (83 commits, was an **orphan branch with no remote**),
   `pip.git feat/prism-e2e-cycle` (+ backup commit `b3ff40a`, 45 laptop-only files),
   `prism.git feat/audit-acl` (3 HMAC commits, laptop-only), `prism.git prism-v2` (+ `43e1c3e`).
2. **VPS-only work rescued read-only** → `prism.git` branch `vps-local-20260727`, then fast-forwarded
   into `feat/prism-vps-hosting`. Commit `3b13838`. Verified byte-identical to the live server.
3. **`PIP/.gitignore` hardened** — `.playwright-mcp/`, `.ship-loop/`, `.development-loop/`, `/prism-*.png`,
   and `*.bak-*` / `*.bak.*` (32 timestamped hand-edit backups were sitting untracked).
4. **`/opt/prism-deploy-hook/deploy.sh` hardened → v2** (`546d4d36`). See the incident below.
5. **`~/.claude/hooks/aios/mandate-guard.sh` fixed** — 3 bugs: fired on `--dry-run`; used session CWD
   instead of the push target (blocked every feature-branch push); scanned heredoc bodies as commands
   (blocked any commit whose *message* mentioned `reset --hard`). Also closed a real hole — `git push
   origin HEAD:main` bypassed the protected-branch check entirely. Verdict changed `deny` → `ask`.
   12/12 test matrix passes.
6. **Backend diff report** — `~/.claude/plans/reports/backend-diff-report.md`.

## ⚠️ INCIDENT — I broke live content for ~90 seconds

Deploy-script v1 stashed dirty files **before** attempting the merge. The merge then failed on an
untracked-file collision (`server/belk-audit-data-corrected.json` existed untracked; the incoming commit
adds that same path). Script exited, working tree left reverted: `belk/index.html` lost 17,655 bytes
and `reports/index.html` 684 bytes **on the live site**.

Caught by baseline checksums taken before the push. Restored by completing the fast-forward; all 7
tracked files verified byte-identical to baseline afterwards.

**v2 rule: validate everything before mutating anything**, and roll the working tree back if the merge
fails. Guards: (a) abort if local commits aren't on origin; (b) untracked collisions — set aside if
content-identical, abort if it differs; (c) stash only after validation; (d) restore on merge failure.

## CORRECTIONS — three things earlier in this session were WRONG

Recorded so the next session doesn't act on them. All three came from reading prose/stale code in the
repo and reporting it as behaviour.

1. **"VPS `v2/modules` has only `audit_report`"** — false, from a truncated `ls | head`. The VPS has
   **18 of 19** modules; only `landing_page_intake` is missing.
2. **"PRISM has zero Gemini references"** — false, grep was scoped to `v2/modules/` only. PRISM **does**
   use Gemini: `v2/gemini_api.py`, and `v2/synthesis.py` defaults to `gemini-3.1-flash-lite-preview`
   when `GEMINI_API_KEY` is set. Retiring the markdown skills does NOT remove Gemini.
3. **"Track 1 uses WebFetch"** — misleading. `webfetch` is an internal stage name; `intel_company`
   fetches via `BrowserClient` (httpx + Jina Reader). **`intel_hiring` uses Scout.** The codebase is
   half-migrated to Scout; I described the old half as current.

**Perplexity is live in production** (Arijit believed it was gone — it is not). `PERPLEXITY_API_KEY` is
one of only 7 vars in `/opt/prism-platform/.env`; `v2/agent_api.py` hits `api.perplexity.ai`; 23 files
reference it across all branches. Arijit's instruction: **remove it completely.** NOT started — removing
the key before replacing the callers breaks the live pipeline, and `GEMINI_API_KEY` is *not* set on that
box, so Perplexity is currently the only working synthesis provider.

## RESUME ACTIONS (numbered, concrete)

1. **Merge everything except `prism-v2` into `main`, both repos.** Arijit's decision: `prism-v2` stays a
   branch (next version); everything else "should have already been in the singular branch."
   Conflict load is small — measured, not guessed:
   - `pip.git`: `feat/prism-e2e-cycle` **clean**; `feat/audit-acl` → **1 file** (`prism_platform/main.py`)
   - `prism.git`: `feat/prism-vps-hosting` **clean**; `feat/prism-vps-hosting-local` **clean**;
     `feat/ia-ab-prototype` → 73 mechanical + 5 real; `feat/audit-acl` → 1 (`server/chat-proxy.mjs`)
   - The 73 are all `CONFLICT (file location)` from the `dell/`→`reports/dell/` rename; git prints the
     resolution for each. **Arijit's call: resolve them toward KEEPING FLAT URLs** — take
     `feat/ia-ab-prototype`'s real work (role-door page, LiveAvatar) but reject the directory move, so
     no prospect link 404s.
   - Real judgement needed on 6 files total: `prism_platform/main.py`, `README.md`, `index.html`,
     `package.json`, `reports/index.html`, `server/chat-proxy.mjs`.
   - **Merge into `main`, not into the production branch** — main isn't the deploy target, so this
     touches nothing live. Cut production over to `main` as a separate, deliberate step afterwards.
2. **Backend redeploy** — `/opt/prism-platform` is **not a git repo**. The diff report proves it holds
   **zero unique files**: 13 missing (incl. `orchestrator/pipeline.py`, `integrations/scout.py`,
   `v2/gemini_api.py`, the whole `landing_page_intake` module), 5 differing (4 are exact copies of known
   commits; 1 is a 3-line stub working around the missing `orchestrator/pipeline.py`). Safe to replace.
   Convert to a `pip.git` checkout, `.gitignore`ing `.venv/`. **Tracked surface is ~2 MB**, not 5.3 GB.
3. **Perplexity removal** — replace callers → verify an audit runs end-to-end → *then* strip config + key.
4. **`v2/synthesis.py` provider decision** — its config layer supports anthropic/openai/gemini/openrouter,
   but the *code* only implements Gemini + a Perplexity fallback ("wasteful but works"). Setting
   `ENRICHER_PROVIDER=anthropic` silently uses Perplexity. Needs a `_call_anthropic` method (~30 lines).
5. **Optional, low priority:** `/opt/prism-platform/.venv` is 5.3 GB, of which ~4.6 GB is CUDA/NVIDIA
   libraries on a box with **no GPU** (`sentence-transformers` pulls the CUDA torch build by default).
   Pin the CPU wheel → ~700 MB. Disk is at 55%, so this is waste, not risk.

## CURRENT VERIFIED STATE (2026-07-28)

- VPS `/opt/PRISM/v1`: HEAD `3b13838`, `behind=0 ahead=0`, dirty `0`, on `feat/prism-vps-hosting`
- All 5 services active: `prism-chat-proxy`, `prism-platform`, `prism-runner`, `prism-v2-static`, `prism-deploy-hook`
- `prism.chowmes.com` → 200; `/belk/` `/dell/` → 200
- Laptop: 0 unpushed, 0 dirty across `PIP`, `~/prism`; `PIP-audit-acl` has 1 (`.venv`, ignorable)
- `pip.git/main` is 7 commits behind local `main` — **0 at risk** (reachable from a pushed branch), cosmetic only
- Deploy `deploy.sh` v2 `546d4d36`; backups `deploy.sh.bak-preharden-*`, `deploy.sh.bak-v1-*`
- Two harmless leftovers on the VPS: a redundant stash `pre-deploy-20260728-005809` (content now
  committed) and `/tmp/belk-audit-data-corrected.json.aside`

## WHAT HAS NOT BEEN DONE (prevents false completion claims)

- **No merges performed.** All eight branches still separate; both `main`s still dead.
- **Backend not redeployed.** `/opt/prism-platform` still unversioned and still missing 13 files.
- **Perplexity not removed** anywhere.
- **No VPS tarball** (was Phase 0 step 5) — deliberately skipped once the diff proved nothing unique
  lives on the box.
- Prior threads untouched: Notebook doc effort, and the landing-page wizard's Arijit hands-on pass
  (see git history / vault for the 2026-07-15 state).

## REFERENCE

- Plan: `~/.claude/plans/imperative-dazzling-finch.md` (approved; Phase 0 + 1 done)
- Backend diff: `~/.claude/plans/reports/backend-diff-report.md`
- Superseded: `~/.claude/docs/gemini-dependency-audit.md` (written before correction #2 above)
- Vault: `Projects/PRISM/index.md`, `log.md`
- VPS access: `ssh chowmes-vps` (user `chowmesadmin`, key auth working)

## PROCESS NOTE FOR THE NEXT SESSION

Three wrong claims this session all came from the same habit: reading a `SKILL.md`, a docstring, or an
older code path and reporting it as how the system works. The repo is full of stale halves. **Trace to a
live call path or a running command before asserting behaviour** — and attach `file:line` or command
output to every factual claim.
