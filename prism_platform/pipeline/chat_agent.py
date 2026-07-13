"""Task 5 (Track C.3) -- the embedded chat agent.

A plain `claude -p` invocation (NOT the Claude Agent SDK -- this project's
locked decision, plan doc 2026-07-12 §1), grounded against Postgres/pgvector
via `prism_platform.pipeline.retrieval.retrieve()`. Same `[FACT]`-citation
discipline as the existing prism-hub chat (memory
`project-prism-hub-chat-live.md`): every claim in the answer must cite the
report section that backed it, and the model is instructed not to answer
beyond what was retrieved.

This module's LLM call point (`claude_cli_fn`) is dependency-injected, same
pattern as `gate.py`/`self_heal.py`'s injectable stages -- so prompt
construction and citation-extraction logic are fully unit-testable without a
live `claude` CLI, live DB, or API key. The default `_default_claude_cli`
below is WRITTEN BUT UNVERIFIED against a real `claude -p` invocation in this
sandbox -- see the task-5 report.
"""

from __future__ import annotations

import re
import subprocess
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from prism_platform.pipeline.retrieval import RetrievedChunk, retrieve

NO_CONTEXT_ANSWER = (
    "I don't have any grounded information from this audit report to answer that. "
    "No retrieved context matched your question closely enough to answer safely."
)

_CITATION_PATTERN = re.compile(r"\(Source:\s*([A-Za-z0-9_\-]+)\)")

_SYSTEM_INSTRUCTIONS = (
    "You are a grounded report-QA assistant for a PRISM Algolia search audit. "
    "You must answer ONLY using the CONTEXT sections below -- never from general "
    "knowledge, never by guessing, and never by fabricating a detail not present "
    "in the CONTEXT. Every factual claim in your answer MUST be followed by a "
    "citation in the exact form (Source: <section_name>), naming the bracketed "
    "[SECTION: ...] the claim came from. If the CONTEXT does not contain enough "
    "information to answer the question, say so plainly instead of speculating -- "
    "do not answer beyond what was retrieved."
)


def build_chat_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    """Build the full prompt sent to `claude -p`, injecting retrieved chunks
    with explicit `[SECTION: name]` citation markers the model must reference
    back via `(Source: name)` in its answer.
    """
    if not chunks:
        return (
            f"{_SYSTEM_INSTRUCTIONS}\n\n"
            "CONTEXT:\n(no retrieved context matched this question)\n\n"
            f"QUESTION: {question}\n\n"
            "Tell the user plainly that no matching context was found in the "
            "audit report -- do not fabricate an answer."
        )

    context_block = "\n\n".join(
        f"[SECTION: {chunk.section_name}]\n{chunk.text}" for chunk in chunks
    )
    return (
        f"{_SYSTEM_INSTRUCTIONS}\n\n"
        f"CONTEXT (cite the bracketed [SECTION: name] backing every claim you make):\n"
        f"{context_block}\n\n"
        f"QUESTION: {question}\n\n"
        "Answer using ONLY the CONTEXT above. Cite the section for every factual "
        "claim as (Source: <section_name>)."
    )


def extract_cited_sections(answer: str) -> set[str]:
    """Pull every `(Source: section_name)` tag out of a model answer -- used
    to prove/measure citation discipline, e.g. for a future gate that BLOCKs
    an answer with zero citations despite having retrieved context."""
    return set(_CITATION_PATTERN.findall(answer))


@dataclass(frozen=True)
class ChatAgentResult:
    """What the chat endpoint returns: the answer, which sections it cited,
    and which sections were actually retrieved (for a downstream "cited vs
    retrieved" grounding check -- not enforced here, v1 scope per the brief)."""

    answer: str
    cited_sections: set[str]
    retrieved_sections: tuple[str, ...]


RetrieveFn = Callable[..., Awaitable[list[RetrievedChunk]]]
ClaudeCliFn = Callable[[str], str]


def _default_claude_cli(prompt: str, *, timeout_s: int = 120) -> str:
    """Invoke `claude -p <prompt>` as a plain subprocess (no Agent SDK, no
    MCP) and return its stdout. WRITTEN BUT UNVERIFIED -- no `claude` CLI
    invocation was executed against a live report in this sandbox; see the
    task-5 report for what live verification would look like.
    """
    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_s,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude -p failed (exit {result.returncode}): {result.stderr}")
    return result.stdout.strip()


async def run_chat_agent(
    *,
    session: Any,
    question: str,
    audit_id: uuid.UUID,
    k: int = 5,
    retrieve_fn: RetrieveFn = retrieve,
    claude_cli_fn: ClaudeCliFn = _default_claude_cli,
) -> ChatAgentResult:
    """The chat agent's full turn: retrieve -> build prompt -> invoke `claude -p`.

    If retrieval returns zero chunks, the model is never called -- the
    no-fabrication guarantee is enforced at this boundary, not left to the
    model's own restraint (per `feedback-no-credit-no-fabrication`).
    """
    chunks = await retrieve_fn(session, question, audit_id, k)
    if not chunks:
        return ChatAgentResult(
            answer=NO_CONTEXT_ANSWER, cited_sections=set(), retrieved_sections=()
        )

    prompt = build_chat_prompt(question, chunks)
    answer = claude_cli_fn(prompt)
    return ChatAgentResult(
        answer=answer,
        cited_sections=extract_cited_sections(answer),
        retrieved_sections=tuple(chunk.section_name for chunk in chunks),
    )
