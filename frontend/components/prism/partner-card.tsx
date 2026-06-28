"use client";

import { useRef, useCallback } from "react";
import NumberFlow from "@number-flow/react";
import { useInView } from "react-intersection-observer";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Handshake, Users, BookOpen, Layers } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ModuleResult, PartnerResult } from "@/lib/types";

/**
 * PartnerCard — SI relationships, co-sell opportunities, case studies, and partner play.
 * Pattern: `.glow-card` (conic-gradient border glow on hover).
 */

interface PartnerCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

const confidenceColors: Record<string, { bg: string; text: string; border: string }> = {
  high: { bg: "bg-green-50", text: "text-green-600", border: "border-green-200" },
  medium: { bg: "bg-amber-50", text: "text-amber-600", border: "border-amber-200" },
  low: { bg: "bg-zinc-50", text: "text-zinc-500", border: "border-zinc-200" },
};

export function PartnerCard({ data, isLoading, error }: PartnerCardProps) {
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

  if (isLoading) return <PartnerSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Partner data unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = (data.output ?? {}) as Partial<PartnerResult>;
  const output = {
    partner_play_recommendation: raw.partner_play_recommendation ?? null,
    crossbeam_overlap_count: raw.crossbeam_overlap_count ?? null,
    si_relationships: raw.si_relationships ?? [],
    co_sell_opportunities: raw.co_sell_opportunities ?? [],
    case_studies: raw.case_studies ?? [],
  };

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
          <Handshake className="h-3.5 w-3.5" />
          Partner Intelligence
        </div>
        <Badge variant="outline" className="text-[10px] font-mono">
          {data.module_version}
        </Badge>
      </div>

      <p className="text-[10px] text-[var(--muted-text)] mb-3">
        {data.duration_ms}ms
        {data.status !== "success" && (
          <span className="ml-2 text-amber-500">({data.status})</span>
        )}
      </p>

      {/* Partner play recommendation */}
      {output.partner_play_recommendation && (
        <div className="rounded-lg bg-[#003DFF]/5 border border-[#003DFF]/15 px-3 py-2.5 mb-4">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[#003DFF]">
            Recommended Play
          </span>
          <p className="text-xs font-semibold text-[#23263B] mt-1">{output.partner_play_recommendation}</p>
        </div>
      )}

      {/* Crossbeam overlap */}
      {output.crossbeam_overlap_count != null && (
        <div className="flex items-center gap-2 mb-4">
          <Layers className="h-3.5 w-3.5 text-[var(--muted-text)]" />
          <span className="text-[10px] text-[var(--muted-text)]">Crossbeam Overlap:</span>
          <span className="text-sm font-bold text-[#23263B]">
            {inView ? <NumberFlow value={output.crossbeam_overlap_count} /> : "0"}
          </span>
          <span className="text-[10px] text-[var(--muted-text)]">accounts</span>
        </div>
      )}

      {/* SI relationships */}
      {output.si_relationships.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center gap-1.5 mb-2">
            <Users className="h-3.5 w-3.5 text-[var(--muted-text)]" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
              SI Relationships
            </span>
          </div>
          <div className="space-y-1.5">
            {output.si_relationships.map((si, i) => (
              <div
                key={i}
                className="flex items-center justify-between py-1.5 border-b border-[var(--border-warm)] last:border-b-0"
              >
                <div className="min-w-0">
                  <span className="text-xs font-semibold text-[#23263B]">{si.partner_name}</span>
                  <span className="ml-1.5 text-[11px] text-[var(--muted-text)]">{si.relationship_type}</span>
                </div>
                <span className="text-[10px] text-[var(--muted-text)] shrink-0 ml-2">{si.relevance}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <Separator className="mb-3" />

      {/* Co-sell opportunities */}
      {output.co_sell_opportunities.length > 0 && (
        <div className="mb-4">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)] mb-2 block">
            Co-Sell Opportunities
          </span>
          <div className="space-y-2">
            {output.co_sell_opportunities.map((opp, i) => {
              const cc = confidenceColors[opp.confidence] ?? confidenceColors.low;
              return (
                <div
                  key={i}
                  className="rounded-lg border border-[var(--border-warm)] px-3 py-2 transition-colors hover:bg-[#F8F9FF]"
                >
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-xs font-semibold text-[#23263B]">{opp.partner_name}</span>
                    <Badge variant="outline" className={cn("text-[9px]", cc.bg, cc.text, cc.border)}>
                      {opp.confidence}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-[var(--muted-text)] leading-relaxed">{opp.opportunity}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Vertical case studies */}
      {output.case_studies.length > 0 && (
        <>
          <Separator className="mb-3" />
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <BookOpen className="h-3.5 w-3.5 text-[var(--muted-text)]" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
                Relevant Case Studies
              </span>
            </div>
            <div className="space-y-2">
              {output.case_studies.map((cs, i) => (
                <div key={i} className="rounded-lg bg-[#F5F5F7] px-3 py-2">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="text-xs font-semibold text-[#23263B]">{cs.customer_name}</span>
                    <Badge variant="secondary" className="text-[9px]">{cs.vertical}</Badge>
                  </div>
                  <p className="text-[11px] text-[var(--muted-text)]">
                    <span className="font-semibold">{cs.algolia_product}</span> — {cs.key_result}
                  </p>
                </div>
              ))}
            </div>
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

function PartnerSkeleton() {
  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5">
      <div className="flex justify-between mb-3">
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-4 w-16" />
      </div>
      <Skeleton className="h-12 w-full rounded-lg mb-4" />
      <Skeleton className="h-4 w-40 mb-3" />
      <div className="space-y-2">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
      <Separator className="my-3" />
      <div className="space-y-2">
        <Skeleton className="h-10 w-full rounded-lg" />
        <Skeleton className="h-10 w-full rounded-lg" />
      </div>
    </div>
  );
}
