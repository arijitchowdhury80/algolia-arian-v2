"""Tests for v2 core types — Finding, ModuleConfig, ExecutionContextV2, ClaimRegistryEntry."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.types import (
    ClaimRegistryEntry,
    ExecutionContextV2,
    Finding,
    FindingCategory,
    ModuleConfig,
)


class TestFinding:
    """Finding model — the immutable research unit."""

    def test_valid_finding(self) -> None:
        f = Finding(
            id="f-001",
            company="Dell Technologies",
            category=FindingCategory.COMPANY_OVERVIEW,
            statement="Dell reported $88.4B revenue in FY2025",
            source_url="https://investors.delltechnologies.com/annual-report-2025",
            confidence="high",
            provider="perplexity",
        )
        assert f.company == "Dell Technologies"
        assert f.category == FindingCategory.COMPANY_OVERVIEW
        assert f.confidence == "high"

    def test_finding_rejects_missing_source_url(self) -> None:
        with pytest.raises(ValidationError):
            Finding(
                id="f-002",
                company="Dell",
                category=FindingCategory.REVENUE,
                statement="Dell is big",
                source_url="",  # empty string should fail min_length=1
                confidence="high",
                provider="perplexity",
            )

    def test_finding_rejects_invalid_confidence(self) -> None:
        with pytest.raises(ValidationError):
            Finding(
                id="f-003",
                company="Dell",
                category=FindingCategory.REVENUE,
                statement="test",
                source_url="https://example.com",
                confidence="very high",  # not a valid Literal
                provider="perplexity",
            )

    def test_finding_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            Finding(
                id="f-004",
                company="Dell",
                category=FindingCategory.REVENUE,
                statement="test",
                source_url="https://example.com",
                confidence="high",
                provider="perplexity",
                invented_field="oops",  # extra="forbid"
            )

    def test_finding_is_frozen(self) -> None:
        f = Finding(
            id="f-005",
            company="Dell",
            category=FindingCategory.REVENUE,
            statement="test",
            source_url="https://example.com",
            confidence="high",
            provider="perplexity",
        )
        with pytest.raises(ValidationError):
            f.statement = "mutated"  # frozen=True


class TestModuleConfig:
    """ModuleConfig — the agent's identity card."""

    def test_valid_config(self) -> None:
        cfg = ModuleConfig(
            name="intel-company",
            version="2.0.0",
            description="Company seed intelligence",
            layer="intelligence",
            cost_tier="pro-search",
            timeout_seconds=120,
            max_retries=2,
            cache_ttl_days=180,
            api_clients=[],
            composes=[],
        )
        assert cfg.name == "intel-company"
        assert cfg.cost_tier == "pro-search"

    def test_config_rejects_invalid_layer(self) -> None:
        with pytest.raises(ValidationError):
            ModuleConfig(
                name="test",
                version="1.0.0",
                description="test",
                layer="invented",  # not a valid Literal
                cost_tier="pro-search",
                timeout_seconds=60,
                max_retries=1,
                cache_ttl_days=30,
                api_clients=[],
                composes=[],
            )


class TestExecutionContextV2:
    """ExecutionContextV2 — the runtime context passed to every module."""

    def test_valid_context(self) -> None:
        ctx = ExecutionContextV2(
            audit_id=str(uuid4()),
            account_domain="dell.com",
            company_name="Dell Technologies",
            industry="Enterprise Technology",
            is_public=True,
            ticker="DELL",
        )
        assert ctx.account_domain == "dell.com"
        assert ctx.is_public is True

    def test_context_defaults(self) -> None:
        ctx = ExecutionContextV2(
            audit_id=str(uuid4()),
            account_domain="startup.io",
            company_name="Startup Inc",
            industry="SaaS",
        )
        assert ctx.is_public is False
        assert ctx.ticker is None
        assert ctx.competitors == []
        assert ctx.executives == []
        assert ctx.cluster_findings == {}


class TestClaimRegistryEntry:
    """ClaimRegistryEntry — auto-generated from module output for factcheck."""

    def test_valid_claim(self) -> None:
        c = ClaimRegistryEntry(
            statement="Dell reported $88.4B revenue in FY2025",
            source_url="https://investors.delltechnologies.com",
            evidence_tier="VERIFIED",
            module_origin="intel-company",
            field_path="revenue_estimate",
        )
        assert c.evidence_tier == "VERIFIED"
        assert c.module_origin == "intel-company"
