"""Tests for intel-techstack v2 module.

Validates:
- TechStackV2Output schema correctness
- Config layer/cost_tier/name
- Playbook loads and resolves {domain}
- Execution strategy is per-company (fan-out)
- golden_angle_competitors field (Algolia displacement signal)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from core.playbook import PlaybookLoader
from core.types import ExecutionContextV2
from prism_platform.v2.modules.intel_techstack.config import INTEL_TECHSTACK_CONFIG
from prism_platform.v2.modules.intel_techstack.schemas import (
    SearchVendorV2,
    TechStackV2Output,
)

PLAYBOOK_PATH = (
    Path(__file__).parent.parent.parent / "prism_platform/v2/modules/intel_techstack/playbook.md"
)


# ---------------------------------------------------------------------------
# SearchVendorV2 schema
# ---------------------------------------------------------------------------


class TestSearchVendorV2:
    def test_valid_vendor(self) -> None:
        v = SearchVendorV2(
            name="Elasticsearch",
            status="ACTIVE",
            detection_method="builtwith",
            evidence_summary="BuiltWith reports Elasticsearch 8.x",
            evidence_url="https://builtwith.com/example.com",
        )
        assert v.name == "Elasticsearch"
        assert v.status == "ACTIVE"

    def test_status_literals(self) -> None:
        for status in ("ACTIVE", "TAG_ONLY", "REMOVED", "UNDETECTED"):
            SearchVendorV2(
                name="X",
                status=status,  # type: ignore[arg-type]
                detection_method="research",
                evidence_summary="test",
                evidence_url="https://example.com",
            )

    def test_rejects_invalid_status(self) -> None:
        with pytest.raises(ValidationError):
            SearchVendorV2(
                name="X",
                status="MAYBE",  # type: ignore[arg-type]
                detection_method="research",
                evidence_summary="test",
                evidence_url="https://example.com",
            )

    def test_is_frozen(self) -> None:
        v = SearchVendorV2(
            name="Algolia",
            status="ACTIVE",
            detection_method="builtwith",
            evidence_summary="test",
            evidence_url="https://builtwith.com",
        )
        with pytest.raises(ValidationError):
            v.name = "Elasticsearch"  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            SearchVendorV2(
                name="X",
                status="ACTIVE",
                detection_method="builtwith",
                evidence_summary="test",
                evidence_url="https://example.com",
                unknown_field="oops",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# TechStackV2Output schema
# ---------------------------------------------------------------------------


class TestTechStackV2Output:
    def test_valid_minimal_output(self) -> None:
        out = TechStackV2Output(
            domain="dell.com",
            search_vendor=None,
            ecommerce_platform=None,
            analytics=[],
            all_detected_technologies=[],
            golden_angle_competitors=[],
            is_algolia_customer=False,
            tech_stack_narrative="No search vendor detected.",
        )
        assert out.domain == "dell.com"
        assert out.is_algolia_customer is False

    def test_valid_full_output(self) -> None:
        vendor = SearchVendorV2(
            name="Elasticsearch",
            status="ACTIVE",
            detection_method="builtwith",
            evidence_summary="BuiltWith confirms Elasticsearch",
            evidence_url="https://builtwith.com/dell.com",
        )
        out = TechStackV2Output(
            domain="dell.com",
            search_vendor=vendor,
            ecommerce_platform="Salesforce Commerce Cloud",
            analytics=["Google Analytics 4", "Adobe Analytics"],
            all_detected_technologies=["Elasticsearch", "Cloudflare", "React"],
            golden_angle_competitors=["hp.com"],
            is_algolia_customer=False,
            tech_stack_narrative=(
                "Dell uses Elasticsearch for site search, detected via BuiltWith. "
                "Competitor HP uses Algolia (golden angle)."
            ),
        )
        assert out.search_vendor is not None
        assert out.search_vendor.name == "Elasticsearch"
        assert "hp.com" in out.golden_angle_competitors

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            TechStackV2Output(
                domain="dell.com",
                unknown="bad",  # type: ignore[call-arg]
            )

    def test_narrative_required(self) -> None:
        with pytest.raises(ValidationError):
            TechStackV2Output(domain="dell.com")  # type: ignore[call-arg]

    def test_generates_json_schema(self) -> None:
        schema = TechStackV2Output.model_json_schema()
        assert "properties" in schema
        assert "golden_angle_competitors" in schema["properties"]
        assert "search_vendor" in schema["properties"]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestIntelTechstackConfig:
    def test_name(self) -> None:
        assert INTEL_TECHSTACK_CONFIG.name == "intel-techstack"

    def test_version(self) -> None:
        assert INTEL_TECHSTACK_CONFIG.version.startswith("2.")

    def test_layer_is_intelligence(self) -> None:
        assert INTEL_TECHSTACK_CONFIG.layer == "intelligence"

    def test_cost_tier_is_pro_search(self) -> None:
        # BuiltWith is structured API; cluster-c handles deep research
        assert INTEL_TECHSTACK_CONFIG.cost_tier == "pro-search"


# ---------------------------------------------------------------------------
# Playbook wiring
# ---------------------------------------------------------------------------


class TestIntelTechstackPlaybook:
    def test_playbook_file_exists(self) -> None:
        assert PLAYBOOK_PATH.exists(), f"Playbook not found at {PLAYBOOK_PATH}"

    def test_playbook_loads(self) -> None:
        loader = PlaybookLoader()
        meta, body = loader.load(PLAYBOOK_PATH)
        assert meta.name == "intel-techstack"
        assert len(body) > 100

    def test_playbook_execution_strategy_is_per_company(self) -> None:
        loader = PlaybookLoader()
        meta, _ = loader.load(PLAYBOOK_PATH)
        assert meta.execution_strategy == "per-company"

    def test_playbook_resolves_domain(self) -> None:
        loader = PlaybookLoader()
        context = ExecutionContextV2(
            audit_id="test",
            account_domain="dell.com",
            company_name="Dell Technologies",
            industry="Enterprise Technology",
        )
        _, body = loader.load(PLAYBOOK_PATH)
        resolved = loader.resolve(body, context)
        assert "dell.com" in resolved

    def test_playbook_contains_search_vendor_detection_instructions(self) -> None:
        loader = PlaybookLoader()
        _, body = loader.load(PLAYBOOK_PATH)
        body_lower = body.lower()
        assert "search" in body_lower
        assert "builtwith" in body_lower
