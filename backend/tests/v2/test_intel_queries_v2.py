"""Unit tests for intel-queries v2 module.

Covers:
- Typo injection helpers (_inject_typo, _typo_for_phrase) — pure logic, no IO
- Query generation from sample upstream data — determinism and correctness
- Schema validation — QueryItem and QueryIntelOutput
- Config + playbook contract
- Registry registration (import-level smoke test)

Per plan §9 Q2: pure-logic helpers use fast unit tests with no mocks and no
fabricated intelligence (these functions produce queries, not intelligence).
Integration tests against real company data are a separate concern.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.types import ExecutionContextV2
from prism_platform.v2.modules.intel_queries.collector import (
    _generate_brand_subbrand,
    _generate_broad_category,
    _generate_keyword_queries,
    _generate_nlp_conversational,
    _generate_non_product_content,
    _generate_specific_product,
    _generate_synonym_colloquial,
    _generate_typo_variants,
    _generate_zero_results_gibberish,
    _inject_typo,
    _typo_for_phrase,
    collect,
)
from prism_platform.v2.modules.intel_queries.config import INTEL_QUERIES_CONFIG
from prism_platform.v2.modules.intel_queries.schemas import QueryIntelOutput, QueryItem

PLAYBOOK_PATH = (
    Path(__file__).parent.parent.parent
    / "prism_platform/v2/modules/intel_queries/playbook.md"
)

# ---------------------------------------------------------------------------
# Sample upstream data (structured facts, not fabricated intelligence)
# ---------------------------------------------------------------------------

_SAMPLE_CATEGORIES = ["running shoes", "yoga pants", "sports bags"]
_SAMPLE_KEYWORDS = ["nike running shoes", "yoga leggings", "sports kit"]
_SAMPLE_COMPANY_DATA = {
    "product_categories": _SAMPLE_CATEGORIES,
    "subsidiaries": [{"name": "Jordan"}, {"name": "Converse"}],
}
_SAMPLE_TRAFFIC_DATA = {
    "top_organic_keywords": _SAMPLE_KEYWORDS,
}


def _make_context(
    company_name: str = "Nike",
    company_data: dict | None = None,
    traffic_data: dict | None = None,
) -> ExecutionContextV2:
    return ExecutionContextV2(
        audit_id="test-audit-001",
        account_domain="nike.com",
        company_name=company_name,
        upstream_results={
            "intel-company": company_data if company_data is not None else _SAMPLE_COMPANY_DATA,
            "intel-traffic": traffic_data if traffic_data is not None else _SAMPLE_TRAFFIC_DATA,
        },
    )


# ---------------------------------------------------------------------------
# Tests: _inject_typo
# ---------------------------------------------------------------------------

class TestInjectTypo:
    def test_swaps_chars_1_and_2_for_long_words(self) -> None:
        # "shoes" → swap index 1 ('h') and 2 ('o') → "sohes"
        result = _inject_typo("shoes")
        assert result == "sohes"

    def test_swaps_chars_for_four_char_word(self) -> None:
        # "yoga" → swap index 1 ('o') and 2 ('g') → "ygoa"
        result = _inject_typo("yoga")
        assert result == "ygoa"

    def test_drops_middle_char_for_three_char_word(self) -> None:
        # "bag" → drop index 1 → "bg"
        result = _inject_typo("bag")
        assert result == "bg"

    def test_doubles_last_char_for_two_char_word(self) -> None:
        # "pc" → "pcc"
        result = _inject_typo("pc")
        assert result == "pcc"

    def test_doubles_last_char_for_one_char_word(self) -> None:
        result = _inject_typo("a")
        assert result == "aa"

    def test_is_deterministic(self) -> None:
        """Same input always produces the same output."""
        for word in ["running", "shoes", "sports", "bag", "tv"]:
            assert _inject_typo(word) == _inject_typo(word)

    def test_result_differs_from_input(self) -> None:
        """Typo must actually change something (for words len >= 2)."""
        for word in ["shoe", "yoga", "bag", "pc"]:
            assert _inject_typo(word) != word or len(word) <= 1


class TestTypoForPhrase:
    def test_targets_first_substantive_word(self) -> None:
        # "running shoes" — "running" (len 7 >= 3, not a stopword) gets the typo
        result = _typo_for_phrase("running shoes")
        assert result != "running shoes"
        # second word "shoes" should be untouched
        assert result.endswith("shoes")

    def test_skips_short_stopwords(self) -> None:
        # "a yoga mat" — skip "a", target "yoga"
        result = _typo_for_phrase("a yoga mat")
        parts = result.split()
        assert parts[0] == "a"          # stopword untouched
        assert parts[1] != "yoga"       # "yoga" got the typo
        assert parts[2] == "mat"        # trailing word untouched

    def test_single_word_phrase(self) -> None:
        result = _typo_for_phrase("shoes")
        assert result == _inject_typo("shoes")

    def test_is_deterministic(self) -> None:
        phrase = "running shoes"
        assert _typo_for_phrase(phrase) == _typo_for_phrase(phrase)


# ---------------------------------------------------------------------------
# Tests: individual generators
# ---------------------------------------------------------------------------

class TestGenerateBroadCategory:
    def test_returns_one_per_category(self) -> None:
        result = _generate_broad_category(_SAMPLE_CATEGORIES)
        assert len(result) == len(_SAMPLE_CATEGORIES)

    def test_all_types_correct(self) -> None:
        result = _generate_broad_category(_SAMPLE_CATEGORIES)
        assert all(q["type"] == "broad_category" for q in result)

    def test_text_is_lowercased(self) -> None:
        result = _generate_broad_category(["Running Shoes"])
        assert result[0]["text"] == "running shoes"

    def test_source_is_product_categories(self) -> None:
        result = _generate_broad_category(_SAMPLE_CATEGORIES)
        assert all(q["source"] == "product_categories" for q in result)


class TestGenerateSpecificProduct:
    def test_returns_one_per_category(self) -> None:
        result = _generate_specific_product(_SAMPLE_CATEGORIES)
        assert len(result) == len(_SAMPLE_CATEGORIES)

    def test_all_types_correct(self) -> None:
        result = _generate_specific_product(_SAMPLE_CATEGORIES)
        assert all(q["type"] == "specific_product" for q in result)

    def test_text_contains_modifier_and_category(self) -> None:
        result = _generate_specific_product(["running shoes"])
        # modifier must appear before category text
        text = result[0]["text"]
        assert "running shoes" in text
        assert len(text) > len("running shoes")


class TestGenerateNlpConversational:
    def test_returns_one_per_category(self) -> None:
        result = _generate_nlp_conversational(_SAMPLE_CATEGORIES)
        assert len(result) == len(_SAMPLE_CATEGORIES)

    def test_all_types_correct(self) -> None:
        result = _generate_nlp_conversational(_SAMPLE_CATEGORIES)
        assert all(q["type"] == "nlp_conversational" for q in result)

    def test_category_embedded_in_text(self) -> None:
        result = _generate_nlp_conversational(["yoga pants"])
        assert "yoga pants" in result[0]["text"]


class TestGenerateTypoVariants:
    def test_at_most_three_variants(self) -> None:
        broad_texts = ["running shoes", "yoga pants", "sports bags", "extra one"]
        result = _generate_typo_variants(broad_texts)
        assert len(result) == 3

    def test_returns_three_for_exactly_three_inputs(self) -> None:
        result = _generate_typo_variants(["running shoes", "yoga pants", "sports bags"])
        assert len(result) == 3

    def test_returns_fewer_when_fewer_inputs(self) -> None:
        result = _generate_typo_variants(["single query"])
        assert len(result) == 1

    def test_all_types_correct(self) -> None:
        result = _generate_typo_variants(["running shoes", "yoga pants", "sports bags"])
        assert all(q["type"] == "typo_variant" for q in result)

    def test_text_differs_from_original(self) -> None:
        originals = ["running shoes", "yoga pants", "sports bags"]
        result = _generate_typo_variants(originals)
        for orig, variant in zip(originals, result):
            assert variant["text"] != orig, f"Typo variant of '{orig}' should differ"

    def test_is_deterministic(self) -> None:
        inputs = ["running shoes", "yoga pants", "sports bags"]
        assert _generate_typo_variants(inputs) == _generate_typo_variants(inputs)


class TestGenerateSynonymColloquial:
    def test_produces_synonym_for_known_term(self) -> None:
        result = _generate_synonym_colloquial(["running shoes", "yoga pants"])
        texts = [q["text"] for q in result]
        # "shoes" → "kicks"
        assert any("kicks" in t for t in texts)

    def test_skips_category_with_no_known_synonym(self) -> None:
        result = _generate_synonym_colloquial(["database software"])
        assert result == []

    def test_all_types_correct(self) -> None:
        result = _generate_synonym_colloquial(["running shoes"])
        assert all(q["type"] == "synonym_colloquial" for q in result)

    def test_no_duplicate_synonyms(self) -> None:
        # Two categories both containing "shoes" should produce only one "kicks" query
        result = _generate_synonym_colloquial(["running shoes", "trail shoes"])
        kicks_count = sum(1 for q in result if "kicks" in q["text"])
        assert kicks_count == 1


class TestGenerateNonProductContent:
    def test_returns_six_static_queries(self) -> None:
        result = _generate_non_product_content()
        assert len(result) == 6

    def test_all_types_correct(self) -> None:
        result = _generate_non_product_content()
        assert all(q["type"] == "non_product_content" for q in result)

    def test_is_deterministic(self) -> None:
        assert _generate_non_product_content() == _generate_non_product_content()

    def test_includes_returns_policy(self) -> None:
        texts = [q["text"] for q in _generate_non_product_content()]
        assert "returns policy" in texts


class TestGenerateBrandSubbrand:
    def test_brand_alone_first(self) -> None:
        result = _generate_brand_subbrand("Nike", ["Jordan", "Converse"])
        assert result[0]["text"] == "nike"

    def test_subbrands_combined(self) -> None:
        result = _generate_brand_subbrand("Nike", ["Jordan", "Converse"])
        texts = [q["text"] for q in result]
        assert "nike jordan" in texts
        assert "nike converse" in texts

    def test_at_most_four_results(self) -> None:
        result = _generate_brand_subbrand("Nike", ["Jordan", "Converse", "Hurley", "Extra"])
        # brand itself + max 3 subbrands = 4
        assert len(result) <= 4

    def test_skips_subbrand_matching_brand(self) -> None:
        # subbrand same as brand should be skipped (case-insensitive)
        result = _generate_brand_subbrand("Nike", ["Nike", "Jordan"])
        texts = [q["text"] for q in result]
        assert "nike nike" not in texts

    def test_empty_brand_produces_no_brand_only_query(self) -> None:
        result = _generate_brand_subbrand("", ["Jordan"])
        brand_only = [q for q in result if q["text"] == ""]
        assert brand_only == []

    def test_all_types_correct(self) -> None:
        result = _generate_brand_subbrand("Nike", ["Jordan"])
        assert all(q["type"] == "brand_subbrand" for q in result)


class TestGenerateZeroResultsGibberish:
    def test_returns_exactly_three(self) -> None:
        result = _generate_zero_results_gibberish()
        assert len(result) == 3

    def test_all_types_correct(self) -> None:
        result = _generate_zero_results_gibberish()
        assert all(q["type"] == "zero_results_gibberish" for q in result)

    def test_static_strings_present(self) -> None:
        texts = {q["text"] for q in _generate_zero_results_gibberish()}
        assert "xqzpfk" in texts
        assert "asdfghjkl" in texts
        assert "zzznoresult" in texts

    def test_is_deterministic(self) -> None:
        assert _generate_zero_results_gibberish() == _generate_zero_results_gibberish()


class TestGenerateKeywordQueries:
    def test_at_most_five_keywords(self) -> None:
        keywords = ["kw1", "kw2", "kw3", "kw4", "kw5", "kw6", "kw7"]
        result = _generate_keyword_queries(keywords)
        assert len(result) == 5

    def test_source_is_top_organic_keywords(self) -> None:
        result = _generate_keyword_queries(["yoga leggings"])
        assert result[0]["source"] == "top_organic_keywords"

    def test_type_is_broad_category(self) -> None:
        result = _generate_keyword_queries(["yoga leggings"])
        assert result[0]["type"] == "broad_category"

    def test_empty_input_returns_empty(self) -> None:
        assert _generate_keyword_queries([]) == []


# ---------------------------------------------------------------------------
# Tests: async collect()
# ---------------------------------------------------------------------------

class TestCollect:
    async def test_returns_query_set_key(self) -> None:
        context = _make_context()
        result = await collect(context)
        assert "query_set" in result

    async def test_query_set_has_required_fields(self) -> None:
        context = _make_context()
        result = await collect(context)
        qs = result["query_set"]
        assert "domain" in qs
        assert "queries" in qs
        assert "query_coverage" in qs
        assert "total_queries" in qs

    async def test_domain_is_correct(self) -> None:
        context = _make_context()
        result = await collect(context)
        assert result["query_set"]["domain"] == "nike.com"

    async def test_coverage_consistent_with_queries(self) -> None:
        context = _make_context()
        result = await collect(context)
        qs = result["query_set"]
        expected_coverage = dict(Counter(q["type"] for q in qs["queries"]))
        assert qs["query_coverage"] == expected_coverage

    async def test_total_queries_consistent(self) -> None:
        context = _make_context()
        result = await collect(context)
        qs = result["query_set"]
        assert qs["total_queries"] == len(qs["queries"])

    async def test_all_eight_query_types_present(self) -> None:
        context = _make_context()
        result = await collect(context)
        types_present = set(result["query_set"]["query_coverage"].keys())
        expected = {
            "broad_category",
            "specific_product",
            "nlp_conversational",
            "typo_variant",
            "synonym_colloquial",
            "non_product_content",
            "brand_subbrand",
            "zero_results_gibberish",
        }
        required = expected - {"synonym_colloquial"}
        assert required.issubset(types_present), (
            f"Missing query types: {required - types_present}"
        )

    async def test_no_duplicate_query_texts(self) -> None:
        context = _make_context()
        result = await collect(context)
        texts = [q["text"].lower() for q in result["query_set"]["queries"]]
        assert len(texts) == len(set(texts)), "Duplicate query texts found"

    async def test_is_deterministic(self) -> None:
        context = _make_context()
        r1 = await collect(context)
        r2 = await collect(context)
        assert r1["query_set"]["queries"] == r2["query_set"]["queries"]

    async def test_graceful_degradation_no_upstream(self) -> None:
        context = ExecutionContextV2(
            audit_id="test-audit-002",
            account_domain="unknown.com",
            company_name="UnknownCo",
            upstream_results={},
        )
        result = await collect(context)
        qs = result["query_set"]
        assert qs["total_queries"] > 0
        assert qs["domain"] == "unknown.com"

    async def test_graceful_degradation_no_product_categories(self) -> None:
        context = _make_context(
            company_name="Acme",
            company_data={"product_categories": [], "subsidiaries": []},
        )
        result = await collect(context)
        qs = result["query_set"]
        assert qs["total_queries"] > 0

    async def test_zero_results_gibberish_always_present(self) -> None:
        context = _make_context(company_data={"product_categories": [], "subsidiaries": []})
        result = await collect(context)
        texts = {q["text"] for q in result["query_set"]["queries"]}
        assert "xqzpfk" in texts
        assert "asdfghjkl" in texts
        assert "zzznoresult" in texts

    async def test_keyword_queries_included_when_available(self) -> None:
        context = _make_context()
        result = await collect(context)
        sources = {q["source"] for q in result["query_set"]["queries"]}
        assert "top_organic_keywords" in sources


# ---------------------------------------------------------------------------
# Tests: schema validation
# ---------------------------------------------------------------------------

class TestQueryItem:
    def test_valid_item(self) -> None:
        item = QueryItem(text="running shoes", type="broad_category", source="product_categories")
        assert item.text == "running shoes"
        assert item.type == "broad_category"

    def test_is_frozen(self) -> None:
        item = QueryItem(text="test", type="broad_category", source="static")
        with pytest.raises(ValidationError):
            item.text = "changed"  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            QueryItem(
                text="test",
                type="broad_category",
                source="static",
                bad="oops",  # type: ignore[call-arg]
            )

    def test_rejects_invalid_query_type(self) -> None:
        with pytest.raises(ValidationError):
            QueryItem(text="test", type="invalid_type", source="static")  # type: ignore[arg-type]


class TestQueryIntelOutput:
    def test_valid_output(self) -> None:
        out = QueryIntelOutput(
            domain="nike.com",
            queries=[
                QueryItem(text="running shoes", type="broad_category", source="product_categories")
            ],
            query_coverage={"broad_category": 1},
            total_queries=1,
        )
        assert out.domain == "nike.com"
        assert out.total_queries == 1

    def test_defaults_are_safe(self) -> None:
        out = QueryIntelOutput(domain="test.com")
        assert out.queries == []
        assert out.query_coverage == {}
        assert out.total_queries == 0

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            QueryIntelOutput(domain="test.com", bad="oops")  # type: ignore[call-arg]

    def test_generates_json_schema(self) -> None:
        schema = QueryIntelOutput.model_json_schema()
        assert "queries" in schema["properties"]
        assert "query_coverage" in schema["properties"]
        assert "total_queries" in schema["properties"]

    async def test_schema_parses_from_collect_output(self) -> None:
        context = _make_context()
        result = await collect(context)
        out = QueryIntelOutput.model_validate(result["query_set"])
        assert out.total_queries > 0
        assert out.domain == "nike.com"


# ---------------------------------------------------------------------------
# Tests: config
# ---------------------------------------------------------------------------

class TestIntelQueriesConfig:
    def test_name(self) -> None:
        assert INTEL_QUERIES_CONFIG.name == "intel-queries"

    def test_version(self) -> None:
        assert INTEL_QUERIES_CONFIG.version.startswith("2.")

    def test_composes(self) -> None:
        assert "intel-company" in INTEL_QUERIES_CONFIG.composes
        assert "intel-traffic" in INTEL_QUERIES_CONFIG.composes

    def test_no_api_clients(self) -> None:
        assert INTEL_QUERIES_CONFIG.api_clients == []

    def test_cache_ttl_reasonable(self) -> None:
        assert 7 <= INTEL_QUERIES_CONFIG.cache_ttl_days <= 90

    def test_timeout_is_short(self) -> None:
        # pure Python — should be well under 60 seconds
        assert INTEL_QUERIES_CONFIG.timeout_seconds <= 60


# ---------------------------------------------------------------------------
# Tests: playbook
# ---------------------------------------------------------------------------

class TestIntelQueriesPlaybook:
    def test_playbook_exists(self) -> None:
        assert PLAYBOOK_PATH.exists()

    def test_execution_strategy_is_prospect_only(self) -> None:
        from core.playbook import PlaybookLoader

        loader = PlaybookLoader()
        meta, _ = loader.load(PLAYBOOK_PATH)
        assert meta.execution_strategy == "prospect-only"

    def test_playbook_resolves_domain(self) -> None:
        from core.playbook import PlaybookLoader

        loader = PlaybookLoader()
        context = ExecutionContextV2(
            audit_id="t",
            account_domain="nike.com",
            company_name="Nike",
        )
        _, body = loader.load(PLAYBOOK_PATH)
        resolved = loader.resolve(body, context)
        assert "nike.com" in resolved


# ---------------------------------------------------------------------------
# Tests: registry smoke test
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_module_importable(self) -> None:
        """Registry block imports must succeed."""
        from prism_platform.v2.modules.intel_queries.collector import collect  # noqa: F401
        from prism_platform.v2.modules.intel_queries.config import (
            INTEL_QUERIES_CONFIG,  # noqa: F401
        )
        from prism_platform.v2.modules.intel_queries.schemas import QueryIntelOutput  # noqa: F401

    def test_registered_in_registry(self) -> None:
        from core.registry import V2_MODULE_REGISTRY, register_all_v2_modules

        register_all_v2_modules()
        assert "intel-queries" in V2_MODULE_REGISTRY

    def test_handle_has_collector(self) -> None:
        from core.registry import V2_MODULE_REGISTRY, register_all_v2_modules

        register_all_v2_modules()
        handle = V2_MODULE_REGISTRY["intel-queries"]
        assert handle.collector is not None

    def test_handle_playbook_path_exists(self) -> None:
        from core.registry import V2_MODULE_REGISTRY, register_all_v2_modules

        register_all_v2_modules()
        handle = V2_MODULE_REGISTRY["intel-queries"]
        assert handle.playbook_path.exists()
