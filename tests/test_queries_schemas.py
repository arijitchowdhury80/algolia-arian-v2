"""Contract tests for intel-queries schemas.

Validates Pydantic models accept valid data, reject invalid data,
and enforce all constraints for the query generation module.
25+ pure Pydantic tests. No API calls.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.intel_queries.schemas import (
    DIFFICULTY_LEVELS,
    DIFFICULTY_MAP,
    QUERY_TYPES,
    CompetitorQuerySet,
    QueriesInput,
    QueriesOutput,
    QueryDifficultyDistribution,
    TestQuery,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_test_query(**overrides: object) -> dict:
    """Build a valid TestQuery dict with optional overrides."""
    base = {
        "query": "Dell XPS 15",
        "query_type": "exact_product",
        "difficulty": "easy",
        "expected_behavior": "Should return the Dell XPS 15 laptop product page",
        "what_good_looks_like": "Top result is the Dell XPS 15 product page",
        "what_bad_looks_like": "Returns unrelated products or no results",
        "target_domain": "dell.com",
    }
    base.update(overrides)
    return base


def _make_queries_output(**overrides: object) -> dict:
    """Build a valid QueriesOutput dict with optional overrides."""
    queries = []
    # Generate 2 queries per type for a complete set of 16
    for qt in QUERY_TYPES:
        for i in range(2):
            queries.append(
                _make_test_query(
                    query=f"test query {qt} {i}",
                    query_type=qt,
                    difficulty=DIFFICULTY_MAP.get(qt, "medium"),
                )
            )

    base: dict = {
        "domain": "dell.com",
        "industry": "Enterprise Technology",
        "sub_vertical": "Consumer Electronics",
        "prospect_queries": queries,
        "competitor_query_sets": [],
        "difficulty_distribution": {
            "easy_count": 2,
            "medium_count": 4,
            "hard_count": 10,
        },
        "query_count": 16,
        "types_covered": list(QUERY_TYPES),
        "generation_notes": "Test data",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# QueriesInput tests
# ---------------------------------------------------------------------------


class TestQueriesInput:
    """Tests for QueriesInput validation."""

    def test_valid_input(self) -> None:
        inp = QueriesInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            QueriesInput(domain="dell.com", unknown="bad")

    def test_domain_required(self) -> None:
        with pytest.raises(ValidationError):
            QueriesInput()


# ---------------------------------------------------------------------------
# TestQuery tests
# ---------------------------------------------------------------------------


class TestTestQuery:
    """Tests for TestQuery model validation."""

    def test_valid_query(self) -> None:
        q = TestQuery(**_make_test_query())
        assert q.query == "Dell XPS 15"
        assert q.query_type == "exact_product"
        assert q.difficulty == "easy"

    def test_all_query_types_valid(self) -> None:
        for qt in QUERY_TYPES:
            q = TestQuery(**_make_test_query(query_type=qt))
            assert q.query_type == qt

    def test_all_difficulty_levels_valid(self) -> None:
        for diff in DIFFICULTY_LEVELS:
            q = TestQuery(**_make_test_query(difficulty=diff))
            assert q.difficulty == diff

    def test_rejects_invalid_query_type(self) -> None:
        with pytest.raises(ValidationError, match="query_type"):
            TestQuery(**_make_test_query(query_type="invalid_type"))

    def test_rejects_invalid_difficulty(self) -> None:
        with pytest.raises(ValidationError, match="difficulty"):
            TestQuery(**_make_test_query(difficulty="extreme"))

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            TestQuery(**_make_test_query(unknown_field="bad"))

    def test_query_required(self) -> None:
        data = _make_test_query()
        del data["query"]
        with pytest.raises(ValidationError):
            TestQuery(**data)

    def test_expected_behavior_required(self) -> None:
        data = _make_test_query()
        del data["expected_behavior"]
        with pytest.raises(ValidationError):
            TestQuery(**data)

    def test_what_good_looks_like_required(self) -> None:
        data = _make_test_query()
        del data["what_good_looks_like"]
        with pytest.raises(ValidationError):
            TestQuery(**data)

    def test_what_bad_looks_like_required(self) -> None:
        data = _make_test_query()
        del data["what_bad_looks_like"]
        with pytest.raises(ValidationError):
            TestQuery(**data)

    def test_target_domain_required(self) -> None:
        data = _make_test_query()
        del data["target_domain"]
        with pytest.raises(ValidationError):
            TestQuery(**data)

    def test_model_dump_roundtrip(self) -> None:
        q = TestQuery(**_make_test_query())
        dumped = q.model_dump()
        q2 = TestQuery.model_validate(dumped)
        assert q == q2


# ---------------------------------------------------------------------------
# CompetitorQuerySet tests
# ---------------------------------------------------------------------------


class TestCompetitorQuerySet:
    """Tests for CompetitorQuerySet model validation."""

    def test_valid_competitor_set(self) -> None:
        cqs = CompetitorQuerySet(
            company_name="HP Inc.",
            domain="hp.com",
            queries=[TestQuery(**_make_test_query(target_domain="hp.com"))],
        )
        assert cqs.company_name == "HP Inc."
        assert cqs.domain == "hp.com"
        assert len(cqs.queries) == 1

    def test_empty_queries_default(self) -> None:
        cqs = CompetitorQuerySet(company_name="HP Inc.", domain="hp.com")
        assert cqs.queries == []

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            CompetitorQuerySet(
                company_name="HP Inc.",
                domain="hp.com",
                extra_field="bad",
            )


# ---------------------------------------------------------------------------
# QueryDifficultyDistribution tests
# ---------------------------------------------------------------------------


class TestQueryDifficultyDistribution:
    """Tests for QueryDifficultyDistribution model."""

    def test_defaults_to_zero(self) -> None:
        dist = QueryDifficultyDistribution()
        assert dist.easy_count == 0
        assert dist.medium_count == 0
        assert dist.hard_count == 0

    def test_custom_values(self) -> None:
        dist = QueryDifficultyDistribution(easy_count=2, medium_count=4, hard_count=10)
        assert dist.easy_count == 2
        assert dist.medium_count == 4
        assert dist.hard_count == 10

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            QueryDifficultyDistribution(easy_count=2, unknown=5)


# ---------------------------------------------------------------------------
# QueriesOutput tests
# ---------------------------------------------------------------------------


class TestQueriesOutput:
    """Tests for QueriesOutput model validation."""

    def test_valid_full_output(self) -> None:
        out = QueriesOutput(**_make_queries_output())
        assert out.domain == "dell.com"
        assert out.query_count == 16
        assert len(out.prospect_queries) == 16
        assert len(out.types_covered) == 8

    def test_defaults(self) -> None:
        out = QueriesOutput(domain="dell.com")
        assert out.industry == ""
        assert out.sub_vertical is None
        assert out.prospect_queries == []
        assert out.competitor_query_sets == []
        assert out.difficulty_distribution is None
        assert out.query_count == 0
        assert out.types_covered == []
        assert out.generation_notes == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            QueriesOutput(domain="dell.com", unknown="bad")

    def test_domain_required(self) -> None:
        with pytest.raises(ValidationError):
            QueriesOutput()

    def test_model_dump_roundtrip(self) -> None:
        out = QueriesOutput(**_make_queries_output())
        dumped = out.model_dump()
        out2 = QueriesOutput.model_validate(dumped)
        assert out == out2

    def test_with_competitor_query_sets(self) -> None:
        data = _make_queries_output()
        data["competitor_query_sets"] = [
            {
                "company_name": "HP Inc.",
                "domain": "hp.com",
                "queries": [_make_test_query(target_domain="hp.com")],
            },
        ]
        out = QueriesOutput(**data)
        assert len(out.competitor_query_sets) == 1
        assert out.competitor_query_sets[0].company_name == "HP Inc."

    def test_sub_vertical_optional(self) -> None:
        out = QueriesOutput(**_make_queries_output(sub_vertical=None))
        assert out.sub_vertical is None


# ---------------------------------------------------------------------------
# Constants tests
# ---------------------------------------------------------------------------


class TestConstants:
    """Verify schema constants are correct."""

    def test_query_types_count(self) -> None:
        assert len(QUERY_TYPES) == 8

    def test_difficulty_levels_count(self) -> None:
        assert len(DIFFICULTY_LEVELS) == 3

    def test_difficulty_map_covers_all_types(self) -> None:
        for qt in QUERY_TYPES:
            assert qt in DIFFICULTY_MAP, f"{qt} missing from DIFFICULTY_MAP"

    def test_difficulty_map_values_valid(self) -> None:
        for qt, diff in DIFFICULTY_MAP.items():
            assert diff in DIFFICULTY_LEVELS, f"{qt} has invalid difficulty {diff}"

    def test_exact_product_is_easy(self) -> None:
        assert DIFFICULTY_MAP["exact_product"] == "easy"

    def test_misspelled_is_hard(self) -> None:
        assert DIFFICULTY_MAP["misspelled"] == "hard"
