# Company Intel UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the minimal `company-card.tsx` with a full 5-layer Company Intelligence section rendering all fields from the `intel-company` v2 module output.

**Architecture:** 8 focused component files compose into `CompanyIntelCard`. The root card is always-open at the top of the Research Tab (not a collapsible). Layers follow the narrative structure: Identity Anchor → WHO ARE THEY → WHO'S IN CHARGE → THEIR FOOTPRINT → ONLINE PRESENCE.

**Tech Stack:** Next.js 15, React 19, TypeScript 5, Tailwind CSS 4, Framer Motion 12, Lucide React, `@number-flow/react`

**Design spec:** `docs/superpowers/specs/2026-04-14-company-intel-ui-design.md`

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| **Modify** | `frontend/lib/types.ts` | Add `CompanyIntelOutput`, `ExecutiveSeed`, `SubsidiarySeed`, `CompetitorSeed` types |
| **Create** | `frontend/components/prism/narrative-layer.tsx` | Section divider label — "WHO ARE THEY?" etc |
| **Create** | `frontend/components/prism/meddpicc-badge.tsx` | Colour-coded MEDDPICC role badge + sort constants |
| **Create** | `frontend/components/prism/grid-pattern-bg.tsx` | SVG grid texture for dark cards |
| **Create** | `frontend/components/prism/identity-anchor.tsx` | Layer 0 — dark hero card: logo, name, badges, stats |
| **Create** | `frontend/components/prism/stat-chip-grid.tsx` | Layer 1 — 4-column stat chip grid |
| **Create** | `frontend/components/prism/intel-row-hover.tsx` | Layer 2 — executive list with hover choreography |
| **Create** | `frontend/components/prism/brand-portfolio-tree.tsx` | Layer 3 left — parent → subsidiary tree |
| **Create** | `frontend/components/prism/competitor-card-grid.tsx` | Layer 3 right — competitor feature card grid |
| **Create** | `frontend/components/prism/company-intel-card.tsx` | Root assembler — composes all layers |
| **Modify** | `frontend/components/dashboard/tabs/research-tab.tsx` | Render `CompanyIntelCard` always-open at top; other modules remain collapsible below |
| **Keep (unused)** | `frontend/components/prism/company-card.tsx` | Deprecated — do not delete, do not use |

---

## Task 1: Add types to `frontend/lib/types.ts`

**Files:**
- Modify: `frontend/lib/types.ts` (append at end of file)

- [ ] **Step 1: Append the new types**

Add to the end of `frontend/lib/types.ts`:

```typescript
/* ── Company Intel v2 (intel-company module output) ── */

export type MeddpiccRole =
  | "economic_buyer"
  | "technical_buyer"
  | "champion"
  | "influencer"
  | "end_user";

export interface ExecutiveSeed {
  full_name: string;
  title: string;
  role_classification: MeddpiccRole | null;
  linkedin_url: string | null;
  tenure_description: string | null;
  previous_company: string | null;
}

export interface SubsidiarySeed {
  name: string;
  domain: string | null;
  description: string | null;
}

export interface CompetitorSeed {
  company_name: string;
  domain: string;
  why_competitor: string;
  ticker: string | null;
  linkedin_url: string | null;
}

export interface CompanyIntelOutput {
  // Identity
  legal_name: string;
  common_name: string;
  domain: string;
  headquarters: string;
  employee_count: number | null;
  employee_count_source: string | null;
  year_founded: number | null;
  business_model: string;
  // Classification
  industry: string;
  sub_vertical: string | null;
  is_public: boolean;
  ticker: string | null;
  parent_company: string | null;
  parent_domain: string | null;
  revenue_estimate: number | null;
  revenue_source: string | null;
  // Brand portfolio
  subsidiaries: SubsidiarySeed[];
  // People & competitors
  executives: ExecutiveSeed[];
  competitors: CompetitorSeed[];
  // Website snapshot
  product_categories: string[];
  company_linkedin_url: string | null;
  twitter_handle: string | null;
  youtube_url: string | null;
  recent_headline: string | null;
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```
Expected: no errors (or only pre-existing errors unrelated to the new types).

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/types.ts
git commit -m "feat(types): add CompanyIntelOutput and related types for intel-company v2"
```

---

## Task 2: NarrativeLayer component

**Files:**
- Create: `frontend/components/prism/narrative-layer.tsx`

- [ ] **Step 1: Create the file**

```tsx
// frontend/components/prism/narrative-layer.tsx

interface NarrativeLayerProps {
  label: string;
}

export function NarrativeLayer({ label }: NarrativeLayerProps) {
  return (
    <div className="flex items-center gap-3 my-2">
      <div className="flex-1 h-px bg-black/[0.09]" />
      <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-gray-400 px-1 select-none whitespace-nowrap">
        {label}
      </span>
      <div className="flex-1 h-px bg-black/[0.09]" />
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```
Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/prism/narrative-layer.tsx
git commit -m "feat(ui): add NarrativeLayer section divider component"
```

---

## Task 3: MeddpiccBadge component

**Files:**
- Create: `frontend/components/prism/meddpicc-badge.tsx`

- [ ] **Step 1: Create the file**

```tsx
// frontend/components/prism/meddpicc-badge.tsx
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
        borderRadius: 6,
        padding: "3px 8px",
        fontSize: 10,
        fontWeight: 700,
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
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```
Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/prism/meddpicc-badge.tsx
git commit -m "feat(ui): add MeddpiccBadge colour-coded role badge component"
```

---

## Task 4: GridPatternBg component

**Files:**
- Create: `frontend/components/prism/grid-pattern-bg.tsx`

- [ ] **Step 1: Create the file**

```tsx
// frontend/components/prism/grid-pattern-bg.tsx
"use client";

import { useId } from "react";

function genRandomPattern(length = 5): number[][] {
  return Array.from({ length }, () => [
    Math.floor(Math.random() * 4) + 7,
    Math.floor(Math.random() * 6) + 1,
  ]);
}

export function GridPatternBg() {
  const patternId = useId();
  const squares = genRandomPattern(5);

  return (
    <div
      className="pointer-events-none absolute inset-0"
      style={{
        maskImage: "linear-gradient(white, transparent)",
        WebkitMaskImage: "linear-gradient(white, transparent)",
        zIndex: 1,
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(to right, rgba(255,255,255,0.03), rgba(255,255,255,0.01))",
          maskImage:
            "radial-gradient(farthest-side at top, white, transparent)",
          WebkitMaskImage:
            "radial-gradient(farthest-side at top, white, transparent)",
        }}
      >
        <svg
          aria-hidden="true"
          className="absolute inset-0 h-full w-full"
          style={{
            fill: "rgba(255,255,255,0.05)",
            stroke: "rgba(255,255,255,0.20)",
            mixBlendMode: "overlay",
          }}
        >
          <defs>
            <pattern
              id={patternId}
              width={20}
              height={20}
              patternUnits="userSpaceOnUse"
              x="-12"
              y="4"
            >
              <path d="M.5 20V.5H20" fill="none" />
            </pattern>
          </defs>
          <rect
            width="100%"
            height="100%"
            strokeWidth={0}
            fill={`url(#${patternId})`}
          />
          <svg x="-12" y="4" className="overflow-visible">
            {squares.map(([x, y], i) => (
              <rect
                key={i}
                strokeWidth={0}
                width={21}
                height={21}
                x={x * 20}
                y={y * 20}
              />
            ))}
          </svg>
        </svg>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/prism/grid-pattern-bg.tsx
git commit -m "feat(ui): add GridPatternBg SVG texture for dark cards"
```

---

## Task 5: IdentityAnchor component

**Files:**
- Create: `frontend/components/prism/identity-anchor.tsx`

- [ ] **Step 1: Create the file**

```tsx
// frontend/components/prism/identity-anchor.tsx
"use client";

import { useState } from "react";
import { GridPatternBg } from "./grid-pattern-bg";
import type { CompanyIntelOutput } from "@/lib/types";

function formatRevenue(value: number): string {
  if (value >= 1e12) return `~$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `~$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `~$${(value / 1e6).toFixed(0)}M`;
  return `~$${value.toLocaleString()}`;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

interface IdentityAnchorProps {
  output: CompanyIntelOutput;
}

const BADGE_BASE: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 5,
  background: "rgba(255,255,255,0.08)",
  border: "1px solid rgba(255,255,255,0.14)",
  borderRadius: 20,
  padding: "4px 12px",
  fontSize: 12,
  fontWeight: 500,
  color: "rgba(255,255,255,0.80)",
};

const STAT_LABEL: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.10em",
  color: "rgba(255,255,255,0.40)",
};

const STAT_SOURCE: React.CSSProperties = {
  fontSize: 10,
  color: "rgba(255,255,255,0.28)",
  fontStyle: "italic",
};

export function IdentityAnchor({ output }: IdentityAnchorProps) {
  const [logoError, setLogoError] = useState(false);
  const companyName = output.common_name || output.legal_name;
  const initials = getInitials(companyName);
  const yearsSince = output.year_founded
    ? new Date().getFullYear() - output.year_founded
    : null;

  return (
    <div
      className="relative overflow-hidden rounded-2xl"
      style={{
        background:
          "linear-gradient(135deg, #0d1b38 0%, #1a2d52 55%, #13244a 100%)",
        border: "1px solid rgba(255,255,255,0.09)",
        boxShadow:
          "0 4px 24px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.06)",
      }}
    >
      <GridPatternBg />

      {/* Parent company banner */}
      {output.parent_company && (
        <div
          style={{
            position: "relative",
            zIndex: 3,
            padding: "8px 28px",
            background: "rgba(255,165,0,0.08)",
            borderBottom: "1px solid rgba(255,165,0,0.15)",
            fontSize: 11,
            color: "rgba(255,210,100,0.85)",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <span style={{ opacity: 0.6 }}>Subsidiary of:</span>
          <span style={{ fontWeight: 600 }}>{output.parent_company}</span>
          {output.parent_domain && (
            <a
              href={`https://${output.parent_domain}`}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: "rgba(255,210,100,0.70)",
                fontSize: 10,
                textDecoration: "none",
              }}
            >
              {output.parent_domain} ↗
            </a>
          )}
        </div>
      )}

      {/* Two-column grid */}
      <div
        style={{
          position: "relative",
          zIndex: 3,
          display: "grid",
          gridTemplateColumns: "55fr 45fr",
        }}
      >
        {/* Left: Identity */}
        <div
          style={{
            padding: "28px 30px",
            borderRight: "1px solid rgba(255,255,255,0.09)",
          }}
        >
          {/* Logo / initials */}
          <div style={{ marginBottom: 14 }}>
            {!logoError ? (
              <div
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: 12,
                  overflow: "hidden",
                  background: "white",
                  border: "1px solid rgba(255,255,255,0.15)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <img
                  src={`https://logo.clearbit.com/${output.domain}`}
                  alt={`${companyName} logo`}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "contain",
                    padding: 4,
                  }}
                  onError={() => setLogoError(true)}
                />
              </div>
            ) : (
              <div
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: 12,
                  background: "#003DFF",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 20,
                  fontWeight: 700,
                  color: "white",
                }}
              >
                {initials}
              </div>
            )}
          </div>

          {/* Eyebrow */}
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.13em",
              color: "rgba(255,255,255,0.45)",
              marginBottom: 8,
            }}
          >
            {output.sub_vertical || output.industry}
          </div>

          {/* Name */}
          <div
            style={{
              fontSize: 26,
              fontWeight: 800,
              color: "#ffffff",
              letterSpacing: "-0.5px",
              lineHeight: 1.15,
              marginBottom: 16,
            }}
          >
            {companyName}
          </div>

          {/* Badge pills */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {output.headquarters && (
              <span style={BADGE_BASE}>📍 {output.headquarters}</span>
            )}
            {output.year_founded && (
              <span style={BADGE_BASE}>📅 Est. {output.year_founded}</span>
            )}
            {output.employee_count && (
              <span style={BADGE_BASE}>
                👥 {output.employee_count.toLocaleString()} employees
              </span>
            )}
            {output.is_public && output.ticker ? (
              <span
                style={{
                  ...BADGE_BASE,
                  background: "rgba(255,213,0,0.12)",
                  border: "1px solid rgba(255,213,0,0.25)",
                  color: "#FFD500",
                  fontWeight: 600,
                }}
              >
                🏢 Public · {output.ticker}
              </span>
            ) : (
              <span style={BADGE_BASE}>🏢 Private</span>
            )}
          </div>
        </div>

        {/* Right: Stats 2×2 */}
        <div
          style={{
            padding: "28px 30px",
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "20px 24px",
            alignContent: "start",
          }}
        >
          {output.revenue_estimate != null && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 700,
                  color: "#ffffff",
                  letterSpacing: "-0.3px",
                }}
              >
                {formatRevenue(output.revenue_estimate)}
              </div>
              <div style={STAT_LABEL}>Revenue</div>
              {output.revenue_source && (
                <div style={STAT_SOURCE}>{output.revenue_source}</div>
              )}
            </div>
          )}
          {output.employee_count != null && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 700,
                  color: "#ffffff",
                  letterSpacing: "-0.3px",
                }}
              >
                {output.employee_count.toLocaleString()}
              </div>
              <div style={STAT_LABEL}>Employees</div>
              {output.employee_count_source && (
                <div style={STAT_SOURCE}>{output.employee_count_source}</div>
              )}
            </div>
          )}
          {output.year_founded != null && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 700,
                  color: "#ffffff",
                  letterSpacing: "-0.3px",
                }}
              >
                {output.year_founded}
              </div>
              <div style={STAT_LABEL}>Founded</div>
              {yearsSince && (
                <div style={STAT_SOURCE}>{yearsSince} years ago</div>
              )}
            </div>
          )}
          {output.headquarters && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div
                style={{
                  fontSize: 16,
                  fontWeight: 700,
                  color: "#ffffff",
                  letterSpacing: "-0.3px",
                  lineHeight: 1.2,
                }}
              >
                {output.headquarters.split(",")[0]}
              </div>
              <div style={STAT_LABEL}>Headquarters</div>
              <div style={STAT_SOURCE}>
                {output.headquarters.split(",").slice(1).join(",").trim()}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/prism/identity-anchor.tsx frontend/components/prism/grid-pattern-bg.tsx
git commit -m "feat(ui): add IdentityAnchor hero card with GridPatternBg texture"
```

---

## Task 6: StatChipGrid component

**Files:**
- Create: `frontend/components/prism/stat-chip-grid.tsx`

- [ ] **Step 1: Create the file**

```tsx
// frontend/components/prism/stat-chip-grid.tsx

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
            border: "1px solid rgba(0,0,0,0.07)",
            borderRadius: 12,
            padding: "14px 16px",
            display: "flex",
            flexDirection: "column",
            gap: 4,
          }}
        >
          <div style={{ fontSize: 18, marginBottom: 6, lineHeight: 1 }}>
            {chip.icon}
          </div>
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.10em",
              color: "#6B7280",
            }}
          >
            {chip.label}
          </div>
          <div
            style={{
              fontSize: 17,
              fontWeight: 700,
              color: "#23263B",
              letterSpacing: "-0.3px",
              lineHeight: 1.2,
            }}
          >
            {chip.value}
          </div>
          {chip.source && (
            <div
              style={{
                fontSize: 9,
                fontWeight: 500,
                color: "#9CA3AF",
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
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/prism/stat-chip-grid.tsx
git commit -m "feat(ui): add StatChipGrid 4-column metric display component"
```

---

## Task 7: IntelRowHover component (executive list)

**Files:**
- Create: `frontend/components/prism/intel-row-hover.tsx`

- [ ] **Step 1: Create the file**

```tsx
// frontend/components/prism/intel-row-hover.tsx
"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  MeddpiccBadge,
  MEDDPICC_CONFIG,
  MEDDPICC_SORT_ORDER,
} from "./meddpicc-badge";
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

export function IntelRowHover({
  executives,
  defaultVisible = 5,
}: IntelRowHoverProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [showAll, setShowAll] = useState(false);

  const sorted = sortExecutives(executives);
  const visible = showAll ? sorted : sorted.slice(0, defaultVisible);
  const hiddenCount = sorted.length - defaultVisible;

  if (executives.length === 0) {
    return (
      <div
        style={{
          padding: "24px",
          textAlign: "center",
          color: "#9CA3AF",
          fontSize: 13,
        }}
      >
        No leadership data available
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div
        style={{
          fontSize: 11,
          color: "#9CA3AF",
          fontStyle: "italic",
          textAlign: "right",
          marginBottom: 8,
        }}
      >
        {executives.length} contacts identified · public sources only
      </div>

      {/* Row list */}
      <div
        style={{
          borderRadius: 12,
          overflow: "hidden",
          border: "1px solid rgba(0,0,0,0.07)",
        }}
      >
        <AnimatePresence initial={false}>
          {visible.map((exec, i) => {
            const isHovered = hoveredIndex === i;
            const isDimmed = hoveredIndex !== null && !isHovered;
            const badgeColor =
              exec.role_classification
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
                  borderBottom:
                    i < visible.length - 1
                      ? "1px solid rgba(0,0,0,0.05)"
                      : "none",
                  borderLeft: `3px solid ${isHovered ? badgeColor : "transparent"}`,
                  background: isHovered
                    ? "rgba(255,255,255,0.90)"
                    : "rgba(255,255,255,0.55)",
                  transition: "background 200ms ease, border-left-color 200ms ease",
                  cursor: "default",
                }}
              >
                {/* Badge */}
                <div>
                  <MeddpiccBadge role={exec.role_classification} />
                </div>

                {/* Identity */}
                <div
                  style={{ display: "flex", flexDirection: "column", gap: 3 }}
                >
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: 600,
                      color: "#23263B",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {exec.full_name}
                  </div>
                  <div style={{ fontSize: 12, fontWeight: 500, color: "#6B7280" }}>
                    {exec.title}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: "#9CA3AF",
                      display: "flex",
                      gap: 8,
                    }}
                  >
                    {exec.tenure_description && (
                      <span>{exec.tenure_description}</span>
                    )}
                    {exec.previous_company && (
                      <span>· Prev: {exec.previous_company}</span>
                    )}
                  </div>
                </div>

                {/* LinkedIn action */}
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
                        borderRadius: 6,
                        background: "rgba(0,119,181,0.10)",
                        border: "1px solid rgba(0,119,181,0.20)",
                        color: "#0077B5",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 13,
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
            fontSize: 12,
            fontWeight: 600,
            color: "#003DFF",
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: "6px 0",
            opacity: 0.75,
          }}
          onMouseEnter={(e) =>
            ((e.currentTarget as HTMLButtonElement).style.opacity = "1")
          }
          onMouseLeave={(e) =>
            ((e.currentTarget as HTMLButtonElement).style.opacity = "0.75")
          }
        >
          {showAll ? "↑ Show less" : `↓ Show ${hiddenCount} more`}
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/prism/intel-row-hover.tsx
git commit -m "feat(ui): add IntelRowHover executive list with MEDDPICC hover choreography"
```

---

## Task 8: BrandPortfolioTree component

**Files:**
- Create: `frontend/components/prism/brand-portfolio-tree.tsx`

- [ ] **Step 1: Create the file**

```tsx
// frontend/components/prism/brand-portfolio-tree.tsx
import type { SubsidiarySeed } from "@/lib/types";

interface BrandPortfolioTreeProps {
  subsidiaries: SubsidiarySeed[];
  auditDomain: string;
  parentCompany: string | null;
}

export function BrandPortfolioTree({
  subsidiaries,
  auditDomain,
  parentCompany,
}: BrandPortfolioTreeProps) {
  if (subsidiaries.length === 0) {
    return (
      <div style={{ fontSize: 12, color: "#9CA3AF", fontStyle: "italic" }}>
        No distinct sub-brands identified
      </div>
    );
  }

  const portfolioText =
    subsidiaries.length === 1
      ? "1 additional brand alongside the audit domain"
      : `${subsidiaries.length + 1}-brand portfolio = ${subsidiaries.length + 1}× search optimization surface`;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {/* Parent entity label */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          paddingBottom: 10,
          fontSize: 11,
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.10em",
          color: "#6B7280",
        }}
      >
        <span
          style={{
            background: "rgba(0,0,0,0.05)",
            border: "1px solid rgba(0,0,0,0.09)",
            borderRadius: 6,
            padding: "3px 8px",
            fontSize: 10,
          }}
        >
          {parentCompany ?? "Holding Company"}
        </span>
      </div>

      {/* Tree */}
      <div style={{ position: "relative", paddingLeft: 20 }}>
        {/* Vertical connector */}
        <div
          style={{
            position: "absolute",
            left: 8,
            top: 0,
            bottom: 24,
            width: 1,
            background: "rgba(0,0,0,0.12)",
          }}
        />

        {/* Audit domain row (always first) */}
        {[
          { name: auditDomain.split(".")[0], domain: auditDomain, isAudit: true },
          ...subsidiaries.map((s) => ({
            name: s.name,
            domain: s.domain,
            isAudit: false,
          })),
        ].map((brand, i, arr) => (
          <div
            key={brand.name}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "10px 0",
              position: "relative",
              borderBottom:
                i < arr.length - 1
                  ? "1px solid rgba(0,0,0,0.05)"
                  : "none",
            }}
          >
            {/* Horizontal connector */}
            <div
              style={{
                position: "absolute",
                left: 0,
                top: "50%",
                width: 16,
                height: 1,
                background: "rgba(0,0,0,0.12)",
              }}
            />

            {/* Avatar */}
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: "rgba(0,61,255,0.08)",
                border: "1px solid rgba(0,61,255,0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 12,
                fontWeight: 700,
                color: "#003DFF",
                flexShrink: 0,
                textTransform: "uppercase",
              }}
            >
              {brand.name[0]}
            </div>

            {/* Name + domain */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 600,
                  color: "#23263B",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  flexWrap: "wrap",
                }}
              >
                {brand.name}
                {brand.isAudit && (
                  <span
                    style={{
                      background: "rgba(0,61,255,0.10)",
                      border: "1px solid rgba(0,61,255,0.20)",
                      borderRadius: 4,
                      padding: "2px 7px",
                      fontSize: 9,
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.10em",
                      color: "#003DFF",
                    }}
                  >
                    THIS AUDIT
                  </span>
                )}
              </div>
              {brand.domain && (
                <a
                  href={`https://${brand.domain}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    fontSize: 12,
                    color: "#003DFF",
                    textDecoration: "none",
                    opacity: 0.65,
                  }}
                  onMouseEnter={(e) =>
                    ((e.currentTarget as HTMLAnchorElement).style.opacity = "1")
                  }
                  onMouseLeave={(e) =>
                    ((e.currentTarget as HTMLAnchorElement).style.opacity = "0.65")
                  }
                >
                  {brand.domain} ↗
                </a>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Portfolio opportunity callout */}
      {subsidiaries.length >= 2 && (
        <div
          style={{
            marginTop: 16,
            padding: "12px 14px",
            background: "rgba(234,179,8,0.08)",
            border: "1px solid rgba(234,179,8,0.20)",
            borderRadius: 10,
            display: "flex",
            alignItems: "flex-start",
            gap: 10,
          }}
        >
          <span style={{ fontSize: 16 }}>💡</span>
          <div>
            <div
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: "#92400E",
                marginBottom: 2,
              }}
            >
              Portfolio Opportunity
            </div>
            <div style={{ fontSize: 12, color: "#78350F", lineHeight: 1.5 }}>
              {portfolioText}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/prism/brand-portfolio-tree.tsx
git commit -m "feat(ui): add BrandPortfolioTree subsidiary hierarchy component"
```

---

## Task 9: CompetitorCardGrid component

**Files:**
- Create: `frontend/components/prism/competitor-card-grid.tsx`

- [ ] **Step 1: Create the file**

```tsx
// frontend/components/prism/competitor-card-grid.tsx
"use client";

import { useState } from "react";
import type { CompetitorSeed } from "@/lib/types";

interface CompetitorCardGridProps {
  competitors: CompetitorSeed[];
  defaultVisible?: number;
}

export function CompetitorCardGrid({
  competitors,
  defaultVisible = 4,
}: CompetitorCardGridProps) {
  const [showAll, setShowAll] = useState(false);

  if (competitors.length === 0) {
    return (
      <div style={{ fontSize: 12, color: "#9CA3AF", fontStyle: "italic" }}>
        No competitor data available
      </div>
    );
  }

  const visible = showAll ? competitors : competitors.slice(0, defaultVisible);
  const hiddenCount = competitors.length - defaultVisible;

  return (
    <div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: 10,
        }}
      >
        {visible.map((comp) => (
          <CompetitorCard key={comp.company_name} competitor={comp} />
        ))}
      </div>

      {hiddenCount > 0 && (
        <button
          onClick={() => setShowAll((v) => !v)}
          style={{
            marginTop: 8,
            fontSize: 12,
            fontWeight: 600,
            color: "#003DFF",
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: "6px 0",
            opacity: 0.75,
          }}
          onMouseEnter={(e) =>
            ((e.currentTarget as HTMLButtonElement).style.opacity = "1")
          }
          onMouseLeave={(e) =>
            ((e.currentTarget as HTMLButtonElement).style.opacity = "0.75")
          }
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
        border: "1px solid rgba(0,0,0,0.07)",
        borderRadius: 12,
        padding: "14px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        transform: hovered ? "translateY(-3px)" : "translateY(0)",
        boxShadow: hovered
          ? "0 6px 20px rgba(0,0,0,0.10)"
          : "0 1px 3px rgba(0,0,0,0.04)",
        transition: "transform 200ms ease, box-shadow 200ms ease",
        cursor: "default",
      }}
    >
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: "rgba(0,61,255,0.08)",
            border: "1px solid rgba(0,61,255,0.12)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 13,
            fontWeight: 700,
            color: "#003DFF",
            flexShrink: 0,
            textTransform: "uppercase",
          }}
        >
          {competitor.company_name[0]}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "#23263B",
              lineHeight: 1.2,
            }}
          >
            {competitor.company_name}
          </div>
          <a
            href={`https://${competitor.domain}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              fontSize: 11,
              color: "#003DFF",
              opacity: 0.65,
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: 2,
            }}
            onMouseEnter={(e) =>
              ((e.currentTarget as HTMLAnchorElement).style.opacity = "1")
            }
            onMouseLeave={(e) =>
              ((e.currentTarget as HTMLAnchorElement).style.opacity = "0.65")
            }
          >
            {competitor.domain} ↗
          </a>
        </div>
      </div>

      {/* Why competitor */}
      <div
        style={{
          fontSize: 11,
          color: "#6B7280",
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
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/prism/competitor-card-grid.tsx
git commit -m "feat(ui): add CompetitorCardGrid atomic competitor card component"
```

---

## Task 10: CompanyIntelCard root assembler

**Files:**
- Create: `frontend/components/prism/company-intel-card.tsx`

- [ ] **Step 1: Create the file**

```tsx
// frontend/components/prism/company-intel-card.tsx
"use client";

import { useState } from "react";
import type { ModuleResult, CompanyIntelOutput } from "@/lib/types";
import { IdentityAnchor } from "./identity-anchor";
import { NarrativeLayer } from "./narrative-layer";
import { StatChipGrid } from "./stat-chip-grid";
import { IntelRowHover } from "./intel-row-hover";
import { BrandPortfolioTree } from "./brand-portfolio-tree";
import { CompetitorCardGrid } from "./competitor-card-grid";

function castOutput(raw: Record<string, unknown>): CompanyIntelOutput {
  return {
    legal_name: (raw.legal_name as string) ?? "",
    common_name: (raw.common_name as string) ?? "",
    domain: (raw.domain as string) ?? "",
    headquarters: (raw.headquarters as string) ?? "",
    employee_count: (raw.employee_count as number | null) ?? null,
    employee_count_source: (raw.employee_count_source as string | null) ?? null,
    year_founded: (raw.year_founded as number | null) ?? null,
    business_model: (raw.business_model as string) ?? "",
    industry: (raw.industry as string) ?? "",
    sub_vertical: (raw.sub_vertical as string | null) ?? null,
    is_public: (raw.is_public as boolean) ?? false,
    ticker: (raw.ticker as string | null) ?? null,
    parent_company: (raw.parent_company as string | null) ?? null,
    parent_domain: (raw.parent_domain as string | null) ?? null,
    revenue_estimate: (raw.revenue_estimate as number | null) ?? null,
    revenue_source: (raw.revenue_source as string | null) ?? null,
    subsidiaries: (raw.subsidiaries as CompanyIntelOutput["subsidiaries"]) ?? [],
    executives: (raw.executives as CompanyIntelOutput["executives"]) ?? [],
    competitors: (raw.competitors as CompanyIntelOutput["competitors"]) ?? [],
    product_categories: (raw.product_categories as string[]) ?? [],
    company_linkedin_url: (raw.company_linkedin_url as string | null) ?? null,
    twitter_handle: (raw.twitter_handle as string | null) ?? null,
    youtube_url: (raw.youtube_url as string | null) ?? null,
    recent_headline: (raw.recent_headline as string | null) ?? null,
  };
}

const GLASS_CARD: React.CSSProperties = {
  background: "rgba(255,255,255,0.72)",
  backdropFilter: "blur(20px)",
  WebkitBackdropFilter: "blur(20px)",
  border: "1px solid rgba(255,255,255,0.85)",
  borderRadius: 20,
  padding: "24px 28px",
  boxShadow:
    "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.95)",
};

interface CompanyIntelCardProps {
  data: ModuleResult;
}

export function CompanyIntelCard({ data }: CompanyIntelCardProps) {
  const [bioExpanded, setBioExpanded] = useState(false);
  const output = castOutput(data.output);

  const yearsSince = output.year_founded
    ? new Date().getFullYear() - output.year_founded
    : null;

  // Build stat chips for Layer 1
  const statChips = [
    output.revenue_estimate != null
      ? {
          icon: "💰",
          label: "Revenue",
          value: formatRevenue(output.revenue_estimate),
          source: output.revenue_source ?? undefined,
        }
      : null,
    output.employee_count != null
      ? {
          icon: "👥",
          label: "Employees",
          value: output.employee_count.toLocaleString(),
          source: output.employee_count_source ?? undefined,
        }
      : null,
    output.headquarters
      ? { icon: "📍", label: "Headquarters", value: output.headquarters }
      : null,
    output.year_founded != null
      ? {
          icon: "📅",
          label: "Founded",
          value: String(output.year_founded),
          source: yearsSince ? `${yearsSince} years ago` : undefined,
        }
      : null,
  ].filter((c): c is NonNullable<typeof c> => c !== null);

  const hasFootprint =
    output.subsidiaries.length > 0 || output.competitors.length > 0;
  const hasOnlinePresence =
    output.product_categories.length > 0 ||
    output.company_linkedin_url ||
    output.twitter_handle ||
    output.youtube_url ||
    output.recent_headline;

  const socialLinks = [
    output.domain
      ? { icon: "🔗", label: output.domain, href: `https://${output.domain}` }
      : null,
    output.company_linkedin_url
      ? { icon: "in", label: "LinkedIn", href: output.company_linkedin_url }
      : null,
    output.twitter_handle
      ? {
          icon: "@",
          label: `@${output.twitter_handle}`,
          href: `https://twitter.com/${output.twitter_handle}`,
        }
      : null,
    output.youtube_url
      ? { icon: "▶", label: "YouTube", href: output.youtube_url }
      : null,
  ].filter((l): l is NonNullable<typeof l> => l !== null);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Layer 0: Identity Anchor */}
      <IdentityAnchor output={output} />

      {/* Layer 1: WHO ARE THEY? */}
      {(output.business_model || statChips.length > 0) && (
        <>
          <NarrativeLayer label="WHO ARE THEY?" />
          <div style={GLASS_CARD}>
            {output.business_model && (
              <div
                style={{
                  borderLeft: "3px solid rgba(0,61,255,0.20)",
                  paddingLeft: 16,
                  marginBottom: statChips.length > 0 ? 20 : 0,
                }}
              >
                <div
                  style={{
                    fontSize: 14,
                    color: "#374151",
                    lineHeight: 1.65,
                    display: bioExpanded ? "block" : "-webkit-box",
                    WebkitLineClamp: bioExpanded ? undefined : 3,
                    WebkitBoxOrient: "vertical",
                    overflow: bioExpanded ? "visible" : "hidden",
                  }}
                >
                  {output.business_model}
                </div>
                {output.business_model.length > 200 && (
                  <button
                    onClick={() => setBioExpanded((v) => !v)}
                    style={{
                      marginTop: 6,
                      fontSize: 12,
                      fontWeight: 600,
                      color: "#003DFF",
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      padding: 0,
                      opacity: 0.75,
                    }}
                  >
                    {bioExpanded ? "Show less" : "Read more"}
                  </button>
                )}
              </div>
            )}
            {statChips.length > 0 && <StatChipGrid chips={statChips} />}
          </div>
        </>
      )}

      {/* Layer 2: WHO'S IN CHARGE? */}
      {output.executives.length > 0 && (
        <>
          <NarrativeLayer label="WHO'S IN CHARGE?" />
          <div style={GLASS_CARD}>
            <IntelRowHover executives={output.executives} />
          </div>
        </>
      )}

      {/* Layer 3: THEIR FOOTPRINT */}
      {hasFootprint && (
        <>
          <NarrativeLayer label="THEIR FOOTPRINT" />
          <div style={{ ...GLASS_CARD, padding: 0, overflow: "hidden" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns:
                  output.subsidiaries.length > 0 && output.competitors.length > 0
                    ? "1fr 1fr"
                    : "1fr",
              }}
            >
              {output.subsidiaries.length > 0 && (
                <div
                  style={{
                    padding: "24px 24px 24px 28px",
                    borderRight:
                      output.competitors.length > 0
                        ? "1px solid rgba(0,0,0,0.07)"
                        : "none",
                  }}
                >
                  <div
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.12em",
                      color: "#6B7280",
                      marginBottom: 14,
                    }}
                  >
                    Brand Portfolio
                  </div>
                  <BrandPortfolioTree
                    subsidiaries={output.subsidiaries}
                    auditDomain={output.domain}
                    parentCompany={output.parent_company}
                  />
                </div>
              )}
              {output.competitors.length > 0 && (
                <div style={{ padding: "24px 28px 24px 24px" }}>
                  <div
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.12em",
                      color: "#6B7280",
                      marginBottom: 14,
                    }}
                  >
                    Competitors
                  </div>
                  <CompetitorCardGrid competitors={output.competitors} />
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Layer 4: ONLINE PRESENCE */}
      {hasOnlinePresence && (
        <>
          <NarrativeLayer label="ONLINE PRESENCE" />
          <div style={{ ...GLASS_CARD, background: "rgba(255,255,255,0.50)" }}>
            {output.product_categories.length > 0 && (
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 6,
                  marginBottom: socialLinks.length > 0 ? 14 : 0,
                }}
              >
                {output.product_categories.map((cat) => (
                  <span
                    key={cat}
                    style={{
                      background: "rgba(0,61,255,0.07)",
                      border: "1px solid rgba(0,61,255,0.15)",
                      borderRadius: 6,
                      padding: "3px 10px",
                      fontSize: 10,
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      color: "#003DFF",
                    }}
                  >
                    {cat}
                  </span>
                ))}
              </div>
            )}

            {socialLinks.length > 0 && (
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: output.recent_headline ? 14 : 0 }}>
                {socialLinks.map((link) => (
                  <a
                    key={link.href}
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={link.label}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "5px 12px",
                      background: "rgba(0,61,255,0.06)",
                      border: "1px solid rgba(0,61,255,0.12)",
                      borderRadius: 8,
                      fontSize: 12,
                      fontWeight: 600,
                      color: "#003DFF",
                      textDecoration: "none",
                    }}
                  >
                    <span style={{ fontSize: 13 }}>{link.icon}</span>
                    {link.label}
                  </a>
                ))}
              </div>
            )}

            {output.recent_headline && (
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 8,
                  fontSize: 12,
                  color: "#374151",
                  lineHeight: 1.5,
                  fontStyle: "italic",
                }}
              >
                <span>🗞</span>
                <span>{output.recent_headline}</span>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function formatRevenue(value: number): string {
  if (value >= 1e12) return `~$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `~$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `~$${(value / 1e6).toFixed(0)}M`;
  return `~$${value.toLocaleString()}`;
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/prism/company-intel-card.tsx
git commit -m "feat(ui): add CompanyIntelCard root assembler — 5-layer company intelligence view"
```

---

## Task 11: Wire CompanyIntelCard into ResearchTab

**Files:**
- Modify: `frontend/components/dashboard/tabs/research-tab.tsx`

- [ ] **Step 1: Read the current file first**

Read `frontend/components/dashboard/tabs/research-tab.tsx` to confirm the current SECTIONS array and CollapsibleSection structure before editing.

- [ ] **Step 2: Replace the import and add always-open section at top**

In `frontend/components/dashboard/tabs/research-tab.tsx`:

Replace:
```tsx
import { CompanyCard } from "@/components/prism/company-card";
```

With:
```tsx
import { CompanyIntelCard } from "@/components/prism/company-intel-card";
```

Remove `intel-company` from the `SECTIONS` array entirely (it will no longer be a collapsible section):
```tsx
// Remove this entry from SECTIONS:
{
  id: "company-snapshot",
  eyebrow: "COMPANY OVERVIEW",
  title: "Company Snapshot",
  moduleKeys: ["intel-company"],
  CardComponent: CompanyCard as unknown as React.ComponentType<{ data: ModuleResult }>,
},
```

In the `ResearchTab` component, add the always-open Company Intel section above the collapsible sections:

```tsx
export function ResearchTab({ results }: TabProps) {
  const highlighted = usePrismStore((s) => s.highlightedSection);
  const activeSection = usePrismStore((s) => s.activeSection);
  const companyData = results["intel-company"];

  useEffect(() => {
    if (activeSection) {
      const timer = setTimeout(() => {
        const el = document.getElementById(activeSection);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [activeSection]);

  return (
    <div className="px-6 py-8 space-y-6">
      {/* Company Intel — always open, top of page */}
      {companyData && (
        <div id="company-snapshot">
          <CompanyIntelCard data={companyData} />
        </div>
      )}

      {/* Remaining modules — collapsible */}
      {SECTIONS.map((section) => {
        const data = findModuleData(results, section.moduleKeys);
        return (
          <CollapsibleSection
            key={section.id}
            config={section}
            data={data}
            isHighlighted={highlighted === section.id}
          />
        );
      })}

      <style jsx>{`
        @keyframes highlight {
          0% { background: #fef3c7; }
          100% { background: transparent; }
        }
      `}</style>
    </div>
  );
}
```

- [ ] **Step 3: Type-check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```
Expected: no new errors.

- [ ] **Step 4: Start dev server and visually verify**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000`. Navigate to an audit with company intel data. Verify:
- Identity Anchor renders with dark gradient, logo/initials, badge pills
- WHO ARE THEY layer renders business model text + stat chips
- WHO'S IN CHARGE layer renders sorted executive rows; hover dims others and reveals LinkedIn
- THEIR FOOTPRINT renders brand portfolio tree (if subsidiaries) and competitor cards
- ONLINE PRESENCE renders categories, social links, headline

- [ ] **Step 5: Commit**

```bash
git add frontend/components/dashboard/tabs/research-tab.tsx
git commit -m "feat(ui): wire CompanyIntelCard into ResearchTab as always-open top section"
```

---

## Task 12: Final type-check and verification

- [ ] **Step 1: Full TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```
Expected: 0 errors. Fix any that appear before proceeding.

- [ ] **Step 2: Lint check**

```bash
cd /Users/arijitchowdhury/AI-Development/PIP && ruff check . 2>&1 | head -20
```
Expected: no Python errors (frontend changes don't affect Python linting).

- [ ] **Step 3: Verify in browser with mock data**

If no live audit data is available, use the mock seeder at `frontend/components/dev/mock-seeder.tsx` to inject a `ModuleResult` for `intel-company` with the `CompanyIntelOutput` shape. Verify all 5 layers render without errors.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete company intel UI — 5-layer CompanyIntelCard replacing company-card"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Identity Anchor: dark gradient, GridPattern, 55/45 split | Task 5 |
| Parent company amber banner | Task 5 |
| Logo with Clearbit fallback to initials | Task 5 |
| Stat chips (revenue, employees, HQ, founded) with source labels | Task 6 |
| Business model text with read-more | Task 10 |
| Executives sorted by MEDDPICC priority | Task 7 |
| Hover: row brightens, badge-colour left border, LinkedIn reveals | Task 7 |
| Show N more / collapse for executives | Task 7 |
| Brand portfolio tree with THIS AUDIT badge and portfolio callout | Task 8 |
| Competitor cards with hover lift and show more | Task 9 |
| Online presence: categories, social links, recent headline | Task 10 |
| Always-open at top of Research Tab (not collapsible) | Task 11 |
| Deprecated company-card.tsx kept but not used | Task 11 |
| CompanyIntelOutput type matching v2 schema | Task 1 |

**All spec requirements covered. No placeholders.**

**Type consistency check:**
- `CompanyIntelOutput` defined in Task 1, used in Tasks 5, 7, 8, 9, 10 ✓
- `ExecutiveSeed` defined in Task 1, used in Task 7 ✓
- `SubsidiarySeed` defined in Task 1, used in Task 8 ✓
- `CompetitorSeed` defined in Task 1, used in Task 9 ✓
- `MeddpiccRole` defined in Task 1, used in Tasks 3, 7 ✓
- `MEDDPICC_CONFIG` and `MEDDPICC_SORT_ORDER` exported from Task 3, imported in Task 7 ✓
- `formatRevenue` defined locally in Task 10 (not shared — intentional, used only there) ✓
