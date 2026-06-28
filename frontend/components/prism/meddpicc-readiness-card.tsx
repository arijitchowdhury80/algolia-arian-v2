/**
 * DiscoveryCallPrepCard — surfaces what PRISM knows so the AE
 * walks into the call armed, not blind.
 *
 * Three sections, matching what PRISM can actually contribute:
 *   1. Pain Points — top search gaps from audit evidence
 *   2. ROI Ammunition — business case levers with numbers
 *   3. Competitive Landscape — who they're fighting + tech
 *
 * Plus: suggested discovery questions for what PRISM can't see
 * (budget owner, buying process, timeline).
 *
 * This is NOT a MEDDPICC scorecard. PRISM is a prospect enrichment
 * platform — it feeds into the AE's sales process, it doesn't run it.
 */
"use client";

import { font, color, radius } from "@/lib/tokens";
import type { ModuleResult } from "@/lib/types";

interface DiscoveryCallPrepCardProps {
  results: Record<string, ModuleResult>;
}

// ── Helpers ──────────────────────────────────────────────────────────────

interface PrepSection {
  icon: string;
  title: string;
  signal: "ready" | "partial" | "missing";
  content: string[];
}

function buildSections(results: Record<string, ModuleResult>): PrepSection[] {
  const audit   = results["audit-browser"]?.output as Record<string, unknown> | undefined;
  const bizCase = results["synth-business-case"]?.output as Record<string, unknown> | undefined;
  const comps   = results["intel-competitors"]?.output as Record<string, unknown> | undefined;
  const company = results["intel-company"]?.output as Record<string, unknown> | undefined;

  const competitors = (company?.competitors as Array<{ company_name: string; domain: string }>) ?? [];

  // 1. Pain Points
  const dimensionScores = (audit?.dimension_scores as Array<{ dimension: string; score: number; evidence: string }>) ?? [];
  const topGaps = dimensionScores
    .filter((d) => d.score <= 4)
    .sort((a, b) => a.score - b.score)
    .slice(0, 3);

  const painSection: PrepSection = {
    icon: "🎯",
    title: "Pain Points — Lead With These",
    signal: topGaps.length > 0 ? "ready" : audit ? "partial" : "missing",
    content: topGaps.length > 0
      ? topGaps.map((g) => `${g.dimension}: ${g.score}/10 — ${g.evidence}`)
      : audit
        ? ["Audit complete but no critical gaps found — search is decent. Focus on incremental gains."]
        : ["No audit data yet — run browser audit first to identify search gaps."],
  };

  // 2. ROI Ammunition
  const roiLevers = (bizCase?.roi_levers as Array<{ lever: string; conservative_value: number; unit: string }>) ?? [];

  const roiSection: PrepSection = {
    icon: "💰",
    title: "ROI Ammunition — Numbers to Quote",
    signal: roiLevers.length > 0 ? "ready" : audit ? "partial" : "missing",
    content: roiLevers.length > 0
      ? roiLevers.map((l) => `${l.lever}: +${l.conservative_value}${l.unit} (conservative)`)
      : audit
        ? ["Audit data available — run business case module to generate ROI levers."]
        : ["No ROI data — need audit + business case modules to build the model."],
  };

  // 3. Competitive Landscape
  const compSummary = (comps as Record<string, unknown>)?.summary as string | undefined;

  const compSection: PrepSection = {
    icon: "⚔️",
    title: "Competitive Landscape",
    signal: comps ? "ready" : competitors.length > 0 ? "partial" : "missing",
    content: comps
      ? [
          compSummary ?? "Full competitive analysis available.",
          ...competitors.slice(0, 3).map((c) => `${c.company_name} (${c.domain})`),
        ]
      : competitors.length > 0
        ? [`${competitors.length} competitors identified — detailed analysis not yet run.`]
        : ["No competitor data — run intel-competitors module."],
  };

  return [painSection, roiSection, compSection];
}

const DISCOVERY_QUESTIONS = [
  { area: "Budget", question: "Who owns the budget for search / digital experience? Can they approve independently?" },
  { area: "Process", question: "Walk me through how you've purchased similar tools. How many stages from eval to contract?" },
  { area: "Timeline", question: "Is there a deadline driving this? A replatform, a board mandate, a contract renewal?" },
  { area: "Criteria", question: "What are your top 3 criteria when evaluating a search vendor?" },
];

const SIGNAL_STYLE = {
  ready:   { dot: "#22C55E", bg: "rgba(34,197,94,0.06)",  label: "Ready" },
  partial: { dot: "#F59E0B", bg: "rgba(245,158,11,0.06)", label: "Partial" },
  missing: { dot: "#DC2626", bg: "rgba(220,38,38,0.04)",  label: "Missing" },
} as const;

// ── Component ────────────────────────────────────────────────────────────

export function DiscoveryCallPrepCard({ results }: DiscoveryCallPrepCardProps) {
  const sections = buildSections(results);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      {/* Header */}
      <div>
        <div style={{ fontSize: font.h5, fontWeight: font.weight.semibold, color: color.navy }}>
          Discovery Call Prep
        </div>
        <div style={{ fontSize: font.small, color: color.muted, marginTop: 4 }}>
          What PRISM knows — walk in armed, not blind
        </div>
      </div>

      {/* Three sections */}
      {sections.map((section) => {
        const s = SIGNAL_STYLE[section.signal];
        return (
          <div
            key={section.title}
            style={{
              background: s.bg,
              borderRadius: radius.lg,
              border: `1px solid ${color.divider}`,
              padding: "20px 24px",
            }}
          >
            {/* Section header */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
              <span style={{ fontSize: "16px" }}>{section.icon}</span>
              <div style={{ fontSize: font.label, fontWeight: font.weight.semibold, color: color.navy, flex: 1 }}>
                {section.title}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: s.dot }} />
                <span style={{ fontSize: font.caption, fontWeight: font.weight.semibold, color: s.dot, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  {s.label}
                </span>
              </div>
            </div>

            {/* Content bullets */}
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {section.content.map((line, i) => (
                <div
                  key={i}
                  style={{
                    fontSize: font.small,
                    color: color.text,
                    lineHeight: 1.6,
                    paddingLeft: 12,
                    borderLeft: `2px solid ${color.divider}`,
                  }}
                >
                  {line}
                </div>
              ))}
            </div>
          </div>
        );
      })}

      {/* Discovery questions — what PRISM can't see */}
      <div
        style={{
          borderRadius: radius.lg,
          border: `1px solid ${color.blue15}`,
          background: color.blue06,
          padding: "20px 24px",
        }}
      >
        <div style={{ fontSize: font.label, fontWeight: font.weight.semibold, color: color.navy, marginBottom: 14 }}>
          Questions for Discovery — What PRISM Can't See
        </div>
        <div style={{ fontSize: font.small, color: color.muted, marginBottom: 16, lineHeight: 1.5 }}>
          These require direct conversation. PRISM surfaces public intelligence; the AE uncovers the rest.
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {DISCOVERY_QUESTIONS.map((q) => (
            <div key={q.area} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
              <span
                style={{
                  fontSize: font.caption,
                  fontWeight: font.weight.semibold,
                  color: color.blue,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  minWidth: 64,
                  paddingTop: 2,
                }}
              >
                {q.area}
              </span>
              <span style={{ fontSize: font.small, color: color.text, lineHeight: 1.5, fontStyle: "italic" }}>
                "{q.question}"
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
