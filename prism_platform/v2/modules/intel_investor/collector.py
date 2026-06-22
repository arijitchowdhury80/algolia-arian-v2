"""Intel Investor Track-1 collector — deterministic Yahoo Finance signals.

For public companies, fetches:
  - Current stock price
  - 3 years of annual revenue
  - Analyst recommendation consensus
  - 5 recent news headlines

For private companies (or when the ticker is unavailable), returns an empty
dict immediately — non-fatal. Track 2 (Perplexity) handles the residual.

The result is merged into context.upstream_results under ``investor_yahoo``
so the playbook can reference it as ``{upstream_investor_yahoo}``.
"""

from __future__ import annotations

import datetime
from typing import Any

import structlog

try:
    import yfinance as yf
except ImportError:  # yfinance may not be installed in lightweight envs
    yf = None  # type: ignore[assignment]

from prism_platform.v2.types import ExecutionContextV2

logger = structlog.get_logger(__name__)

# Maximum number of revenue years to collect.
_MAX_REVENUE_YEARS = 3
# Maximum number of news headlines to collect.
_MAX_NEWS = 5


def _resolve_public_status(context: ExecutionContextV2) -> tuple[bool, str | None]:
    """Determine whether the company is public and what its ticker is.

    Reads from context fields first (set by F1 composes hydration from
    intel-company), then falls back to context.upstream_results.

    Returns:
        (is_public, ticker) — both may be falsy for private companies.
    """
    is_public: bool = context.is_public
    ticker: str | None = context.ticker

    # Also check upstream intel-company output if the context fields are empty.
    # F1 hydration may have placed the full intel-company JSON here.
    if not ticker:
        company_data: dict[str, Any] = context.upstream_results.get("intel-company", {})
        if isinstance(company_data, dict):
            ticker = company_data.get("ticker") or ticker
            if not is_public:
                is_public = bool(company_data.get("is_public", False))

    return is_public, ticker


def _fetch_yahoo_data(ticker: str) -> dict[str, Any]:
    """Fetch structured signals from Yahoo Finance via yfinance.

    Returns a dict with keys: stock_price, revenue_3yr, analyst_consensus,
    recent_news, sources.

    Never raises — all exceptions are caught and logged.
    """
    if yf is None:
        raise ImportError("yfinance is not installed")

    stock = yf.Ticker(ticker)

    result: dict[str, Any] = {
        "stock_price": None,
        "revenue_3yr": [],
        "analyst_consensus": None,
        "recent_news": [],
        "sources": [],
    }

    # ── Stock price ────────────────────────────────────────────────────────────
    try:
        info = stock.info or {}
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if price is not None:
            result["stock_price"] = float(price)
            result["sources"].append(
                f"https://finance.yahoo.com/quote/{ticker}"
            )
    except Exception as exc:
        logger.warning("[intel-investor] stock price fetch failed", ticker=ticker, error=str(exc))

    # ── Revenue (3 years, annual income statement) ─────────────────────────────
    try:
        income = stock.income_stmt  # DataFrame, columns are fiscal period dates
        if income is not None and not income.empty:
            revenue_row = None
            for label in ("Total Revenue", "Revenue"):
                if label in income.index:
                    revenue_row = income.loc[label]
                    break

            if revenue_row is not None:
                # Columns are Timestamps (most recent first in yfinance ≥0.2)
                years_collected = 0
                for col in revenue_row.index:
                    if years_collected >= _MAX_REVENUE_YEARS:
                        break
                    value = revenue_row[col]
                    if value is None or (hasattr(value, "__float__") and value != value):
                        # Skip NaN
                        continue
                    year = col.year if hasattr(col, "year") else int(str(col)[:4])
                    result["revenue_3yr"].append(
                        {"year": year, "revenue_usd": float(value), "source": "yahoo_finance"}
                    )
                    years_collected += 1

            if result["revenue_3yr"]:
                result["sources"].append(
                    f"https://finance.yahoo.com/financials/{ticker}"
                )
    except Exception as exc:
        logger.warning(
            "[intel-investor] revenue fetch failed", ticker=ticker, error=str(exc)
        )

    # ── Analyst consensus ─────────────────────────────────────────────────────
    try:
        info = stock.info or {}
        # yfinance exposes 'recommendationKey' (e.g. 'buy', 'hold') and
        # 'recommendationMean' (numeric: 1=Strong Buy … 5=Strong Sell).
        consensus_key: str | None = info.get("recommendationKey")
        if consensus_key:
            result["analyst_consensus"] = consensus_key.title()  # "Buy", "Hold", etc.
            result["sources"].append(
                f"https://finance.yahoo.com/quote/{ticker}/analysis"
            )
    except Exception as exc:
        logger.warning(
            "[intel-investor] analyst consensus fetch failed",
            ticker=ticker,
            error=str(exc),
        )

    # ── Recent news ────────────────────────────────────────────────────────────
    try:
        news_items = stock.news or []
        for item in news_items[:_MAX_NEWS]:
            title = item.get("title") or item.get("content", {}).get("title", "")
            if title:
                result["recent_news"].append(title)
        if result["recent_news"]:
            result["sources"].append(
                f"https://finance.yahoo.com/quote/{ticker}/news"
            )
    except Exception as exc:
        logger.warning(
            "[intel-investor] news fetch failed", ticker=ticker, error=str(exc)
        )

    return result


async def collect(context: ExecutionContextV2) -> dict[str, Any]:
    """Collect deterministic Yahoo Finance signals for public companies.

    Returns a dict merged into context.upstream_results under the key
    ``investor_yahoo``. For private companies or missing tickers, returns
    an empty dict (Track 2 handles the residual). Never raises.
    """
    is_public, ticker = _resolve_public_status(context)

    if not is_public:
        logger.info(
            "[intel-investor] private company — skipping Yahoo Finance Track 1",
            domain=context.account_domain,
        )
        return {}

    if not ticker:
        logger.warning(
            "[intel-investor] public company but no ticker — skipping Yahoo Finance Track 1",
            domain=context.account_domain,
            company=context.company_name,
        )
        return {}

    logger.info(
        "[intel-investor] fetching Yahoo Finance data",
        ticker=ticker,
        domain=context.account_domain,
    )

    try:
        yahoo_data = _fetch_yahoo_data(ticker)
    except Exception as exc:
        # yfinance may not be installed in all environments — non-fatal
        logger.warning(
            "[intel-investor] Yahoo Finance fetch failed entirely",
            ticker=ticker,
            error=str(exc),
        )
        return {}

    logger.info(
        "[intel-investor] Track-1 complete",
        ticker=ticker,
        stock_price=yahoo_data.get("stock_price"),
        revenue_years=len(yahoo_data.get("revenue_3yr", [])),
        news_count=len(yahoo_data.get("recent_news", [])),
        analyst_consensus=yahoo_data.get("analyst_consensus"),
    )

    return {"investor_yahoo": yahoo_data}
