# PRISM v2.0 — Unified Module Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the agentic module pattern (config + playbook + schema + generic executor) by building the core infrastructure and intel-company v2.0 as proof of concept, then design cluster playbooks and domain schemas for Phase 2.

**Architecture:** Every module becomes an agent — config.py is the system prompt, playbook.md is the user prompt, schemas.py is the output contract, and a generic ModuleExecutor is the harness. Research happens via Perplexity API calls with structured output. The v2 code lives in `prism_platform/v2/` alongside the existing v1 code — no v1 breakage.

**Tech Stack:** Python 3.12, Pydantic v2 (strict mode, extra="forbid"), httpx (async HTTP), structlog, Perplexity Sonar API, pytest-asyncio

**Status:** Phase 1 (Prove the Pattern). Cluster playbooks and domain schemas are Phase 2 design artifacts included here for completeness.

**Open architectural questions (to be resolved and appended):**
- Merge strategy implementation details per module
- Rate limiter / priority queue for Agent API
- Citation validation implementation specifics
- AgentAPIClient streaming vs batch
- Cluster playbook → Finding extraction pipeline details
- Private company financial waterfall simplification with dual-provider research

---

## File Structure

All v2 code lives under `prism_platform/v2/` to avoid disturbing v1:

```
prism_platform/v2/
├── __init__.py
├── types.py                          # Finding, ModuleConfig, ExecutionContextV2, ClaimRegistryEntry
├── agent_api.py                      # AgentAPIClient — Perplexity wrapper
├── playbook.py                       # PlaybookLoader — .md → resolved prompt
├── executor.py                       # ModuleExecutor — generic harness
├── modules/
│   ├── __init__.py
│   └── intel_company/
│       ├── __init__.py
│       ├── config.py                 # ModuleConfig instance
│       ├── playbook.md               # Research instructions with {domain} variable
│       └── schemas.py                # CompanySeedOutput (tightened, extra="forbid")
└── clusters/                         # Phase 2 design artifacts
    ├── cluster_a_company.md          # Company & Competitive Landscape
    ├── cluster_b_financial.md        # Financial & Investor Intelligence
    ├── cluster_c_technology.md       # Technology & Digital Experience
    ├── cluster_d_people.md           # People & Signals
    └── cluster_e_buying_signals.md   # Buying Signals & Intent

tests/v2/
├── __init__.py
├── conftest.py                       # Shared fixtures (fake Perplexity responses, contexts)
├── test_types.py                     # Finding, ModuleConfig, ExecutionContextV2
├── test_agent_api.py                 # AgentAPIClient with mocked HTTP
├── test_playbook.py                  # PlaybookLoader
├── test_executor.py                  # ModuleExecutor end-to-end with mocks
└── test_intel_company_v2.py          # intel-company v2 schemas + config
```

---

## Task 1: v2 Core Types

**Files:**
- Create: `prism_platform/v2/__init__.py`
- Create: `prism_platform/v2/types.py`
- Create: `tests/v2/__init__.py`
- Create: `tests/v2/test_types.py`

These are the foundational data contracts for the entire v2 architecture. Every other task depends on these.

- [ ] **Step 1: Write failing tests for Finding model**

```python
# tests/v2/test_types.py
"""Tests for v2 core types — Finding, ModuleConfig, ExecutionContextV2."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from prism_platform.v2.types import (
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/v2/test_types.py -v
```
Expected: `ModuleNotFoundError: No module named 'prism_platform.v2'`

- [ ] **Step 3: Implement v2 core types**

```python
# prism_platform/v2/__init__.py
"""PRISM v2 — Unified agentic module architecture."""

# prism_platform/v2/types.py
"""PRISM v2 Core Types — immutable contracts for the agentic module pattern.

Key models:
- Finding: immutable research unit extracted from deep research documents
- ModuleConfig: agent identity card (system prompt equivalent)
- ExecutionContextV2: runtime context passed to every module
- ClaimRegistryEntry: auto-generated claim for factcheck consumption
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FindingCategory(StrEnum):
    """Taxonomy of research findings.

    Used to filter cluster findings by domain module relevance.
    Each domain module declares which categories it consumes.
    """

    # Cluster A: Company & Competitive Landscape
    COMPANY_OVERVIEW = "company_overview"
    BUSINESS_MODEL = "business_model"
    COMPETITIVE_POSITIONING = "competitive_positioning"
    MARKET_POSITION = "market_position"
    PARTNER_ECOSYSTEM = "partner_ecosystem"
    INDUSTRY_TREND = "industry_trend"

    # Cluster B: Financial & Investor Intelligence
    REVENUE = "revenue"
    MARGINS = "margins"
    GROWTH = "growth"
    ANALYST_CONSENSUS = "analyst_consensus"
    EARNINGS_CALL_QUOTE = "earnings_call_quote"
    SEC_FILING_INSIGHT = "sec_filing_insight"
    MA_ACTIVITY = "ma_activity"

    # Cluster C: Technology & Digital Experience
    SEARCH_TECHNOLOGY = "search_technology"
    TECH_STACK = "tech_stack"
    TECH_MIGRATION = "tech_migration"
    DIGITAL_UX = "digital_ux"
    ARCHITECTURE = "architecture"
    USER_REVIEW = "user_review"

    # Cluster D: People & Signals
    EXEC_STATEMENT = "exec_statement"
    LEADERSHIP_CHANGE = "leadership_change"
    SOCIAL_SENTIMENT = "social_sentiment"
    CONFERENCE_TALK = "conference_talk"
    NEWS_EVENT = "news_event"

    # Cluster E: Buying Signals & Intent
    HIRING_SIGNAL = "hiring_signal"
    TECH_REMOVAL = "tech_removal"
    BUDGET_SIGNAL = "budget_signal"
    EVALUATION_SIGNAL = "evaluation_signal"
    COMPETITIVE_PRESSURE = "competitive_pressure"
    FUNDING_EVENT = "funding_event"


class Finding(BaseModel):
    """An immutable research finding extracted from deep research.

    Findings are the atomic unit of research intelligence. Once extracted
    from a research document, they flow through the pipeline unchanged.
    The citation chain from final output back to source URL is always traceable.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: str = Field(description="Unique identifier, e.g. 'f-a-perplexity-001'")
    company: str = Field(description="Which company this finding applies to")
    category: FindingCategory = Field(description="Finding taxonomy category")
    statement: str = Field(description="The actual finding — one clear sentence")
    source_url: str = Field(
        min_length=1,
        description="Citation URL — REQUIRED. No URL = finding is rejected.",
    )
    source_date: date | None = Field(
        default=None,
        description="When the source was published, if known",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="high=multi-source confirmed, medium=single source, low=conflicting data"
    )
    raw_quote: str | None = Field(
        default=None,
        description="Verbatim quote from the source, if applicable",
    )
    provider: str = Field(
        description="Which research provider produced this: 'perplexity' or 'openai'"
    )


class CompetitorRef(BaseModel):
    """Lightweight competitor reference from the seed phase."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    domain: str
    linkedin_url: str | None = None


class ExecutiveRef(BaseModel):
    """Lightweight executive reference from the seed phase."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    title: str
    linkedin_url: str | None = None
    role_classification: Literal[
        "economic_buyer", "technical_buyer", "champion", "influencer", "end_user"
    ] | None = None


class ModuleConfig(BaseModel):
    """Agent identity card — declares WHO the module is and WHAT it can access.

    This is the system prompt equivalent in the agentic mapping.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(description="Module identifier, e.g. 'intel-company'")
    version: str = Field(description="Semantic version, e.g. '2.0.0'")
    description: str = Field(description="One-line description of what this module discovers")
    layer: Literal["seed", "intelligence", "synthesis", "quality", "delivery"] = Field(
        description="Pipeline layer this module belongs to"
    )
    cost_tier: Literal["pro-search", "deep-research"] = Field(
        description="Perplexity API preset to use"
    )
    timeout_seconds: int = Field(default=120, description="Max execution time")
    max_retries: int = Field(default=2, description="Retry attempts on transient failure")
    cache_ttl_days: int = Field(default=90, description="How long cached results are valid")
    api_clients: list[str] = Field(
        default_factory=list,
        description="Structured API clients this module calls, e.g. ['builtwith', 'similarweb']",
    )
    composes: list[str] = Field(
        default_factory=list,
        description="Upstream modules whose cached output this module reads",
    )


class ExecutionContextV2(BaseModel):
    """Runtime context passed to every module execution.

    Populated progressively as pipeline phases complete:
    - After seed: domain, company_name, industry, is_public, competitors, executives
    - After research: cluster_findings populated
    - During domain modules: upstream_results populated as each module completes
    """

    model_config = ConfigDict(extra="forbid")

    audit_id: str
    account_domain: str
    company_name: str = ""
    industry: str = ""
    is_public: bool = False
    ticker: str | None = None
    competitors: list[CompetitorRef] = Field(default_factory=list)
    executives: list[ExecutiveRef] = Field(default_factory=list)
    cluster_findings: dict[str, list[Finding]] = Field(
        default_factory=dict,
        description="Merged findings keyed by cluster ID: 'A', 'B', 'C', 'D', 'E'",
    )
    upstream_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Cached outputs from completed upstream modules, keyed by module name",
    )


class ClaimRegistryEntry(BaseModel):
    """A verifiable claim extracted from module output for factcheck consumption.

    Every module auto-generates these from its output fields.
    The factcheck evaluator (Phase 7) consumes all claim registries.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    statement: str = Field(description="The claim in natural language")
    source_url: str = Field(description="Citation URL backing this claim")
    evidence_tier: Literal["VERIFIED", "WEBFETCH", "WEBSEARCH", "ESTIMATE"] = Field(
        description="How confident we are in this data point"
    )
    module_origin: str = Field(description="Which module produced this claim")
    field_path: str = Field(description="Dot-path to the output field, e.g. 'revenue_estimate'")
```

- [ ] **Step 4: Create test __init__ and run tests**

```bash
# tests/v2/__init__.py is empty
pytest tests/v2/test_types.py -v
```
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add prism_platform/v2/__init__.py prism_platform/v2/types.py tests/v2/__init__.py tests/v2/test_types.py
git commit -m "feat(v2): add core types — Finding, ModuleConfig, ExecutionContextV2, ClaimRegistryEntry"
```

---

## Task 2: AgentAPIClient

**Files:**
- Create: `prism_platform/v2/agent_api.py`
- Create: `tests/v2/test_agent_api.py`

Thin wrapper around Perplexity's chat completions API. Supports `pro-search` (seed) and `deep-research` (clusters) presets. Returns parsed JSON + extracted citations.

- [ ] **Step 1: Write failing tests for AgentAPIClient**

```python
# tests/v2/test_agent_api.py
"""Tests for AgentAPIClient — Perplexity API wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from prism_platform.v2.agent_api import AgentAPIClient, AgentAPIResponse


MOCK_PERPLEXITY_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": '{"legal_name": "Dell Technologies", "domain": "dell.com"}'
            }
        }
    ],
    "citations": [
        "https://www.dell.com/about",
        "https://investors.delltechnologies.com",
    ],
    "usage": {
        "prompt_tokens": 150,
        "completion_tokens": 200,
    },
}


class TestAgentAPIClient:
    """AgentAPIClient — Perplexity API wrapper."""

    @pytest.fixture
    def client(self) -> AgentAPIClient:
        return AgentAPIClient(api_key="test-key")

    @pytest.mark.asyncio
    async def test_pro_search_returns_parsed_response(self, client: AgentAPIClient) -> None:
        mock_response = httpx.Response(
            status_code=200,
            json=MOCK_PERPLEXITY_RESPONSE,
        )
        with patch.object(
            client._http, "post", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.research(
                system_prompt="You are a researcher.",
                user_prompt="Research dell.com",
                model="sonar-pro",
            )
            assert isinstance(result, AgentAPIResponse)
            assert '"Dell Technologies"' in result.content
            assert len(result.citations) == 2
            assert result.usage_input_tokens == 150
            assert result.usage_output_tokens == 200

    @pytest.mark.asyncio
    async def test_empty_choices_raises(self, client: AgentAPIClient) -> None:
        mock_response = httpx.Response(
            status_code=200,
            json={"choices": [], "citations": []},
        )
        with patch.object(
            client._http, "post", new_callable=AsyncMock, return_value=mock_response
        ):
            with pytest.raises(ValueError, match="No choices"):
                await client.research(
                    system_prompt="test",
                    user_prompt="test",
                    model="sonar-pro",
                )

    @pytest.mark.asyncio
    async def test_http_error_propagates(self, client: AgentAPIClient) -> None:
        mock_response = httpx.Response(status_code=429)
        mock_response.request = httpx.Request("POST", "https://api.perplexity.ai/chat/completions")
        with patch.object(
            client._http, "post", new_callable=AsyncMock, return_value=mock_response
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await client.research(
                    system_prompt="test",
                    user_prompt="test",
                    model="sonar-pro",
                )

    @pytest.mark.asyncio
    async def test_strips_markdown_code_fences(self, client: AgentAPIClient) -> None:
        fenced_response = {
            "choices": [
                {"message": {"content": '```json\n{"name": "Dell"}\n```'}}
            ],
            "citations": [],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        mock_response = httpx.Response(status_code=200, json=fenced_response)
        with patch.object(
            client._http, "post", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.research(
                system_prompt="test",
                user_prompt="test",
                model="sonar-pro",
            )
            assert "```" not in result.content
            assert '"Dell"' in result.content
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/v2/test_agent_api.py -v
```
Expected: `ModuleNotFoundError: No module named 'prism_platform.v2.agent_api'`

- [ ] **Step 3: Implement AgentAPIClient**

```python
# prism_platform/v2/agent_api.py
"""AgentAPIClient — thin wrapper around Perplexity's chat completions API.

Supports two presets:
- pro-search (sonar-pro): fast, single-step research for seed phase
- deep-research (sonar-deep-research): multi-step autonomous research for clusters

Returns structured AgentAPIResponse with content, citations, and usage metadata.
"""

from __future__ import annotations

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field

logger = structlog.get_logger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

# Model mapping for cost tiers
COST_TIER_MODELS = {
    "pro-search": "sonar-pro",
    "deep-research": "sonar-deep-research",
}


class AgentAPIResponse(BaseModel):
    """Parsed response from a Perplexity API call."""

    model_config = ConfigDict(frozen=True)

    content: str = Field(description="Response text (JSON or free-form)")
    citations: list[str] = Field(default_factory=list, description="Citation URLs from Perplexity")
    usage_input_tokens: int = 0
    usage_output_tokens: int = 0


class AgentAPIClient:
    """Perplexity API client for research calls.

    Args:
        api_key: Perplexity API key.
        timeout: Request timeout in seconds.
    """

    def __init__(self, api_key: str, timeout: float = 120.0) -> None:
        self._api_key = api_key
        self._http = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def research(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "sonar-pro",
        temperature: float = 0.1,
        max_tokens: int = 8192,
    ) -> AgentAPIResponse:
        """Execute a research call against the Perplexity API.

        Args:
            system_prompt: System message (agent identity + constraints).
            user_prompt: User message (resolved playbook content).
            model: Perplexity model ID (sonar-pro, sonar-deep-research).
            temperature: Sampling temperature. Low for factual research.
            max_tokens: Maximum response tokens.

        Returns:
            AgentAPIResponse with content, citations, and usage.

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses.
            ValueError: If Perplexity returns no choices.
        """
        logger.info(
            "AgentAPI research call",
            model=model,
            system_len=len(system_prompt),
            user_len=len(user_prompt),
        )

        resp = await self._http.post(
            PERPLEXITY_API_URL,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "return_citations": True,
            },
        )
        resp.raise_for_status()

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("No choices returned from Perplexity API")

        content = choices[0].get("message", {}).get("content", "")
        content = self._strip_code_fences(content)

        citations = data.get("citations", [])
        usage = data.get("usage", {})

        logger.info(
            "AgentAPI response received",
            model=model,
            content_len=len(content),
            citation_count=len(citations),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )

        return AgentAPIResponse(
            content=content,
            citations=citations,
            usage_input_tokens=usage.get("prompt_tokens", 0),
            usage_output_tokens=usage.get("completion_tokens", 0),
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        """Strip markdown code fences if Perplexity wraps JSON in ```json ... ```."""
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            return "\n".join(lines)
        return content
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/v2/test_agent_api.py -v
```
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add prism_platform/v2/agent_api.py tests/v2/test_agent_api.py
git commit -m "feat(v2): add AgentAPIClient — Perplexity API wrapper with citation extraction"
```

---

## Task 3: PlaybookLoader

**Files:**
- Create: `prism_platform/v2/playbook.py`
- Create: `tests/v2/test_playbook.py`

Reads playbook.md files, parses YAML frontmatter, and resolves template variables like `{domain}` and `{company_name}` from the ExecutionContextV2.

- [ ] **Step 1: Write failing tests**

```python
# tests/v2/test_playbook.py
"""Tests for PlaybookLoader — .md → resolved prompt."""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from prism_platform.v2.playbook import PlaybookLoader, PlaybookMeta
from prism_platform.v2.types import ExecutionContextV2


SAMPLE_PLAYBOOK = """---
name: intel-company
version: 2.0.0
description: Company seed intelligence
cost_tier: pro-search
execution_strategy: per-company
composes: []
---

## Objective
Research the company at {domain} and produce a comprehensive identity card.

## Data Collection
Discover: {company_name} legal name, headquarters, employee count, revenue.

## Competitors
Identify 5-7 direct competitors to {domain}.
"""


class TestPlaybookLoader:
    """PlaybookLoader — markdown to resolved prompt."""

    @pytest.fixture
    def playbook_dir(self, tmp_path: Path) -> Path:
        pb_file = tmp_path / "playbook.md"
        pb_file.write_text(SAMPLE_PLAYBOOK)
        return tmp_path

    @pytest.fixture
    def context(self) -> ExecutionContextV2:
        return ExecutionContextV2(
            audit_id=str(uuid4()),
            account_domain="dell.com",
            company_name="Dell Technologies",
            industry="Enterprise Technology",
            is_public=True,
            ticker="DELL",
        )

    def test_load_parses_frontmatter(self, playbook_dir: Path) -> None:
        loader = PlaybookLoader()
        meta, _ = loader.load(playbook_dir / "playbook.md")
        assert meta.name == "intel-company"
        assert meta.version == "2.0.0"
        assert meta.cost_tier == "pro-search"

    def test_load_returns_body(self, playbook_dir: Path) -> None:
        loader = PlaybookLoader()
        _, body = loader.load(playbook_dir / "playbook.md")
        assert "{domain}" in body
        assert "## Objective" in body

    def test_resolve_substitutes_variables(
        self, playbook_dir: Path, context: ExecutionContextV2
    ) -> None:
        loader = PlaybookLoader()
        _, body = loader.load(playbook_dir / "playbook.md")
        resolved = loader.resolve(body, context)
        assert "dell.com" in resolved
        assert "Dell Technologies" in resolved
        assert "{domain}" not in resolved
        assert "{company_name}" not in resolved

    def test_resolve_preserves_unknown_variables(self, playbook_dir: Path) -> None:
        ctx = ExecutionContextV2(
            audit_id=str(uuid4()),
            account_domain="test.com",
        )
        loader = PlaybookLoader()
        body = "Research {domain} and check {nonexistent_var}"
        resolved = loader.resolve(body, ctx)
        assert "test.com" in resolved
        assert "{nonexistent_var}" in resolved  # preserved, not crashed

    def test_load_missing_file_raises(self) -> None:
        loader = PlaybookLoader()
        with pytest.raises(FileNotFoundError):
            loader.load(Path("/nonexistent/playbook.md"))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/v2/test_playbook.py -v
```
Expected: `ModuleNotFoundError: No module named 'prism_platform.v2.playbook'`

- [ ] **Step 3: Implement PlaybookLoader**

```python
# prism_platform/v2/playbook.py
"""PlaybookLoader — reads playbook.md files and resolves template variables.

Playbooks are markdown files with YAML frontmatter. The body contains
research instructions with template variables like {domain}, {company_name},
{competitors} that are resolved from the ExecutionContextV2 at runtime.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict

from prism_platform.v2.types import ExecutionContextV2

logger = structlog.get_logger(__name__)

# Match YAML frontmatter between --- delimiters
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class PlaybookMeta(BaseModel):
    """Parsed YAML frontmatter from a playbook.md file."""

    model_config = ConfigDict(extra="ignore")

    name: str
    version: str
    description: str = ""
    cost_tier: str = "pro-search"
    execution_strategy: str = "per-company"
    composes: list[str] = []


class PlaybookLoader:
    """Loads and resolves playbook markdown files."""

    def load(self, path: Path) -> tuple[PlaybookMeta, str]:
        """Load a playbook.md file and parse its frontmatter.

        Args:
            path: Absolute path to the playbook.md file.

        Returns:
            Tuple of (PlaybookMeta, body_text).

        Raises:
            FileNotFoundError: If the playbook file doesn't exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"Playbook not found: {path}")

        raw = path.read_text(encoding="utf-8")
        meta, body = self._split_frontmatter(raw)

        logger.info(
            "Playbook loaded",
            path=str(path),
            name=meta.name,
            version=meta.version,
        )

        return meta, body

    def resolve(self, body: str, context: ExecutionContextV2) -> str:
        """Resolve template variables in a playbook body.

        Substitutes {domain}, {company_name}, {industry}, {ticker}, etc.
        from the ExecutionContextV2. Unknown variables are preserved as-is.

        Args:
            body: Raw playbook body text with {variable} placeholders.
            context: The execution context providing variable values.

        Returns:
            Resolved playbook text.
        """
        variables: dict[str, str] = {
            "domain": context.account_domain,
            "company_name": context.company_name,
            "industry": context.industry,
            "ticker": context.ticker or "",
            "is_public": str(context.is_public),
        }

        if context.competitors:
            comp_lines = [f"- {c.name} ({c.domain})" for c in context.competitors]
            variables["competitors"] = "\n".join(comp_lines)

        if context.executives:
            exec_lines = [f"- {e.name}, {e.title}" for e in context.executives]
            variables["executives"] = "\n".join(exec_lines)

        resolved = self._safe_substitute(body, variables)

        logger.debug(
            "Playbook resolved",
            domain=context.account_domain,
            variables_applied=list(variables.keys()),
        )

        return resolved

    @staticmethod
    def _split_frontmatter(raw: str) -> tuple[PlaybookMeta, str]:
        """Split a markdown file into YAML frontmatter and body.

        Args:
            raw: Full markdown file content.

        Returns:
            Tuple of (PlaybookMeta, body_text).
        """
        match = FRONTMATTER_RE.match(raw)
        if not match:
            return PlaybookMeta(name="unknown", version="0.0.0"), raw

        # Parse YAML frontmatter manually (avoid PyYAML dependency for now)
        yaml_text = match.group(1)
        meta_dict: dict[str, Any] = {}
        for line in yaml_text.split("\n"):
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                key, _, value = line.partition(":")
                value = value.strip().strip("'\"")
                if value == "[]":
                    meta_dict[key.strip()] = []
                elif value.startswith("["):
                    items = value.strip("[]").split(",")
                    meta_dict[key.strip()] = [i.strip().strip("'\"") for i in items if i.strip()]
                else:
                    meta_dict[key.strip()] = value

        body = raw[match.end():]
        return PlaybookMeta.model_validate(meta_dict), body

    @staticmethod
    def _safe_substitute(template: str, variables: dict[str, str]) -> str:
        """Substitute {key} placeholders, preserving unknown variables.

        Unlike str.format(), this does not raise KeyError for missing keys.

        Args:
            template: Template string with {variable} placeholders.
            variables: Key-value pairs to substitute.

        Returns:
            Template with known variables substituted.
        """
        def replacer(match: re.Match[str]) -> str:
            key = match.group(1)
            return variables.get(key, match.group(0))

        return re.sub(r"\{(\w+)\}", replacer, template)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/v2/test_playbook.py -v
```
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add prism_platform/v2/playbook.py tests/v2/test_playbook.py
git commit -m "feat(v2): add PlaybookLoader — markdown frontmatter parsing + template resolution"
```

---

## Task 4: ModuleExecutor

**Files:**
- Create: `prism_platform/v2/executor.py`
- Create: `tests/v2/conftest.py`
- Create: `tests/v2/test_executor.py`

The generic harness that runs any module. Same for every module — never changes. Loads playbook, calls Agent API, validates output, generates claim registry.

- [ ] **Step 1: Write test fixtures**

```python
# tests/v2/conftest.py
"""Shared fixtures for v2 tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from prism_platform.v2.types import ExecutionContextV2, ModuleConfig


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
```

- [ ] **Step 2: Write failing tests for ModuleExecutor**

```python
# tests/v2/test_executor.py
"""Tests for ModuleExecutor — the generic module harness."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, ConfigDict, Field

from prism_platform.v2.agent_api import AgentAPIResponse
from prism_platform.v2.executor import ModuleExecutor, ModuleExecutorResult
from prism_platform.v2.types import ExecutionContextV2, ModuleConfig


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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/v2/test_executor.py -v
```
Expected: `ModuleNotFoundError: No module named 'prism_platform.v2.executor'`

- [ ] **Step 4: Implement ModuleExecutor**

```python
# prism_platform/v2/executor.py
"""ModuleExecutor — the generic harness that runs any v2 module.

Execution flow:
1. Load and resolve playbook (replace {domain}, {company_name}, etc.)
2. Build system prompt from ModuleConfig
3. Call AgentAPIClient with resolved playbook as user prompt
4. Parse JSON response
5. Validate against Pydantic output schema
6. Generate claim registry entries
7. Return ModuleExecutorResult

The executor does NOT know what any module researches. It follows
config (which constraints), playbook (what instructions), and
schema (what shape). Pure plumbing.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, TypeVar

import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from prism_platform.v2.agent_api import AgentAPIClient
from prism_platform.v2.playbook import PlaybookLoader
from prism_platform.v2.types import ClaimRegistryEntry, ExecutionContextV2, ModuleConfig

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class ModuleExecutorResult(BaseModel):
    """Standard return type from the ModuleExecutor."""

    model_config = ConfigDict(extra="forbid")

    module_name: str
    module_version: str
    status: str  # "success", "partial", "failed"
    output: dict[str, Any] = Field(default_factory=dict)
    claims: list[ClaimRegistryEntry] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class ModuleExecutor:
    """Generic harness that runs any v2 module.

    Args:
        agent_api: AgentAPIClient instance for making research calls.
    """

    def __init__(self, agent_api: AgentAPIClient) -> None:
        self._api = agent_api
        self._playbook_loader = PlaybookLoader()

    async def execute(
        self,
        config: ModuleConfig,
        context: ExecutionContextV2,
        output_schema: type[T],
        playbook_path: Path,
    ) -> ModuleExecutorResult:
        """Execute a module using its config, playbook, and schema.

        Args:
            config: ModuleConfig defining the agent's identity and constraints.
            context: ExecutionContextV2 with runtime data (domain, findings, etc.).
            output_schema: Pydantic model class to validate the response against.
            playbook_path: Path to the playbook.md file.

        Returns:
            ModuleExecutorResult with validated output or errors.
        """
        start_ns = time.monotonic_ns()

        logger.info(
            "ModuleExecutor.execute started",
            module=config.name,
            version=config.version,
            domain=context.account_domain,
        )

        try:
            # Step 1: Load and resolve playbook
            meta, body = self._playbook_loader.load(playbook_path)
            resolved_prompt = self._playbook_loader.resolve(body, context)

            # Step 2: Build system prompt from config
            system_prompt = self._build_system_prompt(config, output_schema)

            # Step 3: Call Agent API
            response = await self._api.research(
                system_prompt=system_prompt,
                user_prompt=resolved_prompt,
                model=self._model_for_tier(config.cost_tier),
            )

            # Step 4: Parse JSON
            try:
                raw_data = json.loads(response.content)
            except json.JSONDecodeError as e:
                return self._fail_result(
                    config, start_ns,
                    errors=[f"JSON parse failed: {e}"],
                    llm_calls=1,
                    input_tokens=response.usage_input_tokens,
                    output_tokens=response.usage_output_tokens,
                )

            # Step 5: Validate against Pydantic schema
            try:
                validated = output_schema.model_validate(raw_data)
            except ValidationError as e:
                field_errors = [
                    f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                    for err in e.errors()
                ]
                return self._fail_result(
                    config, start_ns,
                    errors=[f"Schema validation failed: {err}" for err in field_errors],
                    llm_calls=1,
                    input_tokens=response.usage_input_tokens,
                    output_tokens=response.usage_output_tokens,
                )

            output_dict = validated.model_dump()

            # Step 6: Generate claim registry
            claims = self._build_claims(output_dict, config.name, response.citations)

            duration_ms = (time.monotonic_ns() - start_ns) // 1_000_000

            logger.info(
                "ModuleExecutor.execute completed",
                module=config.name,
                domain=context.account_domain,
                status="success",
                duration_ms=duration_ms,
                claim_count=len(claims),
            )

            return ModuleExecutorResult(
                module_name=config.name,
                module_version=config.version,
                status="success",
                output=output_dict,
                claims=claims,
                citations=response.citations,
                duration_ms=duration_ms,
                llm_calls=1,
                input_tokens=response.usage_input_tokens,
                output_tokens=response.usage_output_tokens,
            )

        except Exception as e:
            logger.exception(
                "ModuleExecutor.execute failed",
                module=config.name,
                domain=context.account_domain,
            )
            return self._fail_result(
                config, start_ns,
                errors=[f"{type(e).__name__}: {e}"],
            )

    def _build_system_prompt(self, config: ModuleConfig, schema: type[BaseModel]) -> str:
        """Build the system prompt from config and output schema.

        The system prompt tells the LLM WHO it is and WHAT shape the output must take.
        The JSON schema from Pydantic is included so the LLM knows the exact contract.
        """
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        return (
            f"You are {config.description}. "
            f"Module: {config.name} v{config.version}.\n\n"
            "Return your response as a single valid JSON object matching this schema exactly. "
            "No markdown, no commentary before or after the JSON.\n\n"
            f"JSON Schema:\n{schema_json}\n\n"
            "Rules:\n"
            "- Every fact must have a source. Cite with URLs.\n"
            "- Numbers must be raw values (88400000000.0 not '$88.4B').\n"
            "- Dates in YYYY-MM-DD format.\n"
            "- Do not fabricate URLs — only use URLs you actually found.\n"
        )

    @staticmethod
    def _model_for_tier(cost_tier: str) -> str:
        """Map cost tier to Perplexity model ID."""
        mapping = {
            "pro-search": "sonar-pro",
            "deep-research": "sonar-deep-research",
        }
        return mapping.get(cost_tier, "sonar-pro")

    @staticmethod
    def _build_claims(
        output: dict[str, Any],
        module_name: str,
        citations: list[str],
    ) -> list[ClaimRegistryEntry]:
        """Auto-generate claim registry entries from output fields.

        Creates a claim for each non-None, non-empty scalar field in the output.
        Uses the first citation as fallback source URL.
        """
        claims: list[ClaimRegistryEntry] = []
        fallback_url = citations[0] if citations else "no-citation"

        for key, value in output.items():
            if value is None or value == "" or isinstance(value, (list, dict)):
                continue
            claims.append(
                ClaimRegistryEntry(
                    statement=f"{key} = {value}",
                    source_url=fallback_url,
                    evidence_tier="WEBSEARCH",
                    module_origin=module_name,
                    field_path=key,
                )
            )

        return claims

    def _fail_result(
        self,
        config: ModuleConfig,
        start_ns: int,
        errors: list[str],
        llm_calls: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> ModuleExecutorResult:
        """Build a failed ModuleExecutorResult."""
        duration_ms = (time.monotonic_ns() - start_ns) // 1_000_000
        return ModuleExecutorResult(
            module_name=config.name,
            module_version=config.version,
            status="failed",
            errors=errors,
            duration_ms=duration_ms,
            llm_calls=llm_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/v2/test_executor.py -v
```
Expected: All 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add prism_platform/v2/executor.py tests/v2/conftest.py tests/v2/test_executor.py
git commit -m "feat(v2): add ModuleExecutor — generic harness with playbook resolution and claim registry"
```

---

## Task 5: intel-company v2 Schemas

**Files:**
- Create: `prism_platform/v2/modules/__init__.py`
- Create: `prism_platform/v2/modules/intel_company/__init__.py`
- Create: `prism_platform/v2/modules/intel_company/schemas.py`
- Create: `tests/v2/test_intel_company_v2.py`

The output schema for intel-company v2 (the seed module). Tightened from v1: `extra="forbid"`, `Literal` types for role classification, field descriptions that serve as LLM instructions.

- [ ] **Step 1: Write failing tests**

```python
# tests/v2/test_intel_company_v2.py
"""Tests for intel-company v2 schemas — the seed module."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.v2.modules.intel_company.schemas import (
    CompanySeedOutput,
    CompetitorSeed,
    ExecutiveSeed,
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/v2/test_intel_company_v2.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement schemas**

```python
# prism_platform/v2/modules/__init__.py
"""v2 module implementations."""

# prism_platform/v2/modules/intel_company/__init__.py
"""intel-company v2 — the seed module."""

# prism_platform/v2/modules/intel_company/schemas.py
"""intel-company v2 schemas — the seed module's data contracts.

CompanySeedOutput is the foundation that every downstream module reads.
Field descriptions double as LLM instructions when the schema is passed
to the Agent API as response_format or included in the system prompt.

Changes from v1:
- extra="forbid" (v1 used extra="ignore" — silently ate bad fields)
- Literal types for role_classification (v1 used bare str)
- min_length on business_model (v1 validated post-hoc in validator.py)
- ExecutiveSeed includes role_classification for MEDDPICC mapping
- CompetitorSeed includes linkedin_url for social intelligence
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExecutiveSeed(BaseModel):
    """An executive discovered during seed research.

    role_classification maps to MEDDPICC buyer roles for downstream
    sales intelligence generation.
    """

    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(description="Full name of the executive")
    title: str = Field(description="Current job title")
    role_classification: Literal[
        "economic_buyer",
        "technical_buyer",
        "champion",
        "influencer",
        "end_user",
    ] | None = Field(
        default=None,
        description=(
            "MEDDPICC role classification based on title. "
            "CEO/CFO/CRO = economic_buyer. CTO/VP Eng = technical_buyer. "
            "VP Digital/Head of Search = champion. Director level = influencer. "
            "None if unclear."
        ),
    )
    linkedin_url: str | None = Field(
        default=None,
        description=(
            "LinkedIn profile URL. Must start with https://linkedin.com/in/ or "
            "https://www.linkedin.com/in/. Do NOT fabricate — only include if found."
        ),
    )
    tenure_description: str | None = Field(
        default=None,
        description="How long in current role, e.g. 'Since 2021' or '3 years'",
    )
    previous_company: str | None = Field(
        default=None,
        description="Most recent previous employer",
    )


class CompetitorSeed(BaseModel):
    """A direct competitor discovered during seed research."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(description="Competitor's name")
    domain: str = Field(description="Competitor's primary website domain")
    why_competitor: str = Field(
        description="One sentence: why they compete with the prospect"
    )
    linkedin_url: str | None = Field(
        default=None,
        description="Company LinkedIn page URL, if found",
    )


class CompanySeedOutput(BaseModel):
    """Full output from the intel-company seed module.

    This is the identity card that every downstream module reads.
    Every field description is an LLM instruction — write them carefully.
    """

    model_config = ConfigDict(extra="forbid")

    # Identity
    legal_name: str = Field(description="Official registered company name")
    common_name: str = Field(description="Name used in press/marketing")
    domain: str = Field(description="Primary website domain, e.g. 'dell.com'")
    headquarters: str = Field(description="HQ city and country, e.g. 'Round Rock, Texas, USA'")
    employee_count: int | None = Field(
        default=None,
        description="Approximate employee count as integer, e.g. 133000. NOT a string.",
    )
    employee_count_source: str | None = Field(
        default=None,
        description="Source of employee count, e.g. 'LinkedIn', 'Company website'",
    )
    year_founded: int | None = Field(
        default=None,
        description="Year founded as 4-digit integer, e.g. 1984",
    )
    business_model: str = Field(
        min_length=50,
        description=(
            "Detailed description of how the company makes money. "
            "Minimum 50 characters. Include revenue streams, target market, "
            "and key products/services."
        ),
    )

    # Classification
    industry: str = Field(
        description="Primary industry, e.g. 'Enterprise Technology', 'E-commerce Retail'"
    )
    sub_vertical: str | None = Field(
        default=None,
        description="Specific sub-vertical, e.g. 'Consumer Electronics', 'Fashion Retail'",
    )
    is_public: bool = Field(
        default=False,
        description="True if publicly traded on a stock exchange",
    )
    ticker: str | None = Field(
        default=None,
        description="Stock ticker if public, e.g. 'DELL'. None if private.",
    )
    parent_company: str | None = Field(
        default=None,
        description="Parent company name if subsidiary. None if independent.",
    )
    revenue_estimate: float | None = Field(
        default=None,
        description=(
            "Annual revenue in USD as float, e.g. 88400000000.0 for $88.4B. "
            "NOT a formatted string. None if unknown."
        ),
    )
    revenue_source: str | None = Field(
        default=None,
        description="Source of revenue figure, e.g. 'SEC 10-K FY2025'",
    )

    # People & competitors
    executives: list[ExecutiveSeed] = Field(
        default_factory=list,
        description=(
            "5-12 key executives. Must include CEO, CTO, CFO at minimum. "
            "Include VP/Director of Engineering, Product, E-commerce, Digital, Search. "
            "For subsidiaries, include both subsidiary and relevant parent company leaders."
        ),
    )
    competitors: list[CompetitorSeed] = Field(
        default_factory=list,
        description=(
            "5-7 direct competitors selling similar products/services "
            "to similar customers in the same market."
        ),
    )

    # Website snapshot
    product_categories: list[str] = Field(
        default_factory=list,
        description="Top-level product/service categories visible on the website",
    )
    company_linkedin_url: str | None = Field(
        default=None,
        description="Company LinkedIn page URL",
    )
    recent_headline: str | None = Field(
        default=None,
        description="One recent newsworthy headline about the company (last 90 days)",
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/v2/test_intel_company_v2.py -v
```
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add prism_platform/v2/modules/ tests/v2/test_intel_company_v2.py
git commit -m "feat(v2): add intel-company v2 schemas — CompanySeedOutput with extra=forbid and role classification"
```

---

## Task 6: intel-company v2 Config + Playbook

**Files:**
- Create: `prism_platform/v2/modules/intel_company/config.py`
- Create: `prism_platform/v2/modules/intel_company/playbook.md`

The ModuleConfig instance and the playbook markdown — together they define the agent.

- [ ] **Step 1: Write the config**

```python
# prism_platform/v2/modules/intel_company/config.py
"""intel-company v2 ModuleConfig — the agent's identity card.

This is the SEED module. It runs first in every audit, using a single
Perplexity pro-search call to produce the company identity card that
every downstream module reads.
"""

from prism_platform.v2.types import ModuleConfig

INTEL_COMPANY_CONFIG = ModuleConfig(
    name="intel-company",
    version="2.0.0",
    description=(
        "Foundation company intelligence researcher. Discovers company identity, "
        "leadership team, competitors, and business model from a single domain input."
    ),
    layer="seed",
    cost_tier="pro-search",
    timeout_seconds=120,
    max_retries=2,
    cache_ttl_days=180,
    api_clients=[],  # Seed uses only Agent API, no structured APIs
    composes=[],  # Seed has no upstream dependencies
)
```

- [ ] **Step 2: Write the playbook**

```markdown
# prism_platform/v2/modules/intel_company/playbook.md
---
name: intel-company
version: 2.0.0
description: Company seed intelligence — the identity card
cost_tier: pro-search
execution_strategy: per-company
composes: []
---

## Objective

Research the company that owns the website **{domain}** and produce a comprehensive company identity card. This is the SEED module — every other module in the audit pipeline depends on your output being accurate and complete.

## What to Discover

### Identity
- Official registered company name (legal name) and common marketing name
- Headquarters location (city, state/region, country)
- Year founded
- Approximate employee count (cite source: LinkedIn, company website, etc.)
- Business model: how they make money, who their customers are, key product/service categories (minimum 3 sentences)
- Company LinkedIn page URL

### Financial Snapshot
- Whether the company is publicly traded or private
- Stock ticker symbol (if public)
- Parent company (if subsidiary)
- Annual revenue estimate in USD (cite source: SEC filing, Forbes, etc.)

### Classification
- Primary industry (e.g. "Enterprise Technology", "E-commerce Retail")
- Sub-vertical (e.g. "Consumer Electronics", "Fashion Retail")
- Top-level product/service categories visible on the website

### Leadership Team
Find **8-12 named executives**. This section is critical — downstream modules depend on it.

Search these sources:
- The company website "About Us", "Leadership", or "Team" page
- LinkedIn profiles
- Companies House director filings (for UK companies)
- Press releases and recent news

Must include at minimum: CEO, CFO, CTO/VP Engineering, CMO/VP Marketing.
Also look for: VP/Director of Product, E-commerce, Digital, Search, Data/AI.
For subsidiaries: include BOTH subsidiary leaders AND parent company executives who oversee it.

For each executive, classify their MEDDPICC buyer role based on title:
- CEO, CFO, CRO, COO, President → economic_buyer
- CTO, VP Engineering, Chief Architect → technical_buyer
- VP Digital, VP E-commerce, Head of Search, VP Customer Experience → champion
- Director-level roles → influencer
- If unclear from title alone → null

### Competitors
Find **5-7 direct competitors** that sell similar products/services to similar customers in the same market. For each competitor, include their website domain and one sentence explaining why they compete with {domain}.

### Recent Activity
Find one recent headline about the company from the last 90 days.

## Output Format
Return a single valid JSON object. No markdown, no commentary before or after.

## Quality Rules
- LinkedIn URLs must be real — do NOT fabricate. Only include if you actually found them.
- Revenue must be a raw number in USD (e.g. 88400000000.0, not "$88.4B")
- Dates in YYYY-MM-DD format
- Employee count as integer (e.g. 133000, not "~133K")
- business_model must be at least 50 characters with real substance
- Executives must have at least 5 entries
- Competitors must have at least 5 entries
```

- [ ] **Step 3: Write a test that loads the config and playbook together**

Add to `tests/v2/test_intel_company_v2.py`:

```python
from pathlib import Path

from prism_platform.v2.modules.intel_company.config import INTEL_COMPANY_CONFIG
from prism_platform.v2.playbook import PlaybookLoader
from prism_platform.v2.types import ExecutionContextV2


class TestIntelCompanyWiring:
    """Test that config + playbook + schema wire together correctly."""

    def test_config_is_valid(self) -> None:
        assert INTEL_COMPANY_CONFIG.name == "intel-company"
        assert INTEL_COMPANY_CONFIG.layer == "seed"
        assert INTEL_COMPANY_CONFIG.cost_tier == "pro-search"

    def test_playbook_loads(self) -> None:
        playbook_path = (
            Path(__file__).resolve().parents[2]
            / "prism_platform"
            / "v2"
            / "modules"
            / "intel_company"
            / "playbook.md"
        )
        loader = PlaybookLoader()
        meta, body = loader.load(playbook_path)
        assert meta.name == "intel-company"
        assert "{domain}" in body

    def test_playbook_resolves(self) -> None:
        playbook_path = (
            Path(__file__).resolve().parents[2]
            / "prism_platform"
            / "v2"
            / "modules"
            / "intel_company"
            / "playbook.md"
        )
        loader = PlaybookLoader()
        _, body = loader.load(playbook_path)

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
        # Verify key fields present
        props = schema["properties"]
        assert "legal_name" in props
        assert "executives" in props
        assert "competitors" in props
        # Verify extra=forbid manifests as additionalProperties: false
        assert schema.get("additionalProperties") is False
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/v2/test_intel_company_v2.py -v
```
Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add prism_platform/v2/modules/intel_company/config.py prism_platform/v2/modules/intel_company/playbook.md tests/v2/test_intel_company_v2.py
git commit -m "feat(v2): add intel-company v2 config + playbook — the seed agent definition"
```

---

## Task 7: End-to-End Smoke Test

**Files:**
- Create: `tests/v2/test_e2e_intel_company.py`

Integration test that wires everything together: config → playbook → executor → AgentAPI (mocked) → schema validation → claim registry. This is the proof that the pattern works.

- [ ] **Step 1: Write the end-to-end test**

```python
# tests/v2/test_e2e_intel_company.py
"""End-to-end test for intel-company v2 — proves the agentic pattern works.

Uses a realistic mocked Perplexity response to validate the full pipeline:
config → playbook → executor → API → schema → claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from prism_platform.v2.agent_api import AgentAPIClient, AgentAPIResponse
from prism_platform.v2.executor import ModuleExecutor
from prism_platform.v2.modules.intel_company.config import INTEL_COMPANY_CONFIG
from prism_platform.v2.modules.intel_company.schemas import CompanySeedOutput
from prism_platform.v2.types import ExecutionContextV2


# Realistic mock response matching CompanySeedOutput schema
REALISTIC_DELL_RESPONSE = json.dumps({
    "legal_name": "Dell Technologies Inc.",
    "common_name": "Dell",
    "domain": "dell.com",
    "headquarters": "Round Rock, Texas, USA",
    "employee_count": 133000,
    "employee_count_source": "LinkedIn",
    "year_founded": 1984,
    "business_model": (
        "Dell Technologies designs, manufactures, and sells enterprise hardware including "
        "servers, storage, networking equipment, and personal computers. The company generates "
        "revenue through direct sales to enterprises and consumers, professional services, "
        "and software solutions through subsidiaries like VMware and Secureworks."
    ),
    "industry": "Enterprise Technology",
    "sub_vertical": "Hardware & Infrastructure",
    "is_public": True,
    "ticker": "DELL",
    "parent_company": None,
    "revenue_estimate": 88400000000.0,
    "revenue_source": "SEC 10-K FY2025",
    "executives": [
        {"full_name": "Michael Dell", "title": "Chairman & CEO", "role_classification": "economic_buyer", "linkedin_url": "https://www.linkedin.com/in/michaeldell", "tenure_description": "Since 1984", "previous_company": None},
        {"full_name": "Yvonne McGill", "title": "Chief Financial Officer", "role_classification": "economic_buyer", "linkedin_url": None, "tenure_description": "Since 2022", "previous_company": "Dell (various roles)"},
        {"full_name": "Jeff Clarke", "title": "Vice Chairman & COO", "role_classification": "economic_buyer", "linkedin_url": None, "tenure_description": "Since 2021", "previous_company": None},
        {"full_name": "John Roese", "title": "Global CTO", "role_classification": "technical_buyer", "linkedin_url": None, "tenure_description": "Since 2020", "previous_company": "Huawei"},
        {"full_name": "Jen Felch", "title": "Chief Digital Officer", "role_classification": "champion", "linkedin_url": None, "tenure_description": "Since 2019", "previous_company": None},
    ],
    "competitors": [
        {"company_name": "HP Inc", "domain": "hp.com", "why_competitor": "Competes in PCs, printers, and enterprise hardware", "linkedin_url": None},
        {"company_name": "Lenovo", "domain": "lenovo.com", "why_competitor": "Major PC and server manufacturer competing globally", "linkedin_url": None},
        {"company_name": "Hewlett Packard Enterprise", "domain": "hpe.com", "why_competitor": "Competes in enterprise servers, storage, and networking", "linkedin_url": None},
        {"company_name": "Cisco Systems", "domain": "cisco.com", "why_competitor": "Competes in networking and enterprise infrastructure", "linkedin_url": None},
        {"company_name": "IBM", "domain": "ibm.com", "why_competitor": "Competes in enterprise IT services and infrastructure", "linkedin_url": None},
    ],
    "product_categories": ["Laptops", "Desktops", "Servers", "Storage", "Networking", "Services"],
    "company_linkedin_url": "https://www.linkedin.com/company/dell-technologies",
    "recent_headline": "Dell Technologies reports strong Q4 FY2025 results driven by AI server demand",
})


@pytest.mark.asyncio
async def test_intel_company_v2_full_pipeline() -> None:
    """Full pipeline: config → playbook → executor → API → schema → claims."""

    # Build mock API client
    mock_response = AgentAPIResponse(
        content=REALISTIC_DELL_RESPONSE,
        citations=[
            "https://investors.delltechnologies.com/annual-report-2025",
            "https://www.dell.com/en-us/about",
            "https://www.linkedin.com/company/dell-technologies",
        ],
        usage_input_tokens=250,
        usage_output_tokens=800,
    )
    mock_api = AsyncMock(spec=AgentAPIClient)
    mock_api.research = AsyncMock(return_value=mock_response)

    # Build context
    context = ExecutionContextV2(
        audit_id=str(uuid4()),
        account_domain="dell.com",
        company_name="Dell Technologies",
        industry="Enterprise Technology",
        is_public=True,
        ticker="DELL",
    )

    # Build executor and run
    executor = ModuleExecutor(agent_api=mock_api)
    playbook_path = (
        Path(__file__).resolve().parents[2]
        / "prism_platform"
        / "v2"
        / "modules"
        / "intel_company"
        / "playbook.md"
    )

    result = await executor.execute(
        config=INTEL_COMPANY_CONFIG,
        context=context,
        output_schema=CompanySeedOutput,
        playbook_path=playbook_path,
    )

    # Assertions — the pattern works
    assert result.status == "success", f"Expected success, got {result.status}: {result.errors}"
    assert result.module_name == "intel-company"
    assert result.module_version == "2.0.0"

    # Output validates against schema
    output = CompanySeedOutput.model_validate(result.output)
    assert output.legal_name == "Dell Technologies Inc."
    assert output.domain == "dell.com"
    assert output.is_public is True
    assert output.ticker == "DELL"
    assert output.revenue_estimate == 88400000000.0
    assert len(output.executives) >= 5
    assert len(output.competitors) >= 5

    # Role classification works
    ceo = next(e for e in output.executives if "CEO" in e.title)
    assert ceo.role_classification == "economic_buyer"
    cto = next(e for e in output.executives if "CTO" in e.title)
    assert cto.role_classification == "technical_buyer"

    # Claims generated
    assert len(result.claims) > 0
    assert all(c.module_origin == "intel-company" for c in result.claims)
    revenue_claim = next((c for c in result.claims if c.field_path == "revenue_estimate"), None)
    assert revenue_claim is not None

    # Citations passed through
    assert len(result.citations) == 3

    # Cost tracked
    assert result.llm_calls == 1
    assert result.input_tokens == 250
    assert result.output_tokens == 800

    # Verify the API was called with resolved playbook (no {domain} placeholder)
    call_args = mock_api.research.call_args
    user_prompt = call_args.kwargs.get("user_prompt", call_args.args[1] if len(call_args.args) > 1 else "")
    assert "dell.com" in user_prompt
    assert "{domain}" not in user_prompt


@pytest.mark.asyncio
async def test_intel_company_v2_handles_bad_response() -> None:
    """Executor gracefully handles API returning non-schema-compliant JSON."""

    bad_response = AgentAPIResponse(
        content='{"name": "Dell", "bad_field": true}',  # missing required fields
        citations=[],
        usage_input_tokens=10,
        usage_output_tokens=20,
    )
    mock_api = AsyncMock(spec=AgentAPIClient)
    mock_api.research = AsyncMock(return_value=bad_response)

    context = ExecutionContextV2(
        audit_id=str(uuid4()),
        account_domain="dell.com",
    )

    executor = ModuleExecutor(agent_api=mock_api)
    playbook_path = (
        Path(__file__).resolve().parents[2]
        / "prism_platform"
        / "v2"
        / "modules"
        / "intel_company"
        / "playbook.md"
    )

    result = await executor.execute(
        config=INTEL_COMPANY_CONFIG,
        context=context,
        output_schema=CompanySeedOutput,
        playbook_path=playbook_path,
    )

    assert result.status == "failed"
    assert len(result.errors) > 0
    # Should mention the missing required field
    assert any("legal_name" in e for e in result.errors)
```

- [ ] **Step 2: Run the end-to-end test**

```bash
pytest tests/v2/test_e2e_intel_company.py -v
```
Expected: Both tests PASS

- [ ] **Step 3: Run ALL v2 tests together**

```bash
pytest tests/v2/ -v
```
Expected: All tests PASS (should be ~25 tests total across all test files)

- [ ] **Step 4: Commit**

```bash
git add tests/v2/test_e2e_intel_company.py
git commit -m "test(v2): add end-to-end smoke test proving the agentic module pattern works"
```

---

## Task 8: Research Cluster Playbooks (Design Artifacts)

**Files:**
- Create: `prism_platform/v2/clusters/cluster_a_company.md`
- Create: `prism_platform/v2/clusters/cluster_b_financial.md`
- Create: `prism_platform/v2/clusters/cluster_c_technology.md`
- Create: `prism_platform/v2/clusters/cluster_d_people.md`
- Create: `prism_platform/v2/clusters/cluster_e_buying_signals.md`

These are Phase 2 design artifacts. Each cluster runs as two independent deep-research calls (Perplexity + OpenAI) during the research phase. They produce free-form research documents that are later extracted into Finding objects via map-reduce.

**NOTE:** These playbooks are not wired into the executor yet — they are design artifacts for the next implementation phase (Phase 2: Research Clusters + Domain Migration).

- [ ] **Step 1: Write Cluster A playbook**

```markdown
# prism_platform/v2/clusters/cluster_a_company.md
---
name: cluster-a-company
version: 1.0.0
description: Company & Competitive Landscape deep research
cluster_id: A
cost_tier: deep-research
recency_bias_months: 12
feeds: [intel-company, intel-industry, intel-partner, intel-competitors]
---

## Research Mission

Conduct deep research on **{company_name}** ({domain}) and their competitive landscape. You are researching for a sales intelligence platform — your findings will be used to help sales teams understand the prospect's business, market position, and competitive dynamics.

## Depth Allocation

- **60% effort** on {company_name} (the prospect) — deep dive
- **40% effort** on competitors — comparison-focused key data points

Competitors to investigate:
{competitors}

## What to Discover

### Company Deep Dive (Prospect)
1. **Business Model Detail:** Revenue streams breakdown, customer segments, go-to-market strategy, pricing model if discoverable
2. **Market Position:** Market share estimates, analyst commentary on positioning, growth trajectory relative to market
3. **Strategic Direction:** Recent strategic announcements, pivots, new market entries, product launches in last 12 months
4. **Partner Ecosystem:** Technology partners, system integrators, channel partners, marketplace presence
5. **Digital Presence Assessment:** How sophisticated is their website/app? Any public commentary on their digital strategy?
6. **Organizational Structure:** Divisions, subsidiaries, key brands, geographic presence

### Competitive Landscape
For each competitor:
1. **How they compete:** Where do they overlap with {company_name}? Where do they differentiate?
2. **Relative strength:** Are they gaining or losing ground? Any market share data?
3. **Technology differences:** Different tech stack, different approach to search/digital experience?
4. **Recent moves:** Acquisitions, partnerships, product launches that shift competitive dynamics

### Industry Context
1. **Market size and growth:** Total addressable market, growth rate
2. **Industry trends:** What's changing in this vertical? Digital transformation, AI adoption, etc.
3. **Regulatory landscape:** Any regulations affecting digital commerce or data in this vertical?

## Source Priority
Prefer these sources (in order):
1. Analyst reports (Gartner, Forrester, IDC, Baymard)
2. Industry publications and trade press
3. Company investor presentations and earnings materials
4. Business news (Reuters, Bloomberg, TechCrunch)
5. Company blog posts and press releases
6. Wikipedia and Crunchbase for factual foundations

## Output Instructions
Write a comprehensive research document. Include inline citations [source](url) for every factual claim. Structure your findings with clear headers. Be thorough — downstream modules will extract structured data from your research.
```

- [ ] **Step 2: Write Cluster B playbook**

```markdown
# prism_platform/v2/clusters/cluster_b_financial.md
---
name: cluster-b-financial
version: 1.0.0
description: Financial & Investor Intelligence deep research
cluster_id: B
cost_tier: deep-research
recency_bias_months: 6
feeds: [intel-financials, intel-investor]
---

## Research Mission

Conduct deep financial and investor intelligence research on **{company_name}** ({domain}). Your findings will feed financial analysis and investor intelligence modules.

## Depth Allocation

- **70% effort** on {company_name} financial intelligence
- **30% effort** on competitor financial comparisons

## What to Discover

### Revenue & Growth
1. **Revenue trend:** Last 3 years of annual revenue (or best estimates for private companies)
2. **Revenue breakdown:** By segment, geography, product line if available
3. **Growth rate:** YoY revenue growth, organic vs acquisition-driven
4. **Digital/ecommerce revenue:** What percentage of revenue comes from digital channels? Is this growing faster than overall?

### Profitability & Margins
1. **EBITDA margin** and trend
2. **Gross margin** by segment if available
3. **Operating expenses:** R&D spend, S&M spend as % of revenue
4. **Free cash flow** generation

### Analyst & Investor Perspective
1. **Analyst consensus:** Buy/hold/sell ratings, price targets, consensus revenue estimates
2. **Earnings call quotes:** Verbatim quotes from CEO/CFO about strategy, priorities, challenges — especially anything related to digital transformation, customer experience, search, or technology investment
3. **10-K risk factors:** What does the company identify as key risks? (SEC filings for public companies)
4. **Investor presentations:** Key strategic messages from recent investor day or shareholder letters

### M&A and Capital Allocation
1. **Recent acquisitions:** What have they bought? What does it signal about strategic direction?
2. **Capital expenditure focus:** Where are they investing? Technology, retail, supply chain?
3. **Dividend/buyback policy:** How are they returning capital to shareholders?

### Competitor Financial Comparison
For key competitors, find:
- Revenue scale comparison
- Growth rate comparison
- Profitability comparison
- Digital investment signals

## Source Priority
1. SEC filings (10-K, 10-Q, proxy statements) — for public companies
2. Earnings call transcripts (Seeking Alpha, The Motley Fool, company IR page)
3. Yahoo Finance, Bloomberg, Reuters financial data
4. Analyst reports (if publicly summarized)
5. Company investor relations pages
6. Financial news and commentary

## Output Instructions
Write a comprehensive financial research document. Include inline citations [source](url) for every number and quote. Distinguish between VERIFIED figures (from filings) and ESTIMATES. For private companies, clearly label all revenue/financial figures as estimates and cite the basis for each estimate.
```

- [ ] **Step 3: Write Cluster C playbook**

```markdown
# prism_platform/v2/clusters/cluster_c_technology.md
---
name: cluster-c-technology
version: 1.0.0
description: Technology & Digital Experience deep research
cluster_id: C
cost_tier: deep-research
recency_bias_months: 12
feeds: [intel-techstack, intel-traffic, intel-hiring]
---

## Research Mission

Conduct deep technology and digital experience research on **{company_name}** ({domain}). Focus on their search technology, tech stack, digital UX, and any technology migration signals.

## Depth Allocation

- **60% effort** on {company_name} technology deep dive
- **40% effort** on competitor technology comparison

## What to Discover

### Search Technology
1. **Current search solution:** What powers search on {domain}? (Algolia, Elasticsearch, Coveo, Bloomreach, native platform search, custom-built, etc.)
2. **Search features observed:** Autocomplete, faceted search, NLP/semantic search, personalization, recommendations, visual search
3. **Search quality signals:** Any user complaints about search? G2/Capterra reviews mentioning search? App store reviews?
4. **Search team:** Any job postings or LinkedIn profiles suggesting a dedicated search team?

### Tech Stack & Architecture
1. **E-commerce platform:** Salesforce Commerce Cloud, Shopify Plus, Magento, custom-built, etc.
2. **Frontend framework:** React, Next.js, Vue, Angular, or monolithic?
3. **CDN/hosting:** Cloudflare, Akamai, Fastly, AWS CloudFront?
4. **Analytics:** Google Analytics, Adobe Analytics, Segment, etc.
5. **A/B testing:** Optimizely, VWO, LaunchDarkly, etc.
6. **Personalization:** Any personalization engine beyond search?

### Technology Migration Signals
1. **Recent platform changes:** Have they migrated e-commerce platforms, replatformed their website, or changed search providers in the last 2 years?
2. **Technology removals:** Any technologies recently removed from their stack?
3. **Engineering blog posts:** Any posts about architecture decisions, migrations, or technology investments?
4. **Conference talks:** Any engineers from {company_name} speaking at conferences about their tech stack?

### Digital UX Assessment
1. **Mobile experience:** Is the site mobile-optimized? Any PWA or native app?
2. **Performance signals:** Any public data on page load speed, Core Web Vitals?
3. **User reviews:** What do customers say about the digital experience on G2, Capterra, Trustpilot, app stores?

### Competitor Technology Comparison
For each competitor:
1. What search solution do they use?
2. What e-commerce platform?
3. Any recent technology investments or migrations?
4. How does their digital UX compare?

## Source Priority
1. BuiltWith / Wappalyzer (for technology detection — note: we verify this with structured APIs)
2. Company engineering blog
3. Developer forums, Stack Overflow, GitHub
4. G2, Capterra, TrustRadius reviews (especially search-related)
5. Job postings mentioning technologies
6. Conference talk recordings and slides
7. App store reviews (iOS/Android)

## Output Instructions
Write a comprehensive technology research document. Include inline citations [source](url) for every technology detection claim. Distinguish between CONFIRMED (seen on website, stated in blog) and INFERRED (from job postings, indirect evidence) technology claims.
```

- [ ] **Step 4: Write Cluster D playbook**

```markdown
# prism_platform/v2/clusters/cluster_d_people.md
---
name: cluster-d-people
version: 1.0.0
description: People & Signals deep research
cluster_id: D
cost_tier: deep-research
recency_bias_months: 3
feeds: [intel-social, intel-hiring, intel-news, intel-investor]
---

## Research Mission

Conduct deep research on the people, social signals, and recent events surrounding **{company_name}** ({domain}). Focus on executive statements, leadership changes, social sentiment, and newsworthy events from the last 90 days.

## Depth Allocation

- **70% effort** on {company_name} people and signals
- **30% effort** on competitor leadership and signals for contrast

## What to Discover

### Executive Voice & Priorities
Search for statements from these executives (from seed data):
{executives}

For each executive found speaking publicly:
1. **What are they saying?** Verbatim quotes about strategy, priorities, challenges
2. **Where are they saying it?** LinkedIn posts, Twitter/X, conference talks, podcasts, press interviews, earnings calls
3. **What themes emerge?** Customer experience, digital transformation, AI/ML, operational efficiency, growth, international expansion
4. **Any mentions of search, discovery, or content findability?** These are direct Algolia relevance signals

### Leadership Changes (Last 6 Months)
1. **New hires:** Any new C-suite or VP-level hires? What does their background signal about strategic direction?
2. **Departures:** Any notable departures? What roles are now vacant?
3. **Promotions:** Internal promotions that signal shifting priorities?
4. **Board changes:** New board members with relevant backgrounds?

### News & Events (Last 90 Days)
1. **Company news:** Product launches, partnerships, acquisitions, expansions, earnings announcements
2. **Industry events:** Industry conferences where {company_name} presented or exhibited
3. **Awards/recognition:** Any industry awards or analyst recognition?
4. **Negative signals:** Layoffs, lawsuits, regulatory issues, security breaches

### Social Sentiment
1. **Employee sentiment:** Glassdoor ratings, Blind posts, LinkedIn commentary
2. **Customer sentiment:** Social media complaints or praise about the company's digital experience
3. **Brand perception:** How is {company_name} perceived in their industry?

### Competitor Signals
For key competitors:
1. Any leadership changes that signal competitive moves?
2. Any public statements about technology investments?
3. Any news that shifts the competitive landscape?

## Source Priority
1. LinkedIn posts and articles by executives
2. Twitter/X posts by executives and company accounts
3. Conference recordings and published talks
4. Podcast appearances
5. Press interviews and feature articles
6. Earnings call transcripts (for exec quotes)
7. Glassdoor and Blind (for internal signals)
8. Company press releases and newsroom

## Output Instructions
Write a comprehensive people and signals research document. Include VERBATIM QUOTES whenever possible — exact words matter for downstream sales intelligence. Include inline citations [source](url) for every quote and claim. Focus heavily on recency — signals older than 90 days are much less valuable.
```

- [ ] **Step 5: Write Cluster E playbook**

```markdown
# prism_platform/v2/clusters/cluster_e_buying_signals.md
---
name: cluster-e-buying-signals
version: 1.0.0
description: Buying Signals & Intent Inference deep research
cluster_id: E
cost_tier: deep-research
recency_bias_months: 3
feeds: [intel-hiring, intel-techstack, synth-sales-plays]
---

## Research Mission

Conduct deep research to identify buying signals and technology purchase intent at **{company_name}** ({domain}). Your findings will determine whether this company is likely to be evaluating search/discovery solutions and how urgent their need might be.

## Depth Allocation

- **80% effort** on {company_name} buying signals
- **20% effort** on competitor technology moves that create competitive pressure

## What to Discover

### Hiring Signals
1. **Search/Discovery roles:** Any job postings for Search Engineer, Relevance Engineer, ML Engineer (search/recommendations), NLP Engineer?
2. **Digital experience roles:** VP/Director of Digital Experience, E-commerce Manager, Product Manager (Search), UX Researcher?
3. **Platform engineering roles:** Roles that mention search infrastructure, Elasticsearch, Solr, or search platform migration?
4. **Volume and urgency:** How many open roles? Are they marked urgent? Multiple similar roles suggesting a new team?
5. **Role seniority:** Director/VP level hiring suggests strategic initiative. Individual contributor suggests existing team growth.

### Technology Change Signals
1. **Platform migrations:** Any evidence of e-commerce replatforming? CMS migration? Search vendor evaluation?
2. **Technology removals:** Has {domain} recently removed any search or personalization technology?
3. **RFP signals:** Any RFP postings, vendor comparison articles, or evaluation-related content?
4. **Technology blog posts:** Any engineering posts about search challenges, scalability issues, or architecture decisions?

### Budget & Investment Signals
1. **Recent funding:** Any funding rounds, debt financing, or capital allocation announcements?
2. **Digital investment:** CEO/CFO statements about investing in digital, technology, or customer experience?
3. **Cost pressure signals:** Mentions of consolidating tech stack, reducing vendor count, or optimizing costs?
4. **Technology budget indicators:** IT budget mentions in earnings calls, analyst reports, or press?

### Competitive Pressure Signals
1. **Competitor search investment:** Have any of {company_name}'s competitors recently invested in search/discovery technology?
2. **Competitor using Algolia:** Are any competitors known Algolia customers? (This is the "Golden Angle" — prospect's competitor chose Algolia)
3. **Market pressure:** Are competitors offering better digital experiences that create pressure to invest?
4. **Industry benchmarks:** What are search/discovery conversion benchmarks in this vertical?

### Evaluation Timeline Signals
For each signal found, classify the timing:
- **ACTIVE:** Evidence of current evaluation or active investment (e.g., search engineer hired last month, RFP posted, vendor demos mentioned)
- **EMERGING:** Early signals suggesting future investment (e.g., VP Digital hired, "digital transformation" mentioned in earnings call, job posting for platform architect)
- **LATENT:** Conditions are right but no active signal (e.g., competitor invested in search, industry trend toward better digital experience, but no direct evidence of evaluation)

## Source Priority
1. Job postings (LinkedIn Jobs, Indeed, company careers page, Glassdoor)
2. BuiltWith technology changes (we verify with structured API — look for qualitative context)
3. Funding databases (Crunchbase, SEC EDGAR Form D)
4. Earnings calls and investor presentations (budget signals)
5. Conference talks about search/discovery challenges
6. Engineering blog posts about technical challenges
7. Vendor comparison articles and G2/Capterra reviews
8. RFP databases and procurement portals

## Output Instructions
Write a comprehensive buying signal research document. For each signal found, clearly state:
1. What the signal is (factual description)
2. Why it matters (what it implies about purchase intent)
3. Timing classification (ACTIVE / EMERGING / LATENT)
4. Source citation [source](url)

Be specific about what you found vs what you inferred. Inference is valuable but must be clearly labeled.
```

- [ ] **Step 6: Commit all cluster playbooks**

```bash
git add prism_platform/v2/clusters/
git commit -m "feat(v2): add 5 research cluster playbooks — design artifacts for Phase 2"
```

---

## Task 9: Domain Module Output Schema Catalog (Design Artifacts)

**Files:**
- Create: `prism_platform/v2/modules/schemas_catalog.py`
- Create: `tests/v2/test_schemas_catalog.py`

Pydantic output schemas for each domain module. These are Phase 2 design artifacts — the output contracts that domain modules must produce. Having them defined upfront ensures consistency across the pipeline and allows synthesis modules to be designed against concrete types.

**NOTE:** These schemas are not wired into modules yet. They establish the contracts that Phase 2 module migration will implement.

- [ ] **Step 1: Write the schema catalog**

```python
# prism_platform/v2/modules/schemas_catalog.py
"""Domain module output schema catalog — contracts for all domain modules.

These are Phase 2 design artifacts. Each schema defines the output contract
that a domain module MUST produce. Synthesis modules (business-case, sales-plays)
consume these typed outputs.

Design principles:
- extra="forbid" on every model — reject unexpected fields
- Literal types for constrained strings — no LLM-invented values
- Field descriptions are LLM instructions — write them carefully
- Every factual field has a companion _source or evidence_tier field
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# intel-techstack
# ---------------------------------------------------------------------------


class DetectedTechnology(BaseModel):
    """A technology detected on the prospect's website."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Technology name, e.g. 'Elasticsearch', 'React'")
    category: Literal[
        "search", "ecommerce_platform", "frontend", "analytics",
        "cdn", "personalization", "ab_testing", "cms", "payment",
        "tag_manager", "advertising", "other",
    ] = Field(description="Technology category")
    status: Literal["ACTIVE", "TAG_ONLY", "REMOVED", "UNDETECTED"] = Field(
        description="ACTIVE=currently in use, TAG_ONLY=JS tag but no product usage, "
        "REMOVED=was present but removed, UNDETECTED=not found"
    )
    detection_source: Literal["builtwith", "similarweb", "research", "manual"] = Field(
        description="How this technology was detected"
    )
    first_detected: date | None = Field(default=None, description="When first seen")
    last_detected: date | None = Field(default=None, description="When last confirmed")


class TechStackOutput(BaseModel):
    """Output from intel-techstack module."""

    model_config = ConfigDict(extra="forbid")

    search_vendor: str | None = Field(
        default=None,
        description="Primary search vendor, e.g. 'Elasticsearch', 'Algolia', 'Coveo'. None if undetected.",
    )
    search_vendor_status: Literal["ACTIVE", "TAG_ONLY", "REMOVED", "UNDETECTED"] = Field(
        default="UNDETECTED"
    )
    search_vendor_evidence_tier: Literal["VERIFIED", "WEBFETCH", "WEBSEARCH", "ESTIMATE"] = Field(
        default="WEBSEARCH"
    )
    ecommerce_platform: str | None = Field(
        default=None,
        description="Primary ecommerce platform, e.g. 'Salesforce Commerce Cloud', 'Shopify Plus'",
    )
    all_technologies: list[DetectedTechnology] = Field(default_factory=list)
    migration_signals: list[str] = Field(
        default_factory=list,
        description="Evidence of technology changes or migrations",
    )


# ---------------------------------------------------------------------------
# intel-traffic
# ---------------------------------------------------------------------------


class TrafficMetrics(BaseModel):
    """Traffic and engagement metrics from SimilarWeb."""

    model_config = ConfigDict(extra="forbid")

    monthly_visits: int | None = Field(default=None, description="Monthly unique visits estimate")
    bounce_rate: float | None = Field(default=None, description="Bounce rate as decimal, e.g. 0.45")
    pages_per_visit: float | None = Field(default=None, description="Average pages per session")
    avg_visit_duration_seconds: int | None = Field(default=None)
    device_split_desktop: float | None = Field(default=None, description="Desktop share as decimal")
    device_split_mobile: float | None = Field(default=None, description="Mobile share as decimal")


class TrafficSource(BaseModel):
    """Traffic source breakdown."""

    model_config = ConfigDict(extra="forbid")

    source: Literal["direct", "referral", "search_organic", "search_paid", "social", "email", "display"] = Field(
        description="Traffic source type"
    )
    share: float = Field(description="Share of total traffic as decimal, e.g. 0.35")


class TrafficOutput(BaseModel):
    """Output from intel-traffic module."""

    model_config = ConfigDict(extra="forbid")

    prospect: TrafficMetrics = Field(default_factory=TrafficMetrics)
    traffic_sources: list[TrafficSource] = Field(default_factory=list)
    top_keywords_organic: list[str] = Field(default_factory=list, description="Top 10 organic keywords")
    top_keywords_paid: list[str] = Field(default_factory=list, description="Top 10 paid keywords")
    global_rank: int | None = Field(default=None, description="SimilarWeb global rank")
    country_rank: int | None = Field(default=None)
    competitor_comparison: dict[str, TrafficMetrics] = Field(
        default_factory=dict,
        description="Competitor domain → their traffic metrics",
    )


# ---------------------------------------------------------------------------
# intel-financials (unified — branches on is_public)
# ---------------------------------------------------------------------------


class FinancialYear(BaseModel):
    """One year of financial data."""

    model_config = ConfigDict(extra="forbid")

    fiscal_year: str = Field(description="e.g. 'FY2025' or '2024'")
    revenue_usd: float | None = Field(default=None, description="Revenue in USD")
    revenue_growth_yoy: float | None = Field(default=None, description="YoY growth as decimal, e.g. 0.18")
    ebitda_margin: float | None = Field(default=None, description="EBITDA margin as decimal")
    digital_revenue_usd: float | None = Field(default=None, description="Digital/ecommerce revenue if broken out")
    evidence_tier: Literal["VERIFIED", "WEBFETCH", "WEBSEARCH", "ESTIMATE"] = "WEBSEARCH"
    source: str = Field(default="", description="Source citation, e.g. 'SEC 10-K FY2025'")


class FinancialsOutput(BaseModel):
    """Output from intel-financials module (public or private)."""

    model_config = ConfigDict(extra="forbid")

    is_public: bool
    financial_years: list[FinancialYear] = Field(default_factory=list, description="Last 3 years")
    analyst_consensus: str | None = Field(
        default=None,
        description="Buy/Hold/Sell consensus if public",
    )
    digital_revenue_share: float | None = Field(
        default=None,
        description="Digital as % of total revenue, decimal",
    )
    key_financial_insight: str = Field(
        default="",
        description="One-paragraph synthesis: what the financial data means for an Algolia pitch",
    )


# ---------------------------------------------------------------------------
# intel-investor
# ---------------------------------------------------------------------------


class ExecQuote(BaseModel):
    """A verbatim executive quote from earnings calls or public statements."""

    model_config = ConfigDict(extra="forbid")

    speaker: str = Field(description="Executive name and title")
    quote: str = Field(description="Verbatim quote — exact words, not paraphrased")
    context: str = Field(description="Where this was said: earnings call, conference, LinkedIn, etc.")
    date: str = Field(description="Date of statement, YYYY-MM-DD")
    source_url: str = Field(description="URL to source")
    algolia_relevance: Literal["high", "medium", "low"] = Field(
        description="How relevant is this quote to an Algolia sales conversation?"
    )


class InvestorOutput(BaseModel):
    """Output from intel-investor module."""

    model_config = ConfigDict(extra="forbid")

    exec_quotes: list[ExecQuote] = Field(default_factory=list)
    strategic_priorities: list[str] = Field(
        default_factory=list,
        description="Top 3-5 strategic priorities extracted from executive communications",
    )
    risk_factors: list[str] = Field(
        default_factory=list,
        description="Key risk factors from 10-K or research (search/digital relevant)",
    )
    said_vs_found: list[str] = Field(
        default_factory=list,
        description=(
            "Contradictions between what execs say and what we observe. "
            "e.g. 'CEO says customer experience is #1 priority, but search scores 3/10'"
        ),
    )


# ---------------------------------------------------------------------------
# intel-hiring
# ---------------------------------------------------------------------------


class JobPosting(BaseModel):
    """A discovered job posting."""

    model_config = ConfigDict(extra="forbid")

    title: str
    department: str | None = None
    location: str | None = None
    posted_date: str | None = Field(default=None, description="YYYY-MM-DD")
    url: str | None = None
    icp_tier: Literal["economic_buyer", "technical_buyer", "champion", "influencer", "end_user"] | None = Field(
        default=None,
        description="MEDDPICC classification of this role's buyer type",
    )
    algolia_relevance: Literal["high", "medium", "low"] = Field(
        default="low",
        description="high=search/relevance/ML role, medium=digital/ecom role, low=other",
    )
    buying_signal_strength: Literal["ACTIVE", "EMERGING", "LATENT"] = Field(
        default="LATENT",
    )


class HiringOutput(BaseModel):
    """Output from intel-hiring module."""

    model_config = ConfigDict(extra="forbid")

    total_open_roles: int = 0
    algolia_relevant_roles: int = 0
    job_postings: list[JobPosting] = Field(default_factory=list)
    vacancy_signals: list[str] = Field(
        default_factory=list,
        description="Key roles that are vacant — indicates org gaps",
    )
    hiring_insight: str = Field(
        default="",
        description="One-paragraph synthesis: what hiring patterns mean for Algolia opportunity",
    )


# ---------------------------------------------------------------------------
# intel-social
# ---------------------------------------------------------------------------


class SocialPost(BaseModel):
    """An executive or company social media post."""

    model_config = ConfigDict(extra="forbid")

    author: str = Field(description="Who posted — exec name or 'Company Account'")
    platform: Literal["linkedin", "twitter", "other"] = "linkedin"
    content_summary: str = Field(description="One-sentence summary of the post")
    date: str = Field(description="YYYY-MM-DD")
    url: str | None = None
    algolia_relevance: Literal["high", "medium", "low"] = "low"
    themes: list[str] = Field(
        default_factory=list,
        description="Themes: 'digital_transformation', 'customer_experience', 'ai_ml', etc.",
    )


class SocialOutput(BaseModel):
    """Output from intel-social module."""

    model_config = ConfigDict(extra="forbid")

    posts: list[SocialPost] = Field(default_factory=list)
    exec_voice_summary: str = Field(
        default="",
        description="One paragraph: what are executives talking about publicly?",
    )
    dominant_themes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# intel-news
# ---------------------------------------------------------------------------


class NewsItem(BaseModel):
    """A news article about the company."""

    model_config = ConfigDict(extra="forbid")

    headline: str
    source: str = Field(description="Publication name")
    date: str = Field(description="YYYY-MM-DD")
    url: str | None = None
    category: Literal[
        "leadership_change", "product_launch", "partnership",
        "financial", "acquisition", "technology", "expansion",
        "layoff", "regulatory", "other",
    ] = "other"
    urgency_signal: bool = Field(
        default=False,
        description="True if this news creates sales urgency (e.g., new CTO, platform migration)",
    )


class NewsOutput(BaseModel):
    """Output from intel-news module."""

    model_config = ConfigDict(extra="forbid")

    news_items: list[NewsItem] = Field(default_factory=list)
    urgency_summary: str = Field(
        default="",
        description="One paragraph: what recent events create urgency for an Algolia conversation?",
    )


# ---------------------------------------------------------------------------
# intel-competitors (pure synthesis)
# ---------------------------------------------------------------------------


class CompetitorProfile(BaseModel):
    """Competitive profile synthesized from all upstream data."""

    model_config = ConfigDict(extra="forbid")

    company_name: str
    domain: str
    search_vendor: str | None = None
    ecommerce_platform: str | None = None
    monthly_visits: int | None = None
    is_algolia_customer: bool = False
    competitive_advantage: str = Field(
        default="",
        description="One sentence: where this competitor is stronger than the prospect",
    )
    competitive_weakness: str = Field(
        default="",
        description="One sentence: where the prospect is stronger",
    )


class CompetitorsOutput(BaseModel):
    """Output from intel-competitors module."""

    model_config = ConfigDict(extra="forbid")

    competitors: list[CompetitorProfile] = Field(default_factory=list)
    golden_angle: str | None = Field(
        default=None,
        description="If any competitor uses Algolia, this is the 'your competitor chose us' narrative",
    )
    competitive_matrix_summary: str = Field(
        default="",
        description="One paragraph: how the prospect stacks up against competitors on search/digital",
    )
```

- [ ] **Step 2: Write tests for the schema catalog**

```python
# tests/v2/test_schemas_catalog.py
"""Tests for domain module output schemas — contract validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.v2.modules.schemas_catalog import (
    CompetitorProfile,
    CompetitorsOutput,
    DetectedTechnology,
    ExecQuote,
    FinancialYear,
    FinancialsOutput,
    HiringOutput,
    InvestorOutput,
    JobPosting,
    NewsItem,
    NewsOutput,
    SocialOutput,
    SocialPost,
    TechStackOutput,
    TrafficMetrics,
    TrafficOutput,
    TrafficSource,
)


class TestTechStackOutput:
    def test_valid_output(self) -> None:
        t = TechStackOutput(
            search_vendor="Elasticsearch",
            search_vendor_status="ACTIVE",
            search_vendor_evidence_tier="VERIFIED",
            ecommerce_platform="Salesforce Commerce Cloud",
            all_technologies=[
                DetectedTechnology(
                    name="Elasticsearch",
                    category="search",
                    status="ACTIVE",
                    detection_source="builtwith",
                ),
            ],
        )
        assert t.search_vendor == "Elasticsearch"

    def test_rejects_invalid_status(self) -> None:
        with pytest.raises(ValidationError):
            DetectedTechnology(
                name="Test",
                category="search",
                status="MAYBE",  # invalid Literal
                detection_source="builtwith",
            )

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            TechStackOutput(oops="bad")


class TestTrafficOutput:
    def test_valid_output(self) -> None:
        t = TrafficOutput(
            prospect=TrafficMetrics(monthly_visits=5000000, bounce_rate=0.45),
            traffic_sources=[
                TrafficSource(source="search_organic", share=0.35),
                TrafficSource(source="direct", share=0.30),
            ],
        )
        assert t.prospect.monthly_visits == 5000000
        assert len(t.traffic_sources) == 2

    def test_rejects_invalid_source_type(self) -> None:
        with pytest.raises(ValidationError):
            TrafficSource(source="television", share=0.1)  # invalid Literal


class TestFinancialsOutput:
    def test_valid_public(self) -> None:
        f = FinancialsOutput(
            is_public=True,
            financial_years=[
                FinancialYear(
                    fiscal_year="FY2025",
                    revenue_usd=88400000000.0,
                    revenue_growth_yoy=0.08,
                    evidence_tier="VERIFIED",
                    source="SEC 10-K FY2025",
                ),
            ],
            analyst_consensus="Buy",
        )
        assert f.is_public is True
        assert len(f.financial_years) == 1

    def test_valid_private(self) -> None:
        f = FinancialsOutput(
            is_public=False,
            financial_years=[
                FinancialYear(
                    fiscal_year="2024",
                    revenue_usd=50000000.0,
                    evidence_tier="ESTIMATE",
                    source="Crunchbase estimate",
                ),
            ],
        )
        assert f.is_public is False


class TestInvestorOutput:
    def test_valid_with_quotes(self) -> None:
        inv = InvestorOutput(
            exec_quotes=[
                ExecQuote(
                    speaker="Michael Dell, CEO",
                    quote="Customer experience is our number one priority.",
                    context="Q4 FY2025 earnings call",
                    date="2025-03-01",
                    source_url="https://example.com/earnings",
                    algolia_relevance="high",
                ),
            ],
            strategic_priorities=["AI infrastructure", "Customer experience"],
            said_vs_found=["CEO says CX is #1, but search scores 3/10"],
        )
        assert len(inv.exec_quotes) == 1
        assert inv.exec_quotes[0].algolia_relevance == "high"


class TestHiringOutput:
    def test_valid_with_postings(self) -> None:
        h = HiringOutput(
            total_open_roles=150,
            algolia_relevant_roles=3,
            job_postings=[
                JobPosting(
                    title="Senior Search Engineer",
                    department="Engineering",
                    icp_tier="technical_buyer",
                    algolia_relevance="high",
                    buying_signal_strength="ACTIVE",
                ),
            ],
        )
        assert h.algolia_relevant_roles == 3


class TestSocialOutput:
    def test_valid(self) -> None:
        s = SocialOutput(
            posts=[
                SocialPost(
                    author="Michael Dell",
                    platform="linkedin",
                    content_summary="Posted about AI investment strategy",
                    date="2026-03-15",
                    algolia_relevance="medium",
                    themes=["ai_ml", "digital_transformation"],
                ),
            ],
            exec_voice_summary="Executives focused on AI and digital transformation.",
            dominant_themes=["ai_ml", "digital_transformation"],
        )
        assert len(s.posts) == 1


class TestNewsOutput:
    def test_valid(self) -> None:
        n = NewsOutput(
            news_items=[
                NewsItem(
                    headline="Dell appoints new CTO",
                    source="Reuters",
                    date="2026-03-10",
                    category="leadership_change",
                    urgency_signal=True,
                ),
            ],
        )
        assert n.news_items[0].urgency_signal is True

    def test_rejects_invalid_category(self) -> None:
        with pytest.raises(ValidationError):
            NewsItem(
                headline="Test",
                source="Test",
                date="2026-01-01",
                category="gossip",  # invalid Literal
            )


class TestCompetitorsOutput:
    def test_valid_with_golden_angle(self) -> None:
        c = CompetitorsOutput(
            competitors=[
                CompetitorProfile(
                    company_name="HP Inc",
                    domain="hp.com",
                    search_vendor="Algolia",
                    is_algolia_customer=True,
                    competitive_advantage="Stronger consumer brand recognition",
                    competitive_weakness="Weaker enterprise server portfolio",
                ),
            ],
            golden_angle="HP Inc, your direct competitor, chose Algolia for their search experience.",
        )
        assert c.golden_angle is not None
        assert c.competitors[0].is_algolia_customer is True


class TestAllSchemasProduceJsonSchema:
    """Every output schema must produce a valid JSON schema for LLM consumption."""

    @pytest.mark.parametrize("schema_class", [
        TechStackOutput, TrafficOutput, FinancialsOutput,
        InvestorOutput, HiringOutput, SocialOutput,
        NewsOutput, CompetitorsOutput,
    ])
    def test_generates_json_schema(self, schema_class: type) -> None:
        schema = schema_class.model_json_schema()
        assert "properties" in schema
        assert schema.get("additionalProperties") is False
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/v2/test_schemas_catalog.py -v
```
Expected: All tests PASS (~15 tests)

- [ ] **Step 4: Commit**

```bash
git add prism_platform/v2/modules/schemas_catalog.py tests/v2/test_schemas_catalog.py
git commit -m "feat(v2): add domain module schema catalog — output contracts for all domain modules"
```

---

## Summary

| Task | What | Type | Status |
|------|------|------|--------|
| 1 | v2 Core Types (Finding, ModuleConfig, ExecutionContextV2) | Infrastructure | Ready |
| 2 | AgentAPIClient (Perplexity wrapper) | Infrastructure | Ready |
| 3 | PlaybookLoader (markdown → prompt) | Infrastructure | Ready |
| 4 | ModuleExecutor (generic harness) | Infrastructure | Ready |
| 5 | intel-company v2 Schemas (CompanySeedOutput) | PoC | Ready |
| 6 | intel-company v2 Config + Playbook | PoC | Ready |
| 7 | End-to-End Smoke Test | PoC | Ready |
| 8 | 5 Research Cluster Playbooks | Phase 2 Design | Ready |
| 9 | Domain Module Schema Catalog | Phase 2 Design | Ready |

**Estimated total: ~40 tests across 6 test files.**

**What this proves:** The config + playbook + schema + generic executor pattern works. A module is defined by 3 files. The executor never changes. Adding a new capability = writing 3 files.

**What's NOT in this plan (pending architectural discussion):**
- Merge strategy implementation (how to merge Perplexity + OpenAI findings per cluster)
- Rate limiter for parallel Agent API calls
- Citation validation implementation (3-tier URL checking)
- AgentAPIClient streaming support
- Cluster orchestration (how Temporal wires the 5×2 research calls)
- Finding extraction pipeline (research doc → Finding objects via fast model)
- Database schema changes for v2 module results
- v1 → v2 migration path for existing modules
