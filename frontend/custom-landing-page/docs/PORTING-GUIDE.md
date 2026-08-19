# Porting Guide — reuse this configurator pattern in another project

_You want the same mechanism (browse + pick assets per section → apply → live preview → produce the
output) for a different purpose, e.g. building presentations from your own art/assets. This tells another
Claude Code instance exactly where the code is, what the reusable architecture is, and how to adapt it._

## Where the code is (point the other instance here)
- **GitHub:** `github.com/arijitchowdhury80/prism`, branch `feat/whale-landing-builder`,
  path **`frontend/custom-landing-page/`**.
- **Local:** `/Users/arijitchowdhury/Dropbox/AI-Development/prism/frontend/custom-landing-page/`.
- **Read these, in order:**
  1. `docs/SKILL-BLUEPRINT.md` — the pipeline, gotchas, blockers (the "why").
  2. `src/manifest.ts` — the data model: sections, each section's variants (+ thumbnails), slots (text /
     asset / pick), caps, per-customer prefill.
  3. `src/App.tsx` — the whole configurator: split screen, variant picker, per-slot **asset Browse**
     modal, **live preview** (`previewInner` + `bodyLayoutHTML`), drag-reorder, validation.
  4. `server/index.mjs` — the **source adapter**: a tiny Node backend that reads components + assets from
     a locked source (Jahia here) with the secret token **server-side**, exposed as `/api/*`.
  5. `src/index.css` — design tokens + the split-screen layout.
  6. `prototype/whale-configurator.html` — the single-file UX spec (the whole idea in one file).

## The reusable pattern (generic — not landing-page-specific)
A **configurator** = split screen. LEFT = a list of **sections**; each section has: a **variant picker**
(layout options shown as thumbnails), **content fields**, **per-slot asset browse** (pick from a *locked*
source folder), and a validity flag. RIGHT = a **live preview** that re-renders as you edit. Bottom bar =
status + Preview + Publish/Export.

Four **pluggable adapters** — swap these per use case, keep everything else:
1. **Manifest** (`src/manifest.ts`) — the sections + their variants + slots + caps + defaults.
2. **Source adapter** (`server/index.mjs`) — where components/assets come from, and a **lock** so browse
   is scoped to approved folders. Here = Jahia GraphQL + DAM folders. Secret stays server-side.
3. **Preview renderer** (`previewInner`/`bodyLayoutHTML` in `App.tsx`) — section + variant + content → HTML.
4. **Output/publish adapter** — composition → final artifact. Here = a Jahia page (gated).

## How to adapt it for PRESENTATIONS / art (the other thread)
- **Section → slide** (hero slide, section slide, closing slide). Manifest = your slide types + layout variants.
- **Asset browse → your asset library.** Point the source adapter at *your* art/asset folder (local dir,
  Google Drive, S3 — whatever). Lock it to that folder. Browse → pick an image/video → **Apply** → the
  slide preview on the right updates. (This is exactly what you described.)
- **Preview renderer → slide renderer.** **Output adapter → a deck** (export to PDF / Google Slides / HTML).
- **Keep:** split screen, per-section variant thumbnails, per-slot asset browse locked to a source, live
  preview, validation, drag-reorder, the design tokens.
- **Drop the Jahia specifics:** `Authorization: APIToken`, `/sites/www`, the 56 `aant:` components —
  replace with your asset source + your slide component set.

## Gotchas to carry over
- **Secrets/tokens server-side only** — a static browser page can't call a private source (leak + CORS);
  you need a tiny backend endpoint (like `server/index.mjs`).
- **Lock browse to a source folder** — governance/safety: operators only pick approved assets.
- **Prototype the UX in one HTML file first**, then graduate to React+Vite+backend (see the
  `feedback-dont-ship-flat-html-as-the-app` lesson). Don't keep bolting onto the flat file.

## Paste-prompt for the other Claude Code instance
> Read `frontend/custom-landing-page/` in `github.com/arijitchowdhury80/prism` (branch
> `feat/whale-landing-builder`) — especially `src/App.tsx`, `src/manifest.ts`, `server/index.mjs`,
> `docs/SKILL-BLUEPRINT.md`, and `docs/PORTING-GUIDE.md`. It's a working configurator: split screen,
> per-section variant picker with real thumbnails, per-slot asset browse **locked to a source folder**,
> live preview, drag-reorder. I want the SAME mechanism to build **presentations** for myself: sections =
> slides; the asset browse should point at MY asset folder at `<PATH-OR-SOURCE>`; picking an asset applies
> it and the slide preview updates on the side; the output is a deck (PDF/Google Slides). Reuse the
> architecture (manifest + source adapter + preview renderer + output adapter). Swap the Jahia source for
> my asset folder and the Jahia-page output for a slide/deck export. Start by reading those files, then
> propose the adapted manifest + source adapter before building.
