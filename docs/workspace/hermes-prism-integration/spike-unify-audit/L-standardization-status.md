# L — Report Standardization (status + plan)

Goal: every published audit report at the latest canonical schema + consistent format, then re-import to the Hermes store. Baseline = the latest contract `audit_data_schema.py` (even HD-Mexico failed it).

## Done — deterministic format migration
- New tool: `algolia-search-audit/scripts/migrate-audit-data.py` (no LLM, idempotent). Fixes mechanical drift: findings.severity enum, intelligence_signals.type enum, score.breakdown keys, abx day/channel/Source-notes-strip/video_script, icp + case_studies field-name aliases (`priority`/`question`/`algolia_product`/`stat` → canonical).
- Applied to all 10 with-data reports (each `.bak` + git-tracked).
- **Result: 4/10 PASS clean** (british-airways, labanquepostale, brooks-running, petsmart). The other 6 had violations slashed to genuine-content-gaps only.

## Remaining = DEPTH completion (needs PRISM execution + secrets)
Two buckets, both need the execution plane (MCP keys + LLM credits; the 7 also need browser/residential-IP):

**Bucket 1 — 6 with-data reports, genuine content gaps** (re-run the relevant synth/report modules to fill):
- homedepot-mexico: 1 exec missing `quote`.
- nike, savage-x-fenty: case_studies missing `why`/`product`.
- oriental-trading, llbean, dsw: icp discovery questions missing `evidence`/`exact_quote`.
- savage: a strategic_angle missing `algolia_proof`.

**Bucket 2 — 7 dataless companies, full re-audit** (no audit-data.json): dell, footlocker, jbl, michaelkors, thenorthface, torrid, autozone (autozone has nothing).

## Execution-plane dependency (the decision)
- Re-render (format→HTML) is deterministic: `render-audit.ts {slug}` — run anywhere, ~20-30s.
- Module re-runs / full audits need: MCP keys (BuiltWith, SimilarWeb, Tavily, Apify) + Anthropic/LLM credits + (Bucket 2) browser residential-IP.
- WHERE: **laptop** (Claude Code — proven, MCP configured, residential IP) vs **VPS executor** (`/opt/prism-executor` — needs `.mcp.env` created first + datacenter-IP browser problem).

## Then — re-import + republish
Standardized audit-data.json → render-audit.ts → {slug}/index.html → commit prism-hub + import to /root/.hermes-prism/reports/ + index.json (live, no restart). Chat then grounds on the full standardized set.

## Verification
All reports pass `audit_data_schema.py` + `template_contract.py`; render with zero blank sections; grounded chat returns the new data.

---

## ⏸️ CURRENT STATE + EXACT RESUME (checkpoint 2026-06-28)

**Decisions locked:** run depth-completion on the LAPTOP (this machine — MCP + residential IP configured); scope = ALL 17. Two waves: Wave 1 = 10 with-data reports (render 4 clean + synthesis-fill the 6 gaps); Wave 2 = 7 dataless full re-audits.

**What's DONE:**
- `migrate-audit-data.py` BUILT (scripts dir) + APPLIED to all 10 with-data reports. Working tree of `~/prism-hub` is DIRTY/UNCOMMITTED: 7 `*-audit-data.json` modified (brooks, dsw, homedepot, llbean, nike, oriental-trading, savage) + `.bak` backups present. british-airways/labanquepostale/petsmart unchanged (were already clean).
- Validator result after migration: **4 PASS** (british-airways, labanquepostale, brooks-running, petsmart). **6 still fail** on GENUINE content gaps only:
  - homedepot-mexico: exec[5] missing `quote` (it's in `key_signal` "Stated: …" — extractable).
  - nike, savage-x-fenty: case_studies missing `why`/`product` (company+stat+url present; fetch product/why from the algolia.com/customers URL already in the JSON).
  - oriental-trading, llbean, dsw: icp `priority_to_product[]` discovery questions missing `evidence`/`exact_quote` (derive from findings/quotes already in the JSON).
  - savage: a strategic_angle (`FableticsOS Platform Deal`) missing `algolia_proof`.

**⚠️ RENDER-INVOCATION BUG to fix on resume:** `deno run -A render-audit.ts <slug> site` from `~/prism-hub` wrote to ROOT `index.html` (clobbered the hub homepage — restored via `git checkout index.html`), NOT `<slug>/index.html`. Resolve the correct workdir/arg before batch-rendering (the script may expect a workspace where `<slug>/` is the output, or a different cwd). DO NOT batch-render until this is fixed.

**RESUME STEPS (Wave 1):**
1. Fix the render-invocation (find how it derives the output path; likely run from a per-company workspace or pass an out dir).
2. Complete the 6 gaps via grounded synthesis FROM EACH JSON's existing data (no re-audit; light WebFetch of the algolia case-study URLs already present for nike/savage product/why). Each must then pass `python3 audit_data_schema.py <slug>-audit-data.json`.
3. Render all 10 → `<slug>/index.html`. Re-run `generate-index.ts` for the hub.
4. Re-import the standardized 10 → `/root/.hermes-prism/reports/<slug>/audit-data.json` + index.json (live, no restart) on the VPS.
5. Commit `prism-hub` (add `.gitignore` for `*.bak`/`.DS_Store` first) + push.

**RESUME STEPS (Wave 2 — the 7 dataless full re-audits):** dell, footlocker, jbl, michaelkors, thenorthface, torrid, autozone. Run `algolia-search-audit` orchestrator per company on the laptop (MCP + browser). Big batch — sequence/manage. autozone has no index.html either (fully from scratch).

**Tools/paths:** migrate=`…/algolia-search-audit/scripts/migrate-audit-data.py`; validate=`audit_data_schema.py`+`template_contract.py`; render=`render-audit.ts <slug> site`; hub=`generate-index.ts`. Reports live in `~/prism-hub/<slug>-audit-data.json` (root) — some also have a stray `<slug>/<slug>-audit-data.json` (untracked, ignore/clean).
