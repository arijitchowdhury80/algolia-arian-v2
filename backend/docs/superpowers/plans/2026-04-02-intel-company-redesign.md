# intel-company Redesign: Hub-and-Spoke Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign intel-company as the hub module: single Perplexity call returning JSON, deterministic parsing with field-level citation extraction, denormalized accounts table with proper columns, and account_id threaded through the Temporal workflow chain.

**Architecture:** intel-company makes ONE Perplexity `sonar` API call with a composite prompt requesting JSON output. The response is parsed deterministically (json.loads + Pydantic, NO LLM). Inline Perplexity citations `[label](url)` are extracted as field-level Source records. All fields are written to proper columns on the denormalized `accounts` table. account_id is threaded from the API layer through AuditInput → RunModuleInput → ExecutionContext so modules can read/write the accounts table.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async, Alembic, Pydantic v2, httpx, Temporal, PostgreSQL, structlog

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `prism_platform/config.py` | Add `perplexity_model` config setting |
| Modify | `prism_platform/db/models.py` | Denormalize accounts table — add proper columns, drop intelligence JSONB |
| Create | `alembic/versions/005_denormalize_accounts.py` | Alembic migration for accounts schema change |
| Modify | `prism_platform/modules/intel_company/schemas.py` | Update CompanyProfileOutput — extra="ignore", remove Field descriptions (not LLM instructions anymore) |
| Rewrite | `prism_platform/modules/intel_company/collector.py` | Single Perplexity call with composite JSON prompt |
| Create | `prism_platform/modules/intel_company/parser.py` | Deterministic JSON parsing + citation extraction |
| Delete | `prism_platform/modules/intel_company/enricher.py` | Replaced by parser.py — no LLM parsing |
| Modify | `prism_platform/modules/intel_company/module.py` | Rewrite execute() to use collector → parser → write to accounts |
| Modify | `prism_platform/orchestrator/workflows.py` | Add account_id to AuditInput and RunModuleInput |
| Modify | `prism_platform/orchestrator/activities.py` | Pass account_id to ExecutionContext |
| Modify | `prism_platform/api/routers/audits.py` | Pass account_id into AuditInput |
| Create | `tests/test_company_parser.py` | Tests for deterministic parser + citation extraction |
| Create | `tests/test_company_collector_v2.py` | Integration test for single Perplexity call |
| Create | `tests/test_account_id_threading.py` | Verify account_id flows through the chain |
| Create | `scripts/diagnose_pipeline_v2.py` | Updated diagnostic script that runs Jewson end-to-end |

---

### Task 1: Add `perplexity_model` to config

**Files:**
- Modify: `prism_platform/config.py:75-88`
- Modify: `prism_platform/.env.example`

- [ ] **Step 1: Add perplexity_model setting to config.py**

In `prism_platform/config.py`, add after line 88 (`apify_api_key`):

```python
    # Perplexity model selection (sonar = cheap research, sonar-pro = deep research)
    perplexity_model: str = "sonar"
```

- [ ] **Step 2: Add to .env.example**

Add to `.env.example`:

```bash
# Perplexity model (sonar = $0.25/M input, sonar-pro = $3/M input)
PERPLEXITY_MODEL=sonar
```

- [ ] **Step 3: Verify config loads**

Run:
```bash
.venv/bin/python -c "from prism_platform.config import settings; print(f'Model: {settings.perplexity_model}')"
```
Expected: `Model: sonar`

- [ ] **Step 4: Commit**

```bash
git add prism_platform/config.py .env.example
git commit -m "feat: add configurable perplexity_model setting, default to sonar"
```

---

### Task 2: Denormalize accounts table — Alembic migration

**Files:**
- Modify: `prism_platform/db/models.py:28-41`
- Create: `alembic/versions/005_denormalize_accounts.py`

- [ ] **Step 1: Update the Account SQLAlchemy model**

Replace the Account class in `prism_platform/db/models.py` (lines 28-41):

```python
class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identity (populated by intel-company)
    legal_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    headquarters: Mapped[str | None] = mapped_column(Text, nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employee_count_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    year_founded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    business_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    motto: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Classification
    industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    sub_vertical: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    ticker: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_company: Mapped[str | None] = mapped_column(Text, nullable=True)
    revenue_estimate: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    revenue_source: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Website snapshot
    has_search_bar: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    product_categories: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)

    # Nested entities (JSONB arrays — variable-length, always read as a unit)
    executives: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)
    competitors: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)
    recent_news: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)
    recent_blog_posts: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)

    # Field-level source citations (parsed from Perplexity inline citations)
    sources: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

- [ ] **Step 2: Create Alembic migration**

Create `alembic/versions/005_denormalize_accounts.py`:

```python
"""Denormalize accounts table — proper columns replacing intelligence JSONB.

Revision ID: 005
Revises: 004
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns
    op.add_column("accounts", sa.Column("legal_name", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("headquarters", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("employee_count", sa.Integer(), nullable=True))
    op.add_column("accounts", sa.Column("employee_count_source", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("year_founded", sa.Integer(), nullable=True))
    op.add_column("accounts", sa.Column("business_model", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("motto", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("industry", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("sub_vertical", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("parent_company", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("revenue_estimate", sa.Numeric(15, 2), nullable=True))
    op.add_column("accounts", sa.Column("revenue_source", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("has_search_bar", sa.Boolean(), nullable=True))
    op.add_column("accounts", sa.Column("product_categories", JSONB(), server_default="[]"))
    op.add_column("accounts", sa.Column("executives", JSONB(), server_default="[]"))
    op.add_column("accounts", sa.Column("competitors", JSONB(), server_default="[]"))
    op.add_column("accounts", sa.Column("recent_news", JSONB(), server_default="[]"))
    op.add_column("accounts", sa.Column("recent_blog_posts", JSONB(), server_default="[]"))
    op.add_column("accounts", sa.Column("sources", JSONB(), server_default="[]"))

    # Migrate data from intelligence JSONB to proper columns
    op.execute("""
        UPDATE accounts SET
            legal_name = intelligence->>'legal_name',
            headquarters = intelligence->>'headquarters',
            employee_count = (intelligence->>'employee_count')::integer,
            industry = COALESCE(intelligence->>'industry', vertical),
            sub_vertical = intelligence->>'sub_vertical',
            business_model = intelligence->>'business_model',
            revenue_estimate = (intelligence->>'revenue_estimate')::numeric
        WHERE intelligence IS NOT NULL AND intelligence != '{}'::jsonb
    """)

    # Drop old columns
    op.drop_column("accounts", "intelligence")
    op.drop_column("accounts", "vertical")


def downgrade() -> None:
    op.add_column("accounts", sa.Column("intelligence", JSONB(), server_default="{}"))
    op.add_column("accounts", sa.Column("vertical", sa.Text(), nullable=True))
    op.drop_column("accounts", "sources")
    op.drop_column("accounts", "recent_blog_posts")
    op.drop_column("accounts", "recent_news")
    op.drop_column("accounts", "competitors")
    op.drop_column("accounts", "executives")
    op.drop_column("accounts", "product_categories")
    op.drop_column("accounts", "has_search_bar")
    op.drop_column("accounts", "revenue_source")
    op.drop_column("accounts", "revenue_estimate")
    op.drop_column("accounts", "parent_company")
    op.drop_column("accounts", "sub_vertical")
    op.drop_column("accounts", "industry")
    op.drop_column("accounts", "motto")
    op.drop_column("accounts", "business_model")
    op.drop_column("accounts", "year_founded")
    op.drop_column("accounts", "employee_count_source")
    op.drop_column("accounts", "employee_count")
    op.drop_column("accounts", "headquarters")
    op.drop_column("accounts", "legal_name")
```

- [ ] **Step 3: Run migration**

```bash
cd "/Users/arijitchowdhury/Library/CloudStorage/GoogleDrive-arijit.chowdhury@algolia.com/My Drive/AI/COE:PIP:Migrating to App/PIP"
.venv/bin/alembic upgrade head
```
Expected: migration applies without errors.

- [ ] **Step 4: Verify columns exist**

```bash
.venv/bin/python -c "
import asyncio
from sqlalchemy import text
from prism_platform.db.session import async_session_factory
async def check():
    async with async_session_factory() as s:
        r = await s.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='accounts' ORDER BY ordinal_position\"))
        for row in r: print(row[0])
asyncio.run(check())
"
```
Expected: all new columns listed (legal_name, headquarters, employee_count, etc.), no `intelligence` or `vertical`.

- [ ] **Step 5: Commit**

```bash
git add prism_platform/db/models.py alembic/versions/005_denormalize_accounts.py
git commit -m "feat: denormalize accounts table — proper columns replacing intelligence JSONB"
```

---

### Task 3: Thread account_id through Temporal workflow chain

**Files:**
- Modify: `prism_platform/api/routers/audits.py:182-192`
- Modify: `prism_platform/orchestrator/workflows.py:96-134`
- Modify: `prism_platform/orchestrator/activities.py:54-61`
- Modify: `prism_platform/orchestrator/workflows.py:354-362`

- [ ] **Step 1: Add account_id to AuditInput**

In `prism_platform/orchestrator/workflows.py`, modify AuditInput (line 96-107):

```python
@dataclass
class AuditInput:
    """Input for the audit workflow."""

    audit_id: str
    account_id: str
    domain: str
    company_name: str
    ticker: str | None = None
    is_private: bool = False
    modules_to_run: list[str] | None = None
    audit_mode: str = "full"
    skip_modules: list[str] = field(default_factory=list)
    refresh_modules: list[str] = field(default_factory=list)
```

- [ ] **Step 2: Add account_id to RunModuleInput**

In same file, modify RunModuleInput (line 123-133):

```python
@dataclass
class RunModuleInput:
    """Input for the run_module activity."""

    audit_id: str
    account_id: str
    module_name: str
    domain: str
    company_name: str
    ticker: str | None = None
    is_private: bool = False
    wave: int = 0
```

- [ ] **Step 3: Pass account_id when building RunModuleInput in _execute_wave**

In `workflows.py` around line 354, update the RunModuleInput construction to include `account_id=input.account_id`:

```python
        tasks = [
            workflow.execute_activity(
                "run_module",
                RunModuleInput(
                    audit_id=input.audit_id,
                    account_id=input.account_id,
                    module_name=name,
                    domain=input.domain,
                    company_name=input.company_name,
                    ticker=input.ticker,
                    is_private=input.is_private,
                    wave=wave_num,
                ),
                start_to_close_timeout=timeout,
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    backoff_coefficient=2.0,
                ),
            )
            for name in modules
        ]
```

Also update the fire-and-forget block in `_execute_fire_and_forget` (~line 509) and the FactcheckChildWorkflow RunModuleInput (~line 626) with the same `account_id=input.account_id`.

- [ ] **Step 4: Pass account_id in activities.py**

In `prism_platform/orchestrator/activities.py`, change line 56 from `account_id=""` to `account_id=input.account_id`:

```python
    context = ExecutionContext(
        audit_id=input.audit_id,
        account_id=input.account_id,
        domain=input.domain,
        company_name=input.company_name,
        ticker=input.ticker,
        is_private=input.is_private,
    )
```

- [ ] **Step 5: Pass account_id from API router**

In `prism_platform/api/routers/audits.py`, modify `run_audit()` at line 182:

```python
            AuditInput(
                audit_id=str(audit_id),
                account_id=str(account.id),
                domain=account.domain,
                company_name=account.company_name,
                ticker=account.ticker,
                is_private=not account.is_public,
                audit_mode=body.audit_mode,
                modules_to_run=body.modules_to_run,
                skip_modules=body.skip_modules,
                refresh_modules=body.refresh_modules,
            ),
```

- [ ] **Step 6: Verify import still works**

```bash
.venv/bin/python -c "from prism_platform.orchestrator.workflows import AuditInput, RunModuleInput; print('OK')"
```
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add prism_platform/orchestrator/workflows.py prism_platform/orchestrator/activities.py prism_platform/api/routers/audits.py
git commit -m "feat: thread account_id through AuditInput → RunModuleInput → ExecutionContext"
```

---

### Task 4: Create deterministic parser with citation extraction

**Files:**
- Create: `prism_platform/modules/intel_company/parser.py`
- Create: `tests/test_company_parser.py`

- [ ] **Step 1: Write the failing test for citation extraction**

Create `tests/test_company_parser.py`:

```python
"""Tests for intel-company deterministic parser — citation extraction + JSON parsing."""

import pytest

from prism_platform.modules.intel_company.parser import (
    extract_citations,
    strip_citations,
    parse_perplexity_json,
)


class TestExtractCitations:
    def test_extracts_single_citation(self):
        text = '"employee_count": 3500, [cbinsights](https://www.cbinsights.com/company/jewson)'
        citations = extract_citations(text)
        assert len(citations) >= 1
        assert any(c["source_label"] == "cbinsights" for c in citations)
        assert any("cbinsights.com" in c["source_url"] for c in citations)

    def test_extracts_multiple_citations(self):
        text = (
            '"year_founded": 1836, [news.sky](https://news.sky.com/story/jewson) '
            '"parent_company": "STARK" [cvc](https://www.cvc.com/media/news/2022/)'
        )
        citations = extract_citations(text)
        assert len(citations) >= 2
        labels = {c["source_label"] for c in citations}
        assert "news.sky" in labels
        assert "cvc" in labels

    def test_no_citations_returns_empty(self):
        text = '{"legal_name": "Jewson Limited"}'
        citations = extract_citations(text)
        assert citations == []


class TestStripCitations:
    def test_strips_inline_citation(self):
        text = '"employee_count_source": "LinkedIn data [cbinsights](https://www.cbinsights.com/company/jewson)"'
        result = strip_citations(text)
        assert "[cbinsights]" not in result
        assert "cbinsights.com" not in result
        assert "LinkedIn data" in result

    def test_preserves_non_citation_brackets(self):
        text = '"product_categories": ["Building materials", "Timber"]'
        result = strip_citations(text)
        assert result == text


class TestParsePerplexityJson:
    def test_parses_minimal_valid_json(self):
        raw = '''{
            "legal_name": "Jewson Limited",
            "common_name": "Jewson",
            "domain": "jewson.co.uk",
            "headquarters": "Coventry, England, UK",
            "business_model": "Jewson is a builders merchant supplying building materials to trade professionals across the UK through 500+ branches and online.",
            "industry": "Building materials distribution",
            "is_public": false,
            "executives": [],
            "competitors": [],
            "recent_news": [],
            "recent_blog_posts": []
        }'''
        profile, sources = parse_perplexity_json(raw)
        assert profile.legal_name == "Jewson Limited"
        assert profile.domain == "jewson.co.uk"
        assert profile.is_public is False

    def test_parses_json_with_citations_and_extracts_sources(self):
        raw = '''{
            "legal_name": "Jewson Limited",
            "common_name": "Jewson",
            "domain": "jewson.co.uk",
            "headquarters": "Coventry, England, UK",
            "employee_count": 3500,
            "employee_count_source": "LinkedIn data [cbinsights](https://www.cbinsights.com/company/jewson)",
            "business_model": "Jewson is a builders merchant supplying building materials to trade professionals across the UK through 500+ branches and online.",
            "industry": "Building materials distribution",
            "is_public": false,
            "executives": [],
            "competitors": [],
            "recent_news": [],
            "recent_blog_posts": []
        }'''
        profile, sources = parse_perplexity_json(raw)
        assert profile.employee_count == 3500
        assert "cbinsights" not in profile.employee_count_source
        assert len(sources) >= 1
        assert any("cbinsights.com" in s["source_url"] for s in sources)

    def test_ignores_extra_fields(self):
        raw = '''{
            "legal_name": "Jewson Limited",
            "common_name": "Jewson",
            "domain": "jewson.co.uk",
            "headquarters": "Coventry, England, UK",
            "business_model": "Jewson is a builders merchant supplying building materials to trade professionals across the UK through 500+ branches and online.",
            "industry": "Building materials distribution",
            "is_public": false,
            "executives": [],
            "competitors": [],
            "recent_news": [],
            "recent_blog_posts": [],
            "_notes": {"ownership": "Owned by STARK Group"}
        }'''
        profile, sources = parse_perplexity_json(raw)
        assert profile.legal_name == "Jewson Limited"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_company_parser.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'prism_platform.modules.intel_company.parser'`

- [ ] **Step 3: Implement parser.py**

Create `prism_platform/modules/intel_company/parser.py`:

```python
"""Intel Company parser — deterministic JSON parsing + citation extraction.

Parses Perplexity JSON responses into CompanyProfileOutput. Extracts inline
citations [label](url) as field-level Source records. NO LLM involved.

Data flow:
    raw Perplexity text → extract_citations() → strip_citations() → json.loads() → Pydantic validate
"""

from __future__ import annotations

import json
import re
from typing import Any

import structlog

from prism_platform.modules.intel_company.schemas import CompanyProfileOutput

logger = structlog.get_logger(__name__)

# Matches Perplexity inline citations: [label](url)
CITATION_RE = re.compile(r'\s*\[([\w.\-]+)\]\((https?://[^\)]+)\)')


def extract_citations(raw_text: str) -> list[dict[str, str]]:
    """Extract all inline citations from raw Perplexity response.

    Perplexity annotates facts with [label](url) inline. This function
    extracts every citation as a {source_label, source_url} dict.

    Args:
        raw_text: Raw Perplexity response text (may contain JSON + citations).

    Returns:
        List of dicts with 'source_label' and 'source_url' keys.
    """
    citations: list[dict[str, str]] = []
    for match in CITATION_RE.finditer(raw_text):
        citations.append({
            "source_label": match.group(1),
            "source_url": match.group(2),
        })
    return citations


def strip_citations(raw_text: str) -> str:
    """Remove inline citations from text so JSON parses cleanly.

    Args:
        raw_text: Text with [label](url) annotations.

    Returns:
        Clean text with citations removed.
    """
    return CITATION_RE.sub("", raw_text)


def parse_perplexity_json(
    raw_text: str,
) -> tuple[CompanyProfileOutput, list[dict[str, str]]]:
    """Parse Perplexity JSON response into validated output + field-level sources.

    Steps:
        1. Extract all [label](url) citations from raw text
        2. Strip citations so JSON is parseable
        3. json.loads() the cleaned text
        4. Pydantic model_validate() for type safety

    Args:
        raw_text: Raw Perplexity response (JSON with inline citations).

    Returns:
        Tuple of (CompanyProfileOutput, list of source dicts).

    Raises:
        json.JSONDecodeError: If the response is not valid JSON after stripping.
        pydantic.ValidationError: If the JSON doesn't match the schema.
    """
    logger.info("[Parser] parsing Perplexity JSON response", raw_length=len(raw_text))

    # Step 1: Extract citations before stripping
    citations = extract_citations(raw_text)
    logger.info("[Parser] citations extracted", citation_count=len(citations))

    # Step 2: Strip citations from JSON string
    cleaned = strip_citations(raw_text)

    # Step 3: Parse JSON
    data = json.loads(cleaned)

    # Step 4: Validate with Pydantic (extra="ignore" handles _notes, etc.)
    profile = CompanyProfileOutput.model_validate(data)

    logger.info(
        "[Parser] parsing complete",
        domain=profile.domain,
        legal_name=profile.legal_name,
        executive_count=len(profile.executives),
        competitor_count=len(profile.competitors),
        citation_count=len(citations),
    )

    return profile, citations
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_company_parser.py -v
```
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add prism_platform/modules/intel_company/parser.py tests/test_company_parser.py
git commit -m "feat: add deterministic parser for intel-company — json.loads + citation extraction"
```

---

### Task 5: Update CompanyProfileOutput schema

**Files:**
- Modify: `prism_platform/modules/intel_company/schemas.py`

- [ ] **Step 1: Change extra="forbid" to extra="ignore"**

In `prism_platform/modules/intel_company/schemas.py`, update every model_config:

For `CompanyProfileOutput` (line 149):
```python
    model_config = ConfigDict(extra="ignore")
```

For `Executive` (line 35):
```python
    model_config = ConfigDict(extra="ignore")
```

For `Competitor` (line 81):
```python
    model_config = ConfigDict(extra="ignore")
```

For `NewsItem` (line 101):
```python
    model_config = ConfigDict(extra="ignore")
```

For `BlogPost` (line 126):
```python
    model_config = ConfigDict(extra="ignore")
```

This is necessary because Perplexity may add extra fields like `notes` or `_notes` that aren't in our schema.

- [ ] **Step 2: Remove INTELLIGENCE_FIELDS constant**

Delete lines 260-272 (the `INTELLIGENCE_FIELDS` list and its docstring). This is no longer needed — we write to proper columns now, not a JSONB blob.

- [ ] **Step 3: Verify schemas still import**

```bash
.venv/bin/python -c "from prism_platform.modules.intel_company.schemas import CompanyProfileOutput; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add prism_platform/modules/intel_company/schemas.py
git commit -m "refactor: update CompanyProfileOutput to extra=ignore, remove INTELLIGENCE_FIELDS"
```

---

### Task 6: Rewrite collector — single Perplexity call with JSON output

**Files:**
- Rewrite: `prism_platform/modules/intel_company/collector.py`

- [ ] **Step 1: Rewrite collector.py**

Replace entire content of `prism_platform/modules/intel_company/collector.py`:

```python
"""Intel Company collector — ONE Perplexity call returning JSON + homepage fetch.

Data flow:
    1. Single Perplexity sonar call with composite prompt → JSON response with citations
    2. HTTP GET homepage → search bar regex detection
"""

from __future__ import annotations

import re
from typing import Any

import httpx
import structlog

from prism_platform.config import settings

logger = structlog.get_logger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
HOMEPAGE_TIMEOUT = 15.0
PERPLEXITY_TIMEOUT = 90.0

# Common search input patterns for homepage detection
SEARCH_BAR_PATTERNS = [
    re.compile(r'<input[^>]*type=["\']search["\']', re.IGNORECASE),
    re.compile(r'<input[^>]*name=["\'](?:q|query|search|s)["\']', re.IGNORECASE),
    re.compile(r'<input[^>]*placeholder=["\'][^"\']*search[^"\']*["\']', re.IGNORECASE),
    re.compile(r'role=["\']search["\']', re.IGNORECASE),
    re.compile(r'aria-label=["\'][^"\']*search[^"\']*["\']', re.IGNORECASE),
]


class CompanyCollector:
    """Collects company intelligence via ONE Perplexity call + homepage fetch."""

    async def collect(self, domain: str) -> dict[str, Any]:
        """Run single Perplexity call + homepage fetch.

        Args:
            domain: Website domain to research (e.g. 'jewson.co.uk').

        Returns:
            Dict with keys:
                perplexity_raw: raw text response from Perplexity (JSON with citations)
                has_search_bar: bool | None from homepage regex
                homepage_fetched: whether homepage fetch succeeded
        """
        logger.info("[CompanyCollector] collect started", domain=domain)

        result: dict[str, Any] = {
            "perplexity_raw": "",
            "has_search_bar": None,
            "homepage_fetched": False,
        }

        # Step 1: Single Perplexity call
        try:
            prompt = self._build_prompt(domain)
            result["perplexity_raw"] = await self._call_perplexity(prompt)
            logger.info(
                "[CompanyCollector] Perplexity call completed",
                domain=domain,
                response_length=len(result["perplexity_raw"]),
            )
        except httpx.TimeoutException as exc:
            logger.error("[CompanyCollector] Perplexity timeout", domain=domain, error=str(exc))
            raise
        except httpx.HTTPStatusError as exc:
            logger.error(
                "[CompanyCollector] Perplexity HTTP error",
                domain=domain,
                status_code=exc.response.status_code,
            )
            raise
        except Exception:
            logger.exception("[CompanyCollector] Perplexity unexpected error", domain=domain)
            raise

        # Step 2: Homepage fetch for search bar detection
        try:
            html = await self._fetch_homepage(domain)
            result["has_search_bar"] = self._detect_search_bar(html)
            result["homepage_fetched"] = True
        except Exception as exc:
            logger.warning("[CompanyCollector] homepage fetch failed", domain=domain, error=str(exc))

        logger.info(
            "[CompanyCollector] collect completed",
            domain=domain,
            has_perplexity=bool(result["perplexity_raw"]),
            has_search_bar=result["has_search_bar"],
        )
        return result

    async def _call_perplexity(self, prompt: str) -> str:
        """Call Perplexity chat completions API.

        Args:
            prompt: The user message to send.

        Returns:
            The assistant's response text.
        """
        model = settings.perplexity_model
        async with httpx.AsyncClient(timeout=PERPLEXITY_TIMEOUT) as client:
            resp = await client.post(
                PERPLEXITY_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.perplexity_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a business intelligence researcher. "
                                "Return ONLY valid JSON matching the requested schema. "
                                "No markdown, no commentary outside the JSON object. "
                                "Cite sources inline using [label](url) format after relevant values."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 8192,
                    "return_citations": True,
                },
            )
            resp.raise_for_status()

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            logger.warning("[CompanyCollector] Perplexity returned no choices")
            return ""

        content = choices[0].get("message", {}).get("content", "")

        # Strip markdown code fences if Perplexity wraps JSON in ```json ... ```
        if content.strip().startswith("```"):
            lines = content.strip().split("\n")
            # Remove first line (```json) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            content = "\n".join(lines)

        return content

    async def _fetch_homepage(self, domain: str) -> str:
        """Fetch homepage HTML for search bar detection.

        Args:
            domain: Website domain.

        Returns:
            First 50KB of HTML.
        """
        url = f"https://{domain}"
        logger.info("[CompanyCollector] fetching homepage", url=url)
        async with httpx.AsyncClient(
            timeout=HOMEPAGE_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Prism Intelligence Bot)"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        html = resp.text[:50_000]
        logger.info("[CompanyCollector] homepage fetched", domain=domain, html_length=len(html))
        return html

    @staticmethod
    def _detect_search_bar(html: str) -> bool | None:
        """Detect search bar from homepage HTML using regex patterns.

        Args:
            html: Raw HTML content.

        Returns:
            True if search bar found, False if not, None if html is empty.
        """
        if not html:
            return None
        return any(p.search(html) for p in SEARCH_BAR_PATTERNS)

    @staticmethod
    def _build_prompt(domain: str) -> str:
        """Build composite Perplexity prompt requesting JSON output."""
        return f"""Research the company that owns the website {domain}. Find comprehensive information covering company identity, business model, financials, industry classification, executive team, competitors, and recent activity.

For executives, prioritize: CEO, CTO, CFO, VP Engineering, VP Product, CMO, VP/Head of E-commerce or Digital, VP/Head of Search, VP Data/Analytics, CIO, CDO. Only include real LinkedIn URLs — do not guess.

For competitors, focus on companies that sell similar products/services to similar customers and compete for the same market share.

For recent activity, cover the last 90 days only.

Be specific. Use exact numbers not ranges. Revenue as a raw number in USD. Dates in YYYY-MM-DD format.

Return your response as valid JSON matching this EXACT structure. No markdown, no commentary, just the JSON object:

{{
  "legal_name": "Official registered company name",
  "common_name": "Name used in press/marketing",
  "domain": "{domain}",
  "headquarters": "City, State/Region, Country",
  "year_founded": 1836,
  "employee_count": 6000,
  "employee_count_source": "Where you found the number",
  "business_model": "Minimum 3 sentences describing what the company does, how it makes money, who its customers are",
  "motto": "Company tagline or null",
  "industry": "Primary industry classification",
  "sub_vertical": "More specific sub-vertical",
  "is_public": false,
  "ticker": null,
  "parent_company": "Parent company name or null",
  "revenue_estimate": 62000000.0,
  "revenue_source": "Source and fiscal year of revenue figure",
  "product_categories": ["Category 1", "Category 2"],
  "executives": [
    {{
      "full_name": "John Smith",
      "title": "Chief Executive Officer",
      "linkedin_url": "https://www.linkedin.com/in/johnsmith or null",
      "tenure_description": "Since 2019 or null",
      "previous_company": "Previous employer or null",
      "previous_role": "Previous title or null"
    }}
  ],
  "competitors": [
    {{
      "company_name": "Competitor Inc",
      "domain": "competitor.com",
      "why_competitor": "One sentence explaining competitive relationship",
      "relative_size": "larger"
    }}
  ],
  "recent_news": [
    {{
      "headline": "Article headline",
      "source": "Publication name",
      "date": "2026-03-15",
      "url": "https://example.com/article or null",
      "category": "leadership_change"
    }}
  ],
  "recent_blog_posts": [
    {{
      "title": "Post title",
      "date": "2026-03-15",
      "url": "https://example.com/post or null",
      "summary": "One sentence summary"
    }}
  ]
}}"""
```

- [ ] **Step 2: Verify collector imports**

```bash
.venv/bin/python -c "from prism_platform.modules.intel_company.collector import CompanyCollector; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add prism_platform/modules/intel_company/collector.py
git commit -m "feat: rewrite intel-company collector — single Perplexity call with JSON output"
```

---

### Task 7: Rewrite intel-company module.py — collector → parser → write to accounts

**Files:**
- Modify: `prism_platform/modules/intel_company/module.py`
- Delete: `prism_platform/modules/intel_company/enricher.py`

- [ ] **Step 1: Rewrite module.py execute() method**

Replace entire content of `prism_platform/modules/intel_company/module.py`:

```python
"""Intel Company module — THE FOUNDATION HUB.

This module runs FIRST in every audit. All spoke modules depend on its output.
It populates the accounts table with the canonical company profile.

Data flow:
    1. Collector: ONE Perplexity call (JSON) + homepage fetch
    2. Parser: json.loads + citation extraction + Pydantic validation (NO LLM)
    3. Persist: write every field to proper columns on accounts table
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

import structlog
from sqlalchemy import update

from prism_platform.core.module import ExecutionContext, ModuleInterface
from prism_platform.core.types import EvidenceTier, ModuleResult, Source, ValidationResult
from prism_platform.db.models import Account
from prism_platform.db.session import async_session_factory
from prism_platform.modules.intel_company.collector import CompanyCollector
from prism_platform.modules.intel_company.parser import parse_perplexity_json
from prism_platform.modules.intel_company.schemas import (
    CompanyInput,
    CompanyProfileOutput,
)
from prism_platform.modules.intel_company.validator import validate_output

logger = structlog.get_logger(__name__)

# Known Algolia customers for competitor cross-check
KNOWN_ALGOLIA_CUSTOMERS: set[str] = {
    "twitch.tv", "lacoste.com", "gymshark.com", "stripe.com", "netlify.com",
    "discourse.org", "medium.com", "birchbox.com", "hm.com", "decathlon.com",
    "under-armour.com", "underarmour.com",
}


class CompanyModule(ModuleInterface):
    """Foundation company intelligence module — the hub.

    Produces: canonical company profile written to accounts table.
    Consumed by: every spoke module in the audit pipeline.
    """

    name: ClassVar[str] = "intel-company"
    version: ClassVar[str] = "0.2.0"
    description: ClassVar[str] = (
        "Foundation company intelligence via single Perplexity API call. "
        "Populates accounts table with company identity, executives, "
        "competitors, financials, and field-level source citations."
    )
    layer: ClassVar[str] = "intelligence"

    input_schema: ClassVar[type[CompanyInput]] = CompanyInput
    output_schema: ClassVar[type[CompanyProfileOutput]] = CompanyProfileOutput
    dependencies: ClassVar[list[str]] = []
    requires_llm: ClassVar[bool] = False  # No LLM — deterministic parsing

    timeout_seconds: ClassVar[int] = 120
    max_retries: ClassVar[int] = 2

    def __init__(self) -> None:
        self._collector = CompanyCollector()

    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run company intelligence collection: Perplexity → parse → persist.

        Args:
            context: Execution context with domain, account_id, audit metadata.

        Returns:
            ModuleResult with CompanyProfileOutput and field-level sources.
        """
        logger.info(
            "[CompanyModule] execute started",
            domain=context.domain,
            audit_id=context.audit_id,
            account_id=context.account_id,
        )
        start_ms = time.monotonic_ns() // 1_000_000
        sources: list[Source] = []

        try:
            # Step 1: Collect — ONE Perplexity call + homepage fetch
            raw_data = await self._collector.collect(context.domain)

            if not raw_data.get("perplexity_raw"):
                duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
                logger.error("[CompanyModule] Perplexity returned empty response", domain=context.domain)
                return ModuleResult(
                    module_name=self.name,
                    module_version=self.version,
                    status="failed",
                    output={},
                    sources=sources,
                    duration_ms=duration_ms,
                    llm_calls=1,
                    errors=["Perplexity returned empty response"],
                )

            # Step 2: Parse — deterministic, NO LLM
            output, citations = parse_perplexity_json(raw_data["perplexity_raw"])

            # Apply search bar detection from homepage
            if raw_data.get("has_search_bar") is not None:
                output = output.model_copy(update={"has_search_bar": raw_data["has_search_bar"]})

            # Cross-check competitors against Algolia customer list
            for comp in output.competitors:
                if comp.domain.lower().strip() in KNOWN_ALGOLIA_CUSTOMERS:
                    comp.is_algolia_customer = True

            # Build Source provenance records
            sources.append(
                Source(
                    field="perplexity_response",
                    value=f"Perplexity sonar JSON ({len(raw_data['perplexity_raw'])} chars)",
                    tier=EvidenceTier.WEBSEARCH,
                    source_label="Perplexity API (composite company research)",
                    method="llm_extraction",
                )
            )
            for citation in citations:
                sources.append(
                    Source(
                        field=citation.get("field", "general"),
                        value=citation["source_label"],
                        tier=EvidenceTier.WEBSEARCH,
                        source_url=citation["source_url"],
                        source_label=citation["source_label"],
                        method="llm_extraction",
                    )
                )
            if raw_data.get("homepage_fetched"):
                sources.append(
                    Source(
                        field="has_search_bar",
                        value=f"Homepage fetched, search_bar={raw_data['has_search_bar']}",
                        tier=EvidenceTier.WEBFETCH,
                        source_url=f"https://{context.domain}",
                        source_label=f"{context.domain} homepage",
                        method="scrape",
                    )
                )

            # Step 3: Persist to accounts table
            try:
                await self._update_account(context.account_id, context.domain, output, citations)
            except Exception as exc:
                logger.error(
                    "[CompanyModule] failed to update accounts table",
                    domain=context.domain,
                    error=str(exc),
                )
                # Non-fatal — module result is still valid

            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

            result = ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="success",
                output=output.model_dump(),
                sources=sources,
                duration_ms=duration_ms,
                llm_calls=1,
                llm_cost_usd=0.0,
            )

            logger.info(
                "[CompanyModule] execute completed",
                domain=context.domain,
                status="success",
                duration_ms=duration_ms,
                executives_count=len(output.executives),
                competitors_count=len(output.competitors),
                news_count=len(output.recent_news),
                citation_count=len(citations),
            )
            return result

        except Exception as error:
            duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms
            logger.exception(
                "[CompanyModule] execute failed",
                domain=context.domain,
                audit_id=context.audit_id,
            )
            return ModuleResult(
                module_name=self.name,
                module_version=self.version,
                status="failed",
                output={},
                sources=sources,
                duration_ms=duration_ms,
                errors=[f"{type(error).__name__}: {error}"],
            )

    async def validate(self, result: ModuleResult) -> ValidationResult:
        """Validate module output meets quality standards (8 checks)."""
        logger.info("[CompanyModule] validate started", module=self.name)
        try:
            output = CompanyProfileOutput.model_validate(result.output)
            return validate_output(output, result.sources, expected_domain=output.domain)
        except Exception as error:
            logger.error("[CompanyModule] validate failed", error=str(error))
            return ValidationResult(
                passed=False, checks_run=0, checks_passed=0,
                errors=[f"Output deserialization failed: {error}"],
            )

    async def health_check(self) -> bool:
        """Check if Perplexity API key is configured."""
        from prism_platform.config import settings
        has_perplexity = bool(settings.perplexity_api_key)
        if not has_perplexity:
            logger.warning("[CompanyModule] PERPLEXITY_API_KEY not set")
        return has_perplexity

    async def _update_account(
        self,
        account_id: str,
        domain: str,
        output: CompanyProfileOutput,
        citations: list[dict[str, str]],
    ) -> None:
        """Write every field to proper columns on the accounts table.

        Args:
            account_id: UUID of the account to update.
            domain: Domain of the account.
            output: The structured company profile.
            citations: Field-level source citations from Perplexity.
        """
        if not account_id:
            logger.warning("[CompanyModule] account_id is empty, skipping account update")
            return

        async with async_session_factory() as session:
            try:
                await session.execute(
                    update(Account)
                    .where(Account.id == uuid.UUID(account_id))
                    .values(
                        legal_name=output.legal_name,
                        company_name=output.common_name or output.legal_name,
                        headquarters=output.headquarters,
                        employee_count=output.employee_count,
                        employee_count_source=output.employee_count_source,
                        year_founded=output.year_founded,
                        business_model=output.business_model,
                        motto=output.motto,
                        industry=output.industry,
                        sub_vertical=output.sub_vertical,
                        is_public=output.is_public,
                        ticker=output.ticker,
                        parent_company=output.parent_company,
                        revenue_estimate=output.revenue_estimate,
                        revenue_source=output.revenue_source,
                        has_search_bar=output.has_search_bar,
                        product_categories=[c for c in output.product_categories],
                        executives=[e.model_dump() for e in output.executives],
                        competitors=[c.model_dump() for c in output.competitors],
                        recent_news=[n.model_dump() for n in output.recent_news],
                        recent_blog_posts=[b.model_dump() for b in output.recent_blog_posts],
                        sources=citations,
                        updated_at=datetime.now(UTC),
                    )
                )
                await session.commit()
                logger.info(
                    "[CompanyModule] accounts table updated",
                    account_id=account_id,
                    domain=domain,
                    fields_written=22,
                    citation_count=len(citations),
                )
            except Exception as exc:
                await session.rollback()
                logger.error(
                    "[CompanyModule] accounts table update failed",
                    account_id=account_id,
                    error=str(exc),
                )
                raise
```

- [ ] **Step 2: Delete enricher.py**

```bash
rm prism_platform/modules/intel_company/enricher.py
```

- [ ] **Step 3: Verify module imports and registers**

```bash
.venv/bin/python -c "
from prism_platform.core.registry import register_all_modules, MODULE_REGISTRY
register_all_modules()
mod = MODULE_REGISTRY['intel-company']
print(f'{mod.name} v{mod.version} requires_llm={mod.requires_llm}')
" 2>&1 | grep intel-company
```
Expected: `intel-company v0.2.0 requires_llm=False`

- [ ] **Step 4: Commit**

```bash
git add prism_platform/modules/intel_company/module.py
git rm prism_platform/modules/intel_company/enricher.py
git commit -m "feat: rewrite intel-company module — collector → parser → accounts (no LLM parsing)"
```

---

### Task 8: Run Jewson end-to-end test

**Files:**
- Modify: `scripts/diagnose_pipeline.py`

- [ ] **Step 1: Test intel-company module directly for Jewson**

```bash
.venv/bin/python -c "
import asyncio
from prism_platform.core.registry import register_all_modules, MODULE_REGISTRY
from prism_platform.core.module import ExecutionContext

async def test():
    register_all_modules()
    module = MODULE_REGISTRY['intel-company']
    
    context = ExecutionContext(
        audit_id='test-jewson-001',
        account_id='',
        domain='jewson.co.uk',
        company_name='Jewson',
    )
    
    result = await module.execute(context)
    print(f'Status: {result.status}')
    print(f'Duration: {result.duration_ms}ms')
    print(f'LLM calls: {result.llm_calls}')
    print(f'Sources: {len(result.sources)}')
    print(f'Errors: {result.errors}')
    
    output = result.output
    print(f'legal_name: {output.get(\"legal_name\")}')
    print(f'common_name: {output.get(\"common_name\")}')
    print(f'domain: {output.get(\"domain\")}')
    print(f'headquarters: {output.get(\"headquarters\")}')
    print(f'employee_count: {output.get(\"employee_count\")}')
    print(f'industry: {output.get(\"industry\")}')
    print(f'is_public: {output.get(\"is_public\")}')
    print(f'ticker: {output.get(\"ticker\")}')
    print(f'parent_company: {output.get(\"parent_company\")}')
    print(f'executives: {len(output.get(\"executives\", []))}')
    print(f'competitors: {len(output.get(\"competitors\", []))}')
    print(f'recent_news: {len(output.get(\"recent_news\", []))}')
    
    # Validate
    validation = await module.validate(result)
    print(f'Validation: {\"PASS\" if validation.passed else \"FAIL\"} ({validation.checks_passed}/{validation.checks_run})')
    if validation.errors: print(f'Errors: {validation.errors}')
    if validation.warnings: print(f'Warnings: {validation.warnings}')

asyncio.run(test())
" 2>&1
```

Expected:
- Status: success
- Duration: <15 seconds (vs ~33 seconds before)
- LLM calls: 1 (vs 5 before)
- legal_name: "Jewson Limited" (or similar)
- executives: 3+ entries
- competitors: 3+ entries
- Validation: PASS

- [ ] **Step 2: Run full pipeline diagnostic**

```bash
.venv/bin/python scripts/diagnose_pipeline.py jewson.co.uk Jewson 2>&1 | tail -40
```

Expected: intel-company succeeds. intel-queries may still fail (separate fix needed for account_id in diagnostic script) but intel-competitors health check should now pass.

- [ ] **Step 3: Commit diagnostic results**

```bash
git add scripts/diagnose_pipeline.py
git commit -m "test: verify intel-company redesign with Jewson end-to-end"
```

---

## Test Plan Summary

| Test | What it verifies | Command |
|------|------------------|---------|
| `test_company_parser.py::TestExtractCitations` | Citation regex extracts [label](url) correctly | `pytest tests/test_company_parser.py -k TestExtractCitations -v` |
| `test_company_parser.py::TestStripCitations` | Citation stripping produces clean JSON | `pytest tests/test_company_parser.py -k TestStripCitations -v` |
| `test_company_parser.py::TestParsePerplexityJson` | Full parse: JSON + citations + Pydantic validation | `pytest tests/test_company_parser.py -k TestParsePerplexityJson -v` |
| Module health check | All 20 modules pass health check with Gemini config | Inline python script from Task 8 |
| Jewson integration | intel-company returns success for jewson.co.uk with 1 API call | Inline python script from Task 8 |
| Full pipeline diagnostic | All waves execute, intel-company populates data | `python scripts/diagnose_pipeline.py jewson.co.uk Jewson` |
