"""Intel Financial Public collector -- Yahoo Finance + SEC EDGAR data collection.

Collects:
1. Yahoo Finance: market data, income statement (3 years), analyst recommendations
2. SEC EDGAR: recent 10-K and 10-Q filings metadata
3. Competitor financials: basic Yahoo Finance data for competitor tickers

Yahoo Finance uses the yfinance library (free, no API key needed).
SEC EDGAR uses the free EFTS search API (no API key needed).
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
import yfinance as yf

from prism_platform.modules.intel_financial_public.schemas import (
    AnalystData,
    AnnualFinancials,
    CompetitorFinancials,
    MarketData,
    SECInsight,
)

logger = structlog.get_logger(__name__)

SEC_EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
SEC_EDGAR_USER_AGENT = "PRISM Platform research@prism-platform.com"
SEC_EDGAR_TIMEOUT = 30.0


class FinancialCollector:
    """Collects financial data from Yahoo Finance and SEC EDGAR."""

    async def collect_yahoo_finance(
        self, ticker: str
    ) -> tuple[list[AnnualFinancials], MarketData | None, AnalystData | None]:
        """Collect structured financial data from Yahoo Finance.

        Args:
            ticker: Stock ticker symbol, e.g. 'DELL'.

        Returns:
            Tuple of (annual_financials, market_data, analyst_data).
        """
        logger.info("[FinancialCollector] Yahoo Finance collection started", ticker=ticker)

        annual_financials: list[AnnualFinancials] = []
        market_data: MarketData | None = None
        analyst_data: AnalystData | None = None

        try:
            ticker_obj = yf.Ticker(ticker)
            info = self._get_ticker_info(ticker_obj, ticker)
            annual_financials = self._extract_annual_financials(ticker_obj, ticker)
            market_data = self._extract_market_data(info, ticker)
            analyst_data = self._extract_analyst_data(info, ticker)

            logger.info(
                "[FinancialCollector] Yahoo Finance collection complete",
                ticker=ticker,
                annual_years=len(annual_financials),
                has_market_data=market_data is not None,
                has_analyst_data=analyst_data is not None,
            )
        except Exception:
            logger.exception(
                "[FinancialCollector] Yahoo Finance collection failed",
                ticker=ticker,
            )

        return annual_financials, market_data, analyst_data

    async def collect_sec_filings(self, company_name: str, ticker: str) -> list[SECInsight]:
        """Collect SEC filing metadata from EDGAR full-text search.

        Args:
            company_name: Company name for search query.
            ticker: Stock ticker for fallback search.

        Returns:
            List of SECInsight with filing metadata (no content analysis yet).
        """
        logger.info(
            "[FinancialCollector] SEC EDGAR collection started",
            company_name=company_name,
            ticker=ticker,
        )

        insights: list[SECInsight] = []

        try:
            filings = await self._search_sec_edgar(company_name, ticker)
            for filing in filings:
                try:
                    insight = SECInsight(
                        filing_type=filing["form_type"],
                        filing_date=filing["filed_date"],
                        filing_url=filing.get("url"),
                        technology_mentions=[],
                        key_excerpts=[],
                        management_discussion_summary="",
                    )
                    insights.append(insight)
                except Exception as exc:
                    logger.warning(
                        "[FinancialCollector] Failed to parse SEC filing",
                        filing=filing,
                        error=str(exc),
                    )

            logger.info(
                "[FinancialCollector] SEC EDGAR collection complete",
                ticker=ticker,
                filings_found=len(insights),
            )
        except httpx.TimeoutException as exc:
            logger.error(
                "[FinancialCollector] SEC EDGAR timeout",
                ticker=ticker,
                error=str(exc),
            )
        except httpx.HTTPStatusError as exc:
            logger.error(
                "[FinancialCollector] SEC EDGAR HTTP error",
                ticker=ticker,
                status_code=exc.response.status_code,
                error=str(exc),
            )
        except Exception:
            logger.exception(
                "[FinancialCollector] SEC EDGAR collection failed",
                ticker=ticker,
            )

        return insights

    async def collect_competitor_financials(
        self, competitor_tickers: list[dict[str, str]]
    ) -> list[CompetitorFinancials]:
        """Collect basic financial data for competitor companies.

        Args:
            competitor_tickers: List of dicts with 'company_name' and 'ticker' keys.

        Returns:
            List of CompetitorFinancials with basic Yahoo Finance data.
        """
        logger.info(
            "[FinancialCollector] competitor collection started",
            count=len(competitor_tickers),
        )

        results: list[CompetitorFinancials] = []
        for comp in competitor_tickers:
            comp_ticker = comp.get("ticker", "")
            comp_name = comp.get("company_name", "")
            if not comp_ticker:
                continue

            try:
                ticker_obj = yf.Ticker(comp_ticker)
                info = self._get_ticker_info(ticker_obj, comp_ticker)

                revenue = self._safe_float(info.get("totalRevenue"))
                prev_revenue = self._safe_float(info.get("revenueGrowth"))
                market_cap = self._safe_float(info.get("marketCap"))
                gross_margins = self._safe_float(info.get("grossMargins"))

                # revenueGrowth from yfinance is already a decimal (e.g., 0.08 for 8%)
                revenue_growth_pct: float | None = None
                if prev_revenue is not None:
                    revenue_growth_pct = round(prev_revenue * 100, 2)

                gross_margin_pct: float | None = None
                if gross_margins is not None:
                    gross_margin_pct = round(gross_margins * 100, 2)

                results.append(
                    CompetitorFinancials(
                        company_name=comp_name or comp_ticker,
                        ticker=comp_ticker,
                        revenue=revenue,
                        revenue_growth_pct=revenue_growth_pct,
                        market_cap=market_cap,
                        gross_margin_pct=gross_margin_pct,
                    )
                )

                logger.debug(
                    "[FinancialCollector] competitor data collected",
                    ticker=comp_ticker,
                    revenue=revenue,
                    market_cap=market_cap,
                )
            except Exception:
                logger.exception(
                    "[FinancialCollector] failed to collect competitor data",
                    ticker=comp_ticker,
                )

        logger.info(
            "[FinancialCollector] competitor collection complete",
            collected=len(results),
            attempted=len(competitor_tickers),
        )
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_ticker_info(ticker_obj: yf.Ticker, ticker: str) -> dict[str, Any]:
        """Safely retrieve ticker info dict from yfinance.

        Args:
            ticker_obj: yfinance Ticker instance.
            ticker: Ticker symbol for logging.

        Returns:
            Info dict, or empty dict on failure.
        """
        try:
            info: dict[str, Any] = ticker_obj.info  # type: ignore[assignment]
            if not info:
                logger.warning("[FinancialCollector] empty info for ticker", ticker=ticker)
                return {}
            return info
        except Exception as exc:
            logger.error(
                "[FinancialCollector] failed to get ticker info",
                ticker=ticker,
                error=str(exc),
            )
            return {}

    @staticmethod
    def _extract_annual_financials(ticker_obj: yf.Ticker, ticker: str) -> list[AnnualFinancials]:
        """Extract up to 3 years of annual financials from yfinance income statement.

        Args:
            ticker_obj: yfinance Ticker instance.
            ticker: Ticker symbol for logging.

        Returns:
            List of AnnualFinancials, most recent first.
        """
        results: list[AnnualFinancials] = []

        try:
            financials = ticker_obj.financials
            if financials is None or financials.empty:
                logger.warning(
                    "[FinancialCollector] no financials data available",
                    ticker=ticker,
                )
                return results

            # financials columns are dates, rows are line items
            columns = list(financials.columns)[:3]  # Up to 3 most recent years

            prev_revenue: float | None = None
            for col in reversed(columns):
                year_label = f"FY{col.year}" if hasattr(col, "year") else str(col)

                revenue = FinancialCollector._safe_float(
                    financials.at["Total Revenue", col]
                    if "Total Revenue" in financials.index
                    else None
                )
                net_income = FinancialCollector._safe_float(
                    financials.at["Net Income", col] if "Net Income" in financials.index else None
                )
                gross_profit = FinancialCollector._safe_float(
                    financials.at["Gross Profit", col]
                    if "Gross Profit" in financials.index
                    else None
                )
                operating_income = FinancialCollector._safe_float(
                    financials.at["Operating Income", col]
                    if "Operating Income" in financials.index
                    else None
                )

                gross_margin_pct: float | None = None
                if gross_profit is not None and revenue is not None and revenue > 0:
                    gross_margin_pct = round((gross_profit / revenue) * 100, 2)

                operating_margin_pct: float | None = None
                if operating_income is not None and revenue is not None and revenue > 0:
                    operating_margin_pct = round((operating_income / revenue) * 100, 2)

                revenue_growth_pct: float | None = None
                if revenue is not None and prev_revenue is not None and prev_revenue > 0:
                    revenue_growth_pct = round(((revenue - prev_revenue) / prev_revenue) * 100, 2)

                prev_revenue = revenue

                results.append(
                    AnnualFinancials(
                        fiscal_year=year_label,
                        revenue=revenue,
                        net_income=net_income,
                        gross_margin_pct=gross_margin_pct,
                        operating_margin_pct=operating_margin_pct,
                        revenue_growth_pct=revenue_growth_pct,
                    )
                )

            logger.info(
                "[FinancialCollector] annual financials extracted",
                ticker=ticker,
                years=len(results),
            )
        except Exception:
            logger.exception(
                "[FinancialCollector] failed to extract annual financials",
                ticker=ticker,
            )

        return results

    @staticmethod
    def _extract_market_data(info: dict[str, Any], ticker: str) -> MarketData | None:
        """Extract current market data from yfinance info dict.

        Args:
            info: yfinance info dict.
            ticker: Ticker symbol for logging.

        Returns:
            MarketData or None if no data available.
        """
        try:
            market_cap = FinancialCollector._safe_float(info.get("marketCap"))
            stock_price = FinancialCollector._safe_float(
                info.get("currentPrice") or info.get("regularMarketPrice")
            )
            high_52 = FinancialCollector._safe_float(info.get("fiftyTwoWeekHigh"))
            low_52 = FinancialCollector._safe_float(info.get("fiftyTwoWeekLow"))
            pe = FinancialCollector._safe_float(info.get("trailingPE"))
            fwd_pe = FinancialCollector._safe_float(info.get("forwardPE"))

            if market_cap is None and stock_price is None:
                logger.warning(
                    "[FinancialCollector] no market data available",
                    ticker=ticker,
                )
                return None

            data = MarketData(
                market_cap=market_cap,
                stock_price=stock_price,
                fifty_two_week_high=high_52,
                fifty_two_week_low=low_52,
                pe_ratio=pe,
                forward_pe=fwd_pe,
            )

            logger.debug(
                "[FinancialCollector] market data extracted",
                ticker=ticker,
                market_cap=market_cap,
                stock_price=stock_price,
            )
            return data
        except Exception:
            logger.exception(
                "[FinancialCollector] failed to extract market data",
                ticker=ticker,
            )
            return None

    @staticmethod
    def _extract_analyst_data(info: dict[str, Any], ticker: str) -> AnalystData | None:
        """Extract analyst consensus data from yfinance info dict.

        Args:
            info: yfinance info dict.
            ticker: Ticker symbol for logging.

        Returns:
            AnalystData or None if no data available.
        """
        try:
            rec = info.get("recommendationKey")
            target = FinancialCollector._safe_float(info.get("targetMeanPrice"))
            num_analysts = info.get("numberOfAnalystOpinions")

            if rec is None and target is None:
                logger.debug(
                    "[FinancialCollector] no analyst data available",
                    ticker=ticker,
                )
                return None

            # Map yfinance recommendation keys to readable labels
            rec_map: dict[str, str] = {
                "strong_buy": "Strong Buy",
                "buy": "Buy",
                "hold": "Hold",
                "sell": "Sell",
                "strong_sell": "Strong Sell",
            }
            recommendation = (
                rec_map.get(str(rec), str(rec).replace("_", " ").title()) if rec else None
            )

            data = AnalystData(
                recommendation=recommendation,
                target_price=target,
                number_of_analysts=int(num_analysts) if num_analysts is not None else None,
            )

            logger.debug(
                "[FinancialCollector] analyst data extracted",
                ticker=ticker,
                recommendation=recommendation,
                target_price=target,
            )
            return data
        except Exception:
            logger.exception(
                "[FinancialCollector] failed to extract analyst data",
                ticker=ticker,
            )
            return None

    async def _search_sec_edgar(self, company_name: str, ticker: str) -> list[dict[str, str]]:
        """Search SEC EDGAR for recent 10-K and 10-Q filings.

        Uses the EDGAR full-text search API (efts.sec.gov/LATEST/search-index)
        and falls back to the company submissions API if no results.

        Args:
            company_name: Company name for the search query.
            ticker: Ticker symbol for CIK lookup fallback.

        Returns:
            List of dicts with keys: form_type, filed_date, url.

        Raises:
            httpx.TimeoutException: If the API call times out.
            httpx.HTTPStatusError: If the API returns a non-2xx status.
        """
        filings: list[dict[str, str]] = []

        async with httpx.AsyncClient(timeout=SEC_EDGAR_TIMEOUT) as client:
            # Strategy 1: EDGAR full-text search API
            for query in [f'"{company_name}"', ticker]:
                try:
                    resp = await client.get(
                        "https://efts.sec.gov/LATEST/search-index",
                        params={
                            "q": query,
                            "dateRange": "custom",
                            "startdt": "2024-01-01",
                            "enddt": "2026-04-01",
                            "forms": "10-K,10-Q",
                        },
                        headers={
                            "User-Agent": SEC_EDGAR_USER_AGENT,
                            "Accept": "application/json",
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    hits = data.get("hits", {}).get("hits", [])

                    for hit in hits[:5]:
                        source = hit.get("_source", {})
                        form_type = source.get("form_type", "")
                        if form_type not in ("10-K", "10-Q"):
                            continue
                        filed_date = source.get("file_date", "")
                        accession = source.get("accession_no", "").replace("-", "")
                        cik = source.get("entity_id", "")
                        url = (
                            f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/"
                            if accession and cik
                            else ""
                        )
                        filings.append(
                            {
                                "form_type": form_type,
                                "filed_date": filed_date,
                                "url": url,
                            }
                        )

                    if filings:
                        break
                except httpx.HTTPStatusError:
                    logger.warning(
                        "[FinancialCollector] EFTS search failed",
                        query=query,
                    )
                    continue

            # Strategy 2: CIK lookup + company submissions API
            if not filings:
                try:
                    cik_resp = await client.get(
                        f"https://www.sec.gov/cgi-bin/browse-edgar"
                        f"?company={ticker}&CIK=&type=10-K&dateb=&owner=include"
                        f"&count=5&search_text=&action=getcompany&output=atom",
                        headers={"User-Agent": SEC_EDGAR_USER_AGENT},
                    )
                    cik_resp.raise_for_status()

                    # Parse ATOM XML for filing entries
                    import re

                    entries = re.findall(r"<entry>(.*?)</entry>", cik_resp.text, re.DOTALL)
                    for entry in entries[:5]:
                        form_match = re.search(r"<category[^>]*term=\"(10-[KQ])", entry)
                        date_match = re.search(r"<updated>(\d{4}-\d{2}-\d{2})", entry)
                        link_match = re.search(r'<link[^>]*href="([^"]+)"', entry)
                        if form_match and date_match:
                            filings.append(
                                {
                                    "form_type": form_match.group(1),
                                    "filed_date": date_match.group(1),
                                    "url": link_match.group(1) if link_match else "",
                                }
                            )
                except Exception:
                    logger.warning(
                        "[FinancialCollector] CIK lookup fallback failed",
                        ticker=ticker,
                    )

            # Strategy 3: Company submissions JSON API
            if not filings:
                try:
                    # Look up CIK from ticker
                    tickers_resp = await client.get(
                        "https://www.sec.gov/files/company_tickers.json",
                        headers={"User-Agent": SEC_EDGAR_USER_AGENT},
                    )
                    tickers_resp.raise_for_status()
                    tickers_data = tickers_resp.json()

                    cik_str = ""
                    for entry_val in tickers_data.values():
                        if str(entry_val.get("ticker", "")).upper() == ticker.upper():
                            cik_str = str(entry_val["cik_str"]).zfill(10)
                            break

                    if cik_str:
                        sub_resp = await client.get(
                            f"https://data.sec.gov/submissions/CIK{cik_str}.json",
                            headers={"User-Agent": SEC_EDGAR_USER_AGENT},
                        )
                        sub_resp.raise_for_status()
                        sub_data = sub_resp.json()

                        recent = sub_data.get("filings", {}).get("recent", {})
                        forms = recent.get("form", [])
                        dates = recent.get("filingDate", [])
                        accessions = recent.get("accessionNumber", [])
                        primary_docs = recent.get("primaryDocument", [])

                        for i, form in enumerate(forms):
                            if form in ("10-K", "10-Q") and len(filings) < 5:
                                acc_no = (
                                    accessions[i].replace("-", "") if i < len(accessions) else ""
                                )
                                doc = primary_docs[i] if i < len(primary_docs) else ""
                                url = (
                                    f"https://www.sec.gov/Archives/edgar/data/"
                                    f"{cik_str.lstrip('0')}/{acc_no}/{doc}"
                                    if acc_no and doc
                                    else ""
                                )
                                filings.append(
                                    {
                                        "form_type": form,
                                        "filed_date": dates[i] if i < len(dates) else "",
                                        "url": url,
                                    }
                                )
                except Exception:
                    logger.warning(
                        "[FinancialCollector] submissions API fallback failed",
                        ticker=ticker,
                    )

        # Deduplicate by filing_date + form_type
        seen: set[str] = set()
        unique_filings: list[dict[str, str]] = []
        for f in filings:
            key = f"{f['form_type']}_{f['filed_date']}"
            if key not in seen:
                seen.add(key)
                unique_filings.append(f)

        logger.info(
            "[FinancialCollector] SEC EDGAR search complete",
            company_name=company_name,
            filings_found=len(unique_filings),
        )
        return unique_filings

    @staticmethod
    def _safe_float(value: object) -> float | None:
        """Safely convert a value to float, returning None on failure.

        Args:
            value: Any value that might be numeric.

        Returns:
            Float value or None.
        """
        if value is None:
            return None
        try:
            result = float(value)  # type: ignore[arg-type]
            # yfinance sometimes returns NaN or Inf
            import math

            if math.isnan(result) or math.isinf(result):
                return None
            return result
        except (ValueError, TypeError):
            return None
