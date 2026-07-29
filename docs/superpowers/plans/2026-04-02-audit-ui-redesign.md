# Audit UI Redesign: 3D Card + Thinking Stream

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current audit launched/status cards with a 3D tilt company card (no rocket icon), a copy-to-clipboard audit ID, and a Claude-style "thinking" SSE stream that shows real-time module execution logs instead of repeated status polling cards.

**Architecture:** Three layers — (1) Backend SSE endpoint polls `module_executions` table every 2s and streams wave/module status events, (2) Frontend `AuditThinking` component subscribes to SSE and renders a collapsible log, (3) Redesigned `RunFullAuditToolUI` card uses 3D tilt + cursor spotlight. The `GetAuditStatusToolUI` is removed from the AI tool loop — the thinking stream replaces it entirely.

**Tech Stack:** FastAPI `StreamingResponse` (SSE), React `EventSource`, Zustand for audit stream state, shadcn Card/Badge, Tailwind CSS, framer-motion for collapse animation, lucide-react icons.

---

## File Structure

### Backend (new files)
- `prism_platform/api/routers/audit_stream.py` — SSE endpoint `GET /api/v1/audits/{audit_id}/stream`

### Backend (modified files)
- `prism_platform/main.py` — register new router

### Frontend (new files)
- `frontend/components/chat/audit-thinking.tsx` — collapsible thinking log component
- `frontend/components/chat/audit-launched-card.tsx` — 3D tilt company card
- `frontend/lib/use-audit-stream.ts` — custom hook wrapping EventSource SSE

### Frontend (modified files)
- `frontend/lib/types.ts` — add SSE event types
- `frontend/lib/store.ts` — add audit stream state slice
- `frontend/lib/tools.ts` — modify `run_full_audit` to NOT trigger repeated `get_audit_status`
- `frontend/components/chat/tool-renderers.tsx` — replace `RunFullAuditToolUI` and `GetAuditStatusToolUI`
- `frontend/components/chat/prism-chat.tsx` — remove `GetAuditStatusToolUI` registration
- `frontend/app/api/chat/route.ts` — update system prompt to stop repeated status polling

---

## Task 1: Backend SSE Endpoint

**Files:**
- Create: `prism_platform/api/routers/audit_stream.py`
- Modify: `prism_platform/main.py`

- [ ] **Step 1: Create the SSE router**

```python
"""PRISM Audit Stream — SSE endpoint for real-time audit progress."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from prism_platform.api.deps import DbSession
from prism_platform.db.models import Audit, ModuleExecution
from prism_platform.orchestrator.workflows import MODULE_WAVE_MAP, ALL_WAVES

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()

POLL_INTERVAL_S = 2.0
MAX_STREAM_DURATION_S = 60 * 45  # 45 minutes max


class ModuleEvent(BaseModel):
    """Single module status event."""

    model_config = ConfigDict(extra="forbid")

    event_type: str  # module_started | module_completed | module_failed | wave_started | wave_completed | audit_completed
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


def _sse_event(data: dict, event_type: str = "message") -> str:
    """Format a single SSE event."""
    payload = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {payload}\n\n"


def _module_summary(module: ModuleExecution) -> str:
    """Extract a one-line summary from module output."""
    if not module.output_json:
        return ""
    output = module.output_json
    # Try common summary fields
    for key in ("summary", "company_social_summary", "verdict", "overall_score"):
        if key in output and output[key]:
            return str(output[key])[:120]
    return ""


@router.get("/{audit_id}/stream")
async def stream_audit_progress(audit_id: uuid.UUID, session: DbSession) -> StreamingResponse:
    """Stream real-time audit progress via Server-Sent Events.

    Polls the module_executions table every 2 seconds and emits events
    as modules transition through pending -> running -> success/failed.
    """
    # Verify audit exists
    result = await session.execute(select(Audit).where(Audit.id == audit_id))
    audit = result.scalar_one_or_none()
    if audit is None:
        raise HTTPException(status_code=404, detail="Audit not found.")

    logger.info("audit_stream.start", audit_id=str(audit_id))

    async def event_generator():
        """Async generator that yields SSE events."""
        seen_running: set[str] = set()
        seen_completed: set[str] = set()
        seen_failed: set[str] = set()
        waves_started: set[int] = set()
        waves_completed: set[int] = set()
        start_time = asyncio.get_event_loop().time()

        # Send initial connection event
        yield _sse_event(
            {"event_type": "connected", "audit_id": str(audit_id), "timestamp": datetime.utcnow().isoformat()},
            "connected",
        )

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > MAX_STREAM_DURATION_S:
                yield _sse_event(
                    {"event_type": "timeout", "timestamp": datetime.utcnow().isoformat()},
                    "timeout",
                )
                break

            try:
                # Re-fetch within same session
                await session.expire_all()
                stmt = (
                    select(ModuleExecution)
                    .where(ModuleExecution.audit_id == audit_id)
                    .order_by(ModuleExecution.wave, ModuleExecution.module_name)
                )
                rows = await session.execute(stmt)
                modules = rows.scalars().all()

                now = datetime.utcnow().isoformat()

                # Group by wave
                by_wave: dict[int, list[ModuleExecution]] = {}
                for m in modules:
                    w = m.wave or MODULE_WAVE_MAP.get(m.module_name, 0)
                    by_wave.setdefault(w, []).append(m)

                for wave_num in sorted(by_wave.keys()):
                    wave_modules = by_wave[wave_num]

                    # Emit wave_started
                    if wave_num not in waves_started and any(
                        m.status in ("running", "success", "failed") for m in wave_modules
                    ):
                        waves_started.add(wave_num)
                        wave_names = [m.module_name for m in wave_modules]
                        yield _sse_event(
                            ModuleEvent(
                                event_type="wave_started",
                                timestamp=now,
                                wave=wave_num,
                                modules_in_wave=wave_names,
                            ).model_dump(),
                            "wave_started",
                        )

                    for m in wave_modules:
                        # module_started
                        if m.status == "running" and m.module_name not in seen_running:
                            seen_running.add(m.module_name)
                            yield _sse_event(
                                ModuleEvent(
                                    event_type="module_started",
                                    timestamp=m.started_at.isoformat() if m.started_at else now,
                                    module_name=m.module_name,
                                    wave=wave_num,
                                    status="running",
                                ).model_dump(),
                                "module_started",
                            )

                        # module_completed
                        if m.status == "success" and m.module_name not in seen_completed:
                            seen_completed.add(m.module_name)
                            yield _sse_event(
                                ModuleEvent(
                                    event_type="module_completed",
                                    timestamp=m.completed_at.isoformat() if m.completed_at else now,
                                    module_name=m.module_name,
                                    wave=wave_num,
                                    status="success",
                                    duration_ms=m.duration_ms,
                                    summary=_module_summary(m),
                                ).model_dump(),
                                "module_completed",
                            )

                        # module_failed
                        if m.status == "failed" and m.module_name not in seen_failed:
                            seen_failed.add(m.module_name)
                            yield _sse_event(
                                ModuleEvent(
                                    event_type="module_failed",
                                    timestamp=m.completed_at.isoformat() if m.completed_at else now,
                                    module_name=m.module_name,
                                    wave=wave_num,
                                    status="failed",
                                    duration_ms=m.duration_ms,
                                    error=m.error_message or "Unknown error",
                                ).model_dump(),
                                "module_failed",
                            )

                    # wave_completed
                    if wave_num not in waves_completed and wave_num in waves_started:
                        all_done = all(m.status in ("success", "failed") for m in wave_modules)
                        if all_done:
                            waves_completed.add(wave_num)
                            succeeded = sum(1 for m in wave_modules if m.status == "success")
                            failed = sum(1 for m in wave_modules if m.status == "failed")
                            yield _sse_event(
                                ModuleEvent(
                                    event_type="wave_completed",
                                    timestamp=now,
                                    wave=wave_num,
                                    succeeded=succeeded,
                                    failed=failed,
                                ).model_dump(),
                                "wave_completed",
                            )

                # Check if audit is complete
                audit_result = await session.execute(select(Audit).where(Audit.id == audit_id))
                current_audit = audit_result.scalar_one_or_none()
                if current_audit and current_audit.status in ("completed", "failed", "aborted"):
                    total_ms = None
                    if current_audit.started_at and current_audit.completed_at:
                        total_ms = int((current_audit.completed_at - current_audit.started_at).total_seconds() * 1000)
                    yield _sse_event(
                        ModuleEvent(
                            event_type="audit_completed",
                            timestamp=now,
                            status=current_audit.status,
                            total_duration_ms=total_ms,
                        ).model_dump(),
                        "audit_completed",
                    )
                    break

            except Exception as exc:
                logger.error("audit_stream.poll_error", audit_id=str(audit_id), error=str(exc))
                yield _sse_event(
                    {"event_type": "error", "error": str(exc), "timestamp": datetime.utcnow().isoformat()},
                    "error",
                )

            await asyncio.sleep(POLL_INTERVAL_S)

        logger.info("audit_stream.end", audit_id=str(audit_id))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 2: Register the router in main.py**

Add to `prism_platform/main.py` after the existing audits router:

```python
from prism_platform.api.routers import accounts, audits, audit_stream, benchmarks, evidence, freshness, modules
```

And add the router:

```python
app.include_router(audit_stream.router, prefix="/api/v1/audits", tags=["audit-stream"])
```

- [ ] **Step 3: Verify the backend starts**

Run: `cd prism_platform && uvicorn prism_platform.main:app --port 8000`
Expected: Server starts without import errors.

- [ ] **Step 4: Commit**

```bash
git add prism_platform/api/routers/audit_stream.py prism_platform/main.py
git commit -m "feat: add SSE endpoint for real-time audit progress streaming"
```

---

## Task 2: Frontend SSE Types and Store

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/store.ts`

- [ ] **Step 1: Add SSE event types to types.ts**

Append to `frontend/lib/types.ts`:

```typescript
/* ── Audit stream SSE events ── */
export type AuditStreamEventType =
  | "connected"
  | "wave_started"
  | "module_started"
  | "module_completed"
  | "module_failed"
  | "wave_completed"
  | "audit_completed"
  | "timeout"
  | "error";

export interface AuditStreamEvent {
  event_type: AuditStreamEventType;
  timestamp: string;
  module_name?: string;
  wave?: number;
  status?: string;
  duration_ms?: number;
  summary?: string;
  error?: string;
  modules_in_wave?: string[];
  succeeded?: number;
  failed?: number;
  total_duration_ms?: number;
  audit_id?: string;
}
```

- [ ] **Step 2: Add audit stream state to store.ts**

Add to the `PrismStore` interface and implementation in `frontend/lib/store.ts`:

```typescript
// In the interface, add:
  // Audit stream state
  activeAuditId: string | null;
  auditStreamEvents: AuditStreamEvent[];
  auditStreamStatus: "idle" | "streaming" | "completed" | "failed";
  startAuditStream: (auditId: string) => void;
  addStreamEvent: (event: AuditStreamEvent) => void;
  endAuditStream: (status: "completed" | "failed") => void;
  clearAuditStream: () => void;

// In the create() body, add:
  activeAuditId: null,
  auditStreamEvents: [],
  auditStreamStatus: "idle",
  startAuditStream: (auditId) =>
    set({ activeAuditId: auditId, auditStreamEvents: [], auditStreamStatus: "streaming" }),
  addStreamEvent: (event) =>
    set((state) => ({ auditStreamEvents: [...state.auditStreamEvents, event] })),
  endAuditStream: (status) =>
    set({ auditStreamStatus: status }),
  clearAuditStream: () =>
    set({ activeAuditId: null, auditStreamEvents: [], auditStreamStatus: "idle" }),
```

Import `AuditStreamEvent` from `@/lib/types`.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/store.ts
git commit -m "feat: add audit stream SSE types and Zustand state slice"
```

---

## Task 3: Frontend SSE Hook

**Files:**
- Create: `frontend/lib/use-audit-stream.ts`

- [ ] **Step 1: Create the EventSource hook**

```typescript
"use client";

import { useEffect, useRef } from "react";
import { usePrismStore } from "@/lib/store";
import type { AuditStreamEvent } from "@/lib/types";

const PRISM_API_URL = process.env.PRISM_API_URL || "http://localhost:8000";

/**
 * Custom hook that connects to the audit SSE stream and dispatches events to the store.
 * Automatically connects when auditId is provided, disconnects on unmount or auditId change.
 */
export function useAuditStream(auditId: string | null) {
  const addStreamEvent = usePrismStore((s) => s.addStreamEvent);
  const startAuditStream = usePrismStore((s) => s.startAuditStream);
  const endAuditStream = usePrismStore((s) => s.endAuditStream);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!auditId) return;

    // Initialize store
    startAuditStream(auditId);

    const url = `${PRISM_API_URL}/api/v1/audits/${auditId}/stream`;
    const es = new EventSource(url);
    esRef.current = es;

    const EVENT_TYPES = [
      "connected",
      "wave_started",
      "module_started",
      "module_completed",
      "module_failed",
      "wave_completed",
      "audit_completed",
      "timeout",
      "error",
    ] as const;

    for (const eventType of EVENT_TYPES) {
      es.addEventListener(eventType, (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data) as AuditStreamEvent;
          addStreamEvent(data);

          if (eventType === "audit_completed") {
            endAuditStream(data.status === "completed" ? "completed" : "failed");
            es.close();
          }
          if (eventType === "timeout" || eventType === "error") {
            endAuditStream("failed");
            es.close();
          }
        } catch (err) {
          console.error("[audit-stream] Failed to parse SSE event:", err);
        }
      });
    }

    es.onerror = () => {
      console.error("[audit-stream] EventSource connection error");
      endAuditStream("failed");
      es.close();
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [auditId, addStreamEvent, startAuditStream, endAuditStream]);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/lib/use-audit-stream.ts
git commit -m "feat: add useAuditStream hook for SSE event subscription"
```

---

## Task 4: AuditThinking Component (Collapsible Log)

**Files:**
- Create: `frontend/components/chat/audit-thinking.tsx`

- [ ] **Step 1: Create the thinking component**

```typescript
"use client";

import { useState, useEffect, useRef } from "react";
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { usePrismStore } from "@/lib/store";
import { useAuditStream } from "@/lib/use-audit-stream";
import type { AuditStreamEvent } from "@/lib/types";

const MODULE_ICONS: Record<string, string> = {
  "intel-company": "Building",
  "intel-techstack": "Code",
  "intel-traffic": "Globe",
  "intel-financial-public": "DollarSign",
  "intel-financial-private": "DollarSign",
  "intel-news": "Newspaper",
  "intel-hiring": "Users",
  "intel-social": "Share2",
  "intel-investor": "TrendingUp",
  "intel-partner": "Handshake",
  "intel-industry": "BarChart3",
  "intel-competitors": "Swords",
  "intel-queries": "ListChecks",
  "audit-browser": "Monitor",
  "synth-business-case": "Briefcase",
  "synth-sales-plays": "Target",
  "audit-report": "FileText",
  "campaign-abx": "Megaphone",
  "audit-factcheck": "ShieldCheck",
  "insights-engine": "Zap",
};

const WAVE_LABELS: Record<number, string> = {
  1: "Intelligence",
  2: "Browser Audit",
  3: "Synthesis",
  4: "Activation",
  5: "Factcheck",
  6: "Insights",
};

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "";
  }
}

interface AuditThinkingProps {
  auditId: string;
  companyName: string;
  domain: string;
}

export function AuditThinking({ auditId, companyName, domain }: AuditThinkingProps) {
  const [expanded, setExpanded] = useState(false);
  const logEndRef = useRef<HTMLDivElement>(null);

  // Connect to SSE stream
  useAuditStream(auditId);

  const events = usePrismStore((s) => s.auditStreamEvents);
  const streamStatus = usePrismStore((s) => s.auditStreamStatus);

  // Auto-scroll to latest log entry
  useEffect(() => {
    if (expanded && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [events.length, expanded]);

  const isComplete = streamStatus === "completed";
  const isFailed = streamStatus === "failed";
  const isStreaming = streamStatus === "streaming";

  // Count progress
  const completedModules = events.filter((e) => e.event_type === "module_completed").length;
  const failedModules = events.filter((e) => e.event_type === "module_failed").length;
  const runningModules = events.filter(
    (e) => e.event_type === "module_started" && !events.some(
      (c) => (c.event_type === "module_completed" || c.event_type === "module_failed") && c.module_name === e.module_name
    )
  ).length;

  const totalDuration = events.find((e) => e.event_type === "audit_completed")?.total_duration_ms;

  // Header bar
  const headerLabel = isComplete
    ? `Audit complete — ${completedModules} modules`
    : isFailed
      ? `Audit failed — ${completedModules} succeeded, ${failedModules} failed`
      : `Working — ${completedModules} done${runningModules > 0 ? `, ${runningModules} running` : ""}`;

  const headerColor = isComplete
    ? "text-green-600"
    : isFailed
      ? "text-red-600"
      : "text-amber-600";

  const headerBg = isComplete
    ? "bg-green-50 border-green-200"
    : isFailed
      ? "bg-red-50 border-red-200"
      : "bg-amber-50 border-amber-200";

  return (
    <div className={cn("my-2 rounded-lg border overflow-hidden", headerBg)}>
      {/* Collapsed header bar */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium transition-colors hover:bg-black/5"
      >
        {isStreaming && <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-500" />}
        {isComplete && <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />}
        {isFailed && <XCircle className="h-3.5 w-3.5 text-red-600" />}
        <span className={cn("flex-1", headerColor)}>{headerLabel}</span>
        {totalDuration != null && (
          <span className="flex items-center gap-1 text-xs text-[var(--muted-text)]">
            <Clock className="h-3 w-3" />
            {formatDuration(totalDuration)}
          </span>
        )}
        {expanded ? (
          <ChevronDown className="h-3.5 w-3.5 text-[var(--muted-text)]" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-[var(--muted-text)]" />
        )}
      </button>

      {/* Expanded log */}
      {expanded && (
        <div className="max-h-64 overflow-y-auto border-t border-inherit bg-white/80 px-3 py-2">
          {events.length === 0 && (
            <div className="py-4 text-center text-xs text-[var(--muted-text)]">
              Connecting to audit stream...
            </div>
          )}
          {events.map((event, i) => (
            <LogEntry key={i} event={event} />
          ))}
          <div ref={logEndRef} />
        </div>
      )}
    </div>
  );
}

function LogEntry({ event }: { event: AuditStreamEvent }) {
  const time = formatTime(event.timestamp);

  switch (event.event_type) {
    case "wave_started":
      return (
        <div className="flex items-center gap-2 py-1.5 border-b border-dashed border-gray-100">
          <Zap className="h-3 w-3 text-[#003DFF]" />
          <span className="text-[10px] font-mono text-[var(--muted-text)]">{time}</span>
          <span className="text-xs font-semibold text-[#003DFF]">
            Wave {event.wave}: {WAVE_LABELS[event.wave ?? 0] ?? "Processing"}
          </span>
          <span className="text-[10px] text-[var(--muted-text)]">
            ({event.modules_in_wave?.length ?? 0} modules)
          </span>
        </div>
      );

    case "module_started":
      return (
        <div className="flex items-center gap-2 py-1">
          <Loader2 className="h-3 w-3 animate-spin text-amber-500" />
          <span className="text-[10px] font-mono text-[var(--muted-text)]">{time}</span>
          <span className="text-xs text-gray-700">{event.module_name}</span>
          <span className="text-[10px] text-amber-500">running</span>
        </div>
      );

    case "module_completed":
      return (
        <div className="flex items-start gap-2 py-1">
          <CheckCircle2 className="mt-0.5 h-3 w-3 text-green-500 shrink-0" />
          <span className="text-[10px] font-mono text-[var(--muted-text)]">{time}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-gray-700">{event.module_name}</span>
              <span className="text-[10px] text-green-600">
                {event.duration_ms != null ? formatDuration(event.duration_ms) : "done"}
              </span>
            </div>
            {event.summary && (
              <div className="text-[10px] text-[var(--muted-text)] truncate">{event.summary}</div>
            )}
          </div>
        </div>
      );

    case "module_failed":
      return (
        <div className="flex items-start gap-2 py-1">
          <XCircle className="mt-0.5 h-3 w-3 text-red-500 shrink-0" />
          <span className="text-[10px] font-mono text-[var(--muted-text)]">{time}</span>
          <div className="flex-1 min-w-0">
            <span className="text-xs font-medium text-red-600">{event.module_name}</span>
            {event.error && (
              <div className="text-[10px] text-red-500 truncate">{event.error}</div>
            )}
          </div>
        </div>
      );

    case "wave_completed":
      return (
        <div className="flex items-center gap-2 py-1.5 border-b border-dashed border-gray-100">
          <CheckCircle2 className="h-3 w-3 text-[#003DFF]" />
          <span className="text-[10px] font-mono text-[var(--muted-text)]">{time}</span>
          <span className="text-xs font-semibold text-[#003DFF]">
            Wave {event.wave} complete
          </span>
          <span className="text-[10px] text-[var(--muted-text)]">
            {event.succeeded} ok{event.failed ? `, ${event.failed} failed` : ""}
          </span>
        </div>
      );

    case "audit_completed":
      return (
        <div className="flex items-center gap-2 py-2 mt-1 rounded bg-green-50 px-2">
          <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
          <span className="text-xs font-semibold text-green-700">
            Audit {event.status}
          </span>
          {event.total_duration_ms != null && (
            <span className="text-[10px] text-green-600">
              Total: {formatDuration(event.total_duration_ms)}
            </span>
          )}
        </div>
      );

    default:
      return null;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/chat/audit-thinking.tsx
git commit -m "feat: add AuditThinking collapsible log component with SSE stream"
```

---

## Task 5: Redesigned Audit Launched Card (3D Tilt + Spotlight)

**Files:**
- Create: `frontend/components/chat/audit-launched-card.tsx`

- [ ] **Step 1: Create the 3D tilt card component**

```typescript
"use client";

import { useRef, useState, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Copy } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AuditResponse, RunAuditResponse } from "@/lib/types";
import { AuditThinking } from "./audit-thinking";

interface AuditLaunchedCardProps {
  audit: AuditResponse;
  workflow: RunAuditResponse;
  auditMode: string;
}

export function AuditLaunchedCard({ audit, workflow, auditMode }: AuditLaunchedCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  // 3D tilt + spotlight handler (Jatin tilt + SPA ov-tile spotlight combined)
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const card = cardRef.current;
    if (!card) return;
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    // Tilt: rotate toward cursor (max 8deg)
    const rx = ((y - cy) / cy) * -8;
    const ry = ((x - cx) / cx) * 8;
    card.style.transform = `perspective(1200px) rotateX(${rx}deg) rotateY(${ry}deg) translateZ(8px)`;
    // Spotlight: radial gradient follows cursor
    card.style.setProperty("--spot-x", `${x}px`);
    card.style.setProperty("--spot-y", `${y}px`);
  }, []);

  const handleMouseLeave = useCallback(() => {
    const card = cardRef.current;
    if (!card) return;
    card.style.transform = "";
  }, []);

  const copyAuditId = useCallback(() => {
    navigator.clipboard.writeText(audit.id).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [audit.id]);

  const modeLabel = auditMode === "quick" ? "Quick Lookup" : auditMode === "bulk_triage" ? "Triage" : "Full Audit";

  return (
    <div className="my-2">
      {/* 3D tilt card */}
      <div
        ref={cardRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        className={cn(
          "relative overflow-hidden rounded-xl border border-[#003DFF]/20",
          "bg-gradient-to-br from-white via-[#F8F9FF] to-[#EEF2FF]",
          "p-4 transition-transform duration-150 ease-out",
          "shadow-[0_4px_16px_rgba(0,61,255,0.08)]",
        )}
        style={{
          transformStyle: "preserve-3d",
          willChange: "transform",
        }}
      >
        {/* Cursor spotlight overlay */}
        <div
          className="pointer-events-none absolute inset-0 rounded-xl opacity-0 transition-opacity duration-300 group-hover:opacity-100"
          style={{
            background: "radial-gradient(400px circle at var(--spot-x, 50%) var(--spot-y, 50%), rgba(0,61,255,0.06) 0%, transparent 65%)",
            opacity: 1,
          }}
        />

        {/* Content */}
        <div className="relative z-10 flex items-center gap-3">
          {/* Company initial badge */}
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#003DFF] text-sm font-bold text-white">
            {(audit.company_name || "?")[0].toUpperCase()}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-[#23263B]">
                {audit.company_name}
              </span>
              <Badge
                variant="outline"
                className="bg-[#003DFF]/10 text-[#003DFF] border-[#003DFF]/20 text-[10px]"
              >
                {modeLabel}
              </Badge>
              <Badge
                variant="outline"
                className="bg-green-500/10 text-green-600 border-green-500/20 text-[10px]"
              >
                {workflow.status}
              </Badge>
            </div>
            <div className="text-xs text-[var(--muted-text)]">
              {audit.domain}
            </div>
          </div>

          {/* Copy audit ID button */}
          <button
            type="button"
            onClick={copyAuditId}
            title={`Copy audit ID: ${audit.id}`}
            className={cn(
              "flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-medium transition-colors",
              copied
                ? "border-green-300 bg-green-50 text-green-600"
                : "border-[var(--border-warm)] bg-white text-[var(--muted-text)] hover:border-[#003DFF]/30 hover:text-[#003DFF]"
            )}
          >
            {copied ? (
              <>
                <CheckCircle2 className="h-3 w-3" />
                Copied
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                ID
              </>
            )}
          </button>
        </div>
      </div>

      {/* Thinking stream below the card */}
      <AuditThinking
        auditId={audit.id}
        companyName={audit.company_name}
        domain={audit.domain}
      />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/chat/audit-launched-card.tsx
git commit -m "feat: add 3D tilt audit launched card with cursor spotlight and copy ID"
```

---

## Task 6: Wire Up Tool Renderers and Remove Old Cards

**Files:**
- Modify: `frontend/components/chat/tool-renderers.tsx`
- Modify: `frontend/components/chat/prism-chat.tsx`
- Modify: `frontend/app/api/chat/route.ts`

- [ ] **Step 1: Replace RunFullAuditToolUI in tool-renderers.tsx**

Replace the entire `RunFullAuditToolUI` (lines 583-647) and `GetAuditStatusToolUI` (lines 650-732) with:

```typescript
import { AuditLaunchedCard } from "./audit-launched-card";

/** run_full_audit — 3D tilt company card + thinking stream */
export const RunFullAuditToolUI = makeAssistantToolUI<
  { domain: string; company_name: string; audit_mode?: string },
  { audit: AuditResponse; workflow: RunAuditResponse; audit_mode?: string }
>({
  toolName: "run_full_audit",
  render: ({ args, result, status }) => {
    if (status.type === "running") {
      return (
        <ToolLoading
          icon={<Search className="h-4 w-4 text-[#003DFF]" />}
          label={
            <>
              Starting audit for <strong>{args.company_name}</strong> ({args.domain})...
            </>
          }
        />
      );
    }
    if (status.type === "incomplete") {
      return <ToolErrorCard message={`Failed to start audit for ${args.domain}.`} />;
    }
    if (result) {
      const audit = result.audit as AuditResponse;
      const workflow = result.workflow as RunAuditResponse;
      const auditMode = (result.audit_mode as string) ?? "full";
      return (
        <AuditLaunchedCard
          audit={audit}
          workflow={workflow}
          auditMode={auditMode}
        />
      );
    }
    return null;
  },
});

/** get_audit_status — minimal inline status (no repeated cards) */
export const GetAuditStatusToolUI = makeAssistantToolUI<
  { audit_id: string },
  AuditResponse
>({
  toolName: "get_audit_status",
  render: ({ result, status }) => {
    if (status.type === "running") {
      return (
        <div className="my-1 flex items-center gap-2 text-xs text-[var(--muted-text)]">
          <Loader2 className="h-3 w-3 animate-spin" />
          Checking status...
        </div>
      );
    }
    // Render nothing for completed status checks — the thinking stream shows progress
    return null;
  },
});
```

Also remove the `Rocket` import from lucide-react at the top of the file.

- [ ] **Step 2: Update the system prompt in chat route**

In `frontend/app/api/chat/route.ts`, find the section about audit workflow (around line 58-64 in the SYSTEM_PROMPT) and add after the existing workflow instructions:

```
IMPORTANT: After calling run_full_audit, DO NOT repeatedly call get_audit_status to check progress. The UI automatically streams real-time progress via the thinking panel. Instead, wait for the user to ask about results, or narrate findings as they appear in the conversation context. Only call get_audit_status if the user explicitly asks "what's the status?" after significant time has passed.
```

- [ ] **Step 3: Remove Rocket icon import from tool-renderers.tsx**

Remove `Rocket` from the lucide-react import (line 8). Also remove `ClipboardCheck` if it's only used by the old `GetAuditStatusToolUI`.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/chat/tool-renderers.tsx frontend/app/api/chat/route.ts
git commit -m "feat: replace audit cards with 3D tilt card + thinking stream, update system prompt"
```

---

## Task 7: Verify End-to-End

- [ ] **Step 1: Start backend**

```bash
cd prism_platform && uvicorn prism_platform.main:app --port 8000
```

- [ ] **Step 2: Start frontend dev server**

Navigate to frontend and start dev server.

- [ ] **Step 3: Test the SSE endpoint directly**

```bash
curl -N http://localhost:8000/api/v1/audits/{some-audit-id}/stream
```

Expected: SSE events stream as `event: connected\ndata: {...}\n\n`

- [ ] **Step 4: Test in browser**

1. Open http://localhost:3000/chat
2. Type "Run a full audit on dell.com"
3. Verify: 3D tilt card appears (no rocket icon), audit ID has copy button
4. Verify: Thinking bar appears below card, shows "Working..."
5. Click thinking bar to expand — should show scrolling log of module events
6. Verify: No repeated "AUDIT STATUS" cards appear
7. Verify: When audit completes, bar turns green with total duration

- [ ] **Step 5: Commit final verification**

```bash
git add -A
git commit -m "chore: verify end-to-end audit UI redesign"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - [x] Remove rocket icon — Task 6 Step 3
   - [x] 3D tilt card with cursor spotlight — Task 5
   - [x] Hide audit ID from visible text, add copy button — Task 5
   - [x] SSE backend endpoint — Task 1
   - [x] Thinking/streaming UI — Task 4
   - [x] Stop repeated get_audit_status cards — Task 6 Step 2
   - [x] Update system prompt — Task 6 Step 2

2. **Placeholder scan:** No TBDs, TODOs, or "implement later" found.

3. **Type consistency:** `AuditStreamEvent` type used consistently across types.ts, store.ts, use-audit-stream.ts, and audit-thinking.tsx. `ModuleEvent` Pydantic model in backend matches `AuditStreamEvent` TypeScript interface field-for-field.
