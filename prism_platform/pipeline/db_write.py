"""DB-write helper -- persists a `gate.Verdict` + `self_heal.Attempt` as one
`ModuleExecution` row, using the existing SQLAlchemy model (never raw SQL).

This becomes the `on_attempt` observer callback wired into
`SelfHealLoop.on_attempt` per the interface contract's `run_full_audit`
sketch (Task 4a): Task 4a's real `on_attempt` closure keeps the just-computed
`Verdict` around (before mapping it down to a `self_heal.GateResult`) and
calls `write_module_execution_row(session, verdict=verdict, attempt=attempt, ...)`.
This module is only the mapping + persistence logic, not the wiring.

Gotcha this module works around (see prism_platform/pipeline/self_heal.py's
`ClockFn = Callable[[], float]`, default `time.monotonic`): `Attempt.started_at`
/`finished_at` are MONOTONIC clock readings, not epoch/wall-clock timestamps --
`time.monotonic()`'s reference point is arbitrary and NOT comparable to
`datetime.fromtimestamp`. Converting them directly into `timestamptz` columns
would silently write nonsense dates (e.g. 1970-01-01 plus a few seconds).
This helper instead stamps `completed_at` with real wall-clock time at
persist-time and derives `started_at` by subtracting the attempt's own
(monotonic-delta) duration -- the delta between two monotonic readings is
always a valid, real elapsed-time interval even though neither reading is a
real timestamp on its own.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from prism_platform.db.models import ModuleExecution
from prism_platform.pipeline.gate import BlockClass, Verdict, VerdictStatus
from prism_platform.pipeline.self_heal import Attempt

MODULE_VERSION = "gate-v1"


def verdict_to_status(verdict: Verdict | None, dispatch_ok: bool) -> str:
    """Map a Verdict (or its absence) + dispatch outcome to the `status`
    column's value. Mirrors the terminal states self_heal.py already
    recognizes: dispatch failure or no verdict -> 'failed'; PASS ->
    'completed'; BLOCK/UNFIXABLE -> 'needs_human' (patch #3 -- no retry will
    fix this); BLOCK/RETRY_WORTHY -> 'blocked' (a retry may still happen).
    """
    if not dispatch_ok or verdict is None:
        return "failed"
    if verdict.status == VerdictStatus.PASS:
        return "completed"
    if verdict.block_class == BlockClass.UNFIXABLE:
        return "needs_human"
    return "blocked"


def verdict_to_validation_json(verdict: Verdict) -> dict[str, Any]:
    """Serialize a Verdict into the JSONB shape stored in `validation_json`.
    Every stage-specific sub-verdict (factcheck/adversarial/quality/legal) is
    included when present so the full 5-stage trail is recoverable from one
    DB row, not just the terminal stage's outcome."""
    return {
        "stage": verdict.stage,
        "status": verdict.status.value,
        "block_class": verdict.block_class.value if verdict.block_class else None,
        "findings": list(verdict.findings),
        "mechanical_raw": verdict.mechanical_raw,
        "factcheck": verdict.factcheck.model_dump() if verdict.factcheck else None,
        "adversarial": verdict.adversarial.model_dump() if verdict.adversarial else None,
        "quality": verdict.quality.model_dump() if verdict.quality else None,
        "legal": verdict.legal.model_dump() if verdict.legal else None,
    }


def attempt_duration_ms(attempt: Attempt) -> int | None:
    """Elapsed time for one attempt, in milliseconds. Monotonic-clock deltas
    are safe to use for durations (unlike the raw readings themselves)."""
    if attempt.started_at is None or attempt.finished_at is None:
        return None
    return max(0, round((attempt.finished_at - attempt.started_at) * 1000))


async def write_module_execution_row(
    session: AsyncSession,
    *,
    audit_id: uuid.UUID | None,
    domain: str,
    verdict: Verdict | None,
    attempt: Attempt,
    module_version: str = MODULE_VERSION,
    now: datetime | None = None,
) -> ModuleExecution:
    """Persist one dispatch+gate attempt as a `ModuleExecution` row.

    Upserts on `(audit_id, module_name)` -- the table's existing unique
    constraint -- so repeated attempts for the same skill within the same
    audit update the row in place rather than accumulating duplicates
    (matching the "rerun upserts, doesn't duplicate" behavior already proven
    for the staged runner's raw-SQL writes in tests/pipeline/test_runner_dbwrite.py).

    `now` is injectable for deterministic tests; defaults to real wall-clock
    time.
    """
    resolved_now = now if now is not None else datetime.now(UTC)
    status = verdict_to_status(verdict, attempt.dispatch_ok)
    validation_json = verdict_to_validation_json(verdict) if verdict is not None else None

    error_message: str | None = None
    if not attempt.dispatch_ok:
        error_message = f"dispatch failed on attempt {attempt.attempt_number}"
    elif verdict is not None and verdict.status == VerdictStatus.BLOCK:
        error_message = "; ".join(verdict.findings) or None

    duration_ms = attempt_duration_ms(attempt)
    completed_at = resolved_now
    started_at = (
        resolved_now - timedelta(milliseconds=duration_ms)
        if duration_ms is not None
        else resolved_now
    )

    values: dict[str, Any] = {
        "domain": domain,
        "module_name": attempt.phase,
        "module_version": module_version,
        "status": status,
        "validation_json": validation_json,
        "duration_ms": duration_ms,
        "error_message": error_message,
        "started_at": started_at,
        "completed_at": completed_at,
    }
    if audit_id is not None:
        values["audit_id"] = audit_id

    insert_stmt = pg_insert(ModuleExecution).values(**values)
    if audit_id is not None:
        # ON CONFLICT requires a non-null audit_id -- the unique index is
        # (audit_id, module_name) and Postgres treats NULL as distinct from
        # every other NULL, so a null-audit_id row can never conflict and
        # always inserts fresh (acceptable: that's a caller who hasn't
        # created an Audit row yet, an edge case outside this attempt-write).
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["audit_id", "module_name"],
            set_={
                "module_version": insert_stmt.excluded.module_version,
                "status": insert_stmt.excluded.status,
                "validation_json": insert_stmt.excluded.validation_json,
                "duration_ms": insert_stmt.excluded.duration_ms,
                "error_message": insert_stmt.excluded.error_message,
                "started_at": insert_stmt.excluded.started_at,
                "completed_at": insert_stmt.excluded.completed_at,
                "domain": insert_stmt.excluded.domain,
            },
        ).returning(ModuleExecution)
    else:
        upsert_stmt = insert_stmt.returning(ModuleExecution)

    result = await session.execute(upsert_stmt)
    await session.commit()
    row: ModuleExecution = result.scalar_one()
    return row
