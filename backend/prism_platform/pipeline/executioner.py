"""Track C.1 (Task 4a) — the per-skill executioner: dispatch + gate closures
for `prism_platform.pipeline.self_heal.SelfHealLoop`.

See docs/workspace/phase2-executioner/interface-contract.md (binding shapes,
do not invent a different one) and
docs/workspace/phase2-executioner/task-4a-dispatch-brief.md.

`make_dispatch_fn`'s returned callable reuses the EXISTING per-skill
dispatch mechanism (`run-audit.sh --skill <name>`, confirmed live in Task 1
recon) via the staged runner's own `build_audit_cmd()` — this module does
NOT reimplement argv-building, it forces `job["skill"]` and calls through.

`make_gate_fn`'s returned callable wraps `gate.gate()` (the 5-stage
verification pipeline, already built in Task 3) and maps its richer
`Verdict` down to the `self_heal.GateResult` shape the retry loop
understands (status=CLEAN|BLOCKED, fatal=True iff block_class==UNFIXABLE,
per patch #3 — an UNFIXABLE block must NOT burn the remaining retry budget).
"""

from __future__ import annotations

import importlib.util
import subprocess
import types
from collections.abc import Callable, Sequence
from pathlib import Path

from prism_platform.pipeline import gate as gate_module
from prism_platform.pipeline import self_heal
from prism_platform.pipeline.modules import traffic as traffic_module
from prism_platform.pipeline.verdicts import AdversarialVerdict, FactCheckVerdict, QualityScore

# Skills with a deterministic module executor (docs/workspace/phase2-executioner
# proof of concept, Arijit's call: the claude -p agentic wrapper -- not the
# underlying collect-*.py scripts -- was the actual fabrication vector, since
# it decided what to do on a failed/degraded script result. A module here
# runs the real script and decides success/degraded/needs_human purely in
# code, zero LLM calls. Skills not in this dict still dispatch via the
# existing run-audit.sh --skill claude -p path. Port skills into this
# registry one at a time -- ADDITIVE, not a rewrite.
ModuleFn = Callable[[str, Path], object]
MODULE_REGISTRY: dict[str, ModuleFn] = {
    "algolia-intel-traffic": traffic_module.run_traffic_module,
}

# The 16 skills confirmed in Task 1 recon item 5. Kept as an independent copy
# rather than imported from the staged runner: prism-runner.py is a
# standalone, hyphenated-filename HOST script (no `prism_platform` install is
# guaranteed there — see its own module docstring), loaded here only via
# `_load_staged_runner()` below, and only to reuse `build_audit_cmd`. Keep
# this tuple in sync with prism-runner.py's `SKILL_NAMES` if the skill
# catalog ever changes.
SKILL_NAMES: tuple[str, ...] = (
    "algolia-intel-company",
    "algolia-intel-techstack",
    "algolia-intel-traffic",
    "algolia-intel-competitors",
    "algolia-intel-financial-public",
    "algolia-intel-financial-private",
    "algolia-intel-investor",
    "algolia-intel-social",
    "algolia-intel-news",
    "algolia-intel-hiring",
    "algolia-intel-partner",
    "algolia-intel-industry",
    "algolia-intel-queries",
    "algolia-audit-browser",
    "algolia-audit-report",
    "algolia-audit-factcheck",
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STAGED_RUNNER = _REPO_ROOT / "docs/workspace/cassandra-tooling/staged/prism-runner.py"

BuildCmdFn = Callable[[dict[str, str]], Sequence[str]]
RunCmdFn = Callable[[Sequence[str]], int]

_staged_runner_module: types.ModuleType | None = None  # cached, lazy — see _load_staged_runner


def _load_staged_runner() -> types.ModuleType:
    """Lazily load the staged prism-runner.py module (once per process) via
    the exact `importlib.util` pattern tests/pipeline/test_runner_routes.py
    already uses for the same file — purely to reuse its real
    `build_audit_cmd()`, never to duplicate its argv-building logic. Cached
    so a full 16-skill pipeline run doesn't reimport the file once per
    skill/attempt."""
    global _staged_runner_module
    if _staged_runner_module is None:
        spec = importlib.util.spec_from_file_location(
            "prism_executioner_staged_runner", _STAGED_RUNNER
        )
        if spec is None or spec.loader is None:  # pragma: no cover — defensive
            raise RuntimeError(f"could not load staged runner at {_STAGED_RUNNER}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _staged_runner_module = module
    return _staged_runner_module


def _default_build_cmd_fn(job: dict[str, str]) -> Sequence[str]:
    result: Sequence[str] = _load_staged_runner().build_audit_cmd(job)
    return result


def _default_run_cmd_fn(cmd: Sequence[str]) -> int:
    result = subprocess.run(list(cmd), check=False)
    return result.returncode


def make_dispatch_fn(
    domain: str,
    *,
    build_cmd_fn: BuildCmdFn | None = None,
    run_cmd_fn: RunCmdFn | None = None,
) -> self_heal.DispatchFn:
    """Returns a `self_heal.DispatchFn`: `(skill_name, attempt_number) -> bool`.

    Forces `job["skill"] = skill_name` (never `phase`/`skip` — this is a
    per-skill dispatch, one call per SKILL_NAMES entry) and builds the argv
    via `build_cmd_fn` (default: the real staged prism-runner.py's
    `build_audit_cmd`, lazily loaded; tests inject a fake to avoid touching
    that file or spawning a real subprocess). Returns True iff the
    subprocess exit code is 0 — that means the dispatch RAN TO COMPLETION,
    NOT that its output is good; `make_gate_fn`'s callable decides that.
    `attempt_number` is accepted (per the DispatchFn contract) but does not
    change the command — retries re-run the identical per-skill invocation.
    """
    _build_cmd = build_cmd_fn if build_cmd_fn is not None else _default_build_cmd_fn
    _run_cmd = run_cmd_fn if run_cmd_fn is not None else _default_run_cmd_fn

    def _dispatch(skill_name: str, attempt_number: int) -> bool:
        job = {"domain": domain, "skill": skill_name}
        cmd = _build_cmd(job)
        returncode = _run_cmd(cmd)
        return returncode == 0

    return _dispatch


# ---------------------------------------------------------------------------
# make_gate_fn — stage 2/3/4 NotImplementedError stubs
# ---------------------------------------------------------------------------
# Per the dispatch brief: "you do NOT have a real LLM call to wire in this
# task ... naming a real embedding/LLM call is Task 5's job, not this one."
# These stubs are the DEFAULT for factcheck_fn/adversarial_fn/quality_fn so
# make_gate_fn is fully wired and callable today, but ANY call that actually
# reaches stage 2+ raises loudly instead of silently auto-passing — swapping
# in the real implementation later is exactly a one-line change: pass a real
# callable for the corresponding kwarg below.


def _stub_factcheck_fn(skill_output: gate_module.SkillOutput) -> tuple[FactCheckVerdict, ...]:
    """TODO(Task 5): replace with a real schema-constrained LLM call against
    the algolia-audit-factcheck evidence-tier system (forced tool-use JSON
    into verdicts.FactCheckVerdict, one per claim). Out of scope for Task 4a
    per the dispatch brief."""
    raise NotImplementedError(
        "make_gate_fn's factcheck_fn stub was invoked for skill "
        f"{skill_output.skill_name!r} — wire a real LLM call (Task 5) before "
        "using make_gate_fn in production; see TODO in executioner.py."
    )


def _stub_adversarial_fn(
    skill_output: gate_module.SkillOutput, risky_claims: tuple[str, ...]
) -> tuple[AdversarialVerdict, ...]:
    """TODO(Task 5): replace with the real N=3-voter adversarial panel (each
    voter a schema-constrained LLM call against verdicts.AdversarialVerdict,
    default refuted=true if uncertain). Out of scope for Task 4a per the
    dispatch brief."""
    raise NotImplementedError(
        "make_gate_fn's adversarial_fn stub was invoked for skill "
        f"{skill_output.skill_name!r} ({len(risky_claims)} risky claim(s) "
        "flagged) — wire the real adversarial panel (Task 5) before "
        "production use; see TODO in executioner.py."
    )


def _stub_quality_fn(skill_output: gate_module.SkillOutput) -> QualityScore:
    """TODO(Task 5): replace with a real schema-constrained LLM call against
    algolia-audit-eval's Dimension 3 (instruction adherence), returning a
    verdicts.QualityScore. Out of scope for Task 4a per the dispatch brief."""
    raise NotImplementedError(
        "make_gate_fn's quality_fn stub was invoked for skill "
        f"{skill_output.skill_name!r} — wire the real quality-eval call "
        "(Task 5) before production use; see TODO in executioner.py."
    )


def make_gate_fn(
    domain: str,
    company_name: str,
    audit_dir: Path,
    *,
    mechanical_cmd_fn: Callable[[gate_module.SkillOutput], Sequence[str]] | None = None,
    factcheck_fn: gate_module.FactCheckFn = _stub_factcheck_fn,
    adversarial_fn: gate_module.AdversarialFn = _stub_adversarial_fn,
    quality_fn: gate_module.QualityFn = _stub_quality_fn,
    quality_pass_threshold: float = gate_module.DEFAULT_QUALITY_PASS_THRESHOLD,
    verdict_sink: dict[str, gate_module.Verdict] | None = None,
) -> self_heal.GateFn:
    """Returns a `self_heal.GateFn`: `(skill_name) -> GateResult`.

    Calls `gate.gate()` (the 5-stage verification pipeline) and maps the
    resulting `Verdict` down to `self_heal.GateResult`:
      - `status`: CLEAN iff `Verdict.status == VerdictStatus.PASS`, else BLOCKED.
      - `fatal`: True iff `Verdict.block_class == BlockClass.UNFIXABLE`
        (patch #3 — the self-heal loop escalates to NEEDS_HUMAN immediately
        on a fatal result rather than burning `max_passes` retries on a
        failure that retrying the same skill cannot fix).
      - `findings`/`raw`: passed through from the Verdict.

    `factcheck_fn`/`adversarial_fn`/`quality_fn` default to the
    NotImplementedError stubs above — do NOT silently auto-pass stages 2-4;
    a caller with real LLM wiring (Task 5) passes real callables instead.

    `verdict_sink`, if given, is populated with the full `Verdict` per skill
    (keyed by `skill_name`) after every gate call — `self_heal.GateResult`
    alone doesn't carry the richer stage-by-stage sub-verdicts, but a caller
    that wants to persist the full 5-stage trail (e.g. prism-runner.py's v3
    `on_attempt` observer, via `db_write.write_module_execution_row`) needs
    them. Overwritten on every call for a given skill_name, so it always
    reflects the most recent attempt.
    """

    def _gate(skill_name: str) -> self_heal.GateResult:
        skill_output = gate_module.SkillOutput(
            skill_name=skill_name,
            domain=domain,
            audit_dir=audit_dir,
            company_name=company_name,
        )
        mechanical_cmd = mechanical_cmd_fn(skill_output) if mechanical_cmd_fn is not None else None
        verdict = gate_module.gate(
            skill_output,
            mechanical_cmd=mechanical_cmd,
            factcheck_fn=factcheck_fn,
            adversarial_fn=adversarial_fn,
            quality_fn=quality_fn,
            quality_pass_threshold=quality_pass_threshold,
        )
        if verdict_sink is not None:
            verdict_sink[skill_name] = verdict

        status = (
            self_heal.GateStatus.CLEAN
            if verdict.status == gate_module.VerdictStatus.PASS
            else self_heal.GateStatus.BLOCKED
        )
        return self_heal.GateResult(
            status=status,
            findings=verdict.findings,
            raw=verdict.mechanical_raw,
            fatal=verdict.block_class == gate_module.BlockClass.UNFIXABLE,
        )

    return _gate


def make_routed_dispatch_fn(
    domain: str,
    audit_dir: Path,
    *,
    module_sink: dict[str, object],
    module_registry: dict[str, ModuleFn] = MODULE_REGISTRY,
    build_cmd_fn: BuildCmdFn | None = None,
    run_cmd_fn: RunCmdFn | None = None,
) -> self_heal.DispatchFn:
    """The real per-skill dispatch used by the executioner: for a skill with
    a deterministic module (`module_registry`), run it directly -- no
    claude -p, no LLM call anywhere in this path. For every other skill,
    fall back to the existing `make_dispatch_fn`'s run-audit.sh path. This
    is the actual wiring point: whichever skills get ported into
    `MODULE_REGISTRY` next automatically stop going through claude -p, with
    no change needed to `self_heal.SelfHealLoop` or the calling code.

    `module_sink` is populated with the module's raw result object per
    skill_name (mirrors `make_gate_fn`'s `verdict_sink` pattern) so the
    paired `make_routed_gate_fn` can read it -- module skills decide
    success/degraded/needs_human in ONE call, unlike the dispatch/gate split
    used for claude -p-backed skills.
    """
    _fallback_dispatch = make_dispatch_fn(domain, build_cmd_fn=build_cmd_fn, run_cmd_fn=run_cmd_fn)

    def _dispatch(skill_name: str, attempt_number: int) -> bool:
        module_fn = module_registry.get(skill_name)
        if module_fn is None:
            return _fallback_dispatch(skill_name, attempt_number)
        result = module_fn(domain, audit_dir)
        module_sink[skill_name] = result
        return True  # ran to completion -- make_routed_gate_fn judges the result

    return _dispatch


def make_routed_gate_fn(
    domain: str,
    company_name: str,
    audit_dir: Path,
    *,
    module_sink: dict[str, object],
    module_registry: dict[str, ModuleFn] = MODULE_REGISTRY,
    mechanical_cmd_fn: Callable[[gate_module.SkillOutput], Sequence[str]] | None = None,
    factcheck_fn: gate_module.FactCheckFn = _stub_factcheck_fn,
    adversarial_fn: gate_module.AdversarialFn = _stub_adversarial_fn,
    quality_fn: gate_module.QualityFn = _stub_quality_fn,
    quality_pass_threshold: float = gate_module.DEFAULT_QUALITY_PASS_THRESHOLD,
    verdict_sink: dict[str, gate_module.Verdict] | None = None,
) -> self_heal.GateFn:
    """Paired with `make_routed_dispatch_fn`. For a module-backed skill,
    reads `module_sink` (populated by dispatch) and maps its status to
    `self_heal.GateResult` deterministically -- no LLM judgment here either:
      - "success"     -> CLEAN
      - "degraded"     -> BLOCKED, fatal=False (a retry MIGHT get a better
                          partial result -- unlike "needs_human", this is
                          not known to be permanently unfixable)
      - "needs_human" -> BLOCKED, fatal=True (patch #3 -- e.g. traffic's
                          permanently-dead SimilarWeb key: retrying wastes
                          the retry budget on a failure that cannot change)
    Every other skill falls back to the existing `make_gate_fn`'s real
    5-stage LLM-backed gate (same kwargs, passed straight through)."""
    _fallback_gate = make_gate_fn(
        domain,
        company_name,
        audit_dir,
        mechanical_cmd_fn=mechanical_cmd_fn,
        factcheck_fn=factcheck_fn,
        adversarial_fn=adversarial_fn,
        quality_fn=quality_fn,
        quality_pass_threshold=quality_pass_threshold,
        verdict_sink=verdict_sink,
    )

    def _gate(skill_name: str) -> self_heal.GateResult:
        if skill_name not in module_registry:
            return _fallback_gate(skill_name)

        result = module_sink.get(skill_name)
        if result is None:
            return self_heal.GateResult(
                status=self_heal.GateStatus.ERROR,
                findings=(f"module dispatch for {skill_name!r} produced no result",),
            )

        status = getattr(result, "status", None)
        reason = getattr(result, "reason", "")
        if status == "success":
            return self_heal.GateResult(status=self_heal.GateStatus.CLEAN, raw=reason)
        if status == "degraded":
            return self_heal.GateResult(
                status=self_heal.GateStatus.BLOCKED, fatal=False, findings=(reason,)
            )
        # "needs_human" or any unrecognized status -- fail closed, escalate immediately
        return self_heal.GateResult(
            status=self_heal.GateStatus.BLOCKED, fatal=True, findings=(reason,)
        )

    return _gate
