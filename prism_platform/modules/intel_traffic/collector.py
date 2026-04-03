"""Intel Traffic collector -- SimilarWeb API client for traffic intelligence.

Calls 10 SimilarWeb endpoints to collect comprehensive traffic data:
1. Monthly visits
2. Traffic sources overview
3. Geography breakdown
4. Organic keywords
5. Paid keywords
6. Engagement metrics
7. Device split (desktop + mobile)
8. Audience interests (also-visited)
9. Referrals
10. Popular pages

Every endpoint call is wrapped in try/catch -- SimilarWeb returns 403/404 for
some domains or endpoints. We log warnings and continue with partial data.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog

from prism_platform.config import settings
from prism_platform.modules.intel_traffic.schemas import (
    CompetitorTraffic,
    DeviceSplit,
    Engagement,
    GeoBreakdown,
    Keyword,
    MonthlyVisit,
    TrafficSource,
)

logger = structlog.get_logger(__name__)

SIMILARWEB_BASE = "https://api.similarweb.com/v1/website"
SIMILARWEB_TIMEOUT = 30.0

# ISO 3166-1 numeric → alpha-2 mapping for top countries
_COUNTRY_CODES: dict[int, tuple[str, str]] = {
    840: ("United States", "US"),
    826: ("United Kingdom", "GB"),
    276: ("Germany", "DE"),
    250: ("France", "FR"),
    392: ("Japan", "JP"),
    156: ("China", "CN"),
    356: ("India", "IN"),
    124: ("Canada", "CA"),
    36: ("Australia", "AU"),
    76: ("Brazil", "BR"),
    410: ("South Korea", "KR"),
    380: ("Italy", "IT"),
    724: ("Spain", "ES"),
    528: ("Netherlands", "NL"),
    484: ("Mexico", "MX"),
    643: ("Russia", "RU"),
    756: ("Switzerland", "CH"),
    752: ("Sweden", "SE"),
    578: ("Norway", "NO"),
    208: ("Denmark", "DK"),
    616: ("Poland", "PL"),
    56: ("Belgium", "BE"),
    40: ("Austria", "AT"),
    376: ("Israel", "IL"),
    702: ("Singapore", "SG"),
    344: ("Hong Kong", "HK"),
    158: ("Taiwan", "TW"),
    764: ("Thailand", "TH"),
    360: ("Indonesia", "ID"),
    608: ("Philippines", "PH"),
    710: ("South Africa", "ZA"),
    792: ("Turkey", "TR"),
    818: ("Egypt", "EG"),
    682: ("Saudi Arabia", "SA"),
    784: ("United Arab Emirates", "AE"),
    32: ("Argentina", "AR"),
    170: ("Colombia", "CO"),
    152: ("Chile", "CL"),
    554: ("New Zealand", "NZ"),
    372: ("Ireland", "IE"),
    246: ("Finland", "FI"),
    203: ("Czech Republic", "CZ"),
    620: ("Portugal", "PT"),
    642: ("Romania", "RO"),
    348: ("Hungary", "HU"),
    804: ("Ukraine", "UA"),
    458: ("Malaysia", "MY"),
    704: ("Vietnam", "VN"),
}


def _date_range() -> tuple[str, str]:
    """Return start_date and end_date for SimilarWeb as YYYY-MM strings.

    SimilarWeb data has a ~2 month lag, so we request data ending 2 months ago
    and covering the 6 months before that.

    Returns:
        Tuple of (start_date, end_date) in YYYY-MM format.
    """
    now = datetime.utcnow()
    # End date: 2 months ago (SimilarWeb data lag)
    end = (now.replace(day=1) - timedelta(days=60)).replace(day=1)
    # Start date: 6 months before end
    start = (end - timedelta(days=150)).replace(day=1)
    return start.strftime("%Y-%m"), end.strftime("%Y-%m")


def _default_params() -> dict[str, str]:
    """Return the default query parameters for SimilarWeb API calls.

    Returns:
        Dict of common query parameters.
    """
    start, end = _date_range()
    return {
        "api_key": settings.similarweb_api_key,
        "start_date": start,
        "end_date": end,
        "country": "world",
        "main_domain_only": "true",
        "granularity": "monthly",
    }


class TrafficCollector:
    """Collects raw traffic data from SimilarWeb API for a domain."""

    async def collect_domain(self, domain: str) -> dict[str, Any]:
        """Collect all traffic data for a single domain.

        Calls all 10 SimilarWeb endpoints. Each endpoint failure is logged
        and the corresponding result is set to its empty/default value.

        Args:
            domain: Website domain to analyze, e.g. 'dell.com'.

        Returns:
            Dict containing structured traffic data:
                monthly_visits, traffic_sources, engagement, device_split,
                top_countries, organic_keywords, paid_keywords,
                audience_interests, referrals, popular_pages.
        """
        logger.info("[TrafficCollector] collect_domain started", domain=domain)

        result: dict[str, Any] = {
            "monthly_visits": [],
            "traffic_sources": [],
            "engagement": None,
            "device_split": None,
            "top_countries": [],
            "organic_keywords": [],
            "paid_keywords": [],
            "audience_interests": [],
            "referrals": [],
            "popular_pages": [],
        }

        async with httpx.AsyncClient(timeout=SIMILARWEB_TIMEOUT) as client:
            # 1. Monthly visits
            result["monthly_visits"] = await self._fetch_monthly_visits(client, domain)

            # 2. Traffic sources
            result["traffic_sources"] = await self._fetch_traffic_sources(client, domain)

            # 3. Geography
            result["top_countries"] = await self._fetch_geo(client, domain)

            # 4. Organic keywords
            result["organic_keywords"] = await self._fetch_keywords(
                client, domain, keyword_type="organic"
            )

            # 5. Paid keywords
            result["paid_keywords"] = await self._fetch_keywords(
                client, domain, keyword_type="paid"
            )

            # 6. Engagement
            result["engagement"] = await self._fetch_engagement(client, domain)

            # 7. Device split
            result["device_split"] = await self._fetch_device_split(client, domain)

            # 8. Audience interests
            result["audience_interests"] = await self._fetch_audience_interests(client, domain)

            # 9. Referrals
            result["referrals"] = await self._fetch_referrals(client, domain)

            # 10. Popular pages
            result["popular_pages"] = await self._fetch_popular_pages(client, domain)

        populated = [k for k, v in result.items() if v]
        logger.info(
            "[TrafficCollector] collect_domain completed",
            domain=domain,
            endpoints_populated=len(populated),
            populated_keys=populated,
        )
        return result

    async def collect_competitor(self, domain: str, company_name: str) -> CompetitorTraffic:
        """Collect a subset of traffic data for a competitor domain.

        Only fetches visits, engagement, traffic sources, keywords, and device split.
        Fewer endpoints than the prospect to reduce API usage.

        Args:
            domain: Competitor domain, e.g. 'hp.com'.
            company_name: Competitor company name for labeling.

        Returns:
            CompetitorTraffic model with available data.
        """
        logger.info(
            "[TrafficCollector] collect_competitor started",
            domain=domain,
            company_name=company_name,
        )

        total_visits: int | None = None
        bounce_rate: float | None = None
        pages_per_visit: float | None = None
        traffic_sources: list[TrafficSource] = []
        top_keywords: list[Keyword] = []
        device_split: DeviceSplit | None = None

        async with httpx.AsyncClient(timeout=SIMILARWEB_TIMEOUT) as client:
            # Engagement (bounce rate, pages/visit, total visits)
            eng = await self._fetch_engagement(client, domain)
            if eng is not None:
                total_visits = eng.total_visits
                bounce_rate = eng.bounce_rate
                pages_per_visit = eng.pages_per_visit

            # Traffic sources
            traffic_sources = await self._fetch_traffic_sources(client, domain)

            # Organic keywords (top 5 only)
            raw_keywords = await self._fetch_keywords(client, domain, keyword_type="organic")
            top_keywords = raw_keywords[:5]

            # Device split
            device_split = await self._fetch_device_split(client, domain)

        logger.info(
            "[TrafficCollector] collect_competitor completed",
            domain=domain,
            company_name=company_name,
            has_engagement=bounce_rate is not None,
            source_count=len(traffic_sources),
            keyword_count=len(top_keywords),
        )

        return CompetitorTraffic(
            company_name=company_name,
            domain=domain,
            total_visits=total_visits,
            bounce_rate=bounce_rate,
            pages_per_visit=pages_per_visit,
            traffic_sources=traffic_sources,
            top_keywords=top_keywords,
            device_split=device_split,
        )

    # ------------------------------------------------------------------
    # Endpoint fetchers
    # ------------------------------------------------------------------

    async def _fetch_monthly_visits(
        self, client: httpx.AsyncClient, domain: str
    ) -> list[MonthlyVisit]:
        """Fetch monthly visit counts from SimilarWeb.

        Args:
            client: httpx async client.
            domain: Domain to query.

        Returns:
            List of MonthlyVisit models, or empty list on failure.
        """
        url = f"{SIMILARWEB_BASE}/{domain}/total-traffic-and-engagement/visits"
        try:
            resp = await client.get(url, params=_default_params())
            resp.raise_for_status()
            data = resp.json()
            visits_list = data.get("visits", [])
            results: list[MonthlyVisit] = []
            for entry in visits_list:
                try:
                    date_str = entry.get("date", "")
                    # SimilarWeb returns date as "YYYY-MM-DD"
                    dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    results.append(
                        MonthlyVisit(
                            year=dt.year,
                            month=dt.month,
                            visits=int(entry.get("visits", 0)),
                        )
                    )
                except (ValueError, TypeError) as parse_err:
                    logger.warning(
                        "[TrafficCollector] skipping malformed visit entry",
                        domain=domain,
                        entry=entry,
                        error=str(parse_err),
                    )
            logger.info(
                "[TrafficCollector] monthly visits fetched",
                domain=domain,
                count=len(results),
            )
            return results
        except httpx.TimeoutException:
            logger.error("[TrafficCollector] monthly visits timeout", domain=domain)
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "[TrafficCollector] monthly visits HTTP error",
                domain=domain,
                status_code=exc.response.status_code,
            )
            return []
        except Exception:
            logger.exception("[TrafficCollector] monthly visits unexpected error", domain=domain)
            return []

    async def _fetch_traffic_sources(
        self, client: httpx.AsyncClient, domain: str
    ) -> list[TrafficSource]:
        """Fetch traffic source breakdown from SimilarWeb.

        Args:
            client: httpx async client.
            domain: Domain to query.

        Returns:
            List of TrafficSource models, or empty list on failure.
        """
        url = f"{SIMILARWEB_BASE}/{domain}/traffic-sources/overview"
        try:
            resp = await client.get(url, params=_default_params())
            resp.raise_for_status()
            data = resp.json()

            # SimilarWeb overview returns an array of records with source_type field.
            # source_type values: "Direct", "Search / Organic", "Search / Paid",
            # "Social", "Referrals", "Mail", "Display Ads"
            source_type_mapping: dict[str, str] = {
                "Direct": "direct",
                "Mail": "email",
                "Referrals": "referral",
                "Social": "social",
                "Search / Organic": "organic_search",
                "Search / Paid": "paid_search",
                "Display Ads": "display",
            }

            results: list[TrafficSource] = []
            # Aggregate shares by our source type (multiple records may map
            # to the same type, e.g. Google Organic + Bing Organic)
            aggregated: dict[str, float] = {}
            overview = data.get("overview", data.get("visits", []))
            if isinstance(overview, list):
                for entry in overview:
                    sw_type = entry.get("source_type", "")
                    our_key = source_type_mapping.get(sw_type)
                    if our_key is None:
                        continue
                    try:
                        share = float(entry.get("share", 0))
                        aggregated[our_key] = aggregated.get(our_key, 0.0) + share
                    except (ValueError, TypeError):
                        pass

            for our_key, share in aggregated.items():
                pct = round(share * 100.0, 2)
                results.append(TrafficSource(source_type=our_key, share_pct=pct))

            logger.info(
                "[TrafficCollector] traffic sources fetched",
                domain=domain,
                count=len(results),
            )
            return results
        except httpx.TimeoutException:
            logger.error("[TrafficCollector] traffic sources timeout", domain=domain)
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "[TrafficCollector] traffic sources HTTP error",
                domain=domain,
                status_code=exc.response.status_code,
            )
            return []
        except Exception:
            logger.exception("[TrafficCollector] traffic sources unexpected error", domain=domain)
            return []

    async def _fetch_geo(self, client: httpx.AsyncClient, domain: str) -> list[GeoBreakdown]:
        """Fetch geographic traffic breakdown from SimilarWeb.

        Args:
            client: httpx async client.
            domain: Domain to query.

        Returns:
            List of GeoBreakdown models (top 10), or empty list on failure.
        """
        url = f"{SIMILARWEB_BASE}/{domain}/geo/traffic-by-country"
        try:
            resp = await client.get(url, params=_default_params())
            resp.raise_for_status()
            data = resp.json()
            records = data.get("records", [])

            results: list[GeoBreakdown] = []
            for rec in records[:10]:
                try:
                    share = float(rec.get("share", 0)) * 100.0
                    visits = rec.get("visits")
                    # SimilarWeb returns numeric ISO 3166-1 country codes
                    numeric_code = int(rec.get("country", 0))
                    country_info = _COUNTRY_CODES.get(numeric_code)
                    if country_info:
                        country_name, alpha2 = country_info
                    else:
                        country_name = str(numeric_code)
                        alpha2 = str(numeric_code)
                    results.append(
                        GeoBreakdown(
                            country=country_name,
                            country_code=alpha2,
                            share_pct=round(share, 2),
                            visits=int(visits) if visits is not None else None,
                        )
                    )
                except (ValueError, TypeError) as parse_err:
                    logger.warning(
                        "[TrafficCollector] skipping malformed geo entry",
                        domain=domain,
                        error=str(parse_err),
                    )

            logger.info(
                "[TrafficCollector] geo data fetched",
                domain=domain,
                count=len(results),
            )
            return results
        except httpx.TimeoutException:
            logger.error("[TrafficCollector] geo timeout", domain=domain)
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "[TrafficCollector] geo HTTP error",
                domain=domain,
                status_code=exc.response.status_code,
            )
            return []
        except Exception:
            logger.exception("[TrafficCollector] geo unexpected error", domain=domain)
            return []

    async def _fetch_keywords(
        self,
        client: httpx.AsyncClient,
        domain: str,
        keyword_type: str = "organic",
    ) -> list[Keyword]:
        """Fetch organic or paid keywords from SimilarWeb.

        Args:
            client: httpx async client.
            domain: Domain to query.
            keyword_type: 'organic' or 'paid'.

        Returns:
            List of Keyword models (top 20), or empty list on failure.
        """
        url = f"{SIMILARWEB_BASE}/{domain}/search-keywords/{keyword_type}"
        try:
            resp = await client.get(url, params=_default_params())
            resp.raise_for_status()
            data = resp.json()
            records = data.get("search", [])

            results: list[Keyword] = []
            for rec in records[:20]:
                try:
                    kw = rec.get("search_term", rec.get("keyword", ""))
                    share = float(rec.get("share", 0)) * 100.0
                    change = rec.get("change")
                    volume = rec.get("volume")

                    results.append(
                        Keyword(
                            keyword=kw,
                            share_pct=round(share, 4),
                            change_pct=float(change) * 100.0 if change is not None else None,
                            search_volume=int(volume) if volume is not None else None,
                            is_branded=False,  # Will be enriched later
                        )
                    )
                except (ValueError, TypeError) as parse_err:
                    logger.warning(
                        "[TrafficCollector] skipping malformed keyword entry",
                        domain=domain,
                        keyword_type=keyword_type,
                        error=str(parse_err),
                    )

            logger.info(
                "[TrafficCollector] keywords fetched",
                domain=domain,
                keyword_type=keyword_type,
                count=len(results),
            )
            return results
        except httpx.TimeoutException:
            logger.error(
                "[TrafficCollector] keywords timeout",
                domain=domain,
                keyword_type=keyword_type,
            )
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "[TrafficCollector] keywords HTTP error",
                domain=domain,
                keyword_type=keyword_type,
                status_code=exc.response.status_code,
            )
            return []
        except Exception:
            logger.exception(
                "[TrafficCollector] keywords unexpected error",
                domain=domain,
                keyword_type=keyword_type,
            )
            return []

    async def _fetch_engagement(self, client: httpx.AsyncClient, domain: str) -> Engagement | None:
        """Fetch engagement metrics (bounce rate, pages/visit, duration) from SimilarWeb.

        Args:
            client: httpx async client.
            domain: Domain to query.

        Returns:
            Engagement model or None on failure.
        """
        url = f"{SIMILARWEB_BASE}/{domain}/total-traffic-and-engagement/visits"
        try:
            resp = await client.get(url, params=_default_params())
            resp.raise_for_status()
            data = resp.json()

            visits_list = data.get("visits", [])
            total_visits = sum(int(v.get("visits", 0)) for v in visits_list)

            # Engagement metrics may be at the top level or in a nested structure
            bounce_rate = data.get("bounce_rate")
            pages_per_visit = data.get("pages_per_visit")
            avg_duration = data.get("average_visit_duration") or data.get("avg_visit_duration")

            engagement = Engagement(
                bounce_rate=float(bounce_rate) if bounce_rate is not None else None,
                pages_per_visit=(float(pages_per_visit) if pages_per_visit is not None else None),
                avg_visit_duration_seconds=(
                    float(avg_duration) if avg_duration is not None else None
                ),
                total_visits=total_visits if total_visits > 0 else None,
            )

            logger.info(
                "[TrafficCollector] engagement fetched",
                domain=domain,
                total_visits=total_visits,
                bounce_rate=bounce_rate,
            )
            return engagement
        except httpx.TimeoutException:
            logger.error("[TrafficCollector] engagement timeout", domain=domain)
            return None
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "[TrafficCollector] engagement HTTP error",
                domain=domain,
                status_code=exc.response.status_code,
            )
            return None
        except Exception:
            logger.exception("[TrafficCollector] engagement unexpected error", domain=domain)
            return None

    async def _fetch_device_split(
        self, client: httpx.AsyncClient, domain: str
    ) -> DeviceSplit | None:
        """Fetch desktop vs mobile traffic split from SimilarWeb.

        Makes two calls: one for desktop, one for mobile, then computes percentages.

        Args:
            client: httpx async client.
            domain: Domain to query.

        Returns:
            DeviceSplit model or None on failure.
        """
        desktop_visits = 0
        mobile_visits = 0

        for device in ("Desktop", "MobileWeb"):
            url = f"{SIMILARWEB_BASE}/{domain}/total-traffic-and-engagement/visits"
            params = {**_default_params(), "device": device}
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                visits_list = data.get("visits", [])
                total = sum(int(v.get("visits", 0)) for v in visits_list)
                if device == "Desktop":
                    desktop_visits = total
                else:
                    mobile_visits = total
            except httpx.TimeoutException:
                logger.error(
                    "[TrafficCollector] device split timeout",
                    domain=domain,
                    device=device,
                )
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "[TrafficCollector] device split HTTP error",
                    domain=domain,
                    device=device,
                    status_code=exc.response.status_code,
                )
            except Exception:
                logger.exception(
                    "[TrafficCollector] device split unexpected error",
                    domain=domain,
                    device=device,
                )

        combined = desktop_visits + mobile_visits
        if combined == 0:
            logger.warning("[TrafficCollector] no device split data", domain=domain)
            return None

        desktop_pct = round(desktop_visits / combined * 100.0, 2)
        mobile_pct = round(mobile_visits / combined * 100.0, 2)

        logger.info(
            "[TrafficCollector] device split fetched",
            domain=domain,
            desktop_pct=desktop_pct,
            mobile_pct=mobile_pct,
        )
        return DeviceSplit(
            desktop_pct=desktop_pct,
            mobile_pct=mobile_pct,
            desktop_visits=desktop_visits,
            mobile_visits=mobile_visits,
        )

    async def _fetch_audience_interests(
        self, client: httpx.AsyncClient, domain: str
    ) -> list[dict[str, Any]]:
        """Fetch audience interests (also-visited sites) from SimilarWeb.

        Args:
            client: httpx async client.
            domain: Domain to query.

        Returns:
            List of dicts with also-visited site info, or empty list on failure.
        """
        url = f"{SIMILARWEB_BASE}/{domain}/audience-interests/also-visited"
        try:
            resp = await client.get(url, params=_default_params())
            resp.raise_for_status()
            data = resp.json()
            records = data.get("also_visited", data.get("records", []))
            logger.info(
                "[TrafficCollector] audience interests fetched",
                domain=domain,
                count=len(records),
            )
            return records[:10] if isinstance(records, list) else []
        except httpx.TimeoutException:
            logger.error("[TrafficCollector] audience interests timeout", domain=domain)
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "[TrafficCollector] audience interests HTTP error",
                domain=domain,
                status_code=exc.response.status_code,
            )
            return []
        except Exception:
            logger.exception(
                "[TrafficCollector] audience interests unexpected error",
                domain=domain,
            )
            return []

    async def _fetch_referrals(
        self, client: httpx.AsyncClient, domain: str
    ) -> list[dict[str, Any]]:
        """Fetch top referral sites from SimilarWeb.

        Args:
            client: httpx async client.
            domain: Domain to query.

        Returns:
            List of dicts with referral site info, or empty list on failure.
        """
        url = f"{SIMILARWEB_BASE}/{domain}/referrals/referrals"
        try:
            resp = await client.get(url, params=_default_params())
            resp.raise_for_status()
            data = resp.json()
            records = data.get("referrals", data.get("records", []))
            logger.info(
                "[TrafficCollector] referrals fetched",
                domain=domain,
                count=len(records) if isinstance(records, list) else 0,
            )
            return records[:10] if isinstance(records, list) else []
        except httpx.TimeoutException:
            logger.error("[TrafficCollector] referrals timeout", domain=domain)
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "[TrafficCollector] referrals HTTP error",
                domain=domain,
                status_code=exc.response.status_code,
            )
            return []
        except Exception:
            logger.exception("[TrafficCollector] referrals unexpected error", domain=domain)
            return []

    async def _fetch_popular_pages(
        self, client: httpx.AsyncClient, domain: str
    ) -> list[dict[str, Any]]:
        """Fetch popular pages from SimilarWeb.

        Args:
            client: httpx async client.
            domain: Domain to query.

        Returns:
            List of dicts with popular page info, or empty list on failure.
        """
        url = f"{SIMILARWEB_BASE}/{domain}/popular-pages"
        try:
            resp = await client.get(url, params=_default_params())
            resp.raise_for_status()
            data = resp.json()
            records = data.get("popular_pages", data.get("pages", []))
            logger.info(
                "[TrafficCollector] popular pages fetched",
                domain=domain,
                count=len(records) if isinstance(records, list) else 0,
            )
            return records[:10] if isinstance(records, list) else []
        except httpx.TimeoutException:
            logger.error("[TrafficCollector] popular pages timeout", domain=domain)
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "[TrafficCollector] popular pages HTTP error",
                domain=domain,
                status_code=exc.response.status_code,
            )
            return []
        except Exception:
            logger.exception("[TrafficCollector] popular pages unexpected error", domain=domain)
            return []
