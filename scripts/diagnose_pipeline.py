"""Diagnostic script — tests every registered v2 module in wave order, bypassing Temporal.

Usage:
    PERPLEXITY_API_KEY=your-key uv run python scripts/diagnose_pipeline.py nike.com Nike
    PERPLEXITY_API_KEY=your-key uv run python scripts/diagnose_pipeline.py dell.com Dell
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import traceback
from typing import Any

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://prism:prism_dev_password@localhost:5432/prism"
)


async def run_diagnostic(domain: str, company_name: str) -> None:
    from prism_platform.orchestrator.workflows import WAVE_1_INTEL
    from prism_platform.v2.agent_api import AgentAPIClient
    from prism_platform.v2.executor import ModuleExecutor
    from prism_platform.v2.registry import V2_MODULE_REGISTRY, register_all_v2_modules
    from prism_platform.v2.types import ExecutionContextV2

    register_all_v2_modules()

    api_key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not api_key:
        print("ERROR: PERPLEXITY_API_KEY not set")
        sys.exit(1)

    api = AgentAPIClient(api_key=api_key, timeout=120.0)
    executor = ModuleExecutor(agent_api=api)

    context = ExecutionContextV2(
        audit_id="diag-001",
        account_domain=domain,
        company_name=company_name,
    )

    print(f"\n{'='*70}")
    print(f"PRISM v2 Pipeline Diagnostic — {domain} ({company_name})")
    print(f"Registered modules: {len(V2_MODULE_REGISTRY)}")
    print(f"{'='*70}\n")

    # Run Wave 1 modules (the only wave with v2 implementations so far)
    waves = [(1, "INTEL", WAVE_1_INTEL)]

    all_results: dict[str, dict[str, Any]] = {}

    for wave_num, wave_name, wave_modules in waves:
        print(f"\n{'='*70}")
        print(f"WAVE {wave_num}: {wave_name} ({len(wave_modules)} modules)")
        print(f"{'='*70}")

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

                icon = "✓" if result.status == "success" else ("⚠" if result.status == "partial" else "✗")
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
                    print(f"    Output: {non_empty}/{len(keys)} fields populated — {keys[:8]}{'...' if len(keys) > 8 else ''}")

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

    print(f"\n\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for mod_name, res in all_results.items():
        status = res.get("status", "unknown")
        icon = {"success": "✓", "partial": "⚠", "failed": "✗", "crashed": "💥",
                "not_registered": "–", "health_fail": "⚕"}.get(status, "?")
        extra = ""
        if "error" in res:
            extra = f" — {res['error'][:80]}"
        elif "duration_ms" in res:
            extra = f" — {res['duration_ms']}ms, {res['llm_calls']} LLM calls, {res['citations']} citations"
        print(f"  {icon} {mod_name}: {status}{extra}")

    success = sum(1 for r in all_results.values() if r["status"] in ("success", "partial"))
    failed = sum(1 for r in all_results.values() if r["status"] in ("failed", "crashed"))
    skipped = sum(1 for r in all_results.values() if r["status"] in ("not_registered", "health_fail"))
    print(f"\nTotal: {success} passed, {failed} failed, {skipped} skipped / {len(all_results)} attempted")


if __name__ == "__main__":
    domain = sys.argv[1] if len(sys.argv) > 1 else "nike.com"
    company = sys.argv[2] if len(sys.argv) > 2 else "Nike"
    asyncio.run(run_diagnostic(domain, company))
