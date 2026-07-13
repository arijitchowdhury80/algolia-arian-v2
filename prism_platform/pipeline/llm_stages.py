"""Task 5b -- real (non-stub) LLM implementations for `gate()`'s stages 2-4.

Task 3 (`gate.py`) and Task 4a (`executioner.py`) both built the *shape* of
stages 2 (factcheck), 3 (adversarial), 4 (quality) as dependency-injected
callables that default to loud `NotImplementedError` stubs -- see
`executioner.py`'s `_stub_factcheck_fn` / `_stub_adversarial_fn` /
`_stub_quality_fn` and their `TODO(Task 5)` markers. This module is that
follow-up (despite the stub comment saying "Task 5" -- the real Task 5 built
the separate report-chat agent in `chat_agent.py`; this is Task 5b).

Each stage is a schema-constrained `claude -p` call (E2: the model is told to
emit ONLY a JSON object that validates against the exact Pydantic model in
`verdicts.py`, never free-form prose parsed after the fact). The actual
subprocess-invocation mechanics (timeout handling, stdout capture) are reused
verbatim from `chat_agent.py`'s `_default_claude_cli` -- this module does not
reinvent that part, per the brief.

Design note (E2 vs. true API tool-use forcing): bare `claude -p` (this
project's locked no-Agent-SDK decision) has no equivalent of the Anthropic
Messages API's `tool_choice`-forced JSON schema. E2 compliance here is
approximated by (a) rendering the Pydantic model's JSON Schema directly into
the prompt with an explicit "respond with ONLY this JSON, no prose"
instruction, and (b) validating the response against that same Pydantic
model afterward, raising loudly (never silently guessing/defaulting a
verdict) if the model's response doesn't parse/validate. This is weaker than
true forced tool-use but is the best available approximation without
reintroducing the Agent SDK or the raw Messages API into a subprocess-CLI
codebase -- flagged explicitly, not silently assumed equivalent.

Two levels of function are exported:

1. **Atomic, per-claim functions** -- matching the brief's literal
   signatures (`factcheck_fn(skill_output, claim) -> FactCheckVerdict`,
   `adversarial_fn(skill_output, claim) -> AdversarialVerdict`,
   `quality_fn(skill_output) -> QualityScore`). These are the real judgment
   calls and are independently unit-tested against a fake `claude -p`.
2. **Batch adapters** -- `gate.py`'s actual injection points
   (`gate.FactCheckFn`, `gate.AdversarialFn`, `gate.QualityFn`) operate on a
   whole skill's claim set, not one claim at a time (`FactCheckFn` covers
   every claim for a skill in one callable; `AdversarialFn` is handed the
   `risky_claims` tuple `gate()` already computed from stage 2's weak-tier
   claims). `make_batch_factcheck_fn` / `make_batch_adversarial_fn` adapt the
   atomic functions above into those exact shapes so they are directly
   pluggable as `make_gate_fn(..., factcheck_fn=..., adversarial_fn=...,
   quality_fn=...)`. `quality_fn` needs no adapter -- its atomic signature
   already matches `gate.QualityFn` exactly (`SkillOutput -> QualityScore`).

Known, explicitly-flagged gap: `gate.FactCheckFn` takes *only* `SkillOutput`
-- there is no established mechanism anywhere in this codebase (recon report,
interface contract, or Task 3/4a's code) for turning "a skill's output
directory" into "the list of discrete claims to fact-check." That extraction
step is out of this task's scope (the brief's three functions are the
judgment calls, not claim extraction) and is NOT invented here with a guessed
heuristic. `make_batch_factcheck_fn` therefore requires an explicit
`claims_fn` argument (no default) -- Task 6's parity-run harness must supply
one (e.g. reusing whatever claim list `algolia-audit-factcheck` itself
already produces) before this stage can run end-to-end. See report Concern.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from pydantic import BaseModel, ValidationError

from prism_platform.pipeline import gate as gate_module
from prism_platform.pipeline.chat_agent import _default_claude_cli
from prism_platform.pipeline.verdicts import (
    AdversarialVerdict,
    AdversarialVoterVerdict,
    FactCheckVerdict,
    QualityScore,
)

ClaudeCliFn = Callable[[str], str]

# claude -p frequently wraps JSON in a markdown code fence even when told not
# to -- tolerate that instead of failing on cosmetic formatting.
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)


# ---------------------------------------------------------------------------
# Shared E2 plumbing: schema-instruction rendering + response parsing.
# ---------------------------------------------------------------------------


def _schema_instruction(model: type[BaseModel]) -> str:
    """Render `model`'s JSON Schema into an explicit forced-JSON instruction
    block -- the E2 approximation described in the module docstring."""
    schema = model.model_json_schema()
    return (
        "Respond with ONLY a single JSON object -- no prose, no markdown "
        "code fences, no explanation before or after it -- that validates "
        "against this JSON Schema:\n"
        f"{json.dumps(schema, indent=2)}"
    )


def _extract_json_object(raw: str) -> str:
    """Pull the JSON object out of a claude -p response, tolerating a
    markdown code fence wrapper."""
    stripped = raw.strip()
    match = _JSON_FENCE_RE.search(stripped)
    if match:
        return match.group(1)
    return stripped


def _parse_schema_response[T: BaseModel](raw: str, model: type[T], *, context: str) -> T:
    """Validate a claude -p response against `model`. Raises `ValueError`
    loudly (never silently defaults/guesses a verdict) if the response is
    not valid, schema-conforming JSON -- a malformed LLM response is a real
    failure that must surface, not something to paper over."""
    payload = _extract_json_object(raw)
    try:
        return model.model_validate_json(payload)
    except (ValidationError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"{context}: claude -p response did not match {model.__name__} "
            f"schema -- raw response: {raw[:500]!r}"
        ) from exc


# ---------------------------------------------------------------------------
# Stage 2 -- factcheck (evidence-tier classification)
# ---------------------------------------------------------------------------

_FACTCHECK_EVIDENCE_TIERS = (
    "AUTHENTIC -- the claim is directly backed by a primary source found in "
    "this audit's own research files (10-K, earnings call transcript, the "
    "prospect's own site, etc).\n"
    "  WEBFETCH -- backed by a live web page fetched during the audit, but "
    "not one of the audit's core primary sources.\n"
    "  WEBSEARCH -- backed only by a web-search snippet/summary, not a "
    "fetched primary document.\n"
    "  NO_SOURCE -- no real evidence found for this claim at all."
)


def build_factcheck_prompt(skill_output: gate_module.SkillOutput, claim: str) -> str:
    """The prompt for the real judgment call behind `algolia-audit-factcheck`'s
    evidence-tier system (per Task 1 recon report §4)."""
    return (
        "You are the fact-checking judge for one claim produced by an "
        f"Algolia search audit skill ({skill_output.skill_name!r}) about "
        f"{skill_output.company_name} ({skill_output.domain}).\n\n"
        "Evidence-tier system (algolia-audit-factcheck):\n"
        f"  {_FACTCHECK_EVIDENCE_TIERS}\n\n"
        f"Audit directory (read files here for evidence): {skill_output.audit_dir}\n\n"
        f'CLAIM TO CHECK: "{claim}"\n\n'
        "Classify this claim's evidence_tier and verdict "
        "(SUPPORTED / UNSUPPORTED / CONTRADICTED). If you can cite a "
        "specific source, put its file path or URL in `citation` (else "
        "null). Explain your reasoning briefly in `reasoning`.\n\n"
        f"{_schema_instruction(FactCheckVerdict)}"
    )


def factcheck_fn(
    skill_output: gate_module.SkillOutput,
    claim: str,
    *,
    claude_cli_fn: ClaudeCliFn = _default_claude_cli,
) -> FactCheckVerdict:
    """The real stage-2 judgment call for one claim. Schema-constrained
    against `verdicts.FactCheckVerdict`."""
    prompt = build_factcheck_prompt(skill_output, claim)
    raw = claude_cli_fn(prompt)
    return _parse_schema_response(
        raw,
        FactCheckVerdict,
        context=f"factcheck_fn(skill={skill_output.skill_name!r}, claim={claim!r})",
    )


def make_batch_factcheck_fn(
    claims_fn: Callable[[gate_module.SkillOutput], tuple[str, ...]],
    *,
    claude_cli_fn: ClaudeCliFn = _default_claude_cli,
) -> gate_module.FactCheckFn:
    """Adapter matching `gate.FactCheckFn`'s actual shape
    (`SkillOutput -> tuple[FactCheckVerdict, ...]`) -- `gate()` calls this
    once per skill output, covering every claim in one callable, not once
    per claim. `claims_fn` has NO default: there is no established
    claim-extraction mechanism anywhere in this codebase yet (see module
    docstring) -- the caller (Task 6's parity harness) must supply one
    rather than this module guessing a heuristic."""

    def _batch(skill_output: gate_module.SkillOutput) -> tuple[FactCheckVerdict, ...]:
        claims = claims_fn(skill_output)
        return tuple(
            factcheck_fn(skill_output, claim, claude_cli_fn=claude_cli_fn) for claim in claims
        )

    return _batch


# ---------------------------------------------------------------------------
# Stage 3 -- adversarial panel (N=3 voters)
# ---------------------------------------------------------------------------


def build_adversarial_voter_prompt(
    skill_output: gate_module.SkillOutput, claim: str, voter_id: int, n_voters: int
) -> str:
    return (
        f"You are adversarial voter #{voter_id} of {n_voters} on a "
        "fact-check refutation panel for one claim produced by "
        f"{skill_output.skill_name!r} about {skill_output.company_name} "
        f"({skill_output.domain}).\n\n"
        "Your job is to try to REFUTE the claim below, using the audit "
        f"directory ({skill_output.audit_dir}) or your own knowledge as "
        "evidence. If you cannot find clear evidence either way, default "
        "to refuted=true -- uncertainty counts AGAINST the claim, not in "
        "its favor.\n\n"
        f'CLAIM: "{claim}"\n\n'
        f"{_schema_instruction(AdversarialVoterVerdict)}"
    )


def adversarial_voter_fn(
    skill_output: gate_module.SkillOutput,
    claim: str,
    voter_id: int,
    *,
    n_voters: int = 3,
    claude_cli_fn: ClaudeCliFn = _default_claude_cli,
) -> AdversarialVoterVerdict:
    """One voter's ballot. Schema-constrained against
    `verdicts.AdversarialVoterVerdict`."""
    prompt = build_adversarial_voter_prompt(skill_output, claim, voter_id, n_voters)
    raw = claude_cli_fn(prompt)
    verdict = _parse_schema_response(
        raw,
        AdversarialVoterVerdict,
        context=(
            f"adversarial_voter_fn(skill={skill_output.skill_name!r}, "
            f"claim={claim!r}, voter_id={voter_id})"
        ),
    )
    if verdict.voter_id != voter_id:
        # The model is asked to echo voter_id in the schema; trust our own
        # loop variable over whatever the model returned rather than
        # silently accepting a mismatched id.
        verdict = verdict.model_copy(update={"voter_id": voter_id})
    return verdict


def adversarial_fn(
    skill_output: gate_module.SkillOutput,
    claim: str,
    *,
    n_voters: int = 3,
    claude_cli_fn: ClaudeCliFn = _default_claude_cli,
) -> AdversarialVerdict:
    """The real stage-3 judgment call for one claim: N=3 independent voter
    calls, aggregated into `AdversarialVerdict.survives` (majority NOT
    refuted). Patch #1: `gate()` only invokes this for claims already
    flagged risky -- this function just IS the callable, it does not decide
    when it fires."""
    votes = tuple(
        adversarial_voter_fn(
            skill_output, claim, voter_id, n_voters=n_voters, claude_cli_fn=claude_cli_fn
        )
        for voter_id in range(1, n_voters + 1)
    )
    refuted_count = sum(1 for vote in votes if vote.refuted)
    survives = refuted_count * 2 < len(votes)  # strict majority NOT refuted
    return AdversarialVerdict(claim=claim, votes=list(votes), survives=survives)


def make_batch_adversarial_fn(
    *,
    n_voters: int = 3,
    claude_cli_fn: ClaudeCliFn = _default_claude_cli,
) -> gate_module.AdversarialFn:
    """Adapter matching `gate.AdversarialFn`'s actual shape
    (`(SkillOutput, tuple[str, ...]) -> tuple[AdversarialVerdict, ...]`).
    Unlike factcheck, `gate()` already computes and hands over the risky
    claims tuple itself (patch #1) -- no claims_fn gap here."""

    def _batch(
        skill_output: gate_module.SkillOutput, risky_claims: tuple[str, ...]
    ) -> tuple[AdversarialVerdict, ...]:
        return tuple(
            adversarial_fn(skill_output, claim, n_voters=n_voters, claude_cli_fn=claude_cli_fn)
            for claim in risky_claims
        )

    return _batch


# ---------------------------------------------------------------------------
# Stage 4 -- quality (Dimension 3: instruction adherence)
# ---------------------------------------------------------------------------


def build_quality_prompt(skill_output: gate_module.SkillOutput) -> str:
    """The real Dimension 3 (instruction adherence) judgment from
    `algolia-audit-eval` (per Task 1 recon report §4 -- Dimensions 1/2/4/5
    already delegate to factcheck_mechanical.py; only Dimension 3 needs an
    LLM call)."""
    return (
        "You are scoring Dimension 3 (instruction adherence) of the "
        f"algolia-audit-eval rubric for skill {skill_output.skill_name!r}'s "
        f"output about {skill_output.company_name} ({skill_output.domain}).\n\n"
        f"Audit directory: {skill_output.audit_dir}\n\n"
        "Read this skill's own SKILL.md instructions and the actual output "
        "files it produced in the audit directory. Score how well the "
        "output followed its own skill's explicit instructions (required "
        "sections present, required output format followed, no skipped "
        "steps) on a 0-10 scale. Report `passing_checks`/`total_checks` "
        "against whatever discrete, checkable instructions you identify in "
        "the skill's own SKILL.md, and explain your reasoning.\n\n"
        f"{_schema_instruction(QualityScore)}"
    )


def quality_fn(
    skill_output: gate_module.SkillOutput,
    *,
    claude_cli_fn: ClaudeCliFn = _default_claude_cli,
) -> QualityScore:
    """The real stage-4 judgment call. Signature already matches
    `gate.QualityFn` exactly (`SkillOutput -> QualityScore`) -- no batch
    adapter needed, this is directly pluggable as
    `make_gate_fn(..., quality_fn=quality_fn)`."""
    prompt = build_quality_prompt(skill_output)
    raw = claude_cli_fn(prompt)
    return _parse_schema_response(
        raw, QualityScore, context=f"quality_fn(skill={skill_output.skill_name!r})"
    )
