"""Integration tests for intel-financial-private module.

Tests the full module execute() flow:
- Public company (dell.com) should be skipped.
- Private company context should run the full waterfall (requires API keys).
"""

from __future__ import annotations

import os

import pytest

from prism_platform.core.module import ExecutionContext
from prism_platform.modules.intel_financial_private.module import FinancialPrivateModule
from prism_platform.modules.intel_financial_private.schemas import FinancialPrivateOutput


@pytest.fixture
def module() -> FinancialPrivateModule:
    """Create a FinancialPrivateModule instance."""
    return FinancialPrivateModule()


@pytest.fixture
def public_context() -> ExecutionContext:
    """ExecutionContext for a public company (Dell) -- should be skipped."""
    return ExecutionContext(
        audit_id="test-audit-001",
        account_id="test-account-001",
        domain="dell.com",
        company_name="Dell Technologies",
        ticker="DELL",
        is_private=False,
    )


@pytest.fixture
def private_context() -> ExecutionContext:
    """ExecutionContext for a private company -- should run full waterfall."""
    return ExecutionContext(
        audit_id="test-audit-002",
        account_id="test-account-002",
        domain="databricks.com",
        company_name="Databricks",
        ticker=None,
        is_private=True,
    )


class TestFinancialPrivateModuleMetadata:
    """Tests for module metadata and class variables."""

    def test_module_name(self, module: FinancialPrivateModule) -> None:
        assert module.name == "intel-financial-private"

    def test_module_version(self, module: FinancialPrivateModule) -> None:
        assert module.version == "0.1.0"

    def test_module_layer(self, module: FinancialPrivateModule) -> None:
        assert module.layer == "intelligence"

    def test_module_dependencies(self, module: FinancialPrivateModule) -> None:
        assert "intel-company" in module.dependencies

    def test_module_requires_llm(self, module: FinancialPrivateModule) -> None:
        assert module.requires_llm is True

    def test_timeout(self, module: FinancialPrivateModule) -> None:
        assert module.timeout_seconds == 180


class TestPublicCompanySkip:
    """Test that public companies are skipped immediately."""

    @pytest.mark.asyncio
    async def test_public_company_returns_skipped(
        self,
        module: FinancialPrivateModule,
        public_context: ExecutionContext,
    ) -> None:
        result = await module.execute(public_context)

        assert result.status == "success"
        assert result.module_name == "intel-financial-private"

        output = FinancialPrivateOutput.model_validate(result.output)
        assert output.skipped is True
        assert output.skip_reason is not None
        assert "public" in output.skip_reason.lower()
        assert output.revenue_waterfall is None

    @pytest.mark.asyncio
    async def test_public_company_validation_passes(
        self,
        module: FinancialPrivateModule,
        public_context: ExecutionContext,
    ) -> None:
        result = await module.execute(public_context)
        validation = await module.validate(result)
        assert validation.passed is True

    @pytest.mark.asyncio
    async def test_public_company_no_llm_calls(
        self,
        module: FinancialPrivateModule,
        public_context: ExecutionContext,
    ) -> None:
        result = await module.execute(public_context)
        assert result.llm_calls == 0
        assert result.llm_cost_usd == 0.0

    @pytest.mark.asyncio
    async def test_public_company_fast_execution(
        self,
        module: FinancialPrivateModule,
        public_context: ExecutionContext,
    ) -> None:
        result = await module.execute(public_context)
        # Skip path should be < 100ms
        assert result.duration_ms < 100


@pytest.mark.skipif(
    not os.environ.get("PERPLEXITY_API_KEY") or not os.environ.get("GEMINI_API_KEY"),
    reason="PERPLEXITY_API_KEY and GEMINI_API_KEY required for live integration test",
)
class TestPrivateCompanyWaterfall:
    """Integration tests with real API calls -- requires API keys."""

    @pytest.mark.asyncio
    async def test_private_company_runs_waterfall(
        self,
        module: FinancialPrivateModule,
        private_context: ExecutionContext,
    ) -> None:
        result = await module.execute(private_context)

        assert result.status in ("success", "partial")
        assert result.module_name == "intel-financial-private"
        assert result.llm_calls > 0

        output = FinancialPrivateOutput.model_validate(result.output)
        assert output.skipped is False
        assert output.domain == "databricks.com"

    @pytest.mark.asyncio
    async def test_private_company_has_waterfall(
        self,
        module: FinancialPrivateModule,
        private_context: ExecutionContext,
    ) -> None:
        result = await module.execute(private_context)
        output = FinancialPrivateOutput.model_validate(result.output)

        assert output.revenue_waterfall is not None
        assert len(output.revenue_waterfall.estimates) >= 1

    @pytest.mark.asyncio
    async def test_private_company_has_sources(
        self,
        module: FinancialPrivateModule,
        private_context: ExecutionContext,
    ) -> None:
        result = await module.execute(private_context)
        assert len(result.sources) >= 1

    @pytest.mark.asyncio
    async def test_private_company_validation(
        self,
        module: FinancialPrivateModule,
        private_context: ExecutionContext,
    ) -> None:
        result = await module.execute(private_context)
        validation = await module.validate(result)
        # May be partial if not all sources return data
        assert validation.checks_run >= 4
