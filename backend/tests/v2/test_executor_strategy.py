"""Tests for ModuleExecutor execution strategy fan-out.

Tests the per-company / comparative / prospect-only strategy handling
added in Phase 2 (Decision 3 from architectural decisions doc).

Also tests FROM_CACHE upstream injection (Decision 6).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, ConfigDict

from prism_platform.v2.agent_api import AgentAPIClient, AgentAPIResponse
from prism_platform.v2.executor import ModuleExecutor
from prism_platform.v2.types import (
    CompetitorRef,
    ExecutionContextV2,
    ModuleConfig,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class SimpleOutput(BaseModel):
    """Minimal output schema for executor tests."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    domain: str = ""


def make_api_response(domain: str = "example.com") -> AgentAPIResponse:
    """Build a fake AgentAPIResponse with valid SimpleOutput JSON."""
    content = json.dumps({"summary": f"Research for {domain}", "domain": domain})
    return AgentAPIResponse(
        content=content,
        citations=["https://example.com/source"],
        usage_input_tokens=100,
        usage_output_tokens=50,
    )


@pytest.fixture()
def base_context() -> ExecutionContextV2:
    return ExecutionContextV2(
        audit_id="test-audit",
        account_domain="prospect.com",
        company_name="Prospect Co",
        industry="Retail",
        competitors=[
            CompetitorRef(name="Competitor A", domain="comp-a.com"),
            CompetitorRef(name="Competitor B", domain="comp-b.com"),
        ],
    )


@pytest.fixture()
def simple_config() -> ModuleConfig:
    return ModuleConfig(
        name="test-module",
        version="1.0.0",
        description="A test module",
        layer="intelligence",
        cost_tier="pro-search",
    )


@pytest.fixture()
def prospect_only_playbook(tmp_path: Path) -> Path:
    playbook = tmp_path / "playbook.md"
    playbook.write_text(
        "---\n"
        "name: test-prospect-only\n"
        "version: 1.0.0\n"
        "description: Test playbook\n"
        "execution_strategy: prospect-only\n"
        "---\n\n"
        "Research {domain} for the prospect.\n"
    )
    return playbook


@pytest.fixture()
def per_company_playbook(tmp_path: Path) -> Path:
    playbook = tmp_path / "playbook.md"
    playbook.write_text(
        "---\n"
        "name: test-per-company\n"
        "version: 1.0.0\n"
        "description: Test playbook per company\n"
        "execution_strategy: per-company\n"
        "---\n\n"
        "Research {domain} technology stack.\n"
    )
    return playbook


@pytest.fixture()
def comparative_playbook(tmp_path: Path) -> Path:
    playbook = tmp_path / "playbook.md"
    playbook.write_text(
        "---\n"
        "name: test-comparative\n"
        "version: 1.0.0\n"
        "description: Test comparative playbook\n"
        "execution_strategy: comparative\n"
        "---\n\n"
        "Compare {domain} against competitors: {competitors}.\n"
    )
    return playbook


@pytest.fixture()
def mock_api() -> AgentAPIClient:
    api = MagicMock(spec=AgentAPIClient)
    api.research = AsyncMock(return_value=make_api_response("prospect.com"))
    return api


# ---------------------------------------------------------------------------
# execute_strategy — prospect-only (single call, no fan-out)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prospect_only_makes_single_call(
    mock_api: AgentAPIClient,
    simple_config: ModuleConfig,
    base_context: ExecutionContextV2,
    prospect_only_playbook: Path,
) -> None:
    """prospect-only strategy makes exactly 1 API call regardless of competitor count."""
    executor = ModuleExecutor(mock_api)
    results = await executor.execute_strategy(
        config=simple_config,
        context=base_context,
        output_schema=SimpleOutput,
        playbook_path=prospect_only_playbook,
    )

    assert mock_api.research.call_count == 1  # type: ignore[attr-defined]
    assert len(results) == 1
    assert results[0].status == "success"


@pytest.mark.asyncio
async def test_prospect_only_uses_prospect_domain(
    mock_api: AgentAPIClient,
    simple_config: ModuleConfig,
    base_context: ExecutionContextV2,
    prospect_only_playbook: Path,
) -> None:
    """prospect-only strategy passes the prospect domain to the API."""
    executor = ModuleExecutor(mock_api)
    await executor.execute_strategy(
        config=simple_config,
        context=base_context,
        output_schema=SimpleOutput,
        playbook_path=prospect_only_playbook,
    )

    call_kwargs = mock_api.research.call_args  # type: ignore[attr-defined]
    user_prompt = call_kwargs.kwargs.get("user_prompt") or call_kwargs.args[1]
    assert "prospect.com" in user_prompt


# ---------------------------------------------------------------------------
# execute_strategy — per-company (fan-out: prospect + each competitor)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_per_company_fans_out_to_all_companies(
    mock_api: AgentAPIClient,
    simple_config: ModuleConfig,
    base_context: ExecutionContextV2,
    per_company_playbook: Path,
) -> None:
    """per-company strategy makes 1 call per company (prospect + N competitors)."""
    executor = ModuleExecutor(mock_api)
    results = await executor.execute_strategy(
        config=simple_config,
        context=base_context,
        output_schema=SimpleOutput,
        playbook_path=per_company_playbook,
    )

    # prospect + 2 competitors = 3 calls
    assert mock_api.research.call_count == 3  # type: ignore[attr-defined]
    assert len(results) == 3


@pytest.mark.asyncio
async def test_per_company_results_have_domain_context(
    simple_config: ModuleConfig,
    base_context: ExecutionContextV2,
    per_company_playbook: Path,
) -> None:
    """per-company fan-out results are tagged with the domain they were run for."""
    call_count = 0
    domains_called: list[str] = []

    async def fake_research(system_prompt: str, user_prompt: str, model: str) -> AgentAPIResponse:
        nonlocal call_count
        # Extract domain from user prompt
        if "prospect.com" in user_prompt:
            domains_called.append("prospect.com")
        elif "comp-a.com" in user_prompt:
            domains_called.append("comp-a.com")
        elif "comp-b.com" in user_prompt:
            domains_called.append("comp-b.com")
        call_count += 1
        # Return valid response for whichever domain was called
        domain = user_prompt.split()[1] if len(user_prompt.split()) > 1 else "unknown.com"
        return make_api_response(domain)

    api = MagicMock(spec=AgentAPIClient)
    api.research = AsyncMock(side_effect=fake_research)

    executor = ModuleExecutor(api)
    await executor.execute_strategy(
        config=simple_config,
        context=base_context,
        output_schema=SimpleOutput,
        playbook_path=per_company_playbook,
    )

    assert call_count == 3
    assert "prospect.com" in domains_called
    assert "comp-a.com" in domains_called
    assert "comp-b.com" in domains_called


@pytest.mark.asyncio
async def test_per_company_no_competitors_runs_prospect_only(
    mock_api: AgentAPIClient,
    simple_config: ModuleConfig,
    per_company_playbook: Path,
) -> None:
    """per-company with no competitors runs only for the prospect."""
    context = ExecutionContextV2(
        audit_id="test",
        account_domain="prospect.com",
        company_name="Prospect",
        industry="Tech",
        competitors=[],
    )
    executor = ModuleExecutor(mock_api)
    results = await executor.execute_strategy(
        config=simple_config,
        context=context,
        output_schema=SimpleOutput,
        playbook_path=per_company_playbook,
    )

    assert mock_api.research.call_count == 1  # type: ignore[attr-defined]
    assert len(results) == 1


# ---------------------------------------------------------------------------
# execute_strategy — comparative (single call with all companies in context)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_comparative_makes_single_call(
    mock_api: AgentAPIClient,
    simple_config: ModuleConfig,
    base_context: ExecutionContextV2,
    comparative_playbook: Path,
) -> None:
    """comparative strategy makes exactly 1 API call."""
    executor = ModuleExecutor(mock_api)
    results = await executor.execute_strategy(
        config=simple_config,
        context=base_context,
        output_schema=SimpleOutput,
        playbook_path=comparative_playbook,
    )

    assert mock_api.research.call_count == 1  # type: ignore[attr-defined]
    assert len(results) == 1


@pytest.mark.asyncio
async def test_comparative_injects_all_competitors(
    simple_config: ModuleConfig,
    base_context: ExecutionContextV2,
    comparative_playbook: Path,
) -> None:
    """comparative strategy injects {competitors} with all competitor domains."""
    captured_prompt: list[str] = []

    async def capture_research(
        system_prompt: str, user_prompt: str, model: str
    ) -> AgentAPIResponse:
        captured_prompt.append(user_prompt)
        return make_api_response("prospect.com")

    api = MagicMock(spec=AgentAPIClient)
    api.research = AsyncMock(side_effect=capture_research)

    executor = ModuleExecutor(api)
    await executor.execute_strategy(
        config=simple_config,
        context=base_context,
        output_schema=SimpleOutput,
        playbook_path=comparative_playbook,
    )

    assert len(captured_prompt) == 1
    prompt = captured_prompt[0]
    assert "comp-a.com" in prompt
    assert "comp-b.com" in prompt


# ---------------------------------------------------------------------------
# execute_strategy — upstream cache injection (Decision 6)
# ---------------------------------------------------------------------------


@pytest.fixture()
def cache_playbook(tmp_path: Path) -> Path:
    """Playbook that injects upstream module results."""
    playbook = tmp_path / "playbook.md"
    playbook.write_text(
        "---\n"
        "name: test-synthesis\n"
        "version: 1.0.0\n"
        "description: Synthesis from cache\n"
        "execution_strategy: prospect-only\n"
        "---\n\n"
        "Company: {company_name}\n"
        "Tech data: {upstream_intel_techstack}\n"
        "Financial data: {upstream_intel_financial_public}\n"
    )
    return playbook


@pytest.mark.asyncio
async def test_upstream_cache_injected_into_prompt(
    simple_config: ModuleConfig,
    cache_playbook: Path,
) -> None:
    """upstream_results from context are injected as {upstream_{module_name}} variables."""
    context = ExecutionContextV2(
        audit_id="test",
        account_domain="prospect.com",
        company_name="Prospect Co",
        industry="Retail",
        upstream_results={
            "intel-techstack": {"search_vendor": "Elasticsearch"},
            "intel-financial-public": {"revenue": 1000000.0},
        },
    )

    captured_prompt: list[str] = []

    async def capture_research(
        system_prompt: str, user_prompt: str, model: str
    ) -> AgentAPIResponse:
        captured_prompt.append(user_prompt)
        return make_api_response("prospect.com")

    api = MagicMock(spec=AgentAPIClient)
    api.research = AsyncMock(side_effect=capture_research)

    executor = ModuleExecutor(api)
    await executor.execute_strategy(
        config=simple_config,
        context=context,
        output_schema=SimpleOutput,
        playbook_path=cache_playbook,
    )

    assert len(captured_prompt) == 1
    prompt = captured_prompt[0]
    # Upstream intel-techstack data should be injected
    assert "Elasticsearch" in prompt
    # Upstream financial data should be injected
    assert "1000000" in prompt
