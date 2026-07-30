"""PRISM API Dependencies — injectable database session and Temporal client."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

import structlog
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client as TemporalClient

from core.config import settings
from core.db.session import get_session

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session via the shared factory."""
    async for session in get_session():
        yield session


async def temporal_client() -> TemporalClient:
    """Connect to the Temporal server and return a client."""
    try:
        client = await TemporalClient.connect(settings.temporal_host)
        logger.debug("temporal_client_connected", host=settings.temporal_host)
        return client
    except Exception as exc:
        logger.error(
            "temporal_client_connect_failed",
            host=settings.temporal_host,
            error=str(exc),
        )
        raise


# Type aliases for FastAPI Depends injection
DbSession = Annotated[AsyncSession, Depends(db_session)]
TemporalDep = Annotated[TemporalClient, Depends(temporal_client)]
