"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { usePrismStore } from "@/lib/store";
import { BusinessCaseCard } from "@/components/prism/business-case-card";
import { CustomerProofCard } from "@/components/prism/customer-proof-card";
import { ROICalculator } from "@/components/prism/roi-calculator";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, Calculator, MessageSquareQuote, Users, Zap } from "lucide-react";
import type { ModuleResult, BusinessCaseResult, NewsResult } from "@/lib/types";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface TabProps {
  results: Record<string, ModuleResult>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getOutput(
  results: Record<string, ModuleResult>,
  moduleName: string
): Record<string, unknown> | undefined {
  return results[moduleName]?.output as Record<string, unknown> | undefined;
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

// ---------------------------------------------------------------------------
// Section wrapper with scroll-to + highlight flash
// ---------------------------------------------------------------------------

function Section({
  id,
  children,
}: {
  id: string;
  children: React.ReactNode;
}) {
  const sectionRef = useRef<HTMLElement>(null);
  const activeSection = usePrismStore((s) => s.activeSection);
  const highlightedSection = usePrismStore((s) => s.highlightedSection);

  useEffect(() => {
    if (activeSection === id && sectionRef.current) {
      sectionRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [activeSection, id]);

  return (
    <section
      ref={sectionRef}
      id={id}
      className={cn(
        "mb-10 scroll-mt-6 rounded-2xl transition-all duration-700",
        highlightedSection === id &&
          "ring-2 ring-[#003DFF]/30 ring-offset-2 animate-pulse"
      )}
    >
      {children}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Section chrome (eyebrow + title + subtitle)
// ---------------------------------------------------------------------------

function SectionChrome({
  eyebrow,
  title,
  subtitle,
  icon,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span
          className="font-bold uppercase tracking-wide"
          style={{
            fontSize: 14,
            color: "#003DFF",
            letterSpacing: "0.08em",
          }}
        >
          {eyebrow}
        </span>
      </div>
      <h2
        className="font-semibold"
        style={{ fontSize: "1.75rem", color: "#23263B", lineHeight: 1.2 }}
      >
        {title}
      </h2>
      <p className="mt-1" style={{ fontSize: "0.9rem", color: "#6B7280" }}>
        {subtitle}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function EmptyState({ message }: { message: string }) {
  return (
    <div
      className="flex items-center justify-center rounded-xl border border-dashed py-12 px-6"
      style={{ borderColor: "#E5E7EB", background: "#FAFBFC" }}
    >
      <p className="text-sm" style={{ color: "#6B7280" }}>
        {message}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 4.1 Said vs Found section
// ---------------------------------------------------------------------------

function SaidVsFoundSection({
  results,
}: {
  results: Record<string, ModuleResult>;
}) {
  const bcOutput = getOutput(results, "synth-business-case") as
    | Partial<BusinessCaseResult>
    | undefined;
  const bcModuleResult = results["synth-business-case"];
  const saidVsFound = bcOutput?.said_vs_found ?? [];

  return (
    <Section id="said-vs-found">
      <SectionChrome
        eyebrow="Business Case"
        title="Said vs. Found"
        subtitle="Leadership's stated priorities compared to what our audit found."
        icon={<MessageSquareQuote className="h-4 w-4 text-[#003DFF]" />}
      />

      {bcModuleResult && saidVsFound.length > 0 ? (
        <BusinessCaseCard data={bcModuleResult} />
      ) : saidVsFound.length > 0 ? (
        /* Fallback: 4-column table */
        <div
          style={{
            overflowX: "auto",
            WebkitOverflowScrolling: "touch",
            border: "1px solid #E5E7EB",
            borderRadius: 12,
          }}
        >
          <table
            style={{
              tableLayout: "fixed",
              width: "100%",
              minWidth: 800,
              borderCollapse: "collapse",
              fontSize: 14,
            }}
          >
            <colgroup>
              <col style={{ width: "25%" }} />
              <col style={{ width: "25%" }} />
              <col style={{ width: "25%" }} />
              <col style={{ width: "25%" }} />
            </colgroup>
            <thead>
              <tr>
                {[
                  { label: "They Said", bg: "#F0FDF4", color: "#059669" },
                  { label: "We Found", bg: "#FEF2F2", color: "#DC2626" },
                  {
                    label: "Competitors Doing",
                    bg: "#FFFBEB",
                    color: "#D97706",
                  },
                  { label: "Your Move", bg: "#EEF2FF", color: "#003DFF" },
                ].map((col) => (
                  <th
                    key={col.label}
                    style={{
                      textAlign: "left",
                      padding: "10px 14px",
                      fontSize: 14,
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      fontWeight: 600,
                      background: col.bg,
                      color: col.color,
                    }}
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {saidVsFound.map((row, i) => (
                <tr
                  key={i}
                  className="hover:bg-[#FAFBFF] transition-colors"
                  style={{
                    verticalAlign: "top",
                    borderBottom:
                      i === saidVsFound.length - 1
                        ? "none"
                        : "1px solid #E5E7EB",
                    background: i % 2 === 0 ? "white" : "#FAFAFA",
                  }}
                >
                  <td style={{ padding: 14, fontStyle: "italic", color: "#23263B" }}>
                    &ldquo;{row.exec_said}&rdquo;
                  </td>
                  <td style={{ padding: 14, color: "#23263B" }}>
                    <span style={{ color: "#DC2626", marginRight: 4 }}>&#10007;</span>
                    {row.we_found}
                  </td>
                  <td style={{ padding: 14, color: "#23263B" }}>
                    {row.competitors_doing || "\u2014"}
                  </td>
                  <td style={{ padding: 14, color: "#23263B", fontWeight: 500 }}>
                    {row.your_move || "\u2014"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState message="Run the business case module to see Said vs. Found analysis." />
      )}
    </Section>
  );
}

// ---------------------------------------------------------------------------
// 4.2 Revenue & ROI Calculator section
// ---------------------------------------------------------------------------

function ROISection({
  results,
}: {
  results: Record<string, ModuleResult>;
}) {
  const bcOutput = getOutput(results, "synth-business-case") as
    | Partial<BusinessCaseResult>
    | undefined;

  const conservative = bcOutput?.total_roi_conservative ?? 0;
  const moderate = bcOutput?.total_roi_moderate ?? 0;
  const hasData = conservative > 0 || moderate > 0;

  return (
    <Section id="roi-calculator">
      <SectionChrome
        eyebrow="Business Case"
        title="Revenue & ROI Calculator"
        subtitle="Model the revenue impact of upgrading site search with Algolia."
        icon={<Calculator className="h-4 w-4 text-[#003DFF]" />}
      />

      {hasData ? (
        <>
          {/* Two-panel: ROI summary left, calculator right */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Left: ROI summary from business case */}
            <div
              className="rounded-xl p-6"
              style={{
                background: "linear-gradient(135deg, #090e24, #1a2356)",
                boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
              }}
            >
              <p
                className="uppercase tracking-wide mb-4"
                style={{ fontSize: 11, color: "#94A3B8", letterSpacing: "0.08em" }}
              >
                Projected Annual ROI
              </p>
              <div className="flex items-end gap-8 mb-6">
                <div>
                  <span className="block text-xs text-slate-400 mb-1">Conservative</span>
                  <span className="text-3xl font-bold text-[#059669]">
                    {formatCurrency(conservative)}
                  </span>
                </div>
                <div>
                  <span className="block text-xs text-slate-400 mb-1">Moderate</span>
                  <span className="text-3xl font-bold text-[#5468FF]">
                    {formatCurrency(moderate)}
                  </span>
                </div>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                Based on search conversion lift, AOV increase, bounce reduction, and
                no-results recovery across verified case study benchmarks.
              </p>
            </div>

            {/* Right: Interactive ROI calculator */}
            <div>
              <ROICalculator compact />
            </div>
          </div>

          {/* Revenue at Risk bounce cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              {
                label: "Conservative",
                value: conservative,
                color: "#059669",
                bgFrom: "#F0FDF4",
                bgTo: "#ECFDF5",
              },
              {
                label: "Moderate",
                value: moderate,
                color: "#003DFF",
                bgFrom: "#EEF2FF",
                bgTo: "#E8EDFF",
              },
              {
                label: "Optimistic",
                value: Math.round(moderate * 1.5),
                color: "#7C3AED",
                bgFrom: "#F5F3FF",
                bgTo: "#EDE9FE",
              },
            ].map((card) => (
              <div
                key={card.label}
                className="rounded-xl p-5 text-center"
                style={{
                  background: `linear-gradient(135deg, ${card.bgFrom}, ${card.bgTo})`,
                  border: "1px solid #E5E7EB",
                }}
              >
                <p
                  className="uppercase tracking-wide font-semibold mb-2"
                  style={{ fontSize: 11, color: "#6B7280", letterSpacing: "0.06em" }}
                >
                  {card.label}
                </p>
                <p className="text-2xl font-bold" style={{ color: card.color }}>
                  {formatCurrency(card.value)}
                </p>
                <p className="text-xs mt-1" style={{ color: "#6B7280" }}>
                  annual revenue impact
                </p>
              </div>
            ))}
          </div>
        </>
      ) : (
        <EmptyState message="Run the business case module to see ROI projections." />
      )}
    </Section>
  );
}

// ---------------------------------------------------------------------------
// 4.3 Customer Proof section
// ---------------------------------------------------------------------------

function CustomerProofSection({
  results,
}: {
  results: Record<string, ModuleResult>;
}) {
  const bcOutput = getOutput(results, "synth-business-case") as
    | Record<string, unknown>
    | undefined;
  const partnerOutput = getOutput(results, "intel-partner") as
    | Record<string, unknown>
    | undefined;
  const industryOutput = getOutput(results, "intel-industry") as
    | Record<string, unknown>
    | undefined;

  // Collect case studies from multiple sources
  type CaseStudyShape = {
    company: string;
    vertical?: string;
    result: string;
    product?: string;
    why?: string;
    url?: string;
  };

  const caseStudies: CaseStudyShape[] = [];

  // From partner intelligence
  const partnerCases = (partnerOutput?.case_studies ?? []) as Array<{
    customer_name?: string;
    vertical?: string;
    algolia_product?: string;
    key_result?: string;
  }>;
  for (const cs of partnerCases) {
    caseStudies.push({
      company: cs.customer_name ?? "Unknown",
      vertical: cs.vertical,
      result: cs.key_result ?? "",
      product: cs.algolia_product,
    });
  }

  // From industry intelligence
  const industryCases = (industryOutput?.case_studies ?? []) as Array<{
    customer?: string;
    vertical?: string;
    result?: string;
  }>;
  for (const cs of industryCases) {
    caseStudies.push({
      company: cs.customer ?? "Unknown",
      vertical: cs.vertical,
      result: cs.result ?? "",
    });
  }

  // From business case (if embedded)
  const bcCases = (bcOutput?.customer_proof ?? []) as CaseStudyShape[];
  for (const cs of bcCases) {
    caseStudies.push(cs);
  }

  const companyName = usePrismStore((s) => s.currentCompanyName);

  return (
    <Section id="customer-proof">
      <SectionChrome
        eyebrow="Business Case"
        title="Customer Proof"
        subtitle={
          companyName
            ? `Matched case studies for ${companyName}'s vertical.`
            : "Real results from comparable Algolia customers."
        }
        icon={<Users className="h-4 w-4 text-[#003DFF]" />}
      />

      {caseStudies.length > 0 ? (
        <CustomerProofCard
          caseStudies={caseStudies}
          companyName={companyName ?? undefined}
        />
      ) : (
        <EmptyState message="Ask aRRIe to find customer evidence for this prospect." />
      )}
    </Section>
  );
}

// ---------------------------------------------------------------------------
// 4.4 Why Act Now section
// ---------------------------------------------------------------------------

const severityConfig: Record<
  string,
  { color: string; bg: string; border: string; label: string }
> = {
  HIGH: {
    color: "#DC2626",
    bg: "bg-red-50",
    border: "#DC2626",
    label: "High",
  },
  MEDIUM: {
    color: "#D97706",
    bg: "bg-amber-50",
    border: "#D97706",
    label: "Medium",
  },
  LOW: {
    color: "#6B7280",
    bg: "bg-gray-50",
    border: "#9CA3AF",
    label: "Low",
  },
};

interface MergedSignal {
  title: string;
  detail: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  source: string;
}

function WhyActNowSection({
  results,
}: {
  results: Record<string, ModuleResult>;
}) {
  const bcOutput = getOutput(results, "synth-business-case") as
    | Partial<BusinessCaseResult>
    | undefined;
  const newsOutput = getOutput(results, "intel-news") as
    | Partial<NewsResult>
    | undefined;

  // Merge timing signals from business case and urgency signals from news
  const signals: MergedSignal[] = [];

  const timingSignals = bcOutput?.timing_signals ?? [];
  for (const ts of timingSignals) {
    signals.push({
      title: ts.signal,
      detail: "",
      severity: ts.urgency,
      source: "Business Case",
    });
  }

  const urgencySignals = newsOutput?.urgency_signals ?? [];
  for (const us of urgencySignals) {
    signals.push({
      title: us.title,
      detail: us.detail,
      severity: us.severity,
      source: "News Intelligence",
    });
  }

  // Sort: HIGH first, then MEDIUM, then LOW
  const severityOrder: Record<string, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };
  signals.sort(
    (a, b) => (severityOrder[a.severity] ?? 2) - (severityOrder[b.severity] ?? 2)
  );

  return (
    <Section id="why-act-now">
      <SectionChrome
        eyebrow="Business Case"
        title="Why Act Now"
        subtitle="Time-sensitive signals that create urgency for this deal."
        icon={<Zap className="h-4 w-4 text-[#003DFF]" />}
      />

      {signals.length > 0 ? (
        <div className="space-y-3">
          {signals.map((signal, i) => {
            const cfg = severityConfig[signal.severity] ?? severityConfig.LOW;
            return (
              <div
                key={i}
                className={cn("rounded-lg p-4", cfg.bg)}
                style={{ borderLeft: `4px solid ${cfg.border}` }}
              >
                <div className="flex items-start gap-3">
                  <Badge
                    variant="outline"
                    className="shrink-0 mt-0.5 text-[10px] font-semibold"
                    style={{
                      color: cfg.color,
                      borderColor: cfg.color,
                      background: "white",
                    }}
                  >
                    {cfg.label}
                  </Badge>
                  <div className="min-w-0 flex-1">
                    <p
                      className="font-semibold"
                      style={{ fontSize: 15, color: "#23263B", lineHeight: 1.4 }}
                    >
                      {signal.title}
                    </p>
                    {signal.detail && (
                      <p className="mt-1" style={{ fontSize: 13, color: "#6B7280", lineHeight: 1.5 }}>
                        {signal.detail}
                      </p>
                    )}
                    <span
                      className="inline-block mt-2"
                      style={{ fontSize: 11, color: "#9CA3AF" }}
                    >
                      Source: {signal.source}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState message="Run the business case and news modules to see urgency signals." />
      )}
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Main tab export
// ---------------------------------------------------------------------------

export function BusinessCaseTab({ results }: TabProps) {
  return (
    <div className="space-y-2" style={{ background: "#F8F9FB" }}>
      <SaidVsFoundSection results={results} />
      <ROISection results={results} />
      <CustomerProofSection results={results} />
      <WhyActNowSection results={results} />
    </div>
  );
}
