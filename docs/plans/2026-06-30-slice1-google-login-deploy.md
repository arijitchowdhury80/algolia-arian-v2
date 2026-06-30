# Slice 1: Unify the site under the authed Next app — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Next.js app the entire front door for `prism.chowmes.com`: a public landing at `/`, Google login, and all audit reports + chat behind login (blanket gate). Persist each Clerk user as the tenant key.

**Architecture:** Next owns the root (no basePath). The existing static landing is served as-is from `public/` via a rewrite. Reports are served as-is from a runtime `REPORTS_HTML_DIR` through a Clerk-gated catch-all route handler (with its own `auth()` check, because dotted paths bypass middleware). Report chat keeps working via a new gated `/api/report-chat` (port of the static Hermes proxy) and a repointed widget. Identity is captured into a `users` table.

**Tech Stack:** Next.js 15 + Clerk v7 (frontend); FastAPI + SQLAlchemy async + Alembic + Postgres (backend); Caddy + systemd + Node 22 (VPS).

## Global Constraints

- **Pydantic on every boundary** (`ConfigDict(extra="forbid")` on request models), structlog logging, no bare `except` — match existing routers.
- **Backend stays loopback-only** (`127.0.0.1:8000`); never Caddy-expose it. The on-box Next server is the only caller of `/api/v1/users/upsert`.
- **`BYPASS_AUTH` UNSET in prod** service env (read at `middleware.ts:10`, `layout.tsx:18`).
- **The report route handler MUST `auth()`-check itself.** Dotted paths (`.png`, `.js`) bypass the Clerk middleware matcher (`middleware.ts:19`), so middleware alone does not gate screenshots.
- **No basePath.** The app owns `/`.
- **Reports are not committed to git** (~14 MB). Synced to `REPORTS_HTML_DIR` at deploy; read at runtime.
- **Landing + assets + widget ARE committed** to `frontend/public/` (~3 MB) so they are in the build.
- Migrations: `alembic/versions/`, revision `"009"`, `down_revision = "008"`.
- Backend verify gate: `ruff check . && ruff format --check . && mypy prism_platform --strict && pytest tests/test_users.py -v` (DB tests `@pytest.mark.db`).

## File Structure

| File | Responsibility |
|------|----------------|
| `prism_platform/db/models.py` (mod) | `User` model |
| `alembic/versions/009_add_users.py` (new) | `users` table |
| `prism_platform/api/routers/users.py` (new) | `POST /api/v1/users/upsert` |
| `prism_platform/main.py` (mod) | register users router |
| `tests/test_users.py` (new) | backend tests |
| `frontend/public/landing.html` + `frontend/public/assets/*` + `frontend/public/chat-widget.js` (new) | public landing + shared assets + widget |
| `frontend/app/page.tsx` (delete) | remove the `/`→`/chat` redirect |
| `frontend/next.config.ts` (mod) | rewrite `/` → `/landing.html` |
| `frontend/middleware.ts` (mod) | public = `/`, `/sign-in`, `/demo`; gate the rest |
| `frontend/app/reports/page.tsx` (new) | gated report list |
| `frontend/app/reports/[...slug]/route.ts` (new) | gated report-file streamer |
| `frontend/app/api/report-chat/route.ts` (new) | gated Hermes proxy for report chat |
| `frontend/lib/sync-user.ts` (new) | server-side identity upsert |
| `frontend/app/(authenticated)/layout.tsx` (mod) | call `syncUser()` |
| `frontend/.gitignore` (mod) | ignore `report-data/` |

---

## Task 1: `User` model + migration 009

**Files:** Modify `prism_platform/db/models.py`; Create `alembic/versions/009_add_users.py`; Test `tests/test_users.py`.

**Interfaces:** Produces `User` ORM (`id: str` PK = Clerk userId, `email/name/org_id: str | None`, `created_at`, `updated_at`), table `"users"`.

- [ ] **Step 1: Write the failing pure-logic test** — create `tests/test_users.py`:

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

- [ ] **Step 2: Run test, verify it fails** — `pytest tests/test_users.py::TestUserModel -v` → FAIL (`cannot import name 'User'`).

- [ ] **Step 3: Add the `User` model** — in `prism_platform/db/models.py` after the `Audit` class:

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

(`Text`, `Index`, `DateTime`, `Mapped`, `mapped_column`, `datetime` are already imported.)

- [ ] **Step 4: Run test, verify pass** — `pytest tests/test_users.py::TestUserModel -v` → PASS (3).

- [ ] **Step 5: Write the migration** — create `alembic/versions/009_add_users.py`:

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
        sa.Column("id", sa.Text, primary_key=True),
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

- [ ] **Step 6: Apply + verify** — `alembic upgrade head && alembic current` → ends at `009 (head)`.

- [ ] **Step 7: Commit**

```bash
git add prism_platform/db/models.py alembic/versions/009_add_users.py tests/test_users.py
git commit -m "feat(auth): add users table — Clerk-mirrored tenant identity (slice 1)"
```

---

## Task 2: `POST /api/v1/users/upsert`

**Files:** Create `prism_platform/api/routers/users.py`; Modify `prism_platform/main.py`; append to `tests/test_users.py`.

**Interfaces:** Produces `UpsertUserRequest(id, email, name, org_id)`, `UpsertUserResponse(id, created, updated)`, `async def upsert_user(body, session)`.

- [ ] **Step 1: Failing pure-logic test (append to `tests/test_users.py`):**

```python
class TestUpsertModels:
    def test_request_forbids_extra(self) -> None:
        from pydantic import ValidationError

        from prism_platform.api.routers.users import UpsertUserRequest

        with pytest.raises(ValidationError):
            UpsertUserRequest(id="user_1", surprise="x")

    def test_request_minimal(self) -> None:
        from prism_platform.api.routers.users import UpsertUserRequest

        assert UpsertUserRequest(id="user_1").email is None

    def test_response_shape(self) -> None:
        from prism_platform.api.routers.users import UpsertUserResponse

        r = UpsertUserResponse(id="user_1", created=True, updated=False)
        assert r.created and not r.updated
```

- [ ] **Step 2: Run, verify fail** — `pytest tests/test_users.py::TestUpsertModels -v` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write the router** — create `prism_platform/api/routers/users.py`:

```python
"""PRISM Users Router — tenant identity upsert (Clerk-mirrored).

Loopback-trusted: reachable ONLY at 127.0.0.1:8000 (never Caddy-exposed). The
Next.js server (holding a Clerk-verified session) is the only caller.
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

    id: str
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
        session.add(User(id=body.id, email=body.email, name=body.name, org_id=body.org_id))
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

- [ ] **Step 4: Register in `main.py`** — add the `users` import alongside the other router imports, then after the `knowledge` line (`main.py:37`):

```python
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
```

- [ ] **Step 5: Run pure-logic tests** — `pytest tests/test_users.py -m 'not db' -v` → PASS.

- [ ] **Step 6: DB integration test (append to `tests/test_users.py`):**

```python
@pytest.mark.db
@pytest.mark.asyncio
async def test_upsert_creates_then_updates() -> None:
    from sqlalchemy import delete, select

    from prism_platform.api.routers.users import UpsertUserRequest, upsert_user
    from prism_platform.db.models import User
    from prism_platform.db.session import get_session

    uid = "user_test_slice1_upsert"
    async for session in get_session():
        await session.execute(delete(User).where(User.id == uid))
        await session.commit()

    async for session in get_session():
        r1 = await upsert_user(UpsertUserRequest(id=uid, email="a@x.com", name="Rob"), session)
        await session.commit()
    assert r1.created and not r1.updated

    async for session in get_session():
        r2 = await upsert_user(UpsertUserRequest(id=uid, email="rob@algolia.com", name="Rob R"), session)
        await session.commit()
    assert not r2.created and r2.updated and r2.id == uid

    async for session in get_session():
        row = (await session.execute(select(User).where(User.id == uid))).scalar_one()
        assert row.email == "rob@algolia.com"

    async for session in get_session():
        await session.execute(delete(User).where(User.id == uid))
        await session.commit()
```

- [ ] **Step 7: Run DB test** — `pytest tests/test_users.py -v` (needs Postgres + migration 009). If no DB, run `-m 'not db'` and defer.

- [ ] **Step 8: Verify gate + commit**

```bash
ruff check prism_platform tests && ruff format --check prism_platform tests && mypy prism_platform --strict
git add prism_platform/api/routers/users.py prism_platform/main.py tests/test_users.py
git commit -m "feat(auth): POST /api/v1/users/upsert — idempotent tenant-identity upsert (slice 1)"
```

---

## Task 3: Next owns the root + public landing

**Files:** Create `frontend/public/landing.html`, `frontend/public/assets/*`, `frontend/public/chat-widget.js`; Delete `frontend/app/page.tsx`; Modify `frontend/next.config.ts`, `frontend/middleware.ts`.

- [ ] **Step 1: Copy the static landing + assets + widget into `public/`**

```bash
cp ~/prism-hub/index.html frontend/public/landing.html
cp -R ~/prism-hub/assets frontend/public/assets
cp ~/prism-hub/chat-widget.js frontend/public/chat-widget.js
```

(The widget is repointed in Task 5. Assets are referenced at root `/assets/*` by both landing and reports.)

- [ ] **Step 2: Delete the root redirect** — remove `frontend/app/page.tsx` (it currently `redirect("/chat")`; the landing replaces `/`).

```bash
git rm frontend/app/page.tsx
```

- [ ] **Step 3: Add the rewrite** — `frontend/next.config.ts`:

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  async rewrites() {
    return [{ source: "/", destination: "/landing.html" }];
  },
};

export default nextConfig;
```

- [ ] **Step 4: Make `/` public, gate the rest** — `frontend/middleware.ts`, change the matcher line:

```ts
const isPublicRoute = createRouteMatcher(["/", "/sign-in(.*)", "/demo(.*)"]);
```

(`/assets/*` and `/chat-widget.js` carry a `.` so they already bypass the middleware matcher = public. `/reports(.*)` is NOT public → gated.)

- [ ] **Step 5: Dev verify the landing is public** — `cd frontend && npm run dev`. In a logged-OUT browser: open `http://localhost:3000/` → the landing renders, interactive (tour/grid animate), no redirect to sign-in. `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/assets/grid-bg.js` → 200.

- [ ] **Step 6: Commit**

```bash
git add frontend/public frontend/next.config.ts frontend/middleware.ts
git commit -m "feat(site): Next owns the root — public static landing at / (slice 1)"
```

---

## Task 4: Gated report serving (catch-all + list)

**Files:** Create `frontend/app/reports/[...slug]/route.ts`, `frontend/app/reports/page.tsx`; Modify `frontend/.gitignore`.

**Interfaces:** Reads report files from `REPORTS_HTML_DIR` (env; default `<cwd>/report-data`). Serves `/reports/<slug>/...` gated; `/reports` lists slugs.

- [ ] **Step 1: Gitignore the runtime report dir** — append to `frontend/.gitignore`:

```
# runtime-synced audit reports (not committed; ~14 MB)
/report-data/
```

- [ ] **Step 2: Seed a dev sample** — copy two reports for local testing:

```bash
mkdir -p frontend/report-data
cp -R ~/prism-hub/petsmart frontend/report-data/petsmart
cp -R ~/prism-hub/nike frontend/report-data/nike
```

- [ ] **Step 3: Write the gated catch-all streamer** — create `frontend/app/reports/[...slug]/route.ts`:

```ts
import { auth } from "@clerk/nextjs/server";
import { readFile } from "node:fs/promises";
import path from "node:path";

const REPORTS_DIR = path.resolve(
  process.env.REPORTS_HTML_DIR ?? path.join(process.cwd(), "report-data"),
);

const CONTENT_TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".svg": "image/svg+xml",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".ico": "image/x-icon",
};

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ slug?: string[] }> },
): Promise<Response> {
  // Load-bearing: dotted paths (.png/.js) bypass middleware, so gate HERE.
  const { userId } = await auth();
  if (!userId) return new Response("Unauthorized", { status: 401 });

  const segments = (await params).slug ?? [];
  const rel = segments.join("/");
  // A bare /reports/<slug> or trailing slash → that report's index.html.
  const requested = !rel || rel.endsWith("/") || !path.extname(rel)
    ? path.join(rel, "index.html")
    : rel;

  const abs = path.resolve(REPORTS_DIR, requested);
  // Path-traversal guard: resolved path must stay inside REPORTS_DIR.
  if (abs !== REPORTS_DIR && !abs.startsWith(REPORTS_DIR + path.sep)) {
    return new Response("Forbidden", { status: 403 });
  }

  let data: Buffer;
  try {
    data = await readFile(abs);
  } catch {
    return new Response("Not found", { status: 404 });
  }
  const ext = path.extname(abs).toLowerCase();
  return new Response(new Uint8Array(data), {
    status: 200,
    headers: { "Content-Type": CONTENT_TYPES[ext] ?? "application/octet-stream" },
  });
}
```

- [ ] **Step 4: Write the gated report list** — create `frontend/app/reports/page.tsx`:

```tsx
import { readdir } from "node:fs/promises";
import path from "node:path";
import Link from "next/link";

const REPORTS_DIR = process.env.REPORTS_HTML_DIR ?? path.join(process.cwd(), "report-data");

export default async function ReportsPage() {
  let slugs: string[] = [];
  try {
    const entries = await readdir(REPORTS_DIR, { withFileTypes: true });
    slugs = entries.filter((e) => e.isDirectory()).map((e) => e.name).sort();
  } catch {
    slugs = [];
  }
  return (
    <main style={{ maxWidth: 720, margin: "4rem auto", padding: "0 1rem" }}>
      <h1>Audit reports</h1>
      <ul>
        {slugs.map((s) => (
          <li key={s}>
            <Link href={`/reports/${s}/`}>{s}</Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
```

- [ ] **Step 5: Dev verify gating**

```bash
# logged OUT: report HTML redirects to sign-in (middleware), screenshot 401s (handler)
curl -s -o /dev/null -w "html=%{http_code}\n" -L http://localhost:3000/reports/petsmart/
curl -s -o /dev/null -w "png=%{http_code}\n" http://localhost:3000/reports/petsmart/screenshots/01-homepage.png
```

Expected: the `.png` request returns **401** (handler `auth()` blocks it; this is the load-bearing check). In a logged-IN browser, `http://localhost:3000/reports/` lists petsmart + nike, and `/reports/petsmart/` renders the report with screenshots.

- [ ] **Step 6: Commit**

```bash
git add "frontend/app/reports" frontend/.gitignore
git commit -m "feat(reports): gated report serving — catch-all streamer (self-auth) + list (slice 1)"
```

---

## Task 5: Keep report chat working (gated proxy + widget repoint)

**Files:** Create `frontend/app/api/report-chat/route.ts`; Modify `frontend/public/chat-widget.js`.

**Interfaces:** `POST /api/report-chat` consumes `{message, slug, sid}`, streams plain-text deltas from Hermes. Consumes env `HERMES_API_URL`, `HERMES_API_KEY`.

- [ ] **Step 1: Write the gated Hermes proxy** — create `frontend/app/api/report-chat/route.ts` (port of `~/prism-hub/api/chat.js` to a Web-Response handler, like `app/api/hermes/route.ts`, plus a Clerk gate):

```ts
import { auth } from "@clerk/nextjs/server";

export const maxDuration = 60;

const HERMES_API_URL = process.env.HERMES_API_URL;
const HERMES_API_KEY = process.env.HERMES_API_KEY;
const SLUG_ALIASES: Record<string, string> = { orientaltrading: "oriental-trading" };
const MAX_MESSAGE_CHARS = 2000;

export async function POST(req: Request): Promise<Response> {
  const { userId } = await auth();
  if (!userId) return new Response("Unauthorized", { status: 401 });
  if (!HERMES_API_URL || !HERMES_API_KEY) return new Response("chat not configured", { status: 500 });

  let body: { message?: string; slug?: string; sid?: string } = {};
  try {
    body = await req.json();
  } catch {
    return new Response("bad request", { status: 400 });
  }

  const message = typeof body.message === "string" ? body.message.trim() : "";
  const slug = typeof body.slug === "string" ? body.slug.trim().toLowerCase() : "";
  const sid = (typeof body.sid === "string" && body.sid.slice(0, 40)) || "anon";
  if (!message) return new Response("empty message", { status: 400 });
  if (message.length > MAX_MESSAGE_CHARS) return new Response("message too long", { status: 413 });
  if (!slug) return new Response("missing slug", { status: 400 });

  const reportSlug = SLUG_ALIASES[slug] || slug;
  const sessionKey = `agent:main:prism:web:${sid}:acct:${reportSlug}`.replace(/[\r\n\x00]/g, "");
  const conversation = `prism:web:${sid}:${reportSlug}`;
  const input = message.toLowerCase().includes(reportSlug.split("-")[0])
    ? message
    : `[Account: ${reportSlug}] ${message}`;

  const upstream = await fetch(`${HERMES_API_URL}/v1/responses`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${HERMES_API_KEY}`,
      "Content-Type": "application/json",
      "X-Hermes-Session-Key": sessionKey,
    },
    body: JSON.stringify({ model: "hermes-agent", input, conversation, stream: true, store: true }),
  }).catch(() => null);

  if (!upstream || !upstream.ok || !upstream.body) {
    return new Response("upstream error", { status: 502 });
  }

  const upstreamBody = upstream.body;
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const reader = upstreamBody.getReader();
      const decoder = new TextDecoder();
      const encoder = new TextEncoder();
      let buf = "";
      try {
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          let idx: number;
          while ((idx = buf.indexOf("\n\n")) !== -1) {
            const frame = buf.slice(0, idx);
            buf = buf.slice(idx + 2);
            let event = "message";
            const dataLines: string[] = [];
            for (const line of frame.split("\n")) {
              if (line.startsWith("event:")) event = line.slice(6).trim();
              else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
            }
            if (event === "response.output_text.delta" && dataLines.length) {
              try {
                const payload = JSON.parse(dataLines.join("\n")) as { delta?: string };
                if (payload.delta) controller.enqueue(encoder.encode(payload.delta));
              } catch {
                /* skip malformed frame */
              }
            }
          }
        }
      } catch {
        /* upstream cut — end what we have */
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" },
  });
}
```

- [ ] **Step 2: Repoint the widget endpoint** — in `frontend/public/chat-widget.js`, change the fetch (line ~213) from `"/api/chat"` to `"/api/report-chat"`:

```js
      var res = await fetch("/api/report-chat", {
```

- [ ] **Step 3: Fix the widget slug extraction for `/reports/<slug>/`** — replace the slug line (~18):

```js
  var segs = location.pathname.split("/").filter(Boolean);
  var slug = (segs[0] === "reports" ? (segs[1] || "") : (segs[0] || "")).toLowerCase();
```

- [ ] **Step 4: Dev verify report chat**

In a logged-IN browser at `http://localhost:3000/reports/petsmart/`: open the chat panel, ask "what search vendor does PetSmart use?" → a grounded answer streams. Confirm the network call hits `/api/report-chat` (200), not `/api/chat`.
Logged-OUT: `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:3000/api/report-chat -H 'Content-Type: application/json' -d '{"message":"hi","slug":"petsmart"}'` → **401**.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/api/report-chat frontend/public/chat-widget.js
git commit -m "feat(reports): gated /api/report-chat + widget repoint — grounded chat survives migration (slice 1)"
```

---

## Task 6: Identity capture wiring

**Files:** Create `frontend/lib/sync-user.ts`; Modify `frontend/app/(authenticated)/layout.tsx`.

- [ ] **Step 1: Create the server-side sync** — `frontend/lib/sync-user.ts`:

```ts
import "server-only";
import { currentUser } from "@clerk/nextjs/server";

const PRISM_API_URL = process.env.PRISM_API_URL ?? "http://127.0.0.1:8000";

/** Mirror the Clerk-verified user into the PRISM backend (loopback) as the tenant
 *  key. Idempotent + fail-open: a backend hiccup must never block the render. */
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
    /* fail-open: identity capture is best-effort per load */
  }
}
```

- [ ] **Step 2: Call it from the authenticated layout** — `frontend/app/(authenticated)/layout.tsx`:

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

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/sync-user.ts "frontend/app/(authenticated)/layout.tsx"
git commit -m "feat(auth): server-side Clerk user sync to backend on authed load (slice 1)"
```

---

## Task 7: Dev end-to-end verification (evidence)

- [ ] **Step 1: Run both services** — backend `uvicorn prism_platform.main:app --port 8000` (Postgres up, migration 009 applied); frontend `cd frontend && npm run dev` with `BYPASS_AUTH` **unset**, Clerk dev keys + Google enabled (R1 dev portion).

- [ ] **Step 2: Public landing (logged out)** — `/` renders the interactive landing, no redirect.

- [ ] **Step 3: Gate works (logged out)** — `/reports/` redirects to sign-in; `/reports/petsmart/screenshots/01-homepage.png` returns 401; `POST /api/report-chat` returns 401.

- [ ] **Step 4: Google sign-in** — `/sign-in` shows "Continue with Google" → OAuth → lands on `/chat`.

- [ ] **Step 5: Logged-in audits + chat** — `/reports/` lists reports; `/reports/petsmart/` renders with screenshots; chat answers a grounded question via `/api/report-chat`.

- [ ] **Step 6: Identity captured** — `psql "$DATABASE_URL" -c "select id,email,name from users;"` shows your row.

- [ ] **Step 7: Record evidence** — screenshots of (public landing, logged-out 401, Google button, a rendered gated report, chat answer) + the psql output, saved for the deploy record.

---

## Task 8: VPS deploy + cutover (runbook — live-verify)

> On the Chowmes VPS (`chowmesadmin@72.61.72.147`, key auth). Mirrors `prism-platform.service`. Steps marked USER are dashboard-only.

### R1 — Clerk prod + Google (USER)
- [ ] Clerk **production** instance bound to `prism.chowmes.com`; enable Google (prod = your Google Cloud OAuth client → Clerk); set redirect URLs (Clerk shows exact values).

### R2 — Ship code + reports
- [ ] Sync `frontend/` to `/opt/prism-frontend`. `node --version` (v22). Install + build: `npm ci && npm run build` (or pnpm per the lockfile present).
- [ ] Apply backend migration on the box: `cd /opt/prism-platform && .venv/bin/alembic upgrade head` (→ `009`).
- [ ] Sync the 10 report dirs into `REPORTS_HTML_DIR`: `mkdir -p /opt/prism-frontend/report-data && rsync -a --delete --exclude index.html --exclude reports --exclude assets --exclude api --exclude chat-widget.js /opt/prism-hub/ /opt/prism-frontend/report-data/` then **verify per-dir** (rsync silently skips; `ls /opt/prism-frontend/report-data` shows 10 slugs).

### R3 — systemd service (loopback :3000)
- [ ] `/etc/systemd/system/prism-frontend.service`:

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

- [ ] `/opt/prism-frontend/.env.production` (mode 600): Clerk **prod** `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` + `CLERK_SECRET_KEY`; `PRISM_API_URL=http://127.0.0.1:8000`; `HERMES_API_URL` + `HERMES_API_KEY`; `REPORTS_HTML_DIR=/opt/prism-frontend/report-data`. **No `BYPASS_AUTH`.**
- [ ] `sudo systemctl daemon-reload && sudo systemctl enable --now prism-frontend && sudo systemctl status prism-frontend` (active). `ss -ltnp | grep 127.0.0.1:3000`.

### R4 — Caddy cutover (whole domain → Next)
- [ ] Locate the `prism.chowmes.com` Caddyfile: `sudo grep -rl "prism.chowmes.com" $(sudo find / -name Caddyfile 2>/dev/null)`.
- [ ] **Back it up first.** Replace the site's serving with `reverse_proxy 127.0.0.1:3000` for the whole domain (retire the `:8651` static serve). Keep the old block commented for instant rollback.
- [ ] Reload Caddy. **Rollback plan:** if anything breaks, re-point to `:8651` and reload.

### R5 — Live verification (evidence)
- [ ] `curl -sI https://prism.chowmes.com/` → 200 (landing). Logged-out browser: landing is public + interactive.
- [ ] Logged-out: `curl -s -o /dev/null -w "%{http_code}" https://prism.chowmes.com/reports/petsmart/screenshots/01-homepage.png` → **401** (no public report leak).
- [ ] Browser: `/sign-in` → Google → `/reports/` lists 10 → open one → renders + screenshots + grounded chat works.
- [ ] `sudo docker exec prism-platform-postgres-1 psql -U prism -d prism -c "select id,email from users;"` → your row.
- [ ] Confirm the report-source pipeline (prism-hub GitHub auto-deploy) updates `/opt/prism-frontend/report-data` (extend the on-box deploy listener to rsync into report-data, or document the manual step).

---

## Task 9: Deploy record + finish

- [ ] **Step 1:** Create `docs/runbooks/slice1-deploy.md` capturing live URLs, the systemd unit, the Caddy block (+ rollback), and R5 evidence.
- [ ] **Step 2:** Commit.

```bash
git add docs/runbooks/slice1-deploy.md
git commit -m "docs(auth): slice 1 deploy record — unified authed site live at prism.chowmes.com"
```

- [ ] **Step 3:** Invoke `superpowers:finishing-a-development-branch` for `feat/prism-e2e-cycle`.

---

## Self-Review (against the spec)

**Spec coverage:** public landing at `/` → Task 3. Google login → R1 + existing Clerk. Gated reports → Task 4. Report chat survives → Task 5. Identity capture → Tasks 1, 2, 6. Cutover/deploy → Task 8. The three landmines: `/api/chat` collision → Task 5 (`/api/report-chat`); dotted-path bypass → Task 4 handler `auth()`; root-slug namespacing → Task 4 (`/reports/<slug>/`) + Task 5 (widget slug fix). ✅

**Placeholder scan:** No TBD/TODO. Env-dependent choices (npm vs pnpm; the exact Caddyfile path) are explicit locate-then-act steps.

**Type consistency:** `UpsertUserRequest/UpsertUserResponse/upsert_user` consistent across router, tests, and `sync-user.ts` payload (`{id,email,name}` ⊆ request). `REPORTS_HTML_DIR` used identically in the route handler and the list page. The widget posts `{message,slug,sid}` exactly matching `/api/report-chat`'s reads.

**Out of scope (Slice 2):** per-user ACL, `can_user_see()`, identity-driven Hermes binding + runtime probe, per-audit reports, audit-ownership stamping.
