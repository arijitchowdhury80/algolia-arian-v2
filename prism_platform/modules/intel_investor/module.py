"""Intel Investor module -- investor intelligence for Algolia sales enablement.

This module is THE MOST IMPORTANT intelligence module. It produces the
"Said vs Found" deliverable that maps executive earnings call quotes to
Algolia sales angles.

Data flow:
1. Check if company is public or private
2. Collector: Perplexity (earnings transcripts, YouTube, board) + SEC EDGAR (risk factors)
3. Enricher: Instructor + Claude (quote extraction, Said vs Found, board analysis, etc.)
4. Validator: 10 quality checks

Dependencies:
- intel-company: for company_name, ticker, is_private, executives, competitor_domains
- intel-financial-public: for ticker confirmation and financial context
"""

from __future__ import annotations

import time
from typing import ClassVar

import structlog

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import EvidenceTier, ModuleResult, Source, ValidationResult
from prism_platform.modules.intel_investor.collector import InvestorCollector
from prism_platform.modules.intel_investor.enricher import InvestorEnricher
from prism_platform.modules.intel_investor.schemas import (
    InvestorInput,
    InvestorOutput,
)
from prism_platform.modules.intel_investor.validator import validate_output

logger = structlog.get_logger(__name__)


class InvestorModule(ModuleInterface):
    """Investor intelligence module -- earnings quotes, Said vs Found, and executive intel.

    Produces: earnings call quotes, Said vs Found mappings, competitor investor intel,
    YouTube appearances, board composition, 10-K risk factors, top sales angles.
    Consumed by: synthesis modules for AE brief, battle card, and sales plays.
    """

    name: ClassVar[str] = "intel-investor"
    version: ClassVar[str] = "0.1.0"
    description: ClassVar[str] = (
        "Investor intelligence module: earnings call quotes, Said vs Found mappings, "
        "competitor investor intel, board composition, and 10-K risk factors."
    )
    layer: ClassVar[str] = "intelligence"

    input_schema: ClassVar[type[InvestorInput]] = InvestorInput
    output_schema: ClassVar[type[InvestorOutput]] = InvestorOutput
    dependencies: ClassVar[list[str]] = ["intel-company", "intel-financial-public"]
    requires_llm: ClassVar[bool] = True

    timeout_seconds: ClassVar[int] = 600  # 10 minutes -- heavy LLM work
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        self._collector = InvestorCollector()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run full investor intelligence collection and enrichment.

        Steps:
        1. Determine public vs private strategy
        2. Collect earnings transcripts (or private company fallback)
        3. Extract and structure quotes
        4. Generate Said vs Found mappings (THE CORE DELIVERABLE)
        5. Collect competitor intel, board, risk factors, YouTube
        6. Generate summary and top sales angles

        Args:
            context: Execution context with domain, ticker, company_name, is_private.

        Returns:
            ModuleResult containing InvestorOutput and source provenance.
        """
        logger.info(
            "[InvestorModule] execute started",
            domain=context.domain,
            company_name=context.company_name,
            ticker=context.ticker,
            is_private=context.is_private,
            audit_id=context.audit_id,
        )
        start_ms = time.monotonic_ns() // 1_000_000
        sources: list[Source] = []
        enricher = InvestorEnricher()

        try:
            # Determine strategy based on public vs private
            is_public = not context.is_private and context.ticker is not None

            if is_public:
                output = await self._execute_public(context, enricher, sources)
            else:
                output = await self._execute_private(context, enricher, sources)

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            total_llm_calls = enricher.llm_calls + self._collector.perplexity_calls
            total_cost = enricher.llm_cost

            result = ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="success",
                output=output.model_dump(),
                sources=sources,
                duration_ms=duration_ms,
                llm_calls=total_llm_calls,
                llm_cost_usd=total_cost,
            )

            logger.info(
                "[InvestorModule] execute completed",
                domain=context.domain,
                status="success",
                duration_ms=duration_ms,
                llm_calls=total_llm_calls,
                llm_cost_usd=total_cost,
                prospect_quotes=len(output.prospect_quotes),
                said_vs_found=len(output.said_vs_found),
                competitors=len(output.competitor_intel),
                board_members=len(output.board_members),
                risk_factors=len(output.risk_factors),
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.exception(
                "[InvestorModule] execute failed",
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

    async def _execute_public(
        self,
        context: ExecutionContext,
        enricher: InvestorEnricher,
        sources: list[Source],
    ) -> InvestorOutput:
        """Execute investor intelligence for a public company.

        Args:
            context: Execution context.
            enricher: InvestorEnricher instance.
            sources: Source list to append to.

        Returns:
            InvestorOutput with all sections populated.
        """
        ticker = context.ticker or ""
        company_name = context.company_name
        executives = self._get_executives(context)
        competitors = self._get_competitors(context)

        # Step 1: Collect earnings transcripts
        transcript_texts = await self._collector.collect_earnings_transcripts(
            company_name, ticker, executives
        )
        if transcript_texts:
            sources.append(
                Source(
                    field="prospect_quotes",
                    value=f"Perplexity: {len(transcript_texts)} quarters of transcripts",
                    tier=EvidenceTier.VERIFIED,
                    source_label="Perplexity API (earnings call transcripts)",
                    method="llm_extraction",
                )
            )

        # Step 2: Extract quotes from transcripts
        prospect_quotes = await enricher.extract_earnings_quotes(transcript_texts, company_name)

        # Step 3: Generate Said vs Found mappings (THE CORE DELIVERABLE)
        said_vs_found = await enricher.generate_said_vs_found(prospect_quotes, company_name)
        if said_vs_found:
            sources.append(
                Source(
                    field="said_vs_found",
                    value=f"Claude: {len(said_vs_found)} mappings generated",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Claude via Instructor (Said vs Found mapping)",
                    method="llm_extraction",
                )
            )

        # Step 4: Collect competitor transcripts
        competitor_transcripts = await self._collector.collect_competitor_transcripts(competitors)
        competitor_intel = await enricher.extract_competitor_intel(
            competitor_transcripts, competitors
        )

        # Step 5: Collect YouTube appearances
        youtube_text = await self._collector.collect_youtube_appearances(company_name, executives)
        youtube_appearances = await enricher.extract_youtube_appearances(youtube_text, company_name)
        if youtube_appearances:
            sources.append(
                Source(
                    field="youtube_appearances",
                    value=f"Perplexity: {len(youtube_appearances)} appearances found",
                    tier=EvidenceTier.WEBFETCH,
                    source_label="Perplexity API (YouTube search)",
                    method="llm_extraction",
                )
            )

        # Step 6: Collect board composition
        board_text = await self._collector.collect_board_composition(company_name)
        board_members = await enricher.extract_board_members(board_text, company_name)
        if board_members:
            sources.append(
                Source(
                    field="board_members",
                    value=f"Perplexity: {len(board_members)} board members found",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Perplexity API (board composition)",
                    method="llm_extraction",
                )
            )

        # Step 7: Collect 10-K risk factors
        risk_text = await self._collector.collect_risk_factors(company_name, ticker)
        risk_factors = await enricher.extract_risk_factors(risk_text, company_name)
        if risk_factors:
            sources.append(
                Source(
                    field="risk_factors",
                    value=f"SEC EDGAR + Perplexity: {len(risk_factors)} risk factors",
                    tier=EvidenceTier.VERIFIED,
                    source_label="SEC EDGAR 10-K via Perplexity analysis",
                    method="llm_extraction",
                )
            )

        # Step 8: Generate summary and top sales angles
        investor_summary, top_sales_angles = await enricher.generate_summary(
            company_name,
            prospect_quotes,
            said_vs_found,
            board_members,
            risk_factors,
            competitor_intel,
        )

        # Build output with computed counts
        commitment_count = sum(1 for q in prospect_quotes if q.is_commitment)
        pain_signal_count = sum(1 for q in prospect_quotes if q.category == "pain_signal")
        board_tech_count = sum(1 for b in board_members if b.has_tech_background)

        return InvestorOutput(
            domain=context.domain,
            ticker=context.ticker,
            prospect_quotes=prospect_quotes,
            commitment_count=commitment_count,
            pain_signal_count=pain_signal_count,
            said_vs_found=said_vs_found,
            competitor_intel=competitor_intel,
            youtube_appearances=youtube_appearances,
            board_members=board_members,
            board_tech_count=board_tech_count,
            risk_factors=risk_factors,
            investor_summary=investor_summary,
            top_sales_angles=top_sales_angles,
        )

    async def _execute_private(
        self,
        context: ExecutionContext,
        enricher: InvestorEnricher,
        sources: list[Source],
    ) -> InvestorOutput:
        """Execute investor intelligence for a private company.

        Uses Perplexity-only strategy to find conference presentations,
        CEO/CTO interviews, and strategic communications.

        Args:
            context: Execution context.
            enricher: InvestorEnricher instance.
            sources: Source list to append to.

        Returns:
            InvestorOutput with available sections populated.
        """
        company_name = context.company_name
        domain = context.domain
        executives = self._get_executives(context)

        logger.info(
            "[InvestorModule] running private company strategy",
            company_name=company_name,
            domain=domain,
        )

        # Collect private company intel
        private_intel = await self._collector.collect_private_company_intel(company_name, domain)

        # Try to extract quotes from presentations/interviews
        all_texts = list(private_intel.values())
        prospect_quotes = await enricher.extract_earnings_quotes(all_texts, company_name)

        if all_texts:
            sources.append(
                Source(
                    field="prospect_quotes",
                    value=f"Perplexity: {len(all_texts)} sections collected (private company)",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Perplexity API (private company research)",
                    method="llm_extraction",
                )
            )

        # Generate Said vs Found even for private companies
        said_vs_found = await enricher.generate_said_vs_found(prospect_quotes, company_name)
        if said_vs_found:
            sources.append(
                Source(
                    field="said_vs_found",
                    value=f"Claude: {len(said_vs_found)} mappings for private company",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Claude via Instructor (Said vs Found mapping)",
                    method="llm_extraction",
                )
            )

        # YouTube appearances
        youtube_text = await self._collector.collect_youtube_appearances(company_name, executives)
        youtube_appearances = await enricher.extract_youtube_appearances(youtube_text, company_name)
        if youtube_appearances:
            sources.append(
                Source(
                    field="youtube_appearances",
                    value=f"Perplexity: {len(youtube_appearances)} appearances",
                    tier=EvidenceTier.WEBFETCH,
                    source_label="Perplexity API (YouTube search)",
                    method="llm_extraction",
                )
            )

        # Board composition (may still be available for private companies)
        board_text = await self._collector.collect_board_composition(company_name)
        board_members = await enricher.extract_board_members(board_text, company_name)

        # Generate summary
        investor_summary, top_sales_angles = await enricher.generate_summary(
            company_name,
            prospect_quotes,
            said_vs_found,
            board_members,
            [],  # No risk factors for private companies
            [],  # No competitor intel for private companies
        )

        commitment_count = sum(1 for q in prospect_quotes if q.is_commitment)
        pain_signal_count = sum(1 for q in prospect_quotes if q.category == "pain_signal")
        board_tech_count = sum(1 for b in board_members if b.has_tech_background)

        return InvestorOutput(
            domain=domain,
            ticker=None,
            prospect_quotes=prospect_quotes,
            commitment_count=commitment_count,
            pain_signal_count=pain_signal_count,
            said_vs_found=said_vs_found,
            youtube_appearances=youtube_appearances,
            board_members=board_members,
            board_tech_count=board_tech_count,
            investor_summary=investor_summary,
            top_sales_angles=top_sales_angles,
        )

    async def validate(self, result: ModuleResult) -> ValidationResult:
        """Validate module output meets quality standards (10 checks).

        Args:
            result: The ModuleResult from execute().

        Returns:
            ValidationResult with pass/fail and diagnostic details.
        """
        logger.info("[InvestorModule] validate started", module=self.name)

        try:
            output = InvestorOutput.model_validate(result.output)
            return validate_output(
                output,
                result.sources,
                expected_domain=output.domain,
            )
        except Exception as error:
            logger.error(
                "[InvestorModule] validate failed -- output deserialization error",
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

        Perplexity is needed for collection.
        An LLM provider is needed for enrichment.
        """
        from prism_platform.config import settings

        has_perplexity = bool(settings.perplexity_api_key)
        try:
            settings.get_enricher_provider()
            has_llm = True
        except (ValueError, AttributeError):
            has_llm = False

        if not has_perplexity:
            logger.warning("[InvestorModule] PERPLEXITY_API_KEY not set")
        if not has_llm:
            logger.warning("[InvestorModule] No LLM provider configured")

        return has_perplexity and has_llm

    @staticmethod
    def _get_executives(context: ExecutionContext) -> list[str]:
        """Extract executive names from execution context.

        In a full pipeline, this reads from accounts.intelligence populated by
        intel-company. For now, returns empty list.

        Args:
            context: Execution context.

        Returns:
            List of executive names.
        """
        # TODO: Read executives from accounts.intelligence
        logger.info(
            "[InvestorModule] executive lookup not yet implemented",
            domain=context.domain,
        )
        return []

    @staticmethod
    def _get_competitors(context: ExecutionContext) -> list[dict[str, str]]:
        """Extract competitor information from execution context.

        In a full pipeline, this reads from accounts.intelligence populated by
        intel-company. For now, returns empty list.

        Args:
            context: Execution context.

        Returns:
            List of dicts with 'company_name', 'ticker', 'domain' keys.
        """
        # TODO: Read competitor_domains from accounts.intelligence
        logger.info(
            "[InvestorModule] competitor lookup not yet implemented",
            domain=context.domain,
        )
        return []
