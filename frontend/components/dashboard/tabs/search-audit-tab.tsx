"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { usePrismStore } from "@/lib/store";
import { BrowserAuditCard } from "@/components/prism/browser-audit-card";
import type { ModuleResult, ReportDimensionScore } from "@/lib/types";

/* ── Props ── */

interface TabProps {
  results: Record<string, ModuleResult>;
}

/* ── Helpers ── */

function getOutput(
  results: Record<string, ModuleResult>,
  moduleName: string,
): Record<string, unknown> | undefined {
  return results[moduleName]?.output as Record<string, unknown> | undefined;
}

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

function verdictFromScore(score: number): { label: string; color: string } {
  if (score >= 7) return { label: "EXCELLENT", color: "#059669" };
  if (score >= 4) return { label: "NEEDS IMPROVEMENT", color: "#D97706" };
  return { label: "CRITICAL", color: "#DC2626" };
}

function severityBadgeStyles(severity: Severity): {
  bg: string;
  text: string;
  label: string;
} {
  if (severity === "critical")
    return { bg: "rgba(220,38,38,0.1)", text: "#DC2626", label: "CRITICAL" };
  if (severity === "moderate")
    return { bg: "rgba(217,119,6,0.1)", text: "#D97706", label: "MODERATE" };
  return { bg: "rgba(5,150,105,0.1)", text: "#059669", label: "POSITIVE" };
}

/* ── Section wrapper with scroll-to and flash highlight ── */

function Section({
  id,
  highlightedSection,
  children,
}: {
  id: string;
  highlightedSection: string | null;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const activeSection = usePrismStore((s) => s.activeSection);

  useEffect(() => {
    if (activeSection === id && ref.current) {
      ref.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [activeSection, id]);

  return (
    <div
      ref={ref}
      id={id}
      className={cn(
        "mb-10 transition-all duration-700",
        highlightedSection === id &&
          "ring-2 ring-[#003DFF]/30 rounded-2xl ring-offset-4 ring-offset-[#F8F9FB]",
      )}
    >
      {children}
    </div>
  );
}

/* ── Skeleton loader ── */

function SectionSkeleton({ lines = 5 }: { lines?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="animate-pulse bg-[#E5E7EB] rounded h-4"
          style={{ width: `${60 + Math.random() * 40}%` }}
        />
      ))}
    </div>
  );
}

/* ── Empty state ── */

function EmptyState({ message }: { message: string }) {
  return (
    <div
      className="rounded-xl border border-dashed border-[#E5E7EB] px-6 py-10 text-center"
      style={{ background: "rgba(255,255,255,0.6)" }}
    >
      <p className="text-sm text-[#6B7280]">{message}</p>
    </div>
  );
}

/* ── Evidence badge ── */

function EvidenceBadge() {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-semibold tracking-wide"
      style={{
        background: "rgba(0,61,255,0.08)",
        color: "#003DFF",
      }}
    >
      Sourced from PRISM
    </span>
  );
}

/* ══════════════════════════════════════════════════════════════
   SearchAuditTab — main export
   ══════════════════════════════════════════════════════════════ */

export function SearchAuditTab({ results }: TabProps) {
  const highlightedSection = usePrismStore((s) => s.highlightedSection);

  const auditReportOutput = getOutput(results, "audit-report");
  const browserAuditResult = results["audit-browser"];

  /* Parse audit-report data */
  const overallScore =
    auditReportOutput != null
      ? (auditReportOutput.overall_score as number | undefined) ?? null
      : null;

  const dimensionScores =
    auditReportOutput != null
      ? ((auditReportOutput.dimension_scores as ReportDimensionScore[]) ?? [])
      : [];

  const criticalCount = dimensionScores.filter(
    (d) => d.severity === "critical",
  ).length;

  const totalFindings = dimensionScores.length;

  const verdict =
    overallScore !== null ? verdictFromScore(overallScore) : null;

  return (
    <div className="px-1 py-6" style={{ background: "#F8F9FB" }}>
      {/* ────────────────────────────────────────────────
          3.1 Score Summary
          ──────────────────────────────────────────────── */}
      <Section id="score-summary" highlightedSection={highlightedSection}>
        <p className="text-sm font-bold uppercase tracking-wide text-[#003DFF] mb-1">
          Score Summary
        </p>
        <h2 className="text-[1.75rem] font-semibold text-[#23263B] mb-1">
          Overall Search Score
        </h2>
        <div className="mb-4">
          <EvidenceBadge />
        </div>

        {auditReportOutput == null ? (
          <EmptyState message="Search audit not yet run. Ask aRRIe to run a full audit." />
        ) : (
          <div
            className="rounded-2xl p-6"
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
            {/* Large score number */}
            <div className="flex items-end gap-3 mb-5">
              <span
                style={{
                  fontSize: "72px",
                  fontWeight: 900,
                  lineHeight: 1,
                  letterSpacing: "-3px",
                  color:
                    overallScore !== null
                      ? severityFillColor(scoreSeverity(overallScore))
                      : "#6B7280",
                }}
              >
                {overallScore !== null ? overallScore.toFixed(1) : "--"}
              </span>
              <span
                className="pb-2 text-sm font-semibold uppercase tracking-wider text-[#6B7280] opacity-50"
              >
                / 10
              </span>
            </div>

            {/* Verdict badge */}
            {verdict && (
              <div className="mb-5">
                <span
                  className="inline-block rounded px-3 py-1 text-xs font-bold"
                  style={{
                    background: `${verdict.color}18`,
                    color: verdict.color,
                  }}
                >
                  {verdict.label}
                </span>
              </div>
            )}

            {/* Quick stat cards row */}
            <div
              className="grid gap-4 mb-2"
              style={{ gridTemplateColumns: "1fr 1fr 1fr" }}
            >
              {/* Critical count */}
              <div
                className="rounded-lg border border-[#E5E7EB] bg-white text-center p-4"
              >
                <div
                  className="text-[28px] font-semibold"
                  style={{ color: "#DC2626" }}
                >
                  {criticalCount}
                </div>
                <div className="mt-1 text-sm uppercase tracking-wider text-[#6B7280]">
                  Critical
                </div>
              </div>

              {/* Total findings */}
              <div
                className="rounded-lg border border-[#E5E7EB] bg-white text-center p-4"
              >
                <div
                  className="text-[28px] font-semibold"
                  style={{ color: "#D97706" }}
                >
                  {totalFindings}
                </div>
                <div className="mt-1 text-sm uppercase tracking-wider text-[#6B7280]">
                  Total Findings
                </div>
              </div>

              {/* Overall score */}
              <div
                className="rounded-lg border border-[#E5E7EB] bg-white text-center p-4"
              >
                <div
                  className="text-[28px] font-semibold"
                  style={{
                    color:
                      overallScore !== null
                        ? severityFillColor(scoreSeverity(overallScore))
                        : "#6B7280",
                  }}
                >
                  {overallScore !== null ? overallScore.toFixed(1) : "--"}
                </div>
                <div className="mt-1 text-sm uppercase tracking-wider text-[#6B7280]">
                  Overall Score
                </div>
              </div>
            </div>
          </div>
        )}
      </Section>

      {/* ────────────────────────────────────────────────
          3.2 Score by Dimension
          ──────────────────────────────────────────────── */}
      <Section id="score-dimensions" highlightedSection={highlightedSection}>
        <p className="text-sm font-bold uppercase tracking-wide text-[#003DFF] mb-1">
          Score by Dimension
        </p>
        <h2 className="text-[1.75rem] font-semibold text-[#23263B] mb-1">
          Dimension Breakdown
        </h2>
        <div className="mb-4">
          <EvidenceBadge />
        </div>

        {auditReportOutput == null ? (
          <SectionSkeleton lines={10} />
        ) : dimensionScores.length === 0 ? (
          <EmptyState message="No dimension scores available." />
        ) : (
          <div
            className="rounded-2xl overflow-hidden"
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
            {dimensionScores.map((d, idx) => {
              const sev = d.severity ?? scoreSeverity(d.score);
              const badge = severityBadgeStyles(sev);
              const isEven = idx % 2 === 0;

              return (
                <div
                  key={d.dimension}
                  className="grid items-center gap-3 px-5 py-3"
                  style={{
                    gridTemplateColumns: "200px 1fr 56px 90px",
                    background: isEven ? "#F8F9FB" : "white",
                    borderBottom:
                      idx < dimensionScores.length - 1
                        ? "1px solid #E5E7EB"
                        : "none",
                  }}
                >
                  {/* Dimension name */}
                  <span
                    className="text-sm font-medium text-[#23263B] capitalize truncate"
                  >
                    {d.dimension.replace(/_/g, " ")}
                  </span>

                  {/* Score bar */}
                  <div
                    className="h-2.5 rounded-full overflow-hidden"
                    style={{ background: "#E5E7EB" }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${d.score * 10}%`,
                        background: severityFillColor(sev),
                        transition: "width 0.6s ease",
                      }}
                    />
                  </div>

                  {/* Score number */}
                  <span
                    className="text-sm font-bold text-right"
                    style={{ color: severityFillColor(sev) }}
                  >
                    {d.score}/10
                  </span>

                  {/* Severity badge */}
                  <span
                    className="inline-flex justify-center items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase"
                    style={{
                      background: badge.bg,
                      color: badge.text,
                    }}
                  >
                    {badge.label}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </Section>

      {/* ────────────────────────────────────────────────
          3.3 Per-Finding Details (Browser Audit)
          ──────────────────────────────────────────────── */}
      <Section id="findings" highlightedSection={highlightedSection}>
        <p className="text-sm font-bold uppercase tracking-wide text-[#003DFF] mb-1">
          Per-Finding Details
        </p>
        <h2 className="text-[1.75rem] font-semibold text-[#23263B] mb-1">
          Browser Audit Findings
        </h2>
        <div className="mb-4">
          <EvidenceBadge />
        </div>

        {browserAuditResult != null ? (
          <BrowserAuditCard data={browserAuditResult} />
        ) : (
          <EmptyState message="Browser audit not yet run." />
        )}
      </Section>
    </div>
  );
}
