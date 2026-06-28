/**
 * Algolia PRISM Design Tokens
 *
 * Single source of truth for all styling values.
 * Font: Sora — 300 (light) / 400 (regular) / 600 (semibold) ONLY.
 *       Never use 700/800 — Sora doesn't include those weights;
 *       the browser will synthesize bold, which looks wrong.
 *
 * RULE: Never hardcode colors, font sizes, or spacing in component files.
 *       Always import from this file.
 *
 * Tailwind utilities (registered in globals.css @theme):
 *   Colors:    text-brand-blue · text-brand-navy · text-brand-purple · text-brand-muted
 *   Font size: text-body · text-label · text-small · text-caption
 */

// ── Typography ────────────────────────────────────────────────────────────

export const font = {
  // Algolia type scale — document headings
  h1: "var(--font-h1)",  // 56px, weight-light
  h2: "var(--font-h2)",  // 36px, weight-light
  h3: "var(--font-h3)",  // 28px, weight-regular
  h4: "var(--font-h4)",  // 22px, weight-semibold
  h5: "var(--font-h5)",  // 18px, weight-semibold

  // Algolia text scale — UI copy
  body:    "var(--font-body)",   // 16px — paragraphs, descriptions
  label:   "var(--font-label)",  // 14px — names, titles, primary labels
  small:   "var(--font-small)",  // 13px — secondary text, tenure, sources
  caption: "12px",               // 12px — absolute minimum (badges, captions, tags)

  // UI-specific sizes (data display, not headings)
  entityName: "26px",  // company/person hero names
  statValue:  "20px",  // metric values in stat grids
  statValueSm:"16px",  // stat values with long text (HQ city name)

  weight: {
    light:    300 as const,  // h1, h2 only
    regular:  400 as const,  // body, h3, secondary labels
    semibold: 600 as const,  // labels, badges, h4, h5 — MAX weight in Sora
  },
} as const;

// ── Colors ────────────────────────────────────────────────────────────────

export const color = {
  // Brand
  blue:   "var(--brand-blue)",    // #003DFF
  purple: "var(--brand-purple)",  // #5468FF
  navy:   "var(--brand-navy)",    // #23263B

  // Text hierarchy
  text:   "var(--brand-navy)",    // #23263B — body copy
  muted:  "var(--muted-text)",    // #6B7280 — secondary
  ghost:  "#9CA3AF",              // tertiary — timestamps, sources

  // Blue tints (for interactive chips, avatars, links)
  blue06: "rgba(0,61,255,0.06)",
  blue07: "rgba(0,61,255,0.07)",
  blue08: "rgba(0,61,255,0.08)",
  blue10: "rgba(0,61,255,0.10)",
  blue12: "rgba(0,61,255,0.12)",
  blue15: "rgba(0,61,255,0.15)",
  blue20: "rgba(0,61,255,0.20)",

  // Glassmorphism surface
  glass: {
    bg:      "rgba(255,255,255,0.72)",
    bgLight: "rgba(255,255,255,0.50)",
    bgHover: "rgba(255,255,255,0.90)",
    bgRow:   "rgba(255,255,255,0.55)",
    border:  "rgba(255,255,255,0.85)",
    shadow:  "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.95)",
  },

  // Dark card (Identity Anchor)
  dark: {
    bg:          "linear-gradient(135deg, #0d1b38 0%, #1a2d52 55%, #13244a 100%)",
    border:      "rgba(255,255,255,0.09)",
    divider:     "rgba(255,255,255,0.09)",
    text:        "#ffffff",
    textMuted:   "rgba(255,255,255,0.45)",
    textGhost:   "rgba(255,255,255,0.28)",
    badgeBg:     "rgba(255,255,255,0.08)",
    badgeBorder: "rgba(255,255,255,0.14)",
    badgeText:   "rgba(255,255,255,0.80)",
    statLabel:   "rgba(255,255,255,0.40)",
    shadow:      "0 4px 24px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.06)",
  },

  // Dark card accent banners
  ticker: {
    bg:     "rgba(255,213,0,0.12)",
    border: "rgba(255,213,0,0.25)",
    text:   "#FFD500",
  },
  parent: {
    bg:     "rgba(255,165,0,0.08)",
    border: "rgba(255,165,0,0.15)",
    text:   "rgba(255,210,100,0.85)",
  },

  // Portfolio opportunity (amber)
  amber: {
    bg:     "rgba(234,179,8,0.08)",
    border: "rgba(234,179,8,0.20)",
    title:  "#92400E",
    body:   "#78350F",
  },

  // LinkedIn
  linkedin: {
    bg:     "rgba(0,119,181,0.10)",
    border: "rgba(0,119,181,0.20)",
    text:   "#0077B5",
  },

  // "THIS AUDIT" badge
  auditBadge: {
    bg:     "rgba(0,61,255,0.10)",
    border: "rgba(0,61,255,0.20)",
    text:   "#003DFF",
  },

  // Dividers
  divider:     "rgba(0,0,0,0.07)",
  dividerSoft: "rgba(0,0,0,0.05)",

  // Signals (matches CSS vars in globals.css)
  signal: {
    critical:       "#DC2626",
    criticalBg:     "var(--signal-critical-bg)",
    criticalBorder: "var(--signal-critical-border)",
    warning:        "#D97706",
    warningBg:      "var(--signal-warning-bg)",
    warningBorder:  "var(--signal-warning-border)",
    positive:       "#059669",
    positiveBg:     "var(--signal-positive-bg)",
    positiveBorder: "var(--signal-positive-border)",
  },
} as const;

// ── Radius ────────────────────────────────────────────────────────────────

export const radius = {
  sm:   "6px",   // badges, tags
  md:   "8px",   // buttons, links
  lg:   "12px",  // inner cards, chips
  xl:   "16px",  // medium cards
  "2xl":"20px",  // main glassmorphism cards
  pill: "999px", // pill/capsule badges
} as const;

// ── Shadows ───────────────────────────────────────────────────────────────

export const shadow = {
  card:      "var(--card-shadow)",
  cardHover: "var(--card-shadow-hover)",
  glass:     "0 2px 4px rgba(0,0,0,0.03), 0 6px 16px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.95)",
  dark:      "0 4px 24px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.06)",
  lift:      "0 6px 20px rgba(0,0,0,0.10)",
  flat:      "0 1px 3px rgba(0,0,0,0.04)",
} as const;

// ── Reusable style objects ────────────────────────────────────────────────

/** Standard glassmorphism card — use as `style={styles.glassCard}` */
export const styles = {
  glassCard: {
    background:           color.glass.bg,
    backdropFilter:       "blur(20px)",
    WebkitBackdropFilter: "blur(20px)",
    border:               `1px solid ${color.glass.border}`,
    borderRadius:         radius["2xl"],
    padding:              "24px 28px",
    boxShadow:            shadow.glass,
  } satisfies React.CSSProperties,

  eyebrow: {
    fontSize:      font.caption,
    fontWeight:    font.weight.semibold,
    textTransform: "uppercase" as const,
    letterSpacing: "0.12em",
    color:         color.muted,
    marginBottom:  "14px",
  } satisfies React.CSSProperties,
} as const;
