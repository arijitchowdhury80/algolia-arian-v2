# server — the running backend process

Serves on `127.0.0.1:8000`. Imports `core` and `modules`, mounts their routers, and
listens. This package holds no product logic; anything that reasons about a company
belongs in a module.

| | what |
|---|---|
| `main.py` | the ASGI entrypoint uvicorn runs |
| `api/` | routers, deps, middleware. Platform surface: audits, accounts, ACL, evidence, chat, knowledge |
| `orchestrator/` | Temporal workflows and activities |
| `pipeline/` | audit execution, gates, self-heal, screenshots, embeddings |
| `scripts/` | operational one-offs |
| `static/` | assets the backend serves directly (landing-intake wizard) |

## Rules

- **Thin.** Composition and transport only.
- **Module routers get mounted here, not defined here.** A module owns its own
  `APIRouter`; `server` only wires it up.
