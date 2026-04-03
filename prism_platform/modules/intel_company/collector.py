"""Intel Company collector — ONE Perplexity call returning JSON + homepage fetch.

Data flow:
    1. Single Perplexity sonar call with composite prompt → JSON response with citations
    2. HTTP GET homepage → search bar regex detection
"""

from __future__ import annotations

import re
from typing import Any

import httpx
import structlog

from prism_platform.config import settings

logger = structlog.get_logger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
HOMEPAGE_TIMEOUT = 15.0
PERPLEXITY_TIMEOUT = 90.0

# Common search input patterns for homepage detection
SEARCH_BAR_PATTERNS = [
    re.compile(r'<input[^>]*type=["\']search["\']', re.IGNORECASE),
    re.compile(r'<input[^>]*name=["\'](?:q|query|search|s)["\']', re.IGNORECASE),
    re.compile(r'<input[^>]*placeholder=["\'][^"\']*search[^"\']*["\']', re.IGNORECASE),
    re.compile(r'role=["\']search["\']', re.IGNORECASE),
    re.compile(r'aria-label=["\'][^"\']*search[^"\']*["\']', re.IGNORECASE),
]


class CompanyCollector:
    """Collects company intelligence via ONE Perplexity call + homepage fetch."""

    async def collect(self, domain: str) -> dict[str, Any]:
        """Run single Perplexity call + homepage fetch.

        Args:
            domain: Website domain to research (e.g. 'jewson.co.uk').

        Returns:
            Dict with keys:
                perplexity_raw: raw text response from Perplexity (JSON with citations)
                has_search_bar: bool | None from homepage regex
                homepage_fetched: whether homepage fetch succeeded
        """
        logger.info("[CompanyCollector] collect started", domain=domain)

        result: dict[str, Any] = {
            "perplexity_raw": "",
            "has_search_bar": None,
            "homepage_fetched": False,
        }

        # Step 1: Single Perplexity call with retry
        prompt = self._build_prompt(domain)
        max_retries = 3
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                result["perplexity_raw"] = await self._call_perplexity(prompt)
                logger.info(
                    "[CompanyCollector] Perplexity call completed",
                    domain=domain,
                    attempt=attempt,
                    response_length=len(result["perplexity_raw"]),
                )
                break
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    "[CompanyCollector] Perplexity timeout, retrying",
                    domain=domain,
                    attempt=attempt,
                    max_retries=max_retries,
                )
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code == 429:
                    logger.warning(
                        "[CompanyCollector] Perplexity rate limited, retrying",
                        domain=domain,
                        attempt=attempt,
                        status_code=exc.response.status_code,
                    )
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(
                        "[CompanyCollector] Perplexity HTTP error",
                        domain=domain,
                        status_code=exc.response.status_code,
                    )
                    raise
            except (httpx.ConnectError, httpx.ReadError) as exc:
                last_error = exc
                logger.warning(
                    "[CompanyCollector] Perplexity connection error, retrying",
                    domain=domain,
                    attempt=attempt,
                    error=str(exc),
                )
                import asyncio
                await asyncio.sleep(2 ** attempt)
            except Exception:
                logger.exception("[CompanyCollector] Perplexity unexpected error", domain=domain)
                raise
        else:
            logger.error(
                "[CompanyCollector] Perplexity failed after all retries",
                domain=domain,
                max_retries=max_retries,
            )
            if last_error:
                raise last_error

        # Step 2: Homepage fetch for search bar detection
        try:
            html = await self._fetch_homepage(domain)
            result["has_search_bar"] = self._detect_search_bar(html)
            result["homepage_fetched"] = True
        except Exception as exc:
            logger.warning(
                "[CompanyCollector] homepage fetch failed", domain=domain, error=str(exc)
            )

        logger.info(
            "[CompanyCollector] collect completed",
            domain=domain,
            has_perplexity=bool(result["perplexity_raw"]),
            has_search_bar=result["has_search_bar"],
        )
        return result

    async def _call_perplexity(self, prompt: str) -> str:
        """Call Perplexity chat completions API.

        Args:
            prompt: The user message to send.

        Returns:
            The assistant's response text.
        """
        model = settings.perplexity_model
        logger.info("[CompanyCollector] calling Perplexity", model=model)

        async with httpx.AsyncClient(timeout=PERPLEXITY_TIMEOUT) as client:
            resp = await client.post(
                PERPLEXITY_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.perplexity_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a thorough business intelligence researcher. "
                                "Return valid JSON matching the requested schema. "
                                "Be comprehensive — include ALL executives you can find (minimum 5), "
                                "ALL competitors (minimum 5), and ALL recent news. "
                                "Cite every fact with [label](url) inline after the value."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 8192,
                    "return_citations": True,
                },
            )
            resp.raise_for_status()

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            logger.warning("[CompanyCollector] Perplexity returned no choices")
            return ""

        content = choices[0].get("message", {}).get("content", "")

        # Strip markdown code fences if Perplexity wraps JSON in ```json ... ```
        if content.strip().startswith("```"):
            lines = content.strip().split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            content = "\n".join(lines)

        return content

    async def _fetch_homepage(self, domain: str) -> str:
        """Fetch homepage HTML for search bar detection.

        Args:
            domain: Website domain.

        Returns:
            First 50KB of HTML.
        """
        url = f"https://{domain}"
        logger.info("[CompanyCollector] fetching homepage", url=url)
        async with httpx.AsyncClient(
            timeout=HOMEPAGE_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Prism Intelligence Bot)"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        html = resp.text[:50_000]
        logger.info("[CompanyCollector] homepage fetched", domain=domain, html_length=len(html))
        return html

    @staticmethod
    def _detect_search_bar(html: str) -> bool | None:
        """Detect search bar from homepage HTML using regex patterns.

        Args:
            html: Raw HTML content.

        Returns:
            True if search bar found, False if not, None if html is empty.
        """
        if not html:
            return None
        return any(p.search(html) for p in SEARCH_BAR_PATTERNS)

    @staticmethod
    def _build_prompt(domain: str) -> str:
        """Build composite Perplexity prompt requesting JSON output.

        Args:
            domain: Website domain to research.

        Returns:
            Complete prompt string.
        """
        return f"""Research the company that owns the website {domain}.

I need comprehensive company intelligence. Please be THOROUGH on these sections:

EXECUTIVES: Find 8-12 named executives. Search LinkedIn profiles, the company website "About Us" or "Leadership" page, Companies House director filings, and press releases. Include the CEO, CFO, CTO, CMO, and any VP/Director/Head of Engineering, Product, E-commerce, Digital, Search, or Data. If the company is a subsidiary, include BOTH subsidiary leaders AND parent company executives who oversee it. This section is critical — do not return fewer than 5 people.

COMPETITORS: Find 5-7 direct competitors that sell similar products/services to similar customers in the same market.

RECENT ACTIVITY: Find news articles from the last 90 days and blog posts from the company's own website.

Return your response as a single valid JSON object (no markdown, no commentary before or after the JSON):

{{
  "legal_name": "Official registered company name",
  "common_name": "Name used in press/marketing",
  "domain": "{domain}",
  "headquarters": "City, Region, Country",
  "year_founded": 1836,
  "employee_count": 6000,
  "employee_count_source": "Source (e.g. LinkedIn, Companies House)",
  "business_model": "3+ sentences: what the company does, how it makes money, who its customers are",
  "motto": "Company tagline or null",
  "industry": "Primary industry classification",
  "sub_vertical": "More specific sub-vertical",
  "is_public": false,
  "ticker": "Stock ticker or null",
  "parent_company": "Parent company or null",
  "revenue_estimate": 1600000000.0,
  "revenue_source": "Source and fiscal year",
  "product_categories": ["Category 1", "Category 2", "Category 3"],
  "executives": [
    {{"full_name": "Jane Doe", "title": "CEO", "linkedin_url": "https://www.linkedin.com/in/janedoe", "tenure_description": "Since 2021", "previous_company": "Acme Corp", "previous_role": "COO"}},
    {{"full_name": "John Smith", "title": "CFO", "linkedin_url": null, "tenure_description": "Since 2023", "previous_company": null, "previous_role": null}},
    {{"full_name": "...", "title": "...", "linkedin_url": "...", "tenure_description": "...", "previous_company": "...", "previous_role": "..."}}
  ],
  "competitors": [
    {{"company_name": "Rival Corp", "domain": "rival.com", "why_competitor": "Sells same products to same customers"}},
    {{"company_name": "...", "domain": "...", "why_competitor": "..."}}
  ],
  "recent_news": [
    {{"headline": "Article title", "source": "Publication", "date": "2026-03-15", "url": "https://...", "category": "leadership_change"}}
  ],
  "recent_blog_posts": [
    {{"title": "Post title", "date": "2026-03-15", "url": "https://...", "summary": "One sentence"}}
  ]
}}

Revenue must be a raw number in USD. Dates in YYYY-MM-DD. Only real LinkedIn URLs — do not fabricate. Executives MUST have 5+ entries. Competitors MUST have 5+ entries."""
