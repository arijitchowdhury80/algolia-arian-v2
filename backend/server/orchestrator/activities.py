"""PRISM Activities — module execution as Temporal activities with DB-first caching.

Uses the v2 module registry (V2_MODULE_REGISTRY). Each module is a ModuleHandle
(config + output schema + playbook path). The generic ModuleExecutor handles
the actual research call and schema validation.

The research backend is never chosen here — every site builds it with
``make_research_client()``, which resolves ``RESEARCH_PROVIDER`` (Gemini or
Perplexity). Hardcoding a provider at the call site is what left the pipeline
unable to run when the Perplexity key died.

intel-company is the only module with a bespoke 3-track pipeline:
  Track 1: WebFetch — live page scrape (leadership + IR + newsroom)
  Track 2: grounded web research with citations
  Track 3: Synthesis LLM — reconciles T1 + T2 into verified output

All other modules use the generic single-track executor path.
"""

from __future__ import annotations

import json
import time
from typing import Any

import structlog
from pydantic import ValidationError
from temporalio import activity

from core.db.cache import get_cached_result, persist_result
from core.executor import ModuleExecutor, ModuleExecutorResult
from core.paths import LEGACY_MODULES_ROOT
from core.pipeline_health import PipelineHealthLog
from core.registry import V2_MODULE_REGISTRY, ModuleHandle
from core.research_client import make_research_client
from core.types import (
    CompetitorRef,
    ExecutionContextV2,
    ExecutiveRef,
)
from prism_platform.v2.modules.intel_hiring.fetcher import fetch_careers_page
from server.orchestrator.workflows import RunModuleInput

logger = structlog.get_logger(__name__)

# Path to the intel-company synthesis playbook (Track 3)
_INTEL_COMPANY_SYNTHESIS_PLAYBOOK = (
    LEGACY_MODULES_ROOT / "intel_company" / "playbook_synthesis.md"
)

# Path to intel-hiring playbook (for 2-track pipeline)
_INTEL_HIRING_PLAYBOOK = LEGACY_MODULES_ROOT / "intel_hiring" / "playbook.md"


def _populate_company_refs(context: ExecutionContextV2, company_output: dict[str, Any]) -> None:
    """Map intel-company's CompanySeedOutput into ExecutionContextV2 refs.

    Translates CompetitorSeed -> CompetitorRef and ExecutiveSeed -> ExecutiveRef
    (the field names differ: company_name/full_name vs name) so the existing
    {competitors} / {executives} playbook variables resolve for every module.

    Also backfills `industry` if the run_module context didn't carry it.
    Skips any seed entry missing the fields a Ref requires — never fabricates.
    """
    competitors: list[CompetitorRef] = []
    for c in company_output.get("competitors", []) or []:
        name = c.get("company_name") or c.get("name")
        domain = c.get("domain")
        if name and domain:
            competitors.append(
                CompetitorRef(name=name, domain=domain, linkedin_url=c.get("linkedin_url"))
            )

    executives: list[ExecutiveRef] = []
    for e in company_output.get("executives", []) or []:
        name = e.get("full_name") or e.get("name")
        title = e.get("title")
        if name and title:
            executives.append(
                ExecutiveRef(
                    name=name,
                    title=title,
                    linkedin_url=e.get("linkedin_url"),
                    role_classification=e.get("role_classification"),
                )
            )

    if competitors:
        context.competitors = competitors
    if executives:
        context.executives = executives
    if not context.industry and company_output.get("industry"):
        context.industry = company_output["industry"]


async def _hydrate_context_from_upstream(
    context: ExecutionContextV2,
    handle: ModuleHandle,
) -> None:
    """Populate competitors/executives + composed-module outputs from the DB.

    Fixes the gap where the generic run_module built a context with only
    domain/company/ticker, leaving {competitors}, {executives} and
    {upstream_*} unresolved for every non-bespoke module.

    Two steps:
      1. Load intel-company's persisted output (the identity card) to fill
         competitors/executives/industry — for every module except
         intel-company itself.
      2. For each module in `handle.config.composes`, load its persisted
         output into upstream_results[name] so {upstream_<name>} resolves.

    Every load is non-fatal: a miss leaves the field empty and the module
    degrades to independent research (current behaviour).
    """
    domain = context.account_domain

    if handle.config.name != "intel-company":
        try:
            company_cached = await get_cached_result("intel-company", domain)
            if company_cached and company_cached.get("output"):
                _populate_company_refs(context, company_cached["output"])
                # Expose the full company card for {upstream_intel_company} too.
                context.upstream_results.setdefault("intel-company", company_cached["output"])
        except Exception as exc:
            logger.warning(
                "upstream company hydration failed (non-fatal)",
                module=handle.config.name,
                domain=domain,
                error=str(exc),
            )

    for upstream_name in handle.config.composes:
        if upstream_name in context.upstream_results:
            continue  # already loaded (e.g. intel-company above)
        try:
            cached = await get_cached_result(upstream_name, domain)
            if cached and cached.get("output"):
                context.upstream_results[upstream_name] = cached["output"]
            else:
                logger.info(
                    "compose upstream not yet available (non-fatal)",
                    module=handle.config.name,
                    upstream=upstream_name,
                    domain=domain,
                )
        except Exception as exc:
            logger.warning(
                "compose upstream load failed (non-fatal)",
                module=handle.config.name,
                upstream=upstream_name,
                domain=domain,
                error=str(exc),
            )


@activity.defn(name="run_module")
async def run_module(input: RunModuleInput) -> dict[str, Any]:
    """Execute a single module with database-first caching.

    1. Look up the module handle in the v2 registry
    2. Check PostgreSQL for a cached result (permanent storage, no auto-expiry)
    3. If no cache: for intel-company run the 3-track pipeline;
       for all other modules run the generic single-track executor
    4. Run optional post_execute hook (e.g. accounts table write for intel-company)
    5. Persist result to module_executions

    Args:
        input: RunModuleInput — module_name, domain, audit_id, company_name, etc.

    Returns:
        Module result dict with status, output, sources, duration_ms, errors.
    """
    handle = V2_MODULE_REGISTRY.get(input.module_name)
    if not handle:
        logger.error("Unknown module requested", module_name=input.module_name)
        return {
            "status": "failed",
            "error": f"Unknown module: {input.module_name}",
            "module_name": input.module_name,
        }

    # Step 1: Check cache
    try:
        cached = await get_cached_result(input.module_name, input.domain)
        if cached is not None:
            logger.info(
                "Module cache hit — skipping API call",
                module_name=input.module_name,
                domain=input.domain,
                audit_id=input.audit_id,
            )
            return cached
    except Exception as exc:
        logger.error("Cache check failed, proceeding with fresh call", error=str(exc))

    # Step 2: Build execution context
    v2_context = ExecutionContextV2(
        audit_id=input.audit_id,
        account_domain=input.domain,
        company_name=input.company_name or "",
        is_public=not input.is_private,
        ticker=input.ticker,
    )

    # Step 2b: Hydrate competitors/executives + composed-module outputs from the DB.
    # Makes {competitors}, {executives}, {upstream_*} resolve for composing modules.
    await _hydrate_context_from_upstream(v2_context, handle)

    # Step 2c: Run the module's deterministic Track-1 collector (no LLM), if any.
    # Collected data lands in upstream_results for the playbook to reference as
    # {upstream_<key>}. Failure is non-fatal — Track-2 (LLM) still runs.
    if handle.collector is not None:
        try:
            collected = await handle.collector(v2_context)
            if collected:
                v2_context.upstream_results.update(collected)
                logger.info(
                    "Track-1 collector completed",
                    module_name=input.module_name,
                    domain=input.domain,
                    keys=list(collected.keys()),
                )
        except Exception as exc:
            logger.warning(
                "Track-1 collector failed (non-fatal) — Track-2 runs without it",
                module_name=input.module_name,
                domain=input.domain,
                error=str(exc),
            )

    logger.info(
        "Module execution started (fresh API call)",
        module_name=input.module_name,
        domain=input.domain,
        audit_id=input.audit_id,
        wave=input.wave,
    )

    # Step 3: Execute — intel-company gets the full 3-track pipeline
    start_time = time.monotonic()

    if input.module_name == "intel-company":
        result, result_dict = await _run_intel_company_pipeline(
            input=input,
            handle=handle,
            v2_context=v2_context,
            start_time=start_time,
        )
    elif input.module_name == "intel-hiring":
        result, result_dict = await _run_intel_hiring_pipeline(
            input=input,
            handle=handle,
            v2_context=v2_context,
            start_time=start_time,
        )
    else:
        api = make_research_client(timeout=float(handle.config.timeout_seconds))
        executor = ModuleExecutor(agent_api=api)
        result = await executor.execute(
            config=handle.config,
            context=v2_context,
            output_schema=handle.output_schema,
            playbook_path=handle.playbook_path,
        )
        duration_ms = int((time.monotonic() - start_time) * 1000)
        result_dict = _to_result_dict(result, duration_ms)

    logger.info(
        "Module execution complete",
        module_name=input.module_name,
        domain=input.domain,
        status=result_dict.get("status"),
        duration_ms=result_dict.get("duration_ms"),
    )

    # Step 4: Post-execute hook
    if handle.post_execute and result.status == "success":
        try:
            await handle.post_execute(result, v2_context)
        except Exception as exc:
            logger.error(
                "post_execute hook failed (non-fatal)",
                module_name=input.module_name,
                domain=input.domain,
                error=str(exc),
            )

    # Step 5: Persist to PostgreSQL
    try:
        await persist_result(
            module_name=input.module_name,
            domain=input.domain,
            result_dict=result_dict,
            audit_id=input.audit_id,
        )
    except Exception as exc:
        logger.error("persist_result failed", module_name=input.module_name, error=str(exc))

    return result_dict


async def _run_intel_company_pipeline(
    input: RunModuleInput,
    handle: Any,
    v2_context: ExecutionContextV2,
    start_time: float,
) -> tuple[ModuleExecutorResult, dict[str, Any]]:
    """Execute the intel-company 3-track pipeline.

    Track 1: Fetch leadership + IR + newsroom pages via BrowserClient.
    Track 2: Perplexity sonar-pro web research call via ModuleExecutor.
    Track 3: Synthesis LLM reconciles T1 + T2 into a verified CompanySeedOutput.

    Track 3 failure is non-fatal — the module falls back to Track 2 output
    with DEGRADED status in the pipeline health log.

    Returns:
        (ModuleExecutorResult, result_dict) — the result object for post_execute
        hooks and the dict for persistence.
    """
    from core.synthesis import SynthesisClient
    from prism_platform.v2.modules.intel_company.fetcher import fetch_all_company_pages
    from prism_platform.v2.modules.intel_company.schemas import CompanySeedOutput

    health = PipelineHealthLog(module_name="intel-company", domain=input.domain)

    # ── Track 1: WebFetch ──────────────────────────────────────────────────
    health.info("track1_webfetch", "Fetching company pages", domain=input.domain)
    try:
        track1_pages = await fetch_all_company_pages(input.domain)
        pages_found = sum(1 for v in track1_pages.values() if v)
        if pages_found == 0:
            health.warning(
                "track1_webfetch",
                "No company pages fetched — all paths returned empty",
                domain=input.domain,
            )
        else:
            health.info(
                "track1_webfetch",
                f"Fetched {pages_found}/3 pages successfully",
                has_leadership=bool(track1_pages.get("leadership_page")),
                has_ir=bool(track1_pages.get("ir_page")),
                has_newsroom=bool(track1_pages.get("newsroom_page")),
            )
    except Exception as exc:
        logger.error(
            "[intel-company] Track 1 WebFetch failed",
            domain=input.domain,
            error=str(exc),
        )
        health.error(
            "track1_webfetch",
            f"Page fetch raised exception: {type(exc).__name__}",
            error=str(exc),
        )
        track1_pages = {"leadership_page": "", "ir_page": "", "newsroom_page": ""}

    # Inject Track 1 content into context for playbook resolution
    v2_context.upstream_results.update(track1_pages)

    # ── Track 2: grounded web research (provider from RESEARCH_PROVIDER) ───
    api = make_research_client(timeout=float(handle.config.timeout_seconds))
    health.info(
        "track2_perplexity",
        f"Calling {getattr(api, 'provider', 'unknown')} for grounded research",
        domain=input.domain,
    )
    executor = ModuleExecutor(agent_api=api)

    t2_result = await executor.execute(
        config=handle.config,
        context=v2_context,
        output_schema=handle.output_schema,
        playbook_path=handle.playbook_path,
    )

    if t2_result.status == "success":
        health.info(
            "track2_perplexity",
            "Perplexity call succeeded",
            citations=len(t2_result.citations),
        )
    else:
        health.error(
            "track2_perplexity",
            "Perplexity call failed — cannot proceed to synthesis",
            errors=t2_result.errors,
        )
        # Without Track 2 there is nothing to synthesize
        duration_ms = int((time.monotonic() - start_time) * 1000)
        result_dict = _to_result_dict(t2_result, duration_ms)
        result_dict["pipeline_health"] = health.summary()
        return t2_result, result_dict

    # ── Track 3: Synthesis ─────────────────────────────────────────────────
    health.info("track3_synthesis", "Running synthesis LLM reconciliation", domain=input.domain)
    synthesizer = SynthesisClient()

    template_vars = {
        "domain": input.domain,
        "company_name": input.company_name or "",
        "upstream_leadership_page": track1_pages.get("leadership_page", ""),
        "upstream_ir_page": track1_pages.get("ir_page", ""),
        "upstream_newsroom_page": track1_pages.get("newsroom_page", ""),
        "upstream_perplexity_output": json.dumps(t2_result.output, indent=2),
        "upstream_perplexity_citations": ", ".join(t2_result.citations),
    }

    try:
        t3_result = await synthesizer.synthesize(
            playbook_path=_INTEL_COMPANY_SYNTHESIS_PLAYBOOK,
            template_vars=template_vars,
            output_schema=CompanySeedOutput,
        )
    except Exception as exc:
        logger.error(
            "[intel-company] Track 3 synthesis raised exception",
            domain=input.domain,
            error=str(exc),
        )
        health.error(
            "track3_synthesis",
            "Synthesis raised exception — falling back to Track 2",
            error=str(exc),
        )
        duration_ms = int((time.monotonic() - start_time) * 1000)
        result_dict = _to_result_dict(t2_result, duration_ms)
        result_dict["pipeline_health"] = health.summary()
        return t2_result, result_dict

    if t3_result.status != "success" or not t3_result.output:
        health.error(
            "track3_synthesis",
            "Synthesis failed — falling back to Track 2 output",
            error=t3_result.error or "no output",
            model=t3_result.model_used,
        )
        duration_ms = int((time.monotonic() - start_time) * 1000)
        result_dict = _to_result_dict(t2_result, duration_ms)
        result_dict["pipeline_health"] = health.summary()
        return t2_result, result_dict

    # Validate synthesis output against schema
    try:
        validated = CompanySeedOutput.model_validate(t3_result.output)
    except ValidationError as exc:
        health.error(
            "track3_synthesis",
            "Synthesis output failed schema validation — falling back to Track 2",
            error=str(exc),
        )
        duration_ms = int((time.monotonic() - start_time) * 1000)
        result_dict = _to_result_dict(t2_result, duration_ms)
        result_dict["pipeline_health"] = health.summary()
        return t2_result, result_dict

    health.info(
        "track3_synthesis",
        "Synthesis succeeded — using reconciled output",
        model=t3_result.model_used,
        duration_ms=t3_result.duration_ms,
    )

    # Build the final result from synthesis output
    duration_ms = int((time.monotonic() - start_time) * 1000)
    final_result = ModuleExecutorResult(
        module_name="intel-company",
        module_version="2.0.0",
        status="success",
        output=validated.model_dump(),
        claims=t2_result.claims,  # Claims from Track 2 (has citation URLs)
        citations=t2_result.citations,
        duration_ms=duration_ms,
        llm_calls=2,  # Track 2 (Perplexity) + Track 3 (Synthesis)
        input_tokens=t2_result.input_tokens,
        output_tokens=t2_result.output_tokens,
    )

    result_dict = _to_result_dict(final_result, duration_ms)
    result_dict["pipeline_health"] = health.summary()

    logger.info(
        "[intel-company] 3-track pipeline complete",
        domain=input.domain,
        overall_status=health.overall_status,
        duration_ms=duration_ms,
    )

    return final_result, result_dict


async def _run_intel_hiring_pipeline(
    input: RunModuleInput,
    handle: Any,
    v2_context: ExecutionContextV2,
    start_time: float,
) -> tuple[ModuleExecutorResult, dict[str, Any]]:
    """Execute the intel-hiring 2-track pipeline.

    Track 1: Scout fetches the company's live career page.
    Track 2: Perplexity researches hiring signals with Track 1 content injected.

    Track 1 failure is non-fatal — Track 2 runs regardless, falling back to
    Perplexity's own web search for job listing data.

    Returns:
        (ModuleExecutorResult, result_dict)
    """
    health = PipelineHealthLog(module_name="intel-hiring", domain=input.domain)

    # ── Track 1: Scout career page fetch ──────────────────────────────────
    health.info("track1_webfetch", "Fetching career page", domain=input.domain)
    try:
        hiring_fetch = await fetch_careers_page(input.domain)
    except Exception as exc:
        logger.error(
            "[intel-hiring] Track 1 fetch raised exception (non-fatal)",
            domain=input.domain,
            error=str(exc),
        )
        from prism_platform.v2.modules.intel_hiring.fetcher import HiringFetchResult

        hiring_fetch = HiringFetchResult()

    if hiring_fetch.redirected_to_linkedin:
        health.warning(
            "track1_webfetch",
            "Career page redirects to LinkedIn — Perplexity runs without injected content",
            domain=input.domain,
        )
    elif hiring_fetch.careers_page_content:
        health.info(
            "track1_webfetch",
            "Career page fetched",
            domain=input.domain,
            content_len=len(hiring_fetch.careers_page_content),
            careers_url=hiring_fetch.careers_url,
        )
    else:
        health.warning(
            "track1_webfetch",
            "No career page found — Track 2 runs without injected content",
            domain=input.domain,
        )

    # Inject careers content into context so PlaybookLoader resolves {upstream_careers_page}
    v2_context.upstream_results["careers_page"] = hiring_fetch.careers_page_content

    # ── Track 2: grounded research with injected career page content ──────
    api = make_research_client(timeout=float(handle.config.timeout_seconds))
    health.info(
        "track2_perplexity",
        f"Running {getattr(api, 'provider', 'unknown')} research",
        domain=input.domain,
    )
    executor = ModuleExecutor(agent_api=api)
    result = await executor.execute(
        config=handle.config,
        context=v2_context,
        output_schema=handle.output_schema,
        playbook_path=handle.playbook_path,
    )

    duration_ms = int((time.monotonic() - start_time) * 1000)
    result_dict = _to_result_dict(result, duration_ms)
    result_dict["pipeline_health"] = health.summary()

    logger.info(
        "[intel-hiring] 2-track pipeline complete",
        domain=input.domain,
        overall_status=health.overall_status,
        duration_ms=duration_ms,
        track1_content_len=len(hiring_fetch.careers_page_content),
    )

    return result, result_dict


def _to_result_dict(result: ModuleExecutorResult, duration_ms: int) -> dict[str, Any]:
    """Map ModuleExecutorResult to the standard dict stored in module_executions."""
    return {
        "module_name": result.module_name,
        "module_version": result.module_version,
        "status": result.status,
        "output": result.output or {},
        "sources": result.citations,  # list[str] URLs
        "duration_ms": duration_ms,
        "llm_calls": result.llm_calls,
        "llm_cost_usd": 0.0,
        "errors": result.errors,
        "warnings": [],
    }
