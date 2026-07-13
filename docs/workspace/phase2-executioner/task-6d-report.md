# Task 6d report — fixing the 2 real integration gaps Task 6-local found

Status: **DONE**

3-line summary: Fixed both real gaps `task-6-local-report.md` flagged (not silently patched
mid-proof, per that report's own note): `gate.py`'s default mechanical command now builds the real
`factcheck_mechanical.py --audit-data <path>` form via a new shared `find_audit_data_json()` helper
(also adopted by `claims.py`, removing its duplicate glob logic), and `chat_agent.py`'s
`_default_claude_cli` default timeout is now a named `DEFAULT_CLAUDE_CLI_TIMEOUT_S = 300` constant
instead of a bare `120`. Full suite (814 tests, `tests/pipeline/` 294) passes; `ruff format` and
`mypy --strict` are clean on all 3 touched production modules; live-reran Fix 1 against the real
`jbl` audit workspace using `gate()`'s DEFAULT `mechanical_cmd` (no override) — mechanical stage
came back CLEAN for real.

Report path: `docs/workspace/phase2-executioner/task-6d-report.md`

---

## Fix 1 — `SkillOutput.audit_dir` semantic mismatch

**Confirmed the real flag form first** (per the brief's instruction not to trust the prior
report's prose): read `~/.claude/skills/algolia-audit-factcheck/scripts/factcheck_mechanical.py`'s
argparse block directly (`--audit-data`, line 683) and its module docstring (lines 38-44), which
documents `--audit-data /path/to/{company}-audit-data.json` as "the primary form the gate should
use" and `--audit-dir/--company` as "legacy / pipeline form."

**What changed** (`prism_platform/pipeline/gate.py`):
- Added `find_audit_data_json(audit_dir: Path) -> Path | None` — globs
  `audit_dir/deliverables/*-audit-data.json`, the exact logic `claims.py`'s `_find_audit_data_json`
  already had (real slug drift confirmed: "British Airways" → `british-airways-audit-data.json`,
  "Michael Kors" → `michaelkors-audit-data.json`, no hyphen — never a guessed slug).
- `_default_mechanical_cmd` now calls this helper and builds
  `[sys.executable, FACTCHECK_MECHANICAL_PATH, "--audit-data", str(audit_data_path)]` — no
  `--audit-dir`/`--company` split, so `SkillOutput.audit_dir` now consistently means "the
  company's own directory" for all 3 consumers (`gate.py`, `claims.py`, `llm_stages.py`), fixing
  the odd one out per the brief's instruction.
- If no `deliverables/*-audit-data.json` exists yet under `audit_dir`, `_default_mechanical_cmd`
  raises `FileNotFoundError` with a clear message, rather than building a command against a
  guessed/wrong path. This is a deliberate behavior change from the old default (which built an
  always-syntactically-valid command regardless of whether the target existed, letting
  `subprocess_gate`'s `OSError` handling fail closed at runtime) — callers whose skill legitimately
  runs before the audit-report deliverable exists must pass an explicit `mechanical_cmd`.

**What changed** (`prism_platform/pipeline/claims.py`):
- Removed the duplicate `_find_audit_data_json` glob logic; it's now
  `_find_audit_data_json = gate_module.find_audit_data_json` (claims.py already imports
  `gate_module`, no new import, no circular-import risk since `gate.py` does not import
  `claims.py`). One implementation, not two that could drift.

## Fix 2 — 120s default timeout too short for real audit workspaces

**What changed** (`prism_platform/pipeline/chat_agent.py`):
- Added `DEFAULT_CLAUDE_CLI_TIMEOUT_S = 300` as a module-level named constant, with a docstring
  explaining why (Task 5b's live-proof measured 37.4s against a tiny synthetic fixture; Task
  6-local's real full-audit calls took 130-206s and hit `TimeoutExpired` twice against the old
  120s default).
- `_default_claude_cli`'s `timeout_s` parameter now defaults to this constant instead of a bare
  `120` — no caller has to remember to override it, closing the exact gap the brief named ("that's
  what caused this to go unnoticed").

---

## Tests written (TDD: wrote/ran these against the fix, not after)

`tests/pipeline/test_gate.py`:
- `TestFindAuditDataJson` (3 tests) — the shared helper finds the real slug file, returns `None`
  with no `deliverables/` dir, returns `None` with an empty/unrelated `deliverables/` dir.
- `TestDefaultMechanicalCmdUsesAuditDataForm` (2 tests) — **the core DoD proof**:
  `test_default_mechanical_cmd_passes_real_audit_data_path` calls `gate()` with **no
  `mechanical_cmd` override** against a fixture matching the real shape (a `tmp_path` company dir
  with `deliverables/belk-audit-data.json`), monkeypatches `FACTCHECK_MECHANICAL_PATH` to a
  throwaway script that records its own `argv` and exits 0 only if invoked with `--audit-data` and
  NOT `--audit-dir`/`--company` (so a regression back to the old form fails loudly, not silently),
  and asserts the recorded `argv` is exactly the real audit-data path. The second test proves the
  `FileNotFoundError` when no audit-data.json exists.

`tests/pipeline/test_chat_agent.py`:
- `TestDefaultClaudeCliTimeout` (3 tests) — the constant equals 300; `_default_claude_cli`'s real
  parameter default equals the constant (via `inspect.signature`); `_default_claude_cli` actually
  passes `timeout_s` through to `subprocess.run`'s `timeout` kwarg (via a monkeypatched fake
  `subprocess.run`, not a real 200s+ `claude -p` call — keeps the suite fast per the brief).

`tests/pipeline/test_executioner.py` (regression fix, not in the original brief scope but
necessary): `test_make_gate_fn_default_mechanical_uses_gate_default_when_no_override` relied on
the OLD default-cmd behavior (a command built unconditionally against a real-but-nonexistent path,
failing at the `subprocess.run` `OSError` level). Fix 1 changed this: the new
`_default_mechanical_cmd` now raises `FileNotFoundError` *before* even building a subprocess
command when no fixture exists. Updated the test to give it a real fixture + a fake
`factcheck_mechanical.py` stand-in that deliberately exits 2 (BLOCKED), preserving its original
assertion (`GateStatus.BLOCKED`, `fatal=False`) while now genuinely exercising the real default-cmd
path end-to-end. Added a companion test asserting the new `FileNotFoundError` behavior directly.

## Verification — real command output

```
$ .venv/bin/python3.13 -m pytest -q
...
814 passed, 19 skipped, 4 deselected, 30 warnings in ~65s
```

(4 deselected/pre-existing-failing tests are `tests/v2/test_search_vendor_detector_integration.py`
— confirmed via `git stash` against the pre-fix baseline that these fail identically without any
change of mine: `playwright._impl._errors.Error: ... Executable doesn't exist ... chrome-headless-
shell` — a missing local Playwright browser binary, unrelated to this brief's scope. Not touched,
not caused by this task.)

```
$ .venv/bin/python3.13 -m pytest tests/pipeline/ -q
294 passed, 18 skipped, 24 warnings in ~15s
```

```
$ .venv/bin/python3.13 -m ruff check prism_platform/pipeline/gate.py prism_platform/pipeline/claims.py \
    prism_platform/pipeline/chat_agent.py tests/pipeline/test_gate.py tests/pipeline/test_chat_agent.py \
    tests/pipeline/test_executioner.py
UP042 Class VerdictStatus inherits from both `str` and `enum.Enum`   (gate.py:60, PRE-EXISTING)
UP042 Class BlockClass inherits from both `str` and `enum.Enum`      (gate.py:65, PRE-EXISTING)
Found 2 errors.
```
Confirmed via `git stash` + re-run against the pre-fix baseline: identical 2 errors, same lines,
present before this task touched the file. Not introduced by this fix, not on lines I changed.

```
$ .venv/bin/python3.13 -m ruff format --check <same 6 files>
6 files already formatted

$ .venv/bin/python3.13 -m mypy --strict prism_platform/pipeline/gate.py prism_platform/pipeline/claims.py \
    prism_platform/pipeline/chat_agent.py
Success: no issues found in 3 source files
```

(`mypy --strict` on the 3 test files was NOT run to a clean bar — `tests/pipeline/test_executioner.py`
alone has ~25 pre-existing `no-untyped-def` errors on functions I did not touch, confirmed identical
on the pre-fix baseline via `git stash`. The project's own test suite convention across this repo
does not carry per-function type annotations; holding only the 3 touched production modules to
`--strict` matches the prior task reports' own stated scope ("mypy --strict clean on all 3 touched
modules") and this task's DoD line, which names `ruff`/`ruff format`/`mypy --strict` without
specifying test-file strictness.)

## Optional live re-verification — DONE, not skipped

Ran fresh against the real `jbl` audit workspace (`~/prism-data/audits/jbl/`), using `gate()`'s
**DEFAULT** `mechanical_cmd` (no override at all):

```python
skill_output = SkillOutput(
    skill_name="algolia-intel-techstack",
    domain="jbl.com",
    audit_dir=Path("/Users/arijitchowdhury/prism-data/audits/jbl"),
    company_name="JBL",
)
gate(skill_output)  # no mechanical_cmd override
```

Result: raised `NotImplementedError: gate() stage 2 (factcheck) requires factcheck_fn ...` — i.e.
stage 1 (mechanical) came back **CLEAN** for real, using the real default command against the real
`~/prism-data/audits/jbl/deliverables/jbl-audit-data.json` file on disk, invoking the real
`~/.claude/skills/algolia-audit-factcheck/scripts/factcheck_mechanical.py` script as a real
subprocess. Confirmed by running the exact equivalent command directly and inspecting its real
JSON output: `completeness` 6/6 passing, `source_density` 127 URLs (pass), `no_fabrication` 0
placeholder hits, 0 unsourced impact stats — a real clean structural + corpus pass, not a stub.
This closes Fix 1's gap for real, not just against a unit-test fixture with a fake script.

## Files changed

- `prism_platform/pipeline/gate.py` — `find_audit_data_json()` (new, shared), `_default_mechanical_cmd`
  rewritten to the `--audit-data` form, raises `FileNotFoundError` on no match.
- `prism_platform/pipeline/claims.py` — `_find_audit_data_json` now aliases `gate_module.find_audit_data_json`
  instead of duplicating the glob logic.
- `prism_platform/pipeline/chat_agent.py` — `DEFAULT_CLAUDE_CLI_TIMEOUT_S = 300` (new, named), 
  `_default_claude_cli`'s `timeout_s` default now references it.
- `tests/pipeline/test_gate.py` — `TestFindAuditDataJson`, `TestDefaultMechanicalCmdUsesAuditDataForm`.
- `tests/pipeline/test_chat_agent.py` — `TestDefaultClaudeCliTimeout`.
- `tests/pipeline/test_executioner.py` — regression fix for the one pre-existing test that exercised
  the now-changed default-mechanical-cmd behavior, plus one new companion test.

## Commit

Two commits on `feat/prism-e2e-cycle` (current branch, not `main`):
1. `fix(pipeline): Task 6d — close SkillOutput.audit_dir mismatch + raise LLM timeout to 300s`
   (`gate.py`, `claims.py`, `chat_agent.py`, `test_gate.py`, `test_chat_agent.py`).
2. `test(pipeline): Task 6d — fix test_executioner regression from gate.py's audit-data default`
   (`test_executioner.py`) — kept as a separate commit per the git protocol (new commit, not an
   amend) since it addresses a downstream test regression discovered during verification, distinct
   from the fix commit itself.

## Status: DONE

Both fixes from the brief are implemented, tested (new unit tests against fixtures matching the
real shape, no live 200s+ calls in the test suite), and live-reverified against a real audit
workspace for Fix 1. Full suite passes (814/818, 4 pre-existing/unrelated failures confirmed
identical on the pre-fix baseline). `ruff format` and `mypy --strict` are clean on all 3 touched
production modules; the 2 pre-existing `ruff check` findings on `gate.py` are confirmed unrelated
(different lines, present before this task). One downstream test regression
(`test_executioner.py`) was found and fixed as part of closing this loop, committed separately.
