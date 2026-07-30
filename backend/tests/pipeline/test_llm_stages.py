"""Tests for Task 5b's real (non-stub) LLM implementations of gate()'s
stages 2-4 -- prompt construction + response parsing, against a fake
`claude -p` (no live subprocess, no API key, no network).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.pipeline import gate as gate_module
from server.pipeline.gate import SkillOutput
from server.pipeline.llm_stages import (
    adversarial_fn,
    adversarial_voter_fn,
    build_adversarial_voter_prompt,
    build_factcheck_prompt,
    build_quality_prompt,
    factcheck_fn,
    make_batch_adversarial_fn,
    make_batch_factcheck_fn,
    quality_fn,
)
from server.pipeline.verdicts import (
    AdversarialVerdict,
    AdversarialVoterVerdict,
    FactCheckVerdict,
    QualityScore,
)


def _skill_output(skill_name: str = "algolia-intel-financial-public") -> SkillOutput:
    return SkillOutput(
        skill_name=skill_name,
        domain="belk.com",
        audit_dir=Path("/tmp/does-not-need-to-exist/Belk"),
        company_name="Belk",
    )


def _fake_cli(response: str) -> object:
    calls: list[str] = []

    def _cli(prompt: str) -> str:
        calls.append(prompt)
        return response

    _cli.calls = calls  # type: ignore[attr-defined]
    return _cli


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def test_build_factcheck_prompt_includes_claim_audit_dir_and_schema() -> None:
    so = _skill_output()
    prompt = build_factcheck_prompt(so, "Belk operates 291 stores.")
    assert "Belk operates 291 stores." in prompt
    assert str(so.audit_dir) in prompt
    assert "AUTHENTIC" in prompt and "NO_SOURCE" in prompt
    assert "evidence_tier" in prompt  # schema field name rendered into prompt
    assert "JSON" in prompt


def test_build_factcheck_prompt_names_the_skill_and_company() -> None:
    prompt = build_factcheck_prompt(_skill_output(), "some claim")
    assert "algolia-intel-financial-public" in prompt
    assert "Belk" in prompt
    assert "belk.com" in prompt


def test_build_adversarial_voter_prompt_instructs_default_refuted_on_uncertainty() -> None:
    prompt = build_adversarial_voter_prompt(_skill_output(), "some claim", voter_id=2, n_voters=3)
    assert "voter #2 of 3" in prompt
    assert "refuted=true" in prompt
    assert "some claim" in prompt


def test_build_quality_prompt_names_skill_and_instruction_adherence() -> None:
    prompt = build_quality_prompt(_skill_output())
    assert "instruction adherence" in prompt.lower()
    assert "algolia-intel-financial-public" in prompt
    assert "passing_checks" in prompt


# ---------------------------------------------------------------------------
# factcheck_fn -- response parsing
# ---------------------------------------------------------------------------


def test_factcheck_fn_parses_valid_json_response() -> None:
    response = (
        '{"claim": "Belk operates 291 stores.", "evidence_tier": "AUTHENTIC", '
        '"verdict": "SUPPORTED", "citation": "https://belk.com/about", '
        '"reasoning": "Matches the About page."}'
    )
    cli = _fake_cli(response)
    result = factcheck_fn(_skill_output(), "Belk operates 291 stores.", claude_cli_fn=cli)
    assert isinstance(result, FactCheckVerdict)
    assert result.verdict == "SUPPORTED"
    assert result.evidence_tier == "AUTHENTIC"
    assert result.citation == "https://belk.com/about"
    assert len(cli.calls) == 1  # type: ignore[attr-defined]


def test_factcheck_fn_tolerates_markdown_fenced_json() -> None:
    response = (
        "```json\n"
        '{"claim": "x", "evidence_tier": "WEBSEARCH", "verdict": "UNSUPPORTED", '
        '"citation": null, "reasoning": "no strong source"}\n'
        "```"
    )
    result = factcheck_fn(_skill_output(), "x", claude_cli_fn=_fake_cli(response))
    assert result.verdict == "UNSUPPORTED"
    assert result.citation is None


def test_factcheck_fn_raises_on_malformed_json_rather_than_guessing() -> None:
    with pytest.raises(ValueError, match="did not match FactCheckVerdict schema"):
        factcheck_fn(_skill_output(), "x", claude_cli_fn=_fake_cli("not json at all"))


def test_factcheck_fn_raises_on_json_missing_required_field() -> None:
    # Missing "verdict" -- must fail loudly, not default to SUPPORTED.
    response = '{"claim": "x", "evidence_tier": "AUTHENTIC", "citation": null, "reasoning": "r"}'
    with pytest.raises(ValueError, match="FactCheckVerdict"):
        factcheck_fn(_skill_output(), "x", claude_cli_fn=_fake_cli(response))


def test_factcheck_fn_raises_on_invalid_literal_value() -> None:
    # evidence_tier must be one of the 4 literals -- "MAYBE" is not valid.
    response = (
        '{"claim": "x", "evidence_tier": "MAYBE", "verdict": "SUPPORTED", '
        '"citation": null, "reasoning": "r"}'
    )
    with pytest.raises(ValueError):
        factcheck_fn(_skill_output(), "x", claude_cli_fn=_fake_cli(response))


# ---------------------------------------------------------------------------
# adversarial_voter_fn / adversarial_fn
# ---------------------------------------------------------------------------


def test_adversarial_voter_fn_parses_valid_response() -> None:
    response = '{"voter_id": 1, "refuted": false, "reasoning": "solid evidence"}'
    result = adversarial_voter_fn(
        _skill_output(), "some claim", voter_id=1, claude_cli_fn=_fake_cli(response)
    )
    assert isinstance(result, AdversarialVoterVerdict)
    assert result.refuted is False


def test_adversarial_voter_fn_forces_loop_voter_id_over_model_echo() -> None:
    # Model echoes the wrong voter_id -- our own loop index must win, not
    # the model's (possibly wrong) echo.
    response = '{"voter_id": 99, "refuted": true, "reasoning": "r"}'
    result = adversarial_voter_fn(
        _skill_output(), "some claim", voter_id=2, claude_cli_fn=_fake_cli(response)
    )
    assert result.voter_id == 2


def test_adversarial_fn_survives_when_majority_not_refuted() -> None:
    responses = [
        '{"voter_id": 1, "refuted": false, "reasoning": "r1"}',
        '{"voter_id": 2, "refuted": false, "reasoning": "r2"}',
        '{"voter_id": 3, "refuted": true, "reasoning": "r3"}',
    ]
    calls: list[str] = []

    def cli(prompt: str) -> str:
        calls.append(prompt)
        return responses[len(calls) - 1]

    result = adversarial_fn(_skill_output(), "claim under test", claude_cli_fn=cli)
    assert isinstance(result, AdversarialVerdict)
    assert result.survives is True
    assert len(result.votes) == 3
    assert len(calls) == 3


def test_adversarial_fn_blocked_when_majority_refuted() -> None:
    responses = [
        '{"voter_id": 1, "refuted": true, "reasoning": "r1"}',
        '{"voter_id": 2, "refuted": true, "reasoning": "r2"}',
        '{"voter_id": 3, "refuted": false, "reasoning": "r3"}',
    ]
    calls: list[str] = []

    def cli(prompt: str) -> str:
        calls.append(prompt)
        return responses[len(calls) - 1]

    result = adversarial_fn(_skill_output(), "claim under test", claude_cli_fn=cli)
    assert result.survives is False


def test_adversarial_fn_tie_counts_as_refuted_majority_not_reached() -> None:
    # n_voters=2, one refuted one not -- 1*2=2 !< 2, so NOT strict majority
    # not-refuted -> survives=False (ties do not save the claim).
    responses = [
        '{"voter_id": 1, "refuted": true, "reasoning": "r1"}',
        '{"voter_id": 2, "refuted": false, "reasoning": "r2"}',
    ]
    calls: list[str] = []

    def cli(prompt: str) -> str:
        calls.append(prompt)
        return responses[len(calls) - 1]

    result = adversarial_fn(_skill_output(), "claim", n_voters=2, claude_cli_fn=cli)
    assert result.survives is False


def test_adversarial_fn_calls_exactly_n_voters() -> None:
    response = '{"voter_id": 1, "refuted": false, "reasoning": "r"}'
    calls: list[str] = []

    def cli(prompt: str) -> str:
        calls.append(prompt)
        return response

    adversarial_fn(_skill_output(), "claim", n_voters=5, claude_cli_fn=cli)
    assert len(calls) == 5


# ---------------------------------------------------------------------------
# quality_fn
# ---------------------------------------------------------------------------


def test_quality_fn_parses_valid_response() -> None:
    response = (
        '{"dimension": "instruction_adherence", "score": 8.5, '
        '"passing_checks": 9, "total_checks": 10, "reasoning": "mostly complete"}'
    )
    result = quality_fn(_skill_output(), claude_cli_fn=_fake_cli(response))
    assert isinstance(result, QualityScore)
    assert result.score == 8.5
    assert result.passing_checks == 9


def test_quality_fn_raises_on_score_out_of_declared_dimension() -> None:
    response = (
        '{"dimension": "coverage", "score": 8.5, '
        '"passing_checks": 9, "total_checks": 10, "reasoning": "r"}'
    )
    with pytest.raises(ValueError):
        quality_fn(_skill_output(), claude_cli_fn=_fake_cli(response))


def test_quality_fn_pluggable_as_gate_quality_fn_with_single_positional_arg() -> None:
    # quality_fn's real (non-fake) signature must be callable with exactly
    # one positional arg -- matching gate.QualityFn = Callable[[SkillOutput],
    # QualityScore] exactly -- so a caller can bind claude_cli_fn via
    # functools.partial/closure and pass the result straight to
    # make_gate_fn(quality_fn=...) with no further adapter.
    import functools

    response = (
        '{"dimension": "instruction_adherence", "score": 9.0, '
        '"passing_checks": 10, "total_checks": 10, "reasoning": "r"}'
    )
    bound: gate_module.QualityFn = functools.partial(quality_fn, claude_cli_fn=_fake_cli(response))
    result = bound(_skill_output())
    assert result.score == 9.0


# ---------------------------------------------------------------------------
# Batch adapters -- pluggable into gate.py's actual injection types
# ---------------------------------------------------------------------------


def test_make_batch_factcheck_fn_calls_claims_fn_then_factcheck_fn_per_claim() -> None:
    so = _skill_output()
    seen_claims: list[str] = []

    def claims_fn(skill_output: SkillOutput) -> tuple[str, ...]:
        assert skill_output is so
        return ("claim one", "claim two")

    def cli(prompt: str) -> str:
        # Extract which claim this prompt is about so we can echo a distinct
        # verdict per claim and prove all claims were actually processed.
        claim = "claim one" if "claim one" in prompt else "claim two"
        seen_claims.append(claim)
        return (
            f'{{"claim": "{claim}", "evidence_tier": "AUTHENTIC", '
            '"verdict": "SUPPORTED", "citation": null, "reasoning": "r"}'
        )

    batch_fn = make_batch_factcheck_fn(claims_fn, claude_cli_fn=cli)
    result = batch_fn(so)
    assert len(result) == 2
    assert seen_claims == ["claim one", "claim two"]
    assert {fc.claim for fc in result} == {"claim one", "claim two"}


def test_make_batch_factcheck_fn_empty_claims_makes_zero_cli_calls() -> None:
    calls: list[str] = []

    def claims_fn(skill_output: SkillOutput) -> tuple[str, ...]:
        return ()

    def cli(prompt: str) -> str:
        calls.append(prompt)
        return "unused"

    batch_fn = make_batch_factcheck_fn(claims_fn, claude_cli_fn=cli)
    result = batch_fn(_skill_output())
    assert result == ()
    assert calls == []


def test_make_batch_adversarial_fn_calls_adversarial_fn_per_risky_claim() -> None:
    response = '{"voter_id": 1, "refuted": false, "reasoning": "r"}'
    calls: list[str] = []

    def cli(prompt: str) -> str:
        calls.append(prompt)
        return response

    batch_fn = make_batch_adversarial_fn(claude_cli_fn=cli)
    result = batch_fn(_skill_output(), ("risky claim A", "risky claim B"))
    assert len(result) == 2
    assert {av.claim for av in result} == {"risky claim A", "risky claim B"}
    # n_voters=3 default * 2 claims = 6 calls.
    assert len(calls) == 6


def test_make_batch_adversarial_fn_empty_risky_claims_makes_zero_cli_calls() -> None:
    calls: list[str] = []

    def cli(prompt: str) -> str:
        calls.append(prompt)
        return "unused"

    batch_fn = make_batch_adversarial_fn(claude_cli_fn=cli)
    result = batch_fn(_skill_output(), ())
    assert result == ()
    assert calls == []


# ---------------------------------------------------------------------------
# End-to-end wiring proof: these real functions plug into gate() itself,
# not just into isolated unit tests, using fakes for every LLM call point.
# ---------------------------------------------------------------------------


def test_real_functions_wire_into_gate_end_to_end_with_fake_cli() -> None:
    import sys

    from server.pipeline.gate import gate

    so = _skill_output()

    def clean_mechanical_cmd() -> list[str]:
        return [sys.executable, "-c", "import sys; sys.exit(0)"]

    def claims_fn(skill_output: SkillOutput) -> tuple[str, ...]:
        return ("Belk operates 291 stores.",)

    factcheck_response = (
        '{"claim": "Belk operates 291 stores.", "evidence_tier": "AUTHENTIC", '
        '"verdict": "SUPPORTED", "citation": "https://belk.com/about", '
        '"reasoning": "matches source"}'
    )
    quality_response = (
        '{"dimension": "instruction_adherence", "score": 9.0, '
        '"passing_checks": 10, "total_checks": 10, "reasoning": "complete"}'
    )

    def cli(prompt: str) -> str:
        if "instruction adherence" in prompt.lower():
            return quality_response
        return factcheck_response

    verdict = gate(
        so,
        mechanical_cmd=clean_mechanical_cmd(),
        factcheck_fn=make_batch_factcheck_fn(claims_fn, claude_cli_fn=cli),
        adversarial_fn=make_batch_adversarial_fn(claude_cli_fn=cli),
        quality_fn=lambda skill_output: quality_fn(skill_output, claude_cli_fn=cli),
    )

    # AUTHENTIC tier -> not risky -> stage 3 never invoked -> stage 4 runs ->
    # score 9.0 >= default threshold 7.0 -> stage 5 -> overall PASS.
    assert verdict.status.value == "pass"
    assert verdict.stage == 5
    assert verdict.factcheck is not None
    assert verdict.factcheck.verdict == "SUPPORTED"
    assert verdict.quality is not None
    assert verdict.quality.score == 9.0
    assert verdict.legal is not None
    assert verdict.legal.status == "needs_human_review"
