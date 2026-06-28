"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { usePrismStore } from "@/lib/store";
import { CompetitorMatrixCard } from "@/components/prism/competitor-matrix-card";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronDown, Crown, Swords, Shield, Target } from "lucide-react";
import type {
  ModuleResult,
  CompetitorMatrixResult,
  CompetitorScenario,
} from "@/lib/types";

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
// Scenario badge styling
// ---------------------------------------------------------------------------

const scenarioBadgeConfig: Record<
  string,
  { label: string; color: string; bg: string; borderColor: string; icon: React.ReactNode }
> = {
  GOLDEN: {
    label: "Golden Angle",
    color: "#92400E",
    bg: "#FEF3C7",
    borderColor: "#F59E0B",
    icon: <Crown className="h-3 w-3" />,
  },
  OFFENSIVE: {
    label: "Offensive",
    color: "#1D4ED8",
    bg: "#DBEAFE",
    borderColor: "#3B82F6",
    icon: <Target className="h-3 w-3" />,
  },
  DEFENSIVE: {
    label: "Defensive",
    color: "#6B7280",
    bg: "#F3F4F6",
    borderColor: "#9CA3AF",
    icon: <Shield className="h-3 w-3" />,
  },
  DISPLACEMENT: {
    label: "Displacement",
    color: "#991B1B",
    bg: "#FEE2E2",
    borderColor: "#EF4444",
    icon: <Swords className="h-3 w-3" />,
  },
};

// ---------------------------------------------------------------------------
// Comparison table dimensions config
// ---------------------------------------------------------------------------

const comparisonDimensions = [
  "search vendor",
  "search quality",
  "traffic",
  "revenue",
  "digital investment",
  "hiring",
  "sentiment",
];

function scoreToColor(score: number): { bg: string; text: string } {
  if (score >= 7) return { bg: "#F0FDF4", text: "#059669" };
  if (score >= 4) return { bg: "#FFFBEB", text: "#D97706" };
  return { bg: "#FEF2F2", text: "#DC2626" };
}

function scoreToLabel(score: number): string {
  if (score >= 7) return "Leader";
  if (score >= 4) return "Middle";
  return "Lagging";
}

// ---------------------------------------------------------------------------
// 5.1 Comparison Matrix section
// ---------------------------------------------------------------------------

function ComparisonMatrixSection({
  results,
}: {
  results: Record<string, ModuleResult>;
}) {
  const competitorsResult = results["intel-competitors"];
  const output = getOutput(results, "intel-competitors") as
    | Partial<CompetitorMatrixResult>
    | undefined;
  const competitors = output?.competitors ?? [];
  const matrix = output?.comparison_matrix ?? [];

  return (
    <Section id="comparison-matrix">
      <SectionChrome
        eyebrow="Competitive Intelligence"
        title="Comparison Matrix"
        subtitle="Head-to-head capability comparison across key dimensions."
        icon={<Swords className="h-4 w-4 text-[#003DFF]" />}
      />

      {competitorsResult && (matrix.length > 0 || competitors.length > 0) ? (
        <CompetitorMatrixCard data={competitorsResult} />
      ) : competitors.length > 0 ? (
        /* Fallback: build comparison table manually */
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
              tableLayout: "auto",
              width: "100%",
              minWidth: 700,
              borderCollapse: "collapse",
              fontSize: 13,
            }}
          >
            <thead>
              <tr style={{ background: "#23263B" }}>
                <th
                  style={{
                    padding: "10px 14px",
                    fontSize: 11,
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    color: "white",
                    textAlign: "left",
                  }}
                >
                  Dimension
                </th>
                <th
                  style={{
                    padding: "10px 14px",
                    fontSize: 11,
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    color: "white",
                    textAlign: "center",
                    background: "#1E3A8A",
                    borderBottom: "3px solid #003DFF",
                  }}
                >
                  Prospect
                </th>
                {competitors.map((c) => (
                  <th
                    key={c.domain}
                    style={{
                      padding: "10px 14px",
                      fontSize: 11,
                      fontWeight: 600,
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      color: "white",
                      textAlign: "center",
                    }}
                  >
                    {c.company_name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comparisonDimensions.map((dim, rowIdx) => {
                const matrixRow = matrix.find(
                  (m) => m.dimension.toLowerCase() === dim
                );
                const prospectScore = matrixRow?.prospect_score ?? 5;
                const pColors = scoreToColor(prospectScore);

                return (
                  <tr
                    key={dim}
                    style={{
                      background: rowIdx % 2 === 0 ? "white" : "#FAFAFA",
                      borderTop: "1px solid #E5E7EB",
                    }}
                  >
                    <td
                      style={{
                        padding: "10px 14px",
                        fontWeight: 600,
                        fontSize: 12,
                        textTransform: "capitalize",
                      }}
                    >
                      {dim}
                    </td>
                    <td
                      style={{
                        padding: "8px 6px",
                        textAlign: "center",
                        background: pColors.bg,
                        color: pColors.text,
                        fontWeight: 600,
                        fontSize: 12,
                      }}
                    >
                      {scoreToLabel(prospectScore)}
                    </td>
                    {competitors.map((c) => {
                      const compScore =
                        matrixRow?.competitor_scores?.find(
                          (cs) => cs.company_name === c.company_name
                        )?.score ?? 5;
                      const cColors = scoreToColor(compScore);
                      return (
                        <td
                          key={c.domain}
                          style={{
                            padding: "8px 6px",
                            textAlign: "center",
                            background: cColors.bg,
                            color: cColors.text,
                            fontWeight: 600,
                            fontSize: 12,
                          }}
                        >
                          {scoreToLabel(compScore)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState message="Run competitor analysis to see the comparison matrix." />
      )}
    </Section>
  );
}

// ---------------------------------------------------------------------------
// 5.2 Battle Cards section
// ---------------------------------------------------------------------------

interface CompetitorDetail {
  company_name: string;
  domain: string;
  scenario: string;
  strengths?: string[];
  weaknesses?: string[];
  advantages?: string[];
  our_play?: string;
  strategic_angle?: string;
  why_competitor?: string;
  search_stack?: string;
}

function BattleCardItem({ competitor }: { competitor: CompetitorDetail }) {
  const [isOpen, setIsOpen] = useState(false);
  const cfg =
    scenarioBadgeConfig[competitor.scenario] ?? scenarioBadgeConfig.DEFENSIVE;

  const strengths = competitor.strengths ?? [];
  const advantages = competitor.advantages ?? [];
  const hasContent =
    strengths.length > 0 ||
    advantages.length > 0 ||
    competitor.our_play ||
    competitor.strategic_angle ||
    competitor.why_competitor;

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div
        className="rounded-xl border overflow-hidden"
        style={{
          borderColor: isOpen ? cfg.borderColor : "#E5E7EB",
          background: "white",
          boxShadow: isOpen
            ? `0 2px 12px ${cfg.borderColor}20`
            : "0 1px 4px rgba(0,0,0,0.04)",
          transition: "border-color 0.2s, box-shadow 0.2s",
        }}
      >
        <CollapsibleTrigger
          className="w-full flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <Badge
              className="flex items-center gap-1 text-[10px] font-semibold"
              style={{
                color: cfg.color,
                background: cfg.bg,
                borderColor: cfg.borderColor,
                border: `1px solid ${cfg.borderColor}`,
              }}
            >
              {cfg.icon}
              {cfg.label}
            </Badge>
            <span
              className="font-semibold"
              style={{ fontSize: 15, color: "#23263B" }}
            >
              {competitor.company_name}
            </span>
            {competitor.domain && (
              <span className="text-xs" style={{ color: "#9CA3AF" }}>
                {competitor.domain}
              </span>
            )}
          </div>
          <ChevronDown
            className={cn(
              "h-4 w-4 text-gray-400 transition-transform duration-200",
              isOpen && "rotate-180"
            )}
          />
        </CollapsibleTrigger>

        <CollapsibleContent>
          {hasContent ? (
            <div
              className="px-4 pb-4 pt-0 space-y-4"
              style={{ borderTop: "1px solid #E5E7EB" }}
            >
              {competitor.why_competitor && (
                <div className="pt-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
                    Why Competitor
                  </p>
                  <p className="text-sm text-gray-700">{competitor.why_competitor}</p>
                </div>
              )}

              {competitor.search_stack && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
                    Search Stack
                  </p>
                  <p className="text-sm text-gray-700">{competitor.search_stack}</p>
                </div>
              )}

              {strengths.length > 0 && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
                    Their Strengths
                  </p>
                  <ul className="space-y-1">
                    {strengths.map((s, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 text-sm text-gray-700"
                      >
                        <span
                          className="mt-1.5 h-1.5 w-1.5 rounded-full shrink-0"
                          style={{ background: "#DC2626" }}
                        />
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {advantages.length > 0 && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
                    Our Advantages
                  </p>
                  <ul className="space-y-1">
                    {advantages.map((a, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 text-sm text-gray-700"
                      >
                        <span
                          className="mt-1.5 h-1.5 w-1.5 rounded-full shrink-0"
                          style={{ background: "#059669" }}
                        />
                        {a}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {competitor.our_play && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
                    Our Play
                  </p>
                  <p className="text-sm text-gray-700">{competitor.our_play}</p>
                </div>
              )}

              {competitor.strategic_angle && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
                    Strategic Angle
                  </p>
                  <p className="text-sm text-gray-700">
                    {competitor.strategic_angle}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div
              className="px-4 pb-4 pt-3"
              style={{ borderTop: "1px solid #E5E7EB" }}
            >
              <p className="text-sm text-gray-400">
                No detailed intelligence available for this competitor.
              </p>
            </div>
          )}
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}

function BattleCardsSection({
  results,
}: {
  results: Record<string, ModuleResult>;
}) {
  const output = getOutput(results, "intel-competitors") as
    | Record<string, unknown>
    | undefined;
  const competitors = (output?.competitors ?? []) as CompetitorDetail[];

  // Also pull competitor_tiers for extra detail
  const tiers = (output?.competitor_tiers ?? []) as Array<{
    competitor?: string;
    search_stack?: string;
    our_play?: string;
    strategic_angle?: string;
  }>;

  // Merge tier details into competitor objects
  const enrichedCompetitors: CompetitorDetail[] = competitors.map((c) => {
    const tier = tiers.find(
      (t) =>
        t.competitor?.toLowerCase() === c.company_name?.toLowerCase()
    );
    return {
      ...c,
      search_stack: c.search_stack ?? tier?.search_stack,
      our_play: c.our_play ?? tier?.our_play,
      strategic_angle: c.strategic_angle ?? tier?.strategic_angle,
    };
  });

  return (
    <Section id="battle-cards">
      <SectionChrome
        eyebrow="Competitive Intelligence"
        title="Battle Cards"
        subtitle="Expandable intelligence cards for each competitor."
        icon={<Shield className="h-4 w-4 text-[#003DFF]" />}
      />

      {enrichedCompetitors.length > 0 ? (
        <div className="space-y-3">
          {enrichedCompetitors.map((comp, i) => (
            <BattleCardItem key={comp.domain || i} competitor={comp} />
          ))}
        </div>
      ) : (
        <EmptyState message="Run competitor analysis to see battle cards." />
      )}
    </Section>
  );
}

// ---------------------------------------------------------------------------
// 5.3 Golden Angle Banner (conditional)
// ---------------------------------------------------------------------------

function GoldenAngleBanner({
  results,
}: {
  results: Record<string, ModuleResult>;
}) {
  const output = getOutput(results, "intel-competitors") as
    | Partial<CompetitorMatrixResult>
    | undefined;
  const competitors = (output?.competitors ?? []) as CompetitorScenario[];
  const goldenCompetitor = competitors.find((c) => c.scenario === "GOLDEN");

  if (!goldenCompetitor) return null;

  const navigateTo = usePrismStore((s) => s.navigateTo);

  return (
    <Section id="golden-angle">
      <div
        className="relative overflow-hidden rounded-2xl p-6 sm:p-8"
        style={{
          background:
            "linear-gradient(135deg, #F59E0B 0%, #FBBF24 30%, #FDE68A 70%, #FEF3C7 100%)",
          boxShadow:
            "0 4px 16px rgba(245, 158, 11, 0.25), inset 0 1px 0 rgba(255,255,255,0.4)",
        }}
      >
        {/* Decorative star */}
        <div
          className="absolute top-4 right-6 opacity-20"
          style={{ fontSize: 72 }}
          aria-hidden="true"
        >
          &#10022;
        </div>

        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-2">
            <Crown className="h-5 w-5" style={{ color: "#92400E" }} />
            <span
              className="font-bold uppercase tracking-wide"
              style={{
                fontSize: 14,
                color: "#92400E",
                letterSpacing: "0.08em",
              }}
            >
              Golden Angle Detected
            </span>
          </div>

          <h2
            className="font-semibold mb-2"
            style={{ fontSize: "1.75rem", color: "#78350F", lineHeight: 1.2 }}
          >
            {goldenCompetitor.company_name} uses Algolia
          </h2>

          <p
            className="max-w-2xl mb-4"
            style={{ fontSize: "0.95rem", color: "#92400E", lineHeight: 1.6 }}
          >
            {goldenCompetitor.company_name} ({goldenCompetitor.domain}) is a direct
            competitor that already uses Algolia. This is the strongest possible
            sales angle: &ldquo;Your competitor is already outperforming you with
            the exact technology we&apos;re proposing.&rdquo;
          </p>

          <button
            onClick={() => navigateTo("battle-cards")}
            className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors"
            style={{
              background: "#92400E",
              color: "white",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "#78350F";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "#92400E";
            }}
          >
            View Battle Card
            <Swords className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Main tab export
// ---------------------------------------------------------------------------

export function CompetitiveTab({ results }: TabProps) {
  return (
    <div className="space-y-2" style={{ background: "#F8F9FB" }}>
      <GoldenAngleBanner results={results} />
      <ComparisonMatrixSection results={results} />
      <BattleCardsSection results={results} />
    </div>
  );
}
