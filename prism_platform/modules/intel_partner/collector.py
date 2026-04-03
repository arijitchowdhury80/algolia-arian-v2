"""Intel Partner collector -- Crossbeam API + Perplexity fallback.

Collects partner intelligence via:
1. Crossbeam API (when CROSSBEAM_API_KEY is set) for partner overlaps
2. Perplexity sonar-pro for SI relationships, tech partners, case studies,
   partnership news, and competitor partner ecosystems.

When Crossbeam is unavailable, all data is collected via Perplexity.
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

CROSSBEAM_API_URL = "https://api.crossbeam.com/v1"
CROSSBEAM_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Perplexity helpers
# ---------------------------------------------------------------------------


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
    logger.debug("[PartnerCollector] perplexity query started", label=label)

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
                "[PartnerCollector] perplexity query complete",
                label=label,
                response_length=len(content),
            )
            return content

    except httpx.TimeoutException as exc:
        logger.error("[PartnerCollector] perplexity timeout", label=label, error=str(exc))
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(
            "[PartnerCollector] perplexity HTTP error",
            label=label,
            status_code=exc.response.status_code,
            error=str(exc),
        )
        raise
    except KeyError as exc:
        logger.error(
            "[PartnerCollector] perplexity unexpected response format",
            label=label,
            error=str(exc),
        )
        raise
    except Exception:
        logger.exception("[PartnerCollector] perplexity unexpected error", label=label)
        raise


# ---------------------------------------------------------------------------
# Crossbeam helpers
# ---------------------------------------------------------------------------


async def _crossbeam_get_overlaps(domain: str) -> dict[str, Any]:
    """Fetch partner overlaps from Crossbeam API.

    Args:
        domain: The target domain to look up in Crossbeam.

    Returns:
        Dict with overlap data from Crossbeam.

    Raises:
        httpx.TimeoutException: If the request times out.
        httpx.HTTPStatusError: If Crossbeam returns an HTTP error.
    """
    logger.info("[PartnerCollector] crossbeam overlap query started", domain=domain)

    try:
        async with httpx.AsyncClient(timeout=CROSSBEAM_TIMEOUT) as client:
            resp = await client.get(
                f"{CROSSBEAM_API_URL}/overlaps",
                headers={"Authorization": f"Bearer {settings.crossbeam_api_key}"},
                params={"account_domain": domain},
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            logger.info(
                "[PartnerCollector] crossbeam overlap query complete",
                domain=domain,
                overlap_count=len(data.get("data", [])),
            )
            return data

    except httpx.TimeoutException as exc:
        logger.error("[PartnerCollector] crossbeam timeout", domain=domain, error=str(exc))
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(
            "[PartnerCollector] crossbeam HTTP error",
            domain=domain,
            status_code=exc.response.status_code,
            error=str(exc),
        )
        raise
    except Exception:
        logger.exception("[PartnerCollector] crossbeam unexpected error", domain=domain)
        raise


async def _crossbeam_get_partner_populations() -> dict[str, Any]:
    """Fetch partner populations from Crossbeam API.

    Returns:
        Dict with partner population data.

    Raises:
        httpx.TimeoutException: If the request times out.
        httpx.HTTPStatusError: If Crossbeam returns an HTTP error.
    """
    logger.info("[PartnerCollector] crossbeam partner-populations query started")

    try:
        async with httpx.AsyncClient(timeout=CROSSBEAM_TIMEOUT) as client:
            resp = await client.get(
                f"{CROSSBEAM_API_URL}/partner-populations",
                headers={"Authorization": f"Bearer {settings.crossbeam_api_key}"},
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            logger.info(
                "[PartnerCollector] crossbeam partner-populations query complete",
                population_count=len(data.get("data", [])),
            )
            return data

    except httpx.TimeoutException as exc:
        logger.error("[PartnerCollector] crossbeam populations timeout", error=str(exc))
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(
            "[PartnerCollector] crossbeam populations HTTP error",
            status_code=exc.response.status_code,
            error=str(exc),
        )
        raise
    except Exception:
        logger.exception("[PartnerCollector] crossbeam populations unexpected error")
        raise


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def build_si_relationships_prompt(company_name: str, domain: str) -> str:
    """Build Perplexity prompt for SI relationship discovery.

    Args:
        company_name: Name of the prospect company.
        domain: Domain of the prospect.

    Returns:
        Formatted prompt string.
    """
    return f"""Research the system integrator (SI) relationships for {company_name} ({domain}).

Find:
1. Which system integrators work with {company_name}? (e.g. Accenture, Deloitte, Slalom, Capclaude, Publicis Sapient, etc.)
2. What type of engagement does each SI have? (implementation, consulting, managed services)
3. Are any of these SIs also known Algolia partners?
4. Are there any warm introduction paths via shared customers?

For each SI, provide:
- SI name
- Relationship type
- Evidence source (news article, case study, LinkedIn connection)
- Any connection to Algolia's customer base

Focus on SIs active in e-commerce, search, and digital transformation."""


def build_tech_partners_prompt(company_name: str, domain: str) -> str:
    """Build Perplexity prompt for technology partner discovery.

    Args:
        company_name: Name of the prospect company.
        domain: Domain of the prospect.

    Returns:
        Formatted prompt string.
    """
    return f"""Research the technology partner ecosystem for {company_name} ({domain}).

Find:
1. Which technology platforms does {company_name} use? (e.g. Salesforce Commerce Cloud, Adobe Experience Manager, Shopify Plus, SAP Commerce, etc.)
2. Which of these platforms have known Algolia integrations or connectors?
3. Any recent technology partnership announcements?
4. Agency relationships for digital/e-commerce implementation

For each technology partner, provide:
- Partner name
- Partner type (technology platform, agency, consulting)
- Whether Algolia has a known integration with their platform
- Co-sell opportunity description

Focus on platforms where Algolia has existing connectors: Salesforce Commerce Cloud, Adobe Commerce (Magento), Shopify, BigCommerce, commercetools, SAP Commerce Cloud."""


def build_vertical_case_studies_prompt(company_name: str, domain: str, industry: str) -> str:
    """Build Perplexity prompt for vertical case study discovery.

    Args:
        company_name: Name of the prospect company.
        domain: Domain of the prospect.
        industry: Industry/vertical of the prospect.

    Returns:
        Formatted prompt string.
    """
    return f"""Find Algolia customer case studies and success stories relevant to {company_name} ({domain}) in the {industry} industry.

Search for:
1. Algolia case studies in the {industry} vertical
2. Companies similar to {company_name} that use Algolia
3. Key metrics and outcomes from these case studies (conversion lift, search revenue, time-to-value)
4. Published case study URLs on algolia.com

For each case study, provide:
- Customer name
- Industry
- Primary use case (site search, product discovery, recommendations, etc.)
- Key metric/outcome if available
- URL to the case study if available

Focus on the most relevant and impressive results for a {industry} company like {company_name}."""


def build_partnership_news_prompt(company_name: str, domain: str) -> str:
    """Build Perplexity prompt for recent partnership news.

    Args:
        company_name: Name of the prospect company.
        domain: Domain of the prospect.

    Returns:
        Formatted prompt string.
    """
    return f"""Find recent partnership announcements and news involving {company_name} ({domain}) from the last 6 months.

Focus on:
1. New technology partnerships or platform migrations
2. SI or consulting firm engagements
3. Digital transformation initiatives
4. E-commerce platform changes or upgrades
5. Any mention of search technology, AI, or personalization partnerships

For each item, provide:
- Brief description of the partnership/news
- Date if available
- Source URL if available"""


def build_competitor_partners_prompt(
    company_name: str,
    domain: str,
    competitors: list[dict[str, Any]],
) -> str:
    """Build Perplexity prompt for competitor partner ecosystem research.

    Args:
        company_name: Name of the prospect company.
        domain: Domain of the prospect.
        competitors: List of competitor dicts with 'company_name', 'domain' keys.

    Returns:
        Formatted prompt string.
    """
    comp_list = "\n".join(
        f"- {c.get('company_name', '')} ({c.get('domain', '')})" for c in competitors[:5]
    )

    return f"""Research the partner ecosystems of {company_name}'s competitors:

{comp_list}

For each competitor, find:
1. Known technology partners and platform vendors
2. System integrator relationships
3. Any partners that overlap with {company_name}'s known partners
4. Search technology vendor (do they use Algolia, Elasticsearch, Coveo, etc.?)

This helps the sales team understand the competitive landscape for partner-led deals."""


# ---------------------------------------------------------------------------
# Collector class
# ---------------------------------------------------------------------------


class PartnerCollector:
    """Collects partner intelligence via Crossbeam API + Perplexity fallback.

    Uses Crossbeam when CROSSBEAM_API_KEY is available for partner overlap data.
    Always uses Perplexity for SI relationships, tech partners, case studies,
    partnership news, and competitor partner ecosystems.
    """

    def __init__(self) -> None:
        self._use_crossbeam = bool(settings.crossbeam_api_key)
        logger.info(
            "[PartnerCollector] initialized",
            use_crossbeam=self._use_crossbeam,
        )

    async def collect_all(
        self,
        domain: str,
        company_name: str,
        industry: str,
        competitors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Collect all partner intelligence for a domain.

        Args:
            domain: Target domain (e.g. 'dell.com').
            company_name: Company name for prompts.
            industry: Industry vertical for case study matching.
            competitors: List of competitor dicts with 'company_name', 'domain' keys.

        Returns:
            Dict with keys: crossbeam_overlaps, crossbeam_populations,
            si_research, tech_partners_research, case_studies_research,
            partnership_news, competitor_partners_research, crossbeam_available.
        """
        logger.info(
            "[PartnerCollector] collect_all started",
            domain=domain,
            company_name=company_name,
            industry=industry,
            competitor_count=len(competitors),
            use_crossbeam=self._use_crossbeam,
        )

        raw: dict[str, Any] = {
            "crossbeam_overlaps": {},
            "crossbeam_populations": {},
            "si_research": "",
            "tech_partners_research": "",
            "case_studies_research": "",
            "partnership_news": "",
            "competitor_partners_research": "",
            "crossbeam_available": False,
        }

        # Phase 1: Crossbeam data (if available)
        if self._use_crossbeam:
            crossbeam_tasks = [
                self._collect_crossbeam_overlaps(domain),
                self._collect_crossbeam_populations(),
            ]
            crossbeam_results = await asyncio.gather(*crossbeam_tasks, return_exceptions=True)

            if not isinstance(crossbeam_results[0], Exception):
                raw["crossbeam_overlaps"] = crossbeam_results[0]
                raw["crossbeam_available"] = True
            else:
                logger.error(
                    "[PartnerCollector] crossbeam overlaps failed, falling back to Perplexity",
                    domain=domain,
                    error=str(crossbeam_results[0]),
                )

            if not isinstance(crossbeam_results[1], Exception):
                raw["crossbeam_populations"] = crossbeam_results[1]
            else:
                logger.error(
                    "[PartnerCollector] crossbeam populations failed",
                    error=str(crossbeam_results[1]),
                )

        # Phase 2: Perplexity research (always runs)
        perplexity_tasks = [
            self._collect_si_relationships(company_name, domain),
            self._collect_tech_partners(company_name, domain),
            self._collect_case_studies(company_name, domain, industry),
            self._collect_partnership_news(company_name, domain),
        ]

        # Competitor research only if competitors provided
        if competitors:
            perplexity_tasks.append(
                self._collect_competitor_partners(company_name, domain, competitors)
            )

        perplexity_results = await asyncio.gather(*perplexity_tasks, return_exceptions=True)

        # Map results to raw dict
        result_keys = [
            "si_research",
            "tech_partners_research",
            "case_studies_research",
            "partnership_news",
        ]
        if competitors:
            result_keys.append("competitor_partners_research")

        for i, key in enumerate(result_keys):
            if isinstance(perplexity_results[i], Exception):
                logger.error(
                    "[PartnerCollector] perplexity query failed",
                    key=key,
                    error=str(perplexity_results[i]),
                )
                raw[key] = ""
            else:
                raw[key] = perplexity_results[i]

        logger.info(
            "[PartnerCollector] collect_all complete",
            domain=domain,
            crossbeam_available=raw["crossbeam_available"],
            si_research_length=len(raw["si_research"]),
            tech_partners_length=len(raw["tech_partners_research"]),
            case_studies_length=len(raw["case_studies_research"]),
            news_length=len(raw["partnership_news"]),
            competitor_length=len(raw["competitor_partners_research"]),
        )

        return raw

    # ------------------------------------------------------------------
    # Crossbeam collectors
    # ------------------------------------------------------------------

    async def _collect_crossbeam_overlaps(self, domain: str) -> dict[str, Any]:
        """Collect Crossbeam overlap data for a domain.

        Args:
            domain: Target domain.

        Returns:
            Crossbeam overlaps response dict.
        """
        try:
            return await _crossbeam_get_overlaps(domain)
        except Exception as exc:
            logger.error(
                "[PartnerCollector] crossbeam overlap collection failed",
                domain=domain,
                error=str(exc),
            )
            raise

    async def _collect_crossbeam_populations(self) -> dict[str, Any]:
        """Collect Crossbeam partner population data.

        Returns:
            Crossbeam populations response dict.
        """
        try:
            return await _crossbeam_get_partner_populations()
        except Exception as exc:
            logger.error(
                "[PartnerCollector] crossbeam population collection failed",
                error=str(exc),
            )
            raise

    # ------------------------------------------------------------------
    # Perplexity collectors
    # ------------------------------------------------------------------

    async def _collect_si_relationships(
        self,
        company_name: str,
        domain: str,
    ) -> str:
        """Collect SI relationship data via Perplexity.

        Args:
            company_name: Company name.
            domain: Company domain.

        Returns:
            Raw text from Perplexity about SI relationships.
        """
        try:
            return await _perplexity_query(
                build_si_relationships_prompt(company_name, domain),
                f"si_relationships:{domain}",
            )
        except Exception as exc:
            logger.error(
                "[PartnerCollector] SI relationship collection failed",
                domain=domain,
                error=str(exc),
            )
            raise

    async def _collect_tech_partners(
        self,
        company_name: str,
        domain: str,
    ) -> str:
        """Collect technology partner data via Perplexity.

        Args:
            company_name: Company name.
            domain: Company domain.

        Returns:
            Raw text from Perplexity about tech partners.
        """
        try:
            return await _perplexity_query(
                build_tech_partners_prompt(company_name, domain),
                f"tech_partners:{domain}",
            )
        except Exception as exc:
            logger.error(
                "[PartnerCollector] tech partner collection failed",
                domain=domain,
                error=str(exc),
            )
            raise

    async def _collect_case_studies(
        self,
        company_name: str,
        domain: str,
        industry: str,
    ) -> str:
        """Collect vertical case study data via Perplexity.

        Args:
            company_name: Company name.
            domain: Company domain.
            industry: Industry vertical.

        Returns:
            Raw text from Perplexity about vertical case studies.
        """
        try:
            return await _perplexity_query(
                build_vertical_case_studies_prompt(company_name, domain, industry),
                f"case_studies:{domain}",
            )
        except Exception as exc:
            logger.error(
                "[PartnerCollector] case study collection failed",
                domain=domain,
                error=str(exc),
            )
            raise

    async def _collect_partnership_news(
        self,
        company_name: str,
        domain: str,
    ) -> str:
        """Collect partnership news via Perplexity.

        Args:
            company_name: Company name.
            domain: Company domain.

        Returns:
            Raw text from Perplexity about recent partnerships.
        """
        try:
            return await _perplexity_query(
                build_partnership_news_prompt(company_name, domain),
                f"partnership_news:{domain}",
            )
        except Exception as exc:
            logger.error(
                "[PartnerCollector] partnership news collection failed",
                domain=domain,
                error=str(exc),
            )
            raise

    async def _collect_competitor_partners(
        self,
        company_name: str,
        domain: str,
        competitors: list[dict[str, Any]],
    ) -> str:
        """Collect competitor partner ecosystem data via Perplexity.

        Args:
            company_name: Company name.
            domain: Company domain.
            competitors: List of competitor dicts.

        Returns:
            Raw text from Perplexity about competitor partners.
        """
        try:
            return await _perplexity_query(
                build_competitor_partners_prompt(company_name, domain, competitors),
                f"competitor_partners:{domain}",
            )
        except Exception as exc:
            logger.error(
                "[PartnerCollector] competitor partner collection failed",
                domain=domain,
                error=str(exc),
            )
            raise
