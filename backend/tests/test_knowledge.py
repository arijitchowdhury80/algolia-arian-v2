"""Tests for the Algolia knowledge store router.

Split into two sections:
  - Pure-logic tests (no DB required) — run in any environment.
  - DB-integration tests (require live Postgres with migration 008 applied)
    marked with @pytest.mark.db so they can be skipped: pytest -m 'not db'.

Run pure-logic tests only:
    pytest tests/test_knowledge.py -m 'not db' -v

Run all (DB must be up, migration 008 applied):
    pytest tests/test_knowledge.py -v
"""

from __future__ import annotations

import hashlib

import pytest

from server.api.routers.knowledge import (
    GapResponse,
    KnowledgeResult,
    KnowledgeUpsertResponse,
    RetrieveResponse,
    _build_sources,
    _hash_question,
    _normalize_question,
)

# ===========================================================================
# Pure-logic tests — no database required
# ===========================================================================


class TestNormalizeQuestion:
    def test_lowercases(self) -> None:
        assert _normalize_question("What IS Algolia?") == "what is algolia?"

    def test_strips_leading_trailing_whitespace(self) -> None:
        assert _normalize_question("  hello  ") == "hello"

    def test_collapses_internal_whitespace(self) -> None:
        assert _normalize_question("what  is   algolia") == "what is algolia"

    def test_tabs_and_newlines_collapsed(self) -> None:
        assert _normalize_question("what\t\nis\nalgolia") == "what is algolia"

    def test_idempotent(self) -> None:
        q = "  What IS  Algolia?  "
        assert _normalize_question(_normalize_question(q)) == _normalize_question(q)

    def test_empty_string(self) -> None:
        assert _normalize_question("") == ""

    def test_single_word(self) -> None:
        assert _normalize_question("  ALGOLIA  ") == "algolia"


class TestHashQuestion:
    def test_returns_hex_string(self) -> None:
        h = _hash_question("what is algolia?")
        assert all(c in "0123456789abcdef" for c in h)
        assert len(h) == 64  # SHA-256 hex = 64 chars

    def test_deterministic(self) -> None:
        assert _hash_question("algolia search") == _hash_question("algolia search")

    def test_normalization_applied_before_hashing(self) -> None:
        """Different surface forms that normalize identically must hash identically."""
        assert _hash_question("  What IS Algolia? ") == _hash_question("what is algolia?")
        assert _hash_question("ALGOLIA\tSEARCH") == _hash_question("algolia search")

    def test_different_questions_produce_different_hashes(self) -> None:
        assert _hash_question("question one") != _hash_question("question two")

    def test_hash_matches_manual_sha256(self) -> None:
        normalized = _normalize_question("What is Algolia?")
        expected = hashlib.sha256(normalized.encode()).hexdigest()
        assert _hash_question("What is Algolia?") == expected


class TestBuildSources:
    def test_knowledge_row_parses_json_list(self) -> None:
        sources = _build_sources('["https://a.com", "https://b.com"]', None)
        assert sources == ["https://a.com", "https://b.com"]

    def test_fallback_to_url_when_sources_raw_is_none(self) -> None:
        sources = _build_sources(None, "https://case-study.com")
        assert sources == ["https://case-study.com"]

    def test_empty_list_when_both_null(self) -> None:
        sources = _build_sources(None, None)
        assert sources == []

    def test_empty_json_list(self) -> None:
        sources = _build_sources("[]", None)
        assert sources == []

    def test_malformed_json_falls_back_to_url(self) -> None:
        sources = _build_sources("not-json", "https://fallback.com")
        assert sources == ["https://fallback.com"]

    def test_filters_empty_strings_from_json(self) -> None:
        sources = _build_sources('["https://a.com", "", null]', None)
        assert sources == ["https://a.com"]


class TestResponseModels:
    def test_knowledge_result_required_fields(self) -> None:
        r = KnowledgeResult(
            kind="knowledge",
            title="Algolia",
            text="Algolia is a search API.",
            sources=["https://algolia.com"],
            score=0.42,
        )
        assert r.kind == "knowledge"
        assert r.score == pytest.approx(0.42)

    def test_retrieve_response_shape(self) -> None:
        result = KnowledgeResult(
            kind="case_study",
            title="Acme Corp",
            text="Acme Corp — 20% uplift.",
            sources=[],
            score=0.8,
        )
        resp = RetrieveResponse(results=[result], count=1)
        assert resp.count == 1
        assert len(resp.results) == 1
        assert resp.results[0].kind == "case_study"

    def test_retrieve_response_empty(self) -> None:
        resp = RetrieveResponse(results=[], count=0)
        assert resp.count == 0
        assert resp.results == []

    def test_gap_response_fields(self) -> None:
        g = GapResponse(id="abc-123", status="open", deduped=False)
        assert g.deduped is False

    def test_gap_response_deduped_flag(self) -> None:
        g = GapResponse(id="abc-123", status="open", deduped=True)
        assert g.deduped is True

    def test_knowledge_upsert_response_created(self) -> None:
        r = KnowledgeUpsertResponse(id="abc-123", created=True, updated=False)
        assert r.created is True
        assert r.updated is False

    def test_knowledge_upsert_response_updated(self) -> None:
        r = KnowledgeUpsertResponse(id="abc-123", created=False, updated=True)
        assert r.created is False
        assert r.updated is True

    def test_knowledge_result_sources_is_list(self) -> None:
        r = KnowledgeResult(
            kind="proofpoint",
            title="Acme",
            text="Some result.",
            sources=[],
            score=0.1,
        )
        assert isinstance(r.sources, list)


# ===========================================================================
# DB-integration tests — require live Postgres with migration 008 applied.
#
# Run: pytest tests/test_knowledge.py -v
# Skip: pytest tests/test_knowledge.py -m 'not db'
#
# These tests use the project's async session factory directly to INSERT rows
# then call the router functions with a real session.  They assume:
#   - DATABASE_URL points to a local 'prism' Postgres instance
#   - Migration 008 has been applied (algolia_knowledge + algolia_gaps exist)
# ===========================================================================


pytestmark_db = pytest.mark.db


@pytest.mark.db
@pytest.mark.asyncio
async def test_knowledge_upsert_created() -> None:
    """Insert a new knowledge entry — created=True, updated=False."""
    from sqlalchemy import delete

    from core.db.models import AlgoliaKnowledge
    from core.db.session import get_session
    from server.api.routers.knowledge import KnowledgeUpsertRequest, upsert_knowledge

    question = "Integration test: what is Algolia? (test_knowledge_upsert_created)"
    async for session in get_session():
        # Clean up any leftover from a previous test run
        from server.api.routers.knowledge import _hash_question as hq

        await session.execute(
            delete(AlgoliaKnowledge).where(AlgoliaKnowledge.question_hash == hq(question))
        )
        await session.commit()

    async for session in get_session():
        body = KnowledgeUpsertRequest(
            topic="algolia-overview",
            question=question,
            answer="Algolia is a hosted search and discovery API.",
            sources=["https://algolia.com"],
            origin="seed",
        )
        result = await upsert_knowledge(body, session)
        assert result.created is True
        assert result.updated is False
        assert result.id  # non-empty uuid string

    # Cleanup
    async for session in get_session():
        from server.api.routers.knowledge import _hash_question as hq

        await session.execute(
            delete(AlgoliaKnowledge).where(AlgoliaKnowledge.question_hash == hq(question))
        )
        await session.commit()


@pytest.mark.db
@pytest.mark.asyncio
async def test_knowledge_upsert_updated() -> None:
    """Insert then re-insert the same question — second call must return updated=True."""
    from sqlalchemy import delete

    from core.db.models import AlgoliaKnowledge
    from core.db.session import get_session
    from server.api.routers.knowledge import KnowledgeUpsertRequest, upsert_knowledge
    from server.api.routers.knowledge import _hash_question as hq

    question = "Integration test: upsert update check (test_knowledge_upsert_updated)"
    q_hash = hq(question)

    # Seed + then update
    for i, (answer, expect_created, expect_updated) in enumerate(
        [
            ("First answer.", True, False),
            ("Updated answer.", False, True),
        ]
    ):
        async for session in get_session():
            if i == 0:
                await session.execute(
                    delete(AlgoliaKnowledge).where(AlgoliaKnowledge.question_hash == q_hash)
                )
                await session.commit()

        async for session in get_session():
            body = KnowledgeUpsertRequest(
                topic="test-topic",
                question=question,
                answer=answer,
            )
            result = await upsert_knowledge(body, session)
            assert result.created is expect_created
            assert result.updated is expect_updated

    # Cleanup
    async for session in get_session():
        await session.execute(
            delete(AlgoliaKnowledge).where(AlgoliaKnowledge.question_hash == q_hash)
        )
        await session.commit()


@pytest.mark.db
@pytest.mark.asyncio
async def test_gap_dedup() -> None:
    """Recording the same question twice must return deduped=True on the second call."""
    from sqlalchemy import delete

    from core.db.models import AlgoliaGap
    from core.db.session import get_session
    from server.api.routers.knowledge import GapRequest, create_gap
    from server.api.routers.knowledge import _hash_question as hq

    question = "Integration test: gap dedup check (test_gap_dedup)"
    q_hash = hq(question)

    # Clean slate
    async for session in get_session():
        await session.execute(delete(AlgoliaGap).where(AlgoliaGap.question_hash == q_hash))
        await session.commit()

    # First call — should insert
    async for session in get_session():
        r1 = await create_gap(GapRequest(question=question), session)
    assert r1.deduped is False
    assert r1.status == "open"
    first_id = r1.id

    # Second call with same question — should dedup
    async for session in get_session():
        r2 = await create_gap(GapRequest(question=question), session)
    assert r2.deduped is True
    assert r2.id == first_id

    # Normalization variant should also dedup
    async for session in get_session():
        r3 = await create_gap(GapRequest(question=question.upper()), session)
    assert r3.deduped is True
    assert r3.id == first_id

    # Cleanup
    async for session in get_session():
        await session.execute(delete(AlgoliaGap).where(AlgoliaGap.question_hash == q_hash))
        await session.commit()


@pytest.mark.db
@pytest.mark.asyncio
async def test_retrieve_response_shape() -> None:
    """Retrieve from empty tables returns a well-shaped RetrieveResponse."""
    from core.db.session import get_session
    from server.api.routers.knowledge import RetrieveRequest, retrieve_knowledge

    async for session in get_session():
        resp = await retrieve_knowledge(RetrieveRequest(query="algolia search", k=5), session)

    # Shape contract — count == len(results) always
    assert resp.count == len(resp.results)
    for r in resp.results:
        assert isinstance(r.kind, str)
        assert isinstance(r.title, str)
        assert isinstance(r.text, str)
        assert isinstance(r.sources, list)
        assert isinstance(r.score, float)
