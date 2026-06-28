"use client";

import { useRef, useCallback } from "react";
import NumberFlow from "@number-flow/react";
import { useInView } from "react-intersection-observer";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Briefcase, Users, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ModuleResult, HiringResult } from "@/lib/types";

/**
 * HiringCard — hiring signals, buying committee, and champion signals.
 * Pattern: `.glow-card` (conic-gradient border glow on hover).
 */

interface HiringCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

const tierConfig: Record<string, { label: string; color: string; bg: string; border: string }> = {
  tier1: { label: "Economic Buyer", color: "text-red-600", bg: "bg-red-50", border: "border-red-200" },
  tier2: { label: "Technical", color: "text-blue-600", bg: "bg-blue-50", border: "border-blue-200" },
  tier3: { label: "Champion", color: "text-purple-600", bg: "bg-purple-50", border: "border-purple-200" },
  tier4: { label: "User", color: "text-zinc-500", bg: "bg-zinc-50", border: "border-zinc-200" },
};

const buildVsBuyConfig: Record<string, { label: string; bg: string; text: string; border: string }> = {
  build: { label: "Build Signal", bg: "bg-amber-50", text: "text-amber-600", border: "border-amber-200" },
  buy: { label: "Buy Signal", bg: "bg-green-50", text: "text-green-600", border: "border-green-200" },
  mixed: { label: "Mixed Signal", bg: "bg-zinc-50", text: "text-zinc-500", border: "border-zinc-200" },
};

export function HiringCard({ data, isLoading, error }: HiringCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const { ref: inViewRef, inView } = useInView({ triggerOnce: true, threshold: 0.2 });

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const card = cardRef.current;
    if (!card) return;
    const rect = card.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const angle = Math.atan2(e.clientY - cy, e.clientX - cx) * (180 / Math.PI) + 90;
    card.style.setProperty("--glow-angle", `${angle}deg`);
    card.classList.add("glow-active");
  }, []);

  const handleMouseLeave = useCallback(() => {
    cardRef.current?.classList.remove("glow-active");
  }, []);

  if (isLoading) return <HiringSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Hiring data unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = (data.output ?? {}) as Partial<HiringResult>;
  const output = {
    total_roles: raw.total_roles ?? 0,
    roles_by_tier: raw.roles_by_tier ?? ({} as Record<string, number>),
    buying_committee: raw.buying_committee ?? [],
    champion_signals: raw.champion_signals ?? [],
    build_vs_buy_signal: raw.build_vs_buy_signal ?? "mixed",
    open_roles: raw.open_roles ?? [],
  };
  const bvb = buildVsBuyConfig[output.build_vs_buy_signal] ?? buildVsBuyConfig.mixed;

  return (
    <div
      ref={(node) => {
        (cardRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
        inViewRef(node);
      }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="glow-card my-2 p-5"
      style={{ "--glow-angle": "0deg" } as React.CSSProperties}
    >
      <style jsx>{`
        .glow-card {
          position: relative;
          border-radius: 12px;
          background: white;
          border: 1px solid var(--border-warm, #E5E7EB);
          isolation: isolate;
          transition: box-shadow 0.2s;
        }
        .glow-card::before {
          content: "";
          position: absolute;
          inset: -1px;
          border-radius: inherit;
          background: conic-gradient(
            from var(--glow-angle, 0deg),
            transparent 0%,
            #003dff 10%,
            #5468ff 25%,
            transparent 40%
          );
          opacity: 0;
          transition: opacity 0.4s ease;
          z-index: -1;
        }
        .glow-card::after {
          content: "";
          position: absolute;
          inset: 1px;
          border-radius: calc(12px - 1px);
          background: white;
          z-index: -1;
        }
        .glow-card.glow-active::before {
          opacity: 1;
        }
        .glow-card.glow-active {
          border-color: transparent;
          box-shadow: 0 4px 16px rgba(0, 61, 255, 0.08);
        }
      `}</style>

      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
          <Briefcase className="h-3.5 w-3.5" />
          Hiring Signals
        </div>
        <div className="flex items-center gap-1.5">
          <Badge
            variant="outline"
            className={cn("text-[10px]", bvb.bg, bvb.text, bvb.border)}
          >
            {bvb.label}
          </Badge>
          <Badge variant="outline" className="text-[10px] font-mono">
            {data.module_version}
          </Badge>
        </div>
      </div>

      <p className="text-[10px] text-[var(--muted-text)] mb-3">
        {data.duration_ms}ms
        {data.status !== "success" && (
          <span className="ml-2 text-amber-500">({data.status})</span>
        )}
      </p>

      {/* Total open roles */}
      <div className="flex items-end gap-2 mb-1">
        <div className="text-4xl font-bold text-[#23263B] leading-none tracking-tight">
          {inView ? <NumberFlow value={output.total_roles} /> : "0"}
        </div>
      </div>
      <p className="text-[10px] text-[var(--muted-text)] mb-4">open roles</p>

      {/* Roles by tier */}
      <div className="grid grid-cols-4 gap-2 mb-4">
        {(Object.entries(output.roles_by_tier) as [string, number][]).map(([tier, count]) => {
          const tc = tierConfig[tier] ?? tierConfig.tier4;
          return (
            <div key={tier} className={cn("rounded-lg border px-2.5 py-2 text-center", tc.bg, tc.border)}>
              <p className={cn("text-lg font-bold", tc.color)}>
                {inView ? <NumberFlow value={count} /> : "0"}
              </p>
              <p className="text-[9px] font-semibold uppercase tracking-wider text-[var(--muted-text)]">
                {tc.label}
              </p>
            </div>
          );
        })}
      </div>

      <Separator className="mb-3" />

      {/* Buying committee */}
      {output.buying_committee.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center gap-1.5 mb-2">
            <Users className="h-3.5 w-3.5 text-[var(--muted-text)]" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
              Buying Committee
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[var(--border-warm)]">
                  <th className="text-left py-1.5 text-[10px] font-semibold text-[var(--muted-text)]">Name</th>
                  <th className="text-left py-1.5 text-[10px] font-semibold text-[var(--muted-text)]">Title</th>
                  <th className="text-left py-1.5 text-[10px] font-semibold text-[var(--muted-text)]">Tier</th>
                  <th className="text-left py-1.5 text-[10px] font-semibold text-[var(--muted-text)]">Approach</th>
                </tr>
              </thead>
              <tbody>
                {output.buying_committee.map((member) => {
                  const tc = tierConfig[member.tier] ?? tierConfig.tier4;
                  return (
                    <tr key={member.name} className="border-b border-[var(--border-warm)] last:border-b-0">
                      <td className="py-1.5 font-semibold text-[#23263B]">{member.name}</td>
                      <td className="py-1.5 text-[var(--muted-text)]">{member.title}</td>
                      <td className="py-1.5">
                        <Badge variant="outline" className={cn("text-[9px]", tc.bg, tc.color, tc.border)}>
                          {tc.label}
                        </Badge>
                      </td>
                      <td className="py-1.5 text-[var(--muted-text)]">{member.approach}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Champion signals */}
      {output.champion_signals.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Star className="h-3.5 w-3.5 text-green-500" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-green-600">
              Champion Signals
            </span>
          </div>
          <div className="space-y-1.5">
            {output.champion_signals.map((cs, i) => (
              <div
                key={i}
                className="rounded-lg border border-green-200 bg-green-50 px-3 py-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-green-700">{cs.person_name}</span>
                  <Badge variant="outline" className="text-[9px] bg-green-100 text-green-600 border-green-300">
                    {cs.confidence}
                  </Badge>
                </div>
                <p className="text-[11px] text-green-600 mt-0.5">{cs.signal}</p>
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
    </div>
  );
}

function HiringSkeleton() {
  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5">
      <div className="flex justify-between mb-3">
        <Skeleton className="h-3 w-28" />
        <div className="flex gap-1.5">
          <Skeleton className="h-4 w-20 rounded-full" />
          <Skeleton className="h-4 w-16" />
        </div>
      </div>
      <Skeleton className="h-10 w-20 mb-2" />
      <Skeleton className="h-3 w-16 mb-4" />
      <div className="grid grid-cols-4 gap-2 mb-3">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-14 w-full rounded-lg" />
        ))}
      </div>
      <Separator />
      <div className="mt-3 space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
        <Skeleton className="h-3 w-4/6" />
      </div>
    </div>
  );
}
