"""Tests for Task 5's `retrieve()` -- pure decision logic, no live Postgres.

`retrieve()` itself needs a real pgvector-backed Postgres to execute its
SQL (the `<=>` cosine-distance operator is a Postgres/pgvector extension
function, not something SQLite or an in-memory fake can evaluate). Per the
task-5 brief's DoD ("retrieval + chunking logic has real unit tests with
fixture data (no live DB needed for the pure logic)"), this module tests the
parts that ARE pure logic without a DB:
  - the threshold-filter helper (`_passes_threshold`)
  - the row -> RetrievedChunk mapping (`_row_to_chunk`)
  - the query embedding call is made exactly once per `retrieve()` call
    (verified against a stub session that returns canned rows)

The actual `retrieve()` end-to-end SQL execution against real pgvector is
NOT exercised here -- no live Postgres in this sandbox (confirmed: `nc -z
localhost 5432` closed, no docker daemon reachable). See task-5 report for
the explicit LIVE-VERIFIED vs WRITTEN-BUT-UNVERIFIED split.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import pytest

from server.pipeline.retrieval import (
    SIMILARITY_THRESHOLD,
    RetrievedChunk,
    _passes_threshold,
    _row_to_chunk,
    retrieve,
)


def test_similarity_threshold_is_the_locked_default() -> None:
    # Patch #9 locks this exact value as a named constant, not a magic number.
    assert SIMILARITY_THRESHOLD == 0.35


@pytest.mark.parametrize(
    ("similarity", "expected"),
    [(0.9, True), (0.35, True), (0.34, False), (0.0, False), (1.0, True)],
)
def test_passes_threshold(similarity: float, expected: bool) -> None:
    assert _passes_threshold(similarity) is expected


@dataclass
class _FakeRow:
    section_name: str
    chunk_text: str
    similarity: float


def test_row_to_chunk_maps_fields() -> None:
    row = _FakeRow(section_name="tech_stack", chunk_text="# tech_stack\n...", similarity=0.62)
    chunk = _row_to_chunk(row)
    assert chunk == RetrievedChunk(
        section_name="tech_stack", text="# tech_stack\n...", similarity=0.62
    )


class _FakeResult:
    def __init__(self, rows: list[_FakeRow]) -> None:
        self._rows = rows

    def all(self) -> list[_FakeRow]:
        return self._rows


class _FakeSession:
    """Stub AsyncSession -- records the statement it was asked to execute and
    returns canned rows, so `retrieve()`'s embed-then-query-then-filter
    control flow is exercised without a real DB connection."""

    def __init__(self, rows: list[_FakeRow]) -> None:
        self._rows = rows
        self.executed_statements: list[Any] = []

    async def execute(self, stmt: Any) -> _FakeResult:
        self.executed_statements.append(stmt)
        return _FakeResult(self._rows)


@pytest.mark.asyncio
async def test_retrieve_embeds_query_exactly_once() -> None:
    calls: list[list[str]] = []

    def fake_embed(texts: list[str]) -> list[list[float]]:
        calls.append(texts)
        return [[0.1] * 384 for _ in texts]

    session = _FakeSession(rows=[_FakeRow("meta", "# meta\n...", 0.9)])
    await retrieve(session, "what search vendor do they use", uuid.uuid4(), embed_fn=fake_embed)
    assert len(calls) == 1
    assert calls[0] == ["what search vendor do they use"]


@pytest.mark.asyncio
async def test_retrieve_filters_out_rows_below_threshold() -> None:
    rows = [
        _FakeRow("findings", "# findings\n...", 0.9),
        _FakeRow("bibliography", "# bibliography\n...", 0.1),  # below threshold
    ]
    session = _FakeSession(rows=rows)
    results = await retrieve(
        session, "query", uuid.uuid4(), embed_fn=lambda t: [[0.0] * 384 for _ in t]
    )
    assert [r.section_name for r in results] == ["findings"]


@pytest.mark.asyncio
async def test_retrieve_returns_retrieved_chunk_instances_with_citations() -> None:
    rows = [_FakeRow("competitors", "# competitors\n...", 0.5)]
    session = _FakeSession(rows=rows)
    results = await retrieve(
        session, "who competes with them", uuid.uuid4(), embed_fn=lambda t: [[0.0] * 384 for _ in t]
    )
    assert results == [
        RetrievedChunk(section_name="competitors", text="# competitors\n...", similarity=0.5)
    ]


@pytest.mark.asyncio
async def test_retrieve_empty_query_result_returns_empty_list() -> None:
    session = _FakeSession(rows=[])
    results = await retrieve(
        session, "anything", uuid.uuid4(), embed_fn=lambda t: [[0.0] * 384 for _ in t]
    )
    assert results == []
