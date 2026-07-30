"""Shared fixtures for v2 tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from core.types import ExecutionContextV2, ModuleConfig


@pytest.fixture
def sample_context() -> ExecutionContextV2:
    return ExecutionContextV2(
        audit_id=str(uuid4()),
        account_domain="dell.com",
        company_name="Dell Technologies",
        industry="Enterprise Technology",
        is_public=True,
        ticker="DELL",
    )


@pytest.fixture
def sample_config() -> ModuleConfig:
    return ModuleConfig(
        name="intel-company",
        version="2.0.0",
        description="Company seed intelligence",
        layer="seed",
        cost_tier="pro-search",
        timeout_seconds=120,
        max_retries=2,
        cache_ttl_days=180,
        api_clients=[],
        composes=[],
    )
