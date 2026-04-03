"""Tests for intel-queries collector and validator.

Tests the context builder and validation logic. No external API calls.
"""

from __future__ import annotations

from prism_platform.core.types import EvidenceTier, Source
from prism_platform.modules.intel_queries.collector import QueriesCollector
from prism_platform.modules.intel_queries.schemas import (
    DIFFICULTY_MAP,
    QUERY_TYPES,
    QueriesOutput,
    QueryDifficultyDistribution,
    TestQuery,
)
from prism_platform.modules.intel_queries.validator import validate_output

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_test_query(**overrides: object) -> TestQuery:
    """Build a valid TestQuery with optional overrides."""
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
    return TestQuery(**base)


def _make_full_query_set() -> list[TestQuery]:
    """Build a complete set of 16 queries (2 per type)."""
    queries = []
    for qt in QUERY_TYPES:
        for i in range(2):
            queries.append(
                _make_test_query(
                    query=f"test query {qt} {i}",
                    query_type=qt,
                    difficulty=DIFFICULTY_MAP.get(qt, "medium"),
                )
            )
    return queries


def _make_valid_output() -> QueriesOutput:
    """Build a valid QueriesOutput for validator tests."""
    queries = _make_full_query_set()
    dist = QueryDifficultyDistribution(
        easy_count=sum(1 for q in queries if q.difficulty == "easy"),
        medium_count=sum(1 for q in queries if q.difficulty == "medium"),
        hard_count=sum(1 for q in queries if q.difficulty == "hard"),
    )
    return QueriesOutput(
        domain="dell.com",
        industry="Enterprise Technology",
        sub_vertical="Consumer Electronics",
        prospect_queries=queries,
        competitor_query_sets=[],
        difficulty_distribution=dist,
        query_count=len(queries),
        types_covered=list(QUERY_TYPES),
        generation_notes="Test data",
    )


def _make_source() -> Source:
    """Build a valid Source for validator tests."""
    return Source(
        field="prospect_queries",
        value="Test source",
        tier=EvidenceTier.ESTIMATE,
        source_label="Test",
        method="llm_extraction",
    )


# ---------------------------------------------------------------------------
# QueriesCollector tests
# ---------------------------------------------------------------------------


class TestQueriesCollector:
    """Tests for QueriesCollector.collect_context (no DB needed)."""

    def test_collect_context_basic(self) -> None:
        collector = QueriesCollector()
        ctx = collector.collect_context(
            domain="dell.com",
            company_name="Dell Technologies",
            industry="Enterprise Technology",
            sub_vertical="Consumer Electronics",
            product_categories=["Laptops", "Desktops", "Monitors"],
            competitor_domains=[
                {"company_name": "HP Inc.", "domain": "hp.com"},
                {"company_name": "Lenovo", "domain": "lenovo.com"},
            ],
        )

        assert ctx["domain"] == "dell.com"
        assert ctx["company_name"] == "Dell Technologies"
        assert ctx["industry"] == "Enterprise Technology"
        assert ctx["sub_vertical"] == "Consumer Electronics"
        assert len(ctx["product_categories"]) == 3
        assert len(ctx["competitor_domains"]) == 2

    def test_collect_context_empty_categories(self) -> None:
        collector = QueriesCollector()
        ctx = collector.collect_context(
            domain="dell.com",
            company_name="Dell Technologies",
            industry="Enterprise Technology",
            sub_vertical=None,
            product_categories=[],
            competitor_domains=[],
        )

        assert ctx["product_categories"] == []
        assert ctx["competitor_domains"] == []
        assert ctx["sub_vertical"] is None

    def test_collect_context_preserves_all_fields(self) -> None:
        collector = QueriesCollector()
        categories = ["A", "B", "C", "D", "E"]
        competitors = [{"company_name": f"Comp{i}", "domain": f"comp{i}.com"} for i in range(5)]

        ctx = collector.collect_context(
            domain="test.com",
            company_name="Test Corp",
            industry="Tech",
            sub_vertical="SaaS",
            product_categories=categories,
            competitor_domains=competitors,
        )

        assert len(ctx["product_categories"]) == 5
        assert len(ctx["competitor_domains"]) == 5

    def test_extract_context_with_string_competitors(self) -> None:
        """Test _extract_context handles string competitor domains (as stored by intel-company)."""
        ctx = QueriesCollector._extract_context(
            domain="dell.com",
            company_name="Dell Technologies",
            intelligence={
                "common_name": "Dell",
                "industry": "Enterprise Technology",
                "sub_vertical": "Consumer Electronics",
                "product_categories": ["Laptops"],
                "competitor_domains": ["hp.com", "lenovo.com"],
            },
        )

        assert ctx["company_name"] == "Dell"
        assert ctx["industry"] == "Enterprise Technology"
        assert len(ctx["competitor_domains"]) == 2
        assert ctx["competitor_domains"][0]["domain"] == "hp.com"

    def test_extract_context_with_dict_competitors(self) -> None:
        """Test _extract_context handles dict competitor domains."""
        ctx = QueriesCollector._extract_context(
            domain="dell.com",
            company_name="Dell Technologies",
            intelligence={
                "industry": "Enterprise Technology",
                "competitor_domains": [
                    {"company_name": "HP Inc.", "domain": "hp.com"},
                ],
            },
        )

        assert ctx["competitor_domains"][0]["company_name"] == "HP Inc."
        assert ctx["competitor_domains"][0]["domain"] == "hp.com"

    def test_extract_context_empty_intelligence(self) -> None:
        """Test _extract_context handles empty intelligence dict."""
        ctx = QueriesCollector._extract_context(
            domain="dell.com",
            company_name="Dell Technologies",
            intelligence={},
        )

        assert ctx["domain"] == "dell.com"
        assert ctx["company_name"] == "Dell Technologies"
        assert ctx["industry"] == ""
        assert ctx["sub_vertical"] is None
        assert ctx["product_categories"] == []
        assert ctx["competitor_domains"] == []

    def test_extract_context_uses_common_name(self) -> None:
        """Test that common_name is preferred over company_name."""
        ctx = QueriesCollector._extract_context(
            domain="dell.com",
            company_name="Dell Technologies Inc.",
            intelligence={"common_name": "Dell"},
        )
        assert ctx["company_name"] == "Dell"


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------


class TestQueriesValidator:
    """Tests for validate_output function."""

    def test_valid_output_passes(self) -> None:
        output = _make_valid_output()
        sources = [_make_source()]
        result = validate_output(output, sources)

        assert result.passed is True
        assert result.checks_run == 9
        assert result.checks_passed == 9
        assert result.errors == []

    def test_empty_domain_fails(self) -> None:
        output = _make_valid_output()
        output_dict = output.model_dump()
        output_dict["domain"] = ""
        output = QueriesOutput.model_validate(output_dict)

        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("domain is empty" in e for e in result.errors)

    def test_too_few_queries_fails(self) -> None:
        output = _make_valid_output()
        output_dict = output.model_dump()
        output_dict["prospect_queries"] = output_dict["prospect_queries"][:5]
        output_dict["query_count"] = 5
        output = QueriesOutput.model_validate(output_dict)

        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("Only 5 prospect queries" in e for e in result.errors)

    def test_missing_query_types_fails(self) -> None:
        # Only include exact_product queries (missing 7 types)
        queries = [
            _make_test_query(query=f"query {i}", query_type="exact_product") for i in range(16)
        ]
        output = QueriesOutput(
            domain="dell.com",
            prospect_queries=queries,
            difficulty_distribution=QueryDifficultyDistribution(easy_count=16),
            query_count=16,
            types_covered=["exact_product"],
        )

        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("Missing query types" in e for e in result.errors)

    def test_empty_query_string_fails(self) -> None:
        output = _make_valid_output()
        output_dict = output.model_dump()
        output_dict["prospect_queries"][0]["query"] = ""
        output = QueriesOutput.model_validate(output_dict)

        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("empty query strings" in e for e in result.errors)

    def test_empty_expected_behavior_fails(self) -> None:
        output = _make_valid_output()
        output_dict = output.model_dump()
        output_dict["prospect_queries"][0]["expected_behavior"] = "  "
        output = QueriesOutput.model_validate(output_dict)

        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("empty expected_behavior" in e for e in result.errors)

    def test_difficulty_distribution_mismatch_fails(self) -> None:
        output = _make_valid_output()
        output_dict = output.model_dump()
        # Wrong counts
        output_dict["difficulty_distribution"] = {
            "easy_count": 99,
            "medium_count": 0,
            "hard_count": 0,
        }
        output = QueriesOutput.model_validate(output_dict)

        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("difficulty_distribution mismatch" in e for e in result.errors)

    def test_query_count_mismatch_fails(self) -> None:
        output = _make_valid_output()
        output_dict = output.model_dump()
        output_dict["query_count"] = 999
        output = QueriesOutput.model_validate(output_dict)

        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("query_count mismatch" in e for e in result.errors)

    def test_types_covered_incomplete_fails(self) -> None:
        output = _make_valid_output()
        output_dict = output.model_dump()
        output_dict["types_covered"] = ["exact_product"]
        output = QueriesOutput.model_validate(output_dict)

        result = validate_output(output, [_make_source()])
        assert result.passed is False
        assert any("types_covered" in e for e in result.errors)

    def test_no_sources_fails(self) -> None:
        output = _make_valid_output()
        result = validate_output(output, [])

        assert result.passed is False
        assert any("No source provenance" in e for e in result.errors)

    def test_none_difficulty_distribution_warns(self) -> None:
        output = _make_valid_output()
        output_dict = output.model_dump()
        output_dict["difficulty_distribution"] = None
        output = QueriesOutput.model_validate(output_dict)

        result = validate_output(output, [_make_source()])
        assert any("difficulty_distribution is None" in w for w in result.warnings)

    def test_14_queries_passes(self) -> None:
        """Exactly 14 queries should pass (minimum threshold)."""
        # We need all 8 types covered in 14 queries -- first 14 from 16 covers 7 types
        # Let's build carefully: 2 of each first 7 types = 14
        queries = []
        for qt in QUERY_TYPES[:7]:
            for i in range(2):
                queries.append(
                    _make_test_query(
                        query=f"q {qt} {i}",
                        query_type=qt,
                        difficulty=DIFFICULTY_MAP[qt],
                    )
                )
        # This only has 7 types, so it will fail check 3 but pass check 2
        # For a proper 14-query pass, add all 8 types
        queries = []
        for qt in QUERY_TYPES:
            queries.append(
                _make_test_query(
                    query=f"q {qt} 0",
                    query_type=qt,
                    difficulty=DIFFICULTY_MAP[qt],
                )
            )
        # 8 queries so far, add 6 more
        for qt in QUERY_TYPES[:6]:
            queries.append(
                _make_test_query(
                    query=f"q {qt} extra",
                    query_type=qt,
                    difficulty=DIFFICULTY_MAP[qt],
                )
            )

        dist = QueryDifficultyDistribution(
            easy_count=sum(1 for q in queries if q.difficulty == "easy"),
            medium_count=sum(1 for q in queries if q.difficulty == "medium"),
            hard_count=sum(1 for q in queries if q.difficulty == "hard"),
        )
        output = QueriesOutput(
            domain="dell.com",
            prospect_queries=queries,
            difficulty_distribution=dist,
            query_count=len(queries),
            types_covered=list(QUERY_TYPES),
        )
        result = validate_output(output, [_make_source()])
        assert result.passed is True
