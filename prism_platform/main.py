"""PRISM Platform — FastAPI application entrypoint."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from prism_platform.api.middleware import add_middleware
from prism_platform.api.routers import (
    accounts,
    audit_stream,
    audits,
    benchmarks,
    chat,
    evidence,
    freshness,
    knowledge,
    landing_pages,
    modules,
)
from prism_platform.v2.registry import register_all_v2_modules

register_all_v2_modules()

app = FastAPI(
    title="PRISM — Prospect Intelligence Platform",
    version="2.0.0",
    description="Light goes in, intelligence comes out.",
)

add_middleware(app)

app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(audits.router, prefix="/api/v1/audits", tags=["audits"])
app.include_router(audit_stream.router, prefix="/api/v1/audits", tags=["audit-stream"])
app.include_router(chat.router, prefix="/api/v1/audits", tags=["chat"])
app.include_router(modules.router, prefix="/api/v1/modules", tags=["modules"])
app.include_router(benchmarks.router, prefix="/api/v1/benchmarks", tags=["benchmarks"])
app.include_router(evidence.router, prefix="/api/v1/evidence", tags=["evidence"])
app.include_router(freshness.router, prefix="/api/v1/accounts", tags=["freshness"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"])
app.include_router(landing_pages.router, prefix="/api/v1/landing-pages", tags=["landing-pages"])

# Internal-only intake wizard (Marketer persona deliverable). Not the public
# marketing site -- see docs/workspace/custom-landing-page/00-design-system.md.
# Served with an explicit no-store route (not StaticFiles) because this file
# changes constantly during active development -- StaticFiles' default
# ETag/Last-Modified conditional-request handling was causing browsers to
# keep serving a stale cached copy after a plain refresh.
_LANDING_INTAKE_HTML = Path("prism_platform/static/landing_intake/index.html")


@app.get("/admin/landing-intake/")
async def landing_intake_wizard() -> Response:
    return Response(
        content=_LANDING_INTAKE_HTML.read_text(),
        media_type="text/html",
        headers={"Cache-Control": "no-store"},
    )


# Static assets (logo, etc.) rarely change -- fine to serve normally.
app.mount(
    "/admin/landing-intake/assets",
    StaticFiles(directory="prism_platform/static/landing_intake/assets"),
    name="landing-intake-assets",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok", "version": "2.0.0"}
