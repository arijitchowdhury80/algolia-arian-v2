"""PRISM Platform — FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI

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


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok", "version": "2.0.0"}
