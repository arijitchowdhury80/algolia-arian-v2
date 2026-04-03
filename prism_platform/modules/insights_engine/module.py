"""Insights Engine module -- cross-audit vertical benchmarking.

Wave 6 fire-and-forget module that reads all completed module outputs
for the current audit, identifies the vertical, queries historical audits
in the same vertical, and produces anonymized benchmark metrics.

Data flow:
1. Collector: Read current audit + historical audit data from PostgreSQL
2. Enricher: Instructor + Claude Sonnet -> InsightsOutput
3. Validator: 8 quality checks
4. Persist: vertical_benchmarks table
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

import structlog
from sqlalchemy import delete

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import EvidenceTier, ModuleResult, Source, ValidationResult
from prism_platform.db.models import VerticalBenchmark
from prism_platform.db.session import async_session_factory
from prism_platform.modules.insights_engine.collector import InsightsCollector
from prism_platform.modules.insights_engine.enricher import InsightsEnricher
from prism_platform.modules.insights_engine.schemas import InsightsInput, InsightsOutput
from prism_platform.modules.insights_engine.validator import validate_output

logger = structlog.get_logger(__name__)


class InsightsModule(ModuleInterface):
    """Cross-audit vertical benchmarking module.

    Produces: anonymized vertical benchmark metrics from historical audit data.
    Consumed by: audit report delivery, sales plays, campaign modules.
    """

    name: ClassVar[str] = "insights-engine"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Cross-audit vertical benchmarking via Claude analysis. "
        "Reads all module outputs from historical audits in the same vertical "
        "and produces anonymized benchmark metrics."
    )
    layer: ClassVar[str] = "intelligence"

    input_schema: ClassVar[type[InsightsInput]] = InsightsInput
    output_schema: ClassVar[type[InsightsOutput]] = InsightsOutput
    dependencies: ClassVar[list[str]] = []  # Reads from DB, runs after all others
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 300  # 5 minutes
    max_retries: ClassVar[int] = 1

    def __init__(self) -> None:
        self._collector = InsightsCollector()
        self._enricher = InsightsEnricher()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run vertical benchmarking for the current audit.

        Steps:
        1. Collect current + historical audit data from DB
        2. Enrich via Claude to produce benchmark metrics
        3. Store results in vertical_benchmarks table (idempotent)

        Args:
            context: Execution context with domain and audit metadata.

        Returns:
            ModuleResult containing InsightsOutput and source provenance.
        """
        logger.info(
            "[InsightsModule] execute started",
            domain=context.domain,
            audit_id=context.audit_id,
        )
        start_ms = time.monotonic_ns() // 1_000_000
        sources: list[Source] = []

        try:
            # Step 1: Collect audit data
            collected = await self._collector.collect_all(
                audit_id=context.audit_id,
                domain=context.domain,
            )

            vertical = collected.get("vertical", "")
            if not vertical:
                duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
                logger.warning(
                    "[InsightsModule] no vertical found, skipping",
                    domain=context.domain,
                )
                return ModuleResult(
                    module_name=self.name,
                    module_version=self.version,
                    status="partial",
                    output={"domain": context.domain, "vertical": "", "metrics": []},
                    sources=sources,
                    duration_ms=duration_ms,
                    errors=["No vertical classification found in intel-company output"],
                )

            sources.append(
                Source(
                    field="collector",
                    value=(
                        f"Read {collected.get('total_audits', 1)} audits in vertical '{vertical}'"
                    ),
                    tier=EvidenceTier.VERIFIED,
                    source_label="PostgreSQL module_executions",
                    method="db_read",
                )
            )

            # Step 2: Enrich via Claude
            current_audit: dict[str, Any] = collected.get("current_audit", {})
            historical_audits: list[dict[str, Any]] = collected.get("historical_audits", [])
            historical_ids: list[str] = collected.get("historical_audit_ids", [])
            total_audits: int = collected.get("total_audits", 1)

            output, llm_calls, llm_cost = await self._enricher.enrich(
                domain=context.domain,
                vertical=vertical,
                current_audit=current_audit,
                historical_audits=historical_audits,
                historical_audit_ids=[context.audit_id, *historical_ids],
                total_audits=total_audits,
            )

            sources.append(
                Source(
                    field="enricher",
                    value=f"Claude {llm_calls} call(s), ${llm_cost:.4f}",
                    tier=EvidenceTier.ESTIMATE,
                    source_label="Claude Sonnet via Instructor",
                    method="llm_extraction",
                )
            )

            # Step 3: Store in vertical_benchmarks (idempotent)
            try:
                await self._persist_benchmarks(context.audit_id, output)
            except Exception as exc:
                logger.error(
                    "[InsightsModule] failed to persist benchmarks",
                    domain=context.domain,
                    error=str(exc),
                )
                # Non-fatal

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            status = "success" if len(output.metrics) >= 3 else "partial"

            result = ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status=status,
                output=output.model_dump(),
                sources=sources,
                duration_ms=duration_ms,
                llm_calls=llm_calls,
                llm_cost_usd=llm_cost,
            )

            logger.info(
                "[InsightsModule] execute completed",
                domain=context.domain,
                status=status,
                duration_ms=duration_ms,
                metrics_count=len(output.metrics),
                vertical=vertical,
                total_audits=total_audits,
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.exception(
                "[InsightsModule] execute failed",
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
        """Validate module output meets quality standards (8 checks).

        Args:
            result: The ModuleResult from execute().

        Returns:
            ValidationResult with pass/fail and diagnostic details.
        """
        logger.info("[InsightsModule] validate started", module=self.name)

        try:
            output = InsightsOutput.model_validate(result.output)
            return validate_output(output)
        except Exception as error:
            logger.error(
                "[InsightsModule] validate failed -- output deserialization error",
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
        from prism_platform.config import settings

        try:
            settings.get_enricher_provider()
            has_llm = True
        except (ValueError, AttributeError):
            has_llm = False
        if not has_llm:
            logger.warning("[InsightsModule] No LLM provider configured")
        return has_llm

    async def _persist_benchmarks(
        self,
        audit_id: str,
        output: InsightsOutput,
    ) -> None:
        """Store benchmark metrics in vertical_benchmarks table.

        Idempotent: deletes existing benchmarks for this audit's vertical
        before inserting new ones.

        Args:
            audit_id: The current audit ID.
            output: The InsightsOutput with metrics to persist.
        """
        now = datetime.now(UTC)

        logger.info(
            "[InsightsModule] persisting benchmarks",
            vertical=output.vertical,
            metrics_count=len(output.metrics),
            audit_id=audit_id,
        )
        async with async_session_factory() as session:
            try:
                # Delete existing benchmarks for this vertical (idempotent)
                delete_result = await session.execute(
                    delete(VerticalBenchmark).where(
                        VerticalBenchmark.vertical == output.vertical,
                    )
                )
                deleted_count = delete_result.rowcount
                logger.info(
                    "[InsightsModule] existing benchmarks cleaned up",
                    vertical=output.vertical,
                    deleted_count=deleted_count,
                )

                # Insert new benchmarks
                for metric in output.metrics:
                    benchmark = VerticalBenchmark(
                        id=uuid.uuid4(),
                        vertical=output.vertical,
                        metric_name=metric.metric_name,
                        metric_value=metric.metric_value,
                        sample_size=metric.sample_size,
                        updated_at=now,
                        audit_ids=output.audit_ids_included,
                    )
                    session.add(benchmark)

                await session.commit()

                logger.info(
                    "[InsightsModule] benchmarks persisted",
                    vertical=output.vertical,
                    metrics_inserted=len(output.metrics),
                    deleted_count=deleted_count,
                    audit_id=audit_id,
                )

            except Exception as exc:
                await session.rollback()
                logger.error(
                    "[InsightsModule] benchmark persist failed",
                    vertical=output.vertical,
                    error=str(exc),
                )
                raise
