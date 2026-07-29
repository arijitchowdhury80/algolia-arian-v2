# PIP Phase 0 — Claude Code Build Handoff
## Foundation: Infrastructure + First Module + Proof of Pattern

**Give this entire document to Claude Code. It contains everything needed to build Phase 0.**

---

## What You're Building

PIP — the Prospect Intelligence Platform. An AI-powered account intelligence system that orchestrates 20 modules to produce verified, evidence-graded prospect research with competitive benchmarking.

Phase 0 builds the foundation: project scaffolding, database, Temporal.io orchestration, core contracts, and ONE module (intel-techstack) to prove the entire pattern works end-to-end.

## Technology Stack

- **Python 3.12** with `uv` for package management
- **FastAPI** for the HTTP API
- **Temporal.io** (Python SDK `temporalio`) for workflow orchestration
- **PostgreSQL 16** for persistence
- **Redis 7** for caching
- **Pydantic v2** for all data contracts
- **Instructor** library for structured LLM output
- **Docker Compose** for local development
- **Alembic** for database migrations
- **pytest + pytest-asyncio** for testing
- **ruff** for formatting/linting, **mypy** for type checking

## Project Structure

```
pip/
├── pyproject.toml
├── docker-compose.yml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
├── pip/
│   ├── __init__.py
│   ├── main.py                          # FastAPI application
│   ├── config.py                        # Pydantic Settings
│   │
│   ├── core/                            # === CONTRACTS (build first) ===
│   │   ├── __init__.py
│   │   ├── types.py                     # EvidenceTier, Source, ModuleResult, ValidationResult
│   │   ├── module.py                    # ModuleInterface ABC
│   │   ├── schemas.py                   # Shared models: Person, Company, etc.
│   │   └── registry.py                  # MODULE_REGISTRY
│   │
│   ├── orchestrator/                    # === TEMPORAL (build second) ===
│   │   ├── __init__.py
│   │   ├── workflows.py                 # AuditWorkflow
│   │   ├── activities.py                # run_module activity
│   │   ├── worker.py                    # Temporal worker process
│   │   └── wave_resolver.py             # Dependency → wave resolution
│   │
│   ├── db/                              # === DATABASE (build third) ===
│   │   ├── __init__.py
│   │   ├── models.py                    # SQLAlchemy models
│   │   ├── session.py                   # Async session management
│   │   └── queries.py                   # Common query functions
│   │
│   ├── api/                             # === HTTP API (build fourth) ===
│   │   ├── __init__.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── audits.py                # CRUD + trigger workflows
│   │   │   └── modules.py               # Module health + standalone execution
│   │   ├── middleware.py                # CORS, error handling
│   │   └── deps.py                      # FastAPI dependencies
│   │
│   ├── services/                        # === EXTERNAL API CLIENTS ===
│   │   ├── __init__.py
│   │   ├── builtwith.py                 # BuiltWith API client with caching
│   │   └── similarweb.py                # SimilarWeb API client with caching
│   │
│   └── modules/                         # === INTELLIGENCE MODULES ===
│       └── intel_techstack/             # First module (build fifth)
│           ├── __init__.py
│           ├── module.py                # TechStackModule(ModuleInterface)
│           ├── schemas.py               # TechStackInput, TechStackOutput
│           ├── collector.py             # BuiltWith + SimilarWeb API calls
│           ├── validator.py             # Output validation
│           └── tests/
│               ├── __init__.py
│               ├── test_schemas.py
│               ├── test_collector.py
│               └── test_integration.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Shared fixtures
│   └── test_workflow.py                 # Temporal workflow test
│
└── scripts/
    └── start_worker.py                  # Entry point for Temporal worker
```

## Build Order (STRICT — do not skip ahead)

### Task 0.1: Project Scaffolding

```bash
mkdir pip && cd pip
uv init
```

**pyproject.toml** dependencies:
```toml
[project]
name = "pip-platform"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "redis>=5.2",
    "temporalio>=1.9",
    "instructor>=1.7",
    "anthropic>=0.43",
    "httpx>=0.28",
    "tenacity>=9.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.8",
    "mypy>=1.13",
]
```

### Task 0.2: Docker Compose

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: pip
      POSTGRES_USER: pip
      POSTGRES_PASSWORD: pip_dev_password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

**Note:** Temporal dev server runs natively, not in Docker:
```bash
# Install once
brew install temporal  # or: curl -sSf https://temporal.download/cli | sh

# Start dev server (includes Web UI at localhost:8233)
temporal server start-dev
```

**Verify:** `docker compose up -d` starts PostgreSQL and Redis. `temporal server start-dev` starts Temporal. All three accessible.

### Task 0.3: Core Contracts (pip/core/types.py)

This is the DNA. Every module uses these types. Write exactly this:

```python
"""PIP Core Types — immutable contracts for all modules."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class EvidenceTier(str, Enum):
    """How confident are we in this data point?"""
    VERIFIED = "VERIFIED"       # Direct API, SEC filing, official source
    WEBFETCH = "WEBFETCH"       # Third-party page fetched and confirmed
    WEBSEARCH = "WEBSEARCH"     # Found via search, not independently confirmed
    ESTIMATE = "ESTIMATE"       # Derived/inferred, not directly sourced
    NO_SOURCE = "NO_SOURCE"     # Cannot be verified — MUST be dropped


class Source(BaseModel):
    """Provenance for a single data point."""
    field: str
    value: str
    tier: EvidenceTier
    source_url: Optional[str] = None
    source_label: str
    method: str = "direct_api"  # direct_api, scrape, llm_extraction, model_estimate
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    as_of_date: Optional[date] = None
    confidence: Literal["high", "medium", "low"] = "high"
    conflicts_with: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Result of validating a module's output."""
    passed: bool
    checks_run: int
    checks_passed: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ModuleResult(BaseModel):
    """Standard return type for every module execution."""
    module_name: str
    module_version: str
    status: Literal["success", "partial", "failed"]
    output: dict
    sources: list[Source] = Field(default_factory=list)
    duration_ms: int = 0
    llm_calls: int = 0
    llm_cost_usd: float = 0.0
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    executed_at: datetime = Field(default_factory=datetime.utcnow)
```

### Task 0.4: Module Interface (pip/core/module.py)

```python
"""PIP Module Interface — every module implements this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel

from pip.core.types import ModuleResult, ValidationResult


class ExecutionContext(BaseModel):
    """Passed to every module. Provides shared context."""
    audit_id: str
    account_id: str
    domain: str
    company_name: str
    ticker: Optional[str] = None
    is_private: bool = False

    class Config:
        arbitrary_types_allowed = True


class ModuleInterface(ABC):
    """Every module implements this. No exceptions."""

    name: str
    version: str
    description: str
    layer: str  # intelligence, synthesis, quality, delivery

    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    dependencies: list[str] = []
    requires_llm: bool = False

    timeout_seconds: int = 300  # 5 min default
    max_retries: int = 2

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run the module. Returns structured result with provenance."""
        ...

    @abstractmethod
    async def validate(self, result: ModuleResult) -> ValidationResult:
        """Verify the output meets quality standards."""
        ...

    async def health_check(self) -> bool:
        """Check if external dependencies are available."""
        return True
```

### Task 0.5: Database Schema (Alembic migration)

Create the initial migration with these tables:

```sql
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name TEXT NOT NULL,
    domain TEXT UNIQUE NOT NULL,
    vertical TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    ticker TEXT,
    intelligence JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL DEFAULT 'system',
    status TEXT DEFAULT 'pending',
    score NUMERIC(3,1),
    factcheck_score NUMERIC(3,1),
    factcheck_action TEXT,
    config JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE module_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    module_name TEXT NOT NULL,
    module_version TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    wave INTEGER,
    output_json JSONB,
    sources_json JSONB,
    validation_json JSONB,
    duration_ms INTEGER,
    llm_calls INTEGER DEFAULT 0,
    llm_cost_usd NUMERIC(8,4) DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    UNIQUE(audit_id, module_name)
);

CREATE TABLE deliverables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id UUID REFERENCES audits(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    file_key TEXT,
    file_url TEXT,
    file_size_bytes INTEGER,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audits_account ON audits(account_id);
CREATE INDEX idx_audits_status ON audits(status);
CREATE INDEX idx_module_exec_audit ON module_executions(audit_id);
CREATE INDEX idx_module_exec_status ON module_executions(audit_id, status);
```

**Verify:** Run migration. Connect to PostgreSQL. Confirm all 4 tables exist.

### Task 0.6: Temporal Workflow (pip/orchestrator/workflows.py)

For Phase 0, implement a minimal workflow that runs just Wave 1 with one module:

```python
"""PIP Audit Workflow — Temporal orchestration."""

import asyncio
from datetime import timedelta
from dataclasses import dataclass

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from pip.core.types import ModuleResult


@dataclass
class AuditInput:
    audit_id: str
    domain: str
    company_name: str
    ticker: str | None = None
    is_private: bool = False
    modules_to_run: list[str] | None = None  # None = run all


@dataclass
class AuditResult:
    audit_id: str
    status: str
    module_results: dict[str, str]  # module_name -> status


@workflow.defn
class AuditWorkflow:
    """Full prospect audit workflow."""

    @workflow.run
    async def run(self, input: AuditInput) -> AuditResult:
        modules = input.modules_to_run or ["intel-techstack"]

        # Fan-out: run all requested modules in parallel
        results = await asyncio.gather(*[
            workflow.execute_activity(
                "run_module",
                RunModuleInput(
                    audit_id=input.audit_id,
                    module_name=name,
                    domain=input.domain,
                    company_name=input.company_name,
                    ticker=input.ticker,
                    is_private=input.is_private,
                ),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    backoff_coefficient=2.0,
                ),
            )
            for name in modules
        ])

        # Collect results
        module_statuses = {}
        for name, result_json in zip(modules, results):
            module_statuses[name] = result_json.get("status", "unknown")

        overall = "complete" if all(
            s in ("success", "partial") for s in module_statuses.values()
        ) else "failed"

        return AuditResult(
            audit_id=input.audit_id,
            status=overall,
            module_results=module_statuses,
        )


@dataclass
class RunModuleInput:
    audit_id: str
    module_name: str
    domain: str
    company_name: str
    ticker: str | None = None
    is_private: bool = False
```

### Task 0.7: Temporal Activity (pip/orchestrator/activities.py)

```python
"""PIP Activities — module execution as Temporal activities."""

import time
from temporalio import activity

from pip.core.registry import MODULE_REGISTRY
from pip.core.module import ExecutionContext
from pip.orchestrator.workflows import RunModuleInput


@activity.defn(name="run_module")
async def run_module(input: RunModuleInput) -> dict:
    """Execute a single module. Temporal handles retry."""

    module = MODULE_REGISTRY.get(input.module_name)
    if not module:
        return {"status": "failed", "error": f"Unknown module: {input.module_name}"}

    context = ExecutionContext(
        audit_id=input.audit_id,
        account_id="",  # Will be set from DB in later phases
        domain=input.domain,
        company_name=input.company_name,
        ticker=input.ticker,
        is_private=input.is_private,
    )

    try:
        result = await module.execute(context)

        # Validate
        validation = await module.validate(result)
        if not validation.passed:
            activity.logger.warning(
                f"Module {input.module_name} validation warnings: {validation.errors}"
            )

        # TODO Phase 1: persist to PostgreSQL here

        return result.model_dump(mode="json")

    except Exception as e:
        activity.logger.error(f"Module {input.module_name} failed: {e}")
        return {"status": "failed", "error": str(e), "module_name": input.module_name}
```

### Task 0.8: First Module — intel-techstack

**schemas.py:**
```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from pip.core.types import EvidenceTier


class TechStackInput(BaseModel):
    domain: str


class SearchVendor(BaseModel):
    name: str
    status: Literal["ACTIVE", "TAG_ONLY", "REMOVED", "UNDETECTED"]
    detection_source: str
    evidence_tier: EvidenceTier


class TechStackOutput(BaseModel):
    search_vendor: Optional[SearchVendor] = None
    ecommerce_platform: Optional[str] = None
    cms: Optional[str] = None
    cdn: Optional[str] = None
    analytics: list[str] = Field(default_factory=list)
    personalization: list[str] = Field(default_factory=list)
    bot_detection: Optional[str] = None
    all_technologies: list[dict] = Field(default_factory=list)
    removed_technologies: list[dict] = Field(default_factory=list)
    tech_stack_summary: str = ""
    algolia_detected: bool = False
```

**collector.py:** Convert the existing `collect-techstack.py` script into an async class. Keep the BuiltWith API call logic, the `parse-builtwith.js` filter, and the SimilarWeb cross-check. Use `httpx.AsyncClient` instead of `requests`.

**module.py:** Implement `TechStackModule(ModuleInterface)` with:
- `execute()` that calls `collector.collect_all()` and wraps results in `ModuleResult` with `Source` objects
- `validate()` that checks: search_vendor not null, ecommerce_platform not null, at least 5 technologies detected, at least 1 source

**validator.py:** Separate validation logic for reuse in tests.

### Task 0.9: FastAPI Application

```python
# pip/main.py
from fastapi import FastAPI
from pip.api.routers import audits, modules

app = FastAPI(title="PIP — Prospect Intelligence Platform", version="0.1.0")
app.include_router(audits.router, prefix="/api/v1/audits", tags=["audits"])
app.include_router(modules.router, prefix="/api/v1/modules", tags=["modules"])

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
```

**Audits router:** POST to create audit, POST `/{id}/run` to trigger Temporal workflow, GET `/{id}` to get status.

**Modules router:** GET `/` to list modules with health status, POST `/{name}/execute` to run standalone.

### Task 0.10: Temporal Worker

```python
# scripts/start_worker.py
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from pip.orchestrator.workflows import AuditWorkflow
from pip.orchestrator.activities import run_module


async def main():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="pip-audit-queue",
        workflows=[AuditWorkflow],
        activities=[run_module],
    )
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### Task 0.11: Integration Test

```python
# tests/test_workflow.py
import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from pip.orchestrator.workflows import AuditWorkflow, AuditInput
from pip.orchestrator.activities import run_module


@pytest.mark.asyncio
async def test_audit_workflow_runs_techstack():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[AuditWorkflow],
            activities=[run_module],
        ):
            result = await env.client.execute_workflow(
                AuditWorkflow.run,
                AuditInput(
                    audit_id="test-001",
                    domain="brooks.com",
                    company_name="Brooks Running",
                    modules_to_run=["intel-techstack"],
                ),
                id="test-workflow-001",
                task_queue="test-queue",
            )

            assert result.status == "complete"
            assert result.module_results["intel-techstack"] in ("success", "partial")
```

---

## Definition of Done (Phase 0)

All of these must be true before Phase 0 is complete:

- [ ] `docker compose up -d` starts PostgreSQL and Redis
- [ ] `temporal server start-dev` starts Temporal (Web UI at localhost:8233)
- [ ] `alembic upgrade head` creates all 4 database tables
- [ ] `python scripts/start_worker.py` starts the Temporal worker
- [ ] `uvicorn pip.main:app` starts the FastAPI server
- [ ] `POST /api/v1/modules/intel-techstack/execute` with `{"domain": "brooks.com"}` returns a ModuleResult with real BuiltWith data
- [ ] The result contains at least 1 Source object with evidence tier
- [ ] `POST /api/v1/audits` creates an audit record in PostgreSQL
- [ ] `POST /api/v1/audits/{id}/run` triggers Temporal workflow visible in Web UI
- [ ] Temporal Web UI shows the workflow timeline with intel-techstack activity
- [ ] `pytest` passes with all tests green
- [ ] `ruff check .` passes with no errors
- [ ] `mypy pip/` passes with no errors (or only minor third-party stubs missing)

---

## RULES FOR CLAUDE CODE

1. **Show me the file structure before writing any code.**
2. **Write types.py and schemas.py BEFORE implementation code.**
3. **Every function has type annotations.**
4. **Every module has a validate() method that actually checks output quality.**
5. **Write tests alongside implementation, not after.**
6. **Verify each task works before moving to the next.**
7. **If something fails, fix it. Don't skip it and claim it's done.**
8. **Use async/await everywhere — the entire codebase is async.**
9. **Pydantic v2 syntax only — model_validate, model_dump, Field, ConfigDict. Not v1.**
10. **When in doubt, keep it simple. We add complexity in Phase 1, not Phase 0.**
