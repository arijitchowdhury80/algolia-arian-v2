/**
 * StatChipGrid — 4-column responsive grid of metric chips.
 * Each chip: icon → label → value → source provenance.
 *
 * Tokens: font.caption (12px min), font.small (13px), color.muted, color.ghost
 */
import { font, color, radius } from "@/lib/tokens";

interface StatChip {
  icon: string;
  label: string;
  value: string;
  source?: string;
}

interface StatChipGridProps {
  chips: StatChip[];
}

export function StatChipGrid({ chips }: StatChipGridProps) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: "12px 16px",
      }}
    >
      {chips.map((chip, i) => (
        <div
          key={i}
          style={{
            background: "rgba(255,255,255,0.60)",
            backdropFilter: "blur(8px)",
            WebkitBackdropFilter: "blur(8px)",
            border: `1px solid ${color.divider}`,
            borderRadius: radius.lg,
            padding: "14px 16px",
            display: "flex",
            flexDirection: "column",
            gap: 4,
          }}
        >
          <div style={{ fontSize: "18px", marginBottom: 6, lineHeight: 1 }}>
            {chip.icon}
          </div>
          <div
            style={{
              fontSize: font.caption,        // 12px
              fontWeight: font.weight.semibold,
              textTransform: "uppercase",
              letterSpacing: "0.10em",
              color: color.muted,
            }}
          >
            {chip.label}
          </div>
          <div
            style={{
              fontSize: font.statValue,      // 20px (UI-specific, between h5/h4)
              fontWeight: font.weight.semibold,
              color: color.navy,
              letterSpacing: "-0.3px",
              lineHeight: 1.2,
            }}
          >
            {chip.value}
          </div>
          {chip.source && (
            <div
              style={{
                fontSize: font.caption,      // 12px — was 9px, violation fixed
                fontWeight: font.weight.regular,
                color: color.ghost,
                fontStyle: "italic",
                marginTop: 2,
              }}
            >
              {chip.source}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
