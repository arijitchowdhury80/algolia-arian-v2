"""Intel Hiring collector -- Apify LinkedIn Jobs + Perplexity fallback.

Collects open job postings and buying committee signals via:
1. Apify LinkedIn Jobs Scraper (when APIFY_TOKEN is set)
2. Perplexity sonar-pro fallback (when APIFY_TOKEN is not set)
3. Perplexity for champion signal enrichment on executives

Runs 3 queries per company (prospect + each competitor):
  - Search/discovery/personalization roles
  - Software engineer/platform/architecture roles
  - VP/director/head digital/commerce roles
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

APIFY_BASE_URL = "https://api.apify.com/v2"
APIFY_ACTOR_ID = "curious_coder~linkedin-jobs-scraper"
APIFY_TIMEOUT = 120.0
APIFY_POLL_INTERVAL = 5.0
APIFY_MAX_POLL_ATTEMPTS = 30  # 150 seconds max wait


def _build_search_queries(company_name: str) -> list[str]:
    """Build the 3 standard job search queries for a company.

    Args:
        company_name: Name of the company.

    Returns:
        List of 3 search query strings.
    """
    return [
        f"{company_name} search OR discovery OR personalization jobs",
        f"{company_name} software engineer OR platform OR architecture jobs",
        f"{company_name} VP OR director OR head digital OR commerce jobs",
    ]


async def _perplexity_query(prompt: str, label: str) -> str:
    """Send a single query to Perplexity and return the response content.

    Args:
        prompt: The user prompt to send.
        label: Human-readable label for logging.

    Returns:
        The text content from Perplexity's response.

    Raises:
        httpx.TimeoutException: If the request times out.
        httpx.HTTPStatusError: If Perplexity returns an HTTP error.
        KeyError: If the response format is unexpected.
    """
    logger.debug("[HiringCollector] perplexity query started", label=label)

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
                "[HiringCollector] perplexity query complete",
                label=label,
                response_length=len(content),
            )
            return content

    except httpx.TimeoutException as exc:
        logger.error("[HiringCollector] perplexity timeout", label=label, error=str(exc))
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(
            "[HiringCollector] perplexity HTTP error",
            label=label,
            status_code=exc.response.status_code,
            error=str(exc),
        )
        raise
    except KeyError as exc:
        logger.error(
            "[HiringCollector] perplexity unexpected response format",
            label=label,
            error=str(exc),
        )
        raise
    except Exception:
        logger.exception("[HiringCollector] perplexity unexpected error", label=label)
        raise


async def _apify_collect_jobs(query: str, label: str) -> list[dict[str, Any]]:
    """Run Apify LinkedIn Jobs Scraper for a single query.

    Args:
        query: The search query string.
        label: Human-readable label for logging.

    Returns:
        List of job posting dicts from the Apify dataset.

    Raises:
        httpx.TimeoutException: If the actor run times out.
        httpx.HTTPStatusError: If Apify returns an HTTP error.
        RuntimeError: If the actor fails or times out waiting.
    """
    logger.info("[HiringCollector] apify job search started", label=label, query=query)

    try:
        async with httpx.AsyncClient(timeout=APIFY_TIMEOUT) as client:
            # Start the actor run
            start_resp = await client.post(
                f"{APIFY_BASE_URL}/acts/{APIFY_ACTOR_ID}/runs",
                params={"token": settings.apify_api_key},
                json={
                    "searchQueries": [query],
                    "maxResults": 25,
                    "location": "",
                },
            )
            start_resp.raise_for_status()
            run_data = start_resp.json()
            run_id: str = run_data["data"]["id"]

            logger.info(
                "[HiringCollector] apify actor run started",
                label=label,
                run_id=run_id,
            )

            # Poll for completion
            for attempt in range(APIFY_MAX_POLL_ATTEMPTS):
                await asyncio.sleep(APIFY_POLL_INTERVAL)
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
                    raise RuntimeError(f"Apify actor run {run_id} ended with status: {run_status}")

                logger.debug(
                    "[HiringCollector] apify polling",
                    label=label,
                    run_id=run_id,
                    attempt=attempt + 1,
                    status=run_status,
                )
            else:
                raise RuntimeError(
                    f"Apify actor run {run_id} timed out after {APIFY_MAX_POLL_ATTEMPTS} polls"
                )

            # Fetch dataset items
            dataset_resp = await client.get(
                f"{APIFY_BASE_URL}/actor-runs/{run_id}/dataset/items",
                params={"token": settings.apify_api_key},
            )
            dataset_resp.raise_for_status()
            items: list[dict[str, Any]] = dataset_resp.json()

            logger.info(
                "[HiringCollector] apify job search complete",
                label=label,
                run_id=run_id,
                job_count=len(items),
            )
            return items

    except httpx.TimeoutException as exc:
        logger.error("[HiringCollector] apify timeout", label=label, error=str(exc))
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(
            "[HiringCollector] apify HTTP error",
            label=label,
            status_code=exc.response.status_code,
            error=str(exc),
        )
        raise
    except RuntimeError:
        raise
    except Exception:
        logger.exception("[HiringCollector] apify unexpected error", label=label)
        raise


def _build_perplexity_jobs_prompt(company_name: str, query_focus: str) -> str:
    """Build a Perplexity prompt to find open roles.

    Args:
        company_name: Name of the company.
        query_focus: The focus area for the search.

    Returns:
        Formatted prompt string.
    """
    return f"""List all current open job positions at {company_name} related to {query_focus}.

For each role include:
- Job title
- Department (if available)
- Location
- Posted date (if available)
- URL to the posting (if available)
- Whether the role is related to search, discovery, or personalization technology

Focus on roles that would be relevant to a company evaluating or implementing search technology.
Include at least 10-15 roles if available."""


def _build_champion_signals_prompt(
    exec_name: str,
    exec_title: str,
    company_name: str,
) -> str:
    """Build a Perplexity prompt to search for champion signals for an executive.

    Args:
        exec_name: Name of the executive.
        exec_title: Title of the executive.
        company_name: Company name.

    Returns:
        Formatted prompt string.
    """
    return f"""{exec_name}, {exec_title} at {company_name}: search for information about this person's:
1. Previous companies they worked at
2. How long they've been in their current role
3. LinkedIn profile URL
4. Any public statements about search technology, AI, digital transformation
5. Any connection to Algolia, Elasticsearch, Solr, or similar search technologies
6. Conference talks, blog posts, or social media about search/discovery

Focus on signals that indicate they could be a champion or blocker for search technology purchase decisions."""


class HiringCollector:
    """Collects hiring intelligence via Apify LinkedIn Jobs + Perplexity.

    Uses Apify LinkedIn Jobs Scraper when APIFY_TOKEN is available,
    falls back to Perplexity sonar-pro when it is not.
    """

    def __init__(self) -> None:
        self._use_apify = bool(settings.apify_api_key)
        logger.info(
            "[HiringCollector] initialized",
            use_apify=self._use_apify,
        )

    async def collect_all(
        self,
        domain: str,
        company_name: str,
        executives: list[dict[str, Any]],
        competitor_domains: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Collect all hiring intelligence for a domain.

        Args:
            domain: Target domain (e.g. 'dell.com').
            company_name: Company name for prompts.
            executives: List of executive dicts with 'name', 'title', 'relevance' keys.
            competitor_domains: List of competitor dicts with 'company_name', 'domain' keys.

        Returns:
            Dict with keys: prospect_roles, competitor_roles, champion_signals, source_type.
        """
        logger.info(
            "[HiringCollector] collect_all started",
            domain=domain,
            company_name=company_name,
            exec_count=len(executives),
            competitor_count=len(competitor_domains),
            use_apify=self._use_apify,
        )

        raw: dict[str, Any] = {
            "prospect_roles": [],
            "competitor_roles": {},
            "champion_signals": {},
            "source_type": "linkedin" if self._use_apify else "perplexity",
        }

        # Part 1: Collect prospect roles
        try:
            raw["prospect_roles"] = await self._collect_company_roles(
                company_name=company_name,
                label=f"prospect:{domain}",
            )
        except Exception as exc:
            logger.error(
                "[HiringCollector] prospect role collection failed",
                domain=domain,
                error=str(exc),
            )
            raw["prospect_roles"] = []

        # Part 2: Collect competitor roles (top 3)
        comp_tasks = []
        comp_keys: list[str] = []
        for comp in competitor_domains[:3]:
            comp_name = comp.get("company_name", "")
            comp_domain = comp.get("domain", "")
            if not comp_name:
                continue
            comp_tasks.append(
                self._collect_company_roles(
                    company_name=comp_name,
                    label=f"competitor:{comp_domain}",
                )
            )
            comp_keys.append(comp_name)

        if comp_tasks:
            comp_results = await asyncio.gather(*comp_tasks, return_exceptions=True)
            for i, result in enumerate(comp_results):
                key = comp_keys[i]
                comp_domain = competitor_domains[i].get("domain", "")
                if isinstance(result, Exception):
                    logger.error(
                        "[HiringCollector] competitor role collection failed",
                        competitor=key,
                        error=str(result),
                    )
                    raw["competitor_roles"][key] = {
                        "roles": [],
                        "domain": comp_domain,
                    }
                else:
                    raw["competitor_roles"][key] = {
                        "roles": result,
                        "domain": comp_domain,
                    }

        # Part 3: Champion signals for executives (top 5)
        exec_tasks = []
        exec_keys: list[str] = []
        for ex in executives[:5]:
            name = ex.get("name", ex.get("full_name", ""))
            title = ex.get("title", "")
            if not name:
                continue
            exec_tasks.append(
                self._collect_champion_signals(
                    exec_name=name,
                    exec_title=title,
                    company_name=company_name,
                )
            )
            exec_keys.append(name)

        if exec_tasks:
            exec_results = await asyncio.gather(*exec_tasks, return_exceptions=True)
            for i, result in enumerate(exec_results):
                key = exec_keys[i]
                if isinstance(result, Exception):
                    logger.error(
                        "[HiringCollector] champion signal collection failed",
                        exec_name=key,
                        error=str(result),
                    )
                    raw["champion_signals"][key] = ""
                else:
                    raw["champion_signals"][key] = result

        logger.info(
            "[HiringCollector] collect_all complete",
            domain=domain,
            prospect_role_count=len(raw["prospect_roles"]),
            competitor_count=len(raw["competitor_roles"]),
            champion_signal_count=len(raw["champion_signals"]),
            source_type=raw["source_type"],
        )

        return raw

    async def _collect_company_roles(
        self,
        company_name: str,
        label: str,
    ) -> list[Any]:
        """Collect open roles for a single company using Apify or Perplexity.

        Args:
            company_name: Company name.
            label: Logging label.

        Returns:
            List of role data (Apify dicts or Perplexity text strings).
        """
        queries = _build_search_queries(company_name)

        if self._use_apify:
            return await self._collect_via_apify(queries, label)
        return await self._collect_via_perplexity(company_name, queries, label)

    async def _collect_via_apify(
        self,
        queries: list[str],
        label: str,
    ) -> list[dict[str, Any]]:
        """Collect roles via Apify LinkedIn Jobs Scraper.

        Args:
            queries: List of search queries.
            label: Logging label.

        Returns:
            Combined list of job posting dicts from all queries.
        """
        all_jobs: list[dict[str, Any]] = []

        tasks = [_apify_collect_jobs(q, f"{label}:q{i}") for i, q in enumerate(queries)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "[HiringCollector] apify query failed",
                    label=label,
                    query_index=i,
                    error=str(result),
                )
            else:
                all_jobs.extend(result)

        # Deduplicate by URL
        seen_urls: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for job in all_jobs:
            url = job.get("url", job.get("link", ""))
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            deduped.append(job)

        logger.info(
            "[HiringCollector] apify collection complete",
            label=label,
            total_raw=len(all_jobs),
            deduped=len(deduped),
        )
        return deduped

    async def _collect_via_perplexity(
        self,
        company_name: str,
        queries: list[str],
        label: str,
    ) -> list[str]:
        """Collect roles via Perplexity fallback.

        Args:
            company_name: Company name.
            queries: List of search queries (used for focus areas).
            label: Logging label.

        Returns:
            List of raw text responses from Perplexity.
        """
        focus_areas = [
            "search, discovery, personalization, or recommendation technology",
            "software engineering, platform engineering, or system architecture",
            "VP, director, or head of digital commerce, e-commerce, or technology leadership",
        ]

        tasks = [
            _perplexity_query(
                _build_perplexity_jobs_prompt(company_name, focus),
                f"{label}:focus{i}",
            )
            for i, focus in enumerate(focus_areas)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        collected: list[str] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "[HiringCollector] perplexity jobs query failed",
                    label=label,
                    focus_index=i,
                    error=str(result),
                )
            else:
                collected.append(result)

        logger.info(
            "[HiringCollector] perplexity collection complete",
            label=label,
            successful_queries=len(collected),
        )
        return collected

    async def _collect_champion_signals(
        self,
        exec_name: str,
        exec_title: str,
        company_name: str,
    ) -> str:
        """Collect champion signals for an executive via Perplexity.

        Args:
            exec_name: Name of the executive.
            exec_title: Title of the executive.
            company_name: Company name.

        Returns:
            Raw text from Perplexity about the executive's champion potential.
        """
        logger.info(
            "[HiringCollector] champion signal collection started",
            exec_name=exec_name,
            company_name=company_name,
        )

        try:
            result = await _perplexity_query(
                _build_champion_signals_prompt(exec_name, exec_title, company_name),
                f"champion:{exec_name}",
            )
            return result
        except Exception as exc:
            logger.error(
                "[HiringCollector] champion signal query failed",
                exec_name=exec_name,
                error=str(exc),
            )
            raise
