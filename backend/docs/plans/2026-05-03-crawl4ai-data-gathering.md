# PRISM × Crawl4AI: Authoritative Data Gathering Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Apify and the raw-text-blob approach in PRISM's intel modules with Crawl4AI as the primary structured data gathering layer — crawling corporate websites directly for executive teams, job listings, and investor documents.

**Architecture:** Crawl4AI (Python library, not Docker) provides an `AsyncWebCrawler` with Pydantic-native LLM extraction. A new `Crawl4AIFetcher` class wraps it, sitting alongside the existing `BrowserClient`. The `intel_hiring` module (no fetcher yet = clean slate) gets built first using Crawl4AI natively. The `intel_company` module gets an enhancement pass to add structured extraction on top of its existing text-blob pipeline. Perplexity keeps its role but shifts from primary source to validation/enrichment layer.

**Tech Stack:**
- `crawl4ai` v0.8.x (Python library) — `AsyncWebCrawler`, `LLMExtractionStrategy`, `JsonCssExtractionStrategy`, `BFSDeepCrawlStrategy`
- Pydantic v2 (already PRISM standard)
- Gemini gemini-2.0-flash (PRISM standard LLM) for structured extraction
- PostgreSQL (existing) — no new storage layer needed
- Python asyncio (PRISM is already async-first)

**Validation Risk Surface:**

| Test layer | What it proves | What it does NOT prove |
|---|---|---|
| pytest unit | CrawlOptions → correct Crawl4AI config, schema → Pydantic parse | Actual page fetch, anti-bot bypass |
| VCR cassettes (integration) | Full fetch+extract pipeline on recorded HTML | Live website changes, new bot-detect patterns |
| Live smoke test (1 domain) | Real fetch works end-to-end | Scale, all site structures, edge cases |
| DB/cache integration | module_executions.output JSONB round-trip | Query performance at scale |

Remaining risk after all layers pass: corporate sites can change their DOM structure without warning, breaking CSS extraction schemas. The fallback is LLM extraction (more resilient). Always have both strategies defined per page type.

---

## Open Questions — Discuss With Arijit Before Building

These are real forks in the road. Do NOT default to an assumption; get answers first.

**Q1: Scope of intel_company migration — DECIDED ✅**
Migrate both intel_company AND intel_hiring simultaneously.
intel_company.fetcher.py gets refactored to use Crawl4AIFetcher.
Text-blob approach replaced with structured ExecutiveTeam Pydantic extraction.
BrowserClient retired from intel_company once Crawl4AI extraction is verified.

**Q2: LLM provider for extraction**
Crawl4AI's LLMExtractionStrategy can use any LLM provider. PRISM standard is Gemini flash-lite.
Question: use Gemini for both synthesis AND extraction? Or use a smaller local model (Ollama) for extraction to save cost?
*Recommendation: Gemini flash-lite for extraction — cheap (~$0.0001/1K tokens) and already integrated.*

**Q3: Data freshness cadence**
intel_hiring cache_ttl_days=7. But job boards update daily.
Should we crawl careers pages every 3 days? 1 day? On-demand only?
*Decision needed before building the caching layer.*

**Q4: LinkedIn job board — DECIDED ✅**
If `_discover_careers_url()` finds the careers URL redirects to `linkedin.com/jobs`,
`HiringFetchResult` sets `redirected_to_linkedin=True` + captures `linkedin_redirect_url`.
The API surfaces this to the UI as a user-action prompt:
  > "This company's careers page redirects to LinkedIn. Run Apify LinkedIn scraper?"
If user confirms → launch Apify LinkedIn actor. If no → Perplexity fills the gap.
Apify stays in the stack as an opt-in escalation path, not the default.
`HiringFetchResult` needs two new fields: `redirected_to_linkedin: bool`, `linkedin_redirect_url: str`.

**Q5: PDF content extraction**
For investor relations: 10K and 10Q are PDFs. Crawl4AI can discover PDF links but doesn't natively extract PDF text (it gets raw bytes or HTML redirect).
Do we use a separate PDF extraction step (pypdf, pdfminer)? Or does Crawl4AI's PDF mode handle this?
*Need to verify: `pip install crawl4ai[pdf]` - check if this is in v0.8.x docs.*

---

## File Structure

### New Files
```
prism_platform/
  crawl4ai/
    __init__.py              — exports Crawl4AIFetcher, CrawlTarget, CrawlResult
    client.py                — Crawl4AIFetcher (wraps AsyncWebCrawler)
    types.py                 — CrawlTarget, CrawlOutput (PRISM-native Pydantic)
    schemas/
      __init__.py
      executive.py           — ExecutiveTeam, Executive Pydantic models
      jobs.py                — JobListing, JobBoard CSS extraction schema
      investor.py            — InvestorPage Pydantic model

  v2/modules/intel_hiring/
    fetcher.py               — NEW: crawls careers page via Crawl4AIFetcher
    executor.py              — NEW: orchestrates fetch → classify → output
    activities.py            — NEW: Temporal activities

tests/
  unit/crawl4ai/
    test_client.py           — CrawlOptions → correct AsyncWebCrawler config
    test_schemas.py          — Pydantic extraction schema validation
  integration/crawl4ai/
    test_fetcher_vcr.py      — full fetch+extract with VCR cassettes
  unit/modules/intel_hiring/
    test_fetcher.py          — mock Crawl4AIFetcher, assert OpenRoleV2 output
```

### Modified Files
```
requirements.txt             — add crawl4ai>=0.8.0
prism_platform/config.py     — add GEMINI_API_KEY usage path for Crawl4AI
```

---

## Task 1: Install Crawl4AI and Verify Environment

**Files:**
- Modify: `requirements.txt`
- New: `prism_platform/crawl4ai/__init__.py`

- [ ] **Step 1: Add to requirements.txt**

Add this line to `requirements.txt`:
```
crawl4ai>=0.8.0
```

- [ ] **Step 2: Install and setup**

```bash
pip install -U crawl4ai
crawl4ai-setup
crawl4ai-doctor
```

Expected output from `crawl4ai-doctor`:
```
✅ Python version: 3.x.x (compatible)
✅ Playwright installed
✅ Browser ready
```

- [ ] **Step 3: Write smoke test**

Create `tests/unit/crawl4ai/test_import.py`:
```python
def test_crawl4ai_imports():
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    from crawl4ai import JsonCssExtractionStrategy, LLMExtractionStrategy, LLMConfig
    from crawl4ai import BFSDeepCrawlStrategy
    assert AsyncWebCrawler is not None
```

- [ ] **Step 4: Run import test**

```bash
pytest tests/unit/crawl4ai/test_import.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/unit/crawl4ai/test_import.py
git commit -m "chore: add crawl4ai dependency and import smoke test"
```

---

## Task 2: Build Crawl4AIFetcher — PRISM-native wrapper

**Files:**
- Create: `prism_platform/crawl4ai/types.py`
- Create: `prism_platform/crawl4ai/client.py`
- Create: `prism_platform/crawl4ai/__init__.py`
- Create: `tests/unit/crawl4ai/test_client.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/crawl4ai/test_client.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from prism_platform.crawl4ai.client import Crawl4AIFetcher
from prism_platform.crawl4ai.types import CrawlTarget, CrawlOutput

@pytest.mark.asyncio
async def test_fetch_returns_crawl_output_on_success():
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.markdown = "# Nike Leadership\nJohn Donahoe — CEO"
    mock_result.extracted_content = None
    mock_result.url = "https://about.nike.com/en/leadership"

    with patch("prism_platform.crawl4ai.client.AsyncWebCrawler") as MockCrawler:
        mock_crawler = AsyncMock()
        mock_crawler.arun.return_value = mock_result
        MockCrawler.return_value.__aenter__.return_value = mock_crawler

        fetcher = Crawl4AIFetcher()
        target = CrawlTarget(url="https://about.nike.com/en/leadership")
        output = await fetcher.fetch(target)

    assert output.success is True
    assert "Nike Leadership" in output.markdown
    assert output.url == "https://about.nike.com/en/leadership"

@pytest.mark.asyncio
async def test_fetch_returns_failure_on_crawl_error():
    mock_result = MagicMock()
    mock_result.success = False
    mock_result.error_message = "Connection timeout"

    with patch("prism_platform.crawl4ai.client.AsyncWebCrawler") as MockCrawler:
        mock_crawler = AsyncMock()
        mock_crawler.arun.return_value = mock_result
        MockCrawler.return_value.__aenter__.return_value = mock_crawler

        fetcher = Crawl4AIFetcher()
        target = CrawlTarget(url="https://example.com/leadership")
        output = await fetcher.fetch(target)

    assert output.success is False
    assert output.error == "Connection timeout"
    assert output.markdown == ""

@pytest.mark.asyncio
async def test_fetch_many_runs_concurrently():
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.markdown = "page content"
    mock_result.extracted_content = None
    mock_result.url = "https://example.com"

    with patch("prism_platform.crawl4ai.client.AsyncWebCrawler") as MockCrawler:
        mock_crawler = AsyncMock()
        mock_crawler.arun_many.return_value = iter([mock_result, mock_result])
        MockCrawler.return_value.__aenter__.return_value = mock_crawler

        fetcher = Crawl4AIFetcher()
        targets = [
            CrawlTarget(url="https://example.com/1"),
            CrawlTarget(url="https://example.com/2"),
        ]
        outputs = await fetcher.fetch_many(targets)

    assert len(outputs) == 2
    assert all(o.success for o in outputs)
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
pytest tests/unit/crawl4ai/test_client.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'prism_platform.crawl4ai'"

- [ ] **Step 3: Write types.py**

Create `prism_platform/crawl4ai/types.py`:
```python
"""PRISM-native types for Crawl4AI integration.

These are the types that cross module boundaries — internal Crawl4AI
types (AsyncWebCrawler, CrawlResult) never leak outside this package.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class CrawlTarget(BaseModel):
    """A URL to crawl with optional configuration."""
    model_config = {"frozen": True}

    url: str
    use_js: bool = Field(default=False, description="Enable JS execution for dynamic pages")
    max_pages: int = Field(default=1, description="Max pages to follow (deep crawl)")
    url_pattern: str | None = Field(default=None, description="URL pattern filter for deep crawl")
    cache: bool = Field(default=True, description="Use Crawl4AI cache")
    timeout_ms: int = Field(default=30000, description="Page load timeout in milliseconds")


class CrawlOutput(BaseModel):
    """Result from a Crawl4AI fetch operation."""

    url: str
    success: bool
    markdown: str = ""
    fit_markdown: str = ""
    extracted_content: str | None = None
    error: str = ""
    pages_crawled: int = 1
```

- [ ] **Step 4: Write client.py**

Create `prism_platform/crawl4ai/client.py`:
```python
"""Crawl4AIFetcher — PRISM wrapper around AsyncWebCrawler.

Single entry point for all Crawl4AI operations in PRISM modules.
Keeps Crawl4AI internals (BrowserConfig, CrawlerRunConfig, etc.) out
of module code — modules speak CrawlTarget / CrawlOutput only.
"""
from __future__ import annotations

import json
import structlog

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai import BFSDeepCrawlStrategy, URLPatternFilter, FilterChain
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from .types import CrawlTarget, CrawlOutput

logger = structlog.get_logger(__name__)


class Crawl4AIFetcher:
    """Wraps AsyncWebCrawler for PRISM module use.

    Usage:
        fetcher = Crawl4AIFetcher()
        output = await fetcher.fetch(CrawlTarget(url="https://example.com/leadership"))
    """

    def _build_run_config(self, target: CrawlTarget) -> CrawlerRunConfig:
        cache_mode = CacheMode.ENABLED if target.cache else CacheMode.BYPASS
        md_generator = DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.4, threshold_type="fixed")
        )

        kwargs: dict = {
            "cache_mode": cache_mode,
            "markdown_generator": md_generator,
            "page_timeout": target.timeout_ms,
        }

        if target.max_pages > 1:
            filters: list = []
            if target.url_pattern:
                filters.append(URLPatternFilter(patterns=[target.url_pattern]))
            strategy = BFSDeepCrawlStrategy(
                max_depth=2,
                max_pages=target.max_pages,
                include_external=False,
                filter_chain=FilterChain(filters) if filters else None,
            )
            kwargs["deep_crawl_strategy"] = strategy

        return CrawlerRunConfig(**kwargs)

    async def fetch(self, target: CrawlTarget) -> CrawlOutput:
        """Fetch a single URL."""
        browser_cfg = BrowserConfig(
            headless=True,
            java_script_enabled=target.use_js,
        )
        run_cfg = self._build_run_config(target)

        try:
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(target.url, config=run_cfg)

            if not result.success:
                logger.warning(
                    "[crawl4ai] fetch failed",
                    url=target.url,
                    error=result.error_message,
                )
                return CrawlOutput(url=target.url, success=False, error=result.error_message or "")

            return CrawlOutput(
                url=result.url or target.url,
                success=True,
                markdown=result.markdown or "",
                fit_markdown=getattr(result, "fit_markdown", "") or "",
                extracted_content=result.extracted_content,
            )
        except Exception as exc:
            logger.exception("[crawl4ai] unexpected error", url=target.url, exc=str(exc))
            return CrawlOutput(url=target.url, success=False, error=str(exc))

    async def fetch_many(self, targets: list[CrawlTarget]) -> list[CrawlOutput]:
        """Fetch multiple URLs concurrently."""
        if not targets:
            return []

        # All targets must share same JS/cache settings for a single crawler session
        # Use the first target's settings as the baseline
        browser_cfg = BrowserConfig(
            headless=True,
            java_script_enabled=any(t.use_js for t in targets),
        )

        try:
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                # arun_many expects (urls, config) — use BYPASS for batch to avoid
                # cache key collisions across different targets
                urls = [t.url for t in targets]
                run_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
                results = []
                async for result in await crawler.arun_many(urls, config=run_cfg):
                    results.append(result)

            outputs = []
            for result in results:
                if not result.success:
                    outputs.append(CrawlOutput(
                        url=result.url or "",
                        success=False,
                        error=result.error_message or "",
                    ))
                else:
                    outputs.append(CrawlOutput(
                        url=result.url or "",
                        success=True,
                        markdown=result.markdown or "",
                        fit_markdown=getattr(result, "fit_markdown", "") or "",
                        extracted_content=result.extracted_content,
                    ))
            return outputs

        except Exception as exc:
            logger.exception("[crawl4ai] fetch_many failed", exc=str(exc))
            return [CrawlOutput(url=t.url, success=False, error=str(exc)) for t in targets]
```

- [ ] **Step 5: Write __init__.py**

Create `prism_platform/crawl4ai/__init__.py`:
```python
from .client import Crawl4AIFetcher
from .types import CrawlTarget, CrawlOutput

__all__ = ["Crawl4AIFetcher", "CrawlTarget", "CrawlOutput"]
```

- [ ] **Step 6: Run tests — verify PASS**

```bash
pytest tests/unit/crawl4ai/test_client.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 7: Commit**

```bash
git add prism_platform/crawl4ai/ tests/unit/crawl4ai/test_client.py
git commit -m "feat(crawl4ai): add Crawl4AIFetcher wrapper with CrawlTarget/CrawlOutput types"
```

---

## Task 3: Executive Extraction Schema

**Files:**
- Create: `prism_platform/crawl4ai/schemas/executive.py`
- Create: `tests/unit/crawl4ai/test_schemas.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/crawl4ai/test_schemas.py`:
```python
import json
from prism_platform.crawl4ai.schemas.executive import ExecutiveTeam, Executive
from prism_platform.crawl4ai.schemas.executive import build_executive_extraction_strategy

def test_executive_pydantic_schema_valid():
    team = ExecutiveTeam(executives=[
        Executive(
            name="John Donahoe",
            title="President & CEO",
            bio="Previously CEO of ServiceNow",
            linkedin_url="https://www.linkedin.com/in/johndonahoe/"
        )
    ])
    assert team.executives[0].name == "John Donahoe"
    assert team.executives[0].title == "President & CEO"

def test_executive_defaults_empty():
    exec_ = Executive(name="Jane Smith", title="CFO")
    assert exec_.bio == ""
    assert exec_.linkedin_url == ""

def test_build_extraction_strategy_requires_api_key():
    # strategy should raise if no LLM config provided
    import pytest
    with pytest.raises((ValueError, Exception)):
        build_executive_extraction_strategy(llm_api_key=None)

def test_build_extraction_strategy_returns_strategy():
    strategy = build_executive_extraction_strategy(llm_api_key="fake-key")
    assert strategy is not None
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
pytest tests/unit/crawl4ai/test_schemas.py -v
```
Expected: FAIL with ImportError

- [ ] **Step 3: Write executive.py schema**

Create `prism_platform/crawl4ai/schemas/__init__.py`: (empty)

Create `prism_platform/crawl4ai/schemas/executive.py`:
```python
"""Pydantic extraction schema for corporate executive/leadership pages.

Used with Crawl4AI's LLMExtractionStrategy to extract structured
executive team data from unstructured corporate About/Leadership pages.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from crawl4ai import LLMExtractionStrategy, LLMConfig


class Executive(BaseModel):
    """A single C-suite or VP-level executive."""
    model_config = {"frozen": True}

    name: str = Field(description="Full name, e.g. 'John Donahoe'")
    title: str = Field(description="Job title, e.g. 'President & CEO'")
    bio: str = Field(default="", description="Brief professional background, 1-2 sentences")
    linkedin_url: str = Field(
        default="",
        description="Full LinkedIn profile URL if present on the page, else empty string"
    )


class ExecutiveTeam(BaseModel):
    """Complete executive team extracted from a leadership page."""

    executives: list[Executive] = Field(
        description="All C-suite and VP-level executives found. Max 20 entries."
    )
    source_url: str = Field(default="", description="The page URL this was extracted from")


_EXTRACTION_INSTRUCTION = (
    "Extract all C-suite and VP-level executives from this corporate leadership page. "
    "Include: CEO, CFO, CTO, COO, CMO, CPO, CRO, and any Vice Presidents. "
    "For each person, capture their full name, exact job title, a brief bio if available, "
    "and their LinkedIn URL if a link is visible on the page. "
    "Do NOT include board of directors unless they also hold an executive role. "
    "Return an empty list if no executives are found."
)


def build_executive_extraction_strategy(
    llm_api_key: str | None,
    provider: str = "gemini/gemini-2.0-flash",
) -> LLMExtractionStrategy:
    """Build an LLMExtractionStrategy for executive page extraction.

    Args:
        llm_api_key: API key for the LLM provider. Required.
        provider: LLM provider string in Crawl4AI format.

    Raises:
        ValueError: if llm_api_key is None or empty.
    """
    if not llm_api_key:
        raise ValueError("llm_api_key is required for executive extraction strategy")

    return LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider=provider,
            api_token=llm_api_key,
        ),
        schema=ExecutiveTeam.model_json_schema(),
        extraction_type="schema",
        instruction=_EXTRACTION_INSTRUCTION,
        extra_args={"temperature": 0, "max_tokens": 2000},
    )
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
pytest tests/unit/crawl4ai/test_schemas.py -v
```
Expected: PASS (note: test_build_extraction_strategy_requires_api_key tests the ValueError)

- [ ] **Step 5: Commit**

```bash
git add prism_platform/crawl4ai/schemas/ tests/unit/crawl4ai/test_schemas.py
git commit -m "feat(crawl4ai): add ExecutiveTeam Pydantic extraction schema"
```

---

## Task 4: Job Listings CSS Extraction Schema

**Files:**
- Create: `prism_platform/crawl4ai/schemas/jobs.py`
- Modify: `tests/unit/crawl4ai/test_schemas.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/unit/crawl4ai/test_schemas.py`:
```python
from prism_platform.crawl4ai.schemas.jobs import (
    build_jobs_css_schema,
    JOBS_CSS_SCHEMAS,
    JobBoardPlatform,
)

def test_jobs_css_schema_has_all_platforms():
    for platform in JobBoardPlatform:
        assert platform in JOBS_CSS_SCHEMAS, f"Missing schema for {platform}"

def test_jobs_css_schema_has_required_fields():
    for platform, schema in JOBS_CSS_SCHEMAS.items():
        assert "name" in schema
        assert "baseSelector" in schema
        assert "fields" in schema
        field_names = [f["name"] for f in schema["fields"]]
        assert "title" in field_names, f"{platform} missing 'title' field"

def test_build_jobs_css_schema_returns_strategy():
    from crawl4ai import JsonCssExtractionStrategy
    strategy = build_jobs_css_schema(JobBoardPlatform.GENERIC)
    assert isinstance(strategy, JsonCssExtractionStrategy)
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
pytest tests/unit/crawl4ai/test_schemas.py -v
```
Expected: FAIL with ImportError

- [ ] **Step 3: Write jobs.py**

Create `prism_platform/crawl4ai/schemas/jobs.py`:
```python
"""CSS extraction schemas for corporate careers / job listing pages.

Strategy:
  1. Try platform-specific schema first (Workday, Greenhouse, Lever, iCIMS)
  2. Fall back to GENERIC schema if platform unknown
  3. Fall back to LLM extraction if CSS extraction yields 0 results

Each schema extracts: title, location, department, posted_date, url.
These map directly to intel_hiring.schemas.OpenRoleV2 fields.
"""
from __future__ import annotations

from enum import Enum
from crawl4ai import JsonCssExtractionStrategy


class JobBoardPlatform(str, Enum):
    """Known ATS/job board platforms used by enterprise companies."""
    WORKDAY = "workday"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ICIMS = "icims"
    SMARTRECRUITERS = "smartrecruiters"
    GENERIC = "generic"


# CSS schemas per ATS platform.
# baseSelector targets the repeating job card element.
# These selectors are based on known DOM patterns as of Q1 2026.
# Update when ATS platforms change their markup.
JOBS_CSS_SCHEMAS: dict[JobBoardPlatform, dict] = {
    JobBoardPlatform.WORKDAY: {
        "name": "Workday Job Listings",
        "baseSelector": "li[data-automation-id='compositeContainer']",
        "fields": [
            {"name": "title", "selector": "a[data-automation-id='jobTitle']", "type": "text"},
            {"name": "location", "selector": "dd[data-automation-id='locations']", "type": "text"},
            {"name": "department", "selector": "dd[data-automation-id='workerSubType']", "type": "text"},
            {"name": "posted_date", "selector": "dd[data-automation-id='postedOn']", "type": "text"},
            {"name": "url", "selector": "a[data-automation-id='jobTitle']", "type": "attribute", "attribute": "href"},
        ],
    },
    JobBoardPlatform.GREENHOUSE: {
        "name": "Greenhouse Job Listings",
        "baseSelector": "div.opening",
        "fields": [
            {"name": "title", "selector": "a", "type": "text"},
            {"name": "location", "selector": "span.location", "type": "text"},
            {"name": "department", "selector": "section.level-0 > .main-header", "type": "text"},
            {"name": "posted_date", "selector": "", "type": "text"},  # Greenhouse doesn't show dates
            {"name": "url", "selector": "a", "type": "attribute", "attribute": "href"},
        ],
    },
    JobBoardPlatform.LEVER: {
        "name": "Lever Job Listings",
        "baseSelector": "div.posting",
        "fields": [
            {"name": "title", "selector": "h5 a", "type": "text"},
            {"name": "location", "selector": "span.sort-by-location", "type": "text"},
            {"name": "department", "selector": "span.sort-by-team", "type": "text"},
            {"name": "posted_date", "selector": "", "type": "text"},
            {"name": "url", "selector": "h5 a", "type": "attribute", "attribute": "href"},
        ],
    },
    JobBoardPlatform.ICIMS: {
        "name": "iCIMS Job Listings",
        "baseSelector": "div.iCIMS_JobsTable > div.iCIMS_JobsTableRow",
        "fields": [
            {"name": "title", "selector": "a.iCIMS_Anchor", "type": "text"},
            {"name": "location", "selector": "span.iCIMS_Jobs_Location", "type": "text"},
            {"name": "department", "selector": "span.iCIMS_Jobs_Department", "type": "text"},
            {"name": "posted_date", "selector": "", "type": "text"},
            {"name": "url", "selector": "a.iCIMS_Anchor", "type": "attribute", "attribute": "href"},
        ],
    },
    JobBoardPlatform.SMARTRECRUITERS: {
        "name": "SmartRecruiters Job Listings",
        "baseSelector": "li[data-job-id]",
        "fields": [
            {"name": "title", "selector": "h4 a", "type": "text"},
            {"name": "location", "selector": "span.job-location", "type": "text"},
            {"name": "department", "selector": "span.job-department", "type": "text"},
            {"name": "posted_date", "selector": "", "type": "text"},
            {"name": "url", "selector": "h4 a", "type": "attribute", "attribute": "href"},
        ],
    },
    JobBoardPlatform.GENERIC: {
        "name": "Generic Job Listings",
        "baseSelector": "[class*='job'], [class*='position'], [class*='opening'], [class*='vacancy']",
        "fields": [
            {"name": "title", "selector": "h2, h3, h4, a[href*='job'], a[href*='career']", "type": "text"},
            {"name": "location", "selector": "[class*='location'], [class*='city']", "type": "text"},
            {"name": "department", "selector": "[class*='department'], [class*='team'], [class*='category']", "type": "text"},
            {"name": "posted_date", "selector": "time, [class*='date'], [class*='posted']", "type": "text"},
            {"name": "url", "selector": "a", "type": "attribute", "attribute": "href"},
        ],
    },
}


def build_jobs_css_schema(platform: JobBoardPlatform) -> JsonCssExtractionStrategy:
    """Build a JsonCssExtractionStrategy for a specific job board platform."""
    schema = JOBS_CSS_SCHEMAS[platform]
    return JsonCssExtractionStrategy(schema)


def detect_platform(url: str) -> JobBoardPlatform:
    """Detect ATS platform from careers page URL."""
    lower = url.lower()
    if "myworkdayjobs.com" in lower or "wd1.myworkday" in lower:
        return JobBoardPlatform.WORKDAY
    if "greenhouse.io" in lower or "boards.greenhouse" in lower:
        return JobBoardPlatform.GREENHOUSE
    if "jobs.lever.co" in lower or "lever.co" in lower:
        return JobBoardPlatform.LEVER
    if "icims.com" in lower:
        return JobBoardPlatform.ICIMS
    if "smartrecruiters.com" in lower:
        return JobBoardPlatform.SMARTRECRUITERS
    return JobBoardPlatform.GENERIC
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
pytest tests/unit/crawl4ai/test_schemas.py -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add prism_platform/crawl4ai/schemas/jobs.py tests/unit/crawl4ai/test_schemas.py
git commit -m "feat(crawl4ai): add CSS extraction schemas for Workday/Greenhouse/Lever/iCIMS job boards"
```

---

## Task 5: intel_hiring Fetcher

**Files:**
- Create: `prism_platform/v2/modules/intel_hiring/fetcher.py`
- Create: `tests/unit/modules/intel_hiring/test_fetcher.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/modules/intel_hiring/test_fetcher.py`:
```python
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from prism_platform.v2.modules.intel_hiring.fetcher import HiringFetcher, HiringFetchResult
from prism_platform.v2.modules.intel_hiring.schemas import OpenRoleV2

@pytest.mark.asyncio
async def test_fetch_careers_returns_job_listings():
    mock_output = MagicMock()
    mock_output.success = True
    mock_output.extracted_content = json.dumps([
        {"title": "Senior Search Engineer", "location": "Remote", "department": "Engineering",
         "posted_date": "2026-04-01", "url": "https://jobs.nike.com/12345"}
    ])
    mock_output.markdown = ""

    with patch("prism_platform.v2.modules.intel_hiring.fetcher.Crawl4AIFetcher") as MockFetcher:
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch.return_value = mock_output
        MockFetcher.return_value = mock_fetcher

        fetcher = HiringFetcher()
        result = await fetcher.fetch_careers("nike.com")

    assert result.success is True
    assert len(result.raw_listings) > 0
    assert result.raw_listings[0]["title"] == "Senior Search Engineer"

@pytest.mark.asyncio
async def test_fetch_careers_handles_crawl_failure():
    mock_output = MagicMock()
    mock_output.success = False
    mock_output.error = "404 Not Found"

    with patch("prism_platform.v2.modules.intel_hiring.fetcher.Crawl4AIFetcher") as MockFetcher:
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch.return_value = mock_output
        MockFetcher.return_value = mock_fetcher

        fetcher = HiringFetcher()
        result = await fetcher.fetch_careers("privateco.com")

    assert result.success is False
    assert result.raw_listings == []
    assert "404" in result.error
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
pytest tests/unit/modules/intel_hiring/test_fetcher.py -v
```
Expected: FAIL with ImportError

- [ ] **Step 3: Write fetcher.py**

Create `prism_platform/v2/modules/intel_hiring/fetcher.py`:
```python
"""HiringFetcher — crawls corporate careers pages via Crawl4AI.

Strategy:
  1. Discover careers URL from domain (try common paths + homepage link discovery)
  2. Detect ATS platform (Workday/Greenhouse/Lever/iCIMS or generic)
  3. CSS extraction for known platforms (fast, no LLM cost)
  4. LLM extraction fallback for unknown platforms or zero CSS results
  5. Deep crawl (max 3 pages) for paginated job boards

Returns HiringFetchResult with raw_listings (JSON) for the executor
to classify via ICP tier + build-vs-buy logic.
"""
from __future__ import annotations

import json
import structlog

from pydantic import BaseModel, Field

from prism_platform.crawl4ai import Crawl4AIFetcher, CrawlTarget
from prism_platform.crawl4ai.schemas.jobs import detect_platform, build_jobs_css_schema

logger = structlog.get_logger(__name__)

# Common careers page paths to try (in priority order)
_CAREERS_PATHS = [
    "/careers",
    "/jobs",
    "/careers/jobs",
    "/about/careers",
    "/work-with-us",
    "/join-us",
    "/opportunities",
]


class HiringFetchResult(BaseModel):
    """Raw output from careers page crawl, before ICP classification."""

    domain: str
    careers_url: str = ""
    success: bool = False
    raw_listings: list[dict] = Field(default_factory=list)
    markdown_fallback: str = ""
    error: str = ""
    platform_detected: str = "unknown"

    # LinkedIn escalation path
    redirected_to_linkedin: bool = Field(
        default=False,
        description=(
            "True when the company's careers page redirects to linkedin.com/jobs. "
            "When True, surface a user-action prompt to optionally run the Apify LinkedIn actor."
        ),
    )
    linkedin_redirect_url: str = Field(
        default="",
        description="The full LinkedIn jobs URL if redirected_to_linkedin is True.",
    )


class HiringFetcher:
    """Crawls corporate careers pages and extracts job listing data."""

    def __init__(self) -> None:
        self._client = Crawl4AIFetcher()

    async def _discover_careers_url(self, domain: str) -> str | None:
        """Try common paths to find the careers page URL."""
        base = f"https://{domain}"

        # Try direct paths first (no JS needed — just HTTP)
        target = CrawlTarget(url=base, cache=True, timeout_ms=10000)
        homepage = await self._client.fetch(target)

        if homepage.success:
            # Look for careers links in homepage markdown
            for keyword in ["careers", "/jobs", "join us", "work with us"]:
                for line in homepage.markdown.split("\n"):
                    if keyword.lower() in line.lower() and "http" in line:
                        # Extract URL from markdown link format [text](url)
                        import re
                        urls = re.findall(r'\(https?://[^\)]+\)', line)
                        for url in urls:
                            url = url.strip("()")
                            if domain in url or url.startswith("/"):
                                return url

        # Try direct paths
        for path in _CAREERS_PATHS:
            url = f"{base}{path}"
            result = await self._client.fetch(CrawlTarget(url=url, cache=True, timeout_ms=8000))
            if result.success and len(result.markdown) > 500:
                return url

        return None

    def _detect_linkedin_redirect(self, url: str, result_url: str) -> str | None:
        """Return the LinkedIn URL if a careers page redirected to linkedin.com/jobs, else None."""
        for candidate in (url, result_url):
            if "linkedin.com/jobs" in candidate or "linkedin.com/company" in candidate:
                return candidate
        return None

    async def fetch_careers(self, domain: str) -> HiringFetchResult:
        """Fetch and extract job listings from a company's careers page."""
        careers_url = await self._discover_careers_url(domain)

        if not careers_url:
            logger.warning("[hiring-fetcher] no careers URL found", domain=domain)
            return HiringFetchResult(domain=domain, error="No careers page found", success=False)

        # LinkedIn redirect detection — flag before attempting full crawl
        linkedin_url = self._detect_linkedin_redirect(careers_url, careers_url)
        if linkedin_url:
            logger.info("[hiring-fetcher] careers page redirects to LinkedIn", domain=domain, url=linkedin_url)
            return HiringFetchResult(
                domain=domain,
                careers_url=careers_url,
                success=False,
                redirected_to_linkedin=True,
                linkedin_redirect_url=linkedin_url,
                error="Careers page redirects to LinkedIn — user action required",
            )

        platform = detect_platform(careers_url)
        logger.info(
            "[hiring-fetcher] crawling careers page",
            domain=domain,
            url=careers_url,
            platform=platform.value,
        )

        # Build CrawlTarget with platform-appropriate settings
        use_js = platform.value in ("workday", "smartrecruiters")  # JS-heavy platforms
        target = CrawlTarget(
            url=careers_url,
            use_js=use_js,
            max_pages=3,
            url_pattern=f"*{platform.value}*" if use_js else None,
            cache=True,
        )

        output = await self._client.fetch(target)

        if not output.success:
            return HiringFetchResult(
                domain=domain,
                careers_url=careers_url,
                error=output.error,
                platform_detected=platform.value,
            )

        # Try CSS extraction first
        raw_listings: list[dict] = []
        if output.extracted_content:
            try:
                raw_listings = json.loads(output.extracted_content)
            except (json.JSONDecodeError, ValueError):
                raw_listings = []

        logger.info(
            "[hiring-fetcher] crawl complete",
            domain=domain,
            listings_found=len(raw_listings),
            platform=platform.value,
        )

        return HiringFetchResult(
            domain=domain,
            careers_url=careers_url,
            success=True,
            raw_listings=raw_listings,
            markdown_fallback=output.fit_markdown if not raw_listings else "",
            platform_detected=platform.value,
        )
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
pytest tests/unit/modules/intel_hiring/test_fetcher.py -v
```
Expected: PASS

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```
Expected: no regressions

- [ ] **Step 6: Commit**

```bash
git add prism_platform/v2/modules/intel_hiring/fetcher.py tests/unit/modules/intel_hiring/test_fetcher.py
git commit -m "feat(intel-hiring): add HiringFetcher using Crawl4AI with ATS platform detection"
```

---

## Task 6: Verification

- [ ] **Step 1: Full lint + type check**

```bash
ruff check prism_platform/crawl4ai/ prism_platform/v2/modules/intel_hiring/
ruff format --check prism_platform/crawl4ai/ prism_platform/v2/modules/intel_hiring/
mypy prism_platform/crawl4ai/ --strict
```

- [ ] **Step 2: Full test suite**

```bash
pytest -v --tb=short
```
Expected: all tests PASS, no regressions

- [ ] **Step 3: Live smoke test (1 company)**

```python
# Run manually in .venv/bin/python3 REPL:
import asyncio
from prism_platform.v2.modules.intel_hiring.fetcher import HiringFetcher

async def smoke():
    f = HiringFetcher()
    result = await f.fetch_careers("nike.com")
    print(f"Success: {result.success}")
    print(f"Platform: {result.platform_detected}")
    print(f"Listings found: {len(result.raw_listings)}")
    for r in result.raw_listings[:3]:
        print(f"  - {r.get('title')} @ {r.get('location')}")

asyncio.run(smoke())
```
Expected: success=True, 5+ listings, titles are real job titles.

---

## What This Doesn't Cover (Future Phases)

1. **intel_hiring executor.py** — ICP tier classification + build-vs-buy scoring of raw listings
2. **intel_company enhancement** — add Crawl4AI structured extraction alongside existing BrowserClient
3. **intel_investor** — PDF/10K discovery + extraction
4. **LinkedIn gap** — jobs listed only on LinkedIn.com require a different strategy (Perplexity or targeted search)
5. **Crawl4AI PDF extraction** — verify `crawl4ai[pdf]` for 10K/10Q documents
6. **Production caching** — validate CrawlOutput storage as JSONB in module_executions table
