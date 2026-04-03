"""Intel TechStack module -- BuiltWith-powered technology stack detection."""

from __future__ import annotations

import time
from typing import ClassVar

import structlog

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import ModuleResult, ValidationResult
from prism_platform.modules.intel_techstack.collector import TechStackCollector
from prism_platform.modules.intel_techstack.schemas import TechStackInput, TechStackOutput
from prism_platform.modules.intel_techstack.validator import validate_output

logger = structlog.get_logger(__name__)


class TechStackModule(ModuleInterface):
    """Technology stack detection via BuiltWith API."""

    name: ClassVar[str] = "intel-techstack"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = "Technology stack detection via BuiltWith API"
    layer: ClassVar[str] = "intelligence"

    input_schema: ClassVar[type[TechStackInput]] = TechStackInput
    output_schema: ClassVar[type[TechStackOutput]] = TechStackOutput
    dependencies: ClassVar[list[str]] = []
    requires_llm: ClassVar[bool] = False

    timeout_seconds: ClassVar[int] = 120
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        self._collector = TechStackCollector()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run tech stack detection for the given domain.

        Args:
            context: Execution context with domain and audit metadata.

        Returns:
            ModuleResult containing TechStackOutput and source provenance.
        """
        logger.info(
            "[TechStack] execute started",
            domain=context.domain,
            audit_id=context.audit_id,
        )
        start_ms = time.monotonic_ns() // 1_000_000

        try:
            # Attempt to read competitor data from accounts.intelligence
            competitor_data: list[dict[str, str]] = []
            try:
                intelligence = getattr(context, "intelligence", None)
                if intelligence and isinstance(intelligence, dict):
                    competitor_domains = intelligence.get("competitor_domains", [])
                    if isinstance(competitor_domains, list) and competitor_domains:
                        competitor_data = [
                            cd
                            for cd in competitor_domains
                            if isinstance(cd, dict) and cd.get("domain")
                        ]
                        logger.info(
                            "[TechStack] found competitor data in context",
                            competitor_count=len(competitor_data),
                        )
            except Exception as intel_err:
                logger.warning(
                    "[TechStack] could not read intelligence data, falling back to prospect-only",
                    error=str(intel_err),
                )

            if competitor_data:
                output, sources = await self._collector.collect_all_with_competitors(
                    prospect_domain=context.domain,
                    competitor_data=competitor_data,
                )
            else:
                output, sources = await self._collector.collect_all(context.domain)

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

            status = "success" if len(output.all_technologies) >= 3 else "partial"

            result = ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status=status,
                output=output.model_dump(),
                sources=sources,
                duration_ms=duration_ms,
                llm_calls=0,
                llm_cost_usd=0.0,
            )

            logger.info(
                "[TechStack] execute completed",
                domain=context.domain,
                status=status,
                duration_ms=duration_ms,
                tech_count=len(output.all_technologies),
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.error(
                "[TechStack] execute failed",
                error=str(error),
                context={"domain": context.domain, "audit_id": context.audit_id},
            )
            return ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="failed",
                output={},
                duration_ms=duration_ms,
                errors=[str(error)],
            )

    async def validate(self, result: ModuleResult) -> ValidationResult:
        """Validate module output meets quality standards.

        Args:
            result: The ModuleResult from execute().

        Returns:
            ValidationResult with pass/fail and diagnostic details.
        """
        logger.info("[TechStack] validate started", module=self.name)

        try:
            output = TechStackOutput.model_validate(result.output)
            return validate_output(output, result.sources)
        except Exception as error:
            logger.error(
                "[TechStack] validate failed",
                error=str(error),
            )
            return ValidationResult(
                passed=False,
                checks_run=0,
                checks_passed=0,
                errors=[f"Output deserialization failed: {error}"],
            )

    async def health_check(self) -> bool:
        """Check if BuiltWith API key is configured."""
        from prism_platform.config import settings

        return bool(settings.builtwith_api_key)
