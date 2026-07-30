# core — shared backend library

Everything the modules need but no single module owns. `core` depends on nothing else in
this repo; `modules/` and `server/` both depend on `core`. Dependencies point one way.

| | what |
|---|---|
| `types.py` | `Finding`, `ModuleConfig`, `ExecutionContextV2`, `ClaimRegistryEntry` — the contracts every module speaks |
| `paths.py` | **every filesystem root in the backend.** Nothing else computes `parents[N]` |
| `config.py` | Pydantic settings, env loading |
| `db/` | SQLAlchemy session and models |
| `auth/` | authn, ACL, tenancy queries |
| `registry.py` `executor.py` `playbook.py` | the machinery that runs a module |
| `agent_api.py` `gemini_api.py` `research_client.py` `rate_limiter.py` | LLM and research providers |
| `citation_validator.py` `domain_normalizer.py` `synthesis.py` `pipeline_health.py` | cross-cutting helpers |
| `browser/` `detection/` `integrations/` | Playwright, search-vendor fingerprinting, Scout |
| `clusters/` | deep-research cluster playbooks (A-E) |

## Rules

- **`core` never imports from `modules/` or `server/`.** A `core` module reaching upward is
  a circular dependency waiting to happen.
- **Contracts here are versioned and breaking changes are expensive.** Every module speaks
  these types. Changing `Finding` changes all seven.
- **All roots come from `paths.py`.** See its docstring for why.
