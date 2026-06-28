"use client";

import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { Search } from "lucide-react";
import type { ModuleResult, QueriesResult } from "@/lib/types";

/**
 * QueriesCard -- compact list of test queries grouped by type with difficulty badges.
 */

interface QueriesCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

const difficultyConfig: Record<string, { bg: string; text: string; border: string }> = {
  easy: { bg: "bg-green-500/15", text: "text-green-600", border: "border-green-500/30" },
  medium: { bg: "bg-amber-500/15", text: "text-amber-600", border: "border-amber-500/30" },
  hard: { bg: "bg-red-500/15", text: "text-red-600", border: "border-red-500/30" },
};

export function QueriesCard({ data, isLoading, error }: QueriesCardProps) {
  if (isLoading) return <QueriesSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Queries unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = (data.output ?? {}) as Partial<QueriesResult>;
  const output = {
    query_count: raw.query_count ?? 0,
    prospect_queries: raw.prospect_queries ?? [],
    competitor_query_sets: raw.competitor_query_sets ?? [],
  };
  const queries = output.prospect_queries ?? [];

  // Group by query_type
  const grouped: Record<string, typeof queries> = {};
  for (const q of queries) {
    const key = q.query_type;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(q);
  }

  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5 shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
          <Search className="h-3.5 w-3.5" />
          Test Queries
        </div>
        <Badge variant="outline" className="text-[10px] font-mono">
          {output.query_count} queries
        </Badge>
      </div>

      <p className="text-[10px] text-[var(--muted-text)] mb-3">
        {data.duration_ms}ms
      </p>

      {/* Query groups */}
      {Object.entries(grouped).map(([type, qs], gi) => (
        <div key={type}>
          {gi > 0 && <Separator className="my-2" />}
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted-text)] mb-1 block">
            {type}
          </span>
          <div className="space-y-1">
            {qs.map((q, i) => {
              const dc = difficultyConfig[q.difficulty] ?? difficultyConfig.medium;
              return (
                <div
                  key={i}
                  className="flex items-center gap-2 py-1 group"
                >
                  <Badge
                    variant="outline"
                    className={cn("text-[9px] shrink-0 px-1.5", dc.bg, dc.text, dc.border)}
                  >
                    {q.difficulty}
                  </Badge>
                  <span className="text-[11px] text-[#23263B] font-mono truncate">
                    {q.query}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {/* Competitor sets count */}
      {output.competitor_query_sets && output.competitor_query_sets.length > 0 && (
        <p className="mt-2 text-[10px] text-[var(--muted-text)]">
          + {output.competitor_query_sets.length} competitor query set{output.competitor_query_sets.length !== 1 ? "s" : ""}
        </p>
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

function QueriesSkeleton() {
  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5">
      <div className="flex justify-between mb-3">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-4 w-16" />
      </div>
      <div className="space-y-2">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="flex gap-2">
            <Skeleton className="h-4 w-12 rounded-full" />
            <Skeleton className="h-4 w-40" />
          </div>
        ))}
      </div>
    </div>
  );
}
