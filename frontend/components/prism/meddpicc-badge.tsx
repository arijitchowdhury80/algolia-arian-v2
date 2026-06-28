/**
 * MeddpiccBadge — colour-coded MEDDPICC buyer role pill.
 *
 * Sora only loads 300/400/600. fontWeight is 600 (semibold).
 * Minimum font size is 12px per Algolia guidelines.
 */
import { font } from "@/lib/tokens";
import type { MeddpiccRole } from "@/lib/types";

export const MEDDPICC_CONFIG: Record<
  MeddpiccRole,
  { abbr: string; label: string; color: string; bg: string; border: string }
> = {
  economic_buyer: {
    abbr: "EB",
    label: "Economic Buyer",
    color: "#F59E0B",
    bg: "rgba(245,158,11,0.12)",
    border: "rgba(245,158,11,0.30)",
  },
  champion: {
    abbr: "CH",
    label: "Champion",
    color: "#22C55E",
    bg: "rgba(34,197,94,0.10)",
    border: "rgba(34,197,94,0.25)",
  },
  technical_buyer: {
    abbr: "TB",
    label: "Technical Buyer",
    color: "#3B82F6",
    bg: "rgba(59,130,246,0.10)",
    border: "rgba(59,130,246,0.25)",
  },
  influencer: {
    abbr: "INF",
    label: "Influencer",
    color: "#A855F7",
    bg: "rgba(168,85,247,0.10)",
    border: "rgba(168,85,247,0.25)",
  },
  end_user: {
    abbr: "EU",
    label: "End User",
    color: "#6B7280",
    bg: "rgba(107,114,128,0.10)",
    border: "rgba(107,114,128,0.25)",
  },
};

export const MEDDPICC_SORT_ORDER: MeddpiccRole[] = [
  "economic_buyer",
  "champion",
  "technical_buyer",
  "influencer",
  "end_user",
];

interface MeddpiccBadgeProps {
  role: MeddpiccRole | null;
}

export function MeddpiccBadge({ role }: MeddpiccBadgeProps) {
  if (!role) return null;
  const cfg = MEDDPICC_CONFIG[role];

  return (
    <span
      title={cfg.label}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        borderRadius: "6px",
        padding: "3px 8px",
        fontSize: font.caption,   // 12px — Algolia minimum
        fontWeight: font.weight.semibold,
        textTransform: "uppercase",
        letterSpacing: "0.10em",
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        color: cfg.color,
        whiteSpace: "nowrap",
        cursor: "default",
        userSelect: "none",
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: cfg.color,
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      {cfg.abbr}
    </span>
  );
}
