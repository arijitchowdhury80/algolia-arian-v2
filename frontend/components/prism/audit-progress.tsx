"use client";

import { useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import {
  Check,
  Loader2,
  X,
  ChevronDown,
  ChevronRight,
  Zap,
  Rocket,
  List,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
// Tooltip removed — using title attribute for disabled button tooltip

/**
 * AuditProgress — module-by-module execution progress.
 * Pattern: nyxbui Timeline component adapted for audit module tracking.
 */

export interface AuditModule {
  name: string;
  displayName: string;
  status: "pending" | "running" | "complete" | "error";
  duration_ms?: number;
  error?: string;
}

interface AuditProgressProps {
  modules: AuditModule[];
  isLoading?: boolean;
  error?: string | null;
}

function formatDuration(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

const statusConfig = {
  pending: {
    icon: <div className="h-2.5 w-2.5 rounded-full bg-zinc-300" />,
    lineColor: "bg-zinc-200",
    textColor: "text-[var(--muted-text)]",
  },
  running: {
    icon: <Loader2 className="h-3.5 w-3.5 text-[#003DFF] animate-spin" />,
    lineColor: "bg-[#003DFF]",
    textColor: "text-[#003DFF]",
  },
  complete: {
    icon: <Check className="h-3.5 w-3.5 text-green-600" />,
    lineColor: "bg-green-500",
    textColor: "text-[#23263B]",
  },
  error: {
    icon: <X className="h-3.5 w-3.5 text-red-500" />,
    lineColor: "bg-red-500",
    textColor: "text-red-500",
  },
};

export function AuditProgress({ modules, isLoading, error }: AuditProgressProps) {
  if (isLoading) return <AuditProgressSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Audit progress unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  if (!modules.length) return null;

  const completedCount = modules.filter((m) => m.status === "complete").length;
  const totalCount = modules.length;

  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
          Audit Progress
        </span>
        <span className="text-[11px] font-semibold text-[#23263B]">
          {completedCount}/{totalCount} modules
        </span>
      </div>

      {/* Overall progress bar */}
      <div className="h-1.5 w-full rounded-full bg-[#F5F5F7] mb-4 overflow-hidden">
        <div
          className="h-full rounded-full bg-[#003DFF] transition-all duration-500"
          style={{ width: `${(completedCount / totalCount) * 100}%` }}
        />
      </div>

      {/* Module timeline */}
      <div className="relative pl-5">
        {/* Vertical line */}
        <div className="absolute left-[7px] top-2 bottom-2 w-[2px] bg-[#F5F5F7] rounded-full" />

        {modules.map((mod) => {
          const config = statusConfig[mod.status];
          return (
            <div
              key={mod.name}
              className={cn(
                "relative flex items-start gap-3 pb-3 last:pb-0",
                mod.status === "running" && "animate-pulse"
              )}
            >
              {/* Status dot/icon on the line */}
              <div className="relative z-10 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-white">
                {config.icon}
              </div>

              {/* Module info */}
              <div className="flex-1 min-w-0 -mt-0.5">
                <div className="flex items-center gap-2">
                  <span className={cn("text-xs font-semibold", config.textColor)}>
                    {mod.displayName}
                  </span>
                  {mod.duration_ms !== undefined && mod.status === "complete" && (
                    <span className="text-[10px] font-mono text-[var(--muted-text)]">
                      {formatDuration(mod.duration_ms)}
                    </span>
                  )}
                </div>
                {mod.error && (
                  <p className="text-[10px] text-red-500 mt-0.5">{mod.error}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AuditProgressSkeleton() {
  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5">
      <Skeleton className="h-3 w-28 mb-3" />
      <Skeleton className="h-1.5 w-full mb-4" />
      <div className="space-y-3 pl-5">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex items-center gap-3">
            <Skeleton className="h-4 w-4 rounded-full shrink-0" />
            <Skeleton className="h-3 w-32" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// WaveAuditProgress — wave-based execution view
// ═══════════════════════════════════════════════════════════════════════════════

export interface WaveDefinition {
  wave: number;
  name: string;
  modules: AuditModule[];
  status: "pending" | "running" | "complete" | "error";
}

/** Default wave definitions with module names. Statuses default to "pending". */
export function getDefaultWaves(): WaveDefinition[] {
  return [
    {
      wave: 1,
      name: "Intelligence",
      status: "pending",
      modules: [
        { name: "intel-company", displayName: "Company Profile", status: "pending" },
        { name: "intel-techstack", displayName: "Tech Stack", status: "pending" },
        { name: "intel-traffic", displayName: "Traffic Analysis", status: "pending" },
        { name: "intel-financial-public", displayName: "Public Financials", status: "pending" },
        { name: "intel-financial-private", displayName: "Private Financials", status: "pending" },
        { name: "intel-news", displayName: "News Signals", status: "pending" },
        { name: "intel-hiring", displayName: "Hiring Signals", status: "pending" },
        { name: "intel-social", displayName: "Social Signals", status: "pending" },
        { name: "intel-investor", displayName: "Investor Intel", status: "pending" },
        { name: "intel-partner", displayName: "Partner Ecosystem", status: "pending" },
        { name: "intel-industry", displayName: "Industry Benchmarks", status: "pending" },
        { name: "intel-competitors", displayName: "Competitor Matrix", status: "pending" },
        { name: "intel-queries", displayName: "Test Queries", status: "pending" },
      ],
    },
    {
      wave: 2,
      name: "Experience Audit",
      status: "pending",
      modules: [
        { name: "audit-browser", displayName: "Browser Audit", status: "pending" },
      ],
    },
    {
      wave: 3,
      name: "Synthesis",
      status: "pending",
      modules: [
        { name: "synth-business-case", displayName: "Business Case", status: "pending" },
        { name: "synth-sales-plays", displayName: "Sales Plays", status: "pending" },
        { name: "audit-report", displayName: "Audit Report", status: "pending" },
      ],
    },
    {
      wave: 4,
      name: "Activation",
      status: "pending",
      modules: [
        { name: "campaign-abx", displayName: "ABX Campaign", status: "pending" },
      ],
    },
    {
      wave: 5,
      name: "Quality Gate",
      status: "pending",
      modules: [
        { name: "audit-factcheck", displayName: "Fact Check", status: "pending" },
      ],
    },
    {
      wave: 6,
      name: "Benchmarking",
      status: "pending",
      modules: [
        { name: "insights-engine", displayName: "Insights Engine", status: "pending" },
      ],
    },
  ];
}

const waveStatusBadge: Record<WaveDefinition["status"], { label: string; className: string }> = {
  pending: {
    label: "Pending",
    className: "bg-zinc-100 text-zinc-500 border-zinc-200",
  },
  running: {
    label: "Running",
    className: "bg-blue-50 text-[#003DFF] border-blue-200",
  },
  complete: {
    label: "Complete",
    className: "bg-green-50 text-green-600 border-green-200",
  },
  error: {
    label: "Error",
    className: "bg-red-50 text-red-600 border-red-200",
  },
};

interface WaveAuditProgressProps {
  waves: WaveDefinition[];
  isLoading?: boolean;
  error?: string | null;
}

export function WaveAuditProgress({ waves, isLoading, error }: WaveAuditProgressProps) {
  const [expandedWaves, setExpandedWaves] = useState<Set<number>>(() => {
    // Auto-expand the first running wave, or the first pending wave
    const runningWave = waves.find((w) => w.status === "running");
    const firstPending = waves.find((w) => w.status === "pending");
    const autoExpand = runningWave?.wave ?? firstPending?.wave ?? 1;
    return new Set([autoExpand]);
  });

  const toggleWave = useCallback((waveNum: number) => {
    setExpandedWaves((prev) => {
      const next = new Set(prev);
      if (next.has(waveNum)) {
        next.delete(waveNum);
      } else {
        next.add(waveNum);
      }
      return next;
    });
  }, []);

  if (isLoading) return <AuditProgressSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Audit progress unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  // Calculate overall progress
  const allModules = waves.flatMap((w) => w.modules);
  const totalModules = allModules.length;
  const completedModules = allModules.filter((m) => m.status === "complete").length;
  const progressPct = totalModules > 0 ? (completedModules / totalModules) * 100 : 0;

  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
          Audit Progress
        </span>
        <span className="text-[11px] font-semibold text-[#23263B]">
          {completedModules}/{totalModules} modules
        </span>
      </div>

      {/* Overall progress bar */}
      <div className="h-2 w-full rounded-full bg-[#F5F5F7] mb-4 overflow-hidden">
        <div
          className="h-full rounded-full bg-[#003DFF] transition-all duration-700 ease-out"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Wave sections */}
      <div className="space-y-1">
        {waves.map((wave) => {
          const isExpanded = expandedWaves.has(wave.wave);
          const badge = waveStatusBadge[wave.status];
          const waveCompleted = wave.modules.filter((m) => m.status === "complete").length;
          const waveTotal = wave.modules.length;

          return (
            <div key={wave.wave} className="rounded-lg border border-[#F5F5F7]">
              {/* Wave header — collapsible */}
              <button
                type="button"
                onClick={() => toggleWave(wave.wave)}
                className="flex w-full items-center gap-2 px-3 py-2.5 text-left hover:bg-[#FAFAFA] rounded-lg transition-colors"
              >
                {isExpanded ? (
                  <ChevronDown className="h-3.5 w-3.5 text-[var(--muted-text)] shrink-0" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5 text-[var(--muted-text)] shrink-0" />
                )}

                {wave.status === "complete" && (
                  <Check className="h-3.5 w-3.5 text-green-600 shrink-0" />
                )}
                {wave.status === "running" && (
                  <Loader2 className="h-3.5 w-3.5 text-[#003DFF] animate-spin shrink-0" />
                )}

                <span className="text-xs font-semibold text-[#23263B] flex-1">
                  Wave {wave.wave}: {wave.name}
                </span>

                <span className="text-[10px] text-[var(--muted-text)] mr-2">
                  {waveCompleted}/{waveTotal}
                </span>

                <Badge
                  variant="outline"
                  className={cn("text-[9px] px-1.5 py-0", badge.className)}
                >
                  {badge.label}
                </Badge>
              </button>

              {/* Wave modules — collapsible content */}
              {isExpanded && (
                <div className="px-3 pb-3">
                  <div className="relative pl-5 pt-1">
                    {/* Vertical timeline line */}
                    <div className="absolute left-[7px] top-3 bottom-2 w-[2px] bg-[#F5F5F7] rounded-full" />

                    {wave.modules.map((mod) => {
                      const config = statusConfig[mod.status];
                      return (
                        <div
                          key={mod.name}
                          className={cn(
                            "relative flex items-start gap-3 pb-2.5 last:pb-0",
                            mod.status === "running" && "animate-pulse"
                          )}
                        >
                          <div className="relative z-10 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-white">
                            {config.icon}
                          </div>
                          <div className="flex-1 min-w-0 -mt-0.5">
                            <div className="flex items-center gap-2">
                              <span className={cn("text-xs font-medium", config.textColor)}>
                                {mod.displayName}
                              </span>
                              {mod.duration_ms !== undefined && mod.status === "complete" && (
                                <span className="text-[10px] font-mono text-[var(--muted-text)]">
                                  {formatDuration(mod.duration_ms)}
                                </span>
                              )}
                            </div>
                            {mod.error && (
                              <p className="text-[10px] text-red-500 mt-0.5">{mod.error}</p>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// AuditModeSelector — Quick Lookup / Full Audit / Bulk Triage toggle
// ═══════════════════════════════════════════════════════════════════════════════

export type AuditMode = "quick" | "full" | "bulk";

interface AuditModeSelectorProps {
  value: AuditMode;
  onChange: (mode: AuditMode) => void;
}

const auditModes = [
  {
    id: "quick" as const,
    label: "Quick Lookup",
    description: "3 modules, ~10s",
    icon: Zap,
    disabled: false,
  },
  {
    id: "full" as const,
    label: "Full Audit",
    description: "All waves, ~20-40min",
    icon: Rocket,
    disabled: false,
  },
  {
    id: "bulk" as const,
    label: "Bulk Triage",
    description: "Upload CSV",
    icon: List,
    disabled: true,
    tooltip: "Coming soon",
  },
] as const;

export function AuditModeSelector({ value, onChange }: AuditModeSelectorProps) {
  return (
    <div className="flex gap-2">
        {auditModes.map((mode) => {
          const Icon = mode.icon;
          const isSelected = value === mode.id;
          const isDisabled = mode.disabled;

          const button = (
            <button
              key={mode.id}
              type="button"
              disabled={isDisabled}
              onClick={() => {
                if (!isDisabled) onChange(mode.id);
              }}
              className={cn(
                "flex flex-1 flex-col items-center gap-1 rounded-lg border px-4 py-3 text-center transition-all",
                isSelected && !isDisabled
                  ? "border-[#003DFF] bg-[#003DFF]/5 ring-1 ring-[#003DFF]/20"
                  : "border-[#E5E7EB] bg-white hover:border-[#003DFF]/30",
                isDisabled && "cursor-not-allowed opacity-50 hover:border-[#E5E7EB]"
              )}
              aria-pressed={isSelected}
              aria-label={`${mode.label}: ${mode.description}${isDisabled ? " (coming soon)" : ""}`}
            >
              <Icon
                className={cn(
                  "h-5 w-5",
                  isSelected && !isDisabled
                    ? "text-[#003DFF]"
                    : "text-[var(--muted-text)]"
                )}
              />
              <span
                className={cn(
                  "text-xs font-semibold",
                  isSelected && !isDisabled
                    ? "text-[#003DFF]"
                    : "text-[#23263B]"
                )}
              >
                {mode.label}
              </span>
              <span className="text-[10px] text-[var(--muted-text)]">
                {mode.description}
              </span>
            </button>
          );

          if (isDisabled && "tooltip" in mode) {
            return (
              <div key={mode.id} title={mode.tooltip} className="flex flex-1">
                {button}
              </div>
            );
          }

          return button;
        })}
    </div>
  );
}
