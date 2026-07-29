"""Tests for intel-hiring v2 module."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from prism_platform.v2.modules.intel_hiring.config import INTEL_HIRING_CONFIG
from prism_platform.v2.modules.intel_hiring.schemas import (
    HiringSignalSummary,
    HiringV2Output,
    OpenRoleV2,
)
from prism_platform.v2.playbook import PlaybookLoader
from prism_platform.v2.types import ExecutionContextV2

PLAYBOOK_PATH = (
    Path(__file__).parent.parent.parent / "prism_platform/v2/modules/intel_hiring/playbook.md"
)


class TestOpenRoleV2:
    def test_valid_role(self) -> None:
        r = OpenRoleV2(
            title="Senior Search Relevance Engineer",
            department="Engineering",
            location="Austin, TX",
            icp_tier="tier3_champion",
            search_related=True,
            build_vs_buy_signal="build",
            relevance_score=0.9,
        )
        assert r.icp_tier == "tier3_champion"
        assert r.search_related is True

    def test_relevance_score_clamped(self) -> None:
        with pytest.raises(ValidationError):
            OpenRoleV2(title="x", relevance_score=1.5)

    def test_is_frozen(self) -> None:
        r = OpenRoleV2(title="x")
        with pytest.raises(ValidationError):
            r.title = "changed"  # type: ignore[misc]

    def test_defaults_are_safe(self) -> None:
        r = OpenRoleV2(title="Marketing Manager")
        assert r.search_related is False
        assert r.icp_tier == "tier4_user"
        assert r.build_vs_buy_signal == "insufficient_data"
        assert r.relevance_score == 0.0

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            OpenRoleV2(title="x", bad="oops")  # type: ignore[call-arg]


class TestHiringSignalSummary:
    def test_valid_summary(self) -> None:
        s = HiringSignalSummary(
            total_open_roles=5,
            search_related_roles=3,
            tier1_economic_roles=1,
            build_vs_buy="build",
            build_vs_buy_rationale="3 Elasticsearch roles, no vendor mentions",
            hiring_signal_score=0.7,
        )
        assert s.hiring_signal_score == 0.7

    def test_score_bounds(self) -> None:
        with pytest.raises(ValidationError):
            HiringSignalSummary(hiring_signal_score=1.5)

    def test_is_frozen(self) -> None:
        s = HiringSignalSummary()
        with pytest.raises(ValidationError):
            s.hiring_signal_score = 0.9  # type: ignore[misc]


class TestHiringV2Output:
    def test_valid_output(self) -> None:
        out = HiringV2Output(
            domain="dell.com",
            signal_summary=HiringSignalSummary(
                total_open_roles=3,
                search_related_roles=2,
                hiring_signal_score=0.6,
                build_vs_buy="build",
            ),
            hiring_narrative="Dell is hiring 2 search engineers — building in-house.",
        )
        assert out.domain == "dell.com"
        assert out.signal_summary.search_related_roles == 2

    def test_narrative_required(self) -> None:
        with pytest.raises(ValidationError):
            HiringV2Output(
                domain="dell.com",
                signal_summary=HiringSignalSummary(),
            )

    def test_signal_summary_required(self) -> None:
        with pytest.raises(ValidationError):
            HiringV2Output(domain="dell.com", hiring_narrative="test")  # type: ignore[call-arg]

    def test_generates_json_schema(self) -> None:
        schema = HiringV2Output.model_json_schema()
        assert "open_roles" in schema["properties"]
        assert "signal_summary" in schema["properties"]


class TestIntelHiringConfig:
    def test_name(self) -> None:
        assert INTEL_HIRING_CONFIG.name == "intel-hiring"

    def test_version(self) -> None:
        assert INTEL_HIRING_CONFIG.version.startswith("2.")

    def test_layer(self) -> None:
        assert INTEL_HIRING_CONFIG.layer == "intelligence"


class TestIntelHiringPlaybook:
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
            account_domain="dell.com",
            company_name="Dell",
            industry="Tech",
        )
        _, body = loader.load(PLAYBOOK_PATH)
        resolved = loader.resolve(body, context)
        assert "dell.com" in resolved
