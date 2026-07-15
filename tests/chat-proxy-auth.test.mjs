import assert from "node:assert/strict";
import test from "node:test";

import { checkAuth, handleChatRequest } from "../server/chat-proxy.mjs";

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
