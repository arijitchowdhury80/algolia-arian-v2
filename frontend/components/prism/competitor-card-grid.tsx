/**
 * CompetitorCardGrid — responsive grid of competitor feature cards.
 * Hover: translateY(-3px) lift.
 *
 * Tokens: font.small (13px names/domains), font.caption (12px min)
 */
"use client";

import { useState } from "react";
import { font, color, radius, shadow } from "@/lib/tokens";
import type { CompetitorSeed } from "@/lib/types";

interface CompetitorCardGridProps {
  competitors: CompetitorSeed[];
  defaultVisible?: number;
}

export function CompetitorCardGrid({ competitors, defaultVisible = 4 }: CompetitorCardGridProps) {
  const [showAll, setShowAll] = useState(false);

  if (competitors.length === 0) {
    return (
      <div style={{ fontSize: font.small, color: color.ghost, fontStyle: "italic" }}>
        No competitor data available
      </div>
    );
  }

  const visible    = showAll ? competitors : competitors.slice(0, defaultVisible);
  const hiddenCount = Math.max(0, competitors.length - defaultVisible);

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10 }}>
        {visible.map((comp) => (
          <CompetitorCard key={comp.company_name} competitor={comp} />
        ))}
      </div>
      {hiddenCount > 0 && (
        <button
          onClick={() => setShowAll((v) => !v)}
          style={{
            marginTop: 8,
            fontSize: font.small,              // 13px
            fontWeight: font.weight.semibold,
            color: color.blue,
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: "6px 0",
            opacity: 0.75,
          }}
          onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.opacity = "1")}
          onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.opacity = "0.75")}
        >
          {showAll ? "↑ Show less" : `↓ Show ${hiddenCount} more`}
        </button>
      )}
    </div>
  );
}

function CompetitorCard({ competitor }: { competitor: CompetitorSeed }) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: "rgba(255,255,255,0.60)",
        backdropFilter: "blur(8px)",
        WebkitBackdropFilter: "blur(8px)",
        border: `1px solid ${color.divider}`,
        borderRadius: radius.lg,
        padding: "14px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        transform: hovered ? "translateY(-3px)" : "translateY(0)",
        boxShadow: hovered ? shadow.lift : shadow.flat,
        transition: "transform 200ms ease, box-shadow 200ms ease",
        cursor: "default",
      }}
    >
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div
          style={{
            width: 32, height: 32,
            borderRadius: radius.md,
            background: color.blue08,
            border: `1px solid ${color.blue12}`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: font.small,              // 13px — was 13px
            fontWeight: font.weight.semibold,
            color: color.blue,
            flexShrink: 0,
            textTransform: "uppercase",
          }}
        >
          {competitor.company_name[0]}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: font.small, fontWeight: font.weight.semibold, color: color.navy, lineHeight: 1.2 }}>
            {competitor.company_name}
          </div>
          <a
            href={`https://${competitor.domain}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: font.caption, color: color.blue, opacity: 0.65, textDecoration: "none" }}
            onMouseEnter={(e) => ((e.currentTarget as HTMLAnchorElement).style.opacity = "1")}
            onMouseLeave={(e) => ((e.currentTarget as HTMLAnchorElement).style.opacity = "0.65")}
          >
            {competitor.domain} ↗
          </a>
        </div>
      </div>

      {/* Why competitor — 2 line clamp */}
      <div
        style={{
          fontSize: font.small,               // 13px — was 11px, fixed
          color: color.muted,
          lineHeight: 1.5,
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {competitor.why_competitor}
      </div>
    </div>
  );
}
