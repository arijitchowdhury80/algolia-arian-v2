# Skill Blueprint — Custom Landing Page Builder (Whale/Avail), at scale

_Seed for a future skill: "generate hundreds of per-brand one-to-one landing pages on demand."_
_Written 2026-08-17 from the build session. Everything below is verified against the live Jahia
instance + the working app at `frontend/custom-landing-page/`._

## Goal the skill must serve
Produce **N per-brand landing pages on demand**, published as real Jahia pages (like the live
`algolia.com/lp/ralph-lauren-algolia` / `/belk-algolia`), from a customer profile + a few choices.
Two modes must exist:
- **A) Interactive configurator** — a human reviews a ~80%-prefilled page, tweaks, publishes. (Built.)
- **B) Batch / headless** — feed a list of customer profiles → produce N pages in one run. (The
  "hundreds on demand" mode; not built — the batch harness is the main net-new for the skill.)

## The proven pipeline (read → assemble → preview → publish)
1. **READ from Jahia** (GraphQL `…/modules/graphql`, auth header `Authorization: APIToken <token>`,
   token ALWAYS server-side):
   - Component allowlist: `/sites/www` children typed `algoliaconnectnt:algoliaAllowedNodeType`
     → 56 `aant:` component types the site permits.
   - DAM assets (two roots): videos `/sites/algolia-assets/files/videos`, images `/sites/www/files`,
     logos `/sites/www/files/Logos`.
   - A template page to clone: RL = `/sites/www/home/lp/ralph-lauren-algolia`.
2. **ASSEMBLE** via the **Module Manifest** (`docs/whale-module-manifest.json`): 9 modules; per module =
   its Jahia component type(s), variant set (the Figma layouts), content slots, pick-list caps
   (Features 8–10, Priorities 1–7, Resources optional), and changeability (7 change / 2 standard).
   Bind each slot: `auto` (from customer profile), `pick` (curated catalog + cap), or `manual`.
   No fabrication — unfilled slots stay explicitly empty.
3. **PREVIEW** — WYSIWYG. (Today representative; ideally render a Jahia draft.)
4. **PUBLISH** — clone the template page → set each component's properties → publish. **MUST be ONE
   batched GraphQL mutation per page** (see consistency gotcha). Governance-gated.

## Reusable assets already built (don't rebuild these)
| Asset | Where |
|---|---|
| Module Manifest (9 modules → `aant:` components + caps) | `frontend/custom-landing-page/docs/whale-module-manifest.json` |
| Jahia connection + auth + DAM map | memory `reference-jahia-connection-verified` |
| Figma variant sets + 15 thumbnails (hero 5 / body 8 / footer 2) | `frontend/custom-landing-page/src/assets/figma/` |
| Interactive configurator app (React+Vite+TS+Tailwind + Node backend) | `frontend/custom-landing-page/` |
| Component browse + per-slot asset browse (locked to DAM folders) | app `server/index.mjs` (`/api/jahia/components`, `/api/jahia/assets`) |
| RL / Belk reference compositions (the acceptance test) | `/sites/www/home/lp/{ralph-lauren,belk}-algolia` |

## Scale design ("hundreds on demand") — the net-new for the skill
- **Batch harness:** input = list of `{customer, profile, asset choices, layout defaults}`. For each →
  build a composition doc → **one batched mutation** → publish → verify. Idempotent by slug (upsert).
- **Defaults engine:** a per-module default layout map (Nicole's call) so most pages need zero manual
  picks — that's what makes hundreds feasible.
- **Clone-and-repopulate:** clone RL/Belk template; repopulate only the 7 "change" modules; leave the
  2 standard ones untouched.
- **Concurrency:** throttle mutations (Jahia is clustered); verify each page with direct `nodeByPath`,
  NOT the SQL2 index (it lags).
- Interactive configurator = the review/exception path; batch = the volume path. Same manifest + engine.

## Hard-won gotchas (bake these into the skill)
1. **Auth:** `Authorization: APIToken <token>` only — Basic and Bearer are rejected as anonymous.
2. **Read-after-write consistency lag** on this clustered instance: a just-written node isn't visible in
   the next request. → compose create+populate+publish as ONE mutation; verify via direct `nodeByPath`.
3. **`/sites/www` IS algolia.com (production).** Publishing there is high blast-radius → governance-gated;
   use a scoped **service account**, never a personal token, and honor the publish/approval workflow.
4. **Two DAM roots** (assets site + www files); **Figma is organized by LAYOUT TYPE, not by the 9
   semantic modules** — every body module can use any of the 8 body layouts.
5. **Token server-side always** (backend proxy); a static browser page cannot call Jahia (leak + CORS).
6. **Prototype ≠ product:** a single flat HTML file is a UX spec; graduate to a real app early
   (see memory `feedback-dont-ship-flat-html-as-the-app`).

## Inputs / adapters the skill still needs
- `get_customer_profile(customer)` → structured content from **account plan / brief / Gong call**
  (translate + human-validate for non-English). This is the hardest, highest-hallucination-risk piece.
- Asset libraries: which DAM folder feeds each slot (video/image/logo) — already mapped above.
- Curated pick-list catalogs (features / priorities / resources) — currently stubbed.

## Blockers before true on-demand-at-scale (must clear first)
- Governance + publish workflow + service account (`docs/open-questions.md` Q1–6).
- Real binding from unstructured customer data (biggest risk).
- Brand-asset supply (hero videos, logos) — a creative/content bottleneck, not a code one.
- Per-item asset binding (each card its own logo/icon), bind the Jahia node **path** not the filename,
  and preview via a real Jahia draft render.

## Success criteria for the skill
- One profile → one published page in one automated pass; **preview === published**; zero fabricated values.
- N profiles → N verified pages in a batch run.
- A new module/variant is added by editing the manifest only (no engine change).

## Relationship to existing skills
- Reuse `algolia-design` tokens (Sora + Nebula Blue). Distinct from `algolia-landing` (which generates
  Algolia-branded HTML content) — this skill creates **real Jahia pages** via the API.
- When ready to build it, use `skill-creator`; this file is the spec to hand it.
