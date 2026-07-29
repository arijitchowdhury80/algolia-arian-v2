# N8N × Crawl4AI Integration Research
# Fetched: 2026-05-03

## Summary

Multiple N8N integrations exist for Crawl4AI. The pattern is mature enough to use as inspiration.
The dominant pattern: POST URL to webhook → Crawl4AI scrapes → embed → store in vector DB.

## Available Integrations

### 1. Official-ish N8N Community Node: golfamigo/n8n-nodes-crawl4j
- GitHub: https://github.com/golfamigo/n8n-nodes-crawl4j
- Two nodes:
  - **Basic Crawler**: general web crawling + content extraction
  - **Content Extractor**: CSS selectors, LLM, or JSON extraction
- Install as custom n8n node

### 2. AI Workshops Agent: The-AI-Workshops/Crawl4AI-N8N-Agent
- GitHub: https://github.com/The-AI-Workshops/Crawl4AI-N8N-Agent
- Full stack: Crawl4AI + N8N + Qdrant
- Workflow templates included:
  - `Crawl4AI___Single_URL_Webhook_Raw.json` — single URL via HTTP POST
  - `Crawl4AI_Agent.json` — multi-step orchestration
- Pattern: webhook → scrape → split → embed → upsert to Qdrant
- Docker Compose setup: Crawl4AI + N8N + Qdrant as services

### 3. N8N Template: Sitemap → Vector Store RAG
- URL: https://n8n.io/workflows/8707-from-sitemap-crawling-to-vector-storage-creating-an-efficient-workflow-for-rag/
- Full pipeline: XML sitemap → crawl pages → deduplicate (Supabase) → clean text → store in vector DB
- Use case: build searchable knowledge bases from any website

### 4. N8N Template: Autonomous AI Crawler
- URL: https://n8n.io/workflows/2315-autonomous-ai-crawler/
- Multi-page autonomous crawling with AI-driven link selection

### 5. Community Tutorial: n8n + Crawl4AI
- Community post: https://community.n8n.io/t/scrape-any-site-with-crawl4ai-and-n8n/192397
- Tutorial: https://onedollarvps.com/blogs/n8n-with-crawl4ai-tutorial

## Architecture Pattern (from AI Workshops repo)

```
[Webhook POST {url}]
    → [Crawl4AI Docker service: POST /crawl]
    → [N8N receives markdown/JSON]
    → [Split text into chunks]
    → [Generate embeddings (OpenAI/Gemini)]
    → [Upsert to Qdrant]
    → [Return success]
```

## PRISM Relevance

N8N is NOT in PRISM's current stack — we use Temporal for orchestration.
The N8N templates are useful as:
1. **Inspiration for pipeline design** — the webhook+chunk+embed pattern is solid
2. **Reference for Crawl4AI Docker API** — shows how to call Crawl4AI as a service
3. **Off-the-shelf option** if we ever want a no-code supplement for quick research

For PRISM specifically, the Python library approach (Task 2 in the plan) is better
because it integrates with our existing async/Pydantic/Temporal stack.

## Key Lesson from N8N Research

The Crawl4AI Docker API (REST) is used by N8N workflows — but the docs say it's
"experimental and may break." The Python library is the stable interface.
For PRISM: use Python library, not the REST API.
