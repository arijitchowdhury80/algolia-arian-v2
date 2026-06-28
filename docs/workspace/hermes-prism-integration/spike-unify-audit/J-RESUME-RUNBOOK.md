# J — RESUME RUNBOOK (paste-and-go when you're back)

Everything below was blocked headless — either the auto-permission gate (file deletes/commits while you were away) or needs your secrets. Each block is copy-pasteable. Do them in order.

`.gitignore` is ALREADY fixed (excludes node_modules/.next/.claude/TEMP/*.bak), so the push below won't suck in junk.

---

## 0. 🚨 FIRST: rotate the exposed keys (task #15)
The `arijit-skills` repo is PUBLIC and the old BuiltWith + SimilarWeb keys were in its history (now scrubbed + force-pushed, but assume scraped).
- BuiltWith dashboard → regenerate API key.
- SimilarWeb → revoke `483b77…`, create new.
- Update them wherever used (your local `.env.local`, and `/opt/prism-executor/.mcp.env` in step 3).
GitHub may still cache old SHAs — for a hard purge, delete+recreate the repo or ask GH Support.

---

## 1. Finish the PIP cleanup (the gated deletes)
```bash
cd ~/Dropbox/AI-Development/PIP
# restore the 3 canonical architecture docs CLAUDE.md references, then drop TEMP
cp TEMP/2026-04-09-prism-v2-implementation-plan.md docs/plans/
mkdir -p docs/specs
cp TEMP/2026-04-09-prism-unified-architecture-design.md TEMP/unified-module-architecture.md docs/specs/
# Tier-1 disk junk (~1.14 GB, all gitignored/regen-able)
rm -rf frontend/.next .mypy_cache .pytest_cache .ruff_cache frontend/.clerk/.tmp
find . -name __pycache__ -type d -not -path './.venv/*' -not -path '*/node_modules/*' -exec rm -rf {} +
find . -name .DS_Store -not -path './.venv/*' -not -path '*/node_modules/*' -delete
rm -f frontend/app/favicon.ico.bak docs/workspace/search-detector-validation/results/_sweep.log
# Tier-2 dead files
rm -f global-CLAUDE.md AGENTS.md docs/plans/2026-05-03-crawl4ai-data-gathering.md
rm -rf algolia-search-audit-skill-improvement docs/research/crawl4ai docs/research/n8n TEMP
git rm --quiet CHECKPOINT.md
```
(Kept on purpose: completed workspace dirs under docs/workspace/* — small, hold real reasoning. Delete later if you want, after promoting to vault.)

## 2. Clean push of PIP (private repo: github.com/arijitchowdhury80/prism)
```bash
git add -A
git status   # EYEBALL: must show source/docs only — NO node_modules, NO .next, NO .env*, NO .claude/
# (first-time commit of frontend/ + docs is large but intended — "latest only")
git commit -m "chore: clean repo — remove residual junk, restore canonical docs, commit current state

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push origin main
```
If `git status` shows anything secret/bulky, STOP — the .gitignore should have caught it; investigate before pushing.

---

## 3. W-A — finish the generation plane (drop secrets, one command)
The executor is synced (HEAD a9db07a), browser plane proven, scaffold fail-loud-tested. Two things missing:
```bash
ssh chowmesadmin@72.61.72.147
# (a) fill the 3 MCP servers' launch command/args (replace FILL_IN_*):
nano /opt/prism-executor/.mcp.json     # algolia, builtwith, yahoo-finance  (chrome+apify already done)
# (b) keys:
cat > /opt/prism-executor/.mcp.env <<'EOF'
ALGOLIA_APP_ID=...
ALGOLIA_API_KEY=...
BUILTWITH_API_KEY=...      # the ROTATED one
APIFY_TOKEN=...
# SIMILARWEB_API_KEY=...   # rotated, if any skill needs it
# yahoo-finance needs no key
EOF
chmod 600 /opt/prism-executor/.mcp.env
# (c) ensure the Anthropic key has CREDIT (prior 402 lesson), then run:
cd /opt/prism-executor && ./run-audit.sh petsmart.com
```
Output lands in `/opt/prism-executor/audits/petsmart-com/`. This proves W-A end-to-end on the VPS.

---

## 4. W-D — unify chat (Telegram + SPA on one Hermes brain)
Full design + Read Receipt + 12-step checklist already in `G-wd-design.md`. Critical-path order:
1. **R1 — deploy the FastAPI backend (`prism_platform`) ON the VPS** (it only runs on the Mac today; no container). Add a Dockerfile/compose service, bind 127.0.0.1:8000, point at VPS Postgres/Redis. Verify `curl 127.0.0.1:8000/health` on the box. *This is the hard prerequisite — Hermes can't call tools it can't reach.*
2. **Enable Hermes API server**: `API_SERVER_ENABLED=true` + `API_SERVER_KEY` in `~/.hermes-prism/.env`; verify `/v1/capabilities` shows `responses_api` + `session_key_header`.
3. **Register the 25 FastAPI tools in Hermes** as HTTP tools → `127.0.0.1:8000/api/v1/*`.
4. **Move grounding into Hermes**: aRRIe persona → `instructions`; enable `prism-report-qa` plugin as the `transform_llm_output` gate (already verified for report-QA).
5. **SPA**: new `app/api/hermes/route.ts` proxy (server-side; SSE→AI-SDK-UI-stream shim — see G §2); repoint `prism-chat.tsx` transport; gate the currently-PUBLIC `/api/chat`.
6. **Identity map**: `rep ↔ {clerk_user_id, telegram_chat_id}` table + key builders — `X-Hermes-Session-Key = agent:main:prism:rep:<repId>:acct:<domain>`, `conversation = prism:<repId>:<domain>`. Telegram `/link` step (I1).
7. **E2E**: same question on Telegram then SPA → consistent grounded answers, phone↔laptop continuity. Runs entirely on the VPS (not your laptop).

Biggest runtime risk (per G): the tool-name contract — only provable by a real `/v1/responses` turn on the box.

---

## State snapshot (what's done vs blocked)
- ✅ Skills hardened + committed + pushed (arijit-skills a9db07a); history scrubbed.
- ✅ Hermes fat-audit (18.3 GB reclaimed); self-learning loop already ON+staged.
- ✅ W-A executor synced + browser-plane proven + scaffold ready (blocked on MCP keys + Anthropic credits).
- ✅ W-D fully designed (G-wd-design.md); build pending R1 + secrets.
- ⏳ PIP cleanup PREPARED (.gitignore fixed); deletes+commit+push blocked by permission gate → run section 1–2.
- 🚨 Rotate the 2 exposed keys (section 0) — highest priority.
