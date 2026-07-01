import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import test from "node:test";

async function makeStaticRoot() {
  const root = path.join(tmpdir(), `prism-auth-${process.pid}-${Date.now()}`);
  await mkdir(path.join(root, "reports", "dell", "screenshots"), { recursive: true });
  await mkdir(path.join(root, "assets"), { recursive: true });
  await mkdir(path.join(root, "dell", "screenshots"), { recursive: true });
  await writeFile(path.join(root, "index.html"), "<h1>PRISM home</h1>");
  await writeFile(path.join(root, "chat-widget.js"), "console.log('widget');");
  await writeFile(path.join(root, "assets", "app.js"), "console.log('asset');");
  await writeFile(path.join(root, "reports", "index.html"), "<h1>reports</h1>");
  await writeFile(path.join(root, "reports", "dell", "index.html"), "<h1>dell report</h1>");
  await writeFile(path.join(root, "reports", "dell", "screenshots", "overview.png"), "png");
  await writeFile(path.join(root, "dell", "index.html"), "<h1>legacy dell report</h1>");
  await writeFile(path.join(root, "dell", "dell-audit-data.json"), '{"company":"Dell"}');
  await writeFile(path.join(root, "dell", "screenshots", "overview.png"), "png");
  return root;
}

async function withServer(t) {
  const staticRoot = await makeStaticRoot();
  const port = 31000 + Math.floor(Math.random() * 1000);
  const child = spawn(process.execPath, ["server/chat-proxy.mjs"], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      PORT: String(port),
      STATIC_DIR: staticRoot,
      HERMES_API_URL: "http://127.0.0.1:1",
      HERMES_API_KEY: "test-key",
      CLERK_SECRET_KEY: "",
      CLERK_PUBLISHABLE_KEY: "",
    },
    stdio: ["ignore", "pipe", "pipe"],
  });

  let ready = "";
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error(`server did not start: ${ready}`)), 5000);
    child.stdout.on("data", (chunk) => {
      ready += chunk.toString();
      if (ready.includes("prism web+chat server")) {
        clearTimeout(timeout);
        resolve();
      }
    });
    child.stderr.on("data", (chunk) => {
      ready += chunk.toString();
    });
    child.on("exit", (code) => reject(new Error(`server exited early with ${code}: ${ready}`)));
  });

  t.after(() => child.kill("SIGTERM"));
  return `http://127.0.0.1:${port}`;
}

async function request(baseUrl, pathName, options) {
  return fetch(`${baseUrl}${pathName}`, { redirect: "manual", ...options });
}

test("sign-in page is public even when Clerk config is absent", async (t) => {
  const baseUrl = await withServer(t);
  const res = await request(baseUrl, "/sign-in");

  assert.equal(res.status, 200);
  assert.match(await res.text(), /Sign in to view the audit reports|authentication is not configured/i);
});

test("sign-in HEAD probe is public for deployment checks", async (t) => {
  const baseUrl = await withServer(t);
  const res = await request(baseUrl, "/sign-in", { method: "HEAD" });

  assert.equal(res.status, 200);
});

test("public landing and static assets remain public", async (t) => {
  const baseUrl = await withServer(t);

  assert.equal((await request(baseUrl, "/")).status, 200);
  assert.equal((await request(baseUrl, "/index.html")).status, 200);
  assert.equal((await request(baseUrl, "/chat-widget.js")).status, 200);
  assert.equal((await request(baseUrl, "/assets/app.js")).status, 200);
});

test("anonymous report routes and legacy report slugs fail closed without Clerk config", async (t) => {
  const baseUrl = await withServer(t);

  for (const pathName of [
    "/reports/",
    "/reports/dell/",
    "/reports/dell/screenshots/overview.png",
    "/dell/",
    "/dell/dell-audit-data.json",
    "/dell/screenshots/overview.png",
  ]) {
    const res = await request(baseUrl, pathName);
    assert.notEqual(res.status, 200, `${pathName} must not serve anonymously`);
    assert.match(res.headers.get("location") || "", /^\/sign-in\?/);
  }
});

test("anonymous report chat is gated before Hermes is called", async (t) => {
  const baseUrl = await withServer(t);
  const res = await request(baseUrl, "/api/chat", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ slug: "dell", message: "summarize this audit" }),
  });

  assert.notEqual(res.status, 200);
  assert.equal(res.status, 302);
  assert.match(res.headers.get("location") || "", /^\/sign-in\?/);
});

test("landing page links to sign-in without hardcoded Clerk keys", async () => {
  const html = await import("node:fs/promises").then(({ readFile }) => readFile("index.html", "utf8"));

  assert.match(html, /href="\/sign-in"/);
  assert.doesNotMatch(html, /pk_(test|live)_/);
  assert.doesNotMatch(html, /clerk\.accounts\.dev/);
});
