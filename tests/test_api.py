"""PRISM API Tests — uses real PostgreSQL database via TestClient."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from prism_platform.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    """GET /health should return status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


def test_list_modules_returns_list() -> None:
    """GET /api/v1/modules/ should return a (possibly empty) list."""
    response = client.get("/api/v1/modules/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_audit_valid() -> None:
    """POST /api/v1/audits/ with valid data should create an audit (real DB)."""
    payload = {
        "domain": f"test-{uuid.uuid4().hex[:8]}.example.com",
        "company_name": "Test Corp",
        "ticker": None,
        "is_private": True,
    }
    response = client.post("/api/v1/audits/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["domain"] == payload["domain"]
    assert data["company_name"] == "Test Corp"
    assert data["status"] == "pending"
    assert "id" in data
    assert "account_id" in data


def test_get_audit_not_found() -> None:
    """GET /api/v1/audits/{random_id} should return 404."""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/audits/{fake_id}")
    assert response.status_code == 404


def test_create_audit_rejects_extra_fields() -> None:
    """POST /api/v1/audits/ with unknown fields should return 422."""
    payload = {
        "domain": "extra.example.com",
        "company_name": "Extra Corp",
        "sneaky_field": "should_fail",
    }
    response = client.post("/api/v1/audits/", json=payload)
    assert response.status_code == 422


def test_get_created_audit() -> None:
    """Create an audit, then fetch it by ID."""
    domain = f"roundtrip-{uuid.uuid4().hex[:8]}.example.com"
    create_resp = client.post(
        "/api/v1/audits/",
        json={"domain": domain, "company_name": "Roundtrip Inc", "is_private": False},
    )
    assert create_resp.status_code == 201
    audit_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/v1/audits/{audit_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["domain"] == domain
