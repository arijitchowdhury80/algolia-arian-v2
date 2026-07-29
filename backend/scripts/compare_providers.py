"""Compare Perplexity vs Tavily vs SerpApi for company intelligence.

Usage: .venv/bin/python scripts/compare_providers.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")

NUMBERED_CITATION_RE = re.compile(r"\[\d+\]")
CITATION_RE = re.compile(r'\s*\[([\w.\-]+)\]\((https?://[^\)]+)\)')

COMPANIES = [
    ("wayfair.com", "Wayfair"),
    ("chewy.com", "Chewy"),
    ("etsy.com", "Etsy"),
    ("revolve.com", "Revolve"),
    ("goat.com", "GOAT"),
    ("shein.com", "Shein"),
    ("fashionnova.com", "Fashion Nova"),
    ("gymshark.com", "Gymshark"),
    ("ssense.com", "SSENSE"),
    ("nordstrom.com", "Nordstrom"),
]

QUERY_TEMPLATE = """Research the company that owns {domain}. Return:
1. Legal registered name
2. Common/brand name
3. Headquarters city and country
4. Employee count and source
5. Whether publicly traded, stock ticker if yes
6. Annual revenue in USD with source
7. Parent company if subsidiary
8. Industry classification
9. 8-12 named executives with titles and LinkedIn URLs
10. 5-7 direct competitors with website domains
11. Recent news from last 90 days"""


def extract_json_from_text(text: str) -> dict | None:
    """Try to find and parse a JSON object from text."""
    cleaned = CITATION_RE.sub("", text)
    cleaned = NUMBERED_CITATION_RE.sub("", cleaned)
    start = cleaned.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(cleaned)):
        if cleaned[i] == "{":
            depth += 1
        elif cleaned[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(cleaned[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def count_executives(data: dict | None) -> int:
    if not data:
        return 0
    execs = data.get("executives", [])
    if isinstance(execs, list):
        return len(execs)
    return 0


def count_competitors(data: dict | None) -> int:
    if not data:
        return 0
    comps = data.get("competitors", [])
    if isinstance(comps, list):
        return len(comps)
    return 0


def has_citations(text: str) -> int:
    """Count citation-like patterns."""
    url_citations = len(CITATION_RE.findall(text))
    num_citations = len(NUMBERED_CITATION_RE.findall(text))
    return url_citations + num_citations


# --- Perplexity ---
async def call_perplexity(domain: str, company: str) -> dict[str, Any]:
    prompt = QUERY_TEMPLATE.format(domain=domain)
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "sonar",
                    "messages": [
                        {"role": "system", "content": "You are a business intelligence researcher. Return comprehensive, factual data. Cite sources."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 8192,
                },
            )
            resp.raise_for_status()
        elapsed = time.monotonic() - start
        content = resp.json()["choices"][0]["message"]["content"]
        return {"text": content, "elapsed": elapsed, "chars": len(content), "citations": has_citations(content)}
    except Exception as e:
        return {"text": "", "elapsed": time.monotonic() - start, "chars": 0, "error": str(e), "citations": 0}


# --- Tavily ---
async def call_tavily(domain: str, company: str) -> dict[str, Any]:
    query = f"{company} company {domain} executive team competitors revenue employees headquarters"
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "advanced",
                    "include_answer": True,
                    "max_results": 10,
                },
            )
            resp.raise_for_status()
        elapsed = time.monotonic() - start
        data = resp.json()
        answer = data.get("answer", "")
        results = data.get("results", [])
        source_count = len(results)
        total_content = answer + " ".join(r.get("content", "") for r in results)
        return {
            "text": answer,
            "elapsed": elapsed,
            "chars": len(total_content),
            "citations": source_count,
            "sources": [r.get("url", "") for r in results[:5]],
        }
    except Exception as e:
        return {"text": "", "elapsed": time.monotonic() - start, "chars": 0, "error": str(e), "citations": 0}


# --- SerpApi ---
async def call_serpapi(domain: str, company: str) -> dict[str, Any]:
    query = f"{company} {domain} company executive team revenue employees competitors"
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.get(
                "https://serpapi.com/search.json",
                params={
                    "api_key": SERPAPI_API_KEY,
                    "q": query,
                    "engine": "google",
                    "num": 10,
                },
            )
            resp.raise_for_status()
        elapsed = time.monotonic() - start
        data = resp.json()

        # Extract knowledge graph if present
        kg = data.get("knowledge_graph", {})
        organic = data.get("organic_results", [])
        answer_box = data.get("answer_box", {})

        total_text = json.dumps(kg) + json.dumps(answer_box) + " ".join(
            r.get("snippet", "") for r in organic
        )
        return {
            "text": total_text[:2000],
            "elapsed": elapsed,
            "chars": len(total_text),
            "citations": len(organic),
            "kg_title": kg.get("title", ""),
            "kg_type": kg.get("type", ""),
            "kg_description": (kg.get("description", ""))[:100],
        }
    except Exception as e:
        return {"text": "", "elapsed": time.monotonic() - start, "chars": 0, "error": str(e), "citations": 0}


async def main() -> None:
    print(f"{'Domain':<18} {'Provider':<12} {'Time':>6} {'Chars':>7} {'Cites':>5} {'Notes'}")
    print("-" * 90)

    for domain, company in COMPANIES:
        # Run all 3 in parallel
        pplx, tav, serp = await asyncio.gather(
            call_perplexity(domain, company),
            call_tavily(domain, company),
            call_serpapi(domain, company),
        )

        # Perplexity
        pplx_note = pplx.get("error", "OK")
        print(f"{domain:<18} {'Perplexity':<12} {pplx['elapsed']:>5.1f}s {pplx['chars']:>7} {pplx['citations']:>5}  {pplx_note}")

        # Tavily
        tav_note = tav.get("error", f"OK, {len(tav.get('sources', []))} source URLs")
        print(f"{'':<18} {'Tavily':<12} {tav['elapsed']:>5.1f}s {tav['chars']:>7} {tav['citations']:>5}  {tav_note}")

        # SerpApi
        serp_note = serp.get("error", f"KG: {serp.get('kg_title', '-')}")
        print(f"{'':<18} {'SerpApi':<12} {serp['elapsed']:>5.1f}s {serp['chars']:>7} {serp['citations']:>5}  {serp_note}")

        print()


if __name__ == "__main__":
    asyncio.run(main())
