"use client";

import { useRef, useCallback, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { Swords } from "lucide-react";
import type { ModuleResult, CompetitorMatrixResult } from "@/lib/types";

/**
 * CompetitorMatrixCard -- capability matrix for prospect vs competitors.
 * Glassmorphism container with SPA-style capability indicators.
 */

interface CompetitorMatrixCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

/* ── Scenario badge config (SPA style) ── */
const scenarioConfig: Record<
  string,
  { label: string; bg: string; color: string }
> = {
  GOLDEN: { label: "\u2726 Golden Angle", bg: "#F0FDF4", color: "#059669" },
  OFFENSIVE: { label: "\u26A1 Disruptor", bg: "#EEF2FF", color: "#003DFF" },
  DEFENSIVE: { label: "\u2191 Ahead", bg: "#FFFBEB", color: "#D97706" },
  DISPLACEMENT: { label: "\u2261 Parity", bg: "#F9FAFB", color: "#6B7280" },
};

/* ── Capability indicator from score ── */
function capabilityIndicator(score: number): {
  symbol: string;
  color: string;
  label: string;
} {
  if (score >= 7)
    return { symbol: "\u2713", color: "#059669", label: "Supported" };
  if (score >= 4)
    return { symbol: "~", color: "#D97706", label: "Partial" };
  return { symbol: "\u2717", color: "#DC2626", label: "Missing" };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface CompetitorTier {
  competitor: string;
  search_stack?: string;
  our_play?: string;
  strategic_angle?: string;
  verified_url?: string;
}

export function CompetitorMatrixCard({
  data,
  isLoading,
  error,
}: CompetitorMatrixCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [hoveredCol, setHoveredCol] = useState<number | null>(null);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const card = cardRef.current;
      if (!card) return;
      const rect = card.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const angle =
        Math.atan2(e.clientY - cy, e.clientX - cx) * (180 / Math.PI) + 90;
      card.style.setProperty("--glow-angle", `${angle}deg`);
    },
    []
  );

  if (isLoading) return <CompetitorMatrixSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">
          Competitor matrix unavailable
        </p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const output = data.output as unknown as CompetitorMatrixResult;
  const competitors = output.competitors ?? [];
  const matrix = output.comparison_matrix ?? [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tiers: CompetitorTier[] =
    ((output as unknown as Record<string, unknown>).competitor_tiers as
      | CompetitorTier[]
      | undefined) ?? [];

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      className="my-2 p-5"
      style={
        {
          background: "rgba(255,255,255,0.72)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          border: "1px solid rgba(255,255,255,0.85)",
          borderRadius: "20px",
          boxShadow:
            "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06), 0 16px 36px rgba(0,0,0,0.07), inset 0 1px 0 rgba(255,255,255,0.95)",
        } as React.CSSProperties
      }
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
          <Swords className="h-3.5 w-3.5" />
          Competitor Matrix
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

      {/* Scenario badges (SPA style) */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {competitors.map((c) => {
          const sc = scenarioConfig[c.scenario] ?? scenarioConfig.DISPLACEMENT;
          return (
            <span
              key={c.domain}
              style={{
                fontSize: "10px",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                padding: "2px 8px",
                borderRadius: "20px",
                background: sc.bg,
                color: sc.color,
                display: "inline-block",
              }}
            >
              {sc.label} &mdash; {c.company_name}
            </span>
          );
        })}
      </div>

      <Separator className="mb-3" />

      {/* Competitor Tiers Section */}
      {tiers.length > 0 && (
        <div className="mb-4">
          <p
            style={{
              fontSize: "10px",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "#6B7280",
              marginBottom: "6px",
            }}
          >
            Competitor Tiers
          </p>
          <div
            style={{
              overflowX: "auto",
              WebkitOverflowScrolling: "touch",
              border: "1px solid #E5E7EB",
              borderRadius: "10px",
            }}
          >
            <table
              style={{
                tableLayout: "auto",
                width: "100%",
                minWidth: "600px",
                borderCollapse: "collapse",
                border: "none",
                fontSize: "11px",
              }}
            >
              <thead>
                <tr style={{ background: "#23263B" }}>
                  {["Competitor", "Search Stack", "Our Play", "Strategic Angle", "Verified"].map(
                    (h) => (
                      <th
                        key={h}
                        style={{
                          padding: "8px 10px",
                          fontSize: "11px",
                          fontWeight: 600,
                          textTransform: "uppercase",
                          letterSpacing: "0.08em",
                          color: "white",
                          textAlign: "left",
                        }}
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {tiers.map((t, idx) => (
                  <tr
                    key={t.competitor}
                    style={{
                      background: idx % 2 === 0 ? "white" : "#FAFAFA",
                      borderTop: "1px solid #E5E7EB",
                    }}
                  >
                    <td
                      style={{
                        padding: "8px 10px",
                        fontWeight: 600,
                        wordWrap: "break-word",
                      }}
                    >
                      {t.competitor}
                    </td>
                    <td style={{ padding: "8px 10px" }}>
                      {t.search_stack ?? "\u2014"}
                    </td>
                    <td style={{ padding: "8px 10px" }}>
                      {t.our_play ?? "\u2014"}
                    </td>
                    <td style={{ padding: "8px 10px" }}>
                      {t.strategic_angle ?? "\u2014"}
                    </td>
                    <td style={{ padding: "8px 10px" }}>
                      {t.verified_url ? (
                        <a
                          href={t.verified_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            fontSize: "10px",
                            fontWeight: 600,
                            color: "#003DFF",
                            background: "#EEF2FF",
                            padding: "2px 8px",
                            borderRadius: "20px",
                            textDecoration: "none",
                            whiteSpace: "nowrap",
                          }}
                        >
                          BuiltWith &rarr;
                        </a>
                      ) : (
                        <span style={{ color: "#9CA3AF" }}>\u2014</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Comparison matrix table */}
      {matrix.length > 0 && (
        <div
          style={{
            overflowX: "auto",
            WebkitOverflowScrolling: "touch",
            border: "1px solid #E5E7EB",
            borderRadius: "10px",
          }}
        >
          <table
            style={{
              tableLayout: "auto",
              width: "100%",
              minWidth: "680px",
              borderCollapse: "collapse",
              border: "none",
            }}
          >
            <thead>
              <tr style={{ background: "#23263B" }}>
                {/* Dimension column header */}
                <th
                  style={{
                    padding: "8px 10px",
                    fontSize: "11px",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    color: "white",
                    textAlign: "left",
                  }}
                >
                  Dimension
                </th>
                {/* Prospect "Today" column header */}
                <th
                  style={{
                    padding: "8px 10px",
                    fontSize: "11px",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    color: "white",
                    textAlign: "center",
                    background: "#7F1D1D",
                    borderBottom: "3px solid #DC2626",
                  }}
                  onMouseEnter={() => setHoveredCol(0)}
                  onMouseLeave={() => setHoveredCol(null)}
                >
                  Today
                </th>
                {/* Prospect "+ Algolia" column header */}
                <th
                  style={{
                    padding: "8px 10px",
                    fontSize: "11px",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    color: "white",
                    textAlign: "center",
                    background: "#1E3A8A",
                    borderBottom: "3px solid #003DFF",
                  }}
                  onMouseEnter={() => setHoveredCol(1)}
                  onMouseLeave={() => setHoveredCol(null)}
                >
                  + Algolia
                </th>
                {/* Competitor column headers */}
                {competitors.map((c, ci) => (
                  <th
                    key={c.domain}
                    style={{
                      padding: "8px 10px",
                      fontSize: "11px",
                      fontWeight: 600,
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      color: "white",
                      textAlign: "center",
                    }}
                    onMouseEnter={() => setHoveredCol(ci + 2)}
                    onMouseLeave={() => setHoveredCol(null)}
                  >
                    {c.company_name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrix.map((row, rowIdx) => {
                const prospectIndicator = capabilityIndicator(
                  row.prospect_score
                );
                /* For "+ Algolia" we boost the score by 2 (capped at 10) as a projection */
                const algoliaScore = Math.min(row.prospect_score + 2, 10);
                const algoliaIndicator = capabilityIndicator(algoliaScore);

                return (
                  <tr
                    key={row.dimension}
                    style={{
                      background: rowIdx % 2 === 0 ? "white" : "#FAFAFA",
                      borderTop: "1px solid #E5E7EB",
                    }}
                  >
                    {/* Dimension name */}
                    <td
                      style={{
                        padding: "8px 10px",
                        fontWeight: 600,
                        fontSize: "11px",
                        wordWrap: "break-word",
                      }}
                    >
                      {row.dimension}
                    </td>

                    {/* Prospect "Today" cell */}
                    <td
                      style={{
                        padding: "8px 6px",
                        textAlign: "center",
                        background:
                          hoveredCol === 0 ? "#FEE2E2" : "#FFF5F5",
                        fontSize: "16px",
                        fontWeight: 600,
                        color: prospectIndicator.color,
                      }}
                      onMouseEnter={() => setHoveredCol(0)}
                      onMouseLeave={() => setHoveredCol(null)}
                    >
                      {prospectIndicator.symbol}
                    </td>

                    {/* Prospect "+ Algolia" cell */}
                    <td
                      style={{
                        padding: "8px 6px",
                        textAlign: "center",
                        background:
                          hoveredCol === 1 ? "#DBEAFE" : "#EEF2FF",
                        fontSize: "16px",
                        fontWeight: 600,
                        color: algoliaIndicator.color,
                      }}
                      onMouseEnter={() => setHoveredCol(1)}
                      onMouseLeave={() => setHoveredCol(null)}
                    >
                      {algoliaIndicator.symbol}
                    </td>

                    {/* Competitor cells */}
                    {(row.competitor_scores ?? []).map((cs, ci) => {
                      const ind = capabilityIndicator(cs.score);
                      return (
                        <td
                          key={cs.company_name}
                          style={{
                            padding: "8px 6px",
                            textAlign: "center",
                            fontSize: "16px",
                            fontWeight: 600,
                            color: ind.color,
                            background:
                              hoveredCol === ci + 2
                                ? "#F3F4F6"
                                : "transparent",
                          }}
                          onMouseEnter={() => setHoveredCol(ci + 2)}
                          onMouseLeave={() => setHoveredCol(null)}
                        >
                          {ind.symbol}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Summary */}
      {output.summary && (
        <p className="mt-3 text-[11px] text-[var(--muted-text)] leading-relaxed">
          {output.summary}
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

function CompetitorMatrixSkeleton() {
  return (
    <div
      className="my-2 p-5"
      style={{
        background: "rgba(255,255,255,0.72)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.85)",
        borderRadius: "20px",
        boxShadow:
          "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06), 0 16px 36px rgba(0,0,0,0.07), inset 0 1px 0 rgba(255,255,255,0.95)",
      }}
    >
      <div className="flex justify-between mb-3">
        <Skeleton className="h-3 w-36" />
        <Skeleton className="h-4 w-16" />
      </div>
      <div className="flex gap-1.5 mb-3">
        <Skeleton className="h-5 w-24 rounded-full" />
        <Skeleton className="h-5 w-28 rounded-full" />
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
      <div className="space-y-2">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-6 w-full" />
        ))}
      </div>
    </div>
  );
}
