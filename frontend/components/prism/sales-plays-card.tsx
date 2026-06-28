"use client";

import { useRef, useCallback, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import { Target, ChevronDown, Copy, Check } from "lucide-react";
import type { ModuleResult, SalesPlaysResult } from "@/lib/types";

/**
 * SalesPlaysCard -- MEDDPICC, SPIN questions, objection handlers,
 * power map, talk tracks with copy button.
 */

interface SalesPlaysCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

const attitudeConfig: Record<string, { bg: string; text: string }> = {
  champion: { bg: "bg-green-500/15", text: "text-green-600" },
  neutral: { bg: "bg-zinc-400/15", text: "text-zinc-500" },
  blocker: { bg: "bg-red-500/15", text: "text-red-600" },
};

const spinColors: Record<string, string> = {
  situation: "text-blue-600",
  problem: "text-red-600",
  implication: "text-amber-600",
  need_payoff: "text-green-600",
};

export function SalesPlaysCard({ data, isLoading, error }: SalesPlaysCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [copiedTrack, setCopiedTrack] = useState<number | null>(null);

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

  const handleCopy = useCallback(async (text: string, index: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedTrack(index);
      setTimeout(() => setCopiedTrack(null), 2000);
    } catch {
      // Clipboard API failed silently
    }
  }, []);

  if (isLoading) return <SalesPlaysSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Sales plays unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = (data.output ?? {}) as Partial<SalesPlaysResult>;
  const output = {
    meddpicc: raw.meddpicc ?? [],
    spin_questions: raw.spin_questions ?? [],
    objection_handlers: raw.objection_handlers ?? [],
    power_map: raw.power_map ?? [],
    talk_tracks: raw.talk_tracks ?? [],
  };

  return (
    <div
      ref={cardRef}
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
          background: conic-gradient(from var(--glow-angle, 0deg), transparent 0%, #003dff 10%, #5468ff 25%, transparent 40%);
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
        .glow-card.glow-active::before { opacity: 1; }
        .glow-card.glow-active { border-color: transparent; box-shadow: 0 4px 16px rgba(0, 61, 255, 0.08); }
      `}</style>

      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
          <Target className="h-3.5 w-3.5" />
          Sales Plays
        </div>
        <Badge variant="outline" className="text-[10px] font-mono">
          {data.module_version}
        </Badge>
      </div>

      {/* MEDDPICC */}
      {output.meddpicc.length > 0 && (
        <div className="mb-3">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted-text)] mb-1.5 block">
            MEDDPICC
          </span>
          <div className="space-y-1.5">
            {output.meddpicc.map((item) => (
              <div
                key={item.letter}
                className="flex items-start gap-2 py-1.5 border-b border-[var(--border-warm)] last:border-b-0"
              >
                <span className="text-[11px] font-bold text-[#003DFF] w-4 shrink-0">
                  {item.letter}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="text-[11px] font-semibold text-[#23263B]">{item.name}</span>
                    {item.person && (
                      <Badge variant="secondary" className="text-[9px]">{item.person}</Badge>
                    )}
                  </div>
                  <p className="text-[10px] text-[var(--muted-text)] leading-relaxed">{item.evidence}</p>
                  <p className="text-[10px] text-[#003DFF] mt-0.5">{item.approach}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <Separator className="mb-3" />

      {/* SPIN questions */}
      {output.spin_questions.length > 0 && (
        <div className="mb-3">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted-text)] mb-1.5 block">
            SPIN Questions
          </span>
          <div className="space-y-1">
            {(["situation", "problem", "implication", "need_payoff"] as const).map((cat) => {
              const qs = output.spin_questions.filter((q) => q.category === cat);
              if (qs.length === 0) return null;
              return (
                <div key={cat}>
                  <span className={cn("text-[10px] font-bold uppercase tracking-wider", spinColors[cat])}>
                    {cat === "need_payoff" ? "Need-Payoff" : cat.charAt(0).toUpperCase() + cat.slice(1)}
                  </span>
                  {qs.map((q, i) => (
                    <p key={i} className="text-[11px] text-[#23263B] pl-2 py-0.5 leading-snug">
                      {q.question}
                    </p>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Objection handlers */}
      {output.objection_handlers.length > 0 && (
        <div className="mb-3">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted-text)] mb-1.5 block">
            Objection Handlers
          </span>
          {output.objection_handlers.map((oh, i) => (
            <Collapsible key={i}>
              <CollapsibleTrigger className="flex items-center gap-2 w-full py-1.5 text-left group">
                <ChevronDown className="h-3 w-3 text-[var(--muted-text)] transition-transform group-data-[state=open]:rotate-180" />
                <span className="text-[11px] font-medium text-[#23263B]">{oh.objection}</span>
              </CollapsibleTrigger>
              <CollapsibleContent className="pl-5 pb-1.5">
                <p className="text-[11px] text-[#23263B] mb-0.5">{oh.counter}</p>
                <p className="text-[10px] text-[var(--muted-text)] italic">{oh.evidence}</p>
              </CollapsibleContent>
            </Collapsible>
          ))}
        </div>
      )}

      <Separator className="mb-3" />

      {/* Power map */}
      {output.power_map.length > 0 && (
        <div className="mb-3">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted-text)] mb-1.5 block">
            Power Map
          </span>
          <div className="grid grid-cols-2 gap-1.5">
            {output.power_map.map((p, i) => {
              const ac = attitudeConfig[p.attitude] ?? attitudeConfig.neutral;
              return (
                <div
                  key={i}
                  className="rounded-lg border border-[var(--border-warm)] p-2"
                >
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="text-[11px] font-semibold text-[#23263B]">{p.person}</span>
                    <Badge variant="outline" className={cn("text-[9px]", ac.bg, ac.text)}>
                      {p.attitude}
                    </Badge>
                  </div>
                  <p className="text-[10px] text-[var(--muted-text)]">{p.title}</p>
                  <p className="text-[10px] text-[#003DFF] mt-0.5">{p.approach}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Talk tracks */}
      {output.talk_tracks.length > 0 && (
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted-text)] mb-1.5 block">
            Talk Tracks
          </span>
          <div className="space-y-1.5">
            {output.talk_tracks.map((tt, i) => (
              <div
                key={i}
                className="rounded-lg bg-[#F5F5F7] p-2.5 relative group"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-bold text-[#003DFF]">{tt.topic}</span>
                  <button
                    type="button"
                    onClick={() => handleCopy(tt.track, i)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-white/50"
                    aria-label={`Copy talk track for ${tt.topic}`}
                  >
                    {copiedTrack === i ? (
                      <Check className="h-3 w-3 text-green-600" />
                    ) : (
                      <Copy className="h-3 w-3 text-[var(--muted-text)]" />
                    )}
                  </button>
                </div>
                <p className="text-[11px] text-[#23263B] leading-relaxed">{tt.track}</p>
              </div>
            ))}
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

function SalesPlaysSkeleton() {
  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5">
      <div className="flex justify-between mb-3">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-4 w-16" />
      </div>
      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex gap-2">
            <Skeleton className="h-4 w-4" />
            <div className="flex-1 space-y-1">
              <Skeleton className="h-3 w-32" />
              <Skeleton className="h-2.5 w-full" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
