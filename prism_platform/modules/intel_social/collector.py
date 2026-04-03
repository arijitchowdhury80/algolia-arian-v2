"""Intel Social collector -- Perplexity + Apify for social intelligence.

Calls the Perplexity API (sonar-pro model) to collect:
1. Executive LinkedIn activity (or Apify when token available)
2. Executive public statements beyond LinkedIn
3. Twitter/X activity
4. Competitor executive social activity

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

APIFY_LINKEDIN_COMPANY_POSTS_ACTOR = "harvestapi~linkedin-company-posts"
APIFY_BASE_URL = "https://api.apify.com/v2"
APIFY_TIMEOUT = 120.0


async def _perplexity_query(prompt: str, label: str) -> str:
    """Send a single query to Perplexity and return the response content.

    Args:
        prompt: The user prompt to send.
        label: Human-readable label for logging (e.g. 'linkedin_activity:dell.com').

    Returns:
        The text content from Perplexity's response.

    Raises:
        httpx.TimeoutException: If the request times out.
        httpx.HTTPStatusError: If Perplexity returns an HTTP error.
        KeyError: If the response format is unexpected.
    """
    logger.debug("[SocialCollector] perplexity query started", label=label)

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
                "[SocialCollector] perplexity query complete",
                label=label,
                response_length=len(content),
            )
            return content

    except httpx.TimeoutException as exc:
        logger.error("[SocialCollector] perplexity timeout", label=label, error=str(exc))
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(
            "[SocialCollector] perplexity HTTP error",
            label=label,
            status_code=exc.response.status_code,
            error=str(exc),
        )
        raise
    except KeyError as exc:
        logger.error(
            "[SocialCollector] perplexity unexpected response format",
            label=label,
            error=str(exc),
        )
        raise
    except Exception:
        logger.exception("[SocialCollector] perplexity unexpected error", label=label)
        raise


async def _apify_linkedin_company_posts(company_name: str) -> list[dict[str, Any]]:
    """Fetch recent LinkedIn company posts via the Apify actor.

    Args:
        company_name: Company name to build the LinkedIn company URL.

    Returns:
        List of raw post dicts from Apify.

    Raises:
        httpx.TimeoutException: If the request times out.
        httpx.HTTPStatusError: If Apify returns an HTTP error.
        RuntimeError: If the run fails or returns no dataset.
    """
    slug = company_name.lower().replace(" ", "-").replace(".", "")
    company_url = f"https://www.linkedin.com/company/{slug}/"

    logger.info(
        "[SocialCollector] apify linkedin posts started",
        company_name=company_name,
        company_url=company_url,
    )

    try:
        async with httpx.AsyncClient(timeout=APIFY_TIMEOUT) as client:
            # Start the actor run
            run_resp = await client.post(
                f"{APIFY_BASE_URL}/acts/{APIFY_LINKEDIN_COMPANY_POSTS_ACTOR}/runs",
                params={"token": settings.apify_api_key},
                json={
                    "companyUrl": company_url,
                    "maxPosts": 20,
                },
            )
            run_resp.raise_for_status()
            run_data = run_resp.json()
            run_id: str = run_data["data"]["id"]
            dataset_id: str = run_data["data"]["defaultDatasetId"]

            logger.info(
                "[SocialCollector] apify run started",
                run_id=run_id,
                dataset_id=dataset_id,
            )

            # Poll for completion (max 90 seconds)
            for attempt in range(18):
                await asyncio.sleep(5)
                status_resp = await client.get(
                    f"{APIFY_BASE_URL}/actor-runs/{run_id}",
                    params={"token": settings.apify_api_key},
                )
                status_resp.raise_for_status()
                status_data = status_resp.json()
                run_status: str = status_data["data"]["status"]

                if run_status == "SUCCEEDED":
                    break
                if run_status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    msg = f"Apify run {run_id} ended with status {run_status}"
                    logger.error(
                        "[SocialCollector] apify run failed", run_id=run_id, status=run_status
                    )
                    raise RuntimeError(msg)

                logger.debug(
                    "[SocialCollector] apify run polling",
                    run_id=run_id,
                    attempt=attempt + 1,
                    status=run_status,
                )
            else:
                msg = f"Apify run {run_id} timed out after 90s"
                logger.error("[SocialCollector] apify run timed out", run_id=run_id)
                raise RuntimeError(msg)

            # Fetch dataset items
            dataset_resp = await client.get(
                f"{APIFY_BASE_URL}/datasets/{dataset_id}/items",
                params={"token": settings.apify_api_key, "format": "json"},
            )
            dataset_resp.raise_for_status()
            items: list[dict[str, Any]] = dataset_resp.json()

            logger.info(
                "[SocialCollector] apify linkedin posts complete",
                company_name=company_name,
                post_count=len(items),
            )
            return items

    except httpx.TimeoutException as exc:
        logger.error(
            "[SocialCollector] apify timeout",
            company_name=company_name,
            error=str(exc),
        )
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(
            "[SocialCollector] apify HTTP error",
            company_name=company_name,
            status_code=exc.response.status_code,
            error=str(exc),
        )
        raise
    except RuntimeError:
        raise
    except Exception:
        logger.exception(
            "[SocialCollector] apify unexpected error",
            company_name=company_name,
        )
        raise


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def _build_linkedin_activity_prompt(
    exec_name: str,
    exec_title: str,
    company_name: str,
) -> str:
    """Build the prompt for executive LinkedIn activity search.

    Args:
        exec_name: Name of the executive.
        exec_title: Title of the executive.
        company_name: Company the executive works for.

    Returns:
        Formatted prompt string.
    """
    return (
        f"{exec_name}, {exec_title} at {company_name}: recent LinkedIn posts and activity "
        f"in 2025-2026. What topics have they posted about? Include: post topic, approximate "
        f"date, engagement if known, any quotable statements."
    )


def _build_public_statements_prompt(exec_name: str, company_name: str) -> str:
    """Build the prompt for executive public statements beyond LinkedIn.

    Args:
        exec_name: Name of the executive.
        company_name: Company the executive works for.

    Returns:
        Formatted prompt string.
    """
    return (
        f"{exec_name} {company_name} keynote OR conference OR podcast OR webinar OR interview "
        f"2025 2026. Looking for public statements about digital strategy, technology investment, "
        f"customer experience, search, AI, or competitive positioning. Include verbatim quotes "
        f"where possible."
    )


def _build_twitter_prompt(company_name: str) -> str:
    """Build the prompt for company Twitter/X activity search.

    Args:
        company_name: Company name.

    Returns:
        Formatted prompt string.
    """
    return f"{company_name} Twitter OR X.com announcement technology 2025 2026"


def _build_competitor_exec_prompt(
    exec_name: str,
    exec_title: str,
    company_name: str,
) -> str:
    """Build the prompt for competitor executive social activity.

    Args:
        exec_name: Name of the competitor executive.
        exec_title: Title of the competitor executive.
        company_name: Competitor company name.

    Returns:
        Formatted prompt string.
    """
    return (
        f"{exec_name}, {exec_title} at {company_name}: recent LinkedIn posts, conference talks, "
        f"podcasts, and public statements in 2025-2026. Include: topic, date, any quotable "
        f"statements about technology strategy, search, AI, digital transformation."
    )


# ---------------------------------------------------------------------------
# Collector class
# ---------------------------------------------------------------------------


class SocialCollector:
    """Collects social intelligence via Perplexity API and Apify.

    Produces raw text responses that are later structured by the SocialEnricher.
    """

    async def collect_all(
        self,
        domain: str,
        company_name: str,
        executives: list[dict[str, Any]],
        competitor_domains: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Collect all social intelligence for a domain.

        Args:
            domain: Target domain (e.g. 'dell.com').
            company_name: Company name for prompts.
            executives: List of executive dicts with 'name', 'title', 'relevance' keys.
                Sourced from intel-company output.
            competitor_domains: List of competitor dicts with 'company_name', 'domain' keys.
                Sourced from intel-company output.

        Returns:
            Dict with keys: linkedin_activity, public_statements, apify_posts,
            twitter, competitor_social. Each value is raw text or raw data.

        Raises:
            RuntimeError: If all collection calls fail.
        """
        logger.info(
            "[SocialCollector] collect_all started",
            domain=domain,
            company_name=company_name,
            exec_count=len(executives),
            competitor_count=len(competitor_domains),
        )

        raw: dict[str, Any] = {
            "linkedin_activity": {},
            "public_statements": {},
            "apify_posts": [],
            "twitter": "",
            "competitor_social": {},
        }

        # Sort executives by relevance priority
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

        # Part 1: Executive LinkedIn activity via Perplexity
        linkedin_tasks = []
        linkedin_exec_names: list[str] = []
        for ex in top_execs:
            name = ex.get("name", ex.get("full_name", ""))
            title = ex.get("title", "")
            if not name:
                continue
            linkedin_exec_names.append(name)
            linkedin_tasks.append(
                _perplexity_query(
                    _build_linkedin_activity_prompt(name, title, company_name),
                    label=f"linkedin_activity:{name}",
                )
            )

        if linkedin_tasks:
            linkedin_results = await asyncio.gather(*linkedin_tasks, return_exceptions=True)
            for i, result in enumerate(linkedin_results):
                exec_name = linkedin_exec_names[i]
                if isinstance(result, Exception):
                    logger.error(
                        "[SocialCollector] linkedin activity failed",
                        exec_name=exec_name,
                        error=str(result),
                    )
                    raw["linkedin_activity"][exec_name] = ""
                else:
                    raw["linkedin_activity"][exec_name] = result

        # Part 2: Executive public statements via Perplexity
        statement_tasks = []
        statement_exec_names: list[str] = []
        for ex in top_execs:
            name = ex.get("name", ex.get("full_name", ""))
            if not name:
                continue
            statement_exec_names.append(name)
            statement_tasks.append(
                _perplexity_query(
                    _build_public_statements_prompt(name, company_name),
                    label=f"public_statements:{name}",
                )
            )

        if statement_tasks:
            statement_results = await asyncio.gather(*statement_tasks, return_exceptions=True)
            for i, result in enumerate(statement_results):
                exec_name = statement_exec_names[i]
                if isinstance(result, Exception):
                    logger.error(
                        "[SocialCollector] public statements failed",
                        exec_name=exec_name,
                        error=str(result),
                    )
                    raw["public_statements"][exec_name] = ""
                else:
                    raw["public_statements"][exec_name] = result

        # Part 3: Apify LinkedIn company posts (if token available)
        if settings.apify_api_key:
            try:
                raw["apify_posts"] = await _apify_linkedin_company_posts(company_name)
            except Exception as exc:
                logger.error(
                    "[SocialCollector] apify linkedin posts failed, falling back to perplexity",
                    company_name=company_name,
                    error=str(exc),
                )
                raw["apify_posts"] = []
                # Fallback: use Perplexity for company LinkedIn posts
                try:
                    fallback = await _perplexity_query(
                        (
                            f"{company_name} LinkedIn company page recent posts 2025-2026. "
                            f"What has the company been posting about? Include topics, dates, engagement."
                        ),
                        label=f"linkedin_company_fallback:{domain}",
                    )
                    raw["linkedin_activity"]["__company_page__"] = fallback
                except Exception as fallback_exc:
                    logger.error(
                        "[SocialCollector] linkedin company fallback also failed",
                        error=str(fallback_exc),
                    )
        else:
            logger.info(
                "[SocialCollector] APIFY_API_KEY not set, using perplexity for company linkedin",
                domain=domain,
            )
            try:
                fallback = await _perplexity_query(
                    (
                        f"{company_name} LinkedIn company page recent posts 2025-2026. "
                        f"What has the company been posting about? Include topics, dates, engagement."
                    ),
                    label=f"linkedin_company_perplexity:{domain}",
                )
                raw["linkedin_activity"]["__company_page__"] = fallback
            except Exception as exc:
                logger.error(
                    "[SocialCollector] linkedin company perplexity failed",
                    error=str(exc),
                )

        # Part 4: Twitter/X activity via Perplexity
        try:
            raw["twitter"] = await _perplexity_query(
                _build_twitter_prompt(company_name),
                label=f"twitter:{domain}",
            )
        except Exception as exc:
            logger.error(
                "[SocialCollector] twitter collection failed",
                domain=domain,
                error=str(exc),
            )
            raw["twitter"] = ""

        # Part 5: Competitor social (CEO + CTO only, top 2 competitors)
        comp_tasks = []
        comp_keys: list[tuple[str, str, str]] = []  # (comp_name, comp_domain, exec_label)
        for comp in competitor_domains[:2]:
            comp_name = comp.get("company_name", "")
            comp_domain = comp.get("domain", "")
            if not comp_name or not comp_domain:
                continue
            # Search for CEO and CTO
            for title in ["CEO", "CTO"]:
                comp_keys.append((comp_name, comp_domain, f"{comp_name} {title}"))
                comp_tasks.append(
                    _perplexity_query(
                        _build_competitor_exec_prompt(
                            f"{comp_name} {title}",
                            title,
                            comp_name,
                        ),
                        label=f"competitor_social:{comp_name}:{title}",
                    )
                )

        if comp_tasks:
            comp_results = await asyncio.gather(*comp_tasks, return_exceptions=True)
            for i, result in enumerate(comp_results):
                comp_name, comp_domain, exec_label = comp_keys[i]
                key = f"{comp_name}|{comp_domain}"
                if key not in raw["competitor_social"]:
                    raw["competitor_social"][key] = {
                        "company_name": comp_name,
                        "domain": comp_domain,
                        "exec_texts": {},
                    }
                if isinstance(result, Exception):
                    logger.error(
                        "[SocialCollector] competitor social failed",
                        competitor=comp_name,
                        exec_label=exec_label,
                        error=str(result),
                    )
                    raw["competitor_social"][key]["exec_texts"][exec_label] = ""
                else:
                    raw["competitor_social"][key]["exec_texts"][exec_label] = result

        logger.info(
            "[SocialCollector] collect_all complete",
            domain=domain,
            linkedin_exec_count=len(raw["linkedin_activity"]),
            public_statement_exec_count=len(raw["public_statements"]),
            apify_post_count=len(raw["apify_posts"]),
            twitter_length=len(raw["twitter"]),
            competitor_count=len(raw["competitor_social"]),
        )

        return raw
