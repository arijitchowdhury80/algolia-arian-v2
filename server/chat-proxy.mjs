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
 *   CLERK_SECRET_KEY / CLERK_PUBLISHABLE_KEY  Clerk auth gate for reports + chat
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

let createClerkClient = null;
try {
  ({ createClerkClient } = await import("@clerk/backend"));
} catch {
  console.warn("[auth] @clerk/backend not installed; protected PRISM routes will fail closed");
}

const CLERK_SECRET_KEY = process.env.CLERK_SECRET_KEY || "";
const CLERK_PUBLISHABLE_KEY = process.env.CLERK_PUBLISHABLE_KEY || process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || "";
const CLERK_JS_HOST =
  process.env.CLERK_FRONTEND_HOST ||
  (() => {
    try {
      return Buffer.from(CLERK_PUBLISHABLE_KEY.split("_")[2] || "", "base64").toString("utf8").replace(/\$$/, "");
    } catch {
      return "";
    }
  })();
const clerk =
  createClerkClient && CLERK_SECRET_KEY && CLERK_PUBLISHABLE_KEY
    ? createClerkClient({ secretKey: CLERK_SECRET_KEY, publishableKey: CLERK_PUBLISHABLE_KEY })
    : null;

if (!clerk) {
  console.warn("[auth] Clerk is not fully configured; protected PRISM routes will fail closed");
}

const PUBLIC_EXACT = new Set(["/", "/index.html", "/auth.js", "/chat-widget.js", "/favicon.ico", "/robots.txt", "/healthz", "/sign-in"]);
const PUBLIC_PREFIXES = ["/about", "/assets", "/ia", "/ia1", "/ia2"];

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

function isPublicStaticPath(urlPath) {
  if (PUBLIC_EXACT.has(urlPath)) return true;
  return PUBLIC_PREFIXES.some((prefix) => urlPath === prefix || urlPath.startsWith(`${prefix}/`) || urlPath.startsWith(`${prefix}.`));
}

// Sub-resource assets (images/css/js/fonts) requested by an authed report page. On auth
// failure these must return 401, NOT a 302 -> HTML sign-in page (an <img> cannot follow the
// Clerk handshake redirect, so a redirected image renders broken / returns login markup).
const ASSET_EXTS = new Set([".png",".jpg",".jpeg",".webp",".svg",".gif",".ico",".css",".js",".mjs",".json",".woff",".woff2",".ttf",".otf",".map",".pdf",".mp4",".webm"]);
function isAssetPath(urlPath) {
  const q = urlPath.split("?")[0];
  const dot = q.lastIndexOf(".");
  if (dot < 0) return false;
  return ASSET_EXTS.has(q.slice(dot).toLowerCase());
}

function appendHeader(res, name, value) {
  const existing = res.getHeader(name);
  if (!existing) {
    res.setHeader(name, value);
  } else if (Array.isArray(existing)) {
    res.setHeader(name, [...existing, value]);
  } else {
    res.setHeader(name, [existing, value]);
  }
}

function toWebRequest(req) {
  const host = req.headers.host || "localhost";
  const proto = String(req.headers["x-forwarded-proto"] || "http").split(",")[0];
  const headers = new Headers();
  for (const [key, value] of Object.entries(req.headers)) {
    if (Array.isArray(value)) value.forEach((entry) => headers.append(key, entry));
    else if (value != null) headers.set(key, String(value));
  }
  return new Request(`${proto}://${host}${req.url}`, { method: req.method || "GET", headers });
}

async function checkAuth(req) {
  if (!clerk) return { ok: false };
  try {
    const state = await clerk.authenticateRequest(toWebRequest(req), {});
    if (state.status === "handshake") {
      return {
        ok: false,
        redirect: state.headers.get("location"),
        setCookies: state.headers.getSetCookie?.() || [],
      };
    }
    const auth = state.toAuth();
    return auth?.userId ? { ok: true } : { ok: false };
  } catch {
    return { ok: false };
  }
}

async function requireAuth(req, res, urlPath) {
  const auth = await checkAuth(req);
  if (auth.ok) return true;
  if (auth.setCookies?.length) {
    for (const cookie of auth.setCookies) appendHeader(res, "Set-Cookie", cookie);
  }
  if (isAssetPath(urlPath)) {
    // An authed report page's sub-resource (image/css/js). An <img> cannot follow Clerk's
    // handshake redirect, so if the browser carries any Clerk session cookie, serve the asset
    // (the page it belongs to is auth-gated). Only a truly cookieless (anon) request is blocked.
    const cookie = req.headers.cookie || "";
    if (/(?:^|;\s*)(__session|__client|__clerk)/i.test(cookie)) return true;
    res.statusCode = 401;
    res.end();
    return false;
  }
  res.statusCode = 302;
  res.setHeader("Location", auth.redirect || `/sign-in?redirect_url=${encodeURIComponent(urlPath)}`);
  res.end();
  return false;
}

function signInHtml() {
  const disabled = !CLERK_PUBLISHABLE_KEY || !CLERK_JS_HOST;
  const body = disabled
    ? `<p>Authentication is not configured. Reports are locked until Clerk is configured.</p>`
    : `<p>Sign in to view the audit reports</p>
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
</script>`;
  return `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in · PRISM</title>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600&display=swap" rel="stylesheet">
<style>body{font-family:Sora,sans-serif;background:#F8F9FB;color:#23263B;display:flex;min-height:100vh;align-items:center;justify-content:center;flex-direction:column;margin:0;padding:24px;text-align:center}h1{font-size:30px;font-weight:600;margin:0 0 4px}p{color:#6B7280;margin:0 0 28px;max-width:520px}#sign-in{min-height:380px}</style></head>
<body><h1>PRISM</h1>${body}</body></html>`;
}

function sendSignIn(res) {
  res.statusCode = 200;
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.end(signInHtml());
}

function authClientJs() {
  const config =
    CLERK_PUBLISHABLE_KEY && CLERK_JS_HOST
      ? {
          publishableKey: CLERK_PUBLISHABLE_KEY,
          scriptUrl: `https://${CLERK_JS_HOST}/npm/@clerk/clerk-js@5/dist/clerk.browser.js`,
        }
      : null;

  return `"use strict";
(function(){
  var config = ${JSON.stringify(config)};
  var slotId = "prism-auth";

  function ready(fn) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn, { once: true });
    else fn();
  }

  function fallback(slot) {
    if (!slot) return;
    slot.classList.remove("is-authenticated");
    if (!slot.querySelector("[data-prism-auth-fallback]")) {
      slot.innerHTML = '<a class="tb-link" href="/sign-in" data-prism-auth-fallback>Sign in</a>';
    }
  }

  function loadClerk() {
    if (window.Clerk) return Promise.resolve(window.Clerk);
    if (!config) return Promise.reject(new Error("missing Clerk publishable key"));
    return new Promise(function(resolve, reject) {
      var script = document.createElement("script");
      script.async = true;
      script.crossOrigin = "anonymous";
      script.setAttribute("data-clerk-publishable-key", config.publishableKey);
      script.src = config.scriptUrl;
      script.onload = function() { resolve(window.Clerk); };
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  ready(function(){
    var slot = document.getElementById(slotId);
    fallback(slot);
    if (!slot || !config) return;

    loadClerk()
      .then(function(Clerk) {
        if (!Clerk) throw new Error("Clerk browser client unavailable");
        return Clerk.load().then(function() { return Clerk; });
      })
      .then(function(Clerk) {
        if (!Clerk.user) {
          fallback(slot);
          return;
        }
        slot.innerHTML = "";
        slot.classList.add("is-authenticated");
        Clerk.mountUserButton(slot, { afterSignOutUrl: "/" });
      })
      .catch(function() { fallback(slot); });
  });
})();`;
}

function sendAuthClientJs(req, res) {
  res.statusCode = 200;
  res.setHeader("Content-Type", "text/javascript; charset=utf-8");
  if (req.method === "HEAD") res.end();
  else res.end(authClientJs());
}

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

async function handleChat(req, res, urlPath) {
  if (!(await requireAuth(req, res, urlPath))) return;
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
  if ((req.method === "GET" || req.method === "HEAD") && url === "/sign-in") {
    return sendSignIn(res);
  }
  if ((req.method === "GET" || req.method === "HEAD") && url === "/auth.js") {
    return sendAuthClientJs(req, res);
  }
  if (req.method === "POST" && url === "/api/feedback") {
    return sendJson(res, 200, { ok: true });
  }
  if (req.method === "POST" && url === "/api/chat") {
    return handleChat(req, res, url).catch(() => {
      if (!res.headersSent) sendJson(res, 500, { error: "internal" });
      else res.end();
    });
  }
  if (req.method === "GET" || req.method === "HEAD") {
    if (!isPublicStaticPath(url) && !(await requireAuth(req, res, url))) {
      return;
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
