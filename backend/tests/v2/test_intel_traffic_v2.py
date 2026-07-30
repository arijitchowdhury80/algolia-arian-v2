"""Tests for intel-traffic v2 module."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from core.playbook import PlaybookLoader
from core.types import CompetitorRef, ExecutionContextV2
from prism_platform.v2.modules.intel_traffic.config import INTEL_TRAFFIC_CONFIG
from prism_platform.v2.modules.intel_traffic.schemas import (
    CompetitorTrafficSummary,
    TrafficSourceV2,
    TrafficV2Output,
)

PLAYBOOK_PATH = (
    Path(__file__).parent.parent.parent / "prism_platform/v2/modules/intel_traffic/playbook.md"
)


class TestTrafficV2Output:
    def test_valid_minimal_output(self) -> None:
        out = TrafficV2Output(
            domain="dell.com",
            monthly_visits_estimate="5M-10M",
            traffic_trend="stable",
            google_trends_direction="stable",
            comparative_narrative="Dell has stable traffic compared to peers.",
        )
        assert out.domain == "dell.com"

    def test_traffic_trend_literals(self) -> None:
        for trend in ("growing", "stable", "declining", "unknown"):
            TrafficV2Output(
                domain="x.com",
                monthly_visits_estimate="1M",
                traffic_trend=trend,  # type: ignore[arg-type]
                google_trends_direction="stable",
                comparative_narrative="narrative",
            )

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            TrafficV2Output(
                domain="x.com",
                monthly_visits_estimate="1M",
                traffic_trend="stable",
                google_trends_direction="stable",
                comparative_narrative="narrative",
                bad_field="oops",  # type: ignore[call-arg]
            )

    def test_competitor_summaries_populated(self) -> None:
        comp = CompetitorTrafficSummary(
            domain="hp.com",
            monthly_visits_estimate="50M+",
            traffic_trend="growing",
            primary_traffic_source="organic_search",
            evidence_url="https://similarweb.com/hp.com",
        )
        out = TrafficV2Output(
            domain="dell.com",
            monthly_visits_estimate="10M-20M",
            traffic_trend="stable",
            google_trends_direction="stable",
            comparative_narrative="Dell vs HP traffic analysis.",
            competitor_summaries=[comp],
        )
        assert len(out.competitor_summaries) == 1
        assert out.competitor_summaries[0].domain == "hp.com"

    def test_traffic_source_is_frozen(self) -> None:
        src = TrafficSourceV2(source_type="organic_search", share_pct=45.0)
        with pytest.raises(ValidationError):
            src.share_pct = 50.0  # type: ignore[misc]


class TestIntelTrafficConfig:
    def test_name(self) -> None:
        assert INTEL_TRAFFIC_CONFIG.name == "intel-traffic"

    def test_version(self) -> None:
        assert INTEL_TRAFFIC_CONFIG.version.startswith("2.")

    def test_layer_is_intelligence(self) -> None:
        assert INTEL_TRAFFIC_CONFIG.layer == "intelligence"

    def test_cost_tier(self) -> None:
        assert INTEL_TRAFFIC_CONFIG.cost_tier == "pro-search"


class TestIntelTrafficPlaybook:
    def test_playbook_exists(self) -> None:
        assert PLAYBOOK_PATH.exists()

    def test_execution_strategy_is_comparative(self) -> None:
        loader = PlaybookLoader()
        meta, _ = loader.load(PLAYBOOK_PATH)
        assert meta.execution_strategy == "comparative"

    def test_playbook_resolves_with_competitors(self) -> None:
        loader = PlaybookLoader()
        context = ExecutionContextV2(
            audit_id="t",
            account_domain="dell.com",
            company_name="Dell",
            industry="Tech",
            competitors=[
                CompetitorRef(name="HP", domain="hp.com"),
            ],
        )
        _, body = loader.load(PLAYBOOK_PATH)
        resolved = loader.resolve(body, context)
        assert "dell.com" in resolved
        assert "hp.com" in resolved
