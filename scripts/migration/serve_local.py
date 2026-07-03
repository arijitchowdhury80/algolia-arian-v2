"""Serve the migrated audits FROM the persistent local Postgres DB.

Reads every audit's `audit_data` JSONB straight out of Postgres (the DB
row created by run_local_migration.py) and injects it into the published
report's HTML shell in place of the shell's own inline `window.AUDIT_DATA`
-- so what you see in the browser is provably rendered from the DB, not
from the static file on disk.

stdlib-only (http.server), 127.0.0.1:8099. Never touches the VPS.

Run: python3 -m scripts.migration.serve_local
Then open: http://127.0.0.1:8099/
"""

from __future__ import annotations

import html
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _etl
import psycopg2
import psycopg2.extras

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLISHED_DIR = REPO_ROOT / "docs" / "workspace" / "migration-dryrun" / "published"

HOST = "127.0.0.1"
PORT = 8099

LOCAL_PORT = 55432
LOCAL_USER = "prism"
LOCAL_PASSWORD = "localdev"
LOCAL_DB = "prism"


def db_connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host="127.0.0.1",
        port=LOCAL_PORT,
        user=LOCAL_USER,
        password=LOCAL_PASSWORD,
        dbname=LOCAL_DB,
        connect_timeout=5,
    )


# =============================================================================
# DB reads
# =============================================================================


def fetch_index_rows() -> list[dict]:
    """All migrated audits, joined to their account, for the index page."""
    sql = """
        SELECT
            a.config ->> 'slug' AS slug,
            acc.company_name AS company_name,
            acc.domain AS domain,
            a.score AS score,
            a.completed_at AS completed_at
        FROM audits a
        JOIN accounts acc ON acc.id = a.account_id
        WHERE a.config ->> 'slug' IS NOT NULL
        ORDER BY acc.company_name ASC;
    """
    conn = db_connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def fetch_audit_data(slug: str) -> tuple[dict | None, float | None, str | None]:
    """Return (audit_data, score, company_name) for one slug, sourced from Postgres."""
    sql = """
        SELECT a.audit_data AS audit_data, a.score AS score, acc.company_name AS company_name
        FROM audits a
        JOIN accounts acc ON acc.id = a.account_id
        WHERE a.config ->> 'slug' = %s
        LIMIT 1;
    """
    conn = db_connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (slug,))
            row = cur.fetchone()
            if row is None:
                return None, None, None
            return row["audit_data"], row["score"], row["company_name"]
    finally:
        conn.close()


# =============================================================================
# Rendering
# =============================================================================


def render_index(rows: list[dict]) -> bytes:
    items = []
    for row in rows:
        slug = row["slug"]
        name = html.escape(row["company_name"] or slug)
        domain = html.escape(row["domain"] or "")
        score = row["score"]
        score_str = f"{float(score):.2f}" if score is not None else "--"
        items.append(
            f'<li><a href="/{html.escape(slug)}/">{name}</a> '
            f'<span class="domain">({domain})</span> '
            f'<span class="score">score: {score_str}</span></li>'
        )
    body = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>PRISM local instance</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 720px; margin: 3rem auto;
  padding: 0 1rem; color: #1a1a2e; }}
h1 {{ font-size: 1.3rem; }}
p.note {{ color: #555; font-size: 0.9rem; }}
ul {{ list-style: none; padding: 0; }}
li {{ padding: 0.5rem 0; border-bottom: 1px solid #eee; }}
a {{ text-decoration: none; color: #003DFF; font-weight: 600; }}
.domain {{ color: #888; font-size: 0.85rem; }}
.score {{ float: right; color: #333; font-size: 0.85rem; }}
</style></head>
<body>
<h1>PRISM local instance -- {len(rows)} migrated audits</h1>
<p class="note">Served from the persistent local Postgres DB (prism-local-db, 127.0.0.1:55432).
Live VPS untouched. Each report below is rendered from the DB row, not a static file.</p>
<ul>
{"".join(items)}
</ul>
</body></html>"""
    return body.encode("utf-8")


def render_report(slug: str, audit_data: dict) -> bytes:
    """Load the published HTML shell for this slug and swap in DB-sourced AUDIT_DATA."""
    shell_path = PUBLISHED_DIR / slug / "index.html"
    html_text = shell_path.read_text(encoding="utf-8", errors="replace")
    new_json = json.dumps(audit_data)
    new_assignment = f"window.AUDIT_DATA = {new_json};</script>"
    # Use a replacement function, not a replacement string: json.dumps output
    # contains backslash escapes (e.g. ') that re.sub's string-replacement
    # path misreads as regex backreferences and rejects with PatternError.
    # A callable replacement is inserted verbatim, no backslash processing.
    replaced, n = _etl.AUDIT_DATA_RE.subn(lambda _m: new_assignment, html_text, count=1)
    if n == 0:
        raise ValueError(f"could not locate window.AUDIT_DATA assignment in shell for {slug}")
    return replaced.encode("utf-8")


# =============================================================================
# HTTP handler
# =============================================================================


class Handler(BaseHTTPRequestHandler):
    server_version = "PRISMLocal/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"[serve_local] {self.address_string()} - {fmt % args}\n")

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = unquote(self.path.split("?", 1)[0])

        try:
            if path == "/" or path == "":
                rows = fetch_index_rows()
                self._send(200, "text/html; charset=utf-8", render_index(rows))
                return

            parts = [p for p in path.split("/") if p]

            if len(parts) == 1:
                # Could be a report slug ("/lululemon" or "/lululemon/") or a
                # stray static asset request ("/chat-widget.js") -- try slug
                # first since that is the actual deliverable; fall through to
                # best-effort static/404 otherwise.
                candidate_slug = parts[0]
                if "." not in candidate_slug:
                    audit_data, score, company_name = fetch_audit_data(candidate_slug)
                    if audit_data is not None:
                        body = render_report(candidate_slug, audit_data)
                        print(
                            f"[serve_local] sourced {len(json.dumps(audit_data))} bytes "
                            f"from DB for {candidate_slug} (score={score}, company={company_name})"
                        )
                        self._send(200, "text/html; charset=utf-8", body)
                        return

            # Best-effort static asset passthrough (e.g. /chat-widget.js) --
            # not present in this repo checkout, so this is expected to 404
            # for most requests. Must never crash the server.
            static_candidate = PUBLISHED_DIR / path.lstrip("/")
            if static_candidate.is_file():
                suffix = static_candidate.suffix.lower()
                content_type = {
                    ".js": "application/javascript",
                    ".css": "text/css",
                    ".png": "image/png",
                    ".svg": "image/svg+xml",
                    ".ico": "image/x-icon",
                    ".woff2": "font/woff2",
                }.get(suffix, "application/octet-stream")
                self._send(200, content_type, static_candidate.read_bytes())
                return

            self._send(404, "text/plain; charset=utf-8", b"404 not found")
        except Exception as e:  # never crash the server on a bad request
            sys.stderr.write(f"[serve_local] ERROR handling {path}: {e!r}\n")
            self._send(500, "text/plain; charset=utf-8", f"500 internal error: {e}".encode())


def main() -> int:
    try:
        conn = db_connect()
        conn.close()
    except Exception as e:
        print(f"[serve_local] FATAL: cannot reach local Postgres at 127.0.0.1:{LOCAL_PORT}: {e}")
        print("[serve_local] start it with: docker start prism-local-db")
        print("[serve_local] (or run: python3 scripts/migration/run_local_migration.py)")
        return 1

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[serve_local] serving migrated audits from Postgres at http://{HOST}:{PORT}/")
    print("[serve_local] Ctrl-C to stop (the DB container keeps running independently)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[serve_local] shutting down (DB container left running)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
