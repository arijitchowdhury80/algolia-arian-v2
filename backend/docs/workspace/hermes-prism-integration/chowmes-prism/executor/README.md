# PRISM Executor — Cassandra as the executioner

Backend infra that lets Cassandra (the hermes-prism agent) RUN a full Algolia audit, not just chat a finished one. Deployed on the VPS.

## Pieces
- `prism-runner.py` — host-side loopback service (systemd `prism-runner.service`, root, `127.0.0.1:8770`, bearer-gated). `POST /run {domain}` runs `run-audit.sh` async, then publishes the result into Cass's report store (`/root/.hermes-prism/reports/<slug>/audit-data.json` + `index.json`). Also `GET /status/<job_id>`, `GET /jobs`.
- `../plugins/prism-report-qa/` — Cass's plugin. Beyond the report-grounding hooks it now registers two model-callable tools (toolset `prism_audit`): `run_audit(domain)` and `audit_status(job_id)`. She calls the runner over loopback (container is network_mode:host).

## Deploy notes
- Runner token: `/opt/prism-executor/.runner-token`, also copied to `/root/.hermes-prism/.runner-token` (mode 644 so the container's `hermes` user can read it — a 600 root file gives a silent 401).
- Tool exposure: `prism_audit` must be listed under `platform_toolsets` in `/root/.hermes-prism/config.yaml` (added to `cli` + `telegram`), then restart `hermes-prism`.
- Verified live 2026-07-01: "run an audit on dell.com" via `/v1/responses` -> Cass called `run_audit` -> audit ran end to end -> published (Dell scored 2.7).
