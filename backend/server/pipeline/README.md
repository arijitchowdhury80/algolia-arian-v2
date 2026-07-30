# prism_platform.pipeline — isolated pipeline-hardening modules

Built 2026-07-02 on the SAFE AUTONOMOUS TRACK (Arijit away, demo next day). These are **standalone, tested, NOT wired into the live pipeline.** Integration into `run-audit.sh` / `prism-runner.py` / the browser skill is GATED on Arijit (see `docs/plans/2026-07-02-SAFE-AUTONOMOUS-TRACK.md` and the airtight-pipeline plan).

| Module | Purpose (plan ref) | Tests |
|---|---|---|
| `block_detector.py` | Deterministic bot-wall classifier: `PageEvidence → BlockVerdict(OK\|BLOCKED\|SOFT_BLOCK, vendor, signals)` for DataDome/Akamai/Cloudflare/Imperva. Hard signal ⇒ BLOCKED regardless of HTTP status (catches Imperva's 200 block page). (§0.2 / §3.1) | 27 |
| `self_heal.py` | Scripted deterministic self-heal loop: `dispatch → gate → re-dispatch until CLEAN or max_passes → NEEDS_HUMAN`. Dependency-injected (dispatch/gate/clock/observer), fail-closed (gate ERROR ≠ CLEAN), pipeline stops at first NEEDS_HUMAN. `subprocess_gate()` adapter wraps `factcheck_mechanical.py` (exit 0→CLEAN, 2→BLOCKED). `on_attempt` observer = the seam for future `module_executions` DB writes. (§1.3) | 20 |
| `screenshot_gate.py` | Content-based capture gate: `gate_screenshot(png, dom, query, ...) → ShotReport(USABLE\|UNUSABLE\|UNCONFIRMED_EMPTY)`. Detects black/flat/tiny frames (Pillow) + overlay/popup markers + query-in-input + the timing trap (unconfirmed-empty vs waited-confirmed-zero). (§3.1b/§3.1c) | 48 |

Run: `python3 -m pytest tests/pipeline/ -q` → 95 passed.

**Wiring-in notes for the gated integration:**
- `screenshot_gate.py` needs `pillow` added to `pyproject.toml` (present in dev env, not yet a declared dependency).
- `block_detector.py` treats blocking-status (403/405/429) + any single vendor fingerprint as BLOCKED; peer research suggested requiring 2+ signals for DataDome/Akamai to avoid false-positiving a legit 403 with an incidental cookie. Tunable — decide at integration.
- All three are pure/injected and side-effect-free by design so they drop into the runner state machine without new infra.
