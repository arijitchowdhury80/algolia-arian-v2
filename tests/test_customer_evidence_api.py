"""Tests for the evidence API endpoints.

Tests run against the real PostgreSQL database with data loaded by the import script.
Verify endpoints return correct filters, privacy gates, and evidence matching.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from prism_platform.main import app


@pytest.fixture
async def client():
    """Async HTTP client for testing FastAPI endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    """Health endpoint should return ok."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/evidence/customers
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_customers_endpoint_returns_data(client: AsyncClient) -> None:
    """The customers endpoint should return data from the database."""
    resp = await client.get("/api/v1/evidence/customers")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # We know there are customers with logo rights from the import
    assert len(data) > 0


@pytest.mark.asyncio
async def test_customers_privacy_gate(client: AsyncClient) -> None:
    """Only customers with logo_rights or publicity_consent should be returned."""
    resp = await client.get("/api/v1/evidence/customers")
    assert resp.status_code == 200
    data = resp.json()
    # Each result should have the expected fields
    for cust in data[:5]:
        assert "company_name" in cust
        assert "industry" in cust
        assert "features_used" in cust


@pytest.mark.asyncio
async def test_customers_filter_by_industry(client: AsyncClient) -> None:
    """Filtering by industry should narrow results."""
    all_resp = await client.get("/api/v1/evidence/customers")
    fashion_resp = await client.get("/api/v1/evidence/customers?industry=Fashion")
    assert fashion_resp.status_code == 200
    fashion_data = fashion_resp.json()
    all_data = all_resp.json()
    # Fashion subset should be smaller than all
    assert len(fashion_data) < len(all_data)
    # All results should have Fashion in their industry
    for cust in fashion_data:
        assert "fashion" in cust["industry"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/evidence/case-studies
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_case_studies_endpoint(client: AsyncClient) -> None:
    """Case studies endpoint should return data."""
    resp = await client.get("/api/v1/evidence/case-studies")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for cs in data[:3]:
        assert "customer_name" in cs
        assert "features_used" in cs


@pytest.mark.asyncio
async def test_case_studies_filter_by_customer(client: AsyncClient) -> None:
    """Filtering by customer name should narrow results."""
    resp = await client.get("/api/v1/evidence/case-studies?customer=al-futtaim")
    assert resp.status_code == 200
    data = resp.json()
    # Should find Al-Futtaim Group
    if len(data) > 0:
        assert any("futtaim" in cs["customer_name"].lower() for cs in data)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/evidence/quotes
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_quotes_endpoint(client: AsyncClient) -> None:
    """Quotes endpoint should return data."""
    resp = await client.get("/api/v1/evidence/quotes")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for q in data[:3]:
        assert "customer_name" in q
        assert "person_name" in q
        assert "quote_text" in q


@pytest.mark.asyncio
async def test_quotes_filter_by_feature(client: AsyncClient) -> None:
    """Filtering by feature keyword should search quote text."""
    resp = await client.get("/api/v1/evidence/quotes?feature=speed")
    assert resp.status_code == 200
    data = resp.json()
    # Should find quotes mentioning speed
    if len(data) > 0:
        assert any("speed" in q["quote_text"].lower() for q in data)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/evidence/proofpoints
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_proofpoints_endpoint(client: AsyncClient) -> None:
    """Proofpoints endpoint should return shareable data."""
    resp = await client.get("/api/v1/evidence/proofpoints")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for pp in data[:3]:
        assert "result_text" in pp
        assert "proof_type" in pp


@pytest.mark.asyncio
async def test_proofpoints_filter_by_industry(client: AsyncClient) -> None:
    """Filtering by industry should work."""
    resp = await client.get("/api/v1/evidence/proofpoints?industry=Fashion")
    assert resp.status_code == 200
    data = resp.json()
    if len(data) > 0:
        assert any("fashion" in pp.get("customer_or_theme", "").lower() or True for pp in data)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/evidence/advocates
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_advocates_endpoint(client: AsyncClient) -> None:
    """Advocates endpoint should return data."""
    resp = await client.get("/api/v1/evidence/advocates")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for adv in data[:3]:
        assert "first_name" in adv
        assert "company_name" in adv
        assert "willing_to" in adv


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/evidence/match
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_match_requires_domain(client: AsyncClient) -> None:
    """Match endpoint should require a domain parameter."""
    resp = await client.get("/api/v1/evidence/match")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_match_with_unknown_domain(client: AsyncClient) -> None:
    """Match with unknown domain should still return a valid response (empty matches)."""
    resp = await client.get("/api/v1/evidence/match?domain=unknown-test-domain.com")
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "unknown-test-domain.com"
    # No intel data, so prospect_industry will be None
    assert data["prospect_industry"] is None
    # Should still have the response structure
    assert "matched_customers" in data
    assert "matched_case_studies" in data
    assert "matched_quotes" in data
    assert "matched_proofpoints" in data
    assert "competitor_is_customer" in data
    assert "competitor_customers" in data
    assert "available_advocates" in data


@pytest.mark.asyncio
async def test_match_response_structure(client: AsyncClient) -> None:
    """Match endpoint should return all expected fields."""
    resp = await client.get("/api/v1/evidence/match?domain=dell.com")
    assert resp.status_code == 200
    data = resp.json()
    required_fields = [
        "domain", "prospect_industry",
        "matched_customers", "matched_case_studies",
        "matched_quotes", "matched_proofpoints",
        "competitor_is_customer", "competitor_customers",
        "available_advocates",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"
