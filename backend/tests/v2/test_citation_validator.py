"""Tests for citation_validator — Tier 1 URL existence validation.

RED → GREEN cycle: tests written before implementation.

Tier 1 = HEAD request to check URL exists (fast, cheap).
Does NOT check content — that's Tier 2 (Phase 3).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from pydantic import ValidationError

from core.citation_validator import (
    CitationValidationResult,
    validate_citations_tier1,
)

# ---------------------------------------------------------------------------
# CitationValidationResult schema
# ---------------------------------------------------------------------------


def test_result_has_required_fields() -> None:
    """CitationValidationResult has url and citation_status fields."""
    result = CitationValidationResult(
        url="https://example.com",
        citation_status="live",
    )
    assert result.url == "https://example.com"
    assert result.citation_status == "live"


def test_result_status_literals() -> None:
    """citation_status accepts only 'live', 'dead', 'unchecked'."""
    CitationValidationResult(url="https://a.com", citation_status="live")
    CitationValidationResult(url="https://a.com", citation_status="dead")
    CitationValidationResult(url="https://a.com", citation_status="unchecked")


def test_result_rejects_invalid_status() -> None:
    """citation_status rejects unknown values."""
    with pytest.raises(ValidationError):
        CitationValidationResult(url="https://a.com", citation_status="invalid")  # type: ignore[arg-type]


def test_result_has_optional_status_code() -> None:
    """CitationValidationResult has optional http_status_code field."""
    result = CitationValidationResult(
        url="https://example.com",
        citation_status="live",
        http_status_code=200,
    )
    assert result.http_status_code == 200


def test_result_status_code_defaults_to_none() -> None:
    """http_status_code defaults to None when not provided."""
    result = CitationValidationResult(url="https://example.com", citation_status="unchecked")
    assert result.http_status_code is None


def test_result_is_frozen() -> None:
    """CitationValidationResult is immutable (frozen=True)."""
    result = CitationValidationResult(url="https://example.com", citation_status="live")
    with pytest.raises(ValidationError):
        result.citation_status = "dead"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# validate_citations_tier1
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_list_returns_empty() -> None:
    """Empty citation list returns empty results list."""
    results = await validate_citations_tier1([])
    assert results == []


@pytest.mark.asyncio
async def test_live_url_returns_live_status() -> None:
    """200 response from HEAD request → citation_status='live'."""
    fake_response = httpx.Response(
        status_code=200,
        request=httpx.Request("HEAD", "https://example.com/article"),
    )
    with patch("httpx.AsyncClient.head", new_callable=AsyncMock, return_value=fake_response):
        results = await validate_citations_tier1(["https://example.com/article"])

    assert len(results) == 1
    assert results[0].citation_status == "live"
    assert results[0].http_status_code == 200


@pytest.mark.asyncio
async def test_404_returns_dead_status() -> None:
    """404 response → citation_status='dead'."""
    fake_response = httpx.Response(
        status_code=404,
        request=httpx.Request("HEAD", "https://example.com/gone"),
    )
    with patch("httpx.AsyncClient.head", new_callable=AsyncMock, return_value=fake_response):
        results = await validate_citations_tier1(["https://example.com/gone"])

    assert results[0].citation_status == "dead"
    assert results[0].http_status_code == 404


@pytest.mark.asyncio
async def test_redirect_3xx_counts_as_live() -> None:
    """3xx response (redirect) → citation_status='live' (URL exists, just redirects)."""
    fake_response = httpx.Response(
        status_code=301,
        request=httpx.Request("HEAD", "https://example.com/redirect"),
    )
    with patch("httpx.AsyncClient.head", new_callable=AsyncMock, return_value=fake_response):
        results = await validate_citations_tier1(["https://example.com/redirect"])

    assert results[0].citation_status == "live"


@pytest.mark.asyncio
async def test_network_error_returns_unchecked() -> None:
    """Network error (ConnectError etc.) → citation_status='unchecked'."""
    with patch(
        "httpx.AsyncClient.head",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("timeout"),
    ):
        results = await validate_citations_tier1(["https://example.com/unreachable"])

    assert results[0].citation_status == "unchecked"
    assert results[0].http_status_code is None


@pytest.mark.asyncio
async def test_batch_validates_all_urls() -> None:
    """Multiple URLs are all validated and returned in order."""
    urls = [
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3",
    ]
    responses = [httpx.Response(200, request=httpx.Request("HEAD", u)) for u in urls]

    call_count = 0

    async def mock_head(url: str, **kwargs: object) -> httpx.Response:
        nonlocal call_count
        resp = responses[call_count]
        call_count += 1
        return resp

    with patch("httpx.AsyncClient.head", new_callable=AsyncMock, side_effect=mock_head):
        results = await validate_citations_tier1(urls)

    assert len(results) == 3
    assert all(r.citation_status == "live" for r in results)


@pytest.mark.asyncio
async def test_mixed_statuses_in_batch() -> None:
    """A batch with live, dead, and network-error URLs returns correct statuses."""
    urls = [
        "https://example.com/live",
        "https://example.com/dead",
        "https://example.com/error",
    ]
    call_count = 0
    side_effects: list = [
        httpx.Response(200, request=httpx.Request("HEAD", urls[0])),
        httpx.Response(404, request=httpx.Request("HEAD", urls[1])),
        httpx.ConnectError("timeout"),
    ]

    async def mock_head(url: str, **kwargs: object) -> httpx.Response:
        nonlocal call_count
        effect = side_effects[call_count]
        call_count += 1
        if isinstance(effect, Exception):
            raise effect
        return effect

    with patch("httpx.AsyncClient.head", new_callable=AsyncMock, side_effect=mock_head):
        results = await validate_citations_tier1(urls)

    statuses = [r.citation_status for r in results]
    assert statuses == ["live", "dead", "unchecked"]
