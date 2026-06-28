"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import { ShieldCheck, ChevronDown } from "lucide-react";
import type { ModuleResult, FactcheckResult } from "@/lib/types";

/**
 * FactcheckCard -- gate verdict badge, claim stats stacked bar,
 * correction count, expandable correction list.
 */

interface FactcheckCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

const verdictConfig: Record<
  string,
  { bg: string; text: string; border: string; label: string }
> = {
  PROCEED: { bg: "bg-green-500", text: "text-white", border: "border-green-600", label: "PROCEED" },
  WARN: { bg: "bg-amber-500", text: "text-white", border: "border-amber-600", label: "WARN" },
  BLOCKED: { bg: "bg-red-500", text: "text-white", border: "border-red-600", label: "BLOCKED" },
};

export function FactcheckCard({ data, isLoading, error }: FactcheckCardProps) {
  const [showCorrections, setShowCorrections] = useState(false);

  if (isLoading) return <FactcheckSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Factcheck unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = (data.output ?? {}) as Partial<FactcheckResult>;
  const output = {
    verdict: raw.verdict ?? "BLOCKED",
    total_claims: raw.total_claims ?? 0,
    verified_count: raw.verified_count ?? 0,
    plausible_count: raw.plausible_count ?? 0,
    unverified_count: raw.unverified_count ?? 0,
    contradicted_count: raw.contradicted_count ?? 0,
    corrections: raw.corrections ?? [],
    summary: raw.summary ?? null,
  };
  const vc = verdictConfig[output.verdict] ?? verdictConfig.BLOCKED;
  const total = output.total_claims || 1;
  const verifiedPct = (output.verified_count / total) * 100;
  const plausiblePct = (output.plausible_count / total) * 100;
  const unverifiedPct = (output.unverified_count / total) * 100;
  const contradictedPct = (output.contradicted_count / total) * 100;

  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5 shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
          <ShieldCheck className="h-3.5 w-3.5" />
          Fact Check
        </div>
        <Badge variant="outline" className="text-[10px] font-mono">
          {data.module_version}
        </Badge>
      </div>

      {/* Verdict badge */}
      <div className="flex items-center gap-3 mb-4">
        <span
          className={cn(
            "rounded-lg px-4 py-2 text-sm font-bold uppercase tracking-wider",
            vc.bg,
            vc.text
          )}
        >
          {vc.label}
        </span>
        <span className="text-[11px] text-[var(--muted-text)]">
          {output.total_claims} claims checked
        </span>
      </div>

      {/* Stacked bar */}
      <div className="mb-2">
        <div className="h-3 rounded-full overflow-hidden flex">
          {verifiedPct > 0 && (
            <div
              className="bg-green-500 transition-all duration-700"
              style={{ width: `${verifiedPct}%` }}
              title={`Verified: ${output.verified_count}`}
            />
          )}
          {plausiblePct > 0 && (
            <div
              className="bg-blue-500 transition-all duration-700"
              style={{ width: `${plausiblePct}%` }}
              title={`Plausible: ${output.plausible_count}`}
            />
          )}
          {unverifiedPct > 0 && (
            <div
              className="bg-amber-500 transition-all duration-700"
              style={{ width: `${unverifiedPct}%` }}
              title={`Unverified: ${output.unverified_count}`}
            />
          )}
          {contradictedPct > 0 && (
            <div
              className="bg-red-500 transition-all duration-700"
              style={{ width: `${contradictedPct}%` }}
              title={`Contradicted: ${output.contradicted_count}`}
            />
          )}
        </div>
        {/* Legend */}
        <div className="flex items-center gap-3 mt-1.5">
          <div className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-green-500" />
            <span className="text-[10px] text-[var(--muted-text)]">Verified ({output.verified_count})</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-blue-500" />
            <span className="text-[10px] text-[var(--muted-text)]">Plausible ({output.plausible_count})</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            <span className="text-[10px] text-[var(--muted-text)]">Unverified ({output.unverified_count})</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-red-500" />
            <span className="text-[10px] text-[var(--muted-text)]">Contradicted ({output.contradicted_count})</span>
          </div>
        </div>
      </div>

      <Separator className="my-3" />

      {/* Summary */}
      {output.summary && (
        <p className="text-[11px] text-[var(--muted-text)] leading-relaxed mb-3">
          {output.summary}
        </p>
      )}

      {/* Corrections */}
      {output.corrections.length > 0 && (
        <Collapsible open={showCorrections} onOpenChange={setShowCorrections}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full text-left group">
            <ChevronDown className="h-3 w-3 text-[var(--muted-text)] transition-transform group-data-[state=open]:rotate-180" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-red-600">
              Corrections ({output.corrections.length})
            </span>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-1.5 space-y-1.5">
            {output.corrections.map((c, i) => (
              <div
                key={i}
                className="rounded-lg border border-red-100 bg-red-50/50 p-2.5"
              >
                <div className="flex items-center gap-1.5 mb-0.5">
                  <Badge variant="outline" className="text-[9px] bg-red-500/10 text-red-600 border-red-500/25">
                    {c.source_module}
                  </Badge>
                </div>
                <p className="text-[11px] text-[#23263B] line-through mb-0.5">{c.claim_text}</p>
                <p className="text-[11px] text-green-700 font-medium">{c.corrected_value}</p>
                <p className="text-[10px] text-[var(--muted-text)] italic mt-0.5">{c.correction_reason}</p>
              </div>
            ))}
          </CollapsibleContent>
        </Collapsible>
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

function FactcheckSkeleton() {
  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5">
      <div className="flex justify-between mb-3">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-4 w-16" />
      </div>
      <Skeleton className="h-8 w-28 rounded-lg mb-3" />
      <Skeleton className="h-3 w-full rounded-full mb-2" />
      <div className="flex gap-3">
        <Skeleton className="h-2 w-16" />
        <Skeleton className="h-2 w-16" />
        <Skeleton className="h-2 w-16" />
        <Skeleton className="h-2 w-16" />
      </div>
    </div>
  );
}
