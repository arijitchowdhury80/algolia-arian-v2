"""Intel News module -- Perplexity-powered news and executive media intelligence."""

from __future__ import annotations

import time
from typing import Any, ClassVar

import structlog
from sqlalchemy import select

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import EvidenceTier, ModuleResult, Source, ValidationResult
from prism_platform.db.models import Account
from prism_platform.db.session import async_session_factory
from prism_platform.modules.intel_news.collector import NewsCollector
from prism_platform.modules.intel_news.enricher import NewsEnricher
from prism_platform.modules.intel_news.schemas import NewsInput, NewsOutput
from prism_platform.modules.intel_news.validator import validate_output

logger = structlog.get_logger(__name__)


def _extract_executives(account: Any) -> list[dict[str, Any]]:
    """Extract executive names from Account.executives JSONB column.

    The intel-company module stores executives as a list of dicts with
    'full_name', 'title', 'relevance' keys. We normalize the key names
    for the collector which expects 'name'.

    Args:
        account: The Account ORM object with executives JSONB column.

    Returns:
        List of executive dicts with 'name', 'title', 'relevance' keys.
    """
    raw_execs: list[dict[str, Any]] = account.executives or []
    normalized: list[dict[str, Any]] = []
    for ex in raw_execs:
        normalized.append(
            {
                "name": ex.get("full_name", ex.get("name", "")),
                "title": ex.get("title", ""),
                "relevance": ex.get("relevance", "other"),
            }
        )
    return normalized


def _extract_competitors(account: Any) -> list[dict[str, Any]]:
    """Extract competitor domains from Account.competitors JSONB column.

    Args:
        account: The Account ORM object with competitors JSONB column.

    Returns:
        List of competitor dicts with 'company_name', 'domain' keys.
    """
    raw_competitors: list[dict[str, Any]] = account.competitors or []
    result: list[dict[str, Any]] = []
    for comp in raw_competitors:
        result.append(
            {
                "company_name": comp.get("company_name", ""),
                "domain": comp.get("domain", ""),
            }
        )
    return result


class NewsModule(ModuleInterface):
    """News and executive media intelligence via Perplexity + Claude.

    Collects company news (90-day sweep), executive interviews and quotes,
    competitor news, and urgency signals. Structures all raw data via
    Instructor + Claude into typed Pydantic schemas.
    """

    name: ClassVar[str] = "intel-news"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = "News and executive media intelligence via Perplexity + Claude"
    layer: ClassVar[str] = "intelligence"

    input_schema: ClassVar[type[NewsInput]] = NewsInput
    output_schema: ClassVar[type[NewsOutput]] = NewsOutput
    dependencies: ClassVar[list[str]] = ["intel-company"]
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 300
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        self._collector = NewsCollector()
        self._enricher = NewsEnricher()

    async def execute(
        self,
        context: ExecutionContext,
        intelligence: dict[str, Any] | None = None,
    ) -> ModuleResult:
        """Run news intelligence collection and enrichment.

        Args:
            context: Execution context with domain and audit metadata.
            intelligence: Deprecated, ignored. Data is read from Account columns.

        Returns:
            ModuleResult containing NewsOutput and source provenance.
        """
        logger.info(
            "[News] execute started",
            domain=context.domain,
            audit_id=context.audit_id,
        )
        start_ms = time.monotonic_ns() // 1_000_000

        try:
            # Read executives and competitors from Account columns
            account = await self._load_account(context.domain)
            if account:
                executives = _extract_executives(account)
                competitors = _extract_competitors(account)
            else:
                logger.warning(
                    "[News] account not found, falling back to basic search",
                    domain=context.domain,
                )
                executives = []
                competitors = []

            # Phase 1: Collect raw data from Perplexity
            raw_data = await self._collector.collect_all(
                domain=context.domain,
                company_name=context.company_name,
                executives=executives,
                competitor_domains=competitors,
            )

            # Phase 2: Enrich with Claude via Instructor
            output, llm_calls, llm_cost = await self._enricher.enrich(
                domain=context.domain,
                company_name=context.company_name,
                raw_data=raw_data,
            )

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

            # Build source provenance
            sources = self._build_sources(output)

            status = "success" if len(output.prospect_articles) >= 1 else "partial"

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
                "[News] execute completed",
                domain=context.domain,
                status=status,
                duration_ms=duration_ms,
                articles_count=len(output.prospect_articles),
                quotes_count=len(output.prospect_exec_quotes),
                signals_count=len(output.urgency_signals),
                sell_signals=output.sell_signal_count,
                high_value_quotes=output.high_value_quote_count,
                llm_calls=llm_calls,
                llm_cost_usd=llm_cost,
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.error(
                "[News] execute failed",
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

    @staticmethod
    async def _load_account(domain: str) -> Account | None:
        """Load Account by domain for extracting executives and competitors.

        Args:
            domain: The prospect domain.

        Returns:
            Account object or None if not found.
        """
        try:
            async with async_session_factory() as session:
                stmt = select(Account).where(Account.domain == domain)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        except Exception as exc:
            logger.warning(
                "[News] failed to load account from DB",
                domain=domain,
                error=str(exc),
            )
            return None

    def _build_sources(self, output: NewsOutput) -> list[Source]:
        """Build source provenance records from the enriched output.

        Args:
            output: The enriched NewsOutput.

        Returns:
            List of Source records for provenance tracking.
        """
        sources: list[Source] = []

        # Source for prospect articles
        if output.prospect_articles:
            sources.append(
                Source(
                    field="prospect_articles",
                    value=f"{len(output.prospect_articles)} articles collected",
                    tier=EvidenceTier.WEBFETCH,
                    source_label="Perplexity sonar-pro",
                    method="llm_extraction",
                    confidence="medium",
                )
            )

        # Source for exec quotes
        if output.prospect_exec_quotes:
            sources.append(
                Source(
                    field="prospect_exec_quotes",
                    value=f"{len(output.prospect_exec_quotes)} exec quotes collected",
                    tier=EvidenceTier.WEBFETCH,
                    source_label="Perplexity sonar-pro",
                    method="llm_extraction",
                    confidence="medium",
                )
            )

        # Source for urgency signals
        if output.urgency_signals:
            sources.append(
                Source(
                    field="urgency_signals",
                    value=f"{len(output.urgency_signals)} signals classified",
                    tier=EvidenceTier.WEBFETCH,
                    source_label="Perplexity sonar-pro + Claude classification",
                    method="llm_extraction",
                    confidence="medium",
                )
            )

        # Source for competitor news
        if output.competitor_news:
            total_comp_articles = sum(len(c.articles) for c in output.competitor_news)
            sources.append(
                Source(
                    field="competitor_news",
                    value=(
                        f"{total_comp_articles} competitor articles "
                        f"across {len(output.competitor_news)} competitors"
                    ),
                    tier=EvidenceTier.WEBFETCH,
                    source_label="Perplexity sonar-pro",
                    method="llm_extraction",
                    confidence="medium",
                )
            )

        return sources

    async def validate(self, result: ModuleResult) -> ValidationResult:
        """Validate module output meets quality standards.

        Args:
            result: The ModuleResult from execute().

        Returns:
            ValidationResult with pass/fail and diagnostic details.
        """
        logger.info("[News] validate started", module=self.name)

        try:
            output = NewsOutput.model_validate(result.output)
            return validate_output(output, result.sources)
        except Exception as error:
            logger.error(
                "[News] validate failed",
                error=str(error),
            )
            return ValidationResult(
                passed=False,
                checks_run=0,
                checks_passed=0,
                errors=[f"Output deserialization failed: {error}"],
            )

    async def health_check(self) -> bool:
        """Check if required API keys are configured.

        Returns:
            True if both Perplexity and an LLM provider are configured.
        """
        from prism_platform.config import settings

        has_perplexity = bool(settings.perplexity_api_key)
        try:
            settings.get_enricher_provider()
            has_llm = True
        except (ValueError, AttributeError):
            has_llm = False

        if not has_perplexity:
            logger.warning("[News] perplexity_api_key is not configured")
        if not has_llm:
            logger.warning("[News] No LLM provider configured")

        return has_perplexity and has_llm
