"""Import Algolia customer evidence from Excel into PostgreSQL.

Reads docs/data/CustomerEvidence-Algolia.xlsx and populates:
  - algolia_customers (deduplicated by company name)
  - algolia_case_studies (merged from Cust. Stories + Case Studies sheets)
  - algolia_quotes (from Cust.Quotes)
  - algolia_proofpoints (from Cust. Proofpoints)
  - algolia_advocates (deduplicated by email from Reference Volunteers + Customer Advocates)

Usage:
    python scripts/import_customer_evidence.py [--excel-path PATH] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Add project root to path so we can import prism_platform
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from prism_platform.config import settings  # noqa: E402

logger = structlog.get_logger(__name__)

DEFAULT_EXCEL_PATH = PROJECT_ROOT / "docs" / "data" / "CustomerEvidence-Algolia.xlsx"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def normalize_company_name(name: str | None) -> str:
    """Normalize company name for deduplication: strip, lowercase."""
    if not name or not isinstance(name, str):
        return ""
    return name.strip().lower()


def to_arr_range(arr_value: Any) -> str | None:
    """Convert numeric ARR to a range string for sensitivity."""
    if arr_value is None or (isinstance(arr_value, float) and pd.isna(arr_value)):
        return None
    try:
        if isinstance(arr_value, str):
            # Handle "USD 172,982.50" format
            cleaned = arr_value.replace("USD", "").replace("$", "").replace(",", "").strip()
            arr = float(cleaned)
        else:
            arr = float(arr_value)
    except (ValueError, TypeError):
        return None

    if arr < 50_000:
        return "<50K"
    elif arr < 100_000:
        return "50K-100K"
    elif arr < 250_000:
        return "100K-250K"
    elif arr < 500_000:
        return "250K-500K"
    elif arr < 1_000_000:
        return "500K-1M"
    else:
        return "1M+"


def to_bool(value: Any) -> bool:
    """Convert various Excel truthy values to bool."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        return v in ("true", "yes", "1", "y", "via algolia terms of service")
    return False


def to_date(value: Any) -> date | None:
    """Convert Excel date values to Python date."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        parsed = pd.to_datetime(value)
        if pd.isna(parsed):
            return None
        return parsed.date()
    except Exception:
        return None


def safe_str(value: Any) -> str | None:
    """Convert to string or None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    return s if s else None


def parse_features_checkmarks(row: pd.Series, feature_columns: list[str]) -> list[str]:
    """Extract feature names from checkmark columns (value is checkmark emoji or truthy)."""
    features: list[str] = []
    for col in feature_columns:
        val = row.get(col)
        if val is not None and not (isinstance(val, float) and pd.isna(val)):
            s = str(val).strip()
            if s and s not in ("nan", "None", "0", "False"):
                features.append(col.strip())
    return features


def parse_willing_to(value: Any) -> list[str]:
    """Parse 'willing to participate in' field to list."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def parse_products_notes(notes: Any) -> list[str]:
    """Extract product names from notes field (e.g. 'AI Search, Recommend')."""
    if notes is None or (isinstance(notes, float) and pd.isna(notes)):
        return []
    text = str(notes)
    known_products = [
        "AI Search", "Recommend", "Browse", "NeuralSearch", "Analytics",
        "Personalization", "Autocomplete", "Rules", "Merchandising",
        "Query Suggestions", "A/B Testing", "Dynamic Synonyms",
    ]
    found = []
    for product in known_products:
        if product.lower() in text.lower():
            found.append(product)
    return found


# ─────────────────────────────────────────────────────────────────────────────
# Import functions for each table
# ─────────────────────────────────────────────────────────────────────────────


def import_customers(xls: pd.ExcelFile) -> list[dict[str, Any]]:
    """Import and merge customer data from multiple sheets. Returns list of row dicts."""
    customers: dict[str, dict[str, Any]] = {}  # keyed by normalized name

    def merge_customer(name: str, data: dict[str, Any]) -> None:
        """Merge new data into existing customer record, preferring non-None values."""
        key = normalize_company_name(name)
        if not key:
            return
        if key not in customers:
            customers[key] = {"company_name": name.strip(), "features_used": []}
        existing = customers[key]
        for field, value in data.items():
            if field == "features_used":
                # Merge feature lists
                for feat in value:
                    if feat not in existing.get("features_used", []):
                        existing.setdefault("features_used", []).append(feat)
            else:
                # Skip NaT, NaN, None
                if value is None:
                    continue
                if isinstance(value, float) and pd.isna(value):
                    continue
                try:
                    if pd.isna(value):
                        continue
                except (TypeError, ValueError):
                    pass
                if existing.get(field) is None:
                    existing[field] = value

    # ── Cust.Logos (1307 rows) ──
    try:
        df = pd.read_excel(xls, sheet_name="Cust.Logos", header=1)
        logger.info("Reading Cust.Logos", rows=len(df))
        for _, row in df.iterrows():
            name = safe_str(row.get("Company"))
            if not name:
                continue
            merge_customer(name, {
                "industry": safe_str(row.get("Industry")),
                "signed_date": to_date(row.get("Signed Date")),
                "logo_rights": to_bool(row.get("Logo Rights")),
                "case_study_consent": to_bool(row.get("Case Study in Contract?")),
                "reference_consent": to_bool(row.get("Reference")),
                "competitor_replaced": safe_str(row.get("Competitor")),
                "ecommerce_platform": safe_str(row.get("Tech (Platform Built On)")),
                "notes": safe_str(row.get("Notes\n(product used either AI Search, Recommend, also want to know if its an expansion)")),
                "features_used": parse_products_notes(
                    row.get("Notes\n(product used either AI Search, Recommend, also want to know if its an expansion)")
                ),
            })
    except Exception as e:
        logger.error("Failed to read Cust.Logos", error=str(e))

    # ── Fashion (170 rows) ──
    try:
        df = pd.read_excel(xls, sheet_name="Fashion")
        logger.info("Reading Fashion", rows=len(df))
        for _, row in df.iterrows():
            name = safe_str(row.get("Company"))
            if not name:
                continue
            merge_customer(name, {
                "industry": "Fashion",
                "arr_range": to_arr_range(row.get("ARR")),
                "hierarchy_segment": safe_str(row.get("Segment")),
                "country": safe_str(row.get("Country")),
                "ecommerce_platform": safe_str(row.get("Ecommerce")),
                "go_live_date": to_date(row.get("go_live__c")),
                "logo_rights": to_bool(row.get("consent_logo__c")),
                "publicity_consent": not to_bool(row.get("nopublicityconsent")),
                "case_study_consent": to_bool(row.get("consent_casestudy__c")),
                "reference_consent": to_bool(row.get("consent_referencecall__c")),
            })
    except Exception as e:
        logger.error("Failed to read Fashion", error=str(e))

    # ── Grocery (54 rows) ──
    try:
        df = pd.read_excel(xls, sheet_name="Grocery")
        logger.info("Reading Grocery", rows=len(df))
        for _, row in df.iterrows():
            name = safe_str(row.get("account_name"))
            if not name:
                continue
            merge_customer(name, {
                "industry": "Grocery",
                "arr_range": to_arr_range(row.get("usd_arr")),
                "website": safe_str(row.get("website")),
                "country": safe_str(row.get("Country")),
                "logo_rights": to_bool(row.get("Logo rights")),
                "publicity_consent": not to_bool(row.get("NO publicity consent")),
                "case_study_consent": to_bool(row.get("Case Study")),
                "reference_consent": to_bool(row.get("Reference call ")),
                "signed_date": to_date(row.get("Cust_wonDate")),
                "go_live_date": to_date(row.get("Go-Live Date")),
            })
    except Exception as e:
        logger.error("Failed to read Grocery", error=str(e))

    # ── Luxury (55 rows) ──
    try:
        df = pd.read_excel(xls, sheet_name="Luxury")
        logger.info("Reading Luxury", rows=len(df))
        for _, row in df.iterrows():
            name = safe_str(row.get("name"))
            if not name:
                continue
            merge_customer(name, {
                "industry": "Luxury",
                "website": safe_str(row.get("website")),
                "country": safe_str(row.get("country")),
                "arr_range": to_arr_range(row.get("USD_ARR__c")),
                "hierarchy_segment": safe_str(row.get("hierarchy_segment__c")),
                "logo_rights": to_bool(row.get("consent_logo__c")),
                "publicity_consent": not to_bool(row.get("nopublicityconsent")),
                "case_study_consent": to_bool(row.get("consent_casestudy__c")),
                "reference_consent": to_bool(row.get("consent_referencecall__c")),
            })
    except Exception as e:
        logger.error("Failed to read Luxury", error=str(e))

    # ── 100k+ (546 rows) ──
    try:
        df = pd.read_excel(xls, sheet_name="100k+")
        logger.info("Reading 100k+", rows=len(df))
        for _, row in df.iterrows():
            name = safe_str(row.get("Account Name"))
            if not name:
                continue
            merge_customer(name, {
                "industry": safe_str(row.get("Primary Vertical")) or "Unknown",
                "sub_vertical": safe_str(row.get("Secondary Vertical")),
                "hierarchy_segment": safe_str(row.get("Hierarchy Segment")),
                "country": safe_str(row.get("Billing Country")),
                "arr_range": to_arr_range(row.get("ARR")),
                "website": safe_str(row.get("Website")),
                "go_live_date": to_date(row.get("Go-Live")),
                "logo_rights": to_bool(row.get("logo right")),
                "publicity_consent": not to_bool(row.get("no publicity")),
                "case_study_consent": to_bool(row.get("case study")),
            })
    except Exception as e:
        logger.error("Failed to read 100k+", error=str(e))

    # ── Travel (48 rows) ──
    try:
        df = pd.read_excel(xls, sheet_name="Travel")
        logger.info("Reading Travel", rows=len(df))
        for _, row in df.iterrows():
            name = safe_str(row.get("Account Name"))
            if not name:
                continue
            merge_customer(name, {
                "industry": "Travel",
                "hierarchy_segment": safe_str(row.get("Hierarchy Segment")),
                "logo_rights": to_bool(row.get("Logo Rights")),
                "case_study_consent": to_bool(row.get("Case Study in Contract?")),
                "website": safe_str(row.get("Website")),
                "notes": safe_str(row.get("Notes")),
            })
    except Exception as e:
        logger.error("Failed to read Travel", error=str(e))

    # ── FinServ (61 rows) ──
    try:
        df = pd.read_excel(xls, sheet_name="FinServ")
        logger.info("Reading FinServ", rows=len(df))
        for _, row in df.iterrows():
            name = safe_str(row.get("Company"))
            if not name:
                continue
            merge_customer(name, {
                "industry": "Financial Services",
                "sub_vertical": safe_str(row.get("Category")),
                "hierarchy_segment": safe_str(row.get("Hierarchy Segment")),
                "logo_rights": to_bool(row.get("Logo consent")),
                "case_study_consent": to_bool(row.get("Case study")),
                "reference_consent": to_bool(row.get("Reference")),
                "go_live_date": to_date(row.get("Go Live Date")),
            })
    except Exception as e:
        logger.error("Failed to read FinServ", error=str(e))

    # ── Adobe (390 rows) ──
    try:
        df = pd.read_excel(xls, sheet_name="Adobe")
        logger.info("Reading Adobe", rows=len(df))
        for _, row in df.iterrows():
            name = safe_str(row.get("Account Name"))
            if not name:
                continue
            merge_customer(name, {
                "arr_range": to_arr_range(row.get("ARR")),
                "logo_rights": to_bool(row.get("consent_logo__c")),
                "publicity_consent": not to_bool(row.get("nopublicityconsent")),
                "case_study_consent": to_bool(row.get("consent_casestudy__c")),
                "reference_consent": to_bool(row.get("consent_referencecall__c")),
                "ecommerce_platform": "Adobe Commerce",
            })
    except Exception as e:
        logger.error("Failed to read Adobe", error=str(e))

    # ── NRF FY26 (95 rows) ──
    try:
        df = pd.read_excel(xls, sheet_name="NRF FY26")
        logger.info("Reading NRF FY26", rows=len(df))
        for _, row in df.iterrows():
            name = safe_str(row.get("account_name"))
            if not name:
                continue
            ai_features = safe_str(row.get("AI ranking features "))
            features = [f.strip() for f in (ai_features or "").split(",") if f.strip()]
            merge_customer(name, {
                "arr_range": to_arr_range(row.get("account_arr")),
                "hierarchy_segment": safe_str(row.get("customer_account_segment")),
                "country": safe_str(row.get("billing_country")),
                "industry": safe_str(row.get("naics_sector_title")) or "Retail",
                "logo_rights": to_bool(row.get("Logo rights? ")),
                "case_study_consent": to_bool(row.get("Case Study Commitment ")),
                "features_used": features,
            })
    except Exception as e:
        logger.error("Failed to read NRF FY26", error=str(e))

    result = list(customers.values())
    logger.info("Customers imported", unique_count=len(result))
    return result


def import_case_studies(xls: pd.ExcelFile) -> list[dict[str, Any]]:
    """Import case studies from Cust. Stories + Case Studies sheets."""
    cases: dict[str, dict[str, Any]] = {}  # keyed by normalized customer name

    # ── Cust. Stories (82 rows) ──
    try:
        df = pd.read_excel(xls, sheet_name="Cust. Stories")
        logger.info("Reading Cust. Stories", rows=len(df))
        # Feature columns are columns after 'Industry'
        feature_cols = [
            c for c in df.columns
            if c.strip() not in (
                " Customer", " URL", "Localized(for localized URLs, scroll to the right)",
                "Country", "Region", "Use Case", "Industry", "Integration",
                "FR URL ", "GE URL ", "ES URL ", "PT URL ",
            )
        ]
        for _, row in df.iterrows():
            name = safe_str(row.get(" Customer"))
            if not name:
                continue
            key = normalize_company_name(name)
            features = parse_features_checkmarks(row, feature_cols)
            cases[key] = {
                "customer_name": name,
                "url": safe_str(row.get(" URL")),
                "country": safe_str(row.get("Country")),
                "use_case": safe_str(row.get("Use Case")),
                "industry": safe_str(row.get("Industry")) or "Unknown",
                "features_used": features,
            }
    except Exception as e:
        logger.error("Failed to read Cust. Stories", error=str(e))

    # ── Case Studies (134 rows) ──
    try:
        df = pd.read_excel(xls, sheet_name="Case Studies")
        logger.info("Reading Case Studies", rows=len(df))
        for _, row in df.iterrows():
            name = safe_str(row.get("Customer"))
            if not name:
                continue
            key = normalize_company_name(name)
            new_data = {
                "customer_name": name,
                "country": safe_str(row.get("Country")),
                "sub_vertical": safe_str(row.get("Customer Type/Persona")) or safe_str(row.get("Sub Category")),
                "url": safe_str(row.get("Story Link")),
                "status": safe_str(row.get("Status")) or "Complete",
                "competitor_takeout": safe_str(row.get("Competitor Takeout")),
                "partner_integrations": safe_str(row.get("Partners/Integrations")),
                "key_results": safe_str(row.get("Key Results / Metrics")),
            }
            if key in cases:
                # Merge: prefer existing Cust. Stories data, fill gaps from Case Studies
                for field, value in new_data.items():
                    if field == "customer_name":
                        continue
                    if value is not None and cases[key].get(field) is None:
                        cases[key][field] = value
            else:
                cases[key] = new_data
                cases[key].setdefault("features_used", [])
                cases[key].setdefault("industry", "Unknown")
    except Exception as e:
        logger.error("Failed to read Case Studies", error=str(e))

    result = list(cases.values())
    logger.info("Case studies imported", count=len(result))
    return result


def import_quotes(xls: pd.ExcelFile) -> list[dict[str, Any]]:
    """Import customer quotes from Cust.Quotes sheet."""
    quotes: list[dict[str, Any]] = []
    try:
        df = pd.read_excel(xls, sheet_name="Cust.Quotes")
        logger.info("Reading Cust.Quotes", rows=len(df))
        for _, row in df.iterrows():
            customer = safe_str(row.get("Customer"))
            person = safe_str(row.get("Name"))
            quote = safe_str(row.get("Evidence (Check out the full reviews on TrustRadius and G2)"))
            if not customer or not person or not quote:
                continue
            tags_raw = safe_str(row.get("Notes/Tags"))
            tags = [t.strip() for t in (tags_raw or "").split(",") if t.strip()] if tags_raw else None
            quotes.append({
                "customer_name": customer,
                "person_name": person,
                "person_title": safe_str(row.get("Title")),
                "industry": safe_str(row.get("Industry")) or "Unknown",
                "country": safe_str(row.get("Country")),
                "quote_text": quote,
                "evidence_type": safe_str(row.get("Evidence Type")),
                "source": safe_str(row.get("Source")),
                "tags": tags,
            })
    except Exception as e:
        logger.error("Failed to read Cust.Quotes", error=str(e))

    # Also import from Recommend Quotes sheet
    try:
        df = pd.read_excel(xls, sheet_name="Recommend Quotes")
        logger.info("Reading Recommend Quotes", rows=len(df))
        for _, row in df.iterrows():
            customer = safe_str(row.get("Customer"))
            person = safe_str(row.get("Name"))
            quote = safe_str(row.get("Evidence"))
            if not customer or not person or not quote:
                continue
            quotes.append({
                "customer_name": customer,
                "person_name": person,
                "person_title": safe_str(row.get("Title")),
                "industry": safe_str(row.get("Industry")) or "Unknown",
                "country": safe_str(row.get("Country")),
                "quote_text": quote,
                "evidence_type": safe_str(row.get("Evidence Type")),
                "source": safe_str(row.get("Source")),
                "tags": None,
            })
    except Exception as e:
        logger.error("Failed to read Recommend Quotes", error=str(e))

    logger.info("Quotes imported", count=len(quotes))
    return quotes


def import_proofpoints(xls: pd.ExcelFile) -> list[dict[str, Any]]:
    """Import proof points from Cust. Proofpoints sheet."""
    proofpoints: list[dict[str, Any]] = []
    try:
        df = pd.read_excel(xls, sheet_name="Cust. Proofpoints")
        logger.info("Reading Cust. Proofpoints", rows=len(df))
        for _, row in df.iterrows():
            result_text = safe_str(row.get("Results / Quotes "))
            if not result_text:
                continue
            shareable_raw = safe_str(row.get("Can you share this data ? "))
            shareable = shareable_raw is not None and shareable_raw.strip().lower() == "yes"
            proofpoints.append({
                "result_text": result_text,
                "source": safe_str(row.get("Source of the results")),
                "proof_type": safe_str(row.get("Type")) or "Aggregated Results",
                "industry": safe_str(row.get("Industry")) or "Unknown",
                "customer_or_theme": safe_str(row.get("Customer / Theme")),
                "shareable": shareable,
            })
    except Exception as e:
        logger.error("Failed to read Cust. Proofpoints", error=str(e))

    logger.info("Proofpoints imported", count=len(proofpoints))
    return proofpoints


def import_advocates(xls: pd.ExcelFile) -> list[dict[str, Any]]:
    """Import advocates from Reference Volunteers + Customer Advocates, deduplicated by email."""
    advocates: dict[str, dict[str, Any]] = {}  # keyed by email (lowercase)

    # ── Reference Volunteers (130 rows) ──
    try:
        df = pd.read_excel(xls, sheet_name="Reference Volunteers")
        logger.info("Reading Reference Volunteers", rows=len(df))
        for _, row in df.iterrows():
            name = safe_str(row.get("Name"))
            email = safe_str(row.get("Email Address"))
            customer = safe_str(row.get("Customer"))
            if not name or not customer:
                continue
            # Split name into first/last
            parts = name.split(None, 1)
            first = parts[0] if parts else name
            last = parts[1] if len(parts) > 1 else ""

            key = (email or "").strip().lower() or f"_nomail_{normalize_company_name(name)}"
            advocates[key] = {
                "first_name": first,
                "last_name": last,
                "company_name": customer,
                "job_title": safe_str(row.get("Title")),
                "email": email,
                "industry": safe_str(row.get("Industry")),
                "country": safe_str(row.get("Country")),
                "willing_to": parse_willing_to(row.get("Willing to participate in:")),
                "person_source": safe_str(row.get("Source")),
            }
    except Exception as e:
        logger.error("Failed to read Reference Volunteers", error=str(e))

    # ── Customer Advocates (172 rows) ──
    try:
        df = pd.read_excel(xls, sheet_name="Customer Advocates")
        logger.info("Reading Customer Advocates", rows=len(df))
        for _, row in df.iterrows():
            first = safe_str(row.get("First Name"))
            last = safe_str(row.get("Last Name"))
            company = safe_str(row.get("Company Name"))
            email = safe_str(row.get("Email Address"))
            if not first or not company:
                continue
            key = (email or "").strip().lower() or f"_nomail_{normalize_company_name(first or '')}{normalize_company_name(last or '')}"
            if key not in advocates:
                advocates[key] = {
                    "first_name": first,
                    "last_name": last or "",
                    "company_name": company,
                    "job_title": safe_str(row.get("Job Title")),
                    "email": email,
                    "industry": None,
                    "country": safe_str(row.get("Country")),
                    "willing_to": [],
                    "person_source": safe_str(row.get("Person Source")),
                }
            else:
                # Fill gaps
                existing = advocates[key]
                if not existing.get("job_title"):
                    existing["job_title"] = safe_str(row.get("Job Title"))
                if not existing.get("country"):
                    existing["country"] = safe_str(row.get("Country"))
                if not existing.get("person_source"):
                    existing["person_source"] = safe_str(row.get("Person Source"))
    except Exception as e:
        logger.error("Failed to read Customer Advocates", error=str(e))

    result = list(advocates.values())
    logger.info("Advocates imported", count=len(result))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Database insertion
# ─────────────────────────────────────────────────────────────────────────────


def _sanitize_value(value: Any) -> Any:
    """Convert pandas NaT/NaN to None for database insertion."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def insert_all(
    engine: Any,
    customers: list[dict],
    case_studies: list[dict],
    quotes: list[dict],
    proofpoints: list[dict],
    advocates: list[dict],
    dry_run: bool = False,
) -> dict[str, int]:
    """Insert all evidence data into the database. Returns row counts."""
    import json

    counts: dict[str, int] = {}

    if dry_run:
        counts = {
            "algolia_customers": len(customers),
            "algolia_case_studies": len(case_studies),
            "algolia_quotes": len(quotes),
            "algolia_proofpoints": len(proofpoints),
            "algolia_advocates": len(advocates),
        }
        logger.info("DRY RUN — would insert", **counts)
        return counts

    with Session(engine) as session:
        try:
            # Clear existing data (idempotent reimport)
            for table in [
                "algolia_advocates", "algolia_proofpoints", "algolia_quotes",
                "algolia_case_studies", "algolia_customers",
            ]:
                session.execute(text(f"DELETE FROM {table}"))
                logger.info("Cleared table", table=table)

            # Insert customers
            sv = _sanitize_value  # alias for brevity
            for cust in customers:
                session.execute(
                    text("""
                        INSERT INTO algolia_customers
                        (id, company_name, industry, sub_vertical, country, website,
                         arr_range, hierarchy_segment, features_used, ecommerce_platform,
                         logo_rights, case_study_consent, publicity_consent, reference_consent,
                         signed_date, go_live_date, competitor_replaced, notes)
                        VALUES
                        (:id, :company_name, :industry, :sub_vertical, :country, :website,
                         :arr_range, :hierarchy_segment, CAST(:features_used AS jsonb), :ecommerce_platform,
                         :logo_rights, :case_study_consent, :publicity_consent, :reference_consent,
                         :signed_date, :go_live_date, :competitor_replaced, :notes)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "company_name": cust["company_name"],
                        "industry": sv(cust.get("industry")) or "Unknown",
                        "sub_vertical": sv(cust.get("sub_vertical")),
                        "country": sv(cust.get("country")),
                        "website": sv(cust.get("website")),
                        "arr_range": sv(cust.get("arr_range")),
                        "hierarchy_segment": sv(cust.get("hierarchy_segment")),
                        "features_used": json.dumps(cust.get("features_used", [])),
                        "ecommerce_platform": sv(cust.get("ecommerce_platform")),
                        "logo_rights": bool(cust.get("logo_rights", False)),
                        "case_study_consent": bool(cust.get("case_study_consent", False)),
                        "publicity_consent": bool(cust.get("publicity_consent", False)),
                        "reference_consent": bool(cust.get("reference_consent", False)),
                        "signed_date": sv(cust.get("signed_date")),
                        "go_live_date": sv(cust.get("go_live_date")),
                        "competitor_replaced": sv(cust.get("competitor_replaced")),
                        "notes": sv(cust.get("notes")),
                    },
                )
            counts["algolia_customers"] = len(customers)

            # Insert case studies
            for cs in case_studies:
                session.execute(
                    text("""
                        INSERT INTO algolia_case_studies
                        (id, customer_name, url, industry, sub_vertical, country,
                         use_case, features_used, competitor_takeout, partner_integrations,
                         key_results, status)
                        VALUES
                        (:id, :customer_name, :url, :industry, :sub_vertical, :country,
                         :use_case, CAST(:features_used AS jsonb), :competitor_takeout, :partner_integrations,
                         :key_results, :status)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "customer_name": cs["customer_name"],
                        "url": cs.get("url"),
                        "industry": cs.get("industry") or "Unknown",
                        "sub_vertical": cs.get("sub_vertical"),
                        "country": cs.get("country"),
                        "use_case": cs.get("use_case"),
                        "features_used": json.dumps(cs.get("features_used", [])),
                        "competitor_takeout": cs.get("competitor_takeout"),
                        "partner_integrations": cs.get("partner_integrations"),
                        "key_results": cs.get("key_results"),
                        "status": cs.get("status") or "Complete",
                    },
                )
            counts["algolia_case_studies"] = len(case_studies)

            # Insert quotes
            for q in quotes:
                session.execute(
                    text("""
                        INSERT INTO algolia_quotes
                        (id, customer_name, person_name, person_title, industry, country,
                         quote_text, evidence_type, source, tags)
                        VALUES
                        (:id, :customer_name, :person_name, :person_title, :industry, :country,
                         :quote_text, :evidence_type, :source, CAST(:tags AS jsonb))
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "customer_name": q["customer_name"],
                        "person_name": q["person_name"],
                        "person_title": q.get("person_title"),
                        "industry": q.get("industry") or "Unknown",
                        "country": q.get("country"),
                        "quote_text": q["quote_text"],
                        "evidence_type": q.get("evidence_type"),
                        "source": q.get("source"),
                        "tags": json.dumps(q.get("tags")) if q.get("tags") else None,
                    },
                )
            counts["algolia_quotes"] = len(quotes)

            # Insert proofpoints
            for pp in proofpoints:
                session.execute(
                    text("""
                        INSERT INTO algolia_proofpoints
                        (id, result_text, source, proof_type, industry, customer_or_theme, shareable)
                        VALUES
                        (:id, :result_text, :source, :proof_type, :industry, :customer_or_theme, :shareable)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "result_text": pp["result_text"],
                        "source": pp.get("source"),
                        "proof_type": pp.get("proof_type") or "Aggregated Results",
                        "industry": pp.get("industry") or "Unknown",
                        "customer_or_theme": pp.get("customer_or_theme"),
                        "shareable": pp.get("shareable", True),
                    },
                )
            counts["algolia_proofpoints"] = len(proofpoints)

            # Insert advocates
            for adv in advocates:
                session.execute(
                    text("""
                        INSERT INTO algolia_advocates
                        (id, first_name, last_name, company_name, job_title, email,
                         industry, country, willing_to, person_source)
                        VALUES
                        (:id, :first_name, :last_name, :company_name, :job_title, :email,
                         :industry, :country, CAST(:willing_to AS jsonb), :person_source)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "first_name": adv["first_name"],
                        "last_name": adv.get("last_name") or "",
                        "company_name": adv["company_name"],
                        "job_title": adv.get("job_title"),
                        "email": adv.get("email"),
                        "industry": adv.get("industry"),
                        "country": adv.get("country"),
                        "willing_to": json.dumps(adv.get("willing_to", [])),
                        "person_source": adv.get("person_source"),
                    },
                )
            counts["algolia_advocates"] = len(advocates)

            session.commit()
            logger.info("All evidence data inserted", **counts)

        except Exception as e:
            session.rollback()
            logger.exception("Failed to insert evidence data", error=str(e))
            raise

    return counts


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    """Run the full import pipeline."""
    parser = argparse.ArgumentParser(description="Import Algolia customer evidence from Excel")
    parser.add_argument(
        "--excel-path",
        type=Path,
        default=DEFAULT_EXCEL_PATH,
        help="Path to CustomerEvidence-Algolia.xlsx",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse but don't insert into DB")
    args = parser.parse_args()

    excel_path = args.excel_path
    if not excel_path.exists():
        logger.error("Excel file not found", path=str(excel_path))
        sys.exit(1)

    logger.info("Starting customer evidence import", path=str(excel_path), dry_run=args.dry_run)

    xls = pd.ExcelFile(excel_path, engine="openpyxl")
    logger.info("Excel file loaded", sheet_count=len(xls.sheet_names), sheets=xls.sheet_names)

    # Parse all data
    customers = import_customers(xls)
    case_studies = import_case_studies(xls)
    quotes = import_quotes(xls)
    proofpoints = import_proofpoints(xls)
    advocates = import_advocates(xls)

    logger.info(
        "Parsing complete",
        customers=len(customers),
        case_studies=len(case_studies),
        quotes=len(quotes),
        proofpoints=len(proofpoints),
        advocates=len(advocates),
    )

    if args.dry_run:
        insert_all(None, customers, case_studies, quotes, proofpoints, advocates, dry_run=True)
        return

    # Use sync engine for the import script (simpler than async)
    sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(sync_url)

    counts = insert_all(engine, customers, case_studies, quotes, proofpoints, advocates)

    logger.info("Import complete", **counts)
    total = sum(counts.values())
    print(f"\n{'='*60}")
    print("IMPORT COMPLETE")
    print(f"{'='*60}")
    for table, count in counts.items():
        print(f"  {table}: {count} rows")
    print(f"  TOTAL: {total} rows")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
