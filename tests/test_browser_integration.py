"""Integration tests for audit-browser module.

Tests the enricher, validator, and module health_check using synthetic
data that doesn't require a real browser or Gemini API.
"""

from __future__ import annotations

from prism_platform.core.types import ModuleResult, ValidationResult
from prism_platform.modules.audit_browser.enricher import BrowserEnricher
from prism_platform.modules.audit_browser.module import BrowserModule
from prism_platform.modules.audit_browser.schemas import (
    SEARCH_DIMENSIONS,
    BrowserOutput,
    CompetitorBrowserResult,
    DimensionScore,
    MobileTestResult,
    NetworkInterception,
    QueryResult,
)
from prism_platform.modules.audit_browser.validator import validate_output

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_good_output() -> BrowserOutput:
    """Build a BrowserOutput that passes all validation checks."""
    query_results = [
        QueryResult(
            query=f"test query {i}",
            query_type="exact_product",
            response_time_ms=200 + i * 50,
            result_count=10 + i,
            screenshot_path=f"/tmp/screenshot_{i:02d}.png",
            has_autocomplete=True,
            has_facets=True,
        )
        for i in range(12)
    ]
    mobile_results = [
        MobileTestResult(
            query=f"test query {i}",
            viewport="390x844",
            response_time_ms=300,
            screenshot_path=f"/tmp/mobile_{i:02d}.png",
        )
        for i in range(3)
    ]
    network_interceptions = [
        NetworkInterception(
            url="https://abc.algolia.net/1/indexes/products/query",
            method="POST",
            provider_detected="Algolia",
            is_search_api=True,
        )
    ]
    dimension_scores = [
        DimensionScore(
            dimension=dim,  # type: ignore[arg-type]
            score=7.0,
            evidence=f"Good performance observed for {dim}",
        )
        for dim in SEARCH_DIMENSIONS
    ]
    competitor_results = [
        CompetitorBrowserResult(
            company_name="HP Inc.",
            domain="hp.com",
            query_results=[
                QueryResult(
                    query="laptop",
                    query_type="exact_product",
                    response_time_ms=300,
                    result_count=20,
                )
            ],
            dimension_scores=[
                DimensionScore(
                    dimension="relevance",
                    score=6.0,
                    evidence="Decent relevance on competitor",
                )
            ],
        )
    ]

    return BrowserOutput(
        domain="dell.com",
        prospect_query_results=query_results,
        mobile_test_results=mobile_results,
        network_interceptions=network_interceptions,
        dimension_scores=dimension_scores,
        competitor_results=competitor_results,
        detected_search_provider="Algolia",
        search_bar_found=True,
        search_bar_selector='input[type="search"]',
        total_queries_executed=17,
        total_screenshots=15,
        was_blocked=False,
    )


def _make_bad_output_few_queries() -> BrowserOutput:
    """Build a BrowserOutput with fewer than 10 queries."""
    return BrowserOutput(
        domain="dell.com",
        prospect_query_results=[QueryResult(query="test", response_time_ms=200, result_count=5)],
        dimension_scores=[
            DimensionScore(
                dimension=dim,  # type: ignore[arg-type]
                score=5.0,
                evidence="Limited data",
            )
            for dim in SEARCH_DIMENSIONS
        ],
        competitor_results=[
            CompetitorBrowserResult(
                company_name="HP",
                domain="hp.com",
            )
        ],
        search_bar_found=True,
        total_queries_executed=2,
        total_screenshots=1,
    )


# ---------------------------------------------------------------------------
# Enricher tests
# ---------------------------------------------------------------------------


class TestBrowserEnricher:
    """Tests for the BrowserEnricher without a real Gemini API."""

    def test_default_scores_has_10_dimensions(self) -> None:
        enricher = BrowserEnricher()
        scores = enricher._default_scores()
        assert len(scores) == 10
        dims = {s.dimension for s in scores}
        assert dims == set(SEARCH_DIMENSIONS)

    def test_default_scores_are_zero(self) -> None:
        enricher = BrowserEnricher()
        scores = enricher._default_scores()
        for score in scores:
            assert score.score == 0.0

    async def test_enrich_with_empty_collector_output(self) -> None:
        """Enricher should produce valid output even with empty collector data."""
        enricher = BrowserEnricher()
        output, _llm_calls, _cost = await enricher.enrich(
            domain="test.com",
            collector_output={
                "prospect_query_results": [],
                "mobile_test_results": [],
                "network_interceptions": [],
                "competitor_results": [],
                "detected_search_provider": None,
                "search_bar_found": False,
                "search_bar_selector": None,
                "total_queries_executed": 0,
                "total_screenshots": 0,
                "was_blocked": False,
                "block_details": None,
            },
        )
        assert isinstance(output, BrowserOutput)
        assert output.domain == "test.com"
        assert len(output.dimension_scores) == 10

    async def test_enrich_produces_browser_output(self) -> None:
        """Enricher should return a valid BrowserOutput."""
        enricher = BrowserEnricher()
        collector_output = {
            "prospect_query_results": [
                {
                    "query": "laptop",
                    "query_type": "exact_product",
                    "response_time_ms": 250,
                    "result_count": 42,
                    "screenshot_path": None,
                    "has_autocomplete": True,
                    "has_did_you_mean": False,
                    "has_facets": True,
                    "has_zero_result_page": False,
                    "detected_search_provider": None,
                    "notes": "",
                }
            ],
            "mobile_test_results": [],
            "network_interceptions": [],
            "competitor_results": [],
            "detected_search_provider": None,
            "search_bar_found": True,
            "search_bar_selector": 'input[name="q"]',
            "total_queries_executed": 1,
            "total_screenshots": 0,
            "was_blocked": False,
            "block_details": None,
        }
        output, _llm_calls, _cost = await enricher.enrich("test.com", collector_output)
        assert isinstance(output, BrowserOutput)
        assert len(output.prospect_query_results) == 1


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------


class TestBrowserValidator:
    """Tests for the validate_output function."""

    def test_passes_with_good_data(self) -> None:
        output = _make_good_output()
        result = validate_output(output)
        assert result.passed is True
        assert result.checks_run == 9
        assert result.checks_passed == 9
        assert len(result.errors) == 0

    def test_warns_on_missing_search_provider(self) -> None:
        output = _make_good_output()
        # Override detected_search_provider to None
        output_dict = output.model_dump()
        output_dict["detected_search_provider"] = None
        output_no_provider = BrowserOutput.model_validate(output_dict)

        result = validate_output(output_no_provider)
        # Should still pass (warning only) but have a warning
        assert len(result.warnings) >= 1
        assert any("search provider" in w.lower() for w in result.warnings)

    def test_fails_with_fewer_than_10_queries(self) -> None:
        output = _make_bad_output_few_queries()
        result = validate_output(output)
        assert result.passed is False
        assert any("10" in e for e in result.errors)

    def test_fails_with_no_competitors(self) -> None:
        output_dict = _make_good_output().model_dump()
        output_dict["competitor_results"] = []
        output = BrowserOutput.model_validate(output_dict)
        result = validate_output(output)
        assert result.passed is False
        assert any("competitor" in e.lower() for e in result.errors)

    def test_fails_with_missing_dimensions(self) -> None:
        output_dict = _make_good_output().model_dump()
        output_dict["dimension_scores"] = output_dict["dimension_scores"][:5]
        output = BrowserOutput.model_validate(output_dict)
        result = validate_output(output)
        assert result.passed is False
        assert any("dimension" in e.lower() for e in result.errors)

    def test_fails_with_no_search_bar(self) -> None:
        output_dict = _make_good_output().model_dump()
        output_dict["search_bar_found"] = False
        output = BrowserOutput.model_validate(output_dict)
        result = validate_output(output)
        assert result.passed is False
        assert any("search bar" in e.lower() for e in result.errors)

    def test_warns_on_slow_response_time(self) -> None:
        output_dict = _make_good_output().model_dump()
        for qr in output_dict["prospect_query_results"]:
            qr["response_time_ms"] = 6000
        output = BrowserOutput.model_validate(output_dict)
        result = validate_output(output)
        assert any("5000" in w for w in result.warnings)

    def test_passes_with_exactly_10_queries(self) -> None:
        """Edge case: exactly 10 queries should pass."""
        output_dict = _make_good_output().model_dump()
        output_dict["prospect_query_results"] = output_dict["prospect_query_results"][:10]
        output = BrowserOutput.model_validate(output_dict)
        result = validate_output(output)
        # Should pass the queries check (>=10)
        assert not any("queries executed" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Module tests
# ---------------------------------------------------------------------------


class TestBrowserModule:
    """Tests for the BrowserModule class."""

    def test_module_class_vars(self) -> None:
        module = BrowserModule()
        assert module.name == "audit-browser"
        assert module.version == "0.1.0"
        assert module.layer == "experience"
        assert module.requires_llm is True
        assert module.timeout_seconds == 600
        assert module.max_retries == 1
        assert "intel-company" in module.dependencies
        assert "intel-queries" in module.dependencies

    async def test_health_check(self) -> None:
        module = BrowserModule()
        # health_check should return bool without crashing
        result = await module.health_check()
        assert isinstance(result, bool)

    async def test_validate_with_good_result(self) -> None:
        module = BrowserModule()
        good_output = _make_good_output()
        module_result = ModuleResult(
            module_name="audit-browser",
            module_version="0.1.0",
            status="success",
            output=good_output.model_dump(),
        )
        validation = await module.validate(module_result)
        assert isinstance(validation, ValidationResult)
        assert validation.passed is True

    async def test_validate_with_bad_output(self) -> None:
        module = BrowserModule()
        module_result = ModuleResult(
            module_name="audit-browser",
            module_version="0.1.0",
            status="failed",
            output={"not": "valid"},
        )
        validation = await module.validate(module_result)
        assert isinstance(validation, ValidationResult)
        assert validation.passed is False

    async def test_validate_with_empty_output(self) -> None:
        module = BrowserModule()
        module_result = ModuleResult(
            module_name="audit-browser",
            module_version="0.1.0",
            status="failed",
            output={},
        )
        validation = await module.validate(module_result)
        assert isinstance(validation, ValidationResult)
        assert validation.passed is False
