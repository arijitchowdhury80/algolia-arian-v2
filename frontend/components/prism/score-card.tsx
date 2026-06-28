"use client";

import { useRef, useCallback, type MouseEvent } from "react";
import NumberFlow from "@number-flow/react";
import { useInView } from "react-intersection-observer";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * ScoreCard — large animated score number with severity bars and critical gaps.
 * Pattern: OV-Bento glassmorphism tile with mouse-tracking spotlight,
 * animated number, critical gaps, and score breakdown bars.
 */

interface ScoreBreakdownItem {
  area: string;
  score: number;
  severity: "critical" | "moderate" | "positive";
}

interface ScoreCardProps {
  overall: number | null;
  verdict: string;
  criticalGaps: string[];
  breakdown?: ScoreBreakdownItem[];
  isLoading?: boolean;
  error?: string | null;
}

function scoreColor(score: number): string {
  if (score < 4) return "#DC2626";
  if (score < 6.5) return "#D97706";
  return "#059669";
}

function severityHexColor(severity: string): string {
  if (severity === "critical") return "#DC2626";
  if (severity === "moderate") return "#D97706";
  return "#059669";
}

export function ScoreCard({
  overall,
  verdict,
  criticalGaps,
  breakdown,
  isLoading,
  error,
}: ScoreCardProps) {
  const { ref: inViewRef, inView } = useInView({ triggerOnce: true, threshold: 0.2 });
  const cardRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = useCallback((e: MouseEvent<HTMLDivElement>) => {
    const el = cardRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--ov-x", `${e.clientX - rect.left}px`);
    el.style.setProperty("--ov-y", `${e.clientY - rect.top}px`);
  }, []);

  // Merge refs (intersection observer + card ref)
  const setRefs = useCallback(
    (node: HTMLDivElement | null) => {
      cardRef.current = node;
      inViewRef(node);
    },
    [inViewRef],
  );

  if (isLoading) {
    return <ScoreCardSkeleton />;
  }

  if (error) {
    return (
      <div className="my-2 rounded-[20px] border border-red-200 bg-red-50 p-[26px_28px]">
        <p className="text-sm font-semibold text-red-600">Score unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  if (overall === null) return null;

  const color = scoreColor(overall);

  return (
    <div
      ref={setRefs}
      onMouseMove={handleMouseMove}
      className="group relative my-2 overflow-hidden transition-all hover:-translate-y-0.5"
      style={{
        background: "rgba(255,255,255,0.72)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.85)",
        borderRadius: "20px",
        boxShadow:
          "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06), 0 16px 36px rgba(0,0,0,0.07), inset 0 1px 0 rgba(255,255,255,0.95)",
        padding: "26px 28px",
      }}
    >
      {/* Mouse-tracking spotlight overlay */}
      <div
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background:
            "radial-gradient(600px circle at var(--ov-x) var(--ov-y), rgba(220,38,38,0.07) 0%, transparent 65%)",
          borderRadius: "20px",
        }}
      />

      {/* Eyebrow label */}
      <p
        style={{
          fontSize: "10px",
          fontWeight: 800,
          textTransform: "uppercase",
          letterSpacing: "0.12em",
          color: "#6B7280",
          marginBottom: "14px",
        }}
      >
        How Bad Is Their Search?
      </p>

      {/* Score display row */}
      <div className="flex items-end gap-3" style={{ marginBottom: "16px" }}>
        {/* Large animated number */}
        <div
          style={{
            color,
            fontSize: "72px",
            fontWeight: 900,
            letterSpacing: "-3px",
            lineHeight: 1,
          }}
        >
          {inView ? (
            <NumberFlow
              value={overall}
              format={{ minimumFractionDigits: 1, maximumFractionDigits: 1 }}
            />
          ) : (
            "0.0"
          )}
        </div>

        {/* "out of 10" subscript */}
        <span
          style={{
            fontSize: "11px",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "#6B7280",
            paddingBottom: "10px",
          }}
        >
          out of 10
        </span>
      </div>

      {/* Verdict badge */}
      <div style={{ marginBottom: "16px" }}>
        <span
          style={{
            display: "inline-block",
            background: `${color}18`,
            color,
            padding: "3px 10px",
            borderRadius: "4px",
            fontSize: "12px",
            fontWeight: 700,
          }}
        >
          {verdict}
        </span>
      </div>

      {/* Critical gaps list */}
      {criticalGaps.length > 0 && (
        <div
          style={{
            borderTop: "1px solid rgba(0,0,0,0.06)",
            paddingTop: "12px",
            marginBottom: "16px",
          }}
        >
          <p
            style={{
              fontSize: "12px",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.10em",
              color: "#DC2626",
              marginBottom: "8px",
            }}
          >
            Critical Gaps
          </p>
          {criticalGaps.map((gap, i) => (
            <div
              key={i}
              className="flex items-center gap-2"
              style={{
                borderBottom: "1px solid rgba(220,38,38,0.12)",
                padding: "7px 0",
              }}
            >
              <span
                className="shrink-0"
                style={{
                  width: "6px",
                  height: "6px",
                  borderRadius: "50%",
                  background: "#DC2626",
                }}
              />
              <span style={{ fontSize: "14px", color: "#23263B" }}>{gap}</span>
            </div>
          ))}
        </div>
      )}

      {/* Score breakdown bars */}
      {breakdown && breakdown.length > 0 && (
        <div>
          {breakdown.map((item) => {
            const barColor = severityHexColor(item.severity);
            return (
              <div
                key={item.area}
                style={{
                  display: "grid",
                  gridTemplateColumns: "180px 1fr 48px",
                  alignItems: "center",
                  gap: "8px",
                  padding: "7px 0",
                  borderBottom: "1px solid #E5E7EB",
                }}
              >
                <span style={{ fontSize: "14px", color: "#23263B" }}>
                  {item.area}
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
                      borderRadius: "5px",
                      background: barColor,
                      width: `${item.score * 10}%`,
                      transition: "width 0.6s ease",
                    }}
                  />
                </div>
                <span
                  style={{
                    fontSize: "14px",
                    fontWeight: 600,
                    color: barColor,
                    textAlign: "right",
                  }}
                >
                  {item.score}/10
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Navigation link */}
      <div
        style={{
          borderTop: "1px solid rgba(0,0,0,0.07)",
          marginTop: "auto",
          paddingTop: "12px",
        }}
      >
        <a
          href="#search-audit"
          className="transition-colors"
          style={{
            fontSize: "11px",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "#94A3B8",
            textDecoration: "none",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.color = "#003DFF";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.color = "#94A3B8";
          }}
        >
          Search Audit &rarr;
        </a>
      </div>
    </div>
  );
}

function ScoreCardSkeleton() {
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
        padding: "26px 28px",
      }}
    >
      <Skeleton className="mb-4 h-3 w-40" />
      <Skeleton className="mb-4 h-[72px] w-32" />
      <Skeleton className="mb-4 h-6 w-24 rounded" />
      <div className="space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-3/4" />
        <Skeleton className="h-3 w-5/6" />
      </div>
    </div>
  );
}
