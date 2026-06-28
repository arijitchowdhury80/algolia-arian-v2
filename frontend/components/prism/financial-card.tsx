"use client";

import { useRef, useCallback } from "react";
import NumberFlow from "@number-flow/react";
import { useInView } from "react-intersection-observer";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { DollarSign, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ModuleResult, FinancialPublicResult, FinancialPrivateResult } from "@/lib/types";

/**
 * FinancialCard — financial intelligence for public or private companies.
 * Detects public vs private by checking for `ticker` field in output.
 * Pattern: `.glow-card` (conic-gradient border glow on hover).
 */

interface FinancialCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

function formatCurrency(n: number): string {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
}

function confidenceColor(c: string): string {
  if (c === "high") return "text-green-600";
  if (c === "medium") return "text-amber-600";
  return "text-red-500";
}

export function FinancialCard({ data, isLoading, error }: FinancialCardProps) {
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

  if (isLoading) return <FinancialSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Financial data unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = data.output as Record<string, unknown>;
  const isPublic = "ticker" in raw && typeof raw.ticker === "string";

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
          background: conic-gradient(
            from var(--glow-angle, 0deg),
            transparent 0%,
            #003dff 10%,
            #5468ff 25%,
            transparent 40%
          );
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
        .glow-card.glow-active::before {
          opacity: 1;
        }
        .glow-card.glow-active {
          border-color: transparent;
          box-shadow: 0 4px 16px rgba(0, 61, 255, 0.08);
        }
      `}</style>

      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
          <DollarSign className="h-3.5 w-3.5" />
          Financials
        </div>
        <div className="flex items-center gap-1.5">
          {isPublic ? (
            <Badge variant="outline" className="text-[10px] bg-green-50 text-green-600 border-green-200">
              Public ({(raw as unknown as FinancialPublicResult).ticker})
            </Badge>
          ) : (
            <Badge variant="outline" className="text-[10px] bg-amber-50 text-amber-600 border-amber-200">
              Private (Estimated)
            </Badge>
          )}
          <Badge variant="outline" className="text-[10px] font-mono">
            {data.module_version}
          </Badge>
        </div>
      </div>

      <p className="text-[10px] text-[var(--muted-text)] mb-3">
        {data.duration_ms}ms
        {data.status !== "success" && (
          <span className="ml-2 text-amber-500">({data.status})</span>
        )}
      </p>

      {isPublic ? (
        <PublicFinancials output={raw as unknown as FinancialPublicResult} inView={inView} />
      ) : (
        <PrivateFinancials output={raw as unknown as FinancialPrivateResult} inView={inView} />
      )}

      {/* Warnings */}
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

function PublicFinancials({ output, inView }: { output: FinancialPublicResult; inView: boolean }) {
  const revenue3yr = output.revenue_3yr ?? [];
  const latestRevenue = revenue3yr.length > 0
    ? revenue3yr[revenue3yr.length - 1].revenue
    : 0;

  return (
    <>
      {/* Revenue — big animated */}
      <div className="flex items-end gap-2 mb-1">
        <div className="text-4xl font-bold text-[#23263B] leading-none tracking-tight">
          {inView ? (
            <NumberFlow
              value={latestRevenue}
              format={{ style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }}
            />
          ) : (
            "$0"
          )}
        </div>
      </div>
      <p className="text-[10px] text-[var(--muted-text)] mb-4">annual revenue</p>

      {/* Revenue trend — 3 data points */}
      {revenue3yr.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center gap-1.5 mb-2">
            <TrendingUp className="h-3 w-3 text-[var(--muted-text)]" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
              Revenue Trend
            </span>
          </div>
          <div className="flex items-end gap-4">
            {revenue3yr.map((yr) => {
              const maxRev = Math.max(...revenue3yr.map((r) => r.revenue));
              const heightPct = maxRev > 0 ? (yr.revenue / maxRev) * 100 : 0;
              return (
                <div key={yr.year} className="flex flex-col items-center gap-1">
                  <span className="text-[10px] font-semibold text-[#23263B]">
                    {formatCurrency(yr.revenue)}
                  </span>
                  <div
                    className="w-10 rounded-t bg-[#003DFF]/20"
                    style={{ height: `${Math.max(heightPct * 0.5, 4)}px` }}
                  />
                  <span className="text-[10px] text-[var(--muted-text)]">{yr.year}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <Separator className="mb-3" />

      {/* Margins */}
      <div className="grid grid-cols-2 gap-4 mb-3">
        <div>
          <p className="text-[10px] text-[var(--muted-text)]">Gross Margin</p>
          <p className="text-sm font-semibold text-[#23263B]">{((output.gross_margin ?? 0) * 100).toFixed(1)}%</p>
        </div>
        <div>
          <p className="text-[10px] text-[var(--muted-text)]">Operating Margin</p>
          <p className={cn(
            "text-sm font-semibold",
            (output.operating_margin ?? 0) >= 0 ? "text-green-600" : "text-red-500"
          )}>
            {((output.operating_margin ?? 0) * 100).toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Market cap */}
      {(output.market_cap ?? 0) > 0 && (
        <div className="mb-3">
          <p className="text-[10px] text-[var(--muted-text)]">Market Cap</p>
          <p className="text-sm font-semibold text-[#23263B]">{formatCurrency(output.market_cap)}</p>
        </div>
      )}

      {/* Analyst consensus */}
      {output.analyst_consensus && (
        <div className="rounded-md bg-[#F5F5F7] px-3 py-2">
          <p className="text-[10px] text-[var(--muted-text)]">Analyst Consensus</p>
          <p className="text-xs font-semibold text-[#23263B]">{output.analyst_consensus}</p>
        </div>
      )}
    </>
  );
}

function PrivateFinancials({ output, inView }: { output: FinancialPrivateResult; inView: boolean }) {
  return (
    <>
      {/* Revenue — big animated */}
      <div className="flex items-end gap-2 mb-1">
        <div className="text-4xl font-bold text-[#23263B] leading-none tracking-tight">
          {inView ? (
            <NumberFlow
              value={output.revenue_best_estimate ?? 0}
              format={{ style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }}
            />
          ) : (
            "$0"
          )}
        </div>
      </div>
      <p className="text-[10px] text-[var(--muted-text)] mb-2">estimated annual revenue</p>

      {/* Confidence band */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-[10px] text-[var(--muted-text)]">Range:</span>
        <span className="text-xs font-semibold text-[#23263B]">
          {formatCurrency(output.revenue_estimate_low ?? 0)} — {formatCurrency(output.revenue_estimate_high ?? 0)}
        </span>
        <Badge
          variant="outline"
          className={cn("text-[9px]", confidenceColor(output.confidence ?? "low"))}
        >
          {output.confidence ?? "low"} confidence
        </Badge>
      </div>

      {/* Visual confidence band */}
      <div className="relative h-2 bg-[#F5F5F7] rounded-full mb-4 overflow-hidden">
        <div
          className="absolute h-full bg-[#003DFF]/20 rounded-full"
          style={{
            left: `${((output.revenue_estimate_low ?? 0) / (output.revenue_estimate_high || 1)) * 50}%`,
            right: "0%",
          }}
        />
        <div
          className="absolute h-full w-1 bg-[#003DFF] rounded-full"
          style={{
            left: `${((output.revenue_best_estimate ?? 0) / (output.revenue_estimate_high || 1)) * 80}%`,
          }}
        />
      </div>

      <Separator className="mb-3" />

      {/* Estimation sources */}
      {(output.estimation_sources?.length ?? 0) > 0 && (
        <div>
          <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)] mb-2 block">
            Estimation Sources
          </span>
          <div className="flex flex-wrap gap-1.5">
            {(output.estimation_sources ?? []).map((src) => (
              <Badge key={src} variant="secondary" className="text-[10px]">
                {src}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function FinancialSkeleton() {
  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5">
      <div className="flex justify-between mb-3">
        <Skeleton className="h-3 w-20" />
        <div className="flex gap-1.5">
          <Skeleton className="h-4 w-24 rounded-full" />
          <Skeleton className="h-4 w-16" />
        </div>
      </div>
      <Skeleton className="h-10 w-32 mb-2" />
      <Skeleton className="h-3 w-24 mb-4" />
      <div className="flex gap-4 mb-3">
        <Skeleton className="h-12 w-10" />
        <Skeleton className="h-12 w-10" />
        <Skeleton className="h-12 w-10" />
      </div>
      <Separator />
      <div className="mt-3 grid grid-cols-2 gap-4">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    </div>
  );
}
