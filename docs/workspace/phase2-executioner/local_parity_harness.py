#!/usr/bin/env python3.13
"""Task 6-local — throwaway harness proving the v3 pipeline (gate.gate() +
llm_stages + claims + db_write) runs END-TO-END for real: real subprocess
mechanical check, real `claude -p` calls for stages 2-4, real INSERT into the
local Postgres `module_executions` table.

Scratch script per docs/workspace/phase2-executioner/task-6-local-brief.md.
NOT part of the production pipeline. Run with:
    .venv/bin/python3.13 docs/workspace/phase2-executioner/local_parity_harness.py [1|2|3|4|all]

Real audit workspaces used: /Users/arijitchowdhury/prism-data/audits/{jbl,lululemon}/
(both already have complete real research output for all 16 skills, per Task 6's brief
item 3 -- no fresh 16-skill research audit is run here).

Interface gotcha found while wiring (see task-6-local-report.md "Findings"):
`gate.py`'s DEFAULT `_default_mechanical_cmd` builds
`factcheck_mechanical.py --audit-dir <SkillOutput.audit_dir> --company <company_name>`,
which requires `audit_dir` to be the PARENT of the company directory (matching
factcheck_mechanical.py's `company_dir = audit_dir/company` resolution). But
`claims.py`'s extractors and `llm_stages.py`'s prompts both read
`SkillOutput.audit_dir` AS THE COMPANY DIRECTORY ITSELF (e.g.
`audit_dir / "research" / "01-company-context.json"`). Both cannot be true of
the same field simultaneously. This harness resolves it by (a) setting
`SkillOutput.audit_dir` to the COMPANY dir (satisfying claims.py/llm_stages.py,
which is the majority convention -- 2 of 3 downstream consumers), and (b)
building an EXPLICIT `mechanical_cmd` using factcheck_mechanical.py's other,
documented "direct" form (`--audit-data <company_dir>/deliverables/*-audit-data.json`),
which needs no separate parent/company split at all. This is exactly the kind
of first-time-wired-together mismatch Task 6 exists to surface.
"""

from __future__ import annotations

import asyncio
import functools
import glob
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from prism_platform.config import settings  # noqa: E402
from prism_platform.pipeline import claims as claims_module  # noqa: E402
from prism_platform.pipeline import db_write  # noqa: E402
from prism_platform.pipeline import gate as gate_module  # noqa: E402
from prism_platform.pipeline import llm_stages  # noqa: E402
from prism_platform.pipeline.chat_agent import _default_claude_cli  # noqa: E402
from prism_platform.pipeline.self_heal import (  # noqa: E402
    Attempt,
    GateResult,
    GateStatus,
    SelfHealLoop,
)

AUDITS_ROOT = Path("/Users/arijitchowdhury/prism-data/audits")
FACTCHECK_MECHANICAL = (
    Path.home() / ".claude/skills/algolia-audit-factcheck/scripts/factcheck_mechanical.py"
)

# FINDING (Task 6): llm_stages.py's default claude_cli_fn (chat_agent._default_claude_cli)
# uses a 120s subprocess timeout. Against a REAL, full audit workspace (not Task 5b's tiny
# smoke-test fixture), `quality_fn`'s prompt -- which tells the model to "read this skill's
# own SKILL.md instructions and the actual output files it produced in the audit directory"
# -- reliably exceeds 120s (bare `claude -p` actually goes and reads multiple real files, it
# doesn't just judge a paragraph handed to it). Confirmed live: this exact call timed out
# twice (Test 1b, Test 4) before this override was added. 300s is a pragmatic bump for this
# harness, not a validated production value -- flagging as a real gap for whoever wires
# engine=v3 into production, not silently working around it uninvestigated.
REAL_WORKSPACE_TIMEOUT_S = 300
_slow_claude_cli = functools.partial(_default_claude_cli, timeout_s=REAL_WORKSPACE_TIMEOUT_S)


def _find_audit_data(company_dir: Path) -> Path | None:
    matches = sorted(glob.glob(str(company_dir / "deliverables" / "*-audit-data.json")))
    return Path(matches[0]) if matches else None


def make_skill_output(
    company_slug: str, company_name: str, skill_name: str
) -> gate_module.SkillOutput:
    return gate_module.SkillOutput(
        skill_name=skill_name,
        domain=f"{company_slug}.com",
        audit_dir=AUDITS_ROOT / company_slug,  # COMPANY dir -- see module docstring gotcha
        company_name=company_name,
    )


def real_mechanical_cmd(skill_output: gate_module.SkillOutput) -> list[str]:
    """The `--audit-data` direct form (factcheck_mechanical.py's own "primary
    form the gate should use") -- sidesteps the audit_dir parent/company-dir
    ambiguity entirely."""
    audit_data = _find_audit_data(skill_output.audit_dir)
    if audit_data is None:
        raise FileNotFoundError(f"no *-audit-data.json under {skill_output.audit_dir}/deliverables")
    return [sys.executable, str(FACTCHECK_MECHANICAL), "--audit-data", str(audit_data)]


async def _persist(
    verdict: gate_module.Verdict | None,
    *,
    domain: str,
    phase: str,
    dispatch_ok: bool = True,
    duration_s: float = 0.0,
) -> str:
    engine = create_async_engine(settings.database_url)
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            attempt = Attempt(
                phase=phase,
                attempt_number=1,
                dispatch_ok=dispatch_ok,
                gate=None,
                started_at=0.0,
                finished_at=duration_s,
            )
            row = await db_write.write_module_execution_row(
                session, audit_id=None, domain=domain, verdict=verdict, attempt=attempt
            )
            return str(row.id)
    finally:
        await engine.dispose()


def persist(verdict: gate_module.Verdict | None, *, domain: str, phase: str, **kw) -> str:
    return asyncio.run(_persist(verdict, domain=domain, phase=phase, **kw))


def print_verdict(label: str, verdict: gate_module.Verdict) -> None:
    print(f"\n=== {label} ===")
    print(
        f"skill={verdict.skill_name} stage={verdict.stage} status={verdict.status.value} "
        f"block_class={verdict.block_class}"
    )
    print(f"findings: {verdict.findings}")
    if verdict.factcheck is not None:
        print(f"factcheck (first): {verdict.factcheck.model_dump()}")
    if verdict.adversarial is not None:
        print(f"adversarial: {verdict.adversarial.model_dump()}")
    if verdict.quality is not None:
        print(f"quality: {verdict.quality.model_dump()}")
    if verdict.legal is not None:
        print(f"legal: {verdict.legal.model_dump()}")


# ---------------------------------------------------------------------------
# Test 1 -- real full 5-stage gate() run, expect a clean PASS.
# ---------------------------------------------------------------------------
def run_test1_pass() -> gate_module.Verdict:
    so = make_skill_output("jbl", "jbl", "algolia-intel-industry")
    t0 = time.monotonic()
    verdict = gate_module.gate(
        so,
        mechanical_cmd=real_mechanical_cmd(so),
        factcheck_fn=llm_stages.make_batch_factcheck_fn(
            claims_module.extract_claims, claude_cli_fn=_slow_claude_cli
        ),
        adversarial_fn=llm_stages.make_batch_adversarial_fn(claude_cli_fn=_slow_claude_cli),
        quality_fn=functools.partial(llm_stages.quality_fn, claude_cli_fn=_slow_claude_cli),
    )
    dt = time.monotonic() - t0
    print_verdict("TEST 1: jbl / algolia-intel-industry (expect real PASS all 5 stages)", verdict)
    row_id = persist(verdict, domain=so.domain, phase=so.skill_name, duration_s=dt)
    print(f"elapsed={dt:.1f}s  DB row id: {row_id}")
    return verdict


# ---------------------------------------------------------------------------
# Test 2 -- real ORGANIC stage-1 mechanical BLOCK (a genuine pre-existing bug
# in lululemon's audit-data.json: tech_stack_summary contradicts populated
# vendor fields). No injection needed -- proves the gate catches real bad
# output, not a synthetic strawman.
# ---------------------------------------------------------------------------
def run_test2_mechanical_block() -> gate_module.Verdict:
    so = make_skill_output("lululemon", "lululemon", "algolia-intel-industry")
    t0 = time.monotonic()
    verdict = gate_module.gate(
        so,
        mechanical_cmd=real_mechanical_cmd(so),
        factcheck_fn=llm_stages.make_batch_factcheck_fn(
            claims_module.extract_claims, claude_cli_fn=_slow_claude_cli
        ),
        adversarial_fn=llm_stages.make_batch_adversarial_fn(claude_cli_fn=_slow_claude_cli),
        quality_fn=functools.partial(llm_stages.quality_fn, claude_cli_fn=_slow_claude_cli),
    )
    dt = time.monotonic() - t0
    print_verdict(
        "TEST 2: lululemon / algolia-intel-industry "
        "(expect real organic stage-1 mechanical BLOCK, zero LLM calls spent)",
        verdict,
    )
    row_id = persist(verdict, domain=so.domain, phase=so.skill_name, duration_s=dt)
    print(f"elapsed={dt:.1f}s  DB row id: {row_id}")
    return verdict


# ---------------------------------------------------------------------------
# Test 3 -- deliberately injected FALSE claim, mechanical stage passes clean
# (jbl), proving stage-2 real LLM factcheck is the one that catches it.
# ---------------------------------------------------------------------------
def run_test3_factcheck_block() -> gate_module.Verdict:
    so = make_skill_output("jbl", "jbl", "algolia-intel-industry")
    fake_claim = (
        "JBL was founded in 1850 in Antarctica and reported $50 trillion in annual "
        "revenue in 2025, making it the single largest company in human history."
    )
    t0 = time.monotonic()
    verdict = gate_module.gate(
        so,
        mechanical_cmd=real_mechanical_cmd(so),
        factcheck_fn=llm_stages.make_batch_factcheck_fn(
            lambda _so: (fake_claim,), claude_cli_fn=_slow_claude_cli
        ),
        adversarial_fn=llm_stages.make_batch_adversarial_fn(claude_cli_fn=_slow_claude_cli),
        quality_fn=functools.partial(llm_stages.quality_fn, claude_cli_fn=_slow_claude_cli),
    )
    dt = time.monotonic() - t0
    print_verdict(
        "TEST 3: jbl + one deliberately injected false claim "
        "(mechanical PASSES clean, expect real stage-2 LLM factcheck BLOCK)",
        verdict,
    )
    row_id = persist(
        verdict, domain=so.domain, phase="algolia-intel-industry-INJECTED-BLOCK-TEST", duration_s=dt
    )
    print(f"elapsed={dt:.1f}s  DB row id: {row_id}")
    return verdict


# ---------------------------------------------------------------------------
# Test 4 -- SelfHealLoop over 2 real jbl skills. `dispatch_fn` is stubbed to
# True (per brief item 3: this reuses the EXISTING complete research output,
# it does not re-run the real 16-skill research/run-audit.sh dispatch, which
# is VPS-only and explicitly out of scope for this local proof). `gate_fn` is
# the REAL wiring: real subprocess mechanical check + real `claude -p` calls
# for factcheck/adversarial/quality, exactly as production would call it.
# ---------------------------------------------------------------------------
def run_test4_self_heal() -> tuple:
    domain = "jbl.com"
    company_name = "jbl"
    verdict_sink: dict[str, gate_module.Verdict] = {}

    def dispatch_fn(skill_name: str, attempt_number: int) -> bool:
        return True

    def gate_fn(skill_name: str) -> GateResult:
        so = make_skill_output("jbl", company_name, skill_name)
        verdict = gate_module.gate(
            so,
            mechanical_cmd=real_mechanical_cmd(so),
            factcheck_fn=llm_stages.make_batch_factcheck_fn(
                claims_module.extract_claims, claude_cli_fn=_slow_claude_cli
            ),
            adversarial_fn=llm_stages.make_batch_adversarial_fn(claude_cli_fn=_slow_claude_cli),
            quality_fn=functools.partial(llm_stages.quality_fn, claude_cli_fn=_slow_claude_cli),
        )
        verdict_sink[skill_name] = verdict
        status = (
            GateStatus.CLEAN
            if verdict.status == gate_module.VerdictStatus.PASS
            else GateStatus.BLOCKED
        )
        return GateResult(
            status=status,
            findings=verdict.findings,
            raw=verdict.mechanical_raw,
            fatal=verdict.block_class == gate_module.BlockClass.UNFIXABLE,
        )

    def on_attempt(attempt: Attempt) -> None:
        verdict = verdict_sink.get(attempt.phase)
        row_id = persist(
            verdict, domain=domain, phase=attempt.phase, dispatch_ok=attempt.dispatch_ok
        )
        print(
            f"  [on_attempt] phase={attempt.phase} attempt={attempt.attempt_number} "
            f"-> DB row {row_id}"
        )

    loop = SelfHealLoop(dispatch=dispatch_fn, gate=gate_fn, max_passes=3, on_attempt=on_attempt)
    t0 = time.monotonic()
    reports = loop.run_pipeline(["algolia-intel-investor", "algolia-intel-company"])
    dt = time.monotonic() - t0
    print("\n=== TEST 4: SelfHealLoop over jbl [algolia-intel-investor, algolia-intel-company] ===")
    for r in reports:
        print(
            f"  phase={r.phase} outcome={r.outcome.value} attempts={len(r.attempts)} "
            f"escalation={r.escalation_reason}"
        )
    print(f"elapsed={dt:.1f}s")
    return reports


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("1", "all"):
        run_test1_pass()
    if which in ("2", "all"):
        run_test2_mechanical_block()
    if which in ("3", "all"):
        run_test3_factcheck_block()
    if which in ("4", "all"):
        run_test4_self_heal()
