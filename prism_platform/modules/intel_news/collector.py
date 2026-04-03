"""Intel News collector -- Perplexity-based news and executive media collection.

Calls the Perplexity API (sonar-pro model) to collect:
1. Company news (90-day sweep)
2. Executive media and interviews (verbatim quotes)
3. Competitor news
4. Signal classification for urgency

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
        label: Human-readable label for logging (e.g. 'company_news:dell.com').

    Returns:
        The text content from Perplexity's response.

    Raises:
        httpx.TimeoutException: If the request times out.
        httpx.HTTPStatusError: If Perplexity returns an HTTP error.
        KeyError: If the response format is unexpected.
    """
    logger.debug("[NewsCollector] perplexity query started", label=label)

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
                "[NewsCollector] perplexity query complete",
                label=label,
                response_length=len(content),
            )
            return content

    except httpx.TimeoutException as exc:
        logger.error("[NewsCollector] perplexity timeout", label=label, error=str(exc))
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(
            "[NewsCollector] perplexity HTTP error",
            label=label,
            status_code=exc.response.status_code,
            error=str(exc),
        )
        raise
    except KeyError as exc:
        logger.error(
            "[NewsCollector] perplexity unexpected response format",
            label=label,
            error=str(exc),
        )
        raise
    except Exception:
        logger.exception("[NewsCollector] perplexity unexpected error", label=label)
        raise


def _build_company_news_prompt(company_name: str, domain: str) -> str:
    """Build the prompt for 90-day company news sweep.

    Args:
        company_name: Name of the company.
        domain: Website domain.

    Returns:
        Formatted prompt string.
    """
    return f"""Latest news for {company_name} ({domain}) in the last 90 days. Include:
leadership changes, technology investments, partnerships, funding,
product launches, acquisitions, search/AI/digital initiatives.
For each article: headline, publication, date, URL, brief summary.
Focus on major announcements and strategic moves. Include at least 5-10 articles if available."""


def _build_exec_interviews_prompt(
    exec_name: str,
    exec_title: str,
    company_name: str,
) -> str:
    """Build the prompt for executive media search.

    Args:
        exec_name: Name of the executive.
        exec_title: Title of the executive.
        company_name: Company the executive works for.

    Returns:
        Formatted prompt string.
    """
    return f"""{exec_name}, {exec_title} at {company_name}: recent interviews, keynotes,
podcasts, conference talks in 2025-2026. Include verbatim quotes about
digital strategy, technology investment, customer experience, search, AI,
or competitive positioning. For each: the exact quote, where it was said, date, URL."""


def _build_exec_quotes_prompt(exec_name: str, company_name: str) -> str:
    """Build the targeted quote search prompt for an executive.

    Args:
        exec_name: Name of the executive.
        company_name: Company the executive works for.

    Returns:
        Formatted prompt string.
    """
    return f"""{exec_name} {company_name} quote OR statement about digital OR technology
OR search OR AI 2025 2026. Looking for public commitments, budget statements,
priority declarations, or pain point admissions. Include the exact verbatim quote,
the source, and the date."""


def _build_signal_classification_prompt(company_name: str, news_text: str) -> str:
    """Build the prompt for urgency signal classification.

    Args:
        company_name: Name of the company.
        news_text: Concatenated news and quotes text.

    Returns:
        Formatted prompt string.
    """
    return f"""Given these news items and executive quotes about {company_name}, classify the urgency
for a sales team selling search technology (Algolia). Flag:
- Leadership changes in last 30 days (new exec window = high urgency)
- Competitor technology moves (medium urgency)
- Executive public commitments to digital investment (high urgency)
- Platform migration announcements (high urgency)
- AI/search-related announcements (medium urgency)
- General technology investments (low urgency)

For each signal, provide: signal type, description, urgency level (high/medium/low),
the source headline, and the date.

NEWS AND QUOTES:
{news_text[:8000]}"""


class NewsCollector:
    """Collects news and executive media data via Perplexity API.

    Produces raw text responses that are later structured by the NewsEnricher.
    """

    async def collect_all(
        self,
        domain: str,
        company_name: str,
        executives: list[dict[str, Any]],
        competitor_domains: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Collect all news intelligence for a domain.

        Args:
            domain: Target domain (e.g. 'dell.com').
            company_name: Company name for prompts.
            executives: List of executive dicts with 'name', 'title', 'relevance' keys.
                Sourced from intel-company output.
            competitor_domains: List of competitor dicts with 'company_name', 'domain' keys.
                Sourced from intel-company output.

        Returns:
            Dict with keys: prospect_news, exec_media, competitor_news, signals.
            Each value is the raw text from Perplexity.

        Raises:
            RuntimeError: If all Perplexity calls fail.
        """
        logger.info(
            "[NewsCollector] collect_all started",
            domain=domain,
            company_name=company_name,
            exec_count=len(executives),
            competitor_count=len(competitor_domains),
        )

        raw: dict[str, Any] = {
            "prospect_news": "",
            "exec_media": {},
            "competitor_news": {},
            "signals": "",
        }

        # Part 1: Company news (90-day sweep)
        try:
            raw["prospect_news"] = await _perplexity_query(
                _build_company_news_prompt(company_name, domain),
                label=f"company_news:{domain}",
            )
        except Exception as exc:
            logger.error(
                "[NewsCollector] company news collection failed",
                domain=domain,
                error=str(exc),
            )
            raw["prospect_news"] = ""

        # Part 2: Executive media -- top 5 by relevance priority
        priority_order = [
            "economic_buyer",
            "technical_evaluator",
            "champion_candidate",
            "influencer",
            "other",
        ]
        sorted_execs = sorted(
            executives,
            key=lambda e: (
                priority_order.index(e.get("relevance", "other"))
                if e.get("relevance", "other") in priority_order
                else 99
            ),
        )
        top_execs = sorted_execs[:5]

        exec_tasks = []
        for ex in top_execs:
            name = ex.get("name", ex.get("full_name", ""))
            title = ex.get("title", "")
            if not name:
                continue
            exec_tasks.append(self._collect_exec_media(name, title, company_name))

        if exec_tasks:
            exec_results = await asyncio.gather(*exec_tasks, return_exceptions=True)
            for i, result in enumerate(exec_results):
                exec_name = top_execs[i].get("name", top_execs[i].get("full_name", f"exec_{i}"))
                if isinstance(result, Exception):
                    logger.error(
                        "[NewsCollector] exec media failed",
                        exec_name=exec_name,
                        error=str(result),
                    )
                    raw["exec_media"][exec_name] = ""
                else:
                    raw["exec_media"][exec_name] = result

        # Part 3: Competitor news
        comp_tasks = []
        for comp in competitor_domains[:5]:
            comp_name = comp.get("company_name", "")
            comp_domain = comp.get("domain", "")
            if not comp_name or not comp_domain:
                continue
            comp_tasks.append(self._collect_competitor_news(comp_name, comp_domain))

        if comp_tasks:
            comp_results = await asyncio.gather(*comp_tasks, return_exceptions=True)
            for i, result in enumerate(comp_results):
                comp_name = competitor_domains[i].get("company_name", f"comp_{i}")
                comp_domain = competitor_domains[i].get("domain", "")
                if isinstance(result, Exception):
                    logger.error(
                        "[NewsCollector] competitor news failed",
                        competitor=comp_name,
                        error=str(result),
                    )
                    raw["competitor_news"][comp_name] = {
                        "news": "",
                        "domain": comp_domain,
                    }
                else:
                    raw["competitor_news"][comp_name] = {
                        "news": result,
                        "domain": comp_domain,
                    }

        # Part 4: Signal classification
        all_text = raw["prospect_news"]
        for _name, media in raw["exec_media"].items():
            if isinstance(media, str):
                all_text += f"\n\n{media}"

        if all_text.strip():
            try:
                raw["signals"] = await _perplexity_query(
                    _build_signal_classification_prompt(company_name, all_text),
                    label=f"signals:{domain}",
                )
            except Exception as exc:
                logger.error(
                    "[NewsCollector] signal classification failed",
                    domain=domain,
                    error=str(exc),
                )
                raw["signals"] = ""

        logger.info(
            "[NewsCollector] collect_all complete",
            domain=domain,
            prospect_news_length=len(raw["prospect_news"]),
            exec_media_count=len(raw["exec_media"]),
            competitor_news_count=len(raw["competitor_news"]),
            signals_length=len(raw["signals"]),
        )

        return raw

    async def _collect_exec_media(
        self,
        exec_name: str,
        exec_title: str,
        company_name: str,
    ) -> str:
        """Collect executive media: interviews + targeted quote search.

        Args:
            exec_name: Name of the executive.
            exec_title: Title of the executive.
            company_name: Company name.

        Returns:
            Combined text from both Perplexity calls.
        """
        logger.info(
            "[NewsCollector] exec media collection started",
            exec_name=exec_name,
            company_name=company_name,
        )

        interviews = ""
        quotes = ""

        try:
            interviews = await _perplexity_query(
                _build_exec_interviews_prompt(exec_name, exec_title, company_name),
                label=f"exec_interviews:{exec_name}",
            )
        except Exception as exc:
            logger.error(
                "[NewsCollector] exec interviews failed",
                exec_name=exec_name,
                error=str(exc),
            )

        try:
            quotes = await _perplexity_query(
                _build_exec_quotes_prompt(exec_name, company_name),
                label=f"exec_quotes:{exec_name}",
            )
        except Exception as exc:
            logger.error(
                "[NewsCollector] exec quotes failed",
                exec_name=exec_name,
                error=str(exc),
            )

        combined = f"## Interviews and keynotes for {exec_name}:\n{interviews}\n\n## Targeted quotes for {exec_name}:\n{quotes}"

        logger.info(
            "[NewsCollector] exec media collection complete",
            exec_name=exec_name,
            combined_length=len(combined),
        )

        return combined

    async def _collect_competitor_news(
        self,
        comp_name: str,
        comp_domain: str,
    ) -> str:
        """Collect news for a single competitor.

        Args:
            comp_name: Competitor company name.
            comp_domain: Competitor domain.

        Returns:
            Raw text from Perplexity.
        """
        logger.info(
            "[NewsCollector] competitor news started",
            competitor=comp_name,
            domain=comp_domain,
        )

        try:
            result = await _perplexity_query(
                _build_company_news_prompt(comp_name, comp_domain),
                label=f"competitor_news:{comp_domain}",
            )
            return result
        except Exception as exc:
            logger.error(
                "[NewsCollector] competitor news failed",
                competitor=comp_name,
                error=str(exc),
            )
            raise
