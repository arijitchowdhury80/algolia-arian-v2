# Phase 2 interface contract (patch #2) — binding, read by every downstream subagent

Written by the controller after Task 1 recon, informed by two recon findings that change scope:
1. `run-audit.sh --skill <name>` already exists and works (manual rerun path) — per-skill dispatch is NOT new, it's exposing an existing capability through an automatic loop.
2. `prism_platform/pipeline/self_heal.py` already implements a generic, tested (20 tests), dependency-injected `dispatch -> gate -> retry-until-clean -> NEEDS_HUMAN` loop (`SelfHealLoop`). It operates on a `phase: str` — a skill name is just another string, so it fits without modification for the *loop* itself. **Reuse it. Do not write a new retry loop from scratch.**

`prism_platform/orchestrator/` (Temporal-free FastAPI pipeline, Perplexity-based `ModuleExecutor`) is a **separate, dead system** from the old custom-SaaS build (see CLAUDE.md NAMING CANON — "NOT the old custom-SaaS/deterministic-module build (dead)"). It also writes to `module_executions` but through an unrelated code path. **Do not extend or call into it. Not in scope.** The `ModuleExecution` SQLAlchemy model in `prism_platform/db/models.py` IS reusable (confirmed live schema match in recon report item 3) — use it for the DB-write layer, not raw SQL.

## File placement

- `prism_platform/pipeline/gate.py` — new file, alongside existing `block_detector.py` / `screenshot_gate.py` / `self_heal.py`.
- `prism_platform/pipeline/verdicts.py` — new file, the Pydantic schemas (kept separate from `gate.py` so subagents building stage-specific LLM calls can import schemas without importing gate orchestration logic).
- Required, scoped extension to `prism_platform/pipeline/self_heal.py`: add a `fatal: bool = False` field to `GateResult` (default preserves all 20 existing tests unmodified) and change `SelfHealLoop.run_phase` to break to `NEEDS_HUMAN` immediately when the latest `GateResult.fatal is True`, without waiting for `max_passes`. This is what makes patch #3 (unfixable BLOCKs skip retry) actually work — `SelfHealLoop` as it stands today has no early-exit path other than CLEAN. New tests required for the fatal-early-exit behavior; do not touch or weaken the existing 20 tests. This is a small, additive, backward-compatible change — build it as part of Task 3, not a separate ask.

## `gate()` — the function every skill's output passes through

```python
# prism_platform/pipeline/gate.py
from prism_platform.pipeline.verdicts import (
    FactCheckVerdict, AdversarialVerdict, QualityScore, LegalVerdict,
)

def gate(skill_output: SkillOutput) -> Verdict:
    """Run all 5 verification stages against one skill's output, in order,
    short-circuiting on the first non-PASS stage. Returns one Verdict."""
```

```python
@dataclass(frozen=True)
class SkillOutput:
    skill_name: str          # one of the 16 SKILL_NAMES in prism-runner.py
    domain: str               # e.g. "belk.com"
    audit_dir: Path           # $ALGOLIA_AUDIT_DIR/{CompanyName}/ — factcheck_mechanical.py is file-based, not value-based
    company_name: str         # factcheck_mechanical.py's --company arg

class VerdictStatus(str, Enum):
    PASS = "pass"
    BLOCK = "block"

class BlockClass(str, Enum):        # patch #3
    RETRY_WORTHY = "retry_worthy"   # schema/format drift, transient — safe to re-dispatch same skill
    UNFIXABLE = "unfixable"         # data genuinely absent / contradicted by source — NEEDS_HUMAN on first occurrence, no retry

@dataclass(frozen=True)
class Verdict:
    skill_name: str
    stage: int                      # 1-5 — the stage that produced this verdict. Patch #4: "same check" for the 3-strike kill condition = same STAGE, not same claim/reason.
    status: VerdictStatus
    block_class: BlockClass | None  # set only when status == BLOCK
    findings: tuple[str, ...]
    mechanical_raw: str = ""        # stdout/stderr of factcheck_mechanical.py, stage 1
    factcheck: FactCheckVerdict | None = None      # stage 2
    adversarial: AdversarialVerdict | None = None  # stage 3
    quality: QualityScore | None = None            # stage 4
    legal: LegalVerdict | None = None              # stage 5
```

### The 5 stages, in order (short-circuit on first BLOCK)

1. **Mechanical** — `factcheck_mechanical.py --audit-dir X --company Y` (already exists, confirmed executable in recon item 3+4). Exit 0 → PASS. Exit 2 → BLOCK, `block_class=RETRY_WORTHY` (schema/format issues are exactly what this script catches). Wrap via `self_heal.subprocess_gate()`, do not reimplement the exit-code mapping.
2. **Factcheck** — the LLM judgment layer already inside `algolia-audit-factcheck` (evidence-tier system: AUTHENTIC/WEBFETCH/WEBSEARCH/NO_SOURCE). **E2: schema-constrained** — force tool-use JSON against `FactCheckVerdict` (Pydantic, in `verdicts.py`). `verdict="CONTRADICTED"` or `"UNSUPPORTED"` → BLOCK, `block_class=UNFIXABLE` (the source doesn't exist or disagrees — retrying the same skill won't fix that). `verdict="SUPPORTED"` → PASS.
3. **Adversarial panel** — patch #1: run ONLY on claims stage 1 or 2 flagged as risky (not every claim in every skill). N=3 voters, each schema-constrained (`AdversarialVerdict`, forced tool-use JSON, each voter told to try to refute and default `refuted=true` if uncertain). Majority-not-refuted → PASS; majority-refuted → BLOCK, `block_class=UNFIXABLE`.
4. **Quality** — `algolia-audit-eval`'s Dimension 3 (instruction adherence) — the one dimension recon confirmed is NOT already delegated to `factcheck_mechanical.py`. Schema-constrained (`QualityScore`). Score below the skill's pass threshold → BLOCK, `block_class=RETRY_WORTHY` (a re-run may follow instructions better; this is the one stage where retry is plausibly productive).
5. **Legal** — patch #8: **no rubric exists.** Do not build automated logic for this stage. `LegalVerdict` is a stub: always returns `status="needs_human_review"`, never PASS/BLOCK automatically. Wire the plumbing (the DB row, the report surface) but the actual judgment is manual-Arijit-only until a rubric exists — say so explicitly in the code comment and the DoD, don't silently auto-pass it.

### Pydantic schemas (`prism_platform/pipeline/verdicts.py`, E2-compliant — every field the LLM must fill, no free-form prose parsed after)

```python
class FactCheckVerdict(BaseModel):
    claim: str
    evidence_tier: Literal["AUTHENTIC", "WEBFETCH", "WEBSEARCH", "NO_SOURCE"]
    verdict: Literal["SUPPORTED", "UNSUPPORTED", "CONTRADICTED"]
    citation: str | None
    reasoning: str

class AdversarialVoterVerdict(BaseModel):
    voter_id: int
    refuted: bool
    reasoning: str

class AdversarialVerdict(BaseModel):
    claim: str
    votes: list[AdversarialVoterVerdict]
    survives: bool   # true iff majority NOT refuted

class QualityScore(BaseModel):
    dimension: Literal["instruction_adherence"]
    score: float           # 0-10
    passing_checks: int
    total_checks: int
    reasoning: str

class LegalVerdict(BaseModel):
    status: Literal["needs_human_review"]   # only value until a rubric exists — do not add PASS/BLOCK here yet
    note: str
```

## `dispatch()` — Track C's per-skill executioner call

Reuses `self_heal.SelfHealLoop` directly, does not reimplement retry logic:

```python
# prism_platform/pipeline/executioner.py (Task 4a)
def make_dispatch_fn(domain: str) -> DispatchFn:
    """Returns a self_heal.DispatchFn: (skill_name, attempt_number) -> bool,
    shelling out to the EXISTING run-audit.sh --skill flag (confirmed live,
    recon item 2) — this is NOT a new subprocess mechanism."""

def make_gate_fn(domain: str, company_name: str, audit_dir: Path) -> GateFn:
    """Returns a self_heal.GateFn: (skill_name) -> GateResult, calling
    gate.gate() and mapping our Verdict -> self_heal.GateResult
    (status=CLEAN|BLOCKED, fatal=True iff block_class==UNFIXABLE per patch #3)."""

def run_full_audit(domain: str, company_name: str, audit_dir: Path) -> tuple[PhaseReport, ...]:
    loop = SelfHealLoop(
        dispatch=make_dispatch_fn(domain),
        gate=make_gate_fn(domain, company_name, audit_dir),
        max_passes=3,   # per patch #4, 3 BLOCKs from the same stage trips NEEDS_HUMAN
        on_attempt=write_module_execution_row,   # persists to module_executions via ModuleExecution model, per attempt
    )
    return loop.run_pipeline(SKILL_NAMES)   # SKILL_NAMES = the 16 confirmed in recon item 5
```

Every subagent building Task 3 (gate) or Task 4a (dispatch) reads this file, not each other's prose. Neither invents its own shape.
