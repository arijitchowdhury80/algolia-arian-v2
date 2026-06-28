"use client";

import { useRef, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { EvidenceBadge } from "./evidence-badge";
import type { EvidenceTier } from "./evidence-badge";
import { Separator } from "@/components/ui/separator";
import { Globe, Search, ShoppingCart, Server } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { ModuleResult, TechStackResult } from "@/lib/types";

/**
 * TechStackCard — technology detection results rendered inline in chat.
 * Pattern: `.glow-card` (conic-gradient border glow on hover) from Audit SPA.
 */

interface TechStackCardProps {
  data: ModuleResult;
  isLoading?: boolean;
  error?: string | null;
}

export function TechStackCard({ data, isLoading, error }: TechStackCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  // Glow-card mouse tracking (conic-gradient border)
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

  if (isLoading) return <TechStackSkeleton />;

  if (error) {
    return (
      <div className="my-2 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-semibold text-red-600">Tech stack unavailable</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  const raw = (data.output ?? {}) as Partial<TechStackResult>;
  const output = {
    search_vendor: raw.search_vendor ?? null,
    ecommerce_platform: raw.ecommerce_platform ?? null,
    cms: raw.cms ?? null,
    cdn: raw.cdn ?? null,
    analytics: raw.analytics ?? [],
    personalization: raw.personalization ?? [],
    all_technologies: raw.all_technologies ?? [],
    algolia_detected: raw.algolia_detected ?? false,
  };

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="glow-card my-2 p-5"
      style={
        {
          "--glow-angle": "0deg",
        } as React.CSSProperties
      }
    >
      {/* Glow CSS */}
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
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[var(--muted-text)]">
          <Globe className="h-3.5 w-3.5" />
          Technology Stack
        </div>
        <Badge variant="outline" className="text-[10px] font-mono">
          {data.module_version}
        </Badge>
      </div>

      {/* Duration */}
      <p className="text-[10px] text-[var(--muted-text)] mb-3">
        {data.duration_ms}ms
        {data.status !== "success" && (
          <span className="ml-2 text-amber-500">({data.status})</span>
        )}
      </p>

      {/* Search vendor */}
      {output.search_vendor && (
        <div className="flex items-center gap-2 mb-2">
          <Search className="h-3.5 w-3.5 text-[var(--muted-text)]" />
          <span className="text-xs text-[var(--muted-text)]">Search:</span>
          <span className="text-xs font-semibold text-[#23263B]">
            {output.search_vendor.name}
          </span>
          <Badge
            variant="outline"
            className={cn(
              "text-[10px]",
              output.search_vendor.status === "ACTIVE"
                ? "bg-green-500/15 text-green-600 border-green-500/30"
                : "bg-zinc-400/15 text-zinc-500 border-zinc-400/30"
            )}
          >
            {output.search_vendor.status}
          </Badge>
          <EvidenceBadge
            tier={output.search_vendor.evidence_tier as EvidenceTier}
          />
        </div>
      )}

      {/* Ecommerce platform */}
      {output.ecommerce_platform && (
        <div className="flex items-center gap-2 mb-2">
          <ShoppingCart className="h-3.5 w-3.5 text-[var(--muted-text)]" />
          <span className="text-xs text-[var(--muted-text)]">Ecommerce:</span>
          <span className="text-xs font-semibold">{output.ecommerce_platform}</span>
        </div>
      )}

      {/* CMS / CDN */}
      {(output.cms || output.cdn) && (
        <div className="flex items-center gap-2 mb-3">
          <Server className="h-3.5 w-3.5 text-[var(--muted-text)]" />
          {output.cms && (
            <>
              <span className="text-xs text-[var(--muted-text)]">CMS:</span>
              <span className="text-xs font-semibold">{output.cms}</span>
            </>
          )}
          {output.cdn && (
            <>
              <span className="ml-2 text-xs text-[var(--muted-text)]">CDN:</span>
              <span className="text-xs font-semibold">{output.cdn}</span>
            </>
          )}
        </div>
      )}

      <Separator className="mb-3" />

      {/* Analytics & personalization pills */}
      {output.analytics && output.analytics.length > 0 && (
        <div className="mb-2">
          <span className="text-[10px] text-[var(--muted-text)]">Analytics</span>
          <div className="mt-1 flex flex-wrap gap-1">
            {output.analytics.map((a) => (
              <Badge key={a} variant="secondary" className="text-[10px]">
                {a}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {output.personalization && output.personalization.length > 0 && (
        <div className="mb-2">
          <span className="text-[10px] text-[var(--muted-text)]">Personalization</span>
          <div className="mt-1 flex flex-wrap gap-1">
            {output.personalization.map((p) => (
              <Badge key={p} variant="secondary" className="text-[10px]">
                {p}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Tech count */}
      {output.all_technologies && (
        <p className="text-[10px] text-[var(--muted-text)] mt-2">
          {output.all_technologies.length} technologies detected
        </p>
      )}

      {/* Detection banners */}
      {output.algolia_detected ? (
        <div className="mt-2 rounded-md bg-green-50 border border-green-200 px-3 py-2 text-xs text-green-700">
          Algolia detected on this domain
        </div>
      ) : output.search_vendor ? (
        <div className="mt-2 rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-700">
          Competitor detected: {output.search_vendor.name} — displacement opportunity
        </div>
      ) : null}

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

function TechStackSkeleton() {
  return (
    <div className="my-2 rounded-xl border border-[var(--border-warm)] bg-white p-5">
      <div className="flex justify-between mb-3">
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-4 w-16" />
      </div>
      <div className="space-y-2.5">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-4 w-36" />
        <Skeleton className="h-4 w-40" />
        <Separator />
        <div className="flex gap-1.5">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-5 w-14 rounded-full" />
        </div>
      </div>
    </div>
  );
}
