/**
 * PRISM hub — standalone chat proxy (VPS Node service; replaces the Vercel /api/chat function).
 *
 * Serves POST /api/chat for the static SPA hosted under prism.chowmes.com (Caddy file_server).
 * Streams a grounded report-QA answer from the Hermes-PRISM brain on the loopback — the SAME
 * brain + grounding gate as Telegram. Bearer + URL stay server-side (env). Same-origin (no CORS).
 * The page slug binds the right company's report via an invisible [Account: <slug>] prefix.
 *
 * This is the on-VPS equivalent of api/chat.js — logic kept identical so behaviour matches the
 * proven Vercel path. Difference: HERMES_API_URL points at the loopback (http://127.0.0.1:8642),
 * so nothing routes through judge.contentengagement.info.
 *
 * Env (server-side only):
 *   HERMES_API_URL  http://127.0.0.1:8642   (loopback to the Hermes brain)
 *   HERMES_API_KEY  the bearer (Hermes API_SERVER_KEY)
 *   PORT            listen port (default 8651, bind 127.0.0.1 — Caddy fronts it)
 */

import http from "node:http";
import path from "node:path";
import { readFile, stat } from "node:fs/promises";

const HERMES_API_URL = process.env.HERMES_API_URL;
const HERMES_API_KEY = process.env.HERMES_API_KEY;
const PORT = Number(process.env.PORT || 8651);
const STATIC_DIR = process.env.STATIC_DIR || "/opt/prism-hub";
const MAX_MESSAGE_CHARS = 2000;

// ── Auth gate (Clerk) ───────────────────────────────────────────────────────
// The landing ("/") + marketing pages stay public. The audit reports (/reports
// and every report slug dir) require a signed-in Clerk session. Secure-by-default:
// anything NOT in the public allowlist below is gated.
// Resilient import: if @clerk/backend isn't installed on the box yet, the server
// must still start (gate simply stays OFF / fail-open) rather than crash on boot.
let createClerkClient = null;
try {
  ({ createClerkClient } = await import("@clerk/backend"));
} catch {
  console.warn("[auth] @clerk/backend not installed — /reports NOT gated until it is");
}

const CLERK_SECRET_KEY = process.env.CLERK_SECRET_KEY;
const CLERK_PUBLISHABLE_KEY =
  process.env.CLERK_PUBLISHABLE_KEY || process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || "";
// clerk-js host is derived from the publishable key (dev: glad-skunk-4.clerk.accounts.dev).
const CLERK_JS_HOST = process.env.CLERK_FRONTEND_HOST ||
  (() => { try { return atob(CLERK_PUBLISHABLE_KEY.split("_")[2] || "").replace(/\$$/, ""); } catch { return ""; } })();
const clerk = createClerkClient && CLERK_SECRET_KEY && CLERK_PUBLISHABLE_KEY
  ? createClerkClient({ secretKey: CLERK_SECRET_KEY, publishableKey: CLERK_PUBLISHABLE_KEY })
  : null;
if (!clerk) console.warn("[auth] Clerk NOT configured — reports are NOT gated (set CLERK_SECRET_KEY + CLERK_PUBLISHABLE_KEY)");

const PUBLIC_EXACT = new Set(["/", "/index.html", "/chat-widget.js", "/favicon.ico", "/robots.txt", "/healthz", "/sign-in"]);
const PUBLIC_PREFIXES = ["/about", "/assets", "/ia", "/ia1", "/ia2", "/api"];
function isPublicPath(u) {
  if (PUBLIC_EXACT.has(u)) return true;
  return PUBLIC_PREFIXES.some((p) => u === p || u.startsWith(p + "/") || u.startsWith(p + "."));
}

function toWebRequest(req) {
  const host = req.headers.host || "localhost";
  const proto = String(req.headers["x-forwarded-proto"] || "http").split(",")[0];
  const headers = new Headers();
  for (const [k, v] of Object.entries(req.headers)) {
    if (Array.isArray(v)) v.forEach((x) => headers.append(k, x));
    else if (v != null) headers.set(k, String(v));
  }
  return new Request(`${proto}://${host}${req.url}`, { method: "GET", headers });
}

// { ok:true } signed-in (or auth disabled); { redirect, setCookies } otherwise.
async function checkAuth(req) {
  if (!clerk) return { ok: true };
  try {
    const state = await clerk.authenticateRequest(toWebRequest(req), {});
    if (state.status === "handshake") {
      return { redirect: state.headers.get("location"), setCookies: state.headers.getSetCookie?.() || [] };
    }
    const auth = state.toAuth();
    return auth && auth.userId ? { ok: true } : { redirect: null };
  } catch {
    return { redirect: null };
  }
}

const SIGN_IN_HTML = `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in &middot; PRISM</title>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600&display=swap" rel="stylesheet">
<style>body{font-family:Sora,sans-serif;background:#F8F9FB;color:#23263B;display:flex;min-height:100vh;align-items:center;justify-content:center;flex-direction:column;margin:0}
h1{font-size:30px;font-weight:600;margin:0 0 4px}p{color:#6B7280;margin:0 0 28px}#sign-in{min-height:380px}</style></head>
<body>
<h1>PRISM</h1><p>Sign in to view the audit reports</p>
<div id="sign-in"></div>
<script async crossorigin="anonymous" data-clerk-publishable-key="${CLERK_PUBLISHABLE_KEY}"
 src="https://${CLERK_JS_HOST}/npm/@clerk/clerk-js@5/dist/clerk.browser.js"></script>
<script>
window.addEventListener("load", function(){
  var tries=0;(function go(){
    if(!window.Clerk){ if(tries++<50){ setTimeout(go,100); } return; }
    window.Clerk.load().then(function(){
      var p=new URLSearchParams(location.search), r=p.get("redirect_url")||"/reports/";
      if(window.Clerk.user){ location.replace(r); return; }
      window.Clerk.mountSignIn(document.getElementById("sign-in"),{fallbackRedirectUrl:r,forceRedirectUrl:r});
    }).catch(function(){});
  })();
});
</script></body></html>`;

const CONTENT_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
  ".woff": "font/woff",
  ".txt": "text/plain; charset=utf-8",
  ".pdf": "application/pdf",
};

// Serve a static file under STATIC_DIR. Directory → its index.html. Path traversal is blocked.
async function serveStatic(res, urlPath) {
  let rel;
  try {
    rel = decodeURIComponent(urlPath);
  } catch {
    return sendJson(res, 400, { error: "bad path" });
  }
  if (rel.endsWith("/")) rel += "index.html";
  const full = path.normalize(path.join(STATIC_DIR, rel));
  if (full !== STATIC_DIR && !full.startsWith(STATIC_DIR + path.sep)) {
    return sendJson(res, 403, { error: "forbidden" });
  }
  let file = full;
  try {
    const s = await stat(full);
    if (s.isDirectory()) file = path.join(full, "index.html");
    const data = await readFile(file);
    res.statusCode = 200;
    res.setHeader("Content-Type", CONTENT_TYPES[path.extname(file).toLowerCase()] || "application/octet-stream");
    res.end(data);
  } catch {
    res.statusCode = 404;
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.end("<!doctype html><meta charset=utf-8><title>404</title><h1>404 — not found</h1>");
  }
}

// URL slug (page dir) → Hermes report-store slug, where they differ.
const SLUG_ALIASES = { orientaltrading: "oriental-trading" };

function sendJson(res, code, obj) {
  res.statusCode = code;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.end(JSON.stringify(obj));
}

async function readBody(req) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  if (!chunks.length) return {};
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf-8"));
  } catch {
    return {};
  }
}

async function handleChat(req, res) {
  if (!HERMES_API_URL || !HERMES_API_KEY) {
    return sendJson(res, 500, { error: "chat not configured" });
  }
  const body = (await readBody(req)) || {};
  const message = typeof body.message === "string" ? body.message.trim() : "";
  const slug = typeof body.slug === "string" ? body.slug.trim().toLowerCase() : "";
  const sid = (typeof body.sid === "string" && body.sid.slice(0, 40)) || "anon";

  if (!message) return sendJson(res, 400, { error: "empty message" });
  if (message.length > MAX_MESSAGE_CHARS) return sendJson(res, 413, { error: "message too long" });
  if (!slug) return sendJson(res, 400, { error: "missing slug" });

  const reportSlug = SLUG_ALIASES[slug] || slug;
  const sessionKey = `agent:main:prism:web:${sid}:acct:${reportSlug}`.replace(/[\r\n\x00]/g, "");
  const conversation = `prism:web:${sid}:${reportSlug}`;
  const input = message.toLowerCase().includes(reportSlug.split("-")[0])
    ? message
    : `[Account: ${reportSlug}] ${message}`;

  let upstream;
  try {
    upstream = await fetch(`${HERMES_API_URL}/v1/responses`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${HERMES_API_KEY}`,
        "Content-Type": "application/json",
        "X-Hermes-Session-Key": sessionKey,
      },
      body: JSON.stringify({ model: "hermes-agent", input, conversation, stream: true, store: true }),
    });
  } catch {
    return sendJson(res, 502, { error: "upstream unreachable" });
  }
  if (!upstream.ok || !upstream.body) {
    return sendJson(res, 502, { error: `upstream ${upstream.status}` });
  }

  res.statusCode = 200;
  res.setHeader("Content-Type", "text/plain; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("X-Accel-Buffering", "no");

  const reader = upstream.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n\n")) !== -1) {
        const frame = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        let event = "message";
        const dataLines = [];
        for (const line of frame.split("\n")) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
        }
        if (event === "response.output_text.delta" && dataLines.length) {
          try {
            const payload = JSON.parse(dataLines.join("\n"));
            if (payload.delta) res.write(payload.delta);
          } catch {
            /* skip malformed frame */
          }
        }
      }
    }
  } catch {
    /* upstream cut — end what we have */
  }
  res.end();
}

const server = http.createServer(async (req, res) => {
  const url = (req.url || "").split("?")[0];
  if (req.method === "GET" && url === "/healthz") {
    return sendJson(res, 200, { status: "ok" });
  }
  // --- IA prototype feedback capture (additive; does not touch /api/chat) ---
  if (req.method === "POST" && url === "/api/feedback") {
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", async () => {
      try {
        const rec = { ...JSON.parse(raw || "{}"), ts: new Date().toISOString() };
        const fs = await import("node:fs");
        fs.appendFileSync(process.env.IA_FEEDBACK_FILE || "/opt/prism-hub-feedback.jsonl", JSON.stringify(rec) + "\n");
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true }));
      } catch {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: false }));
      }
    });
    return;
  }
  if (req.method === "POST" && url === "/api/chat") {
    return handleChat(req, res).catch(() => {
      if (!res.headersSent) sendJson(res, 500, { error: "internal" });
      else res.end();
    });
  }
  if (req.method === "GET" && url === "/sign-in") {
    res.statusCode = 200;
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    return res.end(SIGN_IN_HTML);
  }
  if (req.method === "GET" || req.method === "HEAD") {
    if (!isPublicPath(url)) {
      const a = await checkAuth(req);
      if (!a.ok) {
        if (a.setCookies && a.setCookies.length) {
          for (const c of a.setCookies) res.appendHeader("Set-Cookie", c);
        }
        res.statusCode = 302;
        res.setHeader("Location", a.redirect || `/sign-in?redirect_url=${encodeURIComponent(url)}`);
        return res.end();
      }
    }
    return serveStatic(res, url).catch(() => {
      if (!res.headersSent) sendJson(res, 500, { error: "internal" });
      else res.end();
    });
  }
  sendJson(res, 404, { error: "not found" });
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`prism web+chat server on 127.0.0.1:${PORT} (static=${STATIC_DIR})`);
});
