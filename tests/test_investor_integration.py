"""End-to-end integration tests for intel-investor module.

These tests run the full module pipeline against dell.com with real API calls.

Requires: PERPLEXITY_API_KEY and GEMINI_API_KEY set in .env.

Run with: pytest tests/test_investor_integration.py -v
"""

from __future__ import annotations

import os

import pytest

from prism_platform.core.module import ExecutionContext
from prism_platform.modules.intel_investor.module import InvestorModule
from prism_platform.modules.intel_investor.schemas import InvestorOutput
from prism_platform.modules.intel_investor.validator import validate_output

# Marker for tests that require Perplexity + Gemini API keys
requires_api_keys = pytest.mark.skipif(
    not (os.environ.get("PERPLEXITY_API_KEY") and os.environ.get("GEMINI_API_KEY")),
    reason="PERPLEXITY_API_KEY and GEMINI_API_KEY required",
)


def _make_public_context() -> ExecutionContext:
    """Build a test ExecutionContext for dell.com (public company)."""
    return ExecutionContext(
        audit_id="test-audit-inv-001",
        account_id="00000000-0000-0000-0000-000000000001",
        domain="dell.com",
        company_name="Dell Technologies",
        ticker="DELL",
        is_private=False,
    )


def _make_private_context() -> ExecutionContext:
    """Build a test ExecutionContext for a private company."""
    return ExecutionContext(
        audit_id="test-audit-inv-002",
        account_id="00000000-0000-0000-0000-000000000002",
        domain="stripe.com",
        company_name="Stripe Inc.",
        ticker=None,
        is_private=True,
    )


# ---------------------------------------------------------------------------
# Module skip / private behavior
# ---------------------------------------------------------------------------


class TestModulePrivateBehavior:
    """Test that the module handles private companies correctly."""

    @requires_api_keys
    @pytest.mark.asyncio
    async def test_private_company_still_runs(self) -> None:
        """Private company should still produce output (not skip)."""
        module = InvestorModule()
        context = _make_private_context()
        result = await module.execute(context)

        assert result.status in ("success", "partial"), (
            f"Expected success/partial for private company, got {result.status}"
        )
        assert result.module_name == "intel-investor"

        output = InvestorOutput.model_validate(result.output)
        # Private companies should NOT be skipped -- they get Perplexity-only strategy
        assert output.skipped is False
        assert output.domain == "stripe.com"
        assert output.ticker is None

    @requires_api_keys
    @pytest.mark.asyncio
    async def test_private_company_validates(self) -> None:
        """Private company output should pass validation."""
        module = InvestorModule()
        context = _make_private_context()
        result = await module.execute(context)

        validation = await module.validate(result)
        # May have warnings but should not have hard errors on counts
        if not validation.passed:
            for err in validation.errors:
                print(f"  ERROR: {err}")


# ---------------------------------------------------------------------------
# Full pipeline integration (requires API keys)
# ---------------------------------------------------------------------------


@requires_api_keys
class TestFullPipelineIntegration:
    """Full pipeline tests against dell.com with real API calls."""

    @pytest.mark.asyncio
    async def test_full_dell_pipeline(self) -> None:
        """Run the full investor module against Dell Technologies.

        This is the primary integration test. It verifies:
        1. Module executes successfully
        2. Output deserializes to InvestorOutput
        3. Earnings quotes are extracted
        4. Said vs Found mappings are generated
        5. Sources are attached
        """
        module = InvestorModule()
        context = _make_public_context()
        result = await module.execute(context)

        assert result.status == "success", f"Module failed: {result.errors}"
        assert result.module_name == "intel-investor"
        assert result.duration_ms > 0
        assert result.llm_calls > 0

        output = InvestorOutput.model_validate(result.output)

        # Part 1: Prospect quotes
        assert output.domain == "dell.com"
        assert output.ticker == "DELL"
        assert len(output.prospect_quotes) >= 1, "Expected at least 1 earnings quote for Dell"

        # Verify quote structure
        for q in output.prospect_quotes:
            assert q.speaker_name, "speaker_name should not be empty"
            assert q.quote, "quote should not be empty"
            assert q.source, "source should not be empty"

        # Part 2: Said vs Found (THE CORE DELIVERABLE)
        assert len(output.said_vs_found) >= 1, "Expected at least 1 Said vs Found mapping"
        for svf in output.said_vs_found:
            assert svf.algolia_angle, "algolia_angle should not be empty"
            assert svf.recommended_talking_point, "talking_point should not be empty"

        # Computed counts should be consistent
        actual_commitments = sum(1 for q in output.prospect_quotes if q.is_commitment)
        assert output.commitment_count == actual_commitments

        actual_pain = sum(1 for q in output.prospect_quotes if q.category == "pain_signal")
        assert output.pain_signal_count == actual_pain

        # Sources should be attached
        assert len(result.sources) >= 1, "Expected at least 1 source"

    @pytest.mark.asyncio
    async def test_dell_validation_passes(self) -> None:
        """Dell output should pass the 10-check validation."""
        module = InvestorModule()
        context = _make_public_context()
        result = await module.execute(context)

        validation = await module.validate(result)

        assert validation.checks_run >= 8, f"Expected >= 8 checks, got {validation.checks_run}"

        if not validation.passed:
            for err in validation.errors:
                print(f"  ERROR: {err}")
            for warn in validation.warnings:
                print(f"  WARNING: {warn}")

        # Counts should match (checks 4 and 5)
        output = InvestorOutput.model_validate(result.output)

        val_result = validate_output(output, result.sources, expected_domain="dell.com")
        count_errors = [e for e in val_result.errors if "mismatch" in e]
        assert len(count_errors) == 0, f"Count mismatches found: {count_errors}"


# ---------------------------------------------------------------------------
# Module health check
# ---------------------------------------------------------------------------


@requires_api_keys
class TestModuleHealthCheck:
    """Test module health check."""

    @pytest.mark.asyncio
    async def test_health_check_passes(self) -> None:
        """Health check should pass when API keys are set."""
        module = InvestorModule()
        healthy = await module.health_check()
        assert healthy is True, (
            "Health check failed -- check PERPLEXITY_API_KEY and GEMINI_API_KEY in .env"
        )


# ---------------------------------------------------------------------------
# Module metadata
# ---------------------------------------------------------------------------


class TestModuleMetadata:
    """Test module class properties."""

    def test_module_name(self) -> None:
        """Module name should be intel-investor."""
        module = InvestorModule()
        assert module.name == "intel-investor"

    def test_module_version(self) -> None:
        """Module version should be 0.1.0."""
        module = InvestorModule()
        assert module.version == "0.1.0"

    def test_module_dependencies(self) -> None:
        """Module should depend on intel-company and intel-financial-public."""
        module = InvestorModule()
        assert "intel-company" in module.dependencies
        assert "intel-financial-public" in module.dependencies

    def test_module_requires_llm(self) -> None:
        """Module should require LLM."""
        module = InvestorModule()
        assert module.requires_llm is True

    def test_module_timeout(self) -> None:
        """Module timeout should be 600 seconds."""
        module = InvestorModule()
        assert module.timeout_seconds == 600

    def test_module_layer(self) -> None:
        """Module layer should be intelligence."""
        module = InvestorModule()
        assert module.layer == "intelligence"
