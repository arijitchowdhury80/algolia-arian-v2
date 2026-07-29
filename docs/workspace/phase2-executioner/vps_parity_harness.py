#!/usr/bin/env python3
"""Task 6 — VPS parity run. Proves the v3 pipeline (real per-skill dispatch
via run-audit.sh --skill + gate.gate() + llm_stages + claims + db_write) runs
END-TO-END FOR REAL on the VPS: real `run-audit.sh --skill <name>` subprocess
dispatch (not stubbed True, unlike Task 6-local's Test 4), real `claude -p`
calls for gate stages 2-4, real INSERT into the VPS's real Postgres
`module_executions` table.

Company: jbl (RE-RUN of an existing, already-fully-audited company, not a
fresh company). Chosen over a fresh company because gate()'s default
mechanical_cmd (Task 6d's fix) resolves `deliverables/*-audit-data.json`
under `audit_dir` -- that file is only produced by `algolia-audit-report`,
the second-to-last skill in the 16-skill pipeline. A fresh company's early
skills (techstack, industry, ...) have no audit-data.json yet, so gate()'s
DEFAULT wiring would raise FileNotFoundError before ever reaching stage 2 --
not a bug in this harness, a real precondition of gate()'s current design
worth flagging (see task-6-report.md Findings). Re-running 2 already-audited
skills for jbl (whose audit-data.json already exists) lets gate()'s TRUE
DEFAULT `mechanical_cmd_fn=None` path run un-worked-around, which is exactly
what Task 6d's fix was supposed to unlock.

Safety: re-running a research skill for jbl only rewrites
audits/jbl/research/<file> on the HOST. It does NOT call publish_to_store()
or touch /root/.hermes-prism/reports/jbl/ (the live-published content
prism.chowmes.com/jbl actually serves) -- this harness only calls
`executioner.make_dispatch_fn` + `executioner.make_gate_fn` directly, never
`prism-runner.py`'s `run_job`/publish path. Confirmed no publish call exists
in this file.

Run with (as chowmesadmin, on the VPS, with .claude-oauth.env + DATABASE_URL
sourced into the shell -- see run-vps-parity.sh):
    /opt/prism-platform/.venv/bin/python3 vps_parity_harness.py [1|2|3|all]
"""

from __future__ import annotations

import asyncio
import functools
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path("/opt/prism-platform")
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from prism_platform.config import settings  # noqa: E402
from prism_platform.pipeline import claims as claims_module  # noqa: E402
from prism_platform.pipeline import db_write  # noqa: E402
from prism_platform.pipeline import executioner  # noqa: E402
from prism_platform.pipeline import gate as gate_module  # noqa: E402
from prism_platform.pipeline import llm_stages  # noqa: E402
from prism_platform.pipeline.chat_agent import _default_claude_cli  # noqa: E402
from prism_platform.pipeline.self_heal import Attempt, SelfHealLoop  # noqa: E402

DOMAIN = "jbl.com"
SLUG = "jbl"
COMPANY_NAME = "JBL"
AUDIT_DIR = Path("/opt/prism-executor/audits") / SLUG

REAL_WORKSPACE_TIMEOUT_S = 300
_slow_claude_cli = functools.partial(_default_claude_cli, timeout_s=REAL_WORKSPACE_TIMEOUT_S)


async def _persist(verdict, *, domain, phase, dispatch_ok=True, duration_s=0.0):
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


def persist(verdict, *, domain, phase, **kw) -> str:
    return asyncio.run(_persist(verdict, domain=domain, phase=phase, **kw))


def print_verdict(label: str, verdict: gate_module.Verdict) -> None:
    print(f"\n=== {label} ===")
    print(
        f"skill={verdict.skill_name} stage={verdict.stage} status={verdict.status.value} "
        f"block_class={verdict.block_class}"
    )
    print(f"findings: {verdict.findings}")
    if verdict.factcheck is not None:
        print(f"factcheck: {verdict.factcheck.model_dump()}")
    if verdict.adversarial is not None:
        print(f"adversarial: {verdict.adversarial.model_dump()}")
    if verdict.quality is not None:
        print(f"quality: {verdict.quality.model_dump()}")


def snapshot_ps(label: str) -> None:
    """Snapshot ps aux for skill/claude subprocesses -- proves N separate
    dispatches, not one long-lived process (Task 6 DoD line 2)."""
    out = subprocess.run(
        ["ps", "-eo", "pid,ppid,etimes,cmd"], capture_output=True, text=True, check=False
    ).stdout
    lines = [
        line
        for line in out.splitlines()
        if ("run-audit.sh" in line or ("claude" in line and "-p" in line)) and "grep" not in line
    ]
    print(f"\n--- ps aux snapshot ({label}) ---")
    print("\n".join(lines) if lines else "(no matching process at this instant)")


def run_one_real_skill_through_gate(skill_name: str, tag: str = "") -> gate_module.Verdict:
    """Real dispatch (run-audit.sh --skill <skill_name> for jbl) + real gate()
    with real llm_stages/claims wiring, per the brief's exact instruction."""
    dispatch = executioner.make_dispatch_fn(DOMAIN)
    t0 = time.monotonic()
    print(f"\n>>> DISPATCHING real skill: {skill_name} (domain={DOMAIN}) ...")
    ok = dispatch(skill_name, 1)
    dispatch_dt = time.monotonic() - t0
    print(f">>> dispatch_fn returned ok={ok} after {dispatch_dt:.1f}s")

    verdict_sink: dict[str, gate_module.Verdict] = {}
    gate_fn = executioner.make_gate_fn(
        DOMAIN,
        COMPANY_NAME,
        AUDIT_DIR,
        factcheck_fn=llm_stages.make_batch_factcheck_fn(
            claims_module.extract_claims, claude_cli_fn=_slow_claude_cli
        ),
        adversarial_fn=llm_stages.make_batch_adversarial_fn(claude_cli_fn=_slow_claude_cli),
        quality_fn=functools.partial(llm_stages.quality_fn, claude_cli_fn=_slow_claude_cli),
        verdict_sink=verdict_sink,
    )
    t1 = time.monotonic()
    gate_result = gate_fn(skill_name)
    gate_dt = time.monotonic() - t1
    verdict = verdict_sink[skill_name]
    print_verdict(f"REAL VPS RUN: jbl / {skill_name} {tag}", verdict)
    row_id = persist(
        verdict,
        domain=DOMAIN,
        phase=skill_name,
        dispatch_ok=ok,
        duration_s=dispatch_dt + gate_dt,
    )
    print(
        f"dispatch={dispatch_dt:.1f}s gate={gate_dt:.1f}s total={dispatch_dt + gate_dt:.1f}s "
        f"DB row id: {row_id}  gate_result.status={gate_result.status} fatal={gate_result.fatal}"
    )
    return verdict


def run_self_heal_two_skills() -> list:
    """Real SelfHealLoop over 2 real skills, real dispatch, real gate -- the
    actual production shape (executioner.make_dispatch_fn +
    executioner.make_gate_fn), not the stubbed dispatch_fn=True Task 6-local
    used. on_attempt persists every attempt to module_executions."""
    verdict_sink: dict[str, gate_module.Verdict] = {}
    dispatch_fn = executioner.make_dispatch_fn(DOMAIN)
    gate_fn = executioner.make_gate_fn(
        DOMAIN,
        COMPANY_NAME,
        AUDIT_DIR,
        factcheck_fn=llm_stages.make_batch_factcheck_fn(
            claims_module.extract_claims, claude_cli_fn=_slow_claude_cli
        ),
        adversarial_fn=llm_stages.make_batch_adversarial_fn(claude_cli_fn=_slow_claude_cli),
        quality_fn=functools.partial(llm_stages.quality_fn, claude_cli_fn=_slow_claude_cli),
        verdict_sink=verdict_sink,
    )

    def on_attempt(attempt: Attempt) -> None:
        snapshot_ps(f"on_attempt phase={attempt.phase} attempt={attempt.attempt_number}")
        verdict = verdict_sink.get(attempt.phase)
        row_id = persist(verdict, domain=DOMAIN, phase=attempt.phase, dispatch_ok=attempt.dispatch_ok)
        print(f"  [on_attempt] phase={attempt.phase} attempt={attempt.attempt_number} -> DB row {row_id}")

    loop = SelfHealLoop(dispatch=dispatch_fn, gate=gate_fn, max_passes=2, on_attempt=on_attempt)
    t0 = time.monotonic()
    reports = loop.run_pipeline(["algolia-intel-techstack", "algolia-intel-industry"])
    dt = time.monotonic() - t0
    print("\n=== SELF-HEAL: jbl [algolia-intel-techstack, algolia-intel-industry] REAL dispatch+gate ===")
    for r in reports:
        print(f"  phase={r.phase} outcome={r.outcome.value} attempts={len(r.attempts)} escalation={r.escalation_reason}")
    print(f"elapsed={dt:.1f}s")
    return reports


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("selfheal", "all"):
        run_self_heal_two_skills()
    if which == "techstack":
        run_one_real_skill_through_gate("algolia-intel-techstack")
    if which == "industry":
        run_one_real_skill_through_gate("algolia-intel-industry")
