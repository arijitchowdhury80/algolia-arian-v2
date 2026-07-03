"""Shared ETL logic for PRISM historical audit -> Postgres migration.

Parsing, mapping, and round-trip verification logic, factored out of the
proven dry-run migration (dryrun_migrate.py, 16/18 exact round-trip on a
scratch DB) so the real local migration (run_local_migration.py) reuses the
identical algorithm instead of re-deriving it. Nothing here talks to Docker
or picks a DSN -- callers own the engine/connection lifecycle.

Difference from the dry run: this version writes the full AUDIT_DATA blob
into the dedicated `audits.audit_data` JSONB column (added in alembic 009),
not `config`, and gives every audit a deterministic UUID (uuid5 of the slug)
so re-running the migration upserts in place instead of duplicating rows --
this is what makes the local migration idempotent/re-runnable.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from prism_platform.db.models import Account, Audit, Deliverable, ModuleExecution

AUDIT_DATA_RE = re.compile(r"window\.AUDIT_DATA\s*=\s*(\{.*?\})\s*;?\s*</script>", re.S)

# section key in AUDIT_DATA -> pipeline module name it originated from
SECTION_MODULE_MAP: dict[str, str] = {
    "company_snapshot": "algolia-intel-company",
    "tech_stack": "algolia-intel-techstack",
    "traffic": "algolia-intel-traffic",
    "competitors": "algolia-intel-competitors",
    "hiring": "algolia-intel-hiring",
    "executives": "algolia-intel-investor",
    "partner_intel": "algolia-intel-partner",
    "industry_context": "algolia-intel-industry",
    # financials module name depends on is_public, resolved per-audit below
}
FINANCIALS_KEY = "financials"

# everything else that constitutes the synthesized report deliverable
REPORT_SECTION_KEYS = [
    "score",
    "cover",
    "findings",
    "gap_pairs",
    "toc",
    "intelligence_signals",
    "competitive_synthesis",
    "golden_angle",
    "strategic_angles",
    "icp_mapping",
    "ae_fields",
    "next_steps",
    "methodology",
    "bibliography",
    "recommended_first_play",
    "case_studies",
    "demos",
    "abx_sequence",
    "tab_subtitles",
]

DEDUP_DOMAIN_ALIASES = {
    # both slugs resolve to the same real-world domain/company; reconciled to one account
    "oriental-trading": "orientaltrading.com",
    "orientaltrading": "orientaltrading.com",
}


# =============================================================================
# Small helpers -- money/number parsing (never strip-then-parseFloat; that's
# unit-blind and silently corrupts every "$1.2B" style figure).
# =============================================================================

_MONEY_RE = re.compile(r"\$?\s*([\d,]+(?:\.\d+)?)\s*([BMK])?", re.I)
_UNIT_MULT = {"B": 1_000_000_000, "M": 1_000_000, "K": 1_000}


def parse_money_amount(text: Any) -> float | None:
    """Parse a figure like '$113.5B (FY2026)' or '27.76M' into a float dollar amount.

    Returns None (never a fabricated number) if no numeric token is found.
    """
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    if not isinstance(text, str):
        return None
    m = _MONEY_RE.search(text)
    if not m:
        return None
    raw, unit = m.groups()
    try:
        value = float(raw.replace(",", ""))
    except ValueError:
        return None
    if unit:
        value *= _UNIT_MULT[unit.upper()]
    return value


def parse_int_loose(text: Any) -> int | None:
    """Extract the first integer-looking token from an int or a free-text string."""
    if text is None:
        return None
    if isinstance(text, bool):
        return None
    if isinstance(text, int):
        return text
    if isinstance(text, float):
        return int(text)
    if not isinstance(text, str):
        return None
    m = re.search(r"\d[\d,]*", text)
    if not m:
        return None
    try:
        return int(m.group(0).replace(",", ""))
    except ValueError:
        return None


def parse_year(text: Any) -> int | None:
    """Extract a plausible founding year (18xx/19xx/20xx) from free text."""
    if text is None:
        return None
    if isinstance(text, int):
        return text
    if not isinstance(text, str):
        return None
    m = re.search(r"\b(1[89]\d{2}|20\d{2})\b", text)
    return int(m.group(1)) if m else None


def parse_score_overall(score: Any) -> float | None:
    if score is None:
        return None
    if isinstance(score, dict):
        v = score.get("overall")
        return float(v) if v is not None else None
    if isinstance(score, (int, float)):
        return float(score)
    return None


def audit_id_for_slug(slug: str) -> uuid.UUID:
    """Deterministic audit id so re-running the migration upserts in place."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"prism-local-migration://{slug}")


# =============================================================================
# Data classes for gap / reconciliation tracking
# =============================================================================


@dataclass
class SlugResult:
    slug: str
    domain: str = ""
    company_name: str = ""
    account_id: str | None = None
    audit_id: str | None = None
    score: float | None = None
    module_exec_count: int = 0
    gaps: list[str] = field(default_factory=list)
    roundtrip_ok: bool | None = None
    roundtrip_detail: str = ""
    has_grounding: bool = False
    error: str | None = None


# =============================================================================
# AUDIT_DATA loading
# =============================================================================


def load_published(published_dir: Path, slug: str) -> dict[str, Any]:
    path = published_dir / slug / "index.html"
    html = path.read_text(encoding="utf-8", errors="replace")
    m = AUDIT_DATA_RE.search(html)
    if not m:
        raise ValueError(f"window.AUDIT_DATA not found in {path}")
    return json.loads(m.group(1))


def load_grounding(grounding_dir: Path, slug: str) -> dict[str, Any] | None:
    path = grounding_dir / slug / "audit-data.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def published_slugs(published_dir: Path) -> list[str]:
    return sorted(p.name for p in published_dir.iterdir() if (p / "index.html").is_file())


# =============================================================================
# Mapping: AUDIT_DATA -> ORM rows
# =============================================================================


def canonical_domain(slug: str, data: dict[str, Any]) -> str:
    if slug in DEDUP_DOMAIN_ALIASES:
        return DEDUP_DOMAIN_ALIASES[slug]
    domain = (data.get("meta", {}) or {}).get("domain") or (
        data.get("company_snapshot", {}) or {}
    ).get("domain")
    if not domain:
        raise ValueError(f"no domain found for slug {slug}")
    return domain.strip().lower()


def build_account_fields(data: dict[str, Any], gaps: list[str]) -> dict[str, Any]:
    snap = data.get("company_snapshot") or {}
    meta = data.get("meta") or {}

    company_name = snap.get("name") or meta.get("company")
    if not company_name:
        gaps.append("account.company_name: missing in both company_snapshot.name and meta.company")

    headquarters = snap.get("hq")
    if not headquarters:
        gaps.append("account.headquarters: missing (company_snapshot.hq)")

    employee_count = parse_int_loose(snap.get("employees"))
    if snap.get("employees") is not None and employee_count is None:
        gaps.append(f"account.employee_count: unparseable value {snap.get('employees')!r}")
    elif snap.get("employees") is None:
        gaps.append("account.employee_count: missing (company_snapshot.employees)")

    year_founded = parse_year(snap.get("founded"))
    if snap.get("founded") is not None and year_founded is None:
        gaps.append(f"account.year_founded: unparseable value {snap.get('founded')!r}")
    elif snap.get("founded") is None:
        gaps.append("account.year_founded: missing (company_snapshot.founded)")

    ticker = snap.get("ticker")
    is_public = bool(ticker)

    revenue_estimate = parse_money_amount(snap.get("revenue"))
    if snap.get("revenue") is not None and revenue_estimate is None:
        gaps.append(f"account.revenue_estimate: unparseable value {snap.get('revenue')!r}")
    elif snap.get("revenue") is None:
        gaps.append("account.revenue_estimate: missing (company_snapshot.revenue)")

    industry = snap.get("industry")
    if not industry:
        gaps.append("account.industry: missing (company_snapshot.industry)")

    business_model = snap.get("business_model")

    subsidiaries = snap.get("portfolio_brands") or []
    parent_company = snap.get("parent_entity")

    executives = data.get("executives") or []
    competitors = data.get("competitors") or []

    # AUDIT_DATA carries no dedicated news array (news-like signals are folded
    # into intelligence_signals / findings) -- flag rather than fabricate a
    # structured news list out of unrelated fields.
    gaps.append(
        "account.recent_news: no dedicated news array in AUDIT_DATA "
        "(news-like content is embedded in intelligence_signals/findings, not extracted)"
    )
    # AUDIT_DATA carries no LinkedIn/Twitter/YouTube URLs, no has_search_bar
    # flag, no product_categories, no recent_blog_posts, no field-level
    # source citation array -- these Account columns have no source in the
    # audit-data shape at all.
    gaps.append(
        "account.company_linkedin_url / twitter_handle / youtube_url / has_search_bar / "
        "product_categories / recent_blog_posts / sources: no corresponding field in AUDIT_DATA "
        "(schema-vs-source shape gap, not a per-company data gap)"
    )

    return {
        "company_name": company_name or "UNKNOWN",
        "legal_name": None,
        "headquarters": headquarters,
        "employee_count": employee_count,
        "year_founded": year_founded,
        "business_model": business_model,
        "industry": industry,
        "is_public": is_public,
        "ticker": ticker,
        "parent_company": parent_company,
        "parent_domain": None,
        "subsidiaries": subsidiaries,
        "revenue_estimate": revenue_estimate,
        "revenue_source": snap.get("revenue_source"),
        "executives": executives,
        "competitors": competitors,
    }


def upsert_account(session: Session, domain: str, account_fields: dict[str, Any]) -> uuid.UUID:
    """Real Postgres `INSERT ... ON CONFLICT (domain) DO UPDATE`, so this is
    genuinely idempotent/re-runnable against a non-fresh DB, not just
    deduped in Python. On conflict, COALESCE(existing, excluded) keeps
    whatever the first-processed slug already wrote and only fills columns
    the existing row left null/empty -- never overwrites a present value
    with a null one. This is what handles the oriental-trading /
    orientaltrading dedup (both resolve to domain=orientaltrading.com)."""
    stmt = pg_insert(Account).values(id=uuid.uuid4(), domain=domain, **account_fields)
    update_set = {
        k: func.coalesce(getattr(Account, k), getattr(stmt.excluded, k)) for k in account_fields
    }
    stmt = stmt.on_conflict_do_update(index_elements=["domain"], set_=update_set).returning(
        Account.id
    )
    return session.execute(stmt).scalar_one()


def build_module_executions(
    audit_id: uuid.UUID, domain: str, data: dict[str, Any], gaps: list[str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(module_name: str, payload: Any) -> None:
        has_data = (
            bool(payload) if not isinstance(payload, (int, float, bool)) else payload is not None
        )
        rows.append(
            {
                "id": uuid.uuid4(),
                "audit_id": audit_id,
                "domain": domain,
                "module_name": module_name,
                "module_version": "migrated",
                "status": "completed" if has_data else "skipped",
                "output_json": payload if has_data else None,
            }
        )
        if not has_data:
            gaps.append(
                f"module_executions[{module_name}]: source section empty/missing, marked skipped"
            )

    for section_key, module_name in SECTION_MODULE_MAP.items():
        add(module_name, data.get(section_key))

    is_public = bool((data.get("company_snapshot") or {}).get("ticker"))
    financial_module = (
        "algolia-intel-financial-public" if is_public else "algolia-intel-financial-private"
    )
    add(financial_module, data.get(FINANCIALS_KEY))

    report_payload = {k: data.get(k) for k in REPORT_SECTION_KEYS if data.get(k) is not None}
    add("algolia-audit-report", report_payload)

    return rows


def build_deliverables(data: dict[str, Any], gaps: list[str]) -> list[dict[str, Any]]:
    # No deliverable file references (deck/landing/pdf/playbook file_url or
    # file_key) exist anywhere in AUDIT_DATA for any of the 18 published
    # reports -- verified by full-text scan. Do not fabricate file_urls.
    gaps.append(
        "deliverables: no deck/landing/pdf/playbook file_url or file_key present in AUDIT_DATA; "
        "0 deliverable rows created for this audit (not fabricated)"
    )
    return []


def deep_equal_jsonable(a: Any, b: Any) -> bool:
    """Compare via JSON round-trip so tuple/list and Decimal/float mismatches
    introduced purely by the DB round-trip don't produce false failures."""
    return json.loads(json.dumps(a, default=str)) == json.loads(json.dumps(b, default=str))


# =============================================================================
# Full migration loop -- writes into audits.audit_data (not config), with a
# deterministic audit id per slug so re-runs upsert instead of duplicating.
# =============================================================================


def run_migration(
    engine: Any,
    published_dir: Path,
    grounding_dir: Path | None,
) -> tuple[list[SlugResult], dict[str, int]]:
    from prism_platform.db.models import Base

    Base.metadata.create_all(engine)

    results: list[SlugResult] = []
    domain_to_account_id: dict[str, uuid.UUID] = {}

    slugs = published_slugs(published_dir)
    print(f"[migrate] {len(slugs)} published slugs: {slugs}")

    with Session(engine) as session:
        for slug in slugs:
            res = SlugResult(slug=slug)
            try:
                data = load_published(published_dir, slug)
            except Exception as e:
                res.error = f"failed to load/parse published data: {e}"
                results.append(res)
                continue

            grounding = load_grounding(grounding_dir, slug) if grounding_dir else None
            res.has_grounding = grounding is not None

            gaps: list[str] = []

            if grounding is not None:
                g_score = parse_score_overall(grounding.get("score"))
                p_score = parse_score_overall(data.get("score"))
                if g_score is not None and p_score is not None and abs(g_score - p_score) >= 0.05:
                    gaps.append(
                        f"cross-check: grounding-store score ({g_score}) differs from published "
                        f"score ({p_score}); published treated as PRIMARY per instructions, "
                        "grounding-store value not used"
                    )

            domain = canonical_domain(slug, data)
            res.domain = domain
            account_fields = build_account_fields(data, gaps)
            res.company_name = account_fields["company_name"]

            # --- account upsert (dedup by domain, real ON CONFLICT DO UPDATE) ---
            was_seen_before = domain in domain_to_account_id
            account_id = upsert_account(session, domain, account_fields)
            domain_to_account_id[domain] = account_id
            if was_seen_before:
                gaps.append(
                    f"account dedup: domain {domain} already had an account from a prior slug; "
                    "ON CONFLICT (domain) DO UPDATE ran, COALESCE(existing, new) merge applied"
                )

            res.account_id = str(account_id)

            # --- audit (deterministic id per slug -> idempotent upsert) ---
            score = parse_score_overall(data.get("score"))
            res.score = score
            if score is None:
                gaps.append("audit.score: could not parse score.overall")

            meta = data.get("meta") or {}
            completed_at = None
            audit_date = meta.get("audit_date")
            if audit_date:
                try:
                    completed_at = datetime.strptime(audit_date, "%Y-%m-%d")
                except ValueError:
                    gaps.append(f"audit.completed_at: unparseable audit_date {audit_date!r}")
            else:
                gaps.append("audit.completed_at: missing meta.audit_date")

            # AUDIT_DATA does not carry a factcheck_score/action field anywhere
            # in the 18 published reports -- the factcheck gate result is not
            # persisted into the rendered page. Flagged, not fabricated.
            gaps.append(
                "audit.factcheck_score / factcheck_action: not present in AUDIT_DATA "
                "(factcheck-mechanical gate result is not persisted into the rendered report)"
            )

            audit_id = audit_id_for_slug(slug)
            audit_values = {
                "id": audit_id,
                "account_id": account_id,
                "user_id": "system",
                "status": "completed",
                "score": score,
                "factcheck_score": None,
                "factcheck_action": None,
                "config": {"migration_source": "published-html-local", "slug": slug},
                "audit_data": data,
                "completed_at": completed_at,
            }
            stmt = pg_insert(Audit).values(**audit_values)
            update_cols = ["account_id", "status", "score", "config", "audit_data", "completed_at"]
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={c: getattr(stmt.excluded, c) for c in update_cols},
            )
            session.execute(stmt)
            res.audit_id = str(audit_id)

            # --- module executions (upsert on the audit_id+module_name unique constraint) ---
            module_rows = build_module_executions(audit_id, domain, data, gaps)
            for row in module_rows:
                mstmt = pg_insert(ModuleExecution).values(**row)
                mstmt = mstmt.on_conflict_do_update(
                    index_elements=["audit_id", "module_name"],
                    set_={
                        "status": mstmt.excluded.status,
                        "output_json": mstmt.excluded.output_json,
                        "module_version": mstmt.excluded.module_version,
                    },
                )
                session.execute(mstmt)
            res.module_exec_count = len(module_rows)

            # --- deliverables (none in source; delete-then-reinsert keeps it idempotent) ---
            session.query(Deliverable).filter(Deliverable.audit_id == audit_id).delete()
            deliverable_rows = build_deliverables(data, gaps)
            for row in deliverable_rows:
                session.add(Deliverable(audit_id=audit_id, **row))

            res.gaps = gaps
            results.append(res)

        session.commit()

    # --- round-trip verification against audit_data (not config) ---
    with Session(engine) as session:
        for res in results:
            if res.error or not res.audit_id:
                continue
            audit = session.get(Audit, uuid.UUID(res.audit_id))
            if audit is None:
                res.roundtrip_ok = False
                res.roundtrip_detail = "audit row not found on re-read"
                continue
            source = load_published(published_dir, res.slug)
            stored = audit.audit_data
            ok = deep_equal_jsonable(source, stored)
            account = session.get(Account, uuid.UUID(res.account_id)) if res.account_id else None
            score_expected = parse_score_overall(source.get("score"))
            score_ok = (score_expected is None and audit.score is None) or (
                score_expected is not None
                and audit.score is not None
                and abs(float(audit.score) - score_expected) < 0.001
            )
            domain_ok = account is not None and account.domain == res.domain
            res.roundtrip_ok = ok and score_ok and domain_ok
            if not res.roundtrip_ok:
                detail = []
                if not ok:
                    detail.append("audit_data != source AUDIT_DATA (deep JSON compare failed)")
                if not score_ok:
                    detail.append(f"score mismatch: stored={audit.score} expected={score_expected}")
                if not domain_ok:
                    actual = account.domain if account else None
                    detail.append(f"domain mismatch: account.domain={actual} expected={res.domain}")
                res.roundtrip_detail = "; ".join(detail)
            else:
                res.roundtrip_detail = "PASS (audit_data, score, domain all match source exactly)"

    with Session(engine) as session:
        rowcounts = {
            "accounts": session.scalar(select(func.count()).select_from(Account)) or 0,
            "audits": session.scalar(select(func.count()).select_from(Audit)) or 0,
            "module_executions": session.scalar(select(func.count()).select_from(ModuleExecution))
            or 0,
            "deliverables": session.scalar(select(func.count()).select_from(Deliverable)) or 0,
        }

    return results, rowcounts
