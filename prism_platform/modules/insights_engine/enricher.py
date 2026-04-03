"""Insights Engine enricher -- Claude analysis for vertical benchmarking.

Uses Instructor + Claude Sonnet to analyze patterns across audits
in the same vertical. Produces anonymized VerticalMetric objects.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from prism_platform.core.llm import create_completion
from prism_platform.modules.insights_engine.schemas import InsightsOutput

logger = structlog.get_logger(__name__)


class InsightsEnricher:
    """Analyzes cross-audit patterns via Claude Sonnet."""

    def __init__(self) -> None:
        pass

    async def enrich(
        self,
        domain: str,
        vertical: str,
        current_audit: dict[str, Any],
        historical_audits: list[dict[str, Any]],
        historical_audit_ids: list[str],
        total_audits: int,
    ) -> tuple[InsightsOutput, int, float]:
        """Analyze patterns across audits and produce vertical metrics.

        Args:
            domain: The current audit domain.
            vertical: The vertical classification.
            current_audit: Current audit's module outputs.
            historical_audits: List of historical audit module outputs.
            historical_audit_ids: List of historical audit ID strings.
            total_audits: Total audits in this vertical.

        Returns:
            Tuple of (InsightsOutput, llm_calls, cost_usd).
        """
        logger.info(
            "[InsightsEnricher] enrich started",
            domain=domain,
            vertical=vertical,
            total_audits=total_audits,
        )

        is_first = total_audits <= 1
        all_audit_data = [current_audit, *historical_audits]
        all_audit_ids = historical_audit_ids  # Current audit ID added by module

        try:
            prompt = self._build_prompt(
                vertical=vertical,
                all_audit_data=all_audit_data,
                total_audits=total_audits,
                is_first=is_first,
            )
            logger.info(
                "[InsightsEnricher] Claude call started",
                domain=domain,
                prompt_chars=len(prompt),
                est_input_tokens=len(prompt) // 4,
                audit_data_count=len(all_audit_data),
            )

            result = create_completion(
                response_model=InsightsOutput,
                max_retries=3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )

            # Override fields that must come from our data, not the LLM
            result = InsightsOutput(
                domain=domain,
                vertical=vertical,
                metrics=result.metrics,
                audit_ids_included=all_audit_ids,
                total_audits_in_vertical=total_audits,
                summary=result.summary,
                is_first_in_vertical=is_first,
            )

            output_chars = len(result.model_dump_json())
            estimated_cost = (len(prompt) / 4 / 1_000_000 * 0.10) + (
                output_chars / 4 / 1_000_000 * 0.40
            )
            logger.info(
                "[InsightsEnricher] enrich completed",
                domain=domain,
                vertical=vertical,
                metrics_count=len(result.metrics),
                is_first=is_first,
                est_input_tokens=len(prompt) // 4,
                est_output_tokens=output_chars // 4,
                est_cost_usd=round(estimated_cost, 6),
            )

            return result, 1, round(estimated_cost, 4)

        except Exception as exc:
            logger.exception(
                "[InsightsEnricher] enrich failed",
                domain=domain,
                vertical=vertical,
                error=str(exc),
            )
            # Return minimal valid output on failure
            fallback = InsightsOutput(
                domain=domain,
                vertical=vertical,
                metrics=[],
                audit_ids_included=all_audit_ids,
                total_audits_in_vertical=total_audits,
                summary=f"Analysis failed: {type(exc).__name__}",
                is_first_in_vertical=is_first,
            )
            return fallback, 1, 0.0

    def _build_prompt(
        self,
        vertical: str,
        all_audit_data: list[dict[str, Any]],
        total_audits: int,
        is_first: bool,
    ) -> str:
        """Build the analysis prompt for Claude.

        Args:
            vertical: The vertical name.
            all_audit_data: All audit module outputs to analyze.
            total_audits: Total number of audits.
            is_first: Whether this is the first audit in the vertical.

        Returns:
            The prompt string.
        """
        # Truncate data to avoid token limits
        truncated_data = json.dumps(all_audit_data, default=str)[:30000]

        return f"""You are analyzing {total_audits} audit(s) in the "{vertical}" vertical.
{"This is the FIRST audit in this vertical -- base metrics on this single audit only." if is_first else f"There are {total_audits} audits to compare."}

Analyze the audit data below and produce ANONYMIZED vertical benchmark metrics.
CRITICAL: Do NOT include any company names, domains, or identifying information in metric values.
Only include aggregated/averaged values.

Produce these metrics:
1. avg_search_quality_score -- average search quality from audit-report dimension scores
2. most_common_search_vendor -- most frequent search vendor from intel-techstack outputs
3. most_common_missing_capabilities -- common weak areas from audit-report dimension scores
4. avg_digital_revenue_share -- average digital/ecommerce revenue share from financial modules
5. tech_stack_patterns -- common platforms and technologies from intel-techstack
6. hiring_patterns -- build vs buy signals from intel-hiring
7. traffic_patterns -- average monthly visits, bounce rate from intel-traffic

For each metric provide:
- metric_name: one of the names above
- metric_value: a dict with the aggregated data (NO company names or domains)
- sample_size: how many audits contributed data for this metric
- description: human-readable explanation

Also provide a summary paragraph describing the vertical's overall patterns.
Do NOT mention any company names or domains in the summary.

Audit data (anonymized):
{truncated_data}"""
