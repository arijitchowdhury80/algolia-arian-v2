import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const html = await readFile(new URL("../index.html", import.meta.url), "utf8");
const chatWidget = await readFile(new URL("../chat-widget.js", import.meta.url), "utf8");

function sectionByClass(className) {
  const match = html.match(new RegExp(`<section class="${className}"[\\s\\S]*?</section>`));
  assert.ok(match, `Expected <section class="${className}"> to exist`);
  return match[0];
}

test("landing page presents Cassandra as a supporting operator, not the product hero", () => {
  const section = sectionByClass("cassandra");

  assert.match(section, /<h2 class="s-title">Cassandra keeps the audit alive<\/h2>/);
  // Her established portrait, not a live-avatar still. Cassandra is the grounded
  // report guide, so the landing page must not dress her up as the LiveAvatar demo.
  assert.match(section, /src="\/assets\/cassandra\.png"/);
  assert.match(section, /alt="Cassandra, the operator behind PRISM"/);
  assert.match(section, /Ask Cassandra/);
  assert.match(section, /Telegram/);
  assert.match(html, /PRISM turns a prospect domain into a sourced search audit/);
  assert.match(html, /What PRISM builds/);
  assert.match(html, /How PRISM works/);
  assert.doesNotMatch(section, /Hermes/);
});

test("landing page copy stays concrete and human, not infrastructure-first", () => {
  assert.match(html, /Domain in\.[\s\S]*Audit, sales kit, answers out\./);
  assert.match(html, /Audit engine/);
  assert.match(html, /Grounded chat on web and Telegram/);
  assert.doesNotMatch(html, /What Cassandra hands you/);
  assert.doesNotMatch(html, /Cassandra's operating loop/);
  assert.doesNotMatch(html, /Hermes: the engine that runs it/);
  assert.doesNotMatch(html, /Hermes \/ Cassandra make it conversational/);
});

test("landing page is built for a 30 second scan", () => {
  const stripTags = (value) => value.replace(/<[^>]*>/g, "").replace(/\s+/g, " ").trim();
  const heroSub = html.match(/<p class="hero-sub">([\s\S]*?)<\/p>/);
  assert.ok(heroSub, "Expected hero subcopy");
  assert.ok(stripTags(heroSub[1]).length <= 230, "Hero subcopy should stay under 230 characters");

  const sectionLeads = [...html.matchAll(/<p class="s-lead">([\s\S]*?)<\/p>/g)].map((match) => stripTags(match[1]));
  assert.ok(sectionLeads.length >= 5, "Expected scannable section leads");
  for (const lead of sectionLeads) {
    assert.ok(lead.length <= 150, `Section lead is too long: ${lead}`);
  }

  assert.doesNotMatch(html, /It feels less like a dashboard to babysit/);
  assert.doesNotMatch(html, /Every PRISM audit has a pulse because Cassandra is there/);
  assert.doesNotMatch(html, /Give Cassandra a domain/);
});

test("chat widget uses the current Cassandra portrait", () => {
  assert.match(chatWidget, /src="\/assets\/cassandra\.png\?v=20260701"/);
  assert.match(chatWidget, /alt="Cassandra"/);
});

test("mobile header can collapse the GitHub link without losing its label", () => {
  assert.match(html, /<a class="tb-gh"[^>]*href="https:\/\/github\.com\/arijitchowdhury80\/prism"[^>]*aria-label="View PRISM on GitHub"/);
  assert.doesNotMatch(html, /github\.com\/arijitchowdhury80\/arijit-skills/);
  assert.match(html, /@media \(max-width: 720px\)[\s\S]*\.tb-gh \{[^}]*font-size: 0/);
});

test("who and produce sections swap interaction effects without changing their copy", () => {
  const who = sectionByClass("band band--who");
  const produce = sectionByClass("band band--produce");

  assert.match(who, /Account Executives/);
  assert.match(who, /BDRs/);
  assert.match(who, /Sales Leaders/);
  assert.match(produce, /Overview/);
  assert.match(produce, /Search Audit/);
  assert.match(produce, /Downloadable assets/);

  assert.match(who, /class="role-card r1 reveal"[\s\S]*class="b-spot"[\s\S]*class="b-glow"/);
  assert.doesNotMatch(who, /class="ge-edge"/);
  assert.match(produce, /class="deliv reveal"[\s\S]*class="ge-edge"/);
  assert.doesNotMatch(produce, /class="b-spot"/);

  assert.match(html, /Role cards: spotlight, border glow, 3D tilt, magnetism, particles, ripple/);
  assert.match(html, /Deliverables: glowing edge follows the pointer/);
  assert.match(html, /\.deliv\.reveal\.in:hover \{ transform: translateY\(-6px\); \}/);
  assert.match(html, /document\.querySelectorAll\('\.role-grid \.role-card'\)/);
  assert.match(html, /document\.querySelectorAll\('\.deliv-grid \.deliv'\)/);
});

test("what prism builds is grounded in actual audit sections and downloadable assets", () => {
  const produce = sectionByClass("band band--produce");
  const prismOutput = html.match(/<div class="pc-out">([\s\S]*?)<\/div>\s*<\/div>\s*<\/div>\s*<\/section>/);
  assert.ok(prismOutput, "Expected hero prism output chips");

  for (const label of ["Overview", "Research", "Search Audit", "Business Case", "Sales Actions", "Downloadable assets"]) {
    assert.match(produce, new RegExp(`<h4>${label}</h4>`));
    assert.match(prismOutput[1], new RegExp(`>${label}<`));
  }

  assert.match(produce, /Score, gaps, and next step\./);
  assert.match(produce, /Company context, financials, tech stack, traffic, hiring, signals, partners\./);
  assert.match(produce, /Tested queries, scorecard, findings, and screenshots\./);
  assert.match(produce, /Said-vs-found hook, ROI model, case studies, why now\./);
  assert.match(produce, /Battle card, plays, pre-call brief, power map, ABX campaign\./);
  assert.match(produce, /AE report, battle card, leave-behind, full audit binder, PDF\/PPTX where generated\./);

  assert.doesNotMatch(produce, /Evidence audit/);
  assert.doesNotMatch(produce, /Live search proof/);
  assert.doesNotMatch(produce, /ROI case/);
  assert.doesNotMatch(produce, /ABX motion/);
  assert.doesNotMatch(prismOutput[1], /Evidence audit|Search findings|ROI case|ABX moves|Ask Cassandra/);
});
