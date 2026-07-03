# Skill Feedback — Dell Factcheck

## Root Cause Patterns Found

### Pattern 1: Case-study slugs written from memory, never resolved
- Cause: The audit pipeline emits Algolia case-study URLs by guessing the slug from the customer name (`pc-componentes` → `pccomponentes`, `staples` → `staples-canada`, `hagergroup` → `hager-group`). No step validates that `algolia.com/customers/{slug}/` returns HTTP 200 before the slug is propagated into 6+ downstream fields and the customer-facing SPA. One wrong slug becomes 91 dead links.
- Affected files: dell-audit-data.json, 04-competitors.json/.md, index.html, dell-ae-report.html, dell-leave-behind.html, dell/ae-report.html, dell/leave-behind.html, dell-ae-precall-brief.md, dell-playbook.md, dell-business-case.md, abx-campaign/00-campaign-brief.md.
- Fix: Add to algolia-intel-competitors/SKILL.md (and any skill that emits `algolia_case_study_url`): "Before writing any `algolia.com/customers/{slug}/` URL, resolve it with a HEAD/GET request. If it 404s, do NOT guess a variant — look up the correct slug from the Algolia customers index or drop the citation (NO_SOURCE = drop). Never propagate an unresolved case-study URL into deliverables."
- Fix: Add to algolia-audit-factcheck/scripts/factcheck_mechanical.py: promote `algolia.com/customers/` URL liveness to a MECHANICAL blocking check (currently the script only checks field presence, not resolution, so the block was found only by the LLM/curl pass — it should be deterministic).

### Pattern 2: Scoring-matrix denominator computed by hand, not from the weights it lists
- Cause: 10-scoring-matrix.md hand-writes the weight-sum as "15.5" while the individual weights it enumerates sum to 15.0. The overall (2.6) was derived from the wrong denominator, disagreeing with the arithmetically-correct JSON value (2.7). Manual arithmetic in a narrative file drifts from the machine value.
- Affected files: research/10-scoring-matrix.md.
- Fix: Add to algolia-audit-report/SKILL.md (scoring step): "Do not hand-type the denominator. Compute sum(weights) programmatically and echo it; the matrix denominator, the matrix overall, and audit-data.json score.overall must be produced from the same computation. Assert matrix_overall == json_overall before writing."

### Pattern 3: score.* count fields set by estimate, not derived from breakdown_severity
- Cause: score.moderate_count=8 and low_count=null despite breakdown_severity clearly containing exactly 2 MEDIUM and 2 LOW. The counts were not derived from the actual severity map.
- Affected files: deliverables/dell-audit-data.json.
- Fix: Add to algolia-audit-report/SKILL.md: "critical_count/moderate_count/low_count MUST be computed as Counter(breakdown_severity.values()) — never hand-entered. Add a self-check that critical+moderate+low == len(breakdown)."

### Pattern 4 (minor): Deliverable competitors[] array degrades vs research JSON
- Cause: The lift step from 04-competitors.json into audit-data.json.competitors dropped the sourced search_vendor ("HawkSearch" → "Unknown") and injected endpoint fragments/placeholder traffic values.
- Affected files: deliverables/dell-audit-data.json.
- Fix: Add to the lift script: validate each lifted competitor row retains search_vendor from the source JSON; fail loudly if a CONFIRMED vendor becomes "Unknown".

## Patterns NOT Found (confirmed working correctly)
- Investor quotes: all 4 carry SEC 8-K source_urls; 2 load-bearing quotes verbatim on live filings. Quote-verification discipline is solid.
- Financial figures: FY26/FY25/FY24 consistent across research and all deliverables; money spot-check 3/3.
- No fabrication: 0 placeholders, 0 unsourced impact_stats; empty impact_stat fields correctly left empty.
- ABX campaign: all 5 touches have real bodies (no placeholders).
- Strategic angles / discovery questions: all populated with evidence + proof URLs (URLs themselves affected by Pattern 1, but structure is correct).
- Golden Angle: OFFENSIVE / no-competitor-on-Algolia, internally consistent across files.

---

## Run 2 Addendum (re-run after corrections C1–C4)

### New pattern found: Partial multi-occurrence find-replace
- Cause: C2 was applied to the arithmetic lines (51–53) and the narrative (line 66) of the scoring matrix, but the standalone summary block on line 56 still read `2.6 / 10`. The same value lived in three places with no single source of truth, so the correction missed one. Fixed this run.
- Affected files: research/10-scoring-matrix.md.
- Fix: Add to algolia-audit-report/SKILL.md and any correction step: "After editing a repeated literal value, grep the entire file for the OLD value and assert zero matches before declaring the correction complete."

### Environment gap: mechanical script missing
- The deterministic `factcheck_mechanical.py` that SKILL.md instructs to run first does not exist in this environment (`~/.claude/skills/algolia-audit-factcheck/scripts/` has no files). Mechanical checks were reconstructed by hand, defeating reproducibility.
- Fix: Ship the script with the skill, OR have SKILL.md print the exact fallback grep/curl/python commands when the script is absent, so mechanical results stay deterministic.

### Corrections confirmed applied correctly (Run 1 patterns resolved)
- Pattern 1 (dead slugs): RESOLVED — curl confirms pc-componentes/staples/hagergroup → 200, old slugs → 404, no dead slugs in content files.
- Pattern 2 (denominator 15.5): RESOLVED — now 15.0 everywhere, 40.5/15.0 = 2.7.
- Pattern 3 (score counts): RESOLVED — moderate=2, low=2, critical=6.
- Pattern 4 (competitors[] degradation): RESOLVED — deliverable competitors[] == research JSON, HP→HawkSearch restored.
