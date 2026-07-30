"""Deterministic module executor for algolia-intel-traffic.

Replaces the claude -p agentic wrapper for this skill's data collection
step with pure Python: run the real collect-traffic.py subprocess, parse
its real structured stdout, and decide success/degraded/needs_human purely
in code -- never as an LLM judgment call.

Per the skill's own canonical rule (SKILL.md "PERMANENT HITL" banner):
SimilarWeb's API access is permanently dead. When endpoints_ok == 0, this
module marks NEEDS_HUMAN (a real logged-in SimilarWeb PRO browser capture
is required) and makes zero LLM calls -- it never falls back to an
estimate or lets anything "helpfully" fill the gap.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_SCRIPT_PATH = Path(
    "~/.claude/skills/algolia-search-audit/scripts/collect-traffic.py"
).expanduser()


class TrafficStatus:
    SUCCESS = "success"
    DEGRADED = "degraded"
    NEEDS_HUMAN = "needs_human"


@dataclass(frozen=True)
class TrafficModuleResult:
    status: str
    domain: str
    endpoints_called: int
    endpoints_ok: int
    json_output: str | None
    md_output: str | None
    reason: str


def _needs_human(domain: str, reason: str, *, endpoints_called: int = 0) -> TrafficModuleResult:
    return TrafficModuleResult(
        status=TrafficStatus.NEEDS_HUMAN,
        domain=domain,
        endpoints_called=endpoints_called,
        endpoints_ok=0,
        json_output=None,
        md_output=None,
        reason=reason,
    )


def run_traffic_module(
    domain: str,
    output_dir: Path,
    *,
    run_cmd_fn: Any = subprocess.run,
    script_path: Path = DEFAULT_SCRIPT_PATH,
) -> TrafficModuleResult:
    """Deterministic dispatch for algolia-intel-traffic. Every branch below
    is a plain if/else on a real subprocess exit code or a real parsed JSON
    field -- there is no LLM call anywhere in this function, by design."""
    proc = run_cmd_fn(
        ["python3", str(script_path), domain, str(output_dir)],
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        return _needs_human(
            domain,
            "collect-traffic.py exited non-zero (SimilarWeb API key missing or "
            "unavailable) -- per SKILL.md's PERMANENT HITL rule, this requires "
            "a real logged-in SimilarWeb PRO browser capture, not an automated "
            "retry or an estimate.",
        )

    stdout = (proc.stdout or "").strip()
    if not stdout:
        return _needs_human(domain, "collect-traffic.py produced no stdout output.")

    try:
        parsed = json.loads(stdout.splitlines()[-1])
    except (ValueError, IndexError) as exc:
        return _needs_human(domain, f"collect-traffic.py's stdout was not parseable JSON: {exc!r}")

    endpoints_ok = parsed.get("endpoints_ok", 0)
    endpoints_called = parsed.get("endpoints_called", 0)
    json_output = parsed.get("json_output")
    md_output = parsed.get("md_output")

    if endpoints_ok == 0:
        return _needs_human(
            domain,
            f"SimilarWeb API returned 0/{endpoints_called} successful endpoints -- "
            "the permanent-dead-key state per SKILL.md. Requires HITL browser "
            "capture; this module does not fabricate or estimate.",
            endpoints_called=endpoints_called,
        )

    if endpoints_ok < endpoints_called:
        return TrafficModuleResult(
            status=TrafficStatus.DEGRADED,
            domain=domain,
            endpoints_called=endpoints_called,
            endpoints_ok=endpoints_ok,
            json_output=json_output,
            md_output=md_output,
            reason=(
                f"{endpoints_ok}/{endpoints_called} endpoints succeeded -- partial data, real gaps."
            ),
        )

    return TrafficModuleResult(
        status=TrafficStatus.SUCCESS,
        domain=domain,
        endpoints_called=endpoints_called,
        endpoints_ok=endpoints_ok,
        json_output=json_output,
        md_output=md_output,
        reason="all endpoints succeeded",
    )
