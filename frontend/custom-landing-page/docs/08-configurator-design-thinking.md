# Configurator Shell — Design Thinking (condensed; decisions already made)

Most of Phase-1 thinking was done live via approved inline sketches + the hybrid decision + the
Module Manifest. This records it against the frontend-builder rubric so the build is disciplined.

## 1. Mental model
**Wizard × Inbox hybrid.** Operator expects a *pre-filled worklist*: the page is already 80% built
from the account plan/brief/Gong; they review a list of module rows and edit only what's off, then
publish. NOT a blank-canvas builder. Confusion risk = making it feel like authoring from scratch.

## 2. Information architecture (tiers)
- **Hero:** the single-scroll list of 9 module rows (the work).
- **Primary:** customer picker + auto-fill banner; the Preview/Publish bar.
- **Secondary:** per-row variant chip + content summary; pick-list counts (8/10, 5/7).
- **Supporting:** changeability tags (per-brand / standard-locked), module order numbers, governance note.

## 3. Interaction flow
Top-3 actions: (1) edit a module row inline, (2) adjust a pick-list, (3) Preview→Publish.
Happy path: pick customer → rows pre-fill → tweak a few → Preview → (Publish, gated). Guide-me mode =
same data walked one row at a time. No dead ends; Publish disabled with a visible "governance pending" note.
States: empty (no customer picked → prompt to pick), loading (pre-fill spinner), locked (M6/M8), error (n/a in shell).

## 4. Cognitive load
Chunks on first view: customer header (1), auto-fill banner (1), module list (1 — rows are uniform,
scanned as one pattern), preview/publish bar (1) = ~4. Under budget. Row detail opens on demand (inline edit),
so per-module complexity is deferred, not simultaneous.

## 5. Emotional journey
Arrive → *reassured* ("it's already mostly done") → *in control* (edit only what matters) →
*confident* (preview matches publish) → *safe* (publish gated until governance clears).

## 6. Pre-mortem
- **Generic-AI look** → mitigate: Algolia brand (Sora + Algolia blue #003DFF/#5468FF), distinctive per-brand vs locked treatment.
- **Overload** → uniform rows + deferred inline edit keep first view calm.
- **Ambiguous action** → one clear Preview/Publish bar; publish visibly gated with reason.
- **Mobile/dark/a11y** → build responsive + dark tokens + labels from the start; verify in Step 9/10.
- Elephant: untested on a real operator; shell is a prototype, not wired to real data yet (explicit).

## 7. Aesthetic
**theme-professional base + Algolia brand tokens** (this is an internal Algolia tool). Sora headings,
Inter/system body, Algolia blue #003DFF primary / #5468FF secondary, navy #21243D text, #F5F5FA surface.
Per-brand modules = blue accent; standard/locked = muted gray + lock. Dark mode via CSS variables.

## Scope of THIS build
Clickable front-end shell only. Reads the 9-module manifest (embedded inline so it's self-contained).
NO Jahia writes. Preview/Publish are present; Publish gated. Single-scroll default + guide-me toggle.
