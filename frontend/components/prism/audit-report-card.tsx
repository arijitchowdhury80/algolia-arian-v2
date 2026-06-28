"use client";

import { useRef, useCallback } from "react";
import NumberFlow from "@number-flow/react";
import { useInView } from "react-intersection-observer";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { FileText, Zap } from "lucide-react";
import type { ModuleResult, AuditReportResult } from "@/lib/types";

/**
 * AuditReportCard -- overall score with bar breakdown, pre-call brief,
 * leave-behind summary, competitor scores comparison.
 */

interface AuditReportCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

function scoreColor(score: number): string {
  if (score < 4) return "#DC2626";
  if (score < 6.5) return "#D97706";
  return "#059669";
}

function severityBarColor(severity: string): string {
  if (severity === "critical") return "bg-red-500";
  if (severity === "moderate") return "bg-amber-500";
  return "bg-green-500";
}

function severityTextColor(severity: string): string {
  if (severity === "critical") return "text-red-500";
  if (severity === "moderate") return "text-amber-500";
  return "text-green-500";
}

export function AuditReportCard({ data, isLoading, error }: AuditReportCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const { ref: inViewRef, inView } = useInView({ triggerOnce: true, threshold: 0.2 });

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const card = cardRef.current;
    if (!card) return;
    const rect = card.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const angle = Math.atan2(e.clientY - cy, e.clientX - cx) * (180 / Math.PI) + 90;
    card.style.setProperty("--glow-angle", `${angle}deg`);
    card.classList.add("glow-active");
  }, []);

  const handleMouseLeave = useCallback(() => {
    cardRef.current?.classList.remove("glow-active");
  }, []);

  if (isLoading) return <AuditReportSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Audit report unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = (data.output ?? {}) as Record<string, unknown>;
  const companyName = (raw.company_name as string) ?? "";
  const overallScore = (raw.overall_score as number) ?? 0;
  const dimensionScores = (raw.dimension_scores as AuditReportResult["dimension_scores"]) ?? [];
  const brief = (raw.pre_call_brief as AuditReportResult["pre_call_brief"]) ?? null;
  const lb = (raw.leave_behind as AuditReportResult["leave_behind"]) ?? null;
  const competitorScores = (raw.competitor_scores as AuditReportResult["competitor_scores"]) ?? [];
  const color = scoreColor(overallScore);

  return (
    <div
      ref={(node) => {
        (cardRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
        inViewRef(node);
      }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="glow-card my-2 p-5"
      style={{ "--glow-angle": "0deg" } as React.CSSProperties}
    >
      <style jsx>{`
        .glow-card {
          position: relative;
          border-radius: 12px;
          background: white;
          border: 1px solid var(--border-warm, #E5E7EB);
          isolation: isolate;
          transition: box-shadow 0.2s;
        }
        .glow-card::before {
          content: "";
          position: absolute;
          inset: -1px;
          border-radius: inherit;
          background: conic-gradient(from var(--glow-angle, 0deg), transparent 0%, #003dff 10%, #5468ff 25%, transparent 40%);
          opacity: 0;
          transition: opacity 0.4s ease;
          z-index: -1;
        }
        .glow-card::after {
          content: "";
          position: absolute;
          inset: 1px;
          border-radius: calc(12px - 1px);
          background: white;
          z-index: -1;
        }
        .glow-card.glow-active::before { opacity: 1; }
        .glow-card.glow-active { border-color: transparent; box-shadow: 0 4px 16px rgba(0, 61, 255, 0.08); }
      `}</style>

      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
          <FileText className="h-3.5 w-3.5" />
          Audit Report &mdash; {companyName}
        </div>
        <Badge variant="outline" className="text-[10px] font-mono">
          {data.module_version}
        </Badge>
      </div>

      {/* Big score */}
      <div className="flex items-end gap-3 mb-4">
        <div style={{ color }} className="text-5xl font-bold leading-none tracking-tight">
          {inView ? (
            <NumberFlow value={overallScore} format={{ minimumFractionDigits: 1, maximumFractionDigits: 1 }} />
          ) : (
            "0.0"
          )}
        </div>
        <span className="pb-1 text-lg text-[var(--muted-text)] opacity-50">/ 10</span>
      </div>

      {/* Dimension score bars */}
      {dimensionScores.length > 0 && (
        <div className="space-y-1.5 mb-4">
          {dimensionScores.map((d) => (
            <div
              key={d.dimension}
              className="grid grid-cols-[1fr_100px_40px] items-center gap-2"
            >
              <span className="text-[11px] text-[#23263B] truncate capitalize">
                {d.dimension.replace(/_/g, " ")}
              </span>
              <div className="h-1.5 rounded-full bg-[#F5F5F7] overflow-hidden">
                <div
                  className={cn("h-full rounded-full transition-all duration-700", severityBarColor(d.severity))}
                  style={{ width: `${d.score * 10}%` }}
                />
              </div>
              <span className={cn("text-[11px] font-semibold text-right", severityTextColor(d.severity))}>
                {d.score}/10
              </span>
            </div>
          ))}
        </div>
      )}

      <Separator className="mb-3" />

      {/* Pre-call brief */}
      {brief && (
        <div className="mb-3 rounded-lg border-2 border-[#003DFF]/20 bg-[#003DFF]/5 p-3">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[#003DFF] mb-1.5 flex items-center gap-1">
            <Zap className="h-3 w-3" /> Pre-Call Brief
          </span>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
            <div>
              <span className="text-[var(--muted-text)]">Score:</span>{" "}
              <span className="font-semibold" style={{ color: scoreColor(brief.search_score) }}>
                {brief.search_score}/10
              </span>
            </div>
            <div>
              <span className="text-[var(--muted-text)]">Key Exec:</span>{" "}
              <span className="font-semibold text-[#23263B]">{brief.key_exec_to_reference}</span>
            </div>
            <div className="col-span-2">
              <span className="text-[var(--muted-text)]">Top Angle:</span>{" "}
              <span className="font-semibold text-[#003DFF]">{brief.top_angle}</span>
            </div>
            <div className="col-span-2">
              <span className="text-[var(--muted-text)]">Urgent Signal:</span>{" "}
              <span className="font-semibold text-red-600">{brief.most_urgent_signal}</span>
            </div>
            <div className="col-span-2">
              <span className="text-[var(--muted-text)]">First Play:</span>{" "}
              <span className="font-semibold text-[#23263B]">{brief.recommended_first_play}</span>
            </div>
          </div>
        </div>
      )}

      {/* Leave-behind */}
      {lb && (
        <div className="mb-3 rounded-lg bg-[#F5F5F7] p-3">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted-text)] mb-1.5 block">
            Leave-Behind Summary
          </span>
          <p className="text-[11px] text-[#23263B] mb-1">{lb.search_quality_summary}</p>
          <p className="text-[11px] text-[var(--muted-text)] mb-1">{lb.competitive_benchmark}</p>
          {(lb.top_3_recommendations?.length ?? 0) > 0 && (
            <div className="mt-1.5">
              <span className="text-[10px] font-bold text-[var(--muted-text)]">Top Recommendations:</span>
              {(lb.top_3_recommendations ?? []).map((r, i) => (
                <div key={i} className="flex items-start gap-1.5 mt-0.5">
                  <span className="text-[10px] font-bold text-[#003DFF]">{i + 1}.</span>
                  <span className="text-[11px] text-[#23263B]">{r}</span>
                </div>
              ))}
            </div>
          )}
          <p className="text-[11px] text-green-600 font-semibold mt-1.5">{lb.roi_summary}</p>
        </div>
      )}

      {/* Competitor scores */}
      {competitorScores.length > 0 && (
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted-text)] mb-1.5 block">
            Competitor Scores
          </span>
          <div className="flex flex-wrap gap-2">
            {competitorScores.map((cs) => {
              const csColor = scoreColor(cs.overall_score);
              return (
                <div
                  key={cs.domain}
                  className="rounded-lg border border-[var(--border-warm)] px-3 py-1.5 text-center"
                >
                  <span className="text-[10px] text-[var(--muted-text)] block">{cs.company_name}</span>
                  <span className="text-lg font-bold" style={{ color: csColor }}>
                    {cs.overall_score.toFixed(1)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {(data.warnings?.length ?? 0) > 0 && (
        <div className="mt-2 text-[10px] text-amber-600">
          {(data.warnings ?? []).map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}
    </div>
  );
}

function AuditReportSkeleton() {
  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5">
      <div className="flex justify-between mb-3">
        <Skeleton className="h-3 w-40" />
        <Skeleton className="h-4 w-16" />
      </div>
      <Skeleton className="h-12 w-20 mb-4" />
      <div className="space-y-2 mb-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="grid grid-cols-[1fr_100px_40px] gap-2">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-1.5 w-full" />
            <Skeleton className="h-3 w-8" />
          </div>
        ))}
      </div>
      <Separator />
      <Skeleton className="h-24 w-full mt-3 rounded-lg" />
    </div>
  );
}
