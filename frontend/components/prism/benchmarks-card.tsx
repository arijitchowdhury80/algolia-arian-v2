"use client";

import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { BarChart2 } from "lucide-react";
import type { ModuleResult, BenchmarkEntry } from "@/lib/types";

/**
 * BenchmarksCard -- vertical benchmarks with "you vs average" horizontal
 * bar comparisons. Vertical name + sample size badge. Confidence indicator.
 */

interface BenchmarksCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

export function BenchmarksCard({ data, isLoading, error }: BenchmarksCardProps) {
  if (isLoading) return <BenchmarksSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Benchmarks unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const rawOutput = data.output;
  const entries: BenchmarkEntry[] = Array.isArray(rawOutput) ? rawOutput : [];
  if (entries.length === 0) return null;

  // Group by vertical
  const grouped: Record<string, BenchmarkEntry[]> = {};
  for (const entry of entries) {
    if (!grouped[entry.vertical]) grouped[entry.vertical] = [];
    grouped[entry.vertical].push(entry);
  }

  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5 shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
          <BarChart2 className="h-3.5 w-3.5" />
          Vertical Benchmarks
        </div>
        <Badge variant="outline" className="text-[10px] font-mono">
          {data.module_version}
        </Badge>
      </div>

      {Object.entries(grouped).map(([vertical, benchmarks], gi) => {
        const sampleSize = benchmarks[0]?.sample_size ?? 0;
        const updatedAt = benchmarks[0]?.updated_at ?? "";

        return (
          <div key={vertical}>
            {gi > 0 && <Separator className="my-3" />}

            {/* Vertical header */}
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-semibold text-[#23263B]">{vertical}</span>
              <Badge variant="secondary" className="text-[9px]">
                n={sampleSize}
              </Badge>
              {updatedAt && (
                <span className="text-[9px] text-[var(--muted-text)] ml-auto">{updatedAt}</span>
              )}
            </div>

            {/* Metrics */}
            <div className="space-y-2">
              {benchmarks.map((b, i) => {
                const mv = b.metric_value as Record<string, number | undefined>;
                const yourVal = (mv.value ?? mv.you ?? 0) as number;
                const avgVal = (mv.average ?? mv.avg ?? mv.industry_avg ?? 0) as number;
                const maxVal = Math.max(yourVal, avgVal, 1);
                const yourPct = (yourVal / maxVal) * 100;
                const avgPct = (avgVal / maxVal) * 100;
                const isLeading = yourVal >= avgVal;
                const confidence = mv.confidence as string | undefined;

                return (
                  <div key={i}>
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-[11px] font-medium text-[#23263B]">{b.metric_name}</span>
                      {confidence && (
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-[9px]",
                            confidence === "high"
                              ? "bg-green-500/15 text-green-600 border-green-500/30"
                              : confidence === "medium"
                                ? "bg-amber-500/15 text-amber-600 border-amber-500/30"
                                : "bg-zinc-400/15 text-zinc-500 border-zinc-400/30"
                          )}
                        >
                          {confidence}
                        </Badge>
                      )}
                    </div>
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] w-8 text-right text-[var(--muted-text)]">You</span>
                        <div className="flex-1 h-1.5 rounded-full bg-[#F5F5F7] overflow-hidden">
                          <div
                            className={cn(
                              "h-full rounded-full transition-all duration-700",
                              isLeading ? "bg-green-500" : "bg-red-500"
                            )}
                            style={{ width: `${yourPct}%` }}
                          />
                        </div>
                        <span
                          className={cn(
                            "text-[10px] font-semibold w-12 text-right",
                            isLeading ? "text-green-600" : "text-red-600"
                          )}
                        >
                          {yourVal.toLocaleString()}
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
                          {avgVal.toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

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

function BenchmarksSkeleton() {
  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5">
      <div className="flex justify-between mb-3">
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-4 w-16" />
      </div>
      <Skeleton className="h-4 w-24 mb-2" />
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="space-y-1">
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-1.5 w-full" />
            <Skeleton className="h-1.5 w-3/4" />
          </div>
        ))}
      </div>
    </div>
  );
}
