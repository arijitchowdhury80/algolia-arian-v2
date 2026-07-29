# D — Algolia Audit Skills: Determinism & Accuracy Survey

> Scope: the 22 `algolia-*` skills (1 orchestrator + 21 sub-skills) in
> `~/.claude/skills/algolia-audit-skills/` (symlinked into the `arijit-skills` repo).
> Goal: scope a follow-on deep-dive that makes each skill MORE deterministic
> (fewer LLM calls, more code/API/MCP) while making the deliverable DEEPER and MORE accurate.
> Method: read the spine doc (`01-skill-engine-map.md`), every `SKILL.md`, and — for ground truth —
> the actual collector/compute scripts in `algolia-search-audit/scripts/`. SKILL.md text often
> describes intent; the scripts reveal what is *actually* wired vs. done by the LLM by hand.
> This is a scoping survey. Nothing is fixed here.

---

## 0. The one finding that reframes everything

The author already split the pipeline by determinism — the orchestrator's model table
assigns **Haiku** to "pure Python script" modules (techstack, traffic, hiring, news, social)
and **Opus** to "deep reading / creative generation" modules. That self-assessment is mostly
right at the *data-collection* boundary but **wrong in three expensive places**, because
deterministic scripts that exist were never wired into the live skills:

1. **`calculate-roi.py` exists and is deterministic — but the live `algolia-synth-business-case`
   skill does the 6-component ROI arithmetic BY HAND in the LLM.** The script is referenced only
   by the dead `algolia-audit-research` monolith. The LLM is literally doing
   `visits × rate × AOV × 12` multiplications in prose. (Verified: `business-case/SKILL.md`
   spells the formulas as text; `grep calculate-roi */SKILL.md` → only `algolia-audit-research`.)
2. **`collect-hiring.py`'s `classify()` (tier regex + ICP keyword scorer) is dead code.** v3.0 of
   the script removed scraping and now just prints "classification reference only"; the live
   `algolia-intel-hiring` skill re-implements role-tiering by LLM judgment via WebFetch/WebSearch.
   The deterministic classifier is sitting unused.
3. **`calculate-score.py` (deterministic weighted-average) is also referenced only by the dead
   monolith** — but here the live `algolia-audit-report` is partly saved because
   `generate-audit-data.py` independently *recalculates* `score.overall` from the matrix. So the
   *math* is deterministic at report time; the per-area 0–10 *judgment* is the LLM (correctly).

So the headline determinism win is not "write new scripts" — it's **wire up scripts that already
exist** and **stop the LLM from doing arithmetic and mechanical parsing it was never meant to do**.

A second structural fact: `generate-audit-data.py` is a 75KB **post-LLM JSON corrector** that
re-extracts ~20 structured fields from the `.md` scratchpads and overwrites whatever the LLM put in
the JSON (tech list, channels, device split, demographics, score breakdown, competitors, geo,
keywords, urgency scores). This is the single best pattern in the suite: *let the LLM write prose,
then deterministically extract the structured fields from the prose it wrote.* The deep-dive should
extend this pattern, not fight it.

---

## 1. Master table — all 22 skills

`%det` = rough share of the skill's *work* that is (or trivially could be) deterministic code/API/MCP today.
`risk` = fabrication / accuracy risk of the deliverable (H/M/L). `effort` = to harden (S/M/L).

| # | Skill | Deliverable | %det today | Top reducible step (LLM→code) | Irreducible-LLM core | risk | effort |
|---|-------|-------------|:---:|---|---|:---:|:---:|
| 0 | **algolia-search-audit** (orch) | Routes all modules, gates, publish | 90% | public/private check = WebSearch → ticker-lookup API | none (it's a router) | L | S |
| 1A | **intel-company** | 01-company-context | 70% | exec-team / vertical via WebSearch → Scout + classifier | vertical *judgment*, parent/portfolio reasoning | M | S |
| 1B | **intel-techstack** | 02-tech-stack | 85% | Layer-3 live search-vendor check → reuse `detect-search` skill | displacement/expansion/greenfield *call* | L | M |
| 1C | **intel-traffic** | 03-traffic-data | 95% | (already `collect-traffic.py` → SimilarWeb API) | one-line traffic narrative | L | S |
| 1D | **intel-competitors** | 04-competitors | 55% | per-competitor vendor detect → `detect-search`; algolia-customer check → fetch+match | "who really competes" set selection | M | M |
| 1E | **intel-financial-public** | 08-financial-profile | 80% | (yfinance script) BUT digital-rev split is LLM-read of 10-K | reading 10-K MD&A prose, ROI framing | M | M |
| 1F | **intel-financial-private** | 08-financial-profile | 25% | headcount→revenue & Inc5000 lookups → scripted waterfall | reconciling 6 conflicting estimates | **H** | L |
| 1G | **intel-investor** | 11-investor-intelligence | 35% | transcript/10-K fetch → scripted; quote *extraction* stays LLM | choosing the quote that matters, date filter | **H** | M |
| 1H | **intel-hiring** | 09d-hiring-signals | 40% | role collection + **tier classification** → `collect-hiring.classify()` (dead) | "is this role a buying signal" nuance | M | M |
| 1I | **intel-social** | 09b-social-signals | 70% | (Apify scripts) relevance *scoring* per post is LLM | which post is a real signal | M | S |
| 1J | **intel-news** | 09c-news-signals | 70% | (Apify scripts) event classification is LLM | event significance call | M | S |
| 1K | **intel-partner** | partner-intel (no JSON) | 30% | tech-partner overlap from `02-tech-stack` → scripted join | SI-relationship narrative, co-sell angle | **H** | M |
| 1L | **intel-industry** | industry-intel | 45% | benchmark stat collection → Tavily script (exists); fallback unfiltered | vertical narrative, analyst-quote curation | **H** | M |
| 2 | **intel-queries** | 05-test-queries | 5% | (none — pure design) | query-set design for the vertical | L | — |
| L2 | **audit-browser** | screenshots + 09-browser-findings | 50% | navigation/screenshot = Playwright (scripted) | judging search UX quality from results | M | L |
| 3A | **synth-business-case** | {slug}-business-case | 30% | **6-component ROI math → `calculate-roi.py` (exists, unwired)** | narrative framing, AE fill-in prompts | **H** | S |
| 3B | **synth-sales-plays** | {slug}-playbook | 5% | (none — grounded writing) | talking points, MEDDPICC, objections | M | — |
| 3C | **audit-report** | audit-data.json + SPA + 5 deliverables | 75% | score *math* already det (`generate-audit-data.py`); SPA det (`render-audit.ts`) | per-area 0–10 scoring, finding narrative | M | M |
| 3D | **campaign-abx** | abx-campaign/ (10 files) | 25% | JSON back-patch of `abx_sequence` → scripted extractor | email/LinkedIn/Loom copywriting | M | M |
| L4a | **audit-factcheck** | FACTCHECK_GATE verdict | 55% | HTTP-200 / cross-file stat consistency → scripted; URL liveness | quote-vs-transcript truth judgment | M | M |
| L4b | **audit-eval** | eval report (5 dims) | 80% | (already bash grep/wc/ls) | "is this fabricated" judgment | L | S |
| — | **audit-research** (legacy) | (dead monolith) | — | DELETE / archive — superseded by per-module skills | — | — | S |

(22 counted = orchestrator + 21 sub-skills; `audit-research` is the deprecated monolith still
shipping in the dir and still holding the only references to `calculate-roi.py` / `calculate-score.py`.)

---

## 2. Ranked determinism targets — highest ROI first

Ranked by (LLM work that is genuinely mechanical) × (frequency it runs) × (accuracy upside).

1. **business-case ROI → wire `calculate-roi.py`** *(effort S, risk H→L).*
   The LLM is doing multi-factor arithmetic in prose. Deterministic script already exists; the live
   skill just doesn't call it. **Biggest single win:** removes arithmetic-hallucination risk AND
   removes LLM tokens. Fix = call `calculate-roi.py`, have the LLM only write the narrative around
   the script's numbers (mirror the report's `generate-audit-data.py` pattern).

2. **techstack Layer-3 + competitor vendor detection → reuse the `detect-search` skill**
   *(effort M, risk H→L for techstack, M→L for competitors).*
   Both currently lean on the LLM interpreting BuiltWith + live network. `detect-search` is a
   purpose-built Playwright packet-inspection detector (17 vendors, ~230 sites, zero-FP per project
   memory). It returns vendor + appID + index deterministically. Make it the canonical search-vendor
   oracle for 1B and per-competitor in 1D, instead of LLM-from-BuiltWith.

3. **hiring tier classification → wire `collect-hiring.classify()`** *(effort M, risk M→L).*
   The regex tier-classifier + ICP keyword scorer is written and tested but dead. The LLM still
   collects roles (irreducible — careers pages vary), but tiering each role is mechanical. Feed
   collected `{title, desc}` through `classify()`; LLM only handles edge cases.

4. **campaign-abx JSON back-patch → scripted extractor (`generate-abx-json.py`, to build)**
   *(effort M, risk M→L).* The LLM writes the email/LinkedIn/Loom copy (irreducible) but also
   hand-assembles `abx_sequence.touches[]` JSON — exactly the failure class `generate-audit-data.py`
   was built to kill. Build the analogous post-LLM patcher for the campaign JSON.

5. **industry benchmark collection → always run `collect-industry.py` (Tavily) + fix fallback filter**
   *(effort M, risk H→L).* Stat collection is API work; only the narrative is LLM. Plus the
   fallback-path staleness bug (see §4).

6. **financial-private waterfall → scripted source lookups** *(effort L, risk H→M).*
   headcount→revenue heuristics, Inc 5000 / Deloitte Fast 500 membership, ecdb lookups are
   table/lookup operations. Script the 6 sources into structured candidates; LLM only reconciles.

7. **orchestrator public/private check → ticker-lookup API** *(effort S, risk L).*
   Replace the free-text WebSearch "is it public" with a deterministic ticker/exchange lookup
   (yfinance symbol search or an exchange-listing API). Removes a routing-misclassification risk
   at the very top of the pipeline.

8. **factcheck mechanical dimensions → scripted** *(effort M, risk M).*
   URL liveness (HTTP-200), cross-file stat equality, label-presence counts, placeholder detection
   are all deterministic. Keep quote-vs-transcript and "does this claim match evidence" as LLM.
   (`audit-eval` already shows the bash pattern to copy.)

---

## 3. Ranked accuracy / fabrication risks — worst first

1. **synth-business-case — hand-computed ROI.** LLM arithmetic over 6 components × 2 scenarios is a
   prime fabrication surface (wrong multiplication, dropped factor, invented AOV). *Fix:* deterministic
   `calculate-roi.py`; LLM never emits a number it didn't get from the script. **(also #1 determinism target)**

2. **intel-financial-private — 6-source estimate reconciliation.** Every figure is `[ESTIMATE]` and the
   LLM picks/blends among conflicting unstructured sources with no scripted floor. High risk of a
   confident wrong revenue that then propagates into the ROI model. *Fix:* scripted candidate
   collection + an explicit reconciliation rubric (range, not point); never collapse to a single
   number without showing the spread.

3. **intel-investor — quote authenticity + recency.** Skill rule rejects quotes before Jan 2025, but
   enforcement is LLM-side; mis-dated or paraphrased "verbatim" quotes are the classic hallucination.
   *Fix:* fetch transcript/10-K deterministically, require an exact substring match of the quote
   against fetched text (scripted check), reject on no-match. (This is the same grounding gap that
   `[[feedback-injection-insufficient-need-hard-gate]]` proved needs a post-gen verifier.)

4. **intel-industry — staleness leak on the WebSearch fallback path** (see §4 bug #2). Benchmarks can
   silently be >24 months old when Tavily is unavailable, despite the skill advertising a 24-month rule.

5. **intel-partner — hardcoded SI shortlist masquerading as dynamic discovery** (see §4 bug #1).
   Produces a co-sell narrative that can name the wrong/absent partner.

6. **audit-report per-area scoring drift.** The 0–10 area scores are LLM judgment with no rubric anchor
   beyond the matrix; two runs can score the same site differently. *Fix:* tighten the scoring rubric
   (anchored descriptors per score band) so the LLM judgment is reproducible; the weighted math is
   already deterministic.

7. **Universal "WebSearch fallback" degradation.** Nearly every research skill silently degrades to
   WebSearch when its key/MCP is absent (Apify, Tavily, SimilarWeb, BuiltWith). The deliverable looks
   identical but the sourcing is weaker, and the `[FACT]`/`[ESTIMATE]` discipline depends on the LLM
   remembering to downgrade labels. *Fix:* make `collection_method` a first-class field that the
   renderer surfaces, and have factcheck hard-check that WebSearch-sourced stats carry the amber label.

---

## 4. Real BUGS found (not just "too much LLM")

**BUG-1 — partner-1K hardcodes the SI list it explicitly says to discover dynamically.**
`algolia-intel-partner/SKILL.md` line 65 argues "Why dynamic matters: the relevant firm is whichever
Crossbeam shows… that changes per prospect." But lines 99–100 bake the firm names directly into the
fallback WebSearch queries:
`"{company}" EPAM OR "Publicis Sapient" …` and `"{company}" Deloitte OR Accenture OR IBM …`.
So any SI partner outside that ~5-name shortlist is structurally invisible on the (headless) path
where Crossbeam isn't authenticated — which is the common case (Crossbeam is RED/interactive). The
stated principle and the implementation contradict each other.
*Fix:* derive candidate firms from tech-stack overlap + a maintained partner registry, then search per
candidate; don't hardcode names into the query string.

**BUG-2 — industry-1L 24-month staleness rule leaks on the WebSearch fallback.**
Line 70: "Staleness rule (enforced by script): age_months > 24 excluded at collection time." That
enforcement lives in `collect-industry.py` (the Tavily path). The WebSearch fallback (Step 2b, lines
89–117) applies **no age filter** — queries hardcode "2025" but WebSearch returns arbitrary-age pages
and nothing drops stale results. Whenever `TAVILY_API_KEY` is unset (a YELLOW dependency, i.e. routine),
the advertised freshness guarantee silently does not hold.
*Fix:* apply the same `age_months > 24` exclusion to the fallback path, or label every fallback stat
`[ESTIMATE]` + surface `collection_method: websearch_fallback` so downstream knows freshness is unverified.

**BUG-3 — dead deterministic code presented as live.**
`calculate-roi.py` and `calculate-score.py` are only referenced by the deprecated `algolia-audit-research`
monolith; the live `synth-business-case` and `audit-report` skills don't call them. `collect-hiring.py`'s
`classify()` is referenced by no skill at all. Anyone reading the scripts assumes ROI/score/tiering are
deterministic; they are LLM-by-hand in the live path. *Fix:* wire them in (see §2) or delete to avoid the
false impression.

**BUG-4 — hardcoded API keys committed in scripts.**
`collect-techstack.py` has `BW_KEY = os.environ.get('BUILTWITH_API_KEY', '8fd992ef-…')` and
`SW_KEY = …'483b77d48d…'` as literal fallbacks (same pattern in `collect-traffic.py`). These are live
credentials in a git repo. *Fix:* remove the literal fallbacks; fail loud if the env var is missing.
(Not a determinism issue but a security bug found during the sweep — flagging per cardinal rules.)

**BUG-5 — financial filename collision is correct-by-convention but fragile.**
1E and 1F both write `08-financial-profile.{md,json}` and are "mutually exclusive" by the orchestrator's
public/private routing. If the routing misclassifies (BUG-adjacent to determinism target #7) or both run
on a re-run, one silently overwrites the other with no guard. *Fix:* write a `company_type` field and have
each financial skill refuse to overwrite the other type's file.

**BUG-6 — per-company browser scripts are committed as if reusable.**
The scripts dir holds ~20 one-off audit scripts (`tnf-audit-v3.js`, `jbl-audit-stealth.js`,
`hd-mx-audit-full.js`, `dell-browser-audit.js`, `torrid-audit.js`, `therealreal-audit.js`, …). These are
abandoned per-prospect forks of `audit-browser.js`, not part of any skill. They bloat the dir and imply a
generality that isn't there. *Fix:* archive them; the only live browser entry points are `audit-browser.js`
and `collect-similarweb-browser.js`. This also signals the real problem: **`audit-browser.js` isn't general
enough**, so each prospect got a hand-forked script — the browser layer is the least deterministic and the
deep-dive's hardest target.

---

## 5. Proposed cluster grouping for the deep-dive team (6 clusters)

Grouped so each cluster shares data sources / scripts / failure modes — one agent can deepen the whole
cluster coherently. Ordered by ROI.

**Cluster A — "ROI & Scoring math" (the arithmetic-out-of-the-LLM cluster).** *Highest ROI, lowest effort.*
`synth-business-case`, `audit-report` (scoring portion), `intel-financial-public` (ROI framing).
Shared asset: `calculate-roi.py`, `calculate-score.py`, `generate-audit-data.py`. Mission: every dollar
and every score comes from a script; LLM writes only narrative. Wire the dead calculators; extend the
post-LLM-corrector pattern. *(Determinism targets #1, plus reproducible-scoring accuracy risk #6.)*

**Cluster B — "Search-vendor truth" (network/packet detection).**
`intel-techstack`, `intel-competitors`, and the `detect-search` skill as the shared oracle.
Mission: make `detect-search` the single deterministic source of "what search vendor does site X run,"
replacing LLM-from-BuiltWith for both the prospect (1B Layer-3) and each competitor (1D). *(Target #2.)*

**Cluster C — "Financial & investor grounding" (must-not-fabricate cluster).**
`intel-financial-private`, `intel-investor`, `intel-industry`.
Shared failure mode: unstructured-source estimates + quote/benchmark recency. Mission: scripted candidate
collection (waterfall, transcript fetch, Tavily) + hard grounding gates (exact-substring quote match,
24-month filter on ALL paths) + range-not-point estimates. *(Accuracy risks #2/#3/#4; bug #2.)*

**Cluster D — "Signals collectors" (Apify/WebSearch enrichment cluster).**
`intel-social`, `intel-news`, `intel-hiring`, `intel-company` (enrichment portion).
Shared asset: Apify MCP + Scout + WebSearch fallback + `collect-*.py`. Mission: scripted collection +
deterministic classification/scoring (wire `collect-hiring.classify()`; scripted relevance pre-filter for
social/news), LLM only for significance calls. Standardize the `collection_method` + label-downgrade
discipline across all four. *(Target #3; accuracy risk #7.)*

**Cluster E — "Synthesis & campaign" (irreducible-writing + JSON-patch cluster).**
`intel-queries`, `synth-sales-plays`, `campaign-abx`.
These are legitimately LLM-heavy (query design, playbook, outreach copy). Mission: leave the writing alone;
build the post-LLM JSON patcher for `abx_sequence` (`generate-abx-json.py`) mirroring `generate-audit-data.py`,
and add grounding checks that every claim in copy traces to a research file. *(Target #4.)*

**Cluster F — "Browser, gates & orchestration" (the hard headless cluster).**
`audit-browser`, `audit-factcheck`, `audit-eval`, `algolia-search-audit` (orchestrator), and cleanup of
`audit-research` (legacy) + the per-company browser scripts.
Mission: (1) generalize `audit-browser.js` so per-prospect forks die (bug #6); (2) script factcheck's
mechanical dimensions (HTTP-200, cross-file equality, label presence) using the `audit-eval` bash pattern;
(3) deterministic public/private ticker check in the orchestrator (target #7); (4) archive dead code.
Highest effort, but it owns the suite's worst headless risk (WAF browser) and its quality gates.

---

## 6. Quick reference — what's already deterministic vs. LLM-by-hand (verified)

| Already deterministic (scripts WIRED & running) | Deterministic script EXISTS but UNWIRED (dead) | Legitimately irreducible LLM |
|---|---|---|
| `collect-traffic.py` (SimilarWeb API, ~15 endpoints) | `calculate-roi.py` (ROI math) | query-set design (1-queries) |
| `collect-techstack.py` + `parse-builtwith.js` (BuiltWith) | `calculate-score.py` (weighted avg) | sales playbook / MEDDPICC (3B) |
| `collect-financials.py` (yfinance) | `collect-hiring.classify()` (tier regex) | outreach copywriting (3D) |
| `collect-company.py` + `scout_company.py` (Scout) | — | per-area 0–10 scoring judgment (3C) |
| `generate-audit-data.py` (post-LLM JSON corrector, ~20 fields) | — | reading 10-K/transcript prose (1E/1G) |
| `render-audit.ts` (Deno SPA renderer) | — | vertical/parent classification (1A) |
| `audit-eval` (bash grep/wc/ls scorer) | — | search-UX quality judgment (L2) |
| `collect-industry.py` (Tavily, staleness filter) | — | estimate reconciliation (1F) |

The deep-dive's center of gravity: **wire the dead column, push the right-column items behind grounding
gates, and extend the `generate-audit-data.py` "LLM writes prose → script extracts structure" pattern to
business-case (ROI) and campaign-abx (JSON).**
