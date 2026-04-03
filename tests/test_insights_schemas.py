"""Contract tests for insights-engine schemas -- pure Pydantic tests, no API/DB calls."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.insights_engine.schemas import (
    InsightsInput,
    InsightsOutput,
    VerticalMetric,
)


# ---------------------------------------------------------------------------
# InsightsInput
# ---------------------------------------------------------------------------
class TestInsightsInput:
    def test_valid_input(self) -> None:
        inp = InsightsInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            InsightsInput(domain="dell.com", bogus="nope")  # type: ignore[call-arg]

    def test_empty_domain_allowed_by_schema(self) -> None:
        """Domain validation is handled by the validator, not the schema."""
        inp = InsightsInput(domain="")
        assert inp.domain == ""

    def test_missing_domain_raises(self) -> None:
        with pytest.raises(ValidationError):
            InsightsInput()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# VerticalMetric
# ---------------------------------------------------------------------------
class TestVerticalMetric:
    def test_valid_full(self) -> None:
        vm = VerticalMetric(
            metric_name="avg_search_quality_score",
            metric_value={"average": 7.2, "min": 4.0, "max": 9.5},
            sample_size=5,
            description="Average search quality score across audits in this vertical.",
        )
        assert vm.metric_name == "avg_search_quality_score"
        assert vm.sample_size == 5
        assert vm.metric_value["average"] == 7.2

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            VerticalMetric(
                metric_name="test",
                metric_value={"x": 1},
                sample_size=1,
                description="test",
                bogus="nope",  # type: ignore[call-arg]
            )

    def test_sample_size_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            VerticalMetric(
                metric_name="test",
                metric_value={"x": 1},
                sample_size=0,
                description="test",
            )

    def test_sample_size_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            VerticalMetric(
                metric_name="test",
                metric_value={"x": 1},
                sample_size=-1,
                description="test",
            )

    def test_missing_metric_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            VerticalMetric(
                metric_value={"x": 1},  # type: ignore[call-arg]
                sample_size=1,
                description="test",
            )

    def test_missing_metric_value_raises(self) -> None:
        with pytest.raises(ValidationError):
            VerticalMetric(
                metric_name="test",  # type: ignore[call-arg]
                sample_size=1,
                description="test",
            )

    def test_metric_value_is_dict(self) -> None:
        vm = VerticalMetric(
            metric_name="test",
            metric_value={"nested": {"a": 1}, "list_val": [1, 2, 3]},
            sample_size=1,
            description="test",
        )
        assert isinstance(vm.metric_value, dict)
        assert "nested" in vm.metric_value

    def test_large_sample_size(self) -> None:
        vm = VerticalMetric(
            metric_name="test",
            metric_value={"x": 1},
            sample_size=10000,
            description="test",
        )
        assert vm.sample_size == 10000


# ---------------------------------------------------------------------------
# InsightsOutput
# ---------------------------------------------------------------------------
class TestInsightsOutput:
    def test_valid_full(self) -> None:
        output = InsightsOutput(
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
            audit_ids_included=["id1", "id2", "id3"],
            total_audits_in_vertical=5,
            summary="Enterprise Technology vertical shows strong search adoption.",
            is_first_in_vertical=False,
        )
        assert output.domain == "dell.com"
        assert output.vertical == "Enterprise Technology"
        assert len(output.metrics) == 3
        assert output.total_audits_in_vertical == 5
        assert output.is_first_in_vertical is False

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            InsightsOutput(
                domain="dell.com",
                vertical="Tech",
                bogus="nope",  # type: ignore[call-arg]
            )

    def test_defaults(self) -> None:
        output = InsightsOutput(
            domain="dell.com",
            vertical="Tech",
        )
        assert output.metrics == []
        assert output.audit_ids_included == []
        assert output.total_audits_in_vertical == 1
        assert output.summary == ""
        assert output.is_first_in_vertical is False

    def test_is_first_in_vertical_true(self) -> None:
        output = InsightsOutput(
            domain="dell.com",
            vertical="Tech",
            total_audits_in_vertical=1,
            is_first_in_vertical=True,
            summary="First audit in this vertical.",
            audit_ids_included=["id1"],
        )
        assert output.is_first_in_vertical is True
        assert output.total_audits_in_vertical == 1

    def test_empty_metrics_list(self) -> None:
        output = InsightsOutput(
            domain="dell.com",
            vertical="Tech",
            metrics=[],
        )
        assert output.metrics == []

    def test_multiple_metrics_different_sample_sizes(self) -> None:
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
                VerticalMetric(
                    metric_name="m2",
                    metric_value={"x": 2},
                    sample_size=10,
                    description="d2",
                ),
                VerticalMetric(
                    metric_name="m3",
                    metric_value={"x": 3},
                    sample_size=100,
                    description="d3",
                ),
            ],
        )
        assert output.metrics[0].sample_size == 1
        assert output.metrics[1].sample_size == 10
        assert output.metrics[2].sample_size == 100

    def test_total_audits_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            InsightsOutput(
                domain="dell.com",
                vertical="Tech",
                total_audits_in_vertical=0,
            )

    def test_missing_domain_raises(self) -> None:
        with pytest.raises(ValidationError):
            InsightsOutput(vertical="Tech")  # type: ignore[call-arg]

    def test_missing_vertical_raises(self) -> None:
        with pytest.raises(ValidationError):
            InsightsOutput(domain="dell.com")  # type: ignore[call-arg]

    def test_model_dump_roundtrip(self) -> None:
        output = InsightsOutput(
            domain="dell.com",
            vertical="Tech",
            metrics=[
                VerticalMetric(
                    metric_name="m1",
                    metric_value={"avg": 5.0},
                    sample_size=3,
                    description="desc",
                ),
            ],
            audit_ids_included=["a1"],
            total_audits_in_vertical=3,
            summary="Summary text.",
            is_first_in_vertical=False,
        )
        dumped = output.model_dump()
        restored = InsightsOutput.model_validate(dumped)
        assert restored.domain == output.domain
        assert restored.metrics[0].metric_name == "m1"
