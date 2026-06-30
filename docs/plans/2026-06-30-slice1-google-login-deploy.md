# Slice 1: Google Login + VPS Deploy + Identity Capture — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship "Sign in with Google" on the Next.js app deployed at `prism.chowmes.com/app` (VPS, systemd + Caddy), and persist each authenticated Clerk user into a `users` table as the durable tenant key.

**Architecture:** Clerk handles Google OAuth (a dashboard toggle — `<SignIn>` auto-renders enabled social connections). The app deploys as a Node systemd service behind Caddy at the `/app` basePath. On each authenticated page load, the Next.js server upserts the Clerk-verified user into the FastAPI backend over loopback (`127.0.0.1:8000`), creating the tenant identity Slice 2's ACL builds on.

**Tech Stack:** Next.js 15 + Clerk v7 (frontend); FastAPI + SQLAlchemy async + Alembic + Postgres (backend); Caddy + systemd + Node 22 (VPS).

## Global Constraints

- **Pydantic on every boundary** (CLAUDE.md rule 7). Request models use `model_config = ConfigDict(extra="forbid")`, matching `audits.py`/`knowledge.py`.
- **No bare `except`; structlog structured logging** — match existing routers (`logger.info("event.name", key=val)`).
- **Backend stays loopback-only** (`127.0.0.1:8000`). **Never add a Caddy route to port 8000.** The Next.js server (on the box) is the only caller of the upsert endpoint; that is the trust boundary.
- **`BYPASS_AUTH` must be UNSET** in the production `prism-frontend.service` env (read at `middleware.ts:10`, `layout.tsx:18`).
- **Migrations** live in `alembic/versions/`; new revision `"009"`, `down_revision = "008"`.
- **Backend verify gate:** `ruff check . && ruff format --check . && mypy prism_platform --strict && pytest tests/test_users.py -v`. Pure-logic tests run anywhere; DB tests are `@pytest.mark.db` (need local Postgres with migrations applied) — run with `-m 'not db'` where Postgres is absent.
- **Same-origin path route:** the app lives under `/app` so app + (future gated) reports share the Clerk cookie. `basePath: '/app'` is mandatory.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `prism_platform/db/models.py` (modify) | Add `User` ORM model |
| `alembic/versions/009_add_users.py` (create) | `users` table migration |
| `prism_platform/api/routers/users.py` (create) | `POST /api/v1/users/upsert` (loopback-trusted, idempotent) |
| `prism_platform/main.py` (modify) | Register the users router |
| `tests/test_users.py` (create) | Pure-logic + `@pytest.mark.db` tests |
| `frontend/next.config.*` (modify) | `basePath: '/app'` |
| `frontend/lib/sync-user.ts` (create) | Server fn: Clerk `currentUser()` → backend upsert |
| `frontend/app/(authenticated)/layout.tsx` (modify) | Call `syncUser()` on authed load |
| `docs/runbooks/slice1-deploy.md` (create in Task 6) | The deploy runbook (R1–R5) |

---

## Task 1: `User` model + migration 009

**Files:**
- Modify: `prism_platform/db/models.py` (add `User` after `Audit`/before the Algolia section)
- Create: `alembic/versions/009_add_users.py`
- Test: `tests/test_users.py`

**Interfaces:**
- Produces: `User` ORM — `id: str` (PK = Clerk userId), `email: str | None`, `name: str | None`, `org_id: str | None`, `created_at`, `updated_at`. Table name `"users"`.

- [ ] **Step 1: Write the failing pure-logic test**

Create `tests/test_users.py`:

```python
"""Tests for the users tenant-identity table + upsert router.

Pure-logic tests run anywhere. DB tests (@pytest.mark.db) need a live Postgres
with migration 009 applied:  pytest tests/test_users.py -m 'not db' -v
"""
from __future__ import annotations

import pytest


class TestUserModel:
    def test_user_table_name(self) -> None:
        from prism_platform.db.models import User

        assert User.__tablename__ == "users"

    def test_user_has_tenant_columns(self) -> None:
        from prism_platform.db.models import User

        cols = set(User.__table__.columns.keys())
        assert {"id", "email", "name", "org_id", "created_at", "updated_at"} <= cols

    def test_user_id_is_primary_key(self) -> None:
        from prism_platform.db.models import User

        assert User.__table__.primary_key.columns.keys() == ["id"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_users.py::TestUserModel -v`
Expected: FAIL — `ImportError: cannot import name 'User' from prism_platform.db.models`

- [ ] **Step 3: Add the `User` model**

In `prism_platform/db/models.py`, after the `Audit` class (line ~100), add:

```python
class User(Base):
    """Tenant identity — mirrors a Clerk user. id == Clerk userId.

    org_id is the org-ready seam (null today; populated when Clerk Organizations
    is enabled in a later slice). See docs/specs/2026-06-30-slice2-multitenancy-acl-design.md.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # Clerk userId
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    org_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("idx_users_org", "org_id"),)
```

(`Text`, `Index`, `DateTime`, `Mapped`, `mapped_column`, `datetime` are already imported in this file.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_users.py::TestUserModel -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Write the migration**

Create `alembic/versions/009_add_users.py`:

```python
"""Add users table — Clerk-mirrored tenant identity.

Revision ID: 009
Revises: 008
Create Date: 2026-06-30
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "009"
down_revision: str = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Text, primary_key=True),  # Clerk userId
        sa.Column("email", sa.Text, nullable=True),
        sa.Column("name", sa.Text, nullable=True),
        sa.Column("org_id", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("idx_users_org", "users", ["org_id"])


def downgrade() -> None:
    op.drop_index("idx_users_org", table_name="users")
    op.drop_table("users")
```

- [ ] **Step 6: Apply the migration locally and verify head**

Run: `alembic upgrade head && alembic current`
Expected: output ends at `009 (head)`; no error.

- [ ] **Step 7: Commit**

```bash
git add prism_platform/db/models.py alembic/versions/009_add_users.py tests/test_users.py
git commit -m "feat(auth): add users table — Clerk-mirrored tenant identity (slice 1)"
```

---

## Task 2: `POST /api/v1/users/upsert` (loopback-trusted, idempotent)

**Files:**
- Create: `prism_platform/api/routers/users.py`
- Modify: `prism_platform/main.py` (register router)
- Test: `tests/test_users.py` (append)

**Interfaces:**
- Consumes: `User` model + `DbSession` from `prism_platform.api.deps`.
- Produces: `UpsertUserRequest(id: str, email: str | None, name: str | None, org_id: str | None)`, `UpsertUserResponse(id: str, created: bool, updated: bool)`, and `async def upsert_user(body, session) -> UpsertUserResponse`.

- [ ] **Step 1: Write the failing pure-logic test (append to `tests/test_users.py`)**

```python
class TestUpsertModels:
    def test_request_forbids_extra_fields(self) -> None:
        from pydantic import ValidationError

        from prism_platform.api.routers.users import UpsertUserRequest

        with pytest.raises(ValidationError):
            UpsertUserRequest(id="user_1", surprise="x")

    def test_request_minimal_is_valid(self) -> None:
        from prism_platform.api.routers.users import UpsertUserRequest

        req = UpsertUserRequest(id="user_1")
        assert req.id == "user_1"
        assert req.email is None

    def test_response_shape(self) -> None:
        from prism_platform.api.routers.users import UpsertUserResponse

        r = UpsertUserResponse(id="user_1", created=True, updated=False)
        assert r.created is True and r.updated is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_users.py::TestUpsertModels -v`
Expected: FAIL — `ModuleNotFoundError: prism_platform.api.routers.users`

- [ ] **Step 3: Write the router**

Create `prism_platform/api/routers/users.py`:

```python
"""PRISM Users Router — tenant identity upsert (Clerk-mirrored).

Loopback-trusted: this endpoint is reachable ONLY at 127.0.0.1:8000 (never
exposed via Caddy). The Next.js server, holding a Clerk-verified session, is the
only caller. Do not add a public route to this endpoint.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from prism_platform.api.deps import DbSession
from prism_platform.db.models import User

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()


class UpsertUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str  # Clerk userId
    email: str | None = None
    name: str | None = None
    org_id: str | None = None


class UpsertUserResponse(BaseModel):
    id: str
    created: bool
    updated: bool


@router.post("/upsert", response_model=UpsertUserResponse)
async def upsert_user(body: UpsertUserRequest, session: DbSession) -> UpsertUserResponse:
    """Insert or refresh a tenant-identity row keyed by Clerk userId. Idempotent."""
    result = await session.execute(select(User).where(User.id == body.id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(id=body.id, email=body.email, name=body.name, org_id=body.org_id)
        session.add(user)
        await session.flush()
        logger.info("upsert_user.created", user_id=body.id)
        return UpsertUserResponse(id=body.id, created=True, updated=False)

    user.email = body.email
    user.name = body.name
    if body.org_id is not None:
        user.org_id = body.org_id
    await session.flush()
    logger.info("upsert_user.updated", user_id=body.id)
    return UpsertUserResponse(id=body.id, created=False, updated=True)
```

- [ ] **Step 4: Register the router in `main.py`**

In `prism_platform/main.py`, add to the imports the `users` router (match the existing import style for `audits`, `knowledge`), then after line 37 (`app.include_router(knowledge.router, ...)`) add:

```python
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
```

- [ ] **Step 5: Run pure-logic tests to verify pass**

Run: `pytest tests/test_users.py -m 'not db' -v`
Expected: PASS (all `TestUserModel` + `TestUpsertModels`)

- [ ] **Step 6: Write the DB integration tests (append to `tests/test_users.py`)**

```python
@pytest.mark.db
@pytest.mark.asyncio
async def test_upsert_creates_then_updates() -> None:
    from sqlalchemy import delete

    from prism_platform.api.routers.users import UpsertUserRequest, upsert_user
    from prism_platform.db.models import User
    from prism_platform.db.session import get_session

    uid = "user_test_slice1_upsert"
    async for session in get_session():
        await session.execute(delete(User).where(User.id == uid))
        await session.commit()

    # First call → created
    async for session in get_session():
        r1 = await upsert_user(
            UpsertUserRequest(id=uid, email="a@example.com", name="Rob"), session
        )
        await session.commit()
    assert r1.created is True and r1.updated is False

    # Second call → updated, same id
    async for session in get_session():
        r2 = await upsert_user(
            UpsertUserRequest(id=uid, email="rob@algolia.com", name="Rob R"), session
        )
        await session.commit()
    assert r2.created is False and r2.updated is True
    assert r2.id == uid

    # Verify persisted value
    async for session in get_session():
        from sqlalchemy import select

        row = (await session.execute(select(User).where(User.id == uid))).scalar_one()
        assert row.email == "rob@algolia.com"

    # Cleanup
    async for session in get_session():
        await session.execute(delete(User).where(User.id == uid))
        await session.commit()
```

- [ ] **Step 7: Run DB tests (requires local Postgres + migration 009)**

Run: `pytest tests/test_users.py -v`
Expected: PASS. If Postgres is unavailable, run `pytest tests/test_users.py -m 'not db' -v` and defer DB tests to a box with the DB up.

- [ ] **Step 8: Backend verify gate + commit**

```bash
ruff check prism_platform tests && ruff format --check prism_platform tests && mypy prism_platform --strict
git add prism_platform/api/routers/users.py prism_platform/main.py tests/test_users.py
git commit -m "feat(auth): POST /api/v1/users/upsert — idempotent tenant-identity upsert (slice 1)"
```

---

## Task 3: Frontend — `/app` basePath + Clerk paths + identity upsert

> No frontend test runner exists (`frontend/package.json` has no test script). This task is verified in dev (Task 4), not by unit tests. Keep changes minimal and follow existing patterns.

**Files:**
- Modify: `frontend/next.config.*`
- Create: `frontend/lib/sync-user.ts`
- Modify: `frontend/app/(authenticated)/layout.tsx`

**Interfaces:**
- Consumes: backend `POST /api/v1/users/upsert` (Task 2); Clerk `auth()` + `currentUser()` from `@clerk/nextjs/server`.

- [ ] **Step 1: Find the Next config file**

Run: `ls frontend/next.config.*`
Note the extension (`.ts` / `.js` / `.mjs`) for the next step.

- [ ] **Step 2: Add `basePath`**

In `frontend/next.config.*`, add `basePath: '/app'` to the exported config object. Example (TS):

```ts
const nextConfig = {
  basePath: "/app",
  // ...keep any existing config
};
export default nextConfig;
```

- [ ] **Step 3: Create the server-side user-sync helper**

Create `frontend/lib/sync-user.ts`:

```ts
import "server-only";
import { currentUser } from "@clerk/nextjs/server";

const PRISM_API_URL = process.env.PRISM_API_URL ?? "http://127.0.0.1:8000";

/**
 * Mirror the Clerk-verified user into the PRISM backend (loopback) as the tenant
 * key. Idempotent + fail-open: a backend hiccup must never block the page render.
 */
export async function syncUser(): Promise<void> {
  const user = await currentUser();
  if (!user) return;
  const email = user.primaryEmailAddress?.emailAddress ?? null;
  const name = [user.firstName, user.lastName].filter(Boolean).join(" ") || null;
  try {
    await fetch(`${PRISM_API_URL}/api/v1/users/upsert`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: user.id, email, name }),
    });
  } catch {
    // fail-open: identity capture is best-effort per page load; never break chat
  }
}
```

- [ ] **Step 4: Call `syncUser()` from the authenticated layout**

Modify `frontend/app/(authenticated)/layout.tsx` to an async server component that awaits `syncUser()` before rendering:

```tsx
import { AppShell } from "@/components/layout/app-shell";
import { syncUser } from "@/lib/sync-user";

export default async function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  await syncUser();
  return <AppShell>{children}</AppShell>;
}
```

- [ ] **Step 5: Add Clerk path env vars to `frontend/.env.local` (dev)**

Append (these tell Clerk the basePath-prefixed routes):

```
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/app/sign-in
NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL=/app/chat
NEXT_PUBLIC_CLERK_SIGN_UP_FALLBACK_REDIRECT_URL=/app/chat
```

- [ ] **Step 6: Commit**

```bash
git add frontend/next.config.* frontend/lib/sync-user.ts "frontend/app/(authenticated)/layout.tsx"
git commit -m "feat(auth): /app basePath + server-side Clerk user sync to backend (slice 1)"
```

---

## Task 4: Dev verification (evidence before deploy)

- [ ] **Step 1: Start backend + frontend in dev**

Backend (with local Postgres up + migration 009 applied): `uvicorn prism_platform.main:app --port 8000`
Frontend: `cd frontend && npm run dev` (or `pnpm dev`). Ensure `BYPASS_AUTH` is **unset** so Clerk is active. Clerk dev keys + Google enabled (Runbook R1 dev portion).

- [ ] **Step 2: Walk the Google sign-in flow**

In a browser: open `http://localhost:3000/app` → expect redirect to `/app/sign-in` → the Clerk card shows **Continue with Google** → complete OAuth → land on `/app/chat`.

- [ ] **Step 3: Confirm identity captured**

Run: `psql "$DATABASE_URL" -c "select id, email, name from users;"`
Expected: a row whose `id` is your Clerk userId and `email` is your Google email.

- [ ] **Step 4: Record evidence**

Capture the screenshot of the Google button + the `psql` row output into the deploy record. (Per CLAUDE.md: never claim done without showing output.)

---

## Task 5: VPS deploy (runbook — live-verify, not unit-tested)

> These steps run on the Chowmes VPS (`chowmesadmin@72.61.72.147`, key auth). Mirror `prism-platform.service`. Some sub-steps are **user-owned** (Clerk/Google dashboards — Claude can't click them).

### R1 — Clerk production + Google (USER, in dashboards)
- [ ] Create/confirm a Clerk **production** instance bound to domain `prism.chowmes.com`.
- [ ] Enable the **Google** social connection. For prod, create a Google Cloud OAuth client and paste client ID/secret into Clerk; set the authorized redirect to Clerk's prod Frontend API domain (Clerk shows the exact value).
- [ ] In Clerk paths, set sign-in URL `/app/sign-in` and redirect URLs under `/app/*` (Clerk binds to the domain; paths come from env in R4).

### R2 — Ship code to the box
- [ ] Sync `frontend/` to `/opt/prism-frontend` on the VPS (git pull or rsync). Confirm Node: `node --version` (expect v22).
- [ ] Install + build: `cd /opt/prism-frontend && npm ci && npm run build` (if the lockfile is pnpm, `corepack enable && pnpm install --frozen-lockfile && pnpm build` — decide from the lockfile present).
- [ ] Apply backend migration on the box: `cd /opt/prism-platform && .venv/bin/alembic upgrade head` (expect `009`).

### R3 — systemd service (loopback :3000)
- [ ] Create `/etc/systemd/system/prism-frontend.service`:

```ini
[Unit]
Description=PRISM Frontend (Next.js)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/prism-frontend
EnvironmentFile=/opt/prism-frontend/.env.production
ExecStart=/usr/bin/npx next start -H 127.0.0.1 -p 3000
Restart=always

[Install]
WantedBy=multi-user.target
```

- [ ] Write `/opt/prism-frontend/.env.production` (mode 600) with: Clerk **prod** `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` + `CLERK_SECRET_KEY`; the three `NEXT_PUBLIC_CLERK_*` path vars from Task 3 Step 5; `PRISM_API_URL=http://127.0.0.1:8000`; `HERMES_API_URL` + `HERMES_API_KEY`. **Do NOT set `BYPASS_AUTH`.**
- [ ] `sudo systemctl daemon-reload && sudo systemctl enable --now prism-frontend && sudo systemctl status prism-frontend` (expect active/running). Confirm listening: `ss -ltnp | grep 127.0.0.1:3000`.

### R4 — Caddy `/app` route
- [ ] Locate the Caddyfile serving `prism.chowmes.com`: `sudo grep -rl "prism.chowmes.com" $(sudo find / -name Caddyfile 2>/dev/null)`.
- [ ] In the `prism.chowmes.com` site block, add a `/app` reverse_proxy **above** the existing static handler so it takes precedence:

```caddy
handle_path /app/* {
    reverse_proxy 127.0.0.1:3000
}
# existing static prism-hub handler (e.g. reverse_proxy 127.0.0.1:8651) stays below
```

  > Note: `next start` already serves assets under `/app` because of `basePath`. Use `handle` vs `handle_path` per how basePath emits asset URLs — verify in R5 that `/app/_next/...` assets 200. If assets 404, switch `handle_path` → `handle` (keeps the `/app` prefix).
- [ ] Reload Caddy: `sudo docker exec caddy caddy reload --config /etc/caddy/Caddyfile` (or the container's reload command). **Confirm the static reports at `prism.chowmes.com` still load** (route isolation).

### R5 — Live verification (evidence)
- [ ] `curl -sI https://prism.chowmes.com/app/sign-in` → expect 200 (HTML).
- [ ] In a browser: `https://prism.chowmes.com/app` → `/app/sign-in` → **Continue with Google** → OAuth → `/app/chat`. Screenshot each.
- [ ] On the box: `sudo docker exec prism-platform-postgres-1 psql -U prism -d prism -c "select id,email from users;"` → your row appears.
- [ ] Confirm `prism.chowmes.com` (no `/app`) still serves the public static reports unchanged.

---

## Task 6: Capture the deploy record + finish

- [ ] **Step 1: Write the deploy record**

Create `docs/runbooks/slice1-deploy.md` capturing: the live URLs, the systemd unit, the Caddy block added, and the R5 evidence (screenshots + psql output). Per CLAUDE.md cardinal rule 1.

- [ ] **Step 2: Commit**

```bash
git add docs/runbooks/slice1-deploy.md
git commit -m "docs(auth): slice 1 deploy record — Google login live at prism.chowmes.com/app"
```

- [ ] **Step 3: Finishing the branch** — invoke `superpowers:finishing-a-development-branch` to decide merge/PR for `feat/prism-e2e-cycle`.

---

## Self-Review (against the spec)

**Spec coverage:**
- Enable Google → R1. ✅
- Deploy to VPS (systemd + Caddy, `/app`) → R2–R4. ✅
- Identity capture hook (persist Clerk userId as tenant key) → Tasks 1–3 (`users` table + upsert + `syncUser`). ✅
- Verify end-to-end → Tasks 4 + R5. ✅
- `basePath`, Caddy precedence, Clerk path env, `BYPASS_AUTH` unset, loopback-only backend → Global Constraints + R3/R4. ✅
- Open item "webhook vs lazy upsert" → resolved to **lazy upsert over loopback** (Task 3), simplest secure path given the backend is loopback-only.

**Placeholder scan:** No TBD/TODO. The two genuinely env-dependent decisions (next.config extension; npm vs pnpm) are explicit *locate-then-act* steps, not placeholders.

**Type consistency:** `UpsertUserRequest`/`UpsertUserResponse`/`upsert_user` names match across Task 2 router, tests, and the `sync-user.ts` payload (`{id, email, name}` ⊆ request fields). `User` columns match between model (Task 1) and migration (Task 1) and the upsert (Task 2).

**Out of scope (Slice 2):** ACL, audit ownership stamping, report-binding ACL, per-audit reports — not touched here.
