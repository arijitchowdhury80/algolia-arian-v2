"""Diagnostic script: tests every module in wave order, bypassing Temporal.

Usage: .venv/bin/python scripts/diagnose_pipeline.py jewson.co.uk Jewson
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import traceback
from typing import Any

# Must be set before imports that read env
import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://prism:prism_dev_password@localhost:5432/prism")


async def run_diagnostic(domain: str, company_name: str) -> None:
    from prism_platform.core.registry import register_all_modules, MODULE_REGISTRY
    from prism_platform.core.module import ExecutionContext
    from prism_platform.orchestrator.workflows import (
        WAVE_1_INTEL, WAVE_2_BROWSER, WAVE_3_SYNTHESIS,
        WAVE_4_ACTIVATION, WAVE_5_FACTCHECK, WAVE_6_INSIGHTS,
    )

    register_all_modules()
    print(f"\n{'='*70}")
    print(f"PRISM Pipeline Diagnostic — {domain} ({company_name})")
    print(f"Registered modules: {len(MODULE_REGISTRY)}")
    print(f"{'='*70}\n")

    context = ExecutionContext(
        audit_id="diag-001",
        account_id="",
        domain=domain,
        company_name=company_name,
    )

    waves = [
        (1, "INTEL", WAVE_1_INTEL),
        (2, "BROWSER", WAVE_2_BROWSER),
        (3, "SYNTHESIS", WAVE_3_SYNTHESIS),
        (4, "ACTIVATION", WAVE_4_ACTIVATION),
        (5, "FACTCHECK", WAVE_5_FACTCHECK),
        (6, "INSIGHTS", WAVE_6_INSIGHTS),
    ]

    all_results: dict[str, dict[str, Any]] = {}
    wave_statuses: dict[int, str] = {}

    for wave_num, wave_name, wave_modules in waves:
        print(f"\n{'='*70}")
        print(f"WAVE {wave_num}: {wave_name} ({len(wave_modules)} modules)")
        print(f"{'='*70}")

        wave_pass = True

        for mod_name in wave_modules:
            module = MODULE_REGISTRY.get(mod_name)
            if not module:
                print(f"\n  [{mod_name}] NOT REGISTERED — SKIP")
                all_results[mod_name] = {"status": "not_registered"}
                wave_pass = False
                continue

            print(f"\n  [{mod_name}] deps={module.dependencies}")

            # Check if dependencies succeeded
            missing_deps = []
            for dep in module.dependencies:
                dep_result = all_results.get(dep, {})
                dep_status = dep_result.get("status", "not_run")
                if dep_status not in ("success", "partial"):
                    missing_deps.append(f"{dep}={dep_status}")

            if missing_deps:
                print(f"  [{mod_name}] SKIPPED — missing deps: {missing_deps}")
                all_results[mod_name] = {"status": "skipped_deps", "missing": missing_deps}
                wave_pass = False
                continue

            # Health check
            try:
                healthy = await module.health_check()
                if not healthy:
                    print(f"  [{mod_name}] HEALTH CHECK FAILED")
                    all_results[mod_name] = {"status": "health_fail"}
                    wave_pass = False
                    continue
            except Exception as e:
                print(f"  [{mod_name}] HEALTH CHECK ERROR: {e}")
                all_results[mod_name] = {"status": "health_error", "error": str(e)}
                wave_pass = False
                continue

            # Execute
            start = time.monotonic()
            try:
                result = await module.execute(context)
                elapsed = time.monotonic() - start

                status_icon = "✓" if result.status == "success" else ("⚠" if result.status == "partial" else "✗")
                print(f"  [{mod_name}] {status_icon} status={result.status} "
                      f"duration={result.duration_ms}ms llm_calls={result.llm_calls} "
                      f"sources={len(result.sources)}")

                if result.errors:
                    print(f"    ERRORS: {result.errors}")
                if result.warnings:
                    print(f"    WARNINGS: {result.warnings}")

                # Show key output fields
                output = result.output
                if isinstance(output, dict):
                    keys = list(output.keys())
                    print(f"    Output keys ({len(keys)}): {keys[:10]}{'...' if len(keys) > 10 else ''}")
                    # Show non-empty field count
                    non_empty = sum(1 for v in output.values() if v)
                    print(f"    Non-empty fields: {non_empty}/{len(keys)}")

                # Validate
                try:
                    validation = await module.validate(result)
                    v_icon = "✓" if validation.passed else "✗"
                    print(f"    Validation: {v_icon} ({validation.checks_passed}/{validation.checks_run})")
                    if validation.errors:
                        print(f"    Validation errors: {validation.errors}")
                except Exception as ve:
                    print(f"    Validation CRASHED: {ve}")

                all_results[mod_name] = {
                    "status": result.status,
                    "duration_ms": result.duration_ms,
                    "llm_calls": result.llm_calls,
                    "sources": len(result.sources),
                    "errors": result.errors,
                    "output_keys": list(output.keys()) if isinstance(output, dict) else [],
                }

                if result.status == "failed":
                    wave_pass = False

            except Exception as e:
                elapsed = time.monotonic() - start
                print(f"  [{mod_name}] ✗ CRASHED after {elapsed:.1f}s: {type(e).__name__}: {e}")
                traceback.print_exc()
                all_results[mod_name] = {"status": "crashed", "error": str(e)}
                wave_pass = False

        wave_statuses[wave_num] = "PASS" if wave_pass else "FAIL"
        print(f"\n  Wave {wave_num} result: {wave_statuses[wave_num]}")

        # Gate check: if intel-company failed, abort
        if wave_num == 1:
            ic_status = all_results.get("intel-company", {}).get("status", "not_run")
            if ic_status not in ("success", "partial"):
                print(f"\n  *** GATE FAIL: intel-company={ic_status} — would abort in production ***")
                break

    # Summary
    print(f"\n\n{'='*70}")
    print("DIAGNOSTIC SUMMARY")
    print(f"{'='*70}")
    print(f"\nWave Results:")
    for wn, ws in wave_statuses.items():
        print(f"  Wave {wn}: {ws}")

    print(f"\nModule Results:")
    for mod_name, mod_res in all_results.items():
        status = mod_res.get("status", "unknown")
        icon = {"success": "✓", "partial": "⚠", "failed": "✗", "crashed": "💥"}.get(status, "?")
        extra = ""
        if "missing" in mod_res:
            extra = f" (missing deps: {mod_res['missing']})"
        elif "error" in mod_res:
            extra = f" (error: {mod_res['error'][:80]})"
        elif "duration_ms" in mod_res:
            extra = f" ({mod_res['duration_ms']}ms, {mod_res.get('llm_calls', 0)} LLM calls)"
        print(f"  {icon} {mod_name}: {status}{extra}")

    # Count
    success = sum(1 for r in all_results.values() if r["status"] in ("success", "partial"))
    failed = sum(1 for r in all_results.values() if r["status"] in ("failed", "crashed"))
    skipped = sum(1 for r in all_results.values() if r["status"].startswith("skipped"))
    print(f"\nTotal: {success} passed, {failed} failed, {skipped} skipped out of {len(all_results)}")


if __name__ == "__main__":
    domain = sys.argv[1] if len(sys.argv) > 1 else "jewson.co.uk"
    company = sys.argv[2] if len(sys.argv) > 2 else "Jewson"
    asyncio.run(run_diagnostic(domain, company))
