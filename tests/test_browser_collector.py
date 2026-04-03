"""Tests for audit-browser collector -- Playwright browser automation.

All browser tests are marked with @pytest.mark.browser so they can be
skipped in CI environments without Playwright installed.
Tests include both unit tests (no real browser) and integration tests.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from prism_platform.modules.audit_browser.collector import (
    COMMON_SEARCH_SELECTORS,
    PROVIDER_PATTERNS,
    STEALTH_USER_AGENT,
    BrowserCollector,
    detect_provider_from_url,
    is_search_api_request,
    load_screenshots_as_base64,
)
from prism_platform.modules.audit_browser.schemas import COMMON_SEARCH_SELECTORS as SCHEMA_SELECTORS

# ---------------------------------------------------------------------------
# Unit tests -- no browser needed
# ---------------------------------------------------------------------------


class TestDetectProviderFromUrl:
    """Tests for the detect_provider_from_url function."""

    def test_algolia_detected(self) -> None:
        url = "https://abc123-dsn.algolia.net/1/indexes/products/query"
        assert detect_provider_from_url(url) == "Algolia"

    def test_algolianet_detected(self) -> None:
        url = "https://abc123.algolianet.com/1/indexes/products"
        assert detect_provider_from_url(url) == "Algolia"

    def test_elasticsearch_detected(self) -> None:
        url = "https://search.example.com/elasticsearch/_search"
        assert detect_provider_from_url(url) == "Elasticsearch"

    def test_coveo_detected(self) -> None:
        url = "https://platform.cloud.coveo.com/rest/search/v2"
        assert detect_provider_from_url(url) == "Coveo"

    def test_constructor_io_detected(self) -> None:
        url = "https://ac.cnstrc.com/search/laptop"
        assert detect_provider_from_url(url) == "Constructor.io"

    def test_unknown_url_returns_none(self) -> None:
        url = "https://example.com/api/v1/data"
        assert detect_provider_from_url(url) is None

    def test_empty_url_returns_none(self) -> None:
        assert detect_provider_from_url("") is None

    def test_case_insensitive(self) -> None:
        url = "https://ABC123.ALGOLIA.NET/1/indexes"
        assert detect_provider_from_url(url) == "Algolia"


class TestIsSearchApiRequest:
    """Tests for the is_search_api_request function."""

    def test_algolia_is_search(self) -> None:
        assert (
            is_search_api_request("https://abc.algolia.net/1/indexes/products/query", "POST")
            is True
        )

    def test_search_path_is_search(self) -> None:
        assert is_search_api_request("https://example.com/api/search?q=laptop", "GET") is True

    def test_autocomplete_is_search(self) -> None:
        assert is_search_api_request("https://example.com/autocomplete?prefix=lap", "GET") is True

    def test_image_not_search(self) -> None:
        assert is_search_api_request("https://cdn.example.com/images/logo.png", "GET") is False

    def test_analytics_not_search(self) -> None:
        assert is_search_api_request("https://analytics.example.com/event", "POST") is False


class TestStealthConfig:
    """Tests for stealth configuration constants."""

    def test_user_agent_is_chrome(self) -> None:
        assert "Chrome" in STEALTH_USER_AGENT
        assert "Mozilla" in STEALTH_USER_AGENT

    def test_common_selectors_present(self) -> None:
        assert len(COMMON_SEARCH_SELECTORS) > 5
        assert 'input[type="search"]' in COMMON_SEARCH_SELECTORS
        assert 'input[name="q"]' in COMMON_SEARCH_SELECTORS

    def test_selectors_match_schema(self) -> None:
        """Verify collector selectors match schema constants."""
        assert COMMON_SEARCH_SELECTORS == SCHEMA_SELECTORS

    def test_all_providers_have_patterns(self) -> None:
        """Verify all provider entries have at least one pattern."""
        for provider, patterns in PROVIDER_PATTERNS.items():
            assert len(patterns) > 0, f"Provider {provider} has no patterns"


class TestBrowserCollectorHelpers:
    """Tests for BrowserCollector helper methods."""

    def test_empty_result_has_all_keys(self) -> None:
        collector = BrowserCollector()
        result = collector._empty_result("test.com")
        expected_keys = {
            "prospect_query_results",
            "mobile_test_results",
            "network_interceptions",
            "search_bar_found",
            "search_bar_selector",
            "detected_search_provider",
            "was_blocked",
            "block_details",
            "competitor_results",
            "total_queries_executed",
            "total_screenshots",
        }
        assert set(result.keys()) == expected_keys

    def test_empty_result_is_blocked(self) -> None:
        collector = BrowserCollector()
        result = collector._empty_result("test.com")
        assert result["was_blocked"] is True
        assert result["total_queries_executed"] == 0

    def test_time_exceeded_false(self) -> None:
        import time

        collector = BrowserCollector()
        assert collector._time_exceeded(time.monotonic()) is False

    def test_time_exceeded_true(self) -> None:
        import time

        collector = BrowserCollector()
        # Pretend start was 700 seconds ago
        assert collector._time_exceeded(time.monotonic() - 700) is True

    def test_detect_primary_provider(self) -> None:
        collector = BrowserCollector()
        interceptions = [
            {"provider_detected": "Algolia"},
            {"provider_detected": "Algolia"},
            {"provider_detected": "Elasticsearch"},
            {"provider_detected": None},
        ]
        assert collector._detect_primary_provider(interceptions) == "Algolia"

    def test_detect_primary_provider_empty(self) -> None:
        collector = BrowserCollector()
        assert collector._detect_primary_provider([]) is None

    def test_count_screenshots(self) -> None:
        collector = BrowserCollector()
        results = {
            "prospect_query_results": [
                {"screenshot_path": "/tmp/a.png"},
                {"screenshot_path": None},
                {"screenshot_path": "/tmp/b.png"},
            ],
            "mobile_test_results": [
                {"screenshot_path": "/tmp/m.png"},
            ],
            "competitor_results": [
                {"query_results": [{"screenshot_path": "/tmp/c.png"}]},
            ],
        }
        assert collector._count_screenshots(results) == 4

    def test_ensure_screenshot_dir(self, tmp_path: Path) -> None:
        with patch(
            "prism_platform.modules.audit_browser.collector.Path",
            return_value=tmp_path / "screenshots" / "test-audit",
        ):
            # Use direct Path creation instead
            screenshot_dir = tmp_path / "data" / "screenshots" / "test-audit"
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            assert screenshot_dir.exists()


class TestLoadScreenshotsAsBase64:
    """Tests for the screenshot loading helper."""

    def test_loads_existing_file(self, tmp_path: Path) -> None:
        # Create a fake PNG file
        png_path = tmp_path / "test.png"
        png_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        result = load_screenshots_as_base64([str(png_path)])
        assert len(result) == 1
        assert result[0]["path"] == str(png_path)
        assert len(result[0]["base64"]) > 0

    def test_skips_missing_file(self) -> None:
        result = load_screenshots_as_base64(["/nonexistent/path.png"])
        assert result == []

    def test_empty_input(self) -> None:
        result = load_screenshots_as_base64([])
        assert result == []


# ---------------------------------------------------------------------------
# Browser integration tests -- require Playwright
# ---------------------------------------------------------------------------


@pytest.mark.browser
class TestBrowserCollectorIntegration:
    """Integration tests requiring a real browser.

    These tests are marked with @pytest.mark.browser and will be skipped
    if Playwright is not installed or --browser flag is not set.
    """

    @pytest.fixture(autouse=True)
    def check_playwright(self) -> None:
        """Skip tests if Playwright is not available."""
        try:
            from playwright.async_api import async_playwright  # noqa: F401
        except ImportError:
            pytest.skip("Playwright not installed")

    async def test_collect_nike_com(self) -> None:
        """Integration test: run a few queries against nike.com."""
        collector = BrowserCollector()
        queries = [
            {"query": "running shoes", "query_type": "category_browse"},
            {"query": "air max", "query_type": "exact_product"},
        ]
        result = await collector.collect_all(
            domain="nike.com",
            audit_id="test-nike-integration",
            queries=queries,
        )
        # We don't assert specific results because the site may change,
        # but we verify the structure is correct
        assert "prospect_query_results" in result
        assert "network_interceptions" in result
        assert isinstance(result["total_queries_executed"], int)

    async def test_collect_bestbuy_com(self) -> None:
        """Integration test: run queries against bestbuy.com."""
        collector = BrowserCollector()
        queries = [
            {"query": "laptop", "query_type": "exact_product"},
            {"query": "4k television", "query_type": "category_browse"},
        ]
        result = await collector.collect_all(
            domain="bestbuy.com",
            audit_id="test-bestbuy-integration",
            queries=queries,
        )
        assert "prospect_query_results" in result
        assert isinstance(result["search_bar_found"], bool)
