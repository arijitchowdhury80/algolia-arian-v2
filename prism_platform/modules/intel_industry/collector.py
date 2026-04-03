"""Intel Industry collector -- Perplexity-based industry intelligence collection.

Calls the Perplexity API (sonar-pro model) to collect:
1. Vertical benchmarks (conversion rates, AOV, search metrics)
2. Industry trends (digital transformation, AI, personalization)
3. Pain points (search/discovery challenges)
4. Algolia case studies in this industry
5. Search vendor landscape and market share

All raw text responses are returned for downstream structuring by the enricher.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

from prism_platform.config import settings

logger = structlog.get_logger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar-pro"
PERPLEXITY_TIMEOUT = 30.0


async def _perplexity_query(prompt: str, label: str) -> str:
    """Send a single query to Perplexity and return the response content.

    Args:
        prompt: The user prompt to send.
        label: Human-readable label for logging (e.g. 'benchmarks:Retail').

    Returns:
        The text content from Perplexity's response.

    Raises:
        httpx.TimeoutException: If the request times out.
        httpx.HTTPStatusError: If Perplexity returns an HTTP error.
        KeyError: If the response format is unexpected.
    """
    logger.debug("[IndustryCollector] perplexity query started", label=label)

    try:
        async with httpx.AsyncClient(timeout=PERPLEXITY_TIMEOUT) as client:
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
            data = resp.json()
            content: str = data["choices"][0]["message"]["content"]
            logger.info(
                "[IndustryCollector] perplexity query complete",
                label=label,
                response_length=len(content),
            )
            return content

    except httpx.TimeoutException as exc:
        logger.error("[IndustryCollector] perplexity timeout", label=label, error=str(exc))
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(
            "[IndustryCollector] perplexity HTTP error",
            label=label,
            status_code=exc.response.status_code,
            error=str(exc),
        )
        raise
    except KeyError as exc:
        logger.error(
            "[IndustryCollector] perplexity unexpected response format",
            label=label,
            error=str(exc),
        )
        raise
    except Exception:
        logger.exception("[IndustryCollector] perplexity unexpected error", label=label)
        raise


def build_benchmarks_prompt(industry: str, sub_vertical: str | None = None) -> str:
    """Build the prompt for collecting vertical benchmarks.

    Args:
        industry: Primary industry vertical.
        sub_vertical: Optional sub-vertical for more specific data.

    Returns:
        Formatted prompt string.
    """
    vertical = f"{industry} ({sub_vertical})" if sub_vertical else industry
    return (
        f"{vertical} e-commerce benchmarks 2025 2026 conversion rate "
        f"average order value search relevance bounce rate. "
        f"Include specific numbers with sources (Baymard Institute, Forrester, "
        f"NRF, Statista, eMarketer). For each benchmark: metric name, value, "
        f"source, and year."
    )


def build_trends_prompt(industry: str, sub_vertical: str | None = None) -> str:
    """Build the prompt for collecting industry trends.

    Args:
        industry: Primary industry vertical.
        sub_vertical: Optional sub-vertical for more specific data.

    Returns:
        Formatted prompt string.
    """
    vertical = f"{industry} ({sub_vertical})" if sub_vertical else industry
    return (
        f"{vertical} trends 2026 digital transformation AI personalization "
        f"search discovery composable commerce headless. "
        f"Include analyst quotes from Gartner, Forrester, McKinsey, IDC. "
        f"For each trend: name, description, how it relates to search/discovery, "
        f"and source attribution."
    )


def build_pain_points_prompt(industry: str, sub_vertical: str | None = None) -> str:
    """Build the prompt for collecting industry pain points.

    Args:
        industry: Primary industry vertical.
        sub_vertical: Optional sub-vertical for more specific data.

    Returns:
        Formatted prompt string.
    """
    vertical = f"{industry} ({sub_vertical})" if sub_vertical else industry
    return (
        f"{vertical} e-commerce challenges 2026 search discovery product findability "
        f"site search problems. What are the top pain points for {vertical} companies "
        f"when it comes to site search, product discovery, and digital experience? "
        f"For each: the pain point, its business impact, and how search technology "
        f"(like Algolia) can solve it."
    )


def build_case_studies_prompt(industry: str) -> str:
    """Build the prompt for finding Algolia case studies.

    Args:
        industry: Primary industry vertical.

    Returns:
        Formatted prompt string.
    """
    return (
        f"Algolia {industry} case study OR customer story. "
        f"Find Algolia customers in {industry} who have published results. "
        f"For each: customer name, industry, use case, key metrics "
        f"(conversion lift, click-through rate improvement, search usage), "
        f"and URL to the case study on algolia.com if available."
    )


def build_vendor_landscape_prompt(industry: str) -> str:
    """Build the prompt for search vendor landscape.

    Args:
        industry: Primary industry vertical.

    Returns:
        Formatted prompt string.
    """
    return (
        f"{industry} search technology OR site search vendor market share 2025 2026. "
        f"Which search vendors (Algolia, Elasticsearch, Coveo, Bloomreach, "
        f"Constructor, Lucidworks, Searchspring, Klevu) are most popular in "
        f"{industry}? Estimated market share or adoption percentage for each. "
        f"Include any analyst reports or surveys on search vendor usage."
    )


class IndustryCollector:
    """Collects industry intelligence data via Perplexity API.

    Produces raw text responses that are later structured by the IndustryEnricher.
    """

    async def collect_all(
        self,
        domain: str,
        industry: str,
        sub_vertical: str | None = None,
    ) -> dict[str, Any]:
        """Collect all industry intelligence for a domain.

        Args:
            domain: Target domain (e.g. 'dell.com').
            industry: Primary industry vertical.
            sub_vertical: Optional sub-vertical.

        Returns:
            Dict with keys: benchmarks, trends, pain_points, case_studies, vendor_landscape.
            Each value is the raw text from Perplexity.

        Raises:
            RuntimeError: If all Perplexity calls fail.
        """
        logger.info(
            "[IndustryCollector] collect_all started",
            domain=domain,
            industry=industry,
            sub_vertical=sub_vertical,
        )

        raw: dict[str, Any] = {
            "benchmarks": "",
            "trends": "",
            "pain_points": "",
            "case_studies": "",
            "vendor_landscape": "",
        }

        # Build all prompts
        prompts: dict[str, tuple[str, str]] = {
            "benchmarks": (
                build_benchmarks_prompt(industry, sub_vertical),
                f"benchmarks:{industry}",
            ),
            "trends": (
                build_trends_prompt(industry, sub_vertical),
                f"trends:{industry}",
            ),
            "pain_points": (
                build_pain_points_prompt(industry, sub_vertical),
                f"pain_points:{industry}",
            ),
            "case_studies": (
                build_case_studies_prompt(industry),
                f"case_studies:{industry}",
            ),
            "vendor_landscape": (
                build_vendor_landscape_prompt(industry),
                f"vendor_landscape:{industry}",
            ),
        }

        # Run all 5 queries concurrently
        keys = list(prompts.keys())
        tasks = [_perplexity_query(prompt, label) for prompt, label in prompts.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = 0
        for i, result in enumerate(results):
            key = keys[i]
            if isinstance(result, Exception):
                logger.error(
                    "[IndustryCollector] query failed",
                    key=key,
                    industry=industry,
                    error=str(result),
                )
                raw[key] = ""
            else:
                raw[key] = result
                success_count += 1

        if success_count == 0:
            logger.error(
                "[IndustryCollector] all queries failed",
                domain=domain,
                industry=industry,
            )
            raise RuntimeError(
                f"All 5 Perplexity queries failed for industry={industry}, domain={domain}"
            )

        logger.info(
            "[IndustryCollector] collect_all complete",
            domain=domain,
            industry=industry,
            success_count=success_count,
            benchmarks_length=len(raw["benchmarks"]),
            trends_length=len(raw["trends"]),
            pain_points_length=len(raw["pain_points"]),
            case_studies_length=len(raw["case_studies"]),
            vendor_landscape_length=len(raw["vendor_landscape"]),
        )

        return raw
