"""PRISM-side Scout HTTP adapter.

Boundary (per Scout project docs): **Scout acquires, structures, cites,
validates, and writes artifacts; PRISM interprets and decides.** This module is
the thin client PRISM uses to *call* Scout and *consume* its outputs. PRISM must
NOT reimplement crawling / scraping / browser capture / citation tracking — that
is entirely Scout's domain.

Read receipt (Scout source, 2026-06-29):
  POST /scrape                 -> ScrapeResponse (scout/core/types.py)
  POST /run/{use_case}         -> RunResponse w/ RunManifest (scout/core/platform/types.py)
                                  use_case ∈ {company, prism, investor, careers, news, ...}
  GET  /runs/{id}/records      -> {run_id, total, records:[{record_type, ..., citations:[...]}]}
  GET  /runs/{id}/sources      -> {run_id, total, sources:[SourceEvidence]}
  GET  /runs/{id}/artifacts    -> {run_id, output_dir, artifacts:{...file paths...}}
  Auth: X-API-Key header (scout/api/main.py AuthMiddleware; local default "dev-key").

Provenance is first-class: every record carries ``citations[]`` (source_id ->
source_url, field, claim, confidence) and the run's ``sources`` registry resolves
each source_id back to the fetched URL. PRISM preserves these in its outputs and
should treat a record with empty citations as NOT evidence-grounded.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# Local Scout HTTP service default; override via config / constructor.
DEFAULT_SCOUT_BASE_URL = "http://127.0.0.1:8421"
DEFAULT_SCOUT_API_KEY = "dev-key"


# ---------------------------------------------------------------------------
# PRISM-side consumption models (lenient: ignore Scout fields PRISM doesn't use,
# so Scout schema evolution never breaks the adapter).
# ---------------------------------------------------------------------------


class ScoutScrapeResult(BaseModel):
    """Single-URL fetch result from POST /scrape."""

    model_config = ConfigDict(extra="ignore")

    success: bool = False
    url: str = ""
    final_url: str = ""
    markdown: str = ""
    provider: str = ""
    quality_score: float = 0.0
    error: str = ""
    duration_ms: int = 0


class ScoutCitation(BaseModel):
    """Field-level evidence bridge: ties a record claim to a source page."""

    model_config = ConfigDict(extra="ignore")

    source_id: str = ""
    source_url: str = ""
    field: str = ""
    claim: str = ""
    snippet: str = ""
    confidence: float = 1.0


class ScoutSource(BaseModel):
    """Source registry entry (from source_pages.json / GET /runs/{id}/sources)."""

    model_config = ConfigDict(extra="ignore")

    source_id: str = ""
    source_url: str = ""
    final_url: str = ""
    provider: str = ""
    status_code: int | None = None
    blocked: bool = False
    error: str = ""
    confidence: float = 1.0


class ScoutRecord(BaseModel):
    """A typed record Scout produced (company.v1, news_signal.v1, etc.).

    Record bodies vary by use case, so the structured payload is kept in ``data``
    (the full raw record) while ``record_type`` and ``citations`` are surfaced
    explicitly because PRISM gates evidence-grounding on them.
    """

    model_config = ConfigDict(extra="ignore")

    record_type: str = ""
    citations: list[ScoutCitation] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> ScoutRecord:
        return cls(
            record_type=raw.get("record_type", ""),
            citations=[ScoutCitation.model_validate(c) for c in raw.get("citations", []) or []],
            data=raw,
        )

    @property
    def is_grounded(self) -> bool:
        """True when the record has at least one citation (PRISM's grounding gate)."""
        return len(self.citations) > 0


class ScoutRun(BaseModel):
    """Outcome of a POST /run/{use_case} call, with records + sources hydrated."""

    model_config = ConfigDict(extra="ignore")

    success: bool = False
    use_case: str = ""
    run_id: str = ""
    output_dir: str = ""
    total_records: int = 0
    error: str = ""
    warnings: list[str] = Field(default_factory=list)
    records: list[ScoutRecord] = Field(default_factory=list)
    sources: list[ScoutSource] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class ScoutClient:
    """Async HTTP client for the Scout acquisition service.

    Args:
        base_url: Scout HTTP service root (default local 127.0.0.1:8421).
        api_key: Sent as the ``X-API-Key`` header (local default "dev-key").
        timeout: Per-request timeout (seconds). Crawls can be slow.
        transport: Optional httpx transport (injected in tests).
    """

    def __init__(
        self,
        base_url: str = DEFAULT_SCOUT_BASE_URL,
        api_key: str = DEFAULT_SCOUT_API_KEY,
        timeout: float = 180.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            transport=transport,
        )

    async def health(self) -> bool:
        """Return True if the Scout service answers /health. Never raises."""
        try:
            resp = await self._http.get("/health")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def scrape(
        self,
        url: str,
        *,
        use_js: bool = False,
        stealth: bool = False,
        wait_for: str = "",
        timeout_ms: int = 30000,
    ) -> ScoutScrapeResult:
        """POST /scrape — fetch one URL to clean markdown + evidence."""
        body = {
            "url": url,
            "use_js": use_js,
            "stealth": stealth,
            "wait_for": wait_for,
            "timeout_ms": timeout_ms,
        }
        resp = await self._http.post("/scrape", json=body)
        resp.raise_for_status()
        return ScoutScrapeResult.model_validate(resp.json())

    async def run(
        self,
        use_case: str,
        *,
        query: str = "",
        url: str = "",
        targets: list[str] | None = None,
        mode: str = "auto",
        max_records: int = 250,
        hydrate: bool = True,
    ) -> ScoutRun:
        """POST /run/{use_case} — high-level acquisition for a company/topic.

        When ``hydrate`` is True (default) and the run produced a run_id, the
        records and source registry are fetched via GET /runs/{id}/records and
        /sources so the returned ScoutRun carries full provenance. Failure (no
        manifest) returns an unsuccessful run without hydration.
        """
        body: dict[str, Any] = {"query": query, "mode": mode, "max_records": max_records}
        if url:
            body["url"] = url
        if targets:
            body["targets"] = targets

        resp = await self._http.post(f"/run/{use_case}", json=body)
        resp.raise_for_status()
        data = resp.json()

        manifest = data.get("manifest") or {}
        run_id = manifest.get("run_id", "") if isinstance(manifest, dict) else ""
        result = ScoutRun(
            success=bool(data.get("success")),
            use_case=data.get("use_case", use_case),
            run_id=run_id,
            output_dir=data.get("output_dir", "") or manifest.get("output_dir", ""),
            total_records=data.get("total_records", manifest.get("total_records", 0)),
            error=data.get("error", ""),
            warnings=manifest.get("warnings", []) if isinstance(manifest, dict) else [],
        )

        if hydrate and result.success and run_id:
            result.records = await self.get_records(run_id)
            result.sources = await self.get_sources(run_id)

        logger.info(
            "scout.run",
            use_case=use_case,
            run_id=run_id,
            success=result.success,
            records=len(result.records),
            sources=len(result.sources),
        )
        return result

    async def get_records(self, run_id: str) -> list[ScoutRecord]:
        """GET /runs/{id}/records — typed records produced by a run."""
        resp = await self._http.get(f"/runs/{run_id}/records")
        resp.raise_for_status()
        raw = resp.json().get("records", []) or []
        return [ScoutRecord.from_raw(r) for r in raw]

    async def get_sources(self, run_id: str) -> list[ScoutSource]:
        """GET /runs/{id}/sources — the source registry (provenance)."""
        resp = await self._http.get(f"/runs/{run_id}/sources")
        resp.raise_for_status()
        raw = resp.json().get("sources", []) or []
        return [ScoutSource.model_validate(s) for s in raw]

    async def get_artifacts(self, run_id: str) -> dict[str, Any]:
        """GET /runs/{id}/artifacts — artifact file paths + output_dir."""
        resp = await self._http.get(f"/runs/{run_id}/artifacts")
        resp.raise_for_status()
        return resp.json()

    # Convenience wrappers for the use cases PRISM cares about ----------------

    async def company(self, *, query: str = "", url: str = "", **kw: Any) -> ScoutRun:
        """Company intelligence: about, leadership, socials, key URLs."""
        return await self.run("company", query=query, url=url, **kw)

    async def prism(self, *, query: str = "", url: str = "", **kw: Any) -> ScoutRun:
        """Full PRISM-style bundle: company + exec + investor + careers + news."""
        return await self.run("prism", query=query, url=url, **kw)

    async def news(self, *, query: str = "", url: str = "", **kw: Any) -> ScoutRun:
        """Newsroom / blog / announcement signals."""
        return await self.run("news", query=query, url=url, **kw)

    async def careers(self, *, query: str = "", url: str = "", **kw: Any) -> ScoutRun:
        """Careers / hiring evidence (ATS, departments, role categories)."""
        return await self.run("careers", query=query, url=url, **kw)

    async def investor(self, *, query: str = "", url: str = "", **kw: Any) -> ScoutRun:
        """Investor evidence: IR pages, reports, presentations, filings."""
        return await self.run("investor", query=query, url=url, **kw)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()


def scout_client_from_settings() -> ScoutClient:
    """Build a ScoutClient from prism_platform settings (scout_base_url/api_key)."""
    from prism_platform.config import settings

    return ScoutClient(base_url=settings.scout_base_url, api_key=settings.scout_api_key)
