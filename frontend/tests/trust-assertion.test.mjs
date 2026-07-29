import assert from "node:assert/strict";
import crypto from "node:crypto";
import test from "node:test";

import { mintAssertion, verifyAssertion } from "../server/_trust_assertion.mjs";

/*
Scenario list:
- Happy path: mintAssertion produces a base64url(payload).base64url(hmac) token whose signature
  matches an independently-computed HMAC over the payload segment.
- Deterministic exp: an injected clock lets tests assert `exp` exactly (no reliance on Date.now()).
- Round trip: verifyAssertion accepts its own mintAssertion output and returns the decoded payload.
- Tamper detection: flipping a single bit in the payload segment fails verification.
- Replay-adjacent: jti is present and random per call (two mints never collide).
- Expiry: an assertion past its exp is rejected by verifyAssertion.
*/

const SECRET = "unit-test-trust-secret";

function fixedClock(unixSeconds) {
  return () => unixSeconds * 1000;
}

test("mintAssertion_produces_verifiable_hmac_payload", () => {
  const now = fixedClock(1_700_000_000);
  const token = mintAssertion({
    userId: "user_abc123",
    email: "person@example.com",
    secret: SECRET,
    ttlSeconds: 300,
    now,
  });

  const [payloadB64, sigB64] = token.split(".");
  assert.ok(payloadB64 && sigB64, "token must have exactly a payload and signature segment");

  const expectedSig = crypto.createHmac("sha256", SECRET).update(payloadB64).digest("base64url");
  assert.equal(sigB64, expectedSig);

  const payload = JSON.parse(Buffer.from(payloadB64, "base64url").toString("utf-8"));
  assert.equal(payload.user_id, "user_abc123");
  assert.equal(payload.email, "person@example.com");
  assert.equal(payload.exp, 1_700_000_300);
  assert.match(payload.jti, /^[0-9a-f]{32}$/);
});

test("mintAssertion_jti_is_random_per_call", () => {
  const now = fixedClock(1_700_000_000);
  const a = mintAssertion({ userId: "u1", email: "u1@x.com", secret: SECRET, now });
  const b = mintAssertion({ userId: "u1", email: "u1@x.com", secret: SECRET, now });
  const payloadA = JSON.parse(Buffer.from(a.split(".")[0], "base64url").toString("utf-8"));
  const payloadB = JSON.parse(Buffer.from(b.split(".")[0], "base64url").toString("utf-8"));
  assert.notEqual(payloadA.jti, payloadB.jti);
});

test("verifyAssertion_accepts_its_own_mint_round_trip", () => {
  const now = fixedClock(1_700_000_000);
  const token = mintAssertion({
    userId: "user_abc123",
    email: "person@example.com",
    secret: SECRET,
    now,
  });

  const payload = verifyAssertion(token, { secret: SECRET, now });
  assert.ok(payload);
  assert.equal(payload.user_id, "user_abc123");
  assert.equal(payload.email, "person@example.com");
});

test("verifyAssertion_rejects_single_bit_flip_in_payload", () => {
  const now = fixedClock(1_700_000_000);
  const token = mintAssertion({ userId: "user_abc123", email: "p@x.com", secret: SECRET, now });
  const [payloadB64, sigB64] = token.split(".");

  const raw = Buffer.from(payloadB64, "base64url");
  raw[0] ^= 0b00000001; // flip one bit
  const tamperedToken = `${raw.toString("base64url")}.${sigB64}`;

  const result = verifyAssertion(tamperedToken, { secret: SECRET, now });
  assert.equal(result, null);
});

test("verifyAssertion_rejects_expired_assertion", () => {
  const mintNow = fixedClock(1_700_000_000);
  const token = mintAssertion({ userId: "user_abc123", email: "p@x.com", secret: SECRET, ttlSeconds: 60, now: mintNow });

  const verifyNow = fixedClock(1_700_000_061); // 61s later, past the 60s TTL
  const result = verifyAssertion(token, { secret: SECRET, now: verifyNow });
  assert.equal(result, null);
});

test("verifyAssertion_rejects_wrong_secret", () => {
  const now = fixedClock(1_700_000_000);
  const token = mintAssertion({ userId: "user_abc123", email: "p@x.com", secret: SECRET, now });
  const result = verifyAssertion(token, { secret: "a-different-secret", now });
  assert.equal(result, null);
});

test("verifyAssertion_rejects_malformed_token", () => {
  assert.equal(verifyAssertion("not-a-valid-token", { secret: SECRET }), null);
  assert.equal(verifyAssertion("", { secret: SECRET }), null);
  assert.equal(verifyAssertion(null, { secret: SECRET }), null);
});
