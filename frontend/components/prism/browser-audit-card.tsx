"use client";

import { useRef, useCallback, useMemo } from "react";
import NumberFlow from "@number-flow/react";
import { useInView } from "react-intersection-observer";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { Monitor, Camera, Clock, ChevronRight } from "lucide-react";
import type { ModuleResult, BrowserAuditResult, DimensionScore } from "@/lib/types";

/**
 * BrowserAuditCard -- Glassmorphism container with TOC pattern,
 * quick stats, dimension score bars, provider detection, query results.
 * Matches Algolia audit SPA search audit design.
 */

interface BrowserAuditCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

/* ── Severity helpers ── */

type Severity = "critical" | "moderate" | "positive";

function scoreSeverity(score: number): Severity {
  if (score < 4) return "critical";
  if (score < 6.5) return "moderate";
  return "positive";
}

function severityFillColor(severity: Severity): string {
  if (severity === "critical") return "#DC2626";
  if (severity === "moderate") return "#D97706";
  return "#059669";
}

function severityTextColor(severity: Severity): string {
  if (severity === "critical") return "#DC2626";
  if (severity === "moderate") return "#D97706";
  return "#059669";
}

function severityLabel(severity: Severity): string {
  if (severity === "critical") return "CRITICAL";
  if (severity === "moderate") return "MODERATE";
  return "POSITIVE";
}

function severityLabelColor(severity: Severity): string {
  if (severity === "critical") return "#DC2626";
  if (severity === "moderate") return "#D97706";
  return "#059669";
}

/* ── TOC finding ID prefix ── */
function findingId(severity: Severity, index: number): string {
  const prefix = severity === "critical" ? "G" : severity === "moderate" ? "G" : "S";
  return `${prefix}${String(index + 1).padStart(2, "0")}`;
}

/* ── Group dimensions by severity ── */
interface SeverityGroup {
  severity: Severity;
  label: string;
  emoji: string;
  subtitle: string;
  bgColor: string;
  items: DimensionScore[];
}

function groupBySeverity(dimensions: DimensionScore[]): SeverityGroup[] {
  const critical: DimensionScore[] = [];
  const moderate: DimensionScore[] = [];
  const positive: DimensionScore[] = [];

  for (const d of dimensions) {
    const sev = scoreSeverity(d.score);
    if (sev === "critical") critical.push(d);
    else if (sev === "moderate") moderate.push(d);
    else positive.push(d);
  }

  const groups: SeverityGroup[] = [];
  if (critical.length > 0) {
    groups.push({
      severity: "critical",
      label: "Critical",
      emoji: "\ud83d\udd34",
      subtitle: "needs immediate attention",
      bgColor: "rgba(220,38,38,0.08)",
      items: critical,
    });
  }
  if (moderate.length > 0) {
    groups.push({
      severity: "moderate",
      label: "Moderate",
      emoji: "\ud83d\udfe1",
      subtitle: "improvement opportunities",
      bgColor: "rgba(217,119,6,0.08)",
      items: moderate,
    });
  }
  if (positive.length > 0) {
    groups.push({
      severity: "positive",
      label: "Strengths",
      emoji: "\ud83d\udfe2",
      subtitle: "working well",
      bgColor: "rgba(5,150,105,0.08)",
      items: positive,
    });
  }
  return groups;
}

export function BrowserAuditCard({ data, isLoading, error }: BrowserAuditCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const { ref: inViewRef, inView } = useInView({ triggerOnce: true, threshold: 0.2 });

  const setRefs = useCallback(
    (node: HTMLDivElement | null) => {
      (cardRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
      inViewRef(node);
    },
    [inViewRef],
  );

  if (isLoading) return <BrowserAuditSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Browser audit unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = (data.output ?? {}) as Partial<BrowserAuditResult>;
  const output = {
    dimension_scores: raw.dimension_scores ?? [],
    prospect_query_results: raw.prospect_query_results ?? [],
    competitor_results: raw.competitor_results ?? [],
    total_screenshots: raw.total_screenshots ?? 0,
    total_queries_executed: raw.total_queries_executed ?? 0,
    detected_search_provider: raw.detected_search_provider ?? null,
    search_bar_found: raw.search_bar_found ?? true,
  };
  const dimensions = output.dimension_scores;
  const overallScore =
    dimensions.length > 0
      ? dimensions.reduce((sum, d) => sum + d.score, 0) / dimensions.length
      : 0;
  const criticalCount = dimensions.filter((d) => scoreSeverity(d.score) === "critical").length;
  const groups = groupBySeverity(dimensions);

  return (
    <div
      ref={setRefs}
      className="my-2"
      style={{
        background: "rgba(255,255,255,0.72)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.85)",
        borderRadius: "20px",
        boxShadow:
          "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06), 0 16px 36px rgba(0,0,0,0.07), inset 0 1px 0 rgba(255,255,255,0.95)",
        padding: "24px",
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[#6B7280]">
          <Monitor className="h-3.5 w-3.5" />
          Browser Audit
        </div>
        <div className="flex items-center gap-1.5">
          {output.total_screenshots > 0 && (
            <Badge variant="outline" className="text-[10px] gap-1">
              <Camera className="h-2.5 w-2.5" />
              {output.total_screenshots}
            </Badge>
          )}
          <Badge variant="outline" className="text-[10px] font-mono">
            {data.module_version}
          </Badge>
        </div>
      </div>

      {/* Overall score big number */}
      <div className="flex items-end gap-3 mb-4">
        <div
          style={{ color: severityFillColor(scoreSeverity(overallScore)) }}
          className="text-4xl font-bold leading-none tracking-tight"
        >
          {inView ? (
            <NumberFlow
              value={parseFloat(overallScore.toFixed(1))}
              format={{ minimumFractionDigits: 1, maximumFractionDigits: 1 }}
            />
          ) : (
            "0.0"
          )}
        </div>
        <span className="pb-0.5 text-sm text-[#6B7280] opacity-50">/ 10</span>
      </div>

      {/* Provider detection badge */}
      {output.detected_search_provider && (
        <div
          className="mb-4"
          style={{
            background: "#FFFBEB",
            border: "1px solid #FDE68A",
            borderRadius: "6px",
            padding: "8px 12px",
            display: "inline-block",
          }}
        >
          <span className="text-[13px] text-[#92400E]">
            Detected:{" "}
            <span className="font-bold text-[#78350F]">{output.detected_search_provider}</span>
          </span>
        </div>
      )}

      {!output.search_bar_found && (
        <div className="mb-4 rounded-md bg-red-50 border border-red-200 px-3 py-1.5 text-[11px] text-red-600">
          No search bar found on this domain
        </div>
      )}

      {/* ── Quick Stats Row ── */}
      <div
        className="mb-5"
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px" }}
      >
        <div
          style={{
            background: "white",
            border: "1px solid #E5E7EB",
            borderRadius: "8px",
            textAlign: "center",
            padding: "16px",
          }}
        >
          <div style={{ fontSize: "28px", fontWeight: 600, color: "#DC2626" }}>{criticalCount}</div>
          <div
            style={{
              fontSize: "14px",
              color: "#6B7280",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginTop: "4px",
            }}
          >
            Critical Gaps
          </div>
        </div>
        <div
          style={{
            background: "white",
            border: "1px solid #E5E7EB",
            borderRadius: "8px",
            textAlign: "center",
            padding: "16px",
          }}
        >
          <div style={{ fontSize: "28px", fontWeight: 600, color: "#D97706" }}>
            {dimensions.length}
          </div>
          <div
            style={{
              fontSize: "14px",
              color: "#6B7280",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginTop: "4px",
            }}
          >
            Total Findings
          </div>
        </div>
        <div
          style={{
            background: "white",
            border: "1px solid #E5E7EB",
            borderRadius: "8px",
            textAlign: "center",
            padding: "16px",
          }}
        >
          <div
            style={{
              fontSize: "28px",
              fontWeight: 600,
              color: severityFillColor(scoreSeverity(overallScore)),
            }}
          >
            {overallScore.toFixed(1)}
          </div>
          <div
            style={{
              fontSize: "14px",
              color: "#6B7280",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginTop: "4px",
            }}
          >
            Overall Score
          </div>
        </div>
      </div>

      {/* ── TOC List ── */}
      {dimensions.length > 0 && (
        <div
          style={{
            border: "1px solid #E5E7EB",
            borderRadius: "10px",
            overflow: "hidden",
            marginBottom: "28px",
          }}
        >
          {groups.map((group) => {
            // Running index per severity for finding IDs
            let groupIndex = 0;
            return (
              <div key={group.severity}>
                {/* Group divider */}
                <div
                  style={{
                    background: group.bgColor,
                    padding: "8px 20px",
                    fontSize: "12px",
                    fontWeight: 600,
                    color: severityFillColor(group.severity),
                    borderBottom: "1px solid #E5E7EB",
                  }}
                >
                  {group.emoji} {group.label} &mdash; {group.subtitle}
                </div>
                {/* Rows */}
                {group.items.map((d) => {
                  const sev = scoreSeverity(d.score);
                  const fid = findingId(sev, groupIndex);
                  groupIndex++;
                  return (
                    <div
                      key={d.dimension}
                      className="toc-row group"
                      style={{
                        display: "grid",
                        gridTemplateColumns: "32px 1fr 160px 90px 72px 36px",
                        alignItems: "center",
                        padding: "13px 20px",
                        borderBottom: "1px solid #E5E7EB",
                        cursor: "pointer",
                        transition: "background 0.12s",
                      }}
                      onMouseEnter={(e) => {
                        (e.currentTarget as HTMLElement).style.background = "#F8F9FF";
                      }}
                      onMouseLeave={(e) => {
                        (e.currentTarget as HTMLElement).style.background = "transparent";
                      }}
                    >
                      {/* Col 1: Finding number */}
                      <span
                        style={{ fontSize: "12px", fontWeight: 700, color: "#6B7280" }}
                      >
                        {fid}
                      </span>
                      {/* Col 2: Area name */}
                      <span
                        style={{
                          fontSize: "14px",
                          fontWeight: 600,
                          color: "#23263B",
                          textTransform: "capitalize",
                        }}
                      >
                        {d.dimension.replace(/_/g, " ")}
                      </span>
                      {/* Col 3: Score bar track */}
                      <div
                        style={{
                          height: "6px",
                          background: "#E5E7EB",
                          borderRadius: "3px",
                          overflow: "hidden",
                        }}
                      >
                        <div
                          style={{
                            height: "100%",
                            width: `${d.score * 10}%`,
                            background: severityFillColor(sev),
                            borderRadius: "3px",
                            transition: "width 0.6s ease",
                          }}
                        />
                      </div>
                      {/* Col 4: Score value */}
                      <span
                        style={{
                          fontSize: "13px",
                          fontWeight: 700,
                          color: severityTextColor(sev),
                          textAlign: "right",
                        }}
                      >
                        {d.score}/10
                      </span>
                      {/* Col 5: Severity label */}
                      <span
                        style={{
                          fontSize: "10px",
                          fontWeight: 700,
                          textTransform: "uppercase",
                          color: severityLabelColor(sev),
                          textAlign: "center",
                        }}
                      >
                        {severityLabel(sev)}
                      </span>
                      {/* Col 6: Arrow (visible on hover) */}
                      <ChevronRight
                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                        style={{ width: "14px", height: "14px", color: "#6B7280" }}
                      />
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Dimension Score Bars (upgraded SPA style) ── */}
      {dimensions.length > 0 && (
        <div className="mb-4">
          <span
            className="block mb-2"
            style={{
              fontSize: "10px",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.1em",
              color: "#6B7280",
            }}
          >
            Dimension Scores
          </span>
          <div>
            {dimensions.map((d) => {
              const sev = scoreSeverity(d.score);
              return (
                <div
                  key={d.dimension}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "180px 1fr 48px",
                    gap: "12px",
                    alignItems: "center",
                    padding: "7px 0",
                    borderBottom: "1px solid #E5E7EB",
                  }}
                >
                  <span
                    style={{
                      fontSize: "13px",
                      color: "#23263B",
                      textTransform: "capitalize",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {d.dimension.replace(/_/g, " ")}
                  </span>
                  <div
                    style={{
                      height: "10px",
                      background: "#F5F5F7",
                      borderRadius: "5px",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        width: `${d.score * 10}%`,
                        background: severityFillColor(sev),
                        borderRadius: "5px",
                        transition: "width 0.6s ease",
                      }}
                    />
                  </div>
                  <span
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      textAlign: "right",
                      color: severityTextColor(sev),
                    }}
                  >
                    {d.score}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Query results summary ── */}
      {output.prospect_query_results.length > 0 && (
        <div className="mt-4">
          <div
            style={{ borderTop: "1px solid #E5E7EB", paddingTop: "16px", marginBottom: "12px" }}
          >
            <span
              style={{
                fontSize: "10px",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                color: "#6B7280",
              }}
            >
              Query Results ({output.total_queries_executed})
            </span>
          </div>
          <div className="space-y-1">
            {output.prospect_query_results.slice(0, 5).map((qr, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px]">
                <span className="font-mono text-[#23263B] truncate flex-1">{qr.query}</span>
                <div className="flex items-center gap-1 shrink-0">
                  <Clock className="h-2.5 w-2.5 text-[#6B7280]" />
                  <span
                    style={{
                      fontWeight: 600,
                      color:
                        qr.response_time_ms < 200
                          ? "#059669"
                          : qr.response_time_ms < 500
                            ? "#D97706"
                            : "#DC2626",
                    }}
                  >
                    {qr.response_time_ms}ms
                  </span>
                  <span className="text-[#6B7280]">{qr.result_count} results</span>
                </div>
              </div>
            ))}
            {output.prospect_query_results.length > 5 && (
              <p className="text-[10px] text-[#6B7280]">
                + {output.prospect_query_results.length - 5} more queries
              </p>
            )}
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

function BrowserAuditSkeleton() {
  return (
    <div
      className="my-2"
      style={{
        background: "rgba(255,255,255,0.72)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.85)",
        borderRadius: "20px",
        boxShadow:
          "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06), 0 16px 36px rgba(0,0,0,0.07), inset 0 1px 0 rgba(255,255,255,0.95)",
        padding: "24px",
      }}
    >
      <div className="flex justify-between mb-4">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-4 w-16" />
      </div>
      <Skeleton className="h-10 w-16 mb-4" />
      {/* Quick stats skeleton */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px" }} className="mb-5">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20 w-full rounded-lg" />
        ))}
      </div>
      {/* TOC skeleton */}
      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    </div>
  );
}
