# PRISM

Prospect intelligence for Algolia sales. Give PRISM a prospect's domain; it produces a sourced
search audit, sales-ready assets, and a grounded way to ask questions about the finished report.

**Live:** https://prism.chowmes.com/

## Repository layout

One repository, two halves. This is the whole system.

```
prism/
├── frontend/     what the customer sees
│   ├── index.html          landing page
│   ├── reports/            published audits (the deliverable)
│   ├── server/             Node web + chat server (Caddy proxies to it on the VPS)
│   ├── api/avatar/         LiveAvatar embed helper, imported by the server
│   ├── assets/             images, logos
│   ├── about/ ae/ bdr/ marketer/   role-facing pages
│   ├── ia/ ia1/ ia2/       information-architecture prototypes
│   └── tests/
├── backend/      what makes it
│   ├── prism_platform/     FastAPI service (VPS 127.0.0.1:8000)
│   ├── alembic/            database migrations
│   ├── scripts/
│   └── tests/
└── docs/         specs, decisions, plans (spans both halves)
```

## Environments

| environment | location | role |
|---|---|---|
| laptop | `~/Dropbox/AI-Development/prism` | development |
| VPS | `/opt/prism` | production |
| GitHub | `arijitchowdhury80/prism` | backup |

All three hold the same structure. `main` is production. `v2` is the next-version branch.

## Running it

Frontend:

```bash
cd frontend
npm install
npm test
PORT=8799 STATIC_DIR="$PWD" node server/chat-proxy.mjs
```

Backend:

```bash
cd backend
uv sync
pytest -q
uvicorn prism_platform.main:app --host 127.0.0.1 --port 8000
```

## Conventions

- `docs/specs/` — designs. `docs/decisions/` — ADRs. `docs/plans/` — execution plans.
- Read `SESSION.md` first in any new session; it records the current state and stop point.
- Backups (`*.bak-*`) are never committed. See `.gitignore`.
