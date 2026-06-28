"use client";

import { useRef, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Newspaper, Quote, AlertTriangle, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ModuleResult, NewsResult } from "@/lib/types";

/**
 * NewsCard — news timeline, executive quotes, and urgency signals.
 * Pattern: `.glow-card` + SignalCard-like severity badges for urgency signals.
 */

interface NewsCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

const categoryColors: Record<string, { bg: string; text: string; border: string }> = {
  leadership_change: { bg: "bg-violet-50", text: "text-violet-600", border: "border-violet-200" },
  product_launch: { bg: "bg-blue-50", text: "text-blue-600", border: "border-blue-200" },
  partnership: { bg: "bg-green-50", text: "text-green-600", border: "border-green-200" },
  financial: { bg: "bg-amber-50", text: "text-amber-600", border: "border-amber-200" },
  acquisition: { bg: "bg-red-50", text: "text-red-600", border: "border-red-200" },
  technology: { bg: "bg-cyan-50", text: "text-cyan-600", border: "border-cyan-200" },
  other: { bg: "bg-zinc-50", text: "text-zinc-500", border: "border-zinc-200" },
};

const severityConfig: Record<string, { bg: string; text: string; border: string }> = {
  HIGH: { bg: "bg-red-50", text: "text-red-600", border: "border-red-200" },
  MEDIUM: { bg: "bg-amber-50", text: "text-amber-600", border: "border-amber-200" },
  LOW: { bg: "bg-green-50", text: "text-green-600", border: "border-green-200" },
};

export function NewsCard({ data, isLoading, error }: NewsCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);

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

  if (isLoading) return <NewsSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">News data unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = (data.output ?? {}) as Partial<NewsResult>;
  const output = {
    news_items: raw.news_items ?? [],
    executive_quotes: raw.executive_quotes ?? [],
    urgency_signals: raw.urgency_signals ?? [],
    sell_signals: raw.sell_signals ?? [],
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
          <Newspaper className="h-3.5 w-3.5" />
          News & Signals
        </div>
        <Badge variant="outline" className="text-[10px] font-mono">
          {data.module_version}
        </Badge>
      </div>

      <p className="text-[10px] text-[var(--muted-text)] mb-3">
        {data.duration_ms}ms
        {data.status !== "success" && (
          <span className="ml-2 text-amber-500">({data.status})</span>
        )}
      </p>

      {/* News timeline */}
      {output.news_items.length > 0 && (
        <div className="mb-4">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)] mb-2 block">
            Recent News
          </span>
          <div className="space-y-0">
            {output.news_items.slice(0, 6).map((item, i) => {
              const cc = categoryColors[item.category] ?? categoryColors.other;
              return (
                <div
                  key={i}
                  className="relative flex items-start gap-3 py-2 border-b border-[var(--border-warm)] last:border-b-0"
                >
                  {/* Timeline dot + line */}
                  <div className="flex flex-col items-center shrink-0 mt-1">
                    <span className={cn("h-2 w-2 rounded-full", cc.bg.replace("50", "500").replace("bg-", "bg-"))} />
                    {i < (output.news_items?.length ?? 0) - 1 && (
                      <div className="w-px flex-1 bg-[var(--border-warm)] mt-1" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <Badge
                        variant="outline"
                        className={cn("text-[9px]", cc.bg, cc.text, cc.border)}
                      >
                        {item.category.replace(/_/g, " ")}
                      </Badge>
                      <span className="text-[10px] text-[var(--muted-text)]">{item.date}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-[#23263B] leading-snug line-clamp-2">
                        {item.headline}
                      </span>
                      {item.url && (
                        <a href={item.url} target="_blank" rel="noopener noreferrer" className="shrink-0">
                          <ExternalLink className="h-3 w-3 text-[var(--muted-text)] hover:text-[#003DFF]" />
                        </a>
                      )}
                    </div>
                    <span className="text-[10px] text-[var(--muted-text)]">{item.source}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Executive quotes */}
      {output.executive_quotes.length > 0 && (
        <>
          <Separator className="mb-3" />
          <div className="mb-4">
            <div className="flex items-center gap-1.5 mb-2">
              <Quote className="h-3.5 w-3.5 text-[var(--muted-text)]" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
                Executive Quotes
              </span>
            </div>
            <div className="space-y-2.5">
              {output.executive_quotes.map((eq, i) => (
                <blockquote
                  key={i}
                  className="border-l-2 border-[#003DFF]/30 pl-3 py-1"
                >
                  <p className="text-xs text-[#23263B] italic leading-relaxed">
                    &ldquo;{eq.quote}&rdquo;
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] font-semibold text-[#23263B]">{eq.speaker}</span>
                    <span className="text-[10px] text-[var(--muted-text)]">{eq.context}</span>
                    {eq.source_url && (
                      <a href={eq.source_url} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="h-2.5 w-2.5 text-[var(--muted-text)] hover:text-[#003DFF]" />
                      </a>
                    )}
                  </div>
                </blockquote>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Urgency signals */}
      {output.urgency_signals.length > 0 && (
        <>
          <Separator className="mb-3" />
          <div className="mb-2">
            <div className="flex items-center gap-1.5 mb-2">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
                Urgency Signals
              </span>
            </div>
            <div className="space-y-1.5">
              {output.urgency_signals.map((sig, i) => {
                const sc = severityConfig[sig.severity] ?? severityConfig.LOW;
                return (
                  <div
                    key={i}
                    className={cn(
                      "group relative flex items-start gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-[#F8F9FF]",
                      "border border-[var(--border-warm)]"
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span
                          className={cn(
                            "rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider border",
                            sc.bg, sc.text, sc.border
                          )}
                        >
                          {sig.severity}
                        </span>
                        <span className="text-xs font-semibold text-[#23263B]">{sig.title}</span>
                      </div>
                      <p className="text-[11px] text-[var(--muted-text)] leading-relaxed line-clamp-2">
                        {sig.detail}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* Sell signals */}
      {output.sell_signals.length > 0 && (
        <>
          <Separator className="my-3" />
          <div>
            <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)] mb-2 block">
              Sell Signals
            </span>
            <div className="flex flex-wrap gap-1.5">
              {output.sell_signals.map((s, i) => (
                <Badge key={i} variant="secondary" className="text-[10px]">
                  {s}
                </Badge>
              ))}
            </div>
          </div>
        </>
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

function NewsSkeleton() {
  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5">
      <div className="flex justify-between mb-3">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-4 w-16" />
      </div>
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex gap-3 py-2 border-b border-[var(--border-warm)] last:border-b-0">
          <Skeleton className="h-2 w-2 rounded-full shrink-0 mt-1" />
          <div className="flex-1 space-y-1.5">
            <div className="flex gap-2">
              <Skeleton className="h-4 w-16 rounded-full" />
              <Skeleton className="h-3 w-12" />
            </div>
            <Skeleton className="h-3 w-full" />
          </div>
        </div>
      ))}
      <Separator className="my-3" />
      <Skeleton className="h-12 w-full rounded-lg" />
    </div>
  );
}
