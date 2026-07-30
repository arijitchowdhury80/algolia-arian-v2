"""An empty provider response must be retried and reported as what it is.

Found live: Gemini answered a dell.com intel-company call with HTTP 200,
finishReason STOP, zero content parts and no candidatesTokenCount — it emitted
nothing and stopped cleanly. The executor passed that empty string to
json.loads and reported "JSON parse failed: Expecting value: line 1 column 1",
which points the reader at the parser instead of at the provider. The same
module had succeeded minutes earlier, so the condition is intermittent and
worth one retry.

Also pinned here: when a retry happens, keep the better of the two responses.
The first version discarded a 22k-character retry in favour of an unusable
1.4k first attempt purely because neither carried citations.
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


_GOOD = '{"legal_name": "Dell Technologies"}'
_OTHER = '{"legal_name": "Dell Inc"}'

_EMPTY = AgentAPIResponse(content="", citations=[])
_WHITESPACE = AgentAPIResponse(content="   \n ", citations=[])
_SOURCED = AgentAPIResponse(content=_GOOD, citations=["https://www.dell.com/about"])
_UNSOURCED = AgentAPIResponse(content=_OTHER, citations=[])

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
def playbook(tmp_path: Path) -> Path:
    p = tmp_path / "playbook.md"
    p.write_text(_PLAYBOOK)
    return p


@pytest.fixture
def config() -> ModuleConfig:
    return ModuleConfig(
        name="intel-company",
        version="2.0.0",
        description="Company seed intelligence",
        layer="seed",
        cost_tier="pro-search",
    )


@pytest.fixture
def context() -> ExecutionContextV2:
    return ExecutionContextV2(audit_id="test-001", account_domain="dell.com", company_name="Dell")


async def _run(api: AsyncMock, config: ModuleConfig, context: ExecutionContextV2, pb: Path):
    return await ModuleExecutor(agent_api=api).execute(
        config=config, context=context, output_schema=_Out, playbook_path=pb
    )


@pytest.mark.asyncio
async def test_empty_response_is_retried_and_recovers(
    config: ModuleConfig, context: ExecutionContextV2, playbook: Path
) -> None:
    api = AsyncMock()
    api.research = AsyncMock(side_effect=[_EMPTY, _SOURCED])
    result = await _run(api, config, context, playbook)
    assert api.research.await_count == 2
    assert result.status == "success"
    assert result.output["legal_name"] == "Dell Technologies"


@pytest.mark.asyncio
async def test_two_empty_responses_report_the_provider_not_the_parser(
    config: ModuleConfig, context: ExecutionContextV2, playbook: Path
) -> None:
    api = AsyncMock()
    api.research = AsyncMock(side_effect=[_EMPTY, _EMPTY])
    result = await _run(api, config, context, playbook)
    assert result.status == "failed"
    joined = " ".join(result.errors).lower()
    assert "empty response" in joined, result.errors
    assert "json parse" not in joined, "must not blame the parser for a provider problem"


@pytest.mark.asyncio
async def test_whitespace_only_counts_as_empty(
    config: ModuleConfig, context: ExecutionContextV2, playbook: Path
) -> None:
    api = AsyncMock()
    api.research = AsyncMock(side_effect=[_WHITESPACE, _WHITESPACE])
    result = await _run(api, config, context, playbook)
    assert result.status == "failed"
    assert "empty response" in " ".join(result.errors).lower()


@pytest.mark.asyncio
async def test_usable_retry_is_kept_when_first_attempt_is_empty(
    config: ModuleConfig, context: ExecutionContextV2, playbook: Path
) -> None:
    """Neither response has citations, but only one is usable at all."""
    api = AsyncMock()
    api.research = AsyncMock(side_effect=[_EMPTY, _UNSOURCED])
    result = await _run(api, config, context, playbook)
    assert result.status == "partial"  # usable but unsourced
    assert result.output["legal_name"] == "Dell Inc"


def test_unparseable_json_ranks_below_a_clean_answer() -> None:
    """Malformed JSON is as intermittent as an empty answer; rank it unusable.

    Observed across three dell.com runs: a different set of modules failed each
    time with mid-document errors ("Expecting ',' delimiter: line 55"), and the
    same prompt parsed cleanly on a later call.
    """
    broken = AgentAPIResponse(content='{"legal_name": "Dell", ', citations=["https://x"])
    assert ModuleExecutor._usability(broken, requires_citations=True) == 0
    assert ModuleExecutor._usability(_SOURCED, requires_citations=True) == 2


@pytest.mark.asyncio
async def test_broken_json_then_good_json_recovers(
    config: ModuleConfig, context: ExecutionContextV2, playbook: Path
) -> None:
    api = AsyncMock()
    broken = AgentAPIResponse(content='{"legal_name": "Dell", ', citations=["https://x"])
    api.research = AsyncMock(side_effect=[broken, _SOURCED])
    result = await _run(api, config, context, playbook)
    assert api.research.await_count == 2
    assert result.status == "success"
    assert result.output["legal_name"] == "Dell Technologies"


@pytest.mark.asyncio
async def test_broken_json_twice_still_reports_a_parse_error(
    config: ModuleConfig, context: ExecutionContextV2, playbook: Path
) -> None:
    """Non-empty but unparseable must read as a JSON fault, not an empty response."""
    api = AsyncMock()
    broken = AgentAPIResponse(content='{"legal_name": "Dell", ', citations=["https://x"])
    api.research = AsyncMock(side_effect=[broken, broken])
    result = await _run(api, config, context, playbook)
    assert result.status == "failed"
    joined = " ".join(result.errors).lower()
    assert "json parse failed" in joined, result.errors
    assert "empty response" not in joined


@pytest.mark.asyncio
async def test_sourced_response_wins_over_longer_unsourced_one(
    config: ModuleConfig, context: ExecutionContextV2, playbook: Path
) -> None:
    api = AsyncMock()
    api.research = AsyncMock(side_effect=[_UNSOURCED, _SOURCED])
    result = await _run(api, config, context, playbook)
    assert result.status == "success"
    assert result.citations == ["https://www.dell.com/about"]
