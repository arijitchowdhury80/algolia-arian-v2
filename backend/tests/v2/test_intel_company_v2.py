"""Tests for intel-company v2 schemas — the seed module."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from core.playbook import PlaybookLoader
from core.types import ExecutionContextV2
from prism_platform.v2.modules.intel_company.config import INTEL_COMPANY_CONFIG
from prism_platform.v2.modules.intel_company.schemas import (
    CompanySeedOutput,
    CompetitorSeed,
    ExecutiveSeed,
)

PLAYBOOK_PATH = (
    Path(__file__).resolve().parents[2]
    / "prism_platform"
    / "v2"
    / "modules"
    / "intel_company"
    / "playbook.md"
)


class TestExecutiveSeed:
    """ExecutiveSeed — tightened executive model."""

    def test_valid_executive(self) -> None:
        e = ExecutiveSeed(
            full_name="Michael Dell",
            title="Chairman & CEO",
            role_classification="economic_buyer",
        )
        assert e.full_name == "Michael Dell"
        assert e.role_classification == "economic_buyer"

    def test_rejects_invalid_role(self) -> None:
        with pytest.raises(ValidationError):
            ExecutiveSeed(
                full_name="Test",
                title="CTO",
                role_classification="boss",  # not a valid Literal
            )

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            ExecutiveSeed(
                full_name="Test",
                title="CTO",
                role_classification="technical_buyer",
                favorite_food="pizza",  # extra="forbid"
            )


class TestCompetitorSeed:
    """CompetitorSeed — competitor reference from seed."""

    def test_valid_competitor(self) -> None:
        c = CompetitorSeed(
            company_name="HP Inc",
            domain="hp.com",
            why_competitor="Sells PCs and printers to same enterprise customers",
        )
        assert c.domain == "hp.com"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            CompetitorSeed(
                company_name="HP",
                domain="hp.com",
                why_competitor="Competes",
                secret="oops",  # extra="forbid"
            )


class TestCompanySeedOutput:
    """CompanySeedOutput — full output schema for intel-company v2."""

    def test_valid_full_output(self) -> None:
        output = CompanySeedOutput(
            legal_name="Dell Technologies Inc.",
            common_name="Dell",
            domain="dell.com",
            headquarters="Round Rock, Texas, USA",
            employee_count=133000,
            year_founded=1984,
            business_model=(
                "Dell Technologies designs, manufactures, and sells enterprise hardware, "
                "servers, storage solutions, and IT services to businesses and consumers."
            ),
            industry="Enterprise Technology",
            sub_vertical="Hardware & Infrastructure",
            is_public=True,
            ticker="DELL",
            executives=[
                ExecutiveSeed(
                    full_name="Michael Dell",
                    title="Chairman & CEO",
                    role_classification="economic_buyer",
                ),
            ],
            competitors=[
                CompetitorSeed(
                    company_name="HP Inc",
                    domain="hp.com",
                    why_competitor="Competes in PCs and printers",
                ),
            ],
        )
        assert output.legal_name == "Dell Technologies Inc."
        assert output.is_public is True
        assert len(output.executives) == 1
        assert len(output.competitors) == 1

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            CompanySeedOutput(
                legal_name="Test",
                common_name="Test",
                domain="test.com",
                headquarters="Somewhere",
                business_model="A" * 60,
                industry="Tech",
                executives=[],
                competitors=[],
                mystery_field="nope",  # extra="forbid"
            )

    def test_rejects_short_business_model(self) -> None:
        with pytest.raises(ValidationError):
            CompanySeedOutput(
                legal_name="Test",
                common_name="Test",
                domain="test.com",
                headquarters="Somewhere",
                business_model="Too short",  # min_length=50
                industry="Tech",
                executives=[],
                competitors=[],
            )

    def test_generates_valid_json_schema(self) -> None:
        schema = CompanySeedOutput.model_json_schema()
        assert "legal_name" in schema["properties"]
        assert "executives" in schema["properties"]
        assert schema["additionalProperties"] is False


class TestIntelCompanyWiring:
    """Test that config + playbook + schema wire together correctly."""

    def test_config_is_valid(self) -> None:
        assert INTEL_COMPANY_CONFIG.name == "intel-company"
        assert INTEL_COMPANY_CONFIG.layer == "seed"
        assert INTEL_COMPANY_CONFIG.cost_tier == "pro-search"

    def test_playbook_loads(self) -> None:
        loader = PlaybookLoader()
        meta, body = loader.load(PLAYBOOK_PATH)
        assert meta.name == "intel-company"
        assert "{domain}" in body

    def test_playbook_resolves(self) -> None:
        loader = PlaybookLoader()
        _, body = loader.load(PLAYBOOK_PATH)
        ctx = ExecutionContextV2(
            audit_id="test-001",
            account_domain="dell.com",
            company_name="Dell Technologies",
            industry="Enterprise Technology",
            is_public=True,
        )
        resolved = loader.resolve(body, ctx)
        assert "dell.com" in resolved
        assert "{domain}" not in resolved

    def test_schema_produces_json_schema_for_system_prompt(self) -> None:
        schema = CompanySeedOutput.model_json_schema()
        props = schema["properties"]
        assert "legal_name" in props
        assert "executives" in props
        assert "competitors" in props
        assert schema.get("additionalProperties") is False
