"""Tests for the PRISM-side Scout HTTP adapter.

Scout = evidence/acquisition engine. PRISM calls Scout over HTTP and consumes
its typed records + source provenance — PRISM never reimplements crawling.

These tests use httpx.MockTransport (no network, no running Scout) to verify:
request shaping (path + X-API-Key auth), response parsing into PRISM models,
and — critically — that source provenance / citations survive the round-trip.

Read receipt (Scout source, 2026-06-29):
  scout/api/routers/scrape.py  -> POST /scrape  (ScrapeResponse)
  scout/api/routers/run.py     -> POST /run/{use_case} (RunResponse w/ RunManifest)
  scout/api/routers/runs.py    -> GET /runs/{id}/records|sources|artifacts
  scout/api/main.py            -> AuthMiddleware: X-API-Key header (default "dev-key")
  scout/core/platform/types.py -> RunManifest.run_id, SourceEvidence(source_url, blocked, ...)
"""

from __future__ import annotations

import httpx
import pytest

from prism_platform.integrations.scout import (
    ScoutClient,
    ScoutRun,
    ScoutScrapeResult,
)


def _client(handler) -> ScoutClient:
    return ScoutClient(
        base_url="http://scout.test:8421",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )


# ---------------------------------------------------------------------------
# scrape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scrape_posts_to_scrape_with_apikey_and_parses():
    seen: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["path"] = req.url.path
        seen["key"] = req.headers.get("x-api-key")
        return httpx.Response(
            200,
            json={
                "success": True,
                "url": "https://acme.com",
                "markdown": "# Acme",
                "final_url": "https://acme.com/",
                "provider": "crawl4ai",
                "quality_score": 0.82,
                "duration_ms": 120,
                "error": "",
            },
        )

    result = await _client(handler).scrape("https://acme.com")
    assert seen["path"] == "/scrape"
    assert seen["key"] == "test-key"
    assert isinstance(result, ScoutScrapeResult)
    assert result.success is True
    assert result.markdown == "# Acme"
    assert result.final_url == "https://acme.com/"
    assert result.provider == "crawl4ai"
    assert result.quality_score == 0.82


@pytest.mark.asyncio
async def test_scrape_surfaces_failure_not_raises():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "success": False,
                "url": "https://blocked.com",
                "error": "blocked: datadome",
                "duration_ms": 5,
            },
        )

    result = await _client(handler).scrape("https://blocked.com")
    assert result.success is False
    assert "datadome" in result.error


# ---------------------------------------------------------------------------
# run/{use_case} + hydration of records + sources (provenance)
# ---------------------------------------------------------------------------


def _run_handler():
    """Handler emulating POST /run/company then GET /runs/{id}/records + /sources."""

    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path
        if path == "/run/company":
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "use_case": "company",
                    "output_dir": "/work/run-1",
                    "total_records": 2,
                    "error": "",
                    "manifest": {
                        "run_id": "run-1",
                        "use_case": "company",
                        "query": "Acme",
                        "started_at": "t0",
                        "output_dir": "/work/run-1",
                        "total_records": 2,
                        "total_sources": 1,
                        "total_blocked": 0,
                        "warnings": ["thin"],
                    },
                },
            )
        if path == "/runs/run-1/records":
            return httpx.Response(
                200,
                json={
                    "run_id": "run-1",
                    "total": 1,
                    "records": [
                        {
                            "record_type": "company.v1",
                            "name": "Acme Inc",
                            "citations": [
                                {
                                    "source_id": "s1",
                                    "source_url": "https://acme.com/about",
                                    "field": "name",
                                    "claim": "Acme Inc",
                                    "confidence": 0.9,
                                }
                            ],
                        }
                    ],
                },
            )
        if path == "/runs/run-1/sources":
            return httpx.Response(
                200,
                json={
                    "run_id": "run-1",
                    "total": 1,
                    "sources": [
                        {
                            "source_id": "s1",
                            "source_url": "https://acme.com/about",
                            "final_url": "https://acme.com/about",
                            "provider": "crawl4ai",
                            "status_code": 200,
                            "blocked": False,
                        }
                    ],
                },
            )
        return httpx.Response(404, json={"detail": "nope"})

    return handler


@pytest.mark.asyncio
async def test_run_company_hydrates_records_and_sources():
    run = await _client(_run_handler()).run("company", query="Acme")
    assert isinstance(run, ScoutRun)
    assert run.success is True
    assert run.run_id == "run-1"
    assert run.total_records == 2
    assert run.warnings == ["thin"]
    assert len(run.records) == 1
    assert run.records[0].record_type == "company.v1"
    assert len(run.sources) == 1


@pytest.mark.asyncio
async def test_run_preserves_citation_provenance():
    run = await _client(_run_handler()).run("company", query="Acme")
    cite = run.records[0].citations[0]
    assert cite.source_url == "https://acme.com/about"
    assert cite.field == "name"
    assert cite.confidence == 0.9
    # source registry resolvable back from the citation's source_id
    assert run.sources[0].source_id == cite.source_id


@pytest.mark.asyncio
async def test_run_failure_returns_unsuccessful_run_no_hydration():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"success": False, "use_case": "company", "error": "no targets", "manifest": None},
        )

    run = await _client(handler).run("company", query="Nope")
    assert run.success is False
    assert run.error == "no targets"
    assert run.records == []


@pytest.mark.asyncio
async def test_convenience_methods_hit_right_use_case():
    seen: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.startswith("/run/"):
            seen["use_case"] = req.url.path.split("/run/")[1]
        return httpx.Response(
            200, json={"success": True, "use_case": seen.get("use_case", ""), "manifest": None}
        )

    c = _client(handler)
    await c.news(query="Acme")
    assert seen["use_case"] == "news"
    await c.careers(query="Acme")
    assert seen["use_case"] == "careers"
    await c.investor(query="Acme")
    assert seen["use_case"] == "investor"


@pytest.mark.asyncio
async def test_http_error_raises():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    with pytest.raises(httpx.HTTPStatusError):
        await _client(handler).scrape("https://acme.com")


# ---------------------------------------------------------------------------
# Live smoke — runs ONLY against a real local Scout service. Skipped otherwise.
# Run with: pytest tests/test_scout_client.py -m scout_live -v
# ---------------------------------------------------------------------------


@pytest.mark.scout_live
@pytest.mark.asyncio
async def test_live_scout_health_and_scrape():
    from prism_platform.integrations.scout import scout_client_from_settings

    client = scout_client_from_settings()
    try:
        if not await client.health():
            pytest.skip("Scout service not reachable on configured base_url")
        result = await client.scrape("https://example.com")
        assert result.success is True
        assert result.markdown
    finally:
        await client.close()
