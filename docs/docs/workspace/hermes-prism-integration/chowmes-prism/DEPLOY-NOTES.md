# Chowmes-PRISM — Cass deployment notes (reproducible config)

The identity files in this dir are the **source of truth**; they are deployed to the VPS at
`/root/.hermes-prism/` (= container `/opt/data/`, bind-mounted) and the agent runs in the
`hermes-prism` Docker container (Nous Hermes `hermes_agent` 0.16.0).

## Persona = Cass
- **SOUL.md** is the persona. In this Hermes build, **only SOUL.md is assembled into the system
  prompt** — `AGENTS.md`, `USER.md`, `MEMORY.md` are NOT loaded into the prompt (kept as repo
  reference / future use). So persona lives entirely in SOUL.md.
- Persona = pure traits, **no scripted lines/biography/jokes** (those get parroted and read fake).
  The model invents all specific imagery itself; that's the design. See git history for the
  scripted-examples → traits refactor.

## Model routing (per user directive: complex→gemini, low-end→algolia)
- **Main brain (complex):** `provider: gemini`, `model: gemini-2.5-flash` (direct Gemini API; key
  in VPS `.env` `GEMINI_API_KEY`). Paid/standard tier.
- **Auxiliary low-end tasks** (web_extract, compression, skills_hub): repointed to **Algolia US
  Inference** (OpenAI-compatible) — `base_url: https://inference-us.api.enablers.algolia.net/v1`,
  `model: medium` (gemma-4-31b), provider adapter `openrouter` with base_url override, key inline in
  config.yaml. **Token is a Vault OIDC JWT that EXPIRES ~monthly (was 2026-07-09) — rotate.**
- Vision left on its existing provider (gemma may be text-only).

## Voice-tuning knobs (in VPS `config.yaml` `model:` block — NOT in repo)
- `max_tokens: 512`  — hard cap; stops her writing novels.
- `temperature: 1.05` — flair / striking phrasing (was flat at default).
- Dials: too long → lower max_tokens; want more bite → raise temperature toward 1.1.

## Grounding plugin (plugins/prism-report-qa/__init__.py)
- Neutralized: it enforces **facts-discipline only** (facts come from the bound audit report, no
  fabrication) and **explicitly leaves tone to the SOUL**. The earlier robotic directives ("reply
  exactly: 'That's not in the audit report'", "ask which company") were the main thing flattening
  her voice — removed.

## Operational gotchas (hard-won)
- **SOUL changes don't affect live conversations.** Hermes snapshots the system prompt into
  `sessions.system_prompt` at conversation creation. To apply a persona change: deploy SOUL →
  restart `hermes-prism` → **delete the live sessions** so they rebuild fresh:
  `docker exec hermes-prism python3 -c "import sqlite3;c=sqlite3.connect('/opt/data/state.db');c.execute(\"delete from sessions where source in ('telegram','unknown')\");c.commit()"`
  Telegram `/start` does NOT reset (it's ignored as a platform ping).
- Verify a fresh persona quickly via `docker exec hermes-prism hermes -z "sup"` (one-shot, always
  loads current SOUL) before blaming the prompt.
- Telegram DM session key: `agent:main:telegram:dm:<chat_id>` → stored row id `YYYYMMDD_HHMMSS_hex`.

## Deploy procedure
1. Edit files here → `scp` to `/root/.hermes-prism/` (chown `10000:10000`).
2. `hermes config check` if config.yaml changed.
3. Restart: `docker restart hermes-prism`.
4. Purge stale sessions (command above).
5. Verify: `hermes -z "sup"`.
