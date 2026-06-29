# ADR: PRISM consumes Scout over HTTP for evidence acquisition

**Date:** 2026-06-29
**Status:** Accepted
**Deciders:** Arijit Chowdhury

## Context

PRISM's research/intel tier needs real web evidence (company about/team pages,
careers, investor materials, news, single-URL scrapes). Scout is a purpose-built,
self-hosted **evidence/acquisition engine** (Crawl4AI-based) that already does
crawling, browser/stealth capture, blocked-page evidence, HTML→typed-record
structuring, citation tracking, validation, and artifact writing.

Two ways PRISM could use it:
1. Import `scout.core` as a library (how `prism_platform/browser/tier2_stealth.py`
   currently calls `ScoutCrawler` directly).
2. Call Scout's **HTTP service** (`POST /scrape`, `POST /run/{use_case}`,
   `GET /runs/{id}/records|sources|artifacts`) and consume its outputs.

## Decision

**PRISM calls Scout over its HTTP API and consumes Scout outputs. PRISM does NOT
reimplement crawling, scraping, browser capture, source evidence, citation
tracking, or artifact writing.**

The boundary (from Scout's own docs):
- **Scout** = acquire, crawl, render, capture, structure, cite, validate, artifact.
- **PRISM** = interpret, summarize, score, synthesize, recommend, generate
  prospect intelligence.

New adapter: `prism_platform/integrations/scout.py` — `ScoutClient` (async httpx)
with `scrape()`, `run(use_case)`, `company/news/careers/investor/prism()`
convenience wrappers, and `get_records/get_sources/get_artifacts()`. Lenient
Pydantic consumption models (`ScoutScrapeResult`, `ScoutRun`, `ScoutRecord`,
`ScoutSource`, `ScoutCitation`) ignore unknown Scout fields so Scout schema
evolution never breaks the adapter.

## Why HTTP over library import

- **Clean boundary + deployment independence.** Scout can run as a local service,
  Docker, or remote host; PRISM doesn't inherit Scout's crawler deps or browser
  binaries. (PRISM on the VPS, Scout on the Mac today — HTTP spans that; a direct
  import cannot, since `scout` is a Mac-local path dep.)
- **Provenance is first-class over the wire.** Records carry `citations[]`
  (source_id → source_url, field, claim, confidence); `GET /runs/{id}/sources`
  resolves each source_id to the fetched URL. The adapter preserves both.
- The existing direct-import path (`tier2_stealth.py`) stays for the in-process
  detector use, but new research-tier acquisition goes through the HTTP adapter.

## Grounding rule (consequence)

A Scout record with **empty `citations[]` is NOT evidence-grounded.**
`ScoutRecord.is_grounded` exposes this; PRISM synthesis must gate confidence on
it and check `validation.json` `missing_citations` warnings. This aligns with
PRISM's hard no-fabrication constraint — Scout supplies the evidence, PRISM never
invents it.

## Configuration

`prism_platform/config.py`:
- `scout_base_url` (default `http://127.0.0.1:8421`)
- `scout_api_key` (sent as `X-API-Key`; local default `dev-key`, override per env)

Scout must be running and reachable at `scout_base_url` for the research tier to
acquire evidence. When Scout is down, acquisition fails closed (no fabricated
fallback). Live integration smoke: `pytest tests/test_scout_client.py -m scout_live`.

## Out of scope (not done here)

Wiring the adapter into the research-tier modules (Scout fetch → cheap LLM
synthesize) is a follow-on. This ADR + adapter establish the contract and client;
module wiring lands with the runtime-routing layer.
