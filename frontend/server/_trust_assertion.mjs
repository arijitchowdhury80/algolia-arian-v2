/**
 * Trust-signal channel: prism-hub proxy -> PIP FastAPI (04-spec.md §4).
 *
 * Pure signer/verifier — no fetch, no Clerk dependency, so it is unit-testable
 * with a fixed secret and an injected clock. The proxy mints an assertion only
 * after its own Clerk-backed checkAuth() has succeeded (see chat-proxy.mjs);
 * FastAPI is the one that verifies it (prism_platform/auth/deps.py, separate repo).
 *
 * Format: base64url(payload) + "." + base64url(hmac_sha256(payload, secret))
 * payload = { user_id, email, jti: <random 128-bit hex>, exp: <unix seconds> }
 */

import crypto from "node:crypto";

const DEFAULT_TTL_SECONDS = 300;

function nowSeconds(now) {
  const ms = typeof now === "function" ? now() : typeof now === "number" ? now : Date.now();
  return Math.floor(ms / 1000);
}

function signPayload(payloadB64, secret) {
  return crypto.createHmac("sha256", secret).update(payloadB64).digest("base64url");
}

/**
 * Mint a signed trust assertion for a verified Clerk session.
 * @param {{userId: string, email?: string, secret: string, ttlSeconds?: number, now?: (() => number) | number}} opts
 * @returns {string} the assertion token
 */
export function mintAssertion({ userId, email = "", secret, ttlSeconds = DEFAULT_TTL_SECONDS, now = Date.now } = {}) {
  if (!userId) throw new Error("mintAssertion requires userId");
  if (!secret) throw new Error("mintAssertion requires secret");

  const payload = {
    user_id: userId,
    email: email || "",
    jti: crypto.randomBytes(16).toString("hex"),
    exp: nowSeconds(now) + ttlSeconds,
  };

  const payloadB64 = Buffer.from(JSON.stringify(payload), "utf-8").toString("base64url");
  const sigB64 = signPayload(payloadB64, secret);
  return `${payloadB64}.${sigB64}`;
}

/**
 * Verify a trust assertion minted by mintAssertion. Returns the decoded
 * payload on success, or null on ANY failure (malformed, bad signature,
 * wrong secret, expired) — never throws, so a caller can treat null as
 * "no verified user" without a try/catch.
 * @param {string} assertion
 * @param {{secret: string, now?: (() => number) | number}} opts
 * @returns {{user_id: string, email: string, jti: string, exp: number} | null}
 */
export function verifyAssertion(assertion, { secret, now = Date.now } = {}) {
  if (!assertion || typeof assertion !== "string" || !secret) return null;

  const parts = assertion.split(".");
  if (parts.length !== 2) return null;
  const [payloadB64, sigB64] = parts;
  if (!payloadB64 || !sigB64) return null;

  let expectedSigBuf;
  let providedSigBuf;
  try {
    expectedSigBuf = Buffer.from(signPayload(payloadB64, secret), "base64url");
    providedSigBuf = Buffer.from(sigB64, "base64url");
  } catch {
    return null;
  }
  if (
    expectedSigBuf.length === 0 ||
    providedSigBuf.length !== expectedSigBuf.length ||
    !crypto.timingSafeEqual(providedSigBuf, expectedSigBuf)
  ) {
    return null;
  }

  let payload;
  try {
    payload = JSON.parse(Buffer.from(payloadB64, "base64url").toString("utf-8"));
  } catch {
    return null;
  }
  if (!payload || typeof payload.exp !== "number") return null;
  if (nowSeconds(now) > payload.exp) return null;

  return payload;
}
