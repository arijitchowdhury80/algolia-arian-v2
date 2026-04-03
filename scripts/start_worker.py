"""PRISM Temporal Worker -- starts the worker process for audit workflows."""

from __future__ import annotations

import asyncio

import structlog
from temporalio.client import Client
from temporalio.worker import Worker

from prism_platform.config import settings
from prism_platform.core.registry import register_all_modules
from prism_platform.orchestrator.activities import run_module
from prism_platform.orchestrator.workflows import AuditWorkflow

logger = structlog.get_logger(__name__)


async def main() -> None:
    """Connect to Temporal and start the worker."""
    # Register all modules so activities can find them
    register_all_modules()

    logger.info(
        "Connecting to Temporal",
        host=settings.temporal_host,
        task_queue=settings.temporal_task_queue,
    )

    client = await Client.connect(settings.temporal_host)

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[AuditWorkflow],
        activities=[run_module],
    )

    logger.info("PRISM worker started", task_queue=settings.temporal_task_queue)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
