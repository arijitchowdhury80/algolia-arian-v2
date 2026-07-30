"""A research module that returns no sources must not report clean success.

Found live on a Gemini-backed dell.com run: Google-Search grounding is
non-deterministic. 9 of 13 modules came back with zero citations, and the same
modules returned 10 and 2 citations when re-run minutes later. The old executor
stamped those claims "no-citation" and still returned status="success", so
completely unsourced audit data was indistinguishable from sourced data.

Policy pinned here: retry the research call once, and if sources are still
absent, downgrade to "partial" with an explicit error. The output is kept —
it may well be correct — but nothing downstream may mistake it for evidenced.
Modules that legitimately produce no citations (query generation, for instance)
opt out with requires_citations=False.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel, ConfigDict, Field

from core.agent_api import AgentAPIResponse
from core.executor import ModuleExecutor
from core.types import ExecutionContextV2, ModuleConfig


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legal_name: str = Field(description="Company legal name")


_CONTENT = '{"legal_name": "Dell Technologies"}'

_UNSOURCED = AgentAPIResponse(content=_CONTENT, citations=[])
_SOURCED = AgentAPIResponse(content=_CONTENT, citations=["https://www.dell.com/about"])

_PLAYBOOK = """---
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


@pytest.fixture
def playbook_dir(tmp_path: Path) -> Path:
    (tmp_path / "playbook.md").write_text(_PLAYBOOK)
    return tmp_path


def _config(requires_citations: bool = True) -> ModuleConfig:
    return ModuleConfig(
        name="intel-company",
        version="2.0.0",
        description="Company seed intelligence",
        layer="seed",
        cost_tier="pro-search",
        requires_citations=requires_citations,
    )


@pytest.fixture
def context() -> ExecutionContextV2:
    return ExecutionContextV2(audit_id="test-001", account_domain="dell.com", company_name="Dell")


def test_requires_citations_defaults_to_true() -> None:
    """Evidence is the default expectation; opting out must be deliberate."""
    assert _config().requires_citations is True


@pytest.mark.asyncio
async def test_no_citations_triggers_one_retry_and_succeeds_if_sources_appear(
    context: ExecutionContextV2, playbook_dir: Path
) -> None:
    api = AsyncMock()
    api.research = AsyncMock(side_effect=[_UNSOURCED, _SOURCED])
    result = await ModuleExecutor(agent_api=api).execute(
        config=_config(),
        context=context,
        output_schema=_Out,
        playbook_path=playbook_dir / "playbook.md",
    )
    assert api.research.await_count == 2
    assert result.status == "success"
    assert result.citations == ["https://www.dell.com/about"]
    assert result.llm_calls == 2


@pytest.mark.asyncio
async def test_still_no_citations_after_retry_is_partial_not_success(
    context: ExecutionContextV2, playbook_dir: Path
) -> None:
    api = AsyncMock()
    api.research = AsyncMock(side_effect=[_UNSOURCED, _UNSOURCED])
    result = await ModuleExecutor(agent_api=api).execute(
        config=_config(),
        context=context,
        output_schema=_Out,
        playbook_path=playbook_dir / "playbook.md",
    )
    assert api.research.await_count == 2
    assert result.status == "partial"
    assert result.citations == []
    assert any("no sources" in e.lower() for e in result.errors), result.errors
    # The data is preserved — it is unverified, not discarded.
    assert result.output["legal_name"] == "Dell Technologies"


@pytest.mark.asyncio
async def test_sourced_first_call_never_retries(
    context: ExecutionContextV2, playbook_dir: Path
) -> None:
    api = AsyncMock()
    api.research = AsyncMock(return_value=_SOURCED)
    result = await ModuleExecutor(agent_api=api).execute(
        config=_config(),
        context=context,
        output_schema=_Out,
        playbook_path=playbook_dir / "playbook.md",
    )
    assert api.research.await_count == 1
    assert result.status == "success"
    assert result.llm_calls == 1


@pytest.mark.asyncio
async def test_opted_out_module_passes_with_no_citations_and_no_retry(
    context: ExecutionContextV2, playbook_dir: Path
) -> None:
    """intel-queries generates test queries; there is nothing to cite."""
    api = AsyncMock()
    api.research = AsyncMock(return_value=_UNSOURCED)
    result = await ModuleExecutor(agent_api=api).execute(
        config=_config(requires_citations=False),
        context=context,
        output_schema=_Out,
        playbook_path=playbook_dir / "playbook.md",
    )
    assert api.research.await_count == 1
    assert result.status == "success"
    assert result.errors == []
