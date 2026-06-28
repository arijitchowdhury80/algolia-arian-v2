"use client";

import { useRef, useCallback } from "react";
import NumberFlow from "@number-flow/react";
import { useInView } from "react-intersection-observer";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { AlertTriangle } from "lucide-react";
import { EvidenceBadge } from "./evidence-badge";
import type { ModuleResult, BusinessCaseResult } from "@/lib/types";

/**
 * BusinessCaseCard -- the money shot. Said vs Found table, ROI levers,
 * displacement model, timing signals.
 */

interface BusinessCaseCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

const urgencyConfig: Record<string, { bg: string; text: string; border: string }> = {
  HIGH: { bg: "bg-red-50", text: "text-red-600", border: "border-red-200" },
  MEDIUM: { bg: "bg-amber-50", text: "text-amber-600", border: "border-amber-200" },
  LOW: { bg: "bg-green-50", text: "text-green-600", border: "border-green-200" },
};

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export function BusinessCaseCard({ data, isLoading, error }: BusinessCaseCardProps) {
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

  if (isLoading) return <BusinessCaseSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Business case unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = (data.output ?? {}) as Partial<BusinessCaseResult>;
  const output = {
    total_roi_conservative: raw.total_roi_conservative ?? 0,
    total_roi_moderate: raw.total_roi_moderate ?? 0,
    said_vs_found: raw.said_vs_found ?? [],
    roi_levers: raw.roi_levers ?? [],
    displacement_model: raw.displacement_model ?? null,
    timing_signals: raw.timing_signals ?? [],
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
          border-radius: 20px;
          background: rgba(255, 255, 255, 0.72);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.85);
          isolation: isolate;
          transition: box-shadow 0.2s;
          box-shadow: 0 2px 8px rgba(33, 36, 61, 0.10);
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
          border-radius: calc(20px - 1px);
          background: rgba(255, 255, 255, 0.72);
          z-index: -1;
        }
        .glow-card.glow-active::before { opacity: 1; }
        .glow-card.glow-active { border-color: transparent; box-shadow: 0 4px 16px rgba(0, 61, 255, 0.08); }
      `}</style>

      {/* Section Chrome */}
      <div className="mb-1">
        <div
          style={{
            fontSize: "14px",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            color: "#003DFF",
            marginBottom: "4px",
          }}
        >
          Business Case &middot; The Hook
        </div>
        <h2
          style={{
            fontSize: "1.75rem",
            fontWeight: 600,
            color: "#23263B",
            marginBottom: "6px",
            lineHeight: 1.2,
          }}
        >
          Said vs. Found
        </h2>
        <p
          style={{
            fontSize: "0.9rem",
            color: "#6B7280",
            marginBottom: "24px",
          }}
        >
          Leadership&apos;s stated priorities &mdash; compared to what our audit found.
        </p>
      </div>

      {/* ROI headline numbers */}
      <div className="flex items-center gap-6 mb-4">
        <div>
          <span className="text-[10px] text-[var(--muted-text)] block mb-0.5">Conservative</span>
          <div className="text-2xl font-bold text-[#059669] leading-none">
            {inView ? (
              <NumberFlow value={output.total_roi_conservative} format={{ style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }} />
            ) : (
              "$0"
            )}
          </div>
        </div>
        <div>
          <span className="text-[10px] text-[var(--muted-text)] block mb-0.5">Moderate</span>
          <div className="text-2xl font-bold text-[#003DFF] leading-none">
            {inView ? (
              <NumberFlow value={output.total_roi_moderate} format={{ style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }} />
            ) : (
              "$0"
            )}
          </div>
        </div>
      </div>

      <Separator className="mb-3" />

      {/* Said vs Found — 3-column table */}
      {output.said_vs_found.length > 0 && (
        <div className="mb-4">
          <table
            style={{
              tableLayout: "fixed",
              width: "100%",
              borderCollapse: "collapse",
              fontSize: "14px",
              background: "white",
              borderRadius: "8px",
              overflow: "hidden",
              boxShadow: "0 2px 8px rgba(33,36,61,0.10)",
            }}
          >
            <colgroup>
              <col style={{ width: "30%" }} />
              <col style={{ width: "35%" }} />
              <col style={{ width: "35%" }} />
            </colgroup>
            <thead>
              <tr>
                <th
                  style={{
                    textAlign: "left",
                    padding: "10px 14px",
                    fontSize: "14px",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    fontWeight: 600,
                    background: "#F0FDF4",
                    color: "#059669",
                  }}
                >
                  They Said
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: "10px 14px",
                    fontSize: "14px",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    fontWeight: 600,
                    background: "#FEF2F2",
                    color: "#DC2626",
                  }}
                >
                  We Found
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: "10px 14px",
                    fontSize: "14px",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    fontWeight: 600,
                    background: "#EEF2FF",
                    color: "#003DFF",
                  }}
                >
                  Algolia Solution
                </th>
              </tr>
            </thead>
            <tbody>
              {output.said_vs_found.map((row, i) => {
                const isLast = i === output.said_vs_found.length - 1;
                const algSolution = [row.your_move, row.competitors_doing]
                  .filter(Boolean)
                  .join(" ");
                return (
                  <tr
                    key={i}
                    style={{
                      verticalAlign: "top",
                      borderBottom: isLast ? "none" : "1px solid #E5E7EB",
                    }}
                    className="hover:bg-[#FAFBFF] transition-colors"
                  >
                    {/* They Said */}
                    <td style={{ padding: "16px", verticalAlign: "top" }}>
                      <p
                        style={{
                          fontStyle: "italic",
                          color: "#23263B",
                          lineHeight: 1.5,
                          marginBottom: "8px",
                        }}
                      >
                        &ldquo;{row.exec_said}&rdquo;
                      </p>
                      <span
                        style={{
                          fontSize: "12px",
                          color: "#003DFF",
                          fontWeight: 600,
                        }}
                      >
                        Source
                      </span>
                    </td>
                    {/* We Found */}
                    <td style={{ padding: "16px", verticalAlign: "top" }}>
                      <p
                        style={{
                          fontSize: "14px",
                          fontWeight: 600,
                          color: "#23263B",
                          lineHeight: 1.4,
                          marginBottom: "6px",
                        }}
                      >
                        <span
                          style={{ color: "#DC2626", marginRight: "4px" }}
                          aria-hidden="true"
                        >
                          &#10007;
                        </span>
                        {row.we_found}
                      </p>
                      <EvidenceBadge tier="VERIFIED" className="mt-1" />
                    </td>
                    {/* Algolia Solution */}
                    <td style={{ padding: "16px", verticalAlign: "top" }}>
                      <p
                        style={{
                          fontSize: "12px",
                          color: "#23263B",
                          lineHeight: 1.6,
                        }}
                      >
                        {algSolution || "See Search Audit tab"}
                      </p>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ROI levers */}
      {output.roi_levers.length > 0 && (
        <div className="mb-3">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted-text)] mb-1.5 block">
            ROI Levers
          </span>
          <div className="space-y-1">
            {output.roi_levers.map((lever, i) => (
              <div key={i} className="flex items-center justify-between py-1 border-b border-[var(--border-warm)] last:border-b-0">
                <span className="text-[11px] text-[#23263B]">{lever.lever}</span>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-green-600 font-semibold">
                    {formatCurrency(lever.conservative_value)}
                  </span>
                  <span className="text-[10px] text-[var(--muted-text)]">&ndash;</span>
                  <span className="text-[10px] text-[#003DFF] font-semibold">
                    {formatCurrency(lever.moderate_value)}
                  </span>
                  <span className="text-[9px] text-[var(--muted-text)]">{lever.unit}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Displacement model */}
      {output.displacement_model && (
        <div className="mb-3 rounded-lg bg-[#F5F5F7] p-3">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted-text)] mb-1 block">
            Displacement Model
          </span>
          <div className="grid grid-cols-3 gap-2 text-[11px]">
            <div>
              <span className="text-[var(--muted-text)] block text-[9px]">Current ({output.displacement_model.current_vendor})</span>
              <span className="font-semibold text-red-600">{formatCurrency(output.displacement_model.current_tco)}</span>
            </div>
            <div>
              <span className="text-[var(--muted-text)] block text-[9px]">Algolia TCO</span>
              <span className="font-semibold text-[#003DFF]">{formatCurrency(output.displacement_model.algolia_tco)}</span>
            </div>
            <div>
              <span className="text-[var(--muted-text)] block text-[9px]">3-Year Savings</span>
              <span className="font-semibold text-green-600">{formatCurrency(output.displacement_model.savings_3yr)}</span>
            </div>
          </div>
        </div>
      )}

      {/* Timing signals */}
      {output.timing_signals.length > 0 && (
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted-text)] mb-1.5 block flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" /> Timing Signals
          </span>
          <div className="flex flex-wrap gap-1.5">
            {output.timing_signals.map((ts, i) => {
              const uc = urgencyConfig[ts.urgency] ?? urgencyConfig.LOW;
              return (
                <Badge
                  key={i}
                  variant="outline"
                  className={cn("text-[10px]", uc.bg, uc.text, uc.border)}
                >
                  {ts.urgency} &mdash; {ts.signal}
                </Badge>
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

function BusinessCaseSkeleton() {
  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5">
      <div className="flex justify-between mb-3">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-4 w-16" />
      </div>
      <div className="flex gap-6 mb-4">
        <div>
          <Skeleton className="h-2 w-16 mb-1" />
          <Skeleton className="h-8 w-20" />
        </div>
        <div>
          <Skeleton className="h-2 w-16 mb-1" />
          <Skeleton className="h-8 w-20" />
        </div>
      </div>
      <Separator />
      <div className="mt-3 space-y-2">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-6 w-full" />
        ))}
      </div>
    </div>
  );
}
