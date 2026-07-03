"""Post-migration regression harness for PRISM audit reports.

The "prove nothing broke" gate for the DB-as-source-of-truth cutover
(airtight plan section 4.2, P3.2). Loads each PRISM report in a real
browser, captures uncaught JS errors, and asserts the report actually
rendered its data (not just an empty shell).

HTTP 200 + grep is NOT proof a report renders — a render crash only shows
up as an uncaught JS exception in the browser. This harness exists because
that exact failure class has bitten PRISM before (see memory
feedback-grep-validation-insufficient-need-browser-load): a truthy
non-array value reaching `.forEach()` crashed the renderer while the page
still returned HTTP 200 and still contained the right JSON in a grep.

Two modes:

Mode A (default) - LOCAL DRY RUN, safe, run any time:
    Iterates docs/workspace/migration-dryrun/published/<slug>/index.html,
    serves the `published/` directory root over a throwaway local
    http.server (so absolute asset paths like /chat-widget.js resolve the
    same way they would in production), and loads each report at
    http://127.0.0.1:<port>/<slug>/. Missing local assets (404s) are
    EXPECTED and are not a failure condition -- only uncaught JS
    exceptions (pageerror) count.

    Run it:
        python3 scripts/migration/regression_check.py

Mode B (parameterized) - LIVE CHECK, for Arijit to run attended later,
against the real Clerk-gated site:
    python3 scripts/migration/regression_check.py \\
        --base https://prism.chowmes.com \\
        --cookie "__session=<value>" \\
        --slugs dell,lululemon,jbl

    How to grab the cookie: open a logged-in browser session on
    prism.chowmes.com (Clerk auth already completed), open DevTools ->
    Application -> Cookies, and copy the `__session` cookie's value.
    Pass it as `--cookie "__session=<value>"`. Multiple cookies can be
    given semicolon-separated the way a raw Cookie header would be:
    `--cookie "__session=abc; __client_uat=123"`.

This script does NOT touch the live VPS by default and never writes
anywhere outside this repo. Mode B makes real HTTP requests to whatever
--base is given -- only pass a live URL when intentionally checking it.

Output: docs/workspace/migration-dryrun/REGRESSION-REPORT.md (table +
raw pageerror text for any failing report), and the same table printed to
stdout. Exit code 0 if every report PASSes, non-zero if any report FAILs,
so this can gate a real cutover in CI or in an attended run.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import functools
import http.server
import socketserver
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
DRYRUN_DIR = REPO_ROOT / "docs" / "workspace" / "migration-dryrun"
PUBLISHED_DIR = DRYRUN_DIR / "published"
REPORT_PATH = DRYRUN_DIR / "REGRESSION-REPORT.md"

# DOM selectors that only exist once the report's inline render script has
# actually run against window.AUDIT_DATA (see render script's `init()` /
# `_boot()` -- these section ids are written by renderSections()/etc, not
# present in a static shell). If these are missing, the page rendered its
# skeleton but not its data.
SCORE_SELECTOR = "#score-heatmap"
FINDINGS_SELECTOR = "#section-said-found"
# NOTE: reports are a tabbed SPA — only the default-active tab's group is
# `display:block`; other tab groups (e.g. #group-audit) are `display:none`
# until clicked. document.body.innerText only returns VISIBLE text, so it
# undercounts by whichever tabs aren't active on load (verified: a real
# rendered report can show as little as ~1300 chars of *visible* text while
# still being fully correct). textContent ignores CSS visibility and pulls
# every tab's content regardless of which one is active, so it isn't
# fooled by tab state. A fully rendered report is ~500K+ chars of
# textContent; an empty/crashed shell (verified via a forced early-read)
# is under 1,000. 5,000 sits with wide margin on both sides.
MIN_BODY_TEXT_LEN = 5000


@dataclass
class ReportResult:
    slug: str
    url: str
    pageerrors: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    audit_data_ok: bool = False
    audit_data_reason: str = ""
    sections_ok: bool = False
    sections_reason: str = ""
    load_error: str | None = None

    @property
    def passed(self) -> bool:
        if self.load_error:
            return False
        return not self.pageerrors and self.audit_data_ok and self.sections_ok

    @property
    def verdict(self) -> str:
        return "PASS" if self.passed else "FAIL"


def discover_local_slugs() -> list[str]:
    if not PUBLISHED_DIR.is_dir():
        raise SystemExit(f"published dir not found: {PUBLISHED_DIR}")
    slugs = sorted(
        p.name
        for p in PUBLISHED_DIR.iterdir()
        if p.is_dir() and (p / "index.html").is_file()
    )
    if not slugs:
        raise SystemExit(f"no <slug>/index.html reports found under {PUBLISHED_DIR}")
    return slugs


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        pass  # local static server for a test harness; don't spam stdout


def start_local_server(root: Path) -> tuple[socketserver.TCPServer, int, threading.Thread]:
    handler = functools.partial(_QuietHandler, directory=str(root))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, port, thread


def parse_cookie_header(raw: str, domain: str) -> list[dict]:
    """Turn a raw `Cookie:`-header-style string into Playwright cookie dicts."""
    cookies = []
    for part in raw.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        cookies.append(
            {"name": name.strip(), "value": value.strip(), "domain": domain, "path": "/"}
        )
    return cookies


async def check_report(context, slug: str, url: str) -> ReportResult:
    result = ReportResult(slug=slug, url=url)
    page = await context.new_page()

    def on_pageerror(exc) -> None:
        result.pageerrors.append(str(exc))

    def on_console(msg) -> None:
        if msg.type == "error":
            result.console_errors.append(msg.text)

    page.on("pageerror", on_pageerror)
    page.on("console", on_console)

    try:
        await page.goto(url, wait_until="load", timeout=30_000)
        # The render script runs synchronously in _boot() on DOMContentLoaded,
        # writing window.AUDIT_DATA-derived DOM before 'load' fires — so by
        # the time goto() above resolves, rendering is already done. This is
        # a defensive extra wait, not the primary sync point. NOTE: don't use
        # wait_for_selector(state="visible") here — #score-heatmap sits
        # inside a tabbed group that is legitimately display:none when its
        # tab isn't the default-active one, so a visibility wait times out
        # even on a correctly rendered page.
        with contextlib.suppress(Exception):
            # Absence is asserted below via the audit_data check, not fatal here.
            await page.wait_for_function("() => !!window.AUDIT_DATA", timeout=5_000)

        audit_data = await page.evaluate(
            """() => {
                const d = window.AUDIT_DATA;
                if (!d || typeof d !== 'object') return null;
                const s = d.score;
                const score = s && typeof s.overall === 'number' ? s.overall : null;
                const findingsLen = Array.isArray(d.findings) ? d.findings.length : 0;
                const snapshotOk = d.company_snapshot && typeof d.company_snapshot === 'object'
                    && Object.keys(d.company_snapshot).length > 0;
                return { score, findingsLen, snapshotOk };
            }"""
        )
        if audit_data is None:
            result.audit_data_reason = "window.AUDIT_DATA missing or not an object"
        elif not audit_data["score"]:
            result.audit_data_reason = f"score.overall not truthy (got {audit_data['score']!r})"
        elif audit_data["findingsLen"] == 0 and not audit_data["snapshotOk"]:
            result.audit_data_reason = "findings empty AND company_snapshot empty"
        else:
            result.audit_data_ok = True

        score_present = await page.query_selector(SCORE_SELECTOR) is not None
        findings_present = await page.query_selector(FINDINGS_SELECTOR) is not None
        # textContent (not innerText) — see MIN_BODY_TEXT_LEN note above on
        # why innerText is the wrong signal for this tabbed layout.
        body_text = (await page.evaluate("document.body.textContent")) or ""
        body_len = len(body_text.strip())

        missing = []
        if not score_present:
            missing.append(f"{SCORE_SELECTOR} not in DOM")
        if not findings_present:
            missing.append(f"{FINDINGS_SELECTOR} not in DOM")
        if body_len < MIN_BODY_TEXT_LEN:
            missing.append(f"body text only {body_len} chars (< {MIN_BODY_TEXT_LEN})")

        if missing:
            result.sections_reason = "; ".join(missing)
        else:
            result.sections_ok = True

    except Exception as exc:  # navigation/timeout failure etc — this IS a real failure
        result.load_error = f"{type(exc).__name__}: {exc}"
    finally:
        await page.close()

    return result


async def run_mode_a(slugs: list[str]) -> list[ReportResult]:
    httpd, port, thread = start_local_server(PUBLISHED_DIR)
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()
            results = []
            for slug in slugs:
                url = f"http://127.0.0.1:{port}/{slug}/"
                results.append(await check_report(context, slug, url))
            await browser.close()
        return results
    finally:
        httpd.shutdown()
        thread.join(timeout=5)


async def run_mode_b(base: str, cookie: str | None, slugs: list[str]) -> list[ReportResult]:
    from urllib.parse import urlparse

    domain = urlparse(base).hostname or ""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        if cookie:
            await context.add_cookies(parse_cookie_header(cookie, domain))
        results = []
        for slug in slugs:
            url = f"{base.rstrip('/')}/{slug}/"
            results.append(await check_report(context, slug, url))
        await browser.close()
    return results


def render_report_md(results: list[ReportResult], mode: str) -> str:
    lines = [
        "# Post-Migration Regression Report",
        "",
        f"Mode: **{mode}**",
        "",
        "| Slug | Pageerrors | AUDIT_DATA ok | Sections ok | Verdict |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        pe = "0" if not r.pageerrors else f"{len(r.pageerrors)} FAIL"
        ad = "ok" if r.audit_data_ok else f"FAIL ({r.audit_data_reason})"
        sec = "ok" if r.sections_ok else f"FAIL ({r.sections_reason})"
        lines.append(f"| {r.slug} | {pe} | {ad} | {sec} | **{r.verdict}** |")

    failures = [r for r in results if not r.passed]
    if failures:
        lines += ["", "## Failure detail", ""]
        for r in failures:
            lines.append(f"### {r.slug} ({r.url})")
            if r.load_error:
                lines.append(f"- Load error: `{r.load_error}`")
            if r.pageerrors:
                lines.append("- Uncaught JS pageerrors:")
                for pe in r.pageerrors:
                    lines.append(f"  ```\n  {pe}\n  ```")
            if not r.audit_data_ok:
                lines.append(f"- AUDIT_DATA check failed: {r.audit_data_reason}")
            if not r.sections_ok:
                lines.append(f"- Section check failed: {r.sections_reason}")
            lines.append("")

    passed = sum(1 for r in results if r.passed)
    lines += ["", f"**{passed}/{len(results)} passed.**", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--base", default=None, help="Live base URL, e.g. https://prism.chowmes.com. Enables mode B"
    )
    parser.add_argument(
        "--cookie", default=None, help='Raw cookie header, e.g. "__session=<value>". Mode B only.'
    )
    parser.add_argument(
        "--slugs",
        default=None,
        help="Comma-separated slug list. Default: all local reports (mode A), required in mode B.",
    )
    args = parser.parse_args()

    if args.base:
        if not args.slugs:
            parser.error("--slugs is required when --base is given (mode B)")
        slugs = [s.strip() for s in args.slugs.split(",") if s.strip()]
        mode = f"B (live, base={args.base})"
        results = asyncio.run(run_mode_b(args.base, args.cookie, slugs))
    else:
        slugs = [s.strip() for s in args.slugs.split(",")] if args.slugs else discover_local_slugs()
        mode = "A (local dry run)"
        results = asyncio.run(run_mode_a(slugs))

    report_md = render_report_md(results, mode)
    print(report_md)

    DRYRUN_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report_md)
    print(f"\nWritten to {REPORT_PATH}", file=sys.stderr)

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
