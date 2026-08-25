// Standalone Jahia adapter backend for the Whale Page Builder.
// Holds the Jahia API token SERVER-SIDE. The browser talks only to this backend over /api.
// Read-only for now (component library + views). Publish (write) will be added behind a governance gate.
import http from "node:http";
import { Readable } from "node:stream";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// .env.local lives at the Prism repo root. This app sits at frontend/landing-page/, so walk UP from
// this server dir until we find it (robust to how deep the app is nested). When fully standalone the
// app gets its own .env; for now it reuses the central env symlink at the repo root.
const ENV_CANDIDATES = (() => {
  const out = [];
  let dir = __dirname;
  for (let i = 0; i < 7; i++) { out.push(path.join(dir, ".env.local")); dir = path.dirname(dir); }
  return out;
})();
const PORT = Number(process.env.PORT) || 8799;

function loadEnv() {
  const out = {};
  for (const p of ENV_CANDIDATES) {
    try {
      for (const line of fs.readFileSync(p, "utf8").split("\n")) {
        const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
        if (m && !(m[1] in out)) out[m[1]] = m[2].replace(/^["']|["']$/g, "").trim();
      }
    } catch {
      /* try next candidate */
    }
  }
  return out;
}
const ENV = loadEnv();
// Jahia base URL + API token (JAHIA_BASE_URL accepted as an alias for JAHIA_URL).
const JURL = ENV.JAHIA_URL || ENV.JAHIA_BASE_URL || null;
const TOKEN = ENV.JAHIA_API_TOKEN;
const GQL = JURL ? JURL.replace(/\/$/, "") + "/modules/graphql" : null;

async function jahia(query) {
  if (!GQL || !TOKEN) throw new Error("Missing JAHIA_URL / JAHIA_API_TOKEN");
  const res = await fetch(GQL, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "APIToken " + TOKEN },
    body: JSON.stringify({ query }),
  });
  return res.json();
}

// Locked DAM roots (discovered from the live Ralph Lauren page). Browse is scoped to these — the
// server refuses any path outside them, so the modal can never wander the whole repository.
const ASSET_ROOTS = {
  video: "/sites/algolia-assets/files/videos",
  image: "/sites/www/files",
  logo: "/sites/www/files/Logos",
};
async function assets(kind, path) {
  const root = ASSET_ROOTS[kind];
  if (!root) throw new Error(`unknown asset kind '${kind}'`);
  const target = path || root;
  if (target !== root && !target.startsWith(root + "/")) throw new Error("path outside locked folder");
  const j = await jahia(`{ jcr(workspace: LIVE) { nodeByPath(path: ${JSON.stringify(target)}) { children { nodes { name path primaryNodeType { name } } } } } }`);
  const nodes = j?.data?.jcr?.nodeByPath?.children?.nodes || [];
  const isFolder = (n) => /folder/i.test(n.primaryNodeType?.name || "");
  return {
    root, path: target,
    folders: nodes.filter(isFolder).map((n) => ({ name: n.name, path: n.path })),
    files: nodes.filter((n) => (n.primaryNodeType?.name || "") === "jnt:file").map((n) => ({ name: n.name, path: n.path })),
  };
}

// Stream a real asset binary from Jahia's live file servlet to the browser, so the
// preview can show actual images/videos. Path is locked to the same DAM roots as assets().
// Honors Range (video seek). Token sent server-side; the browser never sees it.
async function fileProxy(req, res, jcrPath) {
  const roots = Object.values(ASSET_ROOTS);
  if (!jcrPath || !roots.some((r) => jcrPath === r || jcrPath.startsWith(r + "/"))) {
    return json(res, 400, { ok: false, error: "path outside locked asset folders" });
  }
  const base = JURL.replace(/\/$/, "");
  const headers = { Authorization: "APIToken " + TOKEN };
  if (req.headers.range) headers.Range = req.headers.range;
  const up = await fetch(`${base}/files/live${jcrPath}`, { headers });
  const pass = { "Content-Type": up.headers.get("content-type") || "application/octet-stream", "Cache-Control": "private, max-age=300" };
  for (const h of ["content-length", "accept-ranges", "content-range"]) {
    const v = up.headers.get(h);
    if (v) pass[h.replace(/(^|-)([a-z])/g, (_, a, b) => a + b.toUpperCase())] = v;
  }
  res.writeHead(up.status, pass);
  if (!up.body) return res.end();
  Readable.fromWeb(up.body).pipe(res);
}

let cache = null;
async function components() {
  if (cache && Date.now() - cache.at < 5 * 60 * 1000) return cache.list;
  const json = await jahia(
    `{ jcr(workspace: EDIT) { nodeByPath(path: "/sites/www") { children { nodes { name primaryNodeType { name } } } } } }`
  );
  const nodes = json?.data?.jcr?.nodeByPath?.children?.nodes || [];
  const list = nodes
    .filter((n) => (n.primaryNodeType?.name || "") === "algoliaconnectnt:algoliaAllowedNodeType")
    .map((n) => n.name.replace(/_/, ":"))
    .filter((t) => /^(aant|adnt|jnt|algoliatemplatecore):/.test(t))
    .sort();
  cache = { at: Date.now(), list };
  return list;
}

const json = (res, code, body) => {
  res.writeHead(code, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
};

http
  .createServer(async (req, res) => {
    const u = new URL(req.url, "http://localhost");
    if (u.pathname === "/api/health") return json(res, 200, { ok: true, env: GQL ? "loaded" : "missing" });
    if (u.pathname === "/api/jahia/assets") {
      try {
        const r = await assets(u.searchParams.get("kind") || "image", u.searchParams.get("path") || undefined);
        return json(res, 200, { ok: true, ...r });
      } catch (e) {
        return json(res, 502, { ok: false, error: e.message });
      }
    }
    if (u.pathname === "/api/jahia/file") {
      try { return await fileProxy(req, res, u.searchParams.get("path") || ""); }
      catch (e) { return json(res, 502, { ok: false, error: e.message }); }
    }
    if (u.pathname === "/api/jahia/components") {
      try {
        const list = await components();
        return json(res, 200, { ok: true, source: "jahia:/sites/www allowlist", count: list.length, components: list });
      } catch (e) {
        return json(res, 502, { ok: false, error: e.message });
      }
    }
    return json(res, 404, { ok: false, error: "not found" });
  })
  .listen(PORT, "127.0.0.1", () => console.log(`[whale-builder api] http://127.0.0.1:${PORT} (env: ${GQL ? "loaded" : "MISSING"})`));
