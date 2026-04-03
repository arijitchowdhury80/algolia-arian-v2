"""Intel Investor collector -- SEC EDGAR + Perplexity data collection.

Collects:
1. Earnings call transcripts via Perplexity (last 4 quarters for prospect)
2. Competitor earnings call content via Perplexity (last 2 quarters each)
3. YouTube / conference appearances via Perplexity
4. Board composition via Perplexity
5. 10-K risk factors via SEC EDGAR + Perplexity

SEC EDGAR uses the free company submissions API (no API key needed).
Perplexity sonar-pro is used for all search/summarization tasks.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from prism_platform.config import settings

logger = structlog.get_logger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar-pro"
PERPLEXITY_TIMEOUT = 60.0
SEC_EDGAR_USER_AGENT = "PRISM Platform research@prism-platform.com"
SEC_EDGAR_TIMEOUT = 30.0


class InvestorCollector:
    """Collects investor intelligence from Perplexity and SEC EDGAR."""

    def __init__(self) -> None:
        self._perplexity_calls = 0

    @property
    def perplexity_calls(self) -> int:
        """Total Perplexity API calls made."""
        return self._perplexity_calls

    # ------------------------------------------------------------------
    # Part 1: Earnings Call Transcripts (Prospect)
    # ------------------------------------------------------------------

    async def collect_earnings_transcripts(
        self,
        company_name: str,
        ticker: str | None,
        executives: list[str] | None = None,
    ) -> list[str]:
        """Collect earnings call transcript content for the last 4 quarters.

        Args:
            company_name: Company name for search queries.
            ticker: Stock ticker for more precise searches.
            executives: List of executive names to focus on (CEO, CFO, CTO).

        Returns:
            List of raw text responses from Perplexity, one per quarter searched.
        """
        logger.info(
            "[InvestorCollector] earnings transcript collection started",
            company_name=company_name,
            ticker=ticker,
        )

        exec_names = ", ".join(executives[:3]) if executives else "CEO and CFO"
        quarters = ["Q4 FY2025", "Q3 FY2025", "Q2 FY2025", "Q1 FY2025"]
        results: list[str] = []

        for quarter in quarters:
            prompt = (
                f"{company_name} earnings call transcript {quarter} full text. "
                f"Include all executive remarks, especially from {exec_names}. "
                f"Focus on: digital transformation, technology investment, customer experience, "
                f"AI, search, e-commerce, platform modernization, revenue growth drivers, "
                f"competitive positioning, and pain points."
            )
            if ticker:
                prompt += f" Ticker: {ticker}."

            try:
                text = await self._call_perplexity(prompt)
                if text:
                    results.append(text)
                    logger.debug(
                        "[InvestorCollector] transcript collected",
                        company_name=company_name,
                        quarter=quarter,
                        length=len(text),
                    )
            except Exception:
                logger.exception(
                    "[InvestorCollector] failed to collect transcript",
                    company_name=company_name,
                    quarter=quarter,
                )

        logger.info(
            "[InvestorCollector] earnings transcript collection complete",
            company_name=company_name,
            transcripts_collected=len(results),
        )
        return results

    # ------------------------------------------------------------------
    # Part 2: Competitor Earnings Transcripts
    # ------------------------------------------------------------------

    async def collect_competitor_transcripts(
        self,
        competitors: list[dict[str, str]],
    ) -> dict[str, list[str]]:
        """Collect earnings call content for top competitors (last 2 quarters each).

        Args:
            competitors: List of dicts with 'company_name', 'ticker', 'domain' keys.

        Returns:
            Dict mapping company_name to list of raw text responses.
        """
        logger.info(
            "[InvestorCollector] competitor transcript collection started",
            count=len(competitors),
        )

        results: dict[str, list[str]] = {}

        for comp in competitors[:3]:
            comp_name = comp.get("company_name", "")
            comp_ticker = comp.get("ticker", "")
            if not comp_name:
                continue

            comp_texts: list[str] = []
            for quarter in ["Q4 FY2025", "Q3 FY2025"]:
                prompt = (
                    f"{comp_name} earnings call transcript {quarter}. "
                    f"CEO and CFO remarks about digital strategy, technology investment, "
                    f"search technology, AI, customer experience, and revenue growth drivers."
                )
                if comp_ticker:
                    prompt += f" Ticker: {comp_ticker}."

                try:
                    text = await self._call_perplexity(prompt)
                    if text:
                        comp_texts.append(text)
                except Exception:
                    logger.exception(
                        "[InvestorCollector] failed to collect competitor transcript",
                        company_name=comp_name,
                        quarter=quarter,
                    )

            if comp_texts:
                results[comp_name] = comp_texts

        logger.info(
            "[InvestorCollector] competitor transcript collection complete",
            competitors_collected=len(results),
        )
        return results

    # ------------------------------------------------------------------
    # Part 3: YouTube / Conference Appearances
    # ------------------------------------------------------------------

    async def collect_youtube_appearances(
        self,
        company_name: str,
        executives: list[str] | None = None,
    ) -> str:
        """Search for executive YouTube and conference appearances.

        Args:
            company_name: Company name for search queries.
            executives: List of executive names to search for.

        Returns:
            Raw text response from Perplexity about appearances.
        """
        logger.info(
            "[InvestorCollector] YouTube appearance search started",
            company_name=company_name,
        )

        try:
            prompt = (
                f"{company_name} YouTube keynote OR presentation OR product launch 2025 2026. "
                f"CEO or CTO speaking at conferences, investor days, product events."
            )

            text = await self._call_perplexity(prompt)

            if executives:
                for exec_name in executives[:2]:
                    exec_prompt = f"{exec_name} keynote OR presentation 2025 2026 YouTube video"
                    try:
                        exec_text = await self._call_perplexity(exec_prompt)
                        if exec_text:
                            text = f"{text}\n\n---\n\n{exec_text}" if text else exec_text
                    except Exception:
                        logger.exception(
                            "[InvestorCollector] failed exec YouTube search",
                            executive=exec_name,
                        )

            logger.info(
                "[InvestorCollector] YouTube appearance search complete",
                company_name=company_name,
                has_results=bool(text),
            )
            return text or ""

        except Exception:
            logger.exception(
                "[InvestorCollector] YouTube appearance search failed",
                company_name=company_name,
            )
            return ""

    # ------------------------------------------------------------------
    # Part 4: Board Composition
    # ------------------------------------------------------------------

    async def collect_board_composition(self, company_name: str) -> str:
        """Search for board of directors composition.

        Args:
            company_name: Company name for search queries.

        Returns:
            Raw text response from Perplexity about board members.
        """
        logger.info(
            "[InvestorCollector] board composition search started",
            company_name=company_name,
        )

        try:
            prompt = (
                f"{company_name} board of directors 2025 2026 members backgrounds. "
                f"List each board member with their title, professional background, "
                f"and any technology or digital experience."
            )
            text = await self._call_perplexity(prompt)

            logger.info(
                "[InvestorCollector] board composition search complete",
                company_name=company_name,
                has_results=bool(text),
            )
            return text or ""

        except Exception:
            logger.exception(
                "[InvestorCollector] board composition search failed",
                company_name=company_name,
            )
            return ""

    # ------------------------------------------------------------------
    # Part 5: 10-K Risk Factors (SEC EDGAR + Perplexity)
    # ------------------------------------------------------------------

    async def collect_risk_factors(
        self,
        company_name: str,
        ticker: str,
    ) -> str:
        """Collect 10-K risk factors via SEC EDGAR CIK lookup + Perplexity analysis.

        Args:
            company_name: Company name for search context.
            ticker: Stock ticker for SEC EDGAR CIK lookup.

        Returns:
            Raw text response from Perplexity about risk factors.
        """
        logger.info(
            "[InvestorCollector] risk factor collection started",
            company_name=company_name,
            ticker=ticker,
        )

        # Step 1: Look up CIK from ticker via SEC EDGAR
        cik_str = await self._lookup_cik(ticker)
        if cik_str:
            logger.debug(
                "[InvestorCollector] CIK found",
                ticker=ticker,
                cik=cik_str,
            )

        # Step 2: Use Perplexity to analyze risk factors
        try:
            prompt = (
                f"{company_name} 10-K annual report risk factors related to technology, "
                f"cybersecurity, digital disruption, legacy systems, or competitive threats. "
                f"What specific risks does {company_name} mention about their technology "
                f"infrastructure, search capabilities, customer experience technology, "
                f"or digital transformation challenges?"
            )
            if ticker:
                prompt += f" Ticker: {ticker}."
            if cik_str:
                prompt += f" SEC EDGAR CIK: {cik_str}."

            text = await self._call_perplexity(prompt)

            logger.info(
                "[InvestorCollector] risk factor collection complete",
                company_name=company_name,
                has_results=bool(text),
            )
            return text or ""

        except Exception:
            logger.exception(
                "[InvestorCollector] risk factor collection failed",
                company_name=company_name,
            )
            return ""

    # ------------------------------------------------------------------
    # Private Company Fallback
    # ------------------------------------------------------------------

    async def collect_private_company_intel(
        self,
        company_name: str,
        domain: str,
    ) -> dict[str, str]:
        """Collect investor-like intelligence for private companies.

        Uses Perplexity to search for conference presentations, annual reports,
        CEO/CTO interviews, and strategic communications.

        Args:
            company_name: Company name for search queries.
            domain: Company domain for context.

        Returns:
            Dict with keys 'presentations', 'interviews', 'strategy' mapping to raw text.
        """
        logger.info(
            "[InvestorCollector] private company intel collection started",
            company_name=company_name,
            domain=domain,
        )

        results: dict[str, str] = {}

        queries = {
            "presentations": (
                f"{company_name} conference presentation OR keynote OR annual report "
                f"2025 2026. CEO or CTO speaking about strategy, technology investment, "
                f"product roadmap."
            ),
            "interviews": (
                f"{company_name} CEO OR CTO interview 2025 2026 about strategy, "
                f"technology, AI, digital transformation, customer experience."
            ),
            "strategy": (
                f"{company_name} ({domain}) strategic priorities technology investment "
                f"digital transformation 2025 2026. What has the leadership said about "
                f"their technology direction?"
            ),
        }

        for key, prompt in queries.items():
            try:
                text = await self._call_perplexity(prompt)
                if text:
                    results[key] = text
            except Exception:
                logger.exception(
                    "[InvestorCollector] private company query failed",
                    company_name=company_name,
                    query_key=key,
                )

        logger.info(
            "[InvestorCollector] private company intel collection complete",
            company_name=company_name,
            sections_collected=len(results),
        )
        return results

    # ------------------------------------------------------------------
    # SEC EDGAR helpers
    # ------------------------------------------------------------------

    async def _lookup_cik(self, ticker: str) -> str:
        """Look up SEC EDGAR CIK number from ticker symbol.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            CIK string zero-padded to 10 digits, or empty string on failure.
        """
        try:
            async with httpx.AsyncClient(timeout=SEC_EDGAR_TIMEOUT) as client:
                resp = await client.get(
                    "https://www.sec.gov/files/company_tickers.json",
                    headers={"User-Agent": SEC_EDGAR_USER_AGENT},
                )
                resp.raise_for_status()
                tickers_data: dict[str, Any] = resp.json()

                for entry_val in tickers_data.values():
                    if str(entry_val.get("ticker", "")).upper() == ticker.upper():
                        return str(entry_val["cik_str"]).zfill(10)

            logger.warning(
                "[InvestorCollector] CIK not found for ticker",
                ticker=ticker,
            )
            return ""

        except httpx.TimeoutException as exc:
            logger.error(
                "[InvestorCollector] SEC EDGAR CIK lookup timeout",
                ticker=ticker,
                error=str(exc),
            )
            return ""
        except httpx.HTTPStatusError as exc:
            logger.error(
                "[InvestorCollector] SEC EDGAR CIK lookup HTTP error",
                ticker=ticker,
                status_code=exc.response.status_code,
                error=str(exc),
            )
            return ""
        except Exception:
            logger.exception(
                "[InvestorCollector] SEC EDGAR CIK lookup failed",
                ticker=ticker,
            )
            return ""

    # ------------------------------------------------------------------
    # Perplexity API helper
    # ------------------------------------------------------------------

    async def _call_perplexity(self, prompt: str) -> str:
        """Call the Perplexity chat completions API.

        Args:
            prompt: The user message to send.

        Returns:
            The assistant's response text, or empty string on failure.
        """
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
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are an equity research analyst specializing in "
                                    "technology companies and digital transformation. "
                                    "Return factual, well-sourced information with verbatim "
                                    "executive quotes when available. Cite sources inline."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 4096,
                        "return_citations": True,
                    },
                )
                resp.raise_for_status()

            data: dict[str, Any] = resp.json()
            choices = data.get("choices", [])
            if not choices:
                logger.warning("[InvestorCollector] Perplexity returned no choices")
                return ""

            self._perplexity_calls += 1
            content: str = choices[0].get("message", {}).get("content", "")
            return content

        except httpx.TimeoutException as exc:
            logger.error(
                "[InvestorCollector] Perplexity timeout",
                error=str(exc),
            )
            return ""
        except httpx.HTTPStatusError as exc:
            logger.error(
                "[InvestorCollector] Perplexity HTTP error",
                status_code=exc.response.status_code,
                error=str(exc),
            )
            return ""
        except Exception:
            logger.exception("[InvestorCollector] Perplexity call failed")
            return ""
