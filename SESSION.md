# SESSION.md — PRISM e2e cycle + Gemini-grounded skill migration + chowmes.com hosting

**Status:** Active multi-thread build. **KEYSTONE PROVEN** — headless claude-cli runs the algolia
skills on the VPS and grounds research via the new `gemini_search.py` (no WebSearch, no fabrication).
**Branch: `feat/prism-e2e-cycle`.**

**Last updated:** 2026-06-29 (~8pm EDT)

---

## RESUME ACTION (next session, in order)
1. Read this file + memory [[feedback-prism-orchestrates-skills-not-rebuild]] + [[feedback-claude-cli-setup-token-headless]].
2. VPS reachable via `ssh chowmes-vps` (alias = chowmesadmin@72.61.72.147). **Use `dangerouslyDisableSandbox:true` on every VPS bash** (raw-TCP egress is sandbox-blocked; SSH works unsandboxed).
3. Three live workstreams below — pick up where each says.

---

## WHAT GOT PROVEN THIS SESSION (the keystone)
Full read-receipt: `claude -p "Use the algolia-intel-company skill for petsmart.com"` ran headless on the
executor and produced `01-company-context.json` with **grounded** fields:
`hq=Phoenix AZ, founded=1986, public_private=private, vertical=Pet specialty retail, employee_count=~20,000,
3 execs` — ALL `src='gemini grounded search'`, `[FACT — gemini grounded search]`, `enrichment_completed=True`.
BuiltWith degraded → null → grounded-filled. **NO WebSearch** (excluded from `--allowed-tools`). This validates
the whole architecture: skills are the engine, Scout acquires, gemini_search grounds, no fabrication.

## INFRA UNBLOCKED THIS SESSION
- **Headless claude-cli auth** = Claude **subscription** (API key was credit-empty). Token at
  `/opt/prism-executor/.claude-oauth.env` (`CLAUDE_CODE_OAUTH_TOKEN`, chmod 600). Run env MUST
  `unset ANTHROPIC_API_KEY` + `source` that file. (`setup-token` needs a real TTY — user ran it; see
  [[feedback-claude-cli-setup-token-headless]].) ⚠️ The OAuth token leaked into chat earlier — ROTATE it
  (user re-run `claude setup-token`, swap the file) once convenient.
- **GEMINI_API_KEY** (paid, works, no 429) lives in `/root/.hermes-prism/.env`. Read as root, pass inline to runs.
- **SCOUT_API_KEY** in `/opt/prism-platform/.env`; Scout on loopback `127.0.0.1:8421`.
- **Brain (Hermes)** on loopback `127.0.0.1:8642/v1/responses` (bearer-gated; 401 w/o key = reachable).

---

## THREAD A — Gemini-grounded migration ✅ CORE DONE (2026-06-29); sync+commit pending
**Right-tool routing (user's correction, internalized):** Scout = acquire the TARGET's own data
(company details, about, executives, **careers/jobs**, IR); Gemini-grounded Google search = OPEN-WEB
research (industry benchmarks, analyst quotes, third-party news, competitor tech, external estimates).
Do NOT blanket-swap everything to gemini.
- ✅ `gemini_search.py` (CLI helper) — built, 6 tests, live-smoked grounded.
- ✅ `platform_utils.gemini_search_results()` — Tavily replacement, returns grounded PROSE as result
  `content` (google_search grounding can't emit JSON), single result (no per-citation stat dup),
  no-fabrication gate (ungrounded→[]). 6 tests. **Live-verified via collect-industry → grounded 2.5% benchmark.**
- ✅ 2 scripts swapped (alias import): `collect-industry.py`, `collect-exec-media.py`. (`collect-news.py`=Apify,
  `collect-investor.py`=WebFetch/Yahoo — neither used Tavily; left as-is, correct.)
- ✅ 16 SKILL.md migrated: intel-company (live-proven) + competitors, financial-pub/priv, hiring, social,
  traffic, partner, industry, investor, news, audit-research/factcheck/eval/report, search-audit (via 4 subagents).
- ✅ **intel-hiring re-routed to Scout** (Layer 1 = Scout scrape of careers/jobs page via POST {SCOUT_URL}/scrape;
  Layer 2 = gemini for third-party boards) — fixing the subagent's blanket-gemini mis-route.
- ⬜ **PENDING:** sync ALL migrated skill files to VPS `/home/chowmesadmin/.claude/skills/` (only company/industry/
  exec-media/platform_utils synced so far). NOT committed to arijit-skills repo. exec-media + hiring NOT live-verified
  (doc/low-risk). Cosmetic "tavily"/"TAVILY" strings remain inside the 2 scripts (collection_method labels) — honesty polish.

## THREAD A (history) — Gemini-grounded skill migration
**Decision (user):** ALL audit skills switch from claude-cli **WebSearch → Gemini-grounded Google search**
(Scout stays PRIMARY for acquisition). WebSearch was NEVER removed before — the skills genuinely used it.
**Mechanism chosen:** a Bash-invoked python helper, NOT an MCP server. **Sequencing:** prove on one skill, then propagate.

- ✅ Built `~/.claude/skills/algolia-search-audit/scripts/gemini_search.py` (mirrors verified
  `prism_platform/v2/gemini_api.py` contract: `generateContent` + `tools:[{google_search:{}}]`, model
  `gemini-2.5-flash`; returns `{answer,citations[],queries[],grounded}`; reads `GEMINI_API_KEY`). **6 unit
  tests green** (`scripts/tests/test_gemini_search.py`); **live-smoked** (grounded:true on petsmart query).
- ✅ Migrated `algolia-intel-company/SKILL.md`: Step 2b + Step 3a WebSearch/Tavily → `gemini_search.py`;
  frontmatter `mcp_required` updated; WebFetch direct-URL fetches kept. Proven via the keystone run.
- ✅ Synced both files to VPS `/home/chowmesadmin/.claude/skills/...` (the claude-cli discovery path).
- ⬜ **PROPAGATE (next):** Explore agent mapped the full surface —
  - **4 scripts actually call Tavily/WebSearch APIs** → refactor to use gemini_search:
    `collect-industry.py` (34 refs; **preserve its 24-month staleness gate**), `collect-exec-media.py` (23),
    `collect-news.py` (17), `collect-investor.py` (3, WebSearch for transcript discovery).
  - ~12 other SKILL.md files have WebSearch *instructions* (LLM tool) → swap to gemini_search.py like intel-company.
  - 115 WebFetch refs = direct-URL fetches → LEAVE. No skill hard-declares `mcp_required: websearch`.
  - AGENT-CONTEXT mandates MCP-first (BuiltWith/SimilarWeb/Yahoo primary); Tavily/WebSearch = Tier-3 swap point.
  - Skills symlinked to arijit-skills repo locally → edit→commit→scp to VPS. NOT yet committed. Route bulk to cheap tiers (haiku/sonnet).

## THREAD B — chowmes.com hosting ✅ DONE (2026-06-29)
**PRISM fully self-hosted under `https://prism.chowmes.com` on the VPS; judge decoupled.** Verified live:
- `prism.chowmes.com` → Caddy → `prism-chat-proxy.service` (Node, `127.0.0.1:8651`) serving the **static reports
  SPA** (`/opt/prism-hub`, rsynced from `~/prism-hub`) + **`POST /api/chat`** → Hermes loopback `127.0.0.1:8642`.
  Grounded chat works over HTTPS (petsmart proven). TLS auto via Caddy. No Vercel, no judge in the path.
- Proxy = `~/prism-hub/server/chat-proxy.mjs` (ports the Vercel `api/chat.js` logic; static file server + chat).
  Service env `/opt/prism-chat-proxy/.env` (HERMES_API_URL loopback + API_SERVER_KEY bearer + PORT 8651 + STATIC_DIR).
- `scout.chowmes.com` → Scout (8421), live. Caddy block added in `/home/chowmesadmin/lab-judge/Caddyfile` (backup `.bak-*`).
- **Judge paths REMOVED:** `judge.contentengagement.info/scout` + `/hermes-api` now **404**; judge block = lab-judge app only.
- ⚠️ **Side effect:** the OLD Vercel SPA (`algolia-arian-v2.vercel.app`) chat is now BROKEN (it called judge/hermes-api).
  Superseded by prism.chowmes.com. To re-deploy the SPA: `rsync ~/prism-hub/ → /opt/prism-hub/` (exclude api/,server/,node_modules,.bak) + `systemctl restart prism-chat-proxy`. Old `publish.sh` (Vercel) is retired.
- Minor: apex `chowmes.com` still listed in the Vercel account (removal denied by guard; harmless — DNS at Hostinger).
- `chat-proxy.mjs` NOT yet committed to the prism-hub repo.

## THREAD B (history) — chowmes.com hosting (was IN PROGRESS, user-driven)
User bought **chowmes.com** (Hostinger DNS, nameservers apollo/athena.dns-parking.com). Structure rule
(agreed): **subdomain-per-product is right** for separate apps; **but PRISM = everything under one name,
`prism.chowmes.com`, hosted on the VPS** (front SPA + `/api/*` paths → brain on loopback). No `hermes.*`.
- DNS now: `prism` A → 72.61.72.147 (VPS) ✓, `scout` A → 72.61.72.147 ✓ (scout.chowmes.com Caddy block exists, live).
- ⚠️ I wrongly attached prism.chowmes.com to **Vercel** earlier (`vercel domains add`, project "prism") — **UNDO
  it** (DNS points to VPS, won't verify). 
- **LOCKED PLAN — host PRISM on the VPS under prism.chowmes.com:**
  1. Caddy block `prism.chowmes.com`: `file_server` static SPA + `/api/chat` → a small VPS Node proxy → brain.
  2. Move `~/prism-hub` static → VPS (rsync to e.g. `/var/www/prism`).
  3. Port `api/chat.js` (Node SSE proxy: session-key bind `agent:main:prism:web:{sid}:acct:{slug}`,
     `[Account: slug]` prefix, Hermes `/v1/responses` stream→plaintext) to a standalone VPS Node service
     calling `http://127.0.0.1:8642` (loopback) with the Hermes bearer. Caddy routes `/api/chat` → it.
  4. Verify chat on prism.chowmes.com. THEN (destructive, last):
  5. **Disable judge paths** — remove `handle_path /scout/*` + `/hermes-api/*` from
     `/home/chowmesadmin/lab-judge/Caddyfile`, reload Caddy. (judge.contentengagement.info = completely separate.)
     ⚠️ The LIVE Vercel SPA currently calls `HERMES_API_URL=https://judge.../hermes-api` — do NOT disable until
     the new prism.chowmes.com chat path is verified, or repoint the existing Vercel SPA's env first.
- Active Caddyfile: `/home/chowmesadmin/lab-judge/Caddyfile` (docker container `caddy`, network_mode host).
  Has `scout.chowmes.com`→8421, and judge.contentengagement.info with `/scout/`,`/hermes-api/`,default→8787.

## THREAD C — full PRISM e2e cycle (PRIMARY GOAL, behind A)
The original goal: domain → full audit via the skills (orchestrated) → store → two-way chat (SPA + Telegram).
The skill runner = `/opt/prism-executor/run-audit.sh` (ALREADY EXISTS: `claude -p` headless, all-MCP, fail-loud
on `FILL_IN` placeholders). **Blocker B (open):** `.mcp.json` has `FILL_IN` for algolia/builtwith/yahoo-finance
+ no `.mcp.env`. User chose "fill all MCP keys now" — STILL NEED those keys from user. Once Thread A lands +
MCP keys in, wire run_pipeline → run-audit.sh (or per-skill runner), report-bridge, chat-trigger. See the
older plan `~/.claude/plans/polymorphic-enchanting-metcalfe.md` (module-rebuild parts SUPERSEDED by skill-orchestration).

---

## HARD CONSTRAINTS (user)
- **NO fabrication.** Blank stays blank. gemini_search `grounded:false` → field null, never model-knowledge.
- **PRISM orchestrates skills, never rebuilds them.**
- **Everything under prism.chowmes.com** (VPS-hosted); judge.contentengagement.info is separate.
- Don't storm the VPS (use the `chowmes-vps` ControlPersist alias; batch commands; `dangerouslyDisableSandbox`).
- Caveman mode active (terse); code/commits/security written normal.

## NOT DONE / NOT TRUE (no false claims)
- Propagation to the 4 scripts + ~12 skills NOT done. Local skill edits NOT committed/pushed.
- VPS prism.chowmes.com hosting NOT built. Vercel prism domain NOT yet removed. Judge paths NOT disabled.
- Full e2e audit NEVER run. MCP keys NOT provided. OAuth token NOT yet rotated.
