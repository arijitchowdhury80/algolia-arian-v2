"""Intel TechStack collector -- calls BuiltWith v22 API and classifies technologies."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

from prism_platform.config import settings
from prism_platform.core.types import EvidenceTier, Source
from prism_platform.modules.intel_techstack.schemas import (
    CompetitorTechStack,
    SearchVendor,
    TechStackOutput,
)

logger = structlog.get_logger(__name__)

BUILTWITH_API_URL = "https://api.builtwith.com/v22/api.json"

KNOWN_SEARCH_VENDORS = [
    "Algolia",
    "Elasticsearch",
    "Solr",
    "Coveo",
    "Bloomreach",
    "Searchspring",
    "Klevu",
    "Constructor",
    "Lucidworks",
    "Swiftype",
    "Yext",
    "SearchStax",
]


def _categories_contain(categories: list[str], *keywords: str) -> bool:
    """Check if any category/group name contains any of the given keywords (case-insensitive).

    Works with both paid API categories and free API group+category names.
    """
    lower_cats = [c.lower() for c in categories]
    return any(kw.lower() in cat for cat in lower_cats for kw in keywords)


def _match_search_vendor(tech_name: str) -> str | None:
    """Return the canonical vendor name if tech_name matches a known search vendor."""
    name_lower = tech_name.lower()
    for vendor in KNOWN_SEARCH_VENDORS:
        if vendor.lower() in name_lower:
            return vendor
    return None


class TechStackCollector:
    """Collects technology stack data from the BuiltWith v22 API."""

    async def collect_all(self, domain: str) -> tuple[TechStackOutput, list[Source]]:
        """Call BuiltWith and return classified tech stack with sources.

        Args:
            domain: The website domain to look up (e.g. "dell.com").

        Returns:
            Tuple of (TechStackOutput, list of Source provenance records).
        """
        logger.info("[TechStack] collect_all started", domain=domain)
        sources: list[Source] = []

        try:
            raw_technologies = await self._fetch_builtwith(domain)
        except Exception as error:
            logger.error(
                "[TechStack] BuiltWith API call failed",
                error=str(error),
                context={"domain": domain},
            )
            return TechStackOutput(tech_stack_summary="BuiltWith API call failed"), sources

        try:
            output = self._classify_technologies(raw_technologies, domain)
        except Exception as error:
            logger.error(
                "[TechStack] technology classification failed",
                error=str(error),
                context={"domain": domain},
            )
            return TechStackOutput(tech_stack_summary="Classification failed"), sources

        # Build source provenance
        sources.append(
            Source(
                field="all_technologies",
                value=f"{len(raw_technologies)} technologies detected",
                tier=EvidenceTier.VERIFIED,
                source_url=f"{BUILTWITH_API_URL}?KEY=***&LOOKUP={domain}",
                source_label="BuiltWith v22 API",
                method="direct_api",
            )
        )
        if output.search_vendor:
            sources.append(
                Source(
                    field="search_vendor",
                    value=output.search_vendor.name,
                    tier=output.search_vendor.evidence_tier,
                    source_url=f"{BUILTWITH_API_URL}?KEY=***&LOOKUP={domain}",
                    source_label="BuiltWith v22 API",
                    method="direct_api",
                )
            )

        logger.info(
            "[TechStack] collect_all completed",
            domain=domain,
            tech_count=len(raw_technologies),
            search_vendor=output.search_vendor.name if output.search_vendor else None,
            algolia_detected=output.algolia_detected,
        )
        return output, sources

    async def _fetch_builtwith(self, domain: str) -> list[dict[str, Any]]:
        """Call the BuiltWith v22 API and extract the technology list.

        The v22 API returns:
        {
          "Results": [{
            "Result": {
              "Paths": [{
                "Technologies": [{
                  "Name": "...",
                  "Description": "...",
                  "Tag": "...",
                  "Link": "...",
                  "Categories": ["..."],
                  ...
                }]
              }]
            }
          }]
        }

        Args:
            domain: Domain to look up.

        Returns:
            List of technology dicts, each with Name, Tag, Categories keys.
        """
        logger.info("[TechStack] calling BuiltWith v22 API", domain=domain)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                BUILTWITH_API_URL,
                params={
                    "KEY": settings.builtwith_api_key,
                    "LOOKUP": domain,
                    "LIVEONLY": "yes",
                },
            )
            resp.raise_for_status()

        data = resp.json()
        technologies: list[dict[str, Any]] = []

        results = data.get("Results", [])
        for result_wrapper in results:
            result = result_wrapper.get("Result", {})
            paths = result.get("Paths", [])
            for path in paths:
                techs = path.get("Technologies", [])
                for tech in techs:
                    technologies.append(
                        {
                            "Name": tech.get("Name", ""),
                            "Tag": tech.get("Tag", ""),
                            "Categories": tech.get("Categories", []),
                        }
                    )

        logger.info(
            "[TechStack] BuiltWith returned technologies",
            domain=domain,
            count=len(technologies),
        )
        return technologies

    async def collect_competitor(self, domain: str, company_name: str) -> CompetitorTechStack:
        """Collect tech stack for a single competitor domain.

        Args:
            domain: Competitor's website domain.
            company_name: Competitor's company name.

        Returns:
            CompetitorTechStack with classified technology data.
        """
        logger.info(
            "[TechStack] collecting competitor tech stack",
            domain=domain,
            company_name=company_name,
        )
        try:
            raw_technologies = await self._fetch_builtwith(domain)
        except httpx.TimeoutException as exc:
            logger.error(
                "[TechStack] BuiltWith timeout for competitor",
                domain=domain,
                error=str(exc),
            )
            return CompetitorTechStack(
                company_name=company_name,
                domain=domain,
            )
        except httpx.HTTPStatusError as exc:
            logger.error(
                "[TechStack] BuiltWith HTTP error for competitor",
                domain=domain,
                status_code=exc.response.status_code,
                error=str(exc),
            )
            return CompetitorTechStack(
                company_name=company_name,
                domain=domain,
            )
        except Exception:
            logger.exception(
                "[TechStack] unexpected error collecting competitor",
                domain=domain,
            )
            return CompetitorTechStack(
                company_name=company_name,
                domain=domain,
            )

        classified = self._classify_technologies(raw_technologies, domain)

        is_algolia = any(
            _match_search_vendor(t.get("Name", "")) == "Algolia" for t in raw_technologies
        )

        return CompetitorTechStack(
            company_name=company_name,
            domain=domain,
            search_vendor=classified.search_vendor,
            ecommerce_platform=classified.ecommerce_platform,
            all_technologies=raw_technologies,
            tech_count=len(raw_technologies),
            is_algolia_customer=is_algolia,
        )

    async def collect_all_with_competitors(
        self,
        prospect_domain: str,
        competitor_data: list[dict[str, str]],
    ) -> tuple[TechStackOutput, list[Source]]:
        """Collect tech stack for the prospect and all competitors in parallel.

        Args:
            prospect_domain: The prospect's website domain.
            competitor_data: List of dicts with keys ``company_name`` and ``domain``.

        Returns:
            Tuple of (TechStackOutput with competitor data populated, list of Source records).
        """
        logger.info(
            "[TechStack] collect_all_with_competitors started",
            prospect_domain=prospect_domain,
            competitor_count=len(competitor_data),
        )

        # Run prospect + all competitors in parallel
        prospect_coro = self.collect_all(prospect_domain)
        competitor_coros = [
            self.collect_competitor(
                domain=c["domain"],
                company_name=c["company_name"],
            )
            for c in competitor_data
            if c.get("domain")
        ]

        all_results = await asyncio.gather(prospect_coro, *competitor_coros, return_exceptions=True)

        # First result is the prospect
        prospect_result = all_results[0]
        if isinstance(prospect_result, BaseException):
            logger.error(
                "[TechStack] prospect collection failed in gather",
                error=str(prospect_result),
            )
            output = TechStackOutput(tech_stack_summary="Prospect collection failed")
            sources: list[Source] = []
        else:
            output, sources = prospect_result

        # Remaining results are competitors
        competitor_stacks: list[CompetitorTechStack] = []
        for i, result in enumerate(all_results[1:]):
            if isinstance(result, BaseException):
                logger.error(
                    "[TechStack] competitor collection failed in gather",
                    competitor_index=i,
                    error=str(result),
                )
                continue
            competitor_stacks.append(result)

        # Detect Golden Angle -- competitors using Algolia
        golden_angle_competitors = [
            cs.company_name for cs in competitor_stacks if cs.is_algolia_customer
        ]

        # Build comparative summary
        comparative_summary = self._build_comparative_summary(
            prospect_domain=prospect_domain,
            prospect_vendor=output.search_vendor,
            competitor_stacks=competitor_stacks,
        )

        # Add competitor sources
        for cs in competitor_stacks:
            sources.append(
                Source(
                    field=f"competitor_tech_stack.{cs.domain}",
                    value=f"{cs.tech_count} technologies detected",
                    tier=EvidenceTier.VERIFIED,
                    source_url=f"{BUILTWITH_API_URL}?KEY=***&LOOKUP={cs.domain}",
                    source_label="BuiltWith v22 API",
                    method="direct_api",
                )
            )

        # Update the output with competitor data
        output = output.model_copy(
            update={
                "competitor_tech_stacks": competitor_stacks,
                "comparative_summary": comparative_summary,
                "golden_angle_competitors": golden_angle_competitors,
            }
        )

        logger.info(
            "[TechStack] collect_all_with_competitors completed",
            prospect_domain=prospect_domain,
            competitors_collected=len(competitor_stacks),
            golden_angle_count=len(golden_angle_competitors),
        )
        return output, sources

    @staticmethod
    def _build_comparative_summary(
        prospect_domain: str,
        prospect_vendor: SearchVendor | None,
        competitor_stacks: list[CompetitorTechStack],
    ) -> str:
        """Build a human-readable comparative summary of search vendors.

        Args:
            prospect_domain: The prospect's domain.
            prospect_vendor: The prospect's detected search vendor (may be None).
            competitor_stacks: List of competitor tech stacks.

        Returns:
            Summary string describing search vendor landscape.
        """
        parts: list[str] = []
        prospect_name = prospect_vendor.name if prospect_vendor else "no detected search vendor"
        parts.append(f"Prospect ({prospect_domain}) uses {prospect_name}.")

        for cs in competitor_stacks:
            vendor_name = cs.search_vendor.name if cs.search_vendor else "no detected search vendor"
            algolia_note = " [ALGOLIA CUSTOMER]" if cs.is_algolia_customer else ""
            parts.append(f"{cs.company_name} ({cs.domain}) uses {vendor_name}.{algolia_note}")

        return " ".join(parts)

    def _classify_technologies(
        self, technologies: list[dict[str, Any]], domain: str
    ) -> TechStackOutput:
        """Classify raw technologies into structured output.

        Args:
            technologies: Raw tech list from BuiltWith.
            domain: The domain being analyzed.

        Returns:
            Fully populated TechStackOutput.
        """
        search_vendor: SearchVendor | None = None
        ecommerce_platform: str | None = None
        cms: str | None = None
        cdn: str | None = None
        analytics: list[str] = []
        personalization: list[str] = []
        bot_detection: str | None = None
        algolia_detected = False

        for tech in technologies:
            name: str = tech.get("Name", "")
            categories: list[str] = tech.get("Categories", [])

            # Search vendor detection
            vendor_match = _match_search_vendor(name)
            if vendor_match:
                if vendor_match == "Algolia":
                    algolia_detected = True
                if search_vendor is None:
                    search_vendor = SearchVendor(
                        name=vendor_match,
                        status="ACTIVE",
                        detection_source="BuiltWith v22 API",
                        evidence_tier=EvidenceTier.VERIFIED,
                    )

            # Category-based classification
            if (
                _categories_contain(categories, "search")
                and vendor_match is None
                and search_vendor is None
            ):
                # Detected a search-category tech not in our known vendors list
                search_vendor = SearchVendor(
                    name=name,
                    status="TAG_ONLY",
                    detection_source="BuiltWith v22 API (category match)",
                    evidence_tier=EvidenceTier.WEBFETCH,
                )

            if (
                _categories_contain(categories, "ecommerce", "shopping-cart")
                and ecommerce_platform is None
            ):
                ecommerce_platform = name

            if _categories_contain(categories, "cms") and cms is None:
                cms = name

            if _categories_contain(categories, "cdn") and cdn is None:
                cdn = name

            if _categories_contain(categories, "analytics") and name not in analytics:
                analytics.append(name)

            if (
                _categories_contain(categories, "personalization", "a-b-testing")
                and name not in personalization
            ):
                personalization.append(name)

            if _categories_contain(categories, "bot", "captcha") and bot_detection is None:
                bot_detection = name

        # Build summary
        parts: list[str] = []
        if search_vendor:
            parts.append(f"Search: {search_vendor.name} ({search_vendor.status})")
        if ecommerce_platform:
            parts.append(f"Ecommerce: {ecommerce_platform}")
        if cms:
            parts.append(f"CMS: {cms}")
        if cdn:
            parts.append(f"CDN: {cdn}")
        if analytics:
            parts.append(f"Analytics: {', '.join(analytics)}")
        if personalization:
            parts.append(f"Personalization: {', '.join(personalization)}")
        if bot_detection:
            parts.append(f"Bot Detection: {bot_detection}")

        summary = f"{domain}: {'; '.join(parts)}" if parts else f"{domain}: No notable technologies"

        return TechStackOutput(
            search_vendor=search_vendor,
            ecommerce_platform=ecommerce_platform,
            cms=cms,
            cdn=cdn,
            analytics=analytics,
            personalization=personalization,
            bot_detection=bot_detection,
            all_technologies=technologies,
            removed_technologies=[],
            tech_stack_summary=summary,
            algolia_detected=algolia_detected,
        )
