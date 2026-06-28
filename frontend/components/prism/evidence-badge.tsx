"use client";

import { cn } from "@/lib/utils";

/**
 * Evidence tier types matching Pydantic schema.
 * Each tier maps to a visual style (proof-pill pattern from Algolia SPA).
 */
export type EvidenceTier =
  | "VERIFIED"
  | "WEBFETCH"
  | "WEBSEARCH"
  | "ESTIMATE"
  | "NO_SOURCE";

interface EvidenceBadgeProps {
  tier: EvidenceTier;
  sourceUrl?: string | null;
  sourceLabel?: string;
  className?: string;
}

/**
 * Proof-pill style evidence badge — matches the `.proof-pill` pattern
 * from the Algolia Search Audit SPA. Two-part: colored badge + label.
 */

const tierConfig: Record<
  EvidenceTier,
  { bg: string; text: string; border: string; icon: string; label: string }
> = {
  VERIFIED: {
    bg: "bg-green-500/10",
    text: "text-green-600",
    border: "border-green-500/25",
    icon: "✓",
    label: "Verified",
  },
  WEBFETCH: {
    bg: "bg-blue-500/10",
    text: "text-blue-600",
    border: "border-blue-500/25",
    icon: "🌐",
    label: "Web Fetch",
  },
  WEBSEARCH: {
    bg: "bg-amber-500/10",
    text: "text-amber-600",
    border: "border-amber-500/25",
    icon: "🔍",
    label: "Web Search",
  },
  ESTIMATE: {
    bg: "bg-zinc-400/10",
    text: "text-zinc-500",
    border: "border-zinc-400/25",
    icon: "~",
    label: "Estimate",
  },
  NO_SOURCE: {
    bg: "bg-red-500/10",
    text: "text-red-500",
    border: "border-red-500/25",
    icon: "⚠",
    label: "No Source",
  },
};

export function EvidenceBadge({
  tier,
  sourceUrl,
  sourceLabel,
  className,
}: EvidenceBadgeProps) {
  const config = tierConfig[tier] ?? tierConfig.NO_SOURCE;

  const badge = (
    <span
      className={cn(
        "inline-flex items-center gap-0 rounded-full overflow-hidden border text-[11px] font-semibold",
        config.border,
        className
      )}
    >
      {/* Badge part — colored background */}
      <span
        className={cn(
          "px-2 py-0.5 text-white",
          tier === "VERIFIED"
            ? "bg-green-600"
            : tier === "WEBFETCH"
              ? "bg-blue-600"
              : tier === "WEBSEARCH"
                ? "bg-amber-600"
                : tier === "ESTIMATE"
                  ? "bg-zinc-500"
                  : "bg-red-500"
        )}
      >
        {config.icon}
      </span>
      {/* Label part */}
      <span className={cn("px-2 py-0.5", config.bg, config.text)}>
        {sourceLabel ?? config.label}
      </span>
    </span>
  );

  if (sourceUrl) {
    return (
      <a
        href={sourceUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex hover:opacity-80 transition-opacity"
      >
        {badge}
      </a>
    );
  }

  return badge;
}
