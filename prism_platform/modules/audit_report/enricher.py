"""Audit Report enricher -- Instructor + Claude for final report synthesis.

Multiple LLM calls:
1. Score 10 search dimensions from techstack + traffic + competitor data
2. Score competitors on the same 10 dimensions
3. Assemble full_audit_data JSON (all module outputs organized by section)
4. Generate PreCallBrief (6 key data points for the AE)
5. Generate LeaveBehind (prospect-safe, NO hiring/buying committee/internal data)
6. Generate audit_summary
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from prism_platform.core.llm import create_completion
from prism_platform.modules.audit_report.schemas import (
    ALL_DIMENSIONS,
    AuditReportOutput,
    CompetitorScore,
    DimensionScore,
    LeaveBehind,
    PreCallBrief,
)

logger = structlog.get_logger(__name__)


class AuditReportEnricher:
    """Synthesizes all upstream module outputs into the final audit report via Claude."""

    def __init__(self) -> None:
        """Initialize the Instructor+Anthropic client."""
        pass

    async def enrich(
        self,
        domain: str,
        company_name: str,
        collected_data: dict[str, Any],
    ) -> tuple[AuditReportOutput, int, float]:
        """Synthesize all upstream data into the final AuditReportOutput.

        Args:
            domain: Domain being audited.
            company_name: Company name from intel-company module.
            collected_data: Dict of all upstream module outputs from collector.

        Returns:
            Tuple of (AuditReportOutput, total_llm_calls, total_llm_cost_usd).

        Raises:
            Exception: If any LLM call fails after retries.
        """
        logger.info(
            "[AuditReportEnricher] enrich started",
            domain=domain,
            modules_available=collected_data.get("modules_found", []),
        )

        total_llm_calls = 0
        total_cost = 0.0

        # Step 1: Score 10 dimensions
        dimension_scores, calls_1, cost_1 = await self._score_dimensions(
            domain, company_name, collected_data
        )
        total_llm_calls += calls_1
        total_cost += cost_1

        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_scores)
        score_methodology = (
            "Weighted average of 10 search quality dimensions. "
            "Relevance, speed, and zero_result_handling weighted 1.5x. "
            "All scores estimated from techstack + traffic data (no browser audit)."
        )

        # Step 2: Score competitors
        competitor_scores, calls_2, cost_2 = await self._score_competitors(
            domain, company_name, collected_data
        )
        total_llm_calls += calls_2
        total_cost += cost_2

        # Calculate industry average
        industry_average = self._calculate_industry_average(competitor_scores)

        # Step 3: Assemble full_audit_data
        full_audit_data = self._assemble_full_audit_data(collected_data)

        # Step 4: Generate PreCallBrief
        pre_call_brief, calls_4, cost_4 = await self._generate_pre_call_brief(
            domain, company_name, overall_score, collected_data
        )
        total_llm_calls += calls_4
        total_cost += cost_4

        # Step 5: Generate LeaveBehind
        leave_behind, calls_5, cost_5 = await self._generate_leave_behind(
            domain, company_name, overall_score, dimension_scores, collected_data
        )
        total_llm_calls += calls_5
        total_cost += cost_5

        # Step 6: Generate audit_summary
        audit_summary, calls_6, cost_6 = await self._generate_audit_summary(
            domain, company_name, overall_score, dimension_scores, collected_data
        )
        total_llm_calls += calls_6
        total_cost += cost_6

        output = AuditReportOutput(
            domain=domain,
            company_name=company_name,
            dimension_scores=dimension_scores,
            overall_score=overall_score,
            score_methodology=score_methodology,
            competitor_scores=competitor_scores,
            industry_average_score=industry_average,
            full_audit_data=full_audit_data,
            pre_call_brief=pre_call_brief,
            leave_behind=leave_behind,
            audit_summary=audit_summary,
        )

        logger.info(
            "[AuditReportEnricher] enrich completed",
            domain=domain,
            overall_score=overall_score,
            dimension_count=len(dimension_scores),
            competitor_count=len(competitor_scores),
            total_llm_calls=total_llm_calls,
            total_cost_usd=round(total_cost, 4),
        )

        return output, total_llm_calls, round(total_cost, 4)

    async def _score_dimensions(
        self,
        domain: str,
        company_name: str,
        collected_data: dict[str, Any],
    ) -> tuple[list[DimensionScore], int, float]:
        """Score the prospect on 10 search quality dimensions using Claude.

        Args:
            domain: Domain being audited.
            company_name: Company name.
            collected_data: All upstream module outputs.

        Returns:
            Tuple of (list of DimensionScore, llm_calls, cost_usd).
        """
        logger.info("[AuditReportEnricher] scoring 10 dimensions", domain=domain)

        techstack = collected_data.get("intel-techstack", {})
        traffic = collected_data.get("intel-traffic", {})
        competitors = collected_data.get("intel-competitors", {})
        company = collected_data.get("intel-company", {})

        prompt = f"""You are scoring the search quality of {company_name} ({domain}) across 10 dimensions.

## Available Data

### Tech Stack:
{json.dumps(techstack, indent=2, default=str)[:8000]}

### Traffic & Engagement:
{json.dumps(traffic, indent=2, default=str)[:4000]}

### Competitor Data:
{json.dumps(competitors, indent=2, default=str)[:4000]}

### Company Profile:
{json.dumps(company, indent=2, default=str)[:3000]}

## Instructions

Score EACH of these 10 dimensions from 0-10:
{", ".join(ALL_DIMENSIONS)}

For each dimension:
- Score 0-3 = critical severity
- Score 4-5 = major severity
- Score 6-7 = minor severity
- Score 8-10 = ok severity
- Provide specific evidence for each score
- Mark ALL as is_estimated=True (no browser audit data available)

Be realistic. Without browser audit data, be conservative in scoring.
Most dimensions without direct evidence should score 3-6."""

        try:
            result = create_completion(
                response_model=list[DimensionScore],
                max_retries=3,
                messages=[{"role": "user", "content": prompt}],
            )

            # Ensure all 10 dimensions are represented
            scored_dims = {ds.dimension for ds in result}
            missing_dims = set(ALL_DIMENSIONS) - scored_dims

            for dim in missing_dims:
                logger.warning(
                    "[AuditReportEnricher] dimension missing from LLM output, adding default",
                    dimension=dim,
                    domain=domain,
                )
                result.append(
                    DimensionScore(
                        dimension=dim,  # type: ignore[arg-type]
                        score=4.0,
                        evidence=f"No data available to score {dim}. Default score applied.",
                        severity="major",
                        is_estimated=True,
                    )
                )

            cost = self._estimate_cost(prompt, json.dumps([ds.model_dump() for ds in result]))
            logger.info(
                "[AuditReportEnricher] dimension scoring complete",
                domain=domain,
                dimensions_scored=len(result),
            )
            return result, 1, cost

        except Exception as exc:
            logger.exception(
                "[AuditReportEnricher] dimension scoring failed",
                domain=domain,
                error=str(exc),
            )
            raise

    async def _score_competitors(
        self,
        domain: str,
        company_name: str,
        collected_data: dict[str, Any],
    ) -> tuple[list[CompetitorScore], int, float]:
        """Score competitors on the same 10 dimensions.

        Args:
            domain: Domain being audited.
            company_name: Company name.
            collected_data: All upstream module outputs.

        Returns:
            Tuple of (list of CompetitorScore, llm_calls, cost_usd).
        """
        logger.info("[AuditReportEnricher] scoring competitors", domain=domain)

        competitors_data = collected_data.get("intel-competitors", {})
        techstack = collected_data.get("intel-techstack", {})

        # Extract competitor list
        competitor_list = competitors_data.get("competitors", [])
        if not competitor_list:
            logger.warning(
                "[AuditReportEnricher] no competitor data available for scoring",
                domain=domain,
            )
            return [], 0, 0.0

        prompt = f"""You are scoring the search quality of competitors of {company_name} ({domain}).

## Competitor Data:
{json.dumps(competitor_list, indent=2, default=str)[:6000]}

## Tech Stack Context:
{json.dumps(techstack, indent=2, default=str)[:4000]}

## Instructions

For each competitor, score them on the same 10 dimensions:
{", ".join(ALL_DIMENSIONS)}

Return a list of CompetitorScore objects. For each competitor:
- Include their company_name and domain
- Score each dimension 0-10 with evidence and severity
- Calculate an overall_score (average of all dimensions)
- Mark ALL as is_estimated=True

Score based on their known search technology and traffic patterns.
If a competitor uses Algolia, score them higher on relevant dimensions.
Be realistic and conservative."""

        try:
            result = create_completion(
                response_model=list[CompetitorScore],
                max_retries=3,
                messages=[{"role": "user", "content": prompt}],
            )

            cost = self._estimate_cost(prompt, json.dumps([cs.model_dump() for cs in result]))
            logger.info(
                "[AuditReportEnricher] competitor scoring complete",
                domain=domain,
                competitors_scored=len(result),
            )
            return result, 1, cost

        except Exception as exc:
            logger.exception(
                "[AuditReportEnricher] competitor scoring failed",
                domain=domain,
                error=str(exc),
            )
            raise

    async def _generate_pre_call_brief(
        self,
        domain: str,
        company_name: str,
        overall_score: float | None,
        collected_data: dict[str, Any],
    ) -> tuple[PreCallBrief, int, float]:
        """Generate the 60-second AE pre-call brief.

        Args:
            domain: Domain being audited.
            company_name: Company name.
            overall_score: Overall search quality score.
            collected_data: All upstream module outputs.

        Returns:
            Tuple of (PreCallBrief, llm_calls, cost_usd).
        """
        logger.info("[AuditReportEnricher] generating pre-call brief", domain=domain)

        investor = collected_data.get("intel-investor", {})
        news = collected_data.get("intel-news", {})
        partner = collected_data.get("intel-partner", {})
        hiring = collected_data.get("intel-hiring", {})
        business_case = collected_data.get("synth-business-case", {})
        sales_plays = collected_data.get("synth-sales-plays", {})

        prompt = f"""You are creating a 60-second pre-call brief for an Algolia AE about {company_name} ({domain}).

Overall search quality score: {overall_score or "unknown"}/10

## Investor Intelligence:
{json.dumps(investor, indent=2, default=str)[:3000]}

## News Signals:
{json.dumps(news, indent=2, default=str)[:2000]}

## Partner Data:
{json.dumps(partner, indent=2, default=str)[:2000]}

## Hiring Signals:
{json.dumps(hiring, indent=2, default=str)[:2000]}

## Business Case:
{json.dumps(business_case, indent=2, default=str)[:3000]}

## Sales Plays:
{json.dumps(sales_plays, indent=2, default=str)[:2000]}

## Instructions

Create a PreCallBrief with these 6 fields:
1. company_name: "{company_name}"
2. search_score: The overall search quality score (0-10)
3. top_angle: The single strongest angle for the conversation
4. key_exec_to_reference: A specific executive quote to reference (e.g. "CFO Jane Smith said on Q4 call: 'digital is our priority'")
5. partner_play: If there's a partner ecosystem opportunity, describe it. Otherwise null.
6. most_urgent_signal: The most time-sensitive signal (hiring, news, competitor move)
7. recommended_first_play: What the AE should lead with

Be concise. The AE has 60 seconds to read this before the call."""

        try:
            result = create_completion(
                response_model=PreCallBrief,
                max_retries=3,
                messages=[{"role": "user", "content": prompt}],
            )

            cost = self._estimate_cost(prompt, result.model_dump_json())
            logger.info(
                "[AuditReportEnricher] pre-call brief generated",
                domain=domain,
            )
            return result, 1, cost

        except Exception as exc:
            logger.exception(
                "[AuditReportEnricher] pre-call brief generation failed",
                domain=domain,
                error=str(exc),
            )
            raise

    async def _generate_leave_behind(
        self,
        domain: str,
        company_name: str,
        overall_score: float | None,
        dimension_scores: list[DimensionScore],
        collected_data: dict[str, Any],
    ) -> tuple[LeaveBehind, int, float]:
        """Generate the 3-page prospect-safe leave-behind document.

        IMPORTANT: The leave-behind must NOT contain:
        - Hiring signals
        - Buying committee information
        - Internal strategy data
        - Competitor names (use anonymized labels like "Competitor A")

        Args:
            domain: Domain being audited.
            company_name: Company name.
            overall_score: Overall search quality score.
            dimension_scores: Scored dimensions.
            collected_data: All upstream module outputs.

        Returns:
            Tuple of (LeaveBehind, llm_calls, cost_usd).
        """
        logger.info("[AuditReportEnricher] generating leave-behind", domain=domain)

        business_case = collected_data.get("synth-business-case", {})
        techstack = collected_data.get("intel-techstack", {})
        traffic = collected_data.get("intel-traffic", {})

        scores_summary = "\n".join(
            f"- {ds.dimension}: {ds.score}/10 ({ds.severity}) -- {ds.evidence[:100]}"
            for ds in dimension_scores
        )

        prompt = f"""You are creating a prospect-safe leave-behind document for {company_name} ({domain}).

Overall search quality score: {overall_score or "unknown"}/10

## Dimension Scores:
{scores_summary}

## Tech Stack (safe to reference):
{json.dumps(techstack, indent=2, default=str)[:3000]}

## Traffic (safe to reference general trends):
{json.dumps(traffic, indent=2, default=str)[:2000]}

## Business Case ROI:
{json.dumps(business_case, indent=2, default=str)[:3000]}

## CRITICAL RULES:
- Do NOT include hiring signals
- Do NOT include buying committee information
- Do NOT name competitors -- use "Competitor A", "Competitor B", etc.
- Do NOT include internal strategy data or executive quotes
- This document will be shared WITH the prospect

## Instructions

Create a LeaveBehind with:
1. search_quality_summary: 2-3 paragraph summary of search quality findings
2. competitive_benchmark: Anonymized benchmark (e.g. "Your search scores 5.2/10 vs industry avg 6.8/10")
3. top_3_recommendations: Exactly 3 actionable recommendations
4. roi_summary: ROI potential from the business case
5. next_steps: Recommended next steps for the prospect

Keep it professional, data-driven, and actionable."""

        try:
            result = create_completion(
                response_model=LeaveBehind,
                max_retries=3,
                messages=[{"role": "user", "content": prompt}],
            )

            cost = self._estimate_cost(prompt, result.model_dump_json())
            logger.info(
                "[AuditReportEnricher] leave-behind generated",
                domain=domain,
                recommendations_count=len(result.top_3_recommendations),
            )
            return result, 1, cost

        except Exception as exc:
            logger.exception(
                "[AuditReportEnricher] leave-behind generation failed",
                domain=domain,
                error=str(exc),
            )
            raise

    async def _generate_audit_summary(
        self,
        domain: str,
        company_name: str,
        overall_score: float | None,
        dimension_scores: list[DimensionScore],
        collected_data: dict[str, Any],
    ) -> tuple[str, int, float]:
        """Generate the executive audit summary.

        Args:
            domain: Domain being audited.
            company_name: Company name.
            overall_score: Overall search quality score.
            dimension_scores: Scored dimensions.
            collected_data: All upstream module outputs.

        Returns:
            Tuple of (audit_summary string, llm_calls, cost_usd).
        """
        logger.info("[AuditReportEnricher] generating audit summary", domain=domain)

        # Gather key data points
        critical_dims = [ds for ds in dimension_scores if ds.severity == "critical"]
        major_dims = [ds for ds in dimension_scores if ds.severity == "major"]
        business_case = collected_data.get("synth-business-case", {})

        prompt = f"""Write a 3-4 paragraph executive summary for the {company_name} ({domain}) search audit.

Overall score: {overall_score or "unknown"}/10
Critical issues ({len(critical_dims)}): {", ".join(d.dimension for d in critical_dims) or "none"}
Major issues ({len(major_dims)}): {", ".join(d.dimension for d in major_dims) or "none"}

Business case summary:
{json.dumps(business_case, indent=2, default=str)[:3000]}

Modules available: {collected_data.get("modules_found", [])}

Write for an Algolia AE audience. Include:
1. Opening: Company context and why this audit matters
2. Key findings: Top 3-4 search quality issues with severity
3. Opportunity: Revenue impact and competitive angle
4. Recommendation: What to do next

Be specific with numbers. No generic filler."""

        try:
            # For the summary, we use a simple string response
            # Wrap in a helper model for Instructor
            from pydantic import BaseModel as _BaseModel

            class _SummaryWrapper(_BaseModel):
                summary: str

            result = create_completion(
                response_model=_SummaryWrapper,
                max_retries=3,
                messages=[{"role": "user", "content": prompt}],
            )

            cost = self._estimate_cost(prompt, result.summary)
            logger.info(
                "[AuditReportEnricher] audit summary generated",
                domain=domain,
                summary_length=len(result.summary),
            )
            return result.summary, 1, cost

        except Exception as exc:
            logger.exception(
                "[AuditReportEnricher] audit summary generation failed",
                domain=domain,
                error=str(exc),
            )
            raise

    def _assemble_full_audit_data(self, collected_data: dict[str, Any]) -> dict[str, object]:
        """Assemble all module outputs into a structured full_audit_data dict.

        Organizes module outputs by section for easy consumption by
        downstream templates and deliverable generators.

        Args:
            collected_data: All upstream module outputs from collector.

        Returns:
            Organized dict with sections: intelligence, synthesis, metadata.
        """
        logger.info("[AuditReportEnricher] assembling full audit data")

        intelligence: dict[str, object] = {}
        synthesis: dict[str, object] = {}

        for module_name, output in collected_data.items():
            if module_name in ("modules_found", "modules_missing"):
                continue
            if module_name.startswith("intel-"):
                intelligence[module_name] = output
            elif module_name.startswith("synth-"):
                synthesis[module_name] = output

        full_data: dict[str, object] = {
            "intelligence": intelligence,
            "synthesis": synthesis,
            "metadata": {
                "modules_found": collected_data.get("modules_found", []),
                "modules_missing": collected_data.get("modules_missing", []),
                "total_modules": len(collected_data.get("modules_found", [])),
            },
        }

        logger.info(
            "[AuditReportEnricher] full audit data assembled",
            intelligence_modules=len(intelligence),
            synthesis_modules=len(synthesis),
        )

        return full_data

    @staticmethod
    def _calculate_overall_score(dimension_scores: list[DimensionScore]) -> float | None:
        """Calculate weighted average of dimension scores.

        Weights: relevance, speed, zero_result_handling get 1.5x weight.
        All others get 1.0x weight.

        Args:
            dimension_scores: List of scored dimensions.

        Returns:
            Weighted average score, or None if no scores.
        """
        if not dimension_scores:
            return None

        high_weight_dims = {"relevance", "speed", "zero_result_handling"}
        total_weight = 0.0
        weighted_sum = 0.0

        for ds in dimension_scores:
            weight = 1.5 if ds.dimension in high_weight_dims else 1.0
            weighted_sum += ds.score * weight
            total_weight += weight

        if total_weight == 0:
            return None

        return round(weighted_sum / total_weight, 1)

    @staticmethod
    def _calculate_industry_average(
        competitor_scores: list[CompetitorScore],
    ) -> float | None:
        """Calculate the industry average score from competitor scores.

        Args:
            competitor_scores: List of scored competitors.

        Returns:
            Average of competitor overall_scores, or None if no data.
        """
        scores = [cs.overall_score for cs in competitor_scores if cs.overall_score is not None]
        if not scores:
            return None
        return round(sum(scores) / len(scores), 1)

    @staticmethod
    def _estimate_cost(input_text: str, output_text: str) -> float:
        """Estimate Claude API cost.

        Claude Sonnet: ~$0.10/1M input tokens, ~$0.40/1M output tokens.
        Rough approximation: 1 token ~= 4 characters.

        Args:
            input_text: The input prompt text.
            output_text: The output response text.

        Returns:
            Estimated cost in USD.
        """
        input_tokens = len(input_text) / 4
        output_tokens = len(output_text) / 4
        cost = (input_tokens / 1_000_000 * 0.10) + (output_tokens / 1_000_000 * 0.40)
        return round(cost, 6)
