"""PRISM API Middleware — CORS and global exception handling."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from prism_platform.config import settings

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def add_middleware(app: FastAPI) -> None:
    """Attach CORS and exception handlers to the FastAPI app."""

    # --- CORS ---
    allowed_origins: list[str] = (
        ["*"] if settings.app_env == "development" else ["https://prism.algolia.com"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Global exception handler ---
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            path=str(request.url),
            method=request.method,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        body: dict[str, Any] = {
            "error": "internal_server_error",
            "detail": "An unexpected error occurred. Please try again later.",
        }
        return JSONResponse(status_code=500, content=body)
