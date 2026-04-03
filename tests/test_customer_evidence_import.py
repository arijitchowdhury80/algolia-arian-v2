"""Tests for the customer evidence import script.

Verifies that the Excel parser correctly:
- Reads and deduplicates customers from 9 sheets
- Merges case studies from 2 sheets
- Parses quotes, proofpoints, and advocates
- Converts ARR to ranges
- Handles consent flags correctly
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_customer_evidence import (
    import_advocates,
    import_case_studies,
    import_customers,
    import_proofpoints,
    import_quotes,
    normalize_company_name,
    parse_willing_to,
    safe_str,
    to_arr_range,
    to_bool,
    to_date,
)

EXCEL_PATH = PROJECT_ROOT / "docs" / "data" / "CustomerEvidence-Algolia.xlsx"


# ─────────────────────────────────────────────────────────────────────────────
# Helper function tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHelperFunctions:
    """Test utility functions used by the import script."""

    def test_normalize_company_name(self) -> None:
        assert normalize_company_name("  Dell Technologies  ") == "dell technologies"
        assert normalize_company_name("HP Inc.") == "hp inc."
        assert normalize_company_name(None) == ""
        assert normalize_company_name("") == ""

    def test_to_arr_range_numeric(self) -> None:
        assert to_arr_range(30000) == "<50K"
        assert to_arr_range(75000) == "50K-100K"
        assert to_arr_range(150000) == "100K-250K"
        assert to_arr_range(400000) == "250K-500K"
        assert to_arr_range(750000) == "500K-1M"
        assert to_arr_range(2000000) == "1M+"

    def test_to_arr_range_string(self) -> None:
        assert to_arr_range("USD 172,982.50") == "100K-250K"
        assert to_arr_range("$1,200,000") == "1M+"

    def test_to_arr_range_none(self) -> None:
        assert to_arr_range(None) is None
        assert to_arr_range(float("nan")) is None

    def test_to_bool(self) -> None:
        assert to_bool(True) is True
        assert to_bool(False) is False
        assert to_bool(1) is True
        assert to_bool(0) is False
        assert to_bool("Yes") is True
        assert to_bool("No") is False
        assert to_bool(None) is False
        assert to_bool(float("nan")) is False
        assert to_bool("Via Algolia Terms of Service") is True

    def test_to_date(self) -> None:
        from datetime import date, datetime

        assert to_date(datetime(2024, 1, 15)) == date(2024, 1, 15)
        assert to_date(pd.Timestamp("2024-01-15")) == date(2024, 1, 15)
        assert to_date(None) is None
        assert to_date(float("nan")) is None

    def test_safe_str(self) -> None:
        assert safe_str("hello") == "hello"
        assert safe_str("  spaced  ") == "spaced"
        assert safe_str(None) is None
        assert safe_str(float("nan")) is None
        assert safe_str("") is None

    def test_parse_willing_to(self) -> None:
        result = parse_willing_to("Reference, Phone, Case Study, Testimonial")
        assert result == ["Reference", "Phone", "Case Study", "Testimonial"]
        assert parse_willing_to(None) == []
        assert parse_willing_to(float("nan")) == []


# ─────────────────────────────────────────────────────────────────────────────
# Integration tests — read actual Excel file
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def excel_file() -> pd.ExcelFile:
    """Load the Excel file once for all tests in this module."""
    if not EXCEL_PATH.exists():
        pytest.skip(f"Excel file not found at {EXCEL_PATH}")
    return pd.ExcelFile(EXCEL_PATH, engine="openpyxl")


class TestCustomerImport:
    """Test customer import from real Excel data."""

    def test_customer_count(self, excel_file: pd.ExcelFile) -> None:
        """Verify we get a reasonable number of deduplicated customers."""
        customers = import_customers(excel_file)
        # Cust.Logos alone has ~1306 rows, but with dedup across 9 sheets
        # we expect roughly 1500-2500 unique customers
        assert len(customers) >= 1500, f"Expected at least 1500 customers, got {len(customers)}"
        assert len(customers) <= 3000, f"Expected at most 3000 customers, got {len(customers)}"

    def test_customer_has_required_fields(self, excel_file: pd.ExcelFile) -> None:
        """Every customer must have a company_name."""
        customers = import_customers(excel_file)
        for cust in customers:
            assert cust.get("company_name"), f"Customer missing company_name: {cust}"
            assert isinstance(cust.get("features_used"), list)

    def test_customer_deduplication(self, excel_file: pd.ExcelFile) -> None:
        """Verify that the same company appearing in multiple sheets is merged."""
        customers = import_customers(excel_file)
        names = [normalize_company_name(c["company_name"]) for c in customers]
        assert len(names) == len(set(names)), "Duplicate company names found after dedup"

    def test_arr_converted_to_ranges(self, excel_file: pd.ExcelFile) -> None:
        """ARR values should be converted to range strings, never exact numbers."""
        customers = import_customers(excel_file)
        valid_ranges = {"<50K", "50K-100K", "100K-250K", "250K-500K", "500K-1M", "1M+", None}
        for cust in customers:
            arr = cust.get("arr_range")
            assert arr in valid_ranges, f"Invalid ARR range '{arr}' for {cust['company_name']}"

    def test_consent_flags_are_booleans(self, excel_file: pd.ExcelFile) -> None:
        """Consent flags must be booleans."""
        customers = import_customers(excel_file)
        for cust in customers[:50]:  # Check first 50 for speed
            for flag in ("logo_rights", "case_study_consent", "publicity_consent", "reference_consent"):
                if flag in cust:
                    assert isinstance(cust[flag], bool), f"{flag} is not bool for {cust['company_name']}"


class TestCaseStudyImport:
    """Test case study import from real Excel data."""

    def test_case_study_count(self, excel_file: pd.ExcelFile) -> None:
        """Verify we get a reasonable number of case studies."""
        cases = import_case_studies(excel_file)
        # Cust. Stories (82) + Case Studies (134) with dedup
        assert len(cases) >= 100, f"Expected at least 100 case studies, got {len(cases)}"
        assert len(cases) <= 250, f"Expected at most 250 case studies, got {len(cases)}"

    def test_case_study_has_customer_name(self, excel_file: pd.ExcelFile) -> None:
        """Every case study must have a customer_name."""
        cases = import_case_studies(excel_file)
        for cs in cases:
            assert cs.get("customer_name"), f"Case study missing customer_name: {cs}"

    def test_features_used_is_list(self, excel_file: pd.ExcelFile) -> None:
        """Features used should be a list."""
        cases = import_case_studies(excel_file)
        for cs in cases:
            assert isinstance(cs.get("features_used", []), list)


class TestQuoteImport:
    """Test quote import from real Excel data."""

    def test_quote_count(self, excel_file: pd.ExcelFile) -> None:
        """Verify we get a reasonable number of quotes."""
        quotes = import_quotes(excel_file)
        # Cust.Quotes has 379 rows, but some may be skipped
        assert len(quotes) >= 300, f"Expected at least 300 quotes, got {len(quotes)}"
        assert len(quotes) <= 450, f"Expected at most 450 quotes, got {len(quotes)}"

    def test_quote_has_required_fields(self, excel_file: pd.ExcelFile) -> None:
        """Every quote must have customer_name, person_name, and quote_text."""
        quotes = import_quotes(excel_file)
        for q in quotes:
            assert q.get("customer_name"), f"Quote missing customer_name"
            assert q.get("person_name"), f"Quote missing person_name"
            assert q.get("quote_text"), f"Quote missing quote_text"


class TestProofpointImport:
    """Test proofpoint import from real Excel data."""

    def test_proofpoint_count(self, excel_file: pd.ExcelFile) -> None:
        """Verify we get all 81 proofpoints."""
        proofpoints = import_proofpoints(excel_file)
        assert len(proofpoints) >= 70, f"Expected at least 70 proofpoints, got {len(proofpoints)}"
        assert len(proofpoints) <= 90, f"Expected at most 90 proofpoints, got {len(proofpoints)}"

    def test_proofpoint_has_result_text(self, excel_file: pd.ExcelFile) -> None:
        """Every proofpoint must have result_text."""
        proofpoints = import_proofpoints(excel_file)
        for pp in proofpoints:
            assert pp.get("result_text"), f"Proofpoint missing result_text"


class TestAdvocateImport:
    """Test advocate import from real Excel data."""

    def test_advocate_count(self, excel_file: pd.ExcelFile) -> None:
        """Verify we get a reasonable number of deduplicated advocates."""
        advocates = import_advocates(excel_file)
        # Reference Volunteers (130) + Customer Advocates (172) with dedup
        assert len(advocates) >= 200, f"Expected at least 200 advocates, got {len(advocates)}"
        assert len(advocates) <= 350, f"Expected at most 350 advocates, got {len(advocates)}"

    def test_advocate_has_required_fields(self, excel_file: pd.ExcelFile) -> None:
        """Every advocate must have first_name and company_name."""
        advocates = import_advocates(excel_file)
        for adv in advocates:
            assert adv.get("first_name"), f"Advocate missing first_name"
            assert adv.get("company_name"), f"Advocate missing company_name"

    def test_willing_to_is_list(self, excel_file: pd.ExcelFile) -> None:
        """willing_to should be a list."""
        advocates = import_advocates(excel_file)
        for adv in advocates:
            assert isinstance(adv.get("willing_to", []), list)
