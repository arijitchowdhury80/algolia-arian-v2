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
