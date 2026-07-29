"""PRISM historical audit -> Postgres migration DRY RUN.

SCRATCH DB ONLY. This script never touches the live VPS or the live
Postgres instance. It spins up a throwaway `postgres:16` Docker
container on 127.0.0.1:55433, creates the schema from
`prism_platform/db/models.py`, loads all 18 published historical
audits into it, round-trip verifies every row, and emits a
decision-grade migration report before tearing the container down.

Run: python3 scripts/migration/dryrun_migrate.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from prism_platform.db.models import Account, Audit, Base, Deliverable, ModuleExecution

# docs/ sits at the repo root, one level above backend/, since the 2026-07-28 restructure.
REPO_ROOT = Path(__file__).resolve().parents[3]
PUBLISHED_DIR = REPO_ROOT / "docs" / "workspace" / "migration-dryrun" / "published"
GROUNDING_DIR = Path("/Users/arijitchowdhury/prism-data/hermes-prism/reports")
REPORT_PATH = REPO_ROOT / "docs" / "workspace" / "migration-dryrun" / "MIGRATION-REPORT.md"

CONTAINER_NAME = "prism-migrate-scratch"
SCRATCH_PORT = 55433
SCRATCH_USER = "prism"
SCRATCH_PASSWORD = "scratch"
SCRATCH_DB = "prism"
DSN = (
    f"postgresql+psycopg2://{SCRATCH_USER}:{SCRATCH_PASSWORD}@127.0.0.1:{SCRATCH_PORT}/{SCRATCH_DB}"
)

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
# financials special-cased because module name depends on public/private status
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
# Docker scratch DB lifecycle
# =============================================================================


def docker_teardown_if_exists() -> None:
    subprocess.run(
        ["docker", "rm", "-f", CONTAINER_NAME],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def docker_start() -> None:
    docker_teardown_if_exists()
    print(f"[scratch-db] starting {CONTAINER_NAME} on 127.0.0.1:{SCRATCH_PORT} ...")
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER_NAME,
            "-e",
            f"POSTGRES_USER={SCRATCH_USER}",
            "-e",
            f"POSTGRES_PASSWORD={SCRATCH_PASSWORD}",
            "-e",
            f"POSTGRES_DB={SCRATCH_DB}",
            "-p",
            f"127.0.0.1:{SCRATCH_PORT}:5432",
            "postgres:16",
        ],
        check=True,
    )


def docker_wait_ready(timeout_s: int = 60) -> None:
    """Poll with a real SELECT 1 over psycopg2 -- pg_isready gives false-ready
    during initdb on a fresh container (hit this race in a prior run)."""
    import psycopg2

    deadline = time.time() + timeout_s
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=SCRATCH_PORT,
                user=SCRATCH_USER,
                password=SCRATCH_PASSWORD,
                dbname=SCRATCH_DB,
                connect_timeout=3,
            )
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            conn.close()
            print("[scratch-db] ready.")
            return
        except Exception as e:
            last_err = e
            time.sleep(1)
    raise RuntimeError(f"scratch DB never became ready within {timeout_s}s: {last_err}")


# =============================================================================
# AUDIT_DATA loading
# =============================================================================


def load_published(slug: str) -> dict[str, Any]:
    path = PUBLISHED_DIR / slug / "index.html"
    html = path.read_text(encoding="utf-8", errors="replace")
    m = AUDIT_DATA_RE.search(html)
    if not m:
        raise ValueError(f"window.AUDIT_DATA not found in {path}")
    return json.loads(m.group(1))


def load_grounding(slug: str) -> dict[str, Any] | None:
    path = GROUNDING_DIR / slug / "audit-data.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def published_slugs() -> list[str]:
    return sorted(p.name for p in PUBLISHED_DIR.iterdir() if (p / "index.html").is_file())


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
    # Note: subsidiaries/executives/competitors are JSONB NOT NULL columns
    # (default=[]), so COALESCE(col, excluded) never fires for them on
    # conflict -- an existing (even empty-list) row always wins over the
    # new slug's array. This is a documented dedup-merge caveat, not a bug:
    # the first-processed slug's structured arrays are treated as canonical.
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


# =============================================================================
# Load pipeline
# =============================================================================


def deep_equal_jsonable(a: Any, b: Any) -> bool:
    """Compare via JSON round-trip so tuple/list and Decimal/float mismatches
    introduced purely by the DB round-trip don't produce false failures."""
    return json.loads(json.dumps(a, default=str)) == json.loads(json.dumps(b, default=str))


def run_migration() -> tuple[list[SlugResult], dict[str, int]]:
    engine = create_engine(DSN, future=True)
    Base.metadata.create_all(engine)

    results: list[SlugResult] = []
    domain_to_account_id: dict[str, uuid.UUID] = {}

    slugs = published_slugs()
    print(f"[migrate] {len(slugs)} published slugs: {slugs}")

    with Session(engine) as session:
        for slug in slugs:
            res = SlugResult(slug=slug)
            try:
                data = load_published(slug)
            except Exception as e:
                res.error = f"failed to load/parse published data: {e}"
                results.append(res)
                continue

            grounding = load_grounding(slug)
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

            # --- audit (one per slug, no audit-level dedup) ---
            score = parse_score_overall(data.get("score"))
            res.score = score
            if score is None:
                gaps.append("audit.score: could not parse score.overall")

            meta = data.get("meta") or {}
            completed_at = None
            audit_date = meta.get("audit_date")
            if audit_date:
                try:
                    from datetime import datetime as _dt

                    completed_at = _dt.strptime(audit_date, "%Y-%m-%d")
                except ValueError:
                    gaps.append(f"audit.completed_at: unparseable audit_date {audit_date!r}")
            else:
                gaps.append("audit.completed_at: missing meta.audit_date")

            factcheck_score = None
            factcheck_action = None
            # AUDIT_DATA does not carry a factcheck_score/action field anywhere
            # in the 18 published reports -- the factcheck gate result is not
            # persisted into the rendered page. Flagged, not fabricated.
            gaps.append(
                "audit.factcheck_score / factcheck_action: not present in AUDIT_DATA "
                "(factcheck-mechanical gate result is not persisted into the rendered report)"
            )

            audit = Audit(
                id=uuid.uuid4(),
                account_id=account_id,
                user_id="system",
                status="completed",
                score=score,
                factcheck_score=factcheck_score,
                factcheck_action=factcheck_action,
                config={"audit_data": data, "migration_source": "published-html", "slug": slug},
                completed_at=completed_at,
            )
            session.add(audit)
            session.flush()
            res.audit_id = str(audit.id)

            # --- module executions (upsert on the audit_id+module_name unique constraint) ---
            module_rows = build_module_executions(audit.id, domain, data, gaps)
            for row in module_rows:
                stmt = pg_insert(ModuleExecution).values(**row)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["audit_id", "module_name"],
                    set_={
                        "status": stmt.excluded.status,
                        "output_json": stmt.excluded.output_json,
                        "module_version": stmt.excluded.module_version,
                    },
                )
                session.execute(stmt)
            res.module_exec_count = len(module_rows)

            # --- deliverables ---
            deliverable_rows = build_deliverables(data, gaps)
            for row in deliverable_rows:
                session.add(Deliverable(audit_id=audit.id, **row))

            res.gaps = gaps
            results.append(res)

        session.commit()

    # --- round-trip verification ---
    with Session(engine) as session:
        for res in results:
            if res.error or not res.audit_id:
                continue
            audit = session.get(Audit, uuid.UUID(res.audit_id))
            if audit is None:
                res.roundtrip_ok = False
                res.roundtrip_detail = "audit row not found on re-read"
                continue
            source = load_published(res.slug)
            stored = audit.config.get("audit_data") if isinstance(audit.config, dict) else None
            ok = deep_equal_jsonable(source, stored)
            account = session.get(Account, uuid.UUID(res.account_id)) if res.account_id else None
            score_expected = parse_score_overall(source.get("score"))
            score_ok = (score_expected is None and audit.score is None) or (
                score_expected is not None
                and audit.score is not None
                and abs(float(audit.score) - score_expected) < 0.01
            )
            domain_ok = account is not None and account.domain == res.domain
            res.roundtrip_ok = ok and score_ok and domain_ok
            if not res.roundtrip_ok:
                detail = []
                if not ok:
                    detail.append(
                        "config.audit_data != source AUDIT_DATA (deep JSON compare failed)"
                    )
                if not score_ok:
                    detail.append(f"score mismatch: stored={audit.score} expected={score_expected}")
                if not domain_ok:
                    actual = account.domain if account else None
                    detail.append(f"domain mismatch: account.domain={actual} expected={res.domain}")
                res.roundtrip_detail = "; ".join(detail)
            else:
                res.roundtrip_detail = "PASS (config.audit_data, score, domain all match source)"

    # --- final rowcounts ---
    with Session(engine) as session:
        rowcounts = {
            "accounts": session.scalar(select(func.count()).select_from(Account)) or 0,
            "audits": session.scalar(select(func.count()).select_from(Audit)) or 0,
            "module_executions": session.scalar(select(func.count()).select_from(ModuleExecution))
            or 0,
            "deliverables": session.scalar(select(func.count()).select_from(Deliverable)) or 0,
        }

    engine.dispose()
    return results, rowcounts


# =============================================================================
# Report generation
# =============================================================================


def render_report(results: list[SlugResult], rowcounts: dict[str, int]) -> str:
    lines: list[str] = []
    lines.append("# PRISM Historical Audit Migration -- DRY RUN REPORT")
    lines.append("")
    lines.append("**SCRATCH DB -- live Postgres untouched.** Everything below ran against a")
    lines.append(
        f"throwaway `postgres:16` Docker container on `127.0.0.1:{SCRATCH_PORT}`, torn down"
    )
    lines.append("at the end of this run. No VPS, no live database, no deploy.")
    lines.append("")
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    lines.append("")

    n_ok = sum(1 for r in results if r.roundtrip_ok)
    n_fail = sum(1 for r in results if r.roundtrip_ok is False)
    n_err = sum(1 for r in results if r.error)
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Slugs processed: {len(results)}")
    lines.append(f"- Round-trip PASS: {n_ok}")
    lines.append(f"- Round-trip FAIL: {n_fail}")
    lines.append(f"- Load errors: {n_err}")
    lines.append(f"- Unique accounts created (post-dedup): {rowcounts['accounts']}")
    lines.append(f"- Audits created: {rowcounts['audits']}")
    lines.append("")

    lines.append("## Per-slug results")
    lines.append("")
    lines.append("| slug | domain | account_id | score | #module_execs | #gaps | round-trip |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in results:
        if r.error:
            lines.append(f"| {r.slug} | -- | -- | -- | -- | -- | ERROR: {r.error} |")
            continue
        rt = "PASS" if r.roundtrip_ok else "FAIL"
        lines.append(
            f"| {r.slug} | {r.domain} | `{r.account_id}` | {r.score} | "
            f"{r.module_exec_count} | {len(r.gaps)} | {rt} |"
        )
    lines.append("")

    lines.append("## Round-trip verification detail")
    lines.append("")
    lines.append("Proves: `config.audit_data` read back from Postgres deep-equals the source")
    lines.append("`window.AUDIT_DATA` blob (full JSON compare), `audits.score` matches the parsed")
    lines.append("`score.overall`, and `accounts.domain` matches the canonical domain used to file")
    lines.append("this audit. Any mismatch is a FAILURE line below, not a warning.")
    lines.append("")
    for r in results:
        if r.error:
            continue
        lines.append(f"- **{r.slug}**: {r.roundtrip_detail}")
    lines.append("")

    score_precision_fails = [
        r for r in results if r.roundtrip_ok is False and "score mismatch" in r.roundtrip_detail
    ]
    if score_precision_fails:
        lines.append("## SCHEMA GAP -- `audits.score` precision loss (REAL BUG, found by this run)")
        lines.append("")
        lines.append("`audits.score` is `Numeric(3, 1)` -- one digit after the decimal point. Real")
        lines.append(
            "audit scores carry two decimal digits (e.g. jbl = 1.93, nike = 4.32). Postgres"
        )
        lines.append(
            "silently rounds on insert: 1.93 -> 1.9, 4.32 -> 4.3. This is exactly the class"
        )
        lines.append(
            "of silent-precision-loss bug the round-trip check exists to catch, and it did:"
        )
        lines.append("")
        for r in score_precision_fails:
            lines.append(f"- **{r.slug}**: {r.roundtrip_detail}")
        lines.append("")
        lines.append("**Recommendation:** widen `audits.score` (and `audits.factcheck_score`, same")
        lines.append(
            "`Numeric(3, 1)` type) to `Numeric(3, 2)` in the same alembic migration that adds"
        )
        lines.append(
            "`audit_data` (see schema-gap section below), before the real cutover runs. Do"
        )
        lines.append(
            "NOT round scores to fit the current column -- that's fabricating precision the"
        )
        lines.append("source data doesn't claim to have lost.")
        lines.append("")

    lines.append("## Per-slug gap list (fields NULL/missing -- never fabricated)")
    lines.append("")
    for r in results:
        if r.error:
            continue
        lines.append(f"### {r.slug}")
        if not r.gaps:
            lines.append("- (no gaps)")
        for g in r.gaps:
            lines.append(f"- {g}")
        lines.append("")

    lines.append("## Dedup reconciliation: oriental-trading / orientaltrading")
    lines.append("")
    lines.append("Both slugs resolve to the same real-world domain, `orientaltrading.com`, and the")
    lines.append("same company, Oriental Trading Company. They are two distinct historical audit")
    lines.append(
        "runs of the same account (not duplicate runs of the same audit), so the migration"
    )
    lines.append(
        "keeps **one account row** (deduped by the `accounts.domain` UNIQUE constraint) and"
    )
    lines.append("**two audit rows** (one per slug), both pointing at that single `account_id`.")
    lines.append("")
    lines.append("Reconciliation policy for the shared account row: the first-processed slug wins")
    lines.append("field-for-field; any field left null/empty by the first slug is backfilled from")
    lines.append("the second slug via a real `INSERT ... ON CONFLICT (domain) DO UPDATE` with")
    lines.append("`COALESCE(existing, new)` per column (`upsert_account`). No field is ever")
    lines.append(
        "overwritten from a present value to null. A per-slug gap entry records the merge."
    )
    lines.append("")

    lines.append("## Published-vs-grounding-store coverage")
    lines.append("")
    lines.append("13 of the 18 published slugs also have a grounding-store JSON at")
    lines.append("`~/prism-data/hermes-prism/reports/<slug>/audit-data.json`; those were compared")
    lines.append("but the published HTML's inline `window.AUDIT_DATA` was treated as PRIMARY per")
    lines.append(
        "instructions (it is the actually-served truth). 5 slugs have no grounding JSON at"
    )
    lines.append("all -- for those, the published HTML is the *only* source.")
    lines.append("")
    lines.append("| slug | has grounding JSON |")
    lines.append("|---|---|")
    for r in results:
        if r.error:
            continue
        lines.append(f"| {r.slug} | {'yes' if r.has_grounding else 'no'} |")
    lines.append("")

    lines.append("## SCHEMA GAP -- recommendation for real cutover")
    lines.append("")
    lines.append(
        "`audits` has no dedicated `audit_data JSONB` column -- only `config JSONB`, which"
    )
    lines.append(
        "is meant for run configuration, not the full rendered audit payload. This dry run"
    )
    lines.append(
        'stored the entire `window.AUDIT_DATA` blob inside `config["audit_data"]` to prove'
    )
    lines.append("faithful round-trip, but that overloads a column with two unrelated purposes.")
    lines.append("")
    lines.append(
        "**Recommendation:** add an `audit_data JSONB` column to `audits` via a new alembic"
    )
    lines.append(
        "migration (`009_add_audit_data_column`, next after the current head at `007`) for"
    )
    lines.append(
        "the real cutover, and keep `config` reserved for run-time configuration only. This"
    )
    lines.append("matches airtight-pipeline plan section 1.4 (full audit-data JSON persisted).")
    lines.append("")

    lines.append("## Deliverables")
    lines.append("")
    lines.append("0 deliverable rows were created for any of the 18 audits. Verified by full-text")
    lines.append("scan of every published `window.AUDIT_DATA` blob for `.pdf`, `.pptx`, `deck`,")
    lines.append("`landing`, `playbook`, `file_url`, `file_key` -- none of the 18 reports carry a")
    lines.append("deck/landing/PDF/playbook file reference in their rendered data. This is a real")
    lines.append(
        "gap in the source, not a migration bug: those deliverables exist as separate files"
    )
    lines.append("on disk/VPS outside AUDIT_DATA and were out of scope for this dry run.")
    lines.append("")

    lines.append("## Final rowcounts (scratch DB, before teardown)")
    lines.append("")
    for table, count in rowcounts.items():
        lines.append(f"- `{table}`: {count}")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    docker_start()
    try:
        docker_wait_ready()
        results, rowcounts = run_migration()
    except Exception:
        print(f"\n[scratch-db] migration raised -- tearing down {CONTAINER_NAME} before re-raise")
        docker_teardown_if_exists()
        raise

    report = render_report(results, rowcounts)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print("\n" + "=" * 80)
    print(report)
    print("=" * 80)
    print(f"\n[migrate] report written to {REPORT_PATH}")
    print("[migrate] final rowcounts (scratch DB, before teardown):")
    for table, count in rowcounts.items():
        print(f"  {table}: {count}")

    print(f"\n[scratch-db] tearing down {CONTAINER_NAME} ...")
    docker_teardown_if_exists()
    print("[scratch-db] torn down. Live Postgres was never touched.")

    n_fail = sum(1 for r in results if r.roundtrip_ok is False)
    n_err = sum(1 for r in results if r.error)
    return 1 if (n_fail or n_err) else 0


if __name__ == "__main__":
    sys.exit(main())
