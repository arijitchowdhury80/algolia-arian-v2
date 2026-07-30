"""Tests for intel-investor v2 module.

Coverage:
  - Schema validation and field constraints
  - Collector: public company with full data
  - Collector: public company with no ticker (graceful empty return)
  - Collector: private company (graceful skip)
  - Collector: yfinance raises (graceful empty return)
  - Collector: ticker resolved from upstream intel-company result
  - Config assertions
  - Playbook existence and execution-strategy meta

Yahoo Finance calls are mocked via unittest.mock.patch — no real network calls.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.playbook import PlaybookLoader
from core.types import ExecutionContextV2
from prism_platform.v2.modules.intel_investor.collector import (
    _resolve_public_status,
    collect,
)
from prism_platform.v2.modules.intel_investor.config import INTEL_INVESTOR_CONFIG
from prism_platform.v2.modules.intel_investor.schemas import (
    ExecutiveQuote,
    InvestorIntelOutput,
    RevenueDataPoint,
)

PLAYBOOK_PATH = (
    Path(__file__).parent.parent.parent
    / "prism_platform/v2/modules/intel_investor/playbook.md"
)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _public_context(**kwargs: Any) -> ExecutionContextV2:
    return ExecutionContextV2(
        audit_id=str(uuid4()),
        account_domain="dell.com",
        company_name="Dell Technologies",
        industry="Enterprise Technology",
        is_public=True,
        ticker="DELL",
        **kwargs,
    )


def _private_context(**kwargs: Any) -> ExecutionContextV2:
    return ExecutionContextV2(
        audit_id=str(uuid4()),
        account_domain="acme.com",
        company_name="Acme Corp",
        industry="Manufacturing",
        is_public=False,
        ticker=None,
        **kwargs,
    )


def _mock_yf_ticker(
    *,
    price: float | None = 125.50,
    revenue_rows: dict[str, Any] | None = None,
    recommendation_key: str | None = "buy",
    news: list[dict[str, Any]] | None = None,
) -> MagicMock:
    """Build a minimal yfinance.Ticker mock."""
    import pandas as pd

    ticker_mock = MagicMock()

    # stock.info
    info: dict[str, Any] = {}
    if price is not None:
        info["currentPrice"] = price
    if recommendation_key is not None:
        info["recommendationKey"] = recommendation_key
    ticker_mock.info = info

    # stock.income_stmt — a DataFrame with "Total Revenue" row
    if revenue_rows is not None:
        ticker_mock.income_stmt = pd.DataFrame(revenue_rows)
    else:
        # Default: 3 years of revenue data
        idx = pd.to_datetime(["2024-01-31", "2023-01-31", "2022-01-31"])
        ticker_mock.income_stmt = pd.DataFrame(
            {"Total Revenue": [92_300_000_000.0, 88_500_000_000.0, 80_100_000_000.0]},
            index=["Total Revenue"],
            columns=idx,
        )

    # stock.news
    ticker_mock.news = news if news is not None else [
        {"title": "Dell reports strong Q1 results"},
        {"title": "Dell AI PC demand surges"},
    ]

    return ticker_mock


# ── Schema tests ───────────────────────────────────────────────────────────────


class TestRevenueDataPoint:
    def test_valid(self) -> None:
        r = RevenueDataPoint(year=2024, revenue_usd=88_400_000_000.0, source="yahoo_finance")
        assert r.year == 2024
        assert r.revenue_usd == 88_400_000_000.0

    def test_is_frozen(self) -> None:
        r = RevenueDataPoint(year=2024, revenue_usd=1.0, source="yahoo_finance")
        with pytest.raises((ValidationError, TypeError)):
            r.year = 2025  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            RevenueDataPoint(
                year=2024, revenue_usd=1.0, source="yahoo_finance", extra="bad"  # type: ignore[call-arg]
            )


class TestExecutiveQuote:
    def test_valid(self) -> None:
        q = ExecutiveQuote(
            quote="Our search investments drove a 12% conversion lift.",
            speaker="Jeff Clarke",
            title="CEO",
            theme="search_conversion",
            source="Q3 FY2025 Earnings Call",
        )
        assert q.theme == "search_conversion"

    def test_is_frozen(self) -> None:
        q = ExecutiveQuote(
            quote="test", speaker="CEO", title="CEO", theme="digital_experience", source="call"
        )
        with pytest.raises((ValidationError, TypeError)):
            q.quote = "changed"  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            ExecutiveQuote(
                quote="test",
                speaker="CEO",
                title="CEO",
                theme="digital_experience",
                source="call",
                extra_field="bad",  # type: ignore[call-arg]
            )


class TestInvestorIntelOutput:
    def test_minimal_public_output(self) -> None:
        out = InvestorIntelOutput(
            domain="dell.com",
            is_public=True,
            ticker="DELL",
            stock_price=125.50,
            analyst_consensus="Buy",
        )
        assert out.domain == "dell.com"
        assert out.is_public is True
        assert out.revenue_3yr == []
        assert out.executive_quotes == []
        assert out.recent_news == []
        assert out.sources == []

    def test_full_public_output(self) -> None:
        out = InvestorIntelOutput(
            domain="dell.com",
            is_public=True,
            ticker="DELL",
            stock_price=125.50,
            revenue_3yr=[
                RevenueDataPoint(year=2024, revenue_usd=92_300_000_000.0, source="yahoo_finance"),
            ],
            analyst_consensus="Buy",
            recent_news=["Dell reports strong Q1"],
            executive_quotes=[
                ExecutiveQuote(
                    quote="Our digital experience investments are paying off.",
                    speaker="Jeff Clarke",
                    title="CEO",
                    theme="digital_experience",
                    source="Q3 FY2025 Earnings Call",
                )
            ],
            sources=["https://finance.yahoo.com/quote/DELL"],
        )
        assert len(out.revenue_3yr) == 1
        assert out.revenue_3yr[0].revenue_usd == 92_300_000_000.0
        assert len(out.executive_quotes) == 1

    def test_private_company_output(self) -> None:
        out = InvestorIntelOutput(
            domain="acme.com",
            is_public=False,
            ticker=None,
            stock_price=None,
            analyst_consensus=None,
        )
        assert out.is_public is False
        assert out.ticker is None
        assert out.stock_price is None
        assert out.analyst_consensus is None

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            InvestorIntelOutput(domain="dell.com", unknown="bad")  # type: ignore[call-arg]

    def test_generates_json_schema(self) -> None:
        schema = InvestorIntelOutput.model_json_schema()
        props = schema["properties"]
        assert "domain" in props
        assert "is_public" in props
        assert "ticker" in props
        assert "stock_price" in props
        assert "revenue_3yr" in props
        assert "analyst_consensus" in props
        assert "recent_news" in props
        assert "executive_quotes" in props
        assert "sources" in props


# ── Config tests ───────────────────────────────────────────────────────────────


class TestIntelInvestorConfig:
    def test_name(self) -> None:
        assert INTEL_INVESTOR_CONFIG.name == "intel-investor"

    def test_version(self) -> None:
        assert INTEL_INVESTOR_CONFIG.version.startswith("2.")

    def test_layer_is_intelligence(self) -> None:
        assert INTEL_INVESTOR_CONFIG.layer == "intelligence"

    def test_cost_tier_is_deep_research(self) -> None:
        assert INTEL_INVESTOR_CONFIG.cost_tier == "deep-research"

    def test_composes_intel_company(self) -> None:
        assert "intel-company" in INTEL_INVESTOR_CONFIG.composes

    def test_api_clients_documents_yfinance(self) -> None:
        assert "yfinance" in INTEL_INVESTOR_CONFIG.api_clients


# ── Playbook tests ─────────────────────────────────────────────────────────────


class TestIntelInvestorPlaybook:
    def test_playbook_exists(self) -> None:
        assert PLAYBOOK_PATH.exists(), f"Playbook not found at {PLAYBOOK_PATH}"

    def test_execution_strategy_is_prospect_only(self) -> None:
        loader = PlaybookLoader()
        meta, _ = loader.load(PLAYBOOK_PATH)
        assert meta.execution_strategy == "prospect-only"

    def test_playbook_resolves_ticker_and_domain(self) -> None:
        loader = PlaybookLoader()
        context = ExecutionContextV2(
            audit_id="t",
            account_domain="dell.com",
            company_name="Dell Technologies",
            industry="Tech",
            is_public=True,
            ticker="DELL",
        )
        _, body = loader.load(PLAYBOOK_PATH)
        resolved = loader.resolve(body, context)
        assert "DELL" in resolved
        assert "dell.com" in resolved

    def test_playbook_resolves_for_private_company(self) -> None:
        loader = PlaybookLoader()
        context = ExecutionContextV2(
            audit_id="t",
            account_domain="acme.com",
            company_name="Acme Corp",
            industry="Retail",
            is_public=False,
            ticker=None,
        )
        _, body = loader.load(PLAYBOOK_PATH)
        resolved = loader.resolve(body, context)
        assert "acme.com" in resolved


# ── Collector tests ────────────────────────────────────────────────────────────


class TestResolvePublicStatus:
    def test_reads_context_fields_directly(self) -> None:
        ctx = _public_context()
        is_public, ticker = _resolve_public_status(ctx)
        assert is_public is True
        assert ticker == "DELL"

    def test_private_company_context(self) -> None:
        ctx = _private_context()
        is_public, ticker = _resolve_public_status(ctx)
        assert is_public is False
        assert ticker is None

    def test_falls_back_to_upstream_intel_company(self) -> None:
        ctx = ExecutionContextV2(
            audit_id=str(uuid4()),
            account_domain="dell.com",
            company_name="Dell Technologies",
            industry="Tech",
            is_public=False,  # not set in context
            ticker=None,      # not set in context
            upstream_results={
                "intel-company": {"is_public": True, "ticker": "DELL"}
            },
        )
        is_public, ticker = _resolve_public_status(ctx)
        assert is_public is True
        assert ticker == "DELL"


class TestCollectorPrivateCompany:
    def test_returns_empty_for_private(self) -> None:
        ctx = _private_context()
        result = asyncio.run(collect(ctx))
        assert result == {}

    def test_returns_empty_for_public_without_ticker(self) -> None:
        ctx = ExecutionContextV2(
            audit_id=str(uuid4()),
            account_domain="dell.com",
            company_name="Dell Technologies",
            industry="Tech",
            is_public=True,
            ticker=None,
        )
        result = asyncio.run(collect(ctx))
        assert result == {}


class TestCollectorPublicCompany:
    def test_returns_investor_yahoo_key(self) -> None:
        ticker_mock = _mock_yf_ticker()
        with patch("prism_platform.v2.modules.intel_investor.collector.yf") as mock_yf_module:
            mock_yf_module.Ticker.return_value = ticker_mock
            ctx = _public_context()
            result = asyncio.run(collect(ctx))

        assert "investor_yahoo" in result
        data = result["investor_yahoo"]
        assert data["stock_price"] == 125.50
        assert data["analyst_consensus"] == "Buy"
        assert isinstance(data["revenue_3yr"], list)
        assert isinstance(data["recent_news"], list)
        assert isinstance(data["sources"], list)

    def test_news_headlines_capped_at_five(self) -> None:
        many_news = [{"title": f"Headline {i}"} for i in range(10)]
        ticker_mock = _mock_yf_ticker(news=many_news)
        with patch("prism_platform.v2.modules.intel_investor.collector.yf") as mock_yf_module:
            mock_yf_module.Ticker.return_value = ticker_mock
            ctx = _public_context()
            result = asyncio.run(collect(ctx))

        assert len(result["investor_yahoo"]["recent_news"]) <= 5

    def test_graceful_on_yfinance_import_error(self) -> None:
        """If yfinance raises at import time, collector returns empty dict."""
        ctx = _public_context()
        with patch(
            "prism_platform.v2.modules.intel_investor.collector._fetch_yahoo_data",
            side_effect=ImportError("No module named 'yfinance'"),
        ):
            result = asyncio.run(collect(ctx))

        assert result == {}

    def test_graceful_on_fetch_exception(self) -> None:
        """If _fetch_yahoo_data raises, collector returns empty dict."""
        ctx = _public_context()
        with patch(
            "prism_platform.v2.modules.intel_investor.collector._fetch_yahoo_data",
            side_effect=RuntimeError("network timeout"),
        ):
            result = asyncio.run(collect(ctx))

        assert result == {}

    def test_revenue_years_capped_at_three(self) -> None:
        import pandas as pd

        # Supply 5 years of data; should only collect 3.
        idx = pd.to_datetime([
            "2024-01-31", "2023-01-31", "2022-01-31", "2021-01-31", "2020-01-31"
        ])
        df = pd.DataFrame(
            [90e9, 88e9, 80e9, 70e9, 60e9],
            index=idx,
            columns=["Total Revenue"],
        ).T
        ticker_mock = _mock_yf_ticker(revenue_rows=None)
        ticker_mock.income_stmt = df

        with patch("prism_platform.v2.modules.intel_investor.collector.yf") as mock_yf_module:
            mock_yf_module.Ticker.return_value = ticker_mock
            ctx = _public_context()
            result = asyncio.run(collect(ctx))

        assert len(result["investor_yahoo"]["revenue_3yr"]) <= 3

    def test_missing_stock_price_is_handled(self) -> None:
        """currentPrice absent from info dict — stock_price should be None."""
        ticker_mock = _mock_yf_ticker(price=None)
        ticker_mock.info = {}  # completely empty info
        with patch("prism_platform.v2.modules.intel_investor.collector.yf") as mock_yf_module:
            mock_yf_module.Ticker.return_value = ticker_mock
            ctx = _public_context()
            result = asyncio.run(collect(ctx))

        assert result["investor_yahoo"]["stock_price"] is None


# ── Registry integration test ─────────────────────────────────────────────────


class TestRegistryIntegration:
    def test_intel_investor_is_registered(self) -> None:
        from core.registry import V2_MODULE_REGISTRY, register_all_v2_modules

        register_all_v2_modules()
        assert "intel-investor" in V2_MODULE_REGISTRY

    def test_registered_handle_has_collector(self) -> None:
        from core.registry import V2_MODULE_REGISTRY, register_all_v2_modules

        register_all_v2_modules()
        handle = V2_MODULE_REGISTRY["intel-investor"]
        assert handle.collector is not None

    def test_registered_handle_has_playbook(self) -> None:
        from core.registry import V2_MODULE_REGISTRY, register_all_v2_modules

        register_all_v2_modules()
        handle = V2_MODULE_REGISTRY["intel-investor"]
        assert handle.playbook_path.exists()

    def test_output_schema_is_investor_intel_output(self) -> None:
        from core.registry import V2_MODULE_REGISTRY, register_all_v2_modules

        register_all_v2_modules()
        handle = V2_MODULE_REGISTRY["intel-investor"]
        assert handle.output_schema is InvestorIntelOutput
