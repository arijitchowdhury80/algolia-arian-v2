# Algolia Search Audit — Skill Engine Map

> Structured map of the 22 `algolia-*` Claude skills in `~/.claude/skills/`.
> Purpose: feed the Hermes/PRISM integration decision — understand the pipeline,
> what each module needs, what it emits, and which parts can run headless.
> Source: each skill's `SKILL.md` + the orchestrator `algolia-search-audit/SKILL.md`
> + shared scripts in `algolia-search-audit/scripts/`.

---

## 0. Shared conventions (apply to all 21 sub-skills)

- Every sub-skill's **mandatory first action** is to read `~/.claude/skills/algolia-search-audit/AGENT-CONTEXT.md` (canonical JSON field names, CSS classes, token names, naming rules).
- Every sub-skill uses the `$ALGOLIA_AUDIT_DIR` path convention. Workspace layout:
  ```
  $ALGOLIA_AUDIT_DIR/{CompanyName}/
    research/        ← all module .md + .json outputs
    deliverables/
      screenshots/
      {slug}-audit-data.json
      {slug}/index.html (+ ae-report, battle-card, leave-behind, PDF)
      abx-campaign/
    audit-progress.jsonl
  ```
- **Collector scripts are NOT inside the individual skill folders.** They live centrally in `~/.claude/skills/algolia-search-audit/scripts/` (e.g. `collect-company.py`, `collect-traffic.py`, `audit-browser.js`, `render-audit.ts`, `generate-audit-data.py`, `generate-pdf.sh`). Each sub-skill dir is essentially just `SKILL.md` (a few also ship `REFERENCE.md` / `test-cases.json`).
- The orchestrator is a **pure router** (orchestrator-workers pattern): it spawns one isolated Agent per module, passes file *paths* not content, and only reads `audit-progress.jsonl` + output file sizes for gate checks.

---

## 1. Per-skill detail

### Orchestrator

#### `algolia-search-audit`
- **Purpose:** Full-pipeline orchestrator. Spawns one agent per module in wave order; does no data work itself.
- **Category:** orchestrator
- **Inputs:** `{domain}` (+ optional `--company`, `--ticker`, `--no-browser`, `--phase`). Determines public-vs-private before Wave 1.
- **Outputs:** None directly — coordinates all module outputs; manages `audit-progress.jsonl` and the publish step.
- **Dependencies:** none (entry point).
- **External tools:** WebSearch (public/private ticker check); `publish-audit.sh` (git commit + push to `~/algolia-arian-v2`, Vercel auto-deploy); local `python3 -m http.server 8766` for review.
- **Interactivity:** Spawns agents headlessly, BUT the **publish step is human-gated** — stages locally, presents a review URL, waits for the user to type `publish` before `git push`.

---

### Wave 1 — Research / Intelligence (run in parallel)

#### `algolia-intel-company`  (1A — runs FIRST, others depend on it)
- **Purpose:** Company context — overview, vertical classification, exec team, key URLs, parent/portfolio detection.
- **Category:** research-intel
- **Inputs:** `{domain}` (+ `{CompanyName}`). No upstream files.
- **Outputs:** `01-company-context.md`, `01-company-context.json`
- **Dependencies:** none (true root; all other Wave-1 modules read its `.json`).
- **External tools:** `collect-company.py` → BuiltWith API + `scout_company.py`; **Scout** (PRISM platform) for /about, /leadership, /careers, /investors; `mcp__builtwith__keywords-api`; WebSearch; Tavily search + WebFetch (parent/portfolio).
- **Interactivity:** Headless. Scout + WebSearch/Tavily auto-run.

#### `algolia-intel-techstack`  (1B)
- **Purpose:** Detect current search vendor, ecommerce platform, analytics, CDN/WAF, removed tech → classifies displacement / expansion / greenfield.
- **Category:** research-intel
- **Inputs:** `{domain}`; reads `01-company-context.json`.
- **Outputs:** `02-tech-stack.md`, `02-tech-stack.json`
- **Dependencies:** 1A.
- **External tools:** `collect-techstack.py` + `parse-builtwith.js`; **all 7 BuiltWith MCP endpoints** (`mcp__builtwith__domain-lookup`, `relationships-api`, `recommendations-api`, `financial-api`, `social-api`, `trust-api`, `keywords-api`); SimilarWeb tech cross-check; **Chrome MCP** (`mcp__chrome__*`) for live network inspection of the active search API.
- **Interactivity:** Headless. WAF/bot blocks on the live-network step are recorded as data (`UNCONFIRMED_WAF_BLOCK`), not escalated to a human.

#### `algolia-intel-traffic`  (1C)
- **Purpose:** Traffic & engagement profile — visits, bounce, device split, channels, geo, keywords, referrals, demographics.
- **Category:** research-intel
- **Inputs:** `{domain}`. No upstream files.
- **Outputs:** `03-traffic-data.md`, `03-traffic-data.json`
- **Dependencies:** none.
- **External tools:** `collect-traffic.py` → **SimilarWeb REST API (key-based, ~14 endpoints)**; WebSearch fallback. SEPARATE path exists: `collect-similarweb-browser.js` (Playwright + stealth) for UI-only data.
- **Interactivity:** API path is headless (API key). **BUT** the browser-scraper variant needs a **one-time interactive login: SimilarWeb → Google → Algolia SSO (Okta) → MFA**, saved to a persistent profile; subsequent runs headless. Degrades gracefully on 403s (plan limits).

#### `algolia-intel-competitors`  (1D)
- **Purpose:** Who competes, what search tech each uses, any Algolia users (Golden Angle), matching case studies.
- **Category:** research-intel
- **Inputs:** `{domain}`; reads `01-company-context.json`, `02-tech-stack.json`.
- **Outputs:** `04-competitors.md`, `04-competitors.json`
- **Dependencies:** 1A, 1B.
- **External tools:** `collect-competitors.py` (SimilarWeb Competitors tab — often 0 due to anti-bot, expected); SimilarWeb MCP (`similar-sites-agg`, `keywords-competitors-agg`); BuiltWith `domain-lookup` per competitor; **WebSearch (primary path)**; WebFetch of `algolia.com/customers/{slug}`.
- **Interactivity:** Headless. WebSearch is primary because the SimilarWeb script reliably hits anti-bot.

#### `algolia-intel-financial-public`  (1E — public companies only)
- **Purpose:** 3-yr revenue trend, EBITDA margin, analyst consensus, 10-K digital-revenue, earnings-call quotes.
- **Category:** research-intel
- **Inputs:** `{domain} --ticker {TICKER}`; reads `01-company-context.json`.
- **Outputs:** `08-financial-profile.md`, `08-financial-profile.json`
- **Dependencies:** 1A.
- **External tools:** **Yahoo Finance MCP (all endpoints)**; WebFetch (SEC EDGAR 10-K, Motley Fool / Seeking Alpha / IR); `collect-financials.py --ticker`.
- **Interactivity:** Headless. **HARD GATE:** if Yahoo Finance MCP is down, STOP — no WebSearch substitute allowed.

#### `algolia-intel-financial-private`  (1F — private companies only)
- **Purpose:** Revenue estimate via 6-source waterfall, all figures `[ESTIMATE]`.
- **Category:** research-intel
- **Inputs:** `{domain} --private`; reads `01-company-context.json`; soft-consumes hiring job-volume.
- **Outputs:** `08-financial-profile.md`, `08-financial-profile.json` (same filenames as 1E — mutually exclusive).
- **Dependencies:** 1A (soft: 1H hiring).
- **External tools:** WebFetch + WebSearch only (ecdb.com, PitchBook/Crunchbase, LinkedIn, CEO interviews, trade press, Inc 5000 / Deloitte Fast 500); `collect-financials.py --private`. No Yahoo, no SEC.
- **Interactivity:** Headless, no credentials.

#### `algolia-intel-investor`  (1G)
- **Purpose:** Verbatim exec quotes from earnings calls, 10-K MD&A/risk, Yahoo news, trade-press media quotes.
- **Category:** research-intel
- **Inputs:** `{domain}` (+ `--ticker`/`--private`); reads `01-company-context.json`; optional `TAVILY_API_KEY`.
- **Outputs:** `11-investor-intelligence.md`, `11-investor-intelligence.json`
- **Dependencies:** 1A.
- **External tools:** Yahoo Finance MCP (`get_yahoo_finance_news`); WebSearch + WebFetch (transcripts, SEC EDGAR direct HTTP — no EDGAR MCP exists); `collect-investor.py`, `collect-exec-media.py` (Tavily).
- **Interactivity:** Headless. Tavily optional → WebSearch fallback. Hard rule: reject quotes dated before Jan 2025.

#### `algolia-intel-hiring`  (1H)
- **Purpose:** ICP-relevant open roles, tiered by buyer type (Economic / Technical / Champion), vacancy flags.
- **Category:** research-intel
- **Inputs:** `{domain}`; reads `01-company-context.json` (careers_url).
- **Outputs:** `09d-hiring-signals.md`, `09d-hiring-signals.json`
- **Dependencies:** 1A.
- **External tools:** WebFetch (careers page) + WebSearch (ZipRecruiter, Indeed, LinkedIn jobs) ONLY. **No Apify, no script.**
- **Interactivity:** Fully headless. Gracefully handles auth-walled careers portals (returns Layer-1 = 0, relies on WebSearch).

#### `algolia-intel-social`  (1I)
- **Purpose:** LinkedIn company posts + Twitter/X posts, each scored for Algolia relevance.
- **Category:** research-intel
- **Inputs:** `{domain} --company-name`; reads `01-company-context.json` (linkedin_url, twitter_handle); needs `APIFY_TOKEN`.
- **Outputs:** `09b-social-signals.md`, `09b-social-signals.json`
- **Dependencies:** 1A.
- **External tools:** **Apify MCP** — actors `harvestapi/linkedin-company-posts`, `apidojo/tweet-scraper`; `collect-social.py`; WebSearch fallback.
- **Interactivity:** Headless. **Needs `APIFY_TOKEN`** for primary path; degrades to WebSearch without it.

#### `algolia-intel-news`  (1J)
- **Purpose:** Google News (3 queries) + company RSS/newsroom over 60-day lookback — leadership/funding/tech/launch events.
- **Category:** research-intel
- **Inputs:** `{domain} --company-name`; reads `01-company-context.json`; needs `APIFY_TOKEN` for Apify path.
- **Outputs:** `09c-news-signals.md`, `09c-news-signals.json`
- **Dependencies:** 1A.
- **External tools:** **Apify MCP** — actor `data_xplorer/google-news-scraper-fast`; `collect-news.py`; WebSearch fallback.
- **Interactivity:** Fully headless. `APIFY_TOKEN` for primary path; WebSearch fallback otherwise.

#### `algolia-intel-partner`  (partner)
- **Purpose:** Map Algolia tech-partners in the prospect's stack (co-sell) + SI/consulting firms with C-suite relationships.
- **Category:** research-intel
- **Inputs:** company slug; reads `02-tech-stack.md` (required). No Python script (LLM-driven).
- **Outputs:** `partner-intel.md` (single file, **no `.json`**)
- **Dependencies:** 1B.
- **External tools:** **Crossbeam MCP** (`mcp__crossbeam__authenticate` → `complete_authentication`) for account overlap; WebSearch.
- **Interactivity:** **NOT fully headless if Crossbeam data is needed** — Crossbeam requires an interactive OAuth-style auth flow. Degrades to tech-stack + WebSearch (headless) when Crossbeam unavailable.

#### `algolia-intel-industry`  (1L)
- **Purpose:** Vertical benchmarks (Baymard/Forrester/NRF), search-conversion stats, 2025-26 trends, analyst quotes, Algolia vertical angle.
- **Category:** research-intel
- **Inputs:** company slug + `<domain>` (+ optional `--vertical`); soft-reads `01-company-context.json`, `04-competitors.md`.
- **Outputs:** `industry-intel.md`, `industry-intel.json`
- **Dependencies:** soft on 1A, 1D (runs even if absent).
- **External tools:** `collect-industry.py` → **Tavily advanced search** (needs `TAVILY_API_KEY`); WebSearch + WebFetch fallback (Baymard JS pages often only yield `[ESTIMATE]`).
- **Interactivity:** Headless. Degrades to WebSearch when Tavily key unavailable.

---

### Wave 2 — Query Generation (after Wave 1)

#### `algolia-intel-queries`
- **Purpose:** Generate the 14–18 query test set (broad, specific, NLP, typo, synonym, non-product, brand, no-results) for the browser audit.
- **Category:** browser-testing (prep)
- **Inputs:** company slug; reads `01-company-context.md` (required), `03-traffic-data.md` (optional).
- **Outputs:** `05-test-queries.md` (**`.md` only, no `.json`**)
- **Dependencies:** 1A (required), 1C (preferred).
- **External tools:** **None** — pure analysis/writing. No MCP, no script, no network.
- **Interactivity:** Fully headless, idempotent.

---

### Layer 2 — Browser Audit (sequential, after Waves 1+2)

#### `algolia-audit-browser`
- **Purpose:** Live browser search testing (20 steps: SAYT, NLP, typo, zero-results, federation, personalization, recommendations) with screenshot evidence.
- **Category:** browser-testing
- **Inputs:** company slug; requires `01-company-context.md`, `02-tech-stack.md`, `05-test-queries.md` (stops if missing); reads `04-competitors.md`.
- **Outputs:** `deliverables/screenshots/*.png` (≥10), `09-browser-findings.md`, `research/CHECKPOINT.md`; patches `02-tech-stack.md` + `04-competitors.md` with confirmed vendor status.
- **Dependencies:** Wave 1 (1A, 1B, 1D) + Wave 2 (queries).
- **External tools:** **Playwright CLI + puppeteer-extra-plugin-stealth** via `audit-browser.js`; **Chrome MCP** (`mcp__chrome__*` navigate/type/screenshot/network) for vendor API detection; Puppeteer MCP fallback.
- **Interactivity:** **NEEDS A REAL BROWSER; NOT reliably headless-clean.** Built to defeat WAF/bot (Akamai, Cloudflare, Imperva, PerimeterX). Escalation ladder: headless stealth → `--headed` visible browser → **human-in-the-loop CAPTCHA solving** → connect to user-launched Chrome on `--remote-debugging-port=9222`. Cooperative sites run unattended; aggressive-WAF sites require interactive intervention. Gate: ≥10 non-empty (>50KB) screenshots.

---

### Layer 3 — Synthesis & Report (sequential, each feeds the next)

#### `algolia-synth-business-case`  (Step 3A)
- **Purpose:** Search ROI business case in 6 revenue components, conservative + moderate scenarios, AE fill-in prompts.
- **Category:** synthesis
- **Inputs:** company slug; requires `08-financial-profile.md` (STOPS if missing), `10-scoring-matrix.md`, `03-traffic-data.md`; optional `04-competitors.md`, `{slug}-audit-data.json`.
- **Outputs:** `deliverables/{slug}-business-case.md`
- **Dependencies:** 1E/1F, 1C, scoring (from report); ideally browser findings.
- **External tools:** Bash + WebFetch (verify Algolia case-study / Baymard URLs).
- **Interactivity:** Headless.

#### `algolia-synth-sales-plays`  (Step 3B)
- **Purpose:** Grounded AE/BDR playbook — BLUF, top-5 talking points, SPIN discovery, MEDDPICC gap map, objection handling, power map, partner angles.
- **Category:** synthesis
- **Inputs:** company slug; reads `11-investor-intelligence.md`, `10-scoring-matrix.md`, `04-competitors.md`, `09d-hiring-signals.md`, `08-financial-profile.md`; optional `{slug}-business-case.md`, `partner-intel.md`.
- **Outputs:** `deliverables/{slug}-playbook.md`
- **Dependencies:** 1G, 1D, 1H, 1E/1F, scoring; optional business-case.
- **External tools:** Bash only. No MCP, no network.
- **Interactivity:** Fully headless.

#### `algolia-audit-report`  (Step 3C)
- **Purpose:** Score the 10 search areas and render the full deliverable package.
- **Category:** report-generation
- **Inputs:** company slug; requires all 12 research scratchpads (≥30 lines each) + ≥8–10 screenshots + `10-scoring-matrix.md` + `09-browser-findings.md` (≥50 lines); optional `partner-intel.json`.
- **Outputs (9):** `{slug}-audit-data.json`, `{slug}/index.html` (SPA), `ae-report.html`, `battle-card.html`, `leave-behind.html`, `{slug}-leave-behind.pdf`, `{slug}-playbook.md`, `{slug}-strategic-signal-brief.md`, `abx-campaign/` (via the ABX skill). Also `10-scoring-matrix.md`, `{slug}-search-audit.md`.
- **Dependencies:** all of Wave 1 + Layer 2. **Calls `algolia-campaign-abx`** internally (Phase 5f, mandatory).
- **External tools:** WebFetch (`algolia.com/customers/`); scripts `validate-workspace.sh`, `generate-audit-data.py`, `validate-json-schema.py`, `check-style-tokens.py`, **`render-audit.ts` (Deno, `--allow-net`)**, `test-spa-runtime.js`, `generate-pdf.sh`.
- **Interactivity:** Headless/batch. Requires local toolchain: **Deno** (renderer w/ network), **Python3**, PDF generator. No publish step in this skill itself.

#### `algolia-campaign-abx`  (Step 3D — mandatory, after report)
- **Purpose:** Multi-touch ABX outreach — 5 emails + 3 LinkedIn messages + Loom script + collateral schedule; back-fills `abx_sequence` in audit-data.json.
- **Category:** campaign
- **Inputs:** company slug; requires `{slug}-playbook.md`, `09-browser-findings.md`; reads `11-investor-intelligence.md`, `04-competitors.md`, `08-financial-profile.md`, screenshots.
- **Outputs:** `deliverables/abx-campaign/` (10 files: `email-1-hook.md` … `email-5-breakup.md`, `linkedin-connect.md`, `linkedin-followup-1.md`, `linkedin-followup-2.md`, `loom-script.md`, `collateral-schedule.md`); updates `audit-data.json → abx_sequence.touches[]`.
- **Dependencies:** playbook (3B / report 5d) + browser findings. Invoked BY `algolia-audit-report`; enforced by factcheck Dim 21.
- **External tools:** Python/Bash (extract+patch JSON); **calls `algolia-brand-check` skill** for brand validation (graceful skip if absent); references algolia-email/brief/social; WebFetch only for verified case-study URLs.
- **Interactivity:** Headless. Downstream brand-check call optional/graceful.

---

### Layer 4 — Quality Gates

#### `algolia-audit-factcheck`  (mandatory, blocks publish)
- **Purpose:** Verify all deliverables across 20+ dimensions → PROCEED / WARN / BLOCKED verdict.
- **Category:** quality-gate
- **Inputs:** company name (+ `--tier quick|standard|full`, `--dim`); reads `audit-data.json`, `10-scoring-matrix.md`, `09-browser-findings.md`, all 11 scratchpads, screenshots, deck/report/leave-behind.
- **Outputs:** `{slug}-factcheck-report.md`, `{slug}-correction-manifest.md`, `research/FACTCHECK_GATE.md` (machine-readable SCORE/CONFIDENCE/ACTION), `{slug}-skill-feedback.md`.
- **Dependencies:** full audit (research + browser + report + ABX).
- **External tools:** Re-calls **SimilarWeb MCP, BuiltWith MCP**, competitor APIs, WebFetch (HTTP-200 + content checks); Full tier may re-run browser tests. Quick = 0 external calls / Standard ~15–20 / Full ~30–40.
- **Interactivity:** Headless (Full tier inherits browser/WAF concerns if it re-runs browser). It is itself the gate; the orchestrator parses its ACTION field and human-gates publish on WARN.

#### `algolia-audit-eval`  (standalone quality scorer)
- **Purpose:** Score any `algolia-audit-*` module output against 5 dimensions (completeness, source density, instruction adherence, data accuracy, no fabrication); ≥7.0 pass.
- **Category:** quality-gate
- **Inputs:** skill name + company slug; reads the target module's outputs.
- **Outputs:** `{Company}/eval/{skill-name}-eval-report.md`
- **Dependencies:** the target module must have produced output. Not in the main pipeline path — a dev/QA tool.
- **External tools:** Bash only (grep/wc/find/ls) — self-contained deterministic checker. No MCP/network/browser.
- **Interactivity:** Fully headless.

---

## 2. Dependency DAG (wave / execution order)

```
ENTRY: algolia-search-audit (orchestrator)
   │  └─ determines public vs private (WebSearch ticker check)
   ▼
WAVE 1  ── 11 modules in PARALLEL (10 if you count financial as one route) ──
   │
   ├─ algolia-intel-company (1A)  ◄── ROOT. Must finish first in practice;
   │        │                          all others read 01-company-context.json
   │        ├─► algolia-intel-techstack (1B)        [reads 1A]
   │        │        └─► algolia-intel-competitors (1D)  [reads 1A + 1B]
   │        │        └─► algolia-intel-partner          [reads 1B]
   │        ├─► algolia-intel-financial-public (1E)  OR  -private (1F)  [reads 1A]
   │        ├─► algolia-intel-investor (1G)          [reads 1A]
   │        ├─► algolia-intel-hiring (1H)            [reads 1A]   ─┐ (1F soft-reads)
   │        ├─► algolia-intel-social (1I)            [reads 1A]
   │        └─► algolia-intel-news (1J)              [reads 1A]
   ├─ algolia-intel-traffic (1C)        [independent of 1A]
   └─ algolia-intel-industry (1L)       [soft-reads 1A + 1D]
   │
   ▼  GATE: ≥11 research/*.md files, each >500 bytes
WAVE 2  ── algolia-intel-queries  [reads 1A + 1C] → 05-test-queries.md
   │
   ▼  GATE: 05-test-queries.md exists >500 bytes
LAYER 2 ── algolia-audit-browser  [reads 1A,1B,1D + queries] → ≥10 screenshots + 09-browser-findings.md
   │
   ▼  GATE: ≥10 screenshots
LAYER 3 (sequential, each feeds next):
   3A algolia-synth-business-case   [reads 1E/1F, 1C, scoring, browser] → {slug}-business-case.md
   3B algolia-synth-sales-plays     [reads 1G,1D,1H,1E/1F, scoring, +business-case] → {slug}-playbook.md
   3C algolia-audit-report          [reads ALL research + screenshots]   → audit-data.json + SPA + extras
   │      └─ calls 3D internally
   3D algolia-campaign-abx          [reads playbook + browser findings]  → abx-campaign/ (10 files)
   │
   ▼  GATE: audit-data.json + index.html exist; abx-campaign/ non-empty
LAYER 4 ── algolia-audit-factcheck → FACTCHECK_GATE.md (PROCEED / WARN / BLOCKED)
   │
   ▼  HUMAN GATE: stage locally (http.server 8766) → user types "publish"
PUBLISH ── publish-audit.sh → git push ~/algolia-arian-v2 → Vercel auto-deploy

OFF-PIPELINE (dev/QA, not in the run path):
   algolia-audit-eval  — score any module's output, 5 dimensions, ≥7.0 pass
```

Note: within Wave 1 the orchestrator spawns all agents simultaneously, but 1A is the
true gating root because nearly every other module reads `01-company-context.json`.
1B→{1D, partner} is the only intra-wave hard chain; 1C and 1L are effectively
independent of 1A.

---

## 3. Category grouping (presentation table)

| Category | Skills | Count |
|---|---|---|
| **Orchestrator** | `algolia-search-audit` | 1 |
| **Research-intel** | `algolia-intel-company`, `-techstack`, `-traffic`, `-competitors`, `-financial-public`, `-financial-private`, `-investor`, `-hiring`, `-social`, `-news`, `-partner`, `-industry` | 12 |
| **Browser-testing** | `algolia-intel-queries` (prep), `algolia-audit-browser` | 2 |
| **Report-generation** | `algolia-audit-report` | 1 |
| **Synthesis** | `algolia-synth-business-case`, `algolia-synth-sales-plays` | 2 |
| **Campaign** | `algolia-campaign-abx` | 1 |
| **Quality-gate** | `algolia-audit-factcheck`, `algolia-audit-eval` | 2 |
| **Total** | | **21 sub-skills + 1 orchestrator = 22** |

---

## 4. Final deliverable files (end-state of a full run)

Research scratchpads (`research/`):
`01-company-context.{md,json}`, `02-tech-stack.{md,json}`, `03-traffic-data.{md,json}`,
`04-competitors.{md,json}`, `05-test-queries.md`, `06`/`industry-intel.{md,json}`,
`07`/`partner-intel.md`, `08-financial-profile.{md,json}`,
`09b-social-signals.{md,json}`, `09c-news-signals.{md,json}`, `09d-hiring-signals.{md,json}`,
`09-browser-findings.md`, `10-scoring-matrix.md`, `11-investor-intelligence.{md,json}`,
`FACTCHECK_GATE.md`.

Deliverables (`deliverables/`):
`screenshots/*.png` (≥10), `{slug}-audit-data.json`, `{slug}/index.html` (SPA),
`{slug}/ae-report.html`, `{slug}/battle-card.html`, `{slug}/leave-behind.html`,
`{slug}-leave-behind.pdf`, `{slug}-business-case.md`, `{slug}-playbook.md`,
`{slug}-strategic-signal-brief.md`, `{slug}-factcheck-report.md`,
`{slug}-correction-manifest.md`, `{slug}-skill-feedback.md`,
`abx-campaign/` (10 files), `{slug}-search-audit.md`.

Published artifact: SPA pushed to `~/algolia-arian-v2` → Vercel.

---

## 5. Headless-readiness assessment (per external tool)

Legend: **GREEN** = works headless/automated, no human, no interactive auth.
**YELLOW** = headless only if a token/key/profile is pre-provisioned; else degrades.
**RED** = needs an interactive session (login, OAuth, CAPTCHA, or human approval).

| External tool | Used by | Headless? | Notes / what blocks automation |
|---|---|---|---|
| **WebSearch / WebFetch** | almost every research skill, synth, factcheck | **GREEN** | Built-in, no auth. The universal fallback path — most skills degrade to this. |
| **Scout (PRISM, localhost:8421)** | `intel-company` | **GREEN** | Local service; must be running. No interactive auth. |
| **BuiltWith MCP** (7 endpoints) | `intel-techstack`, `-competitors`, factcheck | **GREEN** (key-based) | API key in MCP config; no human. (Memory note: BuiltWith budget was a concern — confirm the key is live.) |
| **Yahoo Finance MCP** | `intel-financial-public`, `-investor` | **GREEN** | No auth beyond MCP config. Public skill has a HARD STOP if MCP is down — automation must treat MCP outage as a fatal gate, not retryable. |
| **SimilarWeb REST API** (`collect-traffic.py`) | `intel-traffic`, factcheck | **YELLOW** | Works headless with `SIMILARWEB_API_KEY`. A key is hardcoded as fallback — verify it is valid/funded; plan-tier 403s silently drop fields (e.g. demographics). |
| **SimilarWeb browser scraper** (`collect-similarweb-browser.js`) | `intel-traffic` (UI-only data path) | **RED → then GREEN** | **One-time interactive login: SimilarWeb → Google → Algolia SSO (Okta) → MFA.** After the persistent profile is saved, subsequent runs are headless. First-time setup (or expired session) cannot be automated. **Top risk for a fresh/headless environment.** |
| **Tavily API** | `intel-industry`, `-investor` | **YELLOW** | Needs `TAVILY_API_KEY`; degrades to WebSearch if unset. |
| **Apify MCP** | `intel-social`, `-news` | **YELLOW** | Needs `APIFY_TOKEN`; degrades to WebSearch if unset. Social/news quality drops materially without it. |
| **Crossbeam MCP** | `intel-partner` | **RED** | **Interactive OAuth-style flow** (`authenticate` → `complete_authentication`). Cannot be done unattended. Skill degrades to tech-stack + WebSearch, so partner intel runs headless but with reduced fidelity. |
| **Chrome MCP** (`mcp__chrome__*`) | `intel-techstack` (network), `audit-browser` | **YELLOW** | Needs a Chrome instance reachable by MCP. Techstack tolerates WAF blocks as data. |
| **Playwright + stealth** (`audit-browser.js`) | `audit-browser` | **RED (worst case)** | Cooperative sites run unattended, but the skill's escalation ladder ends in **human CAPTCHA solving** and connecting to a **user-launched Chrome on port 9222**. Aggressive-WAF sites (Akamai/Imperva/PerimeterX) require a person. **Top risk for the Phase-2 step.** |
| **Deno renderer** (`render-audit.ts --allow-net`) | `audit-report` | **GREEN** (if Deno installed) | Local toolchain dependency: Deno + network allowance. No human. |
| **PDF generator** (`generate-pdf.sh`) | `audit-report` | **GREEN** (if toolchain installed) | Local dependency. |
| **git push + Vercel** (`publish-audit.sh`) | orchestrator publish step | **RED** | **Human approval gate** — orchestrator stages locally and waits for the user to type `publish` before pushing. By design, not automatable without a policy decision. |

### Top headless-readiness risks (ranked)

1. **`algolia-audit-browser` (Playwright/stealth on WAF sites)** — the only step that can hard-require a human (CAPTCHA / manual Chrome launch). Any "PRISM/Hermes runs the audit unattended" plan must solve or skip this for aggressive-WAF prospects. Note `02-tech-stack` already does lighter network inspection that tolerates WAF blocks as data — but the full browser audit needs real screenshots.
2. **SimilarWeb browser-scraper login (Google→Okta→MFA)** — first-time/expired session needs interactive SSO+MFA. The API-key path avoids this; ensure the run uses the API path (and the key is funded) rather than the UI scraper.
3. **The publish step (git push / Vercel)** — human "publish" gate by design. Headless automation needs an explicit auto-publish policy or it stops here.
4. **Crossbeam OAuth** (`intel-partner`) — interactive auth; acceptable because it degrades gracefully, but partner intel loses account-overlap data when run headless.
5. **Token/key provisioning (YELLOW set): `APIFY_TOKEN`, `TAVILY_API_KEY`, `SIMILARWEB_API_KEY`, BuiltWith/Yahoo MCP keys** — none need a human at runtime, but all must be pre-wired or the modules silently degrade to WebSearch (lower fidelity, not a hard failure). Yahoo (public-financial) is the exception: its outage is a hard STOP, not a degrade.
