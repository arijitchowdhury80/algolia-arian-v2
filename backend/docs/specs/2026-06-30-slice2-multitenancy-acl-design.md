# Slice 2 — Multi-tenancy, ACL, and identity-driven Hermes binding

**Date:** 2026-06-30
**Status:** Design — pending user review → writing-plans
**Depends on:** Slice 1 (identity capture) — `2026-06-30-slice1-google-login-deploy-design.md`
**Tenant model:** Approach 3 — org-ready, simple now (individual ownership + sharing, nullable
`org_id`, one `can_user_see()` ACL seam; flip on Clerk Organizations later with no migration scramble).

## Goal

When Rob, Matt, Arijit, and 10 others log in, each sees **only their own prospects/audits** and can
chat with Cassandra about **only the audits they're allowed to see** — concurrently, with
independent threads, no cross-tenant data leakage.

## "Multi-tenancy" is two problems, not one

| Problem | Status |
|---|---|
| **A — concurrency / thread isolation** (N users, independent Cassandra threads) | **Largely already solved** (verified below) |
| **B — data isolation / ACL** (Rob sees Rob's prospects, not Matt's) | **The real work of this slice** |

## Verified facts (VPS + source, 2026-06-30 — evidence, not memory)

All five pre-design gates were verified on the live box and against source. Repo == production
(`prism-report-qa/__init__.py` sha `b897d9…` identical local and deployed).

1. **Session-key binding exists in code but is a runtime NO-OP (corrected 2026-06-30).**
   `_slug_from_session_key()` (`prism-report-qa/__init__.py:166`) reads `…:acct:<domain>` and is
   *preferred* in bind order (lines 286–298). **BUT** on-box evidence
   (`frontend/lib/hermes-session.ts:70-86`, verified live) states: *"Hermes does NOT thread
   X-Hermes-Session-Key into the plugin hook ctx … so the deterministic key-bind patch is a no-op
   and the message tag is the live binding mechanism."* So today binding is actually driven by the
   `[Account: <domain>]` **message tag** (`tagAccountForBinding`, `hermes-session.ts:79`) parsed by
   `_match_slug`, NOT by the session key. An earlier draft of this spec over-claimed "already built
   + preferred" from a source read without a runtime probe — corrected here.

   **HARD PREREQUISITE for Slice 2's identity-driven binding:** before building, run a *runtime*
   probe to determine whether Hermes threads the session key into the hook `kwargs` (it may have
   changed since the comment was written — the plugin code was added expecting it). Two paths
   depending on the result:
   - **If Hermes now threads the key:** proceed with key-carried userId → plugin ACL call (as below).
   - **If it still does not:** the plugin only reliably receives `session_id`. Then identity must
     ride differently — e.g. a **server-signed account+user assertion in the message tag** (the Next
     server already injects `[Account: …]`; extend it to a signed `[Auth: <userId> <sig>]` the
     plugin verifies), or map `session_id → user` via a backend lookup. Pick in Slice 2 planning
     AFTER the probe. This is the one genuinely unresolved mechanism in this design.
2. **Per-session isolation is safe.** `_BINDINGS` (`:34`) and `_KNOWLEDGE_CACHE` (`:36`) are keyed
   by `session_id`. Concurrent distinct sessions do not share state.
3. **Hermes→FastAPI loopback is live and proven.** Plugin already POSTs to `http://127.0.0.1:8000`
   for knowledge retrieve (`:226`) and gap logging (`:272`). Live check: `/health`=200,
   `/api/v1/modules/`=200. `hermes-prism` is `network_mode: host` → reaches loopback directly.
4. **Concurrency model is async.** `prism-platform.service` runs
   `uvicorn prism_platform.main:app --host 127.0.0.1 --port 8000` (single async process). I/O-bound
   ACL lookups + LLM awaits interleave on the event loop; ~10 concurrent users is a non-issue.
5. **Ownership stamp point identified.** `prism_platform/api/routers/audits.py:113` —
   `audit = Audit(account_id=account.id)` creates the row with no user → `user_id` defaults
   `"system"` (`db/models.py:87`). `create_audit` (`:93`) is the clean injection point.

## A — How Cassandra serves N users (mostly already there)

- Each user → distinct session key (carrying their userId) → distinct `session_id` → distinct
  `_BINDINGS[session_id]` → **independent thread**. 10 users = 10 keys, no shared conversation state.
- **One shared Cassandra SOUL** for everyone — same persona, separate threads. No per-user persona.
- Async uvicorn + I/O-bound LLM calls → concurrency for tens of users is fine. Scale is a question
  at hundreds, not tens.

## B — Data model + ACL (the real work)

### Ownership model: shared account, per-audit ownership

`accounts.domain` is **globally unique** (`db/models.py:36`). That constraint is correct and we
embrace it: company intel (executives, competitors, revenue, news) is identical regardless of who
audits, so it is **shared canonical data, owned by no one**. Ownership lives one level down, on the
**audit**.

- **`accounts`** = canonical, shared company intel (keep `domain` unique). Unowned.
- **`audits`** = a user's run against a company (`account_id` + `user_id`). **Ownership + ACL here.**
  Rob and Matt both working PetSmart = one `accounts` row, two `audits`, each owns theirs.
- **"Rob's prospects"** = accounts Rob has an audit for (or is shared into). The list view joins
  through audits.

### Schema changes

| Change | Table | Detail |
|---|---|---|
| New `users` (from Slice 1, extended) | — | `id` text PK = Clerk userId, `email`, `name`, `org_id` nullable |
| `user_id` → FK | `audits` | FK to `users.id`; stamped at `create_audit` (`audits.py:113`). Stop defaulting `"system"` |
| New `audit_shares` | — | `(audit_id, shared_with_user_id, permission)` — explicit sharing |
| `org_id` nullable | `audits` (or via owner) | org-ready; null today, populated when Clerk Orgs flips on |

### The single ACL seam

```
can_user_see(user, audit) -> bool
    = user owns audit
      OR audit shared with user (audit_shares)
      OR (same org_id AND user has leader/admin role)   # dormant until Clerk Orgs
```

- Lives in the **FastAPI backend**. It is the **only** security boundary.
- **Hermes and the LLM never decide access — they ask the backend.** The model is not a boundary.

### Per-audit reports

Today reports are keyed **per-domain** (one PetSmart report on prism-hub). Per-user ownership means
reports become **per-audit** (Rob's PetSmart report ≠ Matt's). Deliverables get keyed by `audit_id`;
report storage namespaced by `audit_id`; the Hermes binding resolves user → their audit → that
audit's report.

> Simpler variant (rejected by default): one shared report per company. Means Rob and Matt see the
> *same* PetSmart report — fine for shared intel, wrong once their audits diverge. Default = per-audit.

## Identity-driven binding rewrite (gated on the runtime probe — see verified fact #1)

> **Prerequisite:** the runtime probe (verified fact #1) must first confirm HOW authenticated
> identity reaches the plugin — session key in `kwargs`, or a server-signed message-tag assertion,
> or a `session_id → user` backend lookup. The flow below assumes the key reaches the plugin; if it
> does not, swap the "reads userId from key" step for the chosen alternative. Everything downstream
> (the ACL call + refuse-on-disallowed) is identical.

```
Rob logs in (Clerk, Google) → clerkUserId = tenant key
  → Next.js /api/hermes extracts userId via Clerk auth() (server-side, verified)
  → builds session key: agent:main:prism:spa:<clerkUserId>:acct:<domain>
  → (X-Hermes-Session-Key) → Hermes → report-qa plugin pre_llm_call
  → plugin calls FastAPI: "which audits/domains can <clerkUserId> see?"  [reuses proven loopback]
  → binds ONLY an allowed report; domain-not-allowed → REFUSE ("not in your prospects")
```

- New backend endpoint: `GET /api/v1/acl/visible?user_id=…` → allowed audit_ids/domains, backed by
  `can_user_see()`. Reuses the proven east-west loopback (gate 3).
- `_slug_from_session_key` (`:166`) gains an ACL gate: the `:acct:<domain>` only binds if the
  userId-in-key is allowed that domain. The company in the message only *selects within* the allowed
  set; it stops being the security boundary.

## Audit ownership stamping

`create_audit` (`audits.py:93`) takes the authenticated user from a request dependency and passes
`user_id=clerkUserId` to `Audit(...)` (`:113`). This is what makes "their prospects" populate.

## Security / threat model

**The session key is bearer-equivalent.** `_slug_from_session_key` binds purely on the key's
`:acct:<domain>`. Therefore:

1. **The userId in the key must be set server-side from Clerk-verified identity only** (the Next.js
   `/api/hermes` route, which already calls `auth()`), never from the browser.
2. **The plugin's ACL call checks "can *this* userId see *this* domain"** before binding — the
   backend, not the key, is the authority.
3. **The Hermes API key (which authorizes setting the session key) must never reach the browser.**
   Only the Next.js server holds it. Public traffic can't hit Hermes directly (bearer-gated).

If any of these three break, a forged key could bind another tenant's report. They are the
non-negotiable invariants of this slice.

## Concurrency correctness (verified, not assumed)
- Distinct session keys → distinct `session_id` → distinct `_BINDINGS`/`_KNOWLEDGE_CACHE` entries
  (gates 1–2). No cross-tenant bleed by construction.
- Async uvicorn handles concurrent ACL lookups (gate 4).

## Out of scope
- Clerk Organizations activation + leader/admin role UI (the schema is org-ready; the *flip* is a
  later slice).
- Migrating the static prism-hub reports into the authed app (that's the report-gating slice
  between Slice 1 and full Slice 2 build — sequence in writing-plans).

## Open items for the plan
- Exact `audit_shares.permission` values (view-only vs comment) — start with view-only.
- Report storage migration path: per-domain → per-audit namespacing (data migration for existing
  reports).
- Whether `/api/v1/acl/visible` returns domains, audit_ids, or both (binding needs domain; list
  views need audit_ids).
- East-west auth between Hermes plugin and the new ACL endpoint (loopback-only vs shared secret).
