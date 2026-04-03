"""Contract tests for audit-browser schemas.

Validates Pydantic models accept valid data, reject invalid data,
and enforce all constraints for the browser testing module.
At least 25 tests covering all schema models.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.audit_browser.schemas import (
    SEARCH_DIMENSIONS,
    BrowserInput,
    BrowserOutput,
    CompetitorBrowserResult,
    DimensionScore,
    MobileTestResult,
    NetworkInterception,
    QueryResult,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_query_result(**overrides: object) -> dict:
    """Build a valid QueryResult dict with optional overrides."""
    base: dict = {
        "query": "laptop",
        "query_type": "exact_product",
        "response_time_ms": 250,
        "result_count": 42,
        "screenshot_path": "/tmp/screenshot_01.png",
        "has_autocomplete": True,
        "has_did_you_mean": False,
        "has_facets": True,
        "has_zero_result_page": False,
        "detected_search_provider": "Algolia",
        "notes": "",
    }
    base.update(overrides)
    return base


def _make_mobile_result(**overrides: object) -> dict:
    """Build a valid MobileTestResult dict with optional overrides."""
    base: dict = {
        "query": "laptop",
        "viewport": "390x844",
        "screenshot_path": "/tmp/mobile_01.png",
        "response_time_ms": 350,
        "notes": "Mobile search bar collapsed",
    }
    base.update(overrides)
    return base


def _make_network_interception(**overrides: object) -> dict:
    """Build a valid NetworkInterception dict with optional overrides."""
    base: dict = {
        "url": "https://abc123-dsn.algolia.net/1/indexes/products/query",
        "method": "POST",
        "provider_detected": "Algolia",
        "is_search_api": True,
    }
    base.update(overrides)
    return base


def _make_dimension_score(**overrides: object) -> dict:
    """Build a valid DimensionScore dict with optional overrides."""
    base: dict = {
        "dimension": "relevance",
        "score": 8.5,
        "evidence": "Results were highly relevant to all test queries",
        "screenshot_reference": "/tmp/screenshot_01.png",
    }
    base.update(overrides)
    return base


def _make_competitor_result(**overrides: object) -> dict:
    """Build a valid CompetitorBrowserResult dict with optional overrides."""
    base: dict = {
        "company_name": "HP Inc.",
        "domain": "hp.com",
        "query_results": [_make_query_result()],
        "dimension_scores": [_make_dimension_score()],
    }
    base.update(overrides)
    return base


def _make_full_output(**overrides: object) -> dict:
    """Build a valid BrowserOutput dict with optional overrides."""
    base: dict = {
        "domain": "dell.com",
        "prospect_query_results": [_make_query_result()],
        "mobile_test_results": [_make_mobile_result()],
        "network_interceptions": [_make_network_interception()],
        "dimension_scores": [_make_dimension_score(dimension=dim) for dim in SEARCH_DIMENSIONS],
        "competitor_results": [_make_competitor_result()],
        "detected_search_provider": "Algolia",
        "search_bar_found": True,
        "search_bar_selector": 'input[type="search"]',
        "total_queries_executed": 16,
        "total_screenshots": 20,
        "was_blocked": False,
        "block_details": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# BrowserInput
# ---------------------------------------------------------------------------


class TestBrowserInput:
    """Tests for the BrowserInput model."""

    def test_valid_input(self) -> None:
        inp = BrowserInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            BrowserInput(domain="dell.com", extra_field="nope")  # type: ignore[call-arg]

    def test_missing_domain_raises(self) -> None:
        with pytest.raises(ValidationError):
            BrowserInput()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# QueryResult
# ---------------------------------------------------------------------------


class TestQueryResult:
    """Tests for the QueryResult model."""

    def test_valid_query_result(self) -> None:
        qr = QueryResult.model_validate(_make_query_result())
        assert qr.query == "laptop"
        assert qr.response_time_ms == 250
        assert qr.has_autocomplete is True
        assert qr.detected_search_provider == "Algolia"

    def test_defaults(self) -> None:
        qr = QueryResult(query="test")
        assert qr.query_type == "unknown"
        assert qr.response_time_ms == 0
        assert qr.result_count == 0
        assert qr.screenshot_path is None
        assert qr.has_autocomplete is False
        assert qr.has_did_you_mean is False
        assert qr.has_facets is False
        assert qr.has_zero_result_page is False
        assert qr.detected_search_provider is None
        assert qr.notes == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            QueryResult.model_validate({**_make_query_result(), "secret": "no"})

    def test_none_screenshot_path(self) -> None:
        qr = QueryResult.model_validate(_make_query_result(screenshot_path=None))
        assert qr.screenshot_path is None

    def test_none_detected_provider(self) -> None:
        qr = QueryResult.model_validate(_make_query_result(detected_search_provider=None))
        assert qr.detected_search_provider is None


# ---------------------------------------------------------------------------
# MobileTestResult
# ---------------------------------------------------------------------------


class TestMobileTestResult:
    """Tests for the MobileTestResult model."""

    def test_valid_mobile_result(self) -> None:
        mr = MobileTestResult.model_validate(_make_mobile_result())
        assert mr.query == "laptop"
        assert mr.viewport == "390x844"
        assert mr.response_time_ms == 350

    def test_defaults(self) -> None:
        mr = MobileTestResult(query="test")
        assert mr.viewport == "390x844"
        assert mr.screenshot_path is None
        assert mr.response_time_ms == 0
        assert mr.notes == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            MobileTestResult.model_validate({**_make_mobile_result(), "device": "iphone"})


# ---------------------------------------------------------------------------
# NetworkInterception
# ---------------------------------------------------------------------------


class TestNetworkInterception:
    """Tests for the NetworkInterception model."""

    def test_valid_interception(self) -> None:
        ni = NetworkInterception.model_validate(_make_network_interception())
        assert ni.url.startswith("https://")
        assert ni.provider_detected == "Algolia"
        assert ni.is_search_api is True

    def test_defaults(self) -> None:
        ni = NetworkInterception(url="https://example.com/api")
        assert ni.method == "GET"
        assert ni.provider_detected is None
        assert ni.is_search_api is False

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            NetworkInterception.model_validate({**_make_network_interception(), "headers": {}})


# ---------------------------------------------------------------------------
# DimensionScore
# ---------------------------------------------------------------------------


class TestDimensionScore:
    """Tests for the DimensionScore model."""

    def test_valid_score(self) -> None:
        ds = DimensionScore.model_validate(_make_dimension_score())
        assert ds.dimension == "relevance"
        assert ds.score == 8.5
        assert len(ds.evidence) > 0

    @pytest.mark.parametrize("dimension", SEARCH_DIMENSIONS)
    def test_all_dimensions_valid(self, dimension: str) -> None:
        ds = DimensionScore.model_validate(_make_dimension_score(dimension=dimension))
        assert ds.dimension == dimension

    def test_invalid_dimension_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionScore.model_validate(_make_dimension_score(dimension="invalid_dimension"))

    def test_score_at_minimum(self) -> None:
        ds = DimensionScore.model_validate(_make_dimension_score(score=0.0))
        assert ds.score == 0.0

    def test_score_at_maximum(self) -> None:
        ds = DimensionScore.model_validate(_make_dimension_score(score=10.0))
        assert ds.score == 10.0

    def test_score_below_minimum_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionScore.model_validate(_make_dimension_score(score=-0.1))

    def test_score_above_maximum_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionScore.model_validate(_make_dimension_score(score=10.1))

    def test_screenshot_reference_none(self) -> None:
        ds = DimensionScore.model_validate(_make_dimension_score(screenshot_reference=None))
        assert ds.screenshot_reference is None

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            DimensionScore.model_validate({**_make_dimension_score(), "weight": 1.5})


# ---------------------------------------------------------------------------
# CompetitorBrowserResult
# ---------------------------------------------------------------------------


class TestCompetitorBrowserResult:
    """Tests for the CompetitorBrowserResult model."""

    def test_valid_competitor_result(self) -> None:
        cr = CompetitorBrowserResult.model_validate(_make_competitor_result())
        assert cr.company_name == "HP Inc."
        assert cr.domain == "hp.com"
        assert len(cr.query_results) == 1
        assert len(cr.dimension_scores) == 1

    def test_empty_lists(self) -> None:
        cr = CompetitorBrowserResult(
            company_name="Test Corp",
            domain="test.com",
        )
        assert cr.query_results == []
        assert cr.dimension_scores == []

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CompetitorBrowserResult.model_validate({**_make_competitor_result(), "rank": 1})


# ---------------------------------------------------------------------------
# BrowserOutput
# ---------------------------------------------------------------------------


class TestBrowserOutput:
    """Tests for the BrowserOutput model."""

    def test_valid_full_output(self) -> None:
        output = BrowserOutput.model_validate(_make_full_output())
        assert output.domain == "dell.com"
        assert output.search_bar_found is True
        assert output.detected_search_provider == "Algolia"
        assert len(output.dimension_scores) == 10
        assert len(output.competitor_results) == 1
        assert output.total_queries_executed == 16
        assert output.was_blocked is False

    def test_minimal_output(self) -> None:
        output = BrowserOutput(domain="test.com")
        assert output.prospect_query_results == []
        assert output.mobile_test_results == []
        assert output.network_interceptions == []
        assert output.dimension_scores == []
        assert output.competitor_results == []
        assert output.detected_search_provider is None
        assert output.search_bar_found is False
        assert output.search_bar_selector is None
        assert output.total_queries_executed == 0
        assert output.total_screenshots == 0
        assert output.was_blocked is False
        assert output.block_details is None

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            BrowserOutput.model_validate({**_make_full_output(), "secret": "no"})

    def test_blocked_output(self) -> None:
        output = BrowserOutput.model_validate(
            _make_full_output(
                was_blocked=True,
                block_details="Cloudflare WAF challenge detected",
            )
        )
        assert output.was_blocked is True
        assert output.block_details == "Cloudflare WAF challenge detected"

    def test_nested_model_validation(self) -> None:
        """Ensure nested models are validated."""
        bad_data = _make_full_output()
        bad_data["dimension_scores"] = [{"dimension": "INVALID", "score": 5.0, "evidence": "x"}]
        with pytest.raises(ValidationError):
            BrowserOutput.model_validate(bad_data)

    def test_all_10_dimensions_in_output(self) -> None:
        output = BrowserOutput.model_validate(_make_full_output())
        scored_dims = {ds.dimension for ds in output.dimension_scores}
        assert scored_dims == set(SEARCH_DIMENSIONS)

    def test_none_optionals(self) -> None:
        output = BrowserOutput.model_validate(
            _make_full_output(
                detected_search_provider=None,
                search_bar_selector=None,
                block_details=None,
            )
        )
        assert output.detected_search_provider is None
        assert output.search_bar_selector is None
        assert output.block_details is None

    def test_empty_lists_valid(self) -> None:
        output = BrowserOutput.model_validate(
            _make_full_output(
                prospect_query_results=[],
                mobile_test_results=[],
                network_interceptions=[],
                dimension_scores=[],
                competitor_results=[],
            )
        )
        assert output.prospect_query_results == []
        assert output.dimension_scores == []
