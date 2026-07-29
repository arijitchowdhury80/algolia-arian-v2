"""Diagnostic script — tests every registered v2 module in wave order, bypassing Temporal.

The research provider comes from settings (``RESEARCH_PROVIDER``, or auto-detected
from the available keys), exactly as it does in the real pipeline — so this script
exercises the same provider production would use.

Exit codes, so a wrapper or CI job cannot read a bad run as green:
  0 = every module produced sourced output
  2 = ran, but some modules returned unsourced (partial) output
  1 = something failed or crashed

Usage:
    uv run python scripts/diagnose_pipeline.py nike.com Nike
    uv run python scripts/diagnose_pipeline.py dell.com Dell
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

# Run the repo's code, not whatever the venv's editable-install map was frozen
# with at install time — that map does not include modules added since, so a
# stale copy would be silently diagnosed instead of the working tree.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://prism:prism_dev_password@localhost:5432/prism"
)


async def run_diagnostic(domain: str, company_name: str) -> int:
    """Run every Wave-1 module. Returns the process exit code.

    0 = every module produced sourced output, 2 = ran but some output is
    unsourced, 1 = something failed, crashed, or nothing ran.
    """
    from prism_platform.orchestrator.workflows import WAVE_1_INTEL
    from prism_platform.v2.executor import ModuleExecutor
    from prism_platform.v2.registry import V2_MODULE_REGISTRY, register_all_v2_modules
    from prism_platform.v2.research_client import (
        ResearchProviderError,
        make_research_client,
        resolve_research_provider,
    )
    from prism_platform.v2.types import ExecutionContextV2

    register_all_v2_modules()

    try:
        provider = resolve_research_provider()
        api = make_research_client(timeout=120.0)
    except ResearchProviderError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    print(f"Research provider: {provider}")
    executor = ModuleExecutor(agent_api=api)

    context = ExecutionContextV2(
        audit_id="diag-001",
        account_domain=domain,
        company_name=company_name,
    )

    print(f"\n{'=' * 70}")
    print(f"PRISM v2 Pipeline Diagnostic — {domain} ({company_name})")
    print(f"Registered modules: {len(V2_MODULE_REGISTRY)}")
    print(f"{'=' * 70}\n")

    # Run Wave 1 modules (the only wave with v2 implementations so far)
    waves = [(1, "INTEL", WAVE_1_INTEL)]

    all_results: dict[str, dict[str, Any]] = {}

    for wave_num, wave_name, wave_modules in waves:
        print(f"\n{'=' * 70}")
        print(f"WAVE {wave_num}: {wave_name} ({len(wave_modules)} modules)")
        print(f"{'=' * 70}")

        wave_pass = True

        for mod_name in wave_modules:
            handle = V2_MODULE_REGISTRY.get(mod_name)
            if not handle:
                print(f"\n  [{mod_name}] NOT REGISTERED — SKIP")
                all_results[mod_name] = {"status": "not_registered"}
                continue

            healthy = await handle.health_check()
            if not healthy:
                print(f"  [{mod_name}] HEALTH CHECK FAILED")
                all_results[mod_name] = {"status": "health_fail"}
                wave_pass = False
                continue

            start = time.monotonic()
            try:
                result = await executor.execute(
                    config=handle.config,
                    context=context,
                    output_schema=handle.output_schema,
                    playbook_path=handle.playbook_path,
                )
                elapsed_ms = int((time.monotonic() - start) * 1000)

                icon = (
                    "✓"
                    if result.status == "success"
                    else ("⚠" if result.status == "partial" else "✗")
                )
                print(
                    f"\n  [{mod_name}] {icon} status={result.status} "
                    f"duration={elapsed_ms}ms llm_calls={result.llm_calls} "
                    f"citations={len(result.citations)} claims={len(result.claims)}"
                )

                if result.errors:
                    print(f"    ERRORS: {result.errors}")

                if isinstance(result.output, dict):
                    keys = list(result.output.keys())
                    non_empty = sum(1 for v in result.output.values() if v)
                    more = "..." if len(keys) > 8 else ""
                    print(
                        f"    Output: {non_empty}/{len(keys)} fields populated — {keys[:8]}{more}"
                    )

                all_results[mod_name] = {
                    "status": result.status,
                    "duration_ms": elapsed_ms,
                    "llm_calls": result.llm_calls,
                    "citations": len(result.citations),
                    "claims": len(result.claims),
                    "errors": result.errors,
                }

                if result.status == "failed":
                    wave_pass = False

            except Exception as exc:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                print(f"  [{mod_name}] ✗ CRASHED after {elapsed_ms}ms: {type(exc).__name__}: {exc}")
                traceback.print_exc()
                all_results[mod_name] = {"status": "crashed", "error": str(exc)}
                wave_pass = False

        print(f"\n  Wave {wave_num} result: {'PASS' if wave_pass else 'FAIL'}")

        if wave_num == 1:
            ic = all_results.get("intel-company", {}).get("status", "not_run")
            if ic not in ("success", "partial"):
                print(f"\n  *** GATE FAIL: intel-company={ic} — aborting ***")
                break

    print(f"\n\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    for mod_name, res in all_results.items():
        status = res.get("status", "unknown")
        icon = {
            "success": "✓",
            "partial": "⚠",
            "failed": "✗",
            "crashed": "💥",
            "not_registered": "–",
            "health_fail": "⚕",
        }.get(status, "?")
        extra = ""
        if "error" in res:
            extra = f" — {res['error'][:80]}"
        elif "duration_ms" in res:
            extra = (
                f" — {res['duration_ms']}ms, {res['llm_calls']} LLM calls, "
                f"{res['citations']} citations"
            )
        print(f"  {icon} {mod_name}: {status}{extra}")

    # Count "partial" separately. It used to be lumped in with success, which
    # reported "13 passed" for a run where 4 modules produced unsourced output —
    # the same false-green this pipeline is supposed to prevent.
    sourced = sum(1 for r in all_results.values() if r["status"] == "success")
    unsourced = sum(1 for r in all_results.values() if r["status"] == "partial")
    failed = sum(1 for r in all_results.values() if r["status"] in ("failed", "crashed"))
    skipped = sum(
        1 for r in all_results.values() if r["status"] in ("not_registered", "health_fail")
    )
    print(
        f"\nTotal {len(all_results)} attempted: {sourced} sourced, "
        f"{unsourced} UNSOURCED (partial), {failed} failed, {skipped} skipped"
    )
    if unsourced:
        print(
            f"  ⚠ {unsourced} module(s) returned no sources after a retry. Their output is "
            "unverified and must not be presented as evidenced."
        )

    await api.close()
    if failed or sourced == 0:
        return 1
    return 2 if unsourced else 0


if __name__ == "__main__":
    domain = sys.argv[1] if len(sys.argv) > 1 else "nike.com"
    company = sys.argv[2] if len(sys.argv) > 2 else "Nike"
    # 0 = every module sourced, 2 = ran but some output unsourced, 1 = something failed.
    sys.exit(asyncio.run(run_diagnostic(domain, company)))
