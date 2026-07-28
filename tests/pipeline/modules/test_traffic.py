"""Tests for the deterministic algolia-intel-traffic module executor.

Every branch is exercised with a FAKE run_cmd_fn (dependency-injected, no
real subprocess) except one real-live test at the bottom, which proves the
actual dead-SimilarWeb-key state produces NEEDS_HUMAN for real, not just
in theory.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from prism_platform.pipeline.modules.traffic import (
    DEFAULT_SCRIPT_PATH,
    TrafficStatus,
    run_traffic_module,
)


def _fake_proc(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_nonzero_exit_is_needs_human_not_a_crash():
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return _fake_proc(returncode=1, stderr="ERROR: SIMILARWEB_API_KEY not set")

    result = run_traffic_module("dsw.com", Path("/tmp/x"), run_cmd_fn=fake_run)
    assert result.status == TrafficStatus.NEEDS_HUMAN
    assert result.endpoints_ok == 0
    assert "non-zero" in result.reason
    assert len(calls) == 1


def test_zero_ok_endpoints_is_needs_human_not_estimate():
    """The dead-API-key state -- must never fall back to an estimate."""

    def fake_run(cmd, **kw):
        payload = {
            "status": "partial",
            "domain": "dsw.com",
            "endpoints_called": 15,
            "endpoints_ok": 0,
            "json_output": "/tmp/x/03-traffic-data.json",
            "md_output": "/tmp/x/03-traffic-data.md",
            "errors": ["401 on all endpoints"],
        }
        return _fake_proc(returncode=0, stdout=json.dumps(payload))

    result = run_traffic_module("dsw.com", Path("/tmp/x"), run_cmd_fn=fake_run)
    assert result.status == TrafficStatus.NEEDS_HUMAN
    assert result.endpoints_called == 15
    assert result.endpoints_ok == 0
    assert "0/15" in result.reason
    assert "does not fabricate or estimate" in result.reason


def test_partial_success_is_degraded_not_success():
    def fake_run(cmd, **kw):
        payload = {
            "endpoints_called": 15,
            "endpoints_ok": 10,
            "json_output": "/tmp/x/03-traffic-data.json",
            "md_output": "/tmp/x/03-traffic-data.md",
        }
        return _fake_proc(returncode=0, stdout=json.dumps(payload))

    result = run_traffic_module("dsw.com", Path("/tmp/x"), run_cmd_fn=fake_run)
    assert result.status == TrafficStatus.DEGRADED
    assert result.endpoints_ok == 10
    assert result.endpoints_called == 15


def test_all_endpoints_ok_is_success():
    def fake_run(cmd, **kw):
        payload = {
            "endpoints_called": 15,
            "endpoints_ok": 15,
            "json_output": "/tmp/x/03-traffic-data.json",
            "md_output": "/tmp/x/03-traffic-data.md",
        }
        return _fake_proc(returncode=0, stdout=json.dumps(payload))

    result = run_traffic_module("dsw.com", Path("/tmp/x"), run_cmd_fn=fake_run)
    assert result.status == TrafficStatus.SUCCESS
    assert result.endpoints_ok == result.endpoints_called == 15


def test_empty_stdout_is_needs_human_not_a_crash():
    def fake_run(cmd, **kw):
        return _fake_proc(returncode=0, stdout="")

    result = run_traffic_module("dsw.com", Path("/tmp/x"), run_cmd_fn=fake_run)
    assert result.status == TrafficStatus.NEEDS_HUMAN
    assert "no stdout" in result.reason


def test_malformed_json_is_needs_human_not_a_crash():
    def fake_run(cmd, **kw):
        return _fake_proc(returncode=0, stdout="not json at all {{{")

    result = run_traffic_module("dsw.com", Path("/tmp/x"), run_cmd_fn=fake_run)
    assert result.status == TrafficStatus.NEEDS_HUMAN
    assert "not parseable JSON" in result.reason


def test_real_command_shape_invokes_the_real_script_path():
    """Proves the default script_path really points at the real skill
    script on disk (not a guessed/wrong path) -- fails loudly if the skill
    ever moves without this module being updated."""
    assert DEFAULT_SCRIPT_PATH.exists(), (
        f"collect-traffic.py not found at {DEFAULT_SCRIPT_PATH} -- "
        "the skill moved or this path is stale"
    )
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return _fake_proc(
            returncode=0, stdout=json.dumps({"endpoints_called": 1, "endpoints_ok": 1})
        )

    run_traffic_module("dsw.com", Path("/tmp/x"), run_cmd_fn=fake_run)
    assert captured["cmd"][0] == "python3"
    assert captured["cmd"][1] == str(DEFAULT_SCRIPT_PATH)
    assert captured["cmd"][2] == "dsw.com"
    assert captured["cmd"][3] == "/tmp/x"


def test_real_live_dead_key_produces_needs_human_for_real(tmp_path):
    """LIVE test, no mocking: runs the ACTUAL collect-traffic.py subprocess
    against the real (dead) SimilarWeb key state on this machine. Proves
    the deterministic module's behavior against reality, not just a fake --
    this is the actual claim this whole module exists to make true."""
    result = run_traffic_module("dsw.com", tmp_path)
    assert result.status == TrafficStatus.NEEDS_HUMAN
    assert result.endpoints_ok == 0
