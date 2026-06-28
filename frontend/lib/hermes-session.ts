/**
 * Hermes session/identity helpers for the unified PRISM chat (W-D).
 *
 * One rep, working one account, gets the SAME remembered context across
 * Telegram and the web SPA — and phone↔laptop on web — because both clients
 * resolve to the same Hermes session-key + conversation name.
 *
 * Design source: docs/workspace/hermes-prism-integration/spike-unify-audit/G-wd-design.md §3.
 *
 *   X-Hermes-Session-Key (long-term memory scope): agent:main:prism:rep:<repId>:acct:<domain>
 *   conversation (transcript chain for /v1/responses):       prism:<repId>:<domain>
 *
 * <repId> derives from the Clerk userId on web (and, later, maps from a Telegram
 * chat_id via a one-time /link step — see G §3.3 option I1).
 */

const KEY_PREFIX = "agent:main:prism";

/** Normalize a domain so petsmart.com / https://www.petsmart.com / PetSmart.com all collapse. */
export function normalizeDomain(input: string): string {
  const trimmed = input.trim().toLowerCase();
  const noScheme = trimmed.replace(/^https?:\/\//, "");
  const host = noScheme.split("/")[0];
  return host.replace(/^www\./, "");
}

/** Stable rep id from a Clerk userId. Kept as a thin indirection so a future
 *  rep↔{clerk,telegram} map (G §3.3) can swap the source without touching callers. */
export function repIdFromClerk(clerkUserId: string): string {
  return clerkUserId.trim();
}

/** X-Hermes-Session-Key — the long-term memory scope (stable across /new). ≤256 chars. */
export function sessionKey(repId: string, domain: string): string {
  const key = `${KEY_PREFIX}:rep:${repId}:acct:${normalizeDomain(domain)}`;
  if (key.length > 256) {
    throw new Error(`Hermes session-key exceeds 256 chars: ${key.length}`);
  }
  // Control chars are rejected by Hermes (\r \n \x00) — guard early.
  if (/[\r\n\x00]/.test(key)) {
    throw new Error("Hermes session-key contains control characters");
  }
  return key;
}

/** conversation name — the server-side transcript chain. Same value from phone+laptop = one thread. */
export function conversationName(repId: string, domain: string): string {
  return `prism:${repId}:${normalizeDomain(domain)}`;
}

export interface HermesScope {
  repId: string;
  domain: string;
  sessionKey: string;
  conversation: string;
}

/** Build the full scope for a (clerkUserId, account-domain) pair. */
export function resolveHermesScope(clerkUserId: string, domain: string): HermesScope {
  const repId = repIdFromClerk(clerkUserId);
  const d = normalizeDomain(domain);
  return {
    repId,
    domain: d,
    sessionKey: sessionKey(repId, d),
    conversation: conversationName(repId, d),
  };
}

/**
 * Report-QA binding helper. The prism-report-qa plugin binds the report by
 * content-matching the user's MESSAGE TEXT (company/domain/slug), per session_id.
 * Hermes does NOT thread X-Hermes-Session-Key into the plugin hook ctx (verified on
 * the box), so the deterministic key-bind patch is a no-op and the message tag is the
 * live binding mechanism. We tag EVERY turn (not just the first): the prefix is sent to
 * Hermes only — never shown in the SPA — so it's invisible + idempotent, and binding
 * survives a Hermes restart that clears the per-session_id cache.
 */
export function tagAccountForBinding(userText: string, domain: string): string {
  const d = normalizeDomain(domain);
  // Skip if the user already named the account, to keep the transcript clean.
  if (userText.toLowerCase().includes(d) || userText.toLowerCase().includes(d.split(".")[0])) {
    return userText;
  }
  return `[Account: ${d}] ${userText}`;
}
