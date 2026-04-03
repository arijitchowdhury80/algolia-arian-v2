"""Integration tests for insights-engine module.

Tests module metadata, validator logic, enricher fallback, and full module flow
with mocked DB data (no real Gemini or DB calls).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from prism_platform.core.types import ModuleResult
from prism_platform.modules.insights_engine.module import InsightsModule
from prism_platform.modules.insights_engine.schemas import (
    InsightsInput,
    InsightsOutput,
    VerticalMetric,
)
from prism_platform.modules.insights_engine.validator import validate_output

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------


def _make_good_output() -> InsightsOutput:
    return InsightsOutput(
        domain="dell.com",
        vertical="Enterprise Technology",
        metrics=[
            VerticalMetric(
                metric_name="avg_search_quality_score",
                metric_value={"average": 7.2},
                sample_size=5,
                description="Average search quality.",
            ),
            VerticalMetric(
                metric_name="most_common_search_vendor",
                metric_value={"vendor": "Elasticsearch", "count": 3},
                sample_size=5,
                description="Most common search vendor.",
            ),
            VerticalMetric(
                metric_name="traffic_patterns",
                metric_value={"avg_monthly_visits": 1000000},
                sample_size=4,
                description="Traffic patterns.",
            ),
        ],
        audit_ids_included=["id1", "id2"],
        total_audits_in_vertical=5,
        summary="Enterprise Technology vertical shows strong search adoption.",
        is_first_in_vertical=False,
    )


# ---------------------------------------------------------------------------
# Module metadata tests
# ---------------------------------------------------------------------------
class TestModuleMetadata:
    def test_module_name(self) -> None:
        mod = InsightsModule()
        assert mod.name == "insights-engine"

    def test_module_version(self) -> None:
        mod = InsightsModule()
        assert mod.version == "0.1.0"

    def test_module_layer(self) -> None:
        mod = InsightsModule()
        assert mod.layer == "intelligence"

    def test_module_dependencies(self) -> None:
        mod = InsightsModule()
        assert mod.dependencies == []

    def test_module_requires_llm(self) -> None:
        mod = InsightsModule()
        assert mod.requires_llm is True

    def test_module_timeout(self) -> None:
        mod = InsightsModule()
        assert mod.timeout_seconds == 300

    def test_module_max_retries(self) -> None:
        mod = InsightsModule()
        assert mod.max_retries == 1

    def test_input_schema(self) -> None:
        mod = InsightsModule()
        assert mod.input_schema is InsightsInput

    def test_output_schema(self) -> None:
        mod = InsightsModule()
        assert mod.output_schema is InsightsOutput


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------
class TestValidator:
    def test_passes_with_good_data(self) -> None:
        output = _make_good_output()
        result = validate_output(output)
        assert result.passed is True
        assert result.checks_run == 8
        assert result.checks_passed == 8
        assert result.errors == []

    def test_fails_with_fewer_than_3_metrics(self) -> None:
        output = InsightsOutput(
            domain="dell.com",
            vertical="Tech",
            metrics=[
                VerticalMetric(
                    metric_name="m1",
                    metric_value={"x": 1},
                    sample_size=1,
                    description="d1",
                ),
            ],
            audit_ids_included=["id1"],
            total_audits_in_vertical=1,
            summary="Summary.",
            is_first_in_vertical=True,
        )
        result = validate_output(output)
        assert result.passed is False
        assert any("at least 3" in e for e in result.errors)

    def test_fails_with_empty_vertical(self) -> None:
        output = InsightsOutput(
            domain="dell.com",
            vertical="",
            metrics=[
                VerticalMetric(
                    metric_name=f"m{i}",
                    metric_value={"x": i},
                    sample_size=1,
                    description="d",
                )
                for i in range(1, 4)
            ],
            audit_ids_included=["id1"],
            total_audits_in_vertical=1,
            summary="Summary.",
            is_first_in_vertical=True,
        )
        result = validate_output(output)
        assert result.passed is False
        assert any("vertical is empty" in e for e in result.errors)

    def test_fails_with_empty_audit_ids(self) -> None:
        output = InsightsOutput(
            domain="dell.com",
            vertical="Tech",
            metrics=[
                VerticalMetric(
                    metric_name=f"m{i}",
                    metric_value={"x": i},
                    sample_size=1,
                    description="d",
                )
                for i in range(1, 4)
            ],
            audit_ids_included=[],
            total_audits_in_vertical=1,
            summary="Summary.",
            is_first_in_vertical=True,
        )
        result = validate_output(output)
        assert result.passed is False
        assert any("audit_ids_included is empty" in e for e in result.errors)

    def test_fails_with_empty_summary(self) -> None:
        output = InsightsOutput(
            domain="dell.com",
            vertical="Tech",
            metrics=[
                VerticalMetric(
                    metric_name=f"m{i}",
                    metric_value={"x": i},
                    sample_size=1,
                    description="d",
                )
                for i in range(1, 4)
            ],
            audit_ids_included=["id1"],
            total_audits_in_vertical=1,
            summary="",
            is_first_in_vertical=True,
        )
        result = validate_output(output)
        assert result.passed is False
        assert any("summary is empty" in e for e in result.errors)

    def test_warns_on_anonymization_with_known_domains(self) -> None:
        output = InsightsOutput(
            domain="dell.com",
            vertical="Tech",
            metrics=[
                VerticalMetric(
                    metric_name="m1",
                    metric_value={"company": "dell.com scored 8"},
                    sample_size=1,
                    description="d1",
                ),
                VerticalMetric(
                    metric_name="m2",
                    metric_value={"x": 2},
                    sample_size=1,
                    description="d2",
                ),
                VerticalMetric(
                    metric_name="m3",
                    metric_value={"x": 3},
                    sample_size=1,
                    description="d3",
                ),
            ],
            audit_ids_included=["id1"],
            total_audits_in_vertical=1,
            summary="Summary.",
            is_first_in_vertical=True,
        )
        result = validate_output(output, known_domains=["dell.com"])
        assert len(result.warnings) > 0
        assert any("dell.com" in w for w in result.warnings)

    def test_fails_inconsistent_first_in_vertical(self) -> None:
        output = InsightsOutput(
            domain="dell.com",
            vertical="Tech",
            metrics=[
                VerticalMetric(
                    metric_name=f"m{i}",
                    metric_value={"x": i},
                    sample_size=1,
                    description="d",
                )
                for i in range(1, 4)
            ],
            audit_ids_included=["id1", "id2"],
            total_audits_in_vertical=5,
            summary="Summary.",
            is_first_in_vertical=True,
        )
        result = validate_output(output)
        assert result.passed is False
        assert any("inconsistent" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Module health_check
# ---------------------------------------------------------------------------
class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_with_key(self) -> None:
        mod = InsightsModule()
        with patch("prism_platform.config.settings") as mock_settings:
            mock_settings.gemini_api_key = "test-key"
            result = await mod.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_without_key(self) -> None:
        mod = InsightsModule()
        with patch("prism_platform.config.settings") as mock_settings:
            mock_settings.gemini_api_key = ""
            result = await mod.health_check()
        assert result is False


# ---------------------------------------------------------------------------
# Full module execute with mock DB + enricher
# ---------------------------------------------------------------------------
class TestModuleExecute:
    @pytest.mark.asyncio
    async def test_full_execute_with_mock_data(self) -> None:
        """Full module flow with mocked collector and enricher."""
        mod = InsightsModule()
        good_output = _make_good_output()

        from prism_platform.core.module import ExecutionContext

        context = ExecutionContext(
            audit_id="00000000-0000-0000-0000-000000000001",
            account_id="00000000-0000-0000-0000-000000000002",
            domain="dell.com",
            company_name="Dell Technologies",
        )

        with (
            patch.object(mod._collector, "collect_all", new_callable=AsyncMock) as mock_collect,
            patch.object(mod._enricher, "enrich", new_callable=AsyncMock) as mock_enrich,
            patch.object(mod, "_persist_benchmarks", new_callable=AsyncMock) as mock_persist,
        ):
            mock_collect.return_value = {
                "vertical": "Enterprise Technology",
                "current_audit": {"intel-company": {"industry": "Enterprise Technology"}},
                "historical_audits": [],
                "historical_audit_ids": [],
                "total_audits": 1,
            }
            mock_enrich.return_value = (good_output, 1, 0.001)

            result = await mod.execute(context)

        assert result.status in ("success", "partial")
        assert result.module_name == "insights-engine"
        assert result.llm_calls == 1
        mock_persist.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_no_vertical_returns_partial(self) -> None:
        """When no vertical found, module returns partial status."""
        mod = InsightsModule()

        from prism_platform.core.module import ExecutionContext

        context = ExecutionContext(
            audit_id="00000000-0000-0000-0000-000000000001",
            account_id="00000000-0000-0000-0000-000000000002",
            domain="unknown.com",
            company_name="Unknown Corp",
        )

        with patch.object(mod._collector, "collect_all", new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = {
                "vertical": "",
                "current_audit": {},
                "historical_audits": [],
                "historical_audit_ids": [],
                "total_audits": 1,
            }

            result = await mod.execute(context)

        assert result.status == "partial"
        assert "No vertical" in result.errors[0]

    @pytest.mark.asyncio
    async def test_idempotency_runs_twice_same_result(self) -> None:
        """Running execute twice should produce equivalent results."""
        mod = InsightsModule()
        good_output = _make_good_output()

        from prism_platform.core.module import ExecutionContext

        context = ExecutionContext(
            audit_id="00000000-0000-0000-0000-000000000001",
            account_id="00000000-0000-0000-0000-000000000002",
            domain="dell.com",
            company_name="Dell Technologies",
        )

        with (
            patch.object(mod._collector, "collect_all", new_callable=AsyncMock) as mock_collect,
            patch.object(mod._enricher, "enrich", new_callable=AsyncMock) as mock_enrich,
            patch.object(mod, "_persist_benchmarks", new_callable=AsyncMock),
        ):
            mock_collect.return_value = {
                "vertical": "Enterprise Technology",
                "current_audit": {"intel-company": {"industry": "Enterprise Technology"}},
                "historical_audits": [],
                "historical_audit_ids": [],
                "total_audits": 1,
            }
            mock_enrich.return_value = (good_output, 1, 0.001)

            result1 = await mod.execute(context)
            result2 = await mod.execute(context)

        assert result1.status == result2.status
        assert result1.output == result2.output


# ---------------------------------------------------------------------------
# Module validate
# ---------------------------------------------------------------------------
class TestModuleValidate:
    @pytest.mark.asyncio
    async def test_validate_good_output(self) -> None:
        mod = InsightsModule()
        good_output = _make_good_output()
        module_result = ModuleResult(
            module_name="insights-engine",
            module_version="0.1.0",
            status="success",
            output=good_output.model_dump(),
        )
        validation = await mod.validate(module_result)
        assert validation.passed is True

    @pytest.mark.asyncio
    async def test_validate_bad_output(self) -> None:
        mod = InsightsModule()
        module_result = ModuleResult(
            module_name="insights-engine",
            module_version="0.1.0",
            status="success",
            output={"domain": "dell.com", "vertical": "Tech", "bogus": True},
        )
        validation = await mod.validate(module_result)
        assert validation.passed is False
