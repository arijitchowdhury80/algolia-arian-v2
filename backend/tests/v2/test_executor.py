"""Tests for ModuleExecutor — the generic module harness."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel, ConfigDict, Field

from core.agent_api import AgentAPIResponse
from core.executor import ModuleExecutor, ModuleExecutorResult
from core.types import ExecutionContextV2, ModuleConfig


class FakeOutput(BaseModel):
    """Minimal output schema for testing."""

    model_config = ConfigDict(extra="forbid")

    legal_name: str = Field(description="Company legal name")
    domain: str = Field(description="Website domain")
    employee_count: int | None = Field(default=None, description="Employee count")


FAKE_API_RESPONSE = AgentAPIResponse(
    content='{"legal_name": "Dell Technologies", "domain": "dell.com", "employee_count": 133000}',
    citations=["https://www.dell.com/about", "https://investors.delltechnologies.com"],
    usage_input_tokens=150,
    usage_output_tokens=200,
)


FAKE_PLAYBOOK = """---
name: intel-company
version: 2.0.0
description: Test
cost_tier: pro-search
execution_strategy: per-company
composes: []
---

## Objective
Research {domain}.
"""


class TestModuleExecutor:
    """ModuleExecutor — generic module harness."""

    @pytest.fixture
    def playbook_dir(self, tmp_path: Path) -> Path:
        pb = tmp_path / "playbook.md"
        pb.write_text(FAKE_PLAYBOOK)
        return tmp_path

    @pytest.fixture
    def executor(self) -> ModuleExecutor:
        mock_api = AsyncMock()
        mock_api.research = AsyncMock(return_value=FAKE_API_RESPONSE)
        return ModuleExecutor(agent_api=mock_api)

    @pytest.mark.asyncio
    async def test_execute_returns_validated_output(
        self,
        executor: ModuleExecutor,
        sample_config: ModuleConfig,
        sample_context: ExecutionContextV2,
        playbook_dir: Path,
    ) -> None:
        result = await executor.execute(
            config=sample_config,
            context=sample_context,
            output_schema=FakeOutput,
            playbook_path=playbook_dir / "playbook.md",
        )
        assert isinstance(result, ModuleExecutorResult)
        assert result.status == "success"
        assert result.output["legal_name"] == "Dell Technologies"
        assert result.output["domain"] == "dell.com"
        assert result.output["employee_count"] == 133000

    @pytest.mark.asyncio
    async def test_execute_populates_claims(
        self,
        executor: ModuleExecutor,
        sample_config: ModuleConfig,
        sample_context: ExecutionContextV2,
        playbook_dir: Path,
    ) -> None:
        result = await executor.execute(
            config=sample_config,
            context=sample_context,
            output_schema=FakeOutput,
            playbook_path=playbook_dir / "playbook.md",
        )
        assert len(result.claims) > 0
        assert all(c.module_origin == "intel-company" for c in result.claims)

    @pytest.mark.asyncio
    async def test_execute_records_cost(
        self,
        executor: ModuleExecutor,
        sample_config: ModuleConfig,
        sample_context: ExecutionContextV2,
        playbook_dir: Path,
    ) -> None:
        result = await executor.execute(
            config=sample_config,
            context=sample_context,
            output_schema=FakeOutput,
            playbook_path=playbook_dir / "playbook.md",
        )
        assert result.llm_calls == 1
        assert result.input_tokens == 150
        assert result.output_tokens == 200

    @pytest.mark.asyncio
    async def test_execute_handles_invalid_json(
        self,
        sample_config: ModuleConfig,
        sample_context: ExecutionContextV2,
        playbook_dir: Path,
    ) -> None:
        bad_response = AgentAPIResponse(
            content="not valid json at all",
            citations=[],
            usage_input_tokens=10,
            usage_output_tokens=20,
        )
        mock_api = AsyncMock()
        mock_api.research = AsyncMock(return_value=bad_response)
        executor = ModuleExecutor(agent_api=mock_api)

        result = await executor.execute(
            config=sample_config,
            context=sample_context,
            output_schema=FakeOutput,
            playbook_path=playbook_dir / "playbook.md",
        )
        assert result.status == "failed"
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_handles_schema_violation(
        self,
        sample_config: ModuleConfig,
        sample_context: ExecutionContextV2,
        playbook_dir: Path,
    ) -> None:
        # Missing required field 'legal_name'
        bad_response = AgentAPIResponse(
            content='{"domain": "dell.com"}',
            citations=[],
            usage_input_tokens=10,
            usage_output_tokens=20,
        )
        mock_api = AsyncMock()
        mock_api.research = AsyncMock(return_value=bad_response)
        executor = ModuleExecutor(agent_api=mock_api)

        result = await executor.execute(
            config=sample_config,
            context=sample_context,
            output_schema=FakeOutput,
            playbook_path=playbook_dir / "playbook.md",
        )
        assert result.status == "failed"
        assert any("legal_name" in e for e in result.errors)
