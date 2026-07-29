#!/usr/bin/env python3
"""Render prism-runner's /status/<job_id> JSON as an ASCII progress board.

No dashboard exists yet (that's real future PRISM UI work) -- this stands in
for it now: one row per skill in SKILL_NAMES order, live status per row,
elapsed time, so a real v3 audit run is actually observable in this session
instead of being a black box for 30-90+ minutes. Reads the same JSON shape
prism-runner.py's handle_status returns; pass it via stdin or a file path.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

SKILL_NAMES = (
    "algolia-intel-company",
    "algolia-intel-techstack",
    "algolia-intel-traffic",
    "algolia-intel-competitors",
    "algolia-intel-financial-public",
    "algolia-intel-financial-private",
    "algolia-intel-investor",
    "algolia-intel-social",
    "algolia-intel-news",
    "algolia-intel-hiring",
    "algolia-intel-partner",
    "algolia-intel-industry",
    "algolia-intel-queries",
    "algolia-audit-browser",
    "algolia-audit-report",
    "algolia-audit-factcheck",
)


def _icon(result: str) -> str:
    if result == "PASS":
        return "[x]"
    if "escalating" in result or "BLOCKED" in result:
        return "[!]"
    if result == "DISPATCH FAILED":
        return "[!]"
    return "[ ]"


def render(job: dict, *, synthetic: bool = False) -> str:
    """`synthetic` MUST be True for any job dict that did not come from a
    real prism-runner.py job (e.g. a renderer self-test, a hand-built fixture).
    This is not decoration -- a prior real incident: this renderer's own
    self-test fed fake dispatch/gate results labeled with REAL skill names
    (algolia-intel-traffic, etc.) and the resulting board was indistinguishable
    from a real audit PASS report. `synthetic=True` forces an unmissable
    banner on every line of output so that can never happen again."""
    completed = {s["skill"]: s["result"] for s in job.get("skills_completed") or []}
    current = job.get("current_skill")
    current_status = job.get("current_skill_status", "")
    total = job.get("skills_total", len(SKILL_NAMES))

    lines = []
    if synthetic:
        lines.append("#" * 70)
        lines.append("### SYNTHETIC TEST DATA -- NOT A REAL AUDIT RUN -- DO NOT TRUST ###")
        lines.append("#" * 70)
        lines.append("")
    slug = job.get("slug") or job.get("domain") or "?"
    lines.append(f"PRISM audit -- {slug}  (job_id={job.get('job_id', '?')}, engine=v3)")
    lines.append(f"status={job.get('status', '?')}  as of {datetime.now(UTC).strftime('%H:%M:%S')} UTC")
    lines.append("")

    done_count = 0
    for name in SKILL_NAMES:
        if name in completed:
            result = completed[name]
            icon = _icon(result)
            done_count += 1
            lines.append(f"  {icon} {name:<32} {result}")
        elif name == current:
            lines.append(f"  [>] {name:<32} RUNNING -- {current_status or 'dispatching...'}")
        else:
            lines.append(f"  [ ] {name:<32} pending")

    lines.append("")
    blocked = sum(1 for r in completed.values() if "BLOCKED" in r or "FAILED" in r)
    lines.append(f"Progress: {done_count}/{total} skills reached a terminal attempt, {blocked} flagged")
    if job.get("needs_human"):
        lines.append(f"NEEDS_HUMAN: {json.dumps(job['needs_human'])}")
    if synthetic:
        lines.append("")
        lines.append("#" * 70)
        lines.append("### SYNTHETIC TEST DATA -- NOT A REAL AUDIT RUN -- DO NOT TRUST ###")
        lines.append("#" * 70)
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="REQUIRED for any non-real job (renderer self-tests, hand-built "
        "fixtures) -- forces an unmissable banner so synthetic output is "
        "never mistaken for a real audit result.",
    )
    parser.add_argument(
        "--real",
        action="store_true",
        help="Explicit opposite of --synthetic, for a job.json actually "
        "written by a real prism-runner.py process. Exactly one of "
        "--synthetic/--real is required -- no silent default.",
    )
    args = parser.parse_args()
    if args.synthetic == args.real:
        parser.error("pass exactly one of --synthetic or --real -- no default, by design")
    raw = sys.stdin.read() if not args.path else open(args.path).read()
    print(render(json.loads(raw), synthetic=args.synthetic))
