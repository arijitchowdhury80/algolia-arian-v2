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
    return new Date(iso).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
}

interface AuditThinkingProps {
  auditId: string;
  companyName: string;
  domain: string;
}

export function AuditThinking({
  auditId,
  companyName,
  domain,
}: AuditThinkingProps) {
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
  const completedModules = events.filter(
    (e) => e.event_type === "module_completed"
  ).length;
  const failedModules = events.filter(
    (e) => e.event_type === "module_failed"
  ).length;
  const runningModules = events.filter(
    (e) =>
      e.event_type === "module_started" &&
      !events.some(
        (c) =>
          (c.event_type === "module_completed" ||
            c.event_type === "module_failed") &&
          c.module_name === e.module_name
      )
  ).length;

  const totalDuration = events.find(
    (e) => e.event_type === "audit_completed"
  )?.total_duration_ms;

  // Header bar text
  const headerLabel = isComplete
    ? `Audit complete \u2014 ${completedModules} modules`
    : isFailed
      ? `Audit failed \u2014 ${completedModules} succeeded, ${failedModules} failed`
      : `Working \u2014 ${completedModules} done${runningModules > 0 ? `, ${runningModules} running` : ""}`;

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
        {isStreaming && (
          <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-500" />
        )}
        {isComplete && (
          <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
        )}
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
          <span className="text-[10px] font-mono text-[var(--muted-text)]">
            {time}
          </span>
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
          <span className="text-[10px] font-mono text-[var(--muted-text)]">
            {time}
          </span>
          <span className="text-xs text-gray-700">{event.module_name}</span>
          <span className="text-[10px] text-amber-500">running</span>
        </div>
      );

    case "module_completed":
      return (
        <div className="flex items-start gap-2 py-1">
          <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-green-500" />
          <span className="text-[10px] font-mono text-[var(--muted-text)]">
            {time}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-gray-700">
                {event.module_name}
              </span>
              <span className="text-[10px] text-green-600">
                {event.duration_ms != null
                  ? formatDuration(event.duration_ms)
                  : "done"}
              </span>
            </div>
            {event.summary && (
              <div className="truncate text-[10px] text-[var(--muted-text)]">
                {event.summary}
              </div>
            )}
          </div>
        </div>
      );

    case "module_failed":
      return (
        <div className="flex items-start gap-2 py-1">
          <XCircle className="mt-0.5 h-3 w-3 shrink-0 text-red-500" />
          <span className="text-[10px] font-mono text-[var(--muted-text)]">
            {time}
          </span>
          <div className="min-w-0 flex-1">
            <span className="text-xs font-medium text-red-600">
              {event.module_name}
            </span>
            {event.error && (
              <div className="truncate text-[10px] text-red-500">
                {event.error}
              </div>
            )}
          </div>
        </div>
      );

    case "wave_completed":
      return (
        <div className="flex items-center gap-2 border-b border-dashed border-gray-100 py-1.5">
          <CheckCircle2 className="h-3 w-3 text-[#003DFF]" />
          <span className="text-[10px] font-mono text-[var(--muted-text)]">
            {formatTime(event.timestamp)}
          </span>
          <span className="text-xs font-semibold text-[#003DFF]">
            Wave {event.wave} complete
          </span>
          <span className="text-[10px] text-[var(--muted-text)]">
            {event.succeeded} ok
            {event.failed ? `, ${event.failed} failed` : ""}
          </span>
        </div>
      );

    case "audit_completed":
      return (
        <div className="mt-1 flex items-center gap-2 rounded bg-green-50 px-2 py-2">
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
