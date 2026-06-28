"use client";

import { useRef, useCallback, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { TrendingUp, Quote, Users, ChevronDown, ChevronUp, Shield, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ModuleResult, InvestorResult } from "@/lib/types";

/**
 * InvestorCard — Said vs Found, earnings quotes, board composition, risk factors, sales angles.
 * MOST IMPORTANT card for demos.
 * Pattern: `.glow-card` (conic-gradient border glow on hover).
 */

interface InvestorCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

export function InvestorCard({ data, isLoading, error }: InvestorCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [riskExpanded, setRiskExpanded] = useState(false);

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

  if (isLoading) return <InvestorSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Investor intelligence unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = (data.output ?? {}) as Partial<InvestorResult>;
  const output = {
    said_vs_found: raw.said_vs_found ?? [],
    earnings_quotes: raw.earnings_quotes ?? [],
    board_members: raw.board_members ?? [],
    risk_factors: raw.risk_factors ?? [],
    sales_angles: raw.sales_angles ?? [],
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
          <TrendingUp className="h-3.5 w-3.5" />
          Investor Intelligence
        </div>
        <Badge variant="outline" className="text-[10px] font-mono">
          {data.module_version}
        </Badge>
      </div>

      <p className="text-[10px] text-[var(--muted-text)] mb-4">
        {data.duration_ms}ms
        {data.status !== "success" && (
          <span className="ml-2 text-amber-500">({data.status})</span>
        )}
      </p>

      {/* Said vs Found — the hero section */}
      {output.said_vs_found.length > 0 && (
        <div className="mb-4">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[#003DFF] mb-2 block">
            Said vs Found
          </span>
          <div className="space-y-3">
            {output.said_vs_found.slice(0, 3).map((row, i) => (
              <div
                key={i}
                className="rounded-lg border border-[var(--border-warm)] p-3 transition-colors hover:bg-[#F8F9FF]"
              >
                {/* Exec said */}
                <div className="mb-2">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--muted-text)]">
                    Exec said:
                  </span>
                  <p className="text-xs text-[#23263B] italic leading-relaxed mt-0.5">
                    &ldquo;{row.exec_said}&rdquo;
                  </p>
                </div>
                {/* We found */}
                <div className="mb-2">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--muted-text)]">
                    We found:
                  </span>
                  <p className="text-xs text-[#23263B] leading-relaxed mt-0.5">
                    {row.we_found}
                  </p>
                </div>
                {/* Competitors doing */}
                <div className="mb-2">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--muted-text)]">
                    Competitors:
                  </span>
                  <p className="text-[11px] text-[var(--muted-text)] leading-relaxed mt-0.5">
                    {row.competitors_doing}
                  </p>
                </div>
                {/* Your move */}
                <Badge
                  variant="outline"
                  className="text-[10px] bg-[#003DFF]/5 text-[#003DFF] border-[#003DFF]/20"
                >
                  {row.your_move}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      )}

      <Separator className="mb-3" />

      {/* Earnings call quotes */}
      {output.earnings_quotes.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center gap-1.5 mb-2">
            <Quote className="h-3.5 w-3.5 text-[var(--muted-text)]" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
              Earnings Call Quotes
            </span>
          </div>
          <div className="space-y-2.5">
            {output.earnings_quotes.map((eq, i) => (
              <blockquote
                key={i}
                className="border-l-2 border-[#5468FF]/30 pl-3 py-1"
              >
                <p className="text-xs text-[#23263B] italic leading-relaxed">
                  &ldquo;{eq.quote}&rdquo;
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] font-semibold text-[#23263B]">{eq.speaker}</span>
                  <span className="text-[10px] text-[var(--muted-text)]">{eq.date}</span>
                  {eq.context && (
                    <span className="text-[10px] text-[var(--muted-text)]">({eq.context})</span>
                  )}
                </div>
              </blockquote>
            ))}
          </div>
        </div>
      )}

      {/* Board composition */}
      {output.board_members.length > 0 && (
        <>
          <Separator className="mb-3" />
          <div className="mb-4">
            <div className="flex items-center gap-1.5 mb-2">
              <Users className="h-3.5 w-3.5 text-[var(--muted-text)]" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
                Board Composition
              </span>
            </div>
            <div className="space-y-1">
              {output.board_members.map((bm) => (
                <div key={bm.name} className="flex items-center justify-between py-1.5 border-b border-[var(--border-warm)] last:border-b-0">
                  <div className="min-w-0">
                    <span className="text-xs font-semibold text-[#23263B]">{bm.name}</span>
                    <span className="ml-1.5 text-[11px] text-[var(--muted-text)]">{bm.background}</span>
                  </div>
                  {bm.is_tech_background && (
                    <Badge variant="outline" className="text-[9px] bg-cyan-50 text-cyan-600 border-cyan-200 shrink-0 ml-2">
                      Tech
                    </Badge>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* 10-K Risk factors — collapsible */}
      {output.risk_factors.length > 0 && (
        <>
          <Separator className="mb-3" />
          <div className="mb-4">
            <button
              onClick={() => setRiskExpanded(!riskExpanded)}
              className="flex items-center gap-1.5 mb-2 text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)] hover:text-[#003DFF] transition-colors"
              type="button"
            >
              <Shield className="h-3.5 w-3.5" />
              10-K Risk Factors ({output.risk_factors.length})
              {riskExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
            {riskExpanded && (
              <div className="flex flex-wrap gap-1.5">
                {output.risk_factors.map((rf, i) => (
                  <Badge key={i} variant="secondary" className="text-[10px]">
                    {rf}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* Top 5 sales angles */}
      {output.sales_angles.length > 0 && (
        <>
          <Separator className="mb-3" />
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Zap className="h-3.5 w-3.5 text-amber-500" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
                Top Sales Angles
              </span>
            </div>
            <ol className="space-y-1.5">
              {output.sales_angles.slice(0, 5).map((angle, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="shrink-0 flex items-center justify-center h-5 w-5 rounded-full bg-[#003DFF]/10 text-[10px] font-bold text-[#003DFF]">
                    {i + 1}
                  </span>
                  <span className="text-xs text-[#23263B] leading-relaxed">{angle}</span>
                </li>
              ))}
            </ol>
          </div>
        </>
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

function InvestorSkeleton() {
  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5">
      <div className="flex justify-between mb-4">
        <Skeleton className="h-3 w-36" />
        <Skeleton className="h-4 w-16" />
      </div>
      <Skeleton className="h-4 w-24 mb-3" />
      {[1, 2, 3].map((i) => (
        <div key={i} className="rounded-lg border border-[var(--border-warm)] p-3 mb-2">
          <Skeleton className="h-2.5 w-16 mb-2" />
          <Skeleton className="h-3 w-full mb-1" />
          <Skeleton className="h-2.5 w-16 mb-2" />
          <Skeleton className="h-3 w-5/6 mb-1" />
          <Skeleton className="h-5 w-28 rounded-full" />
        </div>
      ))}
      <Separator className="my-3" />
      <Skeleton className="h-12 w-full rounded-lg" />
    </div>
  );
}
