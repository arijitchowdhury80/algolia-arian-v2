"""Regression tests for the prism-report-qa plugin's company-matching logic.

Loaded directly from the live-sources snapshot (docs/workspace/cassandra-tooling/
live-sources/prism-report-qa__init__.py) since the plugin only runs on the VPS and
isn't an importable package. Keep that snapshot synced with the live VPS file
(`/root/.hermes-prism/plugins/prism-report-qa/__init__.py`) whenever the plugin changes.

Covers the "running" token-collision bug found live 2026-07-03: a company named
"Brooks Running" contributes the bare English word "running" as a match token, so
any message containing that ordinary word (e.g. cron's own "you are running as a
scheduled job" boilerplate, or "is the audit still running?") falsely bound every
session to the Brooks Running report. See memory
project-cassandra-live-patches-2026-07-03.md and
docs/plans/2026-07-02-cassandra-airtight-pipeline-goal.md.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "workspace"
    / "cassandra-tooling"
    / "live-sources"
    / "prism-report-qa__init__.py"
)


def _load_plugin_module():
    spec = importlib.util.spec_from_file_location("prism_report_qa_plugin", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


plugin = _load_plugin_module()

BROOKS_RUNNING_ROW = {
    "slug": "brooks-running",
    "domain": "brooksrunning.com",
    "company": "Brooks Running",
}
BELK_ROW = {
    "slug": "belk",
    "domain": "belk.com",
    "company": "Belk",
}
INDEX_ROWS = [BROOKS_RUNNING_ROW, BELK_ROW]


@pytest.fixture(autouse=True)
def fixed_index(monkeypatch: pytest.MonkeyPatch):
    """Stub the report index so tests don't depend on the real reports directory."""
    monkeypatch.setattr(plugin, "_load_index", lambda: INDEX_ROWS)


class TestRunningTokenCollision:
    """The exact bug: 'running' is a common English word, not a distinctive company token."""

    def test_generic_status_message_does_not_bind_to_brooks_running(self):
        assert plugin._match_slug("is the audit still running?") is None

    def test_cron_boilerplate_does_not_bind_to_brooks_running(self):
        cron_hint = (
            "[IMPORTANT: You are running as a scheduled cron job. "
            "DELIVERY: Your final response will be automatically delivered "
            "to the user.]"
        )
        assert plugin._match_slug(cron_hint) is None

    def test_check_job_status_message_does_not_bind_to_brooks_running(self):
        msg = "Check the live status of the audit job 'belk-20260703-074150' and report it."
        # Should match Belk (via the job-id containing the slug), never Brooks Running.
        assert plugin._match_slug(msg) == "belk"


class TestLegitimateMatchesStillWork:
    """The fix must not break real company identification."""

    def test_exact_company_name_matches(self):
        assert plugin._match_slug("What's the status of the Brooks Running audit?") == "brooks-running"

    def test_domain_mention_matches(self):
        assert plugin._match_slug("pull up brooksrunning.com for me") == "brooks-running"

    def test_slug_mention_matches(self):
        assert plugin._match_slug("open the belk report") == "belk"

    def test_no_match_returns_none(self):
        assert plugin._match_slug("hey, how's it going today?") is None

    def test_empty_message_returns_none(self):
        assert plugin._match_slug("") is None
        assert plugin._match_slug(None) is None
