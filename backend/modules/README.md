# PRISM Module Tree

`backend/modules/` is the canonical home for PRISM's product modules. Seven top-level
modules, each independently runnable, independently observable, and independently
sellable.

**Repo layout is two halves and only two halves:** `prism/frontend/` and
`prism/backend/`. Product modules live directly under `backend/`. Frontend code lives
under `frontend/`. Do not nest modules inside any other package.

Set up 2026-07-30. Requirements: `docs/PRISM-V2/10-company-intelligence-requirements.md`.

---

## The seven modules

| ID | Module | Scope | Vendor-neutral |
|----|--------|-------|----------------|
| M1 | Company Intelligence | Who the organisation is, how it operates, who runs it, who it competes with, what it earns | Yes |
| M2 | Technology Intelligence | Tech stack, traffic, digital experience | Yes |
| M3 | Signal Intelligence | News, social, hiring, buying signals | Yes |
| M4 | Partner & Ecosystem | Platform partners, SIs, account overlap | Yes |
| M5 | Industry & Market | Vertical benchmarks, trends, analyst view | Yes |
| M6 | Synthesis | Business case, sales plays | **No** — vendor lens applies here |
| M7 | Delivery | Report rendering, campaign assembly | **No** — vendor lens applies here |

**The vendor-neutrality boundary is between M5 and M6.** M1 through M5 describe the
target organisation and must contain no Algolia (or any vendor) language, scoring, or
positioning. M6 and M7 apply a vendor lens on top. Swapping the lens is how PRISM
becomes sellable beyond Algolia. Enforce this in review: a vendor name appearing in
M1-M5 is a defect, not a detail.

---

## Numbering rules

- **Number is identity, not ownership.** A submodule is numbered under one parent for
  lifecycle, logging, and UI grouping. Its output may still be read by any other module
  via `composes`. M1.6 (Financial Position) is read by M6 synthesis; that is correct and
  expected, not a violation.
- **Never renumber.** Renumbering means renaming directories and rewriting imports. New
  submodules are appended at the next free number, even if that breaks thematic order.
- **Depth stops at three levels.** M1 -> M1.4 -> M1.4.2. Anything deeper is a sign the
  parent should have been split.

---

## M1 Company Intelligence — current tree

```
m1_company_intelligence/
  m1_1_business_model/         what they do, revenue streams, segments, how they organise
  m1_2_commercial_footprint/   channels, countries, domains, languages, currencies,
                               storefronts, apps, marketplaces        [NEW — no existing source]
  m1_3_corporate_structure/    founded, HQ, offices, parent, holding co, brand portfolio
  m1_4_executive_team/
    m1_4_1_leadership_roster/  full leadership, titles, LinkedIn, bios, tenure
    m1_4_2_executive_voice/    verbatim exec statements   [reuses v2/modules/intel_investor]
  m1_5_competitive_position/
    m1_5_1_self_declared/      competitors named in the target's own 10-K risk factors
    m1_5_2_analyst_declared/   competitors named by Gartner/Forrester/trade press
    m1_5_3_behavioural/        traffic and SERP overlap
  m1_6_financial_position/
    m1_6_1_public/             3-year trend   [reuses v2/modules/intel_financial_public]
    m1_6_2_private/            estimation waterfall [reuses v2/modules/intel_financial_private]
  m1_7_trajectory/             what changed across all buckets in the last 12-24 months
```

### Decided scope (Arijit, 2026-07-30)

- **Executive team:** no cap. CEO, all CEO direct reports, full C-suite, plus VP-and-above
  with Digital / Ecommerce / Data / Technology / Marketing in title. Complete when the
  company's own leadership page is fully covered.
- **Brand portfolio:** name every brand and subsidiary with domain. Profile none by
  default. One level, no recursion. Profiling a child brand is a separate on-demand run.
- **Financials:** rendered inside the M1 deliverable, executed as separate submodules
  because financial data caches quarterly while identity caches yearly.
- **Stopping rule:** each bucket names one authoritative source it must exhaust. The
  bucket is done when that source is fully consumed, not when the model stops.

### Three competitor lenses, never merged

M1.5 returns three separately labelled lists. They frequently disagree, and the
disagreement is itself the finding. Do not blend them into one list.

---

## Where this sits in the backend

```
backend/
├── core/       shared backend library. types, config, db, auth, paths,
│               registry, executor, LLM clients. Every module imports it.
├── modules/    this tree. M1-M7, each a library in its own right.
└── server/     the process that runs on :8000. Imports core + modules,
                mounts their routers. Thin by design.
```

Three packages, all backend. `frontend/` is the other half of the repo and is not
involved.

`prism_platform/` is what all of this used to be. As of 2026-07-30 it holds only the 17
legacy flat modules at `prism_platform/v2/modules/`, which migrate into `backend/modules/`
one at a time. When the last one moves, the directory gets deleted.

### Known debt, tracked not ignored

Two directories are still named `modules`:
1. `backend/modules/` — this one, the destination
2. `backend/prism_platform/v2/modules/` — the 17 legacy modules, migrating out

`server/pipeline/modules/` also exists with one file (`traffic.py`); delete once confirmed
dead. Do not add a fourth.

### Paths

Nothing in the backend computes `Path(__file__).parents[N]` to find a root. All roots come
from `core/paths.py`. Before the split there were eight independent depth-encoding path
computations and every restructure broke a different subset of them. Adding a new one
re-opens that whole class of bug.

---

## Next

1. Add `module_id` and `parent_id` to `ModuleConfig` in `v2/types.py` so the registry can
   build this tree at runtime and logs can group by module.
2. Write the M1 spec.
3. Build M1 submodule by submodule, migrating the reusable existing modules in place.
