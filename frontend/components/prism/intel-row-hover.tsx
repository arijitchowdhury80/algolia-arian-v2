/**
 * IntelRowHover — ranked executive list with hover choreography.
 * Hover: row brightens, MEDDPICC-coloured left border, LinkedIn fades in.
 * Other rows dim to 45% opacity.
 *
 * Tokens: font.label (14px names), font.small (13px secondary), font.caption (12px min)
 * Sort: MEDDPICC priority — EB → CH → TB → INF → EU
 */
"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { MeddpiccBadge, MEDDPICC_CONFIG, MEDDPICC_SORT_ORDER } from "./meddpicc-badge";
import { font, color, radius } from "@/lib/tokens";
import type { ExecutiveSeed, MeddpiccRole } from "@/lib/types";

interface IntelRowHoverProps {
  executives: ExecutiveSeed[];
  defaultVisible?: number;
}

function sortExecutives(execs: ExecutiveSeed[]): ExecutiveSeed[] {
  return [...execs].sort((a, b) => {
    const ai = a.role_classification
      ? MEDDPICC_SORT_ORDER.indexOf(a.role_classification)
      : MEDDPICC_SORT_ORDER.length;
    const bi = b.role_classification
      ? MEDDPICC_SORT_ORDER.indexOf(b.role_classification)
      : MEDDPICC_SORT_ORDER.length;
    return ai - bi;
  });
}

export function IntelRowHover({ executives, defaultVisible = 5 }: IntelRowHoverProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [showAll, setShowAll]           = useState(false);

  const sorted     = sortExecutives(executives);
  const visible    = showAll ? sorted : sorted.slice(0, defaultVisible);
  const hiddenCount = Math.max(0, sorted.length - defaultVisible);

  if (executives.length === 0) {
    return (
      <div style={{ padding: "24px", textAlign: "center", color: color.ghost, fontSize: font.small }}>
        No leadership data available
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div
        style={{
          fontSize: font.small,            // 13px — was 11px
          color: color.ghost,
          fontStyle: "italic",
          textAlign: "right",
          marginBottom: 8,
        }}
      >
        {executives.length} contact{executives.length !== 1 ? "s" : ""} identified · public sources only
      </div>

      {/* Row list */}
      <div style={{ borderRadius: radius.lg, overflow: "hidden", border: `1px solid ${color.divider}` }}>
        <AnimatePresence initial={false}>
          {visible.map((exec, i) => {
            const isHovered  = hoveredIndex === i;
            const isDimmed   = hoveredIndex !== null && !isHovered;
            const badgeColor = exec.role_classification
              ? MEDDPICC_CONFIG[exec.role_classification].color
              : "transparent";

            return (
              <motion.div
                key={exec.full_name}
                layout
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: isDimmed ? 0.45 : 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.2 }}
                onMouseEnter={() => setHoveredIndex(i)}
                onMouseLeave={() => setHoveredIndex(null)}
                style={{
                  display: "grid",
                  gridTemplateColumns: "90px 1fr auto",
                  alignItems: "center",
                  padding: "14px 18px",
                  gap: 16,
                  borderBottom: i < visible.length - 1 ? `1px solid ${color.dividerSoft}` : "none",
                  borderLeft: `3px solid ${isHovered ? badgeColor : "transparent"}`,
                  background: isHovered ? color.glass.bgHover : color.glass.bgRow,
                  transition: "background 200ms ease, border-left-color 200ms ease",
                  cursor: "default",
                }}
              >
                {/* Badge */}
                <div><MeddpiccBadge role={exec.role_classification} /></div>

                {/* Identity */}
                <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                  <div
                    style={{
                      fontSize: font.label,      // 14px
                      fontWeight: font.weight.semibold,
                      color: color.navy,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {exec.full_name}
                  </div>
                  <div style={{ fontSize: font.small, fontWeight: font.weight.regular, color: color.muted }}>
                    {exec.title}
                  </div>
                  <div style={{ fontSize: font.small, color: color.ghost, display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {exec.tenure_description && <span>{exec.tenure_description}</span>}
                    {exec.previous_company    && <span>· Prev: {exec.previous_company}</span>}
                  </div>
                </div>

                {/* LinkedIn */}
                <motion.div
                  animate={{ opacity: isHovered ? 1 : 0, x: isHovered ? 0 : 4 }}
                  transition={{ duration: 0.18 }}
                >
                  {exec.linkedin_url && (
                    <a
                      href={exec.linkedin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={`${exec.full_name} on LinkedIn`}
                      style={{
                        width: 28,
                        height: 28,
                        borderRadius: radius.sm,
                        background: color.linkedin.bg,
                        border: `1px solid ${color.linkedin.border}`,
                        color: color.linkedin.text,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: font.caption,    // 12px
                        fontWeight: font.weight.semibold,
                        textDecoration: "none",
                      }}
                    >
                      in
                    </a>
                  )}
                </motion.div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* Show more / less */}
      {hiddenCount > 0 && (
        <button
          onClick={() => setShowAll((v) => !v)}
          style={{
            marginTop: 8,
            fontSize: font.small,            // 13px
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
