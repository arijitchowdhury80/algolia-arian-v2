# Crawl4AI — Overview & Core Capabilities
# Source: docs.crawl4ai.com + github.com/unclecode/crawl4ai
# Fetched: 2026-05-03
# Version: v0.8.x (65k+ GitHub stars, 6.6k forks)

## What Is It

Open-source, async-first web crawler designed for LLM pipelines. Converts web pages
to clean Markdown or structured JSON — no API keys required, Apache 2.0 licensed.
Primary use case: feeding structured data into RAG pipelines and AI agents.

## Key Capabilities

### Content Processing
- Raw HTML → clean Markdown with BM25 noise filtering
- `fit_markdown` (filtered) + `raw_markdown` available on every result
- Custom Markdown generation strategies

### Structured Extraction
- **CSS/XPath schema extraction** → `JsonCssExtractionStrategy` — no LLM needed
- **LLM-based extraction** → `LLMExtractionStrategy` + Pydantic model schema
- Chunking: topic-based, regex, sentence-level
- Cosine similarity for semantic content discovery

### Browser Automation
- Session preservation and auth state caching
- Proxy support with authentication
- Full control: headers, cookies, user agents
- Chromium / Firefox / WebKit
- JavaScript execution (sync + async)
- Dynamic content: scroll simulation, lazy-load, IFrame flattening
- Screenshot capture
- Shadow DOM flattening

### Anti-Bot & Stealth
- 3-tier anti-bot system with proxy escalation
- Adaptive crawling that learns website patterns
- Virtual scroll support for infinite-scroll pages

### Deep Crawling
- `BFSDeepCrawlStrategy` — breadth-first (all links at one level before deeper)
- `DFSDeepCrawlStrategy` — depth-first
- `BestFirstCrawlingStrategy` — semantic scoring, visits highest-relevance pages first
- `FilterChain`: URLPatternFilter, DomainFilter, ContentTypeFilter, ContentRelevanceFilter
- `max_depth`, `max_pages`, `score_threshold` controls
- Crash recovery with checkpoint resumption (for cloud/long-running crawls)

### Parallel Crawling
- `arun_many()` — concurrent multi-URL crawling
- `MemoryAdaptiveDispatcher` — auto-adjusts concurrency based on RAM
- Streaming mode: process results as available

## Installation

```bash
pip install -U crawl4ai
crawl4ai-setup      # installs Playwright browsers
crawl4ai-doctor     # verify installation
```

Optional extras:
- `pip install crawl4ai[torch]` — PyTorch clustering
- `pip install crawl4ai[transformer]` — HuggingFace
- `pip install crawl4ai[all]` — everything

**Note:** Docker support is experimental as of v0.8.x. Major revamp planned.
Use as Python library directly — more reliable than Docker sidecar for now.

## Quick Start Pattern

```python
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def main():
    browser_cfg = BrowserConfig(headless=True)
    run_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun("https://example.com", config=run_cfg)
        print(result.markdown)

asyncio.run(main())
```

## CrawlResult Object

Key fields returned from every crawl:
- `result.markdown` — full Markdown conversion
- `result.fit_markdown` — filtered/cleaned Markdown
- `result.extracted_content` — JSON from extraction strategies
- `result.success` — bool
- `result.error_message` — failure details
- `result.crawled_urls` — all pages visited (multi-URL)
- `result.links` — extracted internal + external links
- `result.media` — images, audio, video

## CSS/XPath Schema Extraction (No LLM)

```python
from crawl4ai import JsonCssExtractionStrategy

schema = {
    "name": "Job Listings",
    "baseSelector": "div.job-card",
    "fields": [
        {"name": "title", "selector": "h2.job-title", "type": "text"},
        {"name": "location", "selector": "span.location", "type": "text"},
        {"name": "url", "selector": "a.apply-link", "type": "attribute", "attribute": "href"},
        {"name": "posted_date", "selector": "time", "type": "attribute", "attribute": "datetime"},
    ]
}

strategy = JsonCssExtractionStrategy(schema)
result = await crawler.arun(url, config=CrawlerRunConfig(extraction_strategy=strategy))
data = json.loads(result.extracted_content)
```

## LLM-Based Extraction (Pydantic Schema)

```python
from pydantic import BaseModel, Field
from crawl4ai import LLMExtractionStrategy, LLMConfig

class Executive(BaseModel):
    name: str = Field(description="Full name")
    title: str = Field(description="Job title e.g. CEO, CFO, CTO")
    bio: str = Field(default="", description="Brief bio or background")
    linkedin_url: str = Field(default="", description="LinkedIn profile URL if available")

class ExecutiveTeam(BaseModel):
    executives: list[Executive]

strategy = LLMExtractionStrategy(
    llm_config=LLMConfig(
        provider="gemini/gemini-2.0-flash",   # PRISM uses Gemini
        api_token=os.getenv("GEMINI_API_KEY")
    ),
    schema=ExecutiveTeam.model_json_schema(),
    extraction_type="schema",
    instruction="Extract all C-suite and VP-level executives with their titles and LinkedIn URLs",
    extra_args={"temperature": 0, "max_tokens": 2000}
)
```

Provider options:
- `ollama/llama3.3` — local, no API cost
- `openai/gpt-4o` — OpenAI
- `gemini/gemini-2.0-flash` — Google Gemini (PRISM standard)
- `anthropic/claude-3-5-haiku-20241022` — Anthropic

## Deep Crawling Pattern

```python
from crawl4ai import BFSDeepCrawlStrategy, URLPatternFilter, FilterChain

filter_chain = FilterChain([
    URLPatternFilter(patterns=["*careers*", "*jobs*"]),
])

strategy = BFSDeepCrawlStrategy(
    max_depth=2,
    max_pages=50,
    include_external=False,
    filter_chain=filter_chain,
)

result = await crawler.arun(
    "https://company.com/careers",
    config=CrawlerRunConfig(deep_crawl_strategy=strategy)
)
```

## Markdown Filtering (Content Quality)

```python
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

md_generator = DefaultMarkdownGenerator(
    content_filter=PruningContentFilter(threshold=0.4, threshold_type="fixed")
)
config = CrawlerRunConfig(markdown_generator=md_generator)
```
`threshold=0.4` adds ~50ms overhead. Use for noisy corporate pages.

## Session Management (Multi-Step Pages)

```python
# Reuse same browser tab across requests
config = CrawlerRunConfig(session_id="careers_session_nike")
result1 = await crawler.arun("https://jobs.nike.com/", config=config)
# ... interact/paginate
result2 = await crawler.arun("https://jobs.nike.com/page/2", config=config)
await crawler.kill_session("careers_session_nike")
```

## N8N Integration

- GitHub: `The-AI-Workshops/Crawl4AI-N8N-Agent`
- Pattern: POST URL to webhook → Crawl4AI scrapes → embeds → stores in Qdrant
- Two JSON workflow templates: single-URL webhook + agent workflow
- Also: `golfamigo/n8n-nodes-crawl4j` — n8n custom node (Basic Crawler + Content Extractor)
- Tutorial: n8n community thread + onedollarvps.com/blogs/n8n-with-crawl4ai-tutorial

## Relevant GitHub Repos

- `unclecode/crawl4ai` — main library (65k stars)
- `kaymen99/ai-web-scraper` — leads scraping with Crawl4AI + LLM + Pydantic → CSV
- `The-AI-Workshops/Crawl4AI-N8N-Agent` — Crawl4AI + N8N + Qdrant pipeline
- `golfamigo/n8n-nodes-crawl4j` — custom n8n node for Crawl4AI
