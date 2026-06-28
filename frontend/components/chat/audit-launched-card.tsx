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

export function AuditLaunchedCard({
  audit,
  workflow,
  auditMode,
}: AuditLaunchedCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const card = cardRef.current;
      if (!card) return;
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const cx = rect.width / 2;
      const cy = rect.height / 2;
      const rx = ((y - cy) / cy) * -8;
      const ry = ((x - cx) / cx) * 8;
      card.style.transform = `perspective(1200px) rotateX(${rx}deg) rotateY(${ry}deg) translateZ(8px)`;
      card.style.setProperty("--spot-x", `${x}px`);
      card.style.setProperty("--spot-y", `${y}px`);
    },
    []
  );

  const handleMouseLeave = useCallback(() => {
    const card = cardRef.current;
    if (!card) return;
    card.style.transform = "";
  }, []);

  const auditId = audit?.id ?? "";

  const copyAuditId = useCallback(() => {
    if (!auditId) return;
    navigator.clipboard.writeText(auditId).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [auditId]);

  const modeLabel =
    auditMode === "quick"
      ? "Quick Lookup"
      : auditMode === "bulk_triage"
        ? "Triage"
        : "Full Audit";

  return (
    <div className="my-2">
      <div
        ref={cardRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        className={cn(
          "relative overflow-hidden rounded-xl border border-[#003DFF]/20",
          "bg-gradient-to-br from-white via-[#F8F9FF] to-[#EEF2FF]",
          "p-4 transition-transform duration-150 ease-out",
          "shadow-[0_4px_16px_rgba(0,61,255,0.08)]"
        )}
        style={{
          transformStyle: "preserve-3d",
          willChange: "transform",
        }}
      >
        {/* Cursor spotlight overlay */}
        <div
          className="pointer-events-none absolute inset-0 rounded-xl"
          style={{
            background:
              "radial-gradient(400px circle at var(--spot-x, 50%) var(--spot-y, 50%), rgba(0,61,255,0.06) 0%, transparent 65%)",
          }}
        />

        {/* Content */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#003DFF] text-sm font-bold text-white">
            {(audit.company_name || "?")[0].toUpperCase()}
          </div>

          <div className="min-w-0 flex-1">
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

          <button
            type="button"
            onClick={copyAuditId}
            title={`Copy audit ID: ${auditId}`}
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

      <AuditThinking
        auditId={auditId}
        companyName={audit.company_name}
        domain={audit.domain}
      />
    </div>
  );
}
