# Company Intel UI — Design Spec
**Date:** 2026-04-14
**Status:** Approved
**Module:** `intel-company` (v2)
**Location:** Research Tab → Company Snapshot section (replaces existing `company-card.tsx`)
**Designer:** Arijit Chowdhury + Claude

---

## Design Decisions

### Philosophy
Approach C structure (narrative layers) + Approach B visual treatment (bento card aesthetics). Five distinct cards answering five sequential questions an AE asks before a call. Visual weight descends from identity anchor (heaviest) to online presence (lightest).

### Structural Decision
The Company Intelligence section is a standalone, always-open section at the top of the Research tab — not a collapsible accordion equal to the other modules. Other modules (Financial, Tech Stack, Traffic, etc.) collapse below it. Rationale: company identity is the persistent context for everything else on the page. It should not be buried or closeable.

### Component Sources (from UX research)
- **Identity Anchor:** Original design. Horizontal split ratio from ravikatiyar/card-18 featured variant. SVG grid texture from efferd/grid-feature-cards.
- **Stat Chip Grid:** efferd/grid-feature-cards atomic pattern adapted for data density.
- **Intel Row Hover (executives):** Hover choreography from makviesainte/team-showcase, adapted for no-photo context. MEDDPICC badges replace photos as the primary visual signal.
- **Framer Motion animations:** ravikatiyar/card-18 animation dependency pattern.
- **All other components:** Original designs.

---

## Data Source

Backend module: `intel-company` v2
Schema: `CompanySeedOutput` (see `prism_platform/v2/modules/intel_company/schemas.py`)
Frontend type to create: `CompanyIntelOutput` (replaces legacy `CompanyProfileResult`)

Fields consumed:
```
Identity:         legal_name, common_name, domain, is_public, ticker, parent_company, parent_domain
Stats:            headquarters, employee_count, employee_count_source, year_founded, revenue_estimate, revenue_source
Business model:   business_model, industry, sub_vertical
Brand portfolio:  subsidiaries[] (name, domain, description)
Executives:       executives[] (full_name, title, role_classification, linkedin_url, tenure_description, previous_company)
Competitors:      competitors[] (company_name, domain, why_competitor)
Online presence:  product_categories[], company_linkedin_url, twitter_handle, youtube_url, recent_headline
```

---

## Component Architecture

### New file: `frontend/components/prism/company-intel-card.tsx`
Replaces `company-card.tsx`. Contains all 5 layers as sub-components.

```
CompanyIntelCard (root)
  ├── IdentityAnchor
  │     ├── GridPatternBg
  │     ├── IdentityPanel (logo, name, eyebrow, badges)
  │     │     └── ParentCompanyBanner (conditional — if parent_company present)
  │     └── StatsPanel (2×2 stat cells)
  ├── NarrativeLayer label="WHO ARE THEY?"
  ├── WhoAreTheyLayer
  │     ├── BusinessModelBlock
  │     └── StatChipGrid (4 chips: revenue, employees, HQ, founded)
  ├── NarrativeLayer label="WHO'S IN CHARGE?"
  ├── WhoIsInChargeLayer
  │     └── IntelRowHover (executives, sorted by MEDDPICC priority, show 5 + expand)
  ├── NarrativeLayer label="THEIR FOOTPRINT"
  ├── TheirFootprintLayer
  │     └── Bento2ColGrid
  │           ├── BrandPortfolioTree (left panel, conditional — if subsidiaries.length >= 2)
  │           └── CompetitorFeatureCardGrid (right panel)
  ├── NarrativeLayer label="ONLINE PRESENCE"
  └── OnlinePresenceLayer
        ├── ProductCategoryPills
        ├── SocialLinkRow
        └── RecentHeadline
```

---

## Layer-by-Layer Spec

### Layer 0: Identity Anchor

**Purpose:** Answer "is this the right company?" in 2 seconds. Always visible. Never collapsible.

**Layout:** Full-width dark gradient card, horizontal split 55/45.

**Left panel (identity):**
- Logo: attempt to load from `https://logo.clearbit.com/{domain}`. On failure, render initials avatar (first 2 words of company name, #003DFF background).
- Eyebrow: `industry` (or `sub_vertical` if populated) — 11px uppercase, rgba(255,255,255,0.45)
- Name: `common_name` — 26px bold white
- Badge row: 📍 HQ · 📅 "Est. {year}" · 👥 "{employees} employees" · 🏢 "Public · {ticker}" or "Private"
  - Ticker badge special treatment: amber tint (rgba(255,213,0,0.12), border rgba(255,213,0,0.25), text #FFD500)

**Right panel (stats — 2×2 grid):**
- Revenue: formatted (e.g. "~$51.4B"), source label below
- Employees: formatted with commas, source label below
- Founded: year, secondary "X years ago"
- HQ: city + state/country

**Parent company banner (conditional):**
- Appears as a strip above the left panel content when `parent_company` is populated
- Text: "Subsidiary of: [parent_company] · [parent_domain] ↗"
- Background: rgba(255,165,0,0.08), border-bottom: 1px solid rgba(255,165,0,0.15)
- Rationale: budget authority often sits at parent — highest deal-navigation signal

**Background:** linear-gradient(135deg, #0d1b38 0%, #1a2d52 55%, #13244a 100%) + GridPatternBg texture (z-index 1)

**UIX Lego Blocks:** `01-identity-anchor`, `05-grid-pattern-bg`

---

### Layer 1: WHO ARE THEY?

**Purpose:** Business context and key firmographics.

**Components:**

Business model block:
- Full-width text, `business_model` field
- Font: 14px, color #374151, line-height 1.65
- Left accent border: 3px solid rgba(0,61,255,0.20)
- Padding-left: 16px
- Max visible: 3 lines with "read more" toggle if longer

Stat chip grid:
- 4 chips: Revenue · Employees · Headquarters · Founded
- Light glassmorphism chips (see UIX Lego Block 02)

**Card treatment:** White glassmorphism card (rgba(255,255,255,0.72), blur(20px))

**UIX Lego Block:** `02-stat-chip-grid`

---

### Layer 2: WHO'S IN CHARGE?

**Purpose:** Identify the buying committee. Who has budget? Who is the champion?

**Sort order:** economic_buyer → champion → technical_buyer → influencer → end_user → null

**Row columns:**
1. MEDDPICC badge (80px wide) — colored pill with dot + abbreviation
2. Identity — name (14px semibold), title (12px muted), tenure + previous company (11px ghost)
3. LinkedIn icon button — hidden by default, fades in on row hover

**Hover choreography:**
- Hovered row: background rgba(255,255,255,0.90), left 3px border = badge color, LinkedIn appears
- All other rows: opacity 0.45
- Transition: 200ms ease

**Default display:** 5 rows. "Show N more" expands remaining with Framer Motion layout animation.

**Header:** "7 contacts identified · public sources only" — 11px muted italic, right-aligned above the list

**Card treatment:** White glassmorphism card

**UIX Lego Blocks:** `03-intel-row-hover`, `04-meddpicc-badge`

---

### Layer 3: THEIR FOOTPRINT

**Purpose:** How big is their search surface? Who are they fighting?

**Layout:** Bento 2-col grid (50/50 by default; 55/45 if subsidiaries tree is deep)

**Left panel — Brand Portfolio:**
- Conditional: render if `subsidiaries.length >= 2`. If 0–1, show "No distinct sub-brands" placeholder.
- Parent entity chip at top
- Subsidiary rows with connecting lines (vertical + horizontal 1px rgba(0,0,0,0.12))
- "THIS AUDIT" badge on the current domain's brand
- Portfolio Opportunity callout at bottom (amber, 💡, N× search surface copy)
- If `parent_company` populated and no subsidiaries: show "Part of [Parent]" flat display instead

**Right panel — Competitors:**
- Grid of competitor cards (3-column, collapses to 2)
- Show 4 by default, "show N more" expands
- Each card: initial avatar + name + domain link + why_competitor (2-line clamp)
- Hover: translateY(-3px), increased shadow

**UIX Lego Blocks:** `06-brand-portfolio-tree`, `07-competitor-feature-card`, `08-bento-2col-grid`

---

### Layer 4: ONLINE PRESENCE

**Purpose:** Quick-access digital footprint. Freshness signal.

**Components:**

Product category pills:
- `product_categories[]` rendered as small pill badges
- Background: rgba(0,61,255,0.07), border: rgba(0,61,255,0.15), text: #003DFF, 10px uppercase

Social link row:
- Inline icon-buttons: 🔗 domain · [in] LinkedIn · [@] Twitter · [▶] YouTube
- Only render links where URL is populated
- Each: 28×28px button, border-radius 6px, icon-specific tint on hover

Recent headline:
- `recent_headline` field with a 🗞 prefix and date stamp
- Font: 12px, color #374151, italic
- Only render if populated

**Card treatment:** Lightest card in the stack — background rgba(255,255,255,0.50), slightly more transparent than others.

**UIX Lego Block:** `09-narrative-layer-section` (above this layer)

---

## Interaction Summary

| Interaction | Trigger | Result |
|---|---|---|
| LinkedIn button | Hover on exec row | Fade in + slide in from right |
| Other rows dim | Hover on any exec row | Opacity → 0.45 |
| Show more execs | Click "show N more" | Framer Motion height expand |
| Read more (bio) | Click on truncated text | Inline expand, no modal |
| Show more competitors | Click "show N more" | Fade in remaining cards |
| Domain links | Click | Open in new tab |
| LinkedIn buttons | Click | Open LinkedIn profile in new tab |
| Social links | Click | Open in new tab |

---

## Empty/Null States

| Field | Null behavior |
|---|---|
| Logo | Initials avatar (#003DFF bg) |
| revenue_estimate | "Revenue unknown" in ghost text |
| employee_count | "–" |
| subsidiaries (empty) | Hide Brand Portfolio panel; left panel shows placeholder |
| executives (empty) | "No leadership data available" placeholder |
| competitors (empty) | "No competitor data available" placeholder |
| parent_company (null) | Banner not rendered |
| recent_headline (null) | Headline row not rendered |
| social links (null) | Individual link not rendered (row shrinks) |

---

## Files to Create / Modify

### New files
```
frontend/components/prism/company-intel-card.tsx     ← main component (replaces company-card.tsx)
frontend/components/prism/identity-anchor.tsx         ← Layer 0
frontend/components/prism/stat-chip-grid.tsx          ← Layer 1 chips
frontend/components/prism/intel-row-hover.tsx         ← Layer 2 exec list
frontend/components/prism/meddpicc-badge.tsx          ← badge system
frontend/components/prism/brand-portfolio-tree.tsx    ← Layer 3 left
frontend/components/prism/competitor-card-grid.tsx    ← Layer 3 right
frontend/components/prism/narrative-layer.tsx         ← section divider labels
```

### Modified files
```
frontend/lib/types.ts           ← add CompanyIntelOutput type (replaces CompanyProfileResult for this module)
frontend/components/dashboard/tabs/research-tab.tsx  ← swap CompanyCard → CompanyIntelCard
```

### Deprecated (keep file, stop using)
```
frontend/components/prism/company-card.tsx           ← replaced by company-intel-card.tsx
```

---

## UIX Lego Blocks Used

All 9 blocks defined in `ArijitOS-Brain/UIX-Lego-Blocks/` are used by this module:

| Block | Zone |
|---|---|
| 01 Identity Anchor | Layer 0 |
| 02 Stat Chip Grid | Layer 1 |
| 03 Intel Row Hover | Layer 2 |
| 04 MEDDPICC Badge | Layer 2 |
| 05 Grid Pattern Background | Layer 0 |
| 06 Brand Portfolio Tree | Layer 3 left |
| 07 Competitor Feature Card | Layer 3 right |
| 08 Bento 2-Col Grid | Layer 3 container |
| 09 Narrative Layer Section | Between all layers |

---

## Open Questions (resolved)

1. **Should company intel be one collapsible among equals?** No. It's always-open, at the top of Research. Other modules collapse below it.
2. **Photos for executives?** No — `CompanySeedOutput` has no headshot URLs. Use MEDDPICC badges as the visual signal instead of photos.
3. **Brand portfolio when no subsidiaries?** Hide the left panel; right panel (competitors) takes full width.
4. **Parent company display?** Amber banner above identity left panel. Not buried in stat chips.
