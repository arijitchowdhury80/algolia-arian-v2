"""PRISM Audit Stream Router — SSE endpoint for real-time audit progress."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from core.auth.deps import require_audit_access
from core.db.models import Audit, ModuleExecution
from server.api.deps import DbSession
from server.orchestrator.workflows import ALL_WAVES, MODULE_WAVE_MAP

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POLL_INTERVAL_SECONDS: float = 2.0
MAX_STREAM_SECONDS: float = 45 * 60  # 45 minutes

TERMINAL_AUDIT_STATUSES: set[str] = {"completed", "complete", "failed", "aborted"}

# ---------------------------------------------------------------------------
# Event model
# ---------------------------------------------------------------------------


class ModuleEvent(BaseModel):
    """Payload for a single SSE event emitted during audit streaming."""

    model_config = ConfigDict(extra="forbid")

    event_type: str
    timestamp: str
    module_name: str | None = None
    wave: int | None = None
    status: str | None = None
    duration_ms: int | None = None
    summary: str | None = None
    error: str | None = None
    modules_in_wave: list[str] | None = None
    succeeded: int | None = None
    failed: int | None = None
    total_duration_ms: int | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


def _sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format a single Server-Sent Event frame.

    Args:
        event_type: The SSE event name (goes in the ``event:`` line).
        data: JSON-serialisable dict (goes in the ``data:`` line).

    Returns:
        A correctly formatted SSE frame ending with two newlines.
    """
    payload = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {payload}\n\n"


def _module_summary(output_json: dict[str, Any] | None) -> str | None:
    """Extract a one-line summary from a module's output JSON.

    Tries several well-known keys in priority order.

    Args:
        output_json: The raw JSONB column from ``ModuleExecution.output_json``.

    Returns:
        A short summary string, or ``None`` if nothing useful is found.
    """
    if not output_json or not isinstance(output_json, dict):
        return None

    for key in ("summary", "company_social_summary", "verdict", "overall_score"):
        value = output_json.get(key)
        if value is not None:
            text = str(value).strip()
            if text:
                # Truncate very long summaries
                return text[:200] if len(text) > 200 else text
    return None


def _wave_modules(wave_number: int) -> list[str]:
    """Return the list of module names belonging to a wave (1-indexed).

    Args:
        wave_number: The 1-indexed wave number.

    Returns:
        List of module name strings for that wave.
    """
    idx = wave_number - 1
    if 0 <= idx < len(ALL_WAVES):
        return list(ALL_WAVES[idx])
    return []


# ---------------------------------------------------------------------------
# SSE endpoint
# ---------------------------------------------------------------------------


@router.get("/{audit_id}/stream")
async def stream_audit_progress(
    session: DbSession,
    audit: Annotated[Audit, Depends(require_audit_access)],
) -> StreamingResponse:
    """Stream real-time audit progress via Server-Sent Events.

    Polls the ``module_executions`` table every 2 seconds and emits events
    as modules transition through their lifecycle.  The stream terminates
    when the audit reaches a terminal status or after 45 minutes.

    Auth (04-spec.md §3 row 6): access is gated by ``require_audit_access``
    -- denial (404, identical for missing-or-denied) happens BEFORE this
    function returns a ``StreamingResponse`` at all, i.e. before the SSE
    stream ever opens, not mid-stream.

    Args:
        session: Injected async database session.
        audit: The authorized ``Audit`` row (fetched + ACL-checked by
            ``require_audit_access``).

    Returns:
        A ``StreamingResponse`` with ``text/event-stream`` media type.
    """
    audit_id = audit.id
    logger.info("stream_audit_progress.start", audit_id=str(audit_id))
    logger.info(
        "stream_audit_progress.audit_found",
        audit_id=str(audit_id),
        current_status=audit.status,
    )

    return StreamingResponse(
        _event_generator(audit_id, session),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _event_generator(
    audit_id: uuid.UUID,
    session: Any,
) -> Any:
    """Async generator that yields SSE frames for audit progress.

    Tracks which modules have been seen in each state and emits events
    only on transitions.  Also tracks wave-level start/complete events.

    Args:
        audit_id: The audit UUID to monitor.
        session: An async SQLAlchemy session.

    Yields:
        SSE-formatted strings.
    """
    # --- state tracking ---
    seen_running: set[str] = set()
    seen_completed: set[str] = set()
    seen_failed: set[str] = set()
    waves_started: set[int] = set()
    waves_completed: set[int] = set()

    start_time = asyncio.get_event_loop().time()

    # Send the initial connected event
    yield _sse_event(
        "connected",
        ModuleEvent(
            event_type="connected",
            timestamp=_now_iso(),
        ).model_dump(exclude_none=True),
    )

    logger.info("stream.connected", audit_id=str(audit_id))

    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= MAX_STREAM_SECONDS:
            logger.warning(
                "stream.timeout",
                audit_id=str(audit_id),
                elapsed_seconds=round(elapsed, 1),
            )
            yield _sse_event(
                "timeout",
                ModuleEvent(
                    event_type="timeout",
                    timestamp=_now_iso(),
                    error="Stream timed out after 45 minutes.",
                ).model_dump(exclude_none=True),
            )
            break

        try:
            # Expire cached ORM state so we get fresh data from the DB
            session.expire_all()

            # Fetch all module executions for this audit
            mod_result = await session.execute(
                select(ModuleExecution).where(ModuleExecution.audit_id == audit_id)
            )
            executions: list[ModuleExecution] = list(mod_result.scalars().all())

            # Process each execution row
            for exc_row in executions:
                module_name: str = exc_row.module_name
                status: str = exc_row.status
                wave: int = (
                    exc_row.wave
                    if exc_row.wave is not None
                    else MODULE_WAVE_MAP.get(module_name, 0)
                )

                # --- wave_started ---
                if (
                    wave > 0
                    and wave not in waves_started
                    and status in ("running", "success", "failed", "partial")
                ):
                    waves_started.add(wave)
                    wave_mods = _wave_modules(wave)
                    logger.info(
                        "stream.wave_started",
                        audit_id=str(audit_id),
                        wave=wave,
                        modules_in_wave=wave_mods,
                    )
                    yield _sse_event(
                        "wave_started",
                        ModuleEvent(
                            event_type="wave_started",
                            timestamp=_now_iso(),
                            wave=wave,
                            modules_in_wave=wave_mods,
                        ).model_dump(exclude_none=True),
                    )

                # --- module_started ---
                if status == "running" and module_name not in seen_running:
                    seen_running.add(module_name)
                    logger.debug(
                        "stream.module_started",
                        audit_id=str(audit_id),
                        module_name=module_name,
                        wave=wave,
                    )
                    yield _sse_event(
                        "module_started",
                        ModuleEvent(
                            event_type="module_started",
                            timestamp=_now_iso(),
                            module_name=module_name,
                            wave=wave,
                            status="running",
                        ).model_dump(exclude_none=True),
                    )

                # --- module_completed ---
                if status in ("success", "partial") and module_name not in seen_completed:
                    seen_completed.add(module_name)
                    summary = _module_summary(exc_row.output_json)
                    logger.info(
                        "stream.module_completed",
                        audit_id=str(audit_id),
                        module_name=module_name,
                        wave=wave,
                        duration_ms=exc_row.duration_ms,
                    )
                    yield _sse_event(
                        "module_completed",
                        ModuleEvent(
                            event_type="module_completed",
                            timestamp=_now_iso(),
                            module_name=module_name,
                            wave=wave,
                            status=status,
                            duration_ms=exc_row.duration_ms,
                            summary=summary,
                        ).model_dump(exclude_none=True),
                    )

                # --- module_failed ---
                if status == "failed" and module_name not in seen_failed:
                    seen_failed.add(module_name)
                    logger.warning(
                        "stream.module_failed",
                        audit_id=str(audit_id),
                        module_name=module_name,
                        wave=wave,
                        error_message=exc_row.error_message,
                    )
                    yield _sse_event(
                        "module_failed",
                        ModuleEvent(
                            event_type="module_failed",
                            timestamp=_now_iso(),
                            module_name=module_name,
                            wave=wave,
                            status="failed",
                            error=exc_row.error_message,
                        ).model_dump(exclude_none=True),
                    )

            # --- wave_completed ---
            for wave_num in sorted(waves_started - waves_completed):
                wave_mods = _wave_modules(wave_num)
                if not wave_mods:
                    continue

                done_in_wave = [m for m in wave_mods if m in seen_completed or m in seen_failed]
                if len(done_in_wave) == len(wave_mods):
                    waves_completed.add(wave_num)
                    succeeded_count = sum(1 for m in wave_mods if m in seen_completed)
                    failed_count = sum(1 for m in wave_mods if m in seen_failed)
                    logger.info(
                        "stream.wave_completed",
                        audit_id=str(audit_id),
                        wave=wave_num,
                        succeeded=succeeded_count,
                        failed=failed_count,
                    )
                    yield _sse_event(
                        "wave_completed",
                        ModuleEvent(
                            event_type="wave_completed",
                            timestamp=_now_iso(),
                            wave=wave_num,
                            modules_in_wave=wave_mods,
                            succeeded=succeeded_count,
                            failed=failed_count,
                        ).model_dump(exclude_none=True),
                    )

            # --- audit terminal check ---
            audit_result = await session.execute(select(Audit).where(Audit.id == audit_id))
            audit_row = audit_result.scalar_one_or_none()

            if audit_row is not None and audit_row.status in TERMINAL_AUDIT_STATUSES:
                total_duration_ms: int | None = None
                if audit_row.started_at and audit_row.completed_at:
                    delta = audit_row.completed_at - audit_row.started_at
                    total_duration_ms = int(delta.total_seconds() * 1000)

                logger.info(
                    "stream.audit_completed",
                    audit_id=str(audit_id),
                    status=audit_row.status,
                    total_duration_ms=total_duration_ms,
                )
                yield _sse_event(
                    "audit_completed",
                    ModuleEvent(
                        event_type="audit_completed",
                        timestamp=_now_iso(),
                        status=audit_row.status,
                        total_duration_ms=total_duration_ms,
                    ).model_dump(exclude_none=True),
                )
                break

        except GeneratorExit:
            logger.info("stream.client_disconnected", audit_id=str(audit_id))
            break
        except Exception as exc:
            logger.exception(
                "stream.poll_error",
                audit_id=str(audit_id),
                error=str(exc),
                error_type=type(exc).__name__,
            )
            yield _sse_event(
                "error",
                ModuleEvent(
                    event_type="error",
                    timestamp=_now_iso(),
                    error=f"Poll error: {type(exc).__name__}: {exc}",
                ).model_dump(exclude_none=True),
            )
            # Continue polling — transient errors should not kill the stream

        await asyncio.sleep(POLL_INTERVAL_SECONDS)
