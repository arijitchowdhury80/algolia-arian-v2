"""Tests for intel-financial-private v2 module."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from prism_platform.v2.modules.intel_financial_private.config import (
    INTEL_FINANCIAL_PRIVATE_CONFIG,
)
from prism_platform.v2.modules.intel_financial_private.schemas import (
    FinancialPrivateV2Output,
    RevenueEstimateV2,
)
from prism_platform.v2.playbook import PlaybookLoader
from prism_platform.v2.types import ExecutionContextV2

PLAYBOOK_PATH = (
    Path(__file__).parent.parent.parent
    / "prism_platform/v2/modules/intel_financial_private/playbook.md"
)


class TestRevenueEstimateV2:
    def test_valid_estimate(self) -> None:
        e = RevenueEstimateV2(
            source_name="Crunchbase",
            estimated_revenue_usd=50000000.0,
            confidence="medium",
            evidence="$50M Series C at 5x revenue multiple",
            evidence_url="https://crunchbase.com/company/x",
        )
        assert e.confidence == "medium"

    def test_is_frozen(self) -> None:
        e = RevenueEstimateV2(
            source_name="test",
            confidence="low",
            evidence="test",
        )
        with pytest.raises(ValidationError):
            e.source_name = "changed"  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            RevenueEstimateV2(
                source_name="test",
                confidence="low",
                evidence="test",
                bad="oops",  # type: ignore[call-arg]
            )


class TestFinancialPrivateV2Output:
    def test_valid_output(self) -> None:
        out = FinancialPrivateV2Output(
            domain="private.com",
            revenue_estimates=[
                RevenueEstimateV2(
                    source_name="Employee model",
                    estimated_revenue_usd=75000000.0,
                    confidence="low",
                    evidence="~500 employees x $150K/employee",
                )
            ],
            best_estimate_usd=75000000.0,
            estimate_range="$50M-$100M",
            confidence="low",
            financial_narrative="Estimated revenue $50M-$100M based on employee count model.",
        )
        assert out.confidence == "low"
        assert len(out.revenue_estimates) == 1

    def test_skip_logic(self) -> None:
        out = FinancialPrivateV2Output(
            domain="dell.com",
            skipped=True,
            skip_reason="Public company — use intel-financial-public instead",
            financial_narrative="Skipped.",
        )
        assert out.skipped is True

    def test_narrative_required(self) -> None:
        with pytest.raises(ValidationError):
            FinancialPrivateV2Output(domain="x.com")  # type: ignore[call-arg]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            FinancialPrivateV2Output(
                domain="x.com",
                financial_narrative="test",
                extra="bad",  # type: ignore[call-arg]
            )

    def test_generates_json_schema(self) -> None:
        schema = FinancialPrivateV2Output.model_json_schema()
        assert "revenue_estimates" in schema["properties"]
        assert "funding_data" in schema["properties"]


class TestIntelFinancialPrivateConfig:
    def test_name(self) -> None:
        assert INTEL_FINANCIAL_PRIVATE_CONFIG.name == "intel-financial-private"

    def test_version(self) -> None:
        assert INTEL_FINANCIAL_PRIVATE_CONFIG.version.startswith("2.")

    def test_layer(self) -> None:
        assert INTEL_FINANCIAL_PRIVATE_CONFIG.layer == "intelligence"

    def test_cost_tier(self) -> None:
        assert INTEL_FINANCIAL_PRIVATE_CONFIG.cost_tier == "pro-search"


class TestIntelFinancialPrivatePlaybook:
    def test_playbook_exists(self) -> None:
        assert PLAYBOOK_PATH.exists()

    def test_execution_strategy_is_prospect_only(self) -> None:
        loader = PlaybookLoader()
        meta, _ = loader.load(PLAYBOOK_PATH)
        assert meta.execution_strategy == "prospect-only"

    def test_playbook_resolves_domain(self) -> None:
        loader = PlaybookLoader()
        context = ExecutionContextV2(
            audit_id="t",
            account_domain="startup.com",
            company_name="Startup Inc",
            industry="SaaS",
            is_public=False,
        )
        _, body = loader.load(PLAYBOOK_PATH)
        resolved = loader.resolve(body, context)
        assert "startup.com" in resolved
        assert "Startup Inc" in resolved
