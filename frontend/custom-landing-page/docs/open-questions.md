# Whale Landing-Page Builder — Open Questions (blocking before full build)

The technical path (build the pages in Jahia via the GraphQL API) is proven. What can still sink
this project are decisions only the web/marketing team and Nicole can make. These need answers
before we invest in the full build.

Context: the RL/Belk pages are real Jahia pages under `/sites/www/home/lp/<brand>-algolia` on
`tmp-content-eng-algolia.cloud.jahia.com`, built from `aant:` components, personalized by jExperience.

---

## For the Web / Marketing / Jahia team (governance — Tier-1 risk #1, #10)

1. **Publishing to the live site.** `/sites/www` is algolia.com. Should an automated builder ever
   *publish* a partner LP directly, or must every page go through the existing
   `scheduled-publication-workflow` (human approval) before going live? What's the required review gate?
2. **Who is allowed to create/publish** partner LP pages — marketing/enablement only, or AEs too?
   (Drives the tool's permissions and guardrails.)
3. **Credential.** We're currently using `JAHIA_API_TOKEN` (a personal API token). For a production
   tool, do you want a dedicated **service account** scoped to partner-LP creation, with what
   path/role limits? (The current token can write; we should not rely on a personal token.)
4. **Where should new partner pages live** — under `/sites/www/home/lp/` alongside RL/Belk, or a
   staging/sandbox site first, then promoted? Is there a non-prod site we should build/test against?
5. **Template ownership & drift.** The `algolia-partner-templates` module (v1.1.31) and the ~180
   `aant:` component types evolve. Who owns them, and how will we be told when a component/type
   changes so our mapping doesn't break silently?
6. **Preview.** Can Jahia render a **draft/unpublished** page for preview (so an operator sees the
   page before publishing)? If so, what's the preview URL/mechanism?

## For Nicole (content + scope — Tier-1 risk #3, #4; Tier-3 risk #9)

7. **Per-module data sources.** For each "change" module, where exactly does the content come from —
   which fields in the **account plan**, the **brief**, and the **Gong call**? (You mentioned these;
   we need the mapping per module: hero headline, proof points, quotes, features, priorities, parting.)
8. **The pick-lists.** Can you (or product marketing) provide the **finite catalogs** to pick from —
   the master list of Features (M4, pick 8–10), the master list of Priorities (M5, pick 5–7), and the
   Recommended-Resources list (M7)? These are the curated option sets the tool offers.
9. **Brand assets.** Hero needs a brand-specific **background video** + **logo lockup**; proof/quotes
   need **customer logos**. Where do these come from, and who produces them? (These aren't in a text
   brief — they're the content-supply bottleneck.)
10. **Missing inputs.** When there's no brief (e.g. Farmer/CS del Oro) or the Gong call is non-English
    (Spanish), what's the fallback? You mentioned translate + a human validation loop — who validates?
11. **Volume.** Roughly how many of these one-to-one pages per quarter? (If it's a handful of high-touch
    accounts, we right-size the tool; if it's dozens, we invest more in automation.)
12. **The RL→Belk deltas.** You made the Belk decisions from the RL page. Can you share that side-by-side
    (what you changed and why) as the canonical worked example / acceptance test for the tool?

---

## For the Web / Jahia dev team (module build + deploy — decided: configurator ships INSIDE Jahia)

13. **Framework.** Should the configurator be a **JSME** module (`javascript-modules-engine`, server-
    rendered React via `@jahia/js-server-engine`) or a **Moonstone admin extension**
    (`@jahia/moonstone` + `app-shell`, jContent-style operator tool)? Which fits an internal
    page-building tool in your setup?
14. **Toolchain + repo.** What's the module dev workflow — repo, `@jahia/` CLI/SDK versions, local
    Jahia dev instance, how modules are built (npm pack / Maven) and deployed?
15. **Ownership + contribution.** Who builds and maintains this module — the web team, or can Prism
    contribute a module into your repo/pipeline? Who reviews and deploys?
16. **Deploy environments.** Dev/staging/prod Jahia instances for a module; how a module is promoted;
    release cadence.
17. **The UX spec.** We have an approved clickable UX reference
    (`frontend/marketer/whale-configurator.html`) — split canvas, live preview, 9-module spine. Can
    the module implement against it, and does Moonstone/JSME support the live-preview pattern?

Owner: (assign) · Target answers by: (date) · Source of these: pre-mortem in
`~/.claude/plans/we-are-starting-a-velvet-eagle.md`.
