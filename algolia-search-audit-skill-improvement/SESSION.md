# Session State — Algolia Search Audit Skill Improvement

> Written 2026-04-08 at ~50% context. Resume from here.

---

## What We're Doing

Comprehensive refactor of the Algolia Search Audit skill pipeline (~20 Claude Code skills) to make it reliable, consistent, and automatable. Currently requires 4-6 hours of manual shepherding per audit. Target: one-command, ~30 min, fully automated.

## Where We Are

### Completed
1. Read both Anthropic agent harness engineering blogs — extracted patterns
2. Wrote `Architecture/AgentHarnessPatterns.md` to Obsidian vault
3. Read ALL 20 skills (full text) and assessed each one
4. Created comprehensive Obsidian vault project at `Projects/Algolia-Search-Audit/`:
   - `Index.md` — architecture overview, wave structure, workspace layout, field names
   - `Module-Catalog.md` — all 20 modules with inputs/outputs/issues/codification opportunities
   - `Known-Issues.md` — 20 prioritized issues with root causes and fixes
   - `Refactor-Architecture.md` — target Python harness architecture, sprint plan
5. Presented full diagnosis to Arijit
6. **Decision 1 RESOLVED**: Built `algolia-customer-evidence.json` from CustomerEvidence-Algolia.xlsx spreadsheet
   - Source: `~/Library/CloudStorage/GoogleDrive-arijit.chowdhury@algolia.com/My Drive/AI-Docs/DATA/CustomerEvidence-Algolia.xlsx`
   - Output: `data/algolia-customer-evidence.json` in rc2-algolia project (needs to go to vault `Data/` folder)
   - 866 customers, 333 quotes, 81 proof points, 586 with website domains
   - Tabs used: Cust.Quotes, Cust. Stories, Cust. Proofpoints, Grocery, Fashion, Luxury, 100k+, Travel
   - No sensitive data (no ARR, emails, CSM names, health scores)
   - Still needs to be copied to vault at `ArijitOS-Brain/Data/algolia-customer-evidence.json`
7. **Read PRISM foundation docs** — these are the canonical standards for refactoring:
   - `Standards/Module-Spec-Template.md` — runtime-agnostic module spec template
   - `Projects/PRISM/Context/Patterns-For-Skills.md` — 12 patterns to adopt
   - `Projects/PRISM/Modules/Module-Catalog.md` — all 20 PRISM modules reference
8. **Started per-skill design review** — Wave 1, Module 1A (intel-company)
   - Read current skill.md + collect-company.py
   - Completed gap analysis: Current vs PRISM target
   - Presented proposed changes to Arijit

### 3 Original Decisions — Status
1. **Static customer dataset** — RESOLVED. Built algolia-customer-evidence.json from spreadsheet.
2. **Skill files vs prompts** — STILL OPEN. Keep skill files + separate prompts/*.txt, or consolidate?
3. **Scope / sprints** — STILL OPEN. One big plan or sprints?

### Key Design Decisions Made
- Use PRISM's architectural foundation for skill refactoring (same specs, different runtime)
- Skills need to adopt Perplexity as primary research API (not just WebSearch/WebFetch)
- intel-competitors should become pure synthesis (like PRISM)
- insights-engine should be added as new module
- Said vs Found matrix should be added to intel-investor
- Customer evidence JSON uses two top-level arrays: `customers` (company-level) and `proof_points` (industry stats)
- Verticals stored as array (`verticals[]`) not single field
- algolia-customer-evidence.json goes to vault `Data/` folder as canonical reference

## Per-Skill Design Review — Progress

### Wave 1: Intelligence (11 modules)
- [x] **1A intel-company** — Gap analysis done. Proposed changes:
  1. Replace WebSearch with Perplexity sonar for enrichment
  2. Add competitors[] to output (cross-check vs algolia-customer-evidence.json)
  3. Add has_search_bar via HTML parsing
  4. Adopt _sources array (PRISM evidence tier pattern)
  5. Strengthen validation to 8 checks
  6. Keep portfolio detection (PRISM should adopt FROM skill)
  7. Rename fields to PRISM canonical (legal_name, industry not vertical)
  8. Open question: keep BuiltWith keywords-api or drop (Perplexity may make redundant)?
  - **Status: Presented to Arijit, awaiting feedback before writing spec**
- [ ] 1B intel-techstack
- [ ] 1C intel-traffic
- [ ] 1D intel-competitors
- [ ] 1E intel-financial-public
- [ ] 1F intel-financial-private
- [ ] 1G intel-investor
- [ ] 1H intel-hiring
- [ ] 1I intel-social
- [ ] 1J intel-news
- [ ] 1K intel-partner
- [ ] 1L intel-industry

### Wave 2: Query Generation
- [ ] intel-queries

### Layer 2: Browser Audit
- [ ] audit-browser

### Layer 3: Synthesis
- [ ] synth-business-case
- [ ] synth-sales-plays
- [ ] audit-report
- [ ] campaign-abx

### Layer 4: Quality
- [ ] audit-factcheck
- [ ] audit-eval

### New Module
- [ ] insights-engine (cross-audit benchmarking — no current skill equivalent)

## PRISM 12 Patterns to Apply to Every Skill

1. Collector / Enricher / Validator separation
2. Typed output schemas (no freeform JSON)
3. Evidence tiers on every data point (_sources array)
4. 8-10 validation rules per module
5. Public/private branching (financial + investor)
6. Said vs Found matrix (investor quotes → Algolia value props)
7. Competitor fan-out (collect competitor data in same pass)
8. Golden Angle detection (competitor using Algolia)
9. ICP tier classification in hiring
10. GAN-inspired factcheck (mechanical Python + 5 LLM dims)
11. Cost-conscious LLM tier assignment
12. Module spec as single source of truth

## Key Vault Docs to Read on Resume

1. `Standards/Module-Spec-Template.md` — the universal template
2. `Projects/PRISM/Context/Patterns-For-Skills.md` — 12 patterns
3. `Projects/PRISM/Modules/Module-Catalog.md` — PRISM module reference
4. `Projects/Algolia-Search-Audit/Index.md` — current pipeline architecture
5. `Projects/Algolia-Search-Audit/Known-Issues.md` — 20 issues
6. `Projects/Algolia-Search-Audit/Refactor-Architecture.md` — target harness

## Key File Locations

| What | Where |
|------|-------|
| Obsidian vault | `~/Library/CloudStorage/GoogleDrive-arijit.chowdhury@algolia.com/My Drive/AI-Docs/Obsidian/ArijitOS-Brain/` |
| Customer evidence spreadsheet | `~/...AI-Docs/DATA/CustomerEvidence-Algolia.xlsx` |
| Customer evidence JSON | `rc2-algolia/data/algolia-customer-evidence.json` (needs vault copy) |
| Vault project docs | `...ArijitOS-Brain/Projects/Algolia-Search-Audit/` |
| PRISM docs | `...ArijitOS-Brain/Projects/PRISM/` |
| Current skill files | `~/.claude/skills/algolia-intel-*/skill.md` |
| Python scripts | `~/.claude/skills/algolia-search-audit/scripts/` |
| This project folder | `/Users/arijitchowdhury/AI-Development/PIP/algolia-search-audit-skill-improvement/` |
| Plans directory | `~/.claude/plans/` |

## What Happens Next

1. **Arijit answers open question** on intel-company: keep BuiltWith keywords-api or drop?
2. **Write intel-company module spec** to vault at `Projects/Algolia-Search-Audit/Modules/intel-company.md`
3. **Continue Wave 1 review**: 1B techstack → 1C traffic → ... → 1L industry
4. For each: read current skill, gap analysis vs PRISM, propose changes, write spec
5. After all specs written, answer remaining decisions (skill files vs prompts, scope/sprints)
6. Write comprehensive implementation plan
7. Switch to Sonnet for coding execution

## User Preferences
- Planning on Opus, coding on Sonnet
- Wants comprehensive planning before any code
- Wants each skill reviewed for completeness, not just bugs
- Wants maximum codification — reduce LLM steps wherever possible
- Wants the package to be distributable to others eventually
- PRISM foundation = canonical standard for skill refactoring
- No sensitive data in customer evidence JSON
- Vault path for customer evidence: `ArijitOS-Brain/Data/`
