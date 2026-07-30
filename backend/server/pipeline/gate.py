"""Track G — the 5-stage `gate()` verification pipeline.

Every skill's output passes through `gate()` before the self-heal loop
(server/pipeline/self_heal.py) decides whether to retry or move on.
See docs/workspace/phase2-executioner/interface-contract.md — this file
implements that contract's shapes verbatim; do not invent a different one.

Stages run in order and short-circuit on the first BLOCK:
  1. Mechanical  -- factcheck_mechanical.py via self_heal.subprocess_gate().
  2. Factcheck   -- LLM judgment against the evidence-tier system, schema-
                     constrained to verdicts.FactCheckVerdict.
  3. Adversarial -- N=3-voter panel, but ONLY on claims stage 1/2 flagged as
                     risky (patch #1) -- not every claim in every skill.
  4. Quality     -- algolia-audit-eval Dimension 3 (instruction adherence).
  5. Legal       -- patch #8 stub: ALWAYS needs_human_review, never an
                     automated PASS/BLOCK. No rubric exists yet.

Stages 2-4 are LLM-backed. This module does not make a live API call inline
-- that is Task 4/5's wiring concern. Instead each stage takes an injectable
callable (same dependency-injection pattern as self_heal.py's
`dispatch`/`gate` params) so the stage *decision logic* is fully unit-
testable today against fake/stub LLM responses. `gate()` raises
NotImplementedError if a stage's callable is required (there's something to
judge) but was not supplied -- that is a deliberate, loud failure so nobody
mistakes an unwired stage for an auto-PASS.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from server.pipeline.self_heal import GateStatus, subprocess_gate
from server.pipeline.verdicts import (
    AdversarialVerdict,
    FactCheckVerdict,
    LegalVerdict,
    QualityScore,
)

# ---------------------------------------------------------------------------
# Contract shapes (docs/workspace/phase2-executioner/interface-contract.md)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillOutput:
    """What one skill produced, addressed by file path (factcheck_mechanical.py
    is file-based, not value-based) rather than by an in-memory payload."""

    skill_name: str  # one of the 16 SKILL_NAMES in prism-runner.py
    domain: str  # e.g. "belk.com"
    audit_dir: Path  # $ALGOLIA_AUDIT_DIR/{CompanyName}/
    company_name: str  # factcheck_mechanical.py's --company arg


class VerdictStatus(str, Enum):
    PASS = "pass"
    BLOCK = "block"


class BlockClass(str, Enum):  # patch #3
    RETRY_WORTHY = "retry_worthy"  # schema/format drift, transient -- safe to re-dispatch
    UNFIXABLE = "unfixable"  # data genuinely absent / contradicted -- NEEDS_HUMAN, no retry


@dataclass(frozen=True)
class Verdict:
    skill_name: str
    stage: int  # 1-5 -- the stage that produced this verdict (patch #4: "same
    # check" for the 3-strike kill condition means same STAGE, not same claim)
    status: VerdictStatus
    block_class: BlockClass | None  # set only when status == BLOCK
    findings: tuple[str, ...]
    mechanical_raw: str = ""  # stdout/stderr of factcheck_mechanical.py, stage 1
    factcheck: FactCheckVerdict | None = None  # stage 2
    adversarial: AdversarialVerdict | None = None  # stage 3
    quality: QualityScore | None = None  # stage 4
    legal: LegalVerdict | None = None  # stage 5


# ---------------------------------------------------------------------------
# Injectable LLM call points -- stage 2/3/4's "LlmCallFn" dependency
# injection, same pattern as self_heal.SelfHealLoop's dispatch/gate params.
# Each returns already schema-validated Pydantic verdict object(s); this
# module's job is deciding PASS/BLOCK/block_class from their fields, not
# performing the LLM call or the JSON-schema enforcement itself.
# ---------------------------------------------------------------------------

FactCheckFn = Callable[[SkillOutput], tuple[FactCheckVerdict, ...]]
AdversarialFn = Callable[[SkillOutput, tuple[str, ...]], tuple[AdversarialVerdict, ...]]
QualityFn = Callable[[SkillOutput], QualityScore]

DEFAULT_QUALITY_PASS_THRESHOLD = 7.0

# Local checkout of the shared skill script (also deployed at
# ~/.claude/skills/algolia-audit-factcheck/scripts/factcheck_mechanical.py on
# the VPS -- see docs/workspace/phase2-executioner/task-1-recon-report.md
# item 4). Callers can override via `mechanical_cmd` (tests always do, so
# unit tests never depend on this real path existing).
FACTCHECK_MECHANICAL_PATH = (
    Path.home() / ".claude/skills/algolia-audit-factcheck/scripts/factcheck_mechanical.py"
)


def _weak_evidence_tier(verdict: FactCheckVerdict) -> bool:
    """A claim is 'risky' for stage 3 purposes if its evidence tier is weaker
    than AUTHENTIC -- even a claim that stage 2 marked SUPPORTED is worth a
    second, adversarial look if the only evidence is a web search."""
    return verdict.evidence_tier in ("WEBSEARCH", "NO_SOURCE")


def find_audit_data_json(audit_dir: Path) -> Path | None:
    """Locate `{slug}-audit-data.json` under `audit_dir/deliverables/`.

    Shared by this module's default mechanical-command builder and
    `claims.py`'s extractors -- both need the same real, drifted file-naming
    convention resolved the same way (the slug is NOT a reliable
    slugification of `company_name`; confirmed against real audits:
    "British Airways" -> `british-airways-audit-data.json`, "Michael Kors"
    -> `michaelkors-audit-data.json`, no hyphen). Glob for it instead of
    computing a guessed slug. Returns None (not an error) if no
    `deliverables/` directory or no match exists yet -- callers decide
    whether that is fatal.
    """
    deliverables_dir = audit_dir / "deliverables"
    if not deliverables_dir.is_dir():
        return None
    matches = sorted(deliverables_dir.glob("*-audit-data.json"))
    return matches[0] if matches else None


def _default_mechanical_cmd(skill_output: SkillOutput) -> Sequence[str]:
    """Build the real `factcheck_mechanical.py --audit-data <path>` form.

    `SkillOutput.audit_dir` means "the company's own directory" everywhere
    else in this pipeline (`claims.py`'s extractors, `llm_stages.py`'s
    prompts) -- the old `--audit-dir <parent> --company <name>` form
    required `audit_dir` to be the PARENT of the company directory instead,
    a real interface mismatch caught wiring these modules together for the
    first time (docs/workspace/phase2-executioner/task-6-local-report.md
    Findings #1). `--audit-data <path>` needs no parent/company split at
    all, so it is consistent with the other 2 (majority) consumers.
    """
    audit_data_path = find_audit_data_json(skill_output.audit_dir)
    if audit_data_path is None:
        raise FileNotFoundError(
            f"gate()'s default mechanical command needs a real "
            f"deliverables/*-audit-data.json file under "
            f"{skill_output.audit_dir} for skill {skill_output.skill_name!r} "
            f"-- none found. Pass an explicit mechanical_cmd if this skill "
            f"legitimately runs before the audit-report deliverable exists."
        )
    return [
        sys.executable,
        str(FACTCHECK_MECHANICAL_PATH),
        "--audit-data",
        str(audit_data_path),
    ]


def gate(
    skill_output: SkillOutput,
    *,
    mechanical_cmd: Sequence[str] | None = None,
    factcheck_fn: FactCheckFn | None = None,
    adversarial_fn: AdversarialFn | None = None,
    quality_fn: QualityFn | None = None,
    quality_pass_threshold: float = DEFAULT_QUALITY_PASS_THRESHOLD,
) -> Verdict:
    """Run all 5 verification stages against one skill's output, in order,
    short-circuiting on the first non-PASS stage. Returns one Verdict.

    `mechanical_cmd`/`factcheck_fn`/`adversarial_fn`/`quality_fn` are the
    dependency-injection seams for stages 1-4. In production (Task 4/5) they
    are supplied by real wiring (a subprocess command, real LLM calls); in
    tests they are fakes/stubs. If a stage needs a callable that wasn't
    supplied, `gate()` raises NotImplementedError rather than silently
    treating the stage as PASS.
    """
    skill = skill_output.skill_name

    # ---- Stage 1: mechanical -------------------------------------------------
    cmd = mechanical_cmd if mechanical_cmd is not None else _default_mechanical_cmd(skill_output)
    mechanical_gate_fn = subprocess_gate(cmd)
    mech_result = mechanical_gate_fn(skill)

    if mech_result.status != GateStatus.CLEAN:
        # Both BLOCKED (exit 2, schema/format drift) and ERROR (fail-closed --
        # any other exit code, e.g. a crash) are treated as retry-worthy at
        # this stage: neither implies the underlying data is contradicted or
        # absent, only that the mechanical check didn't come back clean.
        return Verdict(
            skill_name=skill,
            stage=1,
            status=VerdictStatus.BLOCK,
            block_class=BlockClass.RETRY_WORTHY,
            findings=mech_result.findings or (mech_result.raw,),
            mechanical_raw=mech_result.raw,
        )

    # ---- Stage 2: factcheck ---------------------------------------------------
    if factcheck_fn is None:
        raise NotImplementedError(
            f"gate() stage 2 (factcheck) requires factcheck_fn for skill "
            f"{skill!r} -- real LLM wiring is Task 4/5's concern, not stage logic."
        )
    factcheck_verdicts = factcheck_fn(skill_output)
    for fc in factcheck_verdicts:
        if fc.verdict in ("CONTRADICTED", "UNSUPPORTED"):
            return Verdict(
                skill_name=skill,
                stage=2,
                status=VerdictStatus.BLOCK,
                block_class=BlockClass.UNFIXABLE,
                findings=(f"{fc.verdict}: {fc.claim} -- {fc.reasoning}",),
                mechanical_raw=mech_result.raw,
                factcheck=fc,
            )

    # ---- Stage 3: adversarial panel (patch #1 -- risky claims only) ----------
    risky_claims = tuple(fc.claim for fc in factcheck_verdicts if _weak_evidence_tier(fc))
    if risky_claims:
        if adversarial_fn is None:
            raise NotImplementedError(
                f"gate() stage 3 (adversarial) requires adversarial_fn for skill "
                f"{skill!r} -- {len(risky_claims)} risky claim(s) flagged, real LLM "
                f"wiring is Task 4/5's concern, not stage logic."
            )
        adversarial_verdicts = adversarial_fn(skill_output, risky_claims)
        for av in adversarial_verdicts:
            if not av.survives:
                return Verdict(
                    skill_name=skill,
                    stage=3,
                    status=VerdictStatus.BLOCK,
                    block_class=BlockClass.UNFIXABLE,
                    findings=(f"adversarial panel refuted: {av.claim}",),
                    mechanical_raw=mech_result.raw,
                    adversarial=av,
                )

    # ---- Stage 4: quality (instruction adherence) -----------------------------
    if quality_fn is None:
        raise NotImplementedError(
            f"gate() stage 4 (quality) requires quality_fn for skill "
            f"{skill!r} -- real LLM wiring is Task 4/5's concern, not stage logic."
        )
    quality = quality_fn(skill_output)
    if quality.score < quality_pass_threshold:
        return Verdict(
            skill_name=skill,
            stage=4,
            status=VerdictStatus.BLOCK,
            block_class=BlockClass.RETRY_WORTHY,
            findings=(
                f"quality score {quality.score} below threshold "
                f"{quality_pass_threshold} ({quality.passing_checks}/{quality.total_checks} "
                f"checks passing): {quality.reasoning}",
            ),
            mechanical_raw=mech_result.raw,
            quality=quality,
        )

    # ---- Stage 5: legal (patch #8 -- stub, no rubric, never auto-judges) -----
    # Intentional: do not "improve" this into real PASS/BLOCK logic. The gate
    # still reaches stage 5 and records the stub so the DB row and report
    # surface carry it, but the actual legal judgment is manual-Arijit-only
    # until a rubric exists. Because LegalVerdict has no PASS/BLOCK value,
    # reaching stage 5 always yields an overall PASS at the automated-gate
    # level -- a human reviewing the persisted `legal` field is a separate,
    # out-of-band step from this retry loop.
    legal = LegalVerdict(
        status="needs_human_review",
        note="No legal rubric exists yet (patch #8) -- automated gate cannot judge this stage.",
    )
    return Verdict(
        skill_name=skill,
        stage=5,
        status=VerdictStatus.PASS,
        block_class=None,
        findings=(),
        mechanical_raw=mech_result.raw,
        factcheck=factcheck_verdicts[0] if factcheck_verdicts else None,
        quality=quality,
        legal=legal,
    )
