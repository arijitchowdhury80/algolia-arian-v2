# Task 6d brief — fix the 2 real integration gaps Task 6-local found

Read first: `docs/workspace/phase2-executioner/task-6-local-report.md` §"Findings from wiring these pieces together for the first time" (items 1 and 2) — this brief fixes exactly those two, no more, no less.

## Fix 1 — `SkillOutput.audit_dir` semantic mismatch

`gate.py`'s default mechanical-command builder treats `SkillOutput.audit_dir` as the PARENT of the company directory (passes `--audit-dir <audit_dir> --company <company_name>` to `factcheck_mechanical.py`, which then computes `audit_dir/company_name` internally). But `claims.py`'s extractors and `llm_stages.py`'s prompts both read `SkillOutput.audit_dir` as the company directory ITSELF (e.g. `claims.py` does `audit_dir / "research" / "01-company-context.json"` directly, no `company_name` join).

**Fix**: change `gate.py`'s default mechanical command builder to use `factcheck_mechanical.py --audit-data <path>` form instead (glob for the real `*-audit-data.json` file inside `audit_dir`, reusing `claims.py`'s existing `_find_audit_data_json`-style globbing logic — don't duplicate it, extract it to a small shared helper both modules import if that's cleaner). This makes `SkillOutput.audit_dir` consistently mean "the company's own directory" everywhere — matching what `claims.py`/`llm_stages.py` already assume, which is 2 of the 3 consumers, so fix the odd one out rather than the majority.

Confirm `factcheck_mechanical.py --help` (or read its argparse block) to get the exact real flag name/form before assuming `--audit-data` is correct — Task 6-local's report says this form worked live, verify it yourself too, don't just trust the report's prose.

## Fix 2 — 120s timeout too short for real audit workspaces

`prism_platform/pipeline/chat_agent.py`'s `_default_claude_cli` hard-codes `timeout_s=120` (or wherever the literal default lives — check the real code). Real calls against real full audit workspaces took 130-206 seconds and hit `TimeoutExpired` twice in Task 6-local's real testing.

**Fix**: raise the default to something with real headroom (300s, matching what Task 6-local's harness had to pass explicitly to work around this) OR make it a module-level named constant that's easy to tune later — your call on the exact mechanism, but the default must not require every caller to remember to override it (that's what caused this to go unnoticed until Task 6-local's real-workspace test, since Task 5b's own live-proof used a tiny synthetic fixture that stayed under the old default).

## Definition of done

- Both fixes committed.
- Re-run (or write new) unit tests proving: `gate()`'s default path now correctly finds/uses the real audit-data.json form without needing an explicit `mechanical_cmd` override (test against a fixture matching the real shape); `_default_claude_cli`'s new default timeout is the new value (a simple assertion, not a live 200s call in a unit test — don't make the test suite slow).
- Full existing suite still passes (285+ tests) — show output.
- `ruff`/`ruff format`/`mypy --strict` clean.
- If you have time/access, re-run ONE of Task 6-local's real scenarios (e.g. `jbl/algolia-intel-techstack`, which passed cleanly before) using `gate()`'s DEFAULT `mechanical_cmd` (no override) to prove Fix 1 actually closes the gap for real, not just in a unit test with a fake. This is optional but strongly preferred — state clearly if you skip it and why.

## Output

Write your report to `docs/workspace/phase2-executioner/task-6d-report.md`. Return status DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED with the report path and a 3-line summary.
