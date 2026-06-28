"use client";

import { useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { usePrismStore } from "@/lib/store";
import { ArrowRight, Download } from "lucide-react";
import type { ModuleResult } from "@/lib/types";
import type {
  CompanyProfileResult,
  TechStackResult,
  AuditReportResult,
  NewsResult,
  HiringResult,
  InvestorResult,
  SalesPlaysResult,
} from "@/lib/types";

/* ─── Types ─────────────────────────────────────────────────────────── */

interface TabProps {
  results: Record<string, ModuleResult>;
}

/* ─── Helpers ────────────────────────────────────────────────────────── */

function getOutput<T>(
  results: Record<string, ModuleResult>,
  moduleName: string,
): Partial<T> | undefined {
  return results[moduleName]?.output as Partial<T> | undefined;
}

function formatRevenue(value: number): string {
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

function formatEmployees(n: number): string {
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return n.toLocaleString();
}

function scoreColor(s: number) {
  if (s > 7) return "#059669";
  if (s >= 4) return "#D97706";
  return "#DC2626";
}
function scoreBg(s: number) {
  if (s > 7) return "rgba(5,150,105,0.08)";
  if (s >= 4) return "rgba(217,119,6,0.08)";
  return "rgba(220,38,38,0.08)";
}
function scoreLabel(s: number) {
  if (s > 7) return "Strong";
  if (s >= 4) return "Moderate";
  return "Critical";
}

const signalIcon: Record<string, string> = {
  leadership_change: "👤",
  product_launch: "🚀",
  partnership: "🤝",
  financial: "💰",
  acquisition: "🏢",
  technology: "🔧",
  hiring: "📋",
  investor: "📈",
  other: "📌",
};

/* ─── Glassmorphic tile ──────────────────────────────────────────────── */

function OvTile({
  children,
  className,
  spotColor = "0,61,255",
}: {
  children: React.ReactNode;
  className?: string;
  spotColor?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  function onMove(e: React.MouseEvent<HTMLDivElement>) {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const x = e.clientX - r.left;
    const y = e.clientY - r.top;
    // Spotlight follows mouse
    el.style.setProperty("--ov-x", `${x}px`);
    el.style.setProperty("--ov-y", `${y}px`);
    // 3D tilt — exact DSW formula: ±6deg based on distance from center
    const cx = r.width / 2;
    const cy = r.height / 2;
    const rx = ((y - cy) / cy) * -4;
    const ry = ((x - cx) / cx) * 4;
    el.style.transform = `perspective(1200px) rotateX(${rx}deg) rotateY(${ry}deg) translateZ(10px)`;
    el.style.boxShadow = "0 24px 64px rgba(0,0,0,0.14), 0 6px 20px rgba(0,0,0,0.09), inset 0 1px 0 rgba(255,255,255,0.95)";
  }

  function onLeave() {
    const el = ref.current;
    if (!el) return;
    el.style.transform = "";
    el.style.boxShadow = "";
  }

  return (
    <>
      <style jsx>{`
        .ov-tile {
          position: relative;
          background: rgba(255, 255, 255, 0.72);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.85);
          border-radius: 20px;
          padding: 26px 28px;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          box-shadow:
            0 2px 4px rgba(0, 0, 0, 0.03),
            0 6px 16px rgba(0, 0, 0, 0.06),
            0 16px 36px rgba(0, 0, 0, 0.07),
            inset 0 1px 0 rgba(255, 255, 255, 0.95);
          will-change: transform;
        }
        /* Spotlight radial gradient follows mouse */
        .ov-tile::before {
          content: "";
          position: absolute;
          inset: 0;
          border-radius: inherit;
          background: radial-gradient(
            600px circle at var(--ov-x, 50%) var(--ov-y, 50%),
            rgba(${spotColor}, 0.07) 0%,
            transparent 65%
          );
          opacity: 0;
          transition: opacity 0.3s ease;
          pointer-events: none;
          z-index: 0;
        }
        .ov-tile:hover::before { opacity: 1; }
        /* Top shimmer on hover */
        .ov-tile::after {
          content: "";
          position: absolute;
          top: 0;
          left: 10%;
          right: 10%;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,0.9), transparent);
          opacity: 0;
          transition: opacity 0.3s ease;
          pointer-events: none;
          z-index: 0;
        }
        .ov-tile:hover::after { opacity: 1; }
      `}</style>
      <div
        ref={ref}
        className={cn("ov-tile", className)}
        onMouseMove={onMove}
        onMouseLeave={onLeave}
        style={{ "--ov-x": "50%", "--ov-y": "50%" } as React.CSSProperties}
      >
        <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", height: "100%" }}>
          {children}
        </div>
      </div>
    </>
  );
}

/* ─── Tile footer nav ────────────────────────────────────────────────── */

function TileNav({ label, target }: { label: string; target: string }) {
  const navigateTo = usePrismStore((s) => s.navigateTo);
  return (
    <div
      style={{
        marginTop: "auto",
        paddingTop: "14px",
        borderTop: "1px solid rgba(0,0,0,0.07)",
      }}
    >
      <button
        type="button"
        onClick={() => navigateTo(target)}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "4px",
          fontSize: "11px",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          color: "#94A3B8",
          background: "none",
          border: "none",
          cursor: "pointer",
          padding: 0,
          transition: "color 0.2s",
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "#003DFF"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "#94A3B8"; }}
      >
        {label}
        <ArrowRight style={{ width: 12, height: 12 }} />
      </button>
    </div>
  );
}

/* ─── Eyebrow label ──────────────────────────────────────────────────── */

function OvQ({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontSize: "10px",
        fontWeight: 800,
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        color: "#6B7280",
        marginBottom: "14px",
      }}
    >
      {children}
    </div>
  );
}

/* ─── Icon row ───────────────────────────────────────────────────────── */

function IconRow({
  icon,
  label,
  value,
  pill,
  pillColor,
}: {
  icon: string;
  label: string;
  value: string;
  pill?: string;
  pillColor?: string;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 8,
          background: "rgba(0,61,255,0.08)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 13,
          flexShrink: 0,
        }}
      >
        {icon}
      </div>
      <span style={{ fontSize: 12, color: "#6B7280", fontWeight: 500, minWidth: 52 }}>
        {label}
      </span>
      <span style={{ fontSize: 13, color: "#23263B", fontWeight: 600 }}>{value}</span>
      {pill && (
        <span
          style={{
            fontSize: 9,
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: pillColor ?? "#DC2626",
            background: pillColor ? `${pillColor}18` : "rgba(220,38,38,0.10)",
            padding: "2px 7px",
            borderRadius: 3,
          }}
        >
          {pill}
        </span>
      )}
    </div>
  );
}

/* ─── Empty state ────────────────────────────────────────────────────── */

function EmptyState({ eyebrow }: { eyebrow: string }) {
  return (
    <>
      <OvQ>{eyebrow}</OvQ>
      <p style={{ fontSize: 13, color: "#9CA3AF", marginTop: 4 }}>
        Run an audit to populate
      </p>
    </>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   TILE 1 — WHO IS THIS?   (col-span-3)
   ═══════════════════════════════════════════════════════════════════════ */

function WhoTile({ results }: TabProps) {
  const company = getOutput<CompanyProfileResult>(results, "intel-company");
  const tech = getOutput<TechStackResult>(results, "intel-techstack");

  if (!company && !tech) {
    return (
      <OvTile className="col-span-6 md:col-span-3">
        <EmptyState eyebrow="Who is this?" />
      </OvTile>
    );
  }

  const name = company?.common_name || company?.legal_name || "Unknown";
  const revenue = company?.revenue_estimate ?? null;
  const hq = company?.headquarters ?? null;
  const employees = company?.employee_count ?? null;
  const founded = company?.year_founded ?? null;
  const isPublic = company?.is_public ?? false;
  const ticker = company?.ticker ?? null;
  const platform = tech?.ecommerce_platform ?? company?.sub_vertical ?? null;
  const searchVendor = tech?.search_vendor ?? null;
  const isTarget =
    searchVendor != null &&
    searchVendor.status !== "UNDETECTED" &&
    !searchVendor.name.toLowerCase().includes("algolia");

  return (
    <OvTile className="col-span-6 md:col-span-3" spotColor="71,85,105">
      <OvQ>Who is this?</OvQ>

      <div
        style={{
          fontSize: 22,
          fontWeight: 800,
          color: "#23263B",
          letterSpacing: "-0.5px",
          marginBottom: 18,
          lineHeight: 1.2,
        }}
      >
        {name}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 9, marginBottom: 4 }}>
        {revenue != null && (
          <IconRow icon="💰" label="Revenue" value={formatRevenue(revenue)} />
        )}
        {hq && (
          <IconRow icon="📍" label="HQ" value={hq} />
        )}
        {employees != null && (
          <IconRow icon="👥" label="Employees" value={formatEmployees(employees)} />
        )}
        {founded != null && (
          <IconRow icon="📅" label="Founded" value={String(founded)} />
        )}
        {(isPublic || ticker) && (
          <IconRow
            icon="🏢"
            label="Status"
            value={isPublic ? "Public" : "Private"}
            pill={ticker ?? undefined}
            pillColor="#003DFF"
          />
        )}
        {platform && (
          <IconRow icon="🛒" label="Platform" value={platform} />
        )}
        {searchVendor && searchVendor.status !== "UNDETECTED" && (
          <IconRow
            icon={isTarget ? "🎯" : "✅"}
            label="Search"
            value={searchVendor.name}
            pill={isTarget ? "Target" : "Algolia"}
            pillColor={isTarget ? "#DC2626" : "#059669"}
          />
        )}
      </div>

      <TileNav label="Research" target="research" />
    </OvTile>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   TILE 2 — HOW BAD IS THEIR SEARCH?   (col-span-3)
   ═══════════════════════════════════════════════════════════════════════ */

function SearchScoreTile({ results }: TabProps) {
  const report = getOutput<AuditReportResult>(results, "audit-report");

  if (!report) {
    return (
      <OvTile className="col-span-6 md:col-span-3" spotColor="220,38,38">
        <EmptyState eyebrow="How bad is their search?" />
      </OvTile>
    );
  }

  const score = report.overall_score ?? 0;
  const color = scoreColor(score);
  const bg = scoreBg(score);
  const label = scoreLabel(score);
  const criticals = (report.dimension_scores ?? [])
    .filter((d) => d.severity === "critical")
    .slice(0, 3);

  const glowColor =
    score > 7 ? "green" : score >= 4 ? "amber" : "red";
  const glowShadow: Record<string, string> = {
    red:   "0 4px 12px rgba(220,38,38,0.20), 0 10px 28px rgba(220,38,38,0.14), 0 1px 3px rgba(0,0,0,0.08)",
    amber: "0 4px 12px rgba(217,119,6,0.20),  0 10px 28px rgba(217,119,6,0.14),  0 1px 3px rgba(0,0,0,0.08)",
    green: "0 4px 12px rgba(5,150,105,0.20),  0 10px 28px rgba(5,150,105,0.14),  0 1px 3px rgba(0,0,0,0.08)",
  };
  const glowShadowHover: Record<string, string> = {
    red:   "0 8px 20px rgba(220,38,38,0.30), 0 20px 48px rgba(220,38,38,0.22), 0 2px 6px rgba(0,0,0,0.10)",
    amber: "0 8px 20px rgba(217,119,6,0.30),  0 20px 48px rgba(217,119,6,0.22),  0 2px 6px rgba(0,0,0,0.10)",
    green: "0 8px 20px rgba(5,150,105,0.30),  0 20px 48px rgba(5,150,105,0.22),  0 2px 6px rgba(0,0,0,0.10)",
  };
  const conicColors: Record<string, string> = {
    red:   "conic-gradient(transparent 0deg, #DC2626 60deg, transparent 120deg)",
    amber: "conic-gradient(transparent 0deg, #D97706 60deg, transparent 120deg)",
    green: "conic-gradient(transparent 0deg, #059669 60deg, transparent 120deg)",
  };

  return (
    <>
      <style jsx>{`
        @keyframes glow-spin { to { transform: rotate(360deg); } }

        .glow-wrap {
          position: relative;
          grid-column: span 6;
          border-radius: 20px;
          padding: 1.5px;
          overflow: hidden;
          box-shadow: ${glowShadow[glowColor]};
          transition: transform 0.25s cubic-bezier(0.4,0,0.2,1), box-shadow 0.25s cubic-bezier(0.4,0,0.2,1);
        }
        @media (min-width: 768px) {
          .glow-wrap { grid-column: span 3; }
        }
        .glow-wrap:hover {
          transform: translateY(-6px) scale(1.01);
          box-shadow: ${glowShadowHover[glowColor]};
        }
        .glow-wrap::before {
          content: '';
          position: absolute;
          inset: -120%;
          background: ${conicColors[glowColor]};
          animation: glow-spin 3s linear infinite;
          animation-play-state: paused;
          border-radius: inherit;
        }
        .glow-wrap:hover::before { animation-play-state: running; }

        .glow-inner {
          background: rgba(255,255,255,0.95);
          border-radius: 19px;
          padding: 26px 28px;
          display: flex;
          flex-direction: column;
          height: 100%;
          position: relative;
          z-index: 1;
        }
      `}</style>

      <div className="glow-wrap">
        <div className="glow-inner">
          <OvQ>How bad is their search?</OvQ>

          {/* Score hero — 72px matching DSW */}
          <div style={{ display: "flex", alignItems: "flex-end", gap: 14, marginBottom: 18 }}>
            <div style={{ fontSize: 72, fontWeight: 900, color, lineHeight: 1, letterSpacing: "-3px" }}>
              {score.toFixed(1)}
            </div>
            <div style={{ paddingBottom: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#6B7280", marginBottom: 6 }}>
                out of 10
              </div>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  background: bg,
                  color,
                  padding: "3px 10px",
                  borderRadius: 4,
                  fontSize: 12,
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                {label}
              </div>
            </div>
          </div>

          {/* Critical gaps */}
          {criticals.length > 0 && (
            <div style={{ borderTop: "1px solid rgba(0,0,0,0.06)", paddingTop: 12, marginBottom: 4 }}>
              <div
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "#DC2626",
                  marginBottom: 8,
                }}
              >
                Critical Gaps
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                {criticals.map((g, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                    <span
                      style={{
                        marginTop: 5,
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        background: "#DC2626",
                        flexShrink: 0,
                        display: "inline-block",
                      }}
                    />
                    <span style={{ fontSize: 12, color: "#23263B", lineHeight: 1.4 }}>
                      <strong>{g.dimension}:</strong> {g.evidence}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <TileNav label="Search Audit" target="search-audit" />
        </div>
      </div>
    </>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   TILE 3 — WHY ACT NOW?   (col-span-4)
   ═══════════════════════════════════════════════════════════════════════ */

interface Signal {
  icon: string;
  type: string;
  headline: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
}

const severityColor: Record<Signal["severity"], string> = {
  HIGH: "#DC2626",
  MEDIUM: "#D97706",
  LOW: "#059669",
};

function WhyActNowTile({ results }: TabProps) {
  const news = getOutput<NewsResult>(results, "intel-news");
  const hiring = getOutput<HiringResult>(results, "intel-hiring");
  const investor = getOutput<InvestorResult>(results, "intel-investor");

  if (!news && !hiring && !investor) {
    return (
      <OvTile className="col-span-6 md:col-span-4" spotColor="220,100,30">
        <EmptyState eyebrow="Why act now?" />
      </OvTile>
    );
  }

  const signals: Signal[] = [];

  for (const sig of news?.urgency_signals ?? []) {
    signals.push({
      icon: signalIcon[sig.signal_type] ?? "📌",
      type: sig.signal_type.replace(/_/g, " "),
      headline: sig.title,
      severity: sig.severity,
    });
  }
  for (const risk of (investor?.risk_factors ?? []).slice(0, 2)) {
    signals.push({ icon: "📈", type: "investor risk", headline: risk, severity: "MEDIUM" });
  }
  if (hiring?.build_vs_buy_signal === "build") {
    signals.push({
      icon: "🔨",
      type: "hiring signal",
      headline: `${hiring.total_roles ?? 0} open roles — build signal detected`,
      severity: "HIGH",
    });
  }

  const top = signals.slice(0, 4);

  return (
    <OvTile className="col-span-6 md:col-span-4" spotColor="220,100,30">
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 14 }}>
        <OvQ>Why act now?</OvQ>
        <span
          style={{
            fontSize: 10,
            fontWeight: 600,
            color: "#6B7280",
            marginBottom: 14,
          }}
        >
          {signals.length} active signal{signals.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
        {top.map((sig, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 12,
              borderRadius: 10,
              border: "1px solid #E5E7EB",
              padding: "10px 12px",
              background: "rgba(255,255,255,0.6)",
            }}
          >
            <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>{sig.icon}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
                <span
                  style={{
                    fontSize: 9,
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    color: "#6B7280",
                  }}
                >
                  {sig.type}
                </span>
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: severityColor[sig.severity],
                    flexShrink: 0,
                    display: "inline-block",
                  }}
                />
              </div>
              <p
                style={{
                  fontSize: 12,
                  color: "#23263B",
                  lineHeight: 1.4,
                  margin: 0,
                  overflow: "hidden",
                  display: "-webkit-box",
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: "vertical" as const,
                }}
              >
                {sig.headline}
              </p>
            </div>
          </div>
        ))}
      </div>

      <TileNav label="See all signals" target="news-signals" />
    </OvTile>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   TILE 4 — WHAT DO I DO NEXT?   (col-span-2)
   ═══════════════════════════════════════════════════════════════════════ */

function NextActionTile({ results }: TabProps) {
  const sales = getOutput<SalesPlaysResult>(results, "synth-sales-plays");

  if (!sales) {
    return (
      <OvTile className="col-span-6 md:col-span-2" spotColor="0,61,255">
        <EmptyState eyebrow="What do I do next?" />
      </OvTile>
    );
  }

  const meddpicc = sales.meddpicc ?? [];
  const talkTracks = sales.talk_tracks ?? [];
  const isUrgent =
    meddpicc.some((m) => m.evidence?.toLowerCase().includes("urgent")) ||
    talkTracks.length >= 3;

  const topAction =
    meddpicc[0]?.approach ?? talkTracks[0]?.topic ?? "Review the full playbook";
  const preview =
    talkTracks[0]?.track ?? sales.objection_handlers?.[0]?.counter ?? "";

  return (
    <OvTile className="col-span-6 md:col-span-2" spotColor="0,61,255">
      <OvQ>What do I do next?</OvQ>

      {/* Urgency indicator */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: isUrgent ? "#DC2626" : "#D97706",
            boxShadow: `0 0 0 3px ${isUrgent ? "rgba(220,38,38,0.2)" : "rgba(217,119,6,0.2)"}`,
            flexShrink: 0,
          }}
        />
        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            color: isUrgent ? "#DC2626" : "#D97706",
          }}
        >
          {isUrgent ? "Urgent" : "Medium Priority"}
        </span>
      </div>

      {/* Recommended action */}
      <div style={{ marginBottom: 14 }}>
        <div
          style={{
            fontSize: 10,
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "#6B7280",
            marginBottom: 6,
          }}
        >
          Recommended action
        </div>
        <p style={{ fontSize: 14, fontWeight: 600, color: "#23263B", lineHeight: 1.4, margin: 0 }}>
          {topAction}
        </p>
      </div>

      {/* Talk track preview */}
      {preview && (
        <div
          style={{
            borderRadius: 10,
            background: "#F5F5F7",
            padding: "10px 12px",
            marginBottom: 4,
            flex: 1,
          }}
        >
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "#6B7280",
              marginBottom: 6,
            }}
          >
            Talk track preview
          </div>
          <p
            style={{
              fontSize: 12,
              color: "#23263B",
              lineHeight: 1.5,
              margin: 0,
              overflow: "hidden",
              display: "-webkit-box",
              WebkitLineClamp: 4,
              WebkitBoxOrient: "vertical" as const,
            }}
          >
            {preview}
          </p>
        </div>
      )}

      <TileNav label="Sales Actions" target="sales-actions" />
    </OvTile>
  );
}

/* ─── Download buttons ───────────────────────────────────────────────── */

function DownloadButtons() {
  const [toast, setToast] = useState<string | null>(null);
  const show = useCallback((msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  }, []);

  return (
    <div style={{ position: "relative", marginTop: 28, display: "flex", justifyContent: "center", gap: 12 }}>
      <button
        type="button"
        onClick={() => show("Pre-Call Brief download coming soon")}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          borderRadius: 12,
          border: "1px solid #E5E7EB",
          background: "white",
          padding: "10px 20px",
          fontSize: 13,
          fontWeight: 600,
          color: "#23263B",
          cursor: "pointer",
          transition: "border-color 0.2s, color 0.2s",
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.borderColor = "#003DFF";
          (e.currentTarget as HTMLButtonElement).style.color = "#003DFF";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.borderColor = "#E5E7EB";
          (e.currentTarget as HTMLButtonElement).style.color = "#23263B";
        }}
      >
        <Download style={{ width: 15, height: 15 }} />
        Download Pre-Call Brief
      </button>
      <button
        type="button"
        onClick={() => show("Full Report download coming soon")}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          borderRadius: 12,
          border: "1px solid #003DFF",
          background: "#003DFF",
          padding: "10px 20px",
          fontSize: 13,
          fontWeight: 600,
          color: "white",
          cursor: "pointer",
          transition: "background 0.2s",
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "#002ACC"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "#003DFF"; }}
      >
        <Download style={{ width: 15, height: 15 }} />
        Download Full Report
      </button>

      {toast && (
        <div
          style={{
            position: "absolute",
            bottom: -44,
            left: "50%",
            transform: "translateX(-50%)",
            background: "#23263B",
            color: "white",
            borderRadius: 8,
            padding: "8px 16px",
            fontSize: 12,
            fontWeight: 500,
            whiteSpace: "nowrap",
            zIndex: 50,
          }}
        >
          {toast}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   OVERVIEW TAB — main export
   6-column DSW bento: [WHO 3col][SCORE 3col] / [SIGNALS 4col][NEXT 2col]
   ═══════════════════════════════════════════════════════════════════════ */

export function OverviewTab({ results }: TabProps) {
  return (
    <div style={{ padding: "36px 32px 48px" }}>
      {/* Section eyebrow */}
      <div
        style={{
          fontSize: 11,
          fontWeight: 800,
          textTransform: "uppercase",
          letterSpacing: "0.12em",
          color: "#003DFF",
          marginBottom: 6,
        }}
      >
        Dashboard
      </div>
      <h2
        style={{
          fontSize: 28,
          fontWeight: 600,
          color: "#23263B",
          marginBottom: 28,
          lineHeight: 1.2,
        }}
      >
        Intelligence Overview
      </h2>

      {/* 6-col bento grid — generous gap for breathing room */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(6, 1fr)",
          gap: 20,
        }}
      >
        <WhoTile results={results} />
        <SearchScoreTile results={results} />
        <WhyActNowTile results={results} />
        <NextActionTile results={results} />
      </div>

      <DownloadButtons />
    </div>
  );
}
