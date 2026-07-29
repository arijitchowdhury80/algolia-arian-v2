# PRISM Historical Audit Migration -- DRY RUN REPORT

**SCRATCH DB -- live Postgres untouched.** Everything below ran against a
throwaway `postgres:16` Docker container on `127.0.0.1:55433`, torn down
at the end of this run. No VPS, no live database, no deploy.

Generated: 2026-07-02 18:06:01 EDT

## Summary

- Slugs processed: 18
- Round-trip PASS: 16
- Round-trip FAIL: 2
- Load errors: 0
- Unique accounts created (post-dedup): 17
- Audits created: 18

## Per-slug results

| slug | domain | account_id | score | #module_execs | #gaps | round-trip |
|---|---|---|---|---|---|---|
| british-airways | britishairways.com | `708a4dce-d3f9-4a15-a003-31563ed35bbb` | 2.1 | 10 | 4 | PASS |
| brooks-running | brooksrunning.com | `f3b50559-438c-4589-ba08-7983d39267fc` | 4.3 | 10 | 6 | PASS |
| dell | dell.com | `38eb4b5d-e3e3-465b-87b9-3fd4ab21ce31` | 2.7 | 10 | 4 | PASS |
| dsw | dsw.com | `860dda33-4d1b-4cb7-87f9-d47bbd7abb43` | 3.8 | 10 | 5 | PASS |
| footlocker | footlocker.com | `d051a9d5-7835-4e1b-bf72-eb557487d85c` | 3.2 | 10 | 4 | PASS |
| homedepot-mexico | homedepot.com.mx | `710b1215-28a3-44ab-8a01-7c92710cab15` | 2.6 | 10 | 6 | PASS |
| jbl | jbl.com | `f2d3a234-3066-4569-99a6-88c16ef68ec3` | 1.93 | 10 | 6 | FAIL |
| labanquepostale | labanquepostale.fr | `c4aa2993-20b9-4baf-b385-0d73f7736c46` | 2.1 | 10 | 5 | PASS |
| llbean | llbean.com | `c52bb0b0-0448-440e-afb9-af181278a140` | 3.6 | 10 | 5 | PASS |
| lululemon | lululemon.com | `10b315c4-3517-4cad-ac4c-8dbf4f901bd1` | 4.3 | 10 | 7 | PASS |
| michaelkors | michaelkors.com | `5691fd2e-b8ab-40a7-88cb-264f385d6956` | 1.9 | 10 | 4 | PASS |
| nike | nike.com | `3f7389df-1bcc-4cb3-81d9-ef5824892302` | 4.32 | 10 | 7 | FAIL |
| oriental-trading | orientaltrading.com | `0bb60197-c70c-4f30-a2f7-77bd13ccbeda` | 2.6 | 10 | 4 | PASS |
| orientaltrading | orientaltrading.com | `0bb60197-c70c-4f30-a2f7-77bd13ccbeda` | 2.6 | 10 | 5 | PASS |
| petsmart | petsmart.com | `395233c6-036c-4fd3-ab15-21fbd87cb841` | 5.8 | 10 | 4 | PASS |
| savage-x-fenty | savagex.com | `5c7928ae-1aa1-4cad-ad8d-853b558af20f` | 3.5 | 10 | 5 | PASS |
| thenorthface | thenorthface.com | `666de642-138c-4fda-9555-8984550fffc1` | 4.8 | 10 | 4 | PASS |
| torrid | torrid.com | `a1b945c1-8d86-4bb1-b9b6-89a2d05ada35` | 3.0 | 10 | 4 | PASS |

## Round-trip verification detail

Proves: `config.audit_data` read back from Postgres deep-equals the source
`window.AUDIT_DATA` blob (full JSON compare), `audits.score` matches the parsed
`score.overall`, and `accounts.domain` matches the canonical domain used to file
this audit. Any mismatch is a FAILURE line below, not a warning.

- **british-airways**: PASS (config.audit_data, score, domain all match source)
- **brooks-running**: PASS (config.audit_data, score, domain all match source)
- **dell**: PASS (config.audit_data, score, domain all match source)
- **dsw**: PASS (config.audit_data, score, domain all match source)
- **footlocker**: PASS (config.audit_data, score, domain all match source)
- **homedepot-mexico**: PASS (config.audit_data, score, domain all match source)
- **jbl**: score mismatch: stored=1.9 expected=1.93
- **labanquepostale**: PASS (config.audit_data, score, domain all match source)
- **llbean**: PASS (config.audit_data, score, domain all match source)
- **lululemon**: PASS (config.audit_data, score, domain all match source)
- **michaelkors**: PASS (config.audit_data, score, domain all match source)
- **nike**: score mismatch: stored=4.3 expected=4.32
- **oriental-trading**: PASS (config.audit_data, score, domain all match source)
- **orientaltrading**: PASS (config.audit_data, score, domain all match source)
- **petsmart**: PASS (config.audit_data, score, domain all match source)
- **savage-x-fenty**: PASS (config.audit_data, score, domain all match source)
- **thenorthface**: PASS (config.audit_data, score, domain all match source)
- **torrid**: PASS (config.audit_data, score, domain all match source)

## SCHEMA GAP -- `audits.score` precision loss (REAL BUG, found by this run)

`audits.score` is `Numeric(3, 1)` -- one digit after the decimal point. Real
audit scores carry two decimal digits (e.g. jbl = 1.93, nike = 4.32). Postgres
silently rounds on insert: 1.93 -> 1.9, 4.32 -> 4.3. This is exactly the class
of silent-precision-loss bug the round-trip check exists to catch, and it did:

- **jbl**: score mismatch: stored=1.9 expected=1.93
- **nike**: score mismatch: stored=4.3 expected=4.32

**Recommendation:** widen `audits.score` (and `audits.factcheck_score`, same
`Numeric(3, 1)` type) to `Numeric(3, 2)` in the same alembic migration that adds
`audit_data` (see schema-gap section below), before the real cutover runs. Do
NOT round scores to fit the current column -- that's fabricating precision the
source data doesn't claim to have lost.

## Per-slug gap list (fields NULL/missing -- never fabricated)

### british-airways
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### brooks-running
- account.revenue_estimate: missing (company_snapshot.revenue)
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- module_executions[algolia-intel-industry]: source section empty/missing, marked skipped
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### dell
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### dsw
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- module_executions[algolia-intel-industry]: source section empty/missing, marked skipped
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### footlocker
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### homedepot-mexico
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- module_executions[algolia-intel-partner]: source section empty/missing, marked skipped
- module_executions[algolia-intel-industry]: source section empty/missing, marked skipped
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### jbl
- account.employee_count: missing (company_snapshot.employees)
- account.revenue_estimate: missing (company_snapshot.revenue)
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### labanquepostale
- account.revenue_estimate: missing (company_snapshot.revenue)
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### llbean
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- module_executions[algolia-intel-industry]: source section empty/missing, marked skipped
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### lululemon
- cross-check: grounding-store score (3.1) differs from published score (4.3); published treated as PRIMARY per instructions, grounding-store value not used
- account.headquarters: missing (company_snapshot.hq)
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- module_executions[algolia-intel-industry]: source section empty/missing, marked skipped
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### michaelkors
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### nike
- account.headquarters: missing (company_snapshot.hq)
- account.employee_count: missing (company_snapshot.employees)
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- module_executions[algolia-intel-investor]: source section empty/missing, marked skipped
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### oriental-trading
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### orientaltrading
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- account dedup: domain orientaltrading.com already had an account from a prior slug; ON CONFLICT (domain) DO UPDATE ran, COALESCE(existing, new) merge applied
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### petsmart
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### savage-x-fenty
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- module_executions[algolia-intel-industry]: source section empty/missing, marked skipped
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### thenorthface
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

### torrid
- account.recent_news: no dedicated news array in AUDIT_DATA (news-like content is embedded in intelligence_signals/findings, not extracted)
- account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA (schema-vs-source shape gap, not a per-company data gap)
- audit.factcheck_score / factcheck_action: not present in AUDIT_DATA (factcheck-mechanical gate result is not persisted into the rendered report)
- deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; 0 deliverable rows created for this audit (not fabricated)

## Dedup reconciliation: oriental-trading / orientaltrading

Both slugs resolve to the same real-world domain, `orientaltrading.com`, and the
same company, Oriental Trading Company. They are two distinct historical audit
runs of the same account (not duplicate runs of the same audit), so the migration
keeps **one account row** (deduped by the `accounts.domain` UNIQUE constraint) and
**two audit rows** (one per slug), both pointing at that single `account_id`.

Reconciliation policy for the shared account row: the first-processed slug wins
field-for-field; any field left null/empty by the first slug is backfilled from
the second slug via a real `INSERT ... ON CONFLICT (domain) DO UPDATE` with
`COALESCE(existing, new)` per column (`upsert_account`). No field is ever
overwritten from a present value to null. A per-slug gap entry records the merge.

## Published-vs-grounding-store coverage

13 of the 18 published slugs also have a grounding-store JSON at
`~/prism-data/hermes-prism/reports/<slug>/audit-data.json`; those were compared
but the published HTML's inline `window.AUDIT_DATA` was treated as PRIMARY per
instructions (it is the actually-served truth). 5 slugs have no grounding JSON at
all -- for those, the published HTML is the *only* source.

| slug | has grounding JSON |
|---|---|
| british-airways | yes |
| brooks-running | yes |
| dell | yes |
| dsw | yes |
| footlocker | no |
| homedepot-mexico | yes |
| jbl | yes |
| labanquepostale | yes |
| llbean | yes |
| lululemon | yes |
| michaelkors | no |
| nike | yes |
| oriental-trading | yes |
| orientaltrading | no |
| petsmart | yes |
| savage-x-fenty | yes |
| thenorthface | no |
| torrid | no |

## SCHEMA GAP -- recommendation for real cutover

`audits` has no dedicated `audit_data JSONB` column -- only `config JSONB`, which
is meant for run configuration, not the full rendered audit payload. This dry run
stored the entire `window.AUDIT_DATA` blob inside `config["audit_data"]` to prove
faithful round-trip, but that overloads a column with two unrelated purposes.

**Recommendation:** add an `audit_data JSONB` column to `audits` via a new alembic
migration (`009_add_audit_data_column`, next after the current head at `007`) for
the real cutover, and keep `config` reserved for run-time configuration only. This
matches airtight-pipeline plan section 1.4 (full audit-data JSON persisted).

## Deliverables

0 deliverable rows were created for any of the 18 audits. Verified by full-text
scan of every published `window.AUDIT_DATA` blob for `.pdf`, `.pptx`, `deck`,
`landing`, `playbook`, `file_url`, `file_key` -- none of the 18 reports carry a
deck/landing/PDF/playbook file reference in their rendered data. This is a real
gap in the source, not a migration bug: those deliverables exist as separate files
on disk/VPS outside AUDIT_DATA and were out of scope for this dry run.

## Final rowcounts (scratch DB, before teardown)

- `accounts`: 17
- `audits`: 18
- `module_executions`: 180
- `deliverables`: 0
