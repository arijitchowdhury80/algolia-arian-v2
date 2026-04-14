# PRISM v2 — Phase 2 Architectural Decisions
**Date:** 2026-04-14
**Status:** PROPOSED — awaiting Arijit review/approval before Phase 2 implementation

## Context

Phase 1 (v2 core infrastructure) is complete. We have:
- `prism_platform/v2/types.py` — Finding, ModuleConfig, ExecutionContextV2, ClaimRegistryEntry
- `prism_platform/v2/agent_api.py` — AgentAPIClient (Perplexity wrapper)
- `prism_platform/v2/playbook.py` — PlaybookLoader (markdown + template resolution)
- `prism_platform/v2/executor.py` — ModuleExecutor (generic harness)
- `prism_platform/v2/modules/intel_company/` — seed module (schema + config + playbook)
- `prism_platform/v2/clusters/` — 5 deep-research cluster playbooks (A–E)

Phase 2 requires resolving 8 architectural gaps before implementation begins. This document proposes concrete decisions for each gap and identifies what needs Arijit's approval.

---

## Decision 1: Merge Strategy (Gap 1)

**Gap:** When Agent API and structured APIs (BuiltWith, SimilarWeb) return conflicting data for the same field, how is it resolved?

**Proposed Decision: Source-priority merge with explicit conflict recording.**

### Implementation

Add `MergedField` wrapper type used wherever a value might come from multiple sources:

```python
class MergedField(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    
    value: Any = Field(description="The resolved value")
    source: str = Field(description="Where this value came from: 'builtwith', 'perplexity', 'openai', 'yahoo_finance', etc.")
    confidence: Literal["confirmed", "conflicting_signals", "single_source"]
    alternatives: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Other values found from other sources — kept as intelligence"
    )
```

### Source Priority Order (per data type)
| Data Type | Priority |
|-----------|----------|
| Search vendor detection | BuiltWith > SimilarWeb > Agent API |
| Revenue figures | SEC EDGAR > Yahoo Finance > Agent API |
| Employee count | LinkedIn (structured) > Agent API |
| Exec quotes | Agent API (Agent API researches primary sources) |
| News/signals | Agent API (web research) |

### Key principle
Conflicting signals are intelligence. `"BuiltWith detects Elasticsearch; Agent API research shows engineering blog post about evaluating Algolia replacements"` = HIGHER value than either alone. The `alternatives` field preserves this.

**Implementation location:** `prism_platform/v2/merge.py`

**Approval needed?** YES — confirm the `MergedField` pattern vs. keeping simpler flat fields.

---

## Decision 2: Rate Limiter (Gap 2)

**Gap:** 13 modules running Agent API calls in parallel will exhaust Perplexity's rate limits (1 QPS at Tier 0, 8 QPS at Tier 2).

**Proposed Decision: Async semaphore singleton with priority queue.**

### Implementation

```python
# prism_platform/v2/rate_limiter.py
class AgentAPIRateLimiter:
    """Singleton async semaphore for Agent API calls.
    
    Priority levels (lower = higher priority):
    1 = seed (intel-company — blocks everything)
    2 = intelligence (Wave 1 modules)
    3 = clusters (deep-research calls)
    4 = synthesis
    5 = background
    """
    
    _instance: AgentAPIRateLimiter | None = None
    
    def __init__(self, qps: float = 1.0) -> None:
        self._semaphore = asyncio.Semaphore(1)
        self._min_interval = 1.0 / qps
        self._last_call_time = 0.0
```

### Tier auto-detection
Check `PERPLEXITY_TIER` env var. Default to Tier 0 (1 QPS) for safety. When cumulative monthly spend crosses $100, bump to Tier 2 config (8 QPS).

**Approval needed?** NO — implement as described. This is pure infrastructure.

---

## Decision 3: Per-Company vs. Comparative Calls (Gap 3)

**Gap:** Should cluster playbooks make one call per company or one call covering all companies?

**Proposed Decision: Playbook-declared strategy via frontmatter field.**

The `execution_strategy` frontmatter field (already in `PlaybookMeta`) controls this:

| Strategy | When to use | Cost |
|----------|-------------|------|
| `per-company` | Prospect deep dive, exec quotes, search tech | 1 call per company |
| `comparative` | Competitor gap analysis, positioning | 1 call, all companies |
| `prospect-only` | Signals, financial — competitor data not needed | 1 call |

The cluster playbooks already use `{competitors}` variable substitution. For `comparative` strategy, all competitor domains are injected into a single call. For `per-company`, the executor fans out into N calls (one per competitor).

**Implementation:** Extend `ModuleExecutor.execute()` to read `meta.execution_strategy` and handle fan-out.

**Approval needed?** NO — this is already partially designed. Implement as described.

---

## Decision 4: Citation Validation (Gap 4)

**Gap:** Perplexity returns citation URLs but LLMs hallucinate URLs. Need validation.

**Proposed Decision: Implement Tier 1 now, defer Tier 2 to Phase 3.**

### Tier 1 (implement in Phase 2)
URL existence check using async HEAD requests. Fast, cheap, catches the most common hallucination pattern (made-up URLs that return 404).

```python
# prism_platform/v2/citation_validator.py
async def validate_citations_tier1(citations: list[str]) -> list[CitationValidationResult]:
    """Check all citation URLs exist (HEAD request)."""
```

Every `ClaimRegistryEntry` gets `citation_status: Literal["live", "dead", "unchecked"]`.

### Tier 2 (Phase 3)
Content verification — fetch page, confirm claim appears on page. High cost, reserved for revenue figures and exec quotes. Defer until Phase 2 is working.

### Tier 3 (already exists)
Cross-source confirmation — if BuiltWith AND Agent API both say Elasticsearch, that's `confidence: "confirmed"`. No additional cost. Already handled by the merge strategy.

**Approval needed?** NO — Tier 1 now, Tier 2 later.

---

## Decision 5: audit-browser Hybrid Approach (Gap 5)

**Gap:** Full Playwright browser testing of 4 competitors takes 40+ minutes.

**Proposed Decision: Playwright for prospect, Agent API research for competitors.**

| Target | Method | Output |
|--------|--------|--------|
| Prospect ({domain}) | Playwright + Claude Vision | Screenshots + actual scores |
| Each competitor | Cluster C Agent API research | Capability assessment + citations |

The `CompetitorSearchProfile` Pydantic schema covers both:
- Prospect: `evidence_type: "browser_test"`, screenshot paths, actual query results
- Competitors: `evidence_type: "research"`, citations, capability summary

**Implementation:** `audit-browser` v2 module uses `execution_strategy: "hybrid"` — Playwright runner for prospect, playbook executor for competitors.

**Approval needed?** YES — confirm the hybrid approach is acceptable vs. full browser testing for all.

---

## Decision 6: Synthesis Modules as Playbooks (Gap 6)

**Gap:** synth-business-case and synth-sales-plays don't call external APIs — they synthesize from upstream module outputs.

**Proposed Decision: Yes, they become playbooks. Data source is the module cache.**

### New data source type: `FROM_CACHE`

```python
class CacheDataSource(BaseModel):
    """Data source that reads from upstream module results in context."""
    type: Literal["FROM_CACHE"]
    modules: list[str]  # Which upstream modules to read
```

The playbook template for synth-business-case would include:
```
## Upstream Intelligence Available

Company: {company_name} ({domain})

Financial profile:
{upstream_intel_financial}

Search technology:
{upstream_intel_techstack}

Executive quotes:
{upstream_intel_investor}
```

Same `ModuleExecutor`, different context enrichment step before playbook resolution.

**Approval needed?** NO — implement as described.

---

## Decision 7: audit-factcheck Stays Custom (Gap 7)

**Gap:** Should audit-factcheck become a playbook or stay as custom code?

**Proposed Decision: Keep as custom code. Standardize its INPUT via ClaimRegistry.**

**Rationale:** The factcheck module is the quality gate that validates everything else. If it becomes a playbook running through the same executor as the modules it's checking, it loses adversarial independence. Keep custom.

**What changes:** Every playbook-based module auto-generates a `ClaimRegistry` (already done in `ModuleExecutor._build_claims()`). The factcheck module reads these registries. The `ClaimRegistryEntry` type in `v2/types.py` is already the standardized format.

**One gap to close:** The current claim builder only creates entries for scalar fields. Need to also extract claims from list fields (exec names, competitor names, revenue citations). Add to Phase 2 scope.

**Approval needed?** NO.

---

## Decision 8: Playbook Evaluation Framework (Gap 8)

**Gap:** How do you know if a playbook produces good results? Need CI for playbooks.

**Proposed Decision: Design the framework in Phase 2, build the eval runner in Phase 3.**

### What to design now (Phase 2)
File structure per module:
```
prism_platform/v2/modules/{name}/
├── config.py
├── playbook.md
├── schemas.py
└── evals/
    ├── golden/
    │   ├── dell.com.json      # Known-good output for Dell
    │   └── nike.com.json      # Known-good output for Nike
    ├── rubric.md              # Scoring criteria (completeness, citations, accuracy)
    └── eval_runner.py         # Phase 3 implementation
```

### Rubric structure (Phase 2 design)
Each playbook gets a rubric scoring:
- **Completeness** (10 pts): Required fields populated, lists have minimum items
- **Citation quality** (10 pts): All claims cited, URLs live, citations match claims
- **Accuracy** (10 pts): Verifiable facts match known-good fixtures

Pass threshold: 22/30. Below 22 = playbook regression, block merge.

**Approval needed?** YES — confirm golden fixture companies (dell.com, nike.com?) and pass threshold.

---

## Phase 2 Implementation Order

Given the above decisions, the recommended build sequence:

1. **`citation_validator.py`** — Tier 1 URL validation (no dependencies)
2. **`rate_limiter.py`** — Async semaphore singleton (no dependencies)
3. **`merge.py`** — MergedField + source-priority merge logic (no dependencies)
4. **Extend `executor.py`** — Add fan-out for `per-company` strategy + cache data sources
5. **intel-techstack v2** — First spoke module (tests the executor extensions)
6. **intel-traffic v2** — Second spoke (validates SimilarWeb integration pattern)
7. **intel-financial-public v2** — Third spoke (validates Yahoo Finance + SEC integration)
8. **Cluster orchestration layer** — Wire 5 cluster playbooks into a ResearchOrchestrator that runs them in parallel and extracts Findings via map-reduce

---

## Open Questions for Arijit

These need decisions before we can build:

1. **MergedField pattern** (Decision 1) — Use the wrapper type, or keep flat fields with separate `_source` and `_confidence` suffix fields?
2. **audit-browser hybrid** (Decision 5) — Playwright for prospect only, research for competitors — acceptable quality tradeoff?
3. **Eval golden fixtures** (Decision 8) — Which companies? What pass threshold?
4. **Phase 2 start** — Do we start with the infrastructure (citation_validator, rate_limiter, merge) or jump straight to the first spoke module (intel-techstack v2)?

---

## Session Log — 2026-04-14

**Built today:**
- PRISM v2 core infrastructure (Tasks 1–7 from implementation plan): 2,000 lines, 39 tests
- Research cluster playbooks A–E
- This architectural decisions document

**Branch:** `feature/v2-core-infrastructure` merged to `main`

**Next session starting point:**
- Read this document
- Get Arijit's answers to the 4 open questions above
- Start Phase 2 with `rate_limiter.py` + `citation_validator.py` + `merge.py` (the infrastructure that doesn't need approval)
