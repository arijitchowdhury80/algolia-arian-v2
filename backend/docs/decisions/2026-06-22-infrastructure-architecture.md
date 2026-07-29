# ADR: PRISM Infrastructure Architecture
**Date:** 2026-06-22
**Status:** LOCKED
**Supersedes:** Any prior assumptions about self-hosted Postgres, Temporal Cloud, or Modal

---

## Decision

PRISM will be built multi-tenant from the ground up on the following stack:

| Layer | Technology | Rationale |
|---|---|---|
| **Database (now)** | Self-hosted Postgres (Docker on VPS, SQLAlchemy) | Already working. No migration needed now. SQLAlchemy is DB-agnostic. |
| **Database (production multi-tenant)** | Supabase | Auth + RLS for tenant isolation saves weeks of work. Migrate when first real tenant is ready to onboard — it's a connection string swap + `tenant_id` + RLS policies. |
| **Orchestration** | Self-hosted Temporal on Chowmes VPS | Durable execution, lease/heartbeat, per-activity retry — required for multi-tenant concurrent audits. Self-hosted on VPS is cheaper than Temporal Cloud at any realistic volume. Migrate to Temporal Cloud only when ops burden justifies it. |
| **Compute / Workers** | Python workers on Chowmes VPS | Intelligence pipeline requires Python + Playwright. Cannot run in Edge Functions or serverless. VPS has 6.6GB free RAM — sufficient. |
| **Browser / Scraping** | Scout service on Chowmes VPS | Playwright-based, requires full container runtime. Runs as a service on VPS. |
| **Reverse Proxy** | Caddy (already deployed on VPS) | Already handles TLS and routing for other services. PRISM adds new routes. |
| **Frontend** | Next.js (Vercel or VPS) | Talks to Supabase directly for reads/auth/realtime. Calls PRISM API for audit triggers. |
| **API** | FastAPI (thin, on VPS) | Handles audit triggers, Temporal workflow dispatch. Most CRUD moves to Supabase PostgREST. |

---

## Multi-tenancy model

- `tenant_id` on every table
- Supabase Row Level Security (RLS) enforces tenant isolation at DB level
- Temporal namespace per tenant (or shared namespace with workflow ID prefixes — decide at implementation)

---

## Data storage split

| What | Where |
|---|---|
| Transactional (audits, module_executions, run lifecycle) | Supabase Postgres |
| Intelligence outputs (module output_json, sources) | Supabase Postgres (`module_executions.output_json`) |
| Company profiles (current best-known state) | Supabase Postgres (`accounts`) |
| Algolia evidence DB (customers, case studies, quotes) | Supabase Postgres |
| Search layer for aRRIe copilot | Algolia PRISM_Data (synced from Supabase — latest account profiles + evidence only) |
| Deliverables (deck PDF, SPA) | Supabase Storage |
| Workflow state | Temporal (owns durability, retry, lease) |

---

## What was rejected and why

| Option | Rejected because |
|---|---|
| Self-hosted Postgres (Docker) | Eliminated by Supabase — same Postgres, managed, plus auth/realtime/storage free |
| Temporal Cloud | Costs money; VPS has spare capacity; self-hosting is free and sufficient at current scale |
| Modal for workers | Pay-per-execution adds up; VPS already paid for; Scout runs natively on VPS |
| Drop Temporal entirely | Durability, lease/heartbeat, per-activity retry are real requirements for multi-tenant concurrent audits. A home-rolled Postgres job queue would require re-implementing all of this. |
| Temporal replaced by Inngest | Valid alternative but adds a new SaaS dependency; Temporal is already in the codebase |
| Edge Functions for pipeline | Playwright cannot run in Deno runtime; Python pipeline cannot run in Edge Functions |

---

## VPS deployment plan (Chowmes — 72.61.72.147)

Current services (keep as-is):
- `hermes` — Telegram AI agent
- `ac2-lab-backend` — AI eval harness at `judge.contentengagement.info`
- `caddy` — reverse proxy, TLS

Add for PRISM:
- `temporal` — Temporal server + its Postgres (docker-compose)
- `prism-workers` — Python worker process (Temporal activities)
- `scout` — Scout/Playwright service
- New Caddy routes: `prism.contentengagement.info` (API), `temporal.contentengagement.info` (Temporal UI, auth-gated)

RAM budget after PRISM: ~2.7GB used / 7.8GB total. 5GB headroom.

---

## Migration path

### Phase 1 — now (build features, no DB migration)
- Keep self-hosted Postgres (Docker), SQLAlchemy as-is
- Deploy Temporal + workers + Scout to VPS
- Build remaining 5 intel modules

### Phase 2 — before first real tenant
- Migrate Postgres to Supabase (connection string swap)
- Add `tenant_id` to all tables + RLS policies
- Thin FastAPI — CRUD moves to Supabase PostgREST
- Wire Supabase webhook → Algolia sync

### Always
- `module_executions` is the Temporal activity checkpoint state — never remove

---

## All decisions locked (2026-06-22)

| Decision | Choice | Rationale |
|---|---|---|
| Domain | New domain (TBD) | PRISM is a distinct product from `contentengagement.info` |
| Temporal namespace | Shared namespace + workflow ID prefixes (`tenant_id:audit_id:...`) | Simpler ops; per-tenant namespace adds infra overhead with no benefit at current scale |
| Algolia PRISM_Data sync | Supabase webhooks (event-driven) | Sync fires when `module_executions` completes — no polling lag, no cron drift |
| Frontend hosting | Vercel | Zero ops; Next.js first-party support; free tier covers early stage; VPS reserved for compute-only work |
