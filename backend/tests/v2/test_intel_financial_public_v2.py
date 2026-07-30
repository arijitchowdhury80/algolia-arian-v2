"""Tests for intel-financial-public v2 module."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from core.playbook import PlaybookLoader
from core.types import ExecutionContextV2
from prism_platform.v2.modules.intel_financial_public.config import (
    INTEL_FINANCIAL_PUBLIC_CONFIG,
)
from prism_platform.v2.modules.intel_financial_public.schemas import (
    AnnualFinancialSummary,
    EarningsCallQuote,
    FinancialPublicV2Output,
)

PLAYBOOK_PATH = (
    Path(__file__).parent.parent.parent
    / "prism_platform/v2/modules/intel_financial_public/playbook.md"
)


class TestEarningsCallQuote:
    def test_valid_quote(self) -> None:
        q = EarningsCallQuote(
            speaker="Jeff Clarke, CEO",
            quote="Our site search improvements drove a 12% conversion lift.",
            date="Q3 FY2025",
            source="Q3 FY2025 Earnings Call",
            source_url="https://seekingalpha.com/dell-q3-2025",
            relevance_to_search="high",
        )
        assert q.relevance_to_search == "high"

    def test_is_frozen(self) -> None:
        q = EarningsCallQuote(
            speaker="CEO",
            quote="test",
            date="2025",
            source="call",
        )
        with pytest.raises(ValidationError):
            q.quote = "changed"  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            EarningsCallQuote(
                speaker="CEO",
                quote="test",
                date="2025",
                source="call",
                extra_field="bad",  # type: ignore[call-arg]
            )


class TestFinancialPublicV2Output:
    def test_valid_public_output(self) -> None:
        out = FinancialPublicV2Output(
            domain="dell.com",
            ticker="DELL",
            skipped=False,
            annual_financials=[
                AnnualFinancialSummary(
                    fiscal_year="FY2025",
                    revenue_usd=92300000000.0,
                    revenue_growth_pct=8.1,
                    source="10-K FY2025",
                )
            ],
            financial_narrative="Dell revenue grew 8.1% to $92.3B in FY2025.",
        )
        assert out.ticker == "DELL"
        assert out.skipped is False

    def test_skip_logic_fields(self) -> None:
        out = FinancialPublicV2Output(
            domain="private.com",
            ticker=None,
            skipped=True,
            skip_reason="Private company — no public financial data",
            financial_narrative="Skipped.",
        )
        assert out.skipped is True
        assert out.skip_reason is not None

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            FinancialPublicV2Output(
                domain="dell.com",
                financial_narrative="test",
                unknown="bad",  # type: ignore[call-arg]
            )

    def test_narrative_required(self) -> None:
        with pytest.raises(ValidationError):
            FinancialPublicV2Output(domain="dell.com")  # type: ignore[call-arg]

    def test_generates_json_schema(self) -> None:
        schema = FinancialPublicV2Output.model_json_schema()
        assert "earnings_call_quotes" in schema["properties"]
        assert "stated_technology_priorities" in schema["properties"]


class TestIntelFinancialPublicConfig:
    def test_name(self) -> None:
        assert INTEL_FINANCIAL_PUBLIC_CONFIG.name == "intel-financial-public"

    def test_version(self) -> None:
        assert INTEL_FINANCIAL_PUBLIC_CONFIG.version.startswith("2.")

    def test_layer_is_intelligence(self) -> None:
        assert INTEL_FINANCIAL_PUBLIC_CONFIG.layer == "intelligence"

    def test_cost_tier_is_deep_research(self) -> None:
        # Earnings call transcripts require deep-research tier
        assert INTEL_FINANCIAL_PUBLIC_CONFIG.cost_tier == "deep-research"


class TestIntelFinancialPublicPlaybook:
    def test_playbook_exists(self) -> None:
        assert PLAYBOOK_PATH.exists()

    def test_execution_strategy_is_prospect_only(self) -> None:
        loader = PlaybookLoader()
        meta, _ = loader.load(PLAYBOOK_PATH)
        assert meta.execution_strategy == "prospect-only"

    def test_playbook_resolves_ticker(self) -> None:
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
