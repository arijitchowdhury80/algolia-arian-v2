"""Tests for prism_platform.core.domain_normalizer."""

from __future__ import annotations

import pytest

from prism_platform.core.domain_normalizer import (
    extract_domain_from_url,
    looks_like_domain,
    normalize_domain,
)


# ---------------------------------------------------------------------------
# normalize_domain — core test cases
# ---------------------------------------------------------------------------


class TestNormalizeDomain:
    """Verify domain normalization across all input variations."""

    @pytest.mark.parametrize(
        "input_str, expected",
        [
            # Full URL with path
            ("https://www.dell.com/en-us", "dell.com"),
            # HTTP + www + trailing slash
            ("http://www.jewson.co.uk/", "jewson.co.uk"),
            # www prefix only
            ("www.nike.com", "nike.com"),
            # Uppercase
            ("DELL.COM", "dell.com"),
            # Port number
            ("dell.com:443", "dell.com"),
            # Already clean
            ("dell.com", "dell.com"),
            # Company name (no dots) — return as-is
            ("Dell", "Dell"),
            # Empty string
            ("", ""),
            # Whitespace padding
            ("   dell.com   ", "dell.com"),
            # Full URL with query and fragment
            ("https://store.bestbuy.com/products?id=123#review", "store.bestbuy.com"),
            # Path without protocol
            ("dell.com/products", "dell.com"),
            # HTTPS without www
            ("https://dell.com", "dell.com"),
            # HTTP without www
            ("http://dell.com", "dell.com"),
            # Trailing slash only
            ("dell.com/", "dell.com"),
            # Port 8080
            ("dell.com:8080", "dell.com"),
            # UK domain with www and https
            ("https://www.jewson.co.uk/products/bricks", "jewson.co.uk"),
            # Subdomain (non-www) — kept as-is
            ("store.nike.com", "store.nike.com"),
            # Mixed case URL
            ("HTTPS://WWW.Dell.COM/EN-US", "dell.com"),
            # Just www. with domain
            ("www.algolia.com", "algolia.com"),
            # Multiple subdomains
            ("api.v2.example.com", "api.v2.example.com"),
        ],
    )
    def test_normalization(self, input_str: str, expected: str) -> None:
        """Each input variation should normalize to the expected domain."""
        assert normalize_domain(input_str) == expected

    def test_none_like_empty(self) -> None:
        """Empty string returns empty string."""
        assert normalize_domain("") == ""

    def test_whitespace_only(self) -> None:
        """Whitespace-only input returns empty string."""
        assert normalize_domain("   ") == ""

    def test_company_name_preserves_casing(self) -> None:
        """Company names (no dots) are returned with original casing."""
        assert normalize_domain("Dell") == "Dell"
        assert normalize_domain("  Algolia  ") == "Algolia"

    def test_idempotent(self) -> None:
        """Running normalize_domain twice gives the same result."""
        domains = ["dell.com", "jewson.co.uk", "store.bestbuy.com"]
        for d in domains:
            assert normalize_domain(normalize_domain(d)) == normalize_domain(d)


# ---------------------------------------------------------------------------
# looks_like_domain
# ---------------------------------------------------------------------------


class TestLooksLikeDomain:
    """Verify domain detection heuristic."""

    @pytest.mark.parametrize(
        "input_str, expected",
        [
            ("dell.com", True),
            ("www.dell.com", True),
            ("https://dell.com", True),
            ("http://www.jewson.co.uk/", True),
            ("store.bestbuy.com", True),
            ("Dell", False),
            ("", False),
            ("   ", False),
            ("hello world", False),
            ("just-text", False),
        ],
    )
    def test_detection(self, input_str: str, expected: bool) -> None:
        assert looks_like_domain(input_str) is expected


# ---------------------------------------------------------------------------
# extract_domain_from_url (alias)
# ---------------------------------------------------------------------------


class TestExtractDomainFromUrl:
    """Verify the alias delegates correctly."""

    def test_alias_matches_normalize(self) -> None:
        urls = [
            "https://www.dell.com/en-us",
            "http://jewson.co.uk/",
            "www.nike.com",
            "dell.com:443",
        ]
        for url in urls:
            assert extract_domain_from_url(url) == normalize_domain(url)
