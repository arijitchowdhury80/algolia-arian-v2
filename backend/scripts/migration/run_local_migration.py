"""PRISM historical audit -> PERSISTENT local Postgres migration.

Runs entirely on your machine. Does NOT touch the live VPS or the live
Postgres instance. Spins up (or reuses) a PERSISTENT `postgres:16` Docker
container on 127.0.0.1:55432 with a named volume, creates the schema from
the current `prism_platform/db/models.py` (picks up the `audit_data` JSONB
column + `Numeric(3,2)` score added in alembic 009), loads all 18 published
historical audits into it, round-trip verifies every row against the
`audit_data` column, and leaves the container running so `serve_local.py`
(and you, browsing it later) can read from it.

Idempotent: safe to run again. The container is reused if it already
exists; every audit row has a deterministic id (uuid5 of its slug), so a
second run upserts in place instead of duplicating rows.

Run: python3 scripts/migration/run_local_migration.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

# Make sibling module `_etl` importable regardless of how this script is
# invoked (direct `python3 scripts/migration/run_local_migration.py` or
# `python3 -m scripts.migration.run_local_migration`).
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _etl
from sqlalchemy import create_engine

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLISHED_DIR = REPO_ROOT / "docs" / "workspace" / "migration-dryrun" / "published"
GROUNDING_DIR = Path("/Users/arijitchowdhury/prism-data/hermes-prism/reports")
REPORT_PATH = REPO_ROOT / "docs" / "workspace" / "migration-dryrun" / "LOCAL-INSTANCE.md"

CONTAINER_NAME = "prism-local-db"
VOLUME_NAME = "prism-local-pgdata"
LOCAL_PORT = 55432
LOCAL_USER = "prism"
LOCAL_PASSWORD = "localdev"
LOCAL_DB = "prism"
DSN = f"postgresql+psycopg2://{LOCAL_USER}:{LOCAL_PASSWORD}@127.0.0.1:{LOCAL_PORT}/{LOCAL_DB}"

SERVER_URL = "http://127.0.0.1:8099/"


# =============================================================================
# Persistent Docker Postgres lifecycle -- reuse, never tear down
# =============================================================================


def _container_status() -> str | None:
    """Return docker's Status string for the container, or None if it doesn't exist."""
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Status}}", CONTAINER_NAME],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def docker_ensure_running() -> None:
    status = _container_status()
    if status is None:
        print(f"[local-db] {CONTAINER_NAME} does not exist -- creating persistent container ...")
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                CONTAINER_NAME,
                "-e",
                f"POSTGRES_USER={LOCAL_USER}",
                "-e",
                f"POSTGRES_PASSWORD={LOCAL_PASSWORD}",
                "-e",
                f"POSTGRES_DB={LOCAL_DB}",
                "-p",
                f"127.0.0.1:{LOCAL_PORT}:5432",
                "-v",
                f"{VOLUME_NAME}:/var/lib/postgresql/data",
                "postgres:16",
            ],
            check=True,
        )
        return
    if status == "running":
        print(f"[local-db] {CONTAINER_NAME} already running -- reusing.")
        return
    print(f"[local-db] {CONTAINER_NAME} exists but is '{status}' -- starting it ...")
    subprocess.run(["docker", "start", CONTAINER_NAME], check=True)


def docker_wait_ready(timeout_s: int = 60) -> None:
    """Poll with a real SELECT 1 over psycopg2 -- pg_isready gives false-ready
    during initdb on a fresh container."""
    import psycopg2

    deadline = time.time() + timeout_s
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=LOCAL_PORT,
                user=LOCAL_USER,
                password=LOCAL_PASSWORD,
                dbname=LOCAL_DB,
                connect_timeout=3,
            )
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            conn.close()
            print("[local-db] ready.")
            return
        except Exception as e:
            last_err = e
            time.sleep(1)
    raise RuntimeError(f"local DB never became ready within {timeout_s}s: {last_err}")


# =============================================================================
# Report generation
# =============================================================================


def render_report(
    results: list[_etl.SlugResult], rowcounts: dict[str, int]
) -> str:
    lines: list[str] = []
    lines.append("# PRISM Local Instance -- persistent Postgres + browsable reports")
    lines.append("")
    lines.append(
        "Runs entirely on this machine. The live VPS and live Postgres were never touched."
    )
    lines.append(
        f"Data lives in a **persistent** `postgres:16` Docker container (`{CONTAINER_NAME}`,"
    )
    lines.append(
        f"named volume `{VOLUME_NAME}`) on `127.0.0.1:{LOCAL_PORT}` -- it is NOT torn down"
    )
    lines.append("after this script runs, and survives `docker stop` / machine restarts.")
    lines.append("")
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    lines.append("")

    lines.append("## How to start/stop")
    lines.append("")
    lines.append("```bash")
    lines.append("# Start (or reuse) the persistent local DB:")
    lines.append(f"docker start {CONTAINER_NAME}   # no-op if already running")
    lines.append("")
    lines.append("# Re-run the migration (idempotent -- safe any time):")
    lines.append("python3 scripts/migration/run_local_migration.py")
    lines.append("")
    lines.append("# Start the local browsable server (serves FROM the DB):")
    lines.append("python3 -m scripts.migration.serve_local")
    lines.append(f"# then open {SERVER_URL}")
    lines.append("")
    lines.append("# Stop the DB when done (data persists in the named volume):")
    lines.append(f"docker stop {CONTAINER_NAME}")
    lines.append("```")
    lines.append("")

    n_ok = sum(1 for r in results if r.roundtrip_ok)
    n_fail = sum(1 for r in results if r.roundtrip_ok is False)
    n_err = sum(1 for r in results if r.error)
    lines.append("## Round-trip result")
    lines.append("")
    lines.append(f"- Slugs processed: {len(results)}")
    lines.append(f"- Round-trip PASS: {n_ok}")
    lines.append(f"- Round-trip FAIL: {n_fail}")
    lines.append(f"- Load errors: {n_err}")
    lines.append(
        "- Verifies: `audits.audit_data` deep-equals the source `window.AUDIT_DATA` blob, "
        "`audits.score` matches the parsed `score.overall` **exactly** (now that the column "
        "is `Numeric(3,2)` -- jbl=1.93, nike=4.32 both store and read back with no rounding), "
        "and `accounts.domain` matches the canonical domain."
    )
    lines.append("")

    lines.append("## Local DB rowcounts")
    lines.append("")
    for table, count in rowcounts.items():
        lines.append(f"- `{table}`: {count}")
    lines.append("")
    lines.append("Check live any time with:")
    lines.append("```bash")
    lines.append(
        f'docker exec -it {CONTAINER_NAME} psql -U {LOCAL_USER} -d {LOCAL_DB} -c '
        '"SELECT count(*) FROM accounts;"'
    )
    lines.append("```")
    lines.append("")

    lines.append("## Per-slug results")
    lines.append("")
    lines.append("| slug | domain | score | #module_execs | round-trip |")
    lines.append("|---|---|---|---|---|")
    for r in results:
        if r.error:
            lines.append(f"| {r.slug} | -- | -- | -- | ERROR: {r.error} |")
            continue
        rt = "PASS" if r.roundtrip_ok else "FAIL"
        lines.append(f"| {r.slug} | {r.domain} | {r.score} | {r.module_exec_count} | {rt} |")
    lines.append("")

    if n_fail:
        lines.append("## FAILURES (detail)")
        lines.append("")
        for r in results:
            if r.roundtrip_ok is False:
                lines.append(f"- **{r.slug}**: {r.roundtrip_detail}")
        lines.append("")

    lines.append("## Local instance URL")
    lines.append("")
    lines.append(f"`{SERVER_URL}` -- index page listing every migrated audit with score + link.")
    lines.append("Each report page is rendered by pulling `audit_data` for that slug out of")
    lines.append("Postgres and injecting it into the published report shell -- provably served")
    lines.append("from the DB, not the static file on disk.")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    docker_ensure_running()
    docker_wait_ready()

    engine = create_engine(DSN, future=True)
    try:
        results, rowcounts = _etl.run_migration(engine, PUBLISHED_DIR, GROUNDING_DIR)
    finally:
        engine.dispose()

    report = render_report(results, rowcounts)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print("\n" + "=" * 80)
    print(report)
    print("=" * 80)
    print(f"\n[migrate] report written to {REPORT_PATH}")
    print(f"[local-db] {CONTAINER_NAME} left RUNNING (persistent) on 127.0.0.1:{LOCAL_PORT}")

    n_fail = sum(1 for r in results if r.roundtrip_ok is False)
    n_err = sum(1 for r in results if r.error)
    if n_fail or n_err:
        print(f"\n[migrate] FAILED: {n_fail} round-trip failures, {n_err} load errors")
        return 1
    print(f"\n[migrate] SUCCESS: {len(results)}/{len(results)} slugs round-trip PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
