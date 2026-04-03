"""Audit Browser module -- Playwright-based live search testing.

This Wave 2 module drives a real browser to test the prospect's search
experience. It depends on intel-company (search bar detection) and
intel-queries (test query generation).

Data flow:
1. Read intel-queries output from module_executions for the query list
2. Read intel-company output from module_executions for search bar hints
3. Collector: Playwright browser automation → screenshots + query results
4. Enricher: Claude Vision scoring → 10-dimension scores
5. Validator: 9 quality checks
"""

from __future__ import annotations

import time
from typing import ClassVar

import structlog
from sqlalchemy import select

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import EvidenceTier, ModuleResult, Source, ValidationResult
from prism_platform.db.models import ModuleExecution
from prism_platform.db.session import async_session_factory
from prism_platform.modules.audit_browser.collector import BrowserCollector
from prism_platform.modules.audit_browser.enricher import BrowserEnricher
from prism_platform.modules.audit_browser.schemas import BrowserInput, BrowserOutput
from prism_platform.modules.audit_browser.validator import validate_output

logger = structlog.get_logger(__name__)


class BrowserModule(ModuleInterface):
    """Live browser-based search experience testing module.

    Produces: query results, screenshots, dimension scores, competitor comparisons.
    Consumed by: audit-report, synth-business-case, synth-sales-plays.
    """

    name: ClassVar[str] = "audit-browser"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Playwright-based live search testing. Drives a real browser to execute "
        "test queries, capture screenshots, detect NLP features, and score "
        "10 search experience dimensions via Claude Vision."
    )
    layer: ClassVar[str] = "experience"

    input_schema: ClassVar[type[BrowserInput]] = BrowserInput
    output_schema: ClassVar[type[BrowserOutput]] = BrowserOutput
    dependencies: ClassVar[list[str]] = ["intel-company", "intel-queries"]
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 600  # 10 minutes (browser automation is slow)
    max_retries: ClassVar[int] = 1

    def __init__(self) -> None:
        self._collector = BrowserCollector()
        self._enricher = BrowserEnricher()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run full browser-based search testing and scoring.

        Steps:
        1. Read query list from intel-queries module execution
        2. Read search bar hints from intel-company intelligence
        3. Run Playwright browser automation
        4. Score dimensions via Claude Vision
        5. Return structured result

        Args:
            context: Execution context with domain and audit metadata.

        Returns:
            ModuleResult containing BrowserOutput and source provenance.
        """
        logger.info(
            "[BrowserModule] execute started",
            domain=context.domain,
            audit_id=context.audit_id,
        )
        start_ms = time.monotonic_ns() // 1_000_000
        sources: list[Source] = []

        try:
            # Step 1: Read intel-queries output for the query list
            queries = await self._load_queries(context.audit_id)
            if not queries:
                logger.warning(
                    "[BrowserModule] no queries found from intel-queries",
                    audit_id=context.audit_id,
                )
                # Generate minimal default queries
                queries = [
                    {"query": "search test", "query_type": "exact_product"},
                    {"query": "best sellers", "query_type": "category_browse"},
                    {"query": "help", "query_type": "ambiguous"},
                ]

            sources.append(
                Source(
                    field="test_queries",
                    value=f"Loaded {len(queries)} test queries from intel-queries",
                    tier=EvidenceTier.VERIFIED,
                    source_label="intel-queries module output",
                    method="direct_api",
                )
            )

            # Step 2: Read intel-company output for search bar hints and competitors
            search_bar_hint, competitor_domains = await self._load_company_intel(
                context.audit_id, context.account_id
            )

            # Step 3: Run Playwright browser automation
            collector_output = await self._collector.collect_all(
                domain=context.domain,
                audit_id=context.audit_id,
                queries=queries,
                competitor_domains=competitor_domains,
                search_bar_selector_hint=search_bar_hint,
            )

            sources.append(
                Source(
                    field="browser_testing",
                    value=(
                        f"Browser tested "
                        f"{collector_output.get('total_queries_executed', 0)} queries, "
                        f"captured {collector_output.get('total_screenshots', 0)} screenshots"
                    ),
                    tier=EvidenceTier.VERIFIED,
                    source_label=f"Playwright browser test on {context.domain}",
                    method="scrape",
                )
            )

            # Step 4: Score via Claude Vision
            output, enricher_llm_calls, enricher_cost = await self._enricher.enrich(
                domain=context.domain,
                collector_output=collector_output,
            )

            sources.append(
                Source(
                    field="dimension_scores",
                    value=f"Claude Vision scored {len(output.dimension_scores)} dimensions",
                    tier=EvidenceTier.ESTIMATE,
                    source_label="Claude Sonnet Vision (scoring)",
                    method="llm_extraction",
                )
            )

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

            # Determine status
            if output.was_blocked and output.total_queries_executed == 0:
                status = "failed"
            elif output.total_queries_executed < 10:
                status = "partial"
            else:
                status = "success"

            result = ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status=status,
                output=output.model_dump(),
                sources=sources,
                duration_ms=duration_ms,
                llm_calls=enricher_llm_calls,
                llm_cost_usd=enricher_cost,
            )

            logger.info(
                "[BrowserModule] execute completed",
                domain=context.domain,
                status=status,
                duration_ms=duration_ms,
                total_queries=output.total_queries_executed,
                total_screenshots=output.total_screenshots,
                search_bar_found=output.search_bar_found,
                provider=output.detected_search_provider,
                llm_calls=enricher_llm_calls,
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.exception(
                "[BrowserModule] execute failed",
                domain=context.domain,
                audit_id=context.audit_id,
            )
            return ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="failed",
                output={},
                sources=sources,
                duration_ms=duration_ms,
                errors=[f"{type(error).__name__}: {error}"],
            )

    async def validate(self, result: ModuleResult) -> ValidationResult:
        """Validate module output meets quality standards (9 checks).

        Args:
            result: The ModuleResult from execute().

        Returns:
            ValidationResult with pass/fail and diagnostic details.
        """
        logger.info("[BrowserModule] validate started", module=self.name)

        try:
            output = BrowserOutput.model_validate(result.output)
            return validate_output(output)
        except Exception as error:
            logger.error(
                "[BrowserModule] validate failed -- output deserialization error",
                error=str(error),
            )
            return ValidationResult(
                passed=False,
                checks_run=0,
                checks_passed=0,
                errors=[f"Output deserialization failed: {error}"],
            )

    async def health_check(self) -> bool:
        """Check if Playwright and an LLM provider are configured."""
        from prism_platform.modules.audit_browser.collector import PLAYWRIGHT_AVAILABLE

        try:
            settings.get_enricher_provider()
            has_llm = True
        except (ValueError, AttributeError):
            has_llm = False

        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("[BrowserModule] Playwright not installed")
        if not has_llm:
            logger.warning("[BrowserModule] No LLM provider configured")

        return PLAYWRIGHT_AVAILABLE and has_llm

    async def _load_queries(self, audit_id: str) -> list[dict[str, str]]:
        """Load test queries from the intel-queries module execution.

        Args:
            audit_id: Audit ID to look up.

        Returns:
            List of query dicts with 'query' and 'query_type' keys.
        """
        try:
            async with async_session_factory() as session:
                stmt = (
                    select(ModuleExecution)
                    .where(
                        ModuleExecution.audit_id == audit_id,
                        ModuleExecution.module_name == "intel-queries",
                        ModuleExecution.status == "success",
                    )
                    .limit(1)
                )
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()

                if not row or not row.output_json:
                    return []

                output = row.output_json
                queries: list[dict[str, str]] = []

                # Extract prospect queries
                for q in output.get("prospect_queries", []):
                    queries.append(
                        {
                            "query": q.get("query", ""),
                            "query_type": q.get("query_type", "unknown"),
                        }
                    )

                logger.info(
                    "[BrowserModule] loaded queries from intel-queries",
                    audit_id=audit_id,
                    query_count=len(queries),
                )
                return queries

        except Exception as exc:
            logger.error(
                "[BrowserModule] failed to load intel-queries output",
                audit_id=audit_id,
                error=str(exc),
            )
            return []

    async def _load_company_intel(
        self,
        audit_id: str,
        account_id: str,
    ) -> tuple[str | None, list[dict[str, str]]]:
        """Load search bar hints and competitor domains from intel-company.

        Args:
            audit_id: Audit ID to look up.
            account_id: Account ID for intelligence lookup.

        Returns:
            Tuple of (search_bar_selector_hint, list of competitor dicts).
        """
        search_bar_hint: str | None = None
        competitors: list[dict[str, str]] = []

        try:
            async with async_session_factory() as session:
                # Try module_executions first
                stmt = (
                    select(ModuleExecution)
                    .where(
                        ModuleExecution.audit_id == audit_id,
                        ModuleExecution.module_name == "intel-company",
                        ModuleExecution.status == "success",
                    )
                    .limit(1)
                )
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()

                if row and row.output_json:
                    output = row.output_json

                    # Extract search bar info
                    if output.get("has_search_bar"):
                        search_bar_hint = output.get("search_bar_selector")

                    # Extract competitor domains
                    for comp in output.get("competitors", []):
                        domain = comp.get("domain", "")
                        name = comp.get("company_name", domain)
                        if domain:
                            competitors.append(
                                {
                                    "domain": domain,
                                    "company_name": name,
                                }
                            )

                logger.info(
                    "[BrowserModule] loaded company intel",
                    audit_id=audit_id,
                    search_bar_hint=search_bar_hint,
                    competitor_count=len(competitors),
                )

        except Exception as exc:
            logger.error(
                "[BrowserModule] failed to load intel-company data",
                audit_id=audit_id,
                error=str(exc),
            )

        return search_bar_hint, competitors


# Import settings at module level to avoid circular import in health_check
from prism_platform.config import settings  # noqa: E402
