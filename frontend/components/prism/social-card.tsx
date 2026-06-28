"use client";

import { useRef, useCallback, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageSquare, Quote, Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ModuleResult, SocialResult } from "@/lib/types";

/**
 * SocialCard — executive social activity, quotable statements, and social presence.
 * Pattern: `.glow-card` (conic-gradient border glow on hover).
 */

interface SocialCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

export function SocialCard({ data, isLoading, error }: SocialCardProps) {
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

  if (isLoading) return <SocialSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Social data unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = (data.output ?? {}) as Partial<SocialResult>;
  const output = {
    twitter_presence: raw.twitter_presence ?? false,
    company_social_summary: raw.company_social_summary ?? null,
    executive_posts: raw.executive_posts ?? [],
    quotable_statements: raw.quotable_statements ?? [],
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
          <MessageSquare className="h-3.5 w-3.5" />
          Social Signals
        </div>
        <div className="flex items-center gap-1.5">
          {output.twitter_presence && (
            <Badge variant="outline" className="text-[10px] bg-sky-50 text-sky-600 border-sky-200">
              <span className="font-bold mr-0.5">𝕏</span>
              Active
            </Badge>
          )}
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

      {/* Company social summary */}
      {output.company_social_summary && (
        <p className="text-xs text-[#23263B] leading-relaxed mb-4">{output.company_social_summary}</p>
      )}

      {/* Executive activity feed */}
      {output.executive_posts.length > 0 && (
        <div className="mb-4">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)] mb-2 block">
            Executive Activity
          </span>
          <div className="space-y-2">
            {output.executive_posts.slice(0, 5).map((post, i) => (
              <div
                key={i}
                className="group rounded-lg border border-[var(--border-warm)] px-3 py-2.5 transition-colors hover:bg-[#F8F9FF]"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-[#23263B]">{post.executive_name}</span>
                  <span className="text-[10px] text-[var(--muted-text)]">{post.date}</span>
                </div>
                <p className="text-[11px] text-[var(--muted-text)] leading-relaxed line-clamp-2 mb-1.5">
                  {post.post_summary}
                </p>
                <div className="flex items-center gap-1.5">
                  <Badge variant="secondary" className="text-[9px]">
                    {post.topic}
                  </Badge>
                  {post.algolia_relevance && (
                    <Badge
                      variant="outline"
                      className="text-[9px] bg-[#003DFF]/5 text-[#003DFF] border-[#003DFF]/20"
                    >
                      {post.algolia_relevance}
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quotable statements */}
      {output.quotable_statements.length > 0 && (
        <>
          <Separator className="mb-3" />
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Quote className="h-3.5 w-3.5 text-[var(--muted-text)]" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
                Quotable Statements
              </span>
            </div>
            <div className="space-y-2.5">
              {output.quotable_statements.map((qs, i) => (
                <QuotableRow key={i} statement={qs.statement} speaker={qs.speaker} context={qs.context} />
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

function QuotableRow({ statement, speaker, context }: { statement: string; speaker: string; context: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(`"${statement}" — ${speaker}`).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {
      // Clipboard API may fail in non-secure contexts — silently degrade
    });
  }, [statement, speaker]);

  return (
    <blockquote className="border-l-2 border-[#5468FF]/30 pl-3 py-1 group/quote">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs text-[#23263B] italic leading-relaxed flex-1">
          &ldquo;{statement}&rdquo;
        </p>
        <button
          onClick={handleCopy}
          className="shrink-0 mt-0.5 rounded p-1 text-[var(--muted-text)] hover:text-[#003DFF] hover:bg-[#003DFF]/5 transition-colors opacity-0 group-hover/quote:opacity-100"
          title="Copy quote"
          type="button"
        >
          {copied ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
        </button>
      </div>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-[10px] font-semibold text-[#23263B]">{speaker}</span>
        <span className="text-[10px] text-[var(--muted-text)]">{context}</span>
      </div>
    </blockquote>
  );
}

function SocialSkeleton() {
  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5">
      <div className="flex justify-between mb-3">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-4 w-28 rounded-full" />
      </div>
      <Skeleton className="h-3 w-full mb-1" />
      <Skeleton className="h-3 w-3/4 mb-4" />
      {[1, 2, 3].map((i) => (
        <div key={i} className="rounded-lg border border-[var(--border-warm)] p-3 mb-2">
          <Skeleton className="h-3 w-32 mb-2" />
          <Skeleton className="h-2.5 w-full mb-1" />
          <Skeleton className="h-4 w-16 rounded-full" />
        </div>
      ))}
    </div>
  );
}
