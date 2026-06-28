"use client";

import { cn } from "@/lib/utils";
import { EvidenceBadge } from "./evidence-badge";
import type { EvidenceTier } from "./evidence-badge";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * SignalCard — "Why Act Now" intelligence signals card.
 * Glassmorphism container with urgency-grouped signal rows,
 * colored type badges, and source attribution.
 */

export interface Signal {
  type: "exec" | "competitor" | "industry_risk" | "leadership" | "hiring" | "news" | "earnings";
  title: string;
  detail: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  sourceUrl?: string | null;
  sourceLabel?: string;
  evidenceTier?: EvidenceTier;
  date?: string;
  urgencyTier?: 1 | 2 | 3;
}

interface SignalCardProps {
  signals: Signal[];
  isLoading?: boolean;
  error?: string | null;
}

/* ---------- Type badge color map ---------- */
const typeBadgeColors: Record<string, string> = {
  exec: "#003DFF",
  earnings: "#003DFF",
  competitor: "#DC2626",
  industry_risk: "#D97706",
  leadership: "#DC2626",
  hiring: "#7C3AED",
  news: "#003DFF",
};

const typeBadgeLabels: Record<string, string> = {
  exec: "Exec",
  earnings: "Earnings",
  competitor: "Competitor",
  industry_risk: "Industry Risk",
  leadership: "Leadership",
  hiring: "Hiring",
  news: "News",
};

/* ---------- Urgency tier config ---------- */
interface TierStyle {
  label: string;
  color: string;
  borderColor: string;
}

const tierStyles: Record<number, TierStyle> = {
  1: { label: "Urgent — Act This Week", color: "#DC2626", borderColor: "#DC2626" },
  2: { label: "Strong Signal", color: "#D97706", borderColor: "#D97706" },
  3: { label: "Context", color: "#6B7280", borderColor: "#6B7280" },
};

/* ---------- Helpers ---------- */

function inferUrgencyTier(signal: Signal): number {
  if (signal.urgencyTier) return signal.urgencyTier;
  if (signal.severity === "HIGH") return 1;
  if (signal.severity === "MEDIUM") return 2;
  return 3;
}

function groupByUrgency(signals: Signal[]): Map<number, Signal[]> {
  const groups = new Map<number, Signal[]>();
  for (const sig of signals) {
    const tier = inferUrgencyTier(sig);
    const list = groups.get(tier) ?? [];
    list.push(sig);
    groups.set(tier, list);
  }
  return new Map([...groups.entries()].sort(([a], [b]) => a - b));
}

/* ---------- Sub-components ---------- */

function TypeBadge({ type }: { type: Signal["type"] }) {
  const color = typeBadgeColors[type] ?? "#003DFF";
  const label = typeBadgeLabels[type] ?? type;

  return (
    <span
      className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-md px-2 py-[3px] text-xs font-semibold"
      style={{
        background: `${color}15`,
        border: `1px solid ${color}35`,
        color,
      }}
    >
      {label}
    </span>
  );
}

function TierHeader({ tier }: { tier: number }) {
  const style = tierStyles[tier] ?? tierStyles[3];
  return (
    <div
      className="px-5"
      style={{
        fontSize: 12,
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: "0.10em",
        color: style.color,
        borderBottom: `2px solid ${style.borderColor}`,
        padding: "8px 0 4px",
      }}
    >
      {style.label}
    </div>
  );
}

function SignalRow({ sig, isLast }: { sig: Signal; isLast: boolean }) {
  const color = typeBadgeColors[sig.type] ?? "#003DFF";

  return (
    <div
      className={cn("flex items-start gap-4 px-5")}
      style={{
        borderBottom: isLast ? "none" : "1px solid #E5E7EB",
        padding: "14px 20px",
      }}
    >
      {/* Left — type badge */}
      <div className="pt-0.5">
        <TypeBadge type={sig.type} />
      </div>

      {/* Center — title + detail */}
      <div className="min-w-0 flex-1">
        <p
          style={{
            fontSize: 16,
            fontWeight: 600,
            color: "#23263B",
            lineHeight: 1.4,
            marginBottom: 4,
          }}
        >
          {sig.title}
        </p>
        <p
          style={{
            fontSize: 14,
            color: "#6B7280",
            lineHeight: 1.5,
          }}
        >
          {sig.detail}
        </p>

        {/* Evidence badge (kept from original) */}
        {sig.evidenceTier && (
          <div className="mt-1.5">
            <EvidenceBadge
              tier={sig.evidenceTier}
              sourceUrl={sig.sourceUrl}
              sourceLabel={sig.sourceLabel}
            />
          </div>
        )}
      </div>

      {/* Right — source link + date */}
      <div className="flex shrink-0 flex-col items-end">
        {sig.sourceUrl && (
          <a
            href={sig.sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:underline"
            style={{
              fontSize: 14,
              fontWeight: 600,
              color: "#003DFF",
              textDecoration: "none",
            }}
          >
            {sig.sourceLabel ?? "Source"}
          </a>
        )}
        {sig.date && (
          <span
            style={{
              fontSize: 12,
              color: "#6B7280",
              marginTop: 2,
            }}
          >
            {sig.date}
          </span>
        )}
      </div>
    </div>
  );
}

/* ---------- Main component ---------- */

export function SignalCard({ signals, isLoading, error }: SignalCardProps) {
  if (isLoading) return <SignalCardSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Signals unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  if (!signals.length) return null;

  const grouped = groupByUrgency(signals);

  return (
    <div
      className="my-2"
      style={{
        background: "rgba(255,255,255,0.72)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.85)",
        borderRadius: 20,
        boxShadow:
          "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06), 0 16px 36px rgba(0,0,0,0.07), inset 0 1px 0 rgba(255,255,255,0.95)",
      }}
    >
      {/* Header */}
      <div className="px-5 pt-5 pb-3">
        <span
          style={{
            fontSize: 10,
            fontWeight: 800,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            color: "#6B7280",
          }}
        >
          Intelligence Signals
        </span>
        <p
          style={{
            fontSize: 14,
            color: "#6B7280",
            marginTop: 4,
          }}
        >
          {signals.length} active signal{signals.length !== 1 ? "s" : ""} — call
          this week, not next quarter.
        </p>
      </div>

      {/* Grouped signals */}
      <div>
        {Array.from(grouped.entries()).map(([tier, tierSignals]) => (
          <div key={tier}>
            <TierHeader tier={tier} />
            {tierSignals.map((sig, i) => (
              <SignalRow
                key={`${tier}-${i}`}
                sig={sig}
                isLast={
                  i === tierSignals.length - 1 &&
                  tier === Math.max(...Array.from(grouped.keys()))
                }
              />
            ))}
          </div>
        ))}
      </div>

      {/* Bottom navigation */}
      <div
        className="flex items-center justify-center"
        style={{
          borderTop: "1px solid rgba(0,0,0,0.07)",
          padding: "12px 20px",
        }}
      >
        <a
          href="#signals"
          className="transition-colors"
          style={{
            fontSize: 11,
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
          See all signals &rarr;
        </a>
      </div>
    </div>
  );
}

/* ---------- Skeleton ---------- */

function SignalCardSkeleton() {
  return (
    <div
      className="my-2 p-5"
      style={{
        background: "rgba(255,255,255,0.72)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.85)",
        borderRadius: 20,
        boxShadow:
          "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06), 0 16px 36px rgba(0,0,0,0.07), inset 0 1px 0 rgba(255,255,255,0.95)",
      }}
    >
      <Skeleton className="mb-2 h-2.5 w-28" />
      <Skeleton className="mb-4 h-3 w-56" />
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="flex items-start gap-4 border-b border-gray-100 py-3.5 last:border-b-0"
        >
          <Skeleton className="h-5 w-16 shrink-0 rounded-md" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-full" />
          </div>
          <div className="flex flex-col items-end gap-1">
            <Skeleton className="h-3 w-14" />
            <Skeleton className="h-2.5 w-16" />
          </div>
        </div>
      ))}
    </div>
  );
}
