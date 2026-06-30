// ia/shared/render.js - pure model -> HTML string renderers (no em dashes in output)

// esc() HTML-escapes user text and normalizes em dashes to plain ASCII.
// Any em dash in data values (U+2014) becomes a space so output is always em-dash-free.
function esc(s) {
  return String(s ?? "")
    .replace(/\u2014/g, " ")
    .replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
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
    // actual data uses prospect_description or actual_behavior; brief code used detail/summary
    (f.detail || f.summary || f.prospect_description || f.actual_behavior
      ? `<p>${esc(f.detail ?? f.summary ?? f.prospect_description ?? f.actual_behavior)}</p>`
      : "") +
    `</div>`
  ).join("");
}

function pairs(arr) {
  const a = Array.isArray(arr) ? arr : [];
  return `<table class="ia-pairs"><tr><th>They said</th><th>We found</th></tr>` +
    // actual data fields: said_quote, found_title / found_evidence
    a.map((p) =>
      `<tr><td>${esc(p.said ?? p.quote ?? p.said_quote ?? "")}</td>` +
      `<td>${esc(p.found ?? p.finding ?? p.found_title ?? p.found_evidence ?? "")}</td></tr>`
    ).join("") + `</table>`;
}

function abx(seq) {
  // actual data: abx_sequence is a dict with touches[] (not emails/steps)
  const a = Array.isArray(seq) ? seq : (seq?.emails ?? seq?.steps ?? seq?.touches ?? []);
  return `<ol class="ia-abx">` + a.map((e) =>
    `<li><strong>${esc(e.subject ?? e.step ?? "Email")}</strong>` +
    `<p>${esc((e.body ?? e.text ?? e.message ?? "").slice(0, 400))}</p></li>`
  ).join("") + `</ol>`;
}

const DISPATCH = { kv, list, findings, pairs, abx };

export function renderBrief(brief) {
  const whyNow = (brief.whyNow || []).map((s) =>
    `<li>${esc(typeof s === "object" ? (s.headline ?? s.title ?? JSON.stringify(s).slice(0, 160)) : s)}</li>`
  ).join("");
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
    job.sections.map((s) =>
      `<section class="ia-section" data-key="${esc(s.key)}">` +
      `<h4>${esc(s.title)} <button class="ia-export-btn" data-export="${esc(s.key)}">Export</button></h4>` +
      `${(DISPATCH[s.render] || kv)(s.data)}</section>`
    ).join("") +
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
  return `<div class="ia-exports">` +
    exports.map((e) =>
      `<a class="ia-export-btn" href="${esc(e.href)}" target="_blank" rel="noopener">${esc(e.label)}</a>`
    ).join("") +
    `</div>`;
}
