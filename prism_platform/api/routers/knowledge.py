"""PRISM Knowledge Router -- Algolia knowledge store: retrieve, gap tracking, upsert."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text

from prism_platform.api.deps import DbSession
from prism_platform.db.models import AlgoliaGap, AlgoliaKnowledge

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Question-hash helpers (single source of truth for normalization)
# ---------------------------------------------------------------------------


def _normalize_question(question: str) -> str:
    """Lowercase, strip leading/trailing whitespace, collapse internal whitespace."""
    return re.sub(r"\s+", " ", question.strip().lower())


def _hash_question(question: str) -> str:
    """Return the SHA-256 hex digest of the normalized question."""
    return hashlib.sha256(_normalize_question(question).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class RetrieveRequest(BaseModel):
    query: str
    k: int = 8


class KnowledgeResult(BaseModel):
    kind: str
    title: str
    text: str
    sources: list[str]
    score: float


class RetrieveResponse(BaseModel):
    results: list[KnowledgeResult]
    count: int


class GapRequest(BaseModel):
    question: str
    topic: str | None = None
    conversation_id: str | None = None
    why: str = "kb_miss"


class GapResponse(BaseModel):
    id: str
    status: str
    deduped: bool


class KnowledgeUpsertRequest(BaseModel):
    topic: str
    question: str
    answer: str
    sources: list[str] = []
    confidence: float | None = None
    judge_score: float | None = None
    origin: str = "learned"


class KnowledgeUpsertResponse(BaseModel):
    id: str
    created: bool
    updated: bool


# ---------------------------------------------------------------------------
# FTS UNION query across all four searchable tables
# ---------------------------------------------------------------------------

_RETRIEVE_SQL = text(
    """
    WITH tsq AS (
        SELECT plainto_tsquery('english', :query) AS q
    )
    SELECT
        'knowledge'                        AS kind,
        aks.topic                          AS title,
        aks.answer                         AS text_body,
        aks.sources::text                  AS sources_raw,
        NULL::text                         AS url,
        ts_rank(aks.search_tsv, tsq.q)    AS score
    FROM algolia_knowledge aks
    CROSS JOIN tsq
    WHERE aks.search_tsv @@ tsq.q

    UNION ALL

    SELECT
        'case_study'                                                   AS kind,
        acs.customer_name                                              AS title,
        acs.customer_name || ' — ' || coalesce(acs.key_results, '')
            || CASE
                   WHEN acs.competitor_takeout IS NOT NULL
                   THEN ' [' || acs.competitor_takeout || ']'
                   ELSE ''
               END                                                     AS text_body,
        NULL::text                                                     AS sources_raw,
        acs.url                                                        AS url,
        ts_rank(acs.search_tsv, tsq.q)                                AS score
    FROM algolia_case_studies acs
    CROSS JOIN tsq
    WHERE acs.search_tsv @@ tsq.q

    UNION ALL

    SELECT
        'proofpoint'                                        AS kind,
        coalesce(app.customer_or_theme, 'Algolia')          AS title,
        app.result_text                                     AS text_body,
        NULL::text                                          AS sources_raw,
        app.source                                          AS url,
        ts_rank(app.search_tsv, tsq.q)                     AS score
    FROM algolia_proofpoints app
    CROSS JOIN tsq
    WHERE app.search_tsv @@ tsq.q

    UNION ALL

    SELECT
        'quote'                                                        AS kind,
        aq.customer_name                                               AS title,
        '"' || aq.quote_text || '" — ' || coalesce(aq.person_title, '') AS text_body,
        NULL::text                                                     AS sources_raw,
        aq.source                                                      AS url,
        ts_rank(aq.search_tsv, tsq.q)                                 AS score
    FROM algolia_quotes aq
    CROSS JOIN tsq
    WHERE aq.search_tsv @@ tsq.q

    ORDER BY score DESC
    LIMIT :k
    """
)


def _build_sources(sources_raw: str | None, url: str | None) -> list[str]:
    """Convert SQL-returned source data into a list[str].

    - For knowledge rows: sources_raw is the JSONB::text representation of list[str].
    - For all other rows: sources_raw is NULL; url may carry a single URL.
    """
    if sources_raw is not None:
        try:
            parsed: Any = json.loads(sources_raw)
            if isinstance(parsed, list):
                return [str(s) for s in parsed if s]
        except (json.JSONDecodeError, TypeError):
            pass
    if url:
        return [url]
    return []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_knowledge(body: RetrieveRequest, session: DbSession) -> RetrieveResponse:
    """Full-text search across the Algolia knowledge store and evidence tables.

    Runs plainto_tsquery against the search_tsv GENERATED columns on
    algolia_knowledge, algolia_case_studies, algolia_proofpoints, and
    algolia_quotes, then UNIONs and ranks by ts_rank.

    Args:
        body: Query string and optional result limit k.
        session: Injected async database session.

    Returns:
        Ranked list of knowledge results with kind, title, text, sources, score.
    """
    logger.info("knowledge.retrieve.start", query=body.query, k=body.k)
    try:
        result = await session.execute(_RETRIEVE_SQL, {"query": body.query, "k": body.k})
        rows = result.mappings().all()

        results: list[KnowledgeResult] = []
        for row in rows:
            results.append(
                KnowledgeResult(
                    kind=row["kind"],
                    title=row["title"] or "",
                    text=row["text_body"] or "",
                    sources=_build_sources(row["sources_raw"], row["url"]),
                    score=float(row["score"]),
                )
            )

        logger.info("knowledge.retrieve.done", query=body.query, count=len(results))
        return RetrieveResponse(results=results, count=len(results))

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("knowledge.retrieve.failed", error=str(exc), query=body.query)
        raise HTTPException(status_code=500, detail="Knowledge retrieval failed.") from exc


@router.post("/gaps", response_model=GapResponse)
async def create_gap(body: GapRequest, session: DbSession) -> GapResponse:
    """Record a question that could not be answered from the knowledge store.

    Deduplicates: if an OPEN gap already exists for the same normalized
    question, returns that gap's id with deduped=True instead of inserting.

    Args:
        body: Question, optional topic/conversation_id, and why (kb_miss|low_confidence).
        session: Injected async database session.

    Returns:
        Gap id, status, and whether this was a deduped return.
    """
    logger.info("knowledge.gaps.start", why=body.why)
    try:
        q_hash = _hash_question(body.question)

        # Dedup: return existing open gap if question already logged
        existing_result = await session.execute(
            select(AlgoliaGap).where(
                AlgoliaGap.question_hash == q_hash,
                AlgoliaGap.status == "open",
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            logger.info("knowledge.gaps.deduped", gap_id=str(existing.id))
            return GapResponse(id=str(existing.id), status=existing.status, deduped=True)

        # Insert new gap
        new_gap = AlgoliaGap(
            question=body.question,
            question_hash=q_hash,
            topic=body.topic,
            conversation_id=body.conversation_id,
            why=body.why,
            status="open",
        )
        session.add(new_gap)
        await session.flush()

        logger.info("knowledge.gaps.created", gap_id=str(new_gap.id))
        return GapResponse(id=str(new_gap.id), status="open", deduped=False)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("knowledge.gaps.failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Gap creation failed.") from exc


@router.post("/", response_model=KnowledgeUpsertResponse)
async def upsert_knowledge(
    body: KnowledgeUpsertRequest, session: DbSession
) -> KnowledgeUpsertResponse:
    """Insert or update a knowledge entry, keyed on the normalized question hash.

    If a row with the same question_hash already exists, updates answer,
    sources, confidence, and judge_score.  Otherwise inserts a new row.

    Args:
        body: topic, question, answer, optional sources/scores/origin.
        session: Injected async database session.

    Returns:
        Row id plus created/updated flags (exactly one will be True).
    """
    logger.info("knowledge.upsert.start", topic=body.topic)
    try:
        q_hash = _hash_question(body.question)

        existing_result = await session.execute(
            select(AlgoliaKnowledge).where(AlgoliaKnowledge.question_hash == q_hash)
        )
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            # Update mutable fields; onupdate fires automatically on flush
            existing.answer = body.answer
            existing.sources = body.sources  # type: ignore[assignment]
            if body.confidence is not None:
                existing.confidence = body.confidence  # type: ignore[assignment]
            if body.judge_score is not None:
                existing.judge_score = body.judge_score  # type: ignore[assignment]
            await session.flush()
            logger.info("knowledge.upsert.updated", id=str(existing.id))
            return KnowledgeUpsertResponse(id=str(existing.id), created=False, updated=True)

        # Insert new knowledge entry
        new_entry = AlgoliaKnowledge(
            topic=body.topic,
            question=body.question,
            question_hash=q_hash,
            answer=body.answer,
            sources=body.sources,  # type: ignore[arg-type]
            confidence=body.confidence,  # type: ignore[arg-type]
            judge_score=body.judge_score,  # type: ignore[arg-type]
            origin=body.origin,
        )
        session.add(new_entry)
        await session.flush()

        logger.info("knowledge.upsert.created", id=str(new_entry.id))
        return KnowledgeUpsertResponse(id=str(new_entry.id), created=True, updated=False)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("knowledge.upsert.failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Knowledge upsert failed.") from exc
