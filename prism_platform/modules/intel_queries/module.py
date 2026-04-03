"""Intel Queries module -- vertically-calibrated test query generation.

This module generates test queries for the browser-based search experience
audit. It reads company context from accounts.intelligence (populated by
intel-company and intel-techstack) and uses Claude via Instructor to produce
queries calibrated to the prospect's industry, catalog, and competitors.

Data flow:
1. Collector: Read industry, product_categories, competitors from Account columns
2. Enricher: Instructor + Claude → 16 prospect queries + competitor query sets
3. Validator: 9 quality checks
4. Persist: module_executions (full output)
"""

from __future__ import annotations

import time
from typing import ClassVar

import structlog

from prism_platform.config import settings
from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import EvidenceTier, ModuleResult, Source, ValidationResult
from prism_platform.modules.intel_queries.collector import QueriesCollector
from prism_platform.modules.intel_queries.enricher import QueriesEnricher
from prism_platform.modules.intel_queries.schemas import (
    QueriesInput,
    QueriesOutput,
)
from prism_platform.modules.intel_queries.validator import validate_output

logger = structlog.get_logger(__name__)


class QueriesModule(ModuleInterface):
    """Vertically-calibrated test query generation for browser audit.

    Produces: 16 prospect queries (2 per type) + competitor query sets.
    Depends on: intel-company (for industry, categories, competitors),
                intel-techstack (for search vendor context).
    """

    name: ClassVar[str] = "intel-queries"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Generates vertically-calibrated test queries for the browser-based "
        "search experience audit using Claude via Instructor. Produces 16 "
        "prospect queries across 8 types plus competitor query sets."
    )
    layer: ClassVar[str] = "intelligence"

    input_schema: ClassVar[type[QueriesInput]] = QueriesInput
    output_schema: ClassVar[type[QueriesOutput]] = QueriesOutput
    dependencies: ClassVar[list[str]] = ["intel-company", "intel-techstack"]
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 120
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        """Initialize collector and enricher instances."""
        self._collector = QueriesCollector()
        self._enricher = QueriesEnricher()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run full query generation pipeline.

        Steps:
        1. Read company context from Account columns
        2. Generate 16 prospect queries via Claude
        3. Generate competitor query sets via Claude
        4. Compute difficulty distribution and metadata

        Args:
            context: Execution context with domain and audit metadata.

        Returns:
            ModuleResult containing QueriesOutput and source provenance.
        """
        logger.info(
            "[QueriesModule] execute started",
            domain=context.domain,
            audit_id=context.audit_id,
        )
        start_ms = time.monotonic_ns() // 1_000_000
        sources: list[Source] = []
        total_llm_calls = 0
        total_cost = 0.0

        try:
            # Step 1: Read company context
            company_context = await self._collector.collect_from_db(
                context.account_id, context.domain
            )

            # Step 2: Generate prospect queries
            prospect_queries, llm_calls, cost = await self._enricher.generate_prospect_queries(
                company_context
            )
            total_llm_calls += llm_calls
            total_cost += cost

            sources.append(
                Source(
                    field="prospect_queries",
                    value=f"Claude generated {len(prospect_queries)} prospect queries",
                    tier=EvidenceTier.ESTIMATE,
                    source_label="Claude via Instructor (prospect query generation)",
                    method="llm_extraction",
                )
            )

            # Step 3: Generate competitor query sets
            competitor_query_sets = []
            competitors = company_context.get("competitor_domains", [])

            for competitor in competitors:
                try:
                    (
                        query_set,
                        comp_llm_calls,
                        comp_cost,
                    ) = await self._enricher.generate_competitor_queries(
                        company_context, competitor
                    )
                    competitor_query_sets.append(query_set)
                    total_llm_calls += comp_llm_calls
                    total_cost += comp_cost

                    sources.append(
                        Source(
                            field=f"competitor_queries_{competitor.get('domain', '')}",
                            value=(
                                f"Claude generated {len(query_set.queries)} queries "
                                f"for {competitor.get('company_name', '')}"
                            ),
                            tier=EvidenceTier.ESTIMATE,
                            source_label=(
                                f"Claude via Instructor "
                                f"(competitor: {competitor.get('domain', '')})"
                            ),
                            method="llm_extraction",
                        )
                    )
                except Exception as exc:
                    comp_name = competitor.get("company_name", competitor.get("domain", "unknown"))
                    logger.error(
                        "[QueriesModule] competitor query generation failed",
                        competitor=comp_name,
                        error=str(exc),
                    )
                    # Non-fatal -- continue with other competitors

            # Step 4: Compute metadata
            difficulty_distribution = self._enricher.compute_difficulty_distribution(
                prospect_queries
            )
            types_covered = sorted({q.query_type for q in prospect_queries})

            output = QueriesOutput(
                domain=context.domain,
                industry=company_context.get("industry", ""),
                sub_vertical=company_context.get("sub_vertical"),
                prospect_queries=prospect_queries,
                competitor_query_sets=competitor_query_sets,
                difficulty_distribution=difficulty_distribution,
                query_count=len(prospect_queries),
                types_covered=types_covered,
                generation_notes=(
                    f"Generated via Claude {total_llm_calls} calls. "
                    f"Prospect: {len(prospect_queries)} queries. "
                    f"Competitors: {len(competitor_query_sets)} sets."
                ),
            )

            # Note: query metadata is stored in module_executions output_json.
            # The accounts.intelligence column has been removed.

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            status = "success"

            result = ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status=status,
                output=output.model_dump(),
                sources=sources,
                duration_ms=duration_ms,
                llm_calls=total_llm_calls,
                llm_cost_usd=round(total_cost, 4),
            )

            logger.info(
                "[QueriesModule] execute completed",
                domain=context.domain,
                status=status,
                duration_ms=duration_ms,
                llm_calls=total_llm_calls,
                llm_cost_usd=round(total_cost, 4),
                prospect_query_count=len(prospect_queries),
                competitor_set_count=len(competitor_query_sets),
                types_covered=types_covered,
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.exception(
                "[QueriesModule] execute failed",
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
                llm_calls=total_llm_calls,
                llm_cost_usd=round(total_cost, 4),
                errors=[f"{type(error).__name__}: {error}"],
            )

    async def validate(self, result: ModuleResult) -> ValidationResult:
        """Validate module output meets quality standards (9 checks).

        Args:
            result: The ModuleResult from execute().

        Returns:
            ValidationResult with pass/fail and diagnostic details.
        """
        logger.info("[QueriesModule] validate started", module=self.name)

        try:
            output = QueriesOutput.model_validate(result.output)
            return validate_output(output, result.sources)
        except Exception as error:
            logger.error(
                "[QueriesModule] validate failed -- output deserialization error",
                error=str(error),
            )
            return ValidationResult(
                passed=False,
                checks_run=0,
                checks_passed=0,
                errors=[f"Output deserialization failed: {error}"],
            )

    async def health_check(self) -> bool:
        """Check if an LLM provider is configured."""
        try:
            settings.get_enricher_provider()
            has_llm = True
        except (ValueError, AttributeError):
            has_llm = False

        if not has_llm:
            logger.warning("[QueriesModule] No LLM provider configured")

        return has_llm

