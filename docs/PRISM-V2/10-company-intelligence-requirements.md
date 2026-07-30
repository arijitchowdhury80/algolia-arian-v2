# Company Intelligence Module — V2 Requirements

Status: REQUIREMENTS AGREED, folder tree built, spec not yet written
Date: 2026-07-30
Branch: `feat/v2-module-tree` (off `main`)
Tree: `backend/prism_platform/modules/` — see its README for the live structure
Source: Arijit, verbatim session dictation
Scope: first module of the V2 modularisation. Template for the other 16.

---

## 1. Framing (Arijit's words, condensed)

Company Intelligence is what you run when you are researching an organisation and want to
know everything about them, **before** you have thought about your own offering or
positioning. It is agnostic of Algolia or any other vendor. Whale, dolphin or minnow does
not matter. Same module.

Comparable: Algolia's "whale program" account research, but as a standalone product.

Rule: **no vendor language, no product positioning, no sales framing inside this module.**
Those live in a lens or a downstream synthesis layer.

---

## 2. Required buckets

Arijit enumerated these twice. Union of both passes.

### Bucket 1 — The business
- What is the business of this organisation, what do they actually do
- Their website / primary web properties
- Where do they conduct most of their business
- Channel mix: online, in-store, direct to consumer, wholesale, retail, marketplace
- How they organise the business (segments, divisions, reporting units)
- How many countries they operate in
- Multi-channel and multi-lingual footprint

### Bucket 2 — The company itself
- When founded
- Headquarters
- All office locations
- Organisation hierarchy
- Sister brands
- Holding company / parent company
- Portfolio of brands owned

### Bucket 3 — Executive team
- The **entire** executive team, not a sample
- Names
- Titles
- LinkedIn profiles
- Bios
- Contact (flagged, see open questions)

### Bucket 4 — Competitors
- Who they compete with, in their industry and their vertical
- Where the prospect stands relative to them

### Bucket 5 — Financials (stated in pass 1, omitted in pass 2, see Q1)
- Last 3 years of financials
- Reuse existing work: Yahoo Finance, SEC EDGAR
- Both public and private paths
- Charting
- Narrative story built on top of the numbers

---

## 3. Reuse mandate

Explicit instruction: reuse the existing financial collection work rather than rebuild.
Existing assets in `backend/prism_platform/v2/modules/`:
- `intel_financial_public` (yfinance / EDGAR path)
- `intel_financial_private` (6-source estimation waterfall)
- `intel_company` (current seed module, already carries identity, subsidiaries,
  executives with MEDDPICC tags, competitors, revenue estimate)
- `intel_competitors`
- `intel_investor` (verbatim earnings-call executive quotes)

Also existing and reusable: `ExecutionContextV2`, `Finding` taxonomy, `ModuleConfig`,
`V2_MODULE_REGISTRY`, `POST /api/v1/modules/{name}/execute`.

---

## 4. Naming collision — RESOLVED

Arijit calls this work "V2". Two other things already claim that name:

1. `prism_platform/v2/` — a Python package with 17 built modules. This is the runtime
   (types, registry, executor, clusters). **It stays. The new modules import from it.**
2. Branch `prism-v2` — verified 2026-07-30: this is the **frontend** branch (door pages,
   AE cockpit, marketer, IA variants). No `backend/` directory at all. 203 commits behind
   `main`, predates the monorepo restructure. **Not usable for backend work.**

Decision: new branch `feat/v2-module-tree` cut from `main`. `prism-v2` untouched.

---

## 5. Decisions (all resolved 2026-07-30)

- **Q1 Financials.** IN. Rendered inside the M1 deliverable, executed as separate
  submodules (M1.6.1 / M1.6.2) because financial data caches quarterly while company
  identity caches yearly.
- **Q2 Exec team boundary.** No cap. CEO, all CEO direct reports, full C-suite, plus
  VP-and-above with Digital / Ecommerce / Data / Technology / Marketing in title.
  Complete when the company's own leadership page is fully covered.
- **Q3 Contact details.** OPEN. LinkedIn and public bio are in core. Verified email/phone
  needs a paid provider and drags GDPR/CCPA obligations into a foundation module.
  Recommendation on the table: separate optional add-on. Not yet ruled on.
- **Q4 Brand recursion.** Name every brand and subsidiary with domain. Profile none by
  default. One level, no recursion. Child-brand profiling is a separate on-demand run.
- **Q5 Industry shape.** OPEN. Buckets read retail-flavoured. A neutral core plus
  vertical-specific extensions is the proposed shape. Not yet ruled on.
- **Q6 Stopping rule.** Each bucket names one authoritative source it must exhaust. Done
  when that source is fully consumed, not when the model stops. Accepted by default,
  Arijit did not object.

---

## 6. Accepted structure

Seven top-level modules. Vendor-neutrality boundary sits between M5 and M6.

```
M1 Company Intelligence     M5 Industry & Market
M2 Technology Intelligence  M6 Synthesis   <- vendor lens applies
M3 Signal Intelligence      M7 Delivery    <- vendor lens applies
M4 Partner & Ecosystem
```

M1 expands to seven buckets: business model, commercial footprint, corporate structure,
executive team, competitive position, financial position, trajectory. Full tree and the
per-bucket detail live in `backend/prism_platform/modules/README.md`.

Two additions accepted beyond Arijit's original four buckets:
- **M1.2 Commercial footprint** as its own bucket. Nothing in the existing 17 modules
  produces this.
- **M1.7 Trajectory.** Every original bucket was a static snapshot. What changed in the
  last 12-24 months is where the value sits.

Also accepted: **M1.5 returns three separately labelled competitor lists** (self-declared
in 10-K, analyst-declared, behavioural overlap). Never blended, because the disagreement
between them is itself a finding.

### Still on the table, not yet ruled on

- Per-field provenance and as-of date, mandatory, surfaced in the UI.
- Explicit degraded path for private companies, where three buckets have no authoritative
  source. Precedent exists in `intel_financial_private`'s 6-source waterfall.
- "How the organisation buys" as a future module: procurement model, vendor
  relationships, RFP posture, technology budget owner. Vendor-agnostic and commercially
  valuable. Possibly its own top-level module rather than part of M1.

---

## 7. Next step

1. Add `module_id` and `parent_id` to `ModuleConfig` in `v2/types.py`.
2. Write the M1 spec.
3. Build submodule by submodule, migrating reusable existing modules in place.

Enter `development-loop` at step 2.
