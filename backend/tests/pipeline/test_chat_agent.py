"""Tests for Task 5's chat agent -- prompt construction + citation discipline.

DoD (task-5 brief): "given a fake retrieve() returning known chunks, the
agent's prompt-construction step provably includes section-name citations
and instructs the model not to answer beyond what's retrieved." All of this
is pure logic -- no live LLM call, no live DB -- so every test here runs
without network/DB/API-key access.
"""

from __future__ import annotations

import uuid

import pytest

from server.pipeline.chat_agent import (
    DEFAULT_CLAUDE_CLI_TIMEOUT_S,
    NO_CONTEXT_ANSWER,
    ChatAgentResult,
    _default_claude_cli,
    build_chat_prompt,
    extract_cited_sections,
    run_chat_agent,
)
from server.pipeline.retrieval import RetrievedChunk


def _chunks() -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            section_name="tech_stack",
            text="# tech_stack\nCurrent search vendor: Bloomreach. Ecommerce platform: SFCC.",
            similarity=0.71,
        ),
        RetrievedChunk(
            section_name="findings",
            text="# findings\nNo typo tolerance on misspelled product queries.",
            similarity=0.52,
        ),
    ]


def test_build_chat_prompt_includes_every_chunk_section_name_as_a_citation_marker() -> None:
    prompt = build_chat_prompt("what search vendor do they use today?", _chunks())
    assert "[SECTION: tech_stack]" in prompt
    assert "[SECTION: findings]" in prompt


def test_build_chat_prompt_includes_chunk_text() -> None:
    prompt = build_chat_prompt("what search vendor do they use today?", _chunks())
    assert "Bloomreach" in prompt
    assert "typo tolerance" in prompt


def test_build_chat_prompt_instructs_grounded_only_answering() -> None:
    prompt = build_chat_prompt("anything", _chunks())
    lowered = prompt.lower()
    # The model must be told not to answer beyond retrieved context.
    assert "only" in lowered and "context" in lowered
    assert "cite" in lowered or "citation" in lowered
    assert "do not" in lowered or "must not" in lowered or "never" in lowered


def test_build_chat_prompt_includes_the_question() -> None:
    prompt = build_chat_prompt("does the site have typo tolerance?", _chunks())
    assert "does the site have typo tolerance?" in prompt


def test_build_chat_prompt_with_no_chunks_still_forbids_fabrication() -> None:
    prompt = build_chat_prompt("anything", [])
    assert "no retrieved context" in prompt.lower() or "no matching context" in prompt.lower()


def test_extract_cited_sections_finds_source_tags() -> None:
    answer = (
        "The current vendor is Bloomreach (Source: tech_stack). There is no typo "
        "tolerance on misspelled queries (Source: findings)."
    )
    assert extract_cited_sections(answer) == {"tech_stack", "findings"}


def test_extract_cited_sections_empty_when_no_tags() -> None:
    assert extract_cited_sections("The vendor is Bloomreach.") == set()


class TestDefaultClaudeCliTimeout:
    """Task 6d fix #2: Task 5b's own live-proof measured 37.4s against a tiny
    synthetic fixture; real full-audit `gate()` calls took 130-206s and hit
    the old 120s default's `TimeoutExpired` twice (task-6-local-report.md
    Findings #2). These are simple assertions on the new default, not a live
    200s+ `claude -p` call -- keeps the suite fast."""

    def test_module_level_constant_has_real_headroom(self) -> None:
        assert DEFAULT_CLAUDE_CLI_TIMEOUT_S == 300

    def test_default_claude_cli_uses_the_module_constant_as_its_default(self) -> None:
        import inspect

        sig = inspect.signature(_default_claude_cli)
        assert sig.parameters["timeout_s"].default == DEFAULT_CLAUDE_CLI_TIMEOUT_S

    def test_default_claude_cli_passes_timeout_s_through_to_subprocess_run(self) -> None:
        captured: dict[str, object] = {}

        class _FakeCompletedProcess:
            returncode = 0
            stdout = "ok"
            stderr = ""

        def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
            captured.update(kwargs)
            return _FakeCompletedProcess()

        import server.pipeline.chat_agent as chat_agent_module

        original_run = chat_agent_module.subprocess.run
        chat_agent_module.subprocess.run = fake_run  # type: ignore[assignment]
        try:
            _default_claude_cli("hello")
        finally:
            chat_agent_module.subprocess.run = original_run  # type: ignore[assignment]

        assert captured["timeout"] == DEFAULT_CLAUDE_CLI_TIMEOUT_S


@pytest.mark.asyncio
async def test_run_chat_agent_calls_retrieve_then_builds_prompt_then_invokes_cli() -> None:
    seen_prompts: list[str] = []

    async def fake_retrieve(session, query, audit_id, k=5, **kwargs):
        assert query == "what vendor do they use?"
        return _chunks()

    def fake_cli(prompt: str) -> str:
        seen_prompts.append(prompt)
        return "Bloomreach is the current vendor (Source: tech_stack)."

    result = await run_chat_agent(
        session=object(),
        question="what vendor do they use?",
        audit_id=uuid.uuid4(),
        retrieve_fn=fake_retrieve,
        claude_cli_fn=fake_cli,
    )

    assert len(seen_prompts) == 1
    assert "[SECTION: tech_stack]" in seen_prompts[0]
    assert isinstance(result, ChatAgentResult)
    assert result.answer == "Bloomreach is the current vendor (Source: tech_stack)."
    assert result.cited_sections == {"tech_stack"}
    assert result.retrieved_sections == ("tech_stack", "findings")


@pytest.mark.asyncio
async def test_run_chat_agent_no_chunks_returns_no_context_answer_without_calling_cli() -> None:
    cli_calls: list[str] = []

    async def empty_retrieve(session, query, audit_id, k=5, **kwargs):
        return []

    def fake_cli(prompt: str) -> str:
        cli_calls.append(prompt)
        return "should not be called"

    result = await run_chat_agent(
        session=object(),
        question="anything",
        audit_id=uuid.uuid4(),
        retrieve_fn=empty_retrieve,
        claude_cli_fn=fake_cli,
    )

    assert result.answer == NO_CONTEXT_ANSWER
    assert result.cited_sections == set()
    assert cli_calls == []  # never invoke the LLM with zero grounding context
