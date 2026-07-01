import { assertEquals, assert } from "https://deno.land/std@0.224.0/assert/mod.ts";
import { buildModel } from "./job-model.js";

const data = JSON.parse(await Deno.readTextFile(new URL("../../reports/data/homedepot-mexico-audit-data.json", import.meta.url)));

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
  assert(hrefs.includes("/reports/homedepot-mexico/ae-report.html"));
  assert(hrefs.includes("/reports/homedepot-mexico/battle-card.html"));
  assert(hrefs.includes("/reports/homedepot-mexico/leave-behind.html"));
});

Deno.test("prospect view excludes internal-only surfaces", () => {
  const m = buildModel(data);
  const blob = JSON.stringify(m.prospect).toLowerCase();
  assert(!blob.includes("meddpicc"));
  assert(!blob.includes("abx"));
});

// Render tests (render.js)
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
  assert(!all.includes("\u2014"), "em dash found in rendered output");
});
