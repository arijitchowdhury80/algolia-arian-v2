"""Intel Traffic enricher -- Google Trends momentum via Perplexity API.

Uses Perplexity sonar-pro to assess brand search interest trends
for the prospect and each competitor. Returns a GoogleTrendsMomentum
assessment: rising, stable, declining, or insufficient_data.
"""

from __future__ import annotations

import httpx
import structlog

from prism_platform.config import settings
from prism_platform.modules.intel_traffic.schemas import GoogleTrendsMomentum

logger = structlog.get_logger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar-pro"
PERPLEXITY_TIMEOUT = 60.0


class TrafficEnricher:
    """Enriches traffic data with Google Trends momentum via Perplexity."""

    async def assess_trends(
        self,
        company_name: str,
        domain: str,
    ) -> tuple[GoogleTrendsMomentum | None, int, float]:
        """Assess Google Trends momentum for a company brand.

        Calls Perplexity to research year-over-year brand interest changes
        and classifies as rising, stable, or declining.

        Args:
            company_name: Company or brand name to research.
            domain: Domain for context in the prompt.

        Returns:
            Tuple of (GoogleTrendsMomentum or None, llm_calls, estimated_cost).
        """
        logger.info(
            "[TrafficEnricher] assess_trends started",
            company_name=company_name,
            domain=domain,
        )

        prompt = self._build_trends_prompt(company_name, domain)

        try:
            response_text = await self._call_perplexity(prompt)
            if not response_text:
                logger.warning(
                    "[TrafficEnricher] Perplexity returned empty response",
                    company_name=company_name,
                )
                return (
                    GoogleTrendsMomentum(
                        company_name=company_name,
                        direction="insufficient_data",
                        yoy_change_description="Perplexity returned no data",
                        evidence="",
                    ),
                    1,
                    0.0,
                )

            momentum = self._parse_trends_response(company_name, response_text)

            # Estimate cost: Perplexity sonar-pro ~$3/1M input, ~$15/1M output
            input_chars = len(prompt)
            output_chars = len(response_text)
            estimated_cost = (input_chars / 4 / 1_000_000 * 3.0) + (
                output_chars / 4 / 1_000_000 * 15.0
            )

            logger.info(
                "[TrafficEnricher] assess_trends complete",
                company_name=company_name,
                direction=momentum.direction,
                estimated_cost_usd=round(estimated_cost, 4),
            )
            return momentum, 1, round(estimated_cost, 4)

        except httpx.TimeoutException:
            logger.error(
                "[TrafficEnricher] Perplexity timeout",
                company_name=company_name,
            )
            return (
                GoogleTrendsMomentum(
                    company_name=company_name,
                    direction="insufficient_data",
                    yoy_change_description="API timeout",
                    evidence="",
                ),
                1,
                0.0,
            )
        except httpx.HTTPStatusError as exc:
            logger.error(
                "[TrafficEnricher] Perplexity HTTP error",
                company_name=company_name,
                status_code=exc.response.status_code,
            )
            return (
                GoogleTrendsMomentum(
                    company_name=company_name,
                    direction="insufficient_data",
                    yoy_change_description=f"API error: HTTP {exc.response.status_code}",
                    evidence="",
                ),
                1,
                0.0,
            )
        except Exception:
            logger.exception(
                "[TrafficEnricher] unexpected error in assess_trends",
                company_name=company_name,
            )
            return None, 0, 0.0

    async def assess_competitor_trends(
        self,
        competitors: list[dict[str, str]],
    ) -> tuple[list[GoogleTrendsMomentum], int, float]:
        """Assess Google Trends momentum for a list of competitors.

        Args:
            competitors: List of dicts with 'company_name' and 'domain' keys.

        Returns:
            Tuple of (list of GoogleTrendsMomentum, total_llm_calls, total_cost).
        """
        results: list[GoogleTrendsMomentum] = []
        total_calls = 0
        total_cost = 0.0

        for comp in competitors:
            name = comp.get("company_name", comp.get("domain", "Unknown"))
            domain = comp.get("domain", "")
            momentum, calls, cost = await self.assess_trends(name, domain)
            if momentum is not None:
                results.append(momentum)
            total_calls += calls
            total_cost += cost

        logger.info(
            "[TrafficEnricher] competitor trends complete",
            competitor_count=len(competitors),
            results_count=len(results),
            total_calls=total_calls,
            total_cost_usd=round(total_cost, 4),
        )
        return results, total_calls, total_cost

    async def _call_perplexity(self, prompt: str) -> str:
        """Call the Perplexity chat completions API.

        Args:
            prompt: The user message to send.

        Returns:
            The assistant's response text.

        Raises:
            httpx.TimeoutException: If the API call times out.
            httpx.HTTPStatusError: If the API returns a non-2xx status.
        """
        async with httpx.AsyncClient(timeout=PERPLEXITY_TIMEOUT) as client:
            resp = await client.post(
                PERPLEXITY_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.perplexity_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": PERPLEXITY_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a market research analyst. "
                                "Assess Google Trends data and brand interest trends. "
                                "Be specific about year-over-year changes. "
                                "Cite sources where possible."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2048,
                    "return_citations": True,
                },
            )
            resp.raise_for_status()

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            logger.warning("[TrafficEnricher] Perplexity returned no choices")
            return ""

        return choices[0].get("message", {}).get("content", "")

    @staticmethod
    def _build_trends_prompt(company_name: str, domain: str) -> str:
        """Build the Perplexity prompt for Google Trends assessment.

        Args:
            company_name: Company or brand name.
            domain: Company domain for context.

        Returns:
            Formatted prompt string.
        """
        return f"""Analyze the Google Trends data for "{company_name}" (website: {domain}).

Provide:
1. **Overall trend direction** over the past 12 months: Is brand search interest RISING, STABLE, or DECLINING?
2. **Year-over-year change**: How has search interest changed compared to the same period last year? Be specific (e.g., "+15% YoY" or "-8% YoY").
3. **Seasonal patterns**: Are there notable peaks or valleys (e.g., Q4 holiday surge)?
4. **Evidence**: Cite Google Trends data, Similarweb estimates, or analyst reports that support your assessment.

Classify the trend as exactly ONE of:
- "rising" — sustained upward trajectory, >5% YoY increase
- "stable" — within +/- 5% YoY, no clear directional trend
- "declining" — sustained downward trajectory, >5% YoY decrease
- "insufficient_data" — not enough data to make a determination

Start your response with the classification on its own line: DIRECTION: [rising|stable|declining|insufficient_data]
Then provide the detailed analysis."""

    @staticmethod
    def _parse_trends_response(company_name: str, response_text: str) -> GoogleTrendsMomentum:
        """Parse Perplexity response into a GoogleTrendsMomentum model.

        Looks for the DIRECTION: prefix line to extract the classification,
        then uses the rest as evidence.

        Args:
            company_name: Company name for the model.
            response_text: Raw Perplexity response.

        Returns:
            GoogleTrendsMomentum model.
        """
        direction = "insufficient_data"
        yoy_description = ""
        evidence = response_text.strip()

        lines = response_text.strip().split("\n")
        for line in lines:
            line_stripped = line.strip().lower()
            if line_stripped.startswith("direction:"):
                raw_direction = line_stripped.replace("direction:", "").strip()
                # Remove any markdown formatting
                raw_direction = raw_direction.strip("*").strip()
                if raw_direction in ("rising", "stable", "declining", "insufficient_data"):
                    direction = raw_direction

            # Look for YoY description in the response
            if "yoy" in line_stripped or "year-over-year" in line_stripped:
                yoy_description = line.strip()

        # If no explicit YoY line found, extract first substantive sentence
        if not yoy_description and len(lines) > 1:
            for line in lines[1:]:
                stripped = line.strip()
                if stripped and not stripped.startswith("DIRECTION:"):
                    yoy_description = stripped
                    break

        return GoogleTrendsMomentum(
            company_name=company_name,
            direction=direction,
            yoy_change_description=yoy_description,
            evidence=evidence[:500],  # Cap evidence length
        )
