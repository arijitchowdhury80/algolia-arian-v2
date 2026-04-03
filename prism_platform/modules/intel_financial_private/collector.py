"""Intel Financial Private collector -- Perplexity-powered 6-source revenue waterfall.

Uses Perplexity sonar-pro for six structured research queries to estimate
private company revenue from multiple independent sources.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from prism_platform.config import settings

logger = structlog.get_logger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar-pro"


def _build_prompts(company_name: str, domain: str, industry: str = "") -> list[dict[str, str]]:
    """Build the 6 revenue waterfall prompts for Perplexity.

    Args:
        company_name: The company name to research.
        domain: The company domain.
        industry: Optional industry vertical for context.

    Returns:
        List of dicts with 'label' and 'prompt' keys for each waterfall source.
    """
    industry_ctx = f" in the {industry} industry" if industry else ""

    return [
        {
            "label": "Company press releases / annual reports",
            "prompt": (
                f"What is {company_name} ({domain}) annual revenue? "
                f"Look for official press releases, annual reports, or company-disclosed revenue figures. "
                f"Include specific dollar amounts with dates and sources."
            ),
        },
        {
            "label": "Industry reports",
            "prompt": (
                f"What do industry reports (Gartner, Forrester, IDC, market research firms) "
                f"say about {company_name} ({domain}) revenue or market share{industry_ctx}? "
                f"Include specific figures and report names."
            ),
        },
        {
            "label": "Crunchbase / PitchBook funding data",
            "prompt": (
                f"{company_name} ({domain}) funding rounds, valuation, total raised, "
                f"last funding round, investors. Include specific amounts and dates."
            ),
        },
        {
            "label": "Employee count to revenue model",
            "prompt": (
                f"{company_name} ({domain}) number of employees. "
                f"What is the typical revenue per employee for{industry_ctx} companies? "
                f"Estimate revenue based on employee count and industry benchmarks."
            ),
        },
        {
            "label": "News mentions of revenue",
            "prompt": (
                f"{company_name} ({domain}) revenue growth news 2024 2025 2026. "
                f"Include specific revenue figures mentioned in news articles."
            ),
        },
        {
            "label": "Competitor comparison",
            "prompt": (
                f"Compare {company_name} ({domain}) revenue with its main competitors{industry_ctx}. "
                f"Are any competitor revenue figures public? "
                f"How does {company_name} compare in market share and scale?"
            ),
        },
    ]


class FinancialPrivateCollector:
    """Collects private company revenue data via Perplexity 6-source waterfall."""

    async def collect_waterfall(
        self,
        company_name: str,
        domain: str,
        industry: str = "",
    ) -> list[dict[str, str]]:
        """Run the 6-source Perplexity waterfall and return raw responses.

        Args:
            company_name: Company name to research.
            domain: Company domain.
            industry: Optional industry for context.

        Returns:
            List of dicts with 'label' and 'content' for each source response.
        """
        logger.info(
            "[FinancialPrivate] collect_waterfall started",
            company_name=company_name,
            domain=domain,
            industry=industry,
        )

        prompts = _build_prompts(company_name, domain, industry)
        results: list[dict[str, str]] = []

        for prompt_item in prompts:
            label = prompt_item["label"]
            prompt_text = prompt_item["prompt"]

            try:
                content = await self._call_perplexity(prompt_text)
                results.append({"label": label, "content": content})
                logger.info(
                    "[FinancialPrivate] waterfall source collected",
                    label=label,
                    content_length=len(content),
                )
            except httpx.TimeoutException as exc:
                logger.error(
                    "[FinancialPrivate] Perplexity timeout",
                    label=label,
                    error=str(exc),
                )
                results.append({"label": label, "content": f"[ERROR: Timeout] {exc}"})
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "[FinancialPrivate] Perplexity HTTP error",
                    label=label,
                    status_code=exc.response.status_code,
                    error=str(exc),
                )
                results.append(
                    {
                        "label": label,
                        "content": f"[ERROR: HTTP {exc.response.status_code}] {exc}",
                    }
                )
            except Exception as exc:
                logger.exception(
                    "[FinancialPrivate] unexpected error in Perplexity call",
                    label=label,
                )
                results.append(
                    {
                        "label": label,
                        "content": f"[ERROR: {type(exc).__name__}] {exc}",
                    }
                )

        logger.info(
            "[FinancialPrivate] collect_waterfall completed",
            domain=domain,
            sources_collected=len(results),
            errors=[r["label"] for r in results if r["content"].startswith("[ERROR")],
        )
        return results

    async def _call_perplexity(self, prompt: str) -> str:
        """Call the Perplexity API with a single prompt.

        Args:
            prompt: The research query to send.

        Returns:
            The text content of the Perplexity response.

        Raises:
            httpx.TimeoutException: If the request times out.
            httpx.HTTPStatusError: If the API returns a non-2xx status.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                PERPLEXITY_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.perplexity_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": PERPLEXITY_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()

        data: dict[str, Any] = resp.json()
        choices = data.get("choices", [])
        if not choices:
            logger.warning("[FinancialPrivate] Perplexity returned empty choices")
            return ""

        content: str = choices[0].get("message", {}).get("content", "")
        return content
