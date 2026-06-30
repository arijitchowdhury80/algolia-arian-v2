# SESSION.md — PRISM (skills v2.1.0 · auto-deploy pipe · SPA chat upgrade)

**Status:** Session COMPLETE for what was tackled. arijit-skills v2.1.0 shipped + tagged; prism-hub
GitHub→VPS auto-deploy LIVE; SPA chat upgraded + LIVE. Four-item chat/channel initiative started:
chat done; **TOC blocked on user screenshot**; WhatsApp + canonical-format pending.

Date: 2026-06-30. Working dir: `/Users/arijitchowdhury/Dropbox/AI-Development/PIP` (home project; actual
work spanned the **arijit-skills** and **prism-hub** repos + the **chowmes VPS**).

**LATEST (post-persist reconcile):**
- arijit-skills: TOC commit `937841c` MERGED to **main** + pushed (resolves the earlier "push 937841c?"
  question — DONE). main = 937841c, clean.
- Verified: an arijit-skills→main push does **NOT** trigger the prism-hub webhook (different repo +
  the listener filters branch `feat/prism-vps-hosting`). Template/source changes reach live only via
  a prism-hub re-render+push (Tier 1).
- prism-hub keeps moving from the user's parallel pushes; the **pipe auto-deployed them cleanly**
  (VPS observed advancing dc738db → 845bd22 → local now c2ae53b). Pipe confirmed working on real pushes.
- **Tier-2 (CI-render) QUEUED** — see Remaining work + `memory/reference-prism-hub-autodeploy.md`.

---

## RESUME ACTION (do these first, in order)
1. Read this file + `memory/MEMORY.md` + `memory/project-prism-chat-cross-channel.md` +
   `memory/reference-prism-hub-autodeploy.md`.
2. **Ask the user for a screenshot with the TOC circled** before any layout change (see "TOC" below).
3. Check if the user finished the **Meta Business account** (WhatsApp). If yes → investigate Hermes
   channel architecture on the VPS, then build the WhatsApp channel bound to Cassandra.
4. Continue the **canonical output format** work (one Markdown contract across channels).

---

## WHAT SHIPPED THIS SESSION (all live / pushed)

### A. arijit-skills v2.1.0 (repo: `/Users/arijitchowdhury/Dropbox/AI-Development/Personal/arijit-skills`, branch feat/gemini-grounded-search merged to main, tags v2.0.0 + v2.1.0 pushed)
- **v2.0.0**: 22 per-skill READMEs + root README for `skills/algolia-audit-skills/`; version fields
  normalized to 3-part semver (floor 2.0.0; `algolia-intel-hiring` = 3.0.0, full source redesign).
- **Financial-chart axis fix** (`algolia-search-audit/templates/index-template.html`): replaced
  hardcoded `maxBarVal=56` + fixed gridlines with data-driven `axisMax()` (niceStep + 1-step headroom).
  Home Depot ($165B revenue) overflowed the old $56B axis (~3x off chart); now scales to any size.
  Separate bug from the older `pvB` parser fix. Test: `scripts/tests/test-finance-axis.mjs` (9 cases).
- **News migrated OFF Tavily** → keyless Google News RSS primary (`scripts/collect-news.py` rewritten;
  Tavily path + dead Apify code removed; docstring fixed). SKILL.md + README made consistent.
- **techstack**: README added + version → 2.0.0; SimilarWeb mislabel fixed (it's REST API, not MCP).
- **Frontmatter accuracy audit** across the suite: SimilarWeb = REST (traffic/competitors/techstack)
  not MCP; financials = yfinance lib not Yahoo MCP; eval named non-existent modules (fixed);
  campaign-abx stale sub-skill names; sales-plays missing 6th section.

### B. prism-hub → VPS auto-deploy (Vercel-style) — LIVE, verified
- See `memory/reference-prism-hub-autodeploy.md` for the full runbook.
- Push to `origin/feat/prism-vps-hosting` → GitHub webhook (id 647828356) → `prism.chowmes.com/gh-deploy`
  → Caddy `handle /gh-deploy*` → listener `127.0.0.1:9099` (HMAC) → `git -C /opt/prism-hub reset --hard`
  → served by `prism-chat-proxy.service` (8651). No restart needed. Verified end-to-end (real push
  af43e71 + dc738db auto-deployed; GitHub ping 200; bad sig 401).
- VPS pieces: `/opt/prism-hub` is now a git checkout (was manual copy; untracked `autozone` preserved —
  deploy NEVER runs `git clean`). `/opt/prism-deploy-hook/` (hook.mjs, deploy.sh, .env chmod600).
  systemd `prism-deploy-hook.service`. Caddyfile = `/home/chowmesadmin/lab-judge/Caddyfile` (docker
  caddy, host-net). Backup: `/tmp/prism-hub-backup.tgz`. Webhook secret in scratchpad
  `gh_webhook_secret.txt` (this session's tmp) + VPS .env.
- VPS access: `ssh-hermes-vps` helper + scratchpad `chowmes.env` (SSH_HOST=72.61.72.147,
  user=chowmesadmin, key ~/.ssh/chowmes_ed25519). sudo passwordless.

### C. SPA chat upgrade (`/Users/arijitchowdhury/prism-hub/chat-widget.js`) — LIVE
- Renders Markdown (bold/italic/headings/lists/code/links) instead of raw text. Inline links clickable.
- Auto-links mentions of audit sections → in-page `#section-…` anchors that smooth-scroll.
- Fluid sizing (clamp), slide-in animation, expand toggle → full viewport height.
- Does NOT cover content: on ≥1200px viewports, `html.pc-chat-open #content{margin-left:248px;
  margin-right:470px}` shifts the report so the panel sits beside it. Verified live.
- All 10 reports re-rendered (TOC template change + still benefit from earlier axis fix).

---

## OPEN / NOT DONE (be explicit — do not claim these done)

### TOC — BLOCKED on user input
- User rule: **TOC always LEFT, chat always RIGHT, standardized across EVERY audit.**
- I moved `#section-sidebar` (right→left in index-template.html, re-rendered all 10, deployed).
- **PROBLEM:** `#section-sidebar` renders as a 0×0 empty box on Overview AND Search Audit tabs — and
  it was ALSO 0×0 on the live site BEFORE any change. So it is likely NOT the element the user calls
  "the TOC", or it is pre-existing-broken. Candidates: the top tab bar; `#section-sidebar` (side
  scroll-nav, empty); the in-content `.toc-list` score-heatmap.
- **NEXT: get a screenshot with the TOC circled before changing layout again.** Don't guess.

### WhatsApp channel (Meta WhatsApp Cloud API — decided)
- User has NO Meta Business account yet; is creating one. Steps in
  `memory/project-prism-chat-cross-channel.md`. Then: investigate whether Hermes has a WhatsApp
  adapter or build one; bind to the SAME Cassandra agent/profile as Telegram + SPA.

### Cross-channel canonical output format
- Not built. Plan: Cassandra emits ONE Markdown; section refs as URLs `…/<slug>/#section-<id>`; each
  channel renders that one format (SPA=HTML+scroll built; Telegram=TG markdown; WhatsApp=WA format).
  This is the "modify Hermes base functionality" work (prism-report-qa plugin output contract).

### Tier-2 auto-deploy (CI-render) — QUEUED (optimization, not blocking)
- Pipe is Tier 1 (VPS serves committed HTML; author runs `deno render` before push). To remove the
  local render step: build **GitHub Actions on prism-hub** that renders changed audit-data (checks out
  prism-hub + arijit-skills template) and commits HTML → existing webhook auto-pulls. Keep prod VPS
  dumb (do NOT render on it — shared with Hermes). Guardrails: temp→validate→atomic swap→keep-last-good.
  Full notes in `memory/reference-prism-hub-autodeploy.md`. Sequence after TOC/WhatsApp/canonical.

---

## DECISIONS LOCKED
- Versioning: per-skill semver, floor 2.0.0 baseline, hiring 3.0.0. Git tags v2.0.0 + v2.1.0.
- News retires Tavily via **Google News RSS** (not Gemini — wrong shape for dated articles).
- Auto-deploy = **webhook pull** (not Actions push) — keeps VPS creds out of GitHub. Tier-1 (serve
  committed HTML) now; Tier-2 (VPS render) is a 1-line flip in deploy.sh.
- Prod branch for prism-hub auto-deploy = `feat/prism-vps-hosting` (had content; main was behind).
- WhatsApp provider = **Meta WhatsApp Cloud API**.
- TOC standard = always left; chat always right (element TBD — see OPEN).

## FILES WRITTEN THIS SESSION
- arijit-skills: 22 READMEs + root README; `index-template.html` (axis + TOC-left);
  `scripts/collect-news.py` (rewrite); `scripts/tests/test-finance-axis.mjs` (new); version fields in
  ~21 SKILL.md; techstack SKILL.md+README; frontmatter fixes (traffic/competitors/financial-public/
  sales-plays/campaign-abx/eval/news/techstack). Commits ef458f8(user), d940ec3, 1598f39, 80ae128,
  d3a7854. Tags v2.0.0, v2.1.0.
- prism-hub: `chat-widget.js` (rewrite); all 10 `*/index.html` re-rendered (×3 rounds). Commits incl
  af43e71, dc738db. Branch feat/prism-vps-hosting pushed.
- VPS: /opt/prism-hub→git, /opt/prism-deploy-hook/*, systemd unit, Caddyfile gh-deploy route.
- memory: feedback-parallel-user-commit-mid-session, reference-prism-hub-autodeploy,
  project-prism-chat-cross-channel, updated feedback-strip-parsefloat-unit-blind, MEMORY.md,
  session_pointer.

## REFERENCE FILES (read on resume)
- `memory/project-prism-chat-cross-channel.md` — the 4-item initiative + WhatsApp steps + canonical fmt
- `memory/reference-prism-hub-autodeploy.md` — auto-deploy runbook
- `~/prism-hub/chat-widget.js` — SPA chat (markdown + section-jumps + slide-in)
- arijit-skills `.../templates/index-template.html` — report template (TOC `#section-sidebar`, axis)
