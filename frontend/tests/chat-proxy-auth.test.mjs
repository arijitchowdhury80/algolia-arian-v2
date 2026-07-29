import assert from "node:assert/strict";
import test from "node:test";

import { checkAuth, handleChat, handleChatRequest } from "../server/chat-proxy.mjs";

/*
Scenario list (P1 — Clerk-gate POST /api/chat, closes Risk §0.B):
- Today POST /api/chat dispatches to handleChat unconditionally, before checkAuth ever runs.
  These tests prove the fix: an unauthenticated caller gets 401 (not a 302 page-load redirect),
  and an authenticated caller still reaches the existing handleChat logic.
- checkAuth itself takes an injectable clerkClient so no real Clerk credentials are needed in tests.

Scenario list (P3 — gate handleChat on FastAPI visibility before forwarding to Hermes):
- After checkAuth succeeds, handleChat mints a trust assertion and calls FastAPI's
  by-slug/data endpoint (via an injectable fetchImpl) before ever touching Hermes.
- FastAPI 404 -> 403 to the client (never leak the raw 404), Hermes never called.
- FastAPI unreachable (fetchImpl throws) -> 503, explicitly, no fail-open fallback to Hermes.
- FastAPI 200 -> proceeds to the existing Hermes streaming path, unchanged.
*/

function makeReq({ headers = {}, body } = {}) {
  const bodyStr = body === undefined ? "" : JSON.stringify(body);
  const chunks = bodyStr ? [Buffer.from(bodyStr, "utf-8")] : [];
  return {
    headers,
    url: "/api/chat",
    method: "POST",
    [Symbol.asyncIterator]() {
      let i = 0;
      return {
        next() {
          if (i < chunks.length) return Promise.resolve({ value: chunks[i++], done: false });
          return Promise.resolve({ value: undefined, done: true });
        },
      };
    },
  };
}

function makeRes() {
  return {
    statusCode: 0,
    headers: {},
    headersSent: false,
    chunks: [],
    setHeader(k, v) {
      this.headers[k] = v;
    },
    write(chunk) {
      this.chunks.push(chunk);
    },
    end(chunk) {
      if (chunk) this.chunks.push(chunk);
      this.headersSent = true;
    },
    get body() {
      return this.chunks.join("");
    },
  };
}

function fakeClerkClient({ authenticated, userId = "user_abc123", email = "person@example.com" }) {
  return {
    authenticateRequest: async () => ({
      status: authenticated ? "signed-in" : "signed-out",
      toAuth: () => (authenticated ? { userId, sessionClaims: { email } } : null),
      headers: new Headers(),
    }),
  };
}

test("post_chat_without_clerk_session_returns_401_not_a_redirect", async () => {
  const req = makeReq({ body: { message: "hi", slug: "acme", sid: "s1" } });
  const res = makeRes();

  await handleChatRequest(req, res, { clerkClient: fakeClerkClient({ authenticated: false }) });

  assert.equal(res.statusCode, 401);
  assert.equal(res.headers["Location"], undefined);
  assert.deepEqual(JSON.parse(res.body), { error: "unauthorized" });
});

test("checkAuth_reports_ok_with_userId_and_email_for_a_signed_in_session", async () => {
  const req = makeReq();
  const result = await checkAuth(req, {
    clerkClient: fakeClerkClient({ authenticated: true, userId: "user_xyz", email: "a@b.com" }),
  });

  assert.equal(result.ok, true);
  assert.equal(result.userId, "user_xyz");
  assert.equal(result.email, "a@b.com");
});

test("post_chat_with_valid_session_reaches_existing_handleChat_logic", async () => {
  // Empty message body -> handleChat's own 400 validation fires, proving routing got past
  // the auth gate into the pre-existing handler (not stopped at 401/403/503 first).
  const req = makeReq({ body: { message: "", slug: "acme", sid: "s1" } });
  const res = makeRes();

  await handleChatRequest(req, res, {
    clerkClient: fakeClerkClient({ authenticated: true }),
    hermesApiUrl: "http://127.0.0.1:9999",
    hermesApiKey: "test-key",
  });

  assert.equal(res.statusCode, 400);
  assert.deepEqual(JSON.parse(res.body), { error: "empty message" });
});

// ── P3: gate handleChat on FastAPI visibility before forwarding to Hermes ──

test("handle_chat_denies_when_fastapi_returns_404", async () => {
  const req = makeReq({ body: { message: "what did you find", slug: "acme", sid: "s1" } });
  const res = makeRes();
  const calls = [];

  const fetchImpl = async (url) => {
    calls.push(String(url));
    return new Response("not found", { status: 404 });
  };

  await handleChat(req, res, {
    fetchImpl,
    userId: "user_abc123",
    email: "person@example.com",
    trustSecret: "test-trust-secret",
    apiBase: "https://fastapi.test",
    hermesApiUrl: "http://127.0.0.1:9999",
    hermesApiKey: "test-key",
  });

  assert.equal(res.statusCode, 403);
  assert.deepEqual(JSON.parse(res.body), { error: "forbidden" });
  assert.equal(calls.length, 1, "Hermes must never be called once FastAPI denies visibility");
  assert.match(calls[0], /^https:\/\/fastapi\.test\/api\/v1\/audits\/by-slug\/acme\/data$/);
});

test("handle_chat_returns_503_when_fastapi_unreachable_no_fail_open_to_hermes", async () => {
  const req = makeReq({ body: { message: "what did you find", slug: "acme", sid: "s1" } });
  const res = makeRes();
  let hermesWasCalled = false;

  const fetchImpl = async (url) => {
    if (String(url).includes("/by-slug/")) throw new Error("connect ECONNREFUSED");
    hermesWasCalled = true;
    throw new Error("test bug: hermes should never be reached");
  };

  await handleChat(req, res, {
    fetchImpl,
    userId: "user_abc123",
    email: "person@example.com",
    trustSecret: "test-trust-secret",
    apiBase: "https://fastapi.test",
    hermesApiUrl: "http://127.0.0.1:9999",
    hermesApiKey: "test-key",
  });

  assert.equal(res.statusCode, 503);
  assert.equal(hermesWasCalled, false);
});

test("handle_chat_mints_and_sends_trust_assertion_and_proceeds_to_hermes_on_200", async () => {
  const req = makeReq({ body: { message: "what did you find", slug: "acme", sid: "s1" } });
  const res = makeRes();
  const calls = [];

  const fetchImpl = async (url, init) => {
    calls.push({ url: String(url), init });
    if (String(url).includes("/by-slug/")) {
      assert.ok(init.headers["X-Prism-User-Assertion"], "ACL check must carry the signed assertion header");
      return new Response(JSON.stringify({ audit_data: {} }), { status: 200 });
    }
    // Hermes SSE stream, minimal valid frame.
    const sse = 'event: response.output_text.delta\ndata: {"delta":"hi there"}\n\n';
    return new Response(sse, { status: 200 });
  };

  await handleChat(req, res, {
    fetchImpl,
    userId: "user_abc123",
    email: "person@example.com",
    trustSecret: "test-trust-secret",
    apiBase: "https://fastapi.test",
    hermesApiUrl: "http://127.0.0.1:9999",
    hermesApiKey: "test-key",
  });

  assert.equal(res.statusCode, 200);
  assert.equal(calls.length, 2, "must call FastAPI's by-slug check, then Hermes");
  assert.match(calls[0].url, /by-slug\/acme\/data/);
  assert.match(calls[1].url, /\/v1\/responses$/);
  assert.equal(res.body, "hi there");
});
