# PRISM IA A/B Prototype — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship two isolated, side-by-side IA prototypes of the homedepot-mexico audit — `/ia1` (browse-centric) and `/ia2` (chat-centric) — that differ only on the access axis, with an in-prototype feedback widget, without touching production.

**Architecture:** Self-contained client-side app inside the `prism-hub` repo under `ia/`. A shared core (pure `job-model.js` mapping the audit JSON to a 60-second brief + 6 seller jobs + prospect narrative + exports; plus shared HTML renderers and CSS) is consumed by two thin shells. Both shells fetch the *same* existing `homedepot-mexico-audit-data.json` and render the *same* panels; only the navigation paradigm differs (jobs rail vs. ask box). No server-side renderer, no framework, no build step. Deploys as static files via the existing zero-config path (commit + push → Vercel; `git pull` → VPS Caddy).

**Tech Stack:** Vanilla JS (ES modules, browser-native), HTML, CSS. Deno (already the repo's toolchain) for unit tests (`deno test`) and a structural-assert script. Existing `/api/chat` backend (`api/chat.js` on Vercel, `server/chat-proxy.mjs` on VPS) reused for chat. Chrome MCP tools for browser verification.

## Global Constraints

- **No em dashes** in any reader-facing text (templates, copy, generated strings). Rewrite grammar so it works without one. (Project rule.)
- **Production untouched:** `reports/`, every existing `/{slug}/` dir, `index.html`, `chat-widget.js`, `api/chat.js`, and `render-audit.ts` must be byte-for-byte unchanged. All new code lives under `prism-hub/ia/`. The ONLY permitted edit to an existing file is an *additive, reversible* `/api/feedback` route in `server/chat-proxy.mjs` (Task 6), guarded by a production-unchanged check on every other file.
- **A/B validity:** the two shells share the frozen data, the job-model, the brief, and the CSS skin identically. Any difference other than browse-vs-ask invalidates the test.
- **Data source (single, frozen):** `/homedepot-mexico-audit-data.json` (repo root, same-origin fetch). Never copy or fork it.
- **Slug binding:** chat must POST `slug: "homedepot-mexico"` in the request body (NOT inferred from the URL path).
- **Vendored skin:** brand tokens copied once from `~/.claude/skills/algolia-search-audit/templates/algolia-brand.css` into `ia/shared/brand-tokens.css`; both shells link it. No live dependency on the skills dir at runtime.
- **Repo:** `/Users/arijitchowdhury/prism` (git remote `origin` → `github.com/arijitchowdhury80/prism`, branch `main`). Commit there; this PIP repo holds only the spec/plan.

---

## File Structure (all new, under `prism-hub/ia/`)

```
prism-hub/
  ia/
    shared/
      brand-tokens.css     # vendored :root design tokens + font import (copied from algolia-brand.css)
      ia-shared.css        # prototype layout + component styles, built on the tokens
      job-model.js         # PURE: AUDIT_DATA -> {brief, jobs[6], prospect, exports}. The carve logic.
      job-model.test.js    # Deno.test unit tests for job-model.js
      render.js            # PURE-ish: model -> HTML strings for brief, a job panel, prospect narrative
      chat-client.js       # slug-forced chat client; POST /api/chat {message, slug:"homedepot-mexico", sid}
      feedback.js          # in-prototype feedback widget (POST /api/feedback)
    ia1/
      index.html           # browse shell: links shared, mounts ia1.js
      ia1.js               # assembles brief + always-visible jobs rail + panels + helper chat + mode toggle
    ia2/
      index.html           # chat shell: links shared, mounts ia2.js
      ia2.js               # assembles brief + ask-box hero + chips + chat-client + open-full + browse-all drawer + toggle
    index.html             # /ia compare landing: links both shells + cross-shell preference prompt
    verify.ts              # Deno structural-assert script (invariants + production-unchanged guard)
  api/
    feedback.js            # NEW Vercel lambda: append/forward feedback (Vercel deploy path)
  server/
    chat-proxy.mjs         # MODIFY (additive only): add /api/feedback -> append JSONL (VPS deploy path)
```

Data fed to the model (top-level keys present in `homedepot-mexico-audit-data.json`, confirmed): `meta, cover, score, company_snapshot, executives, intelligence_signals, competitors, findings, gap_pairs, toc, financials, traffic, tech_stack, hiring, strategic_angles, icp_mapping, competitive_synthesis, golden_angle, ae_fields, next_steps, methodology, bibliography, partner_intel, tab_subtitles, recommended_first_play, case_studies, abx_sequence, demos, industry_context`.

`ae_fields` keys: `ae_name, ae_email, next_step_action, next_step_owner, next_step_date, urgency_level, urgency_label, urgency_color, talk_track_opener, talk_track_cta, opportunity_headline, benchmark_proof`. (No `downloads` key — confirmed; that is why production's Downloads button is dead.)

**Carve map (data key → home). Locked in `job-model.js`:**

| Surface | Source keys |
|---|---|
| **Brief** | meta, cover, score, tech_stack (incumbent), intelligence_signals (top why-now), ae_fields (talk_track_opener, opportunity_headline, urgency_*, next_step_*), recommended_first_play, golden_angle |
| **Know the account** | company_snapshot, executives, financials, traffic, tech_stack, hiring, intelligence_signals, partner_intel, industry_context, competitors, competitive_synthesis, icp_mapping |
| **Prove it's broken** | score, findings, gap_pairs, toc, methodology, demos |
| **Make the money case** | gap_pairs, case_studies, strategic_angles, ae_fields (opportunity_headline, benchmark_proof), intelligence_signals (why-now) |
| **Know who decides** | icp_mapping, hiring, executives, ae_fields (next_step_owner) |
| **Run the conversation** | ae_fields (talk_track_opener, talk_track_cta), recommended_first_play, strategic_angles, competitors, competitive_synthesis, golden_angle |
| **Reach out** | abx_sequence |
| **Exports** | static links to existing `/homedepot-mexico/ae-report.html`, `/battle-card.html`, `/leave-behind.html` (+ any PDF present) |

**Known limitation (state in both shells identically):** some production content (full interactive ROI lever calculator, an explicit MEDDPICC object, a discrete discovery-questions list) is computed inside the 12k-line server template, not stored in the JSON. Where a key is absent, the panel renders the available JSON plus a labeled "computed in full report" stub — IDENTICAL in both shells, so parity holds. This is a navigation prototype; content completeness is not the variable under test.

---

## Task 1: Scaffold + vendored skin + isolation baseline

**Files:**
- Create: `prism-hub/ia/shared/brand-tokens.css`
- Create: `prism-hub/ia/shared/ia-shared.css`
- Create: `prism-hub/ia/verify.ts`
- Test: `prism-hub/ia/verify.ts` (acts as the structural-assert harness; first assertion is the isolation guard)

**Interfaces:**
- Produces: `ia-shared.css` exposing layout classes `.ia-brief`, `.ia-rail`, `.ia-panel`, `.ia-toggle`, `.ia-chip`, `.ia-ask` used by later tasks. Produces `verify.ts` with a `Deno.test`-style invariant set runnable via `deno test --allow-read --allow-run ia/verify.ts`.

- [ ] **Step 1: Capture the production baseline (the isolation guard's source of truth).**

Run from `/Users/arijitchowdhury/prism`:
```bash
git rev-parse HEAD > /tmp/ia_baseline_ref.txt
git ls-files reports index.html chat-widget.js api/chat.js server/chat-proxy.mjs > /tmp/ia_protected_files.txt
cat /tmp/ia_protected_files.txt
```
Expected: a list including `index.html`, `chat-widget.js`, `api/chat.js`, `server/chat-proxy.mjs`, and `reports/...`. This is the set that must not change (except the additive feedback route in chat-proxy, handled in Task 6).

- [ ] **Step 2: Vendor the brand tokens.**

```bash
mkdir -p /Users/arijitchowdhury/prism/ia/shared
cp ~/.claude/skills/algolia-search-audit/templates/algolia-brand.css \
   /Users/arijitchowdhury/prism/ia/shared/brand-tokens.css
```

- [ ] **Step 3: Write `ia-shared.css`** built on the vendored tokens. Minimal layout + components both shells reuse.

```css
/* ia/shared/ia-shared.css — built on brand-tokens.css custom properties */
* { box-sizing: border-box; }
body { margin: 0; font-family: var(--font-family, 'Sora', sans-serif); color: var(--brand-navy, #23263B); background: #fff; }
.ia-topbar { display:flex; gap:16px; align-items:center; padding:12px 20px; border-bottom:1px solid #eee; font-weight:600; }
.ia-verdict { padding:2px 10px; border-radius:var(--radius,8px); color:#fff; }
.ia-verdict.critical { background:#E11D48; } .ia-verdict.moderate { background:#F59E0B; } .ia-verdict.ok { background:#10B981; }
.ia-brief { padding:20px; display:grid; gap:12px; max-width:1100px; }
.ia-brief h2 { font-size:var(--font-h3,28px); margin:0 0 8px; }
.ia-brief .ia-brief-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; }
.ia-card { border:1px solid #eee; border-radius:var(--radius,8px); padding:14px; }
.ia-rail { display:flex; flex-direction:column; gap:6px; width:240px; padding:16px; border-right:1px solid #eee; }
.ia-rail button, .ia-chip { text-align:left; border:1px solid #e5e7eb; background:#fff; border-radius:8px; padding:10px 12px; cursor:pointer; font:inherit; }
.ia-rail button.active { background:var(--brand-blue,#003DFF); color:#fff; border-color:var(--brand-blue,#003DFF); }
.ia-layout { display:flex; min-height:70vh; }
.ia-panel { flex:1; padding:20px; max-width:900px; }
.ia-toggle { margin-left:auto; display:flex; gap:6px; }
.ia-ask { display:flex; gap:8px; margin:16px 0; max-width:1100px; }
.ia-ask input { flex:1; padding:12px; border:1px solid #d1d5db; border-radius:8px; font:inherit; }
.ia-chips { display:flex; flex-wrap:wrap; gap:8px; margin:8px 0 0; }
.ia-drawer { position:fixed; top:0; right:0; height:100vh; width:280px; background:#fff; border-left:1px solid #eee; transform:translateX(100%); transition:transform .2s; padding:16px; overflow:auto; }
.ia-drawer.open { transform:translateX(0); }
.ia-export-btn { font-size:13px; border:1px solid #d1d5db; border-radius:6px; padding:4px 8px; background:#fff; cursor:pointer; }
```

- [ ] **Step 4: Write the isolation-guard assertion in `verify.ts`.**

```ts
// ia/verify.ts — run: deno test --allow-read --allow-run ia/verify.ts
async function git(args: string[]): Promise<string> {
  const p = new Deno.Command("git", { args, stdout: "piped" });
  const { stdout } = await p.output();
  return new TextDecoder().decode(stdout).trim();
}

Deno.test("production files are unchanged vs baseline (only ia/ and additive feedback route allowed)", async () => {
  const changed = (await git(["diff", "--name-only", "HEAD"]))
    .split("\n").filter(Boolean);
  const offenders = changed.filter((f) =>
    !f.startsWith("ia/") &&
    f !== "api/feedback.js" &&
    f !== "server/chat-proxy.mjs"
  );
  if (offenders.length) throw new Error("Production files modified: " + offenders.join(", "));
});
```

- [ ] **Step 5: Run the guard to confirm it passes on a clean tree.**

Run: `cd /Users/arijitchowdhury/prism && deno test --allow-read --allow-run ia/verify.ts`
Expected: PASS (only `ia/` files are new/untracked, so `git diff HEAD` shows no tracked-file changes).

- [ ] **Step 6: Commit.**

```bash
cd /Users/arijitchowdhury/prism
git add ia/shared/brand-tokens.css ia/shared/ia-shared.css ia/verify.ts
git commit -m "feat(ia): scaffold prototype dir, vendored brand tokens, isolation guard"
```

---

## Task 2: `job-model.js` — the carve logic (real TDD)

**Files:**
- Create: `prism-hub/ia/shared/job-model.js`
- Test: `prism-hub/ia/shared/job-model.test.js`

**Interfaces:**
- Produces: `export function buildModel(data)` returning
  ```
  {
    brief: { company, oneLiner, score, verdict, damningFinding, incumbent, whyNow, sayFirst },
    jobs: [ { id, label, sections: [ { key, title, render } ] } ]  // exactly 6, in carve order
    prospect: { pain, evidence, value, proof, cta },
    exports: [ { label, href } ]
  }
  ```
  where each `sections[].render` is a string flag naming the renderer to use (resolved in Task 3), and `sections[].data` carries the slice. `verdict` is one of `"critical"|"moderate"|"ok"` derived from `score`. Job ids/labels are exactly: `account`/"Know the account", `broken`/"Prove it's broken", `money`/"Make the money case", `who`/"Know who decides", `convo`/"Run the conversation", `reach`/"Reach out".

- [ ] **Step 1: Write the failing tests** in `job-model.test.js`.

```js
import { assertEquals, assert } from "https://deno.land/std@0.224.0/assert/mod.ts";
import { buildModel } from "./job-model.js";

const data = JSON.parse(await Deno.readTextFile(new URL("../../homedepot-mexico-audit-data.json", import.meta.url)));

Deno.test("brief surfaces company + score-derived verdict", () => {
  const m = buildModel(data);
  assert(m.brief.company && m.brief.company.length > 0);
  assert(["critical", "moderate", "ok"].includes(m.brief.verdict));
  assert(typeof m.brief.score === "number");
});

Deno.test("exactly six jobs in the locked carve order", () => {
  const m = buildModel(data);
  assertEquals(m.jobs.map((j) => j.id), ["account", "broken", "money", "who", "convo", "reach"]);
  assertEquals(m.jobs.map((j) => j.label), [
    "Know the account", "Prove it's broken", "Make the money case",
    "Know who decides", "Run the conversation", "Reach out",
  ]);
});

Deno.test("every job has at least one section", () => {
  const m = buildModel(data);
  for (const j of m.jobs) assert(j.sections.length >= 1, `job ${j.id} empty`);
});

Deno.test("findings feed the 'broken' job", () => {
  const m = buildModel(data);
  const broken = m.jobs.find((j) => j.id === "broken");
  assert(broken.sections.some((s) => s.key === "findings"));
});

Deno.test("abx_sequence feeds the 'reach' job", () => {
  const m = buildModel(data);
  const reach = m.jobs.find((j) => j.id === "reach");
  assert(reach.sections.some((s) => s.key === "abx"));
});

Deno.test("exports link to existing deliverable pages", () => {
  const m = buildModel(data);
  const hrefs = m.exports.map((e) => e.href);
  assert(hrefs.includes("/homedepot-mexico/ae-report.html"));
  assert(hrefs.includes("/homedepot-mexico/battle-card.html"));
  assert(hrefs.includes("/homedepot-mexico/leave-behind.html"));
});

Deno.test("prospect view excludes internal-only surfaces", () => {
  const m = buildModel(data);
  const blob = JSON.stringify(m.prospect).toLowerCase();
  assert(!blob.includes("meddpicc"));
  assert(!blob.includes("abx"));
});
```

- [ ] **Step 2: Run tests to verify they fail.**

Run: `cd /Users/arijitchowdhury/prism && deno test --allow-read ia/shared/job-model.test.js`
Expected: FAIL with "Module not found" / `buildModel is not a function`.

- [ ] **Step 3: Implement `job-model.js`.**

```js
// ia/shared/job-model.js — pure transform: audit JSON -> brief + 6 jobs + prospect + exports
const SLUG = "homedepot-mexico";

function verdictFromScore(score) {
  const n = typeof score === "number" ? score : Number(score?.overall ?? score?.value ?? 0);
  if (n <= 4) return "critical";
  if (n <= 7) return "moderate";
  return "ok";
}

function scoreNumber(score) {
  return typeof score === "number" ? score : Number(score?.overall ?? score?.value ?? 0);
}

function topWhyNow(signals) {
  const arr = Array.isArray(signals) ? signals : (signals?.items ?? []);
  return arr.slice(0, 3);
}

export function buildModel(data) {
  const ae = data.ae_fields ?? {};
  const brief = {
    company: data.company_snapshot?.name ?? data.meta?.company ?? data.cover?.company ?? SLUG,
    oneLiner: data.company_snapshot?.description ?? data.cover?.subtitle ?? "",
    score: scoreNumber(data.score),
    verdict: verdictFromScore(data.score),
    damningFinding: (Array.isArray(data.findings) ? data.findings[0]?.title : data.findings?.[0]?.title) ?? ae.opportunity_headline ?? "",
    incumbent: data.tech_stack?.search_vendor ?? data.tech_stack?.search ?? "unknown",
    whyNow: topWhyNow(data.intelligence_signals),
    sayFirst: { opener: ae.talk_track_opener ?? "", cta: ae.talk_track_cta ?? "", play: data.recommended_first_play ?? null },
  };

  // section() carries a render-flag (resolved in render.js) + its data slice
  const S = (key, title, render, slice) => ({ key, title, render, data: slice });

  const jobs = [
    { id: "account", label: "Know the account", sections: [
      S("company", "Company snapshot", "kv", data.company_snapshot),
      S("execs", "Executives", "list", data.executives),
      S("financials", "Financials", "kv", data.financials),
      S("traffic", "Traffic", "kv", data.traffic),
      S("techstack", "Tech stack", "kv", data.tech_stack),
      S("hiring", "Hiring signals", "list", data.hiring),
      S("signals", "News & social signals", "list", data.intelligence_signals),
      S("partner", "Partner intel", "list", data.partner_intel),
      S("industry", "Industry context", "kv", data.industry_context),
      S("competitors", "Competitors", "list", data.competitors),
      S("competitive", "Competitive synthesis", "kv", data.competitive_synthesis),
      S("icp", "ICP mapping", "kv", data.icp_mapping),
    ].filter((s) => s.data != null) },
    { id: "broken", label: "Prove it's broken", sections: [
      S("score", "Score by dimension", "kv", data.score),
      S("findings", "Findings", "findings", data.findings),
      S("gaps", "Gap pairs (Said vs Found)", "pairs", data.gap_pairs),
      S("queries", "Test queries / methodology", "kv", data.methodology),
      S("demos", "Demos", "list", data.demos),
    ].filter((s) => s.data != null) },
    { id: "money", label: "Make the money case", sections: [
      S("gaps", "Said vs Found", "pairs", data.gap_pairs),
      S("proof", "Customer proof", "list", data.case_studies),
      S("angles", "Strategic angles", "list", data.strategic_angles),
      S("opportunity", "Opportunity", "kv", { headline: ae.opportunity_headline, proof: ae.benchmark_proof }),
    ].filter((s) => s.data != null) },
    { id: "who", label: "Know who decides", sections: [
      S("icp", "Buying committee (ICP)", "kv", data.icp_mapping),
      S("hiring", "Hiring as buying signal", "list", data.hiring),
      S("execs", "Power map", "list", data.executives),
      S("nextowner", "Next-step owner", "kv", { owner: ae.next_step_owner, action: ae.next_step_action, date: ae.next_step_date }),
    ].filter((s) => s.data != null) },
    { id: "convo", label: "Run the conversation", sections: [
      S("talk", "Talk track", "kv", { opener: ae.talk_track_opener, cta: ae.talk_track_cta }),
      S("firstplay", "Recommended first play", "kv", data.recommended_first_play),
      S("angles", "Discovery angles", "list", data.strategic_angles),
      S("battle", "Battle card", "kv", data.competitive_synthesis),
      S("golden", "Golden angle", "kv", data.golden_angle),
    ].filter((s) => s.data != null) },
    { id: "reach", label: "Reach out", sections: [
      S("abx", "ABX sequence", "abx", data.abx_sequence),
    ].filter((s) => s.data != null) },
  ];

  const prospect = {
    pain: brief.damningFinding,
    evidence: data.findings ?? [],
    value: { headline: ae.opportunity_headline ?? "", proof: ae.benchmark_proof ?? "", gaps: data.gap_pairs ?? [] },
    proof: data.case_studies ?? [],
    cta: { action: ae.next_step_action ?? "Book a follow-up", owner: ae.ae_name ?? "" },
  };

  const exports = [
    { label: "AE pre-call brief", href: `/${SLUG}/ae-report.html` },
    { label: "Battle card", href: `/${SLUG}/battle-card.html` },
    { label: "Leave-behind", href: `/${SLUG}/leave-behind.html` },
  ];

  return { brief, jobs, prospect, exports };
}
```

- [ ] **Step 4: Run tests to verify they pass.**

Run: `cd /Users/arijitchowdhury/prism && deno test --allow-read ia/shared/job-model.test.js`
Expected: PASS (7 tests). If a key-name assumption is wrong (e.g. `company_snapshot.name`), fix the accessor in `job-model.js` to match the actual JSON and re-run — do not change the test's intent.

- [ ] **Step 5: Commit.**

```bash
git add ia/shared/job-model.js ia/shared/job-model.test.js
git commit -m "feat(ia): job-model carve (audit JSON -> brief + 6 jobs + prospect + exports) with tests"
```

---

## Task 3: `render.js` — shared HTML renderers

**Files:**
- Create: `prism-hub/ia/shared/render.js`
- Test: add cases to `prism-hub/ia/shared/job-model.test.js` (renderers are pure string functions)

**Interfaces:**
- Consumes: the model from `buildModel(data)`.
- Produces: `export function renderBrief(brief)`, `export function renderPanel(job)`, `export function renderProspect(prospect)`, `export function renderExports(exports)` — each returns an HTML string. `renderPanel` dispatches on `section.render` ("kv"|"list"|"findings"|"pairs"|"abx"). All escape user/data text via an internal `esc()`.

- [ ] **Step 1: Write failing render tests** (append to `job-model.test.js`).

```js
import { renderBrief, renderPanel, renderProspect } from "./render.js";

Deno.test("renderBrief contains company and verdict class", () => {
  const m = buildModel(data);
  const html = renderBrief(m.brief);
  assert(html.includes(m.brief.company));
  assert(html.includes(`ia-verdict ${m.brief.verdict}`));
});

Deno.test("renderPanel for 'reach' renders abx", () => {
  const m = buildModel(data);
  const reach = m.jobs.find((j) => j.id === "reach");
  const html = renderPanel(reach);
  assert(html.includes("ABX") || html.toLowerCase().includes("email"));
});

Deno.test("renderers never emit an em dash", () => {
  const m = buildModel(data);
  const all = renderBrief(m.brief) + m.jobs.map(renderPanel).join("") + renderProspect(m.prospect);
  assert(!all.includes("—"), "em dash found in rendered output");
});
```

- [ ] **Step 2: Run to verify fail.**

Run: `deno test --allow-read ia/shared/job-model.test.js`
Expected: FAIL ("Module not found" for `render.js`).

- [ ] **Step 3: Implement `render.js`.**

```js
// ia/shared/render.js — pure model -> HTML string renderers (no em dashes in output)
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function kv(obj) {
  if (obj == null) return "";
  if (typeof obj !== "object") return `<p>${esc(obj)}</p>`;
  return `<dl class="ia-kv">` + Object.entries(obj)
    .filter(([, v]) => v != null && typeof v !== "object")
    .map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("") + `</dl>`;
}
function list(arr) {
  const a = Array.isArray(arr) ? arr : (arr?.items ?? Object.values(arr ?? {}));
  return `<ul class="ia-list">` + (a || []).map((it) =>
    `<li>${esc(typeof it === "object" ? (it.title ?? it.name ?? it.headline ?? JSON.stringify(it).slice(0, 200)) : it)}</li>`
  ).join("") + `</ul>`;
}
function findings(arr) {
  const a = Array.isArray(arr) ? arr : [];
  return a.map((f) =>
    `<div class="ia-card"><strong>${esc(f.title ?? f.id ?? "Finding")}</strong>` +
    (f.severity ? ` <span class="ia-verdict ${esc((f.severity || "").toLowerCase())}">${esc(f.severity)}</span>` : "") +
    (f.detail || f.summary ? `<p>${esc(f.detail ?? f.summary)}</p>` : "") + `</div>`
  ).join("");
}
function pairs(arr) {
  const a = Array.isArray(arr) ? arr : [];
  return `<table class="ia-pairs"><tr><th>They said</th><th>We found</th></tr>` +
    a.map((p) => `<tr><td>${esc(p.said ?? p.quote ?? "")}</td><td>${esc(p.found ?? p.finding ?? "")}</td></tr>`).join("") + `</table>`;
}
function abx(seq) {
  const a = Array.isArray(seq) ? seq : (seq?.emails ?? seq?.steps ?? []);
  return `<ol class="ia-abx">` + a.map((e) =>
    `<li><strong>${esc(e.subject ?? e.step ?? "Email")}</strong><p>${esc((e.body ?? e.text ?? "").slice(0, 400))}</p></li>`
  ).join("") + `</ol>`;
}
const DISPATCH = { kv, list, findings, pairs, abx };

export function renderBrief(brief) {
  const whyNow = (brief.whyNow || []).map((s) => `<li>${esc(typeof s === "object" ? (s.headline ?? s.title ?? JSON.stringify(s).slice(0,160)) : s)}</li>`).join("");
  return `
    <section class="ia-brief">
      <h2>${esc(brief.company)} <span class="ia-verdict ${brief.verdict}">${brief.score}/10 ${esc(brief.verdict.toUpperCase())}</span></h2>
      <p>${esc(brief.oneLiner)}</p>
      <div class="ia-brief-grid">
        <div class="ia-card"><strong>The one damning finding</strong><p>${esc(brief.damningFinding)}</p></div>
        <div class="ia-card"><strong>Incumbent</strong><p>${esc(brief.incumbent)}</p></div>
        <div class="ia-card"><strong>Why now</strong><ul>${whyNow}</ul></div>
        <div class="ia-card"><strong>Say this first</strong><p>${esc(brief.sayFirst.opener)}</p></div>
      </div>
    </section>`;
}
export function renderPanel(job) {
  return `<div class="ia-panel" data-job="${esc(job.id)}"><h3>${esc(job.label)}</h3>` +
    job.sections.map((s) => `<section class="ia-section" data-key="${esc(s.key)}"><h4>${esc(s.title)} <button class="ia-export-btn" data-export="${esc(s.key)}">Export</button></h4>${(DISPATCH[s.render] || kv)(s.data)}</section>`).join("") +
    `</div>`;
}
export function renderProspect(p) {
  return `
    <div class="ia-panel ia-prospect">
      <section class="ia-card"><h3>The problem</h3><p>${esc(p.pain)}</p></section>
      <section class="ia-card"><h3>The evidence</h3>${findings(p.evidence)}</section>
      <section class="ia-card"><h3>The value</h3><p>${esc(p.value.headline)}</p>${pairs(p.value.gaps)}</section>
      <section class="ia-card"><h3>Proof</h3>${list(p.proof)}</section>
      <section class="ia-card"><h3>Next step</h3><p>${esc(p.cta.action)}</p></section>
    </div>`;
}
export function renderExports(exports) {
  return `<div class="ia-exports">` + exports.map((e) => `<a class="ia-export-btn" href="${esc(e.href)}" target="_blank" rel="noopener">${esc(e.label)}</a>`).join("") + `</div>`;
}
```

- [ ] **Step 4: Run tests to verify pass.**

Run: `deno test --allow-read ia/shared/job-model.test.js`
Expected: PASS (all job-model + render tests). Fix accessor mismatches against real JSON shapes if the abx/findings/pairs assertions fail, keeping test intent.

- [ ] **Step 5: Commit.**

```bash
git add ia/shared/render.js ia/shared/job-model.test.js
git commit -m "feat(ia): shared HTML renderers (brief, job panel, prospect, exports)"
```

---

## Task 4: `chat-client.js` — slug-forced chat (shared by both shells)

**Files:**
- Create: `prism-hub/ia/shared/chat-client.js`

**Interfaces:**
- Produces: `export function createChat({ mount, onOpenFull })` returning `{ send(text), el }`. Internally POSTs `/api/chat` with body `{ message, slug: "homedepot-mexico", sid }` (sid from `localStorage.prism_ia_sid`), streams the text response, and renders messages into `mount`. When a reply references a job, it appends an "Open full" button that calls `onOpenFull(jobId)`.

- [ ] **Step 1: Implement `chat-client.js`** (no unit test — verified live in browser at Task 5/7; logic is a thin fetch wrapper).

```js
// ia/shared/chat-client.js — reuses the existing /api/chat backend, forces the correct slug
const SLUG = "homedepot-mexico";
const JOB_HINTS = [
  { re: /battle|competitor|constructor|coveo/i, job: "convo" },
  { re: /roi|revenue|money|value|opportunity/i, job: "money" },
  { re: /finding|broken|search quality|zero result/i, job: "broken" },
  { re: /who|buyer|committee|champion|meddpicc/i, job: "who" },
  { re: /email|outreach|abx|sequence|linkedin/i, job: "reach" },
  { re: /company|traffic|stack|hiring|financial/i, job: "account" },
];
function sid() {
  let s = localStorage.getItem("prism_ia_sid");
  if (!s) { s = "ia-" + Math.abs(Date.now() ^ (location.pathname.length * 2654435761)).toString(36); localStorage.setItem("prism_ia_sid", s); }
  return s;
}
export function createChat({ mount, onOpenFull }) {
  const log = document.createElement("div");
  log.className = "ia-chatlog";
  mount.appendChild(log);
  function bubble(role, text) {
    const d = document.createElement("div");
    d.className = "ia-msg ia-" + role;
    d.textContent = text;
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
    return d;
  }
  async function send(text) {
    if (!text || !text.trim()) return;
    bubble("user", text);
    const out = bubble("bot", "");
    try {
      const res = await fetch("/api/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, slug: SLUG, sid: sid() }),
      });
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let full = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        full += dec.decode(value, { stream: true });
        out.textContent = full;
        log.scrollTop = log.scrollHeight;
      }
      const hint = JOB_HINTS.find((h) => h.re.test(text) || h.re.test(full));
      if (hint && onOpenFull) {
        const btn = document.createElement("button");
        btn.className = "ia-export-btn";
        btn.textContent = "Open full";
        btn.onclick = () => onOpenFull(hint.job);
        out.appendChild(document.createElement("br"));
        out.appendChild(btn);
      }
    } catch (e) {
      out.textContent = "Chat is unavailable right now.";
    }
  }
  return { send, el: log };
}
```

- [ ] **Step 2: Commit.**

```bash
git add ia/shared/chat-client.js
git commit -m "feat(ia): slug-forced chat client reusing /api/chat backend"
```

---

## Task 5: IA1 shell (browse-centric)

**Files:**
- Create: `prism-hub/ia/ia1/index.html`
- Create: `prism-hub/ia/ia1/ia1.js`

**Interfaces:**
- Consumes: `buildModel`, `renderBrief`, `renderPanel`, `renderProspect`, `renderExports` from `../shared/`, `createChat` from `../shared/chat-client.js`.
- Produces: a live page at `/ia/ia1/` (and `/ia1/` after the deploy-time symlink/copy in Task 9) showing the brief, an always-visible 6-job rail, panels on click, a helper chat in a corner drawer, and a Seller/Prospect mode toggle.

- [ ] **Step 1: Write `ia1/index.html`.**

```html
<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PRISM IA1 (browse) — Home Depot Mexico</title>
<link rel="stylesheet" href="../shared/brand-tokens.css">
<link rel="stylesheet" href="../shared/ia-shared.css">
</head><body>
<div class="ia-topbar"><strong id="ia-title">PRISM</strong>
  <span class="ia-toggle"><button id="m-seller" class="active">Seller</button><button id="m-prospect">Prospect</button></span>
</div>
<div id="ia-brief-host"></div>
<div class="ia-layout">
  <nav class="ia-rail" id="ia-rail"></nav>
  <main id="ia-main"></main>
</div>
<button id="ia-chat-toggle" class="ia-export-btn" style="position:fixed;bottom:20px;right:20px;">Ask aRRIe</button>
<aside class="ia-drawer" id="ia-chat-drawer"><h4>Ask about this audit</h4><div id="ia-chat-mount"></div>
  <div class="ia-ask"><input id="ia-chat-input" placeholder="Ask..."><button id="ia-chat-send">Send</button></div>
</aside>
<script type="module" src="./ia1.js"></script>
</body></html>
```

- [ ] **Step 2: Write `ia1/ia1.js`.**

```js
import { buildModel } from "../shared/job-model.js";
import { renderBrief, renderPanel, renderProspect, renderExports } from "../shared/render.js";
import { createChat } from "../shared/chat-client.js";
import { mountFeedback } from "../shared/feedback.js";

const data = await (await fetch("/homedepot-mexico-audit-data.json")).json();
const model = buildModel(data);
let mode = "seller";

document.getElementById("ia-title").textContent = "PRISM IA1 (browse) " + model.brief.company;
document.getElementById("ia-brief-host").innerHTML = renderBrief(model.brief);

const rail = document.getElementById("ia-rail");
const main = document.getElementById("ia-main");

function showJob(id) {
  const job = model.jobs.find((j) => j.id === id);
  main.innerHTML = renderPanel(job) + renderExports(model.exports);
  [...rail.children].forEach((b) => b.classList.toggle("active", b.dataset.job === id));
}
function renderRail() {
  rail.innerHTML = "";
  model.jobs.forEach((j) => {
    const b = document.createElement("button");
    b.dataset.job = j.id; b.textContent = j.label;
    b.onclick = () => showJob(j.id);
    rail.appendChild(b);
  });
}
function applyMode() {
  document.getElementById("m-seller").classList.toggle("active", mode === "seller");
  document.getElementById("m-prospect").classList.toggle("active", mode === "prospect");
  if (mode === "prospect") { rail.style.display = "none"; main.innerHTML = renderProspect(model.prospect); }
  else { rail.style.display = ""; renderRail(); showJob("account"); }
}
document.getElementById("m-seller").onclick = () => { mode = "seller"; applyMode(); };
document.getElementById("m-prospect").onclick = () => { mode = "prospect"; applyMode(); };

const chat = createChat({ mount: document.getElementById("ia-chat-mount"), onOpenFull: (job) => { mode = "seller"; applyMode(); showJob(job); } });
document.getElementById("ia-chat-toggle").onclick = () => document.getElementById("ia-chat-drawer").classList.toggle("open");
document.getElementById("ia-chat-send").onclick = () => { const i = document.getElementById("ia-chat-input"); chat.send(i.value); i.value = ""; };

applyMode();
mountFeedback("ia1");
```

- [ ] **Step 3: Serve and verify in the browser.**

Run a static server from the repo root:
```bash
cd /Users/arijitchowdhury/prism && python3 -m http.server 8777 >/tmp/ia_http.log 2>&1 &
```
Then with the Chrome MCP: `navigate_page` to `http://localhost:8777/ia/ia1/`, and `evaluate_script`:
```js
({
  title: document.getElementById("ia-title").textContent,
  railCount: document.querySelectorAll("#ia-rail button").length,
  hasBrief: !!document.querySelector(".ia-brief"),
})
```
Expected: `railCount === 6`, `hasBrief === true`, title contains the company name. `take_screenshot` for the record.

- [ ] **Step 4: Verify mode toggle.**

With `evaluate_script`: click `#m-prospect`, then assert `document.querySelector(".ia-prospect") !== null` and `getComputedStyle(document.getElementById("ia-rail")).display === "none"`.
Expected: both true.

- [ ] **Step 5: Commit.**

```bash
git add ia/ia1/index.html ia/ia1/ia1.js
git commit -m "feat(ia): IA1 browse shell (brief + jobs rail + panels + helper chat + mode toggle)"
```

(Note: `mountFeedback` is imported here but created in Task 6; if executing strictly in order, comment the import+call, then uncomment in Task 6. Subagent-driven execution: do Task 6 before browser-verifying Task 5's feedback path.)

---

## Task 6: Feedback widget + capture backend

**Files:**
- Create: `prism-hub/ia/shared/feedback.js`
- Create: `prism-hub/api/feedback.js` (Vercel path)
- Modify (additive only): `prism-hub/server/chat-proxy.mjs` (VPS path)

**Interfaces:**
- Produces: `export function mountFeedback(shell)` — injects a small fixed widget capturing `{ shell, rating, text, preference, sid }` and POSTing to `/api/feedback`. `shell` is `"ia1"` or `"ia2"`.
- `/api/feedback` accepts `POST {shell, rating, text, preference, sid}` and appends one JSONL line; returns `{ ok: true }`.

- [ ] **Step 1: Implement `feedback.js`.**

```js
// ia/shared/feedback.js — in-prototype feedback widget
export function mountFeedback(shell) {
  const sid = localStorage.getItem("prism_ia_sid") || "anon";
  const box = document.createElement("div");
  box.style.cssText = "position:fixed;bottom:20px;left:20px;z-index:9999;";
  box.innerHTML = `<details class="ia-card" style="max-width:300px;background:#fff;">
    <summary>Feedback on this view</summary>
    <p>Easy to find what you needed?</p>
    <button data-r="easy">Easy</button> <button data-r="ok">OK</button> <button data-r="hard">Confusing</button>
    <textarea id="ia-fb-text" placeholder="What was missing or confusing?" style="width:100%;margin-top:8px;"></textarea>
    <p>Which approach do you prefer overall?</p>
    <button data-p="ia1">Browse (IA1)</button> <button data-p="ia2">Chat (IA2)</button>
    <div id="ia-fb-done" style="color:green;"></div>
  </details>`;
  document.body.appendChild(box);
  let rating = "", preference = "";
  async function post() {
    try {
      await fetch("/api/feedback", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ shell, rating, preference, text: box.querySelector("#ia-fb-text").value, sid }) });
      box.querySelector("#ia-fb-done").textContent = "Thanks, recorded.";
    } catch { box.querySelector("#ia-fb-done").textContent = "Saved locally."; }
    localStorage.setItem("prism_ia_fb_" + shell, JSON.stringify({ rating, preference, t: box.querySelector("#ia-fb-text").value }));
  }
  box.querySelectorAll("[data-r]").forEach((b) => b.onclick = () => { rating = b.dataset.r; post(); });
  box.querySelectorAll("[data-p]").forEach((b) => b.onclick = () => { preference = b.dataset.p; post(); });
}
```

- [ ] **Step 2: Implement `api/feedback.js`** (Vercel; appends to /tmp on lambda, also echoes — primary durable capture is the VPS path in Step 3).

```js
// api/feedback.js — Vercel Node lambda. Stateless FS, so this forwards to console + returns ok.
// Durable capture for prism.chowmes.com is the VPS chat-proxy route (Step 3).
export default async function handler(req, res) {
  if (req.method !== "POST") { res.status(405).json({ ok: false }); return; }
  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
  console.log("IA_FEEDBACK", JSON.stringify({ ...body, ts: new Date().toISOString() }));
  res.status(200).json({ ok: true });
}
```

- [ ] **Step 3: Add an additive `/api/feedback` route to `server/chat-proxy.mjs`** (VPS, has disk). Locate the existing request router (the `if (req.url === "/api/chat")` block) and add a sibling branch BEFORE it. Show the exact added block:

```js
// --- IA prototype feedback capture (additive; does not touch /api/chat) ---
if (req.method === "POST" && req.url === "/api/feedback") {
  let raw = "";
  req.on("data", (c) => (raw += c));
  req.on("end", () => {
    try {
      const rec = { ...JSON.parse(raw || "{}"), ts: new Date().toISOString() };
      import("node:fs").then((fs) =>
        fs.appendFileSync(process.env.IA_FEEDBACK_FILE || "/opt/prism-hub-feedback.jsonl", JSON.stringify(rec) + "\n"));
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: true }));
    } catch {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: false }));
    }
  });
  return;
}
```

- [ ] **Step 4: Verify isolation guard still passes** (chat-proxy edit is on the allowlist; nothing else changed).

Run: `cd /Users/arijitchowdhury/prism && deno test --allow-read --allow-run ia/verify.ts`
Expected: PASS (only `ia/`, `api/feedback.js`, `server/chat-proxy.mjs` changed).

- [ ] **Step 5: Verify the chat-proxy still parses + starts** (syntax check the additive edit).

Run: `node --check /Users/arijitchowdhury/prism/server/chat-proxy.mjs`
Expected: no output, exit 0.

- [ ] **Step 6: Browser-verify feedback POST** (local server from Task 5 still running). With Chrome MCP on `/ia/ia1/`, `evaluate_script`:
```js
fetch("/api/feedback", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({shell:"ia1",rating:"easy",sid:"test"})}).then(r=>r.status)
```
Note: `python3 -m http.server` has no `/api`, so this returns 501/404 locally — that is expected. Real capture is verified post-deploy in Task 9 against the live VPS. Locally, just confirm the widget renders: assert `document.querySelector("details") !== null` after `mountFeedback` ran.

- [ ] **Step 7: Commit.**

```bash
git add ia/shared/feedback.js api/feedback.js server/chat-proxy.mjs
git commit -m "feat(ia): in-prototype feedback widget + additive /api/feedback capture (Vercel + VPS)"
```

---

## Task 7: IA2 shell (chat-centric)

**Files:**
- Create: `prism-hub/ia/ia2/index.html`
- Create: `prism-hub/ia/ia2/ia2.js`

**Interfaces:**
- Consumes: same shared modules as IA1.
- Produces: a live page at `/ia/ia2/` showing the brief + an ask box hero + seeded chips + the chat client as the primary surface, an "open full" deep-link into the same panels IA1 renders, a "browse all" drawer holding the 6-job rail, and the Seller/Prospect toggle.

- [ ] **Step 1: Write `ia2/index.html`.**

```html
<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PRISM IA2 (chat) — Home Depot Mexico</title>
<link rel="stylesheet" href="../shared/brand-tokens.css">
<link rel="stylesheet" href="../shared/ia-shared.css">
</head><body>
<div class="ia-topbar"><strong id="ia-title">PRISM</strong>
  <span class="ia-toggle"><button id="m-seller" class="active">Seller</button><button id="m-prospect">Prospect</button></span>
  <button id="ia-browse-all" class="ia-export-btn">Browse all</button>
</div>
<div id="ia-brief-host"></div>
<div class="ia-ask"><input id="ia-ask-input" placeholder="Ask aRRIe anything about this account..."><button id="ia-ask-send">Ask</button></div>
<div class="ia-chips" id="ia-chips"></div>
<main id="ia-chat-mount"></main>
<aside class="ia-drawer" id="ia-browse-drawer"><h4>Browse all</h4><nav class="ia-rail" id="ia-rail"></nav></aside>
<div id="ia-panel-host"></div>
<script type="module" src="./ia2.js"></script>
</body></html>
```

- [ ] **Step 2: Write `ia2/ia2.js`.**

```js
import { buildModel } from "../shared/job-model.js";
import { renderBrief, renderPanel, renderProspect, renderExports } from "../shared/render.js";
import { createChat } from "../shared/chat-client.js";
import { mountFeedback } from "../shared/feedback.js";

const data = await (await fetch("/homedepot-mexico-audit-data.json")).json();
const model = buildModel(data);
let mode = "seller";

document.getElementById("ia-title").textContent = "PRISM IA2 (chat) " + model.brief.company;
document.getElementById("ia-brief-host").innerHTML = renderBrief(model.brief);

const panelHost = document.getElementById("ia-panel-host");
function showJob(id) {
  const job = model.jobs.find((j) => j.id === id);
  panelHost.innerHTML = renderPanel(job) + renderExports(model.exports);
  panelHost.scrollIntoView({ behavior: "smooth" });
}

const chat = createChat({ mount: document.getElementById("ia-chat-mount"), onOpenFull: showJob });
document.getElementById("ia-ask-send").onclick = () => { const i = document.getElementById("ia-ask-input"); chat.send(i.value); i.value = ""; };

const CHIPS = [
  ["battle card vs incumbent", "convo"], ["ROI at +2% conversion", "money"],
  ["who's on the call", "who"], ["what do I send after the call", "reach"],
  ["how bad is their search", "broken"], ["company snapshot", "account"],
];
const chipHost = document.getElementById("ia-chips");
CHIPS.forEach(([label]) => {
  const c = document.createElement("button");
  c.className = "ia-chip"; c.textContent = label;
  c.onclick = () => chat.send(label);
  chipHost.appendChild(c);
});

const rail = document.getElementById("ia-rail");
model.jobs.forEach((j) => {
  const b = document.createElement("button");
  b.dataset.job = j.id; b.textContent = j.label;
  b.onclick = () => { showJob(j.id); document.getElementById("ia-browse-drawer").classList.remove("open"); };
  rail.appendChild(b);
});
document.getElementById("ia-browse-all").onclick = () => document.getElementById("ia-browse-drawer").classList.toggle("open");

function applyMode() {
  document.getElementById("m-seller").classList.toggle("active", mode === "seller");
  document.getElementById("m-prospect").classList.toggle("active", mode === "prospect");
  const sellerOnly = [document.querySelector(".ia-ask"), chipHost, document.getElementById("ia-chat-mount"), document.getElementById("ia-browse-all")];
  if (mode === "prospect") { sellerOnly.forEach((e) => e.style.display = "none"); panelHost.innerHTML = renderProspect(model.prospect); }
  else { sellerOnly.forEach((e) => e.style.display = ""); panelHost.innerHTML = ""; }
}
document.getElementById("m-seller").onclick = () => { mode = "seller"; applyMode(); };
document.getElementById("m-prospect").onclick = () => { mode = "prospect"; applyMode(); };

applyMode();
mountFeedback("ia2");
```

- [ ] **Step 3: Browser-verify IA2.** Chrome MCP `navigate_page` to `http://localhost:8777/ia/ia2/`, `evaluate_script`:
```js
({ chips: document.querySelectorAll("#ia-chips .ia-chip").length, hasAsk: !!document.querySelector(".ia-ask"), railInDrawer: document.querySelectorAll("#ia-browse-drawer #ia-rail button").length })
```
Expected: `chips === 6`, `hasAsk === true`, `railInDrawer === 6`. Screenshot for the record.

- [ ] **Step 4: Verify "open full" renders the same panel as IA1.** `evaluate_script`: call the rail button for `money`, assert `document.querySelector('[data-job="money"]') !== null` in `#ia-panel-host`.
Expected: true (same `renderPanel` output as IA1, proving shared core).

- [ ] **Step 5: Commit.**

```bash
git add ia/ia2/index.html ia/ia2/ia2.js
git commit -m "feat(ia): IA2 chat shell (brief + ask hero + chips + open-full + browse-all drawer + toggle)"
```

---

## Task 8: `/ia` compare landing

**Files:**
- Create: `prism-hub/ia/index.html`

**Interfaces:**
- Produces: a page at `/ia/` linking both shells side by side, framing the comparison for testers.

- [ ] **Step 1: Write `ia/index.html`.**

```html
<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PRISM IA prototypes — compare</title>
<link rel="stylesheet" href="./shared/brand-tokens.css">
<link rel="stylesheet" href="./shared/ia-shared.css">
</head><body>
<div class="ia-brief">
  <h2>Two ways to use a PRISM audit. Tell us which works.</h2>
  <p>Same Home Depot Mexico audit, two layouts. Open each, try to prep a call, then leave feedback in either.</p>
  <div class="ia-brief-grid">
    <a class="ia-card" href="./ia1/"><strong>IA1 — Browse</strong><p>A jobs menu you click through. The map is on screen.</p></a>
    <a class="ia-card" href="./ia2/"><strong>IA2 — Chat</strong><p>Ask for what you need. The page answers.</p></a>
  </div>
</div>
<script type="module">import { mountFeedback } from "./shared/feedback.js"; mountFeedback("compare");</script>
</body></html>
```

- [ ] **Step 2: Browser-verify.** Chrome MCP to `http://localhost:8777/ia/`, assert two `.ia-card` links with hrefs `./ia1/` and `./ia2/`.

- [ ] **Step 3: Commit.**

```bash
git add ia/index.html
git commit -m "feat(ia): compare landing linking IA1 and IA2"
```

---

## Task 9: A/B parity + production-isolation verification

**Files:**
- Modify: `prism-hub/ia/verify.ts` (add parity + presence assertions)

**Interfaces:**
- Produces: an expanded `verify.ts` that asserts (a) production unchanged, (b) both shells exist, (c) both shells consume the identical shared core (same job-model, same CSS).

- [ ] **Step 1: Add parity assertions to `verify.ts`.**

```ts
Deno.test("both shells exist and link the same shared core", async () => {
  const ia1 = await Deno.readTextFile("ia/ia1/index.html");
  const ia2 = await Deno.readTextFile("ia/ia2/index.html");
  for (const html of [ia1, ia2]) {
    if (!html.includes("../shared/brand-tokens.css")) throw new Error("shell missing brand-tokens");
    if (!html.includes("../shared/ia-shared.css")) throw new Error("shell missing ia-shared css");
  }
  const ia1js = await Deno.readTextFile("ia/ia1/ia1.js");
  const ia2js = await Deno.readTextFile("ia/ia2/ia2.js");
  for (const js of [ia1js, ia2js]) {
    if (!js.includes('from "../shared/job-model.js"')) throw new Error("shell not using shared job-model");
    if (!js.includes('from "../shared/render.js"')) throw new Error("shell not using shared render");
  }
});

Deno.test("no em dash anywhere in ia/ source", async () => {
  for await (const entry of walk("ia")) {
    if (!entry.isFile) continue;
    if (/\.(js|ts|html|css)$/.test(entry.name)) {
      const t = await Deno.readTextFile(entry.path);
      if (t.includes("—")) throw new Error("em dash in " + entry.path);
    }
  }
});

async function* walk(dir: string): AsyncGenerator<{ path: string; name: string; isFile: boolean }> {
  for await (const e of Deno.readDir(dir)) {
    const path = `${dir}/${e.name}`;
    if (e.isDirectory) yield* walk(path);
    else yield { path, name: e.name, isFile: true };
  }
}
```

- [ ] **Step 2: Run the full verify suite.**

Run: `cd /Users/arijitchowdhury/prism && deno test --allow-read --allow-run ia/verify.ts`
Expected: PASS (isolation + parity + no-em-dash).

- [ ] **Step 3: Confirm production pages byte-unchanged.**

Run: `git diff --stat $(cat /tmp/ia_baseline_ref.txt) -- reports index.html chat-widget.js api/chat.js render-audit.ts 2>/dev/null; echo "exit: $?"`
Expected: empty diff (no output) for those paths. (`render-audit.ts` is not in this repo, so it cannot have changed here.)

- [ ] **Step 4: Commit.**

```bash
git add ia/verify.ts
git commit -m "test(ia): A/B parity + production-isolation verification suite"
```

---

## Task 10: Deploy + live verification

**Files:** none new (deploy is commit + push; routing is zero-config).

- [ ] **Step 1: Decide top-level URL shape.** The shells live at `/ia/ia1/` and `/ia/ia2/`. To also expose the spec's `/ia1` and `/ia2` top-level paths, create thin redirect stubs (avoids duplicating assets):

```bash
mkdir -p /Users/arijitchowdhury/prism/ia1 /Users/arijitchowdhury/prism/ia2
printf '<!doctype html><meta http-equiv="refresh" content="0; url=/ia/ia1/">' > /Users/arijitchowdhury/prism/ia1/index.html
printf '<!doctype html><meta http-equiv="refresh" content="0; url=/ia/ia2/">' > /Users/arijitchowdhury/prism/ia2/index.html
git add ia1/index.html ia2/index.html
git commit -m "feat(ia): /ia1 and /ia2 redirect stubs to the prototype shells"
```

- [ ] **Step 2: Push to deploy (Vercel auto-build).**

```bash
cd /Users/arijitchowdhury/prism && git push origin main
```
Expected: push succeeds; Vercel begins a build for project `prj_yOUkUWmGkCF8DVQ3J8GK2VJSg4SX`.

- [ ] **Step 3: Trigger VPS update** (so prism.chowmes.com serves it). Per the VPS deploy pattern, run the on-box pull (via the user's normal mechanism — `! ssh ...` or the existing gh-deploy webhook). Confirm with the user which to use; do not assume credentials.

- [ ] **Step 4: Live-verify both shells render.** Chrome MCP `navigate_page` to `https://prism.chowmes.com/ia/ia1/` and `/ia/ia2/`; assert (as in Tasks 5/7) rail=6 / chips=6, brief present. Screenshot both.

- [ ] **Step 5: Live-verify chat is grounded.** On `/ia/ia2/`, send "how bad is their search" via the ask box; confirm a non-empty grounded reply returns (proves slug-forced binding to homedepot-mexico works against the live Hermes backend). If it returns "unavailable", check `server/chat-proxy.mjs` is running and `HERMES_API_URL` is reachable (see memory: gemini grounding-gate key rotation).

- [ ] **Step 6: Live-verify feedback capture.** On the VPS, after clicking a feedback button on `/ia/ia1/`, confirm a line was appended:
```bash
# via the user's VPS access:
tail -n 3 /opt/prism-hub-feedback.jsonl
```
Expected: a JSONL line with `shell:"ia1"`. If `/api/feedback` 404s on the VPS, Caddy is not routing `/api/feedback` to chat-proxy: add a `handle /api/feedback` reverse_proxy block mirroring the existing `/api/chat` handler, reload Caddy. (Flag to user; Caddyfile is infra.)

- [ ] **Step 7: Confirm production untouched, live.** Open `https://prism.chowmes.com/reports/` and one existing audit (e.g. `/dsw/`); confirm they render exactly as before. Screenshot.

- [ ] **Step 8: Final commit (if any redirect/Caddy notes).**

```bash
git add -A && git commit -m "chore(ia): deploy notes" --allow-empty
```

---

## Self-Review (completed during authoring)

- **Spec coverage:** isolation (Task 1, 9, 10), frozen data (Task 2 single fetch), 60-sec brief (Task 3), 6-job carve (Task 2), Exports-as-action (Task 2/3), prospect view (Task 2/3, both shells Tasks 5/7), A/B guardrail / shared core (parity Task 9), IA1 browse (Task 5), IA2 chat text+open-full (Tasks 4/7), seeded chips + browse-all drawer (Task 7), in-prototype feedback widget + capture (Task 6), winner-decision data via feedback `preference` field (Task 6), deploy zero-config (Task 10), homedepot-mexico only (throughout). All spec sections map to a task.
- **Placeholder scan:** no TBD/TODO; every code step shows complete code. The one deferred item (Caddy `/api/feedback` route) is conditional on a live 404 and explicitly flagged as infra requiring user action, not a silent gap.
- **Type consistency:** `buildModel` shape, job ids (`account/broken/money/who/convo/reach`), `mountFeedback(shell)`, `createChat({mount,onOpenFull})`, render function names are used identically across Tasks 2-9.
- **Known limitation stated:** JSON lacks some production-computed content (full ROI levers, explicit MEDDPICC, discrete discovery-Q list); panels render available keys identically in both shells, preserving A/B parity. This is acceptable for a navigation prototype.
