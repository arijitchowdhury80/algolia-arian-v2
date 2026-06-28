"use client";

import { useState, useRef, useCallback, useMemo } from "react";
import NumberFlow from "@number-flow/react";
import { useInView } from "react-intersection-observer";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Globe } from "lucide-react";
import type { ModuleResult, TrafficResult } from "@/lib/types";

/**
 * TrafficCard — web traffic and engagement data with glassmorphism container,
 * SVG donut chart for traffic sources, visual device-split bar, and KPI tiles.
 */

interface TrafficCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function formatVisits(n: number): string {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

/** Polar coordinate helper — angle in degrees, radius, center offset */
function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

/** Build an SVG arc path for a donut segment */
function donutSegmentPath(
  cx: number,
  cy: number,
  outerR: number,
  innerR: number,
  startAngle: number,
  endAngle: number,
): string {
  const sOuter = polarToCartesian(cx, cy, outerR, startAngle);
  const eOuter = polarToCartesian(cx, cy, outerR, endAngle);
  const sInner = polarToCartesian(cx, cy, innerR, startAngle);
  const eInner = polarToCartesian(cx, cy, innerR, endAngle);
  const largeArc = endAngle - startAngle > 180 ? 1 : 0;
  return [
    `M ${sOuter.x} ${sOuter.y}`,
    `A ${outerR} ${outerR} 0 ${largeArc} 1 ${eOuter.x} ${eOuter.y}`,
    `L ${eInner.x} ${eInner.y}`,
    `A ${innerR} ${innerR} 0 ${largeArc} 0 ${sInner.x} ${sInner.y}`,
    "Z",
  ].join(" ");
}

/* ------------------------------------------------------------------ */
/*  Constants                                                         */
/* ------------------------------------------------------------------ */

const DONUT_COLORS: Record<string, string> = {
  direct_pct: "#003DFF",
  search_pct: "#059669",
  paid_pct: "#D97706",
  social_pct: "#7C3AED",
  referral_pct: "#9CA3AF",
};

const SOURCE_LABELS: Record<string, string> = {
  direct_pct: "Direct",
  search_pct: "Organic Search",
  paid_pct: "Paid Search",
  social_pct: "Social",
  referral_pct: "Other",
};

/* ------------------------------------------------------------------ */
/*  Donut Chart                                                       */
/* ------------------------------------------------------------------ */

interface DonutSegment {
  key: string;
  label: string;
  value: number;
  color: string;
  startAngle: number;
  endAngle: number;
}

function buildSegments(sourceEntries: [string, number][]): DonutSegment[] {
  const GAP = 0.3; // degrees between segments
  let cursor = 0;
  return sourceEntries.map(([key, value]) => {
    const sweep = (value / 100) * 360 - GAP;
    const seg: DonutSegment = {
      key,
      label: SOURCE_LABELS[key] ?? key,
      value,
      color: DONUT_COLORS[key] ?? "#9CA3AF",
      startAngle: cursor,
      endAngle: cursor + Math.max(sweep, 0.5), // minimum visible sweep
    };
    cursor += (value / 100) * 360;
    return seg;
  });
}

interface DonutChartProps {
  sourceEntries: [string, number][];
  searchPct: number;
}

function DonutChart({ sourceEntries, searchPct }: DonutChartProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const segments = useMemo(() => buildSegments(sourceEntries), [sourceEntries]);

  const CX = 110;
  const CY = 110;
  const OUTER = 90;
  const INNER = 56;

  return (
    <div className="flex flex-col sm:flex-row items-center gap-6">
      {/* SVG donut */}
      <svg
        viewBox="0 0 220 220"
        width={160}
        height={160}
        className="shrink-0"
        role="img"
        aria-label="Traffic sources donut chart"
      >
        <defs>
          <filter id="donut-shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="4" floodOpacity="0.25" />
          </filter>
        </defs>
        {segments.map((seg) => {
          const isHovered = hovered === seg.key;
          return (
            <path
              key={seg.key}
              d={donutSegmentPath(CX, CY, OUTER, INNER, seg.startAngle, seg.endAngle)}
              fill={seg.color}
              style={{
                transform: isHovered ? "scale(1.12)" : "scale(1)",
                transformOrigin: `${CX}px ${CY}px`,
                filter: isHovered ? "url(#donut-shadow)" : "none",
                transition: "transform 0.15s ease, filter 0.15s ease",
                cursor: "pointer",
              }}
              onMouseEnter={() => setHovered(seg.key)}
              onMouseLeave={() => setHovered(null)}
            />
          );
        })}
        {/* Center text */}
        <text
          x={CX}
          y={CY - 6}
          textAnchor="middle"
          dominantBaseline="central"
          style={{ fontSize: 22, fontWeight: 700, fill: "#23263B" }}
        >
          {searchPct.toFixed(0)}%
        </text>
        <text
          x={CX}
          y={CY + 14}
          textAnchor="middle"
          dominantBaseline="central"
          style={{ fontSize: 10, fontWeight: 500, fill: "#6B7280" }}
        >
          via Search
        </text>
      </svg>

      {/* Legend */}
      <div className="flex flex-col gap-2">
        {segments.map((seg) => (
          <div
            key={seg.key}
            className="flex items-center gap-2 cursor-pointer"
            onMouseEnter={() => setHovered(seg.key)}
            onMouseLeave={() => setHovered(null)}
            style={{
              opacity: hovered && hovered !== seg.key ? 0.5 : 1,
              transition: "opacity 0.15s ease",
            }}
          >
            <span
              className="shrink-0 rounded-full"
              style={{ width: 10, height: 10, background: seg.color }}
            />
            <span className="text-xs text-[#23263B]">
              {seg.label}
            </span>
            <span className="text-xs font-semibold text-[#6B7280]">
              {seg.value.toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function TrafficCard({ data, isLoading, error }: TrafficCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const { ref: inViewRef, inView } = useInView({ triggerOnce: true, threshold: 0.2 });

  const setRefs = useCallback(
    (node: HTMLDivElement | null) => {
      (cardRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
      inViewRef(node);
    },
    [inViewRef],
  );

  if (isLoading) return <TrafficSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Traffic data unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = (data.output ?? {}) as Partial<TrafficResult>;
  const output = {
    monthly_visits: raw.monthly_visits ?? 0,
    bounce_rate: raw.bounce_rate ?? 0,
    pages_per_visit: (raw as Record<string, unknown>).pages_per_visit as number | undefined,
    device_split: raw.device_split ?? { desktop: 0, mobile: 0, tablet: 0 },
    traffic_sources: raw.traffic_sources ?? ({} as Record<string, number>),
    top_countries: raw.top_countries ?? [],
    competitor_traffic: raw.competitor_traffic ?? [],
  };

  const sources = output.traffic_sources ?? {};
  const sourceEntries = Object.entries(sources).filter(([, v]) => v > 0);
  const searchPct =
    (sources.search_pct ?? 0) + (sources.paid_pct ?? 0);

  const mobilePct = output.device_split?.mobile ?? 0;
  const desktopPct = output.device_split?.desktop ?? 0;
  // Normalise to 100 for the visual bar (ignore tablet for the 2-segment bar)
  const mobileNorm = mobilePct + desktopPct > 0 ? (mobilePct / (mobilePct + desktopPct)) * 100 : 50;
  const desktopNorm = 100 - mobileNorm;

  /* KPI tiles data */
  const kpis: { label: string; value: string }[] = [];
  if (output.monthly_visits > 0) {
    kpis.push({ label: "Monthly Visits", value: formatVisits(output.monthly_visits) });
  }
  if (output.bounce_rate > 0) {
    kpis.push({ label: "Bounce Rate", value: `${output.bounce_rate.toFixed(1)}%` });
  }
  if (output.pages_per_visit != null && output.pages_per_visit > 0) {
    kpis.push({ label: "Pages / Visit", value: output.pages_per_visit.toFixed(1) });
  }

  return (
    <div
      ref={setRefs}
      className="my-2"
      style={{
        background: "rgba(255,255,255,0.72)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.85)",
        borderRadius: 20,
        boxShadow:
          "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06), 0 16px 36px rgba(0,0,0,0.07), inset 0 1px 0 rgba(255,255,255,0.95)",
        padding: "26px 28px",
      }}
    >
      {/* Eyebrow */}
      <div className="flex items-center justify-between mb-5">
        <span
          style={{
            fontSize: 10,
            fontWeight: 800,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            color: "#6B7280",
          }}
        >
          Traffic &amp; Digital Presence
        </span>
        <Badge variant="outline" className="text-[10px] font-mono">
          {data.module_version}
        </Badge>
      </div>

      {/* KPI Metric Tiles */}
      {kpis.length > 0 && (
        <div
          className="grid gap-3 mb-7"
          style={{
            gridTemplateColumns: `repeat(${Math.min(kpis.length, 6)}, minmax(0, 1fr))`,
          }}
        >
          {kpis.map((kpi) => (
            <div
              key={kpi.label}
              className="group"
              style={{
                background: "white",
                border: "1px solid #E5E7EB",
                borderRadius: 8,
                padding: "14px 18px",
                transition: "transform 0.15s ease, box-shadow 0.15s ease",
                cursor: "default",
              }}
              onMouseEnter={(e) => {
                const el = e.currentTarget;
                el.style.transform = "translateY(-2px)";
                el.style.boxShadow = "0 5px 16px rgba(33,36,61,0.10)";
              }}
              onMouseLeave={(e) => {
                const el = e.currentTarget;
                el.style.transform = "translateY(0)";
                el.style.boxShadow = "none";
              }}
            >
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.07em",
                  color: "#6B7280",
                  marginBottom: 4,
                }}
              >
                {kpi.label}
              </div>
              <div style={{ fontSize: 14, fontWeight: 400, color: "#23263B" }}>
                {inView && kpi.label === "Monthly Visits" ? (
                  <NumberFlow value={output.monthly_visits} />
                ) : (
                  kpi.value
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Traffic Sources — Donut */}
      {sourceEntries.length > 0 && (
        <div className="mb-6">
          <div
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "#6B7280",
              marginBottom: 8,
            }}
          >
            Traffic Sources
          </div>
          <DonutChart sourceEntries={sourceEntries} searchPct={searchPct} />
        </div>
      )}

      {/* Device Split Bar */}
      {(mobilePct > 0 || desktopPct > 0) && (
        <div className="mb-6">
          <div
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "#6B7280",
              marginBottom: 8,
            }}
          >
            Device Split
          </div>
          <div
            style={{
              height: 32,
              borderRadius: 6,
              overflow: "hidden",
              display: "flex",
            }}
          >
            {/* Mobile segment */}
            <div
              style={{
                width: `${mobileNorm}%`,
                background: "#003DFF",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontSize: 12,
                fontWeight: 600,
                minWidth: mobileNorm > 5 ? undefined : 0,
              }}
            >
              {mobileNorm > 10 && `📱 ${mobilePct.toFixed(0)}%`}
            </div>
            {/* Desktop segment */}
            <div
              style={{
                width: `${desktopNorm}%`,
                background: "#6B7280",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontSize: 12,
                fontWeight: 600,
                minWidth: desktopNorm > 5 ? undefined : 0,
              }}
            >
              {desktopNorm > 10 && `🖥 ${desktopPct.toFixed(0)}%`}
            </div>
          </div>
          <div className="flex justify-between mt-1" style={{ fontSize: 12, color: "#6B7280" }}>
            <span>Mobile</span>
            <span>Desktop</span>
          </div>
        </div>
      )}

      {/* Top countries */}
      {(output.top_countries?.length ?? 0) > 0 && (
        <div className="mb-5">
          <div className="flex items-center gap-1.5 mb-2">
            <Globe className="h-3 w-3" style={{ color: "#6B7280" }} />
            <span
              style={{
                fontSize: 11,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "#6B7280",
              }}
            >
              Top Countries
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {output.top_countries.slice(0, 5).map((c) => (
              <Badge key={c.country} variant="secondary" className="text-[10px]">
                {c.country} {c.pct.toFixed(1)}%
              </Badge>
            ))}
          </div>
        </div>
      )}

      <Separator className="mb-4" />

      {/* Competitor comparison */}
      {(output.competitor_traffic?.length ?? 0) > 0 && (
        <div>
          <span
            className="block mb-2"
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "#6B7280",
            }}
          >
            Competitor Traffic
          </span>
          <div className="space-y-1.5">
            {output.competitor_traffic.map((ct) => (
              <div key={ct.domain} className="flex items-center justify-between py-1">
                <span className="text-xs text-[#23263B]">{ct.company_name}</span>
                <span className="text-xs font-semibold" style={{ color: "#6B7280" }}>
                  {formatVisits(ct.monthly_visits)}/mo
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Warnings */}
      {(data.warnings?.length ?? 0) > 0 && (
        <div className="mt-2 text-[10px] text-amber-600">
          {(data.warnings ?? []).map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}

      {/* Timing metadata */}
      <p className="mt-3 text-[10px]" style={{ color: "#9CA3AF" }}>
        {data.duration_ms}ms
        {data.status !== "success" && (
          <span className="ml-2 text-amber-500">({data.status})</span>
        )}
      </p>
    </div>
  );
}

function TrafficSkeleton() {
  return (
    <div
      className="my-2"
      style={{
        background: "rgba(255,255,255,0.72)",
        backdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.85)",
        borderRadius: 20,
        padding: "26px 28px",
      }}
    >
      <div className="flex justify-between mb-5">
        <Skeleton className="h-3 w-40" />
        <Skeleton className="h-4 w-16" />
      </div>
      <div className="grid grid-cols-3 gap-3 mb-7">
        <Skeleton className="h-16 rounded-lg" />
        <Skeleton className="h-16 rounded-lg" />
        <Skeleton className="h-16 rounded-lg" />
      </div>
      <Skeleton className="h-40 w-40 rounded-full mx-auto mb-4" />
      <Skeleton className="h-8 w-full rounded-md mb-4" />
      <Separator />
      <div className="mt-3 space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
      </div>
    </div>
  );
}
