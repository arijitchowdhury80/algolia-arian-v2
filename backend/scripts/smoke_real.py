"""Real-company smoke test — no Postgres, no Temporal.

Runs intel-company Track 1 (Scout browser) + Track 2 (Perplexity),
then intel-competitors Track 1 (search vendor detector).

Usage:
    uv run python scripts/smoke_real.py [domain]

Defaults to nike.com if no domain given.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import structlog

from core.config import settings
from core.types import ExecutionContextV2
from prism_platform.v2.modules.intel_company.fetcher import fetch_all_company_pages
from prism_platform.v2.modules.intel_competitors.collector import (
    collect as intel_competitors_collect,
)

log = structlog.get_logger("smoke")


async def main(domain: str) -> None:
    print(f"\n{'='*60}")
    print(f"SMOKE TEST — {domain}")
    print(f"{'='*60}\n")

    # ── Context ────────────────────────────────────────────────────────
    context = ExecutionContextV2(
        audit_id="smoke-001",
        account_domain=domain,
        company_name=domain.split(".")[0].title(),
        upstream_results={},
    )

    # ── Track 1A: intel-company Scout fetch ───────────────────────────
    print("[T1] intel-company — fetching pages via Scout...")
    scout_url = getattr(settings, "scout_url", "http://localhost:8421")
    scout_key = getattr(settings, "scout_api_key", "dev-key")
    print(f"     Scout URL: {scout_url}")
    print(f"     Scout key: {scout_key[:8]}...")

    try:
        pages = await fetch_all_company_pages(domain)
        fetched = {k: v for k, v in pages.items() if v}
        print(f"     Pages fetched: {len(fetched)}/{len(pages)}")
        for page_type, content in pages.items():
            status = "ok" if content else "empty"
            print(f"       {status}  {page_type}  ({len(content)} chars)")
    except Exception as exc:
        print(f"     [WARN] fetch_all_company_pages failed: {exc}")
        pages = {}

    # ── Track 2: intel-company — Perplexity executor ───────────────────
    print("\n[T2] intel-company — Perplexity research call...")
    perplexity_key = settings.perplexity_api_key
    if not perplexity_key:
        print("     [SKIP] PERPLEXITY_API_KEY not set — skipping Track 2")
    else:
        print(f"     API key: {perplexity_key[:8]}...")
        try:
            from core.executor import ModuleExecutor
            from core.registry import (
                V2_MODULE_REGISTRY,
                register_all_v2_modules,
            )
            from core.research_client import make_research_client
            from prism_platform.v2.modules.intel_company.config import INTEL_COMPANY_CONFIG
            from prism_platform.v2.modules.intel_company.schemas import CompanySeedOutput

            register_all_v2_modules()
            handle = V2_MODULE_REGISTRY["intel-company"]
            api = make_research_client(timeout=120.0)
            executor = ModuleExecutor(agent_api=api)
            result = await executor.execute(
                config=INTEL_COMPANY_CONFIG,
                context=context,
                output_schema=CompanySeedOutput,
                playbook_path=handle.playbook_path,
            )
            await api.close()

            print(f"     Status: {result.status}")
            print(f"     Duration: {result.duration_ms}ms")
            if result.output:
                print(f"     company: {result.output.get('common_name', '?')}")
                print(f"     HQ: {result.output.get('headquarters', '?')}")
                print(f"     employees: {result.output.get('employee_count', '?')}")
                competitors = result.output.get("competitors", [])
                print(f"     competitors detected: {len(competitors)}")
                # Hydrate context for downstream modules
                context.upstream_results["intel-company"] = result.output
            else:
                print(f"     Errors: {result.errors}")
        except Exception as exc:
            print(f"     [ERROR] {exc}")

    # ── Track 1B: intel-competitors collector ─────────────────────────
    print("\n[T1] intel-competitors — search vendor detector (Scout)...")
    try:
        comp_result = await intel_competitors_collect(context)
        vendor = comp_result.get("detected_search_vendor")
        sources = comp_result.get("detection_sources", [])
        print(f"     Detected vendor: {vendor or 'none'}")
        print(f"     Detection sources: {sources}")
    except Exception as exc:
        print(f"     [ERROR] {exc}")

    print(f"\n{'='*60}")
    print("SMOKE TEST COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    domain = sys.argv[1] if len(sys.argv) > 1 else "nike.com"
    asyncio.run(main(domain))
