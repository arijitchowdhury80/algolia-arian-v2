"""Tests for insights-engine collector extraction logic.

Tests the pure extraction functions and vertical matching with synthetic data.
No real DB or API calls -- uses mocks for database access.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from prism_platform.modules.insights_engine.collector import InsightsCollector

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_module_execution(
    module_name: str,
    output_json: dict[str, Any] | None,
    status: str = "success",
    domain: str = "dell.com",
) -> MagicMock:
    """Create a mock ModuleExecution row."""
    row = MagicMock()
    row.module_name = module_name
    row.output_json = output_json
    row.status = status
    row.domain = domain
    row.completed_at = MagicMock()
    return row


def _make_audit(audit_id: str, account_id: str, status: str = "completed") -> MagicMock:
    """Create a mock Audit row."""
    import uuid

    row = MagicMock()
    row.id = uuid.UUID(audit_id) if len(audit_id) == 36 else audit_id
    row.account_id = uuid.UUID(account_id) if len(account_id) == 36 else account_id
    row.status = status
    row.created_at = MagicMock()
    return row


SAMPLE_COMPANY_OUTPUT: dict[str, Any] = {
    "legal_name": "Dell Technologies Inc.",
    "common_name": "Dell",
    "domain": "dell.com",
    "industry": "Enterprise Technology",
    "sub_vertical": "Consumer Electronics",
}

SAMPLE_TECHSTACK_OUTPUT: dict[str, Any] = {
    "search_vendor": {"name": "Elasticsearch"},
    "ecommerce_platform": "Salesforce Commerce Cloud",
}

SAMPLE_TRAFFIC_OUTPUT: dict[str, Any] = {
    "total_visits": 50000000,
    "bounce_rate": 0.35,
}


# ---------------------------------------------------------------------------
# Vertical extraction tests
# ---------------------------------------------------------------------------
class TestExtractVertical:
    def test_extracts_industry(self) -> None:
        collector = InsightsCollector()
        result = collector._extract_vertical({"intel-company": SAMPLE_COMPANY_OUTPUT})
        assert result == "Enterprise Technology"

    def test_empty_when_no_company_data(self) -> None:
        collector = InsightsCollector()
        result = collector._extract_vertical({})
        assert result == ""

    def test_empty_when_company_has_no_industry(self) -> None:
        collector = InsightsCollector()
        result = collector._extract_vertical({"intel-company": {"domain": "test.com"}})
        assert result == ""

    def test_strips_whitespace(self) -> None:
        collector = InsightsCollector()
        result = collector._extract_vertical({"intel-company": {"industry": "  Retail  "}})
        assert result == "Retail"

    def test_handles_none_company_output(self) -> None:
        collector = InsightsCollector()
        result = collector._extract_vertical({"intel-company": None})
        assert result == ""

    def test_handles_non_dict_company_output(self) -> None:
        collector = InsightsCollector()
        result = collector._extract_vertical({"intel-company": "not a dict"})
        assert result == ""


# ---------------------------------------------------------------------------
# collect_all tests with mocked DB
# ---------------------------------------------------------------------------
class TestCollectAll:
    @pytest.mark.asyncio
    async def test_returns_structure_with_no_data(self) -> None:
        """With empty DB, returns default structure."""
        collector = InsightsCollector()

        with patch.object(collector, "_read_audit_modules", new_callable=AsyncMock) as mock_read:
            mock_read.return_value = {}
            result = await collector.collect_all(
                audit_id="00000000-0000-0000-0000-000000000001",
                domain="unknown.com",
            )

        assert result["vertical"] == ""
        assert result["current_audit"] == {}
        assert result["historical_audits"] == []
        assert result["historical_audit_ids"] == []
        assert result["total_audits"] == 1

    @pytest.mark.asyncio
    async def test_returns_vertical_from_company_output(self) -> None:
        """When intel-company output exists, vertical is extracted."""
        collector = InsightsCollector()

        with (
            patch.object(collector, "_read_audit_modules", new_callable=AsyncMock) as mock_read,
            patch.object(
                collector, "_read_vertical_audits", new_callable=AsyncMock
            ) as mock_vertical,
        ):
            mock_read.return_value = {"intel-company": SAMPLE_COMPANY_OUTPUT}
            mock_vertical.return_value = ([], [])

            result = await collector.collect_all(
                audit_id="00000000-0000-0000-0000-000000000001",
                domain="dell.com",
            )

        assert result["vertical"] == "Enterprise Technology"
        assert result["total_audits"] == 1

    @pytest.mark.asyncio
    async def test_includes_historical_audits(self) -> None:
        """When historical audits exist, they are included."""
        collector = InsightsCollector()

        historical = [{"intel-techstack": SAMPLE_TECHSTACK_OUTPUT}]
        historical_ids = ["00000000-0000-0000-0000-000000000002"]

        with (
            patch.object(collector, "_read_audit_modules", new_callable=AsyncMock) as mock_read,
            patch.object(
                collector, "_read_vertical_audits", new_callable=AsyncMock
            ) as mock_vertical,
        ):
            mock_read.return_value = {"intel-company": SAMPLE_COMPANY_OUTPUT}
            mock_vertical.return_value = (historical, historical_ids)

            result = await collector.collect_all(
                audit_id="00000000-0000-0000-0000-000000000001",
                domain="dell.com",
            )

        assert result["total_audits"] == 2
        assert len(result["historical_audits"]) == 1
        assert len(result["historical_audit_ids"]) == 1

    @pytest.mark.asyncio
    async def test_first_in_vertical(self) -> None:
        """When no historical audits, total is 1."""
        collector = InsightsCollector()

        with (
            patch.object(collector, "_read_audit_modules", new_callable=AsyncMock) as mock_read,
            patch.object(
                collector, "_read_vertical_audits", new_callable=AsyncMock
            ) as mock_vertical,
        ):
            mock_read.return_value = {"intel-company": SAMPLE_COMPANY_OUTPUT}
            mock_vertical.return_value = ([], [])

            result = await collector.collect_all(
                audit_id="00000000-0000-0000-0000-000000000001",
                domain="dell.com",
            )

        assert result["total_audits"] == 1
        assert result["historical_audits"] == []
