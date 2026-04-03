"""Intel Financial Private enricher -- structures raw Perplexity responses via Instructor + Claude.

Takes 6 raw waterfall responses and produces structured RevenueWaterfall,
FundingData, EmployeeRevenueModel, and CompetitorRevenueEstimate objects.
"""

from __future__ import annotations

import structlog
from pydantic import ValidationError

from prism_platform.core.llm import create_completion
from prism_platform.modules.intel_financial_private.schemas import (
    CompetitorRevenueEstimate,
    EmployeeRevenueModel,
    FundingData,
    RevenueWaterfall,
)

logger = structlog.get_logger(__name__)


def _build_enrichment_prompt(
    company_name: str,
    domain: str,
    waterfall_responses: list[dict[str, str]],
) -> str:
    """Build the LLM prompt that structures raw waterfall data.

    Args:
        company_name: The company being analyzed.
        domain: The company domain.
        waterfall_responses: List of dicts with 'label' and 'content' keys.

    Returns:
        A prompt string for the Claude model.
    """
    sources_text = ""
    for idx, resp in enumerate(waterfall_responses, 1):
        sources_text += f"\n--- Source {idx}: {resp['label']} ---\n{resp['content']}\n"

    return f"""You are a financial analyst structuring revenue intelligence for {company_name} ({domain}).

Below are 6 research source responses. Extract ALL revenue estimates, funding data, and benchmarks into the structured schema.

RULES:
- Extract every specific dollar amount mentioned, with its source and methodology.
- For best_estimate: use the median of available numeric estimates, weighted toward higher-confidence sources.
- Set range_low to the lowest estimate and range_high to the highest.
- For best_estimate_methodology: explain which sources you weighted and why.
- For confidence: "high" = multiple independent sources agree, "medium" = single credible source, "low" = derived or uncertain.
- For evidence_tier: use "WEBSEARCH" for Perplexity-sourced data, "ESTIMATE" for derived/calculated values.
- All dollar amounts must be in USD as floats (e.g., 1200000.0 not "$1.2M").
- If a source returned an error or no useful data, skip it.

SOURCES:
{sources_text}

Structure this into the RevenueWaterfall schema with all available estimates.
"""


def _build_funding_prompt(
    company_name: str,
    domain: str,
    funding_response: str,
) -> str:
    """Build prompt to extract funding data from the Crunchbase/PitchBook source.

    Args:
        company_name: The company being analyzed.
        domain: The company domain.
        funding_response: Raw response from the funding research query.

    Returns:
        A prompt string for the Claude model.
    """
    return f"""Extract funding information for {company_name} ({domain}) from the following research:

{funding_response}

RULES:
- All dollar amounts in USD as floats.
- Dates in ISO format (YYYY-MM-DD) if available, otherwise best approximation.
- Set source to the name of the data source (e.g., "Crunchbase", "PitchBook").
- If data is not available for a field, leave it as null.
"""


def _build_employee_model_prompt(
    company_name: str,
    domain: str,
    employee_response: str,
) -> str:
    """Build prompt to extract employee-based revenue model.

    Args:
        company_name: The company being analyzed.
        domain: The company domain.
        employee_response: Raw response from the employee count query.

    Returns:
        A prompt string for the Claude model.
    """
    return f"""Extract employee count and revenue-per-employee model for {company_name} ({domain}):

{employee_response}

RULES:
- employee_count: the actual number of employees mentioned.
- revenue_per_employee: the industry benchmark figure in USD.
- estimated_revenue: employee_count * revenue_per_employee.
- vertical_benchmark: describe the benchmark used, e.g. "SaaS average: $200K/employee".
- confidence: "low" unless multiple sources confirm the employee count.
"""


def _build_competitor_prompt(
    company_name: str,
    domain: str,
    competitor_response: str,
) -> str:
    """Build prompt to extract competitor revenue estimates.

    Args:
        company_name: The company being analyzed.
        domain: The company domain.
        competitor_response: Raw response from the competitor comparison query.

    Returns:
        A prompt string for the Claude model.
    """
    return f"""Extract competitor revenue estimates from the following research about {company_name} ({domain}) competitors:

{competitor_response}

RULES:
- Return a JSON array of competitor objects.
- Each must have: company_name, domain, estimated_revenue (USD float or null), methodology, confidence.
- Only include competitors where some revenue information was found.
- Do NOT include {company_name} itself.
"""


class FinancialPrivateEnricher:
    """Structures raw Perplexity waterfall data using Instructor + Claude."""

    async def enrich_waterfall(
        self,
        company_name: str,
        domain: str,
        waterfall_responses: list[dict[str, str]],
    ) -> tuple[
        RevenueWaterfall | None,
        FundingData | None,
        EmployeeRevenueModel | None,
        list[CompetitorRevenueEstimate],
    ]:
        """Structure all waterfall responses into typed output.

        Args:
            company_name: Company being analyzed.
            domain: Company domain.
            waterfall_responses: The 6 raw Perplexity responses.

        Returns:
            Tuple of (RevenueWaterfall, FundingData, EmployeeRevenueModel, list[CompetitorRevenueEstimate]).
        """
        logger.info(
            "[FinancialPrivate] enrich_waterfall started",
            company_name=company_name,
            domain=domain,
            source_count=len(waterfall_responses),
        )

        waterfall = await self._extract_waterfall(company_name, domain, waterfall_responses)
        funding = await self._extract_funding(company_name, domain, waterfall_responses)
        employee_model = await self._extract_employee_model(
            company_name, domain, waterfall_responses
        )
        competitors = await self._extract_competitors(company_name, domain, waterfall_responses)

        logger.info(
            "[FinancialPrivate] enrich_waterfall completed",
            domain=domain,
            has_waterfall=waterfall is not None,
            has_funding=funding is not None,
            has_employee_model=employee_model is not None,
            competitor_count=len(competitors),
        )

        return waterfall, funding, employee_model, competitors

    async def _extract_waterfall(
        self,
        company_name: str,
        domain: str,
        waterfall_responses: list[dict[str, str]],
    ) -> RevenueWaterfall | None:
        """Extract structured RevenueWaterfall from all sources.

        Args:
            company_name: Company being analyzed.
            domain: Company domain.
            waterfall_responses: All 6 raw responses.

        Returns:
            RevenueWaterfall or None if extraction fails.
        """
        prompt = _build_enrichment_prompt(company_name, domain, waterfall_responses)

        try:
            result: RevenueWaterfall = create_completion(
                response_model=RevenueWaterfall,
                max_retries=3,
                messages=[{"role": "user", "content": prompt}],
            )
            logger.info(
                "[FinancialPrivate] waterfall extraction success",
                domain=domain,
                estimate_count=len(result.estimates),
                best_estimate=result.best_estimate,
            )
            return result

        except ValidationError as ve:
            logger.error(
                "[FinancialPrivate] waterfall extraction validation failed",
                domain=domain,
                error=str(ve),
            )
            return None
        except Exception:
            logger.exception(
                "[FinancialPrivate] waterfall extraction failed",
                domain=domain,
            )
            return None

    async def _extract_funding(
        self,
        company_name: str,
        domain: str,
        waterfall_responses: list[dict[str, str]],
    ) -> FundingData | None:
        """Extract FundingData from the funding source response.

        Args:
            company_name: Company being analyzed.
            domain: Company domain.
            waterfall_responses: All 6 raw responses.

        Returns:
            FundingData or None if extraction fails.
        """
        funding_response = self._find_response(waterfall_responses, "Crunchbase")
        if not funding_response or funding_response.startswith("[ERROR"):
            logger.warning(
                "[FinancialPrivate] no valid funding response to extract",
                domain=domain,
            )
            return None

        prompt = _build_funding_prompt(company_name, domain, funding_response)

        try:
            result: FundingData = create_completion(
                response_model=FundingData,
                max_retries=3,
                messages=[{"role": "user", "content": prompt}],
            )
            logger.info(
                "[FinancialPrivate] funding extraction success",
                domain=domain,
                total_funding=result.total_funding,
            )
            return result

        except ValidationError as ve:
            logger.error(
                "[FinancialPrivate] funding extraction validation failed",
                domain=domain,
                error=str(ve),
            )
            return None
        except Exception:
            logger.exception(
                "[FinancialPrivate] funding extraction failed",
                domain=domain,
            )
            return None

    async def _extract_employee_model(
        self,
        company_name: str,
        domain: str,
        waterfall_responses: list[dict[str, str]],
    ) -> EmployeeRevenueModel | None:
        """Extract EmployeeRevenueModel from the employee count source.

        Args:
            company_name: Company being analyzed.
            domain: Company domain.
            waterfall_responses: All 6 raw responses.

        Returns:
            EmployeeRevenueModel or None if extraction fails.
        """
        employee_response = self._find_response(waterfall_responses, "Employee count")
        if not employee_response or employee_response.startswith("[ERROR"):
            logger.warning(
                "[FinancialPrivate] no valid employee response to extract",
                domain=domain,
            )
            return None

        prompt = _build_employee_model_prompt(company_name, domain, employee_response)

        try:
            result: EmployeeRevenueModel = create_completion(
                response_model=EmployeeRevenueModel,
                max_retries=3,
                messages=[{"role": "user", "content": prompt}],
            )
            logger.info(
                "[FinancialPrivate] employee model extraction success",
                domain=domain,
                employee_count=result.employee_count,
                estimated_revenue=result.estimated_revenue,
            )
            return result

        except ValidationError as ve:
            logger.error(
                "[FinancialPrivate] employee model validation failed",
                domain=domain,
                error=str(ve),
            )
            return None
        except Exception:
            logger.exception(
                "[FinancialPrivate] employee model extraction failed",
                domain=domain,
            )
            return None

    async def _extract_competitors(
        self,
        company_name: str,
        domain: str,
        waterfall_responses: list[dict[str, str]],
    ) -> list[CompetitorRevenueEstimate]:
        """Extract competitor revenue estimates from the comparison source.

        Args:
            company_name: Company being analyzed.
            domain: Company domain.
            waterfall_responses: All 6 raw responses.

        Returns:
            List of CompetitorRevenueEstimate, empty if extraction fails.
        """
        competitor_response = self._find_response(waterfall_responses, "Competitor")
        if not competitor_response or competitor_response.startswith("[ERROR"):
            logger.warning(
                "[FinancialPrivate] no valid competitor response to extract",
                domain=domain,
            )
            return []

        prompt = _build_competitor_prompt(company_name, domain, competitor_response)

        try:
            result: list[CompetitorRevenueEstimate] = create_completion(
                response_model=list[CompetitorRevenueEstimate],
                max_retries=3,
                messages=[{"role": "user", "content": prompt}],
            )
            logger.info(
                "[FinancialPrivate] competitor extraction success",
                domain=domain,
                competitor_count=len(result),
            )
            return result

        except ValidationError as ve:
            logger.error(
                "[FinancialPrivate] competitor extraction validation failed",
                domain=domain,
                error=str(ve),
            )
            return []
        except Exception:
            logger.exception(
                "[FinancialPrivate] competitor extraction failed",
                domain=domain,
            )
            return []

    @staticmethod
    def _find_response(waterfall_responses: list[dict[str, str]], label_keyword: str) -> str | None:
        """Find the waterfall response whose label contains the keyword.

        Args:
            waterfall_responses: The list of waterfall response dicts.
            label_keyword: Keyword to search for in the label.

        Returns:
            The content string if found, None otherwise.
        """
        for resp in waterfall_responses:
            if label_keyword.lower() in resp.get("label", "").lower():
                return resp.get("content", "")
        return None
