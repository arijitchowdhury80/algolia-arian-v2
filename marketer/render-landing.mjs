#!/usr/bin/env node
/**
 * render-landing.mjs — PRISM Marketer landing-page renderer.
 *
 * Plain Node, zero dependencies. Takes a slug, reads
 * data/<slug>.landing.json + landing-template.html, and writes <slug>.html.
 *
 * Template syntax (minimal, hand-rolled — no npm installs):
 *   {{path.to.value}}         simple substitution (dotted path lookup)
 *   {{#each path}} ... {{/each}}   iterate an array; inside the block,
 *                                  {{field}} resolves against the current
 *                                  item first, then falls back to the
 *                                  outer context (Mustache-style).
 *   {{#if path}} ... {{else}} ... {{/if}}   conditional on truthiness
 *   {{#unless path}} ... {{/unless}}        inverse conditional
 *
 * Substitutions are NOT HTML-escaped — this renders trusted, internally
 * authored JSON (account audit data), not untrusted user input.
 *
 * Usage:
 *   node render-landing.mjs <slug>
 *   node render-landing.mjs dell
 *   node render-landing.mjs nike
 */

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const slug = process.argv[2];
if (!slug) {
  console.error("Usage: node render-landing.mjs <slug>");
  process.exit(1);
}

const templatePath = path.join(__dirname, "landing-template.html");
const dataPath = path.join(__dirname, "data", `${slug}.landing.json`);
const outPath = path.join(__dirname, `${slug}.html`);

const template = readFileSync(templatePath, "utf8");
const data = JSON.parse(readFileSync(dataPath, "utf8"));

// ---- tiny mustache-like tokenizer/parser ----

const TAG_RE = /\{\{(#each|#if|#unless|\/each|\/if|\/unless|else)?\s*([^}]*?)\s*\}\}/g;

function tokenize(str) {
  const tokens = [];
  let lastIndex = 0;
  let m;
  TAG_RE.lastIndex = 0;
  while ((m = TAG_RE.exec(str)) !== null) {
    if (m.index > lastIndex) {
      tokens.push({ type: "text", value: str.slice(lastIndex, m.index) });
    }
    const [, control, arg] = m;
    if (control === "#each") tokens.push({ type: "each-open", path: arg.trim() });
    else if (control === "#if") tokens.push({ type: "if-open", path: arg.trim() });
    else if (control === "#unless") tokens.push({ type: "unless-open", path: arg.trim() });
    else if (control === "/each") tokens.push({ type: "each-close" });
    else if (control === "/if") tokens.push({ type: "if-close" });
    else if (control === "/unless") tokens.push({ type: "unless-close" });
    else if (control === "else") tokens.push({ type: "else" });
    else tokens.push({ type: "var", path: arg.trim() });
    lastIndex = TAG_RE.lastIndex;
  }
  if (lastIndex < str.length) tokens.push({ type: "text", value: str.slice(lastIndex) });
  return tokens;
}

// Recursive-descent parse into a tree of nodes.
function parse(tokens) {
  let i = 0;

  function parseNodes(stopTypes) {
    const nodes = [];
    while (i < tokens.length) {
      const t = tokens[i];
      if (stopTypes.includes(t.type)) return nodes;
      if (t.type === "text" || t.type === "var") {
        nodes.push(t);
        i++;
      } else if (t.type === "each-open") {
        i++;
        const body = parseNodes(["each-close"]);
        if (tokens[i]?.type !== "each-close") throw new Error(`Unclosed {{#each ${t.path}}}`);
        i++; // consume each-close
        nodes.push({ type: "each", path: t.path, body });
      } else if (t.type === "if-open" || t.type === "unless-open") {
        const isUnless = t.type === "unless-open";
        i++;
        const closeType = isUnless ? "unless-close" : "if-close";
        const thenBody = parseNodes(["else", closeType]);
        let elseBody = [];
        if (tokens[i]?.type === "else") {
          i++;
          elseBody = parseNodes([closeType]);
        }
        if (tokens[i]?.type !== closeType) throw new Error(`Unclosed {{#if/unless ${t.path}}}`);
        i++; // consume close
        nodes.push({ type: isUnless ? "unless" : "if", path: t.path, thenBody, elseBody });
      } else {
        throw new Error(`Unexpected token: ${JSON.stringify(t)}`);
      }
    }
    return nodes;
  }

  const root = parseNodes([]);
  return root;
}

function lookup(path_, scopes) {
  const parts = path_.split(".");
  for (let s = scopes.length - 1; s >= 0; s--) {
    let cur = scopes[s];
    let ok = true;
    for (const p of parts) {
      if (cur !== null && typeof cur === "object" && p in cur) {
        cur = cur[p];
      } else {
        ok = false;
        break;
      }
    }
    if (ok) return cur;
  }
  return undefined;
}

function truthy(v) {
  if (Array.isArray(v)) return v.length > 0;
  return Boolean(v);
}

function render(nodes, scopes) {
  let out = "";
  for (const node of nodes) {
    if (node.type === "text") {
      out += node.value;
    } else if (node.type === "var") {
      const v = lookup(node.path, scopes);
      out += v === undefined || v === null ? "" : String(v);
    } else if (node.type === "each") {
      const arr = lookup(node.path, scopes);
      if (Array.isArray(arr)) {
        for (const item of arr) {
          out += render(node.body, [...scopes, item]);
        }
      }
    } else if (node.type === "if") {
      const v = lookup(node.path, scopes);
      out += render(truthy(v) ? node.thenBody : node.elseBody, scopes);
    } else if (node.type === "unless") {
      const v = lookup(node.path, scopes);
      out += render(!truthy(v) ? node.thenBody : node.elseBody, scopes);
    }
  }
  return out;
}

const tree = parse(tokenize(template));
const html = render(tree, [data]);

writeFileSync(outPath, html, "utf8");
console.log(`Rendered ${outPath} (${html.length} bytes) from ${dataPath}`);
