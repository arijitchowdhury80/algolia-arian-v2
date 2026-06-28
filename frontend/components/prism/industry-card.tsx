"use client";

import { useRef, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { BarChart3, TrendingUp } from "lucide-react";
import type { ModuleResult, IndustryResult } from "@/lib/types";

/**
 * IndustryCard -- vertical benchmarks with "you vs industry average" bars,
 * trends, pain-point mapping, and case study references.
 */

interface IndustryCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

export function IndustryCard({ data, isLoading, error }: IndustryCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);

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

  if (isLoading) return <IndustrySkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Industry data unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = (data.output ?? {}) as Partial<IndustryResult>;
  const output = {
    vertical: raw.vertical ?? "",
    benchmarks: raw.benchmarks ?? [],
    trends: raw.trends ?? [],
    pain_point_mapping: raw.pain_point_mapping ?? [],
    case_studies: raw.case_studies ?? [],
  };

  return (
    <div
      ref={cardRef}
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
          <BarChart3 className="h-3.5 w-3.5" />
          Industry Intelligence
        </div>
        <Badge variant="outline" className="text-[10px] font-mono">
          {output.vertical}
        </Badge>
      </div>

      <p className="text-[10px] text-[var(--muted-text)] mb-3">
        {data.duration_ms}ms
        {data.status !== "success" && (
          <span className="ml-2 text-amber-500">({data.status})</span>
        )}
      </p>

      {/* Benchmarks -- you vs industry avg */}
      {output.benchmarks.length > 0 && (
        <div className="space-y-2 mb-3">
          {output.benchmarks.map((b) => {
            const maxVal = Math.max(b.value, b.industry_avg, 1);
            const yourPct = (b.value / maxVal) * 100;
            const avgPct = (b.industry_avg / maxVal) * 100;
            const isLeading = b.value >= b.industry_avg;

            return (
              <div key={b.metric}>
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-[11px] font-medium text-[#23263B]">{b.metric}</span>
                  <span className="text-[10px] text-[var(--muted-text)]">{b.unit}</span>
                </div>
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] w-8 text-right text-[var(--muted-text)]">You</span>
                    <div className="flex-1 h-1.5 rounded-full bg-[#F5F5F7] overflow-hidden">
                      <div
                        className={cn("h-full rounded-full transition-all duration-700", isLeading ? "bg-green-500" : "bg-red-500")}
                        style={{ width: `${yourPct}%` }}
                      />
                    </div>
                    <span className={cn("text-[10px] font-semibold w-12 text-right", isLeading ? "text-green-600" : "text-red-600")}>
                      {b.value.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] w-8 text-right text-[var(--muted-text)]">Avg</span>
                    <div className="flex-1 h-1.5 rounded-full bg-[#F5F5F7] overflow-hidden">
                      <div
                        className="h-full rounded-full bg-[#5468FF]/40 transition-all duration-700"
                        style={{ width: `${avgPct}%` }}
                      />
                    </div>
                    <span className="text-[10px] font-semibold w-12 text-right text-[var(--muted-text)]">
                      {b.industry_avg.toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Separator className="mb-3" />

      {/* Trends */}
      {output.trends.length > 0 && (
        <div className="mb-3">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted-text)] flex items-center gap-1 mb-1.5">
            <TrendingUp className="h-3 w-3" /> Trends
          </span>
          <div className="space-y-1">
            {output.trends.map((t, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-[#5468FF] shrink-0 mt-1" />
                <span className="text-[11px] text-[#23263B] leading-snug">{t}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pain point mapping */}
      {output.pain_point_mapping.length > 0 && (
        <div className="mb-3">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted-text)] mb-1.5 block">
            Pain Points &rarr; Algolia
          </span>
          <div className="border border-[var(--border-warm)] rounded-lg overflow-hidden">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="bg-[#F5F5F7]">
                  <th className="text-left py-1.5 px-2.5 text-[10px] font-bold uppercase tracking-wider text-[var(--muted-text)]">Pain Point</th>
                  <th className="text-left py-1.5 px-2.5 text-[10px] font-bold uppercase tracking-wider text-[#003DFF]">Algolia Capability</th>
                </tr>
              </thead>
              <tbody>
                {output.pain_point_mapping.map((p, i) => (
                  <tr key={i} className="border-t border-[var(--border-warm)]">
                    <td className="py-1.5 px-2.5 text-[#23263B]">{p.pain_point}</td>
                    <td className="py-1.5 px-2.5 font-medium text-[#003DFF]">{p.algolia_capability}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Case studies */}
      {output.case_studies.length > 0 && (
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted-text)] mb-1.5 block">
            Case Studies
          </span>
          <div className="flex flex-wrap gap-1.5">
            {output.case_studies.map((cs, i) => (
              <Badge key={i} variant="secondary" className="text-[10px]">
                {cs.customer} ({cs.vertical}) &mdash; {cs.result}
              </Badge>
            ))}
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

function IndustrySkeleton() {
  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5">
      <div className="flex justify-between mb-3">
        <Skeleton className="h-3 w-36" />
        <Skeleton className="h-4 w-20" />
      </div>
      <div className="space-y-3 mb-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="space-y-1">
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-1.5 w-full" />
            <Skeleton className="h-1.5 w-3/4" />
          </div>
        ))}
      </div>
      <Separator />
      <div className="mt-3 space-y-1.5">
        <Skeleton className="h-3 w-48" />
        <Skeleton className="h-3 w-40" />
      </div>
    </div>
  );
}
