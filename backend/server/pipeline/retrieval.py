"""Task 5 (Track C.3) -- retrieve grounding chunks for the chat agent.

Per the task-5 brief's patch #9 (locked):
  - similarity: cosine, via pgvector's `<=>` operator (exposed here through
    `pgvector.sqlalchemy`'s `Column.cosine_distance()` comparator, where
    `similarity = 1 - cosine_distance`)
  - threshold: cosine similarity >= 0.35 (SIMILARITY_THRESHOLD below --
    a named constant, not a magic number scattered inline)
  - retrieval: top-k=5 chunks per query, no cross-encoder re-ranking (v1 scope)

`retrieve()` needs a real pgvector-backed Postgres connection to execute its
SQL. There is no live Postgres in this sandbox (confirmed: port 5432 closed,
no docker daemon reachable) -- the SQL construction below is WRITTEN BUT
UNVERIFIED against a real database. The pure decision logic (threshold
filter, row mapping) IS unit-tested with fakes; see tests/pipeline/test_retrieval.py.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import select

from core.db.models import ReportChunk
from server.pipeline.embeddings import embed_texts

SIMILARITY_THRESHOLD = 0.35  # patch #9 -- typical usable threshold for MiniLM-class models
DEFAULT_TOP_K = 5


@dataclass(frozen=True)
class RetrievedChunk:
    """A grounding chunk returned to the chat agent, carrying its citation."""

    section_name: str  # the citation -- which report section backs this chunk
    text: str
    similarity: float


class _AsyncSessionLike(Protocol):
    async def execute(self, stmt: Any) -> Any: ...


EmbedFn = Callable[[list[str]], list[list[float]]]


def _passes_threshold(similarity: float) -> bool:
    return similarity >= SIMILARITY_THRESHOLD


def _row_to_chunk(row: Any) -> RetrievedChunk:
    return RetrievedChunk(
        section_name=row.section_name,
        text=row.chunk_text,
        similarity=float(row.similarity),
    )


async def retrieve(
    session: _AsyncSessionLike,
    query: str,
    audit_id: uuid.UUID,
    k: int = DEFAULT_TOP_K,
    *,
    embed_fn: EmbedFn = embed_texts,
) -> list[RetrievedChunk]:
    """Embed `query` with the same local model used at index time, run the
    pgvector cosine-similarity search scoped to `audit_id`, and return the
    chunks that clear `SIMILARITY_THRESHOLD` (each carrying its section name
    for citation) -- top `k` candidates considered, threshold-filtered after.
    """
    query_vector = embed_fn([query])[0]

    similarity_expr = (1 - ReportChunk.embedding.cosine_distance(query_vector)).label("similarity")
    stmt = (
        select(ReportChunk.section_name, ReportChunk.chunk_text, similarity_expr)
        .where(ReportChunk.audit_id == audit_id)
        .order_by(ReportChunk.embedding.cosine_distance(query_vector))
        .limit(k)
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [_row_to_chunk(row) for row in rows if _passes_threshold(float(row.similarity))]
